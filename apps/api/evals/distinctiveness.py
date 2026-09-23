"""The Distinctiveness judge — §8.2 test 1, BUG-009.

THE QUESTION. BUG-009 says the eleven personas "collapse toward one generic
coaching template", making them "materially interchangeable". Its own acceptance
test is `blind reviewers identify the intended thinker materially above chance`,
and the bug's evidence line admits `no formal blind-test sample has yet been run`.
This module is that test: a judge sees ONE reply with the persona name removed and
names the thinker from the eleven.

WHY THE PRIOR READING DOES NOT ALREADY ANSWER IT. There IS a stored
persona-identification reading — the `guess_thinker` column of
`results/2026-09-22T09-39_baseline/chatgpt_review_RESULT.csv`, scored against its
own key on 2026-09-23:

    Freud 4/4, Jung 4/4                                          (100%)
    Orwell, Epictetus, Machiavelli, Socrates 2/4                  (50%)
    Lao Tzu, Marcus, Musashi, Wilde, Beauvoir 0/4                  (0%)
    overall 16/44 = 36.4%, against 9.1% chance

That is the source of the arm_b.py:29 docstring line, and of the framing that five
voices are missing. **Two confounds disqualify it, and both are failure modes this
directory already knows about.**

  1. ALL 44 SAT IN ONE CONTEXT. Each reply appeared twice under different ids, and
     the reading reproduced its own guess 22/22 — the same non-independence
     `listening.judge_all` was built to prevent, here confirmed for `guess_thinker`
     specifically. 22/22 is recall, not reliability.

  2. THE MARGINAL WAS PERFECTLY UNIFORM. Across 44 guesses it named each of the
     eleven personas EXACTLY four times, matching the truth distribution exactly.
     That is the signature of a forced one-to-one assignment over a set it could
     see whole, which makes per-reply guesses non-independent: a correct Freud
     costs accuracy somewhere else by construction.

ONE REPLY PER CALL, SEPARATE CALLS, NO SIGHT OF THE SET. Same design rule as the
listening judge and for a sharper reason — there, independence protected a
reliability figure; here it protects the measurement itself.

WHAT n ACTUALLY IS, because the headline number invites overreading. The
independent unit is the REPLY: **10 per persona**. The second call measures judge
noise; it does NOT double n. Against 1/11 chance, pre-registered before any data
existed (see `THRESHOLD_RECOGNISED`):

    >= 4/10   recognised            p < 0.01
       3/10   not established       p ~ 0.055
    <= 2/10   says nothing          P(0/10 | no signal) = 0.386

**A persona at 0/10 is NOT shown to be absent.** A voiceless persona scores 0/10
about 39% of the time. This run can confirm a voice exists; it cannot prove one
does not. The same arithmetic is why the prior 0/4 results carried nothing:
P(0/4 | no signal) = 0.683, the single most likely outcome.

ABSENT vs COLLAPSED — the question the matrix exists for — is read as a SHAPE, not
per cell. Row sums are 20, so a single cell runs 0-3 and no cell is a finding. What
is readable is whether a persona's wrong guesses CONCENTRATE on one name (collapse
into a shared voice) or SCATTER across ten (no voice at all), plus the guess
marginals: a name absorbing far more than 9.1% of all guesses IS the shared voice.

FORCED CHOICE, NO "UNSURE". Chance is then exactly 1/11 and computable; an
abstention rate is not. And `thinker` is emitted BEFORE `quote` in the required
JSON: with thinking disabled, generation runs left-to-right, so the name is
committed before the justification is written and the quote cannot retrofit the
guess.

THE QUOTE IS THE AUDIT, as in listening.py — a non-verbatim quote is a PARSE
FAILURE, not a guess — and here it is also the most useful artefact of the run. It
says WHAT cued each identification: a persona recognised from its lexicon is a
different finding from one recognised from its reasoning.

ACKNOWLEDGED DUPLICATION, named rather than buried. `judge_all` below repeats the
semaphore/gather/progress shape of `listening.judge_all` (~18 lines). Sharing it
would mean parameterising the judge callable in a module that had just produced
founder-approved results, on the eve of a paid run — P-02, one logical change per
PR. The right fix is a shared `evals/_judge_runner.py` when a third judge appears;
two is not yet a pattern.

NEVER RUNS IN CI, like the rest of evals/. Makes real API calls and costs money.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from config import config
from personas import PERSONA_REGISTRY

from evals.listening import (
    JUDGE_MODEL,
    PRICE_IN,
    PRICE_OUT,
    THINKING,
    _pro_completions,
    conversation_block,
)

MAX_TOKENS = 300

# The founder-approved ceiling for this run, 2026-09-23. Enforced as a MECHANISM,
# not a hope: `judge_all` checks accumulated spend before dispatching each call and
# refuses the rest once the ceiling is passed. A run that would overspend comes back
# short and says so, rather than coming back expensive.
COST_CEILING_USD = 1.60

# Pre-registered 2026-09-23, BEFORE any judgement existed. 10 replies per persona,
# chance 1/11: P(X >= 4) = 0.0092, P(X >= 3) = 0.0555. Writing it here rather than
# choosing it from the results is the whole point.
THRESHOLD_RECOGNISED = 4

# ── the approved prompt ─────────────────────────────────────────────────────
#
# FOUNDER-APPROVED COPY, 2026-09-23, reproduced verbatim. Do not reword it, reorder
# the names, or fix its punctuation. If it needs to change it changes by a founder
# ruling, and any stored result becomes a result about the OLD prompt.
#
# The list is ALPHABETICAL, not `PERSONA_REGISTRY` order. A fixed order is what
# makes an exactly-approved prompt possible; the position bias it could carry is
# caught after the fact by the guess marginals, which is exactly the check the
# prior reading failed (its flat 4-4-4 marginal).
RUBRIC = """You are shown one exchange from a reflective conversation application. A person
wrote to a persona modelled on a historical thinker, and the thinker replied.

