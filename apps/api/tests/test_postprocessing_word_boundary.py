"""Word-boundary matching and the curated lexicon (UAT2-001).

WHY THIS FILE EXISTS. The phrase check was `norm_phrase in norm_reply` — bare
substring containment over a case-folded reply. Two distinct failures came out
of that, and they need separate fixes, so they are pinned separately here.

  RULING B — containment reached INSIDE words. `ngl` matched "English", "angle"
  and "single"; `Uber` matched "Übermensch", and it did so only because
  normalize() folds the umlaut away first — correct for matching, lethal here.
  The fix is word-boundary matching, which closes the whole mid-word class.

  RULING C — containment was never the only problem. `Hinge` is a dating app AND
  an ordinary English noun; word boundaries do not help, because "the hinge of
  the argument" IS the bare word. Thirteen brand tokens and one slang token were
  ordinary English and are removed from the lexicon. A persona saying
  "Instagram" breaks character; a persona saying "the hinge" does not.

The production incident was both at once: "That's the hinge." tripped `Hinge`,
regenerated, said it again, and the deterministic strip deleted the word and
persisted "That's the ." while the reader had already been shown the correction.
Ruling D (persist what the user saw) is pinned in
test_correction_persists_verbatim.py — it is a different mechanism in a
different file and does not belong here.

THE STRUCTURAL GUARD AT THE BOTTOM IS NOT OPTIONAL. _load_universal_forbidden
degrades a malformed or missing JSON file to `{}` BY DESIGN, so postprocessing
becomes a silent no-op rather than taking the app down. That is the right
trade for a running service and it means a broken lexicon ships green: nothing
raises, nothing 500s, every reply simply stops being checked. Ruling C edits
that file by hand, including two trailing commas that a JSON parser rejects and
a human eye does not. These tests fail loudly if the file ever stops parsing.
"""
import json

import pytest

from services.postprocessing_service import (
    UNIVERSAL_FORBIDDEN_PATH,
    _UNIVERSAL_FORBIDDEN,
    _UNIVERSAL_PHRASES,
    CheckAction,
    check_universal_forbidden,
)


def _phrases() -> list[str]:
    """Every shipped universal phrase, as authored."""
    return [p for _cat, p, _norm, _reason, _pat in _UNIVERSAL_PHRASES]


# ── Ruling B — a kept token must not match inside a word ──────────────────────
#
# Every string below trips the check on the pre-UAT2-001 matcher. The token each
# one collides with is KEPT by Ruling C, so these cases prove the boundary fix
# and nothing else — a removal could not make them pass.

@pytest.mark.parametrize("reply,collides_with", [
    ("The English word for it.",          "ngl"),
    ("Look at it from another angle.",    "ngl"),
    ("A single thread holds it.",         "ngl"),
    ("He speaks of the Übermensch.",      "Uber"),
    ("He speaks of the Ubermensch.",      "Uber"),
])
def test_a_kept_token_no_longer_matches_inside_a_word(reply, collides_with):
    assert collides_with in _phrases(), (
        f"{collides_with!r} left the lexicon — this case now proves nothing. "
        "Move it to the Ruling C block or drop it."
    )
    r = check_universal_forbidden(reply)
    assert r.passed is True, (
        f"{reply!r} still trips on {collides_with!r}: "
        f"{[(h.category, h.matched_text) for h in r.hits]}"
    )


def test_the_umlaut_pair_is_kept_together():
    """Übermensch and Ubermensch must BOTH pass, and the pair is the point.

    The accented form collides only after normalize() strips the umlaut. Testing
    the bare form alone would still pass if someone removed the Greek/NFD fold,
    and the collision would be waiting for the first person to write Nietzsche
    properly. The two cases fail for different reasons and are both above.
    """
    assert check_universal_forbidden("He speaks of the Übermensch.").passed
    assert check_universal_forbidden("He speaks of the Ubermensch.").passed


# ── Ruling B — a kept token must still match as a standalone word ─────────────

@pytest.mark.parametrize("reply,expected", [
    ("She posts it all on Instagram, apparently.", "Instagram"),
    ("ngl, that is the whole of it.",              "ngl"),
    ("You are talking about boundaries again.",    "boundaries"),
    ("Σου στέλνω αγάπη.",                          "σου στέλνω αγάπη"),
])
def test_a_kept_token_still_matches_as_a_whole_word(reply, expected):
    r = check_universal_forbidden(reply)
    assert r.passed is False, f"{reply!r} stopped tripping on {expected!r}"
    assert r.action == CheckAction.REGENERATE


def test_a_phrase_at_the_end_of_the_string_still_matches():
    """(?!\\w) must be satisfied by the end of the string, not only by a space.

    This is the case `\\b` would also have handled and a naive `+ " "` would not.
    """
    r = check_universal_forbidden("There is no way around it, boundaries")
    assert r.passed is False


