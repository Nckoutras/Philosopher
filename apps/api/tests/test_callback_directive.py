"""MEM2-C-1: the callback directive is the APPROVED copy, and nothing ships it.

The copy was approved by the founder on 2026-10-05 (STEP 1, with three edits).
These tests make that approval mechanical rather than remembered: the literal
below is what was approved, and a reworded DIRECTIVE fails here instead of
quietly changing what the next run measured.

NO API CALLS.
"""
from pathlib import Path

import pytest

from evals import callback_directive as cd

APPROVED = (
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "ONE THING THEY SAID BEFORE\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "In an earlier conversation, {when}, this person wrote:\n"
    "\"{original}\"\n"
    "\n"
    "This is the one exception to the rule above. You may refer to it once in this "
    "reply, only if it sharpens what you are saying about what they brought today. If "
    "it does not clearly fit, leave it unused; not using it is always acceptable.\n"
    "\n"
    "If you use it:\n"
    "- One short clause, as something they said before: \"You said {when} that…\", "
    "\"{When} you wrote that…\". Never say where or to whom they said it, and never "
    "claim to remember more than these words.\n"
    "- Stay faithful to their words. Do not add to them, sharpen them, or make them "
    "more certain than they were. Never turn them into a pattern or a trait: no \"you "
    "always\", \"you never\", \"you tend to\", \"you are someone who\".\n"
    "- Treat it as what they said then, not as what is true of them now. They may see "
    "it differently today.\n"
    "- If they agree with it, that changes nothing: it is no more certain and no more "
    "general than it was.\n"
    "- Quote only words that appear above, exactly, in straight double quotation "
    "marks; otherwise paraphrase plainly. If their earlier words are in a different "
    "language from today's conversation, paraphrase in today's language instead of "
    "quoting.\n"
    "- Do not ask them to confirm it, and do not ask whether it is still true.\n"
    "- It counts toward your length. The reply stays within its usual length."
)


def test_directive_is_the_approved_copy():
    assert cd.DIRECTIVE == APPROVED


def test_the_three_approved_edits_are_present():
    # 1. examples use the given {when}
    assert '"You said {when} that…"' in cd.DIRECTIVE
    assert '"{When} you wrote that…"' in cd.DIRECTIVE
    # 2. no calendar-week wording anywhere
    assert "this week" not in cd.DIRECTIVE
    assert all("this week" not in text for _, text in cd.WHEN_BUCKETS)
    # 3. the anti-laundering line
    assert ("If they agree with it, that changes nothing: it is no more certain and "
            "no more general than it was.") in cd.DIRECTIVE


@pytest.mark.parametrize("days,expected", [
    (0, "a few days ago"), (6, "a few days ago"),
    (7, "last week"), (13, "last week"),
    (14, "a few weeks ago"), (55, "a few weeks ago"),
    (56, "a couple of months ago"), (120, "a couple of months ago"),
    (121, "some months ago"), (4000, "some months ago"),
])
def test_when_bucket_boundaries(days, expected):
    assert cd.when_bucket(days) == expected


def test_negative_age_is_refused():
    with pytest.raises(ValueError):
        cd.when_bucket(-1)


def test_render_fills_every_slot_and_capitalises_only_the_sentence_start():
    out = cd.render_block("I keep {braces} as typed.", 10)
    assert "{when}" not in out and "{When}" not in out and "{original}" not in out
    assert "In an earlier conversation, last week, this person wrote:" in out
    assert '"You said last week that…"' in out
    assert '"Last week you wrote that…"' in out
    # the person's words survive verbatim, braces included (no .format())
    assert '"I keep {braces} as typed."' in out


def test_hash_moves_with_the_copy(monkeypatch):
    before = cd.directive_hash()
    monkeypatch.setattr(cd, "DIRECTIVE", cd.DIRECTIVE + " ")
    assert cd.directive_hash() != before


def test_no_production_module_imports_the_draft_directive():
    """Production never IMPORTS the evals module. Since C-2 it carries its own copy
    (prompts/callback_directive*.txt, read by services/callback_service.py), pinned
    byte-for-byte against this one by tests/services/test_callback_service.py — so
    the guard is on the import, not on the word, which the production loader now
    names as a filename."""
    root = Path(__file__).resolve().parent.parent
    hits = []
    for sub in ("services", "workers", "routers", "prompts", "personas"):
        for p in (root / sub).rglob("*"):
            if p.suffix not in (".py", ".jinja2"):
                continue
            body = p.read_text(encoding="utf-8", errors="ignore")
            if "evals.callback_directive" in body or "from evals" in body:
                hits.append(str(p))
    assert hits == []


# ── the Greek variant (C1-d; approved 2026-10-05, C-2 STEP 0(b)) ─────────────

APPROVED_EL = APPROVED.replace(
    "\"You said {when} that…\", \"{When} you wrote that…\"",
    "\"Είπες {when} ότι…\", \"{When} έγραψες ότι…\"",
)


def test_greek_directive_is_the_approved_copy():
    assert APPROVED_EL != APPROVED, "the EN example clause was not found"
    assert cd.DIRECTIVE_EL == APPROVED_EL


def test_greek_variant_changes_only_the_example_phrasings():
    """Same prose as the measured EN copy: everything outside the example clause
    is identical, so an EL run measures the bucket + examples and nothing else."""
    head, tail = cd.DIRECTIVE.split("\"You said {when} that…\", \"{When} you wrote that…\"")
    assert cd.DIRECTIVE_EL.startswith(head) and cd.DIRECTIVE_EL.endswith(tail)


@pytest.mark.parametrize("days,expected", [
    (0, "πριν από λίγες μέρες"), (6, "πριν από λίγες μέρες"),
    (7, "την προηγούμενη εβδομάδα"), (13, "την προηγούμενη εβδομάδα"),
    (14, "πριν από μερικές εβδομάδες"), (55, "πριν από μερικές εβδομάδες"),
    # the founder's register edit: "ένα-δυο", not "κάνα δυο"
    (56, "πριν από ένα-δυο μήνες"), (120, "πριν από ένα-δυο μήνες"),
    (121, "πριν από αρκετούς μήνες"), (4000, "πριν από αρκετούς μήνες"),
])
def test_greek_when_bucket_boundaries(days, expected):
    assert cd.when_bucket(days, "el") == expected


def test_greek_and_english_buckets_share_cut_points():
    assert [u for u, _ in cd.WHEN_BUCKETS_EL] == [u for u, _ in cd.WHEN_BUCKETS]


def test_render_greek_fills_every_slot_and_capitalises_the_sentence_start():
    out = cd.render_block("Κάτι που είχα γράψει.", 10, "el")
    assert "{when}" not in out and "{When}" not in out and "{original}" not in out
    assert "In an earlier conversation, την προηγούμενη εβδομάδα, this person wrote:" in out
    assert '"Είπες την προηγούμενη εβδομάδα ότι…"' in out
    assert '"Την προηγούμενη εβδομάδα έγραψες ότι…"' in out
    assert "You said" not in out and "last week" not in out


def test_unknown_language_is_refused():
    with pytest.raises(ValueError):
        cd.render_block("x", 3, "fr")


def test_english_hash_is_unchanged_from_the_c1_run():
    """evals/results/2026-10-05_mem2c1/manifest.json recorded bc62f327423cf418.
    Adding the Greek variant must not move the EN hash: the C-1 numbers still
    describe the EN copy that ships."""
    assert cd.directive_hash() == "bc62f327423cf418"
    assert cd.directive_hash("el") != cd.directive_hash()
