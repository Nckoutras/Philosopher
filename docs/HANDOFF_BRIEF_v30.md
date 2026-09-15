# GREAT MINDS — Handoff Brief v30

> **Verification SHA:** `bc8cd09028b5404bb8f177877bc6cdd9ecf9f2a4`.
> **Date:** 2026-09-14.
> **Companions:** `PROJECT_STATE_v29.md`, `IMPLEMENTATION_BACKLOG_v29.md`,
> `reports/STRATEGY_P2_RETENTION_2026-09.md` — **not rotated to v30, deliberately.**
> See §9.

---

## Where things stand

**P2-0 shipped end to end, and the repository was unguarded the entire time.**
Those two facts belong in the same sentence because the second is the one that
matters. A→B→C→D merged as **#642, #643 + #644 + #645, #646, #647** — verified
against `git log origin/main`, not carried from a brief. And on 2026-09-14 the
founder discovered that **`main` had no branch protection rule at all**, and never
had one since the project started. Every merge in this repository's history,
including all six above, went in without a required check. §1.

**The trajectory chain is live but has produced nothing yet, and that is correct.**
Migration 061 is applied in production — `trajectory_snapshots` exists there with
**0 rows** (read 2026-09-14). The first snapshot run is **Sunday 2026-09-20 17:00
UTC**; the first letter that can carry `<also_last_week>` is **2026-09-27**. §2.

**The build order is founder-locked**, 2026-09-14: docs v30 → ~~B6~~ → **A2** → B1
→ Γ → D2 → D3 → **cold beta**. B6 closed on verification rather than on a build
(TD-59 and TD-62 were already done — §9), so **A2 is the first build item**. Beta is
deferred past the three build phases by ruling, over a recorded objection that
Blueprint §15 places it at days 0–30. Anything not on that list does not get a
brief. §7.

**Measured at `bc8cd090`, not carried:**

| | v29 (`93aa0693`) | v30 (`bc8cd090`) | command |
|---|---|---|---|
| backend | 1716 / 45 skip / 0 fail | **1865 passed / 71 skipped / 0 failed** | `cd apps/api && python -m pytest -q` |
| CI quarantine | empty | **0 entries** (comments only, 1385 bytes) | `cat apps/api/tests/ci_baseline_failures.txt` |
| `alembic heads` | `059_job_run` | **`061_trajectory_snapshots`, single head** | `python -m alembic heads` |
| migration files | — | **61** | `ls db/migrations/versions/*.py \| wc -l` |
| web vitest | 13 fail / 272 pass | **13 failed / 279 passed** (292; 6 files fail, 39 pass) | `npx vitest run` |
| web `tsc` | 11 errors | **11 errors across 5 files** | `npx tsc --noEmit` |
| stale remote branches | 0 | **1** — `feat/period-recurrence` | `git ls-remote --heads origin \| grep -v main \| wc -l` |

The web numbers were **re-measured**, not inherited: node lives at
`AppData/Local/nodeportable/node-v20.18.1-win-x64` and is not on `PATH`. The 13
failures are the same 13 by name (DateGrouper ×2, EmptyReflections ×4,
ExistingConversationPage ×3, FilterPills ×1, QuickActionsRow ×2, SavedLineCard ×1);
seven more tests pass than at v29. `tsc` exit code 1 — checked as an exit code, not
by grepping output.

**`feat/period-recurrence` is safe to delete.** `git diff origin/main
origin/feat/period-recurrence` is deletions only plus 17 lines that are the *older*
versions of two files — the pre-#645 ISO-string bindings and the pre-#646
five-cron assertion. It carries no unmerged work. It survived because squash merges
rewrite the SHA and `--merged` therefore reports it as unmerged.

---

## 1. The root cause of every red merge: `main` had no branch protection

**This supersedes the 2026-09-01 diagnosis.** That entry concluded the gap was a
*habit* — that pre-merge verification checked the branch and never checked CI
status, and a green merge button was misread as a green build. That was true as far
as it went, and it is why the entry says the button "reflects branch-protection
settings". **It reflected nothing. There were no settings.** The button was green
because nothing could ever have made it red.

