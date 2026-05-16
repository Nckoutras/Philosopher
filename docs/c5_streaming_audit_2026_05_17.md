# C5 Streaming Architecture Audit

**Date:** 2026-05-17  
**Branch:** `c5a-investigation/streaming-audit`  
**Type:** Investigation-only report — no code modified  
**Follows:** C-RECON-1 pattern (investigation PR → founder decision → implementation PRs)

---

## Section 1 — What exists today

### 1.1 `api.streamMessage()` — `apps/web/lib/api.ts:235-256`

**Signature:**
```typescript
async streamMessage(conversationId: string, content: string): Promise<Response>
```

**Step-by-step:**
1. `fetch()` POSTs to `${API_BASE}/conversations/${conversationId}/messages`
2. Sets `Content-Type: application/json` and `Authorization: Bearer ${this.token}`
3. Body: `JSON.stringify({ content })`
4. On HTTP 429: reads body as JSON, throws an augmented `Error` with `.status = 429` and `.detail = body.detail`
5. On other non-2xx: throws `new Error('Stream failed')`
6. On 2xx: **returns the raw `Response` object** — no SSE parsing is performed

**State reads:** `this.token` (from `ApiClient` singleton, loaded from `localStorage` as `ph_token`)  
**State writes:** none  
**Public API:** `api.streamMessage(conversationId, content)` — caller is responsible for all SSE parsing

**Auth pattern:** Token is stored as `ApiClient.token`. Set via `setToken()` which writes to `localStorage` as `ph_token` and also writes a `ph_token` cookie. Loaded on module init via `api.loadToken()`. Applied inline in `streamMessage` (not via the shared `request()` helper).

---

### 1.2 `useStream.tsx` — `apps/web/lib/useStream.tsx`

**Signature:**
```typescript
export function useStream(): { send: (content: string) => Promise<void> }
```

**Dependencies:** `api` (from `@/lib/api`), `useStore` (from `@/lib/store`)

**Step-by-step on `send(content)`:**
1. Reads `activeConversationId` from store — returns early if null
2. Creates an optimistic user `Message` object with `crypto.randomUUID()` as id
3. Calls `appendMessage(userMsg)` and `setStreaming(true)`
4. Calls `api.streamMessage(activeConversationId, content)` to get raw `Response`
5. Gets reader: `res.body!.getReader()` — **non-null assertion, will throw if body is null**
6. Decodes with `new TextDecoder()`
7. Reads chunks in a `while(true)` loop: `reader.read()` → `decoder.decode(value, { stream: true })`
8. Splits buffer on `\n`, processes lines starting with `data: `, strips prefix, JSON-parses
9. Dispatches by `event.type`:
   - `chunk` → `fullContent += event.data ?? ''`; `appendStreamingContent(event.data ?? '')`
   - `safety` / `safety_override` → `setSafetyActive(true)`; zeroes `fullContent`; clears `streamingContent` via `useStore.getState().setStreamingContent('')`
   - `done` → appends final assistant `Message` to store; calls `resetStreaming()`; `setSafetyActive(false)`
   - `error` → `throw new Error('Stream error from server')` (**`persona_voice` discarded**)
   - `start` → no case; silently ignored
10. On any catch: calls `resetStreaming()`
    - If `err.status === 429`: shows toast with upgrade CTA; reads `err.detail.plan` for plan level
    - Else: shows generic toast

**State reads:** `activeConversationId`, `streamingContent`, `safetyActive`  
**State writes:** `appendMessage`, `setStreaming`, `appendStreamingContent`, `resetStreaming`, `setSafetyActive`, `setStreamingContent` (via `useStore.getState()` escape hatch in safety branch)  
**Public API:** `{ send }` — called by chat UI with the user's message text

---

### 1.3 `store.ts` — `apps/web/lib/store.ts`

**Streaming-relevant state:**

| State key | Type | Purpose |
|---|---|---|
| `activeConversationId` | `string \| null` | Which conversation is active |
| `messages` | `Message[]` | Full message list for active conversation |
| `isStreaming` | `boolean` | True while SSE stream is in flight |
| `streamingContent` | `string` | Accumulated chunk text during streaming |
| `safetyActive` | `boolean` | Set when `safety` or `safety_override` event received |

**Actions:** `appendMessage`, `setMessages`, `updateLastAssistantMessage`, `setStreaming`, `appendStreamingContent`, `resetStreaming` (sets `isStreaming: false`, `streamingContent: ''`), `setSafetyActive`

**Persistence:** Only `user`, `token`, `subscription` are persisted to `localStorage`. All streaming state, messages, and `activeConversationId` reset on page reload.

