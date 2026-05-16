# C-RECON-1: Send-Message Infrastructure Audit

**Status:** Investigation only — no code changes  
**Date:** 2026-05-16  
**Investigator:** Claude Code  
**Branch:** chore/c-recon-1-investigation

---

## Executive Summary

Two parallel send-message paths exist in the deployed API. PATH A is a mature,
feature-rich SSE streaming endpoint with safety checks, memory recall, RAG
retrieval, analytics, and postprocessing. PATH B is a lean, non-streaming
endpoint built in Block C with tier-aware model selection, per-persona daily
rate limiting, and a structured error vocabulary. The two paths use different
LLM service layers (`llm_client.py` vs `llm_service.py`), different auth
helpers, different rate-limiting strategies, and do not share any code.
Reconciling to PATH B is the recommended path, but it requires porting six
distinct capabilities before PATH A can be retired.

---

## Section 1: PATH A — Existing Streaming Endpoint

### Route definition

```
POST /api/v1/conversations/{conversation_id}/messages
```

- **File:** `apps/api/routers/conversations.py`, line 123  
- **Auth dependency:** `get_current_user_plan` (line 128) — resolves both `User`
  and a `plan` string (`"free"` | `"pro"` | `"premium"`) from the `subscriptions`
  table in a single dependency  
- **Decorator:** `@router.post("/{conversation_id}/messages")` — no `response_model`;
  returns a raw `StreamingResponse`

### Full flow (step by step)

1. **Auth** (line 131): `user, plan = auth` — unwrap the user+plan tuple from
   `get_current_user_plan`
2. **Ownership check** (lines 134–138): `SELECT conversations WHERE id=? AND user_id=?`;
   returns 404 if not found
3. **Rate limit check** (lines 141–163): if `not user.is_admin` and `plan` maps to
   a finite limit:
   - Queries `messages` table: `COUNT(*) WHERE user_id=? AND role='user' AND created_at >= today_utc`
   - Returns 429 with a plain JSON detail dict (no `LLMErrorResponse` schema,
     no `persona_voice`) if `count >= limit`
   - `DAILY_LIMITS = {"free": 10, "pro": 100, "premium": inf}` (line 16)
