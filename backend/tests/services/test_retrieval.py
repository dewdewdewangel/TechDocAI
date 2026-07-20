import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.retrieval import search_chunks


def test_search_chunks_filters_below_minimum_score() -> None:
    relevant_chunk = SimpleNamespace(
        id=uuid.uuid4(),
        content="relevant",
        page_number=1,
        chunk_index=0,
    )
    irrelevant_chunk = SimpleNamespace(
        id=uuid.uuid4(),
        content="irrelevant",
        page_number=2,
        chunk_index=1,
    )
    document = SimpleNamespace(id=uuid.uuid4(), title="guide.md")
    session = MagicMock()
    session.exec.return_value.all.return_value = [
        (relevant_chunk, document, 0.1),
        (irrelevant_chunk, document, 0.9),
    ]

    with patch(
        "app.services.retrieval.embed_texts",
        return_value=[[0.0] * 1024],
    ):
        results = search_chunks(
            session=session,
            owner_id=uuid.uuid4(),
            query="question",
            top_k=5,
            min_score=0.35,
        )

    assert [result.content for result in results] == ["relevant"]
