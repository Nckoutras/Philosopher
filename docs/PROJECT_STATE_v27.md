# GREAT MINDS — Project State v27

> **Range covered:** `#564` … `#592` (29 squash-merges on `main` since `ef3e2d89`).
> **Verification SHA:** `7a0ab2e0`.
> **Date:** 2026-09-02.
>
> **This rotation's own PR number is deliberately not asserted**, and no unmerged
> work is described as if it existed. The range above is what is on `main`.
>
> **Companion documents:** `IMPLEMENTATION_BACKLOG_v27.md`, `HANDOFF_BRIEF_v27.md`.
> v26 files are preserved byte-identical.

---

## ⚠️ PROVENANCE

**Every claim below is either VERIFIED THIS ROTATION with its method stated inline,
or explicitly marked FOUNDER-REPORTED / UNVERIFIED.** "Unchanged." is not evidence
and is not used as such.

**Methods used this rotation:** `pytest`, `vitest` and `tsc` executed at `7a0ab2e0`;
`git log` and `git log -S` over the range; live code reads; the FastAPI app's
`openapi()` generated **in-process**; the safety lexicons imported and counted in
Python; `alembic heads` and the C-04 naming script executed.

**No database, no Stripe dashboard, no Sentry project and no production logs were
consulted.** The Supabase MCP query was blocked by this session's permission
classifier and was not retried. Every claim that would require any of those is
marked FOUNDER-REPORTED below — meaning the founder observed it and this document
records that, not that this rotation checked it.

**One carried backlog item was found to be already shipped** (UX-01, closed by #485
on 2026-07-12). It had been carried as open. Details in §5.

---

## 1. What this cycle did

**P0 is 12 of 13 complete.** The one remaining item is #6, letter delivery, which is
gated on an observation that has not happened yet — the Sunday 2026-09-06 18:00 UTC
run.

Six threads closed, in the order they shipped:

