import logging
from config import config

logger = logging.getLogger(__name__)

try:
    from posthog import Posthog
    _ph = Posthog(project_api_key=config.POSTHOG_API_KEY, host="https://app.posthog.com") if config.POSTHOG_API_KEY else None
except ImportError:
    _ph = None


class AnalyticsService:

    def track(self, event: str, user_id: str | None, properties: dict = None):
        if not _ph or not user_id:
            logger.debug(f"[analytics] {event} user={user_id} props={properties}")
            return
        try:
            _ph.capture(distinct_id=user_id, event=event, properties=properties or {})
        except Exception as e:
            logger.warning(f"Analytics track failed: {e}")

    def identify(self, user_id: str, traits: dict):
        if not _ph:
            return
        try:
            _ph.identify(distinct_id=user_id, properties=traits)
        except Exception as e:
            logger.warning(f"Analytics identify failed: {e}")


analytics_service = AnalyticsService()
