import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import AnswerCitation, ChatMessage, ChatSession, Document, DocumentChunk
from tests.utils.user import create_random_user


def test_upload_document_queues_processing(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    with (
        patch("app.api.routes.documents.enforce_upload_limit"),
        patch("app.api.routes.documents.enqueue_document_processing") as enqueue,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/documents/upload",
            headers=normal_user_token_headers,
            files={"file": ("guide.txt", b"TechDoc AI guide", "text/plain")},
            data={"title": "Guide"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["title"] == "Guide"
    enqueue.assert_called_once()

    delete_response = client.delete(
        f"{settings.API_V1_STR}/documents/{body['id']}",
        headers=normal_user_token_headers,
    )
    assert delete_response.status_code == 200


def test_user_cannot_read_another_users_document(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
    tmp_path: Path,
) -> None:
    owner = create_random_user(db)
    path = tmp_path / "private.txt"
    path.write_text("private", encoding="utf-8")
    document = Document(
        title="Private",
        filename=path.name,
        file_size=path.stat().st_size,
        status="indexed",
        storage_path=str(path),
        owner_id=owner.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    response = client.get(
        f"{settings.API_V1_STR}/documents/{document.id}",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 403
    db.delete(document)
    db.commit()


def test_reindex_rejects_duplicate_queued_task(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
    tmp_path: Path,
) -> None:
    me = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    ).json()
    path = tmp_path / "queued.txt"
    path.write_text("queued", encoding="utf-8")
    document = Document(
        title="Queued",
        filename=path.name,
        status="queued",
        storage_path=str(path),
        owner_id=uuid.UUID(me["id"]),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    response = client.post(
        f"{settings.API_V1_STR}/documents/{document.id}/reindex",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 409
    db.delete(document)
    db.commit()


def test_delete_document_cascades_existing_citations(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
    tmp_path: Path,
) -> None:
    me = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    ).json()
    owner_id = uuid.UUID(me["id"])
    path = tmp_path / "cited.txt"
    path.write_text("cited content", encoding="utf-8")

    document = Document(
        title="Cited",
        filename=path.name,
        status="indexed",
        storage_path=str(path),
        owner_id=owner_id,
    )
    chat_session = ChatSession(owner_id=owner_id)
    db.add(document)
    db.add(chat_session)
    db.flush()

    chunk = DocumentChunk(
        document_id=document.id,
        content="cited content",
        chunk_index=0,
    )
    message = ChatMessage(
        session_id=chat_session.id,
        role="assistant",
        content="answer",
    )
    db.add(chunk)
    db.add(message)
    db.flush()

    citation = AnswerCitation(message_id=message.id, chunk_id=chunk.id)
    db.add(citation)
    db.commit()
    citation_id = citation.id

    response = client.delete(
        f"{settings.API_V1_STR}/documents/{document.id}",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 200
    db.expire_all()
    assert db.get(AnswerCitation, citation_id) is None
    assert db.get(ChatMessage, message.id) is not None
    db.delete(chat_session)
    db.commit()
