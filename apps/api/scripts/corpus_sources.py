"""
Allowlisted Project Gutenberg sources per philosopher persona.

All URLs point to plaintext (.txt) cache files. All translations listed are
pre-1928 and confirmed public domain in the US.

Every source carries BOTH a ``title`` and a ``gutenberg_title``:

    title            the label written to ``source_chunks.source_title`` and
                     rendered into the model's prompt ("In [source title]...").
                     Chosen to be readable when spoken aloud by a persona.
    gutenberg_title  the exact ``Title:`` header served by ``gutenberg_url``,
                     as fetched 2026-09-18. ``ingest_corpus`` REFUSES to ingest
                     a source whose fetched header does not equal this string.

The two differ wherever Gutenberg's own title is unusable as prompt copy — the
Tao Teh King, the full subtitle of Earnest, and the Epictetus selection. Keeping
them as separate fields is what lets the guard stay an EXACT match. A substring
or fuzzy comparison would have passed the very damage this file now documents:
"The Enchiridion" is a substring of "A Selection from the Discourses of
Epictetus with the Encheiridion", which is a different book.

WHY THIS FILE IS SHAPED THIS WAY — the 2026-09-18 P0 corpus re-ingest.
Four of these URLs pointed at entirely different books, from the original
ingest on 2026-05-17 until 2026-09-18: 902 chunks across socrates, epictetus
and sigmund_freud, live in production for four months.

    Crito (pg1700)                served Gaskell, *The Life of Charlotte
                                  Brontë, Vol. 2*                     247 rows
    The Enchiridion (pg45140)     served Barbour, *On Your Mark!*, a
                                  boys' sports novel                  178 rows
    Psychopathology... (pg18942)  served *Mémoires de Joseph Fouché*,
                                  in French                           318 rows
    Interpretation of Dreams
        (pg7040)                  served Lecomte, *Paula the
                                  Waldensian*                         159 rows

A fifth source was mislabelled rather than wrong: pg45109 is the Enchiridion
and was filed under "Discourses of Epictetus" (38 rows), so Epictetus had no
Discourses text at all. It is reassigned to its real title here.

Three of the four carried a "# VERIFY IN C3b: URL unconfirmed" comment that was
never discharged. The fourth, Crito, carried no warning — Jowett's Crito is
pg1657 and the config held pg1700, an unrelated number rather than a typo of
it. The ingest script validated only HTTP status, so a 200 response returning
the wrong book was indistinguishable from success. ``gutenberg_title`` plus the
header guard in ``ingest_corpus._assert_title_matches`` is the fix for that
class of failure, not just for these five rows.

Jung, Beauvoir and Orwell are excluded due to copyright (Decision #7 in the
C3a brief).
"""

from typing import TypedDict


class _CorpusSourceRequired(TypedDict):
    title: str
    gutenberg_title: str
    translator: str | None
    year: int
    gutenberg_url: str
    source_type: str
    license: str


class CorpusSource(_CorpusSourceRequired, total=False):
    # Former ``source_title`` values whose rows belong to THIS source but were
    # written under a different label. The ingest script deletes rows for these
    # titles alongside the source's own, so a retitle cannot strand orphans.
    # (``typing.NotRequired`` would be cleaner but lands in 3.11; local dev runs
    # 3.10 while CI runs 3.12, so this is the idiom that works on both.)
    supersedes: list[str]


