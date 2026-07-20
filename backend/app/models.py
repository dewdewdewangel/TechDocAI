import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from pgvector.sqlalchemy import VECTOR
from pydantic import EmailStr
from sqlalchemy import JSON, DateTime, Text
from sqlmodel import Field, Relationship, SQLModel

from app.core.constants import EMBEDDING_DIMENSIONS


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    documents: list[Document] = Relationship(
        back_populates="owner", cascade_delete=True
    )

    chat_sessions: list[ChatSession] = Relationship(
        back_populates="owner", cascade_delete=True
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Documents models


class DocumentBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=100)
    file_size: int | None = Field(default=None, ge=0)
    status: str = Field(default="uploaded", max_length=50)
    summary: str | None = Field(default=None, max_length=2000)
    chunk_count: int = Field(default=0, ge=0)
    error_message: str | None = Field(default=None, max_length=2000)


class DocumentCreate(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=2000)


class DocumentUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, max_length=50)
    summary: str | None = Field(default=None, max_length=2000)


class Document(DocumentBase, table=True):
    __tablename__: ClassVar[str] = "document"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )

    owner: User | None = Relationship(back_populates="documents")
    chunks: list[DocumentChunk] = Relationship(
        back_populates="document", cascade_delete=True
    )
    storage_path: str = Field(max_length=500)


class DocumentPublic(DocumentBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentsPublic(SQLModel):
    data: list[DocumentPublic]
    count: int


# Document chunk models
class DocumentChunkBase(SQLModel):
    content: str = Field(sa_type=Text)
    chunk_index: int = Field(ge=0)
    page_number: int | None = Field(default=None, ge=1)
    token_count: int | None = Field(default=None, ge=0)


class DocumentChunk(DocumentChunkBase, table=True):
    __tablename__: ClassVar[str] = "document_chunk"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        foreign_key="document.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    document: Document | None = Relationship(back_populates="chunks")
    citations: list[AnswerCitation] = Relationship(
        back_populates="chunk", cascade_delete=True
    )
    embedding: list[float] | None = Field(
        default=None,
        sa_type=VECTOR(EMBEDDING_DIMENSIONS),  # type: ignore
    )


class DocumentChunkPublic(DocumentChunkBase):
    id: uuid.UUID
    document_id: uuid.UUID
    created_at: datetime | None = None


class DocumentChunksPublic(SQLModel):
    data: list[DocumentChunkPublic]
    count: int


# Chat session models


class ChatSessionBase(SQLModel):
    title: str = Field(default="New Chat", min_length=1, max_length=255)


class ChatSession(ChatSessionBase, table=True):
    __tablename__: ClassVar[str] = "chat_session"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    updated_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    owner: User | None = Relationship(back_populates="chat_sessions")
    messages: list[ChatMessage] = Relationship(
        back_populates="session", cascade_delete=True
    )


class ChatSessionPublic(ChatSessionBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ChatSessionsPublic(SQLModel):
    data: list[ChatSessionPublic]
    count: int


# Chat message models
class ChatMessageBase(SQLModel):
    role: str = Field(max_length=20)
    content: str = Field(sa_type=Text)


class ChatMessageCreate(SQLModel):
    content: str = Field(min_length=1)


class ChatMessage(ChatMessageBase, table=True):
    __tablename__: ClassVar[str] = "chat_message"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(
        foreign_key="chat_session.id", nullable=False, ondelete="CASCADE"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    session: ChatSession | None = Relationship(back_populates="messages")
    citations: list[AnswerCitation] = Relationship(
        back_populates="message", cascade_delete=True
    )


class ChatCitationPublic(SQLModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    content: str
    page_number: int | None = None
    chunk_index: int
    relevance_score: float = Field(ge=0, le=1)


class ChatMessagePublic(ChatMessageBase):
    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime | None = None
    citations: list[ChatCitationPublic] = Field(default_factory=list)


class ChatMessagesPublic(SQLModel):
    data: list[ChatMessagePublic]
    count: int


class ChatAskResponse(SQLModel):
    session: ChatSessionPublic
    user_message: ChatMessagePublic
    assistant_message: ChatMessagePublic


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)


# Answer citation models
class AnswerCitation(SQLModel, table=True):
    __tablename__: ClassVar[str] = "answer_citation"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    message_id: uuid.UUID = Field(
        foreign_key="chat_message.id", nullable=False, ondelete="CASCADE"
    )
    chunk_id: uuid.UUID = Field(
        foreign_key="document_chunk.id", nullable=False, ondelete="CASCADE"
    )
    relevance_score: float | None = Field(default=None, ge=0)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )

    message: ChatMessage | None = Relationship(back_populates="citations")
    chunk: DocumentChunk | None = Relationship(back_populates="citations")


class AnswerCitationPublic(SQLModel):
    id: uuid.UUID
    message_id: uuid.UUID
    chunk_id: uuid.UUID
    relevance_score: float | None = None
    created_at: datetime | None = None


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class RetrievalRequest(SQLModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalResult(SQLModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    content: str
    page_number: int | None
    chunk_index: int
    score: float = Field(ge=0, le=1)


class RetrievalResults(SQLModel):
    data: list[RetrievalResult]


class DashboardSummary(SQLModel):
    document_count: int
    indexed_document_count: int
    failed_document_count: int
    chat_session_count: int
    question_count: int


class AuditLog(SQLModel, table=True):
    __tablename__: ClassVar[str] = "audit_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    actor_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        index=True,
    )
    action: str = Field(max_length=100, index=True)
    resource_type: str = Field(max_length=100, index=True)
    resource_id: str | None = Field(default=None, max_length=100)
    details: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
        index=True,
    )


class AuditLogPublic(SQLModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict[str, Any]
    created_at: datetime


class AuditLogsPublic(SQLModel):
    data: list[AuditLogPublic]
    count: int
