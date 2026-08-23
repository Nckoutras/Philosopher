# GREAT MINDS — Project State v26

> **Range covered:** `#549` … `#563` (15 squash-merges on `main` since `cace1016`).
> **Verification SHA:** `ef3e2d89`.
> **Date:** 2026-08-23.
>
> **This rotation's own PR number is deliberately not asserted**, and no unmerged
> work is described as if it existed. The range above is what is on `main`.
>
> **Companion documents:** `IMPLEMENTATION_BACKLOG_v26.md`, `HANDOFF_BRIEF_v26.md`,
> `SCREENS_TRACKING_v14.md`. v25 files are preserved byte-identical.

---

## ⚠️ PROVENANCE

**Every claim below is either VERIFIED THIS ROTATION with its method stated inline, or
explicitly MARKED UNVERIFIED / UNCARRIED.** "Unchanged." is not evidence and is not used
as such.

**Methods used:** executed `pytest` / `vitest` / `tsc` at `ef3e2d89`; `git log` and
`git diff --name-status` over the range for the delta; live code reads; the persona
registry and postprocessing checks **executed in-process**, not read from notes.

**No database was consulted this rotation.** The Supabase MCP connector disconnected
mid-session and did not return. Every claim that would require live data is marked
UNVERIFIED, not softened. This is the single largest gap in this document.

**This was a clean cycle.** v25 was written during a crisis and its length reflects that.
This one is shorter because there is less to correct, not because less was checked.

---

## 1. What this cycle did

Four threads, all closed or shipped:

