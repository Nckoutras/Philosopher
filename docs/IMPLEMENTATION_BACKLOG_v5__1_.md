# GREAT MINDS — Implementation Backlog v5

> **Purpose:** Final source of truth for implementation work for Great Minds / Philosopher v1 launch. Consolidates the full `Implementation Backlog v4` baseline (2026-05-04), the `Implementation Backlog additional v4` status update (2026-05-05), and the founder decision 2026-05-06 to build all 43 specced screens before public launch.
>
> **How to read this file:**
> - This v5 file supersedes both prior v4 backlog files and the v4-additional update.
> - Historical detail from v4 is retained where still useful.
> - Status, priority, and launch-readiness calls reflect 2026-05-06 state.
> - Where older v4 sections said Phase 5 / Phase 6 / critical UX were still pending P0 engine work, that framing is obsolete. See §1 and §13 for current status.
>
> **Last updated:** 2026-05-06.
>
> **Companion documents:**
> - `SCREENS_TRACKING_v4.md` — full screen inventory and per-screen specs (43 screens)
> - `DESIGN_SYSTEM_v4.md` — visual and component spec
> - `USER_FLOW_v4.md` — how screens connect across user journeys
> - `HANDOFF_BRIEF_v4.md` — continuity and implementation history
> - `PROJECT_STATE_v4.md` — current project state and session continuity
>
> **Priority key:**
> - **P0** = launch blocker / must be done before public launch
> - **P1** = post-revenue cleanup / fix shortly after first paying user
> - **P2** = v2 / post-MVP refinement
> - **P3** = post-launch / post-feedback backlog
> - **P4** = technical debt / infrastructure cleanup
>
> **Status key:**
> - 🔴 not started
> - 🟡 in progress
> - 🟢 done
> - ⏸ deferred with reason
>
> **Authoritative rule:** If this file conflicts with any earlier `Implementation Backlog v4` or `Implementation Backlog additional v4`, this v5 file wins.

---

## v5 Consolidation Summary

### What changed from v4

- The 2026-05-04 v4 file remains the structural backbone for DB, Stripe, API, background jobs, GDPR, notifications, frontend behavior, and future backlog.
- The 2026-05-05 additional file confirmed the Phase 4 stabilization sequence closed (8 ship items).
- This v5 removes the confusing overlap where the old v4 file said Phase 5 / Phase 6 / critical UX were pending while the newer file claimed engine-first complete.

### Key decisions logged in v5

- **2026-05-05** — Phase 4 stabilization sequence: 8/8 ship items closed (safety pathway, generic crisis copy, `user_name` removal + hotfix, Nietzsche frontend removal, phenomenology trigger audit, phenomenology map content expansion 33→78, sentence-boundary truncation 3-layer fix, empty-conversation dedup).
- **2026-05-06** — Phase 5 (Register UI chips + classifier) reclassified to P3 post-feedback. Data is populated in YAML; runtime activation deferred until user feedback indicates demand.
- **2026-05-06** — Phase 6 (Eval suite + CI) reclassified to P1 post-revenue safety/quality audit. Not a launch blocker; runs after first paying user.
- **2026-05-06** — App store submission (iOS / Google Play) deferred to v2. v1 launch is **web/PWA only**.
- **2026-05-06** — Founder elected to build all 43 specced screens before public launch (per `SCREENS_TRACKING_v4.md`). This reverses the 2026-05-04 "critical subset only" compromise. Estimated total timeline shifts from ~6-7 weeks to ~12-16 weeks to first paying user. See §17.

### Current source-of-truth status

- ✅ Phase 4 stabilization sequence: 8/8 ship items closed
- ✅ Safety crisis pathway shipped (deterministic classifier, country-neutral copy)
- ✅ Sentence-boundary truncation 3-layer fix shipped
- ✅ Empty-conversation dedup shipped (backend + frontend)
- ⏳ 43-screen UI build per `SCREENS_TRACKING_v4` — next P0 work surface
- ⏳ Stripe wiring (calendar-gated, available from 2026-05-11)
- ⏳ Legal/privacy readiness (Terms, Privacy Policy, disclaimer)
- ⏳ Email infrastructure (templates, SPF/DKIM/DMARC)
- ⏳ Founder runbooks
- ⏳ UAT with mixed testers
- ⏳ Web/PWA public launch

---

## Quick Reference Table

| Section | What's in it |
|---|---|
| 1. Current launch status | Phase 4 stabilization closed; Phase 5/6 reclassified |
| 2. Remaining launch-readiness checklist | What still matters before public launch |
| 3. Database schemas | Tables and columns required for v1 |
| 4. Config & environment variables | Required launch env vars and forbidden patterns |
| 5. Stripe integration | Portal, webhooks, entitlement, cancellation, pricing (calendar-gated 2026-05-11) |
| 6. API endpoints | Backend routes and webhook endpoint |
| 7. Background jobs | Scheduled / async jobs |
| 8. Prompt-level rules & AI engine | Persona behavior, safety, phenomenology, postprocessing |
| 9. Auth & account | OAuth, OTP, deletion, logout, disclaimer |
| 10. Privacy & compliance | GDPR, deletion, export, policy requirements |
| 11. Notifications | Email channel, push deferred |
| 12. Frontend behavior | State preservation, validation, sheets, loading/errors |
| 13. Post-launch backlog | P1–P4 work queue |
| 14. v2 / post-MVP backlog | Deliberately deferred product features (incl. native app submission) |
| 15. Block 9 frontend behavior | Empty/error state implementation rules |
| 16. Implementation rules | 16.A operating discipline + 16.B coding/scope rules |
| 17. Immediate recommended next sequence | 43-screen UI build order + parallel work |

---

# 1. Current Launch Status

## 1.1 Status Snapshot

**Updated: 2026-05-06.** Phase 4 stabilization sequence closed (8 ship items in §1.2 below). Phase 5 (Register architecture + UI chips + classifier) reclassified to P3 post-feedback per founder decision 2026-05-06. Phase 6 (Eval suite + CI) reclassified to P1 post-revenue safety/quality audit per founder decision 2026-05-06. The 43-screen UI build per `SCREENS_TRACKING_v4` is now the next P0 work surface.

The previous v4 §8 framing of "engine-first sequence" is historical. It is no longer accurate to treat Phase 5, Phase 6, or the immediate Phase 4 follow-up bug work as open P0 engine tasks unless a new defect is discovered.

## 1.2 Closed Work — Shipped to Main + Production

