import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.api.rate_limits import enforce_limit
from app.core.config import settings
from app.models import (
    AnswerCitation,
    ChatAskResponse,
    ChatCitationPublic,
    ChatMessage,
    ChatMessageCreate,
    ChatMessagePublic,
    ChatMessagesPublic,
    ChatSession,
    ChatSessionCreate,
    ChatSessionPublic,
    ChatSessionsPublic,
    Document,
    DocumentChunk,
    Message,
)
from app.services.audit import record_audit_event
from app.services.llm import (
    LLMConfigurationError,
    LLMServiceError,
    generate_answer,
)
from app.services.rate_limit import enforce_chat_limits
from app.services.retrieval import search_chunks

router = APIRouter(prefix="/chat-sessions", tags=["chat-sessions"])


def _get_chat_session(
    *, session: SessionDep, current_user: CurrentUser, session_id: uuid.UUID
) -> ChatSession:
    chat_session = session.get(ChatSession, session_id)
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found",
        )
    if not current_user.is_superuser and chat_session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return chat_session


def _message_public(
    message: ChatMessage,
    citations: list[ChatCitationPublic] | None = None,
) -> ChatMessagePublic:
    return ChatMessagePublic(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        citations=citations or [],
    )


def _messages_public(
    *, session: SessionDep, messages: list[ChatMessage]
) -> list[ChatMessagePublic]:
    if not messages:
        return []

    message_ids = [message.id for message in messages]
    rows = session.exec(
        select(AnswerCitation, DocumentChunk, Document)
        .join(DocumentChunk, col(AnswerCitation.chunk_id) == col(DocumentChunk.id))
        .join(Document, col(DocumentChunk.document_id) == col(Document.id))
        .where(col(AnswerCitation.message_id).in_(message_ids))
        .order_by(
            col(AnswerCitation.message_id).asc(),
            col(AnswerCitation.message_id).asc(),
            col(AnswerCitation.created_at).asc(),
        )
    ).all()

    citations_by_message: dict[uuid.UUID, list[ChatCitationPublic]] = {}
    for citation, chunk, document in rows:
        citations_by_message.setdefault(citation.message_id, []).append(
            ChatCitationPublic(
                chunk_id=chunk.id,
                document_id=document.id,
                document_title=document.title,
                content=chunk.content,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                relevance_score=citation.relevance_score or 0.0,
            )
        )

    return [
        _message_public(message, citations_by_message.get(message.id, []))
        for message in messages
    ]


@router.get("/", response_model=ChatSessionsPublic)
def read_chat_sessions(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(ChatSession)
        statement = select(ChatSession)
    else:
        count_statement = (
            select(func.count())
            .select_from(ChatSession)
            .where(ChatSession.owner_id == current_user.id)
        )
        statement = select(ChatSession).where(ChatSession.owner_id == current_user.id)

    count = session.exec(count_statement).one()
    chat_sessions = session.exec(
        statement.order_by(col(ChatSession.created_at).desc()).offset(skip).limit(limit)
    ).all()

    return ChatSessionsPublic(
        data=[ChatSessionPublic.model_validate(item) for item in chat_sessions],
        count=count,
    )


@router.post("/", response_model=ChatSessionPublic)
def create_chat_session(
    *, session: SessionDep, current_user: CurrentUser, session_in: ChatSessionCreate
) -> Any:
    chat_session = ChatSession.model_validate(
        session_in, update={"owner_id": current_user.id}
    )
    session.add(chat_session)
    record_audit_event(
        session,
        actor_id=current_user.id,
        action="chat_session.create",
        resource_type="chat_session",
        resource_id=chat_session.id,
    )
    session.commit()
    session.refresh(chat_session)
    return chat_session


@router.get("/{session_id}/messages", response_model=ChatMessagesPublic)
def read_chat_messages(
    session: SessionDep, current_user: CurrentUser, session_id: uuid.UUID
) -> Any:
    _get_chat_session(
        session=session,
        current_user=current_user,
        session_id=session_id,
    )

    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(col(ChatMessage.created_at).asc())
    )
    messages = session.exec(statement).all()
    public_messages = _messages_public(session=session, messages=list(messages))

    return ChatMessagesPublic(
        data=public_messages,
        count=len(public_messages),
    )


@router.post("/{session_id}/ask", response_model=ChatAskResponse)
def ask_chat_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    session_id: uuid.UUID,
    message_in: ChatMessageCreate,
) -> Any:
    enforce_limit(enforce_chat_limits, current_user.id)

    chat_session = _get_chat_session(
        session=session,
        current_user=current_user,
        session_id=session_id,
    )

    history = list(
        session.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(col(ChatMessage.created_at).desc())
            .limit(settings.LLM_HISTORY_MESSAGES)
        ).all()
    )
    history.reverse()

    try:
        results = search_chunks(
            session=session,
            owner_id=chat_session.owner_id,
            query=message_in.content,
            top_k=settings.RETRIEVAL_TOP_K,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service is not available",
        ) from exc

    if results:
        try:
            answer = generate_answer(
                question=message_in.content,
                chunks=results,
                history=history,
            )
        except LLMConfigurationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except LLMServiceError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
    else:
        answer = "没有从已索引的文档中找到足够信息来回答这个问题。"

    user_message = ChatMessage(
        session_id=session_id,
        role="user",
        content=message_in.content,
    )
    assistant_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
    )
    session.add_all([user_message, assistant_message])
    session.flush()

    citations = [
        AnswerCitation(
            message_id=assistant_message.id,
            chunk_id=result.chunk_id,
            relevance_score=result.score,
        )
        for result in results
    ]
    session.add_all(citations)

    chat_session.updated_at = user_message.created_at
    if chat_session.title.strip() == "New Chat":
        chat_session.title = message_in.content.strip().replace("\n", " ")[:80]
    session.add(chat_session)
    record_audit_event(
        session,
        actor_id=current_user.id,
        action="chat.ask",
        resource_type="chat_session",
        resource_id=chat_session.id,
        details={
            "owner_id": str(chat_session.owner_id),
            "citation_count": len(citations),
        },
    )
    session.commit()

    session.refresh(user_message)
    session.refresh(assistant_message)
    session.refresh(chat_session)

    citation_models = [
        ChatCitationPublic(
            chunk_id=result.chunk_id,
            document_id=result.document_id,
            document_title=result.document_title,
            content=result.content,
            page_number=result.page_number,
            chunk_index=result.chunk_index,
            relevance_score=result.score,
        )
        for result in results
    ]

    return ChatAskResponse(
        session=ChatSessionPublic.model_validate(chat_session),
        user_message=_message_public(user_message),
        assistant_message=_message_public(assistant_message, citation_models),
    )


@router.delete("/{session_id}", response_model=Message)
def delete_chat_session(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    session_id: uuid.UUID,
) -> Message:
    chat_session = _get_chat_session(
        session=session,
        current_user=current_user,
        session_id=session_id,
    )
    record_audit_event(
        session,
        actor_id=current_user.id,
        action="chat_session.delete",
        resource_type="chat_session",
        resource_id=chat_session.id,
    )
    session.delete(chat_session)
    session.commit()
    return Message(message="Chat session deleted successfully")