def test_a_phrase_ending_in_punctuation_still_compiles_and_matches():
    """`X (formerly Twitter)` ends in `)` — the reason for lookarounds over \\b.

    A trailing `\\b` after `)` demands a word character next, so the entry would
    match nothing at all and die silently. Ruling C removed the bare `Twitter`
    token; this compound one is KEPT, and it is the entry that proves the
    mechanism.
    """
    assert "X (formerly Twitter)" in _phrases()
    r = check_universal_forbidden("She still calls it X (formerly Twitter) out of habit.")
    assert r.passed is False
    assert any(h.matched_text == "X (formerly Twitter)" for h in r.hits)


# ── Ruling C — the 14 removed tokens are ordinary English ─────────────────────

REMOVED = [
    ("That is the hinge of the argument.",        "Hinge"),
    ("There was discord among them for years.",   "Discord"),
    ("He cut himself some slack, for once.",      "Slack"),
    ("Dry tinder catches before the log does.",   "Tinder"),
    ("The medium is not the message here.",       "Medium"),
    ("An apple, and the whole orchard behind it.", "Apple"),
    ("The teams he built outlasted him.",         "Teams"),
    ("Watch the lens zoom in on one detail.",     "Zoom"),
    ("A twitch at the corner of the mouth.",      "Twitch"),
    ("Do not bumble through the answer.",         "Bumble"),
    ("He sent a telegram, in 1913.",              "Telegram"),
    ("The twitter of birds at first light.",      "Twitter"),
    ("The Amazon is not a metaphor.",             "Amazon"),
    ("He spent his energy freely and early.",     "energy"),
]


@pytest.mark.parametrize("reply,was", REMOVED)
def test_a_removed_token_does_not_trigger_at_all(reply, was):
    r = check_universal_forbidden(reply)
    assert r.passed is True, (
        f"{reply!r} still trips: {[(h.category, h.matched_text) for h in r.hits]}"
    )


@pytest.mark.parametrize("_reply,removed", REMOVED)
def test_a_removed_token_is_gone_from_the_shipped_lexicon(_reply, removed):
    """Boundaries alone would not have saved these — the bare word IS the word."""
    assert removed not in _phrases()


# ── Ruling C — what must NOT have been removed ────────────────────────────────

KEPT_BRANDS = [
    "Instagram", "Facebook", "TikTok", "Snapchat", "Reddit", "WhatsApp",
    "iMessage", "OkCupid", "Match.com", "LinkedIn", "YouTube", "Netflix",
    "Spotify", "Google", "Microsoft", "Uber", "Lyft", "Airbnb", "OnlyFans",
    "Patreon", "Substack",
]


@pytest.mark.parametrize("brand", KEPT_BRANDS)
def test_a_brand_with_no_english_meaning_is_kept(brand):
    assert brand in _phrases()


@pytest.mark.parametrize("phrase", ["boundaries", "codependency", "gaslighting", "συνεξάρτηση"])
def test_the_therapy_jargon_set_is_untouched(phrase):
    """Section 5.7 element-6 choices, deliberate — not collateral of Ruling C."""
    assert phrase in _phrases()


@pytest.mark.parametrize("phrase", ["vibes", "vibing", "the vibes are off"])
def test_the_rest_of_the_slang_set_is_untouched(phrase):
    assert phrase in _phrases()


def test_exactly_the_fourteen_removals_and_no_others():
    """Category sizes, so an accidental deletion cannot hide behind a green run."""
    cats = _UNIVERSAL_FORBIDDEN["categories"]
    assert len(cats["modern_brands_and_platforms"]["phrases"]) == 22
    assert len(cats["modern_slang_and_internet_vernacular"]["phrases"]) == 18
    assert len(_UNIVERSAL_PHRASES) == 196


# ── The structural guard — a malformed lexicon must never ship green ──────────

def test_the_shipped_lexicon_file_is_valid_json():
    """Ruling C edited this file by hand, commas included. Parse it for real.

    Every other test in this file reads the ALREADY-PARSED module-level index,
    which a degraded load leaves merely empty. This one reads the bytes.
    """
    with open(UNIVERSAL_FORBIDDEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("categories"), "lexicon parsed but carries no categories"


def test_the_lexicon_actually_loaded_rather_than_degrading_to_empty():
    """The failure mode this whole file exists to make impossible.

    _load_universal_forbidden catches FileNotFoundError and JSONDecodeError and
    returns {} so the service degrades instead of dying. The cost is that a
    broken file is indistinguishable from a working one at runtime: no
    exception, no 500, just every reply going unchecked forever.
    """
    assert _UNIVERSAL_PHRASES, "universal lexicon degraded to empty — nothing is being checked"
    assert _UNIVERSAL_FORBIDDEN.get("categories"), "lexicon loaded no categories"


def test_every_shipped_phrase_compiles_to_a_usable_matcher():
    """Including the ones whose edges are punctuation, which \\b would have killed."""
    for _cat, phrase, norm, _reason, pattern in _UNIVERSAL_PHRASES:
        assert pattern is not None, f"{phrase!r} has no compiled matcher"
        assert pattern.search(norm), (
            f"{phrase!r} does not match its own normalised form {norm!r} — "
            "the boundary assertion is eating the entry"
        )