| Item | Commit / branch | Status | Notes |
|---|---|---|---|
| **Bug #33 — Safety pathway in-persona voice** | `fix/safety-crisis-pathway` | 🟢 done | Deterministic classifier-only path. LLM-side crisis directives removed. Medium risk now fully suppresses persona. Spec divergence accepted as defensible launch safety fix. |
| **Bug #34 — US-specific crisis copy → generic** | `fix/safety-crisis-pathway` | 🟢 done | Country-neutral copy. No hotline numbers. Generic language covering all regions. |
| **1.7 — `user_name` removal + hotfix** | `0256f97` | 🟢 done | Deprecated `user_name` kwarg removed. Hotfix fixed missed call site at `conversation_service.py:159` after a 10-minute production crash. Discipline rule established: full diffs required; grep summaries do not replace caller audit. |
| **1.6 — Nietzsche removal from frontend landing** | `c49c3cd` | 🟢 done | Option A: removed from persona list display only. Backend YAML preserved for v2. |
| **1.4 — Phenomenology trigger audit** | `ae58479` | 🟢 done | +88 verb-form and gerund triggers across 32 entries. High-frequency modern terms now have natural-language surface-form coverage. |
| **2.1 — Phenomenology map content expansion** | `54a8be4` | 🟢 done | Map expanded 33 → 78 entries. Adversarial review applied. New entries include situationship, FOMO, love bombing, grindset, sunday scaries, hustle culture, expanded burnout, and others. |
| **1.3 — Sentence-boundary truncation 3-layer fix** | `2bf9244` | 🟢 done | Layer 1: attempt-2 budget multiplier 1.0 → 1.15. Layer 2: strip-time sentence boundary trim with `hard_cut_no_sentence_boundary` fallback. Layer 3: `brevity_passed_but_mid_sentence` observability hook. Tests 125 → 129. |
| **1.5 — Empty-conversation dedup + in-flight flag** | `718a7dd` | 🟢 done | Backend: `POST /conversations` returns existing empty conversation for `(user, persona, ritual)` tuple if `message_count == 0`. Frontend: `useState` in-flight flag + disabled HTML attribute + `animate-pulse` visual. Tests 129 → 134. |

## 1.3 Current Launch Interpretation

The engine is no longer the main blocker. Phase 5 and Phase 6 are deferred to post-launch per founder decision 2026-05-06.

The remaining work surfaces, in priority order, are:

1. **43-screen UI implementation** per `SCREENS_TRACKING_v4` — see §17 for ordering.
2. **Stripe wiring** — calendar-gated, available from 2026-05-11.
3. **Legal/privacy readiness** — Terms, Privacy Policy, disclaimer copy, support contact.
4. **Email infrastructure** — provider, templates, sender domain auth.
5. **Operational founder runbooks** — refund, account recovery, GDPR, cancellation, safety escalation.
6. **Production smoke test** of the 8 closed Phase 4 items.
7. **UAT** with mixed testers (≥2/5 spontaneous "I'd pay" criterion).
8. **Public launch (web/PWA)**.

Avoid reopening Phase 4 stabilization work unless:
- production smoke test fails,
- safety classifier shows material false negatives,
- payment entitlement breaks,
- responses show repeated modern-term leakage or severe persona failure.

---

# 2. Remaining Launch-Readiness Checklist

This section is the practical pre-launch checklist after the 2026-05-06 decision to build all 43 screens before launch.

## 2.1 Must Verify Before Public Launch — P0

### A. Production Smoke Test

- [ ] Incognito / fresh browser sign-up
- [ ] All active personas visible and selectable (5 of 6 — Nietzsche removed from frontend)
- [ ] Start a conversation with each persona
- [ ] Chat response latency acceptable
- [ ] No duplicate empty conversation creation
- [ ] Persona responses do not cut mid-sentence in normal use
- [ ] Safety crisis path suppresses persona voice and shows app-voice safety copy
- [ ] Country-neutral safety copy appears where expected
- [ ] No Nietzsche on frontend landing unless intentionally restored
- [ ] Phenomenology map triggers fire naturally for high-frequency terms
- [ ] No catastrophic frontend navigation issue across 43 implemented screens

### B. Stripe / Payment Verification (calendar-gated 2026-05-11)

- [ ] Production Stripe account live
- [ ] Products + prices created for monthly and annual plans (EUR)
- [ ] Stripe Checkout works with real test card
- [ ] Webhook endpoint configured with signature verification
- [ ] Subscription created → user entitlement updates correctly
- [ ] Subscription updated → cached user fields update correctly
- [ ] Cancellation at period end works
- [ ] Past-due / failed payment path tested or explicitly accepted as Stripe-managed for v1
- [ ] Customer Portal configured and reachable from H5
- [ ] Refund process documented for founder/admin manual operation
- [ ] No frontend code path calls Stripe directly (must use backend `/api/subscription`)

### C. Legal / Privacy

- [ ] Terms of Use written and live at `TERMS_URL`
- [ ] Privacy Policy written and live at `PRIVACY_POLICY_URL`
- [ ] Disclaimer copy v1 finalized and stored in `disclaimer_versions`
- [ ] About Great Minds copy written for in-app sheet
- [ ] DPO/contact info or founder privacy contact in Privacy Policy
- [ ] LLM provider data-processing terms reviewed at practical founder level
- [ ] Stripe agreement / account requirements completed
- [ ] Cookie posture verified: strictly necessary cookies only → no consent banner needed; if analytics/marketing cookies added, consent handling required

### D. Database / Backend

- [ ] Required tables migrated: `cancellation_reasons`, `data_requests`, `disclaimer_versions`, `disclaimer_acceptances`, `notification_preferences`
- [ ] Required user columns exist: `subscription_status`, `current_period_end`, `cancel_at_period_end`, `stripe_customer_id`, `stripe_subscription_id`, `account_deleted_at`
- [ ] Indices created where specified
- [ ] Personal data column flags applied (per §10.3)
- [ ] Account deletion guard checks Stripe before deletion
- [ ] Data request creation and expiry path works
- [ ] Logout clears user-specific cached data
- [ ] Backup/restore procedure understood at minimum practical level

### E. Email / Operations

- [ ] Support email configured via `SUPPORT_EMAIL`
- [ ] Email provider configured (Resend / Postmark / SendGrid)
- [ ] Sender domain authenticated (SPF / DKIM / DMARC)
- [ ] Weekly letter template tested (only if weekly letters ship in v1; otherwise skip)
- [ ] Account deletion confirmation email template tested
- [ ] Data export ready email template tested
- [ ] Unsubscribe link in any marketing emails (none planned for v1, but required if any go out)
- [ ] Founder receives / admin monitors data request notifications
- [ ] Support inbox monitored
- [ ] Stripe webhook failures alert founder or are visible in Stripe dashboard
- [ ] Founder runbook exists for: refund, account recovery, GDPR fulfillment, cancellation override, safety escalation review

