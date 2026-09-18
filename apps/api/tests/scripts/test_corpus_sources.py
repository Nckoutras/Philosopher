"""Unit tests for scripts/corpus_sources.py.

No I/O, no network — these tests verify the static data structure only.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from scripts.corpus_sources import CORPUS_SOURCES, EXCLUDED_PERSONAS, KNOWN_CORPUS_SLUGS


_REQUIRED_KEYS = {
    "title",
    "gutenberg_title",
    "translator",
    "year",
    "gutenberg_url",
    "source_type",
    "license",
}

# ── The frozen manifest (Step 6 of the 2026-09-18 P0 corpus re-ingest) ────────
#
# (persona, title) -> (Project Gutenberg id, the exact `Title:` header that id
# serves). Every pair was fetched from gutenberg.org on 2026-09-18 and pasted
# here verbatim.
#
# This is the test that would have caught the original damage, and it reaches
# the network never: CORPUS_SOURCES must agree with this table, so changing a
# URL without changing the manifest fails, and changing both is a two-line diff
# that puts the claim "pg1657 serves Crito" in front of a reviewer. The runtime
# guard in ingest_corpus checks the same claim against the live file; this pins
# it in CI, where fetching 14 books on every run would be slow and flaky.
#
# When a source legitimately changes, update this table in the same commit and
# say in the PR body where the new header was read from.
_EXPECTED_SOURCES: dict[tuple[str, str], tuple[str, str]] = {
    ("socrates", "Apology"): ("1656", "Apology"),
    ("socrates", "Crito"): ("1657", "Crito"),
    ("socrates", "Phaedo"): ("1658", "Phaedo"),
    ("socrates", "The Republic"): ("1497", "The Republic"),
    ("marcus_aurelius", "Meditations"): ("2680", "Meditations"),
    ("lao_tzu", "Tao Te Ching"): (
        "216",
        "The Tao Teh King, or the Tao and its Characteristics",
    ),
    ("niccolo_machiavelli", "The Prince"): ("1232", "The Prince"),
    ("oscar_wilde", "The Picture of Dorian Gray"): ("174", "The Picture of Dorian Gray"),
    ("oscar_wilde", "The Importance of Being Earnest"): (
        "844",
        "The Importance of Being Earnest: A Trivial Comedy for Serious People",
    ),
    ("oscar_wilde", "De Profundis"): ("921", "De Profundis"),
    ("epictetus", "Discourses of Epictetus (selections)"): (
        "10661",
        "A Selection from the Discourses of Epictetus with the Encheiridion",
    ),
    ("epictetus", "The Enchiridion"): ("45109", "The Enchiridion"),
    ("sigmund_freud", "The Interpretation of Dreams"): (
        "66048",
        "The Interpretation of Dreams",
    ),
    ("sigmund_freud", "Psychopathology of Everyday Life"): (
        "67332",
        "Psychopathology of Everyday Life",
    ),
}

# The five ids that served the wrong book (or the wrong work) from the original
# ingest on 2026-05-17 until 2026-09-18. Named so that reintroducing one fails
# with the reason rather than with a diff.
_KNOWN_BAD_IDS: dict[str, str] = {
    "1700": "Gaskell, The Life of Charlotte Bronte Vol. 2 — was configured as Crito",
    "45140": "Barbour, On Your Mark! — was configured as The Enchiridion",
    "18942": "Memoires de Joseph Fouche (French) — was configured as Psychopathology",
    "7040": "Lecomte, Paula the Waldensian — was configured as Interpretation of Dreams",
}

_ACTIVE_PERSONA_SLUGS = {
    "socrates",
    "marcus_aurelius",
    "lao_tzu",
    "niccolo_machiavelli",
    "oscar_wilde",
    "epictetus",
    "sigmund_freud",
}


# ── Exclusion list ─────────────────────────────────────────────────────────────

def test_excluded_personas_contains_jung():
    assert "carl_jung" in EXCLUDED_PERSONAS


def test_excluded_personas_contains_beauvoir():
    assert "simone_de_beauvoir" in EXCLUDED_PERSONAS


def test_excluded_personas_are_not_in_corpus_sources():
    overlap = EXCLUDED_PERSONAS & set(CORPUS_SOURCES)
    assert not overlap, f"Excluded personas appear in CORPUS_SOURCES: {overlap}"


# ── Corpus coverage ────────────────────────────────────────────────────────────

def test_corpus_sources_covers_all_expected_personas():
    missing = _ACTIVE_PERSONA_SLUGS - set(CORPUS_SOURCES)
    assert not missing, f"CORPUS_SOURCES is missing entries for: {missing}"


def test_known_corpus_slugs_matches_corpus_sources_keys():
    assert KNOWN_CORPUS_SLUGS == set(CORPUS_SOURCES.keys())


# ── Per-source data integrity ─────────────────────────────────────────────────

@pytest.mark.parametrize("slug", list(CORPUS_SOURCES.keys()))
def test_each_source_has_required_keys(slug):
    for source in CORPUS_SOURCES[slug]:
        missing = _REQUIRED_KEYS - set(source.keys())
        assert not missing, f"{slug!r} source {source.get('title')!r} missing keys: {missing}"


@pytest.mark.parametrize("slug", list(CORPUS_SOURCES.keys()))
def test_all_gutenberg_urls_are_https(slug):
    for source in CORPUS_SOURCES[slug]:
        url = source["gutenberg_url"]
        assert url.startswith("https://"), f"{slug!r}: URL not HTTPS: {url}"


@pytest.mark.parametrize("slug", list(CORPUS_SOURCES.keys()))
def test_all_gutenberg_urls_point_to_txt(slug):
    for source in CORPUS_SOURCES[slug]:
        url = source["gutenberg_url"]
        assert url.endswith(".txt"), f"{slug!r}: URL does not point to .txt: {url}"


@pytest.mark.parametrize("slug", list(CORPUS_SOURCES.keys()))
def test_all_licenses_are_public_domain(slug):
    for source in CORPUS_SOURCES[slug]:
        assert source["license"] == "public_domain", (
            f"{slug!r} source {source.get('title')!r} has non-PD license: {source['license']}"
        )


@pytest.mark.parametrize("slug", list(CORPUS_SOURCES.keys()))
def test_translation_years_are_pre_1928(slug):
    for source in CORPUS_SOURCES[slug]:
        year = source["year"]
        assert isinstance(year, int), f"{slug!r}: year is not int: {year!r}"
        assert year < 1928, (
            f"{slug!r} source {source.get('title')!r} year {year} >= 1928 "
            "(may not be US public domain)"
        )


# ── The frozen manifest ───────────────────────────────────────────────────────
#
# These are the tests that would have caught the 2026-05-17 damage. None of them
# touches the network: they check the CONFIG against a table of headers recorded
# by hand, so a wrong id fails in CI without a single HTTP request.

def _url_id(url: str) -> str:
    """Extract the Gutenberg ebook id from a cache URL."""
    return url.rstrip("/").split("/cache/epub/", 1)[1].split("/", 1)[0]


def test_manifest_covers_exactly_the_configured_sources():
    configured = {
        (slug, source["title"])
        for slug, sources in CORPUS_SOURCES.items()
        for source in sources
    }
    assert configured == set(_EXPECTED_SOURCES), (
        "CORPUS_SOURCES and the frozen manifest disagree about which sources "
        f"exist.\n  only in config:   {sorted(configured - set(_EXPECTED_SOURCES))}"
        f"\n  only in manifest: {sorted(set(_EXPECTED_SOURCES) - configured)}"
    )


@pytest.mark.parametrize("slug", list(CORPUS_SOURCES.keys()))
def test_each_source_matches_the_frozen_manifest(slug):
    for source in CORPUS_SOURCES[slug]:
        key = (slug, source["title"])
        assert key in _EXPECTED_SOURCES, f"unpinned source: {key}"
        expected_id, expected_header = _EXPECTED_SOURCES[key]

        assert _url_id(source["gutenberg_url"]) == expected_id, (
            f"{key} points at pg{_url_id(source['gutenberg_url'])} but the manifest "
            f"pins pg{expected_id}. If the id is genuinely changing, update the "
            "manifest in the same commit and say where the new header was read."
        )
        assert source["gutenberg_title"] == expected_header, (
            f"{key} declares gutenberg_title {source['gutenberg_title']!r} but the "
            f"manifest records {expected_header!r}."
        )


@pytest.mark.parametrize("slug", list(CORPUS_SOURCES.keys()))
def test_gutenberg_url_id_is_consistent_with_its_filename(slug):
    """.../cache/epub/<id>/pg<id>.txt — the id appears twice and must agree.

    A mismatch fetches one book under another's id, which is exactly the class of
    error this whole file exists to prevent.
    """
    for source in CORPUS_SOURCES[slug]:
        url = source["gutenberg_url"]
        assert url.endswith(f"/pg{_url_id(url)}.txt"), (
            f"{slug!r} source {source['title']!r}: id in path does not match "
            f"filename: {url}"
        )


@pytest.mark.parametrize("slug", list(CORPUS_SOURCES.keys()))
def test_no_known_bad_id_is_reintroduced(slug):
    for source in CORPUS_SOURCES[slug]:
        found = _url_id(source["gutenberg_url"])
        assert found not in _KNOWN_BAD_IDS, (
            f"{slug!r} source {source['title']!r} points at pg{found}, which is a "
            f"known-wrong id: {_KNOWN_BAD_IDS[found]}"
        )


@pytest.mark.parametrize("slug", list(CORPUS_SOURCES.keys()))
def test_gutenberg_title_is_a_non_empty_string(slug):
    for source in CORPUS_SOURCES[slug]:
        value = source["gutenberg_title"]
        assert isinstance(value, str) and value.strip(), (
            f"{slug!r} source {source['title']!r} has an empty gutenberg_title; the "
            "runtime guard would have nothing to compare against."
        )


def test_supersedes_never_names_a_live_title():
    """A supersedes entry must not be a title some source currently writes.

    The ingest clears every superseded title before inserting. If one named a live
    source, ingest order would decide whether that source's rows survived — which
    is a silent, order-dependent data loss rather than a visible failure.
    """
    live_titles = {
        (slug, source["title"])
        for slug, sources in CORPUS_SOURCES.items()
        for source in sources
    }
    for slug, sources in CORPUS_SOURCES.items():
        for source in sources:
            for stale in source.get("supersedes", []):
                assert (slug, stale) not in live_titles, (
                    f"{slug!r} source {source['title']!r} supersedes {stale!r}, but "
                    "that is a live source title for the same persona."
                )
