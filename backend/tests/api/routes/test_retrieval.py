import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings


def test_retrieval_uses_current_user_scope(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    me = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    ).json()

    with patch(
        "app.api.routes.retrieval.search_chunks",
        return_value=[],
    ) as search:
        response = client.post(
            f"{settings.API_V1_STR}/retrieval/search",
            headers=normal_user_token_headers,
            json={"query": "How is deployment configured?", "top_k": 5},
        )

    assert response.status_code == 200
    assert response.json() == {"data": []}
    assert search.call_args.kwargs["owner_id"] == uuid.UUID(me["id"])
