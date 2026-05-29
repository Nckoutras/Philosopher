# PHILOSOPHER — Session Addendum 2026-05-29

> **What this file is:** Session delta for 2026-05-29. Supersedes the relevant sections of PROJECT_STATE_v13.md, HANDOFF_BRIEF_v13.md and IMPLEMENTATION_BACKLOG_v13.md where they conflict. Production reality always wins over docs.
>
> **Baseline:** v13 (2026-05-28).
> **Session theme:** Typography pass (PR-F) closed; C9 "Bring another mind" (headline Pro feature) built end-to-end and shipped; cross-mind awareness shipped.

---

## 1. Shipped this session

### Typography — PR-F (COMPLETE)
- **PR-F V1** (`feat/typography-v1`): chat reading text 14→16px (MessageBubble, StreamingBubble, SafetyBubble, ErrorMessage); Cormorant screen titles font-normal→font-medium (500) across ~21 h1/h2 incl. legal. Excluded: OTP input, splash hero.
- **PR-F Phase 2** (`feat/typography-phase2`): comprehension prose 13→15px on 11 lines (persona bio, ritual descriptions, onboarding match/need/themes, disclaimer, scheduled-letters).
- **Final type scale (locked):** chat 16 / screen titles weight-500 / comprehension prose 15 / saved-lines 17 (cormorant italic) / chrome unchanged.

### C9 "Bring another mind" — COMPLETE (headline Pro feature)
Mid-chat, the user brings a second philosopher for a take on the same topic; the guest's reply renders inline; the conversation then continues with the original ("home") persona. 5 PRs, all squash-merged:

