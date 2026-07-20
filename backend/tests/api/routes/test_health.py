from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings


def test_liveness_does_not_require_dependencies(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/utils/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_checks_redis(client: TestClient) -> None:
    with patch("app.api.routes.utils.redis_is_ready", return_value=True):
        response = client.get(f"{settings.API_V1_STR}/utils/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
