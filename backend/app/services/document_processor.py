import logging
import uuid
from pathlib import Path

import sentry_sdk
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.core.observability import DOCUMENT_JOBS
from app.models import Document, DocumentChunk, get_datetime_utc
from app.services.document_parser import parse_document
from app.services.embedding import embed_texts
from app.services.text_splitter import split_text

logger = logging.getLogger(__name__)


class DocumentProcessingError(RuntimeError):
    pass


def process_document(document_id: uuid.UUID) -> None:
    with Session(engine) as session:
        document = session.exec(
            select(Document).where(Document.id == document_id).with_for_update()
        ).one_or_none()
        if document is None:
            return

        if document.status not in {"queued", "failed"}:
            logger.info(
                "Skipping document %s with status %s",
                document_id,
                document.status,
            )
            return

        document.status = "processing"
        document.error_message = None
        document.updated_at = get_datetime_utc()
        session.add(document)
        session.commit()

        try:
            pages = parse_document(Path(document.storage_path))
            chunks: list[DocumentChunk] = []
            chunk_index = 0

            for page_number, text in pages:
                for content in split_text(
                    text,
                    settings.CHUNK_SIZE,
                    settings.CHUNK_OVERLAP,
                ):
                    chunks.append(
                        DocumentChunk(
                            document_id=document.id,
                            content=content,
                            chunk_index=chunk_index,
                            page_number=page_number,
                        )
                    )
                    chunk_index += 1

            if not chunks:
                raise ValueError("No readable text found in document")

            embeddings = embed_texts([chunk.content for chunk in chunks])

            for chunk, embedding in zip(chunks, embeddings, strict=True):
                chunk.embedding = embedding

            old_chunks = session.exec(
                select(DocumentChunk).where(DocumentChunk.document_id == document.id)
            ).all()
            for chunk in old_chunks:
                session.delete(chunk)

            session.add_all(chunks)
            document.status = "indexed"
            document.chunk_count = len(chunks)
            document.error_message = None
            document.updated_at = get_datetime_utc()
            session.add(document)
            session.commit()
            DOCUMENT_JOBS.labels(result="success").inc()

        except Exception as exc:
            DOCUMENT_JOBS.labels(result="error").inc()
            sentry_sdk.capture_exception(exc)
            logger.exception("Failed to process document %s", document_id)
            session.rollback()
            document = session.get(Document, document_id)
            if document is not None:
                document.status = "failed"
                document.error_message = (str(exc) or type(exc).__name__)[:2000]
                document.updated_at = get_datetime_utc()
                session.add(document)
                session.commit()

            raise DocumentProcessingError(
                f"Failed to process document {document_id}"
            ) from exc