1. **PR-B1 — backend engine** (`feat/pr-b1-another-mind-backend`, #71ce6e3)
   - Migration **016_message_persona_id** (down_revision `015_add_fk_indexes`): nullable `messages.persona_id` UUID FK → personas.id + index `ix_messages_persona_id`. NULL = home persona (existing rows correct).
   - ORM: `Message.persona_id` + `persona` relationship.
   - Schemas: `MessageOut.persona_slug`; new `AnotherMindCreate { target_persona_slug }`.
   - Router: `get_messages` eager-loads persona + returns `persona_slug`; NEW **POST /api/v1/conversations/{id}/another-mind** (SSE; Pro-gate → 403 `upgrade_required`; same-persona → 400; rate-limit keyed to target persona).
   - Service: NEW `stream_another_mind` (does NOT touch `stream_response`). Keys memory recall + RAG + final user turn to the most recent USER message. Emits `start` with `{brought_in, persona_slug, persona_name}`. Persists assistant message with `persona_id = target`.

2. **PR-B2 — picker + streaming UI** (`feat/pr-b2-another-mind-ui`, #ff37f36)
   - `lib/api.ts`: `streamAnotherMind()` (403→`upgrade_required`, 429→RateLimitError); `SSEEventStart` gains `brought_in?/persona_slug?/persona_name?`; `Message` gains `persona_slug?`.
   - `lib/useStream.tsx`: NEW `sendAnotherMind()` (does NOT touch `send()`); no user-message append.
   - NEW `components/chat/AnotherMindSheet.tsx` (reuses BottomSheet; excludes home; locked → /app/upgrade).
   - `QuickActionsRow` + `MessageList`: `onBringAnotherMind` threaded; both chat pages mount the sheet.

3. **Gate bugfix** (`fix/another-mind-gate-backend-authority`, #225a68d)
   - Bug: premium account hit paywall on Bring-another-mind. Cause: store `plan` getter depends on `SubscriptionBootstrap`, which only runs inside `(tabs)/layout.tsx`; chat pages are outside it, so `plan` read 'free'.
   - Fix: removed the client plan check; picker opens unconditionally; `sendAnotherMind` routes 403 `upgrade_required` → /app/upgrade. **Backend entitlement is authority; client plan is UX-only.**

4. **PR-B3 + B3v2 — attribution** (`feat/pr-b3-brought-in-attribution`, then `feat/pr-b3v2-live-attribution`)
   - Eyebrow "{name} · brought in", linen bubble for brought-in turns, "Continuing with {home}" divider.
   - B3v2: store `streamingBroughtInName` + `setStreamingBroughtIn` (cleared in ALL reset sites); live attribution in `StreamingBubble` ("{home} steps aside" + "{guest} · brought in" + linen) while streaming; `persona_name` stamped on the persisted message so the eyebrow is instant (background fetch kept only as reload fallback). `send()` never touched.

### Cross-mind awareness — COMPLETE (`feat/cross-mind-awareness`, cea8f29)
The home persona now recognises a brought-in guest's words instead of mistaking them for its own.
- In `conversation_service.py`, when building LLM history, assistant turns authored by a mind **other than the responder** are labelled inline as `[Name]: ...`. A short `CROSS_MIND_NOTE` is appended to the system prompt **only when** such turns exist (tells the persona those words belong to other invited thinkers; never to bracket its own reply).
- Symmetric: home reply → guests labelled; guest reply → home + other guests labelled. A turn's author = its `persona_id`, or the home persona when NULL.
- **Core-path safety:** with no brought-in turns, `lm_messages` is built byte-identically to before. One persona-name lookup added, only when foreign turns exist.
- No schema / SSE / storage changes. New helper `_build_lm_messages`.

---

## 2. Supersedes in PROJECT_STATE_v13
- **§4 Schema:** `alembic_version` is now **`016_message_persona_id`** (was `015_add_fk_indexes`).
- **§5 Endpoints:** add **POST /api/v1/conversations/{id}/another-mind**. The "exactly ONE send-message endpoint" statement still holds for the *home* chat path; another-mind is a distinct additive endpoint.
- **§6 Architecture:** `conversation_service.py` now has TWO streaming entrypoints — `stream_response` (home, canonical) and `stream_another_mind` (guest). Both apply cross-mind history labelling.
- **§2 / Block C:** C9 "Bring another mind" shipped.

## 3. File paths (additions/changes this session)
### Backend (apps/api/)
- `db/migrations/versions/016_message_persona_id.py` — **NEW** (rev 016, down_rev 015)
- `models/__init__.py` — `Message.persona_id` + `persona` relationship
- `schemas/__init__.py` — `MessageOut.persona_slug`; `AnotherMindCreate`
- `routers/conversations.py` — `get_messages` persona eager-load + `persona_slug`; POST `/another-mind`
- `services/conversation_service.py` — `stream_another_mind`; cross-mind labelling (`_build_lm_messages`, `CROSS_MIND_NOTE`) in both stream methods

### Frontend (apps/web/)
- `lib/api.ts` — `streamAnotherMind`; `SSEEventStart` fields; `Message.persona_slug` + `persona_name`
- `lib/useStream.tsx` — `sendAnotherMind`; streaming brought-in handling
- `lib/store.ts` — `streamingBroughtInName` + `setStreamingBroughtIn`; cleared in all reset sites
- `components/chat/AnotherMindSheet.tsx` — **NEW**
- `components/chat/StreamingBubble.tsx` — live brought-in attribution (+ typography 16px)
- `components/chat/MessageList.tsx` — brought-in eyebrow / linen / "Continuing with" divider
- `components/chat/QuickActionsRow.tsx` — `onBringAnotherMind`
- `app/app/chat/[slug]/page.tsx`, `app/app/chat/conv/[id]/page.tsx` — mount AnotherMindSheet + handler
- Typography: `MessageBubble.tsx`, `SafetyBubble.tsx`, `ErrorMessage.tsx` (16px); ~21 titles → font-medium; 11 comprehension lines → 15px

## 4. Newly logged items
- 🔴 **Systemic frontend `plan` reliability bug** — client `plan` getter unreliable on any route outside `(tabs)/layout.tsx` (where `SubscriptionBootstrap` runs). Affects all client-side plan gates. Fix before paid launch. Ties to **TD-11**.
- 🟡 **Another-mind feature gate (post-beta)** — backend gates another-mind per-persona (`is_persona_accessible`), NOT at feature level. Add a feature-level Pro gate **before** turning off `BETA_GRANT_PRO_TO_ALL`.
- ⚪ **Deferred enhancement — "switch to the brought-in mind"** (persona switching mid-conversation). Needs a "current responder" concept + header/identity changes. Post-validation only.

## 5. Status
- C9 "Bring another mind" — **COMPLETE**, live-tested OK (premium account).
- Cross-mind awareness — **COMPLETE**.
- Typography PR-F — **COMPLETE**.
- Critical path to revenue (unchanged, still open): cold-beta validation → live Stripe → TD-11 + another-mind feature gate → paid launch.

## 6. Drift flag (NOT addressed this session)
- Docs still reference brand "Great Minds" / domain `thegreatminds.app`; infra notes suggest the live brand/domain may now be "The Wise Room" / `thewiseroom.app`. **Unresolved** — reconcile in a dedicated brand/docs PR, not bundled with code.
