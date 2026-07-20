from fastapi.testclient import TestClient

from app.core.config import settings


def test_dashboard_summary_requires_authentication(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/dashboard/summary")
    assert response.status_code == 401


def test_dashboard_summary_returns_aggregates(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/dashboard/summary",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "document_count",
        "indexed_document_count",
        "failed_document_count",
        "chat_session_count",
        "question_count",
    }
