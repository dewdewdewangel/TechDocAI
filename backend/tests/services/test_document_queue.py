import uuid
from unittest.mock import MagicMock

import pytest

from app.services import document_queue
from app.services.document_queue import DocumentQueueError


def test_enqueue_document_processing_sends_uuid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    send = MagicMock()
    monkeypatch.setattr(document_queue.process_document_task, "send", send)
    document_id = uuid.uuid4()

    document_queue.enqueue_document_processing(document_id)

    send.assert_called_once_with(str(document_id))


def test_enqueue_document_processing_wraps_broker_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    send = MagicMock(side_effect=ConnectionError("redis unavailable"))
    monkeypatch.setattr(document_queue.process_document_task, "send", send)

    with pytest.raises(DocumentQueueError, match="not available"):
        document_queue.enqueue_document_processing(uuid.uuid4())