Name the thinker. Choose exactly one from this list:

  Carl Jung
  Epictetus
  George Orwell
  Lao Tzu
  Marcus Aurelius
  Miyamoto Musashi
  Niccolò Machiavelli
  Oscar Wilde
  Sigmund Freud
  Simone de Beauvoir
  Socrates

You must choose one. There is no "unsure", and no name outside this list — if
nothing fits well, choose the closest.

Judge the REPLY only. The person's message is the same for every thinker in this
study and tells you nothing about which one you are reading.

Then give ONE quote from the reply, copied verbatim, that most made you choose
that name — the single passage you would find hardest to attribute to any of the
other ten.

Return only JSON, with no other text:

{"thinker":"NAME EXACTLY AS WRITTEN IN THE LIST ABOVE",
 "quote":"a passage copied word-for-word from the reply"}"""


def _fold(name: str) -> str:
    """Accent- and case-insensitive key for a display name.

    `Niccolò Machiavelli` is in the prompt with its accent, and a judge that
    answers `Niccolo Machiavelli` has named the right person. Folding accepts that
    while still requiring the right NAME — nothing here makes two different
    thinkers compare equal.
    """
    s = unicodedata.normalize("NFKD", name.strip().lower())
    return "".join(c for c in s if not unicodedata.combining(c))


NAME_TO_SLUG: dict[str, str] = {_fold(p.name): slug
                                for slug, p in PERSONA_REGISTRY.items()}
SLUG_TO_NAME: dict[str, str] = {slug: p.name for slug, p in PERSONA_REGISTRY.items()}

# THE PROMPT'S LIST AND THE REGISTRY MUST AGREE, asserted at import.
# A twelfth persona, or a renamed one, changes what "from the eleven" means and
# changes chance from 1/11. Without this the run would simply score the new
# persona wrong every time and report a number that looks like a voice defect.
_PROMPT_NAMES = [ln.strip() for ln in RUBRIC.splitlines()
                 if ln.startswith("  ") and ln.strip() and not ln.strip().startswith(("{", '"'))]
_PROMPT_NAMES = [n for n in _PROMPT_NAMES if _fold(n) in NAME_TO_SLUG or n[0].isupper()]
if sorted(_fold(n) for n in _PROMPT_NAMES) != sorted(NAME_TO_SLUG):
    raise RuntimeError(
        "the approved prompt's name list and PERSONA_REGISTRY disagree.\n"
        f"  prompt:   {sorted(_PROMPT_NAMES)}\n"
        f"  registry: {sorted(SLUG_TO_NAME.values())}\n"
        "This prompt is founder-approved copy — reconcile by ruling, not by editing."
    )
CHANCE = 1.0 / len(NAME_TO_SLUG)


@dataclass
class Guess:
    sample_id: str
    persona_slug: str          # the truth
    problem_id: str
    mode: str
    plan: str
    call: int
    guess_slug: str = ""
    guess_raw: str = ""
    quote: str = ""
    tokens: tuple[int, int] = (0, 0)
    raw_error: str = ""
    skipped: bool = False

    @property
    def correct(self) -> bool:
        return bool(self.guess_slug) and self.guess_slug == self.persona_slug


def parse_guess(text: str, reply: str) -> tuple[str, str, str, str]:
    """-> (guess_slug, guess_raw, quote, error).

    Two ways to fail, both recorded rather than retried, per the listening design:
    a name that is not one of the eleven, and a quote that is not in the reply.
    Whitespace is normalised for the quote check — a model that reflows a line
    break has still quoted the reply; one that paraphrases has not.
    """
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1].rsplit("```", 1)[0] if "\n" in t else t
    try:
        obj = json.loads(t)
    except json.JSONDecodeError as e:
        return "", "", "", f"json: {e}"
    if not isinstance(obj, dict):
        return "", "", "", "json: not an object"

    raw = obj.get("thinker")
    quote = obj.get("quote") or ""
    if not isinstance(raw, str) or not raw.strip():
        return "", "", "", f"thinker missing or not a string ({raw!r})"
    slug = NAME_TO_SLUG.get(_fold(raw))
    if slug is None:
        return "", raw, "", f"thinker not one of the eleven ({raw!r})"
    if not isinstance(quote, str) or not quote.strip():
        return "", raw, "", "quote is empty"
    if " ".join(quote.split()).lower() not in " ".join(reply.split()).lower():
        return "", raw, quote, "quote not verbatim"
    return slug, raw, quote, ""


async def judge_one(client, comp: dict, call: int) -> Guess:
    g = Guess(sample_id=comp["sample_id"], persona_slug=comp["persona_slug"],
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
        g.tokens = (resp.usage.input_tokens, resp.usage.output_tokens)
        g.guess_slug, g.guess_raw, g.quote, g.raw_error = parse_guess(text, comp["reply"])
    except Exception as e:  # noqa: BLE001 - an API failure is data, not a crash
        g.raw_error = f"api: {type(e).__name__}: {e}"
    return g


async def judge_all(comps: list[dict], *, calls: int = 2, concurrency: int = 4,
                    progress=None, ceiling: float = COST_CEILING_USD) -> list[Guess]:
    """Each reply judged `calls` times in SEPARATE API calls.

    Independence is the measurement, not a nicety — see the module docstring on the
    prior reading's 22/22 twin agreement.

    THE CEILING IS CHECKED BEFORE EACH DISPATCH, inside the semaphore, so an
    overspend stops the run instead of being discovered on the invoice. Skipped
    calls come back as `skipped` rows and are counted in the report.
    """
    client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    sem = asyncio.Semaphore(concurrency)
    jobs = [(c, k) for c in comps for k in range(1, calls + 1)]
    out: list[Guess] = [None] * len(jobs)  # type: ignore[list-item]
    spent = {"in": 0, "out": 0}
    done = 0

    async def one(i, comp, call):
        nonlocal done
        async with sem:
            usd = spent["in"] * PRICE_IN / 1e6 + spent["out"] * PRICE_OUT / 1e6
            if usd >= ceiling:
                out[i] = Guess(sample_id=comp["sample_id"],
                               persona_slug=comp["persona_slug"],
                               problem_id=comp["problem_id"], mode=comp["mode"],
                               plan=comp["plan"], call=call, skipped=True,
                               raw_error=f"skipped: ${usd:.4f} >= ceiling ${ceiling}")
            else:
                out[i] = await judge_one(client, comp, call)
                spent["in"] += out[i].tokens[0]
                spent["out"] += out[i].tokens[1]
            done += 1
            if progress:
                progress(done, len(jobs), out[i])

    await asyncio.gather(*(one(i, c, k) for i, (c, k) in enumerate(jobs)))
    return sorted(out, key=lambda g: (g.sample_id, g.call))


CSV_COLUMNS = ["sample_id", "persona_slug", "problem_id", "mode", "plan", "call",
               "guess_slug", "guess_raw", "correct", "quote", "judge_model",
               "raw_error"]


def to_row(g: Guess) -> dict:
    return {"sample_id": g.sample_id, "persona_slug": g.persona_slug,
            "problem_id": g.problem_id, "mode": g.mode, "plan": g.plan,
            "call": g.call, "guess_slug": g.guess_slug, "guess_raw": g.guess_raw,
            "correct": "" if not g.guess_slug else int(g.correct),
            "quote": g.quote, "judge_model": JUDGE_MODEL, "raw_error": g.raw_error}


def write_csv(path: Path, guesses: list[Guess]) -> None:
    """Exercised once with a synthetic row BEFORE the run spends anything — a
    listening.py run once made all 99 calls and then died in its write step."""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for g in guesses:
            w.writerow(to_row(g))


def _from_row(row: dict) -> Guess:
    """Rebuild a Guess from a stored CSV row, for --report-only.

    Tokens are NOT recoverable from the CSV and come back (0, 0), so a
    report-only run prints no cost line. That is deliberate: inventing a cost
    from an average would put a number that was never billed into a record.
    """
    return Guess(sample_id=row["sample_id"], persona_slug=row["persona_slug"],
                 problem_id=row["problem_id"], mode=row["mode"], plan=row["plan"],
                 call=int(row["call"]), guess_slug=row["guess_slug"],
                 guess_raw=row["guess_raw"], quote=row["quote"],
                 raw_error=row["raw_error"])


def cost(guesses: list[Guess]) -> dict:
    tin = sum(g.tokens[0] for g in guesses)
    tout = sum(g.tokens[1] for g in guesses)
    return {"input": tin, "output": tout,
            "usd": round(tin * PRICE_IN / 1e6 + tout * PRICE_OUT / 1e6, 4)}


# ── reporting ───────────────────────────────────────────────────────────────

def per_persona(guesses: list[Guess]) -> dict[str, dict]:
    """Per-persona recognition, counted on REPLIES (the independent unit).

    A reply counts as recognised when BOTH calls named the right thinker; `split`
    records the replies whose two calls disagreed, which is the judge's own noise
    and is reported rather than resolved. `rate_calls` is the per-call rate over
    the same replies and is the looser of the two.
    """
    by_reply: dict[str, list[Guess]] = {}
    for g in guesses:
        by_reply.setdefault(g.sample_id, []).append(g)

    out: dict[str, dict] = {}
    for slug in SLUG_TO_NAME:
        replies = [v for v in by_reply.values() if v and v[0].persona_slug == slug]
        usable = [v for v in replies if all(x.guess_slug for x in v)]
        both = sum(1 for v in usable if all(x.correct for x in v))
        split = sum(1 for v in usable
                    if len({x.guess_slug for x in v}) > 1)
        calls = [x for v in replies for x in v if x.guess_slug]
        out[slug] = {
            "replies": len(replies),
            "usable": len(usable),
            "recognised": both,
            "rate": (100.0 * both / len(usable)) if usable else 0.0,
            "split": split,
            "rate_calls": (100.0 * sum(1 for x in calls if x.correct) / len(calls))
                          if calls else 0.0,
            "meets_threshold": both >= THRESHOLD_RECOGNISED,
        }
    return out


def confusion(guesses: list[Guess]) -> dict[str, Counter]:
    """truth -> Counter(guess). Every call counts; row sums are `calls` x replies."""
    m: dict[str, Counter] = {s: Counter() for s in SLUG_TO_NAME}
    for g in guesses:
        if g.guess_slug:
            m[g.persona_slug][g.guess_slug] += 1
    return m


def marginals(guesses: list[Guess]) -> Counter:
    """How often each name was SAID, regardless of truth — the position/frequency
    bias audit the prior reading failed with its flat 4-4-4."""
    return Counter(g.guess_slug for g in guesses if g.guess_slug)


def self_agreement(guesses: list[Guess]) -> tuple[int, int]:
    """(agreeing replies, usable replies) across the two independent calls."""
    by_reply: dict[str, list[Guess]] = {}
    for g in guesses:
        by_reply.setdefault(g.sample_id, []).append(g)
    pairs = [v for v in by_reply.values() if len(v) == 2 and all(x.guess_slug for x in v)]
    return sum(1 for v in pairs if v[0].guess_slug == v[1].guess_slug), len(pairs)


def _utf8_stdout() -> None:
    """Force UTF-8 on stdout before anything prints a persona name.

    THIS COST A RUN'S REPORT, THOUGH NOT ITS DATA. The first full run (220
    judgements, $1.0563) completed, wrote its CSV, and then died printing the
    per-persona table: `Niccolò` is not encodable in cp1253, the console default
    on this machine, and `print` raised UnicodeEncodeError partway down the list.

    The data survived only because `write_csv` runs BEFORE the report — the same
    ordering listening.py adopted after a TypeError in its write step destroyed 99
    paid judgements. The lesson generalises past kwargs: **the paid artefact is
    written to disk before anything cosmetic is attempted.** A crash in a report
    is then a re-run of the report, not of the run.
    """
    for stream in ("stdout", "stderr"):
        s = getattr(sys, stream)
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8")
            except Exception:  # noqa: BLE001 - a console that refuses is not fatal
                pass


def _report(gs: list[Guess]) -> None:
    """Everything printed after the run. Shared by the live path and
    --report-only so the two can never drift into describing different things."""
    agree, pairs = self_agreement(gs)
    print(f"\nself-agreement: {agree}/{pairs} replies "
          f"({100.0 * agree / pairs:.0f}%)" if pairs else "\nself-agreement: n/a")

    print(f"\nper persona (recognised = BOTH calls correct; threshold "
          f">={THRESHOLD_RECOGNISED}/10):")
    pp = per_persona(gs)
    for slug in sorted(pp, key=lambda s: -pp[s]["rate"]):
        d = pp[slug]
        mark = "OK " if d["meets_threshold"] else "   "
        print(f"  {mark}{SLUG_TO_NAME[slug]:22} {d['recognised']}/{d['usable']}"
              f"  {d['rate']:5.0f}%   per-call {d['rate_calls']:5.0f}%"
              f"   split {d['split']}")

    print("\nguess marginals (what was SAID; uniform would be "
          f"{100 * CHANCE:.1f}% each):")
    mg = marginals(gs)
    tot = sum(mg.values())
    for slug, n in mg.most_common():
        print(f"  {SLUG_TO_NAME[slug]:22} {n:4}  {100.0 * n / tot:5.1f}%")
    never = [SLUG_TO_NAME[s] for s in SLUG_TO_NAME if mg[s] == 0]
    if never:
        # A persona nobody ever NAMES is a stronger result than one nobody gets
        # right, and it is invisible in a recognition rate. Printed separately
        # because it is the finding, not a footnote.
        print("  NEVER PROPOSED FOR ANY REPLY: " + ", ".join(never))


def main() -> int:
    _utf8_stdout()
    p = argparse.ArgumentParser(prog="python -m evals.distinctiveness")
    p.add_argument("--run", required=True, help="a results dir (source of replies)")
    p.add_argument("--calls", type=int, default=2)
    p.add_argument("--mode", choices=["standard", "deep", "all"], default="all",
                   help="which Sonnet replies to judge. DEFAULT IS ALL — the "
                        "distinctiveness corpus is the full 110, unlike the "
                        "listening judge whose default is standard-only.")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--ceiling", type=float, default=COST_CEILING_USD)
    p.add_argument("--dry-run", action="store_true",
                   help="select and print the sample, send nothing")
    p.add_argument("--report-only", action="store_true",
                   help="re-print the report from an existing distinctiveness.csv "
                        "and send nothing. The report is cosmetic and the CSV is "
                        "the paid artefact — a failed report is never a reason to "
                        "re-run the judge.")
    p.add_argument("--out", default=None)
    args = p.parse_args()

    run_dir = Path(args.run)
    out = Path(args.out) if args.out else run_dir / "distinctiveness.csv"

    if args.report_only:
        with open(out, encoding="utf-8", newline="") as fh:
            stored = [_from_row(r) for r in csv.DictReader(fh)]
        print(f"report from {out}   judgements: {len(stored)}   (no API calls)")
        _report(stored)
        return 0

    comps = _pro_completions(run_dir, args.mode)

    print(f"replies: {len(comps)}   calls each: {args.calls}   "
          f"judgements: {len(comps) * args.calls}   mode: {args.mode}")
    print(f"model: {JUDGE_MODEL}   ceiling: ${args.ceiling}   "
          f"chance: {100 * CHANCE:.1f}%")
    if args.dry_run:
        by = Counter(c["persona_slug"] for c in comps)
        for slug in sorted(by):
            print(f"  {slug:22} {by[slug]}")
        return 0

    out = Path(args.out) if args.out else run_dir / "distinctiveness.csv"
    _probe = Guess(sample_id="__preflight__", persona_slug="", problem_id="",
                   mode="", plan="", call=0)
    try:
        write_csv(out, [_probe])
    except Exception as e:  # noqa: BLE001
        print(f"REFUSING TO RUN: the output path failed its write test — {e}",
              file=sys.stderr)
        return 2

    def progress(done, total, g):
        sys.stderr.write("s" if g.skipped else ("!" if g.raw_error else "."))
        if done % 20 == 0 or done == total:
            sys.stderr.write(f" {done}/{total}\n")
        sys.stderr.flush()

    gs = asyncio.run(judge_all(comps, calls=args.calls, concurrency=args.concurrency,
                               progress=progress, ceiling=args.ceiling))
    write_csv(out, gs)

    c = cost(gs)
    bad = sum(1 for g in gs if g.raw_error and not g.skipped)
    skipped = sum(1 for g in gs if g.skipped)
    print(f"\nwrote {out}")
    print(f"  judgements {len(gs)}   parse/api failures {bad}   skipped {skipped}")
    print(f"  cost ${c['usd']}  (in {c['input']}, out {c['output']})")

    _report(gs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