4. **Return StreamingResponse** (lines 165–179): delegates entirely to
   `conversation_service.stream_response(...)` with `media_type="text/event-stream"`
   and headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`

### Inside `conversation_service.stream_response` (conversation_service.py lines 101–295)

5. **Load conversation + persona** (lines 113–121): two DB queries
6. **Pre-generation safety** (lines 124–138): calls `safety_service.check_input()`;
   logs a `SafetyEvent`; if suppressed, saves user msg, saves safe assistant msg,
   commits, streams a `safety` SSE event and returns early
7. **Memory recall** (lines 141–145): `memory_service.recall(db, user_id, user_text, top_k=6)`
8. **RAG retrieval** (lines 148–153): `retrieval_service.retrieve(db, user_text, persona)`
9. **Phenomenology bridge lookup** (lines 155–173): feature-flagged
   (`PHENOMENOLOGY_BRIDGE_ENABLED` env var, default false)
10. **Build system prompt** (lines 176–181): `prompt_builder.build_system(...)` — weaves
    persona config, memories, passages, and optional phenomenology bridge
11. **Build message history** (lines 184–196): `SELECT messages WHERE conversation_id=? ORDER BY created_at ASC LIMIT 20`
12. **Save user message** (line 199): `_save_message(db, conv, user_id, "user", ...)` 
    with `safety_level` from the pre-check
13. **Yield `start` SSE event** (line 207)
14. **Stream from LLM** (lines 209–217): calls `llm_client.stream(system=system_prompt, messages=lm_messages)`;
    behavior controlled by `POSTPROCESSING_ENABLED` flag — either buffers or
    streams chunks immediately
15. **Post-generation safety** (lines 225–260): calls `safety_service.check_output()`;
    if suppressed, sends safety override SSE event; if postprocessing enabled and
    no safety override, calls `regenerate_or_trim()`
16. **Save assistant message** (lines 265–271): `_save_message(...)` with
    `retrieval_ids`, `safety_level`, `persona_override`, `latency_ms`
17. **Update conversation metadata** (lines 274–281): UPDATE `message_count += 2`,
    `last_message_at`
18. **Commit** (line 282)
19. **Analytics** (lines 285–292): `analytics_service.track("message_sent", ...)`
20. **Yield `done` SSE event** (line 294): includes `message_id`

### SSE protocol

Events are JSON-encoded strings in the format `data: <json>\n\n`. Event types:
- `start` — signals begin of streaming
- `chunk` — text fragment, field `data`
- `done` — end of stream, field `message_id`
- `safety` — pre-generation safety suppression
- `safety_override` — post-generation safety suppression

### Schema consumed

`MessageCreate` (schemas/__init__.py line 92):
```python
class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
```
Only `content` — no `persona_id` or `conversation_id` in the body
(conversation is from the URL path parameter).

### Schema returned

No `response_model`. Raw `StreamingResponse` with `text/event-stream`.

### Model selection

Delegated to `llm_client.stream()` in `conversation_service`. No explicit model
is passed — `llm_client.stream()` defaults to `config.ANTHROPIC_MODEL`
(`"claude-sonnet-4-20250514"` per config.py line 27). **All users get Sonnet
regardless of tier.** There is no Haiku/Sonnet split in PATH A.

### LLM client call site

`conversation_service.py` line 211 (or 215 in legacy branch):
```python
async for chunk in llm_client.stream(system=system_prompt, messages=lm_messages):
```
Uses `LLMClient.stream()` from `services/llm_client.py`.

### Rate limiting

- **Strategy:** counts `Message` rows in the `messages` table (not `daily_usage`)
- **Window:** UTC day (midnight boundary)
- **Scope:** total user messages across ALL personas combined, not per-persona
- **Limits:** `free=10`, `pro=100`, `premium=inf` (hardcoded in `conversations.py` line 16)
- **Error format:** plain dict `{"message": "...", "limit": int, "plan": str}` — not `LLMErrorResponse`
- **Headers:** no `X-RateLimit-*` headers on 429 or 200 responses
- **Admin bypass:** `user.is_admin` skips the check entirely (line 141)
- **References:** `daily_usage` table is **NOT referenced** anywhere in PATH A

### Persona-voiced errors

PATH A does **not** use `persona_voice.py` or `LLMErrorResponse`. All error
responses are plain HTTP exceptions with string or dict details. No per-persona
customizable error messaging.

### Auto-title generation

PATH A does **not** trigger `generate_conversation_title`. No ARQ job is
enqueued from this path.

### Persona access control (free user → pro persona)

Access is checked by `is_persona_accessible(persona_config, user_plan)` inside
`conversation_service.create()` (called from the `POST /conversations` endpoint)
at conversation creation time — **not** at message-send time. PATH A's
`send_message` does not re-check access. A user who somehow obtained a
conversation ID for a pro persona could send messages via PATH A without
being blocked.

### Saves user messages to DB

Yes — `_save_message(db, conv, user_id, "user", user_text, ...)` at line 199.
Fields saved: `conversation_id`, `user_id`, `role`, `content`, `retrieval_ids`,
`safety_level`, `persona_override`, `latency_ms`.
**Notable columns NOT populated:** `model_used`, `tokens_used` (both NULL).

### Saves assistant messages to DB

Yes — `_save_message(...)` at line 265 with `latency_ms`. Also without
`model_used` or `tokens_used`.

### Handles ritual_id

Yes — `ritual_id` is carried on the `Conversation` row (set at creation time
via `conversation_service.create()`). PATH A's `send_message` does not directly
read it but respects the conversation's association. The ritual's `prompt_template`
replaces the opening invocation at `POST /rituals/{ritual_id}/start` time.

### Safety checks

Yes — both pre- and post-generation:
- `safety_service.check_input(user_text, user_id)` before LLM call
- `safety_service.check_output(full_response)` after LLM call
- `SafetyEvent` rows written via `_log_safety_event()` for logged or suppressed events
- Safety override text served via `prompt_builder.build_safety_response()`

### External functions called

| Call | Location |
|------|----------|
| `get_current_user_plan()` | `auth.py` |
| `conversation_service.stream_response()` | `conversation_service.py` |
| `safety_service.check_input()` | `safety_service.py` |
| `safety_service.check_output()` | `safety_service.py` |
| `memory_service.recall()` | `memory_service.py` |
| `retrieval_service.retrieve()` | `retrieval_service.py` |
| `phenomenology_bridge_service.lookup()` | `phenomenology_bridge_service.py` |
| `prompt_builder.build_system()` | `prompt_builder.py` |
| `prompt_builder.build_safety_response()` | `prompt_builder.py` |
| `llm_client.stream()` | `llm_client.py` |
| `regenerate_or_trim()` | `postprocessing_service.py` |
| `analytics_service.track()` | `analytics_service.py` |

### Tests exercising PATH A

No dedicated test file for `POST /conversations/{id}/messages` was found in the
test suite. The `test_conversations.py` tests exercise `conversation_service.create()`
(the dedup logic) but not the streaming `send_message` handler or
`stream_response`. **PATH A has zero direct router-level tests.**

---

## Section 2: PATH B — New C4 Endpoint

### Route definition

```
POST /api/v1/messages
```

- **File:** `apps/api/routers/messages.py`, line 30  
- **Auth dependency:** `get_current_user` (line 36) — resolves `User` only,
  no plan  
- **Decorator:** `@router.post("", response_model=MessageEnvelope)`

### Full flow (step by step)

1. **Load persona** (lines 38–43): `SELECT personas WHERE id=?`; returns 404
   if not found
2. **Load or create conversation** (lines 46–69):
   - If `conversation_id` provided: `SELECT conversations WHERE id=? AND user_id=? AND deleted_at IS NULL`; returns 404 if not found, 400 if `persona_id` mismatches
   - If not provided: creates new `Conversation`, flushes (not committed)
3. **Persona access check** (lines 72–80): `get_user_tier(db, user.id)` queries
   `subscriptions`; if `persona.tier == "pro"` and `user_tier == "free"` → 403
   with `LLMErrorResponse(error_code="persona_locked", persona_voice=...)`
4. **Rate limit check** (lines 83–100): `check_rate_limit(db, UUID(user.id), UUID(body.persona_id), user_tier=user_tier)` queries `daily_usage` table; if not allowed → 429 with `LLMErrorResponse(error_code="rate_limited", persona_voice=...)` + `X-RateLimit-*` headers; **user message is NOT saved on rate limit**
5. **Insert user message** (lines 103–110): `Message(role="user", ...)` flushed
6. **Call LLM** (lines 113–139): `llm_service_module.call_llm(db, user_id, persona_id, conversation_id, user_message)`; on `PersonaAccessDenied` → commit + 403; on `LLMServiceUnavailable` → commit + 503; on `LLMRequestInvalid` → commit + 500
7. **Insert assistant message** (lines 142–148): `Message(role="assistant", model_used=..., tokens_used=..., latency_ms=...)` flushed
8. **Update conversation counters** (lines 151–152): `message_count += 2`, `last_message_at`
9. **Increment daily_usage** (lines 155–163): UPSERT to `daily_usage`
10. **Commit** (line 165)
11. **Set X-RateLimit-* headers on 200 response** (lines 168–173)
12. **Enqueue title generation** (lines 177–188): if `conv.message_count == 3` and `conv.title is None`, enqueue `generate_conversation_title` ARQ job
13. **Return MessageEnvelope** (lines 190–207)

### SSE / Streaming

**No streaming.** Response is synchronous JSON (`MessageEnvelope`).

### Schema consumed

`MessageCreateRequest` (schemas/__init__.py line 291):
```python
class MessageCreateRequest(BaseModel):
    persona_id: str
    conversation_id: Optional[str] = None
    content: str = Field(min_length=1, max_length=4000)