**Observability (#556, #561).** `messages.tokens_used` had been NULL on every row since the
table was created; the LLM client read Anthropic's usage object, logged it, and dropped it.
#556 writes the four-bucket sum. #561 adds `input_tokens`, `cache_creation_tokens`,
`cache_read_tokens` as separate columns (migration `054_token_components`), because the
buckets price differently — 1.0× / 1.25× / 0.1× — so equal `tokens_used` can mean ~10×
different spend. `output_tokens` is deliberately not stored: it is
`tokens_used − (the three)`, and that identity survives a message spanning several API
calls because every component accumulates in lockstep.

**Safety (#557).** Ring-true notes on both the mirror and self-comparison surfaces were
persisted with no safety check. Both now gate before any attribute is assigned, so a
suppressed note is never written. See §4 for the part of this that is not reachable.

**CI (#558, #559).** There was no backend CI. There are now two workflows. The pytest job
compares failures against a committed baseline **by test id, never by count** — a count
check cannot distinguish one test fixed plus one regressed from no change at all. Plus a
single-alembic-head check and a C-04 revision-id checker. #559 switched web to `npm ci` so
lockfile drift fails the build instead of being silently rewritten.

**Tests (#560, #562).** 29 backend tests had been red long enough to be grandfathered.
All 29 are repaired; the baseline file is at **zero entries**. Any backend failure is now a
CI failure. What that work turned up is in §3 — it was not only harness repair.

---

## 2. Verified state — every row executed or read at `ef3e2d89`

| Fact | Value | Method |
|---|---|---|
| Backend suite | **578 passed, 0 failed** | `python -m pytest -q`, executed |
| Backend collected | **578** | `pytest --collect-only -q` |
| CI baseline entries | **0** (file retained) | `grep -v '^#' … \| grep -c .` |
| Frontend suite | **13 failed, 119 passed (132)**; 6 of 28 files | `vitest run`, executed |
| Typecheck | **11** errors | `tsc --noEmit \| grep -c "error TS"`, executed |
| Migration head | **`054_token_components`**, exactly **1** head | `alembic heads` — ⚠️ **chain read only, DB not consulted** |
| Migration files | **54** | `ls db/migrations/versions/*.py \| wc -l` |
| Workflows | **2** — `backend-ci.yml`, `web-build.yml` | `ls .github/workflows/` |
| CI scripts | **2** — `check_pytest_baseline.py`, `check_migration_naming.py` | `ls .github/scripts/` |
| Personas | **11** | registry executed in-process |
| Missing `response_length_words` | **0** | `check_brevity` executed per persona |
| Missing `forbidden_lexicon_persona_specific` | **3** — `lao_tzu`, `niccolo_machiavelli`, `oscar_wilde` | `check_persona_forbidden` executed per persona |
| `page.tsx` files | **42** | `find apps/web/app -name page.tsx \| wc -l` |
| Screens added this range | **1** — `app/auth/welcome/page.tsx` (#553) | `git diff --name-status cace1016..ef3e2d89 -- apps/web` |

### ⚠️ UNVERIFIED this rotation — four items, not softened

- ⚠️ **Live `alembic_version`.** The chain says `054_token_components`. Whether production
  is *at* that revision was not checked — no DB access.
- ⚠️ **Backend CI is green on `main`.** The mechanism is verified present. Its actual run
  status has never been read (see §3, TD-50).
- ⚠️ **TD-44 — `cache_read > 0` in production.** Still unconfirmed. #561 built the columns
  that make it answerable; no data has been read.
- ⚠️ **OPS-004 — the API's database role.** Carried from v25, not re-checked. `DATABASE_URL`
  is not in the repo.

---

## 3. What the test repair actually found

TD-45 is recorded as "29 broken harnesses". Repairing them per that description would have
failed, and the search is worth recording because the same shape will recur.

The carried explanation — "hard-coded `execute()` indices" — was correct for the 17 in
`test_conversation_service.py`, which shared **one** root cause: a `get_user_preferences`
query inserted ahead of the history window, exhausting every ordered `side_effect` list.
All 17 died on the same `RuntimeError: async generator raised StopAsyncIteration` without
reaching an assertion.

For the remaining 12 it was **wrong about four of five families**. Verified causes:

| Family | Real cause |
|---|---|
| `routers/test_conversations.py` (1) | `_make_subscription` never set `plan`; an auto-`MagicMock` fails `not in ("pro","premium")`, collapsing the tier to `free` |
| `test_share.py` (4) | `patch()` cannot replace an already-resolved FastAPI `Depends`; all four got `403 {'detail':'Not authenticated'}` from the real authenticator |
| `test_conversations.py` (2) | The only index-shift case — a fourth query (`has_opening`) added inside the dedup branch |
| `test_counterview_rebuttal.py` (2) | `CounterviewOut` gained `still_stands` (#443) and `title` (#453); the mock supplied auto-`Mock`s, which are neither `str` nor `None` |
| `test_postprocessing.py` (3) | A hardcoded 6-slug persona list that had drifted, plus a tripwire grepping for a function the code stopped calling |

Diagnosing per test also surfaced four things a description-driven repair would have buried:

1. **Three stale product expectations.** Auto-title asserted `== 3`; #240 shipped `>= 2`.
   Two postprocessing tests described a migration state that no longer exists.
2. **One shipped behaviour with no test at all.** #244 made `create()` seed an opening on a
   dedup hit that lacks one; the pre-#244 harness could not express that state, so it was
   never covered. It is now.
3. **One live migration gap.** 3 personas still carry no forbidden lexicon (§2).
4. **A recurring mock hazard**, now **C-06** in `CLAUDE.md` — four instances in one session.

Both lessons are recorded in `CLAUDE.md` (#563): the Failure Log entry, and C-05/C-06.

---

## 4. Known state — the ring-true safety gate is not reachable from the UI

Recorded as verified fact, not as a defect to fix silently.

#557's gate is correct and cannot currently fire through the web app:

- `apps/web/app/app/mirror/page.tsx` contains **0** `textarea`/`<input>` occurrences.
- `apps/web/app/app/you-vs-you/page.tsx` contains **1**, and it is the *prompt* (already
  gated at `self_comparison_service.py:175`), not a ring-true note.
- Both clients call with two arguments — `api.setRingTrue(mirror.id, value)` and
  `api.setSelfComparisonRingTrue(comparisonId, value)` — so no note is sent, and both
  discard the response.

Method: `grep -c` on each page, plus reading both call sites.

So the API-layer protection is real and covers any future note UI or a direct API caller.
The approved crisis copy reaches nobody today. Building a note input is the work that makes
it live, and wiring the client to read `safety_triggered` is part of that work, not a
follow-up.

---

## 5. Corrections to prior docs

- **CORR-16** — `#563` (CLAUDE.md, C-05) states the RLS convention "was stated only inside
  migration docstrings". Imprecise: `IMPLEMENTATION_BACKLOG_v25.md:223` also carries a
  "C-05 — new convention (locked)" section. The argument for moving it into `CLAUDE.md`
  stands — a rotation document rotates, the protocol document persists — but the claim as
  worded is wrong.
- **CORR-17** — v25 refers to `ENVIRONMENT=production`. The setting in the repo is
  **`ENV`** (`apps/api/config.py:8`, default `"development"`). No `ENVIRONMENT` key exists.
  Whoever performs the key switch should look for `ENV`.
- **CORR-18** — the session note behind TD-53 recorded "2 unpatched `embed()` calls".
  Verified today: **3** call sites (`conversation_service.py:643, :1173, :1435`) and
  **4** real 401 responses per full suite run. The count moved because the suite grew;
  the original figure was measured before #560/#562 added tests exercising those paths.

---

## 6. Changelog — #549 … #563

| PR | What |
|---|---|
| #549 | v25 rotation (#522–#548) |
| #550 | Corrected the dual-tier entry in `CLAUDE.md` |
| #551 | `globals: true` in vitest config — **closed TD-51**; 62 → 13 failures, as v25 predicted |
| #552 | Self-portrait shows themed-category coverage |
| #553 | New-account signal on the OTP path; **adds `/auth/welcome`** |
| #554 | Same signal on the Google path |
| #555 | Installable as an Android PWA (manifest, icons, service worker) |
| #556 | `messages.tokens_used` written on assistant messages |
| #557 | Ring-true notes safety-checked before persisting — **closed A18c** |
| #558 | Backend CI: pytest baseline, single-head check, C-04 checker |
| #559 | Web installs with `npm ci` |
| #560 | TD-45 part 1 — 17 harnesses, shape-based dispatch; baseline 29 → 12 |
| #561 | Token components stored separately; migration `054_token_components` |
| #562 | TD-45 part 2 — the last 12; baseline 12 → **0** |
| #563 | `CLAUDE.md`: C-05, C-06, and the TD-45 Failure Log entry |

---

## 7. Lessons this rotation

**A carried explanation for a failing test is a doc claim like any other.** It was wrong
about four of five families. A red test is evidence that something is wrong; it is not
evidence about *what*. Now in `CLAUDE.md`'s Failure Log.

**When a repair makes a test reach its assertion for the first time in months, the
assertion is itself unverified text.** Three of these needed `git log -L` on the condition
before they could be trusted — and none of the three turned out to be a product defect.

**A mock that omits a field does not fail loudly.** It makes the code under test take a
branch nobody intended. Four instances in one session; now C-06.

**A convention outside the protocol document is one rotation from not existing.** C-05 was
locked in v25 and cited by three migrations, and still had to be rediscovered to be written
into `CLAUDE.md`. Rotation documents rotate.

**Shipping a mechanism is not the same as verifying it runs.** Backend CI has existed for
seven merges and nobody has read a single run. That is queue item 1 in
`HANDOFF_BRIEF_v26.md` for a reason: with the baseline at zero, a divergence between the
Python version measured locally (3.10.4) and the one CI pins (3.12) would leave `main` red
with nothing absorbing it.
