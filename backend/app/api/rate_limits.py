import uuid
from collections.abc import Callable

from fastapi import HTTPException, status

from app.services.rate_limit import (
    RateLimitExceeded,
    RateLimitServiceError,
)


def enforce_limit(
    check: Callable[[uuid.UUID], None],
    user_id: uuid.UUID,
) -> None:
    try:
        check(user_id)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Request limit exceeded",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except RateLimitServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limit service is not available",
        ) from exc
