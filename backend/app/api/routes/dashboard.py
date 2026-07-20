from fastapi import APIRouter
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ChatMessage,
    ChatSession,
    DashboardSummary,
    Document,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def read_dashboard_summary(
    session: SessionDep,
    current_user: CurrentUser,
) -> DashboardSummary:
    document_filter = (
        True if current_user.is_superuser else Document.owner_id == current_user.id
    )
    session_filter = (
        True if current_user.is_superuser else ChatSession.owner_id == current_user.id
    )

    document_count = session.exec(
        select(func.count()).select_from(Document).where(document_filter)
    ).one()
    indexed_document_count = session.exec(
        select(func.count())
        .select_from(Document)
        .where(document_filter, Document.status == "indexed")
    ).one()
    failed_document_count = session.exec(
        select(func.count())
        .select_from(Document)
        .where(document_filter, Document.status == "failed")
    ).one()
    chat_session_count = session.exec(
        select(func.count()).select_from(ChatSession).where(session_filter)
    ).one()

    question_statement = (
        select(func.count())
        .select_from(ChatMessage)
        .join(ChatSession)
        .where(ChatMessage.role == "user")
    )
    if not current_user.is_superuser:
        question_statement = question_statement.where(
            ChatSession.owner_id == current_user.id
        )
    question_count = session.exec(question_statement).one()

    return DashboardSummary(
        document_count=document_count,
        indexed_document_count=indexed_document_count,
        failed_document_count=failed_document_count,
        chat_session_count=chat_session_count,
        question_count=question_count,
    )
