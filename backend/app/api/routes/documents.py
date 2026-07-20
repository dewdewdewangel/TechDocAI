import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.api.rate_limits import enforce_limit
from app.core.config import settings
from app.models import (
    Document,
    DocumentPublic,
    DocumentsPublic,
    Message,
    get_datetime_utc,
)
from app.services.audit import record_audit_event
from app.services.document_queue import (
    DocumentQueueError,
    enqueue_document_processing,
)
from app.services.rate_limit import enforce_upload_limit

router = APIRouter(prefix="/documents", tags=["documents"])

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf"}
COPY_CHUNK_SIZE = 1024 * 1024


def _enqueue_document(session: SessionDep, document: Document) -> None:
    try:
        enqueue_document_processing(document.id)
    except DocumentQueueError as exc:
        document.status = "failed"
        document.error_message = str(exc)
        document.updated_at = get_datetime_utc()
        session.add(document)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document processing queue is not available",
        ) from exc


@router.get("/", response_model=DocumentsPublic)
def read_documents(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Document)
        statement = select(Document)
    else:
        count_statement = (
            select(func.count())
            .select_from(Document)
            .where(Document.owner_id == current_user.id)
        )
        statement = select(Document).where(Document.owner_id == current_user.id)

    count = session.exec(count_statement).one()
    documents = session.exec(
        statement.order_by(col(Document.created_at).desc()).offset(skip).limit(limit)
    ).all()

    return DocumentsPublic(
        data=[DocumentPublic.model_validate(document) for document in documents],
        count=count,
    )


@router.post("/upload", response_model=DocumentPublic)
async def upload_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
) -> Any:
    enforce_limit(enforce_upload_limit, current_user.id)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    safe_filename = Path(file.filename.replace("\\", "/")).name

    extension = Path(safe_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only TXT, Markdown, and PDF files are supported",
        )

    document_title = (title or safe_filename).strip() or safe_filename
    if len(document_title) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document title must not exceed 255 characters",
        )

    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid.uuid4().hex}{extension}"
    storage_path = settings.UPLOAD_DIR / stored_filename
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file_size = 0

    try:
        with storage_path.open("wb") as output:
            while chunk := await file.read(COPY_CHUNK_SIZE):
                file_size += len(chunk)

                if file_size > max_size:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(f"File size exceeds {settings.MAX_UPLOAD_SIZE_MB} MB"),
                    )

                output.write(chunk)

        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty files are not allowed",
            )

        document = Document(
            title=document_title,
            filename=safe_filename,
            content_type=file.content_type,
            file_size=file_size,
            status="queued",
            storage_path=str(storage_path),
            owner_id=current_user.id,
        )

        session.add(document)
        session.commit()
        session.refresh(document)

    except Exception:
        session.rollback()
        storage_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    _enqueue_document(session, document)
    record_audit_event(
        session,
        actor_id=current_user.id,
        action="document.upload",
        resource_type="document",
        resource_id=document.id,
        details={"filename": document.filename},
    )
    session.commit()
    return document


@router.get("/{document_id}", response_model=DocumentPublic)
def read_document(
    session: SessionDep,
    current_user: CurrentUser,
    document_id: uuid.UUID,
) -> Any:
    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if not current_user.is_superuser and document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return document


@router.post("/{document_id}/reindex", response_model=DocumentPublic)
def reindex_document(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    document_id: uuid.UUID,
) -> Any:
    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if not current_user.is_superuser and document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    if document.status in {"queued", "processing"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already being processed",
        )

    document.status = "queued"
    document.error_message = None
    document.updated_at = get_datetime_utc()
    session.add(document)
    session.commit()
    session.refresh(document)

    _enqueue_document(session, document)
    record_audit_event(
        session,
        actor_id=current_user.id,
        action="document.reindex",
        resource_type="document",
        resource_id=document.id,
    )
    session.commit()
    return document


@router.delete("/{document_id}", response_model=Message)
def delete_document(
    session: SessionDep,
    current_user: CurrentUser,
    document_id: uuid.UUID,
) -> Message:
    document = session.get(Document, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if not current_user.is_superuser and document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    storage_path = Path(document.storage_path)

    record_audit_event(
        session,
        actor_id=current_user.id,
        action="document.delete",
        resource_type="document",
        resource_id=document.id,
        details={"filename": document.filename},
    )
    session.delete(document)
    session.commit()

    try:
        storage_path.unlink(missing_ok=True)
    except OSError:
        logger.warning(
            "Failed to delete document file: %s",
            storage_path,
            exc_info=True,
        )

    return Message(message="Document deleted successfully")
