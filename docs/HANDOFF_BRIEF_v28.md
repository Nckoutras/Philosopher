# GREAT MINDS — Handoff Brief v28

> **Verification SHA:** `e840053ceaadfba3b12c21164f98e949152c4ff4`.
> **Date:** 2026-09-08.
> **Companions:** `PROJECT_STATE_v28.md`, `IMPLEMENTATION_BACKLOG_v28.md`,
> `reports/STRATEGY_P2_RETENTION_2026-09.md`.

---

## Where things stand

**All three of v27's open threads closed this cycle.**

**P0 is 13 of 13 by merged work.** #6, letter delivery, shipped in four PRs
(#608–#611) with its rulings committed verbatim at
`docs/reports/LETTER_DURABILITY_RULINGS_2026-09-07.md`. **The work is merged; the
observation is not made.** The gate is the Sunday 2026-09-13 run — see §1.

**P1 (Memory-v2) closed across #602–#606.** Hybrid recall with two lanes, the SET
NULL cascade, and `<what_you_know>` in both letter kinds. Ruling #10 was honoured
first: #600 built the live-Postgres CI fixture before any PR touched DDL or recall
SQL, which is why TD-57 is now *partially paid* rather than open in full.

**Ruling #3 closed at 360/360.** Every question in the bank carries authored
`pill_weights`; the legacy per-tag fallback is unreachable for real questions and is
now named as tolerance rather than as an active path (TD-66).

**Suites at `e840053c`:** backend **1099 passed / 0 failed** with an empty CI
quarantine file; web **13 failed / 248 passed** — the same 13 as v26 and v27, with
#615's 21 new tests passing — and **11 `tsc` errors**; `alembic heads` a single head
at `059_job_run`.

**One correction is worth carrying even though it is now closed.** The locked-persona
paywall change **was unmerged at `076f74b7`** — carried as merged, found absent by a
content check — and **merged as #615 during this rotation** (`PROJECT_STATE_v28`
§5a). A free user tapping a locked mind now reaches the paywall rather than an error
toast. The reason it stays in this brief: a smoke test on a preview deploy is
evidence about the branch, and under squash merges only content can tell you whether
work landed on `main`.

---

## 1. First thing next session: the Sunday 2026-09-13 result

**This is the gate on P0 #6, and it is the first run under the PR-C period
arithmetic.** Verified in code at `076f74b7`:

- `dispatch_weekly_letters` runs **Sunday 18:00 UTC**, and `timezone` is set
  explicitly to UTC on `WorkerSettings` rather than inherited from the container.
- `catch_up_weekly_letters` runs **Monday 09:00 UTC** and looks back **exactly one
  period** (R8a).
- Both open a `job_run` row keyed `(job_name, run_key)` with `run_key = 2026-W37`.

**What to read, in order:**

1. Does a `job_run` row exist for `('weekly_letter', '2026-W37')`? **The job name is
   singular** — `JOB_WEEKLY = "weekly_letter"` (`workers/letter_dispatch.py:46`),
   and `JOB_MONTHLY = "monthly_letter"`. Querying `'weekly_letters'` (the table
   name) returns zero rows and reads exactly like a run that never happened.
2. Did it close `succeeded`, with `candidate_count` / `selected_count` /
   `enqueued_count` populated?
3. Did letters actually arrive, and from `hello@thewiseroom.app`?
4. If any were suppressed, what does `weekly_letters.email_suppressed_reason` say?
   The five permitted values are `localhost`, `no_email`, `opt_out`, `already_sent`,
   `send_failed` — and `localhost` there means `API_BASE_URL` was not set on the
   worker (OPS-007).

**If the run is missed entirely, mind TD-67:** the catch-up floor is
`min(job_run.started_at)` per job, so if the *very first* run never opens a row,
Monday's catch-up sees no history and skips. The remedy is the manual command in the
rulings doc's Ops section with `run_key='2026-W37'`.

