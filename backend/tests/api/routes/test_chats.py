import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.rate_limit import RateLimitExceeded


def test_chat_question_is_saved_without_retrieval_results(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    created = client.post(
        f"{settings.API_V1_STR}/chat-sessions/",
        headers=normal_user_token_headers,
        json={"title": "New Chat"},
    )
    assert created.status_code == 200
    session_id = created.json()["id"]

    with (
        patch("app.api.routes.chats.enforce_chat_limits"),
        patch("app.api.routes.chats.search_chunks", return_value=[]),
    ):
        asked = client.post(
            f"{settings.API_V1_STR}/chat-sessions/{session_id}/ask",
            headers=normal_user_token_headers,
            json={"content": "What does the document say?"},
        )

    assert asked.status_code == 200
    assert asked.json()["assistant_message"]["citations"] == []

    messages = client.get(
        f"{settings.API_V1_STR}/chat-sessions/{session_id}/messages",
        headers=normal_user_token_headers,
    )
    assert messages.status_code == 200
    assert messages.json()["count"] == 2

    deleted = client.delete(
        f"{settings.API_V1_STR}/chat-sessions/{session_id}",
        headers=normal_user_token_headers,
    )
    assert deleted.status_code == 200


def test_superuser_uses_chat_owner_documents(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    owner = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    ).json()
    created = client.post(
        f"{settings.API_V1_STR}/chat-sessions/",
        headers=normal_user_token_headers,
        json={"title": "Owner session"},
    )
    session_id = created.json()["id"]

    with (
        patch("app.api.routes.chats.enforce_chat_limits"),
        patch(
            "app.api.routes.chats.search_chunks",
            return_value=[],
        ) as search,
    ):
        response = client.post(
            f"{settings.API_V1_STR}/chat-sessions/{session_id}/ask",
            headers=superuser_token_headers,
            json={"content": "Admin follow-up"},
        )

    assert response.status_code == 200
    assert search.call_args.kwargs["owner_id"] == uuid.UUID(owner["id"])

    client.delete(
        f"{settings.API_V1_STR}/chat-sessions/{session_id}",
        headers=superuser_token_headers,
    )


def test_chat_rate_limit_returns_retry_after(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    created = client.post(
        f"{settings.API_V1_STR}/chat-sessions/",
        headers=normal_user_token_headers,
        json={"title": "Rate limited"},
    )
    session_id = created.json()["id"]

    with patch(
        "app.api.routes.chats.enforce_chat_limits",
        side_effect=RateLimitExceeded(42),
    ):
        response = client.post(
            f"{settings.API_V1_STR}/chat-sessions/{session_id}/ask",
            headers=normal_user_token_headers,
            json={"content": "Too many requests"},
        )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"

    client.delete(
        f"{settings.API_V1_STR}/chat-sessions/{session_id}",
        headers=normal_user_token_headers,
    )
