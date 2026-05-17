"""Unit tests for scripts/corpus_sources.py.

No I/O, no network — these tests verify the static data structure only.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

from scripts.corpus_sources import CORPUS_SOURCES, EXCLUDED_PERSONAS, KNOWN_CORPUS_SLUGS


_REQUIRED_KEYS = {"title", "translator", "year", "gutenberg_url", "source_type", "license"}

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
