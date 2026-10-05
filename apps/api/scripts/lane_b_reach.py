"""Lane B reach — read-only measurement against production. Prints aggregates only.

Question: for the last 100 user messages, what is the max cosine between the
message and that user's active Lane B memory rows (entry_type NOT IN STANDING_TYPES),
and how many exceed recall's Lane B floor?

Two corpora per message, because "the rows recall could have seen" is the honest one:
  as_of_message  rows created BEFORE the message (a row extracted from this very
                 message would otherwise match it and inflate the score), active now
  active_now     every currently active Lane B row of that user

FIRST RUN, 2026-10-05 (founder, production): as_of_message, 95 messages, 9 users —
median 0.419, max 0.709, 0 above 0.75 (0 of 62 non-admin). Lane B recall had never
fired; the floor was lowered 0.75 -> 0.45 on this result (IMPLEMENTATION_BACKLOG,
MEM2 Lane B floor). The script reports BOTH the reference 0.75 and the current
INFERRED_SCORE_FLOOR, so a re-run stays comparable with that first run after the
constant moved.

Run from apps/api with the production URL in the environment:
    DATABASE_URL_RO='postgresql://...oregon...' python scripts/lane_b_reach.py
The transaction is READ ONLY; nothing is written. Embeddings use the app's own
embedding_client (text-embedding-3-small), so the scores are the scores recall sees.
Never prints message text: aggregates only.
"""
import asyncio
import math
import os
import statistics
import sys

sys.path.insert(0, os.getcwd())

import asyncpg  # noqa: E402

from services.embedding_client import embedding_client  # noqa: E402
from services.memory_service import INFERRED_SCORE_FLOOR, STANDING_TYPES  # noqa: E402

REFERENCE_FLOOR = 0.75   # the floor the first run (2026-10-05) was measured against

MSGS_SQL = """
    SELECT m.id, m.user_id, m.created_at, m.content, u.is_admin
    FROM messages m JOIN users u ON u.id = m.user_id
    WHERE m.role = 'user'
    ORDER BY m.created_at DESC
    LIMIT 100
"""
ROWS_SQL = """
    SELECT user_id, created_at, embedding::text AS emb
    FROM memory_entries
    WHERE user_id = ANY($1::uuid[]) AND is_active AND embedding IS NOT NULL
      AND entry_type <> ALL($2::text[])
"""


def cos(u, v):
    d = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u)); nv = math.sqrt(sum(b * b for b in v))
    return d / (nu * nv) if nu and nv else 0.0


def summary(label, xs):
    if not xs:
        print(f"  {label}: n=0"); return
    xs = sorted(xs)
    q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]
    # Recall keeps `score > floor`, so strictly greater. 0.75 is the reference the
    # first run was asked against; the current floor is what recall does today.
    over = "  ".join(f">{t}: {sum(1 for x in xs if x > t)}"
                     for t in sorted({REFERENCE_FLOOR, INFERRED_SCORE_FLOOR}))
    print(f"  {label}: n={len(xs)}  min={xs[0]:.3f} p25={q(.25):.3f} median={statistics.median(xs):.3f} "
          f"p75={q(.75):.3f} p90={q(.90):.3f} max={xs[-1]:.3f}  {over}")
    bins = [(-1, .3), (.3, .4), (.4, .45), (.45, .5), (.5, .6), (.6, .7), (.7, .75), (.75, 1.01)]
    print("    bins: " + "  ".join(f"[{a:.2f},{b:.2f}):{sum(1 for x in xs if a <= x < b)}"
                                  for a, b in bins))


async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL_RO"].replace("+asyncpg", ""))
    try:
        tr = conn.transaction(readonly=True)
        await tr.start()
        msgs = await conn.fetch(MSGS_SQL)
        users = sorted({r["user_id"] for r in msgs})
        rows = await conn.fetch(ROWS_SQL, users, list(STANDING_TYPES))
        await tr.rollback()
    finally:
        await conn.close()

    by_user = {}
    for r in rows:
        vec = [float(x) for x in r["emb"].strip("[]").split(",")]
        by_user.setdefault(r["user_id"], []).append((r["created_at"], vec))

    vecs = await embedding_client.embed_batch([m["content"] for m in msgs])
    out = {"all": {"as_of": [], "now": []}, "non_admin": {"as_of": [], "now": []}}
    no_rows = {"as_of": 0, "now": 0}
    for m, q in zip(msgs, vecs):
        cands = by_user.get(m["user_id"], [])
        prior = [cos(q, v) for t, v in cands if t < m["created_at"]]
        now = [cos(q, v) for _, v in cands]
        for key, xs in (("as_of", prior), ("now", now)):
            if not xs:
                no_rows[key] += 1
                continue
            out["all"][key].append(max(xs))
            if not m["is_admin"]:
                out["non_admin"][key].append(max(xs))

    print(f"messages={len(msgs)} users={len(users)} admin_msgs={sum(1 for m in msgs if m['is_admin'])} "
          f"laneb_rows={len(rows)}  floor={INFERRED_SCORE_FLOOR}")
    print(f"messages with NO Lane B row to compare: as_of_message={no_rows['as_of']} active_now={no_rows['now']}")
    for who in ("all", "non_admin"):
        print(f"[{who}] max cosine per message")
        summary("as_of_message", out[who]["as_of"])
        summary("active_now   ", out[who]["now"])


asyncio.run(main())