**`setActiveConversation` side effect:** Resets `messages: []` and `streamingContent: ''` when the active conversation changes — useful but means previous conversation messages are lost on navigation without a refetch.

---

## Section 2 — Actual SSE event shapes from the backend

Source: `apps/api/services/conversation_service.py` `stream_response()` method. These are the authoritative shapes for TypeScript type definitions.

### Stream sequence patterns

There are four distinct emission patterns depending on which code path is taken:

**Pattern A — Normal (no safety trigger, LLM succeeds):**
```
start → [chunk, chunk, ...] → done (with message_id)
```

**Pattern B — Pre-generation safety (user input triggered):**
```
safety → [chunk, chunk, ...] → done (NO message_id, NO start)
```

**Pattern C — Post-generation safety (LLM output triggered):**
```
start → safety_override → [chunk, chunk, ...] → done (with message_id)
```

**Pattern D — LLM failure (after 3 retry attempts):**
```
start → error  (stream ends; no done)
```

### Event shapes (TypeScript)

```typescript
// Emitted at start of normal and post-generation paths (NOT pre-generation safety)
type SSEEventStart = { type: "start" }

// chunk.data field name — NOT chunk.text (brief C5a divergence documented here)
type SSEEventChunk = { type: "chunk"; data: string }

// done includes message_id in normal + post-generation safety paths;
// omits message_id in pre-generation safety path (Pattern B)
type SSEEventDone = { type: "done"; message_id?: string }

// Pre-generation safety trigger
type SSEEventSafety = { type: "safety"; level: string }

// Post-generation safety trigger
type SSEEventSafetyOverride = { type: "safety_override"; level: string }

// LLM unavailable after 3 retry attempts
type SSEEventError = {
  type: "error"
  error_code: "llm_unavailable"
  persona_voice: string
}

type SSEEvent =
  | SSEEventStart
  | SSEEventChunk
  | SSEEventDone
  | SSEEventSafety
  | SSEEventSafetyOverride
  | SSEEventError
```

### HTTP 429 response (before stream opens)

The 429 is a `JSONResponse` (not SSE) with body matching `LLMErrorResponse`:

```typescript
interface LLMErrorResponse {
  error_code: "rate_limited"   // note: "rate_limited", not "llm_unavailable"
  persona_voice: string        // persona-voiced rate limit message
}
```

Headers present on 429:
- `X-RateLimit-Limit: <string>` — daily message limit for tier
- `X-RateLimit-Remaining: "0"` — always 0 on 429 (limit already exceeded)
- `X-RateLimit-Reset: <ISO 8601 UTC>` — when the limit resets

**Note:** `X-RateLimit-*` headers are also present on successful 2xx responses (non-admin, non-ritual conversations), showing remaining messages before the next limit.

### Chunk size

Chunks are produced by `_chunk_text(text, size=20)` — 20-character slices of the full buffered response. The LLM call is fully buffered before any chunks are yielded (see line 230-232: `_buf.append(chunk)` then `full_response = "".join(_buf)`). There is **no true real-time streaming** today — all chunks are yielded after the complete response is generated. This is intentional (enables retry + postprocessing before sending to client).

---

## Section 3 — C5 requirements coverage matrix

| Requirement | Existing support? | Gap |
|---|---|---|
| Stream message chunks into UI | **YES** — `useStream.tsx` handles `chunk` events, accumulates `streamingContent` | None |
| Render `error` event with `persona_voice` italic + Bronze + retry | **NO** — `error` case throws generic `Error`, discards `persona_voice` | Missing: surface `persona_voice` from error event to UI; italic + Bronze styling; retry affordance |
| Render `safety` / `safety_override` events visually | **PARTIAL** — sets `safetyActive: true` and clears `streamingContent`, but no chat UI exists to render any indicator | Missing: chat UI itself; per-spec visual treatment of safety events |
| Surface HTTP 429 to UI as paywall trigger | **PARTIAL** — shows toast with upgrade link to `/app/billing` | Missing: structured paywall UI with limit context and reset timer; reads wrong field from error body (see Risk §6.2) |
| Expose `X-RateLimit-Reset` to UI for paywall reset time | **NO** — `streamMessage()` does not parse any `X-RateLimit-*` headers | Missing: header parsing in `streamMessage()`; typed `RateLimitError` class; reset time display in paywall |
| Render `opening_invocation` as first UI message (not persisted) | **NO** — no chat page exists | Missing: entire chat UI; `opening_invocation` is available on the `Persona` type already returned by `getPersonas()` |
| Conversation list with title refresh after auto-title | **NO** — no conversation list UI; no polling/refresh mechanism | Missing: conversation list component; title polling or WebSocket push (auto-title is async via ARQ after message 3) |
| AbortSignal / cancellation on navigation | **NO** — `useStream.tsx` has no cleanup, no `AbortController` | Missing: abort wiring in `useStream`; tie to component unmount or navigation event |

