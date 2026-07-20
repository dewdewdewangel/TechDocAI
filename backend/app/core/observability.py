from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "techdoc_http_requests_total",
    "HTTP requests processed",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "techdoc_http_request_duration_seconds",
    "HTTP request duration",
    ("method", "route"),
)
LLM_REQUESTS = Counter(
    "techdoc_llm_requests_total",
    "LLM requests",
    ("result",),
)
LLM_DURATION = Histogram(
    "techdoc_llm_request_duration_seconds",
    "LLM request duration",
)
EMBEDDING_REQUESTS = Counter(
    "techdoc_embedding_requests_total",
    "Embedding batches",
    ("result",),
)
EMBEDDING_DURATION = Histogram(
    "techdoc_embedding_duration_seconds",
    "Embedding batch duration",
)
DOCUMENT_JOBS = Counter(
    "techdoc_document_jobs_total",
    "Document processing jobs",
    ("result",),
)
DOCUMENT_JOB_DURATION = Histogram(
    "techdoc_document_job_duration_seconds",
    "Document processing job duration",
)
