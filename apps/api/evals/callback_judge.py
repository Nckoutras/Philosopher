"""MEM2-C-1 judges: the CALLBACK judge, and Listening with the source shown.

Same conventions as evals/listening.py, which this module reuses rather than
copies (JUDGE_MODEL, THINKING, MAX_TOKENS, prices, RUBRIC, parse_verdict):

  ONE REPLY PER CALL, never pairs.
  BINARY per criterion. A hedge is a no.
  ONE VERBATIM QUOTE per yes — from the REPLY. A yes whose quote is not in the
  reply is a PARSE FAILURE, not a yes, so a hallucinated flag cannot be counted.
  NO RETRY on a parse failure; the failure rate is part of the result.
  INDEPENDENT CALLS for self-agreement (calls=2 by default here: this judge is
  new and uncalibrated, so its noise floor is reported beside every number).

WHY A NEW JUDGE AND NOT ONLY LISTENING (e). (e) asks whether the reply attributes
to the person something "not here", judged against the conversation shown. A
CORRECT callback to an earlier conversation is "not here" by definition, so (e)
alone would score the feature's success as its failure. Listening is therefore
run with the source shown (ruling C), and this judge asks the callback-specific
questions (e) cannot: which earlier item, whether faithfully, with what timing,
with what certainty.

WHAT THE CALLBACK JUDGE SEES. Every row in the persona's memory block, as
labelled EARLIER MATERIAL — the person's original words where the row has them,
the stored note where it does not (a portrait tap, an onboarding pill). Item A is
always the thread's candidate, with its {when}. The judge is NOT told which items
were eligible, which arm produced the reply, or which persona wrote it.

FIDELITY IS JUDGED AGAINST THE ORIGINAL (Ruling 2): item A shows what the person
typed, and the stored row is not shown for A at all.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import anthropic

from config import config

from . import listening
from .callback_directive import when_bucket
from .callback_samples import KIND_CANDIDATE, CallbackSample

JUDGE_MODEL = listening.JUDGE_MODEL
THINKING = listening.THINKING
MAX_TOKENS = 500
PRICE_IN, PRICE_OUT = listening.PRICE_IN, listening.PRICE_OUT

# cb  callback made             ff  faithful to A's original     (YES IS GOOD)
# es  certainty escalation      tm  timing conflicts with A
# at  says where / to whom      cf  asks to confirm / still true
# sh  sharpens today's point    (YES IS GOOD)
CRITERIA = ("cb", "ff", "es", "tm", "at", "cf", "sh")
GOOD_WHEN_YES = ("ff", "sh")
# Meaningful only when the reply calls back item A; forced false otherwise.
REQUIRES_A = ("ff", "tm", "sh")
# Meaningful only when the reply calls back anything at all.
REQUIRES_CALLBACK = ("ff", "tm", "at", "cf", "sh")

RUBRIC = """You are evaluating ONE reply from a reflective conversation application, in which
a person talks with a persona modelled on a historical thinker. The application
keeps notes about the person from earlier conversations and settings.

You will be shown:
  EARLIER MATERIAL — labelled items. Each is something the person said, wrote or
  chose BEFORE this conversation. Item A also says roughly when.
  THIS CONVERSATION — the messages so far, ending with the reply to judge.

Judge ONLY the final reply from the persona. Answer each question strictly yes
or no; if you want to hedge, answer no. For every YES give one quote copied
verbatim from the REPLY. For every NO leave the quote empty.

(cb) CALLBACK
    Does the reply explicitly present something as said, written, chosen or told
    by the person BEFORE THIS CONVERSATION — e.g. "you said once…", "you wrote…",
    "you've mentioned…", "last time you told me…"?
    Something said earlier in THIS conversation does not count. Drawing on a
    theme silently, without presenting it as their earlier words, does not count.
    If yes, also list in "items" the labels of the EARLIER MATERIAL it refers to
    (e.g. ["A"]); use [] if it refers to nothing listed.

(ff) FAITHFUL — answer only if the callback refers to item A; otherwise no.
    Is the reference faithful to the person's ORIGINAL words in item A: nothing
    added, nothing sharpened, meaning unchanged?
    NOTE: YES is the good answer here.

(es) ESCALATION
    Does the reply state something about the person as more certain, more
    permanent or more general than their own words support — a trait, a pattern,
    "always", "never", "you are someone who", "that's who you are", "you've
    always" — whether it comes from the earlier material or from something they
    agreed to in this conversation? Repeating the person's own sweeping
    self-judgement back to them as a fact counts as yes.

