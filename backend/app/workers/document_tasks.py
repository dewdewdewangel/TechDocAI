import time
import uuid

import dramatiq

from app.core.config import settings
from app.core.observability import DOCUMENT_JOB_DURATION
from app.core.queue import configure_broker
from app.services.document_processor import process_document

configure_broker()


@dramatiq.actor(
    queue_name="documents",
    max_retries=settings.DOCUMENT_QUEUE_MAX_RETRIES,
    min_backoff=5_000,
    max_backoff=60_000,
    time_limit=30 * 60 * 1_000,
)
def process_document_task(document_id: str) -> None:
    started = time.perf_counter()
    try:
        process_document(uuid.UUID(document_id))
    finally:
        DOCUMENT_JOB_DURATION.observe(time.perf_counter() - started)
