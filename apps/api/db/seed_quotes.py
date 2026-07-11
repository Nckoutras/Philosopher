"""
Seed script for the quotes corpus — run once after migration 045.

Usage:
    cd apps/api
    python db/seed_quotes.py

Loads apps/api/data/quotes_seed.json VERBATIM (only .strip() on string values — no
other mutation), validates every persona_slug against PERSONA_REGISTRY (unknown slug
⇒ abort, insert nothing), then upserts idempotently by the natural key
(persona_slug, source_locator, text_en). On update it refreshes only context,
confidence, text_original, translation_note — it NEVER touches discuss_count or
story_count (engagement counters owned by later slices).
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from db.session import AsyncSessionLocal
from models import Quote
from personas import PERSONA_REGISTRY

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "quotes_seed.json",
)


def _clean(v):
    """VERBATIM: strip surrounding whitespace on strings; leave non-strings (None) as-is."""
    return v.strip() if isinstance(v, str) else v


async def seed_quotes():
    with open(DATA_PATH, encoding="utf-8") as f:
        rows = json.load(f)

    # Validate ALL slugs before inserting anything — unknown slug ⇒ abort, no writes.
    unknown = sorted({r["persona_slug"] for r in rows if r["persona_slug"] not in PERSONA_REGISTRY})
    if unknown:
        print(f"✗ Aborting — persona_slug(s) not in PERSONA_REGISTRY: {unknown}")
        print("  No rows inserted.")
        sys.exit(1)

    inserted = 0
    updated = 0
    async with AsyncSessionLocal() as db:
        for r in rows:
            persona_slug     = _clean(r["persona_slug"])
            text_en          = _clean(r["text_en"])
            source_locator   = _clean(r["source_locator"])
            text_original    = _clean(r.get("text_original"))
            translation_note = _clean(r.get("translation_note"))
            confidence       = _clean(r["confidence"])
            context          = _clean(r["context"])

            result = await db.execute(
                select(Quote).where(
                    Quote.persona_slug == persona_slug,
                    Quote.source_locator == source_locator,
                    Quote.text_en == text_en,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Refresh authored fields only — NEVER discuss_count / story_count.
                existing.context = context
                existing.confidence = confidence
                existing.text_original = text_original
                existing.translation_note = translation_note
                updated += 1
                print(f"  Updated: {persona_slug} — {source_locator}")
            else:
                db.add(Quote(
                    persona_slug=persona_slug,
                    text_en=text_en,
                    text_original=text_original,
                    source_locator=source_locator,
                    translation_note=translation_note,
                    confidence=confidence,
                    context=context,
                ))
                inserted += 1
                print(f"  Created: {persona_slug} — {source_locator}")

        await db.commit()

    print(f"✓ Quotes seed complete — {inserted} inserted, {updated} updated ({inserted + updated} total)")


if __name__ == "__main__":
    asyncio.run(seed_quotes())
