# GREAT MINDS — Handoff Brief v26

> **Range covered:** `#549` … `#563`. **Verification SHA:** `ef3e2d89`. **Date:** 2026-08-23.
>
> This rotation's own PR number is not asserted. Numbers quoted here were executed this
> rotation; methods are in `PROJECT_STATE_v26.md §2`.

---

## Where the project is

A clean cycle. Four threads opened and closed: observability on token spend, the ring-true
safety gate, backend CI, and the 29 red tests.

The backend suite is **578 passed, 0 failed**, and the CI baseline file is at **zero
entries** — the first time this repo has had that property. Any backend failure is now a
CI failure, with no list to consult and no exceptions to weigh.

**The launch blockers did not move.** OPS-006, the TD-28 operational remainder, and
OPS-002/003 are exactly where v25 left them, and none could be re-verified: no database,
no Stripe, no Actions access this session. This cycle was infrastructure and correctness,
not launch readiness.

---

## Queue for the next session

### 1. Read the backend CI run on `main` — do this first

The single highest-value action available, and it costs one glance.

Backend CI has existed since #558 and **no run has ever been read**. It pins Python
**3.12** (matching `apps/api/Dockerfile`); the baseline was captured on **3.10.4**, the
only interpreter on the dev machine. #558's decision B set the checkpoint and it was never
performed.

Open the Actions tab, find the `pytest against committed baseline` step, and read its
summary block — it prints `new failures` and `fixed (prunable)` explicitly:

- `new failures: 0` and `fixed: 0` → the baseline transferred; TD-50 closes fully.
- `fixed: N` → those pass on 3.12; prune them, one commit.
- `new failures: N` → **`main` is red right now.** Report each one individually before
  adding anything to the baseline. A failure that appears on the production Python version
  and not on 3.10 may be a real defect, not harness noise.

With the baseline at zero there is nothing absorbing a divergence. Until this is read, the
claim "backend CI works" is unverified.

### 2. Verify the token columns after the next deploy

Migration `054_token_components` applies automatically (`alembic upgrade head` runs on
container start). Once a few messages land, run the query in
`IMPLEMENTATION_BACKLOG_v26.md §3` — it closes **TD-44** and produces the first data that
can price a message in cost rather than volume.

Expect `cache_read_tokens = 0` on free-tier rows. That is correct, not a bug.

### 3. Decide what `tokens_used` is for

The components are stored; no threshold has been chosen. Two things to settle before weeks
of data accumulate under an unstated definition:

- Cost weighting is a SQL concern now (1.0× / 1.25× / 0.1×). Nothing needs to change in
  code to apply it.
- `complete()` calls — memory, insights, council briefs, titles — are still unlogged, so
  the column covers user-visible assistant messages only. TD-55's redundant title spend is
  invisible in it.

### 4. Then: the launch blockers

OPS-006 (Stripe price objects) is the one with a revenue consequence — display and charge
disagree. It needs Stripe access, which this session did not have.

---

## What to distrust in this document

**Everything requiring a live system.** No database, no Stripe, no Actions run was reached.
Four items are marked ⚠️ UNVERIFIED in `PROJECT_STATE_v26.md §2` and they are the ones most
likely to be wrong.

**v25's §5–10 and TD-01 … TD-42.** UNCARRIED — not re-verified, so not restated. Treat
`IMPLEMENTATION_BACKLOG_v24/v25` content as unverified rather than as background truth.

**Anything phrased as "unchanged".** If this document says a thing is true, a method is
next to it. If there is no method, the claim is marked.

---

## Three things worth carrying into how the next session works

**A carried explanation for a failing test is a doc claim like any other.** TD-45's
one-line description was right about 17 tests and wrong about 4 of the 5 remaining
families. Diagnosing per test found five distinct causes, three stale product
expectations, one shipped behaviour with no test at all, and one live migration gap — none
of which a description-driven repair would have surfaced. Now in `CLAUDE.md`'s Failure Log.

**A repaired test's assertion is unverified text.** When a harness fix lets a test reach
its assertion for the first time in months, that assertion has not been checked against the
code in as long. `git log -L` the condition before trusting it.

**Shipping a mechanism is not verifying it runs.** Backend CI, seven merges, zero runs
read. Queue item 1.

---

## Files this rotation

- `PROJECT_STATE_v26.md` — verified state, what the test repair found, corrections,
  changelog, lessons.
- `IMPLEMENTATION_BACKLOG_v26.md` — closed items with evidence, open items by priority,
  open questions.
- `SCREENS_TRACKING_v14.md` — **one screen added** this range (`/auth/welcome`, #553) plus
  three modified. v13's premise of "zero screens" does not hold for this cycle.
- v25 files preserved byte-identical; `SCREENS_TRACKING_v13.md` likewise.
