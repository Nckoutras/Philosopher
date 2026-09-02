# GREAT MINDS — Handoff Brief v27

> **Companion to:** `PROJECT_STATE_v27.md`, `IMPLEMENTATION_BACKLOG_v27.md`.
> **Verification SHA:** `7a0ab2e0`. **Date:** 2026-09-02.
> v26 files preserved byte-identical.

---

## Where things stand

**P0 is 12 of 13.** One item remains: **#6, letter delivery.** It is not blocked on
code — it is blocked on an observation that has not happened yet.

Everything else in P0 is merged and on `main`. The suites at `7a0ab2e0`: backend
**912 passed / 0 failed** with an empty CI quarantine file, web unchanged at 13
failed / 227 passed and 11 `tsc` errors.

---

## 1. First thing next session: the Monday letter result

**The Sunday 2026-09-06 18:00 UTC cron run is the gate.** Verified in code:
`workers/cron.py:262` is `CronTrigger(day_of_week="sun", hour=18, minute=0)`, id
`weekly_letter`, which enqueues `generate_weekly_letter_task` per eligible user.

Check the inbox Monday. **The result decides the shape of the #6 brief, so do not
write the brief before the result exists.** Two outcomes:

- **Letters arrived.** #6 narrows to the durability work below — the delivery path
  works and the problem is that nothing can prove it did.
- **Letters did not arrive.** #6 starts as a diagnosis, and the durability work
  follows the fix. Per P-06, do not modify code in response to "it didn't arrive"
  until the cause is identified: check Sentry first (it is live now, which was not
  true the last time this failed), then the worker logs, then `weekly_letters` rows.

### What the #6 brief is expected to cover, once the result is in

Four pieces, in dependency order:

1. **cron → ARQ.** Dispatch currently runs on APScheduler **inside the API process**
   (`setup_cron` is called from `main.py`'s lifespan). That means a restart between
   18:00 and completion drops the run silently, and there is no record it was
   attempted. Moving dispatch onto the worker makes it a job with a lifecycle.
2. **`job_run` table.** The 0/22 incident was undetectable because nothing recorded
   that the job ran, how many users it selected, or what happened to each. A row per
   run — started, finished, counts, error — turns "did the letters go out?" from an
   inbox check into a query.
3. **Catch-up.** A missed Sunday currently means those letters never exist. With a
   `job_run` record, a catch-up path can find the gap and fill it.
4. **Deep link.** The email should land the reader on the letter itself.

Note that #587 changed the diagnostic situation materially: the startup swallow at
`main.py` now calls `capture_exception`, so an ARQ/cron startup failure — the exact
shape of a silently dead queue — reaches Sentry instead of only a warning line.

---

## 2. Then: P1 begins with an investigation, not a PR

**P1–P3 are deliberately not decomposed into PRs, and should not be.** Writing briefs
for work that has not been investigated produces briefs built on assumptions, which
is precisely what CLAUDE.md Rule 1 exists to prevent. Three separate items this
session had their scope corrected *after* investigation contradicted the brief:
#588's soft-delete policy premise, #591's "all three paths", and #592's counting
basis. In each case the investigation was cheap and the assumption was wrong.

**P1 opens with a Memory-v2 investigation-only brief.** Investigation only — it
produces a report and a set of rulings to take, not a diff. Rule 1's enumeration
requirements apply in full: every service, every table, every call site in the
memory domain listed before anything is designed.

Two things that investigation should establish early, because they shape everything
after:

- **What the memory system actually does today**, read from code rather than from
  prior descriptions. `memory_service` has recall, extraction, a
  `SHIFT_CLASSIFY_PROMPT` stance comparison, and a weekly stale-memory job that
  *deactivates* rather than deletes. Whether that adds up to the "v2" that is wanted
  is the first question.
- **What TD-57 costs here.** Memory is the most database-shaped subsystem in the
  product — embeddings, recall ordering, dedup, cascade on deletion. Designing v2
  against a suite that cannot open a database connection is a real constraint, and
  it may be that TD-57 has to be paid down first rather than alongside.

---

## 3. Process notes that earned their place this session

**The three-gate merge rule held.** Diff approved, tarball verified, CI green. Worth
restating that the third gate is read from the Actions page: a PR touching only
`apps/api/**` produces **no** web run, and "no run" looks identical to "passed".

**Report the SHA `git ls-remote` returns, not the one `git rev-parse` prints.** A
tarball fetch 404'd this session against a SHA that had never been pushed. `rev-parse`
answers about the local repository; `ls-remote` answers the question actually being
asked, which is whether the remote has it.

**Stage explicit paths, never `-A`.** Held all session; every PR's staged count was
checked against the reported file count before committing.

**Copy is founder-approved before render code.** Used twice — #588's deletion modal
and #589's Greek crisis response — with a `PENDING_COPY` tripwire failing the suite
until the approved strings landed. Both tripwires remain in the tree, so a future
placeholder cannot ship.

**When a ruling names more surface than the code has, check before executing.** Say
so and implement what is real, rather than either doing a fraction silently or
inventing work to match the letter of the instruction.

---

## 4. Standing risks worth carrying into the next session

1. **The Greek lexicon is unreviewed by a native speaker** (TD-61). 210 entries are
   live in a safety gate for the product's first audience.
2. **The fair-use cap's notice has never rendered** (TD-63), so its first reader
   will be a paying customer. The 150 threshold is 1.85× the heaviest recorded usage
   day — a figure measured in #11's Step-1 investigation, not re-read this rotation.
3. **OPS-006 blocks the live-mode switch** — Stripe charges €149 against a page that
   says €99.99. Nothing about going live should proceed until a checkout is observed
   charging the displayed amount. **This is the revenue gate:** the accountant →
   Stripe live-mode switch (NIKOS-ACTION 6) is the single action that makes the
   product revenue-capable, and it sits behind this.
4. **No test opens a database** (TD-57), which is now load-bearing under billing
   lifecycle, cascade deletion and the export.

---

## 5. Documents

`PROJECT_STATE_v27.md` — what is true at `7a0ab2e0`, with the method per claim and an
explicit FOUNDER-REPORTED section for the five production observations this rotation
could not verify.

`IMPLEMENTATION_BACKLOG_v27.md` — TD-57 … TD-63, OPEN-DECISION, OPS-006, UX-01
(closed) and UX-02, each re-verified against the code before being written, plus the
standing NIKOS-ACTIONS.

v26 and earlier are preserved byte-identical. Nothing in them was edited.
