from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables (and `.env` when present)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Google OAuth
    google_client_id: str
    google_client_secret: SecretStr
    google_redirect_uri: str

    # Fernet key used to encrypt OAuth tokens at rest
    token_encryption_key: SecretStr

    frontend_url: str = "http://localhost:5173"

    # RabbitMQ (Celery broker)
    rabbitmq_user: str = "idim"
    rabbitmq_password: SecretStr = SecretStr("idim")
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672

    # Jev (TypeSafe's System One model) via OpenRouter's Decisions API, for AI conditions in filters.
    # Without a key, AI conditions can't be saved.
    openrouter_api_key: SecretStr | None = None
    jev_model: str = "typesafe/jev-1.13"
    jev_decisions_url: str = "https://openrouter.ai/api/alpha/decisions"
    jev_body_max_chars: int = 8000  # plain-text body sent to Jev, truncated
    # An AI condition holds when Jev's P(yes) is at least this.
    jev_threshold: float = Field(default=0.5, gt=0, lt=1)

    # Scanning. How often scheduled scans run is stored in the database (scan_settings, set from the
    # Scans page). Their boundaries fall every interval from midnight in this timezone: with 3 hours,
    # 00:00, 03:00, 06:00, ... local time.
    scan_timezone: str = "Asia/Kolkata"
    # A queued/running scan with no progress for this long is marked failed, so the inbox isn't
    # blocked forever (e.g. a batch message was lost when the worker was killed).
    scan_stale_minutes: int = 30
    scan_concurrency: int = 5  # emails in flight within one batch task (fetch + filter + store)
    # Gmail API calls in flight per worker process. Gmail throttles per user, so the effective total is
    # this × the worker's process count (2 in docker-compose) — keep it small.
    gmail_max_in_flight: int = 2
    # Gmail's per-user quota (units/minute; 6,000 for projects created from May 2026 — see
    # developers.google.com/workspace/gmail/api/reference/quota). We budget a share of it per mailbox,
    # in short windows, and pace work instead of letting Gmail refuse it.
    gmail_quota_units_per_minute: int = 6000
    gmail_quota_utilisation: float = 0.9
    gmail_quota_window_seconds: int = 10
    scan_batch_size: int = 10  # emails per batch task
    scan_max_attempts: int = 12  # tries per email (and for listing) before giving up
    # Exponential back-off (with jitter) for work that hit a provider error. Keep every delay well under
    # RabbitMQ's consumer_timeout (30 min): delayed Celery messages are held unacked until due.
    scan_retry_base_seconds: float = 2  # Google: start retries at least 1s after an error, then double
    scan_retry_max_seconds: float = 60
    # Work paced by our own quota budget is re-queued for the next window plus a random spread, so
    # deferred batches don't all return at the same instant.
    scan_pacing_spread_seconds: float = 30

    # Processors. Their runs retry and pace like scans (SCAN_MAX_ATTEMPTS and the back-off above). A run
    # queued or running with no progress for this long lost its message and is re-published.
    processor_stale_minutes: int = 10

    # Telegram: notifications are also sent to this chat when both are set (otherwise in-app only).
    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str | None = None
    telegram_api_url: str = "https://api.telegram.org"

    @field_validator("scan_timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"unknown timezone {value!r} (use an IANA name, e.g. Asia/Kolkata)") from None
        return value

    @property
    def celery_broker_url(self) -> str:
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password.get_secret_value()}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}//"
        )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
