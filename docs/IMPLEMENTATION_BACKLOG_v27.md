# GREAT MINDS — Implementation Backlog v27

> **Companion to:** `PROJECT_STATE_v27.md`, `HANDOFF_BRIEF_v27.md`.
> **Verification SHA:** `7a0ab2e0`. **Date:** 2026-09-02.
> v26 files preserved byte-identical.

---

## ⚠️ HOW TO READ THIS FILE

**Every item below was re-verified against the code at `7a0ab2e0` before being
written here.** The method is stated per item. An item carried from v26 without a
fresh check would be evidence about v26, not about the system — that is the
2026-08-18 lesson, and §5 of `PROJECT_STATE_v27` records it firing again this
rotation.

Items that could not be verified from the repository (Stripe price objects, mailbox
routing, production observations) are marked **UNVERIFIABLE HERE** with the reason.

---

## 1. Tech debt

### TD-57 — No live-DB integration tests
**Status: OPEN. Deepened by #583, #584, #588.**
**Verified:** grepped `apps/api/tests/` for `create_async_engine`,
`AsyncSessionLocal()`, `DATABASE_URL`, `testcontainers`, `pytest-postgresql`. Two
files matched; **both matches are comments describing mocks**
(`test_conversations.py:164`, `test_cron_stripe_reconcile.py:46`). There is no test
in this repository that opens a database connection.

Every test mocks the session. That was tolerable when the schema was simple. It is
less so now: #583's ordering guard, #584's dunning transitions and #588's cascade
across 21 tables are all *database* behaviours, asserted against mocks that cannot
enforce a foreign key, a cascade, or a unique constraint. #588's `DELETE FROM users`
in particular is proven only by "the statement was issued", never by rows
disappearing.

**Cost of the gap:** a migration that is wrong in a way the models do not express
passes every test.

### TD-58 — Remove `passlib` and `bcrypt`
**Status: OPEN. Standalone chore.**
**Verified this rotation, as the v27 brief required:** `requirements.txt` lines 10–11
still pin `passlib==1.7.4` and `bcrypt==4.0.1`; a grep for
`passlib|bcrypt|CryptContext|pwd_context` across `apps/api/**/*.py` returns
**zero importing files**. Still unimported since #586 removed
`hash_password`/`verify_password`.

Its own PR because removing them changes the Docker build, and P-02 says one logical
change per PR.

### TD-59 — No test pins the privacy policy against the implemented rights
**Status: OPEN. New this rotation.**
**Verified:** the policy is Version 1.3, effective 2 September 2026
(`apps/web/app/legal/privacy/page.tsx:24`). §7 promises access, rectification,
erasure, portability, restriction, objection and withdrawal of consent. Generated
`openapi()` in-process: `DELETE /api/v1/auth/me` (erasure),
`GET /api/v1/auth/me/export` (access + portability) and `PATCH /api/v1/auth/me`
(rectification) all exist.

So the policy and the code agree **today**. Nothing enforces that they keep
agreeing. #588 had to amend the policy because it promised a soft delete with a
recovery window that was never built; that mismatch survived because a legal
document and an endpoint have no shared test.

**Proposed shape:** assert the policy page names the three retained categories #588
introduced, and that each right §7 claims has a route. Cheap, and it makes the next
drift fail rather than sit.

### TD-60 — Postprocessing voice checks are English-only
**Status: OPEN. Last English-only matcher in the reply path.**
**Verified:** `services/postprocessing_service.py` matches with `reply.lower()` +
substring (lines 114, 120, 245, 249) and `re.IGNORECASE` (lines 135, 264, 487). No
`casefold`, no NFD, no accent handling anywhere in the file.

#589 fixed the safety gates; these are the *voice-quality* checks (universal
forbidden lexicon, brevity, persona forbidden). A Greek reply cannot trip the
forbidden-lexicon check at all. Not a safety hole — `check_output` is a separate
path and was fixed — but it means persona-voice enforcement silently does nothing
for the product's first audience.

