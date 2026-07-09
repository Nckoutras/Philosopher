# HANDOFF BRIEF v22 — Philosopher / The Wise Room

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-07-09
**Prior version:** `docs/HANDOFF_BRIEF_v21.md` (2026-06-26)
**Generated:** 2026-07-09 (v22 rotation)

**Block trigger for v22 rotation:** A large feature arc landed since the v21 doc (which stopped at PR #374). The **Self-Portrait** feature was built end-to-end across ~38 PRs (#387–#427, #437, #447), plus **Counterview user-rebuttal turns** (#376/#377) + **still-stands** (#443), the **Explore guides** build-out (#382, #428–#434, #446), **Council decision-architecture** (#386/#444), **dilemma/belief insight doorways** + Home room-noticed (#438–#440), a **Home image-tile** redesign (#378–#393), and letters/YvY continuity beats. Migration head moved 037 → 042. This rotation also **corrects** two doc-vs-reality errors (see PROVENANCE + Corrections).

> **⚠️ PROVENANCE — read this before trusting Part A / the summary below.** #375 is the v21 doc PR itself (it documented through #374). **None of #376–#447 was reviewed in a v21→v22 working session** — the entire delta was built outside these sessions (a prior/founder session series) and its v22 documentation was **reconstructed by reading the merged code at `aa3ecafd`**, not from session review. Treat every v22 description as code-derived, not session-verified — re-read the source before building on it.

**v22 summary (2026-07-09):**
- **Self-Portrait ✅ LIVE (#387–#427, #437, #447)** — a Pro-gated self-knowledge instrument. Quiz: `data/question_bank.json` (360 questions / 12 categories), interleaved round-robin, free tier sees `FREE_QUESTION_LIMIT=15`. Answers → `user_preferences.profile["answers"]` (reuses 037 blob). Portrait: `GET /preferences/self-portrait/portrait` is a **breadth gate** — `forming` (own-answer observation lines) → `ready` (cached **Sonnet summary** + **persona best-fit**, `portrait_cache` JSONB migration 039, regen at `PORTRAIT_REGEN_DELTA=8`, best-effort/always-200). Viz: `PortraitRadar` (top-5 pentagon + compass rose) and `PortraitMap` (Shape/Map toggle, static hand-drawn territories, dominant needle). Client-canvas share card (`portraitShareCard.ts`, ungated). Best-fit → chat with prefilled first sentence. New **Self Portrait** tab (Easel icon) — **replaced Library in the bar** (Library still reachable). Services `self_portrait.py` / `_summary.py` / `_prompts.py`.
- **Counterview rebuttal turns ✅ (#376/#377)** — `POST /counterview/{id}/respond`; `counterview_turns` table (migration 038, own axis — `counterview_responses.round` untouched); bounded `MAX_REBUTTALS=3` generated turns (409 on cap); current speaker replies in one ≤18-word line; suppressed/empty persists a status turn and still 200s. Returns `turns[]` + `rebuttals_remaining`. **+ "What still stands" closing line** (#443, `counterviews.still_stands` migration 041, same LLM call as verdicts).
- **Explore guides ✅ (#382, #428–#434, #446)** — `/app/explore/conversations` (+Council/Deep-mode blocks), `/app/explore/reflections`, `/app/explore/memory` ("The room remembers"); Explore index rewrite + pushable heroes + text-first.
- **Council decision architecture ✅ (#386/#444)** — essence brief distilled from chat before deliberation; `council_sessions.synthesis_structured` JSONB (migration 042): real_question / tension / verdict / next_move. Flat `synthesis` TEXT retained for feed + share; old sessions fall back to it.
- **Insight doorways ✅ (#438–#440)** — dilemma/belief signals detected during memory extraction → chat doorway chips (route to Council/Counterview) + Home "The room noticed" card.
- **Home image tiles ✅ (#378, #379, #384, #393)** — the v21 typographic 2×2 grid → image-card tiles + new Discuss route; priority images + LQIP blur.
- **Letters / YvY beats ✅** — Sunday next-reading line + UTC fix (#380), practical takeaway + continuity (#398), "something new" star for unread letters (#399), "What went unspoken" avoidance line (#445); YvY sentence-owed save → Reflections (#442, `self_comparison_saves` 040).
- **Store fix ✅ (#383)** — `lib/store.ts` derives `plan` as real state (Zustand persist-freeze cause).

**v21 summary (2026-06-26):** Counterview ritual backfill, chat sticky-guest / adaptive length / go-deeper depth + Pro deep mode, Chat → Council, letter write-back, onboarding profile pills, Home tiles + Explore tab; migrations 032–037. Full detail in `HANDOFF_BRIEF_v21.md`.

> **v22 conflict resolution rule:** Where v22 conflicts with v21 or earlier, v22 wins. **Production reality always wins over docs.**

---

## ✅ CORRECTIONS this rotation (docs were wrong — now fixed)

1. **Letter to Future Self delivery is LIVE (v21 said it wasn't).** v21 listed "ARQ delivery not wired / still open." **FALSE.** Delivery ships via **APScheduler**: `send_pending_future_self_emails` at `apps/api/workers/cron.py:133–204` (`AsyncIOScheduler` + `IntervalTrigger(minutes=5)`) sends pending `ScheduledEmail` rows via `send_email`. The open backlog item is **removed**, not carried. (Depends on `API_BASE_URL`/asset base being set — same as weekly/season email.)
2. **`insights.source_count` is populated by design — not "never populated."** `memory_service.py:363,421` (`detect_recurrence`) sets it to the distinct-prior-conversation count; the newer dilemma/belief **signal** path (`memory_service.py:181–187`) sets `None` deliberately ("not a cross-conversation recurrence"). The provenance line renders only when `source_count >= 2`. Logged as **TD-39 (confirm the split is intended)**, not a bug.

---

## ⚠️ OPEN ISSUES — READ BEFORE WRITING ANY CODE

1. **.gitignore security debt (CRITICAL — do first).** `.env.local` NOT in `.gitignore`. Single dedicated commit; add `.env.local`, `.env*.local`.
2. **Migration naming (C-04).** Revision id ≤ 32 chars + filename == revision id. 038–042 all comply.
3. **`API_BASE_URL` must be set on Render API** — else weekly/season **and future-self** letter emails are suppressed by design. `DEPLOY_NOTES.md`.
4. **PR3a memory bugs — verify.** #435 (`conv/[id]` resilience: opening fallback, graceful 404, Continuing-card sync) likely addresses the symptoms; **confirm on smoke test** before treating them as closed.
5. **`rituals.ts:42` future-self copy (TD-38, founder call).** "It isn't sent anywhere" on the future-self **declaration** ritual vs the live scheduled-email feature that shares the name — reword or leave.
6. **OTP delivery failure for ote.gr** — Render logs investigation pending.
7. **Render env var protection** — `render.yaml` needs `sync: false` on all secrets.

---

## Top of mind / Next (2026-07-09)

**Priority order:**

0. **Smoke-test the new surfaces (P-03 cadence):**
   - **Self-Portrait:** free user sees 15 questions + a locked count; Pro sees all 360; answers persist; the portrait starts `forming` (own-answer "Room notices") and flips to `ready` once breadth is met (Sonnet summary + best-fit personas); radar ↔ map toggle renders the same `theme_scores`; the share card exports; "take best-fit mind to chat" opens a prefilled conversation; the **Self Portrait** tab shows (Library still reachable elsewhere).
   - **Counterview rebuttal:** after a verdict, rebut the current speaker → one ≤18-word reply; stops at 3 rebuttals (cap message); a "still stands" closing line appears (or is absent) — never against the person.
   - **Explore guides:** conversations / reflections / memory guides render; heroes push; Council + Deep-mode blocks present.
   - **Council:** synthesis shows real_question / tension / verdict / next_move; old sessions still render via the flat synthesis; feed + share card unaffected.
   - **Insight doorways:** a dilemma/belief in chat surfaces a doorway chip + the Home "room noticed" card; chips route to Council/Counterview.
   - **Home:** image tiles navigate; Discuss route works; no lazy pop-in (priority + LQIP).
   - **Future-Self delivery:** a scheduled letter with `scheduled_for <= now()` sends within ~5 min (confirm `API_BASE_URL` set on Render).
1. **PR3a memory bugs — verify #435 closed them.**
2. **Cold beta with 3–5 fresh users** — once confirmed.
3. **Live Stripe wiring (TD-28) — 🔴 (P0 before any real payment).**
4. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**
5. **TD-37 — wire or retire the dormant brevity post-check** (post-first-paying-user).
6. **App-icon mark (TD-29).**
7. **Fast-follows (post-first-paying-user):** Self-Portrait tuning (breadth gate / regen delta / free-question count / best-fit weights); `rituals.ts:42` copy (TD-38); source_count split confirmation (TD-39); Counterview voice/threshold + multi-round v2; `/app/profile` Explore entry point; Council per-verdict saves + share redesign.

### Still-pending from prior sessions

- `.gitignore` security debt — fix before any code PR.
- Author smoke-test voice changes (6 personas).
- OTP-01 (ote.gr delivery failure) — investigate Render logs.

---

## Changelog v21 → v22 (PR history)

> Full per-PR table (SHA + description) in `PROJECT_STATE_v22.md §"Changelog v21 → v22"`. Range: **#376–#447** (#375 was the v21 doc PR). Highlights:

| PR | SHA | Description |
|---|---|---|
| #447 | aa3ecafd | feat(self-portrait): re-art map + retarget label anchors |
| #444 | 2eaa2914 | feat(council): decision architecture synthesis (migration 042) |
| #443 | e53bf770 | feat(counterview): "What still stands" closing line (migration 041) |
| #442 | 78f46e63 | feat(yvy): save "sentence you owe yourself" → Reflections (migration 040) |
| #440 | 556607d7 | feat(home): The room noticed card |
| #438 | b06fc677 | feat(insights): detect dilemma/belief signals via memory extraction |
| #434 | dd805368 | feat(explore): The room remembers explainer |
| #431 | ac73eb62 | feat(explore): reflections & portraits guide |
| #430 | e0be7a68 | feat(explore): conversations guide — add Council + Deep mode |
| #405 | 2622e264 | feat(self-portrait): Phase B3 — shareable portrait card |
| #404 | 759cf1a9 | feat(self-portrait): Phase B2 — map view + Shape/Map toggle |
| #396 | 0028a7f2 | feat(self-portrait): payoff 5b — Sonnet summary + persona best-fit |
| #395 | 0497853a | feat(self-portrait): payoff 5a — breadth gate + cache column (migration 039) |
| #390 | 1fd2ef2f | content(self-portrait): expand question bank to 360 (12 categories) |
| #388 | c4563db6 | feat(self-portrait): quiz UI + GET endpoint + Pro gating; Library→Portrait tab |
| #387 | 2ed07ad4 | feat(self-portrait): backend pipe — persist answers, seed memory, feed letters |
| #386 | d73326ca | feat(council): distil chat into an essence brief |
| #378 | 69ccd580 | feat(home): image-card 2×2 tiles + Discuss route |
| #377 | e34c6be6 | feat(counterview): rebut the current speaker in place |
| #376 | f8209f1a | feat(counterview): bounded user rebuttal — POST /respond (migration 038) |

Earlier PR history (v20 → v21): see `HANDOFF_BRIEF_v21.md §"Changelog"`.

---

## Earlier session deltas (v16 → v21)

Carried forward by reference. See `HANDOFF_BRIEF_v21.md` (v21 #339–#374) and `HANDOFF_BRIEF_v20.md` (v20 #317–#337).

---

## 1–14.

Investigation Protocol (§1 — `CLAUDE.md`, P-01..P-07 + C-01..C-04), current architecture (§2 — **+ APScheduler in-process cron for future-self email; client-side canvas for the portrait share card**), test infra (§3 — **+ `tests/services/test_counterview_rebuttal.py`**), known limitations (§4 — **+ TD-38 rituals.ts copy, TD-39 source_count split; TD-37 still open**), next-session entry point (§5), PR history (§6 — above), env config (§7 — `API_BASE_URL` load-bearing for weekly/season **and future-self** email), key file paths (§8 — see `PROJECT_STATE_v22.md §17`), decision history (§9), migration plan (§11 — alembic head **`042_council_synthesis_json`**), deployment readiness (§12 — Self-Portrait live; Counterview turns live; **future-self delivery LIVE via APScheduler**), session lessons (§13 — below), closing note (§14) — **unchanged from v21 except as noted.** See `HANDOFF_BRIEF_v21.md`.

### 13. Session lessons (v22 additions)

- **13.37 — Verify a "not wired" claim against the actual scheduler before carrying it forward.** v21 carried "Letter to Future Self — ARQ delivery not wired" for a full cycle; the delivery had in fact shipped on **APScheduler** (`workers/cron.py`), not ARQ. The claim was true about *ARQ* and false about *delivery*. Lesson (per `CLAUDE.md` Rule 3): a mechanism-specific negative ("X isn't wired via Y") is not a feature-level negative ("the feature doesn't work") — grep for the behaviour, not the named plumbing.
- **13.38 — Keep independent axes on independent keys.** `counterview_turns.sequence` (rebuttal order) is a **separate table** from `counterview_responses.round` (verdict/go-deeper depth, capped at 1). Bolting rebuttals onto `round` would have overloaded one column with two meanings; the new table left the verdict model untouched. Pattern for extending a feature with a genuinely new dimension.
- **13.39 — A derived cache belongs beside, not inside, the user-authored blob.** Self-Portrait **answers** live in `user_preferences.profile["answers"]` (user-authored), but the **derived** Sonnet summary + best-fit live in a separate `portrait_cache` JSONB (039). Keeping server-generated derivations out of the authored blob makes regeneration/invalidation safe and the authored data auditable.
- **13.40 — A payoff endpoint should never 500 on the LLM path.** `GET /self-portrait/portrait` is best-effort: a summary-generation failure falls back to a prior cache or the forming preview and still returns 200. A self-knowledge payoff that occasionally errors reads as broken; degrade to "forming," never to an error.
- **13.41 — Additive nullable columns stay the cold-beta default.** 038 (new table) / 039 / 041 / 042 (nullable columns) / 040 (new table) are all pure no-ops for existing rows — old counterviews/councils/preferences render exactly as before until the new path writes. Same shape as 034–037.

---

**End of HANDOFF_BRIEF v22.** Authoritative as of 2026-07-09 (Self-Portrait arc · Counterview rebuttal turns · Explore guides · Council decision architecture · insight doorways · Home image tiles · corrections). Supersedes `HANDOFF_BRIEF_v21.md` (preserved as historical reference). Where this file conflicts with v21, v22 wins.
