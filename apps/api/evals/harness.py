"""Generation for the §8.2 eval harness — the SAME code production uses.

THE WHOLE POINT OF THIS MODULE IS THAT IT CONTAINS ALMOST NO LOGIC. Every piece
of the prompt is produced by the function production calls, imported rather than
reimplemented:

    prompt_builder.build_system          <- services/prompt_builder.py
    _deepen_directive                    <- services/conversation_service.py
    phenomenology_bridge_service.lookup   <- services/phenomenology_bridge_service.py
    prompt_builder.split_system_for_cache <- services/prompt_builder.py
    _history_cache_control                <- services/conversation_service.py
    MODEL_FREE / MODEL_PRO                <- services/conversation_service.py
    llm_client.stream                     <- services/llm_client.py

If the assembled prompt differed from production by one line, the run would be
measuring something else, and nothing about the numbers would say so.
tests/test_harness_parity.py asserts BYTE EQUALITY between what `assemble_system`
returns and a string built inline from the same production pieces, so an edit to
system_base.jinja2 or to the directive text fails in CI rather than quietly
changing what the next eval measured.

WHAT IS STUBBED, AND WHY EACH IS PRODUCTION-IDENTITY RATHER THAN A SHORTCUT.
These are the values `stream_response` computes in Phase A. For the first turn of
a fresh conversation belonging to a user with no onboarding profile, they are:

    memories  = []     memory_service.recall returns nothing on turn 1
    passages  = []     RETRIEVAL-001: zero non-empty retrieval_ids in 166
                       messages; the score ceiling is ~0.46 against a 0.72
                       threshold, so production retrieves nothing for anyone
    profile   = None   no onboarding pills
    history   = []     first message

None of these is a simplification of production behaviour. They are what
production has.

WHAT IS NOT STUBBED. The phenomenology bridge runs, because it runs in
production: PHENOMENOLOGY_BRIDGE_ENABLED is true in Render (philosopher-api,
verified by the founder in the dashboard 2026-09-22). The flag is read from the
environment, recorded in the manifest, and compare.py refuses to diff two runs
that disagree about it.

HOW MUCH THE FLAG ACTUALLY CHANGES — MEASURED, because the obvious number is
wrong. Nine of the ten problems carry an `expected_phenomenology_match`, and an
earlier version of this docstring inferred from that field that the bridge would
fire on nine-tenths of the corpus. Running the real matcher over the real problem
text says otherwise: it fires on THREE of ten problems, i.e. 33 of 110 samples.

    P01  expects ghosting_after_great_dates   fires as  ghosting
    P03  expects burnout                      fires as  imposter_syndrome
    P05  expects fear_of_failure              fires as  fear_of_failure
    P02 P04 P06 P07 P09 P10  expect a match, fire NOTHING
    P08  expects none, fires none

All nine expected keys exist in modern_phenomenology.json; the triggers for them
simply do not occur in the problem text. `expected_phenomenology_match` is an
authored expectation that was never checked against the matcher, and only ONE of
the nine is correct. That is an eval-data defect, logged separately — the harness
reproduces production faithfully either way, and production is what run 1
measures.

The flag still matters: it changes 30% of the corpus, not 90%.

PLAN AND MODEL ARE ONE CHOICE, NOT TWO. conversation_service.py:967 reads
`MODEL_PRO if user_plan in ("pro","premium") else MODEL_FREE`. A run therefore
generates each sample twice — once as a free user on Haiku 4.5, once as a Pro
user on Sonnet 4.6 — because those are production's two paths and BUG-024 GAP 1
means the stored data cannot separate them (`model_used` is NULL on every row).
This harness is the only instrument that can.

NOTHING HERE REGENERATES. `regenerate_or_trim` is never called and must not be.
The harness scores the RAW FIRST COMPLETION, and records separately whether
production's single correction pass would have fired on it. Scoring a corrected
reply would make brevity and anti-flex measure each other.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

from personas import PERSONA_REGISTRY
from personas._base import PersonaConfig
from services.conversation_service import (
    MODEL_FREE,
    MODEL_PRO,
    _deepen_directive,
    _history_cache_control,
)
from services.llm_client import llm_client
from services.phenomenology_bridge_service import phenomenology_bridge_service
from services.prompt_builder import CACHE_SPLIT_SENTINEL, prompt_builder

from . import arm_b
from .prompt_set import Sample

# Read the same way conversation_service.py:214 reads it, so a run cannot
# silently disagree with the deployed flag. Recorded in the manifest.
PHENOMENOLOGY_BRIDGE_ENABLED = (
    os.getenv("PHENOMENOLOGY_BRIDGE_ENABLED", "false").lower() == "true"
)

# (label, plan, model) — production's two paths, conversation_service.py:967.
ARMS_BY_PLAN = (
    ("free", "free", MODEL_FREE),
    ("pro", "pro", MODEL_PRO),
)


@dataclass
class Completion:
    sample_id: str
    problem_id: str
    persona_slug: str
    mode: str
    plan: str
    model: str
    user_message: str
    reply: str
    system_prompt: str            # the exact string sent, sentinel removed
    bridge_matched: str | None    # phenomenology mapping_key, or None
    tokens: dict = field(default_factory=dict)
    error: str | None = None


def assemble_system(
    persona: PersonaConfig,
    user_message: str,
    *,
    deep: bool,
    include_cache_sentinel: bool = True,
    arm: str = "baseline",
) -> tuple[str, str | None]:
    """Build the system prompt exactly as `stream_response` does for turn 1.

    Returns (system_prompt, bridge_matched_term).

    The order below mirrors conversation_service.py:816-936 for the first-turn
    case: build_system, then the deep directive when deep mode is on. The
    adaptive-length directive is NOT applied and must not be — production gates
    it behind `history_len > 1` (:931), so it never fires on a first message.
    The seeded-opening and cross-mind directives likewise do not apply: no
    seeded topic, no foreign persona in an empty history.
    """
    bridge = None
    if PHENOMENOLOGY_BRIDGE_ENABLED:
        try:
            bridge = phenomenology_bridge_service.lookup(
                user_message=user_message, persona_slug=persona.slug,
            )
        except Exception:
            # Production fails open here (conversation_service.py:798-805) and
            # proceeds without a bridge. Matching that matters: a harness that
            # raised would drop the sample, and a dropped sample is invisible in
            # a rate.
            bridge = None

    system = prompt_builder.build_system(
        persona=persona,
        memories=[],
        passages=[],
        phenomenology_bridge=bridge,
        profile=None,
        include_cache_sentinel=include_cache_sentinel,
    )
    if deep:
        system = system + "\n\n" + _deepen_directive(persona)

    # ARM B IS APPENDED LAST — after HARD RULE 8 and after the deep
    # directive. arm "baseline" appends nothing and is byte-identical to
    # run 1, which tests/test_harness_parity.py asserts for all 11 personas
    # x deep/standard x bridge on/off.
    if arm == "tightened":
        system = system + "\n\n" + arm_b.directive(
            persona.slug, deep=deep, first_message=True
        )
    elif arm != "baseline":
        raise ValueError(f"unknown arm {arm!r}; expected one of {arm_b.ARMS}")

    return system, (bridge.matched_term if bridge else None)


async def generate(sample: Sample, plan: str, model: str,
                   arm: str = "baseline") -> Completion:
    """One completion. Streams, exactly as production does, and accumulates."""
    persona = PERSONA_REGISTRY[sample.persona_slug]
    system, bridge_term = assemble_system(
        persona, sample.user_message, deep=sample.deep, arm=arm,
    )
    messages = [{"role": "user", "content": sample.user_message}]
    sink: dict = {}

    buf: list[str] = []
    error = None
    try:
        async for chunk in llm_client.stream(
            system=prompt_builder.split_system_for_cache(system),
            messages=messages,
            model=model,
            # history is empty and nothing was dropped, so this is what
            # production passes on a first turn: None for free, a breakpoint
            # for pro. See conversation_service.py:170-195.
            cache_control=_history_cache_control(plan, False),
            _token_sink=sink,
        ):
            buf.append(chunk)
    except Exception as exc:                       # noqa: BLE001 - recorded, not raised
        error = f"{type(exc).__name__}: {exc}"

    return Completion(
        sample_id=sample.sample_id,
        problem_id=sample.problem_id,
        persona_slug=sample.persona_slug,
        mode=sample.mode,
        plan=plan,
        model=model,
        user_message=sample.user_message,
        reply="".join(buf),
        # The sentinel is an artificial token that never reaches the model —
        # split_system_for_cache removes it and the two halves reconstruct this
        # string byte-for-byte. Storing the sentinel-free form is storing what
        # was actually sent.
        system_prompt=system.replace(CACHE_SPLIT_SENTINEL, ""),
        bridge_matched=bridge_term,
        tokens=sink,
        error=error,
    )


async def generate_all(
    samples: list[Sample],
    *,
    concurrency: int = 4,
    progress=None,
    arm: str = "baseline",
) -> list[Completion]:
    """Every sample on both plans. 110 samples -> 220 completions.

    Bounded concurrency rather than a full gather: 220 simultaneous streams
    invites 429s, and a rate-limited sample would be recorded as an error rather
    than retried, which would silently shrink the denominator of every rate in
    the summary.

    GENERATION ORDER IS PERSONA-MAJOR; ROW ORDER IS BY sample_id. These are two
    different things and only the second one is part of the measurement.

    The cacheable prefix is the part of the system prompt before the sentinel,
    which is static per persona: 11 distinct prefixes, ~2,886 tokens each, one
    for every 10 samples. Sonnet 4.6 can cache that (its minimum cacheable prefix
    is below it); Haiku 4.5 cannot, because its 4,096-token minimum sits above
    it, and no ordering changes that. Grouping a persona's samples together keeps
    the 10 Sonnet calls that share a prefix inside the 5-minute TTL instead of
    spreading them across the whole run, which roughly halves the Sonnet bill.

    It changes nothing about what is measured: the same 220 prompts are sent, the
    cached prefix is byte-identical to the uncached one (split_system_for_cache
    only adds a breakpoint), and the returned list is sorted by (sample_id, plan)
    so every downstream file is ordered independently of how generation was
    scheduled.
    """
    sem = asyncio.Semaphore(concurrency)
    jobs = sorted(
        ((s, plan, model) for s in samples for _, plan, model in ARMS_BY_PLAN),
        key=lambda j: (j[0].persona_slug, j[1], j[0].problem_id),
    )
    done = 0
    results: list[Completion] = [None] * len(jobs)  # type: ignore[list-item]

    async def one(i: int, sample: Sample, plan: str, model: str):
        nonlocal done
        async with sem:
            results[i] = await generate(sample, plan, model, arm)
            done += 1
            if progress:
                progress(done, len(jobs), results[i])

    await asyncio.gather(*(one(i, *job) for i, job in enumerate(jobs)))
    return sorted(results, key=lambda c: (c.sample_id, c.plan))