### TD-61 — The Greek safety lexicon has never been read by a Greek speaker
**Status: OPEN. Highest-value review item in this file.**
**Verified:** imported the lexicons and counted — **73 Greek entries, 79 greeklish,
210 across all four bands and three scripts.**

They pass 53 tests and produce zero false positives against 719,600 characters of
this repository's English prose. None of that is a substitute for a native reader
checking that the phrases are what a distressed Greek speaker actually types. The
per-entry tables with English glosses are in #10's Step-1 report and are formatted
for line-by-line review.

**Two entries flagged by the author as most likely to over-trigger:** `αυτοκτονια`
and `αυτοκτονω` are bare noun/verb forms that will fire on academic or third-person
discussion. They are in deliberately, under the over-trigger ruling.

### TD-62 — No export completeness guard
**Status: OPEN. New this rotation.**
**Verified:** grepped `tests/test_data_export.py` for a completeness assertion —
none exists. Every test there is either shape or exclusion.

So if a future PR adds a table with a `user_id`, nothing fails and the export
silently under-reports. That is a GDPR Art. 15 defect that looks exactly like a
working export.

**Proposed shape:** enumerate mapped classes carrying `user_id`, assert each appears
in the payload **or** in a documented exclusion set. It would have caught nothing
today and will matter on the fifth new table.

### TD-63 — The fair-use refusal path has never rendered
**Status: OPEN. New this rotation.**
**Verified:** grepped the web test suite for `fairUseMessage`, `fair_use_limit` and
`FAIR_USE_COPY` — **no test renders the toast.** The backend refusal is covered;
the thing a person would actually see is not, in tests or in production.

The cap needs 150 messages in one UTC day — 1.85× the heaviest usage day ever
recorded, measured in #11's Step-1 investigation against the production database and
**not re-read this rotation** — so its first execution will be a real Pro subscriber.

**Cheap remedy:** set `PRO_DAILY_FAIR_USE_LIMIT = 2` on a staging account for one
session and look at the toast. Answers the only question the tests cannot.

---

## 2. Open decisions

### OPEN-DECISION — The free daily ceiling is 15/day, not 5 and not 60
**Needs usage data. Not a gap-fill.**

**Corrected this rotation. The figure carried into the v27 brief — "60/day across 12
personas" — is wrong twice**, and both errors were found by running the count rather
than repeating it.

**Method, in-process at `7a0ab2e0`:** imported `PERSONA_REGISTRY` and counted;
imported `get_persona` and `is_persona_accessible` and evaluated the free-tier gate
for every slug.

- **There are 11 personas, not 12.** `len(PERSONA_REGISTRY) == 11`.
- **A free user can reach 3 of them**, not all 11: `lao_tzu`, `marcus_aurelius` and
  `socrates` carry `tier="free"`; the other eight are `tier="pro"` and
  `is_persona_accessible(..., "free")` returns `False` for each. That gate is
  enforced on conversation creation (`services/conversation_service.py:346`, `:518`)
  and on another-mind and go-deeper (`routers/conversations.py:496`, `:604`), so a
  free user cannot open a conversation with a Pro persona at all.

`FREE_DAILY_LIMIT_PER_PERSONA = 5` and `check_rate_limit` filters on
`DailyUsage.persona_id`, so the cap is per persona. **3 reachable personas × 5 =
15 messages/day**, not 60 and not 55.

A grep for `monthly_limit|FREE_MONTHLY|per_month` across `apps/api` still returns
**nothing**: the July intent of "5/day + 30/month, server-side" has a per-persona
daily cap and no monthly cap at all.

**This changes the shape of the decision.** A global 5/day would be 3× stricter than
today, not 12× — a far smaller change than the carried figure implied, and one worth
re-deciding on that basis. Tightening a live free limit still changes what existing
users can do, so it remains a product decision to take with usage data.

**One caveat, not verified here:** `BETA_GRANT_PRO_TO_ALL` defaults to `False` in
`config.py`, but if it is enabled on Render every user resolves to Pro and the free
cap does not apply at all. Its production value was not read this rotation.

---

## 3. Operations

