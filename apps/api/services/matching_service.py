"""Matching service: rule-based weighted scoring to rank personas for a user.

Score formula:
    score = sum(persona.theme_weights[t] for t in user_themes)
          + 2 * persona.need_weights[user_need_most]

Returns the top 3 personas, excluding those without portraits (Jung).
Tie-break by slug alphabetical for deterministic ordering.
"""

from dataclasses import dataclass
from typing import Sequence

# Personas excluded from matching v1 (no portrait yet)
EXCLUDED_SLUGS: set[str] = set()

# Per-persona affinity weights (0-3 scale).
# Tune by editing this dict; no migration required.
PERSONA_AFFINITIES: dict[str, dict[str, dict[str, int]]] = {
    "marcus_aurelius": {
        "themes": {
            "separation": 1, "anxiety": 2, "fear": 2, "grief": 2,
            "acceptance": 3, "work": 3, "relationships": 1, "purpose": 3,
            "dilemma": 2, "controversy": 1, "doubt": 1, "freedom": 2,
        },
        "needs": {
            "comfort": 1, "challenge": 2, "interpretation": 1, "practical_steadiness": 3,
        },
    },
    "socrates": {
        "themes": {
            "separation": 1, "anxiety": 1, "fear": 2, "grief": 1,
            "acceptance": 3, "work": 2, "relationships": 2, "purpose": 3,
            "dilemma": 2, "controversy": 3, "doubt": 3, "freedom": 2,
        },
        "needs": {
            "comfort": 0, "challenge": 3, "interpretation": 2, "practical_steadiness": 1,
        },
    },
    "simone_de_beauvoir": {
        "themes": {
            "separation": 2, "anxiety": 2, "fear": 2, "grief": 2,
            "acceptance": 2, "work": 2, "relationships": 3, "purpose": 3,
            "dilemma": 3, "controversy": 3, "doubt": 2, "freedom": 3,
        },
        "needs": {
            "comfort": 2, "challenge": 2, "interpretation": 3, "practical_steadiness": 1,
        },
    },
    "epictetus": {
        "themes": {
            "separation": 2, "anxiety": 2, "fear": 3, "grief": 2,
            "acceptance": 3, "work": 2, "relationships": 1, "purpose": 2,
            "dilemma": 2, "controversy": 1, "doubt": 1, "freedom": 3,
        },
        "needs": {
            "comfort": 1, "challenge": 2, "interpretation": 1, "practical_steadiness": 3,
        },
    },
    "sigmund_freud": {
        "themes": {
            "separation": 2, "anxiety": 3, "fear": 3, "grief": 2,
            "acceptance": 1, "work": 1, "relationships": 3, "purpose": 1,
            "dilemma": 3, "controversy": 2, "doubt": 2, "freedom": 1,
        },
        "needs": {
            "comfort": 2, "challenge": 1, "interpretation": 3, "practical_steadiness": 1,
        },
    },
    "carl_jung": {
        "themes": {
            "separation": 2, "anxiety": 2, "fear": 2, "grief": 2,
            "acceptance": 2, "work": 2, "relationships": 3, "purpose": 3,
            "dilemma": 2, "controversy": 2, "doubt": 2, "freedom": 2,
        },
        "needs": {
            "comfort": 1, "challenge": 2, "interpretation": 3, "practical_steadiness": 1,
        },
    },
    "lao_tzu": {
        "themes": {
            "separation": 1, "anxiety": 3, "fear": 2, "grief": 2,
            "acceptance": 3, "work": 2, "relationships": 2, "purpose": 2,
            "dilemma": 2, "controversy": 1, "doubt": 2, "freedom": 2,
        },
        "needs": {
            "comfort": 3, "challenge": 1, "interpretation": 2, "practical_steadiness": 2,
        },
    },
    "oscar_wilde": {
        "themes": {
            "separation": 2, "anxiety": 2, "fear": 2, "grief": 2,
            "acceptance": 2, "work": 1, "relationships": 3, "purpose": 2,
            "dilemma": 1, "controversy": 3, "doubt": 2, "freedom": 3,
        },
        "needs": {
            "comfort": 2, "challenge": 2, "interpretation": 2, "practical_steadiness": 1,
        },
    },
    "niccolo_machiavelli": {
        "themes": {
            "separation": 1, "anxiety": 2, "fear": 2, "grief": 1,
            "acceptance": 2, "work": 3, "relationships": 2, "purpose": 3,
            "dilemma": 3, "controversy": 3, "doubt": 1, "freedom": 1,
        },
        "needs": {
            "comfort": 0, "challenge": 3, "interpretation": 2, "practical_steadiness": 3,
        },
    },
    "george_orwell": {
        "themes": {
            "separation": 1, "anxiety": 1, "fear": 2, "grief": 1,
            "acceptance": 1, "work": 2, "relationships": 1, "purpose": 2,
            "dilemma": 2, "controversy": 3, "doubt": 2, "freedom": 2,
        },
        "needs": {
            "comfort": 0, "challenge": 3, "interpretation": 1, "practical_steadiness": 1,
        },
    },
    "miyamoto_musashi": {
        "themes": {
            "separation": 1, "anxiety": 2, "fear": 3, "grief": 1,
            "acceptance": 1, "work": 3, "relationships": 1, "purpose": 2,
            "dilemma": 2, "controversy": 1, "doubt": 2, "freedom": 1,
        },
        "needs": {
            "comfort": 0, "challenge": 3, "interpretation": 1, "practical_steadiness": 3,
        },
    },
}

