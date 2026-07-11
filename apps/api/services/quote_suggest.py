"""Quote-nudge ranking (PR-5b).

Pure theme-resolution + ranking for GET /quotes/suggested. The DB query (active
quotes) is done in the router and passed in; this module performs no I/O, so it
stays unit-testable and the router stays thin.
"""
from __future__ import annotations

from models import Quote, UserPreference
from services.matching_service import PERSONA_AFFINITIES
from services.self_portrait_summary import themes_from_answers


def candidate_themes(prefs: UserPreference) -> list[str]:
    """Resolve the user's candidate themes for the nudge.

    Priority (PR-5b): the Self-Portrait questionnaire, then the onboarding themes
    as a fallback. (PR-5d will prepend a live chat-signal theme above these.)
    """
    answers = (prefs.profile or {}).get("answers") or {}
    cand = themes_from_answers(answers)
    if not cand:
        cand = list(prefs.themes or [])
    return cand


def rank_suggested_quotes(
    prefs: UserPreference,
    quotes: list[Quote],
    *,
    limit: int = 5,
) -> list[tuple[Quote, list[str]]]:
    """Rank active quotes against the user's candidate themes.

    Returns (quote, matched_themes)[] where matched_themes is the sorted overlap
    that drove the match. Fail-quiet: no candidate themes ⇒ []. Deterministic order.
    """
    cand = candidate_themes(prefs)
    if not cand:
        return []
    cand_set = set(cand)

    scored: list[tuple[int, int, str, Quote, list[str]]] = []
    for q in quotes:
        if not q.is_active:
            continue
        overlap = sorted(set(q.themes or []) & cand_set)
        if not overlap:
            continue
        affinity = PERSONA_AFFINITIES.get(q.persona_slug, {}).get("themes", {})
        aff_sum = sum(affinity.get(t, 0) for t in overlap)
        # Rank key: more overlap first, then higher persona affinity, then a stable
        # deterministic tiebreak on the immutable quote.id.
        scored.append((len(overlap), aff_sum, q.id, q, overlap))

    scored.sort(key=lambda s: (-s[0], -s[1], s[2]))
    return [(q, overlap) for _, _, _, q, overlap in scored[:limit]]
