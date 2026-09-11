# -*- coding: utf-8 -*-
"""The last generators that did not state an output language — and the claim.

#626 opened this class, #627/#628 took the memory writers and the self-portrait
summary, #630 took the seven in the counterview / insight-mirror / you-vs-you
group. This file covers the rest, after which the claim in the PR body holds:

    No prompt in the product asks a model to infer its output language.

  MIRROR_PROMPT            (weekly + preview) stated nothing.
  CONCLUSION_PROMPT        stated nothing.
  SHIFT_CLASSIFY_PROMPT    stated nothing.
  RECURRENCE_PROMPT        stated nothing.
  COUNCIL_SYNTHESIS_PROMPT INFERRED — its theme rule ended "Same language as the
                           verdict". Worse than the counterview title line #630
                           deleted: a verdict is another MODEL'S output, so this
                           asked the model to infer a language from itself.
  COUNCIL_DISTILL_PROMPT   stated nothing.
  conversation title       (inline prompt, arq_worker) stated nothing.

TWO CORRECTIONS TO THE BRIEF THIS WAS WRITTEN FROM, both verified against code:

  MIRROR does NOT read both roles. Its query already carries
  Message.role == "user", so its source was clean and needed no change. The
  generators that DO mix roles are assess_conclusion_task, the conversation
  title, and _distill_brief — all three rendered PERSON:/YOU: or role-prefixed,
  and all three take the user subset here.

  THE MEMORY ROWS ARE NOT A SOURCE THAT A FLOOR COULD FIX. The brief asked
  whether old pre-#627 rows need one. They are the smaller half: #627's guard on
  memory writes LOGS rather than blocks, so wrong-language rows are still
  produced deliberately today. detect_recurrence takes the language from its
  caller's verbatim user text instead.

WHY A TRANSCRIPT IS NEVER THE SOURCE, in one line, because it is the thing this
whole class keeps getting wrong: dominant_language counts CHARACTERS, and a
persona reply is several times longer than the message that prompted it, so a
mixed transcript is a vote the model wins.

Run: cd apps/api && pytest tests/test_last_prompt_language.py -v
"""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import services.council_service as cvs
import services.memory_service as ms
import workers.arq_worker as aw
from services.council_prompts import COUNCIL_DISTILL_PROMPT, COUNCIL_SYNTHESIS_PROMPT
from services.memory_service import RECURRENCE_PROMPT, SHIFT_CLASSIFY_PROMPT
from text_utils import EN_MIN_TOKENS, english_function_word_ratio, language_matches
from workers.arq_worker import CONCLUSION_PROMPT, MIRROR_PROMPT

USER_ID = "11111111-1111-1111-1111-111111111111"
CONV_ID = "22222222-2222-2222-2222-222222222222"

EL_USER_1 = "Σκέφτομαι συνέχεια αν πρέπει να αφήσω τη δουλειά μου φέτος."
EL_USER_2 = "Δεν ξέρω αν φοβάμαι την αλλαγή ή απλώς βαριέμαι να αποφασίσω."
EN_USER_1 = "I keep thinking about whether I should leave my job this year."
EN_USER_2 = "I do not know if I fear the change or just dread deciding."

# A persona turn: far longer than the message that prompted it. This is the
# whole reason a transcript cannot be the source.
EN_PERSONA_TURN = (
    "There is a difference between the fear of change and the exhaustion of "
    "deliberation, and you have been treating them as one thing for some time "
    "now. Consider what it would mean to name which of the two is actually "
    "holding the door shut, because the remedies are not the same and the one "
    "you keep reaching for belongs to the other problem entirely."
)

EL_MIRROR = {
    "status": "generated",
    "moments": [{"said": "Δεν ξέρω αν φοβάμαι", "meant": "Δεν ζυγίζεις πια την απόφαση, περιμένεις να στη πάρουν από τα χέρια."}],
    "thread": "Αυτό που λες υπομονή ίσως είναι ο φόβος να είσαι εσύ η αιτία του τέλους.",
}
EN_MIRROR = {
    "status": "generated",
    "moments": [{"said": "I keep thinking", "meant": "You are not weighing this anymore; you are waiting for it to be taken out of your hands."}],
    "thread": "What you call patience may be the fear of being the one who caused the ending.",
}


