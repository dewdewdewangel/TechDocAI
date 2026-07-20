from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import Settings

BASE_SETTINGS: dict[str, Any] = {
    "ENVIRONMENT": "production",
    "SECRET_KEY": "s" * 32,
    "POSTGRES_SERVER": "localhost",
    "POSTGRES_PORT": 5432,
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "d" * 16,
    "POSTGRES_DB": "app",
    "FIRST_SUPERUSER": "admin@example.com",
    "FIRST_SUPERUSER_PASSWORD": "u" * 16,
}


def build_settings(**overrides: Any) -> Settings:
    values = BASE_SETTINGS | overrides
    return Settings(_env_file=None, **values)


def test_valid_production_settings_are_accepted() -> None:
    settings = build_settings()

    assert settings.ENVIRONMENT == "production"
    assert settings.SECRET_KEY == "s" * 32


@pytest.mark.parametrize("environment", ["staging", "production"])
@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("SECRET_KEY", ""),
        ("SECRET_KEY", "changethis"),
        ("SECRET_KEY", "replace-with-at-least-32-random-bytes"),
        ("SECRET_KEY", "short"),
        ("POSTGRES_PASSWORD", ""),
        ("POSTGRES_PASSWORD", "changethis"),
        ("POSTGRES_PASSWORD", "replace-with-a-strong-password"),
        ("POSTGRES_PASSWORD", "short"),
        ("FIRST_SUPERUSER_PASSWORD", ""),
        ("FIRST_SUPERUSER_PASSWORD", "changethis"),
        ("FIRST_SUPERUSER_PASSWORD", "replace-with-a-strong-password"),
        ("FIRST_SUPERUSER_PASSWORD", "short"),
    ],
)
def test_non_local_environment_rejects_insecure_secrets(
    environment: str,
    field_name: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError, match=field_name):
        build_settings(
            ENVIRONMENT=environment,
            **{field_name: value},
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("SECRET_KEY", "changethis"),
        ("POSTGRES_PASSWORD", "replace-with-a-strong-password"),
        ("FIRST_SUPERUSER_PASSWORD", "short"),
    ],
)
def test_local_environment_warns_about_insecure_secrets(
    field_name: str,
    value: str,
) -> None:
    with pytest.warns(UserWarning, match=field_name):
        settings = build_settings(
            ENVIRONMENT="local",
            **{field_name: value},
        )

    assert getattr(settings, field_name) == value


@pytest.mark.parametrize(
    "field_name",
    [
        "SECRET_KEY",
        "POSTGRES_PASSWORD",
    ],
)
def test_required_secrets_must_be_explicitly_configured(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
) -> None:
    monkeypatch.delenv(field_name, raising=False)

    values = BASE_SETTINGS.copy()
    del values[field_name]

    with pytest.raises(ValidationError, match=field_name):
        Settings(_env_file=None, **values)