```
Includes `persona_id`; `conversation_id` is optional (creates new if absent).

### Schema returned

`MessageEnvelope` (schemas/__init__.py line 321):
```python
class MessageEnvelope(BaseModel):
    conversation: ConversationSummary
    message: MessageResponse
```
`MessageResponse` includes `model_used`, `tokens_used`, `latency_ms`.

### Model selection

Delegated to `llm_service.call_llm()`. Selection is tier-aware:
- `free` tier → `MODEL_FREE = "claude-haiku-4-5-20251001"`
- `pro` tier → `MODEL_PRO = "claude-sonnet-4-6"`

### LLM call site

`routers/messages.py` line 115:
```python
llm_response = await llm_service_module.call_llm(
    db=db, user_id=UUID(user.id), persona_id=UUID(body.persona_id),
    conversation_id=UUID(conv.id), user_message=body.content,
)
```
Uses `services/llm_service.py`.

### Rate limiting

- **Strategy:** queries `daily_usage` table (from C1 schema)
- **Window:** UTC day
- **Scope:** per (user, persona) pair — 5 messages per philosopher per day
- **Limit:** `FREE_DAILY_LIMIT_PER_PERSONA = 5` (hardcoded in `rate_limit_service.py`)
- **Error format:** `LLMErrorResponse` with `persona_voice`
- **Headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` on both 200 and 429
- **Admin bypass:** none — admins are rate-limited equally
- **Pro users:** unlimited; `check_rate_limit` short-circuits, no `daily_usage` query

### Persona-voiced errors

Yes — all errors go through `get_error_voice(persona, error_code)`:
- Checks `persona.config["error_messages"][error_code]` first
- Falls back to `_FALLBACKS` dict in `persona_voice.py`:
  - `"persona_locked"`: "This philosopher requires a Pro subscription."
  - `"rate_limited"`: "You've reached your daily message limit with this philosopher. Try again tomorrow or upgrade to Pro for unlimited conversations."
  - `"llm_unavailable"`: "I'm having trouble responding. Please try again in a moment."