**Summary:** The streaming data pipeline (HTTP → SSE parse → store) is functionally present for the happy path. All rendering, error surfacing, paywall display, and the chat UI itself are missing.

---

## Section 4 — Existing UI surface

### Chat-adjacent pages

| File | Route | Purpose |
|---|---|---|
| `apps/web/app/app/persona/[slug]/page.tsx` | `/app/persona/[slug]` | Persona detail (bio, portrait, locked/unlocked CTA) |
| `apps/web/app/app/explore/page.tsx` | `/app/explore` | (not read for this audit) |
| `apps/web/app/app/welcome/page.tsx` | `/app/welcome` | (not read for this audit) |

### Dead route

The persona detail page has a "Begin conversation" button that routes to `/app/chat/${persona.slug}`. **This route does not exist.** No file at `apps/web/app/app/chat/` has been created. Any user clicking "Begin conversation" hits a Next.js 404.

### `useStream.tsx` wiring status

`useStream.tsx` is **defined but not imported by any existing UI component**. It is an orphaned hook. The grep for `useStream` in `apps/web/` returns only the hook's own definition file.

### Existing components

Only three UI components exist in `apps/web/components/ui/`:
- `QueryProvider.tsx`
- `BronzeDivider.tsx`
- `Spinner.tsx`

No chat-specific components exist (no `MessageBubble`, no `ChatInput`, no `MessageList`).

### Test infrastructure

**No test runner exists.** No `vitest.config.*`, no `jest.config.*`, no `.spec.` or `.test.` files anywhere in `apps/web/`. Any C5 sub-task that requires tests will need to set up vitest from scratch as a prerequisite step.

---

## Section 5 — Recommended C5a–e plan

### What's already done (do not duplicate)

- `api.streamMessage()` — thin HTTP layer, returns raw `Response`. Keep and extend.
- `useStream.tsx` — SSE parsing loop. Keep, fix specific bugs (see §6).
- `store.ts` — correct state shape for chat. No changes needed to streaming state keys.
- `Persona` type in `api.ts` — already includes `opening_invocation: string | null`.
- `createConversation(persona_slug, ritual_id?)` — already exists on `api`.

### Revised C5a

**Original C5a brief** proposed a new `sendMessage()` function that would duplicate `streamMessage()` + the SSE parsing in `useStream.tsx`. Investigation shows this creates a parallel implementation.

**Recommended C5a instead:**
1. Add TypeScript SSE event types to `api.ts` (exported discriminated union using actual backend field names — `data` not `text` for chunks)
2. Add `RateLimitError` class that parses `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers from the 429 response
3. Fix `streamMessage()` to throw `RateLimitError` instead of the current ad-hoc augmented Error
4. Fix `useStream.tsx` `error` case to capture and surface `persona_voice` (store it in a new `streamError` state key, or pass via a callback — design decision for C5b)
5. Set up vitest + `@testing-library/react` as a zero-test baseline (required before any test authoring)
6. Write the 5 unit tests from the original brief against the fixed `streamMessage()` / error parsing layer

**No new streaming function required.** The architecture is: `api.streamMessage()` (HTTP) → `useStream.tsx` (parse + state) → store (render source of truth).

### Revised C5b

Build the chat screen at `/app/chat/[slug]`. Responsibilities:
- On mount: call `createConversation(slug)` → get `conversation.id`, set `activeConversationId`
- Show `persona.opening_invocation` as the first visual message (not a DB message)
- Render `messages` from store as message bubbles
- Render `streamingContent` as an in-progress bubble while `isStreaming === true`
- Input box + send button; calls `useStream.send(content)` on submit
- On `safetyActive === true`: render safety copy in the streaming bubble with appropriate styling

### Revised C5c

Error state rendering. Requires C5a's `error` event fix to be in place:
- Render `persona_voice` text in italic, Bronze `#B89968` at ~60% opacity
- Include retry affordance ("Try again" button) that re-calls `send()` with the last user message
- Error is a transient UI state only — do NOT persist to `messages` in store

### Revised C5d

Paywall UI. Requires C5a's `RateLimitError` to be in place:
- Intercept `RateLimitError` thrown by `streamMessage()` in `useStream.tsx`
- Show paywall modal/sheet with: current limit, reset time (from `resetAt`), upgrade CTA
- Replace current toast-only handling

### Revised C5e

