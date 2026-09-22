"""The anti-flex term file, pinned by its own 90 hit / 90 miss fixtures.

WHY EVERY ENTRY CARRIES A HIT AND A MISS. A term list that fires on everything
passes any test shaped "does the matcher work". These 180 fixtures were the
founder's review instrument for 90 entries — one sentence that must trigger the
entry, one that must not — and they are kept as the test so that a later edit to
a term cannot silently break either side. The same discipline as
tests/test_persona_lexicon_wiring.py, which pins the shipped lexicon against
real Oregon replies.

THE MISS IS CHECKED AGAINST THE WHOLE PERSONA, NOT ITS OWN ENTRY. Collateral
fire from a neighbouring entry is just as wrong as a false positive on its own
terms, and it is the failure a per-entry test would miss.

NO API CALLS, NO DATABASE. This is data validation; it belongs in CI.

Run: cd apps/api && pytest tests/test_anti_flex_terms.py -v
"""
import pytest

from evals.anti_flex import check_anti_flex, coverage_summary, entry_hits, load_terms
from personas import PERSONA_REGISTRY

TERMS = load_terms()
ENTRIES = [
    (slug, entry)
    for slug, entries in TERMS["personas"].items()
    for entry in entries
]
IDS = [e["id"] for _, e in ENTRIES]


def test_every_persona_in_the_registry_has_entries():
    """The file must not drift behind the registry. A persona added without
    entries would score a silent clean sheet on every reply."""
    assert set(TERMS["personas"]) == set(PERSONA_REGISTRY), (
        "anti_flex_terms.json and PERSONA_REGISTRY disagree"
    )


def test_every_never_unprompted_topic_has_an_entry():
    """One entry per topic, per persona. A missing entry is an unscored topic."""
    for slug, persona in PERSONA_REGISTRY.items():
        declared = len(persona.anti_flexing.never_unprompted)
        present = len(TERMS["personas"][slug])
        assert present == declared, (
            f"{slug}: {declared} never_unprompted topics, {present} entries"
        )


@pytest.mark.parametrize("slug,entry", ENTRIES, ids=IDS)
def test_the_hit_fixture_triggers_its_own_entry(slug, entry):
    fired = entry_hits(entry, entry["hit"])
    assert fired, (
        f"{entry['id']}: its own hit fixture matched no term in it.\n"
        f"  hit:   {entry['hit']}\n"
        f"  terms: {entry.get('terms', [])}"
    )


@pytest.mark.parametrize("slug,entry", ENTRIES, ids=IDS)
def test_the_miss_fixture_triggers_nothing_in_the_persona(slug, entry):
    """Checked against the persona's WHOLE entry set, not just this entry."""
    user_text = entry.get("miss_user", "")
    result = check_anti_flex(entry["miss"], slug, user_text)
    assert result.passed, (
        f"{entry['id']}: its miss fixture fired.\n"
        f"  miss: {entry['miss']}\n"
        f"  fired: {[(h.entry_id, h.matched) for h in result.hits]}"
    )


# ── the three rules, pinned directly ─────────────────────────────────────────

@pytest.mark.parametrize("term,text,expected", [
    # Rule 1, the discriminator the capital buys
    ("the Senate", "You answer to a senate of your own making.", False),
    ("the Senate", "The Senate taught me patience I did not have.", True),
    ("Meditations", "Your meditations on this are circling.", False),
    ("the Shadow", "There is a shadow over everything you have said.", False),
    ("the Shadow", "That is the Shadow speaking, not you.", True),
    ("The Prince", "The prince you work for forgets quickly.", False),
    # Rule 1, the sentence-start case a per-TERM rule gets wrong
    ("my master", "My master broke my leg.", True),
    ("the Enchiridion", "The Enchiridion begins with this distinction.", True),
    ("the Chancery", "The Chancery taught me how to read a delay.", True),
    ("hard labour", "Hard labour taught me the difference.", True),
])
def test_case_rule_is_per_character(term, text, expected):
    entry = {"id": "t", "never_unprompted": "t", "coverage": "full", "terms": [term]}
    assert bool(entry_hits(entry, text)) is expected


def test_a_term_the_user_used_is_exempt():
    """The founder's case: Athens in the user's holiday is not a Socrates flex."""
    reply = "And what did Athens show you that here does not?"
    assert check_anti_flex(reply, "socrates").passed is False
    assert check_anti_flex(
        reply, "socrates", user_text="I just got back from Athens and felt nothing."
    ).passed is True


def test_coverage_is_declared_for_every_entry():
    """A run summary without the split invites reading a clean sheet as 'no
    flexing', which for a partial or framed entry it does not mean."""
    valid = set(TERMS["_meta"]["coverage_values"])
    for _, entry in ENTRIES:
        assert entry["coverage"] in valid, entry["id"]
    summary = coverage_summary()
    assert sum(summary.values()) == len(ENTRIES)


def test_no_term_list_is_empty():
    for _, entry in ENTRIES:
        assert entry.get("terms") or entry.get("regexes"), (
            f"{entry['id']} declares a topic and carries nothing to match it"
        )


def test_machiavelli_aphorisms_carries_no_feared_loved_variant():
    """Founder ruling 2026-09-22, and it must not be re-added.

    The PROMPT seeds the line as his register — sentence_structure reads
    "Occasional aphorism that lands flat — it is safer to be feared than loved",
    and system_fragment repeats it. Scoring it as a flex would measure the term
    list against the prompt rather than the persona against the user.
    """
    entry = next(
        e for e in TERMS["personas"]["niccolo_machiavelli"]
        if e["id"] == "machiavelli_09_aphorisms"
    )
    blob = " ".join(entry["terms"]).lower()
    assert "feared" not in blob and "loved" not in blob, (
        "feared/loved re-added to machiavelli_09; see the entry's note"
    )
    # and the persona file must agree — the two records drifting is the thing
    # the ruling closed.
    persona_topic = next(
        t for t in PERSONA_REGISTRY["niccolo_machiavelli"].anti_flexing.never_unprompted
        if "aphorisms" in t
    )
    assert "feared" not in persona_topic.lower()