### OPS-006 — Stripe price objects still charge the old amounts
**Status: OPEN. HARD BLOCKER for the live-mode switch.**
**UNVERIFIABLE HERE:** price objects live in Stripe, not in this repository. The
founder observed **€149 charged against a locked price of €99.99**.

What the repo does say: `apps/web/app/app/upgrade/page.tsx:103` displays
**"€99.99 / year"**. So the surface a customer reads and the amount Stripe would
charge disagree, which is the whole of the problem.

**Sequence, in order:** create new price objects at the correct amounts → update the
`STRIPE_PRICE_*` env vars on Render → verify a test-mode checkout charges the
displayed amount → **repeat the entire sequence on the live account**, because test
and live price objects are separate and nothing carries across.

Nothing about the live switch should proceed until a checkout has been observed
charging what the page says.

---

## 4. UX

### UX-01 — CLOSED (#485, 2026-07-12)
**This item was carried as open and is not.**
**Verified:** `git log -S "answeredProfile"` returns **#485, "feat(reflection): skip
profile step once answered; first-run unchanged", merged 2026-07-12 21:03 +0300** —
the same day the fix is recorded as having been decided.

Both halves are live: `apps/web/app/app/onboarding/need/page.tsx` computes
`answeredProfile` from `prefs.profile.values` / `disagreement_style` and routes
straight to matches, and `services/preferences_service.py::set_profile`
shallow-MERGEs so one writer cannot wipe another's section.

Kept as a closed entry rather than deleted, as a standing example of the same
failure the 2026-08-18 log entry describes. See `PROJECT_STATE_v27` §5.

### UX-02 — Greek crisis line (1018) needs a verification process first
**Status: BLOCKED, deliberately.**
**Verified:** `prompts/safety_response_el.jinja2` is country-neutral and contains no
number; `tests/test_safety_response_language.py` asserts no country-specific number
appears in it.

Ruled 2026-09-02: a published crisis number requires founder phone-verification and
its own maintenance process, because **a number that has changed is worse than no
number** — it sends a person in crisis to a dead line. Its own PR if ever, and the
test above would need updating deliberately rather than routed around.

---

## 5. NIKOS-ACTIONS — standing, outside the codebase

These recur or block; none can be done from the repository.

1. **PostHog erasure after every account deletion.** `posthog-python` 3.7.0 exposes
   no deletion API — verified by inspecting the installed package's method list in
   #590's investigation. Person-profile deletion is a dashboard GDPR process. Until
   it is done, a deleted user's profile persists at the processor. The
   `account_deleted` event is unattributed (`distinct_id = "deleted_account"`), so it
   adds nothing new to that profile.
2. **`support@thewiseroom.app` mailbox or forwarding, once DNS lands.** The address
   is published in the Privacy Policy and Terms as the data-controller contact, and
   #590's 413 tells an over-limit user to write there. A test pins the 413 string to
   the legal pages, so the *string* cannot drift — but nothing can verify mail is
   delivered.
3. **Greek lexicon review by a native speaker.** TD-61. Tables in #10's Step-1
   report.
4. **Monday inbox check for the Sunday letter.** The 2026-09-06 18:00 UTC run is the
   observation #6 is gated on. See `HANDOFF_BRIEF_v27` §1.
5. **Set `SENTRY_DSN` on both Render services** if not already done — the API and the
   worker are separate processes and the worker inherits nothing. FOUNDER-REPORTED as
   initialised; not verified here.
6. **Accountant → Stripe live-mode switch.** The single action that turns the product
   revenue-capable, and the last thing standing between the work in this file and any
   income from it. Blocked behind OPS-006 (§3): the live switch must not proceed until
   a checkout has been observed charging the displayed €99.99. UNVERIFIABLE HERE —
   lives entirely outside the repository.

---

## 6. What is NOT in this file, and why

**P1–P3 are not decomposed into PRs.** That is deliberate and is restated in
`HANDOFF_BRIEF_v27`. Pre-decomposing work that has not been investigated produces
briefs written from assumptions, which is the failure mode CLAUDE.md's Rule 1 exists
to prevent. P1 begins with an investigation-only brief, and the PRs come out of what
it finds.
