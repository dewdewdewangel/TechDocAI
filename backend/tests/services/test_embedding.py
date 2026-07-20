from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from app.core.constants import EMBEDDING_DIMENSIONS
from app.services import embedding as embedding_service


def test_embed_texts_returns_empty_without_loading_model(
    monkeypatch: MonkeyPatch,
) -> None:
    def fail_if_loaded() -> None:
        raise AssertionError("Model should not be loaded")

    monkeypatch.setattr(embedding_service, "_get_model", fail_if_loaded)

    assert embedding_service.embed_texts([]) == []


def test_embed_texts_rejects_response_count_mismatch(
    monkeypatch: MonkeyPatch,
) -> None:
    model = MagicMock()
    model.encode.return_value = {"dense_vecs": [[1.0] * EMBEDDING_DIMENSIONS]}
    monkeypatch.setattr(embedding_service, "_get_model", lambda: model)

    with pytest.raises(RuntimeError, match="count mismatch"):
        embedding_service.embed_texts(["first", "second"])


def test_embed_texts_rejects_wrong_dimension(
    monkeypatch: MonkeyPatch,
) -> None:
    model = MagicMock()
    model.encode.return_value = {"dense_vecs": [[1.0] * (EMBEDDING_DIMENSIONS - 1)]}
    monkeypatch.setattr(embedding_service, "_get_model", lambda: model)

    with pytest.raises(RuntimeError, match="dimension mismatch"):
        embedding_service.embed_texts(["first"])


def test_embed_texts_uses_local_bge_m3(monkeypatch: MonkeyPatch) -> None:
    model = MagicMock()
    model.encode.return_value = {
        "dense_vecs": [
            [1.0] * EMBEDDING_DIMENSIONS,
            [2.0] * EMBEDDING_DIMENSIONS,
        ]
    }

    monkeypatch.setattr(embedding_service, "_get_model", lambda: model)

    vectors = embedding_service.embed_texts(["first", "second"])

    model.encode.assert_called_once_with(
        ["first", "second"],
        batch_size=embedding_service.settings.EMBEDDING_BATCH_SIZE,
        max_length=embedding_service.settings.EMBEDDING_MAX_LENGTH,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
