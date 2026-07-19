# PHILOSOPHER — Project State v24

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v24 = v23 baseline (2026-07-12, captured through PR #491 / `8a79ca3c`) + 2026-07-12→2026-07-19 delta (#493–#520).** Four arcs dominate: a **Memory arc** (user-authored text → confidence-1.0 memory across four ritual surfaces), a **Reflections feed schema fix** (a systemic 500 closed), an **Explore hub copy rewrite + portrait section**, and an **Efficiency trip** (six cost-optimization PRs: SDK GA bump, prompt caching, a free counterview cap, ritual_id validation, embed dedup, letter-suppression logging). Alongside them: **deep-mode free metering + chip-row UX**, **ritual/insight door chips**, **Council edited-matter deliberation**, and an **auth/polish** batch. Migrations **050–051**.
>
> **Migration head moved 049 → 051.**
>
> **v23 = v22 baseline + #449–#491:** the **Quotes system ("The Wise Room" authenticated-quote corpus)** end-to-end (~28 PRs), the **Future-Self prediction loop**, **Counterview share-title + collapsed history**, **insight seen-state**, **Self-Portrait polish**, and a **prompt/persona-voice** pass (EMOTIONAL WEIGHT + ADVANCEMENT blocks, ~1.65× deep-mode ceilings). Migrations 043–049. Full detail in `PROJECT_STATE_v23.md`.
>
> **Generated:** 2026-07-19 (v24 rotation) · **Last updated:** 2026-07-19 (Memory arc · Reflections feed fix · Explore copy · Efficiency trip · deep-mode metering · ritual doors · Council edited matter · corrections; current main `faa18600`)

> **v24 conflict resolution rule:** Where v24 conflicts with v23 or earlier, v24 wins. **Production reality always wins over docs.**

> **⚠️ PROVENANCE — read this before trusting Part A.**
> - **#493–#520 — session-reviewed (2026-07-12→2026-07-19 sessions).** Every PR in this delta was reviewed with full diffs in founder+Claude working sessions. Highest confidence.
> - **This rotation additionally re-verified every claim below against the merged code at `faa18600`** (migration chain, requirements pin, new endpoints/validations, new services/constants, the `system_base.jinja2` cache-sentinel placement, the Reflections schema union). Where a claim is quoted from code it is authoritative; where it forwards a founder decision (pricing) it is marked PENDING.
> - **#492 — the v23 doc-rotation PR itself** (docs only; no product surface).

> **⚠️ LIVE DATABASE: Supabase project `bvzeuwzqgnqcghvqghtb` (Oregon, us-west-2) is the only live database.** The old project `plecolxlzshkfvybszgs` (eu-west-1 / Ireland) is legacy / inactive; do not write to it. All Render services must point to Oregon. Unchanged from v23.

---

## Part A — v24 delta (#493–#520)

> Built between the v23 doc cut (#491/#492) and this rotation. All session-reviewed with full diffs; re-verified against merged code at `faa18600`.

### A1. Memory arc — user-authored text → confidence-1.0 memory (#510, #511, #512; + #509)

The most structurally significant arc. A generic helper turns a person's **own words** into one clean third-person memory statement and stores it as a **confidence-1.0** `MemoryEntry`, so it feeds everything memory already feeds (chat recall, letters, insights) — with no new "everywhere" wiring.

- **The helper (`services/memory_service.py`):** `distill_to_memory(text)` — pre-filters text shorter than `MIN_DISTILL_WORDS = 6` and returns `None` **without any LLM call** (trivial edits cost nothing past this check); otherwise one **Haiku** completion (`max_tokens=160`, `DISTILL_TO_MEMORY_PROMPT`) yields a single `"User …"` statement in the input's language, or `None` on empty / the `NONE` sentinel. Generic (no ritual-specific wording) so all surfaces reuse it.
- **The task (`workers/arq_worker.py:distill_user_text_to_memory_task`):** **safety-gated IN the task** — `safety_service.check_input(text, user_id)` runs FIRST; a suppressed input never becomes a memory. Then `distill_to_memory`, then one embed, then a `MemoryEntry(entry_type="stated", confidence=1.0, source_turn=0, is_active=True)`. `confidence=1.0` is **auto-protected from the stale-memory cron** (which only prunes `< 0.6`). Self-contained `try/except` — a failure never breaks anything upstream.
- **Four surfaces wired (all enqueue the one task):**
  - **Council edited matter** — `services/council_service.py:343` (#510). Pairs with the Council edited-matter deliberation (A7 / #508).
  - **Future-Self note** — `routers/scheduled_emails.py:94` (#511).
  - **Mirror ring-true note** — `routers/mirrors.py:108` (#511).
  - **Counterview rebuttal** — `services/counterview_service.py:633` (#512), behind a rollback-safe count guard so a generated rebuttal is distilled once.
- **Bounded insight recheck (#509):** `feat(chat): bounded insight recheck after a reply` — a bounded post-reply pass over the insight surface (paired with the memory arc's "user-stated matter" emphasis).

### A2. Reflections feed schema fix — a systemic 500 closed (#513)

`feat(reflections): add quote + future-self-review members to the feed schema union`. **`ReflectionFeedQuote` and `ReflectionFeedFutureSelfReview` were added to the `ReflectionFeedItem` union** (`schemas/__init__.py:874–889`). Before this, the unified Reflections feed **500'd for any user who had a saved corpus quote or a future-self review** — the feed *service* and the *frontend* had shipped the two item kinds (v23 `SavedQuoteCard`/#475/#476; Future-Self review/#450) **without the corresponding schema union member**, so response validation failed. A regression test now guards the union (`tests/routers/test_reflections_feed.py`). Recorded as **CORR-03** (§19) — a service+frontend-ahead-of-schema class of bug.

### A3. Explore hub copy rewrite + portrait section (#514)

`feat(explore): rewrite hub copy (memories vs noticings) + add portrait section`. The Explore hub copy was corrected to match how the two data stores actually behave, plus a new plain **"The portrait"** section.

- **Copy corrections:** the **memories-vs-noticings** distinction (two distinct stores — `memory_entries` the user's stated/distilled memories, vs `insights` the room's noticings); **saved quotes don't feed the room**; **rituals mostly write, not read**; the **Sunday Letter arrives on its own**.
- **Interconnection-map findings that drove it:** the audit surfaced that `memory_entries` and `insights` are **separate stores**, and that the **letters path reads `insights`, not `memories`** — the copy previously implied a single "memory" the whole product reads from, which is not the architecture.

### A4. Efficiency trip — cost optimization (#515–#520, six PRs)

A focused cost/latency pass. **See the Efficiency-trip detail in §6-cache and §5 below; the cache-sentinel template change updates CORR-02 (§19).**

- **SDK GA bump (#515):** `anthropic` **0.34.2 → 0.99.0** (`apps/api/requirements.txt`, verified `anthropic==0.99.0`) — the GA prompt-caching prerequisite.
- **Prompt caching (#516):** a `{{ cache_sentinel }}` slot was added to `system_base.jinja2` **after VOICE CALIBRATION and before PHENOMENOLOGY BRIDGE** (line 112; updates **CORR-02**). `prompt_builder` gains `CACHE_SPLIT_SENTINEL`, `split_system_for_cache()` (splits the system prompt at the sentinel into a cached stable prefix + volatile suffix), and `cache_whole_system()`. Wired on **chat's 4 stream paths** (`conversation_service.py:723/815/1120/1368` via `split_system_for_cache`) **+ Council members only** (`council_service.py:246` via `cache_whole_system`); **synthesis and one-shots are excluded**. Usage logged by `llm_client` (`"llm_usage model=… input=… cache_write=… cache_read=…"`, from `cache_creation_input_tokens` / `cache_read_input_tokens`). **Accepted limitation:** Haiku's minimum cacheable prompt (~4096 tokens) means **FREE (Haiku) does not cache** — the benefit is PRO-only, by design.
- **Counterview free cap (#517):** `FREE_DAILY_COUNTERVIEW_LIMIT = 2` (`rate_limit_service.py:63`), **`source='direct'` count-based**; the router returns **429 + an upgrade wall**. The 429 convention is now **shared with `self_comparison`**.
- **ritual_id validation at conversation creation (#518):** `conversation_service.create` now validates a provided `ritual_id` — it MUST reference an **active ritual the user's tier can access** (`conversation_service.py:223`). This **closed a free rate-limit bypass exploit**. **P4 note:** `ritual_id` still has **no FK** (an orphan check first; FK deferred).
- **Embed dedup (#519):** `recall()`/`retrieve()` gained an optional `query_embedding` param; each chat turn now **embeds the user text once** and reuses the vector across all three chat paths (main / another-mind / go-deeper). Zero behavior change (identical vector to both consumers).
- **Letter suppression logging (#520):** the weekly/monthly letter-email suppression guard log was elevated **`warning → error`** with an actionable message. The **guard was NOT moved** — the generated letter has in-app value (readable at `/app/letters/{id}`), and the shared helper covers **both weekly and monthly**.

### A5. Deep mode — free daily metering + chip-row UX (#497, #498, #503, #504)

- **Free daily metering (#503, migration 050):** `deep_mode_count` INTEGER NOT NULL default 0 added to **`daily_usage`** (050). `FREE_DAILY_DEEP_MODE_LIMIT = 5` (`rate_limit_service.py:59`) — a **global 5/day** free allowance across all personas; Pro/premium unlimited. Toggle ungated for free (metered, not walled).
- **Chip-row UX (#504):** the deep-mode toggle moved to the chip row with a free-quota UX; the separate go-deeper chip was removed.
- **Toggle wiring / state (#497, #498):** #497 wired the Pro deep-mode toggle on the persona-first chat path; #498 made the ON state read as filled bronze.

### A6. Ritual doors + insight doorways (#501, #502, #505, #506, #507)

A set of one-tap "door" surfaces routing the user from chat / letters / insights into a ritual.

- **Named one-tap ritual door chips (#501)** and **global cross-conversation door-chip surfacing (#502)** in chat.
- **Weekly-letter ritual door (#505, #506):** the Sunday Letter can now **suggest a ritual** with an in-voice proposal carried on payload keys (#505), rendered as a **ritual door card that routes into the ritual** (#506).
- **Aspiration → Future Self door chip (#507):** an `aspiration` insight signal surfaces a **Future Self** door chip.

### A7. Council — edited-matter deliberation (#500, #508)

- **Display-summary prefill (#500):** chat-sourced councils get a display-summary prefill.
- **Deliberate the user's edited matter + persist edit flag (#508, migration 051):** the Council now deliberates the user's **edited** matter, and `matter_edited` BOOLEAN NOT NULL default false was added to **`council_sessions`** (051). The edited matter is the text that feeds the Memory arc distill (A1 / #510).

### A8. Auth + polish (#493, #494, #495, #496, #499)

- **Sign-out cleanup (#493):** clears the `ph_token` cookie + localStorage on sign out.
- **401 self-heal + shared `signOut()` (#494):** self-heals on a 401 and routes sign-out through one shared helper.
- **Polish batch 1 (#495)**, **OTP email header (#496)**, **insights star polish (#499)** — stronger "something new" star + larger today-card mark.

---

## Changelog v23 → v24 (PR history, newest first)

| PR | SHA | Description |
|---|---|---|
| #520 | faa18600 | fix(letters): elevate suppressed-email log to error with actionable message |
| #519 | 98a4e641 | perf(chat): embed user text once per turn for recall and retrieval |
| #518 | 96c39368 | fix(conversations): validate ritual_id at conversation creation |
| #517 | 67859ba7 | feat(counterview): free daily cap on direct counterviews with upgrade wall |
| #516 | 36bb52f2 | feat(llm): prompt caching on chat + council member calls |
| #515 | 3cf6a1f2 | chore(deps): bump anthropic SDK 0.34.2 → 0.99.0 (GA prompt-caching prerequisite) |
| #514 | a5cedee4 | feat(explore): rewrite hub copy (memories vs noticings) + add portrait section |
| #513 | a21e75bb | feat(reflections): add quote + future-self-review members to the feed schema union |
| #512 | f3e9b13b | feat(memory): distill a generated counterview rebuttal into a confidence-1 memory |
| #511 | 8b363735 | feat(memory): distill future-self note and mirror ring-true note into confidence-1 memories |
| #510 | 794bf8ca | feat(memory): distill an edited Council matter into a confidence-1 memory |
| #509 | 0a488c85 | feat(chat): bounded insight recheck after a reply |
| #508 | 3dcb2394 | feat(council): deliberate the user's edited matter + persist edit flag (migration 051) |
| #507 | 75ace2ac | feat(insights): aspiration signal → Future Self door chip |
| #506 | ed9744f9 | feat(weekly-letter): ritual door card + route into the ritual |
| #505 | 0e7fb00c | feat(weekly-letter): suggest a ritual + in-voice proposal (payload keys) |
| #504 | 469bfceb | feat(deep-mode): move toggle to chip row + free quota UX, remove go-deeper chip |
| #503 | 213b6b2c | feat(deep-mode): free daily metering (5/day global), ungate toggle (migration 050) |
| #502 | 6b42076b | feat(chat): global cross-conversation door chip surfacing |
| #501 | 4d00fd1f | feat(chat): named one-tap ritual door chips |
| #500 | d7735e47 | feat(council): display-summary prefill for chat-sourced councils |
| #499 | 3f13dd91 | polish(insights): stronger "something new" star + larger today-card mark |
| #498 | ca59d10a | fix(chat): make deep-mode ON state read as filled bronze |
| #497 | 66f0263c | fix(chat): wire Pro deep-mode toggle on the persona-first chat path |
| #496 | e43594b3 | feat(auth): OTP email header |
| #495 | de38b0fc | feat: polish batch 1 |
| #494 | 15e10051 | fix(auth): self-heal on 401 + shared signOut() helper |
| #493 | 2969fd67 | fix(auth): clear ph_token cookie + localStorage on sign out |

Earlier PR history (v22 → v23, #449–#491): see `PROJECT_STATE_v23.md §"Changelog v22 → v23"`. #492 was the v23 doc-rotation PR.

---

## Earlier session deltas (v16 → v23)

Carried forward by reference (additive convention):
- **v23** (#449–#491, Quotes / Wise Room corpus + Future-Self prediction loop + Counterview title + insight seen-state + persona-voice pass, migrations 043–049) — `PROJECT_STATE_v23.md`.
- **v22** (#376–#447, Self-Portrait arc, migrations 038–042) — `PROJECT_STATE_v22.md`.
- **v21 / v20 and earlier** — `PROJECT_STATE_v21.md` / `_v20.md` / …

---

**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment (canonical):** https://thinkalike.netlify.app
**Custom domain (DNS in progress):** https://thegreatminds.app
**Backend:** https://philosopher-api-z9l9.onrender.com

---

## 1. Stack (locked)

Unchanged from v19–v23 (Next.js 14 / FastAPI / Postgres 17 Supabase Oregon / Redis+ARQ / **APScheduler in-process for cron** / Anthropic Claude / OpenAI embeddings / OTP+JWT / Stripe sandbox / Resend / Pillow share cards / client-side canvas for the portrait share card). **v24: `anthropic` SDK pinned `0.99.0`** (GA prompt-caching; #515). **Prompt caching is now live** on chat + Council-member LLM calls (#516) — see §6-cache.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-07-19** — Memory arc (#510/#511/#512), Reflections feed fix (#513), Explore copy + portrait (#514), Efficiency trip (#515–#520), deep-mode metering + chip UX (#497/#498/#503/#504), ritual doors (#501/#502/#505/#506/#507), Council edited matter (#500/#508), auth/polish (#493–#496/#499). Current main: `faa18600`. **Confirm alembic head `051_council_matter_edited` (050–051) applied on the Render deploy.** Prior deploy 2026-07-12 — #491 (`8a79ca3c`).
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3–5 fresh users still pending)

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; PR1 #77). Live wiring pending (TD-28).
- **BETA bypass active:** No — `BETA_GRANT_PRO_TO_ALL=false`. Tier enforcement live via `get_user_tier`.
- **Rituals:** **Mirror ✅** (+ ring-true note → confidence-1 memory, v24 #511) · **Council ✅** (+ **deliberate user's edited matter + persist flag (051)**, v24 #508; edited matter → memory, #510) · **You vs You ✅** · **Weekly Reading / Sunday Letter ✅** (+ **suggest-a-ritual door card**, v24 #505/#506) · **Counterview ✅** (+ **free daily cap 2/day + 429 wall**, v24 #517; rebuttal → memory, #512) · **Self-Portrait ✅** · **Letter to Future Self ✅ delivery LIVE** (+ note → memory, v24 #511) — **no remaining unbuilt rituals.**
- **Quotes / "The Wise Room":** **LIVE (v23)** — unchanged in v24 except the Reflections feed fix (#513) that restored the feed for users with a saved quote.
- **Deep mode:** **LIVE — free daily metering (5/day global, migration 050) + chip-row toggle (v24 #503/#504).** Pro/premium unlimited.
- **Insight engine:** LIVE — recurrence + shift + dilemma/belief/**aspiration** signal detection; **v24: aspiration → Future Self door chip (#507); bounded post-reply insight recheck (#509).**
- **Reflections:** Unified feed — saved lines + Mirror/Council/Counterview verdicts + `kind="insight"` mirrors + YvY sentence-owed + saved corpus quotes + **Future-Self review**. **v24: `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview` added to the schema union (#513) — the feed previously 500'd for users with either.**
- **Memory:** LIVE — extraction (per-turn) + **user-authored distill → confidence-1.0 `entry_type="stated"` memories across 4 ritual surfaces (v24 #510/#511/#512).**
- **Prompt caching:** **LIVE (v24 #516)** — chat 4 paths + Council members; PRO-only benefit (FREE/Haiku below the cache minimum). **PENDING: confirm `cache_read > 0` in prod logs.**

---

## 3. Personas registered

Unchanged — **11 personas** (Free: Marcus Aurelius, Socrates, Lao Tzu; Pro: de Beauvoir, Epictetus, Freud, Jung, Wilde, Machiavelli, Orwell, Musashi). No new personas or config-field changes in v24. See `PROJECT_STATE_v23.md §3`.

---

## 4. Database schema

### Migrations applied (chronological — new since v23)

| Rev | Description | PR |
|---|---|---|
| 001–049 | See `PROJECT_STATE_v23.md §4` / earlier for full history | — |
| **050** | **`daily_usage.deep_mode_count` INTEGER NOT NULL default 0** (free deep-mode daily metering) | **#503** |
| **051** | **`council_sessions.matter_edited` BOOLEAN NOT NULL default false** (Council edited-matter flag) | **#508** |

**alembic_version = `051_council_matter_edited`** (chain …049 → 050 → 051). Both new ids ≤ 32 chars (`050_deep_mode_count` = 19, `051_council_matter_edited` = 25); filenames == revision ids (per C-04, verified this rotation).

### Live database state (verify on Render deploy)

```
alembic_version:           051_council_matter_edited  (Render auto-runs alembic on deploy; confirm 050–051 applied)
daily_usage:               deep_mode_count INT default 0 (050)  [+ message_count, prior columns]
council_sessions:          matter_edited BOOL default false (051); synthesis_structured JSONB (042)
memory_entries:            entry_type='stated' rows land here at confidence=1.0 (v24 distill; no schema change)
quotes / saved_quotes:     live (045/046/048/049); unchanged in v24
scheduled_emails:          prediction / review_text / review_at (043); unchanged in v24
personas count:            11 (all active, WebP portraits)
source_chunks:             2476 across 7 personas (Orwell copyright-excluded; Musashi deferred → 0 chunks each)
```

Both 050 and 051 are **additive columns with server-defaults** → no-ops for existing rows (old `daily_usage`/`council_sessions` render exactly as before until the new path writes). Same shape as 043–048.

### RLS state

**RLS DISABLED on all public tables.** Unchanged.

---

## 5. Backend endpoints / validations

All v23 endpoints apply (see `PROJECT_STATE_v23.md §5`). **New / changed since v23:**

| Method · Path | Router / Service | Notes |
|---|---|---|
| `POST` (conversation create) | `routers/conversations.py` → `conversation_service.create` | **CHANGED (#518).** Validates a provided `ritual_id` — MUST reference an **active ritual the user's tier can access** (`conversation_service.py:223`). Closed a free rate-limit bypass exploit. No FK (P4: orphan check first). |
| Counterview generate (direct) | `routers/counterview.py` → `rate_limit_service` | **CHANGED (#517).** Free tier capped at `FREE_DAILY_COUNTERVIEW_LIMIT = 2/day` (`source='direct'`, count-based); returns **429 + upgrade wall** (429 convention shared with `self_comparison`). |
| Go-deeper / deep-mode gate | `services/conversation_service.py` → `rate_limit_service` | **CHANGED (#503).** Free tier metered by `FREE_DAILY_DEEP_MODE_LIMIT = 5/day` global (migration 050 `deep_mode_count`); Pro/premium unlimited. |
| Reflections feed | `routers/reflections*` (schema `ReflectionFeedItem`) | **FIXED (#513).** Union gained `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview`; previously 500'd for users with a saved quote / future-self review. |

**New services / constants (v24):** `memory_service.distill_to_memory` + `MIN_DISTILL_WORDS=6`; `arq_worker.distill_user_text_to_memory_task`; `rate_limit_service.FREE_DAILY_COUNTERVIEW_LIMIT=2` / `FREE_DAILY_DEEP_MODE_LIMIT=5`; `prompt_builder.CACHE_SPLIT_SENTINEL` / `split_system_for_cache` / `cache_whole_system`; `recall()`/`retrieve()` optional `query_embedding`.

---

## 6. System prompt / caching

Section 6 (send-message), 7 (Council), 8–18 — **unchanged from v19–v23 except as noted in Part A.**

### 6-cache. Prompt caching (v24 #516)

The system prompt template `prompts/system_base.jinja2` gained a `{{ cache_sentinel }}` slot **between VOICE CALIBRATION and PHENOMENOLOGY BRIDGE** (see CORR-02). `prompt_builder.split_system_for_cache()` splits the rendered system prompt at the sentinel into a **cached stable prefix** (intro → PERSONA → EMOTIONAL WEIGHT → CONVERSATIONAL MOVES → ADVANCEMENT → VOICE CALIBRATION) and a **volatile suffix** (PHENOMENOLOGY BRIDGE → profile → memories → GROUNDING PASSAGES → HARD RULES). Applied on chat's 4 stream paths; `cache_whole_system()` caches Council-member calls whole. **Synthesis + one-shots excluded.** `llm_client` logs `cache_write` / `cache_read` token counts. FREE (Haiku) is below the cache minimum → PRO-only benefit (accepted).

---

## 19. Open / Closed items

### Corrections applied this rotation (docs-vs-reality)

- ✅ **CORR-02 (UPDATED) — `system_base.jinja2` now contains the cache-split sentinel.** The v23 CORR-02 order was PERSONA → EMOTIONAL WEIGHT → CONVERSATIONAL MOVES → ADVANCEMENT → VOICE CALIBRATION → PHENOMENOLOGY BRIDGE → profile → memories → GROUNDING PASSAGES → HARD RULES. **v24 inserts a `{{ cache_sentinel }}` slot between VOICE CALIBRATION and PHENOMENOLOGY BRIDGE (#516)** — verified at `system_base.jinja2:112`. The sentinel is the cache split point (prefix cached, suffix volatile). Any instruction inserting into this template MUST be written against the live file (per `CLAUDE.md` Rule 3 / lesson 13.42).
- ✅ **CORR-03 (NEW) — the Reflections feed schema union was incomplete; the feed 500'd.** The feed *service* and *frontend* shipped `SavedQuoteCard` (v23 #475/#476) and the Future-Self review (v23 #450) **without adding the matching members to the `ReflectionFeedItem` Pydantic union**, so response validation 500'd for any user who had a saved quote or a future-self review. #513 added `ReflectionFeedQuote` + `ReflectionFeedFutureSelfReview` and a regression test (`tests/routers/test_reflections_feed.py`). **Lesson:** when a feed gains a new item kind, the schema union member ships in the SAME PR as the service/frontend that can emit it — a union is not optional plumbing.

### Open items (P0 launch blockers) — carried from v20–v23

Unchanged set: **PR3a memory bugs** (verify #435 closed them), OPS-001 (ote.gr re-sync), source_chunks re-ingest (TD-22), post-Oregon smoke test, TD-10 auth race, mobile nav smoke test, cold beta, consolidated polish PR, lawyer review, DNS + Resend domain, GDPR/DPA, founder runbooks, `PHENOMENOLOGY_BRIDGE_ENABLED` confirmation, RLS, UAT. See `PROJECT_STATE_v23.md §19`.

### Open items (P0 operational — must do before next PR)

- [ ] **.gitignore security debt** — `.env.local` NOT in `.gitignore`. (Carried — still open.)
- [ ] **Author smoke-test voice changes** — 6 personas — including the v23 emotional-acknowledgment tier + ADVANCEMENT block + raised deep-mode ceilings.

### New OPEN items logged this rotation

- [ ] **Cache-read verification (NEW — underwriting check).** Confirm `cache_read > 0` appears in prod `llm_usage` logs for a Pro chat turn / Council call — proves the #516 caching is actually landing hits, not just cache writes. Gates the cost model below. Until confirmed, treat caching savings as unproven.
- [ ] **ritual_id FK (P4, NEW — deferred).** #518 added a validation (orphan check) but `conversation.ritual_id` still has **no FK constraint**. Add the FK before public launch; the validation is the cold-beta stopgap.

### Cost / pricing context (for the handoff's "top of mind")

- **Cost-driver map produced** this rotation (the origin of the Efficiency trip, A4). The efficiency PRs (#515–#520) closed the top named drivers (double-embed, uncached chat, unbounded free counterview/deep-mode).
- **Pricing — locked recommendation: single Pro tier at €11.99/mo / €99.99/yr.** **PENDING FOUNDER DECISION** on final UAT willingness-to-pay data. Not yet wired (Stripe live pending TD-28).
- **PENDING VERIFICATION:** `cache_read > 0` in prod logs (above) is the underwriting check on the caching savings assumption baked into the cost model.

### Carried tech debt / parked (still open from v23)

- [ ] **TD-37** dormant brevity post-check · **TD-38** `rituals.ts` future-self copy · **TD-39** `insights.source_count` split · **TD-40** retrieval dedup (CONDITIONAL) · **TD-41** quote-corpus provenance · **TD-42** Greek/CJK share-card font. All carried from `IMPLEMENTATION_BACKLOG_v23`.
- [ ] **Dual tier resolution** (`auth.get_current_user_plan` vs `tier_service.get_user_tier`) — carried from `CLAUDE.md` known-tech-debt; consolidate before paid launch.
- [ ] Carried parked items: `/app/profile` Explore entry point, insight-seeding from letter write-back (OUT of v1), letter write-back fed-forward truncation, adaptive-length/go-deeper threshold tuning, Counterview / Self-Portrait tuning, Quotes tuning.

### Closed / superseded this rotation

- [x] **PR-OPT-4a — chat double-embed** — closed (#519). One embed per turn.
- [x] **PR-OPT-4b — silent letter-email suppression** — closed (#520). Loud error; guard intentionally not moved.
- [x] **Reflections feed 500 for saved-quote / future-self-review users** — closed (#513, CORR-03).
- [x] **Free counterview / deep-mode uncapped** — closed (#517 counterview 2/day; #503 deep-mode 5/day, migration 050).
- [x] **ritual_id free rate-limit bypass** — closed (#518 validation; FK still deferred → new P4 item above).

### Revenue blockers (P0 before first paying user) — carried

- [ ] **Stripe renewal webhook (live)**; **`ENVIRONMENT=production`** on Render API; **`API_BASE_URL`** set (else weekly/season **and future-self** emails suppressed by design — now logged at ERROR, #520); **Live Stripe keys + live price IDs** (TD-28).

---

## 20. Pre-Launch Blockers

> These gate Stripe checkout / revenue activation. None may be deferred past the first paying user.

- [x] ~~`BETA_GRANT_PRO_TO_ALL`~~ — 🟢 OFF (2026-06-03)
- [x] ~~TD-11 tier resolution~~ — 🟢 COMPLETE (#203) (but see dual-tier-resolution debt above)
- [x] ~~End-to-end Stripe sandbox test~~ — 🟢 COMPLETE
- [ ] **Another-mind feature gate (post-cold-beta).**
- [ ] **Systemic frontend `plan` reliability bug** — verify before paid launch.
- [ ] **Live Stripe wiring (TD-28)** — live keys + live price IDs + separate live-mode webhook + `ENVIRONMENT=production` + `API_BASE_URL`.
- [ ] **Pricing decision** — €11.99/mo / €99.99/yr recommended; founder sign-off on UAT WTP pending.

---

**End of PROJECT_STATE v24.** Authoritative as of 2026-07-19 (Memory arc · Reflections feed fix · Explore copy · Efficiency trip · deep-mode metering · ritual doors · Council edited matter · corrections). Supersedes `PROJECT_STATE_v23.md` (preserved as historical reference). Where this file conflicts with v23, v24 wins.
