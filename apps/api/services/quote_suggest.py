"""Quote-nudge ranking (PR-5b).

Pure theme-resolution + ranking for GET /quotes/suggested. The DB query (active
quotes) is done in the router and passed in; this module performs no I/O, so it
stays unit-testable and the router stays thin.
"""
from __future__ import annotations

from models import Quote, UserPreference
from services.matching_service import PERSONA_AFFINITIES
from services.self_portrait_summary import themes_from_answers


def candidate_themes(prefs: UserPreference, signal_theme: str | None = None) -> list[str]:
    """Resolve the user's candidate themes for the nudge.

    Priority (PR-5b): the Self-Portrait questionnaire, then the onboarding themes
    as a fallback. PR-5d prepends a live chat-signal theme (3a) above these: it
    joins the candidate set at the front, deduped, and may be the ONLY candidate
    when the user has no questionnaire/onboarding themes — that is valid.
    """
    answers = (prefs.profile or {}).get("answers") or {}
    cand = themes_from_answers(answers)
    if not cand:
        cand = list(prefs.themes or [])
    if signal_theme:
        cand = [signal_theme] + [t for t in cand if t != signal_theme]
    return cand


def rank_suggested_quotes(
    prefs: UserPreference,
    quotes: list[Quote],
    *,
    signal_theme: str | None = None,
    limit: int = 5,
) -> list[tuple[Quote, list[str]]]:
    """Rank active quotes against the user's candidate themes.

    Returns (quote, matched_themes)[] where matched_themes is the sorted overlap
    that drove the match. Fail-quiet: no candidate themes ⇒ []. Deterministic order.

    PR-5d (3a): when a live `signal_theme` is present, a quote matching it surfaces
    FIRST — ahead of quotes with more questionnaire/onboarding overlap. With no
    signal theme (or none of the quotes match it), behaviour is identical to 5b.
    """
    cand = candidate_themes(prefs, signal_theme)
    if not cand:
        return []
    cand_set = set(cand)

    scored: list[tuple[int, int, int, str, Quote, list[str]]] = []
    for q in quotes:
        if not q.is_active:
            continue
        overlap = sorted(set(q.themes or []) & cand_set)
        if not overlap:
            continue
        matches_signal = 1 if (signal_theme and signal_theme in overlap) else 0
        affinity = PERSONA_AFFINITIES.get(q.persona_slug, {}).get("themes", {})
        aff_sum = sum(affinity.get(t, 0) for t in overlap)
        # Rank key: a live-signal match first (3a wins), then more overlap, then
        # higher persona affinity, then a stable tiebreak on the immutable quote.id.
        scored.append((matches_signal, len(overlap), aff_sum, q.id, q, overlap))

    scored.sort(key=lambda s: (-s[0], -s[1], -s[2], s[3]))
    return [(q, overlap) for _, _, _, _, q, overlap in scored[:limit]]