Conversation list / navigation:
- List endpoint already exists: `GET /api/v1/conversations` → `getConversations()`
- Auto-title is async (ARQ job fires after message 3) — implement a polling refetch (e.g., poll `getConversations()` every 5s for 30s after message 3 is sent, stop when title appears)
- Conversation switching: `setActiveConversation(id)` clears messages; fetch `getMessages(id)` to load history

---

## Section 6 — Risk flags

### RF-01 — `error` event `persona_voice` is discarded (behavioral bug, not a gap)

**Severity: High** — affects production behavior today  
**Location:** `apps/web/lib/useStream.tsx:84`  
```typescript
case 'error':
  throw new Error('Stream error from server')  // persona_voice lost here
```
When the LLM is unavailable after 3 retries, the backend sends a persona-voiced error message (e.g., Socrates' persona-specific words for "I cannot think right now"). The frontend discards this and shows a generic toast. The product requirement is to show the persona-voiced text. **Fix required in C5a or before.**

### RF-02 — 429 error object reads a field that doesn't exist

**Severity: High** — affects production behavior today  
**Location:** `apps/web/lib/useStream.tsx:91`; `apps/web/lib/api.ts:248`  
`streamMessage()` builds the augmented error as:
```typescript
err.detail = body.detail   // but LLMErrorResponse has no .detail field
```
`LLMErrorResponse` has `{ error_code, persona_voice }` — no `detail` field. So `err.detail` is always `undefined`.

Then `useStream.tsx` reads:
```typescript
const plan: string = err?.detail?.plan ?? 'free'  // always undefined.plan → 'free'
const upgradeTarget = plan === 'pro' ? 'Premium' : 'Pro'  // always 'Pro'
```
The upgrade prompt always says "Upgrade to Pro →" regardless of whether the user is already on Pro and needs to upgrade to Premium. This is wrong for Pro users who hit their premium limit.

**Rate limit headers (`X-RateLimit-*`) are also never read.** The reset time is unavailable to the UI.

### RF-03 — `start` event silently ignored

**Severity: Low** — no current impact  
**Location:** `apps/web/lib/useStream.tsx:59` (switch statement has no `case 'start':`)  
Not a bug today, but blocks any "connection established" UX affordance (e.g., showing a thinking indicator only after the connection opens rather than immediately on submit). Non-blocking for C5.

### RF-04 — Pre-generation safety path emits no `start` event

**Severity: Low** — potential UX inconsistency  
**Location:** `apps/api/services/conversation_service.py:139-150`  
In Pattern B (pre-generation safety trigger), the stream starts immediately with `safety` — no `start` event is emitted. The current `useStream.tsx` doesn't use `start` anyway, so this is invisible today. If C5b adds a "thinking…" indicator triggered by `start`, this path will never show it — the safety response will appear to arrive instantaneously with no loading state.

### RF-05 — `done` without `message_id` in safety pre-generation path

**Severity: Low** — minor data inconsistency  
**Location:** `apps/api/services/conversation_service.py:149` vs `379`  
In Pattern B, `done` is emitted without `message_id`. `useStream.tsx` falls back to `crypto.randomUUID()`, so the in-memory `Message` object gets a random ID that does not correspond to any DB row. If any future feature references the message ID (reactions, delete, report), this path will produce broken references for safety-suppressed responses.

### RF-06 — No `AbortController` wiring — stream runs after navigation

**Severity: Medium** — affects mobile in particular  
**Location:** `apps/web/lib/useStream.tsx` (no cleanup)  
If a user taps "Begin conversation", a stream starts, and then navigates back before it finishes, the `read()` loop continues running in the background. Store mutations (`appendStreamingContent`, `appendMessage`, `resetStreaming`) will fire against whatever conversation is now active. On low-end mobile with a slow LLM response, this is a real race condition. **Fix required in C5a or C5b.**

### RF-07 — `res.body!.getReader()` non-null assertion

**Severity: Low** — theoretical only  
**Location:** `apps/web/lib/useStream.tsx:34`  
`res.body` can be `null` in some environments (e.g., certain service workers, or if fetch is called with `{ body: null }`). The `!` assertion will cause an unhandled runtime TypeError if `body` is null. In practice, the backend always returns a stream body on 2xx, so this is a theoretical concern. A defensive `if (!res.body) throw new Error(...)` is easy to add.

### RF-08 — No test infrastructure anywhere in `apps/web/`

**Severity: Medium** — blocks test authoring for all C5 sub-tasks  
No test runner is configured. Any brief that requires tests (including the original C5a brief's 5-test requirement) cannot be executed without first adding vitest + test dependencies. This is a one-PR setup cost that should be the first step of C5a.

---

*End of audit. All findings based on direct code reads as of 2026-05-17.*
