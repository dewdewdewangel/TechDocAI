import uuid
from unittest.mock import MagicMock

import pytest

from app.services import rate_limit
from app.services.rate_limit import RateLimitExceeded


def test_consume_raises_after_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    pipeline = MagicMock()
    pipeline.__enter__.return_value = pipeline
    pipeline.execute.return_value = [3, True]
    redis = MagicMock()
    redis.pipeline.return_value = pipeline
    monkeypatch.setattr(rate_limit, "_redis", lambda: redis)

    with pytest.raises(RateLimitExceeded):
        rate_limit._consume(
            scope="test",
            subject=uuid.uuid4(),
            limit=2,
            window_seconds=60,
        )
