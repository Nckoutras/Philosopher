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
    #
    # BOTH DEFAULTS POINTED AT DEAD DOMAINS UNTIL 2026-09-11, and the second one
    # was the live defect. `philosopher.app` and `thinkalike.netlify.app` are
    # earlier names for this product.
    #
    # PUBLIC_ASSET_BASE_URL had never been set on Render, because it appeared in
    # no .env.example, no DEPLOY_NOTES row and no ops checklist — nothing had
    # ever told anyone it existed. So every OTP email loaded its logo from
    # thinkalike.netlify.app, and every future-self email printed that hostname
    # to the reader as visible link text (future_self_email.html renders this
    # value in the footer, not just as an <img src>).
    #
    # It failed the way that is hardest to notice: the old Netlify site still
    # answers 200, so nothing broke, no image 404'd and no log line fired. The
    # neighbouring URL defaults degrade LOUDLY by comparison — API_BASE_URL at
    # localhost suppresses the send and says so, FRONTEND_URL at localhost gives
    # obviously dead links. A default that quietly succeeds at the wrong thing is
    # worse than one that fails.
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "hello@thewiseroom.app"
    PUBLIC_ASSET_BASE_URL: str = "https://thewiseroom.app"

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

    # Stripe Tax on checkout (EU B2C digital services: VAT is due in the
    # customer's country). Off by default because automatic_tax ERRORS unless
    # Stripe Tax is also enabled in the Stripe dashboard for the same mode —
    # shipping the code must not break checkout before that is done. Set true
    # on the API service only after the live dashboard is configured. While
    # off, every checkout logs a warning (routers/billing.py).
    STRIPE_TAX_ENABLED: bool = False

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


# ── The outbound-link guard (TD-77) ──────────────────────────────────────────

def is_unset_public_url(url: str | None) -> bool:
    """True when a base URL is still the local placeholder, so no email may use it.

    ONE RULE, TWO CALL SITES, AND THEY GUARD DIFFERENT VARIABLES — which is why
    this takes a url rather than reading config itself. The weekly letter builds
    an UNSUBSCRIBE link and so guards API_BASE_URL; the future-self letter builds
    an ARRIVAL link and so guards FRONTEND_URL. Same rule, different variable, and
    a helper that chose the variable would be wrong for one of the two.

    WHAT THIS EXISTS TO STOP (TD-77). The weekly-letter path has guarded since it
    shipped: on a placeholder it suppresses, records the reason on the row, and
    logs at ERROR. The future-self path had no guard at all — it built the arrival
    link from FRONTEND_URL (default `http://localhost:3000`), SENT anyway, and
    marked the row 'sent'. Two email paths in one product, opposite behaviour on
    the same misconfiguration, and the silent one is the one that reaches a real
    reader with a dead link.

    EMPTY COUNTS AS UNSET, and it is not the same check as "localhost". A var set
    explicitly to "" yields links like "/app/scheduled-letters/<id>" — relative,
    dead in mail, and containing no localhost to match on. The original guard's
    bare substring test would have passed it straight through.
    """
    if not url or not url.strip():
        return True
    return "localhost" in url or "127.0.0.1" in url
