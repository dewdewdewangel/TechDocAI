import logging
import uuid

from app.workers.document_tasks import process_document_task

logger = logging.getLogger(__name__)


class DocumentQueueError(RuntimeError):
    pass


def enqueue_document_processing(document_id: uuid.UUID) -> None:
    try:
        process_document_task.send(str(document_id))
    except Exception as exc:
        logger.exception("Failed to enqueue document %s", document_id)
        raise DocumentQueueError("Document queue is not available") from exc
