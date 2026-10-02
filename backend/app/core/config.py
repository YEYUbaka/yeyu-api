import math
import warnings
from typing import Self

from pydantic import (
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    API_PUBLIC_URL: str = "http://localhost:8000"
    SECRET_KEY: str
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    FASTAPI_ENV: str | None = None

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    DATABASE_URL: PostgresDsn

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, value: str | PostgresDsn) -> str:
        database_url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if database_url.startswith(scheme):
                return database_url.replace(scheme, "postgresql+psycopg://", 1)
        return database_url

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
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 30

    # OAuth/Redis settings are optional for the local template baseline. The
    # OAuth routes fail closed until all GitHub values are provided at runtime.
    REDIS_URL: str = "redis://localhost:6379/0"
    # Must exceed the complete Redis request ambiguity window; the validator
    # below enforces a margin over the configured Redis socket timeout.
    REDIS_LEASE_CANCEL_TOMBSTONE_TTL_SECONDS: int = 900
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None
    GITHUB_OAUTH_CALLBACK_URL: str | None = None
    GITHUB_OAUTH_AUTHORIZE_URL: str = "https://github.com/login/oauth/authorize"
    GITHUB_OAUTH_TOKEN_URL: str = "https://github.com/login/oauth/access_token"
    GITHUB_API_BASE_URL: str = "https://api.github.com"
    GITHUB_OAUTH_TIMEOUT_SECONDS: float = 10.0
    AUTH_COOKIE_NAME: str = "yeyu_session"
    IDENTITY_RATE_LIMIT_PER_MINUTE: int = 5
    IDENTITY_OAUTH_RATE_LIMIT_PER_MINUTE: int = 10

    # API-key pepper is a persistent secret reference supplied by deployment.
    # The existing SECRET_KEY is a local fallback so older environments remain
    # bootable; production should set a separate API_KEY_PEPPER.
    API_KEY_PEPPER: str | None = None
    API_KEY_PEPPER_VERSION: int = 1
    API_KEY_PREVIOUS_PEPPER: str | None = None
    API_KEY_PREVIOUS_PEPPER_VERSION: int | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def github_oauth_enabled(self) -> bool:
        return bool(
            self.GITHUB_CLIENT_ID
            and self.GITHUB_CLIENT_SECRET
            and self.GITHUB_OAUTH_CALLBACK_URL
        )

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.FASTAPI_ENV == "development":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("API_KEY_PEPPER", self.API_KEY_PEPPER)
        for host in self.DATABASE_URL.hosts():
            self._check_default_secret("DATABASE_URL password", host["password"])
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self

    @model_validator(mode="after")
    def _validate_api_key_pepper_configuration(self) -> Self:
        if self.API_KEY_PEPPER_VERSION <= 0:
            raise ValueError("API_KEY_PEPPER_VERSION must be positive")

        has_previous_pepper = self.API_KEY_PREVIOUS_PEPPER is not None
        has_previous_version = self.API_KEY_PREVIOUS_PEPPER_VERSION is not None
        if has_previous_pepper != has_previous_version:
            raise ValueError(
                "API_KEY_PREVIOUS_PEPPER and "
                "API_KEY_PREVIOUS_PEPPER_VERSION must be configured together"
            )
        if has_previous_pepper:
            assert self.API_KEY_PREVIOUS_PEPPER_VERSION is not None
            if not self.API_KEY_PREVIOUS_PEPPER or not self.API_KEY_PREVIOUS_PEPPER.strip():
                raise ValueError("API_KEY_PREVIOUS_PEPPER must not be empty")
            if self.API_KEY_PREVIOUS_PEPPER_VERSION <= 0:
                raise ValueError("API_KEY_PREVIOUS_PEPPER_VERSION must be positive")
            if self.API_KEY_PREVIOUS_PEPPER_VERSION == self.API_KEY_PEPPER_VERSION:
                raise ValueError(
                    "API_KEY_PREVIOUS_PEPPER_VERSION must differ from current version"
                )

        if self.API_KEY_PEPPER is not None and not self.API_KEY_PEPPER.strip():
            raise ValueError("API_KEY_PEPPER must not be empty")
        if self.FASTAPI_ENV != "development":
            if not self.API_KEY_PEPPER:
                raise ValueError(
                    "API_KEY_PEPPER is required outside development"
                )
            if self.API_KEY_PEPPER == self.SECRET_KEY:
                raise ValueError(
                    "API_KEY_PEPPER must be independent from SECRET_KEY"
                )

        return self

    @model_validator(mode="after")
    def _validate_lease_cancel_window(self) -> Self:
        if self.GITHUB_OAUTH_TIMEOUT_SECONDS <= 0:
            raise ValueError("GITHUB_OAUTH_TIMEOUT_SECONDS must be positive")
        minimum_ttl = math.ceil(self.GITHUB_OAUTH_TIMEOUT_SECONDS * 2 + 5)
        if self.REDIS_LEASE_CANCEL_TOMBSTONE_TTL_SECONDS < minimum_ttl:
            raise ValueError(
                "REDIS_LEASE_CANCEL_TOMBSTONE_TTL_SECONDS must exceed the "
                "Redis timeout ambiguity window"
            )
        return self


settings = Settings()  # type: ignore # ty: ignore[unused-ignore-comment]
