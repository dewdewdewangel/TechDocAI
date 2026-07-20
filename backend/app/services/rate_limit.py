import time
import uuid
from functools import lru_cache

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


class RateLimitExceeded(RuntimeError):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after


class RateLimitServiceError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _consume(
    *,
    scope: str,
    subject: uuid.UUID,
    limit: int,
    window_seconds: int,
) -> None:
    bucket = int(time.time()) // window_seconds
    key = f"rate:{scope}:{subject}:{bucket}"
    try:
        with _redis().pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds + 5)
            count, _ = pipe.execute()
    except RedisError as exc:
        raise RateLimitServiceError("Rate limit service is not available") from exc

    if int(count) > limit:
        retry_after = window_seconds - (int(time.time()) % window_seconds)
        raise RateLimitExceeded(retry_after)


def enforce_chat_limits(user_id: uuid.UUID) -> None:
    _consume(
        scope="chat-minute",
        subject=user_id,
        limit=settings.CHAT_REQUESTS_PER_MINUTE,
        window_seconds=60,
    )
    _consume(
        scope="chat-day",
        subject=user_id,
        limit=settings.CHAT_REQUESTS_PER_DAY,
        window_seconds=86_400,
    )


def enforce_upload_limit(user_id: uuid.UUID) -> None:
    _consume(
        scope="upload-minute",
        subject=user_id,
        limit=settings.UPLOAD_REQUESTS_PER_MINUTE,
        window_seconds=60,
    )


def redis_is_ready() -> bool:
    try:
        return bool(_redis().ping())
    except RedisError as exc:
        raise RateLimitServiceError("Redis is not available") from exc
