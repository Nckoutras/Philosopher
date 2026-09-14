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


# ═════════════════════════════════════════════════════════════════════════════
# PR-D — <also_last_week>: the weekly letter reads the trajectory snapshot
# ═════════════════════════════════════════════════════════════════════════════
#
# Same split as the standing lane above, and for the same reason: the read is
# built inline inside generate_weekly_letter_task, so PLACEMENT, FAIL-OPEN, the
# LEGACY GUARD and the QUERY SHAPE are pinned at source/AST level, while the
# rendering itself goes through a pure builder and is tested as a function. The
# copy lives in tests/test_prompts.py beside the other founder-approved text.
#
# WHY THE LETTER NEEDS A SECOND RECURRENCE SOURCE AT ALL, since a reader will
# reasonably ask: the insight spine already carries what recurred THIS week —
# detect_recurrence writes those cards and <what_the_room_noticed> renders them.
# It has no memory of last week. `still_recurring` is the only field that closes
# that gap, and it is the only field this block renders.

SNAPSHOT_READ = "_build_also_last_week_block"


def _payload(still, questions, *, reason=None):
    """A trajectory_snapshots payload in its real shape (061 / PR-C)."""
    changes = None if reason else {
        "still_recurring": list(still),
        "new_since_prior": ["new-1"],
        "absent_since_prior": ["gone-1", "gone-2"],
        "counts": {"still_recurring": len(still), "new_since_prior": 1,
                   "absent_since_prior": 2},
    }
    return {
        "version": 1,
        "recurring_questions": questions,
        "changes_since_prior": changes,
        "changes_since_prior_reason": reason,
    }


def _question(top_score, anchor_ids, text="I keep circling the same decision"):
    return {
        "memory_entry_id": "entry-x", "text": text, "conversation_id": None,
        "match_count": len(anchor_ids), "top_score": top_score,
        "prior_matches": [
            {"memory_entry_id": a, "text": f"words for {a}",
             "conversation_id": None, "score": top_score}
            for a in anchor_ids
        ],
    }


# ── Placement ────────────────────────────────────────────────────────────────

def test_the_snapshot_block_sits_directly_after_the_room_noticings():
    """It DEEPENS the spine rather than competing with it, and the approved
    guardrail says so ("the same thread the Room has already named above"), so
    the two sit adjacent. Standing material still follows both."""
    line = _user_msg_line("week")

    room = line.index("{room_block}")
    also = line.index("{also_last_week_block}")
    portrait = line.index("{portrait_block}")

    assert room < also < portrait


def test_the_monthly_letter_does_not_carry_the_block():
    """D is the SUNDAY letter. There is no monthly snapshot — 061's kind is
    'weekly' and the only writer is the weekly cron — so a monthly block would
    be a tag that is always empty."""
    assert "{also_last_week_block}" not in _user_msg_line("month")


# ── Fail-open ────────────────────────────────────────────────────────────────

def test_the_snapshot_read_is_wrapped_in_a_try():
    """A letter must never fail to send because a snapshot read did — the same
    rule the standing lane follows. Parsed, not grepped: a `try:` elsewhere in
    this long function would satisfy a text search while leaving this call
    unprotected."""
    task = _task(WEEKLY_TASK)
    protected = any(
        SNAPSHOT_READ in _calls_in_body(try_node)
        for try_node in ast.walk(task)
        if isinstance(try_node, ast.Try)
    )
    assert protected, f"{WEEKLY_TASK}: {SNAPSHOT_READ} is not inside a try block"


def test_the_monthly_task_never_reads_the_snapshot():
    assert SNAPSHOT_READ not in _calls(_task(MONTHLY_TASK))
    assert "TrajectorySnapshot" not in ast.get_source_segment(SOURCE, _task(MONTHLY_TASK))


# ── The legacy-branch guard ──────────────────────────────────────────────────

