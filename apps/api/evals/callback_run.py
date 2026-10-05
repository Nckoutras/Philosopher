"""MEM2-C-1 — the callback arm comparison. Generate, judge, report.

    cd apps/api
    python -m evals.callback_run dry-run                 # assemble, send nothing
    python -m evals.callback_run generate                # both arms, both plans
    python -m evals.callback_run judge  --dir <run dir>  # callback + listening
    python -m evals.callback_run report --dir <run dir>  # numbers, no API calls

THE TWO ARMS, on the SAME 132 samples (evals/callback_samples.py):

    ruling6   production today: the memory block under Ruling #6's directive,
              then production's own reply directive (harness arm "shipped").
    callback  identical, plus the approved callback block directly after the
              memory block — only on samples whose gate offered a candidate.

Each sample runs on both plans (Haiku 4.5 free, Sonnet 4.6 pro) as every §8.2
run does: 132 x 2 arms x 2 plans = 528 completions.

WHAT THIS MEASURES, AND WHAT IT CANNOT. Every number is a RATE over synthetic
samples with forced presence (callback_samples' docstring). It can rank the two
arms and show how behaviour moves with relevance and age; it cannot say how
often production would reach these states. The manifest records, per sample,
whether production's `compose_recall` would even have put the candidate in the
block — the bridge between the two.

NO PASS/FAIL. The founder sets X, Y, the callback floor and min-age FROM these
numbers (MEM2-C ruling 4); this module reports and does not decide.

NEVER RUNS IN CI. tests/ exercise the pure parts (aggregation, block order,
manifest) with no network.

COST, ESTIMATED BEFORE THE FIRST RUN (not measured):
    generation  ~528 completions: Haiku ~$0.004, Sonnet ~$0.013 each  ~= $4.5
    callback judge  528 x 2 calls, Opus 5, ~1.6k in / ~250 out        ~= $15
    listening       528 x 1 call,  Opus 5, ~1.0k in / ~200 out        ~= $5
    embeddings      ~400 short texts, text-embedding-3-small          <  $0.01
    total                                                             ~= $25
The real spend is computed from recorded usage and written to the manifest.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from personas import PERSONA_REGISTRY
from services.conversation_service import _adaptive_band_for_input
from services.memory_service import (
    INFERRED_SCORE_FLOOR,
    STANDING_TYPES,
    _ordered,
    compose_recall,
)
from text_utils import dominant_language

from . import callback_judge, harness
from .callback_directive import directive_hash, render_block, when_bucket
from .callback_samples import (
    INELIGIBLE_KINDS,
    LANGUAGE_NAME,
    CallbackSample,
    build_samples,
    sample_set_hash,
)
from .run import PRICES, BUCKET_MULTIPLIER, _git_dirty, _git_sha, persona_config_hash

RESULTS_DIR = Path(__file__).resolve().parent / "results"
ARMS = ("ruling6", "callback")
HARNESS_ARM = "shipped"   # production's reply_directive, called — see harness

# Cosine bins for the floor question. Fixed, not quantiles, so two runs bin alike.
COSINE_BINS = ((-1.0, 0.30), (0.30, 0.40), (0.40, 0.50), (0.50, 0.60),
               (0.60, 0.75), (0.75, 1.01))


# ── assembly (pure) ──────────────────────────────────────────────────────────

def block_rows(sample: CallbackSample) -> list:
    """The memory block's rows in production's order: Lane A (standing types)
    first, then everything else, each ordered by memory_service._ordered —
    compose_recall's order, without its caps (presence is forced here)."""
    standing = [r for r in sample.rows if r.entry_type in STANDING_TYPES]
    rest = [r for r in sample.rows if r.entry_type not in STANDING_TYPES]
    return _ordered(standing) + _ordered(rest)


def callback_for(sample: CallbackSample, arm: str) -> str:
    """The rendered callback block for this arm and sample, or ""."""
    if arm != "callback":
        return ""
    cand = sample.candidate()
    if cand is None:
        return ""
    return render_block(cand.original, cand.days_ago)


