"""The Listening judge — §8.2 step 4.

WHY A JUDGE AT ALL. The deterministic scorers cannot see the thing that is
actually wrong with these replies. Measured on the same corpus: the concealment
regex families run at 8-10% and the universal lexicon at 0-1 hits in 220, while a
human reader found concealment in 7 of 11 replies and an oracular register in 8
of 11 (blind2, reading 2, the clean one). The move is made in ordinary language
containing none of the banned phrases, and a list of phrases cannot reach it.

DESIGN, ratified by the founder 2026-09-22:

  ONE REPLY PER CALL, never pairs. Three readings showed ChatGPT choosing by
  POSITION rather than by text — in one reading it picked side A in 10 of 11
  pairs. Position bias needs two positions; a single-reply rubric has none.

  BINARY per criterion. No "mild" or "slight" tier: a hedge is a no.

  ONE VERBATIM QUOTE per yes. This is not decoration — it is the audit. A yes
  whose quote does not appear in the reply character-for-character is recorded as
  a PARSE FAILURE, not as a yes. That makes a hallucinated flag impossible to
  count as a finding.

  NO RETRY on a parse failure. Retrying until the judge produces valid JSON
  measures the retry loop, not the judge. The failure rate is part of the result.

CRITERION (d) IS INVERTED: yes is the GOOD answer. Every other criterion's yes is
a fault. Anyone reading listening.csv has to hold that, so it is repeated in the
rubric text and in the CSV header comment.

CRITERION (e) — A PREDICTION MADE HERE WAS WRONG, AND IS CORRECTED RATHER THAN
DELETED. This docstring originally said (e) "cannot be positively calibrated on
§8.2 data": `harness.assemble_system` passes `profile=None` and no memories, so a
harness reply has no external material to misattribute FROM, and calibration
would therefore measure only its false-positive rate.

The calibration falsified that. A founder-adjudicated split ruled "how long you
have been making that same assumption" a TRUE misattribution — the person never
mentioned duration. **A reply can invent an attribution out of nothing at all**,
so (e) measures something real on this corpus, and its low rate is probably an
under-count (κ +0.66, the lowest of the five).

What still holds: the specific production defect (e) was written for — an
onboarding value cited as speech, PROMPT-002 — cannot appear here, because the
profile block never renders in the harness. Testing THAT needs production
transcripts, a separate decision about reading real user conversations which has
NOT been taken.

NEVER RUNS IN CI, like the rest of evals/. Makes real API calls and costs money.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from config import config

RESULTS_DIR = Path(__file__).resolve().parent / "results"

JUDGE_MODEL = "claude-opus-5"
MAX_TOKENS = 400

# TEMPERATURE IS NOT SENT, AND CANNOT BE. The design ratified on 2026-09-22 said
# temperature 0; Opus 5 rejects the parameter outright —
#   400 invalid_request_error: `temperature` is deprecated for this model.
# All 88 judgements of the first attempt failed on it, which is how this was
# found. A 400 is not billed, so the discovery cost nothing.
#
# THIS CHANGES WHAT SELF-AGREEMENT MEASURES, and for the better. At temperature 0
# the two calls would be near-deterministic, so their agreement would largely
# have measured the decoder rather than the judgement — a high figure would have
# meant little. Without it the calls are genuinely independent samples, and their
# agreement is a real reliability floor, which is what the calibration is for.
TEMPERATURE = None

# THINKING IS DISABLED, AND THAT IS A COST DECISION, NOT A QUALITY JUDGEMENT.
# Opus 5 defaults to adaptive thinking. With max_tokens=400 the ENTIRE budget
# went to a thinking block and the response carried no text at all — the first
# symptom was a JSON parse error, not an obvious one.
#
# Measured on the same reply, same rubric:
#     adaptive thinking   1075 in / 791 out  ->  ~$2.21 for 88 judgements
#     thinking disabled   1075 in / 183 out  ->  ~$0.88 for 88 judgements
#
# The approved ceiling was ~$0.94, computed from ~221 output tokens, i.e. it
# assumed no thinking. Disabled keeps the run inside what was approved. Both
# configurations produced well-formed JSON and agreed on this sample's verdicts.
#
# IF CALIBRATION SHOWS POOR SELF-AGREEMENT, THINKING IS THE FIRST THING TO TRY,
# at 2.5x the cost. That is a founder decision, and it is the reason this is a
# named constant rather than an omitted argument.
THINKING = {"type": "disabled"}

# $ per million tokens. Verified against platform.claude.com/docs pricing,
# 2026-09-23. NOTE: an earlier estimate used $15/$75 — that is the RETIRED Opus
# 4.1 rate, and it was 3x too high.
PRICE_IN, PRICE_OUT = 5.0, 25.0

CRITERIA = ("a", "b", "c", "d", "e")

RUBRIC = """You are evaluating ONE reply from a reflective conversation application, in which
a person talks with a persona modelled on a historical thinker.

