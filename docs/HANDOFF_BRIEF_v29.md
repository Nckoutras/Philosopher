# GREAT MINDS — Handoff Brief v29

> **Verification SHA:** `93aa06932de12a03c4c523f47733bf9897c44d0f`.
> **Date:** 2026-09-11.
> **Companions:** `PROJECT_STATE_v29.md`, `IMPLEMENTATION_BACKLOG_v29.md`,
> `reports/STRATEGY_P2_RETENTION_2026-09.md`.

---

## Where things stand

**One production defect consumed the cycle, and it was worth it.** On 2026-09-10 an
English conversation titled *"Illusion of information control"* produced an
**Indonesian** council matter — twice, mobile at 10:27 and desktop at 10:20, with
**different sentences** each time. Both founder-observed in production; **neither was
ever reproduced offline** (#626 records that there was no transcript and no API key,
and that nothing rests on a repro). The per-tap difference is what proved the matter
was composed per request rather than stored. That text is not display copy: it lands
in the Council matter **textarea**, so the person submits, as their own words, a
sentence they never wrote. The cause was not a bug in a function but a **construct**
— a prompt asking a model to *infer* its output language, with nothing reading the
answer — and the same construct existed in **seventeen more places**. Six PRs (#626,
#627, #628, #630, #631, #632) closed it.

**No Greek-language defect was ever observed.** Greek appears in this class only as
the *other direction* the guard must catch — the one the script test covers for free
at any length.

**The end state is a test, not a sentence.** No prompt in the product asks a model to
infer its output language, and
`tests/test_last_prompt_language.py::test_every_prompt_in_the_product_is_enumerated_here_or_already_done`
fails if a prompt-bearing module appears that is not accounted for. Run it rather
than trusting this paragraph.

**Trust surfaces closed:** Google OAuth enabled and brand-verified (OPS-008),
`api.thewiseroom.app` (OPS-009), the two email defaults that pointed at a dead
product name (#629), and the Pro-subscriber-sees-upgrade-wall defect on the
counterview fair-use cap (#624).

**Hygiene closed:** TD-58, TD-60, TD-61, TD-63, TD-64, TD-69, and **all 26 stale
remote branches** — `git ls-remote --heads origin | grep -v main | wc -l` returns
**0**.

**Suites at `93aa0693`:** backend **1716 passed / 45 skipped / 0 failed** with an
empty CI quarantine file; web **13 failed / 272 passed** — the same 13 as v26–v28,
with 24 more passing — and **11 `tsc` errors**; `alembic heads` a single head at
`059_job_run`.

**⚠️ One premise the next reader must not inherit.** The "Greek-first audience"
framing in `HANDOFF_BRIEF_v28:199` and `IMPLEMENTATION_BACKLOG_v28:97` is **FALSE**.
Founder decision, 2026-09-11: **the target audience is English-speaking**, and Greek
support is a safety net rather than go-to-market. It justified the *priority* of two
items, both now closed, so nothing is left resting on it — but a future "we should
also do X for Greek" argument no longer inherits first-audience priority from these
documents. Full correction, with the three code sites that record the decision:
`PROJECT_STATE_v29` §3c.

---

## 1. First thing next session: the Sunday 2026-09-13 result

**This is the gate on P0 #6, and it is the first run under the PR-C period
arithmetic.** Verified in code at `93aa0693`:

- `dispatch_weekly_letters` runs **Sunday 18:00 UTC**, and `WorkerSettings.timezone`
  is `UTC` set **explicitly** rather than inherited from the container.
- `catch_up_weekly_letters` runs **Monday 09:00 UTC** and looks back **exactly one
  period** (R8a).
- Both open a `job_run` row keyed `(job_name, run_key)` with **`run_key = '2026-W37'`**.

### The queries, in order

**1. Did a run open at all?**

```sql
SELECT job_name, run_key, status, started_at, finished_at,
       candidate_count, selected_count, enqueued_count, error
FROM   job_run
WHERE  job_name = 'weekly_letter' AND run_key = '2026-W37';
```

**The job name is singular** — `JOB_WEEKLY = "weekly_letter"`
(`workers/letter_dispatch.py:46`), `JOB_MONTHLY = "monthly_letter"`. Querying
`'weekly_letters'` (the table name) returns zero rows and reads **exactly like a run
that never happened**. That is the single most likely way to misread this.

**2. Did it close cleanly, and with what counts?** `status` should be `succeeded`
with `finished_at` set and the three counts populated. `candidate_count` greater than
`selected_count` is normal; `selected_count` greater than `enqueued_count` means
enqueue failures.

**3. Did letters exist, and did they send?**

```sql
SELECT id, user_id, period_start, period_end, kind, status, email_suppressed_reason
FROM   weekly_letters
WHERE  period_start >= '2026-09-07' AND kind = 'weekly'
ORDER  BY period_start;
```

The columns are `period_start` / `period_end` / `kind` — **there is no `week_start`
column** and never has been.

**4. Did they arrive, and from `hello@thewiseroom.app`?** Inbox check; nothing in the
repository can answer it.

### The five suppression reasons

`weekly_letters.email_suppressed_reason` carries exactly one of:

| reason | what it means |
|---|---|
| `localhost` | **`API_BASE_URL` was not set on the worker** (OPS-007). Not a user state. |
| `no_email` | the user row has no address |
| `opt_out` | `weekly_email_opt_out` is true |
| `already_sent` | a send was already recorded for this letter |
| `send_failed` | the provider rejected it |

The column deliberately carries **no CHECK constraint** (R2a), so a sixth reason
stays a code change rather than becoming a production migration.

### If the run is missed entirely — TD-67

**The catch-up floor is `min(job_run.started_at)` per `job_name`**
(`workers/letter_dispatch.py:318`). If the very first run never opens a row, Monday's
catch-up sees **no history** and skips. That is TD-67, it applies exactly twice
(weekly this Sunday, monthly on 2026-09-30), and after those two dates it closes
itself.

**The manual remedy** is the command in
`reports/LETTER_DURABILITY_RULINGS_2026-09-07.md` §Ops — the same dispatch function
invoked with an explicit `run_key`. There is **no admin endpoint**, deliberately (R8).

**The one hard constraint:** **never invoke a weekly `run_key` earlier than
`2026-W37`.** The manual path bypasses the floor and the one-period lookback, so an
older key would write a second letter for a week already delivered under the
pre-PR-C arithmetic. The per-user dedup still holds inside the generator, but the
period arithmetic changed and the unique index cannot see that.

### RESULT: (not yet observed)

> **This section is deliberately empty. The run has not happened.**
>
> Monday 2026-09-15, fill this in with **one paragraph**: did a `job_run` row open
> for `('weekly_letter', '2026-W37')`, did it close `succeeded`, what were the three
> counts, did any letter carry an `email_suppressed_reason` and which, and did a
> letter arrive in a real inbox from `hello@thewiseroom.app`.
>
> If the run was missed, record that instead, plus whether the manual remedy was
> invoked and with which `run_key`.
>
> **Do not write an expected outcome here.** The whole value of this gate is that it
> can fail, and a pre-written result is indistinguishable from an observed one two
> rotations later.

**Only after a Sunday run proves the pattern** does R4's remainder open: the other
three dispatch jobs move to ARQ, in one PR.

---

## 2. What P2 needs before it opens

`reports/STRATEGY_P2_RETENTION_2026-09.md` carries the founder-locked skeleton,
**re-locked 2026-09-11** with one structural change: an **epistemic loop** is
inserted as item 2, before Return to This.

The start gate now reads:

| # | Condition | Status |
|---|---|---|
| 1 | #6 letter delivery merged | ✅ met — #608–#611 |
| 2 | Tranches merged | ✅ met — bank complete at 360/360 |
| 3 | **Founder** post-v2 memory read | ⏳ pending |
| 4 | First v2 Sunday letter | ⏳ pending |

**Condition 3 changed hands.** Dimitris is unavailable, so this is explicitly a
**founder** read. The strategy document names the bias rather than hiding it: the
person who built it is the person judging whether the memory reads as recognition,
and that is a weaker instrument than an outside tester. It is recorded as a known
weakness of the gate, not as an equivalent substitute.

**If either qualitative report is negative, P2 opens with v2 tuning rather than with
the build order.** That branch is in the strategy document deliberately: the point of
a gate that can fail is that failing it changes what happens next.

---

## 3. Standing risks

**The letter path has never completed a real delivery under the current arithmetic.**
Every part is tested; the one production run so far correctly found no eligible
users, which exercises dispatch and the `job_run` row but not generation, the send,
or the suppression reasons. Sunday 2026-09-13 is the first run that can exercise the
rest — and it is also the one period with no automatic catch-up.

**The revenue path is blocked on a price mismatch that lives outside the
repository.** The upgrade page says €99.99; the founder observed €149 charged.
Test-mode is closed, live-mode is not. Nothing about the live switch should proceed
until a live checkout has been observed charging the displayed amount (OPS-006).

**Several load-bearing production facts are founder-reported and leave traces nobody
has read.** Migrations applied, Sentry initialised, the worker deployed,
`BETA_GRANT_PRO_TO_ALL`'s real value. Each leaves a trace — `alembic_version`, a
Sentry release, a running process, a config value — and none was read this rotation.

**The web suite has had the same 13 failures since v26, and 11 `tsc` errors.** They
are stable and quarantined by habit rather than by policy. Stability is not
correctness: nobody has re-read them since the measurement report of 2026-08-13.

**Two new observations, neither a regression:** the insight → counterview route is
uncapped and bounded only by another feature's dedup (TD-70), and `_is_null_reply`
has no production caller (TD-71).

---

## 4. How to work here, restated

Three habits earned their place this cycle and are cheap to lose.

**Verify the premise of a brief before building on it.** Three briefs this cycle
carried a premise the code contradicted — the weekly mirror was said to read both
message roles when its query already filtered to `role == "user"`; the memory rows
were said to need an age floor when the real problem was that #627's guard logs
rather than blocks; a PR was said to be miscited when every citation in `docs/`
checks out. Each was reported before work started, and each changed the work.

**Measure on the surface the rule will run on.** The function-word floor was
calibrated on multi-sentence briefs and then applied to 10-word aphorisms, where it
rejected 20% of correct English. A threshold is only as good as the register it was
measured in.

**Content, not title, answers whether work landed.** Squash merges rewrite the SHA.
`git branch -d` refused two already-merged branches this cycle; the safe check was
`git diff main <branch>` returning empty plus a marker grep on `main`.

**One more, learned the expensive way and still true:** any Greek content sent to an
executing agent goes **base64 with a sha256**. The C1 byte range was silently dropped
once this cycle. A transport that corrupts one lexicon entry produces a safety gate
that passes its tests and misses the phrase it was written for.