### F. UAT / Market Validation

- [ ] Run UAT with 3–5 mixed testers
- [ ] Tester mix: 1–2 close friends, 1–2 acquaintances, 1–2 strangers
- [ ] Avoid using only supportive friends as validation
- [ ] Launch criterion: at least 2 of 5 testers spontaneously indicate they would pay
- [ ] If fewer than 2 of 5 say they would pay, iterate before public launch

### G. Auth — Block 4 Production Verification

- [ ] Google Sign In OAuth client configured for production
- [ ] Email OTP working with chosen provider
- [ ] Rate limiting active in production (`OTP_RATE_LIMIT_PER_HOUR`, `OTP_LOCKOUT_AFTER_ATTEMPTS`, `OTP_LOCKOUT_DURATION_MINUTES`)
- [ ] Account linking tested with verified-email auto-link path
- [ ] OTP state machine tested (5-attempt lockout, 10-min expiry, resend cooldown)
- [ ] Disclaimer re-acceptance flow forced on sign-in if version changed
- [ ] Apple Sign In **explicitly deferred** to native app submission (v2)

### H. Web Deployment

- [ ] Production deployment URL live (Vercel: `thinkalike.vercel.app` or final domain)
- [ ] SSL/TLS verified
- [ ] HTTPS-only enforcement
- [ ] PWA manifest validated (if installable PWA targeted for v1)
- [ ] Production env vars hardened (no committed secrets, no hardcoded URLs in components)

## 2.2 No Longer Launch Blockers Unless Newly Broken

These were either dropped, reclassified, or never v1-critical:

- Marcus shading content (33 strings) — post-launch
- ~200 persona shading paragraphs for expanded phenomenology entries — post-launch
- True lazy-create routing refactor for empty conversations — v2
- Frontend race in same render frame — backend dedup already catches it; theoretical
- Full observability optimization for sentence-boundary truncation — post-launch monitor
- PostHog event polish — post-revenue unless already wired
- App store submission (iOS / Google Play) — v2 only; v1 launch is web/PWA only

---

# 3. Database Schemas

Schemas are illustrative; final migrations should reference Supabase types and be reviewed before applying.

## 3.1 `cancellation_reasons`

**Priority:** P0 if cancellation flow ships at or before payment launch.

```sql
cancellation_reasons (
    id uuid primary key,
    user_id uuid references users(id),
    reason_code enum (
        'not_using_enough',
        'too_expensive',
        'not_useful_enough',
        'expected_more_from_personas',
        'temporary_need',
        'technical_issue',
        'other'
    ) not null,
    free_text varchar(300) nullable,
    created_at timestamp default now(),
    outcome enum (
        'canceled_confirmed',
        'not_canceled_after_24h',
        'superseded',
        'unknown'
    ) default 'unknown',
    expires_at timestamp default (now() + interval '24 hours'),
    status enum (
        'sent_to_stripe',
        'resolved'
    ) default 'sent_to_stripe'
)
```

Notes:
- `free_text` is personal data.
- Index for duplicate prevention lookup, e.g. on `(user_id, status, expires_at)`.
- Prefer extending this table rather than creating a separate `cancel_intents` table.
- When `outcome` is set, flip `status` to `resolved`.

## 3.2 `data_requests`

**Priority:** P0 — GDPR Article 17 / 20 operational support.

```sql
data_requests (
    id uuid primary key,
    user_id uuid references users(id),
    request_type enum ('export', 'deletion', 'correction') not null,
    status enum (
        'requested',
        'processing',
        'completed',
        'rejected',
        'expired'
    ) default 'requested',
    requested_at timestamp default now(),
    completed_at timestamp nullable,
    user_email varchar not null,
    notes text nullable
)
```

Notes:
- `notes` is internal admin-only field.
- Auto-expire stale `requested` rows after `DATA_REQUEST_EXPIRY_DAYS`.

## 3.3 `disclaimer_versions` + `disclaimer_acceptances`

**Priority:** P0 — legal update re-prompt mechanism.

```sql
disclaimer_versions (
    id serial primary key,
    version varchar not null unique,
    copy text not null,
    effective_at timestamp default now()
)

disclaimer_acceptances (
    id uuid primary key,
    user_id uuid references users(id),
    version_id int references disclaimer_versions(id),
    accepted_at timestamp default now(),
    unique (user_id, version_id)
)
```

Behavior:
- A6/A7 acceptance writes a row.
- On sign-in, check if user accepted current effective version.
- If missing, force re-prompt before main app entry.

## 3.4 `notification_preferences`

**Priority:** P0 if weekly letters / notification settings are exposed in v1.

```sql
notification_preferences (
    user_id uuid primary key references users(id),
    weekly_letters boolean default null,
    reflection_reminders boolean default false,
    product_updates boolean default false,
    updated_at timestamp default now()
)
```

Defaults at read-time:
- Pro user + `weekly_letters = null` → treat as ON.
- Free user weekly letters are ignored / not controllable; show Pro pill if surfaced.
- `reflection_reminders` and `product_updates` default OFF.

## 3.5 `users` Table Additions

**Priority:** P0 for payment launch.

Required columns:
- `subscription_status` — cached from Stripe webhook; never fully authoritative
- `current_period_end` — cached
- `cancel_at_period_end` — cached boolean
- `stripe_customer_id`
- `stripe_subscription_id`
- `account_deleted_at` — soft-delete timestamp

Rules:
- Cached columns are updated by webhook handlers.
- For billing-critical UI, query backend entitlement function; do not trust frontend cache.
- Before destructive account deletion, re-query Stripe.

---

# 4. Config & Environment Variables

## 4.1 Required at v1 Launch