def stated_band(sample: CallbackSample) -> tuple[int, int]:
    """The band the prompt actually asks for — conversation_service.py:999-1009:
    the adaptive band past the first exchange, else the persona's standard band."""
    persona = PERSONA_REGISTRY[sample.persona_slug]
    band = None
    if len(sample.history) > 1:
        band = _adaptive_band_for_input(sample.user_message, persona)
    lo, hi = band or persona.response_length_words.standard_reply_words
    return int(lo), int(hi)


def recall_would_keep(sample: CallbackSample) -> set[str]:
    """Ids production's compose_recall would put in the block, given the scores.
    Needs real scores; before embeddings every Lane B row sits at 0.0 and fails
    the floor, which is reported as such rather than guessed around."""
    return {str(r.id) for r in compose_recall(list(sample.rows))}


def completion_key(arm: str, plan: str, sample_id: str) -> str:
    return f"{arm}|{plan}|{sample_id}"


# ── embeddings: the relevance score the C-2 gate would have ──────────────────

def _cos(u, v) -> float:
    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    return dot / (nu * nv) if nu and nv else 0.0


async def score_rows(samples: list[CallbackSample]) -> dict:
    """Embed every distinct text once; set row.score = cosine(row content, current
    message), which is what RECALL_SQL scores. Also returns cosine(original,
    current) per candidate, for reference — Ruling 2 shows the original, but the
    stored row is what a gate can score against the query."""
    from services.embedding_client import embedding_client

    texts = sorted({s.user_message for s in samples}
                   | {r.content for s in samples for r in s.rows}
                   | {r.original for s in samples for r in s.rows if r.original})
    vecs = {}
    for i in range(0, len(texts), 64):
        chunk = texts[i:i + 64]
        for t, v in zip(chunk, await embedding_client.embed_batch(chunk)):
            vecs[t] = v
    originals = {}
    for s in samples:
        q = vecs[s.user_message]
        for r in s.rows:
            r.score = _cos(vecs[r.content], q)
        cand = s.candidate_row()
        originals[s.sample_id] = _cos(vecs[cand.original], q)
    return originals


def apply_scores(samples: list[CallbackSample], stored: dict) -> None:
    """Restore row scores from a run's scores.json so judge/report see the same
    numbers generation did, without re-embedding."""
    for s in samples:
        for r in s.rows:
            r.score = stored[s.sample_id]["rows"][r.id]


# ── generate ─────────────────────────────────────────────────────────────────

