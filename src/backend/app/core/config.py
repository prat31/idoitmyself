from functools import lru_cache

from pydantic import SecretStr
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

    # Jev (TypeSafe System One model) via OpenRouter's Decisions API
    openrouter_api_key: SecretStr | None = None
    jev_model: str = "typesafe/jev-1.13"
    jev_decisions_url: str = "https://openrouter.ai/api/alpha/decisions"
    jev_body_max_chars: int = 8000

    # Run engine
    run_concurrency: int = 5  # emails in flight within one batch task (fetch + Jev + store)
    # Gmail API calls in flight per worker process. Gmail throttles per user, so the effective total is
    # this × the worker's process count (2 in docker-compose) — keep it small.
    gmail_max_in_flight: int = 2
    # Gmail's per-user quota (units/minute; 6,000 for projects created from May 2026 — see
    # developers.google.com/workspace/gmail/api/reference/quota). We budget a share of it per mailbox,
    # in short windows, and pace work instead of letting Gmail refuse it.
    gmail_quota_units_per_minute: int = 6000
    gmail_quota_utilisation: float = 0.9
    gmail_quota_window_seconds: int = 10
    run_batch_size: int = 10  # emails per batch task
    run_max_attempts: int = 12  # tries per email (and for listing) before giving up
    # Exponential back-off (with jitter) for work that hit a provider error. Keep every delay well under
    # RabbitMQ's consumer_timeout (30 min): delayed Celery messages are held unacked until due.
    run_retry_base_seconds: float = 2  # Google: start retries at least 1s after an error, then double
    run_retry_max_seconds: float = 60
    # Work paced by our own quota budget is re-queued for the next window plus a random spread, so
    # deferred batches don't all return at the same instant.
    run_pacing_spread_seconds: float = 30

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