def _msg(content, role="user", safety_level="none"):
    """role / content / safety_level / created_at — every field these generators
    read, set explicitly (C-06)."""
    from datetime import datetime, timezone
    return SimpleNamespace(
        role=role, content=content, safety_level=safety_level,
        message_kind="standard",
        created_at=datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc),
    )


# ═══════════════════════════════════════════════════════════════════════════
# (1) The claim, as a test over the prompt bodies
# ═══════════════════════════════════════════════════════════════════════════

THIS_PR = [
    (MIRROR_PROMPT, "MIRROR_PROMPT"),
    (CONCLUSION_PROMPT, "CONCLUSION_PROMPT"),
    (SHIFT_CLASSIFY_PROMPT, "SHIFT_CLASSIFY_PROMPT"),
    (RECURRENCE_PROMPT, "RECURRENCE_PROMPT"),
    (COUNCIL_SYNTHESIS_PROMPT, "COUNCIL_SYNTHESIS_PROMPT"),
    (COUNCIL_DISTILL_PROMPT, "COUNCIL_DISTILL_PROMPT"),
]


@pytest.mark.parametrize("prompt,name", THIS_PR)
def test_no_prompt_body_infers_or_hardcodes_a_language(prompt, name):
    body = prompt.lower()
    assert "same language" not in body, f"{name} infers its own language"
    assert "write in greek" not in body, f"{name} hardcodes a language"
    assert "write in english" not in body, f"{name} hardcodes a language"


def test_the_synthesis_theme_rule_no_longer_points_at_the_verdict():
    """The specific line, named. It asked the model to take its language from
    text the model had just written — inference squared."""
    assert "Same language as the verdict" not in COUNCIL_SYNTHESIS_PROMPT
    assert "TERRITORY" in COUNCIL_SYNTHESIS_PROMPT, "the rest of the theme rule stands"