def _aligned_flag_assignment(task):
    for node in ast.walk(task):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "period_is_aligned" for t in node.targets
        ):
            return node
    raise AssertionError("period_is_aligned is never assigned")


def test_the_alignment_flag_is_captured_before_period_start_is_rebound():
    """THE WHOLE REASON THE FLAG EXISTS. Both arms of the period if/else assign
    period_start, so afterwards the two paths are indistinguishable. The legacy
    arm floors to a SUNDAY and week_period floors to a MONDAY, so a legacy job's
    period_start can never equal a snapshot's. Capturing the flag after the
    rebinding would compile, read as correct, and be unprovable. Compared by
    line number, which is exact."""
    task = _task(WEEKLY_TASK)
    flag_line = _aligned_flag_assignment(task).lineno

    rebinds = [
        node.lineno
        for node in ast.walk(task)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "period_start" for t in node.targets)
    ]
    assert rebinds, "period_start is never assigned inside the task"
    assert flag_line < min(rebinds)


def test_the_snapshot_read_only_runs_on_the_aligned_path():
    """A query that cannot succeed should not be issued at all. Asserted
    structurally: the call must sit inside an `if period_is_aligned:`."""
    task = _task(WEEKLY_TASK)
    guarded = False
    for node in ast.walk(task):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Name) \
                and node.test.id == "period_is_aligned":
            body_calls = []
            for stmt in node.body:
                body_calls.extend(_calls(stmt))
            if SNAPSHOT_READ in body_calls:
                guarded = True
    assert guarded, "the snapshot read is not guarded by `if period_is_aligned`"


# ── The query shape ──────────────────────────────────────────────────────────

def test_the_read_is_scoped_to_this_week_this_user_and_a_generated_row():
    """A WHERE clause a fake cannot lie about, pinned where it is written. The
    live behaviour of the same clause is proven in
    tests/db_live/test_trajectory_snapshots.py."""
    src = ast.get_source_segment(SOURCE, _task(WEEKLY_TASK))
    for clause in (
        "TrajectorySnapshot.user_id == user_id",
        "TrajectorySnapshot.period_start == period_start",
        'TrajectorySnapshot.kind == "weekly"',
        'TrajectorySnapshot.status == "generated"',
    ):
        assert clause in src, clause


def test_the_letter_never_writes_the_snapshot():
    """READ ONLY, and this is the constraint the whole step rests on: the letter
    must not repair, regenerate or backfill a snapshot. If a row is missing, the
    letter behaves exactly as it did before PR-D."""
    src = ast.get_source_segment(SOURCE, _task(WEEKLY_TASK))
    assert "TrajectorySnapshot(" not in src
    assert "db.add(TrajectorySnapshot" not in src


# ── The builder ──────────────────────────────────────────────────────────────

def test_a_second_week_thread_is_rendered_as_one_line():
    block = aw._build_also_last_week_block(
        _payload(["a"], [_question(0.9, ["a"])])
    )
    assert block == "<also_last_week>\n- words for a\n</also_last_week>\n\n"


def test_the_block_is_capped_at_three_and_keeps_the_strongest():
    """Sized to its neighbours — <what_you_know> is 4, <rituals> is 12 — and NOT
    to 061's storage caps, which allow 40 questions x 5 matches. Rendering those
    would be roughly 9,000 tokens against a ~4,500-token prompt and would make
    this the largest single input in the letter."""
    block = aw._build_also_last_week_block(_payload(
        ["a", "b", "c", "d"],
        [_question(0.5, ["c"]), _question(0.95, ["a"]),
         _question(0.7, ["b"]), _question(0.6, ["d"])],
    ))
    assert aw.ALSO_LAST_WEEK_MAX == 3
    assert block.count("\n- ") == 3
    assert "words for a" in block and "words for b" in block and "words for d" in block
    assert "words for c" not in block


