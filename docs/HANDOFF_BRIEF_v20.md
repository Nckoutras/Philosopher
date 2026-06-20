# HANDOFF BRIEF v20 — Philosopher / The Wise Room

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-06-21
**Prior version:** `docs/HANDOFF_BRIEF_v19.md` (2026-06-16)
**Generated:** 2026-06-21 (v20 rotation)

**Block trigger for v20 rotation:** A full feature arc landed since the v19 doc (which stopped at PR #316): the **Insight engine** end-to-end, the **Insight → Mirror loop**, **weekly-letter email delivery** (closes TD-33), and the **monthly season finale**. Migration head moved 027 → 031.

**v20 summary (2026-06-21):** Insight engine ✅ LIVE (#323 recurrence detector + in-chat chip; #324 shift detection + branch CTA; #327 Today insight card + Dismiss rework; #332 brand seal + cleaner CTA; #333 provenance line + migration 030; #334 three-action card) — the detector runs inside the ARQ `extract_memory_task`. Insight → Mirror loop ✅ (#335 `POST /insights/{id}/reflect` + migration 031 `kind="insight"`; #336 `get_latest_mirror` excludes insight; #337 insight-seeded reader). Weekly-letter email delivery ✅ (#325 synthesize-from-insight-spine + Resend send + `email_sent_at`; #326 `DEPLOY_NOTES` / `API_BASE_URL`; migration 028 opt-out + HMAC unsubscribe). Monthly season finale ✅ (#328 generation reusing the weekly engine + migration 029 `kind`; #329 `kind` on the API; #330 `SeasonFinaleView`; #331 season share card). Guide refresh (#318–#322). Current main: `4c4221c9`.

**v19 summary (2026-06-16):** WebP portrait standard (#315, migration 026) + Orwell & Musashi (#316, migration 027), roster 9 → 11. Full detail in `HANDOFF_BRIEF_v19.md`.

**Status (delta from v19):**
- **Insight engine ✅ LIVE (2026-06-21)** — `detect_recurrence` (`memory_service.py`) wired into the ARQ `extract_memory_task`; constants `SIM 0.75` / `MIN_PRIOR 1` / `THROTTLE 6h`; `pattern` vs `shift` classify. In-chat chip + Today card + three-action card + provenance (`source_count`, migration 030).
- **Insight → Mirror loop ✅ (2026-06-21)** — `POST /insights/{id}/reflect` (sync, dedup by `insight_id`, `kind="insight"`); migration 031; `get_latest_mirror` excludes insight; reader seeds via `?insightId=`.
- **Weekly-letter email ✅ (2026-06-21, TD-33 closed)** — sends via Resend + stamps `email_sent_at`; opt-out (028) + HMAC unsubscribe; localhost `API_BASE_URL` guard. Synthesized from the insight spine.
- **Monthly season finale ✅ (2026-06-21)** — `generate_monthly_letter_task`, `weekly_letters.kind` (029), `WeeklyLetterOut.kind`, `SeasonFinaleView`, season share card.
- Earlier status (Blocks A/B/C, Stripe sandbox, paywall, Mirror/Council/YvY, Sunday Letter reader, Reflections feed, Orwell/Musashi) — unchanged; see `HANDOFF_BRIEF_v19.md`.

> **v20 conflict resolution rule:** Where v20 conflicts with v19 or earlier, v20 wins. Production reality always wins over docs.

---

## 2026-06-21 Session Delta — Insight engine · Insight→Mirror loop · Weekly email · Season finale

> Appended as v20. Where this conflicts with earlier sections, this section wins. **Current main SHA: `4c4221c9` (PR #337).**

**Insight engine (#323, #324, #327, #332, #333, #334) — LIVE:**
- `services/memory_service.py:detect_recurrence` — recurrence (cosine ≥ 0.75 vs OTHER conversations, ≥1 prior match) + one classify+phrase LLM call → `pattern` (default) or `shift` (hedged certainty ladder). Throttle 6h/user, max one per conversation. Try/except — never raises into its caller.
- **Wiring:** called from the ARQ **`extract_memory_task`** right after memory extraction commits. **NOT** the dormant `generate_insight_task` (that's still TD-05).
- Frontend: in-chat chip (`QuickActionsRow`) → `InsightCard` (variant `chat`); Today standing card (variant `today`, `TODAY_INSIGHT_MAX_AGE_DAYS=14`, `/insight_seal.png`); provenance "Noticed across {N} of your conversations" when `source_count >= 2` (030).
- **Three-action card (#334):** Reflect in the Mirror (primary) · Doubt this (→ `/app/counterview` stub, no dismiss) · Discard this (dismiss). `shift` primary = "See how this changed" → You-vs-You.

**Insight → Mirror loop (#335, #336, #337):**
- `POST /insights/{id}/reflect` (`routers/memory.py`) → `services/insight_mirror_service.py:generate_insight_mirror` (sync). Dedups by `insight_id`; writes `Mirror(kind="insight", insight_id, …)`; safety gate (high/critical → suppressed) + empty gate (< 2 user messages) + graceful degrade → empty. `INSIGHT_MIRROR_PROMPT` mirrors the weekly `{moments,thread}` shape + guardrails. Reuses mirrors' `_mirror_out` + `_load_persona`. Migration 031 (`mirrors.insight_id` + `ck_mirrors_kind` allows `insight` + partial unique `uq_mirrors_insight`).
- `get_latest_mirror` excludes `kind="insight"` (#336) — insight mirrors are reached ONLY via `?insightId=`.
- Reader (`app/app/mirror/page.tsx`): reads `insightId` from `window.location.search` inside the load effect (Suspense-safe); `api.reflectInsight(id)` vs `getLatestMirror()`; "Holding up the mirror…" wait; reuse animation + save/ring-true/share; `empty`/`suppressed` → gentle neutral fallback (no controls). Weekly path byte-identical.

**Weekly letter email + insight spine (#325, #326):**
- `generate_weekly_letter_task` builds a `<what_the_room_noticed>` spine from the period's non-dismissed insights and feeds it to the letter prompt. `_maybe_send_weekly_letter_email` sends via Resend + stamps `email_sent_at` (idempotent). Migration 028 `users.weekly_email_opt_out`; public `GET /unsubscribe/weekly?u=&t=` (HMAC-SHA256(user_id) keyed by `JWT_SECRET`). **`API_BASE_URL` must be the public backend URL on Render or all weekly emails are suppressed by design — see `DEPLOY_NOTES.md`.**

**Monthly season finale (#328–#331):**
- `generate_monthly_letter_task` (calendar month, `MONTHLY_MIN_MESSAGES=15`) writes `weekly_letters.kind='monthly'` (migration 029, unique index now `(user_id, period_start, kind)`). `WeeklyLetterOut.kind` exposed (#329). `app/app/letters/[id]/page.tsx` renders `components/letters/SeasonFinaleView.tsx` on `kind==='monthly'`; season share via `seasonImagePreview` (#330, #331).

**Counterview (#334):** `app/app/counterview/page.tsx` is a **placeholder stub** (DS v5 vellum, Cormorant "Counterview", quiet "on its way" line, back control). Reads `?insightId=` only via the URL; does nothing with it. The ritual is unbuilt.

**Guide (#318–#322):** Wise Room copy refresh + ritual rename + minds synced to 11; tappable minds; responsive thumbnails/press/taller hero; Sunday-letter links → buttons; iOS share Send gated on prepared image.

---

## Earlier session deltas (v16 → v19)

Carried forward by reference. See `HANDOFF_BRIEF_v19.md` (v19 #315–#316; v18 #277–#313; v17 #273–#275 + PR3a) and `HANDOFF_BRIEF_v16.md` (Council / YvY / revenue chain).

---

## Top of mind / Next (2026-06-21)

**Priority order:**

0. **Smoke-test the new surfaces (P-03 cadence):** insight chip → expand → three-action card (Reflect / Doubt this / Discard this; no awkward wrap on mobile); **Reflect → `/app/mirror?insightId=` → "Holding up the mirror…" → said/meant + thread**; re-open same insight = same mirror (dedup, no second wait); thin-conversation insight = gentle fallback; weekly mirror card (no `insightId`) still shows the weekly mirror; **Doubt this → `/app/counterview` stub (insight NOT removed)**; **Discard removes + stays gone on reload**; weekly + monthly letter email (with `API_BASE_URL` set) incl. working unsubscribe; `SeasonFinaleView` renders for `kind='monthly'`.

1. **PR3a memory bugs — 🔴 not started (highest priority):** fresh-chat missing opening message/thumbnail; home "Continuing" 404s. The only remaining PR3a cold-beta blocker.

2. **Cold beta with 3–5 fresh users** — once memory bugs resolved.

3. **Live Stripe wiring (TD-28) — 🔴 (P0 before any real payment):** live keys + live price IDs + separate live-mode webhook (own signing secret) + `ENVIRONMENT=production` + `API_BASE_URL` set on Render.

4. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**

5. **Counterview ritual (TD parked):** `/app/counterview` is a stub. Design session with Claude (chat) → build. Only unbuilt ritual.

6. **App-icon mark (TD-29).**

7. **Fast-follows (post-first-paying-user):** YvY funnel analytics; Council per-verdict saves + share redesign; insight detector threshold tuning (TD-35); cache the sync insight-mirror generate (TD-36); Letter-to-Future-Self ARQ delivery.

### Still-pending from prior sessions

- `.gitignore` security debt — fix before any code PR (branch `chore/gitignore-env-local`).
- Author smoke-test voice changes (6 personas).
- OTP-01 (ote.gr delivery failure) — investigate Render logs.
- compress mirror.png (TD-25).

---

## ⚠️ OPEN ISSUES — READ BEFORE WRITING ANY CODE

1. **.gitignore security debt (CRITICAL — do first).** `.env.local` NOT in `.gitignore`. Single dedicated commit (`chore/gitignore-env-local`); add `.env.local`, `.env*.local`.
2. **`API_BASE_URL` must be set on Render API** (public backend URL). Weekly/monthly letter emails are suppressed by design until it is. See `DEPLOY_NOTES.md`.
3. **PR-D2 production smoke test PENDING** — blocked by OTP delivery to ote.gr; use Gmail.
4. **OTP delivery failure for ote.gr** — Render logs investigation pending. Upstash `otp_request:{email}` 5/hour; workaround `+alias`.
5. **Render env var protection** — `render.yaml` needs `sync: false` on all secrets.

---

## Changelog v19 → v20 (PR history)

| PR | Description | Status |
|---|---|---|
| #337 4c4221c9 | feat(insight): insight-seeded reflection in the mirror reader | ✅ merged |
| #336 f30d901f | fix(mirror): never surface insight mirrors as the weekly "latest" | ✅ merged |
| #335 046d840a | feat(insight): insight-seeded mirror — `POST /insights/{id}/reflect` (migration 031, `kind="insight"`) | ✅ merged |
| #334 865b7503 | feat(insight): three-action card — Reflect / Doubt this → `/app/counterview` stub / Discard this | ✅ merged |
| #333 2018ef06 | feat(insight): provenance line "Noticed across N of your conversations" (migration 030) | ✅ merged |
| #332 69397eec | feat(insight): brand-seal ornament on Today + cleaner primary CTA | ✅ merged |
| #331 9a6a97fd | feat(share): branded season card for monthly letter shares | ✅ merged |
| #330 f1221f2b | feat(letters): premium season-finale reader (`SeasonFinaleView`) for monthly letters | ✅ merged |
| #329 5635acba | feat(letters): expose `kind` on the weekly-letter API | ✅ merged |
| #328 6f309546 | feat(monthly-letter): monthly season letter reusing the weekly engine (migration 029) | ✅ merged |
| #327 54ed0fac | feat(today): surface insight spine as a passive Today card; rename Dismiss | ✅ merged |
| #326 c56be764 | docs: add `DEPLOY_NOTES` with `API_BASE_URL` requirement for weekly email | ✅ merged |
| #325 fce5f967 | feat(weekly-letter): synthesize from insight spine + deliver by email (migration 028; TD-33) | ✅ merged |
| #324 bb684f3d | feat(insight): shift detection — classify pattern vs shift + branch CTA | ✅ merged |
| #323 1ec7cda0 | feat(insight): recurrence detector + quietly glowing in-chat chip | ✅ merged |
| #322 bd0b577d | fix(guide): responsive mind thumbnails + press effect + taller hero | ✅ merged |
| #321 209b797b | fix(share): gate Send on prepared image to keep iOS share synchronous | ✅ merged |
| #320 d1e2a4c7 | feat(guide): make minds tappable to persona detail + reframe hero | ✅ merged |
| #319 7c2df8aa | feat(letters): convert Sunday-letter links to buttons | ✅ merged |
| #318 4ac63440 | feat(guide): refresh Wise Room copy, rename ritual, sync minds to 11 | ✅ merged |
| #317 a7069a48 | docs: v19 (#315 WebP + #316 Orwell/Musashi) | ✅ merged |

Earlier PR history (v16 → v19): see `HANDOFF_BRIEF_v19.md §"Changelog"` + `§6`.

---

## 1–14.

Investigation Protocol (§1 — `CLAUDE.md`, P-01..P-07 + persona/migration conventions), current architecture (§2), test infra (§3), known limitations (§4), next-session entry point (§5), PR history (§6 — above), env config (§7 — **`API_BASE_URL` now operationally load-bearing for weekly email**), key file paths (§8 — see `PROJECT_STATE_v20.md §17`), decision history (§9), §5.7 framework (§10), migration plan (§11 — alembic head `031_mirrors_insight_id`), deployment readiness (§12 — **Rituals email delivery: weekly letter now wired; Letter-to-Future-Self still open**), session lessons (§13), closing note (§14) — **unchanged from v19 except as noted**. See `HANDOFF_BRIEF_v19.md`.

### 13. Session lessons (v20 additions)

- **13.28 — The detector is wired into the memory task, not a standalone insight task.** `detect_recurrence` runs inside `extract_memory_task` after extraction commits (same session, expire_on_commit=False so embeddings stay readable). Don't confuse it with the dormant `generate_insight_task` (TD-05) — that one is unrelated and still unwired.
- **13.29 — Read `window.location` in the effect, never in a `useState` initializer.** The insight-mirror reader sets `isInsight` via `setIsInsight(!!insightId)` inside the load effect (client-only) — a `useState(() => …window…)` initializer would diverge between SSR (false) and hydration. Suspense-safe, no `useSearchParams`.
- **13.30 — A non-generated mirror is a real row, not null.** `generate_insight_mirror` returns a `Mirror` with `status` `empty`/`suppressed` and null payload; the reader must branch on `status !== 'generated'` (not `!mirror`) and show the neutral fallback. `getLatestMirror` only ever returns generated-or-null, so the weekly path never hits that branch.
- **13.31 — `API_BASE_URL` is a silent-degradation trap.** The weekly email worker refuses to send on localhost `API_BASE_URL` (to avoid mailing broken unsubscribe links). A fresh deploy that forgets it sends zero emails with no error. Codified in `DEPLOY_NOTES.md` (#326).

---

**End of HANDOFF_BRIEF v20.** Authoritative as of 2026-06-21 (Insight engine · Insight→Mirror loop · weekly email · season finale session). Supersedes `HANDOFF_BRIEF_v19.md` (preserved as historical reference). Where this file conflicts with v19, v20 wins.
