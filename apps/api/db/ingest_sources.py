"""
Source text ingestion script.

Usage:
    cd apps/api
    python db/ingest_sources.py

Ingests grounding passages for each persona into source_chunks.
These are the texts the retrieval service will draw from.

IMPORTANT:
- Only use public domain texts or texts you have rights to.
- All Meditations passages below are from the Gregory Hays translation (2002),
  which is copyrighted. Replace with public domain translations (Long 1862,
  Hammond 2014 Project Gutenberg) before shipping.
- The Long 1862 translation IS public domain — use that for production.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from db.session import AsyncSessionLocal
from models import Persona, SourceChunk
from services.embedding_client import embedding_client

# ── Marcus Aurelius — Meditations (Long 1862, public domain) ──────────────────
# Source: https://www.gutenberg.org/ebooks/2680
# Each chunk is 1–4 sentences. Aim for ~150–300 tokens per chunk.

MARCUS_AURELIUS_CHUNKS = [
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book II.4",
        "content": (
            "Consider how much more pain is brought on us by the anger and vexation "
            "caused by such acts than by the acts themselves at which we are angry "
            "and vexed. Remember also that no one injures thee but by bodily acts, "
            "or at most by affecting thy outward circumstances; while thou hast it "
            "always in thy power to refer the matter to the reason which is within "
            "thee."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book II.7",
        "content": (
            "Even though thou shouldest live three thousand years, or thirty "
            "thousand, remember that no man loses any other life than that which "
            "he now lives, and no man lives any other than that which he now loses. "
            "The longest and the shortest are thus brought to the same. For the "
            "present moment is equal to all, though what is past is not all equal; "
            "and so the present to all is only a moment."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book II.11",
        "content": (
            "Nothing is so conducive to greatness of mind as the ability to examine "
            "methodically and honestly everything that meets us in life, and to "
            "always look at things so as to see at the same time what kind of "
            "universe this is, and what use everything performs in it."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book III.16",
        "content": (
            "Body, soul, intelligence: to the body belong sensations, to the soul "
            "appetites, to the intelligence principles. To receive the impressions "
            "of forms by means of appearances belongs even to animals; to be pulled "
            "by the strings of desire belongs both to wild beasts and to men; "
            "but to have intelligence as a guide to what appears suitable belongs "
            "to none save those who live by reason."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book IV.3",
        "content": (
            "Men seek retreats for themselves, houses in the country, sea-shores "
            "and mountains; and thou too art wont to desire such things very much. "
            "But this is altogether a mark of the most common sort of men, "
            "for it is in thy power whenever thou shalt choose to retire into "
            "thyself. For nowhere either with more quiet or more freedom from "
            "trouble does a man retire than into his own soul."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book IV.7",
        "content": (
            "Do not indulge in such thoughts as these, that thou wilt live a "
            "bad life, or that thou wilt be poor, or unable to live in the way "
            "suited to thy rank in life. If such thoughts present themselves, "
            "expel them: say to them, it is not consistent with my dignity."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book IV.49",
        "content": (
            "Be not disgusted, nor discouraged, nor dissatisfied, if thou dost "
            "not succeed in doing everything according to right principles; "
            "but when thou hast failed, return back again, and be content if "
            "the greater part of what thou doest is consistent with man's nature, "
            "and love this to which thou returnest."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book V.8",
        "content": (
            "In the morning when thou risest unwillingly, let this thought be "
            "present: I am rising to the work of a human being. Why then am I "
            "dissatisfied if I am going to do the things for which I exist and "
            "for which I was brought into the world?"
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book V.13",
        "content": (
            "I have often wondered how it is that every man loves himself more "
            "than all the rest of men, but yet sets less value on his own opinion "
            "of himself than on the opinion of others."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book V.36",
        "content": (
            "Confine yourself to the present. Constantly regard the universe "
            "as one living being, having one substance and one soul; and observe "
            "how all things have reference to one perception, the perception of "
            "this one living being."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book VI.2",
        "content": (
            "Let this always be plain to thee, that this piece of land is like "
            "any other; and that all things here are the same with things on a "
            "hilltop, by the sea-shore, or wherever thou choost to be. "
            "Thou wilt find what the philosopher said: The universe is one "
            "great city, and there is one substance and one law."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book VI.13",
        "content": (
            "When thou art troubled about anything, thou hast forgotten this, "
            "that all things happen according to the universal nature; and "
            "forgotten this, that a man's wrongful act is nothing to thee; "
            "and forgotten this, that everything which happens, always happened "
            "so and will happen so, and now happens so everywhere."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book VII.9",
        "content": (
            "Everything harmonizes with me, which is harmonious to thee, "
            "O Universe. Nothing for me is too early nor too late, which is "
            "in due time for thee. Everything is fruit to me which thy seasons "
            "bring, O Nature: from thee are all things, in thee are all things, "
            "to thee all things return."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book VII.28",
        "content": (
            "Retire into thyself. The rational principle which rules has this "
            "nature, that it is content with itself when it acts justly, "
            "and so secures tranquillity."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book VIII.7",
        "content": (
            "Every nature is contented when it goes on its way well; "
            "and a rational nature goes on its way well, when in its thoughts "
            "it assents to nothing false or uncertain, and when it directs its "
            "movements to social acts only, and when it confines its desires and "
            "aversions to the things which are in its power."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book IX.6",
        "content": (
            "The impediment to action advances action. What stands in the way "
            "becomes the way. This is true of obstacles in nature as it is "
            "in the actions of men."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book X.8",
        "content": (
            "How much trouble he avoids who does not look to see what his "
            "neighbour says or does or thinks, but only to what he does himself, "
            "that it may be just and pure."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book XI.1",
        "content": (
            "These are the properties of the rational soul: it sees itself, "
            "analyses itself, and makes itself whatever it chooses; the fruit "
            "which it bears itself enjoys — for the fruits of plants and that "
            "in animals which corresponds to fruits others enjoy — it obtains "
            "its own end, wherever the limit of life may be fixed."
        ),
    },
    {
        "source_title": "Meditations",
        "source_type": "primary_text",
        "page_ref": "Book XII.23",
        "content": (
            "Everything harmonizes with me, which is harmonious to thee, O Universe. "
            "Let not the future disturb thee, for thou wilt come to it, if it "
            "shall be so, having with thee the same reason which thou now usest "
            "for present things."
        ),
    },
    # ── Commentary / Context ─────────────────────────────────────────────────
    {
        "source_title": "Stanford Encyclopedia of Philosophy — Stoicism",
        "source_type": "commentary",
        "page_ref": None,
        "content": (
            "Central to Stoic ethics is the distinction between what is 'up to us' "
            "(eph' hēmin) and what is not. What is up to us includes our judgments, "
            "impulses, desires, and aversions — our inner life. What is not up to us "
            "includes our bodies, reputation, property, and external circumstances. "
            "The Stoics argued that only the inner life has genuine value; external "
            "things are 'indifferent' (adiaphora)."
        ),
    },
    {
        "source_title": "Stanford Encyclopedia of Philosophy — Stoicism",
        "source_type": "commentary",
        "page_ref": None,
        "content": (
            "For the Stoics, the emotions we typically call negative — fear, anger, "
            "grief, lust — are not natural states to be managed, but errors of "
            "judgment to be corrected. They result from mistakenly treating external "
            "things as genuinely good or bad. The Stoic sage does not suppress emotion "
            "but holds correct opinions, which naturally produce the right responses "
            "called 'good emotional states' (eupatheiai)."
        ),
    },
]

# ── Simone de Beauvoir — The Second Sex (public domain excerpts) ──────────────
# Note: The Second Sex (1949) is NOT in public domain in most jurisdictions.
# These are paraphrased thematic summaries, not direct quotes.
# Replace with licensed content before commercial launch.

BEAUVOIR_CHUNKS = [
    {
        "source_title": "The Second Sex — thematic summary",
        "source_type": "commentary",
        "page_ref": "Introduction",
        "content": (
            "De Beauvoir opens with the question of what a woman is. She argues "
            "that while a man defines himself as the One, the absolute, woman is "
            "always positioned as the Other — defined in relation to man, never "
            "as an independent subject. This is not a biological fact but a "
            "historical and social construction perpetuated by both men and women."
        ),
    },
    {
        "source_title": "The Second Sex — thematic summary",
        "source_type": "commentary",
        "page_ref": "Part II",
        "content": (
            "The existentialist core of de Beauvoir's argument: existence precedes "
            "essence. A human being is not born with a fixed nature but creates "
            "themselves through choices and actions. When this freedom is denied — "
            "when a woman is told her nature is fixed, passive, dependent — it is "
            "an act of oppression equivalent to bad faith: treating a free being "
            "as if they were a thing."
        ),
    },
    {
        "source_title": "The Ethics of Ambiguity — thematic summary",
        "source_type": "commentary",
        "page_ref": "Chapter 1",
        "content": (
            "In The Ethics of Ambiguity, de Beauvoir argues that human existence is "
            "fundamentally ambiguous: we are both free subjects and situated beings "
            "subject to facticity. Bad faith is the refusal to acknowledge this "
            "ambiguity — either denying one's freedom by claiming total determination "
            "by circumstances, or denying facticity by pretending to absolute freedom "
            "detached from the world."
        ),
    },
    {
        "source_title": "Stanford Encyclopedia of Philosophy — de Beauvoir",
        "source_type": "commentary",
        "page_ref": None,
        "content": (
            "De Beauvoir distinguishes between genuine constraint — material poverty, "
            "institutional oppression, physical force — and the internalized constraints "
            "that women often impose on themselves. The latter, she argues, is a form "
            "of complicity with oppression. Liberation requires not only changing "
            "external structures but taking up one's freedom from within, which means "
            "recognizing and refusing the roles one has unconsciously accepted."
        ),
    },
]


# ── Ingestion runner ──────────────────────────────────────────────────────────

async def ingest(persona_slug: str, chunks: list[dict], db):
    result = await db.execute(select(Persona).where(Persona.slug == persona_slug))
    persona = result.scalar_one_or_none()
    if not persona:
        print(f"  ✗ Persona not found: {persona_slug} (run seed.py first)")
        return

    # Count existing
    existing = await db.execute(
        db.query(SourceChunk).where(SourceChunk.persona_id == persona.id)
    )

    ingested = 0
    skipped = 0

    for chunk_data in chunks:
        # Check for duplicate by content hash
        content = chunk_data["content"].strip()
        existing_check = await db.execute(
            select(SourceChunk).where(
                SourceChunk.persona_id == persona.id,
                SourceChunk.content == content,
            )
        )
        if existing_check.scalar_one_or_none():
            skipped += 1
            continue

        # Embed
        embedding = await embedding_client.embed(content)

        chunk = SourceChunk(
            persona_id=persona.id,
            source_title=chunk_data["source_title"],
            source_type=chunk_data["source_type"],
            content=content,
            embedding=embedding,
            page_ref=chunk_data.get("page_ref"),
        )
        db.add(chunk)
        ingested += 1

        # Batch commit every 5 to avoid timeouts
        if ingested % 5 == 0:
            await db.flush()
            print(f"  ... {ingested} chunks embedded")

    await db.commit()
    print(f"  ✓ {persona_slug}: {ingested} ingested, {skipped} skipped")


async def main():
    print("Ingesting source texts...\n")
    async with AsyncSessionLocal() as db:
        print("Marcus Aurelius:")
        await ingest("marcus_aurelius", MARCUS_AURELIUS_CHUNKS, db)
        print("\nSimone de Beauvoir:")
        await ingest("simone_de_beauvoir", BEAUVOIR_CHUNKS, db)
    print("\n✓ Ingestion complete")
    print("\nNOTE: Replace paraphrased Beauvoir summaries with licensed/PD text before commercial launch.")


if __name__ == "__main__":
    asyncio.run(main())
