from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Philosopher"
    ENV: str = "development"
    DEBUG: bool = True
    API_SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://philosopher:philosopher@localhost:5432/philosopher"
    DATABASE_POOL_SIZE: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MEMORY_MODEL: str = "claude-haiku-4-5-20251001"

    # OpenAI (embeddings)
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_PRO_MONTHLY: str = ""
    STRIPE_PRICE_PRO_YEARLY: str = ""
    STRIPE_PRICE_PREMIUM_MONTHLY: str = ""

    # Email (Resend)
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@philosopher.app"
    PUBLIC_ASSET_BASE_URL: str = "https://thinkalike.netlify.app"

    # Error monitoring (Sentry). Empty = disabled, a clean no-op for local and
    # CI — same convention as POSTHOG_API_KEY above. Set on BOTH Render services
    # (api and worker); they are separate processes.
    SENTRY_DSN: str = ""

    # Analytics
    POSTHOG_API_KEY: str = ""
    # EU-hosted by default. The project is EU-hosted and the privacy policy
    # names PostHog as an EU processor; a US default would silently contradict
    # both if the Render env var were ever unset.
    POSTHOG_HOST: str = "https://eu.i.posthog.com"

    # Cold beta override: grants Pro tier to all users regardless of subscription
    BETA_GRANT_PRO_TO_ALL: bool = False

    # Frontend base URL — used for OAuth redirects, email links, Stripe return URLs
    FRONTEND_URL: str = "http://localhost:3000"

    # API (backend) base URL — used to build absolute links BACK to the API in
    # outbound email (e.g. the weekly-letter unsubscribe link). MUST be set on
    # Render to the public backend URL (e.g. https://philosopher-api-z9l9.onrender.com).
    # If left at localhost, the weekly-letter email is NOT sent (see arq_worker).
    API_BASE_URL: str = "http://localhost:8000"

    # Google OAuth (dormant until GOOGLE_OAUTH_ENABLED=true + credentials set on Render)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth/google/callback"
    GOOGLE_OAUTH_ENABLED: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


config = get_settings()
