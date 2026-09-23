"""Arm F — retrieval FORCED INJECTION. Does a grounding passage raise distinctiveness?

THE QUESTION. Every §8.2 reply ever generated ran with `passages=[]`, because
production retrieval has never returned a passage (RETRIEVAL-001: 0 non-empty
`retrieval_ids` in 840 all-time assistant messages; top-1 cosine ceiling 0.462
against a 0.72 threshold). So the effect of grounding passages on distinctiveness
has never been measured — only argued about, from the mismatch between chunk counts
and recognition rates (Jung has 0 chunks and is recognised; Wilde has 352 and is
not).

THE DESIGN. Force the top-1 chunk in regardless of `score_threshold` — no
threshold, always inject. `sigmund_freud` and `epictetus` only: the two personas
with both a real corpus and the highest observed similarity. Their 7 standard
replies each, under the SHIPPED arm E directive. Control is their stored arm E
replies, already judged.

THE PASSAGES ARE REAL AND THEIR SCORES ARE RECORDED. The top-1 chunk per
(persona, problem) was computed against Oregon with pgvector cosine, no threshold,
inside a READ-ONLY transaction. Measured cosines:

    range 0.1917 - 0.4172, mean 0.2965
    NONE of the 14 would clear the live 0.72 threshold

That is the point rather than a caveat: this arm asks what the BEST AVAILABLE
passage does, not what a good one would do. If the best available passage moves
nothing, the threshold is not what is holding retrieval back.

DECISION RULE, FIXED BEFORE THE RUN (founder, 2026-09-23):

    a rise in EITHER persona's recall -> retrieval becomes a real workstream
                                         (threshold, chunking, coverage)
    both flat -> the hypothesis CLOSES **for now**. Explicitly NOT "retrieval can
                 never help": "forcing the best available passage on the two
                 best-equipped personas produced no visible effect at this sample
                 size, and a bigger arm is not justified without one."

PRODUCTION CODE UNTOUCHED. The only change outside this file is an optional
`passages=()` parameter threaded through `harness.assemble_system` / `generate`,
defaulting to empty — which is production identity, so every other arm's prompt is
byte-unchanged. `services/` is not modified.

READ-ONLY ON OREGON. The chunk fetch ran inside `BEGIN TRANSACTION READ ONLY` with
`SHOW transaction_read_only` asserted `on` before any query, and was rolled back
rather than committed. SELECT statements only: no writes, no DDL, no RPC creation,
no temp tables.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from personas import PERSONA_REGISTRY

from . import harness
from .prompt_set import build_samples

PERSONAS = ("sigmund_freud", "epictetus")
ARM = "e"          # the SHIPPED directive; arm F changes passages, not wording


class _Chunk:
    """The shape `system_base.jinja2` reads: source_title, source_type, page_ref,
    content. A real SourceChunk would need a DB session; the template never touches
    anything else, and `tests` assert that."""

    def __init__(self, row: dict):
        self.source_title = row["source_title"]
        self.source_type = "primary_text"
        self.page_ref = None
        self.content = row["content"]
        self.cosine = float(row["cosine"])
        self.chunk_id = row["chunk_id"]


def load_chunks(path: Path) -> dict[tuple[str, str], _Chunk]:
    rows = json.loads(path.read_text(encoding="utf-8-sig"))
    out = {(r["problem_id"], r["slug"]): _Chunk(r) for r in rows}
    if len(out) != len(rows):
        raise SystemExit(f"duplicate (problem, persona) keys in {path}")
    return out


async def run(chunks, out_dir: Path, concurrency: int) -> None:
    samples = [s for s in build_samples()
               if s.persona_slug in PERSONAS and s.mode != "deep"]
    missing = [s.sample_id for s in samples
               if (s.problem_id, s.persona_slug) not in chunks]
    if missing:
        raise SystemExit(f"no chunk for: {missing}")

    print(f"replies: {len(samples)}   personas: {sorted(PERSONAS)}   arm: {ARM}")
    print(f"passages: top-1, NO threshold, cosine "
          f"{min(c.cosine for c in chunks.values()):.4f}"
          f"-{max(c.cosine for c in chunks.values()):.4f}")

    sem = asyncio.Semaphore(concurrency)
    results: list = [None] * len(samples)

    async def one(i, s):
        async with sem:
            ch = chunks[(s.problem_id, s.persona_slug)]
            c = await harness.generate(s, "pro", harness.MODEL_PRO,
                                       arm=ARM, passages=[ch])
            results[i] = (c, ch)
            sys.stderr.write("!" if c.error else ".")
            sys.stderr.flush()

    await asyncio.gather(*(one(i, s) for i, s in enumerate(samples)))
    sys.stderr.write("\n")

    out_dir.mkdir(parents=True, exist_ok=True)
    errors = 0
    with open(out_dir / "completions.jsonl", "w", encoding="utf-8") as fh:
        for c, ch in results:
            d = c.__dict__.copy() if hasattr(c, "__dict__") else dict(c._asdict())
            d["injected_chunk_id"] = ch.chunk_id
            d["injected_cosine"] = ch.cosine
            d["injected_source_title"] = ch.source_title
            errors += 1 if d.get("error") else 0
            fh.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")
    print(f"\nwrote {out_dir / 'completions.jsonl'}   errors {errors}")


def main() -> int:
    p = argparse.ArgumentParser(prog="python -m evals.arm_f_run")
    p.add_argument("--chunks", required=True, help="the exported top1 JSON")
    p.add_argument("--out", required=True)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    chunks = load_chunks(Path(args.chunks))
    if args.dry_run:
        for (pid, slug), c in sorted(chunks.items()):
            print(f"  {pid:32}{slug:16}{c.cosine:.4f}  {c.source_title[:36]}")
        return 0
    asyncio.run(run(chunks, Path(args.out), args.concurrency))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
