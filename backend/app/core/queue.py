import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.core.config import settings

broker = RedisBroker(url=settings.REDIS_URL)  # type: ignore[no-untyped-call]


def configure_broker() -> RedisBroker:
    dramatiq.set_broker(broker)
    return broker


configure_broker()
