_FALLBACKS = {
    "llm_unavailable": "I'm having trouble responding. Please try again in a moment.",
    "persona_locked": "This philosopher requires a Pro subscription.",
    "rate_limited": (
        "You've reached your daily message limit with this philosopher. "
        "Try again tomorrow or upgrade to Pro for unlimited conversations."
    ),
}


def get_error_voice(persona, error_code: str) -> str:
    if persona is not None:
        cfg = getattr(persona, "config", None)
        if isinstance(cfg, dict):
            msg = cfg.get("error_messages", {}).get(error_code)
            if msg:
                return msg
    return _FALLBACKS.get(error_code, "An error occurred. Please try again.")