**Billing lifecycle (#582, #583, #584).** Context-aware upgrade copy driven by
`?source=` and `?reason=`; webhook idempotency with an event-ordering guard;
dunning grace, a recovery email, cancel reason and `last_14d_features`. Migration
`055_billing_lifecycle` carries the schema.

**Housekeeping (#585, #586).** CI actions bumped to v7 across `checkout`,
`setup-python` and `setup-node`, each verified against the repo's actual usage
rather than the changelog headline. The dead password-auth surface —
`POST /auth/register`, `POST /auth/login`, their schemas, `hash_password`,
`verify_password` and the `api.ts` wrappers — deleted; those two routes had never
had a single test.

**Observability (#587).** Sentry, errors only, no tracing. The privacy posture is
four mechanisms rather than one flag, because `send_default_pii=False` does **not**
stop request bodies: `max_request_body_size="never"`,
`include_local_variables=False`, the Anthropic and OpenAI integrations disabled by
name, and a `before_send` scrubber. Two content leaks were found by testing the
scrubber end-to-end against the real SDK rather than by reading the option list —
stack-frame locals, and `logentry.formatted`.

**GDPR (#588, #590).** Erasure and portability, the two rights §7 of the privacy
policy had promised since #577 with nothing behind them. #588 is a hard delete
behind typed confirmation, cancelling Stripe first and aborting if that fails;
migration `056_deletion_fks` gave the database the four `ON DELETE` clauses without
which `DELETE FROM users` could not run at all. The safety-event audit trail is
anonymised rather than destroyed. #590 exports the account as one JSON document,
rate-limited to one per hour.

**Safety (#589, #591).** Greek and greeklish now trip every gate, input and output;
before #589 `θέλω να αυτοκτονήσω` returned `level="none"`. #591 is the ordering
fix found while investigating usage caps: the rate-limit check ran before the
safety gate, so a free user who had spent their allowance and then wrote crisis
text received a 429 that the web client turns into the **PaywallModal**. An upgrade
prompt in answer to suicidal ideation, live until #591.

**Cost (#592).** Pro fair-use cap, 150/day across the four token-spending paths,
resetting at midnight UTC. Five quota sites moved off `date.today()` while there.

---

## 2. Verified state — every row executed or read at `7a0ab2e0`

| Claim | Method | Result |
|---|---|---|
| Backend suite | `pytest -q` executed | **912 passed, 0 failed** |
| CI failure baseline | file read | **0 quarantined entries** — any red is new |
| Web unit suite | `vitest run` executed | 13 failed / 227 passed — the same 13 as v26 |
| Web typecheck | `tsc --noEmit` executed | 11 errors, unchanged |
| Alembic | `alembic heads` executed | single head, `056_deletion_fks` |
| Migration naming | C-04 script executed | passes |
| Erasure endpoint | `openapi()` in-process | `DELETE /api/v1/auth/me` present |
| Export endpoint | `openapi()` in-process | `GET /api/v1/auth/me/export` present |
| Rectification | `openapi()` in-process | `PATCH /api/v1/auth/me` present |
| Safety lexicons | imported and counted | 73 Greek + 79 greeklish, 210 across all bands |
| Sentry init | source read | present in `main.py` **and** `workers/arq_worker.py` |
| Weekly-letter cron | source read | `CronTrigger(day_of_week="sun", hour=18)` |
| Privacy policy | source read | Version 1.3, effective 2 September 2026 |

### ⚠️ FOUNDER-REPORTED — not verified by this rotation

These are recorded because the founder observed them. This document did not check
any of them, and says so rather than adopting them as verified:

1. **#582 attribution verified end-to-end in production** (`source=persona_locked`
   visible in both PostHog properties and Stripe metadata).
2. **#583's ordering guard fired on a real out-of-order Stripe delivery.**
3. **Migrations `055` and `056` are live on production.**
4. **Sentry initialised in the production environment.**
5. **The Greek gates were exercised from pushed code** (11/11 input cases plus the
   output gate).

Items 3–5 are the ones worth re-checking first if anything looks wrong later: each
is a deploy-time fact that leaves a trace (`alembic_version`, a Sentry release, a
`safety_events` row) and none of those traces was read here.

---

## 3. What the safety-ordering fix actually found

#591 exists because #11's Step-1 investigation asked a question the brief told it to
ask — "does any cap check run before the safety check anywhere?" — and the answer was
yes, on the single path where it mattered.

The shape is worth keeping, because it is not a coding error. The rate limit lived in
the router; the safety gate lived in the service. Each was correct in isolation. The
defect was in the *seam*, and no test covered a seam that nobody had described.

Three things this cost, all invisible:

- No crisis response was rendered. The person got a persona-voiced quota message.
- No `safety_events` row was written, so the incidence is unknown and unrecoverable.
- The web client turned the 429 into the PaywallModal, so the app answered a crisis
  disclosure with an offer to subscribe.

The fix is ordering only, and the check is now duplicated between router and service
**on purpose** — 82 microseconds against a multi-second LLM call, ruled 2026-09-02.
The comment at the call site says so and says not to refactor it away.

**The scope was narrowed after checking, not assumed.** The ruling said "all three
router paths". Only `send-message` carries user text: `AnotherMindCreate` is a persona
slug, `go-deeper` has no request body, and `check_input` appears exactly once in the
service. The other two paths have no crisis message that could be blocked, so the fix
lands on one path and two tests pin the schema shapes that make that true.

---

## 4. Known state — the cap has never fired, and its notice has never rendered

#592's fair-use cap is live and correct by test. It has also never executed its
refusal path anywhere: it requires 150 messages in one UTC day, which is 1.85× the
heaviest usage day ever recorded (measured in #11's Step-1 investigation against the
production database; **not re-read this rotation**), and **no test renders the toast
either** — verified by
grepping the web test suite for `fairUseMessage`, `fair_use_limit` and
`FAIR_USE_COPY`, which returns nothing.

So the first exercise of that path will be a real Pro subscriber, and the first thing
production will teach is whether the copy reads well — not whether the counting is
right, which the tests already answer. Carried as TD-63 with a cheap remedy:
temporarily set the constant to 2 on a staging account for one session.

The same reasoning applies, more seriously, to the Greek lexicon. 210 entries across
three scripts pass their tests, and zero of them have been read by a native Greek
speaker. Carried as TD-61.

---

## 5. Corrections to prior docs

**UX-01 was already shipped, and had been carried as open.**

The backlog described it as "per-session values/disagreement questions repeat;
decided fix ask-once + auto-skip (2026-07-12), never briefed." The second half is
false. `git log -S "answeredProfile"` finds **#485, "feat(reflection): skip profile
step once answered; first-run unchanged", merged 2026-07-12 21:03 +0300** — the same
day the decision is recorded as having been taken.

Both halves are in the code: `apps/web/app/app/onboarding/need/page.tsx` computes
`answeredProfile` and routes past the profile step, and
`services/preferences_service.py::set_profile` shallow-MERGES rather than clobbering
so the answers survive. It is **closed**, not open, and v27's backlog records it as
closed rather than dropping it silently.

This is the 2026-08-18 lesson repeating in miniature: the item survived roughly seven
weeks of rotations because each one carried the previous document's text. It was
caught this time only because the rotation brief required every carried claim to be
re-verified before being written, and the grep took under a minute.

---

## 6. Changelog — `#564` … `#592`

This rotation's own session contributed `#582`…`#592`. `#564`…`#581` merged in prior
sessions and had not been rotated into a document.

| PR | Title |
|---|---|
| #592 | Pro fair-use cap — 150/day across generation paths, UTC reset |
| #591 | Run crisis check before rate limits on send-message |
| #590 | Data export — GDPR Art. 15/20, synchronous JSON, rate-limited |
| #589 | Greek + greeklish safety gates, normalized matching, Greek crisis response |
| #588 | Account deletion — hard delete, Stripe cancel, anonymized safety trail, policy v1.3 |
| #587 | Sentry error monitoring with strict privacy scrubbing |
| #586 | Delete dead password-auth surface (`/auth/register`, `/auth/login`) |
| #585 | Bump `actions/checkout`, `setup-python`, `setup-node` |
| #584 | Dunning grace, recovery email, cancel reason + `last_14d_features` |
| #583 | Webhook idempotency, ordering guard, interval, `pro_since`, lifecycle history |
| #582 | Context-aware benefit line from `?source=` and `?reason=` |
| #581 | 14-event taxonomy, enforced registries |
| #580 | Turn every automatic capture off — explicit `track()` only |
| #579 | Failure Log — 8-day red CI, three-gate merge rule |
| #578 | Assert the #568 decision, not the runner's Pillow build; pin Pillow 12.3.0 |
| #577 | PostHog behind opt-in consent, EU host, policy v1.2 |
| #576 | Route in-chat and persona paywalls to live checkout |
| #575 | Preview modal date matches the real card format |
| #574 | True WebP source, capped mobile sizes, `og:image` |
| #573 | Extend splash into full landing page |
| #572 | Add `theme` to council synthesis SSE types |
| #571 | Uniform display date on reflection canvas |
| #570 | Add `SKILL.md` (process protocol) |
| #569 | Fail-closed guard on renewal period-end |
| #568 | `_letterspace` default separator U+2009 → U+0020 |

Four further merges in the range (`#564`…`#567`) predate this session and are listed
in `git log ef3e2d89..7a0ab2e0` rather than transcribed here.

---

## 7. Lessons this rotation

**A seam is not covered by the tests on either side of it.** #591's defect lived
between a router and a service that were each correct. It was found by a brief that
asked an explicit ordering question, not by a test — because no test described the
seam.

**Testing the mechanism is not testing the outcome.** #587's scrubber passed 18 unit
tests while leaking content twice. Both leaks appeared the moment it ran against the
real SDK with planted values. The unit tests were not wrong; they were testing what
had been thought of.

**An import-time assertion earns its place on the day it is written.** #589's guard —
every lexicon entry must equal its own normalised form — caught 24 accented entries
in its own author's first draft. Without it they would have been silently dead
phrases in a safety gate.

**Verify the scope of a ruling before executing it.** Two rulings this session named
more surface than the code actually had (#591's "all three paths", #592's counting
basis). Both were narrowed after checking and the deviation flagged, rather than
executed literally or silently reduced.

**A carried claim is evidence about the previous document.** UX-01, §5. The rule from
2026-08-18 works when it is applied; it costs a grep.