### Auto-title generation

Yes — after commit, if `conv.message_count == 3` and `conv.title is None`,
enqueues ARQ job `generate_conversation_title` (arq_worker.py line 100).
The title worker uses a **new direct Anthropic client** (not `llm_client` or
`llm_service`), hardcodes `"claude-haiku-4-5-20251001"`, and generates a ≤80
char title from the first 3 messages.

### Persona access control (free user → pro persona)

Yes — checked explicitly at line 73 before rate limit and user message save:
```python
if persona.tier == "pro" and user_tier == "free":
    raise HTTPException(403, ...)
```
The check is redundant with the access check inside `llm_service.call_llm()`
(which raises `PersonaAccessDenied`); the outer check returns a cleaner 403
without saving the user message first.

### Saves user messages to DB

Yes — only after rate limit and persona access checks pass. Fields saved:
`conversation_id`, `user_id`, `role="user"`, `content`.
**Not saved on rate limit (429) or persona lock (403).**
**Saved (and committed) on LLM failure (503)** — so user can retry.
`model_used`, `tokens_used`, `latency_ms`, `retrieval_ids`, `safety_level`,
`persona_override` are **not** set on the user message.

### Saves assistant messages to DB

Yes — `model_used`, `tokens_used`, `latency_ms` populated from `LLMResponse`.
`retrieval_ids`, `safety_level`, `persona_override` are **not** set.

### Handles ritual_id

No — `MessageCreateRequest` does not accept `ritual_id`. Conversations
associated with rituals can be continued via PATH B by passing the
`conversation_id`, but PATH B has no ritual-specific logic.

### Safety checks

No — PATH B calls `llm_service.call_llm()` which does not run safety
pre/post-processing. No `SafetyEvent` rows are ever written via PATH B.

### External functions called

| Call | Location |
|------|----------|
| `get_current_user()` | `auth.py` |
| `get_user_tier()` | `tier_service.py` |
| `check_rate_limit()` | `rate_limit_service.py` |
| `get_error_voice()` | `persona_voice.py` |
| `llm_service_module.call_llm()` | `llm_service.py` |
| `arq_queue.enqueue_job("generate_conversation_title", ...)` | `arq_worker.py` |

### Tests exercising PATH B

All 37 tests in `apps/api/tests/routers/test_messages.py`. Named tests include:

**Success path (12):**
- `test_new_conversation_creates_conversation_and_returns_envelope`
- `test_existing_conversation_appends_message`
- `test_auto_title_enqueued_after_3rd_message`
- `test_auto_title_not_enqueued_on_1st_message`
- `test_auto_title_not_enqueued_on_2nd_message`
- `test_auto_title_not_enqueued_on_4th_message`
- `test_daily_usage_new_row_created`
- `test_daily_usage_existing_row_incremented`
- `test_conversation_message_count_and_last_message_at_updated`
- `test_free_user_free_persona_returns_200_with_haiku`
- `test_pro_user_pro_persona_returns_200_with_sonnet`
- `test_rate_limit_1st_message_allowed`

**Access control / error path (9):**
- `test_unauthenticated_returns_401`
- `test_free_user_pro_persona_returns_403_persona_locked`
- `test_conversation_other_user_returns_404`
- `test_deleted_conversation_returns_404`
- `test_persona_id_mismatch_returns_400`
- `test_llm_unavailable_returns_503_with_fallback_voice`
- `test_user_message_saved_on_llm_failure`
- `test_content_too_long_returns_422`
- `test_empty_content_returns_422`

**Rate limiting (8):**
- `test_rate_limit_5th_message_allowed`
- `test_rate_limit_6th_message_blocked`
- `test_rate_limit_blocked_user_message_not_saved`
- `test_rate_limit_blocked_daily_usage_not_incremented`
- `test_rate_limit_pro_user_unlimited`
- `test_rate_limit_headers_present_on_success`
- `test_rate_limit_headers_present_on_429`
- (implicit: `test_rate_limit_1st_message_allowed` counted in success above)

**Validation (2):**
- `test_content_too_long_returns_422`
- `test_empty_content_returns_422`

---

## Section 3: `llm_client.py` (the old service)

**File:** `apps/api/services/llm_client.py`

### What it exposes

A singleton `LLMClient` instance (`llm_client = LLMClient()` at line 55) with
two async methods:

- **`stream(system, messages, model=None, max_tokens=1024)`** (lines 14–35):  
  Wraps `anthropic.AsyncAnthropic.messages.stream()` — true SSE streaming via
  `async for text in stream.text_stream`. Logs total latency at debug level.
  Does **not** capture token usage or model name from the response.
  Model defaults to `config.ANTHROPIC_MODEL` (`"claude-sonnet-4-20250514"`).

