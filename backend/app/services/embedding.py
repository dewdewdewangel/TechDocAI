import logging
import time
from functools import lru_cache
from threading import Lock
from typing import Any

import sentry_sdk
from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-untyped]

from app.core.config import settings
from app.core.constants import EMBEDDING_DIMENSIONS
from app.core.observability import EMBEDDING_DURATION, EMBEDDING_REQUESTS

_encode_lock = Lock()

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model() -> BGEM3FlagModel:
    model_path = settings.EMBEDDING_MODEL_PATH.resolve()
    if not model_path.is_dir():
        raise RuntimeError(f"Embedding model not found: {model_path}")

    use_fp16 = settings.EMBEDDING_USE_FP16 and settings.EMBEDDING_DEVICE == "cuda"

    return BGEM3FlagModel(
        str(model_path),
        devices=settings.EMBEDDING_DEVICE,
        use_fp16=use_fp16,
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = _get_model()

    started = time.perf_counter()
    try:
        with _encode_lock:
            result: Any = model.encode(
                texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                max_length=settings.EMBEDDING_MAX_LENGTH,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
    except Exception as exc:
        EMBEDDING_REQUESTS.labels(result="error").inc()
        sentry_sdk.capture_exception(exc)
        raise RuntimeError("BGE-M3 embedding failed") from exc
    finally:
        EMBEDDING_DURATION.observe(time.perf_counter() - started)

    dense_vectors = result.get("dense_vecs")
    if dense_vectors is None:
        raise RuntimeError("BGE-M3 did not return dense vectors")

    if hasattr(dense_vectors, "tolist"):
        dense_vectors = dense_vectors.tolist()

    vectors = [[float(value) for value in vector] for vector in dense_vectors]

    if len(vectors) != len(texts):
        raise RuntimeError("Embedding response count mismatch")

    if any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
        raise RuntimeError("Embedding dimension mismatch")

    EMBEDDING_REQUESTS.labels(result="success").inc()
    return vectors
