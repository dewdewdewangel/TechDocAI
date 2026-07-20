from fastapi.testclient import TestClient

from app.core.config import settings


def test_normal_user_cannot_read_audit_logs(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/audit-logs/",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403


def test_superuser_can_read_audit_logs(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/audit-logs/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert "data" in response.json()
    assert "count" in response.json()