def test_the_order_is_the_parent_scores_descending():
    block = aw._build_also_last_week_block(_payload(
        ["a", "b"], [_question(0.6, ["b"]), _question(0.9, ["a"])],
    ))
    assert block.index("words for a") < block.index("words for b")


def test_an_anchor_reached_twice_takes_its_stronger_score():
    """Two of the week's entries can echo the same earlier line. It is one
    anchor, ranked by the better of the two, and rendered once."""
    block = aw._build_also_last_week_block(_payload(
        ["a", "b"], [_question(0.2, ["a"]), _question(0.99, ["a"]),
                     _question(0.5, ["b"])],
    ))
    assert block.count("words for a") == 1
    assert block.index("words for a") < block.index("words for b")


def test_the_first_run_renders_nothing_at_all():
    """THE HONESTY RULE. A first snapshot has no prior week, so
    changes_since_prior is None. The letter then says NOTHING about change — it
    does not say nothing changed, because there is no sentence to say it with.
    An absent block is indistinguishable from a week with no repeats, which is
    correct: in both cases there is no evidence of a second week."""
    block = aw._build_also_last_week_block(
        _payload([], [_question(0.9, ["a"])], reason="no_prior_snapshot")
    )
    assert block == ""


def test_a_week_with_a_prior_but_no_overlap_renders_nothing():
    assert aw._build_also_last_week_block(
        _payload([], [_question(0.9, ["a"])])
    ) == ""


def test_absent_since_prior_never_reaches_the_prompt():
    """THE D-CONSTRAINT, asserted directly rather than trusted. An anchor can
    leave that set by slipping out of the top-5 the snapshot stores per question
    — a cap artefact — not because the person let anything go. Prose built on it
    would state a change in someone's inner life that the data does not support.
    The payload here carries two absent ids and one new one; none may appear."""
    block = aw._build_also_last_week_block(
        _payload(["a"], [_question(0.9, ["a"])])
    )
    assert "gone-1" not in block
    assert "gone-2" not in block
    assert "new-1" not in block


def test_new_since_prior_is_not_rendered_either():
    """Deliberately unused: a new anchor this week is, in the common case, the
    same fact as this week's spine card — overlap, not signal. Deferred, not
    forgotten."""
    payload = _payload([], [_question(0.9, ["a"])])
    payload["changes_since_prior"]["new_since_prior"] = ["a"]
    assert aw._build_also_last_week_block(payload) == ""


def test_an_unresolvable_anchor_is_skipped_and_the_rest_still_render():
    """A `still` id is by definition an anchor of this payload, so this should be
    impossible. The snapshot is a historical record that an older version of the
    job may have written, so it is read as data rather than trusted."""
    block = aw._build_also_last_week_block(
        _payload(["missing", "a"], [_question(0.9, ["a"])])
    )
    assert block == "<also_last_week>\n- words for a\n</also_last_week>\n\n"


def test_every_anchor_unresolvable_renders_nothing():
    assert aw._build_also_last_week_block(
        _payload(["missing"], [_question(0.9, ["a"])])
    ) == ""


def test_a_long_snippet_is_truncated_rather_than_dropped():
    block = aw._build_also_last_week_block(_payload(
        ["a"], [{"memory_entry_id": "e", "text": "t", "top_score": 0.9,
                 "prior_matches": [{"memory_entry_id": "a", "text": "x" * 400,
                                    "score": 0.9}]}],
    ))
    line = block.splitlines()[1]
    assert line.endswith("…")
    assert len(line) == len("- ") + aw.ALSO_LAST_WEEK_SNIPPET_MAX + 1


def test_a_missing_or_empty_payload_renders_nothing():
    """A status='failed' row carries {"version", "error"} and no questions at
    all. Such rows are excluded by the WHERE clause, but the builder must not
    depend on that to avoid raising."""
    for payload in (None, {}, {"version": 1, "error": "boom"},
                    {"version": 1, "recurring_questions": []}):
        assert aw._build_also_last_week_block(payload) == ""