async def generate(out: Path, *, concurrency: int, plans, note: str) -> int:
    dirty = _git_dirty()
    samples = build_samples()
    by_id = {s.sample_id: s for s in samples}
    originals = await score_rows(samples)
    scores = {
        s.sample_id: {
            "rows": {r.id: round(r.score, 6) for r in s.rows},
            "candidate_row_cosine": round(s.candidate_row().score, 6),
            "candidate_original_cosine": round(originals[s.sample_id], 6),
            "recall_would_keep": sorted(recall_would_keep(s)),
        }
        for s in samples
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "scores.json").write_text(json.dumps(scores, indent=1, ensure_ascii=False),
                                     encoding="utf-8", newline="\n")

    wanted = [t for t in harness.ARMS_BY_PLAN if not plans or t[1] in plans]
    jobs = sorted(((arm, s, plan, model) for arm in ARMS for s in samples
                   for _, plan, model in wanted),
                  key=lambda j: (j[1].persona_slug, j[2], j[0], j[1].sample_id))
    sem = asyncio.Semaphore(concurrency)
    results: list = [None] * len(jobs)
    done = 0

    async def one(i, arm, s, plan, model):
        nonlocal done
        async with sem:
            c = await harness.generate(
                s, plan, model, arm=HARNESS_ARM, memories=block_rows(s),
                history=s.history, callback_block=callback_for(s, arm),
            )
            results[i] = (arm, c)
            done += 1
            sys.stderr.write("!" if c.error else ".")
            if done % 50 == 0 or done == len(jobs):
                sys.stderr.write(f" {done}/{len(jobs)}\n")
            sys.stderr.flush()

    await asyncio.gather(*(one(i, *j) for i, j in enumerate(jobs)))

    rows = []
    for arm, c in sorted(results, key=lambda x: (x[0], x[1].sample_id, x[1].plan)):
        s = by_id[c.sample_id]
        cand = s.candidate()
        lo, hi = stated_band(s)
        words = len(c.reply.split())        # check_brevity's own count
        rows.append({
            "key": completion_key(arm, c.plan, c.sample_id),
            "arm": arm, "plan": c.plan, "model": c.model,
            "sample_id": c.sample_id, "scenario": s.scenario,
            "persona_slug": s.persona_slug, "language": s.language,
            "thread_id": s.thread_id, "candidate_days": s.candidate_days,
            "when": when_bucket(s.candidate_days),
            "offered": bool(cand) and arm == "callback",
            "gate_offers": bool(cand),
            "user_message": s.user_message, "history": s.history,
            "reply": c.reply, "words": words, "band_lo": lo, "band_hi": hi,
            "in_band": lo <= words <= hi,
            "reply_language": dominant_language([c.reply]) if c.reply else None,
            "tokens": c.tokens, "error": c.error,
            "system_prompt_chars": len(c.system_prompt),
        })
    with open(out / "completions.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = _manifest(note, samples, rows, dry_run=False, git_dirty=dirty)
    _write_json(out / "manifest.json", manifest)
    print(f"\nwrote {out}\n  completions {len(rows)}  errors {manifest['errors']}"
          f"  cost ${manifest['cost']['_total_usd']}")
    return 1 if manifest["errors"] else 0


def _cost(rows: list[dict]) -> dict:
    per: dict = {}
    for r in rows:
        t = r.get("tokens") or {}
        if not t:
            continue
        acc = per.setdefault(r["model"], {"input": 0, "cache_creation": 0,
                                          "cache_read": 0, "output": 0, "usd": 0.0})
        for b in ("input", "cache_creation", "cache_read"):
            acc[b] += t.get(b, 0)
        acc["output"] += t.get("total", 0) - sum(t.get(b, 0) for b in
                                                 ("input", "cache_creation", "cache_read"))
    for model, acc in per.items():
        pin, pout = PRICES.get(model, (0.0, 0.0))
        billed = sum(acc[b] * BUCKET_MULTIPLIER[b] for b in BUCKET_MULTIPLIER)
        acc["usd"] = round(billed / 1e6 * pin + acc["output"] / 1e6 * pout, 4)
    per["_total_usd"] = round(sum(v["usd"] for v in per.values() if isinstance(v, dict)), 4)
    return per


def _manifest(note: str, samples, rows, *, dry_run: bool, git_dirty: bool) -> dict:
    return {
        "what": "MEM2-C-1 callback arm comparison",
        "arms": list(ARMS), "harness_arm": HARNESS_ARM, "note": note,
        "dry_run": dry_run,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git_sha(), "git_dirty": git_dirty,
        "sample_set_hash": sample_set_hash(),
        "persona_config_hash": persona_config_hash(),
        "callback_directive_hash": directive_hash(),
        "n_samples": len(samples), "n_completions": len(rows),
        "models": sorted({m for _, _, m in harness.ARMS_BY_PLAN}),
        "phenomenology_bridge_enabled": harness.PHENOMENOLOGY_BRIDGE_ENABLED,
        "inferred_score_floor": INFERRED_SCORE_FLOOR,
        "errors": sum(1 for r in rows if r.get("error")),
        "cost": _cost(rows) if rows else {},
        "caveats": [
            "Synthetic samples with FORCED PRESENCE: every row is in the block "
            "whether or not compose_recall would have kept it. scores.json records "
            "what it would have kept.",
            "L1 has no candidate offered (within-conversation ledger), so its prompt "
            "is identical in both arms; its two arms are a replicate.",
            "Judge headline numbers use call 1; call 2 is the self-agreement floor.",
            "Rates only. No pass/fail: thresholds are the founder's, from these numbers.",
        ],
    }


def _write_json(path: Path, obj) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# ── dry run ──────────────────────────────────────────────────────────────────

def dry_run(out: Path, note: str) -> int:
    """Assemble every prompt for both arms and send nothing. Writes the manifest
    and the full prompts, so the founder can read exactly what will be sent."""
    samples = build_samples()
    out.mkdir(parents=True, exist_ok=True)
    n_offered = 0
    with open(out / "prompts.jsonl", "w", encoding="utf-8", newline="\n") as fh:
        for arm in ARMS:
            for s in samples:
                block = callback_for(s, arm)
                n_offered += 1 if block else 0
                system, _ = harness.assemble_system(
                    PERSONA_REGISTRY[s.persona_slug], s.user_message, deep=False,
                    include_cache_sentinel=False, arm=HARNESS_ARM,
                    memories=block_rows(s), history_len=len(s.history),
                    callback_block=block,
                )
                fh.write(json.dumps({"arm": arm, "sample_id": s.sample_id,
                                     "system": system, "history": s.history,
                                     "user": s.user_message}, ensure_ascii=False) + "\n")
    manifest = _manifest(note, samples, [], dry_run=True, git_dirty=_git_dirty())
    manifest["completions_that_would_be_sent"] = len(samples) * len(ARMS) * len(
        harness.ARMS_BY_PLAN)
    manifest["callback_blocks_rendered"] = n_offered
    _write_json(out / "manifest.json", manifest)
    print(f"dry run: {len(samples)} samples x {len(ARMS)} arms x "
          f"{len(harness.ARMS_BY_PLAN)} plans = "
          f"{manifest['completions_that_would_be_sent']} completions would be sent")
    print(f"callback blocks rendered (callback arm): {n_offered}")
    print(f"sample_set_hash={manifest['sample_set_hash']}  "
          f"callback_directive_hash={manifest['callback_directive_hash']}")
    print(f"wrote {out}")
    return 0


# ── judge ────────────────────────────────────────────────────────────────────

JUDGE_COLUMNS = ["key", "call", "raw_error", "items"] + [
    f"{c}_{x}" for c in callback_judge.CRITERIA for x in ("v", "q")]
LISTEN_COLUMNS = ["key", "call", "raw_error"] + [
    f"{c}_{x}" for c in ("a", "b", "c", "d", "e") for x in ("v", "q")]


def _judge_row(j, criteria, with_items: bool) -> dict:
    row = {"key": j.key, "call": j.call, "raw_error": j.raw_error}
    if with_items:
        row["items"] = " ".join(j.verdicts.get("items", []))
    for c in criteria:
        v, q = j.verdicts.get(c, (None, ""))
        row[f"{c}_v"] = "" if v is None else int(v)
        row[f"{c}_q"] = q
    return row


def write_judgements(path: Path, js, *, which: str) -> None:
    cols, crit, items = ((JUDGE_COLUMNS, callback_judge.CRITERIA, True)
                         if which == "callback"
                         else (LISTEN_COLUMNS, ("a", "b", "c", "d", "e"), False))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for j in js:
            w.writerow(_judge_row(j, crit, items))


def load_run(run_dir: Path) -> tuple[list[dict], dict[str, CallbackSample]]:
    rows = [json.loads(l) for l in
            (run_dir / "completions.jsonl").read_text(encoding="utf-8").splitlines() if l]
    samples = build_samples()
    apply_scores(samples, json.loads((run_dir / "scores.json").read_text(encoding="utf-8")))
    return rows, {s.sample_id: s for s in samples}


def judge(run_dir: Path, *, calls: int, concurrency: int) -> int:
    rows, by_id = load_run(run_dir)
    jobs = [(r["key"], by_id[r["sample_id"]], r["reply"]) for r in rows if not r["error"]]

    # PRE-FLIGHT THE WRITES before a cent is spent (listening.py's lesson: a paid
    # run once reached its write step for the first time with the data in memory).
    probe = callback_judge.CallbackJudgement(key="__preflight__", call=0)
    for name, which in (("callback_judge.csv", "callback"),
                        ("listening_source.csv", "listening")):
        try:
            write_judgements(run_dir / name, [probe], which=which)
        except Exception as e:  # noqa: BLE001
            print(f"REFUSING TO RUN: {name} failed its write test — {e}", file=sys.stderr)
            return 2

    def progress(done, total, j):
        sys.stderr.write("!" if j.raw_error else ".")
        if done % 50 == 0 or done == total:
            sys.stderr.write(f" {done}/{total}\n")
        sys.stderr.flush()

    print(f"callback judge: {len(jobs)} replies x {calls} calls")
    cb = asyncio.run(callback_judge.judge_all(jobs, which="callback", calls=calls,
                                              concurrency=concurrency, progress=progress))
    write_judgements(run_dir / "callback_judge.csv", cb, which="callback")
    print(f"listening (source shown): {len(jobs)} replies x 1 call")
    ls = asyncio.run(callback_judge.judge_all(jobs, which="listening", calls=1,
                                              concurrency=concurrency, progress=progress))
    write_judgements(run_dir / "listening_source.csv", ls, which="listening")

    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    m["judge"] = {
        "model": callback_judge.JUDGE_MODEL, "callback_calls": calls,
        "callback_cost": callback_judge.cost(cb), "listening_cost": callback_judge.cost(ls),
        "callback_failures": sum(1 for j in cb if j.raw_error),
        "listening_failures": sum(1 for j in ls if j.raw_error),
        "judged_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rubric_hash": hashlib.sha256(callback_judge.RUBRIC.encode("utf-8")).hexdigest()[:16],
    }
    _write_json(run_dir / "manifest.json", m)
    print(f"wrote {run_dir}  callback ${m['judge']['callback_cost']['usd']}  "
          f"listening ${m['judge']['listening_cost']['usd']}")
    return 0


# ── report (pure aggregation) ────────────────────────────────────────────────

def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _yes(row: dict | None, c: str) -> bool:
    return bool(row) and row.get(f"{c}_v") == "1"


def _rate(num: int, den: int) -> str:
    return f"{100.0 * num / den:.1f}% ({num}/{den})" if den else "n/a (0)"


def item_kinds(sample: CallbackSample, items: list[str]) -> list[str]:
    labels = dict(callback_judge.earlier_items(sample))
    return [labels[i].kind for i in items if i in labels]


def aggregate(comps: list[dict], by_id: dict[str, CallbackSample],
              cb_rows: list[dict], ls_rows: list[dict], scores: dict) -> dict:
    """Every measure in the brief, per (arm, plan, language). PURE: no I/O.

    Headline judge numbers use call 1. Agreement between calls 1 and 2 is reported
    per criterion as the judge's own noise floor. A parse failure is excluded
    from that reply's judged measures and counted separately — never read as no.
    """
    cb1 = {r["key"]: r for r in cb_rows if r["call"] == "1" and not r["raw_error"]}
    cb2 = {r["key"]: r for r in cb_rows if r["call"] == "2" and not r["raw_error"]}
    ls1 = {r["key"]: r for r in ls_rows if r["call"] == "1" and not r["raw_error"]}

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for c in comps:
        if c["error"]:
            continue
        for g in ((c["arm"], c["plan"], c["language"]), (c["arm"], c["plan"], "all"),
                  (c["arm"], "all", "all")):
            groups[g].append(c)

    def items_of(key):
        r = cb1.get(key)
        return r["items"].split() if r and r["items"] else []

    def calls_a(c):
        return _yes(cb1.get(c["key"]), "cb") and "A" in items_of(c["key"])

    out: dict = {}
    for g, cs in sorted(groups.items()):
        judged = [c for c in cs if c["key"] in cb1]
        offered = [c for c in judged if c["gate_offers"] and c["scenario"] != "L1"]
        to_a = [c for c in judged if calls_a(c)]
        any_cb = [c for c in judged if _yes(cb1[c["key"]], "cb")]
        misuse = [c for c in judged
                  if set(item_kinds(by_id[c["sample_id"]], items_of(c["key"])))
                  & set(INELIGIBLE_KINDS)]
        misuse_by_kind: dict[str, int] = defaultdict(int)
        for c in misuse:
            for k in set(item_kinds(by_id[c["sample_id"]], items_of(c["key"]))):
                if k in INELIGIBLE_KINDS:
                    misuse_by_kind[k] += 1

        # repetition: same candidate offered in consecutive sessions R -> R2
        pairs = defaultdict(dict)
        for c in judged:
            if c["scenario"] in ("R", "R2"):
                pairs[(c["persona_slug"], c["language"], c["plan"])][c["scenario"]] = c
        r_used = [p for p in pairs.values() if "R" in p and "R2" in p and calls_a(p["R"])]
        both = [p for p in r_used if calls_a(p["R2"])]

        def es_rate(scn):
            xs = [c for c in judged if c["scenario"] == scn]
            return _rate(sum(1 for c in xs if _yes(cb1[c["key"]], "es")), len(xs))

        ls = [c for c in cs if c["key"] in ls1]
        lao = [c for c in cs if c["persona_slug"] == "lao_tzu"]
        out["|".join(g)] = {
            "completions": len(cs), "judged": len(judged),
            "callback_rate_on_offer": _rate(sum(1 for c in offered if calls_a(c)), len(offered)),
            "any_callback_rate": _rate(len(any_cb), len(judged)),
            "fidelity_among_callbacks": _rate(
                sum(1 for c in to_a if _yes(cb1[c["key"]], "ff")), len(to_a)),
            "sharpens_among_callbacks": _rate(
                sum(1 for c in to_a if _yes(cb1[c["key"]], "sh")), len(to_a)),
            "timing_conflict_among_callbacks": _rate(
                sum(1 for c in to_a if _yes(cb1[c["key"]], "tm")), len(to_a)),
            "where_or_to_whom_among_callbacks": _rate(
                sum(1 for c in any_cb if _yes(cb1[c["key"]], "at")), len(any_cb)),
            "asks_confirmation_among_callbacks": _rate(
                sum(1 for c in any_cb if _yes(cb1[c["key"]], "cf")), len(any_cb)),
            "misuse_ineligible_rate": _rate(len(misuse), len(judged)),
            "misuse_by_kind": dict(sorted(misuse_by_kind.items())),
            "misuse_rate_in_B": _rate(sum(1 for c in misuse if c["scenario"] == "B"),
                                      sum(1 for c in judged if c["scenario"] == "B")),
            "repetition_R_then_R2": _rate(len(both), len(r_used)),
            "escalation_R2_control": es_rate("R2"),
            "escalation_L2_after_affirmation": es_rate("L2"),
            "escalation_L1_same_session": es_rate("L1"),
            "listening_e_source_shown": _rate(sum(1 for c in ls if _yes(ls1[c["key"]], "e")), len(ls)),
            "listening_d": _rate(sum(1 for c in ls if _yes(ls1[c["key"]], "d")), len(ls)),
            "listening_a": _rate(sum(1 for c in ls if _yes(ls1[c["key"]], "a")), len(ls)),
            "in_band": _rate(sum(1 for c in cs if c["in_band"]), len(cs)),
            "mean_words": round(sum(c["words"] for c in cs) / len(cs), 1) if cs else None,
            "mean_words_with_callback": (round(sum(c["words"] for c in to_a) / len(to_a), 1)
                                         if to_a else None),
            "lao_tzu_in_band": _rate(sum(1 for c in lao if c["in_band"]), len(lao)),
            "reply_language_matches": _rate(
                sum(1 for c in cs if c["reply_language"] == LANGUAGE_NAME[c["language"]]),
                len(cs)),
        }

    # by relevance bin and by age bucket: callback arm, offered samples only
    def bin_of(x):
        return next(f"{lo:.2f}-{hi:.2f}" for lo, hi in COSINE_BINS if lo <= x < hi)

    by_bin: dict = defaultdict(lambda: [0, 0, 0, 0])   # offered, used, sharpens, recall_keeps
    by_age: dict = defaultdict(lambda: [0, 0, 0, 0])   # offered, used, faithful, timing
    for c in comps:
        if c["error"] or c["arm"] != "callback" or not c["offered"] or c["key"] not in cb1:
            continue
        s = scores[c["sample_id"]]
        b = by_bin[bin_of(s["candidate_row_cosine"])]
        a = by_age[c["when"]]
        used = calls_a(c)
        b[0] += 1; b[1] += used; b[2] += used and _yes(cb1[c["key"]], "sh")
        b[3] += by_id[c["sample_id"]].candidate_row().id in s["recall_would_keep"]
        a[0] += 1; a[1] += used; a[2] += used and _yes(cb1[c["key"]], "ff")
        a[3] += used and _yes(cb1[c["key"]], "tm")

    agreement = {}
    for crit in callback_judge.CRITERIA:
        both_k = [k for k in cb1 if k in cb2]
        agree = sum(1 for k in both_k if cb1[k][f"{crit}_v"] == cb2[k][f"{crit}_v"])
        agreement[crit] = _rate(agree, len(both_k))

    per_persona = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for c in comps:
        if not c["error"]:
            cell = per_persona[c["persona_slug"]][c["arm"]]
            cell[0] += 1; cell[1] += c["in_band"]

    return {
        "groups": out,
        "callback_arm_by_candidate_cosine": {
            k: {"offered": v[0], "used": _rate(v[1], v[0]),
                "sharpens_given_used": _rate(v[2], v[1]),
                "production_recall_would_include_candidate": _rate(v[3], v[0])}
            for k, v in sorted(by_bin.items())},
        "callback_arm_by_age": {
            k: {"offered": v[0], "used": _rate(v[1], v[0]),
                "faithful_given_used": _rate(v[2], v[1]),
                "timing_conflict_given_used": _rate(v[3], v[1])}
            for k, v in by_age.items()},
        "judge_self_agreement": agreement,
        "judge_failures": {
            "callback": sum(1 for r in cb_rows if r["raw_error"]),
            "listening": sum(1 for r in ls_rows if r["raw_error"])},
        "in_band_by_persona": {
            p: {arm: _rate(v[1], v[0]) for arm, v in sorted(d.items())}
            for p, d in sorted(per_persona.items())},
    }


def report(run_dir: Path) -> int:
    comps, by_id = load_run(run_dir)
    scores = json.loads((run_dir / "scores.json").read_text(encoding="utf-8"))
    agg = aggregate(comps, by_id, _read_csv(run_dir / "callback_judge.csv"),
                    _read_csv(run_dir / "listening_source.csv"), scores)
    _write_json(run_dir / "report.json", agg)
    lines = ["# MEM2-C-1 — callback arm comparison", "",
             f"Run: `{run_dir.name}`. Rates are call-1 judge verdicts; see "
             "`judge_self_agreement` for the noise floor.", ""]
    for section, body in agg.items():
        lines += [f"## {section}", "", "```", json.dumps(body, indent=2, ensure_ascii=False),
                  "```", ""]
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"wrote {run_dir / 'report.md'} and report.json")
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m evals.callback_run")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dry-run")
    d.add_argument("--out", default=None)
    d.add_argument("--note", default="")
    g = sub.add_parser("generate")
    g.add_argument("--out", default=None)
    g.add_argument("--note", default="")
    g.add_argument("--concurrency", type=int, default=4)
    g.add_argument("--plan", action="append", default=None, choices=["free", "pro"])
    j = sub.add_parser("judge")
    j.add_argument("--dir", required=True)
    j.add_argument("--calls", type=int, default=2)
    j.add_argument("--concurrency", type=int, default=4)
    r = sub.add_parser("report")
    r.add_argument("--dir", required=True)
    return p


def main() -> int:
    args = build_parser().parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M")
    if args.cmd == "dry-run":
        return dry_run(Path(args.out) if args.out else
                       RESULTS_DIR / f"{stamp}_mem2c1_dryrun", args.note)
    if args.cmd == "generate":
        out = Path(args.out) if args.out else RESULTS_DIR / f"{stamp}_mem2c1"
        return asyncio.run(generate(out, concurrency=args.concurrency,
                                    plans=args.plan, note=args.note))
    if args.cmd == "judge":
        return judge(Path(args.dir), calls=args.calls, concurrency=args.concurrency)
    return report(Path(args.dir))


if __name__ == "__main__":
    raise SystemExit(main())