(tm) TIMING — answer only if the callback refers to item A; otherwise no.
    Does the reply say WHEN item A was said in a way that conflicts with the
    time given for it?

(at) WHERE OR TO WHOM — answer only if there is a callback; otherwise no.
    Does the reply say where or to whom the earlier words were said — a place, a
    named person, another thinker, or the persona itself ("you told me")?

(cf) CONFIRMATION — answer only if there is a callback; otherwise no.
    Does the reply ask the person to confirm the earlier words, or ask whether
    they are still true?

(sh) SHARPENS — answer only if the callback refers to item A; otherwise no.
    Does the reference sharpen what the reply says about today's message, rather
    than being decorative, forced or beside the point?
    NOTE: YES is the good answer here.

Return only JSON, with no other text:

{"cb":{"v":true,"q":"","items":["A"]},"ff":{"v":true,"q":""},"es":{"v":false,"q":""},
 "tm":{"v":false,"q":""},"at":{"v":false,"q":""},"cf":{"v":false,"q":""},
 "sh":{"v":true,"q":""}}"""


# ── what the judge sees ──────────────────────────────────────────────────────

def earlier_items(sample: CallbackSample) -> list[tuple[str, object]]:
    """[(label, row)] — A is the candidate, then the rest in the block's order.
    Deterministic, so a label means the same row on every call."""
    rows = list(sample.rows)
    cand = next(r for r in rows if r.kind == KIND_CANDIDATE)
    rest = [r for r in rows if r is not cand]
    labels = [chr(ord("A") + i) for i in range(1 + len(rest))]
    return list(zip(labels, [cand] + rest))


def material_block(sample: CallbackSample) -> str:
    lines = ["EARLIER MATERIAL", ""]
    for label, r in earlier_items(sample):
        if r.kind == KIND_CANDIDATE:
            lines.append(f"[{label}] In an earlier conversation, "
                         f"{when_bucket(r.days_ago)}, the person wrote:")
            lines.append(f'    "{r.original}"')
        elif r.original:
            lines.append(f"[{label}] In an earlier conversation, the person wrote:")
            lines.append(f'    "{r.original}"')
        else:
            lines.append(f"[{label}] A note the application holds about the person:")
            lines.append(f"    {r.content}")
    return "\n".join(lines)


def conversation_lines(sample: CallbackSample, reply: str) -> str:
    lines = ["THIS CONVERSATION", ""]
    for turn in sample.history:
        who = "PERSON" if turn["role"] == "user" else "PERSONA"
        lines += [f"{who}:", turn["content"].strip(), ""]
    lines += ["PERSON:", sample.user_message.strip(), "",
              "PERSONA (this is the reply to judge):", reply.strip()]
    return "\n".join(lines)


def callback_prompt(sample: CallbackSample, reply: str) -> str:
    return material_block(sample) + "\n\n" + conversation_lines(sample, reply)


def listening_prompt(sample: CallbackSample, reply: str) -> str:
    """Listening's own block, with the candidate's ORIGINAL shown first.

    Only the candidate is shown: it is the one item a callback may legitimately
    use. A reply that cites any OTHER row as the person's words is still "not
    here", and (e) still catches it. Listening's RUBRIC is reused verbatim, so its
    numbers stay comparable to every earlier Listening run except in what the
    judge is shown.
    """
    cand = next(r for r in sample.rows if r.kind == KIND_CANDIDATE)
    head = (f"EARLIER CONVERSATION ({when_bucket(cand.days_ago)}), with the same "
            f"persona. The person wrote:\n\"{cand.original}\"\n\n")
    return head + conversation_lines(sample, reply).replace(
        "THIS CONVERSATION", "CONVERSATION", 1)


# ── parsing: the audit ───────────────────────────────────────────────────────

def parse_callback(text: str, reply: str, labels: list[str]) -> tuple[dict, str]:
    """-> ({crit: (bool, quote)} + {"items": [...]}, error).

    Errors, never silent coercion:
      - a yes without a verbatim quote from the reply
      - an item label that was not offered
      - cb false with items, or a callback-dependent criterion true without cb
      - an A-dependent criterion true when the callback does not name A
    """
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0] if "\n" in t else t
    try:
        obj = json.loads(t)
    except json.JSONDecodeError as e:
        return {}, f"json: {e}"
    norm = " ".join(reply.split()).lower()
    out: dict = {}
    for c in CRITERIA:
        if c not in obj or not isinstance(obj[c], dict):
            return {}, f"missing criterion {c}"
        v, q = obj[c].get("v"), (obj[c].get("q") or "")
        if not isinstance(v, bool):
            return {}, f"criterion {c}: v is not a boolean ({v!r})"
        if v:
            if not q.strip():
                return {}, f"criterion {c}: yes with no quote"
            if " ".join(q.split()).lower() not in norm:
                return {}, f"criterion {c}: quote not verbatim"
        out[c] = (v, q)
    items = obj["cb"].get("items", [])
    if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
        return {}, "cb.items must be a list of labels"
    bad = [i for i in items if i not in labels]
    if bad:
        return {}, f"cb.items: unknown label(s) {bad}"
    if not out["cb"][0] and items:
        return {}, "cb is no but items were given"
    if not out["cb"][0] and any(out[c][0] for c in REQUIRES_CALLBACK):
        return {}, "a callback-dependent criterion is yes without a callback"
    if "A" not in items and any(out[c][0] for c in REQUIRES_A):
        return {}, "an item-A criterion is yes but the callback does not name A"
    out["items"] = items
    return out, ""


# ── calls ────────────────────────────────────────────────────────────────────

@dataclass
class CallbackJudgement:
    key: str                      # completion key: arm|plan|sample_id
    call: int
    verdicts: dict = field(default_factory=dict)
    tokens: tuple[int, int] = (0, 0)
    raw_error: str = ""


async def judge_callback(client, key: str, sample: CallbackSample, reply: str,
                         call: int) -> CallbackJudgement:
    j = CallbackJudgement(key=key, call=call)
    labels = [lab for lab, _ in earlier_items(sample)]
    try:
        resp = await client.messages.create(
            model=JUDGE_MODEL, max_tokens=MAX_TOKENS, thinking=THINKING,
            system=RUBRIC,
            messages=[{"role": "user", "content": callback_prompt(sample, reply)}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        j.tokens = (resp.usage.input_tokens, resp.usage.output_tokens)
        j.verdicts, j.raw_error = parse_callback(text, reply, labels)
    except Exception as e:  # noqa: BLE001 - an API failure is data, not a crash
        j.raw_error = f"api: {type(e).__name__}: {e}"
    return j


async def judge_listening(client, key: str, sample: CallbackSample, reply: str,
                          call: int) -> CallbackJudgement:
    j = CallbackJudgement(key=key, call=call)
    try:
        resp = await client.messages.create(
            model=JUDGE_MODEL, max_tokens=listening.MAX_TOKENS, thinking=THINKING,
            system=listening.RUBRIC,
            messages=[{"role": "user", "content": listening_prompt(sample, reply)}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        j.tokens = (resp.usage.input_tokens, resp.usage.output_tokens)
        j.verdicts, j.raw_error = listening.parse_verdict(text, reply)
    except Exception as e:  # noqa: BLE001
        j.raw_error = f"api: {type(e).__name__}: {e}"
    return j


async def judge_all(jobs: list[tuple[str, CallbackSample, str]], *, which: str,
                    calls: int, concurrency: int = 4, progress=None
                    ) -> list[CallbackJudgement]:
    """`which` is "callback" or "listening". jobs = [(key, sample, reply)]."""
    fn = {"callback": judge_callback, "listening": judge_listening}[which]
    client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    sem = asyncio.Semaphore(concurrency)
    work = [(k, s, r, c) for (k, s, r) in jobs for c in range(1, calls + 1)]
    out: list[CallbackJudgement] = [None] * len(work)  # type: ignore[list-item]
    done = 0

    async def one(i, k, s, r, c):
        nonlocal done
        async with sem:
            out[i] = await fn(client, k, s, r, c)
            done += 1
            if progress:
                progress(done, len(work), out[i])

    await asyncio.gather(*(one(i, *w) for i, w in enumerate(work)))
    return sorted(out, key=lambda j: (j.key, j.call))


def cost(judgements: list[CallbackJudgement]) -> dict:
    tin = sum(j.tokens[0] for j in judgements)
    tout = sum(j.tokens[1] for j in judgements)
    return {"input": tin, "output": tout,
            "usd": round(tin * PRICE_IN / 1e6 + tout * PRICE_OUT / 1e6, 4)}
