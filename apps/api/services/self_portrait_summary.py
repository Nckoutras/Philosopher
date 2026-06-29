"""Self-Portrait "Your portrait" payoff: present-tense summary + persona best-fit.

The summary is a kind, plain mirror of HOW a user answers — generated once and
cached on user_preferences.portrait_cache (migration 039), regenerated only after
PORTRAIT_REGEN_DELTA new answers. Best-fit personas are chosen rule-based via
matching_service.compute_matches, fed by a frequency-ranked set of themes derived
from the user's answered questions through the approved bridge map below; the LLM
authors only the prose (summary + per-persona "why" lines), never the selection.

Best-effort throughout: any failure returns None so the endpoint falls back to the
forming preview and still returns 200. Never raises into the request path.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import MemoryEntry, Persona
from services.llm_client import llm_client
from services.matching_service import compute_matches
from services.self_portrait import answers_to_statements, get_question
from services.self_portrait_prompts import SELF_PORTRAIT_SUMMARY_PROMPT

logger = logging.getLogger(__name__)

# Same premium reflective tier the YvY/Council closings use — this is the payoff,
# so quality matters; it's cached + regenerated rarely, so cost stays small.
MODEL_PRO = "claude-sonnet-4-6"

# How many top themes feed compute_matches. 3 keeps the match driven by the user's
# dominant life-areas (mirroring onboarding's small theme set) and avoids feeding
# all 12 themes, which would wash out the personas' distinctions.
USER_THEMES_N = 3

SUMMARY_MAX_TOKENS = 400
BEST_FIT_PERSONAS = 2  # surface the top 1-2

# After a failed generation, don't re-attempt for this long — serve the forming
# preview (or a prior summary) meanwhile, so a ready user reopening the portrait
# during an LLM outage doesn't re-fire the ~2-4s call on every open. A genuine
# retry resumes once this elapses, so a transient outage self-heals.
GENERATION_RETRY_COOLDOWN_SECONDS = 600  # 10 minutes

# ── Bridge map: self-portrait theme_tags (20-word vocab) → matching themes ──────
#
# matching_service.compute_matches scores against a DIFFERENT 12-word vocabulary
# (acceptance, anxiety, controversy, dilemma, doubt, fear, freedom, grief, purpose,
# relationships, separation, work). Each self-portrait tag maps to one of those —
# `identity` to two. APPROVED MAP, locked; do not edit without sign-off. Values are
# tuples so the one-to-two case is uniform.
SELF_PORTRAIT_TAG_TO_THEME: dict[str, tuple[str, ...]] = {
    # Direct — same word in both vocabularies.
    "fear": ("fear",),
    "freedom": ("freedom",),
    "doubt": ("doubt",),
    "dilemma": ("dilemma",),
    "grief": ("grief",),
    # The ONLY one-to-two: who-am-I is both self-definition (purpose) and
    # self-questioning (doubt). The #1-frequency tag, genuinely two-sided.
    "identity": ("purpose", "doubt"),
    "desire": ("freedom",),       # wanting / appetite / what one chooses -> autonomy
    "control": ("anxiety",),      # locus-of-control, managing outcomes -> anxiety
    "meaning": ("purpose",),
    "loneliness": ("separation",),
    # resentment -> acceptance (NOT controversy): a held grievance is released by
    # reconciling, not by conflict-with-others; favours the Stoic/Taoist let-go minds.
    "resentment": ("acceptance",),
    "duty": ("work",),            # obligation / responsibility one owes
    "power": ("controversy",),    # the only source of controversy now (catch-all fixed)
    "death": ("grief",),
    # guilt -> grief (NOT doubt): guilt is "I did wrong" (a moral wound to process),
    # not "I don't know"; favours Freud + the Stoic-conscience minds.
    "guilt": ("grief",),
    "discipline": ("work",),
    "friendship": ("relationships",),
    "parents": ("relationships",),
    # envy -> freedom (NOT controversy): envy is enslavement to comparison / wanting
    # what isn't yours; Epictetus's freedom-from-desire is the on-the-nose match.
    "envy": ("freedom",),
    "aging": ("acceptance",),
}


def themes_from_answers(answers: dict, top_n: int = USER_THEMES_N) -> list[str]:
    """Aggregate the answered questions' INTERNAL theme_tags, map each through the
    bridge (identity yields two), frequency-rank, and return the top N matching
    themes. Deterministic: ties break alphabetically. Unknown ids / unmapped tags
    are skipped."""
    counts: Counter[str] = Counter()
    for qid in answers or {}:
        q = get_question(qid)
        if q is None:
            continue
        for tag in (q.get("theme_tags") or []):
            for theme in SELF_PORTRAIT_TAG_TO_THEME.get(tag, ()):
                counts[theme] += 1
    ranked = sorted(counts, key=lambda t: (-counts[t], t))
    return ranked[:top_n]


async def _recent_signals(db: AsyncSession, user_id: str, limit: int = 8) -> list[str]:
    """Recent conversation/insight/ritual memory signals — quiet context so the
    summary isn't answers-only. Excludes self_portrait* (that IS the answer set)
    and counterview beliefs, matching self_model_service's exclusions."""
    rows = (await db.execute(
        select(MemoryEntry.content)
        .where(
            MemoryEntry.user_id == user_id,
            MemoryEntry.is_active == True,  # noqa: E712
            MemoryEntry.entry_type.notin_(
                ("self_portrait", "self_portrait_shift", "counterview_belief")
            ),
        )
        .order_by(MemoryEntry.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return [c for c in rows if c and c.strip()]


def _build_user_block(
    statements: list[str], signals: list[str], candidates: list[tuple[str, str]]
) -> str:
    parts = [
        "Their self-portrait answer-statements (how they answered):\n"
        + "\n".join(f"- {s}" for s in statements)
    ]
    if signals:
        parts.append(
            "Recent quiet signals from their conversations / insights / rituals "
            "(context only, do not recite):\n" + "\n".join(f"- {s}" for s in signals)
        )
    parts.append(
        "Candidate personas they resemble, in order:\n"
        + "\n".join(f"- {name} (slug: {slug})" for slug, name in candidates)
    )
    return "\n\n".join(parts)


def _parse_json(raw: str) -> dict | None:
    """Strip an optional ```json fence and parse. Returns None on any failure."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    if text.endswith("```"):
        text = text[:-3].rstrip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def in_failure_cooldown(cache: dict | None) -> bool:
    """True if a recent generation failure is still within the retry cooldown, so
    the caller should NOT re-attempt (avoids hammering a down LLM on every open).
    A missing/unparseable marker reads as 'not in cooldown' — fail open to a retry."""
    if not isinstance(cache, dict):
        return False
    ts = cache.get("last_failed_at")
    if not isinstance(ts, str):
        return False
    try:
        failed = datetime.fromisoformat(ts)
    except Exception:
        return False
    if failed.tzinfo is None:
        failed = failed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - failed).total_seconds() < GENERATION_RETRY_COOLDOWN_SECONDS


def mark_failed(cache: dict | None) -> dict:
    """Record a generation failure as a `last_failed_at` marker, MERGED into the
    existing cache so a prior good summary (text/best_fit/watermark) is preserved.
    A later successful generate_portrait replaces the whole dict, dropping the
    marker — that is the self-heal."""
    merged = dict(cache) if isinstance(cache, dict) else {}
    merged["last_failed_at"] = datetime.now(timezone.utc).isoformat()
    return merged


async def generate_portrait(
    db: AsyncSession, user_id: str, answers: dict, need_most: str
) -> dict | None:
    """Generate the cached portrait payload, or None on any failure (caller falls
    back to the forming preview). Returns the exact cache shape:
    {text, best_fit, answer_count_watermark, generated_at}."""
    statements = answers_to_statements(answers, limit=12)
    if not statements:
        return None

    themes = themes_from_answers(answers, USER_THEMES_N)
    if not themes:
        return None

    matches = compute_matches(themes, need_most or "", top_n=BEST_FIT_PERSONAS)
    slugs = [m.slug for m in matches][:BEST_FIT_PERSONAS]
    if not slugs:
        return None

    rows = (await db.execute(
        select(Persona).where(Persona.slug.in_(slugs), Persona.is_active == True)  # noqa: E712
    )).scalars().all()
    by_slug = {p.slug: p for p in rows}
    # Preserve compute_matches order; drop any slug that doesn't resolve to an
    # active persona (defensive — keeps best_fit honest).
    candidates = [(s, by_slug[s].name) for s in slugs if s in by_slug]
    if not candidates:
        return None

    signals = await _recent_signals(db, user_id)
    user_block = _build_user_block(statements, signals, candidates)

    try:
        raw = await llm_client.complete(
            system=SELF_PORTRAIT_SUMMARY_PROMPT,
            user=user_block,
            model=MODEL_PRO,
            max_tokens=SUMMARY_MAX_TOKENS,
        )
    except Exception as exc:
        logger.warning(f"Self-portrait summary LLM failed for user={user_id}: {exc}")
        return None

    data = _parse_json(raw)
    summary = (data or {}).get("summary")
    if not data or not isinstance(summary, str) or not summary.strip():
        logger.warning(f"Self-portrait summary unparseable for user={user_id}")
        return None

    why_by_slug = {
        e.get("slug"): e.get("why")
        for e in (data.get("best_fit") or [])
        if isinstance(e, dict)
    }
    best_fit = [
        {
            "slug": slug,
            "name": name,
            "portrait_url": by_slug[slug].portrait_url or None,
            "bio": by_slug[slug].bio or None,
            "why": why_by_slug.get(slug),
        }
        for slug, name in candidates
    ]

    return {
        "text": summary.strip(),
        "best_fit": best_fit,
        "answer_count_watermark": len(answers),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
