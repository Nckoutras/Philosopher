# Pre-Work Investigation Protocol

This document defines the mandatory investigation discipline that both the 
planning Claude (in claude.ai conversations) and the Claude Code agent must 
follow before any new code is written for this project.

This exists because on 2026-05-16 we discovered that ~3 hours of work 
building a new message endpoint had duplicated existing infrastructure 
(streaming send-message, llm_client, safety pipeline, memory extraction, 
RAG retrieval) from prior engine work. This protocol prevents that pattern 
from recurring.

## Rule 1: Feature Domain Enumeration

Before writing any brief or any code that adds, modifies, or extends a 
feature, the agent MUST enumerate what already exists in the same feature 
domain. "Look at existing patterns" is NOT sufficient — explicit 
enumeration is required.

### For HTTP endpoint work
- Fetch the live openapi.json from production OR read every router file
- List ALL endpoints in the same logical domain (e.g., "messages", 
  "conversations", "personas")
- For each existing endpoint, note: what it does, what schema it uses, 
  who calls it, whether it overlaps with the proposed new work

### For service / business logic work
- Grep the codebase for files with similar names 
  (e.g., `*_service.py`, `*_client.py`, `*_handler.py`)
- Read every file whose name suggests overlap
- Note overlaps in function names, responsibilities, dependencies

### For database work
- Query information_schema for relevant tables and columns
- Read the latest alembic migration to confirm current state
- Compare proposed schema against existing schema BEFORE designing new

### For frontend / UI work
- Grep for existing components with similar names or purposes  
- Check routing structure for related pages
- List existing screens that touch the same user flow

## Rule 2: Report Findings Before Designing

When investigation surfaces existing functionality:

**If overlap is total** (feature already exists): STOP. Surface to founder. 
Do NOT design a replacement without explicit decision.

**If overlap is partial** (some pieces exist, others missing): surface 
with concrete code references. Do NOT design until founder decides 
(extend existing, build parallel, replace, etc.).

**If no overlap**: confirm absence by listing what was checked, then proceed.

## Rule 3: Source of Truth Verification

