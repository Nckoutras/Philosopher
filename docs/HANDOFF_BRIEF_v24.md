# HANDOFF BRIEF v24 — Philosopher / The Wise Room

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-07-19
**Prior version:** `docs/HANDOFF_BRIEF_v23.md` (2026-07-12)
**Generated:** 2026-07-19 (v24 rotation)

**Block trigger for v24 rotation:** 28 PRs (#493–#520) landed since the v23 doc (which stopped at PR #491). Four arcs dominate — a **Memory arc** (user-authored text distilled into confidence-1.0 memories across four ritual surfaces, #510/#511/#512), a **Reflections feed schema fix** (a systemic 500 closed, #513), an **Explore hub copy rewrite + portrait section** (#514), and an **Efficiency trip** (six cost PRs: anthropic GA bump #515, prompt caching #516, free counterview cap #517, ritual_id validation #518, embed dedup #519, letter-suppression logging #520). Alongside them: **deep-mode free metering + chip UX** (#497/#498/#503/#504), **ritual/insight door chips** (#501/#502/#505/#506/#507), **Council edited-matter deliberation** (#500/#508), and an **auth/polish** batch (#493–#496/#499). Migration head moved 049 → **051**. This rotation also **updates CORR-02** (cache-split sentinel now in the template) and logs **CORR-03** (the Reflections union bug).

> **⚠️ PROVENANCE — read before trusting the summary below.**
> - **#493–#520 — session-reviewed (2026-07-12→2026-07-19):** every PR reviewed with full diffs in founder+Claude sessions. Highest confidence.
> - **Re-verified against merged code at `faa18600` this rotation** — migration chain, `anthropic==0.99.0` pin, the `system_base.jinja2` cache-sentinel line, the `ReflectionFeedItem` union, the distill helper/task, the two rate-limit constants.
> - **#492 — the v23 doc-rotation PR itself** (docs only).

**v24 summary (2026-07-19):**
- **Memory arc ✅ (#510/#511/#512; helper + task).** `distill_to_memory(text)` (Haiku, `max_tokens=160`, `MIN_DISTILL_WORDS=6` pre-filter → no LLM call on trivial text) turns a person's own words into one `"User …"` statement; `distill_user_text_to_memory_task` **safety-gates in the task** (`check_input` first) then stores `entry_type="stated"`, `confidence=1.0` (auto-exempt from the stale-cron, which prunes `<0.6`). Wired to **Council edited matter** (#510), **Future-Self note** + **Mirror ring-true note** (#511), **Counterview rebuttal** (#512, rollback-safe count guard). Feeds chat recall / letters / insights with no new "everywhere" wiring.
- **Reflections feed fix ✅ (#513) — CORR-03.** `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview` added to the `ReflectionFeedItem` union. The feed **500'd** for any user with a saved corpus quote or a future-self review — the service+frontend had shipped the item kinds (v23) without the schema member. Regression test now guards (`tests/routers/test_reflections_feed.py`).
- **Explore copy rewrite + portrait ✅ (#514).** Hub copy corrected to the real architecture — **memories vs noticings** are two stores (`memory_entries` vs `insights`), **saved quotes don't feed the room**, **rituals mostly write not read**, the **Sunday Letter arrives on its own** — plus a new plain **"The portrait"** section. Driven by an interconnection-map audit that found `memory_entries` and `insights` are separate, and **letters read `insights`, not `memories`**.
- **Efficiency trip ✅ (#515–#520).** anthropic **0.34.2 → 0.99.0** (#515); **prompt caching** (#516) — `{{ cache_sentinel }}` in `system_base.jinja2` after VOICE CALIBRATION (**CORR-02**), `split_system_for_cache` on chat's 4 paths + `cache_whole_system` on Council members (synthesis/one-shots excluded), `cache_write`/`cache_read` logged, FREE/Haiku below the cache minimum (PRO-only benefit, accepted); **free counterview cap** `FREE_DAILY_COUNTERVIEW_LIMIT=2` + 429 wall (#517); **ritual_id validation** at conversation creation, closing a free rate-limit bypass (#518, FK still deferred); **embed dedup** (#519, one embed/turn across 3 chat paths); **letter-suppression log** warning→error, guard NOT moved (#520).
- **Deep mode ✅ (#497/#498/#503/#504).** Free daily metering `FREE_DAILY_DEEP_MODE_LIMIT=5` global (migration 050 `daily_usage.deep_mode_count`), toggle ungated (metered not walled), moved to the chip row, go-deeper chip removed; Pro toggle wired on the persona-first path + filled-bronze ON state.
- **Ritual doors ✅ (#501/#502/#505/#506/#507).** Named one-tap ritual door chips + global cross-conversation door surfacing in chat; Sunday Letter suggests a ritual (in-voice proposal on payload keys) rendered as a door card that routes in; aspiration insight → Future Self door chip.
- **Council ✅ (#500/#508).** Display-summary prefill for chat-sourced councils; deliberate the user's **edited** matter + persist `matter_edited` (migration 051). The edited matter feeds the Memory arc distill (#510).
- **Auth + polish ✅ (#493/#494/#495/#496/#499).** Sign-out clears `ph_token` cookie + localStorage; 401 self-heal + shared `signOut()`; polish batch 1; OTP email header; stronger insight star + larger today-card mark.

**v23 summary (2026-07-12):** Quotes / Wise Room corpus, Future-Self prediction loop, Counterview title, insight seen-state, persona-voice pass; migrations 043–049. Full detail in `HANDOFF_BRIEF_v23.md`.

> **v24 conflict resolution rule:** Where v24 conflicts with v23 or earlier, v24 wins. **Production reality always wins over docs.**

---

## ✅ CORRECTIONS this rotation

1. **CORR-02 (UPDATED) — `system_base.jinja2` now carries the cache-split sentinel.** v23 recorded the block order without it. v24: a `{{ cache_sentinel }}` slot sits **between VOICE CALIBRATION and PHENOMENOLOGY BRIDGE** (verified `system_base.jinja2:112`, #516). It is the cache split point — prefix (intro→…→VOICE CALIBRATION) cached, suffix (PHENOMENOLOGY BRIDGE→profile→memories→passages→HARD RULES) volatile. **Any template-insertion instruction must be written against the live file** (Rule 3 / lesson 13.42).
2. **CORR-03 (NEW) — the Reflections feed schema union was incomplete; the feed 500'd.** `SavedQuoteCard` (v23 #475/#476) and the Future-Self review (v23 #450) shipped in the service + frontend **without** the matching `ReflectionFeedItem` union member, so response validation 500'd for any affected user. #513 added `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview` + a regression test. **Lesson: a feed's new item kind ships its schema union member in the SAME PR.**

---

## ⚠️ OPEN ISSUES — READ BEFORE WRITING ANY CODE

1. **.gitignore security debt (CRITICAL — do first).** `.env.local` NOT in `.gitignore`. Single dedicated commit; add `.env.local`, `.env*.local`.
2. **Migration naming (C-04).** Revision id ≤ 32 chars + filename == revision id. 050–051 comply (verified this rotation).
3. **`API_BASE_URL` must be set on Render API** — else weekly/season **and future-self** letter emails are suppressed by design. **v24: suppression is now logged at ERROR (#520)** with an actionable message — watch for it in prod logs as the misconfiguration signal.
4. **Cache-read verification (NEW).** Confirm `cache_read > 0` in prod `llm_usage` logs before trusting the caching cost savings (#516). Until then the savings are unproven.
5. **ritual_id has no FK (P4, NEW).** #518 validates it (orphan check) but the FK is deferred — add before public launch.
6. **PR3a memory bugs — still verify.** #435 likely addresses the symptoms; confirm on smoke test.
7. **Carried:** TD-38 `rituals.ts` future-self copy / TD-39 `insights.source_count` split / TD-41 quote-corpus provenance / TD-42 Greek-CJK share-card font / dual tier-resolution debt.

---

## Top of mind / Next (2026-07-19)

**Priority order:**

0. **Smoke-test the new surfaces (P-03 cadence):**
   - **Memory arc:** editing a Council matter / writing a Future-Self note / a Mirror ring-true note / generating a Counterview rebuttal each lands a `confidence=1.0`, `entry_type="stated"` memory (verify in `memory_entries`); trivial (<6-word) text stores nothing; a safety-suppressed input stores nothing.
   - **Reflections feed:** a user with a saved quote AND a future-self review loads the feed without a 500 (the #513 fix).
   - **Explore:** the hub copy reads memories-vs-noticings correctly; "The portrait" section renders.
   - **Efficiency:** a Pro chat turn logs `cache_write` then `cache_read` on the next turn; a free user hits the counterview cap at the 3rd/day (429 + upgrade wall) and the deep-mode cap at the 6th/day; `ritual_id` on a bogus/inaccessible ritual is rejected at conversation creation.
   - **Deep mode:** free user sees the 5/day metered quota UX on the chip row; Pro is unlimited; ON reads as filled bronze.
   - **Ritual doors:** a chat surfaces a named ritual door chip; the Sunday Letter shows a ritual door card that routes into the ritual; an aspiration signal surfaces a Future Self chip.
   - **Auth:** sign-out clears cookie + localStorage; a 401 self-heals.
1. **Cache-read verification (#516)** — the underwriting check on the cost model.
2. **PR3a memory bugs — verify #435 closed them.**
3. **Dimitris repetition retest (Freud, deep mode, dream scenario) — STILL NEVER RUN.** Carried from v23 §2.6. Does the ADVANCEMENT block (#491) stop the repetition? If not, open the conditional retrieval-dedup item (TD-40).
4. **Empathy mini-eval (6 personas, heavy input)** — carried from v23; confirm the emotional-acknowledgment tiers land in-character.
5. **UAT protocol v2 is READY — tester pending.** Run it to produce the willingness-to-pay data the pricing decision waits on.
6. **Cold beta with 3–5 fresh users** — once memory bugs confirmed.
7. **Live Stripe wiring (TD-28) — 🔴 (P0 before any real payment)** — and the **pricing decision** (€11.99/mo / €99.99/yr recommended, founder sign-off pending UAT WTP).
8. **OPS-001 — nkoutr@ote.gr current_period_end re-sync.**

### Still-pending from prior sessions

- `.gitignore` security debt — fix before any code PR.
- Author smoke-test voice changes (6 personas) — incl. the v23 emotional-acknowledgment tier + ADVANCEMENT + raised deep-mode ceilings.
- OTP-01 (ote.gr delivery failure) — investigate Render logs.

---

## Changelog v23 → v24 (PR history)

> Full per-PR table (SHA + description) in `PROJECT_STATE_v24.md §"Changelog v23 → v24"`. Range: **#493–#520** (#492 was the v23 doc PR). Highlights:

| PR | SHA | Description |
|---|---|---|
| #520 | faa18600 | fix(letters): loud error on suppressed letter email (guard not moved) |
| #519 | 98a4e641 | perf(chat): embed user text once per turn (recall + retrieval) |
| #518 | 96c39368 | fix(conversations): validate ritual_id at creation (closed free-limit bypass) |
| #517 | 67859ba7 | feat(counterview): free daily cap (2/day) + 429 upgrade wall |
| #516 | 36bb52f2 | feat(llm): prompt caching — chat 4 paths + Council members |
| #515 | 3cf6a1f2 | chore(deps): anthropic 0.34.2 → 0.99.0 (GA caching prerequisite) |
| #514 | a5cedee4 | feat(explore): rewrite hub copy (memories vs noticings) + portrait section |
| #513 | a21e75bb | feat(reflections): add quote + future-self-review to the feed union (fixes 500) |
| #512 | f3e9b13b | feat(memory): distill counterview rebuttal → confidence-1 memory |
| #511 | 8b363735 | feat(memory): distill future-self note + mirror ring-true → confidence-1 memory |
| #510 | 794bf8ca | feat(memory): distill edited Council matter → confidence-1 memory |
| #509 | 0a488c85 | feat(chat): bounded insight recheck after a reply |
| #508 | 3dcb2394 | feat(council): deliberate the edited matter + persist flag (051) |
| #507 | 75ace2ac | feat(insights): aspiration signal → Future Self door chip |
| #506 | ed9744f9 | feat(weekly-letter): ritual door card + route into the ritual |
| #505 | 0e7fb00c | feat(weekly-letter): suggest a ritual + in-voice proposal |
| #504 | 469bfceb | feat(deep-mode): chip-row toggle + free quota UX, remove go-deeper chip |
| #503 | 213b6b2c | feat(deep-mode): free daily metering (5/day global) + ungate (050) |
| #502 | 6b42076b | feat(chat): global cross-conversation door chip surfacing |
| #501 | 4d00fd1f | feat(chat): named one-tap ritual door chips |
| #500 | d7735e47 | feat(council): display-summary prefill for chat-sourced councils |
| #499 | 3f13dd91 | polish(insights): stronger "something new" star + larger today-card mark |
| #498 | ca59d10a | fix(chat): deep-mode ON reads as filled bronze |
| #497 | 66f0263c | fix(chat): wire Pro deep-mode toggle on persona-first path |
| #496 | e43594b3 | feat(auth): OTP email header |
| #495 | de38b0fc | feat: polish batch 1 |
| #494 | 15e10051 | fix(auth): self-heal on 401 + shared signOut() helper |
| #493 | 2969fd67 | fix(auth): clear ph_token cookie + localStorage on sign out |

Earlier PR history (v22 → v23): see `HANDOFF_BRIEF_v23.md §"Changelog"`.

---

## Earlier session deltas (v16 → v23)

Carried forward by reference. See `HANDOFF_BRIEF_v23.md` (v23 #449–#491) and `HANDOFF_BRIEF_v22.md` (v22 #376–#447).

---

## 1–14.

Investigation Protocol (§1 — `CLAUDE.md`, P-01..P-07 + C-01..C-04), current architecture (§2 — **+ prompt caching via `prompt_builder.split_system_for_cache`/`cache_whole_system`; `anthropic==0.99.0`**), test infra (§3 — **+ `tests/routers/test_reflections_feed.py`, `tests/services/test_counterview_limit.py`, embed-dedup tests in `tests/services/test_conversation_service.py`**), known limitations (§4 — **+ cache-read unverified, ritual_id no FK, dual tier-resolution; TD-37..42 still open**), next-session entry point (§5 — above), env config (§7 — `API_BASE_URL` load-bearing, now ERROR-logged on suppression), key file paths (§8 — see `PROJECT_STATE_v24.md §Part A`), decision history (§9 — **+ pricing recommendation €11.99/€99.99 pending UAT**), migration plan (§11 — alembic head **`051_council_matter_edited`**), deployment readiness (§12 — Memory arc live; caching live but cache-read unverified), session lessons (§13 — below), closing note (§14) — **unchanged from v23 except as noted.** See `HANDOFF_BRIEF_v23.md`.

### 13. Session lessons (v24 additions)

- **13.46 — A feed's new item kind and its schema union member ship in the SAME PR.** The Reflections 500 (CORR-03 / #513) happened because `SavedQuoteCard` and the Future-Self review reached the *service* and *frontend* while the `ReflectionFeedItem` Pydantic union stayed stale — response validation 500'd for exactly the users the feature was for. A discriminated/typed union is not optional plumbing; adding an emitter without the union member is a latent 500. Guard added as a regression test.
- **13.47 — Distill-to-memory is safety-gated IN the task, not upstream.** `distill_user_text_to_memory_task` re-runs `safety_service.check_input` FIRST even when the caller already checked (Council matter is checked upstream), because the task is the reusable choke point and a suppressed input must never become a `confidence=1.0` memory. The double-check is accepted and intended — the reusable path owns its own safety.
- **13.48 — Cost work is verified by prod logs, not by merging the optimization.** The Efficiency trip (#515–#520) is only *believed* to save until `cache_read > 0` shows in `llm_usage`. Prompt caching in particular has a silent failure mode (cache writes with no reads = pure overhead). The cost model's savings line stays PENDING until the log confirms hits. Ship the optimization, then read the meter.
- **13.49 — Name the guard you did NOT move.** #520 elevated the letter-suppression log rather than moving the guard before generation, because the generated letter has in-app value (readable at `/app/letters/{id}`) and is never re-sent on a later run. The "obvious" fix (skip generation when suppressed) would have destroyed a real artifact. Investigate what a suppressed/aborted path leaves behind before optimizing it away.

---

**End of HANDOFF_BRIEF v24.** Authoritative as of 2026-07-19 (Memory arc · Reflections feed fix · Explore copy · Efficiency trip · deep-mode metering · ritual doors · Council edited matter · corrections). Supersedes `HANDOFF_BRIEF_v23.md` (preserved as historical reference). Where this file conflicts with v23, v24 wins.