# Display labels for reason generation
THEME_LABELS: dict[str, str] = {
    "separation": "separation",
    "anxiety": "anxiety",
    "fear": "fear",
    "grief": "grief",
    "acceptance": "acceptance",
    "work": "work",
    "relationships": "relationships",
    "purpose": "purpose",
    "dilemma": "dilemma",
    "controversy": "controversy",
    "doubt": "doubt",
    "freedom": "freedom",
}

NEED_LABELS: dict[str, str] = {
    "comfort": "comfort",
    "challenge": "a challenge",
    "interpretation": "interpretation",
    "practical_steadiness": "practical steadiness",
}


@dataclass
class PersonaMatch:
    slug: str
    score: int
    reason: str


def _generate_reason(
    slug: str,
    user_themes: Sequence[str],
    user_need: str,
) -> str:
    """Pick the strongest signal and turn it into a one-line reason."""
    affinities = PERSONA_AFFINITIES[slug]

    # Find user's theme with the highest weight on this persona
    strongest_theme: str | None = None
    strongest_theme_weight = 0
    for theme in user_themes:
        weight = affinities["themes"].get(theme, 0)
        if weight > strongest_theme_weight:
            strongest_theme = theme
            strongest_theme_weight = weight

    need_weight = affinities["needs"].get(user_need, 0)

    # Pick stronger signal: weighted by 2x for need_most (matches scoring)
    if strongest_theme and strongest_theme_weight >= need_weight:
        return f"Resonates with your {THEME_LABELS[strongest_theme]}."
    if need_weight > 0:
        return f"Aligned with your need for {NEED_LABELS[user_need]}."
    return "A thoughtful match based on what you shared."


def compute_matches(
    user_themes: Sequence[str],
    user_need_most: str,
    top_n: int = 3,
) -> list[PersonaMatch]:
    """Return top N personas ranked by affinity score.

    Excludes personas in EXCLUDED_SLUGS. Tie-breaks by slug alphabetical.
    """
    scored: list[PersonaMatch] = []

    for slug, affinities in PERSONA_AFFINITIES.items():
        if slug in EXCLUDED_SLUGS:
            continue

        theme_score = sum(affinities["themes"].get(t, 0) for t in user_themes)
        need_score = 2 * affinities["needs"].get(user_need_most, 0)
        total = theme_score + need_score

        reason = _generate_reason(slug, user_themes, user_need_most)
        scored.append(PersonaMatch(slug=slug, score=total, reason=reason))

    # Sort: highest score first, then slug alphabetical for stability
    scored.sort(key=lambda m: (-m.score, m.slug))

    return scored[:top_n]
