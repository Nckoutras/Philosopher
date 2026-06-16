"""
Allowlisted Project Gutenberg sources per philosopher persona.

All URLs point to plaintext (.txt) cache files. All translations listed are
pre-1928 and confirmed public domain in the US.

URLs marked "# VERIFY IN C3b" have not been fetched during development; C3b's
ingest run will surface any 404s via the error-per-source logging in ingest_corpus.py.
Jung and Beauvoir are excluded due to copyright (Decision #7 in the C3a brief).
"""

from typing import TypedDict


class CorpusSource(TypedDict):
    title: str
    translator: str | None
    year: int
    gutenberg_url: str
    source_type: str
    license: str


CORPUS_SOURCES: dict[str, list[CorpusSource]] = {
    # ── Socrates (via Plato — Jowett 1871 translations, public domain) ─────────
    "socrates": [
        {
            "title": "Apology",
            "translator": "Jowett (1871)",
            "year": 1871,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/1656/pg1656.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            "title": "Crito",
            "translator": "Jowett (1871)",
            "year": 1871,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/1700/pg1700.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            "title": "Phaedo",
            "translator": "Jowett (1871)",
            "year": 1871,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/1658/pg1658.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            "title": "The Republic",
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
            "title": "Tao Te Ching",
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
            "translator": None,
            "year": 1890,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/174/pg174.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            "title": "The Importance of Being Earnest",
            "translator": None,
            "year": 1895,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/844/pg844.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
        {
            "title": "De Profundis",
            "translator": None,
            "year": 1905,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/921/pg921.txt",
            "source_type": "primary_text",
            "license": "public_domain",
        },
    ],

    # ── Epictetus ─────────────────────────────────────────────────────────────
    "epictetus": [
        {
            "title": "Discourses of Epictetus",
            "translator": "Higginson (1890)",
            "year": 1890,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/45109/pg45109.txt",
            "source_type": "primary_text",
            "license": "public_domain",
            # VERIFY IN C3b: multiple Epictetus editions on Gutenberg; confirm this ID resolves
        },
        {
            "title": "The Enchiridion",
            "translator": "Higginson (1890)",
            "year": 1890,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/45140/pg45140.txt",
            "source_type": "primary_text",
            "license": "public_domain",
            # VERIFY IN C3b: URL unconfirmed
        },
    ],

    # ── Sigmund Freud ─────────────────────────────────────────────────────────
    # Only pre-1928 English translations qualify for US public domain.
    # Brill translations (1913-1914) are the standard early PD English versions.
    "sigmund_freud": [
        {
            "title": "The Interpretation of Dreams",
            "translator": "Brill (1913)",
            "year": 1913,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/7040/pg7040.txt",
            "source_type": "primary_text",
            "license": "public_domain",
            # VERIFY IN C3b: URL unconfirmed
        },
        {
            "title": "Psychopathology of Everyday Life",
            "translator": "Brill (1914)",
            "year": 1914,
            "gutenberg_url": "https://www.gutenberg.org/cache/epub/18942/pg18942.txt",
            "source_type": "primary_text",
            "license": "public_domain",
            # VERIFY IN C3b: URL unconfirmed
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