def test_every_prompt_in_the_product_is_enumerated_here_or_already_done():
    """THE CLAIM'S EVIDENCE, not a vibe. Every module that builds a system prompt
    is listed with how it settles its language, so the claim in the PR body can be
    re-checked by reading one place. A new prompt module makes this fail.

    'states none, mirrors the conversation' is the chat system prompt. It does not
    ASK the model to infer — it says nothing, and the model answers each turn in
    the language of the turn it is answering. That is a different thing from a
    one-shot generator reading a whole transcript, which is what every defect in
    this class has been.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    settled = {
        # module                              how its language is settled
        "services/council_prompts.py":        "directive (#626 brief, this PR distill+synthesis)",
        "services/counterview_service.py":    "directive (#630)",
        "services/insight_mirror_service.py": "directive (#630)",
        "services/self_comparison_prompts.py": "directive (#630)",
        "services/self_portrait_prompts.py":  "directive (#627)",
        "services/memory_service.py":         "directive (#627/#628, this PR shift+recurrence)",
        "workers/arq_worker.py":              "letters {language} field (2026-08); mirror/conclusion/title directive, this PR",
        "prompts/system_base.jinja2":         "states none, mirrors the conversation — not inference",
        "prompts/safety_response.jinja2":     "per-language template, chosen by dominant_language",
        "prompts/safety_response_el.jinja2":  "per-language template, chosen by dominant_language",
    }
    found = set()
    for path in list(root.glob("services/*.py")) + list(root.glob("workers/*.py")) + list(root.glob("prompts/*.jinja2")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(root).as_posix()
        if "_PROMPT = " in text or path.suffix == ".jinja2":
            found.add(rel)
    unaccounted = found - set(settled)
    assert not unaccounted, (
        f"prompt-bearing modules not accounted for in the language claim: "
        f"{sorted(unaccounted)}"
    )


def test_the_dead_insight_prompt_is_gone():
    """INSIGHT_PROMPT was defined in arq_worker and referenced only by a docstring
    describing a call site that no longer existed. Deleted in its own commit; this
    pins that it does not come back unused."""
    assert not hasattr(aw, "INSIGHT_PROMPT")


# ═══════════════════════════════════════════════════════════════════════════
# (2) The weekly / preview mirror
# ═══════════════════════════════════════════════════════════════════════════


def test_the_mirror_query_still_filters_to_the_person_and_this_is_load_bearing():
    """The mirror's language source is safe ONLY because its query is user-only.
    If that filter is ever relaxed, the source silently becomes a mixed
    transcript — the defect this whole class is made of — so the filter is pinned
    here rather than left as a fact someone has to notice."""
    import inspect
    src = inspect.getsource(aw.generate_weekly_mirror_task)
    assert 'Message.role == "user"' in src
    assert "mirror_language = _dominant_language" in src


async def _mirror(monkeypatch, messages, reply, *, kind="weekly"):
    """Drive generate_weekly_mirror_task with its DB and LLM stubbed. Returns
    (the Mirror rows added, the captured system prompt)."""
    added = []
    systems = []

    complete = AsyncMock(side_effect=lambda **kw: (systems.append(kw["system"]), reply)[1])

    persona = SimpleNamespace(id="p1", name="Carl Jung", tradition="analytical psychology")
    results = [
        _r(scalar=persona),   # persona by slug
        _r(scalar=None),      # dedup: no existing mirror
        _r(all_=messages),    # the week's user messages
    ]
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=results)
    db.add = MagicMock(side_effect=lambda o: added.append(o))
    db.commit = AsyncMock()

    class _Session:
        async def __aenter__(self): return db
        async def __aexit__(self, *a): return False

    # Both are imported INSIDE the task body, so they are patched at their source
    # modules rather than on `aw` — there is no aw.llm_client to set.
    with (
        patch("db.session.AsyncSessionLocal", lambda: _Session()),
        patch("services.llm_client.llm_client.complete", new=complete),
    ):
        await aw.generate_weekly_mirror_task({}, USER_ID, "carl_jung", kind, 7)
    return added, (systems[0] if systems else "")


_SENTINEL = object()


def _r(*, scalar=_SENTINEL, all_=_SENTINEL):
    r = MagicMock()
    if scalar is not _SENTINEL:
        r.scalar_one_or_none.return_value = scalar
    if all_ is not _SENTINEL:
        r.scalars.return_value.all.return_value = all_
    return r


EL_WEEK = [_msg(EL_USER_1), _msg(EL_USER_2), _msg(EL_USER_1), _msg(EL_USER_2), _msg(EL_USER_1)]
EN_WEEK = [_msg(EN_USER_1), _msg(EN_USER_2), _msg(EN_USER_1), _msg(EN_USER_2), _msg(EN_USER_1)]


@pytest.mark.asyncio
async def test_a_greek_week_tells_the_mirror_to_write_greek(monkeypatch):
    _, system = await _mirror(monkeypatch, EL_WEEK, json.dumps(EL_MIRROR))
    assert "LANGUAGE: Write in Greek." in system


@pytest.mark.asyncio
async def test_the_mirror_directive_is_appended_after_format(monkeypatch):
    """MIRROR_PROMPT carries three DOUBLED brace pairs for its JSON shape plus two
    real fields. All three things must hold at once."""
    _, system = await _mirror(monkeypatch, EN_WEEK, json.dumps(EN_MIRROR))
    assert "You are Carl Jung, analytical psychology." in system
    assert '{"status": "generated", "moments"' in system, "JSON braces must be single"
    assert system.endswith("governs the whole output even if the input mixes languages.")


@pytest.mark.asyncio
async def test_a_wrong_language_mirror_writes_NO_ROW_not_an_empty_one(monkeypatch):
    """THE RULING, and the half that is not obvious. 'empty' would assert the week
    held nothing (A18 1.3) AND — because dispatch_preview_mirrors selects users
    with no Mirror row of ANY status — would disqualify this person from every
    future preview mirror. No row leaves them eligible, and that cron runs
    hourly."""
    added, _ = await _mirror(monkeypatch, EN_WEEK, json.dumps(EL_MIRROR))
    assert added == [], "a wrong-language mirror must persist nothing at all"


@pytest.mark.asyncio
async def test_a_matching_mirror_is_written(monkeypatch):
    """The inverse regression: a guard that dropped everything would also pass the
    test above."""
    added, _ = await _mirror(monkeypatch, EN_WEEK, json.dumps(EN_MIRROR))
    assert len(added) == 1 and added[0].status == "generated"
    assert added[0].payload["thread"] == EN_MIRROR["thread"]


@pytest.mark.asyncio
async def test_the_mirror_checks_thread_and_meant_but_never_said(monkeypatch):
    """Shared with the insight mirror through payload_language_matches. `said` is
    the person's own charged phrase quoted back — in their language by
    construction, and too short to measure."""
    payload = {
        "status": "generated",
        "moments": [{"said": "δεν αντέχω άλλο", "meant": EN_MIRROR["moments"][0]["meant"]}],
        "thread": EN_MIRROR["thread"],
    }
    added, _ = await _mirror(monkeypatch, EN_WEEK, json.dumps(payload))
    assert len(added) == 1, "a Greek `said` inside an English mirror must not block"


@pytest.mark.asyncio
async def test_a_wrong_language_meant_does_block(monkeypatch):
    payload = {
        "status": "generated",
        "moments": [{"said": "I keep thinking", "meant": EL_MIRROR["moments"][0]["meant"]}],
        "thread": EN_MIRROR["thread"],
    }
    added, _ = await _mirror(monkeypatch, EN_WEEK, json.dumps(payload))
    assert added == []


def test_both_mirrors_share_one_payload_checker():
    """One helper, two mirrors — promoted rather than copied, so the rule cannot
    drift between the weekly and the insight-seeded mirror."""
    from services.insight_mirror_service import payload_language_matches
    assert aw.payload_language_matches is payload_language_matches


# ═══════════════════════════════════════════════════════════════════════════
# (3) The conversation conclusion — the first of the mixed transcripts
# ═══════════════════════════════════════════════════════════════════════════


async def _conclusion(window, reply):
    """Drive assess_conclusion_task past its dedup and safety gates."""
    added = []
    systems = []

    async def complete(**kw):
        systems.append(kw["system"])
        return reply

    conv = SimpleNamespace(id=CONV_ID, user_id=USER_ID, persona_id="p1")
    persona = SimpleNamespace(id="p1", name="Carl Jung", tradition="analytical psychology")

    results = [
        _r(scalar=conv),        # the conversation
        _scalar_result(None),   # last conclusion timestamp — none yet
        _r(all_=window),        # the context window
        _r(scalar=persona),     # the persona
    ]
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=results)
    db.add = MagicMock(side_effect=lambda o: added.append(o))
    db.commit = AsyncMock()

    class _Session:
        async def __aenter__(self): return db
        async def __aexit__(self, *a): return False

    with (
        patch("db.session.AsyncSessionLocal", lambda: _Session()),
        patch("services.llm_client.llm_client.complete", new=complete),
    ):
        await aw.assess_conclusion_task({}, CONV_ID, USER_ID)
    return added, (systems[0] if systems else "")


def _scalar_result(value):
    r = MagicMock()
    r.scalar.return_value = value
    r.scalar_one_or_none.return_value = value
    return r


# A REALISTIC MIXED WINDOW: the person writes Greek, the persona answered in
# English once. By TURNS it is 2:1 in the person's favour; by CHARACTERS the one
# English reply outweighs both Greek messages together. That inversion is the
# whole reason the source is the user subset and not the transcript.
MIXED_EL_WINDOW = [
    _msg(EL_USER_1, role="user"),
    _msg(EN_PERSONA_TURN, role="assistant"),
    _msg(EL_USER_2, role="user"),
]


def test_the_mixed_window_really_does_invert_by_character_count():
    """The premise the conclusion fix rests on, measured rather than asserted. If
    this ever stops being true the fix is still right, but the comment explaining
    it would be wrong."""
    from text_utils import dominant_language
    whole = [m.content for m in MIXED_EL_WINDOW]
    user_only = [m.content for m in MIXED_EL_WINDOW if m.role == "user"]
    assert dominant_language(whole) == "English", "the transcript reads English"
    assert dominant_language(user_only) == "Greek", "the person does not"


@pytest.mark.asyncio
async def test_the_conclusion_language_comes_from_the_person_not_the_transcript():
    """THE FIX, at the site the brief pointed at. Same window as above: reading the
    transcript would say English, reading the person says Greek."""
    _, system = await _conclusion(MIXED_EL_WINDOW, "Η αναμονή είναι μια απόφαση που αρνείται να υπογράψει το όνομά της.")
    assert "LANGUAGE: Write in Greek." in system


@pytest.mark.asyncio
async def test_the_conclusion_directive_is_appended_after_format():
    _, system = await _conclusion(
        [_msg(EN_USER_1), _msg(EN_PERSONA_TURN, role="assistant"), _msg(EN_USER_2)],
        "You want the ending without being its author.",
    )
    assert "You are Carl Jung, analytical psychology." in system
    assert system.endswith("governs the whole output even if the input mixes languages.")


@pytest.mark.asyncio
async def test_a_wrong_language_conclusion_writes_no_row():
    """Writing nothing is this path's ORDINARY outcome (NOT_YET returns on most
    turns), so the block costs almost nothing and the cadence gate re-triggers on
    the next turn."""
    added, _ = await _conclusion(
        [_msg(EN_USER_1), _msg(EN_PERSONA_TURN, role="assistant"), _msg(EN_USER_2)],
        "Η αναμονή είναι μια απόφαση που αρνείται να υπογράψει το όνομά της.",
    )
    assert added == []


@pytest.mark.asyncio
async def test_a_matching_conclusion_is_written():
    added, _ = await _conclusion(
        [_msg(EN_USER_1), _msg(EN_PERSONA_TURN, role="assistant"), _msg(EN_USER_2)],
        "You want the ending without being its author.",
    )
    assert len(added) == 1
    assert added[0].message_kind == "conclusion"


@pytest.mark.asyncio
async def test_a_terse_english_conclusion_is_not_blocked():
    """EN_MIN_TOKENS ENGAGES HERE AND NOWHERE ELSE IN THIS PR. A conclusion is
    aphoristic and capped at two sentences, so it can land under the threshold —
    where only the script test runs. It must not be nulled for want of function
    words."""
    assert len("Gravity, not cleverness.".split()) < EN_MIN_TOKENS
    assert english_function_word_ratio("Gravity, not cleverness.") < 0.5
    added, _ = await _conclusion(
        [_msg(EN_USER_1), _msg(EN_PERSONA_TURN, role="assistant"), _msg(EN_USER_2)],
        "Gravity, not cleverness.",
    )
    assert len(added) == 1


# ═══════════════════════════════════════════════════════════════════════════
# (4) Shift / recurrence — where the memory rows are NOT the source
# ═══════════════════════════════════════════════════════════════════════════


def test_detect_recurrence_will_not_run_without_being_told_the_language():
    """Keyword-only and undefaulted, so no caller can fall back to the memory rows
    it happens to be holding."""
    import inspect
    sig = inspect.signature(ms.memory_service.detect_recurrence)
    p = sig.parameters["language"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is inspect.Parameter.empty


def test_both_callers_pass_the_persons_verbatim_words():
    """extract_memory_task passes `user_text` (the message itself) and
    counterview_belief_task passes `belief` (what they typed) — never the entries
    just extracted from either."""
    import inspect
    extract = inspect.getsource(aw.extract_memory_task)
    belief = inspect.getsource(aw.counterview_belief_task)
    assert "language=_dominant_language([user_text])" in extract
    assert "language=_dominant_language([belief])" in belief


async def _recurrence(monkeypatch, language, shift_reply, fallback_reply="Το ίδιο ερώτημα επιστρέφει ξανά, όπως και πριν από εβδομάδες."):
    """Drive detect_recurrence from the classify call onward, with detection
    stubbed to a fixed match set."""
    added = []
    systems = []
    replies = iter([shift_reply, fallback_reply])

    async def complete(**kw):
        systems.append(kw["system"])
        return next(replies)

    entry = SimpleNamespace(
        id="e1", content="model-written row", embedding=[0.1] * 8,
        conversation_id=CONV_ID,
    )
    match = SimpleNamespace(content="another model-written row", conversation_id="other")

    db = AsyncMock()
    db.add = MagicMock(side_effect=lambda o: added.append(o))
    db.commit = AsyncMock()
    gate = AsyncMock(return_value=None)
    rows = MagicMock()
    rows.fetchall.return_value = [SimpleNamespace(score=0.99, content=match.content,
                                                 conversation_id="other")]
    db.execute = AsyncMock(return_value=rows)

    monkeypatch.setattr(ms.memory_service, "_insight_gate_blocked", gate)
    with patch("services.llm_client.llm_client.complete", new=complete):
        await ms.memory_service.detect_recurrence(
            db=db, user_id=USER_ID, conversation_id=CONV_ID, persona_id="p1",
            new_entries=[entry], language=language,
        )
    return added, systems


EL_SHIFT = json.dumps({
    "insight_type": "pattern",
    "content": "Το ερώτημα αν πρέπει να φύγεις από τη δουλειά σου επιστρέφει ξανά, όπως και πριν από εβδομάδες.",
})
EN_SHIFT = json.dumps({
    "insight_type": "pattern",
    "content": "The question of whether to leave your job has come up again, as it did weeks ago.",
})


@pytest.mark.asyncio
async def test_the_classify_call_is_told_the_callers_language(monkeypatch):
    _, systems = await _recurrence(monkeypatch, "Greek", EL_SHIFT)
    assert "LANGUAGE: Write in Greek." in systems[0]


@pytest.mark.asyncio
async def test_the_language_is_not_read_off_the_memory_rows(monkeypatch):
    """THE (c) FINDING, pinned. Both rows fed to this call are English — which is
    exactly what a pre-#627 row for a Greek user looks like, and what #627's
    log-only guard still permits today. The caller says Greek; Greek wins."""
    added, systems = await _recurrence(monkeypatch, "Greek", EL_SHIFT)
    assert "LANGUAGE: Write in Greek." in systems[0]
    assert len(added) == 1, "and the Greek insight is written"


@pytest.mark.asyncio
async def test_a_wrong_language_shift_falls_through_to_the_fallback(monkeypatch):
    """NOT straight out. The same door a parse failure takes, so the insight is
    not lost to a classification that was merely in the wrong language — and the
    fallback carries its own directive and its own check."""
    added, systems = await _recurrence(monkeypatch, "Greek", EN_SHIFT)
    assert len(systems) == 2, "the RECURRENCE fallback must have been called"
    assert "LANGUAGE: Write in Greek." in systems[1]
    assert len(added) == 1, "and the fallback's Greek phrasing is written"
    assert added[0].insight_type == "pattern"


@pytest.mark.asyncio
async def test_when_the_fallback_is_wrong_too_no_insight_is_written(monkeypatch):
    """Last chance used up. Costs nothing lasting: the memory rows are untouched,
    so the theme re-triggers later, and _insight_gate_blocked throttles on
    insights that EXIST — writing none never starts the window."""
    added, _ = await _recurrence(
        monkeypatch, "Greek", EN_SHIFT,
        fallback_reply="The question of whether to leave your job has come up again.",
    )
    assert added == []


@pytest.mark.asyncio
async def test_a_matching_shift_is_written_without_the_fallback(monkeypatch):
    added, systems = await _recurrence(monkeypatch, "Greek", EL_SHIFT)
    assert len(systems) == 1, "no fallback call when the classification is fine"
    assert len(added) == 1


# ═══════════════════════════════════════════════════════════════════════════
# (5) The council distill and synthesis
# ═══════════════════════════════════════════════════════════════════════════


async def _distill(recent, reply):
    systems = []

    async def complete(**kw):
        systems.append(kw["system"])
        return reply

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_r(all_=recent))
    with patch("services.llm_client.llm_client.complete", new=complete):
        out = await cvs.council_service._distill_brief(db, USER_ID, CONV_ID)
    return out, (systems[0] if systems else "")


@pytest.mark.asyncio
async def test_the_distill_language_comes_from_the_person_not_the_transcript():
    """Second of the three mixed transcripts. `transcript` renders both roles
    role-prefixed; the language does not."""
    _, system = await _distill(
        MIXED_EL_WINDOW,
        "Αυτό το άτομο παλεύει με το αν πρέπει να αφήσει τη δουλειά του.",
    )
    assert "LANGUAGE: Write in Greek." in system


@pytest.mark.asyncio
async def test_a_wrong_language_brief_is_dropped_and_the_raw_matter_wins():
    """Returning None is the documented failure path, and the caller's fallback is
    `effective_matter = brief or matter` — the person's OWN words. So the block
    does not merely avoid a bad brief, it substitutes a better input."""
    out, _ = await _distill(
        MIXED_EL_WINDOW,
        "This person is wrestling with whether to leave their job and wants a judgment.",
    )
    assert out is None


@pytest.mark.asyncio
async def test_a_matching_brief_survives():
    brief = "Αυτό το άτομο παλεύει με το αν πρέπει να αφήσει τη δουλειά του."
    out, _ = await _distill(MIXED_EL_WINDOW, brief)
    assert out == brief


EN_SYNTHESIS = {
    "verdict": "The chamber converges on the cost of waiting and splits on what you owe the people around you.",
    "tension": "Leaving costs security; staying costs the years you cannot get back.",
    "real_question": "Are you allowed to want this?",
    "next_move": "Name one date by which you will decide.",
    "theme": "On leaving well",
}
EL_VERDICT = "Η αίθουσα συγκλίνει στο κόστος της αναμονής και διχάζεται στο τι οφείλεις."


def test_a_single_wrong_language_beat_is_caught_and_not_outvoted():
    """WHY THE SCRIPT TEST IS PER BEAT. Three correct English beats against one
    Greek `verdict` — and language_matches counts characters, so a joined test
    passes this (measured joined ratio 0.480, comfortably over the floor). The
    beat it would wave through is the one stored flat as session.synthesis and
    printed on the share card."""
    from services.council_service import _synthesis_language_ok
    greek_verdict = dict(EN_SYNTHESIS, verdict=EL_VERDICT)
    assert not _synthesis_language_ok(greek_verdict, "English")
    assert language_matches(" ".join(str(greek_verdict[k]) for k in
                                     ("verdict", "tension", "real_question", "next_move")),
                            "English"), "joined, it would have passed — that is the point"


def test_content_dense_english_beats_are_not_rejected():
    """WHY THE RATIO IS ON THE JOINED PROSE. Both of these are correct English in
    this prompt's own compressed register, both are 7-11 tokens so EN_MIN_TOKENS
    does not exempt them, and both score far under the 0.30 floor ALONE. A
    per-beat ratio would null real synthesis on a regular basis."""
    dense = dict(EN_SYNTHESIS,
                 tension="Ambition dressed as duty exhausts everyone eventually.",
                 next_move="Naming one date converts dread into arithmetic.")
    assert english_function_word_ratio(dense["tension"]) < 0.20
    assert english_function_word_ratio(dense["next_move"]) < 0.30
    assert len(dense["tension"].split()) > EN_MIN_TOKENS
    from services.council_service import _synthesis_language_ok
    assert _synthesis_language_ok(dense, "English")


def test_a_whole_synthesis_in_another_latin_script_language_is_caught():
    """What the ratio half is for: nothing here fails the script test."""
    from services.council_service import _synthesis_language_ok
    indonesian = {
        "verdict": "Ruang sidang sepakat tentang biaya menunggu dan terbelah soal apa yang kamu hutangi.",
        "tension": "Pergi menghabiskan rasa aman; tinggal menghabiskan tahun yang tak bisa kamu ambil kembali.",
        "real_question": "Apakah kamu boleh menginginkan ini?",
        "next_move": "Sebutkan satu tanggal kapan kamu akan memutuskan.",
    }
    assert not _synthesis_language_ok(indonesian, "English")


def test_a_clean_english_synthesis_passes():
    from services.council_service import _synthesis_language_ok
    assert _synthesis_language_ok(EN_SYNTHESIS, "English")


def test_a_wrong_language_theme_does_not_sink_the_synthesis():
    """Field-level, like the counterview title: a bad theme costs the share card's
    context line, not the instrument."""
    from services.council_service import _synthesis_language_ok
    assert _synthesis_language_ok(dict(EN_SYNTHESIS, theme="Περί καλής αποχώρησης"), "English")


@pytest.mark.asyncio
async def test_the_theme_is_nulled_field_level_on_a_language_miss():
    from services.council_service import _clean_field
    assert await _clean_field("Περί καλής αποχώρησης", cap_words=8, language="English") is None
    assert await _clean_field("On leaving well", cap_words=8, language="English") == "On leaving well"


@pytest.mark.asyncio
async def test_a_short_english_theme_is_not_nulled():
    """3-6 words by prompt rule, so usually under EN_MIN_TOKENS — the script test
    is what catches the cross the deleted inference line was aiming at, and it
    must not reject correct English."""
    from services.council_service import _clean_field
    assert await _clean_field("On ambition", cap_words=8, language="English") == "On ambition"
