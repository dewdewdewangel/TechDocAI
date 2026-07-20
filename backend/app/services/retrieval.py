import uuid

from sqlmodel import Session, select

from app.core.config import settings
from app.models import Document, DocumentChunk, RetrievalResult
from app.services.embedding import embed_texts


def search_chunks(
    session: Session,
    owner_id: uuid.UUID,
    query: str,
    top_k: int,
    min_score: float | None = None,
) -> list[RetrievalResult]:
    query_embedding = embed_texts([query])[0]

    distance = DocumentChunk.embedding.cosine_distance(  # type: ignore
        query_embedding
    )

    statement = (
        select(DocumentChunk, Document, distance.label("distance"))
        .join(Document)
        .where(
            Document.owner_id == owner_id,
            Document.status == "indexed",
            DocumentChunk.embedding.is_not(None),  # type: ignore
        )
        .order_by(distance)
        .limit(top_k)
    )

    rows = session.exec(statement).all()

    results = [
        RetrievalResult(
            chunk_id=chunk.id,
            document_id=document.id,
            document_title=document.title,
            content=chunk.content,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            score=max(0.0, min(1.0, 1 - float(distance_value))),
        )
        for chunk, document, distance_value in rows
    ]

    threshold = settings.RETRIEVAL_MIN_SCORE if min_score is None else min_score
    return [result for result in results if result.score >= threshold]