So the eight-day red CI window (runs #11–#19, four PRs merged over it) and the
#643/#644 red merges are not two incidents with two habits behind them. They are one
missing configuration, and the habit was the only thing standing in for it.

**Fixed 2026-09-14 13:30.** A classic branch protection rule on `main`, with three
required checks:

1. **pytest (live Postgres)** — the `db-tests` job
2. **pytest (baseline) + alembic single head**
3. **C-04** — migration revision id ≤ 32 chars and filename == revision id

**The first PR governed by it is the next one.** Nothing merged before 2026-09-14
13:30 was gated, this rotation's six PRs included.

**The `paths:` filter was removed the same day, and protection is why.** Until
2026-09-14 `backend-ci.yml` filtered to `apps/api/**` and its own files, so a
docs-only or web-only PR produced **no backend run at all**. Before protection that
was merely confusing — the 2026-09-01 entry's "*no run is not green*", where a PR
with no backend check looks identical to one that passed.

Under protection it is fatal. **A required check that never reports does not
resolve to "skipped": it sits at "Expected — waiting for status to be reported",
and the merge button never opens.** A docs PR would be blocked forever, with
nothing red to point at and nothing to re-run. So both filter blocks are gone and
every PR runs the suite. The repository is public, so the minutes are free.

**One thing the rule still does not change:**

- **"Re-run jobs" replays the same commit.** It does not pick up a new push. After
  pushing a fix, read the run for the **new** SHA — a re-run of the old one will
  reproduce the old result and read like a flake that cleared or didn't.

---

## 2. P2-0 A→B→C→D — shipped, and the dates that make it legible

All PR numbers verified against `git log origin/main` on 2026-09-14.

| Step | PR | Commit | What |
|---|---|---|---|
| A | **#642** | `abed48ee` | `insights.evidence` — the rows a recurrence card was derived from, kept instead of collapsed (migration 060) |
| B | **#643**, **#644** | `3a5cc191`, `815196a7` | `find_recurrences` extracted with `corpus_since` / `corpus_until` |
| B-fix | **#645** | `3b8e07db` | db_live: bind timestamptz from datetime objects, not ISO strings (TD-76) |
| C | **#646** | `e3d7ed5a` | `trajectory_snapshots` (migration 061) — table, Sunday 17:00 cron dispatch, per-user job |
| D | **#647** | `bc8cd090` | the Sunday letter reads the snapshot — `<also_last_week>` |

### The two dates, and why a quiet 2026-09-20 is correct

- **First snapshot run: Sunday 2026-09-20 17:00 UTC**, `run_key = '2026-W38'`.
- **First letter able to carry `<also_last_week>`: Sunday 2026-09-27.**

The 09-20 snapshot has **no prior week**, so its `changes_since_prior` is `None`,
so `still_recurring` does not exist, so the 09-20 letter renders no block at all.
**A quiet 2026-09-20 is the design working, not a defect**, and it is stated in
`generate_weekly_letter_task`'s docstring so the next reader does not diagnose it.

**Do not add a backfill to fill it.** A snapshot is built against the memory corpus
*as it stood at its period boundary*, and that corpus has already moved — rows have
been deactivated and conversations deleted since. A backfilled snapshot would be a
confident record of a week nobody actually looked at.

### What to check on 2026-09-20 and 2026-09-27

```sql
-- 1. Did the snapshot dispatch run?  Job name is SINGULAR.
SELECT job_name, run_key, status, started_at, finished_at,
       candidate_count, selected_count, enqueued_count, error
FROM   job_run
WHERE  job_name = 'weekly_trajectory_snapshot' AND run_key = '2026-W38';

-- 2. Did the per-user jobs land?  0 acts -> NO ROW, deliberately (not 'empty').
SELECT status, count(*) FROM trajectory_snapshots
WHERE  period_start = '2026-09-14T00:00:00+00'::timestamptz  -- Monday of W38
GROUP  BY status;

-- 3. On 09-27: does anyone have a second week?
SELECT user_id, payload->'changes_since_prior'->'counts'
FROM   trajectory_snapshots
WHERE  period_start = '2026-09-21T00:00:00+00'::timestamptz
  AND  status = 'generated';
```

`selected_count` equals `candidate_count` by construction for this job — ≥1 act is
both the eligibility gate and the selection. `NULL` counts mean the run died before
counting; `0` means it counted and found none. That distinction is 059's and it is
load-bearing.

---

## 3. Rulings recorded this rotation

**D-CONSTRAINT — `absent_since_prior` is never rendered as prose.** Founder ruling,
2026-09-14. An anchor can leave that set by slipping out of the top-5 the snapshot
stores per question — a **cap artefact** — and not because the person let anything
go. Prose built on it would state a change in someone's inner life that the data
does not support. It stays data. Enforced in three places: the builder never reads
it (`tests/workers/test_letter_standing_memory.py::test_absent_since_prior_never_reaches_the_prompt`),
the approved guardrail tells the model the same thing from the other side
(`tests/test_prompts.py::test_the_guardrail_forbids_reading_absence_as_letting_go`),
and `_build_also_last_week_block`'s docstring says why.

**D shrank because the premise did not hold.** The brief assumed the letter carried
no recurrence. It already did: `detect_recurrence` writes `Insight` rows with
`insight_type` `'pattern'`/`'shift'`, and the letter's spine query pulls every
non-dismissed insight from the window into `<what_the_room_noticed>` **without
filtering on type**. Rendering the snapshot's `recurring_questions` too would have
told the person the same echo twice in one letter. D therefore contributes exactly
one field — `still_recurring`, the one sentence the spine cannot say, because the
spine has no memory of last week.

**The `mirrors` shape duplication was ruled, not overlooked.** `trajectory_snapshots`
is column-for-column the shape of `mirrors`, including the unique index. Widening
`ck_mirrors_kind` / `ck_mirrors_status` to admit an internal record with no host, no
insight and no ring-true triplet would have made every existing `mirrors` query a
candidate for an unqualified sweep — a production risk taken to avoid a migration.
And `'failed'` is not a mirror state. Duplicated shape is acceptable; duplicated
lifecycle is not. Recorded in 061's docstring.

---

## 4. Deferred — decided, not forgotten

None of these is on the §7 build order, so **none gets a brief**. They are recorded
so the next reader finds the decision instead of rediscovering the question.

1. **Spine ↔ snapshot dedup by `memory_entry_id`.** A real join exists: `insights.evidence`
   carries the ids since #642, and the snapshot payload carries them too. Deferred
   until something needs it — D avoids the overlap by rendering a field the spine
   cannot express, rather than by de-duplicating.
2. **`new_since_prior` in the letter.** A new anchor this week is, in the common
   case, the same fact as this week's spine card — overlap, not signal.
3. **`<what_the_room_noticed>` tag-binding**, as a standalone cosmetic PR after beta
   opens. The block **is** governed — `LETTER_PROMPT:60`, "Treat these as the spine…
   never quote or restate them" — it simply is not bound to its tag the way
   `<self_portrait>`, `<what_you_know>` and `<rituals>` are. An earlier claim in this
   session that it had *no* guardrail was wrong; it came from counting occurrences of
   the tag string rather than reading the prompt. Not approved for D, correctly.
4. **`evolving_beliefs` in the snapshot payload** — blocked on the version-chain
   question. `find_recurrences`'s corpus is `is_active = TRUE`, so supersession is
   invisible to it; the shape would be a third parameter no caller passes today.
5. **`unresolved_threads`** — out. No signal for it exists.

---

## 5. Operations

### 5a. Production database identification — VERIFIED 2026-09-14, and it is a trap

**Three Supabase projects exist on the account. The one named "Philosopher" is NOT
production.**

| Project ref | Region | Name | What it actually is |
|---|---|---|---|
| **`bvzeuwzqgnqcghvqghtb`** | **us-west-2** | "nckoutras@gmail.com's Project" | ✅ **PRODUCTION** |
| `plecolxlzshkfvybszgs` | eu-west-1 | **"Philosopher"** | ❌ abandoned April scaffold |
| `smteoctlnperiactwism` | eu-central-1 | "cleo-wholesale" | unrelated, INACTIVE |

Verified by reading both schemas, not by name. **Production** (`bvzeuwzqgnqcghvqghtb`,
created 2026-05-26) holds **39 public tables** — 22 users, 1,389 messages, 994
memory entries, 26 weekly letters, 1 `job_run` row (the 2026-09-13 delivery), and
`trajectory_snapshots` present with 0 rows. **RLS is enabled on all 39**, which is
C-05 holding.

The **eu-west-1 "Philosopher"** project (created 2026-04-19) holds **20 tables, every
one with 0 rows**, on a pre-020 schema — no council, no quotes, no mirrors, no
`weekly_letters`, no `job_run`. It is a dead early instance that kept the good name.

> ⚠️ **NIKOS-ACTION, new:** that abandoned project is `ACTIVE_HEALTHY`, billable, and
> has **RLS disabled on all 20 tables**, so its anon key grants read *and write* on
> the whole schema. There is no data to leak — every table is empty — but it is a
> live writable Postgres wearing the project's name. **Recommendation: delete or
> pause it, rather than enabling RLS on it.** Enabling RLS would tidy the advisory
> and leave the real problem (a confusable, billable, writable double) in place.

### 5b. Password / credential rotation

Standing procedure, to run whenever a credential may have been exposed — a paste
into a chat, a screenshot, a log, a departing collaborator:

1. **Rotate at the source first**, before touching the app: Supabase database
   password, Anthropic and OpenAI API keys, Stripe secret + webhook signing secret,
   Resend API key, the JWT signing secret.
2. **Update Render** (API service + ARQ worker — **both**; they are separate
   services and a worker left on an old key fails silently as "letters stopped")
   and **Netlify** for anything the web build reads.
3. **Redeploy both Render services.** An env change without a redeploy is not
   applied.
4. **JWT secret rotation logs everyone out.** `users.token_version` (053) is the
   intended mechanism for invalidating sessions *without* a secret change — prefer
   it when the goal is to end sessions rather than to replace a leaked secret.
5. **Verify by reading a trace, not by assuming**: one authenticated request, one
   Stripe webhook delivery, one worker log line.
6. Record the rotation date here. Do not record the values.

### 5c. NIKOS-ACTIONS

**New this rotation, both verified above rather than reported:**

- **B7 — DELETE the eu-west-1 "Philosopher" Supabase project
  `plecolxlzshkfvybszgs`.** Delete, **not** RLS-fix. Enabling RLS would clear the
  advisory and leave the actual problem in place: a live, billable, writable
  Postgres wearing the product's name next to the real one. Evidence in §5a — 20
  tables, every one empty, on a pre-020 schema. Confirm the ref before deleting;
  production is `bvzeuwzqgnqcghvqghtb`.
- **Delete the stale remote branch `feat/period-recurrence`.** Proven to hold no
  unmerged work — see the check quoted at the top of this document. It reads as
  unmerged only because squash merges rewrite the SHA.

**Carried from `IMPLEMENTATION_BACKLOG_v29` §6 — not re-verified this rotation, and
marked as such rather than restated as fact:** Stripe live switch (OPS-006, still
blocked on the €99.99-vs-€149 price mismatch); monthly remedy if 2026-09-30 is
missed (`run_key='2026-09'`; **never** a weekly key earlier than `2026-W37`);
`support@` mailbox; DMARC; PostHog erasure.

---

## 6. Standing risks

**The monthly letter path has still never run in production.** First on 2026-09-30,
and TD-67 applies to it. One Sunday delivery (2026-09-13, 2 letters) is one
observation, not a rate.

**The revenue path is blocked outside the repository.** Upgrade page says €99.99;
founder observed €149 charged. Test-mode closed, live-mode not. Nothing about the
live switch proceeds until a live checkout is observed charging the displayed
amount.

**The web suite's 13 failures and 11 `tsc` errors are frozen, not fixed.** They are
stable — same 13 by name since v26, now with seven more tests passing beside them —
and quarantined by habit rather than policy. Stability is not correctness; nobody
has re-read them since 2026-08-13.

**The snapshot job has never run in production.** Everything in §2 is verified in
code and in schema; the first execution is 2026-09-20. Its `db_live` tests have
never executed on this machine either — no Docker, no `DATABASE_URL_TEST` — and
first ran in CI.

**Load-bearing production facts still founder-reported:** Sentry initialised, the
worker actually deployed and awake, `BETA_GRANT_PRO_TO_ALL`'s real value. Migrations
applied is **no longer** in this list — `trajectory_snapshots` existing in production
proves 061 landed.

**The evidence base under the retention work is thin, and it has not thickened.**
`IMPLEMENTATION_BACKLOG_v29` §6.3 named it: real usage is the weakest input. What
production actually holds, read 2026-09-14: 22 user rows, 220 conversations, 1,389
messages, 26 weekly letters — and the 2026-09-13 delivery reached **2** people. The
P2 start gate's condition 3 was a **founder self-read**, with the bias named rather
than hidden (`HANDOFF_BRIEF_v29` §2): the person who built the memory judged whether
it reads as recognition. Nothing since has replaced that instrument. Every phase in
§7 that lands before cold beta is designed against this same absence.

---

## 7. Build order (founder-locked 2026-09-14)

**docs v30 → ~~B6~~ → A2 → B1 → Γ → D2 → D3 → cold beta.**

| # | Item | What it is | State |
|---|---|---|---|
| 1 | **docs v30** | this document | in flight |
| 2 | ~~**B6**~~ | TD-59 privacy-rights pins | **CLOSED on verification — no build.** #638/#639 |
| 3 | **A2** | global free-cap decision | **← first build item** |
| 4 | **B1** | nightly encrypted `pg_dump`, GitHub Actions | |
| 5 | **Γ** | engagement loops — Blueprint §11, in the locked order below | |
| 6 | **D2** | sameness / anti-repetition (teardown churn #2) | |
| 7 | **D3** | verify memory-v2 dedup | |
| 8 | **cold beta** | | |

> ✅ **B6 IS CLOSED. It was verified rather than briefed, and there is no build.**
> Founder ruling 2026-09-14, on the evidence below. **The first build item is A2.**
>
> `IMPLEMENTATION_BACKLOG_v29` marks **TD-59** "*Status: OPEN. Re-verified,
> unchanged.*" That backlog was written in **#633**; **#638** and **#639** merged
> after it. TD-59's description is "No test pins the privacy policy against the
> implemented rights". Fifteen now do, one per Art. right at §7 — access,
> rectification, erasure, portability:
>
> ```
> $ cd apps/api && python -m pytest tests/test_privacy_policy_claims.py -q
> 15 passed, 21 warnings in 3.03s
> ```
>
> **TD-62** is the same story, and its own entry supplies the command. The backlog
> records the output as **0**; the completeness guard landed in **#636** and #646
> extended it:
>
> ```
> $ cd apps/api && grep -c "completeness\|mapped class\|__mapper__" tests/test_data_export.py
> 9
> ```
>
> Both re-run 2026-09-14 at `bc8cd090`. This is the 2026-08-18 failure caught
> mid-flight — two items marked "re-verified" by a document that predates the PRs
> that closed them — and it cost one grep instead of one brief. See §9.

**Γ runs in this locked P2 order**, and it is an order rather than a list:

1. epistemic loop
2. Continue the Thread
3. letter continuity
4. loop-closure analytics
5. Return to This
6. Council v2
7. portrait versions

**The FIRST brief in Γ is an INVESTIGATION, not a build: enumerate the existing
PostHog events.** Loop-closure analytics is item 4 and cannot be specified against
an unknown event set, and CLAUDE.md Rule 1 requires the enumeration before the
design in any case. Anything already instrumented that Γ would re-instrument is the
finding that changes the work.

### The disagreement, recorded

**Cold beta is deferred past Γ, D2 and D3 by founder ruling.** The planning
assistant disagreed: **Blueprint §15 places beta at days 0–30**, and this ordering
puts it after three more build phases.

This is recorded because it was a **choice**, not an oversight — the founder heard
the objection and ruled. A future reader finding beta late should not reopen it as a
mistake, and should not treat Blueprint §15 as having been forgotten.

The standing counter-argument, for whenever it is next weighed, is the last
paragraph of §6: the retention work's evidence base is one founder self-read plus a
single Sunday that reached 2 people, and every phase added before beta is designed
against that same absence. That is an argument about sequencing, not a reason to
revisit a settled ruling on its own.

### What this replaces

Earlier drafts of this document carried a **BUILD FREEZE** — "no new feature PRs
until cold beta has users". That is **superseded** by the order above. Feature work
continues; it is sequenced rather than stopped. Anything not on the list still does
not get a brief.

---

## 8. How to work here, restated

The four habits from v29 §4 stand — verify the premise of a brief before building on
it; measure on the surface the rule will run on; content not title answers whether
work landed; Greek content travels base64 + sha256. Three additions.

**"Pushed. Holding." must say "PR not yet opened — founder opens."** A pushed branch
is not a pull request and is not merged. The phrase "pushed, holding" has read as
"waiting for review" when nothing existed to review. State the branch name, state
that the PR is not yet open, and state that opening it is the founder's step.

**The planning assistant verifies tarballs directly.** `curl` the codeload tarball
for the branch and `diff -rq` it against the stated base. **A CC diff summary is no
longer the gate** — a summary is a claim about a diff, and this rotation is the one
where a claim about a diff was the thing that needed checking.

**A fixture that is present is not a fixture that is correct.** TD-76 was three
misses on one file, in sequence: a missing column, then a column present with the
wrong type, then a timestamptz bound from an ISO string. Each fix revealed the next.
C-06 says a mock must set every field the code reads; TD-76 extends it — **every
field, with the right TYPE**, checked against the model rather than against what the
previous failure happened to demand.

---

## 9. What this rotation did NOT do, and why

**`PROJECT_STATE` and `IMPLEMENTATION_BACKLOG` were not rotated to v30.** v29's
remain the current companions.

This is deliberate and is the failure log's own rule applied to itself. Rotating 1,045
lines by copying them forward is precisely what produced the 2026-08-18 entry — a
closed tech-debt item carried as open through eight rotations, and "RLS DISABLED"
carried from v8 to v24 while RLS was in fact enabled. With the next work already
sequenced in §7, a copy-forward would add no information and would re-expose every
claim in those files to being restated without evidence.

**Founder approved this scope on 2026-09-14**, so it is a ruling rather than an
executing agent's judgement call. `PROJECT_STATE_v29` and
`IMPLEMENTATION_BACKLOG_v29` stay current until a rotation re-verifies them
claim by claim.

### Carried-claim correction: TD-59 and TD-62 are CLOSED

Both are recorded in `IMPLEMENTATION_BACKLOG_v29` §2 as "**Status: OPEN.
Re-verified, unchanged.**" Both are closed, and were already closed when that line
was written forward. The backlog landed in **#633**; the PRs that closed them
merged after it.

| Item | Closed by | Verification command | Backlog says | 2026-09-14 at `bc8cd090` |
|---|---|---|---|---|
| **TD-59** — no test pins the privacy policy against the implemented rights | **#638**, **#639** | `cd apps/api && python -m pytest tests/test_privacy_policy_claims.py -q` | OPEN | **15 passed** — one per Art. right at §7 |
| **TD-62** — no export completeness guard | **#636** (extended by #646) | `cd apps/api && grep -c "completeness\|mapped class\|__mapper__" tests/test_data_export.py` | **0** | **9** |

TD-62 is the sharper of the two: the entry states its own falsifying command and
records the output. Nobody re-ran it. That is the 2026-08-18 lesson in one line —
**a doc claim repeated without re-verification is evidence about the previous doc,
not about the system** — and "Re-verified, unchanged" is the exact phrase the lesson
warns about, because it asserts the check happened.

**Consequence:** B6 left the §7 build order without a brief being written; A2 is the
first build item. A v30 backlog produced by copy-forward would have carried both as
open and B6 would have been briefed.

**For whoever rotates the backlog next:** re-run each entry's own stated command.
Treat every "re-verified" in the v29 text as a claim about 2026-09-11, not about the
code — the same way this document treats its own §5c carry-forwards.

**What was re-verified for this document**, each with the command in the table above
or beside the claim: the six PR numbers, the backend suite, `alembic heads`, the
migration count, the CI quarantine file, the web vitest and `tsc` state, the stale
branch and whether it holds unmerged work, and the identity and schema of all three
Supabase projects.

**What was NOT re-verified and is carried explicitly as unverified:** the §5c
NIKOS-ACTIONS, the €99.99/€149 price mismatch, Sentry initialisation, the worker's
deploy state, and `BETA_GRANT_PRO_TO_ALL`. Each is marked where it appears. None
should be repeated in a v31 without being read first.

**The branch protection rule itself is founder-reported.** There is no `gh` CLI on
the working machine, so the rule and its three required checks could not be read
from the API. The first PR after 2026-09-14 13:30 will demonstrate it — or fail to,
which is itself the check.

---

## 10. Corrections to carry into v31 (added 2026-09-15, Γ-7)

Three claims about the Council were in circulation during Γ-7 and are wrong or
stale. They are recorded here rather than in the next rotation because a
correction that is not merged does not exist — the 2026-08-18 corollary.

**1. "Day 1 = day 365" and "one line to call" are NOT teardown quotes.** Both
were attributed to `docs/reports/The-Wise-Room-Teardown_2026-08-25` in a brief.
Neither phrase appears in that document; they are handoff-carried paraphrase. The
underlying observation is sound and independently confirmed in code — no council
session receives anything from a prior one — but **do not re-quote them as the
teardown's words.**

**2. The teardown's actual Council line is SUPERSEDED.** It says *"chat → memory
→ Council is not connected at all"*. That was true when written and is false now:
`council_service.py` calls `memory_service.recall(db, user_id, effective_matter)`
at the synthesis step (#598 / PR-2, Memory-v2 Ruling #4). What Council still lacks
is memory of **its own prior verdicts**, which is a different gap with a different
fix. A reader who takes the teardown at face value will re-derive a gap that is
half closed.

**3. `memories=[]` in the member prompt is LOAD-BEARING — do not "fix" it.** The
four member calls pass empty memories deliberately (Ruling #4: members meet the
matter cold, synthesis recalls). It is also what keeps the member prompt static
per (persona, role), which `cache_whole_system` depends on: per-user text in that
prefix forfeits the prompt cache across all four Sonnet calls, on the most
expensive ritual in the product.

This is **already pinned by tests** — `tests/services/test_council_synthesis_memory.py`
section (b), two tests, one asserting no member prompt carries memory and one
asserting nothing per-user reaches them at all so the cache holds. Γ-7 added no
new pin because the existing one is better than the one that would have been
written. If a future item needs prior-verdict context, **the synthesis step is the
only admissible injection point.**

### Council v2 — deferred, with its trigger metric

Verdict memory is deferred to post-beta (founder ruling, 2026-09-15) on numbers
read that day: **55 sessions, 55 cases, 6 users, 3 with more than one session, 9
saved verdicts.** Case reuse is **0/55** — `CouncilCase.session_count` and
`CouncilSession.session_number` are multi-session scaffolding that no code path
has ever exercised; every council creates a new case at `session_number=1`.

Three returning users cannot say what is worth remembering. The trigger metric is
`users_with_more_than_one` from the §5 SQL in the Γ-7 investigation; the query
belongs in `RUNBOOK_LOOP_METRICS.md` when someone next touches it.

What shipped instead is the link: `council_cases.insight_id` (065), so a
nudge-sourced council records **which** insight opened it. That was the one piece
of the item with no dependency on volume.
