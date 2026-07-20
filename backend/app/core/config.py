import warnings
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    Field,
    HttpUrl,
    PostgresDsn,
    SecretStr,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MIN_SECRET_KEY_LENGTH = 32
MIN_PASSWORD_LENGTH = 12

INSECURE_SECRET_VALUES = frozenset(
    {
        "changethis",
    }
)

INSECURE_SECRET_PREFIXES = ("replace-with-",)


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local"),
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str = "TechDoc AI"
    UPLOAD_DIR: Path = Path("uploads")
    LLM_API_KEY: SecretStr = SecretStr("")
    LLM_BASE_URL: str | None = None
    LLM_HISTORY_MESSAGES: int = 10
    LLM_MAX_CONTEXT_CHARS: int = 12000
    LLM_MODEL: str = ""

    EMBEDDING_MODEL_PATH: Path = Path("models/bge-m3")
    EMBEDDING_DEVICE: Literal["cpu", "cuda"] = "cpu"
    EMBEDDING_USE_FP16: bool = False
    EMBEDDING_BATCH_SIZE: int = Field(default=4, ge=1)
    EMBEDDING_MAX_LENGTH: int = Field(default=8192, ge=1, le=8192)

    REDIS_URL: str = "redis://redis:6379/0"
    DOCUMENT_QUEUE_MAX_RETRIES: int = Field(default=3, ge=0, le=10)
    CHAT_REQUESTS_PER_MINUTE: int = Field(default=10, ge=1)
    CHAT_REQUESTS_PER_DAY: int = Field(default=200, ge=1)
    UPLOAD_REQUESTS_PER_MINUTE: int = Field(default=10, ge=1)
    METRICS_ENABLED: bool = True

    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_MIN_SCORE: float = Field(default=0.55, ge=0, le=1)
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    MAX_UPLOAD_SIZE_MB: int = 50
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_secret_strength(
        self,
        var_name: str,
        value: str,
        *,
        minimum_length: int,
    ) -> None:
        normalized = value.strip()
        lowered = normalized.casefold()

        if not normalized:
            problem = "must not be empty"
        elif lowered in INSECURE_SECRET_VALUES or lowered.startswith(
            INSECURE_SECRET_PREFIXES
        ):
            problem = "still contains a public placeholder"
        elif normalized != value:
            problem = "must not start or end with whitespace"
        elif len(normalized) < minimum_length:
            problem = f"must contain at least {minimum_length} characters"
        else:
            return

        message = f"{var_name} {problem}. Configure a unique secret before deployment."

        if self.ENVIRONMENT == "local":
            warnings.warn(message, UserWarning, stacklevel=2)
            return

        raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_secure_secrets(self) -> Self:
        self._check_secret_strength(
            "SECRET_KEY",
            self.SECRET_KEY,
            minimum_length=MIN_SECRET_KEY_LENGTH,
        )
        self._check_secret_strength(
            "POSTGRES_PASSWORD",
            self.POSTGRES_PASSWORD,
            minimum_length=MIN_PASSWORD_LENGTH,
        )
        self._check_secret_strength(
            "FIRST_SUPERUSER_PASSWORD",
            self.FIRST_SUPERUSER_PASSWORD,
            minimum_length=MIN_PASSWORD_LENGTH,
        )

        return self


settings = Settings()  # type: ignore
