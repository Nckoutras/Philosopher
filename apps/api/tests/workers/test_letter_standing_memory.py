"""The <what_you_know> standing-memory block in the weekly and monthly letters.

Memory-v2 Ruling #1(d), design §3/§3a — PR-3, the last of the §6 decomposition.

WHY THESE ARE SOURCE AND AST ASSERTIONS RATHER THAN A RENDERED LETTER. The block
is built inline inside generate_weekly_letter_task / generate_monthly_letter_task,
two ARQ tasks that each query User, Persona, Message, Conversation, Insight,
UserPreference and WeeklyLetter, call the LLM twice on the retry path, and commit.
Driving one end-to-end to read one block back would be a mock surface far larger
than the thing under test, and every future letter change would break it for
reasons unrelated to memory.

So each property is pinned where it actually lives:

  * PLACEMENT — the order of the interpolations in the user_msg f-string. A
    string index comparison is exact and cannot drift the way a rendered
    approximation would. (#578 in CLAUDE.md's failure log is the precedent: a
    render assertion that measured the runner was replaced by a source assertion
    that measured the decision.)
  * FAIL-OPEN — parsed with `ast`, not grepped: the call must sit inside a Try.
    A letter must never fail to send because a memory query did, and every other
    memory read in the product is best-effort for the same reason.
  * F-13, NO self_portrait ROW — the guarantee is that the builders call
    standing_memories (which filters to `stated`) and never recall (which is
    lane-aware and would bring self_portrait rows in Lane A). Both halves are
    asserted. The filter ITSELF is a WHERE clause, so it is proven in
    tests/db_live/test_memory_recall_and_cascades.py, where a mock cannot lie
    about what the query returned.
  * THE COPY — in tests/test_prompts.py, beside the other founder-approved
    prompt text.

Run: cd apps/api && pytest tests/workers/test_letter_standing_memory.py -v
"""
import ast
from pathlib import Path

import pytest

import workers.arq_worker as aw

SOURCE_PATH = Path(aw.__file__)
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)

WEEKLY_TASK = "generate_weekly_letter_task"
MONTHLY_TASK = "generate_monthly_letter_task"


def _task(name):
    for node in ast.walk(TREE):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {SOURCE_PATH.name}")


def _user_msg_line(period: str) -> str:
    """The single assembled-prompt line for one letter engine."""
    marker = f"{{rituals_block}}<{period}>"
    lines = [ln for ln in SOURCE.splitlines() if "user_msg = f" in ln and marker in ln]
    assert len(lines) == 1, lines
    return lines[0]


def _calls(node):
    """Every called name inside a subtree, whether the call is an attribute
    (`memory_service.standing_memories(...)`) or a bare name
    (`answers_to_statements(...)`). Collecting only one kind would make an
    assertion about the other silently vacuous."""
    names = []
    for n in ast.walk(node):
        if not isinstance(n, ast.Call):
            continue
        if isinstance(n.func, ast.Attribute):
            names.append(n.func.attr)
        elif isinstance(n.func, ast.Name):
            names.append(n.func.id)
    return names


# ── The cap ──────────────────────────────────────────────────────────────────

def test_the_block_is_capped_at_four_rows():
    """Small on purpose. The block is standing ground; the period's own messages
    have to stay dominant, which both prompts instruct in as many words."""
    assert aw.LETTER_STANDING_MAX == 4


def test_both_engines_use_the_same_cap():
    """A count of standing facts about a person, not a function of window length —
    so the monthly engine does NOT scale it the way it scales the rituals caps."""
    for name in (WEEKLY_TASK, MONTHLY_TASK):
        src = ast.get_source_segment(SOURCE, _task(name))
        assert "limit=LETTER_STANDING_MAX" in src, name


# ── Placement (design §3a) ───────────────────────────────────────────────────

@pytest.mark.parametrize("period", ["week", "month"])
def test_the_block_sits_between_the_portrait_and_the_rituals(period):
    """Standing material groups together, and the period's own words stay last.
    Both prompts' "let the week's/month's messages stay dominant" rests on that
    ordering, so it is pinned rather than left to a future edit's convenience."""
    line = _user_msg_line(period)

    portrait = line.index("{portrait_block}")
    standing = line.index("{standing_block}")
    rituals = line.index("{rituals_block}")
    period_block = line.index(f"<{period}>")

    assert portrait < standing < rituals < period_block


@pytest.mark.parametrize("period", ["week", "month"])
def test_the_room_noticings_still_lead_the_standing_material(period):
    """Unchanged by PR-3, and worth pinning while the order is being asserted:
    the insight spine precedes both standing blocks."""
    line = _user_msg_line(period)
    assert line.index("{room_block}") < line.index("{portrait_block}")


# ── Fail-open ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [WEEKLY_TASK, MONTHLY_TASK])
def test_the_standing_read_is_wrapped_in_a_try(name):
    """A letter must never fail to send because a memory query did. Parsed, not
    grepped: a `try:` on some other line in the same function would satisfy a
    text search while leaving this call unprotected."""
    task = _task(name)
    protected = any(
        "standing_memories" in _calls_in_body(try_node)
        for try_node in ast.walk(task)
        if isinstance(try_node, ast.Try)
    )
    assert protected, f"{name}: standing_memories is not inside a try block"


def _calls_in_body(try_node):
    names = []
    for stmt in try_node.body:
        names.extend(_calls(stmt))
    return names


# ── F-13: the block can never carry a self_portrait row ──────────────────────

@pytest.mark.parametrize("name", [WEEKLY_TASK, MONTHLY_TASK])
def test_the_letter_reads_standing_memories_not_recall(name):
    """THE F-13 GUARANTEE, at the call site. standing_memories filters to `stated`;
    recall is lane-aware and Lane A includes self_portrait, so recall here would
    render the person's quiz answers a SECOND time — the <self_portrait> block
    above already carries them, built from profile.answers.

    Asserting the absence matters as much as the presence: swapping one for the
    other later would look like a simplification and would silently double the
    quiz answers in the prompt."""
    calls = _calls(_task(name))
    assert "standing_memories" in calls, name
    assert "recall" not in calls, name


@pytest.mark.parametrize("name", [WEEKLY_TASK, MONTHLY_TASK])
def test_the_portrait_block_is_still_built_from_profile_answers(name):
    """The other half of the no-double-render argument: <self_portrait> keeps
    coming from answers_to_statements, NOT from memory rows. If that ever changed
    to a memory read, the exclusion reasoning above would need revisiting."""
    assert "answers_to_statements" in _calls(_task(name)), name
