import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import User


def test_private_route_is_disabled_outside_local(client: TestClient) -> None:
    if settings.ENVIRONMENT == 'local':
        return

    response = client.post(
        f'{settings.API_V1_STR}/private/users/',
        json={},
    )

    assert response.status_code == 404


@pytest.mark.skipif(
    settings.ENVIRONMENT != 'local',
    reason='Private test route is enabled only in the local environment',
)
def test_create_user(client: TestClient, db: Session) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/private/users/",
        json={
            "email": "pollo@listo.com",
            "password": "password123",
            "full_name": "Pollo Listo",
        },
    )

    assert r.status_code == 200

    data = r.json()

    user = db.exec(select(User).where(User.id == data["id"])).first()

    assert user
    assert user.email == "pollo@listo.com"
    assert user.full_name == "Pollo Listo"