| Variable | Purpose | Source |
|---|---|---|
| `SUPPORT_EMAIL` | Destination for support / I4 mailto routes | Founder mailbox |
| `STRIPE_SECRET_KEY` | Stripe API access | Stripe dashboard |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification | Stripe webhook config |
| `STRIPE_CUSTOMER_PORTAL_URL` | H5 manage subscription target | Stripe Portal config |
| `STRIPE_CHECKOUT_PRICE_ID_MONTHLY` | Monthly checkout price | Stripe Products |
| `STRIPE_CHECKOUT_PRICE_ID_ANNUAL` | Annual checkout price | Stripe Products |
| `TERMS_URL` | External Terms link | Website |
| `PRIVACY_POLICY_URL` | External Privacy Policy link | Website |
| `OPENAI_API_KEY` or equivalent | LLM provider | Provider dashboard |
| `OTP_RATE_LIMIT_PER_HOUR` | OTP rate limit; default 5 | App config |
| `OTP_LOCKOUT_AFTER_ATTEMPTS` | OTP lockout threshold; default 5 | App config |
| `OTP_LOCKOUT_DURATION_MINUTES` | OTP lockout duration; default 15 | App config |
| `DATA_REQUEST_EXPIRY_DAYS` | Data request expiry; default 30 | App config |
| `ACCOUNT_DELETION_GRACE_PERIOD_DAYS` | Soft-delete grace; default 30 | App config |
| `CANCEL_INTENT_WINDOW_HOURS` | Cancel intent reconciliation window; default 24 | App config |
| `PHENOMENOLOGY_BRIDGE_ENABLED` | Phenomenology bridge flag; should reflect post-smoke-test decision | App config |

## 4.2 Optional / Future

- `RESEND_API_KEY`, `POSTMARK_API_KEY`, or equivalent email provider key
- `PUSH_NOTIFICATION_KEY` for v2 push notifications
- `SENTRY_DSN` for error monitoring
- `ANALYTICS_KEY` for product analytics

## 4.3 Forbidden Patterns

- Never hardcode `SUPPORT_EMAIL` in UI components.
- Never hardcode Stripe URLs in components.
- Never call Stripe directly from frontend UI.
- Never commit secrets to repo.
- Move hardcoded production URLs from `.env.production` to hosting env vars.
- Avoid partial dependency pinning long-term; move toward full pinning after launch.

---

# 5. Stripe Integration

> **Calendar gate:** Stripe wiring is available from **2026-05-11**. Until then, payment infrastructure work is blocked. All §5 verification items are P0 but cannot start before that date.

## 5.1 Customer Portal Setup

**Priority:** P0 for paid launch.

Enable:
- Update payment method
- View invoices / billing history
- Update billing address
- Cancel subscription, end-of-period for v1
- Reactivate canceled subscription within grace period if supported

Disable for v1:
- Plan changes via portal if monthly/annual switching is not implemented cleanly
- Multiple subscription management

## 5.2 Webhook Events

**Endpoint:** `POST /api/webhooks/stripe`

| Event | Action |
|---|---|
| `customer.subscription.created` | Update `users.subscription_status`, `stripe_subscription_id`, customer reference |
| `customer.subscription.updated` | Update cached status, `cancel_at_period_end`, `current_period_end` |
| `customer.subscription.deleted` | Set `subscription_status = canceled`; retain access if period end remains in future |
| `invoice.payment_failed` | Set `subscription_status = past_due`; optional email path if not relying solely on Stripe |
| `invoice.payment_succeeded` | Set `subscription_status = active`; clear past-due state |
| `customer.deleted` | Mark user as Stripe-orphaned edge case |

Rules:
- Verify signature with `STRIPE_WEBHOOK_SECRET`.
- Make handler idempotent.
- Respond within 20 seconds.
- Queue heavy work if needed.

## 5.3 Effective Entitlement Function

A single backend function `get_effective_entitlement(user_id)` should return:

- `free`
- `pro_active`
- `past_due` — access still allowed unless product decision changes
- `canceling_at_period_end` — access until date
- `canceled_no_access`

Rules:
- Billing-gated UI must use this function.
- Frontend never calls Stripe directly.
- Cached user columns are convenience state, not final truth.

## 5.4 Cancel Intent Reconciliation

Run hourly or via webhook-triggered job.

```text
For each cancellation_reasons row where status = 'sent_to_stripe':
  - If Stripe shows cancel_at_period_end = true OR subscription deleted within [created_at, expires_at]:
      set outcome = 'canceled_confirmed', status = 'resolved'
  - Else if expires_at has passed:
      set outcome = 'not_canceled_after_24h', status = 'resolved'
  - Else:
      leave unchanged
```

If a new cancel intent is created while another remains open:
- Mark previous row `outcome = 'superseded'`, `status = 'resolved'`.
- Create new row with fresh `expires_at`.

## 5.5 Account Deletion Subscription Guard

Before account deletion:
1. Query Stripe for active subscription tied to user.
2. If active subscription exists, return `active_subscription_exists`.
3. UI shows blocked deletion sheet.
4. Only proceed when Stripe confirms no active subscription.

## 5.6 Pricing Configuration

Baseline v4 pricing decision:
- Currency: EUR
- Monthly: €9.99
- Annual: €119.99
- No trial
- 14-day money-back guarantee
- Refunds manual in Stripe dashboard for v1

If later pricing was changed in `PROJECT_STATE`, update this section before launch.

---

# 6. API Endpoints

