"""
Seed script — run once after migrations.

Usage:
    cd apps/api
    python db/seed.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.session import AsyncSessionLocal, engine, Base
from models import Persona, Ritual
from personas import PERSONA_REGISTRY


RITUALS_SEED = [
    {
        "slug": "morning_reflection",
        "name": "Morning reflection",
        "description": "Begin the day by examining one assumption you are carrying.",
        "persona_slug": "marcus_aurelius",
        "tier": "free",
        "frequency": "daily",
        "prompt_template": (
            "Today is {{ current_date }}. "
            "Begin as you would begin: with one thing to examine. "
            "What assumption are you carrying into this day that you have not yet questioned?"
        ),
    },
    {
        "slug": "evening_review",
        "name": "Evening review",
        "description": "End the day by accounting for your choices.",
        "persona_slug": "marcus_aurelius",
        "tier": "free",
        "frequency": "daily",
        "prompt_template": (
            "The day is done. "
            "The Stoics called this the evening examination. "
            "Name one moment today when you acted from your best self — and one where you did not."
        ),
    },
    {
        "slug": "freedom_audit",
        "name": "Freedom audit",
        "description": "Examine which constraints in your life are chosen and which are real.",
        "persona_slug": "simone_de_beauvoir",
        "tier": "pro",
        "frequency": "weekly",
        "prompt_template": (
            "Let us audit your freedom. "
            "Name one thing in your life you describe as fixed — "
            "something you say you 'have no choice' about. "
            "We will look at it together."
        ),
    },
    {
        "slug": "what_matters",
        "name": "What matters to you",
        "description": "A weekly inventory of your values in practice.",
        "persona_slug": None,
        "tier": "pro",
        "frequency": "weekly",
        "prompt_template": (
            "Not what you believe matters — what you have actually acted as if matters, "
            "based on where your time and attention went this week. "
            "Let us compare the two."
        ),
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        print("Seeding personas...")

        # Build persona slug → db id map
        persona_map: dict[str, str] = {}

        for slug, config in PERSONA_REGISTRY.items():
            # Check if exists
            result = await db.execute(select(Persona).where(Persona.slug == slug))
            existing = result.scalar_one_or_none()

            if existing:
                # Update config in case it changed
                existing.config = config.to_dict()
                existing.name = config.name
                existing.era = config.era
                existing.tradition = config.tradition
                existing.tier = config.tier
                persona_map[slug] = existing.id
                print(f"  Updated: {slug}")
            else:
                persona = Persona(
                    slug=config.slug,
                    name=config.name,
                    era=config.era,
                    tradition=config.tradition,
                    tier=config.tier,
                    is_active=True,
                    config=config.to_dict(),
                )
                db.add(persona)
                await db.flush()
                persona_map[slug] = persona.id
                print(f"  Created: {slug}")

        print("Seeding rituals...")
        for r in RITUALS_SEED:
            result = await db.execute(select(Ritual).where(Ritual.slug == r["slug"]))
            existing = result.scalar_one_or_none()

            persona_id = persona_map.get(r.pop("persona_slug", None) or "", None)

            if existing:
                print(f"  Skipping (exists): {r['slug']}")
                r["persona_slug"] = None  # restore popped key for loop idempotency
                continue

            ritual = Ritual(
                slug=r["slug"],
                name=r["name"],
                description=r.get("description"),
                persona_id=persona_id,
                tier=r.get("tier", "free"),
                prompt_template=r["prompt_template"],
                frequency=r.get("frequency", "daily"),
                is_active=True,
            )
            db.add(ritual)
            print(f"  Created: {r['slug']}")

        await db.commit()
        print("✓ Seed complete")


if __name__ == "__main__":
    asyncio.run(seed())