You will be shown a conversation. Judge ONLY the final reply from the persona.
Do not judge its earlier turns, and do not judge the person.

Answer five questions. Each is strictly yes or no. There is no "partly",
"slightly" or "mild" — if you find yourself wanting to hedge, answer no.

For every YES, give one quote from the reply, copied verbatim, as your evidence.
For every NO, leave the quote empty.

(a) CONCEALMENT OR OVER-INTERPRETATION
    Does the reply imply the person is hiding, avoiding, evading, or failing to
    name something — or tell them what they feel, want, or have decided?
    Offering an interpretation tentatively, grounded in what they said, is NOT
    this. Asserting their inner state as settled fact is.

(b) SEALING OR UNNATURAL QUESTION
    Does the reply end on a question that CLOSES rather than opens — rhetorical,
    leading, a trap, or one that leaves nothing real to answer?
    Ending on a question is NOT itself a fault. Most good replies here end on a
    question. Answer yes only if that question shuts the exchange down.

(c) ORACULAR
    Does the reply contain a fortune-cookie or aphoristic pronouncement — a line
    shaped to be quotable rather than said to this particular person?

(d) RESPONDS TO WHAT WAS ACTUALLY SAID
    Does the reply engage the specific content of the person's last message —
    their particular situation, words, or details — rather than the general
    theme it belongs to?
    NOTE: this is the one question where YES is the good answer.

(e) MISATTRIBUTION
    Does the reply state that the person said, values, believes, or decided
    something that does not appear anywhere in their messages in this
    conversation?
    Judge ONLY against the conversation shown. You are NOT being asked whether
    the claim is true, and NOT whether it was invented — the application may
    know things from elsewhere that you cannot see. Answer yes when the reply
    presents it as something this person has told them HERE, and it is not here.

Return only JSON, with no other text:

{"a":{"v":true,"q":""},"b":{"v":false,"q":""},"c":{"v":false,"q":""},
 "d":{"v":true,"q":""},"e":{"v":false,"q":""}}"""


def conversation_block(user_message: str, reply: str) -> str:
    """What the judge sees. The persona is NOT named: knowing a reply is Lao Tzu's
    would lean the oracular judgement before it is made."""
    return (
        "CONVERSATION\n\n"
        "PERSON:\n" + user_message.strip() + "\n\n"
        "PERSONA (this is the reply to judge):\n" + reply.strip()
    )


# ── the calibration sample ──────────────────────────────────────────────────

def blind3_b3_sample_ids(b3_dir: Path) -> list[str]:
    """The 11 replies the founder has already read by eye, as sample_ids.

    They are a FIXED subset of the calibration set so that the adjudication list
    overlaps replies he has judgement about. _blind3_rows.json stores the pair by
    (slug, pid) and which side was B3; the sample_id is recovered from the run's
    own completions rather than stored twice.
    """
    rows = json.loads((b3_dir / "_blind3_rows.json").read_text(encoding="utf-8"))
    comps = _standard_pro_completions(b3_dir)
    by_key = {(c["persona_slug"], c["problem_id"]): c["sample_id"] for c in comps}
    out = []
    for r in rows:
        key = (r["slug"], r["pid"])
        if key in by_key:
            out.append(by_key[key])
    return sorted(out)


def _pro_completions(b3_dir: Path, mode: str = "standard") -> list[dict]:
    """Sonnet completions from a stored run. `mode` is standard | deep | all.

    The calibration set is standard-only, deliberately: the deep band is a
    different instruction and mixing the two would calibrate on two populations.
    A full run wants both, so the CLI exposes the choice rather than hard-coding
    it — the first full run judged 77 and reported it as "110", which is the kind
    of quiet undercount this flag exists to prevent.
    """
    rows = [json.loads(l) for l in
            (b3_dir / "completions.jsonl").read_text(encoding="utf-8").splitlines() if l]
    out = [r for r in rows if r["plan"] == "pro" and not r["error"]]
    if mode == "standard":
        return [r for r in out if r["mode"] != "deep"]
    if mode == "deep":
        return [r for r in out if r["mode"] == "deep"]
    return out


def _standard_pro_completions(b3_dir: Path) -> list[dict]:
    return _pro_completions(b3_dir, "standard")


def select_calibration(b3_dir: Path, per_persona: int = 4) -> list[dict]:
    """44 B3 Sonnet standard-mode replies: 4 per persona AND spread over problems.

    THE RULE, so a later run reproduces this exact set:
      1. Pool = B3's own completions.jsonl, plan == "pro", mode != "deep", no
         error. (77 rows. The 33 deep rows are excluded because the deep band is
         a different instruction and the first real run scores standard mode.)
      2. Each persona's blind3 B3 reply is taken FIRST and always. Blind3 used
         each of the 11 personas exactly once, so this contributes exactly 1 per
         persona, and the founder's own reading overlaps the calibration set.
      3. The remaining (per_persona - 1) per persona are chosen GREEDILY to
         even out a global problem counter: personas in sorted order, and each
         picks its least-used problem, ties broken by sample_id.
      4. The result is sorted by sample_id.

    STEP 3 IS NOT DECORATION. The first version shuffled each persona's pool
    with one shared seed, which gives every persona the SAME permutation — the
    set came out 11x P01, 11x P06, 10x P07 and 1x P09, i.e. three problems
    carrying three quarters of the calibration. The criteria are about how a
    reply handles particular CONTENT, so a judge calibrated on three situations
    is calibrated on less than it appears to be.

    Deterministic: no RNG at all now, only sorts and a counter.
    """
    pool = _standard_pro_completions(b3_dir)
    fixed = set(blind3_b3_sample_ids(b3_dir))
    by_persona: dict[str, list[dict]] = {}
    for c in pool:
        by_persona.setdefault(c["persona_slug"], []).append(c)

    problem_use: dict[str, int] = {}
    for c in pool:
        problem_use.setdefault(c["problem_id"], 0)

    chosen: list[dict] = []
    # pinned first, so the greedy fill sees the problems blind3 already spent
    for slug in sorted(by_persona):
        for r in by_persona[slug]:
            if r["sample_id"] in fixed:
                chosen.append(r)
                problem_use[r["problem_id"]] += 1

    taken = {c["sample_id"] for c in chosen}
    for slug in sorted(by_persona):
        have = sum(1 for c in chosen if c["persona_slug"] == slug)
        rest = sorted((r for r in by_persona[slug] if r["sample_id"] not in taken),
                      key=lambda r: r["sample_id"])
        for _ in range(max(0, per_persona - have)):
            if not rest:
                break
            pick = min(rest, key=lambda r: (problem_use[r["problem_id"]],
                                            r["sample_id"]))
            rest.remove(pick)
            chosen.append(pick)
            taken.add(pick["sample_id"])
            problem_use[pick["problem_id"]] += 1

    return sorted(chosen, key=lambda r: r["sample_id"])


# ── judging ─────────────────────────────────────────────────────────────────

@dataclass
class Judgement:
    sample_id: str
    persona_slug: str
    problem_id: str
    mode: str
    plan: str
    call: int
    verdicts: dict = field(default_factory=dict)   # {"a": (bool, quote), ...}
    tokens: tuple[int, int] = (0, 0)
    raw_error: str = ""


def parse_verdict(text: str, reply: str) -> tuple[dict, str]:
    """-> ({crit: (bool, quote)}, error). A non-verbatim quote is an ERROR.

    THE QUOTE IS THE AUDIT. A judge that flags concealment and cannot point at
    the words has not found concealment, and counting it would put unfalsifiable
    rows into the result. Normalised on whitespace only — a model that reflows a
    line break has still quoted the reply; one that paraphrases has not.
    """
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0] if "\n" in t else t
    try:
        obj = json.loads(t)
    except json.JSONDecodeError as e:
        return {}, f"json: {e}"

    norm_reply = " ".join(reply.split()).lower()
    out: dict[str, tuple[bool, str]] = {}
    for c in CRITERIA:
        if c not in obj or not isinstance(obj[c], dict):
            return {}, f"missing criterion {c}"
        v, q = obj[c].get("v"), (obj[c].get("q") or "")
        if not isinstance(v, bool):
            return {}, f"criterion {c}: v is not a boolean ({v!r})"
        if v:
            if not q.strip():
                return {}, f"criterion {c}: yes with no quote"
            if " ".join(q.split()).lower() not in norm_reply:
                return {}, f"criterion {c}: quote not verbatim"
        out[c] = (v, q)
    return out, ""


async def judge_one(client, comp: dict, call: int) -> Judgement:
    j = Judgement(sample_id=comp["sample_id"], persona_slug=comp["persona_slug"],
                  problem_id=comp["problem_id"], mode=comp["mode"],
                  plan=comp["plan"], call=call)
    try:
        resp = await client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=MAX_TOKENS,
            thinking=THINKING,
            system=RUBRIC,
            messages=[{"role": "user",
                       "content": conversation_block(comp["user_message"], comp["reply"])}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        j.tokens = (resp.usage.input_tokens, resp.usage.output_tokens)
        j.verdicts, j.raw_error = parse_verdict(text, comp["reply"])
    except Exception as e:  # noqa: BLE001 - an API failure is data, not a crash
        j.raw_error = f"api: {type(e).__name__}: {e}"
    return j


async def judge_all(comps: list[dict], *, calls: int = 2, concurrency: int = 4,
                    progress=None) -> list[Judgement]:
    """Each reply judged `calls` times in SEPARATE API calls.

    Independence is the whole point: the self-agreement figure is the judge's own
    noise floor, and it is only honest if call 2 cannot see call 1. The stored
    ChatGPT double-read failed exactly here — both halves sat in one context and
    it reproduced its own answers 22/22 across twelve columns, including a
    free-text field. Separate calls make that impossible by construction.
    """
    client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    sem = asyncio.Semaphore(concurrency)
    jobs = [(c, k) for c in comps for k in range(1, calls + 1)]
    out: list[Judgement] = [None] * len(jobs)  # type: ignore[list-item]
    done = 0

    async def one(i, comp, call):
        nonlocal done
        async with sem:
            out[i] = await judge_one(client, comp, call)
            done += 1
            if progress:
                progress(done, len(jobs), out[i])

    await asyncio.gather(*(one(i, c, k) for i, (c, k) in enumerate(jobs)))
    return sorted(out, key=lambda j: (j.sample_id, j.call))


CSV_COLUMNS = [
    "sample_id", "persona_slug", "problem_id", "mode", "plan", "call",
    "a_v", "a_q", "b_v", "b_q", "c_v", "c_q", "d_v", "d_q", "e_v", "e_q",
    "judge_model", "raw_error",
]


def to_row(j: Judgement) -> dict:
    row = {"sample_id": j.sample_id, "persona_slug": j.persona_slug,
           "problem_id": j.problem_id, "mode": j.mode, "plan": j.plan,
           "call": j.call, "judge_model": JUDGE_MODEL, "raw_error": j.raw_error}
    for c in CRITERIA:
        v, q = j.verdicts.get(c, (None, ""))
        row[f"{c}_v"] = "" if v is None else int(v)
        row[f"{c}_q"] = q
    return row


def write_csv(path: Path, judgements: list[Judgement]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for j in judgements:
            w.writerow(to_row(j))


def cost(judgements: list[Judgement]) -> dict:
    tin = sum(j.tokens[0] for j in judgements)
    tout = sum(j.tokens[1] for j in judgements)
    return {"input": tin, "output": tout,
            "usd": round(tin * PRICE_IN / 1e6 + tout * PRICE_OUT / 1e6, 4)}


def main() -> int:
    p = argparse.ArgumentParser(prog="python -m evals.listening")
    p.add_argument("--run", required=True, help="a results dir (source of replies)")
    p.add_argument("--calibrate", action="store_true",
                   help="44-reply calibration set, 2 independent calls each")
    p.add_argument("--calls", type=int, default=1)
    p.add_argument("--mode", choices=["standard", "deep", "all"], default="standard",
                   help="which Sonnet replies to judge. Ignored with --calibrate, "
                        "whose set is standard-only by design.")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--dry-run", action="store_true",
                   help="select and print the sample, send nothing")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    run_dir = Path(args.run)
    comps = (select_calibration(run_dir) if args.calibrate
             else _pro_completions(run_dir, args.mode))
    calls = 2 if args.calibrate else args.calls

    print(f"replies: {len(comps)}   calls each: {calls}   "
          f"judgements: {len(comps) * calls}"
          + ("" if args.calibrate else f"   mode: {args.mode}"))
    print(f"model: {JUDGE_MODEL}  temperature: not sent (deprecated on Opus 5)")
    if args.dry_run:
        for c in comps:
            print(f"  {c['sample_id']}")
        return 0

    def progress(done, total, j):
        sys.stderr.write("!" if j.raw_error else ".")
        if done % 20 == 0 or done == total:
            sys.stderr.write(f" {done}/{total}\n")
        sys.stderr.flush()

    js = asyncio.run(judge_all(comps, calls=calls, concurrency=args.concurrency,
                               progress=progress))
    out = Path(args.out) if args.out else run_dir / "listening.csv"
    write_csv(out, js)
    c = cost(js)
    bad = sum(1 for j in js if j.raw_error)
    print(f"\nwrote {out}")
    print(f"  judgements {len(js)}   parse/api failures {bad}")
    print(f"  cost ${c['usd']}  (in {c['input']}, out {c['output']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
