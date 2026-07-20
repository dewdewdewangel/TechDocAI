from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session]:
    with Session(engine) as session:
        existing_users = {
            user.id: user.model_dump() for user in session.exec(select(User)).all()
        }
        init_db(session)
        yield session

        for user_id, original_data in existing_users.items():
            existing_user = session.get(User, user_id)
            if existing_user is None:
                continue
            existing_user.sqlmodel_update(original_data)
            session.add(existing_user)

        statement = delete(User)
        if existing_users:
            statement = statement.where(col(User.id).not_in(existing_users))
        session.execute(statement)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
