# HANDOFF BRIEF v9 — Philosopher / Great Minds

**For:** The next Claude (chat) and Claude Code session
**From:** Nikos Koutras (founder) + Claude Code
**Date updated:** 2026-05-17
**Prior version:** `docs/HANDOFF_BRIEF_v8.md` (2026-05-13/14)
**Generated:** 2026-05-16 (post-reconciliation); updated 2026-05-17 (C5d + C3a session)

**Block trigger for v9 baseline regen:** Block C backend complete (8/8 items shipped or reconciled). Single canonical send-message endpoint confirmed. PATH B fully deleted. Per §8.17 (addendum vs baseline regen rule): Block C backend closure is a sufficient regen trigger.

**Status:** Block A ✅ FULLY CLOSED (5/5). Block B ✅ SPINE SHIPPED (6/6 functional, polish PR pending). Block C backend ✅ COMPLETE (all features live in PATH A SSE streaming endpoint; PATH B deleted). Block C frontend ✅ COMPLETE (C5a/b/c/d all merged 2026-05-16/17). C3a RAG infrastructure ✅ COMPLETE (migration 008 live). **Next: C3b corpus ingestion operational run (founder action via Render shell).**

> **v9 conflict resolution rule:** Where v9 conflicts with v8 or earlier, v9 wins. Production reality always wins over docs.

---

## Changelog v8 → v9

### 2026-05-16 session — Block C backend + Reconciliation series

**10 PRs merged on 2026-05-16.**

The session split into two phases:

**Phase 1 — Block C initial build (C1, C2, C4, C8):**
- C1 (#50): Schema additions — `conversations.deleted_at`, `messages.model_used`, `daily_usage` table; alembic migration 007
- C2 (#51): `services/llm_service.py` — non-streaming LLM service with tier routing, retry logic, LLMResponse dataclass
- C4 (#52): `routers/messages.py` — `POST /api/v1/messages` non-streaming endpoint with rate limit, auto-title, persona errors
- C8 (#53): Per-persona daily rate limit (5 messages/persona/UTC day for free users)

**Phase 2 — Reconciliation (C-RECON-1 through C-RECON-8):**
C-RECON-1 audit discovered that C2/C4/C8 had built a parallel PATH B alongside the existing feature-rich PATH A streaming endpoint. PATH A was adopted as canonical; 7 reconciliation PRs ported PATH B's features into PATH A and deleted PATH B.

| PR | Description |
|---|---|
| CLAUDE.md (#54) | Pre-Work Investigation Protocol added to repo |
| C-RECON-3 (#55) | Tier-aware model + memory window ported into PATH A |
| C-RECON-4 (#56) | Per-persona rate limit + daily_usage increment ported into PATH A |
| C-RECON-5 (#57) | Auto-title ARQ task wired into PATH A |
| C-RECON-6 (#58) | LLM retry logic + persona-voiced errors ported into PATH A |
| C-RECON-7 (#59) | Memory extraction ARQ task wired into PATH A |
| C-RECON-8 (#60) | PATH B deleted (routers/messages.py, services/llm_service.py, 4 test files, 4 schema classes) |

**Net effect:** 10 architectural decisions locked; 229 tests passing (down from 275 peak — 46 PATH B tests removed); single canonical send-message endpoint confirmed.

### 2026-05-16/17 session — Block C frontend (C5d) + C3a RAG infrastructure

**C5d (#65) — Conversation list (F6) + existing conv route + tab bar:**
- 1128 lines, 13 files, 13 new frontend tests
- Completes Block C frontend: C5a/b/c/d all merged. 43 total frontend tests.

**C3a — HNSW vector indexes + ingestion pipeline + curated chunks recovery:**
- Migration 008 (`008_hnsw_vector_indexes`): HNSW indexes on `source_chunks.embedding` + `memory_entries.embedding`; `chunk_index INTEGER nullable` added to `source_chunks`
- New scripts committed to `apps/api/scripts/`: `chunking.py` (pure tiktoken, 512 tokens/50 overlap), `corpus_sources.py` (13 Gutenberg URLs across 7 personas), `curated_chunks.py` (19 Marcus Aurelius curated chunks), `ingest_corpus.py` (CLI with `--dry-run` + `--persona` flags)
- 63 new backend tests; 292 total backend tests
- CLAUDE.md Rule 5 violation: `apps/api/db/ingest_sources.py` (408 lines) silently deleted during C3a; reconciled via Path C — recovery commit `f78d0f3` restored 19 Marcus Aurelius curated chunks as `curated_chunks.py` with Strategy A disambiguation
- Migration verified live on Render via Supabase MCP queries (alembic_version = `008_hnsw_vector_indexes` confirmed)
- pgvector version verified: 0.8.0 (HNSW supported from 0.5.0+)

---

## 1. Pre-Work Investigation Protocol

**This protocol is mandatory for all future multi-PR work on this project.**

The protocol is defined in `CLAUDE.md` at the repository root (committed PR #54, 2026-05-16). Every new code session that adds, modifies, or extends a feature must:

1. Enumerate all existing functionality in the same domain before writing any code
2. Read the actual source files — not rely on session memory or doc summaries
3. Report findings and stop for founder review if overlaps are found
4. Check cross-system dependencies (ARQ tasks, webhooks, admin endpoints, tests, frontend)

**Why this exists:** On 2026-05-16, C4 built a complete non-streaming message endpoint that duplicated PATH A's streaming infrastructure. C-RECON-1 caught this via openapi.json inspection. Cost: ~3 hours of duplicate work + a rate-limit security hole (PATH A had no rate limit until C-RECON-4). The protocol prevents recurrence.

### What the protocol caught during reconciliation

Four real bugs were avoided by reading actual code before porting:

1. **PATH A SQL-level UPDATE for `message_count`** (C-RECON-5): PATH A uses a raw `UPDATE conversations SET message_count = message_count + 2` after each exchange, not an ORM attribute. The auto-title trigger condition (`message_count == 0`) must be read from the DB row BEFORE the UPDATE fires, or it would never match. A naive port would have wired the title task to fire on every message.

2. **`extract_memory_task` requires 7 arguments** (C-RECON-7): The ARQ task signature takes `ctx, conversation_id, user_id, persona_id, user_text, assistant_text, user_name`. A guess-based port with 2 positional args would have produced silent ARQ task failures that never surface as errors in the SSE stream.

3. **`PersonaConfig` has no `.config` attribute** (C-RECON-6): The in-memory `PersonaConfig` dataclass from `personas/_base.py` does not have a `.config` dict. `get_error_voice()` must receive the ORM `Persona` object (which has `.config` as a JSONB dict) — not the in-memory dataclass. The streaming path correctly loads the ORM object from DB; the confusion was only a documentation/naming risk, but the investigation made it explicit.

4. **`ANTHROPIC_MODEL` in `config.py` is stale** (C-RECON-2): `config.ANTHROPIC_MODEL` defaults to `"claude-sonnet-4-20250514"` (old Sonnet 4). `conversation_service.py` does NOT read this constant — it uses `MODEL_FREE`/`MODEL_PRO` constants defined directly in the service file. Identified before it could mislead anyone into thinking the config constant controlled which model was being served.

---

## 2. Current architecture

### The single canonical chat flow

```
Frontend (Next.js)
  │
  ├─ POST /api/v1/conversations             → create conversation (returns conv_id)
  │
  └─ POST /api/v1/conversations/{id}/messages  → send message (SSE stream)
       │
       ▼
  routers/conversations.py — send_message()
       │
       ├─ Ownership check (SELECT WHERE user_id = auth user)
       ├─ Admin bypass: is_admin → skip rate limit
       ├─ Ritual exemption: ritual_id IS NOT NULL → skip rate limit
       ├─ rate_limit_service.check_rate_limit() → daily_usage table
       │   • free: 5/persona/UTC day; pro: unlimited
       │   • 429 → JSONResponse with LLMErrorResponse + persona-voiced message
       ├─ SSE headers (X-RateLimit-Limit/Remaining/Reset)
       │
       └─ StreamingResponse(conversation_service.stream_response(...))
             │
             ├─ safety_service.check_input()       → suppress or log SafetyEvent
             ├─ retrieval_service.retrieve()        → RAG source chunks (if corpus)
             ├─ memory_service.retrieve()           → memory entries
             ├─ phenomenology_bridge_service        → enrichment (if flag=true)
             ├─ prompt_builder.build_system()       → system prompt assembly
             ├─ SELECT messages LIMIT MEMORY_WINDOW → history (5 free / 20 pro)
             ├─ _save_message(user)
             ├─ yield "start" SSE event
             ├─ llm_client.stream()                 → Anthropic SSE
             │   • model: Haiku (free) / Sonnet (pro/premium)
             │   • retry: 3 attempts, exponential backoff (0s, 2s, 4s)
             │   • on final failure: yield "error" SSE event with persona voice
             ├─ safety_service.check_output()       → suppress or postprocess
             ├─ regenerate_or_trim()                → postprocessing (if enabled)
             ├─ _save_message(assistant, model_used=...)
             ├─ UPDATE conversations SET message_count+=2, last_message_at=now
             ├─ UPDATE daily_usage SET message_count+=1   (free users only)
             ├─ arq_queue.enqueue(generate_conversation_title)  (if msg_count==0)
             └─ arq_queue.enqueue(extract_memory_task)
```

### SSE event types emitted

| Event type | When | Payload |
|---|---|---|
| `start` | Before first token | `{type: "start"}` |
| `chunk` | Each token streamed | `{type: "chunk", text: "..."}` |
| `done` | Stream complete | `{type: "done"}` |
| `safety` | Input safety suppressed | `{type: "safety", level: "..."}` |
| `safety_override` | Output safety suppressed | `{type: "safety_override", level: "..."}` |
| `error` | LLM unavailable after retries | `{type: "error", error_code: "llm_unavailable", persona_voice: "..."}` |

### Key service files

| File | Responsibility |
|---|---|
| `routers/conversations.py` | Router layer: auth, rate limit, ritual/admin bypass, SSE headers, StreamingResponse |
| `services/conversation_service.py` | `stream_response()` generator; also `create()` for new conversations |
| `services/rate_limit_service.py` | Two distinct rate limiters in one file: Redis/OTP (auth flows) + DB/daily (message limits) |
| `services/persona_voice.py` | `get_error_voice(persona_orm_object, error_code)` — reads from `persona.config` dict |
| `services/tier_service.py` | `get_user_tier(db, user_id)` — reads `subscriptions` table |
| `services/llm_client.py` | Streaming Anthropic client (PATH A's LLM layer; preserved through reconciliation) |
| `workers/arq_worker.py` | ARQ task definitions: `generate_conversation_title`, `extract_memory_task` |

### Constants — where they live now

After C-RECON-8 deleted `services/llm_service.py`, the model and memory window constants were relocated:

```python
# apps/api/services/conversation_service.py (lines 28-31)
MODEL_FREE = "claude-haiku-4-5-20251001"
MODEL_PRO = "claude-sonnet-4-6"
MEMORY_WINDOW_FREE = 5
MEMORY_WINDOW_PRO = 20
```

`tests/services/test_conversation_service.py` imports these directly from `conversation_service`.

### What PATH B was and is no longer

PATH B (`POST /api/v1/messages`, `services/llm_service.py`, `schemas.MessageCreateRequest/MessageResponse/MessageEnvelope/ConversationSummary`) was the non-streaming endpoint built in C2/C4. It has been entirely deleted. Do not reference any of these in new code or docs. The canonical endpoint is `POST /api/v1/conversations/{id}/messages`.

---

## 3. Test infrastructure

### Current state

```
292 backend tests passing (as of C3a, 2026-05-17)
43 frontend tests passing (as of C5d, 2026-05-17)
0 failures
```

Test count history:
- Pre-Block-C: 146 backend tests
- After C1 (19 new schema tests): 165
- After C2/C4/C8 (PATH B tests added): ~275 peak
- After C-RECON-8 (46 PATH B tests deleted): 229 backend
- After C5a/b/c/d: 43 frontend tests total
- After C3a (63 new backend tests): **292 backend tests**

### Test file layout (apps/api/tests/)

```
conftest.py                           — app-level fixtures
routers/
  conftest.py                         — router-level fixtures (TestClient, mock deps)
  test_conversations.py               — PATH A streaming endpoint tests
services/
  conftest.py                         — service-level fixtures
  test_conversation_service.py        — tier routing, model selection, memory window
  test_tier_service.py                — get_user_tier() logic
  test_rate_limit_service.py          — both OTP and message rate limit logic
db/
  conftest.py                         — DB fixtures
  test_block_c_schema.py              — migration 007 schema verification
scripts/                              (NEW — C3a)
  conftest.py                         — script-level fixtures (mock DB session, mock OpenAI)
  test_chunking.py                    — tiktoken chunking logic
  test_corpus_sources.py              — Gutenberg URL list + persona mapping
  test_ingest_corpus.py               — ingestion pipeline end-to-end (mocked)
```

### Test scaffolding patterns

**For router tests** (`test_conversations.py`):
- `TestClient` from `fastapi.testclient`
- Auth dependencies overridden via `app.dependency_overrides`
- `arq_queue` mocked via `app.state.arq_queue = AsyncMock()` in conftest
- LLM streaming mocked at `llm_client.stream` level (not Anthropic SDK directly)
- Rate limit service mocked for routing tests that don't want rate-limit side effects

**For service tests** (`test_conversation_service.py`):
- All external I/O mocked: `AsyncMock` for `llm_client.stream`, `safety_service`, `retrieval_service`, `memory_service`, `arq_queue`
- DB session mocked with controlled return values
- Constants imported directly from `conversation_service`: `MODEL_FREE, MODEL_PRO, MEMORY_WINDOW_FREE, MEMORY_WINDOW_PRO`
- Tests verify model selection by inspecting call kwargs passed to `llm_client.stream()`
- Tests verify memory window by inspecting the `.limit()` clause in SQL SELECT calls

**For rate limit tests** (`test_rate_limit_service.py`):
- Tests both Redis-backed OTP section and DB-backed message section
- DB session mocked with `DailyUsage` objects at different `message_count` values
- Tests verify free/pro tier branching and `RateLimitResult` fields

---

## 4. Known limitations and not-yet-wired features

These are known gaps that exist in the current production code. Document them before writing any C5 brief so the frontend implementation makes the right assumptions.

### 4.1 Persona-voiced error messages — wired in SSE, not yet rendered in frontend

All 9 persona-voiced error messages for `llm_unavailable` are stored in `personas.config` JSONB and ARE returned by the API as SSE `type:error` events with `persona_voice` field. However:

- The frontend (C5) does not yet exist, so nothing renders them
- The SSE error event must be handled in the frontend streaming parser
- The messages should render as italic + muted color (Bronze #B89968 at ~60% opacity) + retry affordance
- They should NOT be persisted to message history

### 4.2 PersonaConfig / Persona ORM naming confusion

`personas/_base.py` defines a `PersonaConfig` dataclass (the in-memory character config). The SQLAlchemy ORM model in `models/__init__.py` is named `Persona`. These are different objects.

`get_error_voice(persona, error_code)` in `services/persona_voice.py` works by calling `getattr(persona, "config", None)` — which works on the ORM `Persona` object (whose `.config` is a JSONB dict) but would return `None` for a `PersonaConfig` dataclass (which has no `.config` attribute).

Current code correctly passes the ORM `Persona` object in the streaming path. This is not a production bug today, but the naming confusion is a future maintenance risk. See tech debt item TD-02.

### 4.3 Safety architecture — 2 layers live, 3rd layer deferred

Current production: regex input check + regex output check. The third layer (LLM-based classifier on trigger phrases) was deferred from Decision #6. Cost estimate when fully implemented: ~$0.012/Pro user/month. Not a launch blocker.

### 4.4 generate_insight_task — defined but not triggered

`workers/arq_worker.py` defines `generate_insight_task`. It is NOT enqueued anywhere in the current streaming path. `extract_memory_task` IS wired (dispatched after each response), but insight generation from accumulated memory entries is a separate downstream step that is still disconnected. Will matter once real users accumulate memory entries.

### 4.5 RAG corpus — schema ready, corpus not ingested

The pgvector infrastructure (table `source_chunks`, `vector(1536)` column, `retrieval_service.py`) is live. `retrieval_service.retrieve()` is called in the streaming path. However, no corpus has been ingested yet, so it returns empty results on every call (fail-open — the stream continues with no retrieval context). The copyright-cleared source list is defined in IMPLEMENTATION_BACKLOG_v9.md C3 spec.

### 4.6 ANTHROPIC_MODEL constant is orphaned

`config.py` has `ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"` (old Sonnet 4). This constant is NOT read by `conversation_service.py`, which uses `MODEL_FREE`/`MODEL_PRO` literals directly. The constant is a misleading artifact. Update to current model IDs or remove before it causes confusion.

### 4.7 Render alembic auto-run mechanism undocumented

Alembic runs `upgrade head` on Render container startup. The exact mechanism (Procfile? Dockerfile CMD? render.yaml?) is undocumented. It has worked reliably through 007 migrations. Document before the next engineer touches the deployment.

---

## 5. Next session entry point

**Priority order for next session:**

1. ~~**C5 — Chat UI frontend**~~ **DONE** (C5a/b/c/d merged 2026-05-16/17)

2. **C3b — Corpus ingestion operational run** (P0, immediate — founder action)
   - Verify `OPENAI_API_KEY` set in Render env (Render dashboard → service `srv-d7ijct6gvqtc739a0pdg` → Environment)
   - Run via Render shell: `python -m apps.api.scripts.ingest_corpus`
   - Verify via Supabase SQL: `SELECT persona_id, source_title, COUNT(*) FROM source_chunks GROUP BY 1, 2 ORDER BY 1, 2`
   - Cost: <$0.02. Duration: 2-5 minutes. See §14b for full runbook.

3. **Block B consolidated polish PR** (P0 — blocked on DNS/Resend confirmation)
   - 9 mobile walkthrough findings (see v8 §6 BUG-001 through BUG-009)
   - DNS + Resend domain verification must be confirmed before starting

4. **Landing page waitlist test** (founder-owned, ~2 hours build)
   - Validates $14.99 price point before Stripe wiring
   - Pauses Stripe work until 10-day data period completes

5. **Pre-launch items** (lawyer review, DNS, GDPR/DPA, runbooks)

**Do not start Block D / Block F / Block H / Block I** until polish PR is merged and verified on mobile.

---

## 6. C5 — Chat UI spec requirements

These requirements were established during the 2026-05-16 session. They are the source of truth for the C5 frontend brief.

### API integration

```
// New conversation flow (2 API calls on first message):
const conv = await POST /api/v1/conversations { persona_slug: "socrates" }
const stream = await POST /api/v1/conversations/{conv.id}/messages { content: "..." }

// Subsequent messages in same conversation:
const stream = await POST /api/v1/conversations/{conv.id}/messages { content: "..." }
```

The frontend should NOT create a new conversation for every message. Conversation state (ID) must be persisted in component state or a store after the first creation call.

### SSE streaming parser

```javascript
// Rough implementation guidance
const source = new EventSource(url)  // or fetch with ReadableStream
source.onmessage = (event) => {
  const data = JSON.parse(event.data)
  switch (data.type) {
    case "start":    // clear any previous pending state
    case "chunk":    // append data.text to the current assistant message bubble
    case "done":     // finalize the assistant message
    case "safety":   // show safety response instead of persona voice
    case "safety_override": // replace streamed content with safety response
    case "error":    // show error UI with data.persona_voice (see below)
  }
}
```

### Error message rendering

When the frontend receives `type: "error"` with `error_code: "llm_unavailable"`:

- Display the `persona_voice` text in **italic**, **muted color** (Bronze `#B89968` at ~60% opacity)
- Show a **retry affordance** (e.g., "Try again" button or tap-to-retry gesture)
- Do **NOT** persist the error message to the conversation history
- The error message bubble should be visually distinct from both user and assistant message bubbles

### Rate limit (429) rendering

When the API returns HTTP 429 (rate limit hit before SSE stream starts):

- Show a **paywall UI** with an upgrade CTA
- Include remaining limit context if available from `X-RateLimit-Remaining` header (will be `0`)
- Include reset time from `X-RateLimit-Reset` header (ISO 8601 UTC midnight)

### Opening invocation

Each persona has an `opening_invocation` field in the API response from `GET /api/v1/conversations`. Display this as the first "message" in the chat UI before the user sends anything. It is NOT stored as a `messages` row in the DB — it is a UI affordance derived from persona config. Do not send it to the API.

### Conversation list

`GET /api/v1/conversations` returns a list of conversations ordered by `last_message_at DESC`, max 50. Each entry includes `title` (may be null until auto-title fires), `message_count`, `persona` slug + name.

---

## 7. Environmental configuration

### Backend (Render)

Current Render env vars and their status:

```
DATABASE_URL                    ✅ Set (Supabase pooler)
REDIS_URL                       ✅ Set (Upstash)
RESEND_API_KEY                  ✅ Set
FROM_EMAIL                      "Great Minds <onboarding@resend.dev>" — test sender
JWT_SECRET                      ✅ Set
ANTHROPIC_API_KEY               ✅ Set — actively used for chat
PHENOMENOLOGY_BRIDGE_ENABLED    ⚠️ State unverified (was true 2026-05-04/05)

ANTHROPIC_MODEL (config.py)     ⚠️ ORPHANED — not read by conversation_service.py
                                 Default: "claude-sonnet-4-20250514" (stale Sonnet 4)
                                 conversation_service.py uses MODEL_FREE/MODEL_PRO
                                 literals. Update or remove before next session
                                 to avoid misleading future Claude instances.

ANTHROPIC_MEMORY_MODEL          "claude-haiku-4-5-20251001" — set in config.py
                                 Used by: verify which service reads this
```

### Frontend (Netlify)

```
NEXT_PUBLIC_API_URL             (unset; api.ts falls back to philosopher-api-z9l9.onrender.com/api/v1)
NEXT_PUBLIC_SUPPORT_EMAIL       nckoutras@gmail.com (placeholder)
```

---

## 8. Key file paths (production codebase)

### Backend (apps/api/)

**Active files:**

- `main.py` — FastAPI app + router mounting. `messages_router` import and `include_router` REMOVED in C-RECON-8.
- `models/__init__.py` — all SQLAlchemy ORM models: User, Subscription, Conversation, Message, DailyUsage, SafetyEvent, Persona, MemoryEntry, SourceChunk, etc.
- `schemas/__init__.py` — all Pydantic schemas. PATH B schemas removed (MessageCreateRequest, MessageResponse, MessageEnvelope, ConversationSummary). LLMErrorResponse kept (used by PATH A).
- `routers/conversations.py` — all conversation endpoints. Rate limit wired here. Admin bypass here. Ritual exemption here.
- `services/conversation_service.py` — `ConversationService.stream_response()`. Contains MODEL_FREE, MODEL_PRO, MEMORY_WINDOW_FREE, MEMORY_WINDOW_PRO constants.
- `services/rate_limit_service.py` — two sections: `check_and_increment()` (Redis/OTP) + `check_rate_limit()` (DB/daily messages). Tech debt: split into two files.
- `services/persona_voice.py` — `get_error_voice(persona_orm, error_code)`. Reads `persona.config["error_messages"][error_code]`. Falls back to generic if not found.
- `services/tier_service.py` — `get_user_tier(db, user_id)`. Returns `"free"` or `"pro"`. Reads `subscriptions` table.
- `services/llm_client.py` — `llm_client.stream()`. Native Anthropic streaming client. PATH A's LLM layer.
- `services/safety_service.py` — 2-layer safety (regex input + output). Phase 4 infrastructure.
- `services/retrieval_service.py` — pgvector retrieval. Called on every message. Returns empty if corpus not ingested.
- `services/memory_service.py` — memory recall. Feeds into context; also writes via ARQ.
- `services/prompt_builder.py` — system prompt assembly.
- `workers/arq_worker.py` — ARQ task definitions: `generate_conversation_title`, `extract_memory_task`. Note: `generate_insight_task` defined but NOT triggered.
- `auth.py` — `get_current_user` + `get_current_user_plan` dependencies.
- `config.py` — Settings class. Note `ANTHROPIC_MODEL` orphan.
- `personas/_base.py` — `PersonaConfig` dataclass. NOT the same as ORM `Persona`. Has no `.config` attribute.
- `db/migrations/versions/` — alembic migrations 001–008.
- `db/migrations/versions/008_hnsw_vector_indexes.py` — HNSW indexes on source_chunks.embedding + memory_entries.embedding; chunk_index column on source_chunks.

**Scripts (NEW — C3a, apps/api/scripts/):**
- `scripts/README.md` — usage guide for ingestion pipeline
- `scripts/chunking.py` — pure tiktoken-based text chunker (512 tokens, 50-token overlap)
- `scripts/corpus_sources.py` — 13 Project Gutenberg URLs across 7 personas (Jung + Beauvoir excluded per Decision #7)
- `scripts/curated_chunks.py` — 19 hand-curated Marcus Aurelius chunks (Long 1862 PD, Book.Chapter refs; `source_title = "Meditations (curated)"`)
- `scripts/ingest_corpus.py` — one-shot CLI ingestion runner (`--dry-run`, `--persona` flags). Not an ARQ task.

**Script tests (NEW — C3a, apps/api/tests/scripts/):**
- `tests/scripts/conftest.py`
- `tests/scripts/test_chunking.py`
- `tests/scripts/test_corpus_sources.py`
- `tests/scripts/test_ingest_corpus.py`

**Deleted in C-RECON-8 (do not reference):**
- ~~`routers/messages.py`~~ (PR #60)
- ~~`services/llm_service.py`~~ (PR #60)
- ~~`tests/routers/test_messages.py`~~ (PR #60)
- ~~`tests/services/test_llm_service.py`~~ (PR #60)

### Frontend (apps/web/)

Unchanged from v8. See v8 §11 (specifically `lib/api.ts`, `lib/store.ts`, `app/app/` routes). C5 will add:

- `app/app/conversation/[id]/page.tsx` — chat screen (to be created)
- `lib/api.ts` — add `sendMessage(convId, content)` streaming method
- New components: message bubble, SSE parser hook, retry affordance

---

## 9. Decision history (v9 additions)

### 2026-05-16 — Block C initial build decisions

- C1: Schema additions approved (deleted_at for soft-delete, model_used for analytics, daily_usage for rate limiting)
- C2: Anthropic SDK chosen for LLM provider (not OpenAI); validates § 24.3 Decision 1 from v8
- C4: Non-streaming endpoint chosen for C4 "for velocity" — subsequently identified as creating PATH B duplication

### 2026-05-16 — Reconciliation decisions

All 10 locked decisions documented in PROJECT_STATE_v9.md §9. Key additions vs v8:

- **PATH A adopted as canonical** (vs PATH B). Rationale: PATH A has richer infrastructure (safety, RAG, memory, analytics) that would be expensive to rebuild in PATH B.
- **Rate limit: 5/persona/day** (confirmed from C8; not 10/day as v8 mentor recommended — 5 was shipped and validated as the right number for the per-persona model)
- **Ritual exemption** policy locked (Decision #9)
- **Admin bypass placement** locked in router, not service (Decision #10)
- **Pricing draft $14.99** locked pending landing page validation (Decision #8)

### Preserved from v8 (chronological summary)

See `HANDOFF_BRIEF_v8.md` §21 for complete decision history through 2026-05-13.

---

## 10. Section 5.7 framework — status

Updated from v8 §15.

All Section 5.7 infrastructure is **live in production** for all 9 personas. Block C builds chat runtime ON TOP of this framework — it is NOT rebuilding it.

| Element | Status |
|---|---|
| Character anchors (schema + data) | ✅ 9/9 personas |
| Brevity discipline (runtime) | ✅ check_brevity() active |
| Anti-flexing (enforcement) | ✅ 9/9 personas |
| Modern phenomenology bridge | ✅ Infrastructure live (PHENOMENOLOGY_BRIDGE_ENABLED flag state TBD) |
| Universal + persona-specific forbidden lexicon | ✅ Live via safety pipeline |
| Error message vocabulary | ✅ All 9 stored in DB; accessible via ORM Persona.config |
| Register architecture + UI chips | ⏳ P3 post-feedback |
| Eval suite + CI | ⏳ P1 post-revenue |
| LLM classifier (safety layer 3) | ⏳ Deferred from Decision #6 |

---

## 11. Migration plan — status

Updated from v8 §16.

**Phases 1-3** ✅ COMPLETE (PRs #7-12)
**Phase 4 — Modern phenomenology bridge** ✅ COMPLETE (PHENOMENOLOGY_BRIDGE_ENABLED flag to confirm in Render)
**Block A — Authentication** ✅ FULLY CLOSED 5/5
**Block B — Onboarding spine** ✅ SHIPPED 6/6 (polish PR pending visual closure)
**Block C — Chat backend** ✅ COMPLETE (PATH A has all features)
**Block C remaining** ⏳ C5 (UI) + C3 (RAG corpus) — both unstarted
**Phase 5 — Register architecture + UI chips** ⏳ P3 post-feedback
**Phase 6 — Eval suite + CI** ⏳ P1 post-revenue

---

## 12. Deployment readiness

Updated from v8 §20.

```
✅ Backend                Render web service philosopher-api
                          srv-d7ijct6gvqtc739a0pdg
                          philosopher-api-z9l9.onrender.com
                          ⚠️ Free tier; cold-start 30-60s after idle
                          ⚠️ Upgrade decision pending (~$7/mo)
                          Last deploy: 2026-05-16 C-RECON-8 (PR #60)

✅ Database               Supabase project plecolxlzshkfvybszgs (eu-west-1, paid)
                          alembic_version = '007_block_c_schema'
                          17+ public tables (+ daily_usage from 007)
                          RLS DISABLED on all
                          ⚠️ Mitigation: FastAPI gateway exclusive; no anon key on frontend

✅ Cache (Redis)          Upstash philosopher-prod (eu-west-1) free tier
                          OTP rate limiter VERIFIED WORKING 2026-05-10
                          Message rate limiter wired 2026-05-16 (C-RECON-4)

🟡 Email                  Resend free tier (test sender only)
                          ⚠️ Corporate domains block delivery (@ote.gr confirmed)
                          🟡 DNS + thegreatminds.app domain verification IN PROGRESS

✅ Frontend (canonical)   Netlify thinkalike.netlify.app
                          Auto-deploys from main

✅ LLM                    Anthropic API wired (ANTHROPIC_API_KEY set in Render)
                          Haiku 4.5 for free, Sonnet 4.6 for pro
                          Streaming + retry live

✅ Chat UI (C5)           COMPLETE — C5a/b/c/d merged 2026-05-16/17
✅ RAG infrastructure     COMPLETE — migration 008 live; HNSW indexes verified; 19 curated MA chunks loaded
⏳ RAG corpus (C3b)      Operational run READY — founder executes via Render shell; see §14b runbook
❌ Stripe                 Not wired — paused pending $14.99 landing page validation
🟡 DNS / thegreatminds.app IN PROGRESS
```

---

## 13. Session lessons (v9 additions)

### 13.1 Preserved from v7/v8 (§19.1-§19.17)

All prior lessons retained. Full text in `HANDOFF_BRIEF_v8.md` §19. Key rules:
- §19.14: Unicode JSONB encoding pre-merge check
- §19.15: Mobile walkthrough is non-substitutable
- §19.16: Read existing docs before writing replacement docs
- §19.17: Addendum vs baseline regen discipline

### 13.2 openapi.json is a verification artifact, not source (NEW v9 — 2026-05-16)

During reconciliation, `openapi.json` was generated locally to verify that PATH B's endpoint had been removed and only the PATH A endpoint remained. It is a manual test artifact. Do not commit it.

**Rule:** Never commit `openapi.json` unless it is explicitly declared as a build artifact for the project (it is not, currently). Use it for verification; discard or gitignore in a separate PR.

### 13.3 Reconciliation over deletion (NEW v9 — 2026-05-16)

When parallel implementations of the same feature are discovered, the default is NOT "delete the duplicate immediately." The correct sequence:

1. Investigation-only PR producing a comparison report (C-RECON-1, C-RECON-2)
2. Founder approves reconciliation strategy
3. Feature ports in order of risk (rate limit before auto-title; errors before memory)
4. Deletion only after all ports are verified (C-RECON-8 last)

Each step independently reviewed. This sequencing caught the 4 bugs listed in §1.

### 13.4 Test scaffolding for ARQ-dependent services (NEW v9 — 2026-05-16)

Testing functions that call `arq_queue.enqueue()` requires the queue to be available as `request.app.state.arq_queue`. In router tests:

```python
# conftest.py
app.state.arq_queue = AsyncMock()
```

In service tests for `stream_response()`, pass `arq_queue=AsyncMock()` directly as a parameter. The service does `if arq_queue is not None` — tests that pass `None` will skip the enqueue call cleanly.

---

## 14b. How to run C3b ingestion (operational runbook)

This is the next founder action. Not a coding task.

### Step 1 — Verify OPENAI_API_KEY in Render env

Render dashboard → service `srv-d7ijct6gvqtc739a0pdg` → Environment tab. Confirm `OPENAI_API_KEY` is set. If not, add it (model: `text-embedding-3-small` requires OpenAI key, not Anthropic).

### Step 2 — Open Render shell

Render dashboard → service → Shell tab. Working directory: `/opt/render/project/src`.

### Step 3 — Validate URLs without DB writes (recommended first run)

```bash
python -m apps.api.scripts.ingest_corpus --dry-run
```

### Step 4 — (Optional) Incremental test on one persona

```bash
python -m apps.api.scripts.ingest_corpus --persona marcus_aurelius
```

### Step 5 — Full ingestion

```bash
python -m apps.api.scripts.ingest_corpus
```

Expected duration: 2-5 minutes. Expected cost: <$0.02 (OpenAI `text-embedding-3-small`).

### Step 6 — Verify via Supabase SQL editor (or MCP)

```sql
SELECT persona_id, source_title, COUNT(*)
FROM source_chunks
GROUP BY persona_id, source_title
ORDER BY 1, 2;
```

**Expected outcome:**
- Marcus Aurelius: 19 curated chunks (`source_title = "Meditations (curated)"`) + N auto-chunked Long 1862 chunks (`source_title = "Meditations"`)
- Other 6 personas (Socrates, Lao Tzu, Machiavelli, Wilde, Epictetus, Freud): M auto-chunked chunks each
- Jung and Beauvoir: zero chunks (excluded per Decision #7)
- `retrieval_service.py` becomes functional automatically (currently fail-open; returns empty results)

---

## 14c. Lessons from 2026-05-17 session

### CLAUDE.md Rule 5 violation case study

The C3a implementation silently deleted `apps/api/db/ingest_sources.py` (408 lines) — a pre-existing ingestion script with 19 hand-curated Marcus Aurelius chunks. This violated Rule 5: surface parallel implementations for founder decision; never delete silently.

**Pattern to enforce in every brief:** Investigation Step 2 MUST include `grep -r "ingest\|chunk\|embed\|corpus" apps/api/` before any new ingestion or corpus work. Report findings in PR description before implementation.

### Investigation discipline catches real bugs

pgvector version 0.8.0 was verified via Supabase MCP BEFORE the C3a PR merged. Had the version been < 0.5.0, the HNSW migration would have crashed on deploy. Post-merge verification pattern: use Supabase MCP queries to confirm `alembic_version`, schema columns, and indexes immediately after Render redeploy.

### Trust source files, not briefs

The original C3a brief said "20 chunks" in `ingest_sources.py`. The actual file had 19 chunks. Claude Code correctly caught this by reading the file rather than trusting the brief. Pattern to repeat: verify counts and content against source files, not session summaries or founder descriptions.

### Post-merge verification pattern

After each migration deploy on Render, immediately verify via Supabase MCP:
1. `SELECT version FROM alembic_version` — confirms migration applied
2. `SELECT column_name FROM information_schema.columns WHERE table_name = '<table>'` — confirms schema columns
3. `SELECT indexname FROM pg_indexes WHERE tablename = '<table>'` — confirms indexes

This was done for migration 008 and caught the live state correctly. Make it standard for all future migrations.

---

## 14. Closing note for next instance

### Tone calibration

Unchanged from v8 §25. Founder uses ruthless mentor directive: no flattery, monetization-first filter, kill bad ideas, recommend alternatives. Match that style. §19.12 (complete PR cycles before queuing new work) remains the active counterweight.

### The mandatory investigation rule

Every new code item must follow the Pre-Work Investigation Protocol in `CLAUDE.md`. The 2026-05-16 reconciliation series is evidence this rule has real teeth. Do not skip it for "small" tasks — the C4/C8 duplication was individually small, collectively expensive.

### Documentation hygiene

v9 baseline regen triggered by Block C backend closure. Next baseline regen should wait for either Block C UI closure (C5 merged + verified) OR Stripe integration. Until then, append `*_v9_ADDENDUM_<date>.md` instead of rewriting v9.

### Next session entry point

1. Confirm Plan A still active (default: yes)
2. Verify DNS + Resend domain setup status
3. **C3b corpus ingestion run** — founder executes via Render shell (see §14b runbook); not a coding task
4. **Block B consolidated polish PR** — 9 mobile walkthrough findings; blocked on DNS/Resend
5. **Landing page waitlist test** — founder builds, ~2 hours, 10 days data

---

**End of HANDOFF_BRIEF v9.** Authoritative as of 2026-05-17. Supersedes `HANDOFF_BRIEF_v8.md` (preserved as historical reference). Where v9 conflicts with v8, v9 wins.