## 6.1 Block 6 / Account / Subscription Routes

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/cancel_intents` | Save cancellation reason and create intent row |
| GET | `/api/subscription` | Fetch effective entitlement |
| POST | `/api/data_requests` | Create export / deletion / correction request |
| GET | `/api/data_requests/active` | Check pending request state |
| POST | `/api/account/delete` | Trigger account deletion with Stripe guard |
| GET | `/api/notification_preferences` | Fetch notification toggles |
| PATCH | `/api/notification_preferences` | Update notification toggles |
| POST | `/api/auth/logout` | Clear session and cached user data |

## 6.2 Existing Routes to Verify

- `/api/auth/oauth/{provider}` — OAuth flow
- `/api/auth/otp/request` — send OTP
- `/api/auth/otp/verify` — verify OTP
- `/api/disclaimer/accept` — record disclaimer acceptance
- `/api/messages` — chat send and history
- `/api/saved_lines` — save/retrieve reflections
- `/api/conversations` — conversation creation; now has empty-conversation dedup behavior

## 6.3 Webhook Route

- `POST /api/webhooks/stripe` — all Stripe events

---

# 7. Background Jobs

## 7.1 Weekly Letter Generation

**Priority:** P0 only if weekly letters are included in v1 paid promise; otherwise P1/P2.

Rules:
- Schedule: Sundays at user-local adjusted time, e.g. 7am.
- Only for Pro users with weekly letters ON or default ON.
- Skip if insufficient material.
- Do not send thin / generic letters.
- Track token usage per generated letter.

## 7.2 Cancel Intent Reconciliation

**Priority:** P0 if cancellation reason capture is live.

See §5.4.

## 7.3 Subscription State Cache Refresh

**Priority:** P1.

- Daily job.
- For each Pro user, re-query Stripe and refresh cached user fields.
- Catches missed webhooks.

## 7.4 Data Request Expiry Sweeper

**Priority:** P0 for GDPR operational hygiene.

- Daily job.
- Rows where `status = requested` and older than `DATA_REQUEST_EXPIRY_DAYS` → `expired`.

## 7.5 Soft-Deleted Account Hard-Delete Sweeper

**Priority:** P0 if account deletion is live.

- Daily job.
- After `ACCOUNT_DELETION_GRACE_PERIOD_DAYS`, cascade-delete user data.
- Delete/anonymize conversations, saved lines, weekly letters, cancellation free text, data requests, notification preferences.
- Preserve aggregate analytics only if user reference is removed.

## 7.6 OTP Cleanup

**Priority:** P1.

- Hourly job.
- Delete expired OTP records older than configured window, e.g. 10 minutes unused.

---

# 8. Prompt-Level Rules & AI Engine

## 8.1 Section 5.7 Framework — Current State

The Section 5.7 framework is implemented through production persona configs, prompt construction, classifier logic, and postprocessing.

| Element | Status |
|---|---|
| Character anchors | Populated for all 6 personas |
| Register architecture | Data populated in YAML; runtime UI chip selection deferred (Phase 5 → P3 post-feedback) |
| Brevity discipline | Active with postprocessing and sentence-boundary fix |
| Anti-flexing protocol | Populated and postchecked |
| Modern phenomenology bridge | Infrastructure shipped; map expanded 33 → 78 entries; trigger audit completed |
| Forbidden lexicon | Active universal + persona-specific checks |
| Eval suite | Deferred (Phase 6 → P1 post-revenue safety/quality audit) |

## 8.2 F2 Lite Suggested Insight Guardrails

Prompt must enforce:
- Specificity: reference actual user content from the conversation.
- No diagnosis: never label user emotions/conditions.
- No mysticism.
- Length ≤ 2 sentences.
- Trigger only after enough user material, baseline ≥10 user messages.
- Max 1 insight per conversation.
- Cost target: approximately $0.01–$0.05 per qualifying conversation.

## 8.3 Safety Pathway

Current status:
- Safety crisis pathway fixed via deterministic classifier-only path.
- LLM-side crisis directives removed.
- Medium risk now fully suppresses persona voice.
- Country-neutral safety copy; no US hotline-specific numbers.

Launch implication:
- This is defensible and safer for v1.
- It may diverge from earlier persona-specific safety styling, but safety consistency wins.

Post-launch safety audit (P1, see §13.1):
- Run 30–50 novel crisis phrases.
- Verify medium-or-higher escalation.
- Add regression tests if gaps appear.

## 8.4 Persona Never-Unprompted Enforcement

Per-persona never-unprompted lists and anti-flexing items are populated.

Runtime checks:
- `forbidden_phrases`
- `forbidden_lexicon_persona_specific`
- universal forbidden lexicon categories
- regenerate up to configured attempts
- strip if necessary
- sentence-boundary trim now reduces mid-sentence output risk

## 8.5 Phenomenology Bridge

Current state:
- Map expanded from 33 to 78 entries.
- Trigger audit added +88 natural-language verb-form and gerund triggers across 32 entries.
- High-frequency modern terms now better covered.
- Adversarial review was used for expansion quality.

Known post-launch gaps:
- ~10 missing triggers in `dating_apps` and `caregiving_burden` entries.
- ~200 persona shading paragraphs missing for the expanded entries.
- Marcus shading content originally planned as PR Β is now post-launch.
- Potential modern-term-leak runtime check can be added later if observed.

## 8.6 Sentence-Boundary Truncation

Three-layer fix shipped:
1. Attempt-2 budget multiplier increased from 1.0 to 1.15.
2. Strip-time sentence boundary trim with hard-cut fallback.
3. Observability hook: `brevity_passed_but_mid_sentence`.

Post-launch monitoring:
- If `brevity_passed_but_mid_sentence` fires in more than 5% of qualifying replies, revisit with best-full-sentence-across-regens strategy.

## 8.7 Diagnostic Support Prompt

The diagnostic block format in mailto is client-side.
Server-side diagnostic enrichment may happen through support inbox parsing, but remains out of v1 scope unless urgently needed.

---

# 9. Auth & Account

## 9.1 Platform-Aware OAuth Provider Order

For v1 web/PWA launch:
- Web/PWA: Google, email
- Apple Sign In deferred to native app submission (v2)

## 9.2 Account Linking Security

Rules:
- Auto-link two providers only when both report `email_verified: true`.
- If unverified, require OTP confirmation before linking.
- Never link accounts based on email string alone.

## 9.3 OTP State Machine

States:
- Wrong code attempts 1–4 → inline error, retry
- Wrong code attempt 5 → lockout 15 minutes
- Expired code >10 minutes → prompt to send new code
- Resend cooldown → disabled resend link with countdown
- >5 OTP requests/hour → rate-limit message
- Different email → back to sign-in with field cleared

## 9.4 Account Deletion

Two-stage deletion:

### Stage 1 — Soft Delete

- Set `users.account_deleted_at = now()`.
- Invalidate sessions.
- Send account deleted email with recovery instructions.
- Allow recovery within grace period, default 30 days.

### Stage 2 — Hard Delete

- Daily sweeper deletes after grace period.
- Cascade user data.
- Delete personal data fields.
- Anonymize aggregate analytics.

## 9.5 Logout Behavior

On sign out:
- Clear access token, refresh token, session cookie.
- Clear user-specific cached conversations, saved reflections, profile, subscription state, last active session context, persona preferences, last-viewed letters.
- Keep only non-identifying device preferences.

Allowed to keep:
- View mode
- Theme preference if implemented
- Language preference

Not allowed to keep:
- Last active persona
- Last conversation ID
- Plan state
- Email/name
- Any user-generated content

## 9.6 Disclaimer Re-Acceptance

On sign-in:
- Check current effective disclaimer version.
- If user has not accepted it, force re-prompt before app entry.

---

# 10. Privacy & Compliance

## 10.1 Article 17 — Right to Erasure

Implemented through account deletion flow and two-stage deletion.

## 10.2 Article 20 — Data Portability

v1 process:
1. User submits request.
2. `data_requests` row created.
3. Founder/admin notified.
4. Founder exports user data as JSON or CSV.
5. Sends to account email.
6. Marks request completed.

Target SLA:
- Regulatory ceiling: 30 days.
- Practical aim: under 7 days.

v2:
- Automated export pipeline with signed download URL.

## 10.3 Personal Data Classification

Must be deleted or protected:
- User messages
- Cancellation free text
- Support email contents
- Saved lines
- Weekly letter contents
- User name/email
- IP address/device fingerprint if logged

Analytics:
- Must aggregate or redact.
- Never expose raw personal data in dashboards.

## 10.4 Article 16 — Rectification

For v1, handle lightly through policy/support language:

> To correct your name, update it with your sign-in provider or contact support.

## 10.5 Cookie / Consent Posture

If web/PWA in EU:
- Strictly necessary cookies only → likely no consent banner needed.
- Analytics/marketing cookies → consent required.
- Verify final implementation before launch.

## 10.6 Privacy Policy Requirements

Privacy Policy must cover:
- Data collected
- Purposes
- Retention periods
- User rights
- Data sharing: Stripe, LLM provider, hosting, email provider
- Contact / DPO-style contact
- Data export and deletion process

---

# 11. Notifications

## 11.1 Email Channel

Email-only in v1 unless push is explicitly reprioritized.

Templates potentially needed:
- Weekly letter (only if weekly letters in v1)
- Account deletion confirmation
- Data export ready
- Past-due notice if not relying solely on Stripe
- Welcome email, optional

## 11.2 Push Notifications

Deferred to v2 (and to native app submission).

Rules when later implemented:
- Prompt after engagement signal, e.g. 3 conversations or first saved insight.
- Do not ask permission on first open.

## 11.3 In-App Notification Banner

Deferred to v2.

---

# 12. Frontend Behavior

## 12.1 State Preservation

Persist across journey where relevant:
- Original paywall context
- Conversation persona
- Onboarding selections
- Bottom tab active state
- Bring-another-mind chain
- Safety mode flag per session
- D2/D3 view preference
- Disclaimer acceptance
- Saved insight tag
- Free-tier save count
- Free-tier insight preview used
- Last conversation per persona, unless logout clears it
- OTP attempt count server-side
- Linked auth providers
- Subscription state cache, refetch after Stripe return
- Active cancel intent
- Pending data request status
- Notification preferences

## 12.2 Validation Patterns

- Type DELETE: case-sensitive `DELETE`; trim whitespace.
- OTP: 6 digits, auto-advance, paste full code support.
- Email: standard validation; reject obvious garbage; support international-valid formats.
- Free text: H6 other text max 300 chars.

## 12.3 Loading & Error States

- H5 loading: subtle skeleton; avoid loud SaaS shimmer.
- H5 error: "We couldn't load your subscription." + Try again.
- Avoid vague "Oops!" style copy.
- Use specific verbs.

## 12.4 Sheet Behavior

- Bottom sheets dismissable by Cancel, backdrop, drag-down, Esc, Android back.
- Same analytics event across dismiss paths.
- No stacked modals.

## 12.5 Empty Conversation Dedup Behavior

Current shipped behavior:
- Backend returns existing empty conversation for `(user, persona, ritual)` tuple when `message_count == 0`.
- Frontend includes in-flight flag and disabled state.
- Backend is the main defense against race windows.

Known post-launch improvement:
- True lazy-create routing refactor to eliminate all empty conversation rows, deferred to v2.

---

# 13. Post-Launch Backlog — P1 to P4

## 13.1 P1 — Early Post-Revenue Cleanup / Safety & Quality Audit

1. **Phase 6 — Eval suite + CI**
   - 4 tests per Section 5.7 spec: Distinctiveness, Brevity, Anti-Flex, Listening.
   - Run on each PR via GitHub Actions.
   - Includes adversarial classifier coverage: 30–50 novel crisis phrases → verify medium-or-higher escalation. Addresses residual risk from removing LLM-side crisis directives in Bug #33 fix.
   - Time-box: if 4/4 tests don't pass for all personas, fix what's broken but don't write a 5th test.

2. **Formal production smoke test documentation for `user_name` removal**
   - Incidentally verified during burnout test session.
   - Formal written smoke test still deferred.

3. **Monitor sentence-boundary observability**
   - If `brevity_passed_but_mid_sentence` fires >5%, revisit with best full-sentence reply across regen attempts.

## 13.2 P2 — Product / AI Refinements

1. **Modern-term-leak post-check**
   - Add eval category or forbidden lexicon category when bridge active.
   - Reactive unless leaks appear in production.

2. **Adversarial truncation strip UX smoothing**
   - If strip kicks in after retries, trim to last full sentence and append graceful pivot.

3. **Context-aware safety variants**
   - More nuanced variants for self-harm, harm-to-others, eating disorder, abuse, grief.
   - Only after deterministic safety baseline is stable.

## 13.3 P3 — Post-Launch / Post-Feedback Queue

1. **Phase 5 — Register architecture + UI chips + classifier**
   - Data populated in all persona YAMLs.
   - Build: chip-driven runtime selection from UI; classifier logic that matches user input to register.
   - Time-box: if 4th day and chip UX doesn't feel right, ship classifier-only and defer chips.
   - Trigger to revisit: user feedback indicates register variation valuable, OR product team validates demand.

2. **~10 missing triggers**
   - `dating_apps` and `caregiving_burden` entries noted as incomplete.
   - Low ROI vs shipped trigger coverage.

3. **~200 persona shading paragraphs**
   - New phenomenology entries need per-persona shading.
   - Prioritize high-frequency entries: situationship, FOMO, love bombing, grindset, sunday scaries.

4. **Marcus shading content**
   - Original Phase 4 PR Β (33 strings).
   - Deferred to post-launch.

5. **Real persona avatar artwork**
   - Current emoji/avatar placeholders acceptable for early launch unless brand bar requires upgrade.

6. **Frontend race in same render frame**
   - Current backend dedup catches it.
   - True synchronous prevention would use `useRef` flag before re-render.

## 13.4 P4 — Technical Debt / Infrastructure

1. **`make state` infrastructure repair**
   - Current target invokes `claude` CLI; founder uses VS Code extension.
   - Workaround: manual state entries.

2. **Local test environment repair**
   - Some tests fail locally due to missing dependencies such as `jinja2`.
   - Resolve via `pip install -r requirements.txt`, `requirements-dev.txt`, or Docker-only decision.

3. **`seed.py` UPDATE branch bug**
   - Does not set `is_active=True` on update path.
   - Previously caused invisible personas; direct SQL fixed immediate issue.

4. **Decision E logging visibility in Render UI**
   - Event names appear; structured fields do not render clearly.

5. **Production env vars hardening**
   - Move hardcoded URLs out of committed `.env.production`.
   - Improve dependency pinning.

6. **Greek source text editions for RAG corpus**
   - Decision pending.

7. **Nietzsche persona decision**
   - Frontend landing display removed.
   - Backend YAML retained for v2.
   - Future decision: build 7th persona or permanently remove from marketing.

8. **Runtime template structured-field rendering**
   - `system_base.jinja2` historically did not consume all structured fields.
   - Postprocessing catches many violations, but prompt-level guidance may be less efficient.
   - Revisit only if regenerate frequency or quality issues justify it.

9. **Priority hints for overlapping phenomenology mappings**
   - Add optional `priority_over` schema for edge cases like burnout + caregiving.

10. **Render API web service `WEB_CONCURRENCY=1` bottleneck**
    - Free-tier `philosopher-api` web service allows only 1 concurrent request.
    - Cold-start delay 30-60 seconds after 15 minutes of idle traffic.
    - Resolved by upgrading to Render Starter tier (~$7/month).
    - Trigger to upgrade: BEFORE first UAT tester or BEFORE first paying user, whichever comes first.
    - Mentor recommendation: upgrade now to avoid friction during 43-screen UI development cycle and prevent first-impression damage with UAT testers.
    - Status as of 2026-05-06: Render PostgreSQL `philosopher-db` upgraded to paid tier (resolves 30-day expiry risk). API web service still free pending founder decision.

---

# 14. v2 / Post-MVP Backlog

## 14.1 Product Features

- Multi-mind features: Council Mode, Compare View
- Rituals library
- F2 full insight engine across conversations
- F5 themes dashboard
- F4 PDF export
- D4 search/filter minds when persona count >12
- F6 conversation search when users have 20+ conversations
- F1 "By theme" filter activation
- Personalized Mind-of-the-day rotation
- Per-persona greeting variants based on selected need

## 14.2 Subscription & Billing

- Pause subscription
- Cancellation discount offers
- Win-back campaigns
- Plan change UX
- Embedded Stripe Payment Element
- Multi-currency support
- A/B test on upgrade headline

## 14.3 Privacy & Compliance

- Automated data export pipeline
- In-app account correction
- Self-service data correction interface

## 14.4 Notifications

- Push notification permission flow
- In-app notification banner
- Smart reminder timing

## 14.5 Settings & Account

- Custom avatar upload
- Multiple linked auth providers UI
- Active sessions list
- More account-linking edge cases
- Richer disclaimer re-acceptance UX

## 14.6 Discovery

- D3 grid card 1-word category microcopy when persona count grows

## 14.7 Operational

- Soft cap notice for stacked "Bring another mind" chains
- Library offline read-only mode
- D3 ordering perception A/B test

## 14.8 Native App Submission

- iOS App Store submission
  - Apple Sign In production cert
  - App icon per platform specs
  - Screenshots per platform specs
  - App privacy labels
  - Apple HIG compliance review
- Google Play submission
  - Data safety form
  - Play Store assets
- Cross-platform launch decision
- Push notification permission flow

---

# 15. Block 9 Frontend Behavior

Block 9 remains reuse-only at design level. No new components, ornaments, or tokens.

Block 9 (J1, J2, J3, J5) is included in the 43-screen build per founder decision 2026-05-06 — it ships in this v1 launch, not post-launch.

## 15.1 Routing & Rendering

- J1 and J2 are full-screen replacements between status bar and tab bar.
- J3 and J5 are in-tab body replacements.
- F1/F6 headers remain above empty state card.
- Filter pills hidden while F1 is empty.
- Tab bar remains visible.
- Switching tabs while in J1/J2 re-renders same error/offline state with newly active tab.

## 15.2 Retry Behavior

- "Try again" is user-initiated only.
- No auto-retry on J1.
- J2 does not silently dismiss when connection returns; user retries or navigates.
- Shared CTA CSS: `min-width: 140px; white-space: nowrap;`.

## 15.3 State Derivation

- J3 renders when `saved_lines_count = 0`.
- J5 renders when `conversation_count = 0`.
- Derived live; no DB flags.
- Transition instant after first save/conversation.

## 15.4 Status Bar Treatment

- J2: signal/wifi icons at 0.35 opacity; battery full opacity.
- J1: all status bar icons full opacity.

## 15.5 Forbidden Patterns

- No Rust color on J1.
- No per-tab copy variants on J2.
- No offline availability promise unless offline cache exists and is tested.
- Reuse existing offline and calm-pause ornaments.
- No filter pills on empty F1.
- No upgrade messaging on empty F1.

## 15.6 Optional Tracking

P1/post-revenue only unless analytics is already cleanly wired:
- `error.j1_rendered` `{tab, http_status, retry_count}`
- `error.j2_rendered` `{tab}`
- `empty_state.j3_rendered` `{user_age_days}`
- `empty_state.j5_rendered` `{user_age_days}`

---

# 16. Implementation Rules

## 16.A Operating Discipline (engineering principles)

These principles emerged from the Section 5.7 work cycles and are codified to prevent regression on future work.

1. **Quality-first execution + 3-day soft cap.** Engine-first ≠ engine-forever. UI-forever is the same enemy in different clothes. Each phase has a 3-day soft cap; if work stretches beyond, ship as-is and move on.

2. **Mentor cross-check on design-critical content.** Adversarial review by a different model where stakes warrant. Apply to persona-data work, lexical patterns, prompt content, schema design. The Phase 4 trigger audit returned 81 distinctiveness flags from a different model that the author had rationalized away.

3. **STOP-gate methodology.** INVESTIGATE → PROPOSE → APPROVE → IMPLEMENT → DIFF → APPROVE → COMMIT for any persona-data, schema, or refactor work. No skipping STOP-gates even when in a hurry. The `user_name` 10-minute production crash happened when grep summary stood in for full caller audit.

4. **Brain YAML supplements legacy fields, never replaces.** Two-layer defense: prompt-level soft + runtime-level hard. Postprocessing layer is the safety net even when prompt-level enforcement is incomplete.

5. **Production slug authoritative; brain YAML slug descriptive.** Use slug normalization map (`sigmund_freud → freud`, `carl_jung → jung`, `simone_de_beauvoir → de_beauvoir`) when slug mismatch exists.

6. **Distinctiveness test for content matching.** When authoring lexical patterns that fire on user input substring (triggers, classifier patterns, regex, forbidden phrases), test: "can I think of 2-3 plausible alternative meanings outside the intended context?". If yes, the pattern fails. Self-review necessary but not sufficient — adversarial cross-model review catches what the author rationalized away.

7. **UAT mix mandatory.** Close friends + acquaintances + strangers. Friends-only ≠ market validation.

8. **≥2/5 spontaneous "I'd pay" launch criterion.** Below threshold → iterate before public launch.

## 16.B Coding & Scope Rules

1. **This v5 file is the source of truth.** Do not use older backlog files for priority decisions.
2. **Do not reopen Phase 4 stabilization work unless a launch test fails.** The 8-item closed list is closed.
3. **Use full diffs, not grep summaries, before claiming a refactor is complete.** The `user_name` hotfix showed why caller audits matter.
4. **DB migrations require approval before applying.** Schemas in this file are implementation guidance, not automatic migration permission.
5. **Test cancellation and payment flows end-to-end.** This is the highest-risk commercial surface.
6. **Never call Stripe from UI.** Use backend entitlement/state routes.
7. **Founder approval required for:** new env vars, new third-party services, new background jobs, schema changes to existing tables, new paid-plan behavior.
8. **Do not expand scope.** No retention mechanics, billing experiments, notification types, or extra personas unless explicitly approved.
9. **Safety beats persona style.** The deterministic crisis pathway may suppress persona voice; that is acceptable for launch.
10. **Launch validation must include strangers.** Close friends alone are not market validation.
11. **Keep post-launch backlog visible but do not let it block launch.** UI-forever is the same trap as engine-forever.
12. **Greenfield, not refactor (NEW 2026-05-07).** Old screens are deleted, not refactored. Each new screen built fresh on the spec-compliant foundation (Setup PR tokens + greenfield shell). Backend integration glue (`apps/web/lib/`, `middleware.ts`) preserved through deletion. Reversal trade-offs documented in HANDOFF_BRIEF_v5 §21 2026-05-07.

---

# 17. Immediate Recommended Next Sequence

**Per founder decision 2026-05-06:** build all 43 specced screens before public launch. This reverses the 2026-05-04 "critical subset only" compromise. Order follows `SCREENS_TRACKING_v4.md` block sequence.

## 17.1 UI Implementation Order — 43 Screens

**Block A — Authentication (5 screen items)**
1. A1 — Splash / loading
2. A2/A3 — Sign up + Sign in (merged single screen)
3. A4 — Trouble accessing email
4. A5 — OTP / Email verification
5. A6+A7 — Combined age + positioning disclaimer

**Block B — Onboarding (6 screens)**
6. B1 — Welcome
7. B2 — What brings you here?
8. B3 — What do you need most?
9. B4 — Best matches
10. B5 — Persona detail (unlocked / default)
11. B6 — Persona detail (Pro-locked variant)

**Block C — Chat experience (9 screens)**
12. C1 — Chat live conversation
13. C2 — Chat initial loading
14. C3 — Save line confirmation
15. C4 — Failed message + retry
16. C5 — Daily limit reached (free user)
17. C6 — Weak connection / offline (3 sub-states)
18. C7 — Safety mode activation
19. C8 — First persona greeting
20. C9 — Bring another mind flow (2 sub-states)

**Block D — Discovery (3 screens)**
21. D1 — Home / Today (2 states)
22. D2 — Explore Minds, Carousel/list view
23. D3 — Explore Minds, Grid view

**Block F — Reflection (5 screens)**
24. F1 — Saved reflections
25. F2 — Suggested insights (lite, in-chat)
26. F3 — Weekly letter inbox
27. F4 — Weekly letter detail
28. F6 — Reflection history (UI: "Past conversations")

**Block H — Subscription & Billing (7 screens)**
29. H1 — Upgrade / pricing
30. H2 — Checkout loading bridge
31. H3 — Payment success
32. H4 — Payment failed
33. H4b — Payment canceled (gentle variant)
34. H5 — Subscription management
35. H6 — Cancel subscription flow (bottom sheet)

**Block I — Account & Settings (6 screens)**
36. I1 — Account hub
37. I2 — Notifications
38. I3 — Privacy & data
39. I4 — Help & support
40. I5 — About & legal
41. I6 — Logout (bottom sheet)

**Block J — Empty / error states (4 screens)**
42. J1 — App-wide server error / 5xx
43. J2 — App-wide offline (non-chat shell)
44. J3 — Empty saved reflections
45. J5 — Empty conversation history

> Note on count: `SCREENS_TRACKING_v4` reports **43 effective specced screens** because A2/A3 are a single merged screen and A6/A7 are a single combined screen. The 45 line items above expand the merges for implementation tracking.

## 17.2 Parallel and Post-UI Sequence

While UI is in progress, run in parallel where possible:
- **Stripe wiring** (available from 2026-05-11) — can start as soon as Block H screens exist, even in placeholder form.
- **Stripe entitlement + cancellation end-to-end testing** — after Block H + Stripe.
- **Legal copy** — Terms, Privacy Policy, disclaimer copy. Can be drafted during early UI work and finalized before launch.
- **Email infrastructure** — provider setup, templates, SPF/DKIM/DMARC.
- **Founder runbooks** — refund, account recovery, GDPR fulfillment, cancellation override, safety escalation review.

After all UI complete:
- **Production smoke test** per §2.1.A.
- **UAT** with 3–5 mixed testers (close + acquaintances + strangers).
- **Decision gate:** ≥2/5 spontaneous "I'd pay" → public launch (web/PWA only).
- If <2/5 → iterate before public launch.

## 17.3 Estimated Timeline

Per founder decision 2026-05-06:

| Phase | Estimate | Status |
|---|---|---|
| Setup PR + Greenfield scaffold | 1 day actual | ✅ DONE 2026-05-07 |
| 43-screen UI build | 8–12 weeks (revised down from 8–13 — clean foundation eliminates legacy debugging) | ⏳ Next |
| Stripe wiring + testing (calendar-gated start 2026-05-11) | 1–2 weeks (parallelizable with UI) |
| Legal + email + runbook prep | 1 week (parallelizable with UI) |
| UAT + iteration | 1–2 weeks |
| **Total realistic to first paying user (web/PWA only)** | **~12–16 weeks from 2026-05-06** |

The 2026-05-04 estimate of "~6-7 weeks to first paying user" is superseded by this decision.

## 17.4 Sequence Trade-offs (for reference)

The founder explicitly chose Plan A (all 43 before launch) over two alternatives:
- **Plan B** — hybrid: critical subset (16-20 screens) + Stripe + UAT → launch with payment → remaining screens as P1. Estimated ~5-7 weeks to first revenue.
- **Plan C** — 43 screens with parallel UAT prep on partial cohorts during UI work. Estimated ~10-13 weeks.

These alternatives are documented here so that if circumstances change (timeline pressure, runway concerns, signal from early testers), the founder can pivot to Plan B without re-litigating the decision from scratch.

---

**End of Implementation Backlog v5.**
