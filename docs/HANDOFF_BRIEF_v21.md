# HANDOFF BRIEF v21 — Philosopher / The Wise Room

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-06-26
**Prior version:** `docs/HANDOFF_BRIEF_v20.md` (2026-06-21)
**Generated:** 2026-06-26 (v21 rotation)

**Block trigger for v21 rotation:** Two feature arcs landed since the v20 doc (which stopped at PR #337). (1) The **Counterview ritual** was built end-to-end (#342–#362) — the last unbuilt ritual is now live — and was never documented; v21 backfills it. (2) This session shipped chat **sticky guest mind**, **adaptive response length**, **go-deeper depth + free limit + Pro sticky deep mode**, **Chat → Council**, **letter write-back**, **onboarding profile pills**, and the **Home tiles + Explore tab** restructure (#365–#374). Migration head moved 031 → 037, with a logged migration-id-length incident (#371).

> **⚠️ PROVENANCE — read this before trusting Part A.** #338 is the v20 doc PR itself (it documented through #337). The v21 **working sessions reviewed only #365–#374** (plus the #371 migration fix). The **#339–#364 range — most importantly the entire Counterview ritual (#342–#362), plus the insight/guide/splash polish (#339–#341, #355–#359) and the type bump (#363–#364) — was built outside these sessions** (a prior/founder session) and landed after the v20 doc was cut. It was **never reviewed in the v20→v21 working sessions**; its v21 documentation was **reconstructed by reading the merged code at `fed8d312`**, not from session review. Treat the Part A descriptions as code-derived, not session-verified — re-read the source before building on them.

**v21 summary (2026-06-26):**
- **Counterview ✅ LIVE (#342–#362)** — `services/counterview_service.py`: Musashi + Machiavelli each deliver one ≤10-word line against a belief (typed or insight-seeded), safety-gated both ends, status ∈ {generated,empty,suppressed}. Go-deeper (one ≤18-word round-1/persona, #346/#348). Save → Reflections feed `kind="counterview_verdict"` (migration 033, #349/#350). 4:5 Pillow share card `POST /share/counterview` (#351/#352). Recurrence from voluntary beliefs via `counterview_belief_task` (no migration, #361). Revisit list (#362). Migration 032 (`counterviews`+`counterview_responses`).
- **Sticky guest mind ✅ (#366)** — `conversations.active_persona_id` (034); responder = `coalesce(active_persona_id, persona_id)` at every read site incl. quota; `POST`/`DELETE /conversations/{id}/active-mind`; "Return to {origin}".
- **Adaptive response length ✅ (#367)** — `_length_directive_for_input` sizes reply to input (≤15w short / 16–49 unchanged / ≥50w long), within the persona band, capped at U; distress-gated, skipped on msg 1.
- **Go-deeper depth + limits ✅ (#368)** — `_deepen_directive` targets `reflective_reply_max_words`; escalation neutralized; free 3/day per HOME persona (`daily_usage.go_deeper_count`, keyed on `conv.persona_id`); Pro sticky `conversations.deep_mode` (Pro-gated endpoint + read site). Migration 035.
- **Chat → Council ✅ (#369)** — header Scale icon (all users = upsell); seeds last user msg (≤600) via sessionStorage; Pro → Council, free → upgrade; council `source` gains `'chat'` (own weekly bucket).
- **Letter write-back ✅ (#370)** — `weekly_letters.write_back_text`/`write_back_at` (036); `PATCH /weekly-letters/{id}/write-back` (Pro); window in weekly + `SeasonFinaleView`; fed forward as `<reader_wrote_back>` into the next letter. v1: no live reply, no insight-seeding.
- **Onboarding profile pills ✅ (#372)** — `user_preferences.profile` JSONB (037); `<what_we_know>` block in the prompt (not recall); seeded as `memory_entries` (`onboarding_profile`); instant `forming_reflection()`; `/app/profile` + `/app/onboarding/profile`; shared `profile_text.py`.
- **Home tiles + Explore ✅ (#373/#374)** — Today→"Home" (label only, URL stays `/app/today`); 2×2 tile grid + wide Sunday tile; new `/app/insights`; Rituals tab → Explore tab (guide re-parented into `(tabs)/explore`; `/app/guide` + old `/app/explore` redirect deleted; 4 callers → `/app/library?mode=browse`; `/app/rituals` route kept, delisted).
- Insight/guide/splash polish (#339–#341, #355–#359); type bump 15→17px (#364); `body{zoom:1.15}` removed (#363, closes TD-32).

**v20 summary (2026-06-21):** Insight engine, Insight → Mirror loop, weekly email (TD-33), monthly season finale; migrations 028–031. Full detail in `HANDOFF_BRIEF_v20.md`.

> **v21 conflict resolution rule:** Where v21 conflicts with v20 or earlier, v21 wins. **Production reality always wins over docs.**

---

## Status (delta from v20)

- **Counterview ✅ LIVE (2026-06-21→24)** — no remaining unbuilt rituals. Backend `counterview_service.py`; `routers/counterview.py`; insight-seeded via `POST /insights/{id}/counterview`; saves table 033; share card via `image_service.py`; recurrence via `counterview_belief_task`.
- **Chat depth + routing (2026-06-24→26)** — sticky guest mind (034), adaptive length, go-deeper depth + free limit + Pro deep mode (035), Chat → Council.
- **Letters / onboarding / home (2026-06-25→26)** — letter write-back (036), onboarding profile pills (037), Home tiles + minimal Insights list, Explore tab restructure.
- Earlier status (Blocks A/B/C, Stripe sandbox, paywall, Mirror/Council/YvY, Sunday Letter reader + email + season finale, Reflections feed, Insight engine, Orwell/Musashi) — unchanged; see `HANDOFF_BRIEF_v20.md`.

---

## ⚠️ OPEN ISSUES — READ BEFORE WRITING ANY CODE

1. **.gitignore security debt (CRITICAL — do first).** `.env.local` NOT in `.gitignore`. Single dedicated commit (`chore/gitignore-env-local`); add `.env.local`, `.env*.local`.
2. **Migration naming (NEW — C-04, post-#371).** Every migration's **revision id ≤ 32 chars** (fits `alembic_version.version_num VARCHAR(32)`) **and the filename MUST equal the revision id.** A 33-char id crashed the Render deploy this session; the DB rolled cleanly back to the prior head (transactional DDL). See `CLAUDE.md`.
3. **`API_BASE_URL` must be set on Render API** (public backend URL) or weekly/season letter emails are suppressed by design. See `DEPLOY_NOTES.md`.
4. **PR3a memory bugs still open** — fresh-chat missing opening message/thumbnail; home "Continuing" 404s. Highest cold-beta blocker.
5. **OTP delivery failure for ote.gr** — Render logs investigation pending. Upstash `otp_request:{email}` 5/hour; workaround `+alias`.
6. **Render env var protection** — `render.yaml` needs `sync: false` on all secrets.

---

## Top of mind / Next (2026-06-26)

**Priority order:**

0. **Smoke-test the new surfaces (P-03 cadence):**
   - **Counterview:** insight "Doubt this" → `/app/counterview?insightId=` generates two verdicts (Musashi/Machiavelli); typed belief from the input screen; go-deeper adds one sharper line per persona (capped at one); Save → appears in Reflections; Share renders the 4:5 card; revisit list shows past counterviews; safety-tripped belief → gentle empty/suppressed fallback.
   - **Sticky guest:** "Continue with {guest}" keeps the guest as responder across turns (header, thumbnail, quota all follow); "Return to {origin}" reverts; quota cannot be reset by switching minds.
   - **Adaptive length / deep mode:** a one-line question gets a short reply; a long message gets a fuller one (never over the persona ceiling); Pro deep-mode toggle makes replies deep and sticks; free go-deeper stops at 3/day per home persona; distress always shortens/grounds.
   - **Chat → Council:** Scale icon visible to all; free → `/app/upgrade`; Pro → Council pre-filled with the last message.
   - **Letter write-back:** Pro can write back on a Sunday/season letter; it persists and is editable; it shows up referenced in the next letter.
   - **Onboarding profile:** pills save; "Skip for now" works; the persona shows awareness on turn 1; `/app/profile` edits persist.
   - **Home/Explore:** Home tiles navigate correctly; `/app/insights` lists insights; Explore tab renders the guide; the 4 repointed callers land on `/app/library?mode=browse`; `/app/rituals` still resolves though delisted.

1. **PR3a memory bugs — 🔴 not started (highest priority).**
2. **Cold beta with 3–5 fresh users** — once memory bugs resolved.
3. **Live Stripe wiring (TD-28) — 🔴 (P0 before any real payment).**
4. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**
5. **TD-37 — wire or retire the dormant brevity post-check** (post-first-paying-user).
6. **App-icon mark (TD-29).**
7. **Fast-follows (post-first-paying-user):** Home tiles → custom images; `/app/profile` Explore entry point; letter-write-back fed-forward truncation; adaptive-length/go-deeper threshold tuning; Counterview voice/threshold tuning; YvY funnel analytics; Council per-verdict saves + share redesign; Letter-to-Future-Self ARQ delivery.

### Still-pending from prior sessions

- `.gitignore` security debt — fix before any code PR.
- Author smoke-test voice changes (6 personas).
- OTP-01 (ote.gr delivery failure) — investigate Render logs.
- compress mirror.png (TD-25).

---

## Changelog v20 → v21 (PR history)

| PR | SHA | Description | Status |
|---|---|---|---|
| #374 | fed8d312 | feat(explore): Rituals tab → Explore tab; re-parent guide; fix `/app/explore` collision | ✅ merged |
| #373 | 71a1cba7 | feat(home): Home tiles + minimal Insights list | ✅ merged |
| #372 | a5be7e5f | feat(onboarding): profile pills + guaranteed persona awareness + instant reflection (migration 037) | ✅ merged |
| #371 | 3df38646 | fix(migrations): shorten 035 revision id to fit `alembic_version(32)` | ✅ merged |
| #370 | b7d4f6b0 | feat(letters): write back to the persona from Sunday/season letters (migration 036) | ✅ merged |
| #369 | 2656e5c6 | feat(chat): take the conversation to the Council from chat | ✅ merged |
| #368 | 701469d2 | feat(chat): go-deeper depth + free daily limit + Pro sticky deep mode (migration 035) | ✅ merged |
| #367 | 162bbedc | feat(chat): adaptive response length from user input size | ✅ merged |
| #366 | c15c81d1 | feat(chat): sticky "continue with guest" mind + return to origin (migration 034) | ✅ merged |
| #365 | f875abea | fix(reflections): improve readability of conversation-sourced saved lines | ✅ merged |
| #364 | 46be06df | feat(ui): bump reading-surface type ~15% (chat, insights, verdicts, base) | ✅ merged |
| #363 | 2ea73637 | test: drop `body { zoom: 1.15 }` to isolate fixed-tabbar tap desync (iOS) — closes TD-32 | ✅ merged |
| #362 | bfbcc6ff | feat(counterview): revisit list of past counterviews on the input screen | ✅ merged |
| #361 | aa2e5f73 | feat(counterview): detect recurrence from voluntary beliefs (slice 1, no migration) | ✅ merged |
| #360 | 4c9793ba | feat(counterview): large portraits + single speaker-toggle verdict frame + start over | ✅ merged |
| #359 | 7b17a43a | fix(insight): unify the insight marker on a luminous Sparkle (was a diamond) | ✅ merged |
| #358 | c0677858 | fix(splash): load hero via `next/image` priority so it paints early | ✅ merged |
| #357 | 5d012b51 | feat(guide): tappable rituals → per-ritual explainer screens | ✅ merged |
| #356 | e8f4de6e | feat(insight): discoverability glow on Library tab + source conversation, clears on open | ✅ merged |
| #355 | aca87b1a | fix(polish): insight title, post-read letter copy, fainter conversation share hero | ✅ merged |
| #354 | f26a3e11 | fix(counterview): compact header + dominant portrait panels | ✅ merged |
| #353 | 52ef2a17 | fix(counterview): tighter verdicts — 10-word cut, no compound stitching | ✅ merged |
| #352 | 319d1186 | feat(counterview): Share button + counterview variant in SharePreviewModal | ✅ merged |
| #351 | 45269b46 | feat(counterview): 4:5 share card (Pillow) + `/share/counterview` endpoint | ✅ merged |
| #350 | 3fe02f4a | feat(counterview): Save button + reflections feed card (save/unsave wiring) | ✅ merged |
| #349 | e8be4447 | feat(counterview): saves table + save/unsave + reflections feed source (migration 033) | ✅ merged |
| #348 | 7b8c1cf5 | feat(counterview): wire go-deeper — stacked second cut per persona | ✅ merged |
| #347 | de9d1f98 | feat(counterview): framed visual rebuild of the result screen | ✅ merged |
| #346 | 46a20b73 | feat(counterview): go-deeper — one sharper round per persona, safety-gated | ✅ merged |
| #345 | 65488c1d | feat(counterview): voluntary entry — rituals tile + typed-belief input | ✅ merged |
| #344 | 687a0b2d | feat(counterview): line-level staged reveal on the result screen | ✅ merged |
| #343 | 3732929f | feat(counterview): insight-seeded counterview screen (replaces stub) | ✅ merged |
| #342 | e7d1a0cf | feat(counterview): backend core — 2-persona verdicts, safety-gated, anchored (migration 032) | ✅ merged |
| #341 | 7d92b76a | feat(insight): undo toast on discard (delayed dismiss, 5s window) | ✅ merged |
| #340 | 0f26ce29 | fix(insight): host insight mirror via weekly mirror host; hide weekly-only chrome on insight reflect | ✅ merged |
| #339 | 10b60edc | polish(insight): static bronze emphasis on Today seal | ✅ merged |

Earlier PR history (v19 → v20): see `HANDOFF_BRIEF_v20.md §"Changelog"`.

---

## Earlier session deltas (v16 → v20)

Carried forward by reference. See `HANDOFF_BRIEF_v20.md` (v20 #317–#337) and `HANDOFF_BRIEF_v19.md` (v19 #315–#316; v18 #277–#313).

---

## 1–14.

Investigation Protocol (§1 — `CLAUDE.md`, P-01..P-07 + persona/migration conventions **C-01..C-04**), current architecture (§2), test infra (§3), known limitations (§4 — **+ TD-37 dormant brevity post-check**), next-session entry point (§5), PR history (§6 — above), env config (§7 — `API_BASE_URL` operationally load-bearing for weekly/season email), key file paths (§8 — see `PROJECT_STATE_v21.md §17`), decision history (§9), migration plan (§11 — alembic head **`037_user_preferences_profile`**), deployment readiness (§12 — Counterview live; Letter-to-Future-Self ARQ delivery still open), session lessons (§13), closing note (§14) — **unchanged from v20 except as noted.** See `HANDOFF_BRIEF_v20.md`.

### 13. Session lessons (v21 additions)

- **13.32 — Migration revision ids are length-bounded.** `alembic_version.version_num` is `VARCHAR(32)`. A 33-char revision id (`035_deep_mode_and_go_deeper_count`) crashed the Render deploy at the version-write. Because Postgres DDL is transactional, the failed upgrade rolled back cleanly to the prior head (034) — **never half-applied** — so the fix was a pure rename (#371), no data repair. Rule C-04: revision id ≤ 32 chars **and** filename == revision id.
- **13.33 — Quota must key on the immutable home persona, not the resolved responder.** The free go-deeper limit counts on `conv.persona_id`, not `coalesce(active_persona_id, persona_id)` — otherwise switching to a guest mind would reset the daily bucket (a guest-switch exploit). Sticky-guest resolution (#366) and quota keying (#368) deliberately diverge here.
- **13.34 — Pro-gate sticky flags at BOTH the endpoint and the read site.** `conversations.deep_mode` is gated on write (403 for free) AND re-checked on read (`user_plan in (pro,premium)`), so a stale `true` left on a downgraded account is inert. Pattern for any Pro-sticky conversation state.
- **13.35 — Guaranteed persona awareness goes in the prompt, not recall.** The onboarding profile renders as a `<what_we_know>` block injected directly into the system prompt on turn 1 — RAG/recall is best-effort and would not reliably surface it. The same statements are *also* seeded as `memory_entries` so recall/YvY see them, but the prompt block is the guarantee.
- **13.36 — Additive, nullable columns are pure no-ops for existing rows.** 034/035/036/037 are all nullable / default-valued additive columns; existing conversations/letters/preferences behave exactly as before until the new path writes. This is the preferred shape for cold-beta schema changes (per CLAUDE.md future-proofing).

---

**End of HANDOFF_BRIEF v21.** Authoritative as of 2026-06-26 (Counterview ritual backfill · chat depth/sticky-guest/Council · letter write-back · onboarding profile · Home/Explore restructure). Supersedes `HANDOFF_BRIEF_v20.md` (preserved as historical reference). Where this file conflicts with v20, v21 wins.
</content>
