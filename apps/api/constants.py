"""
Shared constants used across routers, services, and tests.
Keep this import-free from heavy dependencies so tests can import it standalone.
"""

# Plan tier hierarchy — higher = more access
TIER_ORDER: dict[str, int] = {
    "free":    0,
    "pro":     1,
    "premium": 2,
}

# Plan feature gates
PLAN_FEATURES: dict[str, dict] = {
    "free": {
        "personas": 2,
        "memory":   False,
        "rituals":  3,
        "insights": False,
    },
    "pro": {
        "personas": -1,   # unlimited
        "memory":   True,
        "rituals":  -1,
        "insights": True,
    },
    "premium": {
        "personas":      -1,
        "memory":        True,
        "rituals":       -1,
        "insights":      True,
        "premium_packs": True,
    },
}

# Analytics event names — single source of truth
ANALYTICS_EVENTS = {
    # Acquisition
    "user_registered":        ["source", "plan"],
    "onboarding_completed":   ["persona_slug", "time_to_complete_s"],
    # Engagement
    "persona_selected":       ["persona_slug", "tier", "source"],
    "conversation_started":   ["persona_slug", "ritual_id"],
    "message_sent":           ["persona_slug", "conversation_id", "safety_level",
                               "retrieval_hit", "memory_hit", "latency_ms"],
    "conversation_ended":     ["persona_slug", "turn_count", "duration_s"],
    "ritual_started":         ["ritual_slug", "persona_slug"],
    "ritual_completed":       ["ritual_slug", "persona_slug", "streak_count"],
    "insight_viewed":         ["insight_type", "persona_slug"],
    "insight_dismissed":      ["insight_type"],
    "memory_deleted":         [],
    # Monetisation
    "upgrade_banner_viewed":  ["source_page", "plan"],
    "upgrade_cta_clicked":    ["source_page", "plan"],
    "checkout_started":       ["plan", "interval"],
    "subscription_activated": ["plan", "trial"],
    "subscription_canceled":  ["plan", "reason"],
    "subscription_reactivated": ["plan"],
    # Safety (no PII)
    "safety_event_pre":       ["risk_level", "category"],
    "safety_event_post":      ["risk_level", "category"],
    # Retention
    "session_started":        ["day_of_week", "hour"],
    "streak_milestone":       ["days"],
}

# Safety risk levels in ascending severity
RISK_LEVELS = ["none", "low", "medium", "high", "critical"]


def is_plan_sufficient(user_plan: str, required_plan: str) -> bool:
    """Return True if user_plan meets or exceeds required_plan."""
    return TIER_ORDER.get(user_plan, 0) >= TIER_ORDER.get(required_plan, 99)