CORPUS_SOURCES: dict[str, list[CorpusSource]] = {
    # ── Socrates (via Plato — Jowett 1871 translations, public domain) ─────────
    "socrates": [
        {
            "title": "Apology",
            "gutenberg_title": "Apology",
            "translator": "Jowett (1871)",
            "year": 1871,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/1656/pg1656.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            # pg1700 until 2026-09-18; that id is Gaskell's Life of Charlotte Brontë.
            "title": "Crito",
            "gutenberg_title": "Crito",
            "translator": "Jowett (1871)",
            "year": 1871,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/1657/pg1657.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            "title": "Phaedo",
            "gutenberg_title": "Phaedo",
            "translator": "Jowett (1871)",
            "year": 1871,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/1658/pg1658.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            "title": "The Republic",
            "gutenberg_title": "The Republic",
            "translator": "Jowett (1871)",
            "year": 1871,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/1497/pg1497.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
    ],

    # ── Marcus Aurelius ────────────────────────────────────────────────────────
    "marcus_aurelius": [
        {
            "title": "Meditations",
            "gutenberg_title": "Meditations",
            "translator": "Long (1862)",
            "year": 1862,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/2680/pg2680.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
    ],

    # ── Lao Tzu ───────────────────────────────────────────────────────────────
    "lao_tzu": [
        {
            # Gutenberg titles this by Legge's own rendering; the persona says
            # "Tao Te Ching" out loud, hence the two fields differing.
            "title": "Tao Te Ching",
            "gutenberg_title": "The Tao Teh King, or the Tao and its Characteristics",
            "translator": "Legge (1891)",
            "year": 1891,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/216/pg216.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
    ],

    # ── Niccolò Machiavelli ───────────────────────────────────────────────────
    "niccolo_machiavelli": [
        {
            "title": "The Prince",
            "gutenberg_title": "The Prince",
            "translator": "Marriott (1908)",
            "year": 1908,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/1232/pg1232.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
    ],

    # ── Oscar Wilde ────────────────────────────────────────────────────────────
    "oscar_wilde": [
        {
            "title": "The Picture of Dorian Gray",
            "gutenberg_title": "The Picture of Dorian Gray",
            "translator": None,
            "year": 1890,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/174/pg174.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            "title": "The Importance of Being Earnest",
            "gutenberg_title": "The Importance of Being Earnest: A Trivial Comedy for Serious People",
            "translator": None,
            "year": 1895,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/844/pg844.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            "title": "De Profundis",
            "gutenberg_title": "De Profundis",
            "translator": None,
            "year": 1905,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/921/pg921.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
    ],

    # ── Epictetus ─────────────────────────────────────────────────────────────
    # Gutenberg has no complete English Discourses. pg10661 is Long's selection,
    # which also carries the Encheiridion — so the Encheiridion is present twice
    # for this persona, in two translations (Long here, Higginson below). That
    # duplication is a known, bounded cost accepted on 2026-09-18: the fix is
    # dedup in retrieval, not a knowingly mislabelled corpus. Logged as TD-90.
    "epictetus": [
        {
            # pg45109 until 2026-09-18 — that id is the Enchiridion, not the
            # Discourses, so this persona had no Discourses text at all.
            "title": "Discourses of Epictetus (selections)",
            "gutenberg_title": "A Selection from the Discourses of Epictetus with the Encheiridion",
            "translator": "Long (1877)",
            "year": 1877,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/10661/pg10661.txt",
            "source_type": "primary_text",
            "license": "public_domain",
            "supersedes": ["Discourses of Epictetus"],
        },
        {
            # pg45140 until 2026-09-18; that id is Barbour's On Your Mark!.
            "title": "The Enchiridion",
            "gutenberg_title": "The Enchiridion",
            "translator": "Higginson (1890)",
            "year": 1890,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/45109/pg45109.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
    ],

    # ── Sigmund Freud ─────────────────────────────────────────────────────────
    # Only pre-1928 English translations qualify for US public domain. Brill's
    # (1913/1914) are the standard early PD English versions, and BOTH exist on
    # Gutenberg with an explicit `Original publication:` line naming Macmillan
    # and the year — so for these two the pre-1928 rule is verified from the
    # fetched header rather than inferred from the translator's dates. The
    # translator and year recorded here were correct before 2026-09-18; only the
    # URLs were wrong. Nothing about this pair was substituted.
    "sigmund_freud": [
        {
            # pg7040 until 2026-09-18; that id is Lecomte's Paula the Waldensian.
            "title": "The Interpretation of Dreams",
            "gutenberg_title": "The Interpretation of Dreams",
            "translator": "Brill (1913)",
            "year": 1913,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/66048/pg66048.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            # pg18942 until 2026-09-18; that id is the Mémoires de Joseph Fouché.
            "title": "Psychopathology of Everyday Life",
            "gutenberg_title": "Psychopathology of Everyday Life",
            "translator": "Brill (1914)",
            "year": 1914,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/67332/pg67332.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
    ],
}

# Copyright-blocked personas — never ingest these (Decision #7)
# george_orwell: major works + many essays remain under US copyright (publication-based,
# up to ~95 yrs); voice-engineered only, no source chunks. (miyamoto_musashi is NOT excluded —
# his originals are public domain; he is simply absent from CORPUS_SOURCES until a rights-clean
# English translation is sourced.)
EXCLUDED_PERSONAS: set[str] = {"carl_jung", "simone_de_beauvoir", "george_orwell"}

# Canonical set of slugs covered by this corpus config
KNOWN_CORPUS_SLUGS: set[str] = set(CORPUS_SOURCES.keys())
