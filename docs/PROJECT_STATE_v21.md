# PHILOSOPHER — Project State v21

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v21 = v20 baseline (2026-06-21, captured through PR #337) + 2026-06-21→2026-06-26 delta (#339–#374).** Two arcs land here:
> 1. **Counterview ritual — built end-to-end (#342–#362):** the last unbuilt ritual is now live — two minds (Musashi + Machiavelli) each deliver one sharp line making the case against a belief (typed directly or insight-seeded), safety-gated, with go-deeper, save→Reflections feed, a 4:5 Pillow share card, and recurrence detection from voluntary beliefs. Plus insight/guide/splash polish (#339–#341, #355–#359). Migrations **032–033**. *This arc shipped after the v20 doc was cut and was never documented; v21 absorbs it.*
> 2. **This session (#365–#374):** chat **sticky guest mind**, **adaptive response length**, **go-deeper depth + free daily limit + Pro sticky deep mode**, **Chat → Council**, **letter write-back**, **onboarding profile pills**, and the **Home tiles + Explore tab** restructure. Migrations **034–037**. Includes a logged migration incident (revision-id length) and a new migration naming rule.
>
> **Migration head moved 031 → 037.**
>
> **v20 = v19 baseline + 2026-06-21 session (#317–#337):** Insight engine end-to-end, Insight → Mirror loop, weekly-letter email delivery (TD-33), monthly season finale. Migration head 027 → 031. Full detail in `PROJECT_STATE_v20.md`.
>
> **Generated:** 2026-06-26 (v21 rotation) · **Last updated:** 2026-06-26 (Counterview backfill + chat depth/router + letters write-back + onboarding profile + Home/Explore restructure; current main `fed8d312`)

> **v21 conflict resolution rule:** Where v21 conflicts with v20 or earlier, v21 wins. **Production reality always wins over docs.**

> **⚠️ LIVE DATABASE: Supabase project `bvzeuwzqgnqcghvqghtb` (Oregon, us-west-2) is the only live database. The old project `plecolxlzshkfvybszgs` (eu-west-1 / Ireland) is legacy / inactive; do not write to it. All Render services must point to Oregon.**

---

## Part A — Counterview ritual + insight polish (#339–#364) — BACKFILL

> This arc shipped between the v20 doc cut (#338) and this session. It was **built outside the v20→v21 working sessions** (a prior/founder session) and was **never reviewed in them**; this documentation was **reconstructed by reading the merged code at `fed8d312`**, not from session review. Treat it as code-derived, not session-verified — re-read the source before building on it. **Counterview is now LIVE — there are no remaining unbuilt rituals.**

### The Counterview ritual — SHIPPED and LIVE (#342–#362)

Anchored on a position the person holds (typed directly, or seeded from an insight), **two fixed minds each deliver one sharp line making the case against it** — never against the person. Modelled on the Council pattern (one parent row + N persona response rows).

- **Backend core (#342):** `services/counterview_service.py`.
  - **Fixed pair:** `COUNTERVIEW_PERSONAS = [("miyamoto_musashi", 0), ("niccolo_machiavelli", 1)]` — Musashi left (position 0), Machiavelli right (position 1).
  - **`generate_counterview(db, user_id, *, belief=None, insight_id=None, source)`** — resolves the anchor (typed belief → `source='direct'`; insight lookup → `source='insight'`), runs a pre-generation safety gate (`safety_service.check_input` on the anchor; for the insight path also scans the source conversation's user messages), one LLM call (`COUNTERVIEW_PROMPT`, JSON-only, max 300 tokens), then a post-generation `check_output` on each verdict. `status` ∈ `{generated, empty, suppressed}` (empty = LLM returned no case / unparseable; suppressed = safety tripped). Round-0 verdict ceiling **`MAX_WORDS = 10`**, with one automatic tighten-retry (`TIGHTEN_DIRECTIVE`) if over, kept rather than cut mid-sentence (#353).
  - **Insight dedup:** insight path dedups app-level by `insight_id` **and** at the DB by the partial unique index `uq_counterviews_insight`.
- **Go-deeper (#346, #348):** `generate_deeper(db, user_id, counterview_id, persona_slug)` — one sharper round-1 line per persona (`DEEPER_MAX_WORDS = 18`, max 200 tokens), capped at **one round-1 per persona**, safety-gated, race-guarded by the `(counterview_id, persona_slug, round)` unique constraint.
- **Recurrence from voluntary beliefs (#361, "slice 1, no migration"):** on a `generated` direct counterview, the endpoint enqueues `counterview_belief_task` (`workers/arq_worker.py`) which embeds the belief, writes a `MemoryEntry` (`entry_type="counterview_belief"`, confidence 0.7, no persona/conversation), then runs `memory_service.detect_recurrence` (own-id excluded, per-conversation dedup skipped, 6h throttle still honoured). Reuses the existing `memory_entries` table — no migration.
- **Endpoints (`routers/counterview.py`, prefix `/counterview`):**
  - `POST /counterview` (`CounterviewCreate{belief}`) → `CounterviewOut`; on `generated` enqueues the recurrence task. **No tier gate.**
  - `GET /counterview` → `list[CounterviewListItem]` (generated-only, newest first, limit 10) — the revisit list (#362).
  - `GET /counterview/{id}` → `CounterviewOut` (+ `is_saved`).
  - `POST /counterview/{id}/deeper` (`CounterviewDeeperRequest{persona_slug}`) → `CounterviewOut` (returns unchanged on cap/no-op/safety).
  - `POST` / `DELETE /counterview/{id}/save` → upsert / soft-delete (`{saved: bool}`).
  - `POST /insights/{id}/counterview` (`routers/memory.py`) → insight-seeded generate-or-return (DB-level dedup).
- **Save → Reflections feed (#349, #350):** `counterview_saves` table (migration 033, soft-delete via `deleted_at`, unique `(user_id, counterview_id)`). `services/reflections_feed_service.py:_counterview_verdicts` joins save→counterview→round-0 responses and emits feed rows `kind="counterview_verdict"`; rendered by `components/reflections/CounterviewVerdictCard.tsx`.
- **Share (#351, #352):** `POST /share/counterview` (`routers/share.py`) → `services/image_service.py:generate_counterview_share_image` + `_render_counterview_card` — a **1080×1350 (4:5) Pillow card** (two portrait panels, "THE CASE AGAINST", anchor in italics, both verdicts, brand chrome). Rate-limited like line shares: **free 3 / 90 days** (shared `share_screenshot:{user_id}` counter), Pro/premium unlimited. Surfaced via the `kind="counterview"` variant of `components/share/SharePreviewModal.tsx`.
- **Frontend (#343, #344, #345, #347, #354, #360):** `app/app/counterview/page.tsx` — a single screen with `input` (typed belief + revisit list), `insight` (auto-generate from `?insightId=`), and result states. Result screen: large dominant portrait panels, a single speaker-toggle verdict frame, line-level staged reveal (phased, `prefers-reduced-motion` jumps to final), per-persona go-deeper, Save, Share, Start-over. Ritual metadata in `lib/rituals.ts` (`RITUAL_INFO['counterview']`).

### Insight / guide / splash polish (#339–#341, #355–#359, #363)

- **#339** static bronze emphasis on the Today insight seal.
- **#340** insight mirror now hosted via the weekly mirror host; weekly-only chrome hidden on the insight-reflect path.
- **#341** undo toast on insight discard (delayed dismiss, 5s window) — discard is no longer immediate.
- **#355** insight title + post-read letter copy polish; fainter conversation-share hero.
- **#356** discoverability glow on the Library tab + the source conversation, clears on open.
- **#357** tappable rituals → per-ritual explainer screens (`/app/ritual/[slug]`, driven by `RITUAL_INFO`).
- **#358** splash hero loaded via `next/image` `priority` so it paints early.
- **#359** the insight marker unified on a luminous **Sparkle** (was a bronze diamond) — supersedes the v20/v8 "compact bronze diamond" ornament note.
- **#363** dropped `body { zoom: 1.15 }` to isolate a fixed-tabbar tap desync on iOS — **closes TD-32**.

---

## Part B — This session (#365–#374)

> Appended as v21. Where this conflicts with earlier sections, this section wins. **Current main SHA: `fed8d312` (PR #374).**

### Saved-reflection readability (#365) — frontend only

`components/reflections/SavedLineCard.tsx` — the hero background image opacity dropped **0.12 → 0.06** (`opacity-[0.06]`) so conversation-sourced saved lines read cleanly.

### Sticky guest mind (#366)

A conversation can now **stay** with a guest mind instead of reverting to the home persona after one reply.

- **Schema:** `conversations.active_persona_id` (migration 034, FK `personas` `ON DELETE SET NULL`, **nullable** — NULL = no sticky guest, behaves exactly as before).
- **Resolution:** the responder is `coalesce(active_persona_id, persona_id)` at every read site — responder lookup, cross-mind labelling, header, thumbnails, resume, and **quota** (`stream_response` / `stream_go_deeper` in `services/conversation_service.py`). `routers/conversations.py:_conv_out` returns the coalesced active mind as `persona` (with portrait for instant render) and always carries `origin_persona_slug/name` for the "Return to [origin]" affordance.
- **Endpoints:** `POST /conversations/{id}/active-mind` (`ActiveMindSet{target_persona_slug}`; reuses the another-mind tier gate; setting the home persona normalizes to NULL) and `DELETE /conversations/{id}/active-mind` (→ NULL).
- **Frontend:** `components/chat/ChatHeader.tsx` "← Return to {origin}"; `app/app/chat/conv/[id]/page.tsx` handlers `handleContinueWithGuest` / `handleReturnToOrigin`. The fresh-start one-shot another-mind is preserved as the default — stickiness only applies once explicitly activated.

### Adaptive response length (#367)

`services/conversation_service.py:_length_directive_for_input` sizes the reply to the **user's input length**, within the persona's existing band `standard_reply_words = (L, U)`:

- **Short input ≤ 15 words** (`ADAPTIVE_LENGTH_SHORT_MAX_WORDS`) → target `[L, L + round(span × 0.34)]`.
- **Medium input 16–49 words** → `None` (prompt byte-identical to before).
- **Long input ≥ 50 words** (`ADAPTIVE_LENGTH_LONG_MIN_WORDS`) → target `[L + round(span × 0.5), U]`.
- Never exceeds the persona's standard ceiling **U**. Gated: applies **only when `safety_in.level == "none"`** (distress wins) and **skipped on the first message** (`history_len > 1`). All 11 persona modules populate `response_length_words`; a persona without the spec → no directive (no-op).

### Go-deeper depth + free daily limit + Pro sticky deep mode (#368)

Go-deeper now means **genuine depth**, not just a longer reply:

- **`_deepen_directive`** targets `response_length_words.reflective_reply_max_words` (which *exceeds* the standard ceiling U; fallback 90 words). `DEEPEN_ESCALATION` was **neutralized** — repeat taps open a new/deeper layer rather than shortening.
- **Free limit:** **3 / day per HOME persona** (`FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA = 3`, `services/rate_limit_service.py`), counted in `daily_usage.go_deeper_count` (migration 035) keyed on **`conv.persona_id`, not the resolved responder** — this closes the guest-switch exploit. Pro/premium unlimited. Count increments only on committed success.
- **Pro sticky deep mode:** `conversations.deep_mode` (migration 035, BOOL NOT NULL DEFAULT false). `POST` / `DELETE /conversations/{id}/deep-mode` (POST is Pro-gated, 403 for free). Read site is **also** Pro-gated: `deep_mode and user_plan in ('pro','premium') and safety_in.level == 'none'` — a stale `true` on a downgraded account is inert, and distress wins.

### Chat → Council (#369)

- **Frontend:** a header Council icon (lucide `Scale`) in `components/chat/ChatHeader.tsx`, **visible to all users** (an upsell surface), enabled once a user message exists. It seeds the last user message (`slice(0, 600)`) via `sessionStorage` (`council_prefill` + `council_source='chat'`). **Pro → `/app/council`** pre-filled; **free → `/app/upgrade`**. `app/app/council/page.tsx` reads and clears the keys (reusing the mirror→council pattern).
- **Backend:** the council `source` tuple gains `'chat'` (`routers/council.py`); `WEEKLY_LIMIT_PER_SOURCE = 1` (`services/council_service.py`) means `'chat'` is its own analytics-distinct weekly bucket — effectively +1 council/week for Pro through this channel. No new LLM call or component.

### Letter write-back (#370)

A reader can write a short response back to a Sunday/season letter.

- **Schema:** `weekly_letters.write_back_text` + `write_back_at` (migration 036, both nullable; mirrors the `mirrors.ring_true_note`/`ring_true_at` pattern). One write-back per letter, **editable** (row overwritten) — no history table.
- **Endpoint:** `PATCH /weekly-letters/{id}/write-back` (`routers/weekly_letters.py`, **Pro-gated**; `WriteBackIn{text}` 1–2000 chars).
- **Frontend:** `components/letters/WriteBackPanel.tsx` end-of-letter window, wired into both the weekly reader and `SeasonFinaleView` (`app/app/letters/[id]/page.tsx`).
- **Fed forward:** `generate_weekly_letter_task` / monthly task inject the prior letter's write-back as `<reader_wrote_back>…</reader_wrote_back>` inside the existing guarded prior-letters fetch — no new query, no new generator path. **v1: no live reply, no insight-seeding.**

### Onboarding profile pills (#372)

Two tappable-pill questions give the room a guaranteed baseline of who the person is.

- **Questions/keys:** `values`, `disagreement_style`; stored in `user_preferences.profile` JSONB (migration 037, nullable — NULL hides everything).
- **Guaranteed awareness:** a `<what_we_know>` block ("WHAT WE KNOW ABOUT THIS PERSON") rendered directly into the persona prompt on turn 1 (`prompts/system_base.jinja2`, fed `profile_to_display()`) — **not** via RAG/recall.
- **Memory + YvY:** seeded as embedded `memory_entries` (`entry_type='onboarding_profile'`, confidence 0.8, atomic deactivate-old + insert-new) via `seed_profile_memory_task`, so recall and You-vs-You also see it. Instant **forming reflection** via `self_comparison_service.forming_reflection()` on the same statements.
- **Single source of truth:** `services/profile_text.py` (`profile_to_statements`, `profile_to_display`; `VALUE_LABELS` / `DISAGREEMENT_LABELS` enum→phrase maps).
- **Endpoints:** `PATCH /preferences/profile` (`ProfileIn`, enqueues the seed task) and `POST /preferences/profile/reflection`. Screens: `app/app/onboarding/profile/page.tsx` (with "Skip for now") and standalone editable `app/app/profile/page.tsx`. **First weekly letter untouched.**

### Home tiles + minimal Insights list (#373)

- **Today → "Home" (LABEL ONLY** — the URL stays `/app/today`; `app/app/(tabs)/today/page.tsx`, `BottomTabBar` label "Home").
- A **2×2 typographic tile grid** (`HomeTile`): **Discussion** (expands inline to `TodaysTopicCard`), **Insights** (→ `/app/insights`), **Library**, **Rituals**; plus a **5th wide Sunday tile** (`SundayLetterCard`). Continue + reflections cards stay inline below.
- **New screen `/app/insights`** (`app/app/insights/page.tsx`) — a minimal list of non-dismissed insights, each routing to its reflection (mirror `?insightId=`, You-vs-You, or counterview).

### Chat → Council header, Home, Explore restructure (#374)

- **Rituals tab → Explore tab** in `components/layout/BottomTabBar.tsx` (Compass icon; tabs are now **Home · Explore · Library · Account**).
- **Guide re-parented:** the old `app/app/guide/page.tsx` was **moved into `app/app/(tabs)/explore/page.tsx`** (back chrome stripped, safe-area top padding). The standalone `/app/guide` route and the old `/app/explore` redirect page were **deleted**.
- **Collision fix:** the 4 "choose a mind" callers (welcome, onboarding matches, empty conversation history, Sunday-letter card) were repointed to **`/app/library?mode=browse`** — their real intent — before the new tab claimed `/app/explore`.
- The **`/app/rituals` route is kept** (sub-page fallbacks/links + the Home Rituals tile still resolve) but **delisted from the tab bar**. The redundant Home "Explore The Wise Room" button was removed.

### Reading-surface type bump (#364)

Base body font **15px → 17px** (`app/globals.css`), with matching bumps to chat bubbles, the insight card, counterview verdicts, and the error/safety/opening surfaces (commit framing "~15%").

### The migration incident (#371) — logged failure + new rule

- **What happened:** migration 035's revision id was authored as `035_deep_mode_and_go_deeper_count` — **33 chars**, one over `alembic_version.version_num VARCHAR(32)`. The Render deploy crashed at the version-write.
- **Diagnosis:** Postgres transactional DDL rolled the whole upgrade back; the DB stayed cleanly at **034** (035's columns never persisted). **Not half-applied.**
- **Fix (#371):** renamed the revision id (+ filename + 036's `down_revision`) to **`035_deep_mode_go_deeper`** (23 chars).
- **New standing rule:** **a migration's revision id must be ≤ 32 chars, and the filename must equal the revision id.** Codified in `CLAUDE.md` (persona & migration conventions, C-04).

---

## Earlier session deltas (v16 → v20)

Carried forward by reference (additive convention):
- **v20** (#317–#337, Insight engine + Insight→Mirror + weekly email + season finale, migrations 028–031) — `PROJECT_STATE_v20.md`.
- **v19 / v18 / v17 and earlier** — `PROJECT_STATE_v19.md` / `_v18.md` / `_v17.md`.

---

**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment (canonical):** https://thinkalike.netlify.app
**Custom domain (DNS in progress):** https://thegreatminds.app
**Backend:** https://philosopher-api-z9l9.onrender.com

---

## 1. Stack (locked)

Unchanged from v19/v20. (Next.js 14 / FastAPI / Postgres 17 Supabase Oregon / Redis+ARQ / Anthropic Claude / OpenAI embeddings / OTP+JWT / Stripe sandbox / Resend / Pillow share cards.)

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-06-26** — Counterview ritual end-to-end (#342–#362), insight/guide/splash polish (#339–#359), reading-surface type bump (#364), sticky guest mind (#366), adaptive response length (#367), go-deeper depth + free limit + Pro deep mode (#368), Chat → Council (#369), letter write-back (#370), onboarding profile pills (#372), Home tiles + Insights list (#373), Explore tab (#374). Current main: `fed8d312`. Prior deploy 2026-06-21 — #337 (`4c4221c9`).
- **Has paying users:** No
- **Has free trial users:** No (cold beta with 3–5 fresh users still pending)

### Other systems

- **Stripe wired:** Yes — sandbox (checkout + portal + webhook; PR1 #77). Live wiring pending (TD-28).
- **BETA bypass active:** No — `BETA_GRANT_PRO_TO_ALL=false`. Tier enforcement live via `get_user_tier`.
- **Rituals:** **Mirror ✅** (+ insight-seeded mirror, v20); **Council ✅** (+ Chat → Council source, v21); **You vs You ✅**; **Weekly Reading / Sunday Letter ✅** (+ ARQ email, season finale, v20; + write-back, v21); **Letter to Future Self** functional, ARQ delivery still not wired; **Counterview ✅ SHIPPED (v21, #342–#362)** — **no remaining unbuilt rituals.**
- **Insight engine:** LIVE (v20) — recurrence + shift detector; in-chat chip, Today card, three-action card, provenance, insight → Mirror loop. v21: discard undo toast (#341), Sparkle marker (#359), Library discoverability glow (#356), standalone `/app/insights` list (#373).
- **Reflections:** Unified feed live — saved lines + Mirror/Council verdicts + `kind="insight"` mirrors + **`kind="counterview_verdict"` (v21)**; client-side search.
- **Share:** v3 / Council / Letter / Season / **Counterview 4:5 (v21)**.

---

## 3. Personas registered

Unchanged — **11 personas** (Free: Marcus Aurelius, Socrates, Lao Tzu; Pro: de Beauvoir, Epictetus, Freud, Jung, Wilde, Machiavelli, Orwell, Musashi). Council roster fixed (Machiavelli, Epictetus, Freud, de Beauvoir). **Counterview pair fixed (Musashi + Machiavelli).** See `PROJECT_STATE_v19.md §3`.

> **Note:** all 11 persona modules (`apps/api/personas/*.py`) now populate `response_length_words` (`standard_reply_words` band + `reflective_reply_max_words`), which drive adaptive length (#367) and go-deeper depth (#368).

---

## 4. Database schema

### Migrations applied (chronological — new since v20)

| Rev | Description | PR |
|---|---|---|
| 001–031 | See `PROJECT_STATE_v20.md §4` / earlier for full history | — |
| **032** | **`counterviews` + `counterview_responses` tables** (parent + per-persona/round verdicts; `source` ∈ {direct,insight}; partial unique `uq_counterviews_insight`; `status` ∈ {generated,empty,suppressed}) | **#342** |
| **033** | **`counterview_saves` table** (soft-delete `deleted_at`; unique `(user_id, counterview_id)`) | **#349** |
| **034** | **`conversations.active_persona_id` UUID NULL** FK personas ON DELETE SET NULL (sticky guest mind) | **#366** |
| **035** | **`conversations.deep_mode` BOOL NOT NULL DEFAULT false** + **`daily_usage.go_deeper_count` INT NOT NULL DEFAULT 0** (Pro sticky deep mode + free go-deeper limit) | **#368** |
| **036** | **`weekly_letters.write_back_text` TEXT NULL** + **`write_back_at` TIMESTAMPTZ NULL** (letter write-back) | **#370** |
| **037** | **`user_preferences.profile` JSONB NULL** (onboarding profile pills) | **#372** |

**alembic_version = `037_user_preferences_profile`** (chain …031 → 032 → 033 → 034 → 035 → 036 → 037). All revision ids ≤ 32 chars; filenames equal revision ids (per C-04, post-#371).

> **Incident note (035):** the original revision id `035_deep_mode_and_go_deeper_count` (33 chars) overran `version_num VARCHAR(32)`; the deploy rolled back to 034 (transactional DDL — never half-applied) and #371 renamed it to `035_deep_mode_go_deeper`. See Part B and `CLAUDE.md C-04`.

### Live database state (verify on Render deploy)

```
alembic_version:           037_user_preferences_profile  (Render auto-runs alembic on deploy; confirm 032–037 applied)
counterviews:              live (032); status ∈ {generated,empty,suppressed}; source ∈ {direct,insight}
counterview_responses:     live (032); unique (counterview_id, persona_slug, round)
counterview_saves:         live (033); soft-delete deleted_at
conversations:             active_persona_id (034) + deep_mode (035)
daily_usage:               go_deeper_count (035)
weekly_letters:            write_back_text + write_back_at (036); kind ∈ {weekly,monthly}; email_sent_at
user_preferences:          profile JSONB (037)
personas count:            11 (all active, WebP portraits)
source_chunks:             2476 across 7 personas (Orwell copyright-excluded; Musashi deferred → 0 chunks each)
```

### RLS state

**RLS DISABLED on all public tables.** Unchanged.

---

## 5. Backend endpoints

All v20 endpoints apply (see `PROJECT_STATE_v20.md §5`). **New / changed since v20:**

| Method · Path | Router | Notes |
|---|---|---|
| `POST /counterview` · `GET /counterview` · `GET /counterview/{id}` | `counterview.py` | **NEW (#342, #362).** Create (typed belief) / revisit list (generated-only, ≤10) / fetch. No tier gate. Create enqueues recurrence task on `generated`. |
| `POST /counterview/{id}/deeper` | `counterview.py` | **NEW (#346).** One round-1 line per persona; safety-gated; no-op on cap. |
| `POST` · `DELETE /counterview/{id}/save` | `counterview.py` | **NEW (#349, #350).** Upsert / soft-delete; feeds Reflections. |
| `POST /insights/{id}/counterview` | `memory.py` | **NEW (#343).** Insight-seeded generate-or-return (DB dedup). |
| `POST /share/counterview` | `share.py` | **NEW (#351).** 4:5 Pillow card; free 3/90d (shared with line shares), Pro unlimited. |
| `POST` · `DELETE /conversations/{id}/active-mind` | `conversations.py` | **NEW (#366).** Set/clear sticky guest mind. |
| `POST` · `DELETE /conversations/{id}/deep-mode` | `conversations.py` | **NEW (#368).** Pro-gated sticky deep mode. |
| `PATCH /weekly-letters/{id}/write-back` | `weekly_letters.py` | **NEW (#370).** Pro-gated; `WriteBackIn{text}` 1–2000 chars. |
| `PATCH /preferences/profile` · `POST /preferences/profile/reflection` | `preferences.py` | **NEW (#372).** Save profile (enqueues seed task) / forming reflection. |
| `POST /council` | `council.py` | **CHANGED (#369):** `source` tuple gains `'chat'` (own weekly bucket). |

---

## 6–18.

Sections 6 (send-message — now also resolves the active mind + adaptive length + deep mode), 7 (Council — `'chat'` source), 8–18 — **unchanged from v19/v20 except as noted in Parts A/B.** See `PROJECT_STATE_v20.md` / `PROJECT_STATE_v19.md`.

### 14. Session metrics — v21 (2026-06-21→2026-06-26)

| Metric | Value |
|---|---|
| PRs merged | #339–#374 (#338 was the v20 doc PR) |
| Migrations deployed | 032 counterviews, 033 counterview_saves, 034 active_persona_id, 035 deep_mode+go_deeper_count, 036 letter write-back, 037 user profile |
| New services | `services/counterview_service.py`, `services/profile_text.py` |
| New routers | `routers/counterview.py` |
| New endpoints | counterview (6) + `/share/counterview` + active-mind (2) + deep-mode (2) + letter write-back + preferences profile (2) + `POST /insights/{id}/counterview` |
| New screens | `/app/counterview` (live ritual), `/app/insights`, `/app/profile`, `/app/onboarding/profile`, Explore tab (re-parented guide) |
| Key features | Counterview ritual live (last unbuilt ritual closed); sticky guest mind; adaptive length; go-deeper depth + limits + Pro deep mode; Chat → Council; letter write-back; onboarding profile pills; Home tiles + Explore restructure |

### 17. Key file paths — new/updated in v21

**Backend:**
- `apps/api/services/counterview_service.py` — NEW: `generate_counterview`, `generate_deeper`, prompts, fixed pair.
- `apps/api/routers/counterview.py` — NEW: counterview endpoints.
- `apps/api/routers/memory.py` — `POST /insights/{id}/counterview`.
- `apps/api/routers/share.py` + `apps/api/services/image_service.py` — counterview 4:5 card.
- `apps/api/services/reflections_feed_service.py` — `_counterview_verdicts`.
- `apps/api/services/conversation_service.py` — sticky-guest coalescing; `_length_directive_for_input`; `_deepen_directive` + neutralized escalation; deep-mode read gate; `<what_we_know>` profile injection (turn 1).
- `apps/api/services/rate_limit_service.py` — `FREE_DAILY_GO_DEEPER_LIMIT_PER_PERSONA = 3`.
- `apps/api/services/profile_text.py` — NEW: enum→phrase single source of truth.
- `apps/api/services/council_service.py` / `apps/api/routers/council.py` — `'chat'` source.
- `apps/api/routers/conversations.py` — active-mind + deep-mode endpoints; `_conv_out` coalescing + origin fields.
- `apps/api/routers/weekly_letters.py` — write-back endpoint.
- `apps/api/routers/preferences.py` — profile save + reflection.
- `apps/api/workers/arq_worker.py` — `counterview_belief_task`, `seed_profile_memory_task`, `<reader_wrote_back>` injection in letter tasks.
- `apps/api/prompts/system_base.jinja2` — `<what_we_know>` block.
- `apps/api/db/migrations/versions/032_*`…`037_*`.

**Frontend:**
- `apps/web/app/app/counterview/page.tsx` — live ritual (input/insight/result states).
- `apps/web/components/reflections/CounterviewVerdictCard.tsx` — feed card.
- `apps/web/components/share/SharePreviewModal.tsx` — counterview variant.
- `apps/web/components/chat/ChatHeader.tsx` — return-to-origin + Council (Scale) icon + deep-mode toggle.
- `apps/web/app/app/chat/conv/[id]/page.tsx` + `chat/[slug]/page.tsx` — guest/return/deep-mode/take-to-council handlers.
- `apps/web/app/app/council/page.tsx` — reads `council_source='chat'`.
- `apps/web/components/letters/WriteBackPanel.tsx` + `SeasonFinaleView.tsx` + `app/app/letters/[id]/page.tsx` — write-back window.
- `apps/web/app/app/onboarding/profile/page.tsx` + `app/app/profile/page.tsx` — profile pills.
- `apps/web/app/app/(tabs)/today/page.tsx` — Home tiles (`HomeTile`).
- `apps/web/app/app/insights/page.tsx` — NEW: minimal insights list.
- `apps/web/app/app/(tabs)/explore/page.tsx` — re-parented guide (was `/app/guide`).
- `apps/web/components/layout/BottomTabBar.tsx` — Home · Explore · Library · Account.
- `apps/web/components/reflections/SavedLineCard.tsx` — hero opacity 0.06.
- `apps/web/app/globals.css` — body 17px.
- `apps/web/lib/api.ts` + `lib/rituals.ts` — counterview client + ritual metadata.

---

## 19. Open / Closed items

### Open items (P0 launch blockers) — carried from v20

Unchanged set: **PR3a memory bugs** (fresh-chat missing opening message/thumbnail; home "Continuing" 404s), OPS-001 (ote.gr re-sync), source_chunks re-ingest (TD-22), post-Oregon smoke test, TD-10 auth race, mobile nav smoke test, cold beta, consolidated polish PR, lawyer review, DNS + Resend domain, GDPR/DPA, founder runbooks, `PHENOMENOLOGY_BRIDGE_ENABLED` confirmation, RLS, UAT. **None closed this session.** See `PROJECT_STATE_v20.md §19`.

### Open items (P0 operational — must do before next PR)

- [ ] **.gitignore security debt** — `.env.local` NOT in `.gitignore`. (Carried — still open.)
- [ ] **Author smoke-test voice changes** — Wilde, Jung, Freud, de Beauvoir, Machiavelli, Lao Tzu.

### New tech debt logged this session

- [ ] **TD-37 — Dormant brevity post-check.** `services/postprocessing_service.py:check_brevity` is computed on the live stream path but does **NOT** trigger regeneration — only `forbidden_lexicon` hits enter the `_triggered` regenerate set (see the `# brevity no longer forces a regenerate/correction` comment in `conversation_service.py`). The full `regenerate_or_trim` loop runs only in tests. So nothing hard-enforces reply length in production beyond the prompt nudge (adaptive length + `_deepen_directive`). **Wire or retire post-first-paying-user.**

### Parked / follow-ups logged this session (not done)

- [ ] **Home tiles → custom images** — currently typographic; images wanted in v2.
- [ ] **`/app/profile` → Explore-tab entry point** — route exists, no nav link yet; wire when convenient.
- [ ] **Insight-seeding from letter write-back** — explicitly OUT of v1.
- [ ] **Letter write-back fed-forward truncation** — no max-length cap when injected into the next letter; minor future tuning.
- [ ] **Adaptive-length thresholds (15/50) + go-deeper free limit (3/day)** — launch defaults; tune on real cold-beta volume.
- [ ] **Counterview threshold/voice tuning** — fixed Musashi+Machiavelli pair, 10-word cut; revisit on real volume.

### Revenue blockers (P0 before first paying user) — carried

- [ ] **Stripe renewal webhook (live)**; **`ENVIRONMENT=production`** on Render API; **`API_BASE_URL`** set (else weekly/season emails suppressed by design); **Live Stripe keys + live price IDs** (TD-28).

### Closed this session

- [x] **CLOSED** — **Counterview ritual** (the last unbuilt ritual): backend core + go-deeper + save/feed + 4:5 share + recurrence detection + live screen (#342–#362). The `/app/counterview` stub is replaced by the real ritual.
- [x] **CLOSED** — **TD-32** (remove `body { zoom: 1.15 }`) via #363.

### Closed items (2026-06-21 and earlier)

See `PROJECT_STATE_v20.md §19` (TD-33 weekly email, insight engine, insight→Mirror loop, season finale) and `PROJECT_STATE_v19.md §19`.

---

## 20. Pre-Launch Blockers

> These gate Stripe checkout / revenue activation. None may be deferred past the first paying user. **None closed this session.**

- [x] ~~`BETA_GRANT_PRO_TO_ALL`~~ — 🟢 OFF (2026-06-03)
- [x] ~~TD-11 tier resolution~~ — 🟢 COMPLETE (#203)
- [x] ~~End-to-end Stripe sandbox test~~ — 🟢 COMPLETE
- [ ] **Another-mind feature gate (post-cold-beta)** — note: sticky guest mind (#366) reuses the same another-mind tier gate.
- [ ] **Systemic frontend `plan` reliability bug** — fix before paid launch.
- [ ] **Live Stripe wiring (TD-28)** — live keys + live price IDs + separate live-mode webhook + `ENVIRONMENT=production` + `API_BASE_URL`.

---

**End of PROJECT_STATE v21.** Authoritative as of 2026-06-26 (Counterview ritual backfill · chat depth/sticky-guest/Council · letter write-back · onboarding profile · Home/Explore restructure). Supersedes `PROJECT_STATE_v20.md` (preserved as historical reference). Where this file conflicts with v20, v21 wins.
</content>
</invoke>