- **`complete(system, user, model=None, max_tokens=512)`** (lines 37–52):  
  Wraps `anthropic.AsyncAnthropic.messages.create()` for single-shot completions
  (memory extraction, insight generation). Model defaults to
  `config.ANTHROPIC_MEMORY_MODEL` (`"claude-haiku-4-5-20251001"`).
  Returns the text content of the first response block.

### SDK used

Anthropic SDK only (`anthropic.AsyncAnthropic`). OpenAI SDK not imported.

### What it does

Thin wrapper around the Anthropic SDK. No retry logic, no tier-based model
selection, no token tracking, no conversation history management.
`stream()` is the only way to produce streaming output.

### All callers

| Caller | Usage |
|--------|-------|
| `conversation_service.py` line 15, 211, 215 | `llm_client.stream()` — drives PATH A |
| `memory_service.py` line 6, 48 | `llm_client.complete()` — memory extraction |
| `postprocessing_service.py` lines 369–370 | `llm_client.complete()` — postprocessing re-generation |
| `workers/arq_worker.py` lines 61, 78 | `llm_client.complete()` — insight generation |

### Tests

No dedicated unit tests for `llm_client.py` itself. Indirectly tested via
`test_safety.py`, `test_postprocessing.py`, `test_prompts.py` (through
`conversation_service`).

---

## Section 4: `llm_service.py` (the new C2 service)

**File:** `apps/api/services/llm_service.py`

### What it exposes

One async function `call_llm()` and one dataclass `LLMResponse`. Also exports:
- `MODEL_FREE = "claude-haiku-4-5-20251001"`
- `MODEL_PRO = "claude-sonnet-4-6"`
- `MEMORY_WINDOW_FREE = 5`
- `MEMORY_WINDOW_PRO = 20`

### What it does

Non-streaming, synchronous-return LLM call with:
1. **Tier lookup:** `get_user_tier(db, user_id)` → queries `subscriptions`
2. **Persona lookup:** `SELECT personas WHERE id=?`
3. **Access check:** `persona.tier == "pro"` and `user_tier == "free"` → raises `PersonaAccessDenied`
4. **Model selection:** `MODEL_PRO` for pro users, `MODEL_FREE` for free
5. **Window selection:** `MEMORY_WINDOW_PRO=20` or `MEMORY_WINDOW_FREE=5`
6. **History query:** `SELECT messages WHERE conversation_id=? ORDER BY created_at ASC LIMIT {window}`
7. **API call:** `_client.messages.create(model=..., max_tokens=1024, system=..., messages=...)`
8. **Retry logic:** up to `MAX_RETRIES=3` on `RateLimitError`, `APIStatusError` (5xx), `APIConnectionError`, `APITimeoutError`; exponential backoff `2**attempt` seconds; non-retryable 4xx raises `LLMRequestInvalid` immediately
9. **Return `LLMResponse`:** carries `content`, `model_used`, `input_tokens`, `output_tokens`, `latency_ms`

### SDK used

Anthropic SDK only. No streaming is used — `messages.create()` not `messages.stream()`.

### Overlap and differences vs `llm_client.py`

| Dimension | `llm_client.py` | `llm_service.py` |
|-----------|----------------|------------------|
| Streaming | Yes (`stream()`) | No |
| Retries | None | Yes (3 attempts, exponential backoff) |
| Tier awareness | None | Yes (Haiku/Sonnet split) |
| Model default | `config.ANTHROPIC_MODEL` (Sonnet) | Hardcoded constants |
| Token tracking | None | Yes (`input_tokens`, `output_tokens`) |
| Conversation history | Caller's responsibility | Fetched internally from DB |
| Access control | None | Yes (`PersonaAccessDenied`) |
| Memory/RAG/safety | None | None |
| Persona lookup | None | Yes (internal DB query) |
| Callers | 4 (all old infrastructure) | 1 (`routers/messages.py` only) |

### All callers

| Caller | Usage |
|--------|-------|
| `routers/messages.py` line 24, 115 | `call_llm()` — drives PATH B |

### Tests

10 tests in `apps/api/tests/services/test_llm_service.py`:
- `test_free_user_free_persona_uses_free_model`
- `test_free_user_memory_window_is_5`
- `test_pro_user_free_persona_uses_pro_model`
- `test_pro_user_pro_persona_succeeds`
- `test_free_user_pro_persona_raises_access_denied`
- `test_retry_on_503_succeeds_second_attempt`
- `test_retry_on_timeout_all_fail_raises_unavailable`
- `test_auth_error_raises_request_invalid_no_retry`
- `test_response_fields_populated`