**The one hard constraint:** **never invoke a weekly `run_key` earlier than
`2026-W37`.** The manual path deliberately bypasses the floor and the one-period
lookback, so an older key would write a second letter for a week already delivered
under the pre-PR-C arithmetic. The per-user dedup still holds inside the generator,
but the period arithmetic changed and the index cannot see that.

**Only after a Sunday run proves the pattern** does R4's remainder open: the other
three dispatch jobs move to ARQ, in one PR.

### The domain cutover — steps 1–2 DONE, step 3 remains

**Completed 2026-09-08** (FOUNDER-REPORTED): `thewiseroom.app` is live on Netlify
with a Let's Encrypt certificate; `FRONTEND_URL` is set on **both** Render services;
`NEXT_PUBLIC_BASE_URL` is set on Netlify and the web app has been redeployed; OTP
login on `https://thewiseroom.app` lands on `thewiseroom.app/app/today`. The live
`metadataBase` is therefore correct and the user-visible half is closed.

**Step 3 remains — the TD-69 chore PR.** Untrack `apps/web/.env.production` (it pins
a stale Vercel preview host) and change the `layout.tsx:40` fallback from
`https://philosopher.app` to `https://thewiseroom.app`. Its own PR, per P-02. It is
hygiene rather than a fix — the dashboard value is what takes effect — but the repo
still contains two dead hosts that will be believed by the next reader, or by any
build where the dashboard value is absent.

**While you are in the dashboards, check OPS-008.** The "Continue with Google"
button does not render on `/auth` in production. One request answers why:
`GET /api/v1/auth/methods` returns `{"google": GOOGLE_OAUTH_ENABLED and
bool(GOOGLE_CLIENT_ID)}`, so a `false` there distinguishes the flag being off from
the credentials being unset. Both default off, and **the flag is a separate
condition from the credentials** — setting the id and secret alone leaves the button
hidden.

---

## 2. What P2 needs before it opens

`reports/STRATEGY_P2_RETENTION_2026-09.md` carries the founder-locked skeleton. Its
start gate has four conditions, two of which are already met:

- ✅ #6 merged.
- ✅ Tranche A merged (and B and C after it — the bank is complete).
- ⏳ Founder qualitative report (a): a tester's post-v2 memory read.
- ⏳ Founder qualitative report (b): the first v2 Sunday letter.

**If either qualitative report is negative, P2 opens with v2 tuning rather than with
the build order.** That branch is in the strategy document deliberately: the point of
a gate that can fail is that failing it changes what happens next, not that it delays
the same plan.

**P2 is not decomposed into PRs and must not be.** Each item in the build order is
one paragraph of intent. CLAUDE.md Rule 1 requires an investigation-only pass before
any of them becomes a brief — enumerate what exists in the domain first, report,
then design. The Threads item is explicitly the investigation flagship.

---

## 3. Process rules that earned their place

**The three-gate merge rule.** Diff approved, tarball verified, **CI green read from
the Actions page**. The third is the one that cost eight days in the 2026-09-01
failure-log entry, and "no run" is not "green" — a docs-only PR triggers no backend
run at all, and a PR that shows no check looks identical to one that passed.

**This rotation is NOT one of those.** It touches `apps/api/observability.py`,
`apps/api/services/self_portrait.py` and two test files, so `backend-ci.yml`'s
`paths:` filter matches and backend CI **will** run. All three gates apply in full,
and the third must be read from the Actions page rather than inferred from a green
merge button.

**CI is the authority where local cannot run.** There is no local Postgres here, so
`db_live` revert-verify legs are read from CI, as D-1's leg (a) records. Say which
authority answered a question rather than implying both did.

**Copy approval precedes implementation.** All four documents in this rotation were
posted in full for approval before the PR was opened. Same rule as prompt and UI
copy: approve the words, then write them into a diff.

**Rulings are committed the same day they are locked.** R10 required it for the
letter rulings and it paid immediately — R2a, R8a and R9a were added to the same file
during execution, so the refinements live next to what they refine instead of in a
chat log. A ruling that is not in the repo does not exist, for the same reason a doc
that is not merged does not exist.