Before trusting any second-hand description of existing code ("thin 
streaming wrapper", "scaffold", "stub", "minimal implementation"), the 
agent MUST read the actual code and verify the characterization. 
One-line summaries from prior sessions are NOT sufficient evidence of 
what exists or doesn't exist.

## Rule 4: Cross-System Dependency Check

Every new endpoint, service, or schema change must check for:
- Existing ARQ tasks that might depend on the surface area
- Existing webhook handlers (Stripe, etc.) that might depend on it  
- Existing admin endpoints that might call into it
- Existing tests that exercise it
- Existing frontend code that calls the existing surface

## Rule 5: Reconciliation Default

When parallel implementations of the same feature are discovered, the 
default is NOT "delete the duplicate". The default is:
1. Investigation-only PR producing a comparison report
2. Founder approves a reconciliation strategy based on the report
3. Reconciliation PRs follow, ordered by risk (close security or 
   billing holes first)
4. Each step independently reviewed and merged

## Enforcement

Every brief written by the planning Claude MUST include "Investigation 
step" as Step 2 of the brief structure, with explicit requirements per 
Rules 1-4 above. The brief must require the executing agent to:
1. Read the relevant files first
2. Report findings before implementing  
3. Stop and escalate if overlaps are found

Both Claude assistants (planning and execution) consult this protocol 
at the start of every new work item.

That protocol covers WHAT to investigate; SKILL.md (repo root) governs 
HOW a unit of work runs, from brief to push.

## Failure Log

Lessons that updated this protocol:

- **2026-05-16**: C4 message endpoint built in parallel with existing 
  SSE streaming send-message endpoint. Discovered via openapi.json 
  inspection. Cost: ~3 hours of duplicate work + a rate limit security 
  hole. Lesson: enumerate existing endpoints in same domain BEFORE 
  designing new ones.

- **2026-08-18**: A tech-debt item that had been CLOSED for eight doc 
  rotations was still listed as open — here, and in every PROJECT_STATE 
  from v17 to v24. The dual tier-resolution debt was resolved by #203 
  (2026-06-03) and recorded then; the "open" claim survived because each 
  rotation copied the previous document's text instead of re-verifying it 
  against the code. A second instance was found the same way: "RLS 
  DISABLED on all public tables" was propagated from v8 through v24 while 
  RLS was in fact ENABLED on all 35 public tables — and "RLS" sat on the 
  P0 launch-blocker list the whole time, tracking work that was already 
  done. Lesson: **a doc claim repeated without re-verification is evidence 
  about the previous doc, not about the system.** When rotating 
  documentation, re-check every load-bearing claim against code or the 
  database, or mark it explicitly unverified. "Unchanged." is not a 
  verification.

  Corollary, learned the expensive way: the correction to this very entry 
  was written on 2026-08-06 and **never merged** — it sat on an unpushed 
  local branch while the false text stayed in this file for another twelve 
  days, and the next session's brief was written from it. **A doc that is 
  not merged does not exist.** Before a rotation is done: push, open the 
  PR, and confirm the files are on main.

- **2026-08-23 (TD-45)**: 29 backend tests had been failing long enough to
  be grandfathered into a CI baseline, under a carried one-line
  explanation: "hard-coded `execute()` indices". For the 17 in one file
  that was true. For the remaining 12 it was wrong about **four of the
  five** families — the real causes were an unset mock attribute
  collapsing a tier to `free`, `patch()` failing to replace an
  already-resolved FastAPI `Depends`, a mock missing two schema fields
  added by later PRs, and a hardcoded persona list that had drifted.

  Repairing them per the carried explanation would have failed on four
  families and taught nothing. Diagnosing each one first also surfaced
  what a green-looking repair would have buried: **three stale product
  expectations** (auto-title `== 3` vs the shipped `>= 2`, and two
  postprocessing tests describing a migration state that no longer
  existed), **one shipped behaviour with no test at all** (#244's
  seed-the-opening half, which the pre-#244 harness could not express),
  and **one live migration gap** (3 personas still carry no
  forbidden-lexicon).

  Lesson: **a carried explanation for a failing test is a doc claim like
  any other — verify it per test before repairing.** The same rule the
  2026-08-18 entry states for documentation applies to bug diagnoses
  inherited from a previous session. A red test is evidence that
  something is wrong; it is not evidence about *what*.

  Corollary on repair: when a harness repair makes a test reach its
  assertion for the first time in months, the assertion itself is now
  unverified text. Read it against current behaviour and `git log -L` the
  condition before trusting it — three of these needed that, and none of
  the three was a defect in the product.

## Future-proof first, shortcuts second

Every proposal — code, schema, architecture — must be evaluated against
production behavior with real subscribers, not just current cold-beta state.
Cold-beta shortcuts are allowed ONLY when:

1. The shortcut is explicitly named as such (not silently shipped as a "fix")
2. The production-grade alternative is articulated with concrete cost
3. A specific milestone is set for the proper implementation (e.g. "before public launch", "after first 10 paying subscribers")
4. Mentor confirms the shortcut doesn't create user-visible regressions or
   data integrity risks in the cold-beta window

When proposing solutions, default order:
- Production-grade approach (long-term sustainable)
- Hybrid / phased approach if time-to-ship matters
- Shortcut only if the above are infeasible AND the cost is named

When auditing CC's proposals, flag any solution that ships technical debt
without naming it. Tech debt that's named is manageable; tech debt that's
buried compounds silently.

Apply this principle to: schema design (FK constraints, soft vs hard delete,
retention policies), security (auth flows, dead-end navigation post-signout),
state management (caching, race conditions), and any "quick fix" that
touches data integrity.

## Production safety principles

Five mandatory rules codified after the PR4n→PR4p→PR4q regression chain (May 21-24, 2026).
These apply to ALL sessions, not just hotfixes.

### P-01 — Hotfix branch protocol

Before creating any hotfix branch from main, ALWAYS execute in order:

```bash
git fetch origin
git checkout main
git reset --hard origin/main
git log -3 --oneline  # verify expected HEAD commit
git checkout -b feat/...
```

Branching from stale local main = empty no-op merge (PR4q lesson). The `git fetch` line is
the cheapest insurance against this class of failure. NEVER skip.

### P-02 — One logical change per PR

PR4p bundled P0 (api import fix) + P1 (Zustand hydration guard) in one PR. P1 broke
production; P0 was the actual fix. Rollback was complicated because the two changes were
tangled in one commit.

Rule: each PR addresses ONE logical change. Critical bug fix + nice-to-have refactor in
same PR = anti-pattern. If a fix is found alongside an unrelated improvement, ship the
fix alone first. The improvement gets its own PR after smoke test passes.

### P-03 — Mandatory smoke test cadence

After ANY merge that touches user-facing UI or state-management code, run a 2-minute
manual smoke test before issuing the next PR brief.

Symptoms requiring immediate stop: empty page, blank tabs, redirect loops, no API calls
in Network tab, paywall-when-Pro. ANY of these = stop, debug, before any new feature work.

Lesson: PR4n broke Today (api import removed) on May 23 evening. Bug discovered 18 hours
later during PR4o smoke test. A single 2-minute check at PR4n merge would have caught it.
Three PRs and ~18 hours of regression followed from skipping that one check.

NO MORE batch-deferred smoke tests. Cadence: merge → 2-minute manual check → next PR
brief only after check passes.

### P-04 — Preview deploy validation for state/auth changes

Changes touching ANY of the following MUST be smoke tested on Netlify preview deploy
BEFORE merging to main:
- Zustand store shape, middleware, or hydration (`lib/store.ts`)
- Auth flow (OTP, JWT, session management)
- Layout-level wrappers or providers
- API client (`lib/api.ts`)
- Per-page auth useEffects

Unit tests are necessary but not sufficient. Preview deploy runs the actual production
build pipeline.

Lesson: PR4p `_hasHydrated` guard had passing unit tests + clean code review. Failed in
production Next.js build because `onRehydrateStorage` callback timing differs from local
dev. Preview deploy would have caught this in 5 minutes.

### P-05 — Verify backend route changes don't strip data fetching

When refactoring a component (extracting to a new file, renaming imports), grep the
original file for ALL usages of removed imports BEFORE deleting the import line.
Each usage must be either re-added to the original file or confirmed genuinely no longer
needed there.

Lesson: PR4n moved `ShareLimitError` correctly to `SharePreviewModal.tsx` but accidentally
took `api` with it. All Today data fetching silently broke. A pre-extraction grep for
every import being removed would have caught this immediately.

### P-06 — Diagnosis before code change

When a user reports "X is broken" but you don't know what changed, do not modify code in
response. Diagnose first:

1. Query the database state to verify the data the UI claims is missing
2. Check Render/Netlify logs for actual errors vs perceived errors
3. Distinguish:
   (a) Real new bug introduced by recent code
   (b) Latent issue that's always existed
   (c) Forgotten user action (e.g., user soft-deleted their own data)
   (d) Misidentification (user confusing one section for another)

Code only changes after the diagnosis pinpoints (a) and identifies the responsible commit.
Premature code change in response to perceived bugs wastes time and risks introducing real
regressions.

**Source:** 2026-05-24 session, "Reflections deletion" diagnostic detour. Founder reported
Reflections card disappeared after PR4t merge. Investigation revealed: PR4t didn't touch
Reflections, and the card was conditionally hidden because all user's saved_lines had
`deleted_at IS NOT NULL` from a soft-delete mass action on May 22 evening. No bug existed.

### P-07 — One Claude Code session per repository at a time

Two concurrent CC sessions share one git working tree and switch branches under each other.
On 2026-06-12 this caused a commit to land on the wrong branch (docs/v17-smoke-closures
received the mirror_saves work) and required a stash/branch -f/reset recovery. Rule: never
run two CC sessions against the same repo simultaneously. Close or finish one before starting
work in another. Before every commit/push, verify the current branch with
`git rev-parse --abbrev-ref HEAD`.

---

## Persona & migration conventions

Codified 2026-06-16 after the Orwell + Musashi addition (#316) and the portrait WebP
standardization (#315). These apply to all future persona and data-migration work.

### C-01 — Data migrations must be self-contained (no app-code import)

A DB migration must NOT import application code (e.g. `from personas import ...` or call
`config.to_dict()` at runtime). Runtime app code drifts; a migration must reproduce the same
result forever. Freeze any config payload as an **immutable inline literal snapshot** inside the
migration file.

The `027_add_orwell_musashi` pattern is canonical: the `config` jsonb for each persona is a
hand-inlined dict literal, verified identical to `PersonaConfig.to_dict()` at authoring time and
then frozen in the migration. The migration runs the same whether or not the persona module
later changes or is deleted. DOWN deletes the inserted rows by slug only.

### C-02 — Portrait asset format standard = WebP; both stores stay in sync

Persona portraits are **WebP, 1024px, quality 82** (not PNG/JPG). Every persona portrait must
exist in **both** asset stores and stay in sync:
- `apps/web/public/personas/<slug>.webp` (frontend)
- `apps/api/static/personas/<slug>.webp` (API static)

`portrait_url` in the DB is `/personas/<slug>.webp`. When changing a portrait, update both files
and (if the extension changes) add a data migration to repoint `portrait_url` — see
`026_personas_portrait_webp`.

### C-03 — Adding a persona checklist

When adding a new persona, do ALL of the following:
1. **PersonaConfig module** — `apps/api/personas/<slug>.py` (build from the design-YAML brain
   file; verbatim fields where the YAML defines them, authored voice fields in the existing
   persona-module style).
2. **Register** in `apps/api/personas/__init__.py` `PERSONA_REGISTRY`.
3. **Brain YAML** — `apps/api/philosopher_brain/personas/<name>.yaml`.
4. **Matching** — add `PERSONA_AFFINITIES` weights in `services/matching_service.py` for **ALL
   12 themes + 4 needs** (no partial maps). Decide `EXCLUDED_SLUGS` membership (default: matchable).
5. **Copyright / RAG** — if the persona's source texts are under copyright, add the slug to
   `EXCLUDED_PERSONAS` in `scripts/corpus_sources.py` (voice-engineered only, zero chunks). If
   public-domain but no rights-clean source is ready yet, leave it out of `CORPUS_SOURCES`
   (deferred — not excluded). `retrieval_sources=[]` until chunks exist.
6. **Portrait** — `.webp` (per C-02) in **both** stores.
7. **Migration** — self-contained (per C-01): insert the row with `tier`, `is_active`, `config`
   (frozen literal snapshot), `bio = about_en` verbatim from the brain YAML, `portrait_url`.
8. **Error voice** — if a persona-specific `llm_unavailable` voice is desired, include an
   `error_messages` map in the config; otherwise `get_error_voice` falls back to the generic
   message (`services/persona_voice.py`).

### C-04 — Migration revision id ≤ 32 chars, and filename MUST equal the revision id

Codified 2026-06-26 after the migration 035 incident (#371).

`alembic_version.version_num` is **`VARCHAR(32)`**. A revision id longer than 32 characters
crashes the deploy at the version-write step (Alembic tries to record a too-long string).
Because Postgres DDL is transactional, the failed upgrade **rolls back cleanly to the prior
head** — it is never half-applied — so the fix is a pure rename, not a data repair. But it is a
production deploy crash that is entirely avoidable.

Rules for every migration file:
1. **Revision id ≤ 32 characters.** Count it before committing. Prefer terse ids
   (`035_deep_mode_go_deeper`, 23 chars) over descriptive-but-long ones
   (`035_deep_mode_and_go_deeper_count`, 33 chars — the id that broke the deploy).
2. **Filename == revision id** (plus `.py`). The file is `035_deep_mode_go_deeper.py` and the
   in-file `revision = '035_deep_mode_go_deeper'`. Keeping them identical makes the chain
   greppable and prevents a rename touching one but not the other.
3. When renaming a revision id to fix length, update **all three**: the filename, the in-file
   `revision = …`, and the **next** migration's `down_revision = …`.

**Source:** 2026-06-26 session. `035_deep_mode_and_go_deeper_count` (33 chars) crashed the
Render deploy at the version-write; DB stayed cleanly at 034; #371 renamed it to
`035_deep_mode_go_deeper`. No data repair was needed.

### C-05 — A migration that creates a public table enables RLS on it, in the same migration

Established 2026-08-18 by `052_enable_rls`. Recorded here 2026-08-23; it was not new
then, only unwritten.

Every migration that creates a table in the `public` schema must `ENABLE ROW LEVEL
SECURITY` on that table in the **same** migration. Not a follow-up, not a manual step
against production.

`052_enable_rls` is a **one-time catch-up for 001–051, not a pattern to re-run.** RLS had
been enabled on the live database by hand, but no migration contained `ROW LEVEL SECURITY`
in any form — so a database rebuilt from migrations came up with RLS DISABLED on every
table, silently. 052 closed that gap without retrofitting anything: 001–051 stay
byte-identical.

The API connects as the table owner and owners bypass RLS, so this never gates the API.
What it closes is the PostgREST anon/authenticated surface, where an unauthenticated
caller would otherwise read every row of a new table.

A migration that adds a column to an existing table does not need it — say so explicitly in
the docstring rather than leaving a reader to wonder, as `053_token_version` and
`054_token_components` both do.

**Why this entry exists at all:** the convention was stated only inside migration
docstrings (052, and cited by 053 and 054). That is exactly the drift this file's own
failure log warns about — a rule that lives outside the protocol document is one rotation
away from not existing. Nothing about the rule changed when it was written down here.

### C-06 — Mocks must set every field the code under test reads

Codified 2026-08-23 after four instances in a single working session.

A `MagicMock` auto-creates any attribute you ask for. The result is not an error — it is a
`Mock` object that silently fails every type check and membership test it meets:

```python
if sub.plan not in ("pro", "premium"):   # a Mock is not in the tuple -> takes the branch
still_stands: str | None                 # a Mock is neither -> pydantic rejects
input + cache_read                       # int + Mock -> a Mock, not a TypeError
```

So a mock that omits a field does not fail loudly. It makes the code under test take a
branch nobody intended, and the test then passes or fails **for reasons unrelated to what
it claims to check**.

Rule: a mock feeding a validated model (pydantic, SQLAlchemy) or a branch condition must
set **every field that model or condition reads** — explicitly, including fields whose
correct value is `None`. When a real object is cheap to build, prefer it: the plain
`FakeMirror` / `FakeComparison` classes in the ring-true tests exist because a MagicMock
would have absorbed an unwanted attribute write and made "was this persisted?"
unassertable.

Four instances, 2026-08-23:
- `_make_subscription` never set `plan` → tier resolved to `"free"` → a test named "pro is
  not rate limited" asserted against a 429 (TD-45 part 2).
- `_cv` never set `still_stands` / `title` → pydantic `ValidationError` in the router, not
  in the test (TD-45 part 2).
- `_mock_anthropic` omitting a usage field would have made the token sum a `Mock` instead
  of raising, so a dropped bucket would have passed silently (#556).
- The ring-true safety tests could not have asserted "the note was NOT persisted" against a
  MagicMock at all — it accepts an attribute write and still answers every read — so they
  use plain `FakeMirror` / `FakeComparison` classes instead (#557). The fourth instance is
  the one that was avoided, and it is the reason the rule ends with "prefer a real object".

---

## Known tech debt

### Dual tier resolution — CLOSED (#203)

**This entry previously described `get_current_user_plan` and `get_user_tier` as two
parallel tier-resolution functions with different semantics. That has been false since
#203.** `apps/api/auth.py:get_current_user_plan` is a thin FastAPI dependency wrapper
that awaits `tier_service.get_user_tier` and returns `(user, tier)`. There is one
tier-resolution function. `get_user_tier` is canonical, including its expiry/status
validation and the `BETA_GRANT_PRO_TO_ALL` bypass.

The stale entry survived eight doc rotations and shaped briefs during that time. The
correction was written on 2026-08-06 and never merged. It is kept here as a closed item
rather than deleted, as a standing example: **a claim in this file is a claim about the
past unless it was re-verified against the code.**

A separate, still-open question survives this closure. `get_user_tier` remains
typed `Literal["free","pro","premium"]` and can still return `"premium"`
(`tier_service.py:29-31`), and `constants.py` retains `premium` in `TIER_ORDER`
and `PLAN_FEATURES` as deliberate defensive tolerance after #528 retired Premium
from the frontend and schema. 72 non-test occurrences of `premium` remain in
`apps/api` (bounded count, 2026-08-18). **Whether to collapse to `free | pro` is
undecided.** This is tolerance for a tier that will not exist in v1 — it is not
a defect, and it is not urgent, but it is also not closed.