---

## Section 5: Cross-references

### ARQ tasks and which path they depend on

| Task | Enqueued by | LLM caller | Depends on |
|------|-------------|------------|------------|
| `generate_conversation_title` | PATH B (`messages.py` lines 179–188) | Direct `anthropic.AsyncAnthropic` (not via either service) | PATH B only |
| `extract_memory_task` | PATH A (`conversation_service.py` — **not found in current code**) | `llm_client.complete()` | PATH A infrastructure (memory_service) |
| `generate_insight_task` | PATH A infrastructure | `llm_client.complete()` | PATH A infrastructure |
| `send_ritual_reminder_task` | Cron scheduler | Email only (Resend) | Neither |

**Note:** `extract_memory_task` and `generate_insight_task` are defined in
`arq_worker.py` but the current code of `conversation_service.stream_response`
does not contain an explicit `enqueue_job("extract_memory_task")` call — they
appear to be legacy tasks that were part of an older pipeline no longer wired
up in `stream_response`. They remain in `WorkerSettings.functions` but may be
orphaned.

### Ritual endpoints

`POST /api/v1/rituals/{ritual_id}/start` uses `conversation_service.create()`
to create conversations. Ritual conversations are then sent messages via PATH A
(`POST /conversations/{id}/messages`). PATH B has no ritual awareness — it can
continue a ritual conversation by `conversation_id` but does not interpret
`ritual_id`.

### Admin endpoints

`GET /admin/safety-events` and `GET /admin/analytics/summary` read `SafetyEvent`
rows. These rows are only ever written by PATH A (via `_log_safety_event()`).
**If PATH A is retired, the safety-events admin endpoint will return an empty
table going forward.** Admin `PATCH /personas/{persona_id}` is path-agnostic.

### Memory and insight endpoints

`GET /api/v1/memory` and `GET /api/v1/insights` read from `memory_entries` and
`insights`. These tables are only populated by `extract_memory_task` and
`generate_insight_task` (via `llm_client.complete()`). PATH B writes no memory
or insights. **Retiring PATH A without a memory-extraction pipeline in PATH B
would cause the memory/insights feature to silently go stale.**

### Billing / Stripe webhooks

`POST /api/v1/billing/webhook` updates `subscriptions`. `tier_service.get_user_tier()`
reads from `subscriptions`. Both paths depend on the `subscriptions` table but
via different auth layers (`get_current_user_plan` vs `get_user_tier()`).

### grep: route pattern references

All references to the PATH A route pattern in test and source files:
- `routers/conversations.py` — defines it
- No test file exercises `POST /conversations/{id}/messages` directly

All references to PATH B route:
- `routers/messages.py` — defines it
- `apps/api/main.py` — registers both routers
- `tests/routers/test_messages.py` — 37 tests

---

## Section 6: Test coverage

### Tests exercising PATH A

**Zero** direct router-level tests. The only indirect coverage:
- `tests/test_conversations.py` — 5 tests for `conversation_service.create()` dedup logic (not `stream_response`)
- `tests/test_safety.py` — exercises safety logic (the `safety_service` layer, not the endpoint)
- `tests/test_postprocessing.py` — exercises postprocessing logic; includes a tripwire test (line ~400) that verifies `conversation_service.py` still respects the "safety override bypass" invariant by inspecting source code directly

**Implication:** PATH A has no router test that would catch a regression if the endpoint were broken or removed.

### Tests exercising PATH B

All 37 tests in `tests/routers/test_messages.py`. See Section 2 for the full named list.

