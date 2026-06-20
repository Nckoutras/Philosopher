# PHILOSOPHER — Project State v20

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v20 = v19 baseline (2026-06-16, captured through PR #316) + 2026-06-21 session delta (#317–#337).** This batch shipped the **Insight engine end-to-end** (recurrence + shift detection, in-chat chip, provenance line, three-action card), the **Insight → Mirror loop** (insight-seeded mirror reflection), the **weekly-letter-from-insight-spine + email delivery**, and the **monthly "season finale"** reusing the weekly engine. Migration head moved **027 → 031**. See the v20 session delta below.
>
> **v19 = v18 baseline (2026-06-15, through PR #313) + 2026-06-16 delta (#315–#316):** portraits standardized to WebP (migration 026), two new pro-tier personas Orwell + Musashi (migration 027), roster 9 → 11. Full detail in `PROJECT_STATE_v19.md`.
>
> **v18 = v17 baseline + Sunday Letter / Revisit / Letter share / Reflections feed (migrations 022–025).** Full detail in `PROJECT_STATE_v18.md`.
>
> **Generated:** 2026-06-21 (v20 rotation) · **Last updated:** 2026-06-21 (insight engine + insight→Mirror loop + weekly email + season finale; current main `4c4221c9`)

> **v20 conflict resolution rule:** Where v20 conflicts with v19 or earlier, v20 wins. Production reality always wins over docs.

> **⚠️ LIVE DATABASE: Supabase project `bvzeuwzqgnqcghvqghtb` (Oregon, us-west-2) is the only live database. The old project `plecolxlzshkfvybszgs` (eu-west-1 / Ireland) is legacy / inactive; do not write to it. All Render services must point to Oregon.**

---

## 2026-06-21 Session Delta — Insight engine end-to-end · Insight → Mirror loop · Weekly email + Season finale

> Appended as v20. Where this conflicts with earlier sections, this section wins. **Current main SHA: `4c4221c9` (PR #337).**

### The Insight engine — SHIPPED and LIVE (#323, #324, #327, #332, #333, #334)

A factual recurrence/shift detector that surfaces durable "Insights" and routes them into reflection. **The detector is wired and running** — not a dormant task.

- **Detector:** `services/memory_service.py:detect_recurrence`. When a memory the user just raised echoes memories from OTHER conversations (cosine ≥ `RECURRENCE_SIM_THRESHOLD = 0.75`, ≥ `RECURRENCE_MIN_PRIOR = 1` prior-conversation match), it writes a durable `Insight`. One classify+phrase LLM call decides **`pattern`** (default) vs **`shift`** (genuine directional stance change, hedged to a certainty ladder). Throttle: max one non-dismissed insight per user per `RECURRENCE_THROTTLE_HOURS = 6`, and at most one per conversation. The detector is wrapped in try/except and never raises into its caller.
- **Wiring:** called from the ARQ **`extract_memory_task`** (`workers/arq_worker.py`), immediately after memory extraction commits, in the same session. **Note:** this is distinct from the older dormant `generate_insight_task` — **TD-05 ("wire generate_insight_task") remains open** and refers to that separate task, not the recurrence detector.
- **In-chat chip + card (#323):** the last assistant message can carry a quietly-glowing insight chip (`components/chat/QuickActionsRow.tsx`) that expands to `components/chat/InsightCard.tsx` (variant `chat`).
- **Provenance line (#333):** when `source_count >= 2`, the card shows "Noticed across {N} of your conversations" under the eyebrow. `source_count` = distinct prior conversations the theme echoed in + the current one; stored when the detector fires (migration 030).
- **Today insight card (#327, #332):** Today surfaces the insight spine as a passive standing card (`variant='today'`), within a `TODAY_INSIGHT_MAX_AGE_DAYS = 14` staleness window. #332 added the **brand-seal ornament** (`/insight_seal.png`, 44×44, Today variant only) and a cleaner primary CTA. The old secondary "Dismiss"/"Doesn't ring true" affordance was reworked (see three-action card).
- **Three-action card (#334):** the card now offers **"Reflect in the Mirror"** (primary, full-width), **"Doubt this"** (navigates to the Counterview stub; does NOT dismiss), and **"Discard this"** (the quietest action — performs the dismiss). For a `shift` insight the primary is "See how this changed" → You-vs-You.

### The Insight → Mirror loop — SHIPPED (#335, #336, #337)

"Reflect in the Mirror" on a (non-shift) insight opens the mirror reader on an **insight-seeded** reflection.

- **Backend (#335):** `POST /insights/{id}/reflect` (`routers/memory.py`) → synchronous `services/insight_mirror_service.py:generate_insight_mirror`. Loads the insight, **dedups by `insight_id`** (returns the existing mirror — no second LLM call), reads the source conversation's user messages, hosts in the insight's persona voice, and writes a `Mirror` with **`kind="insight"`**, `insight_id`, `source_count`-independent, `status` ∈ {generated, empty, suppressed}, full-precision `period_start = now()`. Safety gate (high/critical → suppressed); empty gate (< 2 user messages → empty); graceful degrade to empty on LLM/parse failure. `INSIGHT_MIRROR_PROMPT` is a local variant of the weekly `MIRROR_PROMPT` carrying the same `{moments:[{said,meant}], thread}` shape + the same wellbeing guardrails, so `MirrorOut`/`MirrorVerdictCard` rendering is unchanged. Reuses the mirrors router's `_mirror_out` + `_load_persona` serializer (one source of truth). Migration 031 adds `mirrors.insight_id` (FK insights ON DELETE SET NULL), extends `ck_mirrors_kind` to allow `'insight'`, and adds a partial unique index `uq_mirrors_insight` (DB-level dedup).
- **Latest-mirror exclusion (#336):** `get_latest_mirror` gained `Mirror.kind != "insight"` in its base WHERE — insight mirrors are reached ONLY via the `?insightId=` flow, never as the weekly reader's "latest". (Free was already preview-only; this covers paid.)
- **Reader (#337):** `app/app/mirror/page.tsx` reads `insightId` from `window.location.search` inside the load effect (Suspense-safe, no `useSearchParams`); when present it calls `api.reflectInsight(id)` instead of `getLatestMirror()`, shows a "Holding up the mirror…" wait, then runs the existing reveal animation + save/ring-true/share unchanged. `empty`/`suppressed` → a gentle neutral fallback (same copy for both, never exposes safety) with no animation/controls. The weekly load path (no `insightId`) is byte-identical.
- A saved insight mirror appears in the Reflections feed and supports ring-true/share like any Mirror row (the feed already keys off any `Mirror`).

### Counterview — STUB only (#334), ritual UNBUILT

- `app/app/counterview/page.tsx` exists as a **tasteful placeholder** (DS v5 vellum, Cormorant "Counterview", a quiet "on its way" line, back control). It reads the `?insightId=` query param **only via the URL** and does nothing with it yet. **The Counterview ritual is not built** — this is a navigation target for "Doubt this", not a feature. Remains the only unbuilt ritual.

### Weekly letter from the insight spine + email delivery — SHIPPED (#325, #326)

- **Synthesis from the insight spine:** `generate_weekly_letter_task` (`workers/arq_worker.py`) fetches the period's non-dismissed insights, formats them as a `<what_the_room_noticed>` spine, and passes that to the letter prompt; raw messages are the texture.
- **Email delivery — now wired:** `_maybe_send_weekly_letter_email` renders + sends the letter via Resend and sets `weekly_letters.email_sent_at` (idempotent — no double-send). **This closes TD-33** (Weekly Reading ARQ email delivery). A localhost guard suppresses sending when `API_BASE_URL` is unset/localhost (so no broken unsubscribe links reach real users).
- **Opt-out + unsubscribe:** migration 028 adds `users.weekly_email_opt_out` (NOT NULL DEFAULT false — opted in). Public endpoint `GET /unsubscribe/weekly?u=<user_id>&t=<hmac>` (`routers/unsubscribe.py`) flips the flag; token is `HMAC-SHA256(user_id)` keyed by `JWT_SECRET`.
- **Deploy requirement (see `DEPLOY_NOTES.md`):** `API_BASE_URL` must be the public backend URL or all weekly emails are suppressed by design.

### Monthly "Season finale" letter — SHIPPED (#328, #329, #330, #331)

- **Generation:** `generate_monthly_letter_task` reuses the weekly engine over a calendar-month window, gated by `MONTHLY_MIN_MESSAGES = 15`, writing a `weekly_letters` row with `kind='monthly'`. Email delivery reuses `_maybe_send_weekly_letter_email` (`reading_label="monthly"`).
- **Schema (migration 029):** `weekly_letters.kind VARCHAR(20)` (CHECK `kind IN ('weekly','monthly')`, existing rows → `'weekly'`); the per-period unique index is recreated as `(user_id, period_start, kind)` so a month's 1st falling on a Sunday cannot collide with that week's letter.
- **API (#329):** `WeeklyLetterOut` now exposes `kind` (`schemas/__init__.py`); `GET /weekly-letters` and `/{id}` return it.
- **Frontend (#330, #331):** `app/app/letters/[id]/page.tsx` renders `components/letters/SeasonFinaleView.tsx` when `letter.kind === 'monthly'` (else the standard weekly reader) — a premium season reader (through-line / what changed / season ahead / keepsake pull-quote + typographic W-monogram seal). The season share card is driven by `seasonImagePreview={letter.kind === 'monthly'}` into `SharePreviewModal` (no new static asset).

### Guide refresh (#318, #320, #322)

- `app/app/guide/page.tsx` — Wise Room copy refresh + ritual rename + minds synced to 11; minds tappable to persona detail; responsive thumbnails + press effect + taller hero. Sunday-letter links converted to buttons (#319). iOS share Send gated on the prepared image to keep the share synchronous (#321).

### Migrations added this session

> **alembic head is now `031_mirrors_insight_id`** (chain …027 → 028 → 029 → 030 → 031).

- **028 `user_weekly_email_opt_out`** — `users.weekly_email_opt_out BOOLEAN NOT NULL DEFAULT false` (schema).
- **029 `weekly_letters_kind`** — `weekly_letters.kind` + recreate unique index as `(user_id, period_start, kind)` (schema).
- **030 `insights_source_count`** — `insights.source_count INTEGER NULL` (schema; existing rows NULL).
- **031 `mirrors_insight_id`** — `mirrors.insight_id UUID NULL` FK insights ON DELETE SET NULL; `ck_mirrors_kind` extended to `('weekly','preview','insight')`; partial unique index `uq_mirrors_insight ON (insight_id) WHERE insight_id IS NOT NULL` (schema).

### Key superseded facts (v20)

- **Weekly Reading ARQ email delivery (TD-33)** — was 🔴 open ("`email_sent_at` unused") → **🟢 DONE (#325): `_maybe_send_weekly_letter_email` sends + stamps `email_sent_at`; localhost `API_BASE_URL` guard.**
- **The Insight engine** — was F2 "Suggested insights (lite)" placeholder / in-chat only → **🟢 LIVE: recurrence + shift detector wired into `extract_memory_task`; in-chat chip + Today card + three-action card + provenance.**
- **Insight primary CTA** — was the generic "Reflect in the Mirror" → `/app/mirror` → **now seeds the mirror: `/app/mirror?insightId={id}` → `POST /insights/{id}/reflect`.**
- **Migration head** — was `027_add_orwell_musashi` → **`031_mirrors_insight_id`** (028–031 added).
- **Counterview** — still 🔴 NOT built, but now has a **navigation stub** at `/app/counterview` (target of "Doubt this").

---

## Earlier session deltas (v16 → v19)

Carried forward by reference (additive convention). See:
- **v19** (#315–#316, WebP portraits + Orwell/Musashi) — `PROJECT_STATE_v19.md` §"2026-06-16 Session Delta".
- **v18** (Sunday Letter / Revisit / Letter share / Reflections feed, migrations 022–025) — `PROJECT_STATE_v19.md` §"2026-06-15 Session Delta" / `PROJECT_STATE_v18.md`.
- **v17 and earlier** — `PROJECT_STATE_v17.md` / `PROJECT_STATE_v16.md`.

---

**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment (canonical):** https://thinkalike.netlify.app
**Custom domain (DNS in progress):** https://thegreatminds.app
**Backend:** https://philosopher-api-z9l9.onrender.com

---

## 1. Stack (locked)

Unchanged from v19. See `PROJECT_STATE_v19.md §1`. (Next.js 14 / FastAPI / Postgres 17 Supabase Oregon / Redis+ARQ / Anthropic Claude / OpenAI embeddings / OTP+JWT / Stripe sandbox / Resend / Pillow share cards.)

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-06-21** — Insight engine end-to-end (#323, #324, #327, #332, #333, #334), Insight → Mirror loop (#335–#337), weekly-letter-from-insight-spine + email delivery (#325, #326), monthly season finale (#328–#331), guide refresh (#318–#322). Current main: `4c4221c9`. Prior deploy 2026-06-16 — #315/#316 (`0a42b0cb`).
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3–5 fresh users still pending)

### Blocks A / B / C

Unchanged from v19. See `PROJECT_STATE_v19.md §2`.

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; PR1 #77). Live wiring pending (TD-28).
- **BETA bypass active:** No — `BETA_GRANT_PRO_TO_ALL=false`. Tier enforcement live via `get_user_tier`.
- **Rituals tab:** Live — **Mirror ✅** (PRs #166–#173) **+ insight-seeded mirror (v20, #335–#337)**; **Council ✅** (#182–#186); **You vs You ✅** (#193–#202); **Weekly Reading / Sunday Letter ✅** reader + **ARQ email delivery now wired (v20, #325)** + **monthly season finale (v20, #328–#331)**; **Letter to Future Self** functional, ARQ delivery still not wired; **Counterview** still unbuilt (navigation stub only).
- **Insight engine:** **LIVE (v20)** — recurrence + shift detector wired into `extract_memory_task`; in-chat chip, Today card, three-action card, provenance line, insight → Mirror loop.
- **Reflections:** Unified feed live (v18) — saved lines + Mirror/Council verdicts incl. `kind="insight"` mirrors; Mirror saves (025); client-side search.
- **Share v3 / Council share / Letter share / Season share:** Live.

---

## 3. Personas registered

Unchanged from v19 — **11 personas** (Free: Marcus Aurelius, Socrates, Lao Tzu; Pro: de Beauvoir, Epictetus, Freud, Jung, Wilde, Machiavelli, Orwell, Musashi). Council roster fixed (Machiavelli, Epictetus, Freud, de Beauvoir). See `PROJECT_STATE_v19.md §3`.

---

## 4. Database schema

### Migrations applied (chronological)

| Rev | Description | Applied | PR |
|---|---|---|---|
| 001–021 | See `PROJECT_STATE_v19.md §4` / v12 for full history | Pre-v18 | — |
| 022 | weekly_letters table | 2026-06-04 | Weekly Reading |
| 023 | messages.message_kind | 2026-06-07 | Conclusions |
| 024 | saved_lines.source_type → {manual_save, kept_insight, conclusion} | 2026-06-09 | Conclusions |
| 025 | mirror_saves table | 2026-06-12 | #277 |
| 026 | personas portrait_url → WebP (data migration) | 2026-06-16 | #315 |
| 027 | add george_orwell + miyamoto_musashi (data migration) | 2026-06-16 | #316 |
| **028** | **users.weekly_email_opt_out BOOLEAN NOT NULL DEFAULT false** | **2026-06-19** | **#325 / #326** |
| **029** | **weekly_letters.kind VARCHAR(20) CHECK ∈ {weekly,monthly}; per-period unique index recreated as (user_id, period_start, kind)** | **2026-06-19** | **#328 / #329** |
| **030** | **insights.source_count INTEGER NULL (distinct conversations a recurring theme was noticed across; existing rows NULL)** | **2026-06-20** | **#333** |
| **031** | **mirrors.insight_id UUID NULL FK insights(id) ON DELETE SET NULL; ck_mirrors_kind extended → {weekly,preview,insight}; partial unique index uq_mirrors_insight ON (insight_id) WHERE insight_id IS NOT NULL** | **2026-06-20** | **#335** |

**alembic_version = `031_mirrors_insight_id`** (chain …027 → 028 → 029 → 030 → 031). 028–031 are schema migrations.

> **Note on `insights`:** the `insights` table itself dates from `001_initial` (with `insight_type`); the v20 recurrence detector began *writing* to it (#323). Migration 030 added `source_count`.

### Live database state (verify on Render deploy)

```
alembic_version:        031_mirrors_insight_id   (Render auto-runs alembic on deploy; confirm 028–031 applied)
insights:               live (001); writes now active (recurrence/shift detector). source_count column (030).
mirrors:                kind ∈ {weekly,preview,insight}; insight_id column + uq_mirrors_insight (031)
weekly_letters:         kind ∈ {weekly,monthly} (029); email_sent_at now stamped on send (#325)
users.weekly_email_opt_out: column live (028; default false)
personas count:         11 (all active, WebP portraits)
source_chunks:          2476 across 7 personas (Orwell copyright-excluded; Musashi deferred → 0 chunks each)
```

### RLS state

**RLS DISABLED on all public tables.** Unchanged.

---

## 5. Backend endpoints

All v19 endpoints apply (see `PROJECT_STATE_v19.md §5` + `PROJECT_STATE_v16.md §5`). **New / changed since v19:**

| Method · Path | Router | Notes |
|---|---|---|
| `POST /insights/{id}/reflect` | `memory.py` (`insights_router`) | **NEW (#335).** Synchronous insight-seeded mirror; returns `MirrorOut`. Dedups by `insight_id`; `empty`/`suppressed` returned as clean 200 with null payload. |
| `GET /insights` · `PATCH /insights/{id}/dismiss` | `memory.py` | Existing (insight engine). Discard = dismiss. |
| `GET /unsubscribe/weekly?u=&t=` | `unsubscribe.py` | **NEW (#325).** Public, HMAC-SHA256(user_id) keyed by `JWT_SECRET`; flips `weekly_email_opt_out`. |
| `GET /weekly-letters` · `GET /weekly-letters/{id}` | `weekly_letters.py` | **CHANGED (#329):** `WeeklyLetterOut` now includes `kind` (`weekly`|`monthly`). |
| `GET /mirrors/latest` | `mirrors.py` | **CHANGED (#336):** base WHERE adds `kind != "insight"`. |

---

## 6–18.

Sections 6 (send-message), 7 (Council), 8 (persona error messages — Orwell/Musashi use the generic fallback), 9 (LLM validation), 10 (locked decisions), 11 (reconciliation history), 12 (BETA bypass — OFF), 13 (frontend architecture), 14 (session metrics), 15 (known bugs), 16 (env vars), 17 (key file paths), 18 (CLAUDE.md violations) — **unchanged from v19 except as noted below.** See `PROJECT_STATE_v19.md`.

### 14. Session metrics — 2026-06-21 (Insight engine · Insight→Mirror · weekly email · season finale)

| Metric | Value |
|---|---|
| PRs merged | #317–#337 (#317 was the v19 doc PR) |
| Migrations deployed | 028 weekly_email_opt_out, 029 weekly_letters.kind, 030 insights.source_count, 031 mirrors.insight_id |
| New endpoints | `POST /insights/{id}/reflect`, `GET /unsubscribe/weekly` |
| New services | `services/insight_mirror_service.py` |
| New screens | `/app/counterview` (stub); insight-seeded state of `/app/mirror`; `SeasonFinaleView` monthly reader |
| Key features | Insight engine live (recurrence/shift), insight→Mirror loop, weekly email delivery (TD-33 closed), monthly season finale |

### 17. Key file paths — new/updated in v20

- `apps/api/services/memory_service.py` — `detect_recurrence` (recurrence/shift detector + thresholds).
- `apps/api/services/insight_mirror_service.py` — NEW: `generate_insight_mirror` + `INSIGHT_MIRROR_PROMPT`.
- `apps/api/routers/memory.py` — `POST /insights/{id}/reflect` (reuses mirrors `_mirror_out`/`_load_persona`).
- `apps/api/routers/unsubscribe.py` — NEW: public weekly unsubscribe (HMAC).
- `apps/api/routers/mirrors.py` — `get_latest_mirror` excludes `kind="insight"`.
- `apps/api/workers/arq_worker.py` — `extract_memory_task` calls `detect_recurrence`; `generate_weekly_letter_task` (insight spine + `_maybe_send_weekly_letter_email`); `generate_monthly_letter_task`.
- `apps/api/schemas/__init__.py` — `InsightOut.source_count`; `WeeklyLetterOut.kind`.
- `apps/api/db/migrations/versions/028_*`, `029_*`, `030_*`, `031_*`.
- `apps/web/components/chat/InsightCard.tsx` — provenance line + three actions (Reflect / Doubt this → counterview / Discard this).
- `apps/web/components/chat/MessageList.tsx` — threads insight props (source count, doubt, discard).
- `apps/web/app/app/(tabs)/today/page.tsx` — Today insight card (seal, 14-day window, reflect→`?insightId=`).
- `apps/web/app/app/chat/conv/[id]/page.tsx` — insight handlers (reflect→`?insightId=`, doubt, discard).
- `apps/web/app/app/mirror/page.tsx` — insight-seeded reflect path + "Holding up the mirror…" + non-generated fallback.
- `apps/web/app/app/counterview/page.tsx` — NEW: placeholder stub.
- `apps/web/components/letters/SeasonFinaleView.tsx` — NEW: monthly season reader.
- `apps/web/app/app/letters/[id]/page.tsx` — dispatch on `kind === 'monthly'`; season share preview.
- `apps/web/lib/api.ts` — `Insight.source_count`, `Mirror`/`reflectInsight`, `WeeklyLetter.kind`.
- `apps/web/public/insight_seal.png` — NEW asset (Today insight ornament).

---

## 19. Open / Closed items

### Open items (P0 launch blockers) — carried from v19

Unchanged set: PR3a memory bugs (fresh-chat missing opening message/thumbnail; home "Continuing" 404s), OPS-001 (ote.gr re-sync), source_chunks re-ingest (TD-22), post-Oregon smoke test, TD-10 auth race, mobile nav smoke test, cold beta, consolidated polish PR, lawyer review, DNS + Resend domain, GDPR/DPA, founder runbooks, `PHENOMENOLOGY_BRIDGE_ENABLED` confirmation, RLS, UAT. See `PROJECT_STATE_v19.md §19`.

### Open items (P0 operational — must do before next PR)

- [ ] **.gitignore security debt** — `.env.local` NOT in `.gitignore`. (Carried — still open.)
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu.

### Parked rituals / engine fast-follows (P1–P2)

- [ ] **Counterview ritual** — only unbuilt ritual; `/app/counterview` is a stub. Design session required before build.
- [ ] **Letter-to-Future-Self ARQ delivery** — still not wired (distinct from weekly email, which is now done).
- [ ] **Detector → ritual routing** — "Doubt this" → Counterview is a stub target; full routing pending Counterview build.
- [ ] **Rituals-to-chat** — surface rituals from chat (post-cold-beta).
- [ ] **Insight detector threshold tuning** — `RECURRENCE_SIM_THRESHOLD` / `MIN_PRIOR` / `THROTTLE_HOURS` are launch defaults; tune against real volume.
- [ ] **TD-05 — wire `generate_insight_task`** — the separate dormant task (NOT the recurrence detector, which is live).

### Revenue blockers (P0 before first paying user)

- [ ] **Stripe renewal webhook (live)** — separate live-mode webhook with its own signing secret.
- [ ] **`ENVIRONMENT=production`** on Render API.
- [ ] **`API_BASE_URL`** set to the public backend URL (else weekly emails are suppressed by design — see `DEPLOY_NOTES.md`).
- [ ] **Live Stripe keys + live price IDs** (TD-28).

### Closed this session (2026-06-21)

- [x] **CLOSED** — **TD-33 Weekly Reading ARQ email delivery**: `_maybe_send_weekly_letter_email` sends + stamps `email_sent_at` (#325); opt-out + unsubscribe (#325, 028); localhost `API_BASE_URL` guard.
- [x] **CLOSED** — **Insight engine**: recurrence + shift detector wired into `extract_memory_task`; in-chat chip (#323), shift CTA branch (#324), Today card + seal (#327, #332), provenance (#333), three-action card (#334).
- [x] **CLOSED** — **Insight → Mirror loop**: `POST /insights/{id}/reflect` + insight-seeded reader (#335–#337); `get_latest_mirror` excludes insight (#336).
- [x] **CLOSED** — **Monthly season finale**: `generate_monthly_letter_task` + `kind` API + `SeasonFinaleView` + season share (#328–#331).

### Closed items (2026-06-16 and earlier)

See `PROJECT_STATE_v19.md §19`.

---

## 20. Pre-Launch Blockers

> These gate Stripe checkout / revenue activation. None may be deferred past the first paying user.

- [x] ~~`BETA_GRANT_PRO_TO_ALL`~~ — 🟢 OFF (2026-06-03)
- [x] ~~TD-11 tier resolution~~ — 🟢 COMPLETE (#203)
- [x] ~~End-to-end Stripe sandbox test~~ — 🟢 COMPLETE
- [ ] **Another-mind feature gate (post-cold-beta)**
- [ ] **Systemic frontend `plan` reliability bug** — fix before paid launch
- [ ] **Live Stripe wiring (TD-28)** — live keys + live price IDs + separate live-mode webhook + `ENVIRONMENT=production` + `API_BASE_URL`

---

**End of PROJECT_STATE v20.** Authoritative as of 2026-06-21 (Insight engine · Insight→Mirror loop · weekly email · season finale session). Supersedes `PROJECT_STATE_v19.md` (preserved as historical reference). Where this file conflicts with v19, v20 wins.
