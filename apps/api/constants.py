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
    # THE BACKEND HALF OF THE TAXONOMY, AND ITS SOURCE OF TRUTH.
    #
    # This dict used to be inert: 21 names, 15 of which no code had ever fired,
    # one name that fired without being declared (user_signed_in), and nothing
    # anywhere that imported it. It documented an intention and drifted from the
    # code for months without anything noticing.
    #
    # It is now enforced, by tests rather than at runtime — see
    # tests/test_analytics_registry.py, which walks the AST of every module and
    # asserts BOTH directions: every analytics_service.track("...") literal
    # appears here, and every name here has at least one call site. A name with
    # no caller is deleted, not left as an aspiration.
    #
    # Enforcement is deliberately not a runtime check. An unknown event name
    # must never raise inside a request that was otherwise going to succeed;
    # analytics is an observer and may not change what the product does.
    #
    # The web half lives in apps/web/lib/analyticsEvents.ts under the same rule.
    # Names shared by both halves must carry the same property list.
    #
    # Property values are ids, enums, counts and buckets. Never conversation
    # text, memory text, letter text, an email, or the council `matter`.

    # ── Acquisition ──────────────────────────────────────────────────────────
    # Renamed from user_registered: one conversion, one name, matching the web
    # side's signup_started. No web twin — double-counting a signup is worse
    # than missing `source` on it.
    "signup_completed":       ["method", "plan"],
    "user_signed_in":         ["method"],

    # ── Engagement ───────────────────────────────────────────────────────────
    # Fired server-side at all THREE creation endpoints — /conversations,
    # /cross-persona and /reading-revisit — because an undercounted top of
    # funnel is the one number a funnel cannot afford to be wrong about. `via`
    # tells them apart without three event names. Server-side rather than at the
    # nine web createConversation call sites: one route cannot drift out of sync
    # with eight others. The cost is `source`, which is not knowable here.
    "conversation_started":   ["persona_slug", "ritual_id", "seeded_topic", "via"],
    # memory_count replaces the former memory_hit boolean. The Blueprint asked
    # for memory_reference_rendered; nothing renders a memory reference (the SSE
    # stream has no memory event and `brought in` is another persona), so the
    # count rides on the event that already knew the answer.
    "message_sent":           ["persona_slug", "conversation_id", "safety_level",
                               "retrieval_hit", "memory_count", "latency_ms"],
    # No `used_memory` on either: council_service passes memories=[]
    # unconditionally (council_service.py), so the property would be a hardcoded
    # False on every event. A constant is not a measurement — and a dashboard
    # reading "used_memory: false, 100%" invites the conclusion that memory does
    # not help the council, when the truth is the council never asks.
    "council_started":        ["source"],
    "council_completed":      ["member_count", "latency_bucket"],
    "council_saved":          [],
    "share_created":          ["artifact_type"],
    "letter_delivered":       ["week", "host", "reading_label"],

    # ── Monetisation ─────────────────────────────────────────────────────────
    # `source` is the paywall the checkout came from. It reaches the webhook
    # through Stripe metadata — session metadata for checkout.session.completed,
    # subscription_data.metadata for customer.subscription.*, because those two
    # webhook cases receive different objects and both fire
    # subscription_activated. None for a checkout that carried no source.
    "checkout_started":       ["plan", "interval", "source"],
    "subscription_activated": ["plan", "interval", "source"],
    # last_14d_features and reason are deferred to PR #5 (grace/dunning), which
    # touches the billing lifecycle anyway. When `reason` ships it is an enum,
    # never typed text.
    "subscription_canceled":  ["plan", "tenure_days"],

    # ── Safety (no PII) ──────────────────────────────────────────────────────
    "safety_event_pre":       ["risk_level", "category"],
}

# Safety risk levels in ascending severity
RISK_LEVELS = ["none", "low", "medium", "high", "critical"]


def is_plan_sufficient(user_plan: str, required_plan: str) -> bool:
    """Return True if user_plan meets or exceeds required_plan."""
    return TIER_ORDER.get(user_plan, 0) >= TIER_ORDER.get(required_plan, 99)