Additionally:
- `tests/services/test_llm_service.py` — 9 tests for `llm_service.call_llm()` (PATH B's LLM layer)
- `tests/services/test_rate_limit_service.py` — 10 tests for `check_rate_limit()` (PATH B's rate limiting)
- `tests/services/test_tier_service.py` — 5 tests for `get_user_tier()` (shared, but only PATH B calls it at the router level)

### Tests that would break if either path were removed

**If PATH A were removed:**
- `tests/test_conversations.py` — 5 tests exercise `conversation_service.create()` directly; these would continue to pass
- `tests/test_postprocessing.py` — the tripwire test reads `conversation_service.py` source code; if the file were deleted it would fail. If PATH A's router handler were just removed, the test would still pass.
- No router-level test would break (none exist for PATH A)

**If PATH B were removed:**
- All 37 tests in `tests/routers/test_messages.py` would fail
- All 9 tests in `tests/services/test_llm_service.py` would fail (these test `llm_service.py`, which would be unused)
- All 10 tests in `tests/services/test_rate_limit_service.py` would fail (the new `check_rate_limit` function would be unused)
- `tests/services/test_tier_service.py` — these test `tier_service.py` directly; they would still pass

---

## Section 7: Reconcile options

### Option α: Keep PATH B, deprecate PATH A

Retire `POST /conversations/{id}/messages`. PATH B becomes the single
send-message entry point.

**What would need to change:**

1. **Safety pipeline (large):** PATH B currently skips all safety checks. Add
   pre/post-generation safety via `safety_service` in the router or in
   `llm_service.call_llm()`. This requires writing `SafetyEvent` rows and
   surfacing safety events to the frontend via a non-streaming mechanism
   (e.g., a field in `MessageEnvelope`) or a separate polling endpoint.

2. **Memory extraction (medium):** PATH B does not trigger memory extraction.
   After a successful response, enqueue `extract_memory_task` with the
   user/assistant text pair. This requires wiring `arq_queue` to the handler
   (already done for title generation; same pattern).

3. **RAG retrieval (medium):** `retrieval_service.retrieve()` and
   `memory_service.recall()` are not called in PATH B. The system prompt
   passed to `llm_service.call_llm()` uses only `persona.config["system_fragment"]`
   with no memories or passages injected. This requires either extending
   `call_llm()` to accept pre-fetched context or adding retrieval in the router.

4. **Analytics (small):** `analytics_service.track("message_sent", ...)` is
   not called in PATH B. Low risk to omit but will cause metrics divergence.

5. **Ritual awareness (small):** PATH B must accept ritual conversations by
   `conversation_id` without breakage — already works. No new ritual logic
   needed unless ritual-specific system prompts are desired.

6. **Admin bypass for rate limiting (small):** PATH A skips rate limiting for
   admins (`user.is_admin`). PATH B does not. Optional addition.

7. **Postprocessing (medium):** the `regenerate_or_trim` postprocessing step is
   feature-flagged and already behind `POSTPROCESSING_ENABLED`. Only needed if
   that flag is on in production.

8. **Phenomenology bridge (small):** feature-flagged; can be added later.

9. **Frontend update (unknown, out of scope):** any frontend clients using the
   SSE streaming protocol must be migrated to poll the non-streaming response.
   This is the largest unknown outside the API codebase.

10. **Remove PATH A code:** delete `send_message` handler from `conversations.py`,
    remove `DAILY_LIMITS`, remove `StreamingResponse` import. Leave
    `create_conversation`, `list_conversations`, `get_messages`, `delete_conversation`
    untouched.

**Effort estimate:** Medium-to-large (items 1–3 are non-trivial features; item 9
depends on frontend scope).

**Risks:**
- Safety regression: production messages go unsafety-checked until #1 is shipped
- Memory staleness: `memory_entries` table stops growing until #2 is shipped
- Response quality degradation: no RAG context in replies until #3 is shipped
- Frontend breakage: any client consuming SSE events must be updated

### Option β: Keep PATH A, deprecate PATH B

Retire `POST /api/v1/messages`. PATH A becomes the single entry point.

**What would need to change:**

1. **Per-persona rate limiting (medium):** PATH A's rate limit uses the `messages`
   table with cross-persona counts. Replace or augment with `daily_usage`-based
   per-persona limits (the C8 work). The `daily_usage` table exists but PATH A
   does not write to it.

2. **Haiku/Sonnet tier split (medium):** PATH A always uses `config.ANTHROPIC_MODEL`
   (Sonnet). Introduce tier-aware model selection in `llm_client.stream()` or
   `conversation_service.stream_response()`.

3. **Token usage tracking (medium):** PATH A saves no `model_used` or `tokens_used`
   on message rows. These would need to be extracted from the streaming response
   (via `stream.get_final_message()`) and stored.

4. **Structured error responses (small):** PATH A's 429 returns a plain dict;
   PATH B returns `LLMErrorResponse` with `persona_voice`. Port
   `persona_voice.py` to PATH A.

5. **`X-RateLimit-*` headers (small):** not present in PATH A.

6. **Auto-title generation (small):** not triggered by PATH A. Port from PATH B.

7. **Delete PATH B code:** remove `routers/messages.py`, `services/llm_service.py`,
   `services/persona_voice.py`, `services/rate_limit_service.py` (new section),
   the `MessageCreateRequest` / `MessageEnvelope` / `MessageResponse` /
   `ConversationSummary` / `LLMErrorResponse` schemas, unregister from `main.py`.

8. **Delete all Block C tests (56 tests):** `test_messages.py` (37),
   `test_llm_service.py` (9), `test_rate_limit_service.py` (10). Significant
   test regression.

**Effort estimate:** Medium (items 1–3 touch streaming infrastructure that is
harder to unit-test; losing 56 tests is a substantial regression).

**Risks:**
- Losing all 56 Block C tests leaves the rate-limiting and tier logic untested
- Streaming infrastructure is harder to unit-test, making future regressions harder to catch
- The non-streaming `MessageEnvelope` is likely what the frontend expects now
  (given C4 was shipped); PATH A's SSE format would need frontend alignment

### Option γ: Keep both for different use cases

Route streaming clients to PATH A, non-streaming clients to PATH B. Define:
- PATH A: web frontend SSE consumers (real-time typing effect)
- PATH B: mobile / programmatic / background callers

**Defensibility:** Weak in the long run. Two paths must stay in sync on
rate limiting, safety, model selection, and data schema. Any bug fixed in one
must be ported to the other. The cognitive overhead is high and test coverage for
PATH A is currently zero.

**Effort estimate:** Small (no changes needed now) but **carries permanent
maintenance overhead**.

**Risks:**
- Divergence: the two paths will drift in behavior over time
- The `daily_usage` rate limit only applies to PATH B; PATH A users could exceed the per-persona cap
- Safety only applies to PATH A; PATH B users bypass it
- These inconsistencies may cause user-facing anomalies that are hard to diagnose

---

## Section 8: Recommendation

**Recommend Option α: Keep PATH B, deprecate PATH A.**

### Rationale

1. **PATH B is the better foundation.** It has tier-aware model selection
   (Haiku/Sonnet), per-persona daily rate limits with `X-RateLimit-*` headers,
   a structured error vocabulary (`LLMErrorResponse` + `persona_voice`), full
   token tracking (`model_used`, `tokens_used`), auto-title generation, and 56
   well-isolated unit tests. These are all hard-won features from C1–C8 that
   would need to be re-ported to PATH A under Option β.

2. **PATH A has zero router tests.** Deprecating it is low-risk from a test
   regression perspective. PATH B has comprehensive coverage.

3. **Non-streaming is safer to extend.** Adding safety checks, memory
   extraction, and RAG to a synchronous response handler is architecturally
   cleaner than adding tier logic and token tracking to a streaming generator.
   Each capability can be added as a discrete, testable step.

4. **The `daily_usage` table is already live.** The C1 schema, C8 rate limiting,
   and daily_usage increment in C4 form a coherent, tested rate-limiting system.
   Abandoning it (Option β) would mean re-implementing equivalent logic on top
   of a raw `messages` count query with different semantics.

5. **Streaming is a presentation concern, not a transport mandate.** If the
   frontend needs a typing effect, it can be achieved by PATH B returning the
   full response and the client displaying it progressively — or by a thin
   streaming wrapper over the existing non-streaming response. This is
   a frontend decision, not an API architecture decision.

### Recommended sequencing for PATH A deprecation

1. **C-SAFETY-1:** Add `safety_service.check_input/output()` to PATH B router
   (pre-save and post-LLM), write `SafetyEvent` rows. This is the most
   safety-critical gap.
2. **C-MEMORY-1:** Enqueue `extract_memory_task` from PATH B after commit.
3. **C-RAG-1:** Add `retrieval_service.retrieve()` and `memory_service.recall()`
   to `call_llm()` or the router (passes context into system prompt).
4. **C-DEPRECATE-A:** Remove PATH A handler from `conversations.py`, update
   `DAILY_LIMITS` removal, remove `StreamingResponse` import. Communicate
   to frontend team before deploy.
5. **C-CLEANUP:** Remove unreferenced `extract_memory_task`/`generate_insight_task`
   from `WorkerSettings.functions` if confirmed orphaned.

### Future cleanup notes (do not act now)

- `llm_client.complete()` is still needed by `memory_service`, `postprocessing_service`,
  and `arq_worker.generate_insight_task` — do not remove it when PATH A is
  deprecated; only `llm_client.stream()` would become unused.
- The `DAILY_LIMITS` dict in `conversations.py` (free=10, pro=100) conflicts
  with PATH B's per-persona limit of 5. When PATH A is retired, the
  `DAILY_LIMITS` constant can be deleted.
- The `get_current_user_plan` auth dependency in PATH A uses `sub.plan` with
  status in `("active", "trialing")`, while `tier_service.get_user_tier()` in
  PATH B uses `sub.status == "active"` and checks `current_period_end`. The
  trialing/expiry semantics differ — this should be unified in a follow-up.

---

*Report generated by Claude Code as part of the C-RECON-1 investigation task.
No source files were modified. All findings are based on reading code at commit
`c1b22a6` on branch `chore/c-recon-1-investigation`.*