**Revert-verify.** Restore the original code, watch the test fail for the stated
reason, restore the fix. Used twice this cycle — once on the widened CHECK
constraint, once on the two repointed portrait tests, where restoring the original
`next(...)` lines produced exactly two `StopIteration` failures. It is the difference
between "the tests pass" and "the change is load-bearing".

**Re-verifying someone else's count means running their command, not your reading of
their sentence.** This rotation twice "corrected" a docstring figure that was right,
once by counting a different quantity and once by counting comments as call sites.
Both were caught by the founder before the PR opened. When a number has no command
beside it, establish what was counted before concluding it is wrong — and leave the
command behind so the next person does not have to. `observability.py` is the worked
example.

**Stop when the brief and the code disagree.** Three times this cycle a brief's
precondition did not hold — the scope-pin test the tranche briefs said not to touch,
the two fallback tests that would have gone red at 360/360, and the toast PR that was
not merged. Each was surfaced before writing rather than worked around. **An
incomplete step reported is cheaper than a complete step built on a false premise.**

**Stage explicit paths, never `-A`.** Held all cycle.

**Report the SHA `git ls-remote` returns**, not the one `git rev-parse` prints.

**Per-service env checklist (OPS-007, new).** The worker inherits nothing from the
API. Before any deploy that adds or changes an environment variable, confirm it on
**both** services and record the answer even when it is "not needed there". The first
three rows are `SENTRY_DSN`, `API_BASE_URL` and `FROM_EMAIL` — each of which has a
default that degrades silently rather than failing loudly.

---

## 4. Standing risks

**The letter path has never completed a real delivery under the current
arithmetic.** Every part is tested, and the one production run so far correctly found
no eligible users — which exercises the dispatch and the `job_run` row but not the
generation, the send, or the suppression reasons. Sunday 2026-09-13 is the first run
that can exercise the rest, and the first period is also the one with no automatic
catch-up.

**The Greek safety lexicon has never been read by a Greek speaker.** 210 entries
across four bands, 73 in Greek script, passing their tests and never reviewed by a
native reader — for a product whose first audience is Greek. TD-61, and the
highest-value review item in the backlog.

**The revenue path is blocked on a price mismatch that lives outside the
repository.** The upgrade page says €99.99; the founder observed €149 charged.
Test-mode is closed, live-mode is not. Nothing about the live switch should proceed
until a live checkout has been observed charging the displayed amount (OPS-006).

**Several load-bearing production facts are founder-reported and leave traces nobody
has read.** Migrations applied, Sentry initialised, the worker deployed at the #611
SHA, `BETA_GRANT_PRO_TO_ALL`'s real value. Each leaves a trace — `alembic_version`, a
Sentry release, a running process, a config value — and none was read this rotation.
They are listed in `PROJECT_STATE_v28` §2, and the first three are the ones to check
first if behaviour ever looks wrong.

---

## 5. Documents

| Document | What it is for |
|---|---|
| `PROJECT_STATE_v28.md` | What this cycle did, measured state, corrections, lessons, changelog `#593`…`#614` |
| `IMPLEMENTATION_BACKLOG_v28.md` | Re-verified tech debt TD-57…TD-69, OPEN-DECISION, OPS-006/007, UX-01/02, NIKOS-ACTIONS, the stale-branch checklist |
| `reports/STRATEGY_P2_RETENTION_2026-09.md` | The P2 skeleton and its start gate |
| `reports/LETTER_DURABILITY_RULINGS_2026-09-07.md` | R1–R10, R2a/R8a/R9a, the manual catch-up runbook |
| `reports/MEMORY_V2_DESIGN_2026-09-03.md` | The ten Memory-v2 rulings verbatim, and the design behind #602–#606 |
| `CLAUDE.md` | Investigation protocol, production safety rules, the failure log |
| `SKILL.md` | How a unit of work runs, brief to push |

v27 files are preserved byte-identical.
