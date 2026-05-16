# C-RECON-2: PATH A Pre-Port Investigation

**Status:** Investigation only — no code changes
**Date:** 2026-05-16
**Investigator:** Claude Code
**Branch:** chore/c-recon-2-path-a-investigation
**Follows:** C-RECON-1 (send-message infrastructure audit)

---

## Context

C-RECON-1 established that two parallel send-message paths exist. The
reconciliation direction has been reversed: PATH A (SSE streaming endpoint at
`POST /api/v1/conversations/{id}/messages`) will become the canonical endpoint,
and the four features built in C4/C8 (tier routing, per-persona rate limit,
auto-title, persona errors) will be ported into PATH A before PATH B is deleted.

This report maps every insertion point required for those ports, and audits
the current state of memory/insights, error handling, and the rituals
integration to surface open decisions before code is written.

Files read for this investigation (all under `apps/api/`):

- `routers/conversations.py`
- `services/conversation_service.py`
- `services/llm_client.py`
- `services/safety_service.py`
- `services/retrieval_service.py`
- `services/memory_service.py`
- `services/prompt_builder.py`
- `services/analytics_service.py` (via grep)
- `services/llm_service.py` (PATH B)
- `services/rate_limit_service.py` (PATH B)
- `services/persona_voice.py` (PATH B)
- `services/tier_service.py` (PATH B)
- `services/exceptions.py`
- `workers/arq_worker.py`
- `routers/messages.py` (PATH B)
- `routers/rituals.py`
- `auth.py`
- `config.py`
- `main.py`
- `schemas/__init__.py`
- `personas/_base.py`

---

## Section 1: Model Selection in PATH A

### Where the model is chosen

**`config.py` line 27:**
```python
ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
```

**`services/llm_client.py` line 22:**
```python
model = model or config.ANTHROPIC_MODEL
```

**`services/conversation_service.py` lines 211 and 215:**
```python
async for chunk in llm_client.stream(system=system_prompt, messages=lm_messages):
```
(Both the buffer-mode and legacy-streaming branches call `llm_client.stream()`
without passing a `model` argument.)

### Current behaviour

PATH A always resolves to `claude-sonnet-4-20250514` regardless of the user's
plan. There is no tier-aware selection anywhere in PATH A today.

### Production value

`claude-sonnet-4-20250514` for all users (free and pro alike).

### Does `llm_client.stream()` accept a `model` parameter?

**Yes.** `llm_client.py` line 18:
```python
async def stream(
    self,
    system: str,
    messages: list[dict],
    model: str | None = None,   # ← already there
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
```
The parameter exists and is honoured — it falls through to
`_client.messages.stream(model=model, ...)` at line 26. PATH A simply never
passes it.

### Insertion point for tier-based model selection

`services/conversation_service.py` lines 211 and 215 — the two `llm_client.stream()`
call sites inside `stream_response`. `user_plan` is already available as a
function argument (signature line 106). The change is:

```python
# Proposed addition — resolve model before the stream branches
model = "claude-sonnet-4-6" if user_plan == "pro" else "claude-haiku-4-5-20251001"

# Then pass to both call sites:
async for chunk in llm_client.stream(system=system_prompt, messages=lm_messages, model=model):
```

Note: PATH B uses model IDs `claude-haiku-4-5-20251001` (free) and
`claude-sonnet-4-6` (pro) — defined in `services/llm_service.py` lines 18-19.
Use the same constants for consistency. `config.ANTHROPIC_MODEL` becomes
unused in PATH A after this change and can be retired from config.

### History window

PATH B also uses a tier-aware history window (`MEMORY_WINDOW_FREE = 5`,
`MEMORY_WINDOW_PRO = 20`; `llm_service.py` lines 20-21). PATH A currently
hard-limits history to 20 messages for all users
(`conversation_service.py` line 187). When adding tier routing, align the
history window too: `.limit(20 if user_plan == "pro" else 5)` at line 187.

---

## Section 2: Existing Rate Limiting in PATH A

### Does PATH A perform a rate limit check?

**Yes.** `routers/conversations.py` lines 141–163.

### Exact logic

```python
DAILY_LIMITS: dict[str, float] = {
    "free": 10,
    "pro": 100,
    "premium": float("inf"),
}

if not user.is_admin:
    limit = DAILY_LIMITS.get(plan, float("inf"))
    if limit != float("inf"):
        today_utc = datetime.now(timezone.utc).replace(hour=0, ...)
        count_result = await db.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.user_id == user.id,
                Message.role == "user",
                Message.created_at >= today_utc,
            )
        )
        count = count_result.scalar_one()
        if count >= limit:
            raise HTTPException(
                status_code=429,
                detail={"message": "...", "limit": int(limit), "plan": plan},
            )
```

### Verification of C-RECON-1 characterisation

C-RECON-1 reported "free=10/pro=100, cross-persona, messages table count".
**Confirmed correct.** Specifically:

| Attribute | Value |
|-----------|-------|
| Free limit | 10 messages/day |
| Pro limit | 100 messages/day |
| Scope | Cross-persona (counts ALL `Message.role='user'` rows for the user today, regardless of which persona or conversation) |
| Table | `messages` (not `daily_usage`) |
| Admin bypass | Yes (`if not user.is_admin`) |
| Error format | Plain `dict` — `{"message": str, "limit": int, "plan": str}` |
| Headers | None — no `X-RateLimit-*` headers |

### Contrast with PATH B (C8 rate limit)

| Attribute | PATH A (current) | PATH B (C8) |
|-----------|-----------------|-------------|
| Limit (free) | 10/day | 5/day per-persona |
| Scope | Cross-persona | Per (user, persona) |
| Table | `messages` | `daily_usage` |
| Pro limit | 100/day | Unlimited |
| Headers | None | `X-RateLimit-{Limit,Remaining,Reset}` |
| Error body | Plain dict | `LLMErrorResponse` + `persona_voice` |
| Admin bypass | Yes | No (free-tier bypass only) |

**This is a behaviour change for free-tier users.** After the port, a free user
will be limited to 5 messages per persona per day (down from 10 cross-persona).

### Insertion point

Replace lines 141–163 of `routers/conversations.py` entirely with a call to
`rate_limit_service.check_rate_limit()`. The `user_plan` value must be
converted to a `user_tier` string first (they use the same values; the param
name differs by convention). The `persona_id` must be resolved from
`conversation_id` at this point or loaded earlier.

**Required prerequisite:** Resolve the conversation row (already done at lines
134–138) and load `conv.persona_id` before the rate-limit call, since
`check_rate_limit` requires `(user_id: UUID, persona_id: UUID)`.

**Decisions needed before implementation:**

1. Does a free user's ritual message count against the per-persona daily limit?
   (See Section 10.)
2. Should admin bypass be added to `check_rate_limit`, or is the existing
   `is_admin` guard in the router sufficient?

---

## Section 3: Safety Pipeline in PATH A

### Full sequence

PATH A runs two safety passes — both regex-only. There is no LLM classifier
in the current code.

**Pass 1 — Pre-generation** (`conversation_service.py` lines 123–138):

```
safety_service.check_input(user_text, user_id)
  ↓ if should_log (level != "none"):
      _log_safety_event(... stage="pre_generation")
  ↓ if should_suppress_persona (level in medium/high/critical):
      _save_message(... role="user",  safety_level=level)
      _save_message(... role="assistant", persona_override=True)
      db.commit()
      analytics_service.track("safety_event_pre", ...)
      yield {"type": "safety", "level": level}
      yield chunks of safe_text
      yield {"type": "done"}
      return  ← generator exits, no LLM call made
```

**Pass 2 — Post-generation** (`conversation_service.py` lines 225–236):

```
safety_service.check_output(full_response)
  ↓ if should_suppress_persona:
      _log_safety_event(... stage="post_generation")
      yield {"type": "safety_override", "level": level}
      safe_text = prompt_builder.build_safety_response(level=level)
      yield chunks of safe_text
      full_response = safe_text
      # postprocessing intentionally skipped
  ↓ elif POSTPROCESSING_ENABLED:
      postprocessing runs on full_response
```

### Input check logic (`safety_service.py` lines 60–90)

| Level | Trigger | Result |
|-------|---------|--------|
| `high` | Any phrase in `RISK_HIGH` list (14 items; "kill myself", "suicide", etc.) | `category="self_harm"`, suppress persona |
| `medium` | Any phrase in `RISK_MEDIUM` list (15 items; "can't go on", "hopeless", etc.) | `category="potential_distress"`, suppress persona |
| `low` | Any of 7 distress words ("tired", "burden", etc.) | `category="distress_signal"`, log only, persona continues |
| `none` | No match | No action |

### Output check logic (`safety_service.py` lines 92–105)

- Scans LLM response for phrases in `OUTPUT_RISK_PHRASES` (7 items; "lethal dose", "best method", etc.)
- Any match → level `high`, category `output_harm`, suppress persona

### Does this match Decision #6?

Decision #6 per the brief: "regex input + regex output + LLM classifier on triggers ONLY".

**Current code: regex input + regex output only. NO LLM classifier is present.**

The architecture matches the first two layers but the LLM classifier layer is
absent entirely. `safety_service.py` contains no `llm_client.complete()` call.
This is not a gap introduced by this investigation — the classifier was
apparently never implemented.

**Verdict:** Two of three layers exist. The LLM classifier is a future addition,
not a pre-port requirement.

### Safety event fields written

`_log_safety_event()` (`conversation_service.py` lines 316–328) writes:

| Field | Value |
|-------|-------|
| `user_id` | user's ID |
| `conversation_id` | conversation's ID |
| `message_id` | **Always `None`** — never resolved to the saved message ID |
| `trigger_stage` | `"pre_generation"` or `"post_generation"` |
| `risk_level` | e.g. `"high"`, `"medium"`, `"low"` |
| `category` | e.g. `"self_harm"`, `"potential_distress"`, `"output_harm"` |
| `action_taken` | `"suppressed"` if should_suppress_persona else `"logged"` |
| `raw_flags` | `{"flags": [list], "trigger": phrase}` |

**Future cleanup note (do not act now):** `message_id` is always `None` because
`_log_safety_event` is called before `_save_message` in the pre-generation path,
and not updated after. This makes admin queries by `message_id` useless. This
should be fixed in a future cleanup PR, not in the port.

### Response when persona is dropped

Both safety passes call `prompt_builder.build_safety_response(level=level)`, which
renders `prompts/safety_response.jinja2`. The rendered text is chunked into
20-character pieces and yielded as `{"type": "chunk", "data": <chunk>}` events,
followed by `{"type": "done"}`.

The client receives no `LLMErrorResponse` and no `persona_voice` — just plain
app-voice safety copy. Porting `get_error_voice()` here is optional (safety copy
intentionally uses a single app voice, not persona voice).

---

## Section 4: RAG Retrieval in PATH A

### File and call site

**`services/retrieval_service.py`**, function `retrieve()` at line 12.

Called from `services/conversation_service.py` line 151:
```python
passages = await retrieval_service.retrieve(db, user_text, persona)
```

### Function signature

```python
async def retrieve(
    self,
    db: AsyncSession,
    query: str,
    persona: PersonaConfig,
    top_k: int | None = None,       # defaults to persona.retrieval_top_k
    score_threshold: float = 0.72,  # hardcoded default
) -> list[SourceChunk]:
```

### Embeddings model

**OpenAI `text-embedding-3-small`**, 1536 dimensions.

- Config: `config.py` lines 31-32: `EMBEDDING_MODEL: str = "text-embedding-3-small"` / `EMBEDDING_DIM: int = 1536`
- Client: `services/embedding_client.py` line 4: `AsyncOpenAI(api_key=config.OPENAI_API_KEY)`
- Both memory recall and RAG retrieval use the same embedding client and model.

### top_k

Sourced from `persona.retrieval_top_k` (`personas/_base.py` line 45, default `4`).
Individual personas can override this value in their dataclass definition.
The caller in `conversation_service.py` does not override it — the per-persona
default is always used.

`retrieval_service.py` line 39 fetches `top_k * 3` rows from the DB, then
filters by `score >= 0.72` and returns `[:top_k]`, so the final count is
at most `persona.retrieval_top_k`.

### Context injection

Retrieved passages are passed to `prompt_builder.build_system()` at
`conversation_service.py` lines 176–181:
```python
system_prompt = prompt_builder.build_system(
    persona=persona,
    memories=memories,
    passages=passages,          # ← injected here
    phenomenology_bridge=phenomenology_bridge,
)
```
`prompt_builder` renders `prompts/system_base.jinja2` which incorporates the
passages into the system prompt text sent to the LLM.

---

## Section 5: Streaming (SSE) Implementation

### Transport mechanism

**`fastapi.responses.StreamingResponse`**, registered at
`routers/conversations.py` lines 165–179:
```python
return StreamingResponse(
    conversation_service.stream_response(...),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    },
)
```

Not SSE-Starlette. Not a custom protocol. FastAPI's built-in `StreamingResponse`
with `text/event-stream` content type. Each SSE event is a plain string yielded
from the `stream_response` generator.

### Events emitted and their meaning

| Event | Sent when | Payload |
|-------|-----------|---------|
| `{"type": "start"}` | Before LLM call begins (line 207) | None beyond type |
| `{"type": "chunk", "data": str}` | Each text chunk yielded (lines 217, 235, 257) | 20-char text slice |
| `{"type": "safety", "level": str}` | Pre-generation safety fires (line 134) | Risk level string |
| `{"type": "safety_override", "level": str}` | Post-generation safety fires (line 228) | Risk level string |
| `{"type": "done", "message_id": str}` | Successful completion (line 294) | Saved assistant message ID |

**Note on postprocessing mode:** When `POSTPROCESSING_ENABLED=true`, no `chunk`
events are sent during the LLM stream (the response is buffered). All chunks
are emitted after postprocessing, between the `start` and `done` events. In
legacy mode (`POSTPROCESSING_ENABLED=false`), chunks are streamed in real time.

### How LLM tokens are forwarded

`llm_client.stream()` (`llm_client.py` lines 25–32) opens an Anthropic SDK
streaming context manager and iterates `stream.text_stream` — the SDK's
incremental token iterator. In legacy (non-postprocessing) mode,
`conversation_service.py` yields each token directly to the client. In buffer
mode, tokens are accumulated into `full_response` and only yielded after
postprocessing.

There is no custom chunking during the live stream — one SDK text fragment
= one chunk event. The 20-character slicing only applies to the postprocessed
or safety-response paths (via `_chunk_text()`).

---

## Section 6: Memory and Insights — Orphaned or Live?

### Is `extract_memory_task` ever enqueued?

**No.** A codebase-wide grep for `enqueue_job` and `extract_memory_task` shows:

- `arq_worker.py` lines 26–53: task **defined**
- `arq_worker.py` line 184: task **registered** in `WorkerSettings.functions`
- `routers/messages.py` line 202: the only `enqueue_job` call in the codebase — enqueues `generate_conversation_title`, not `extract_memory_task`
- `services/conversation_service.py`: **no** `enqueue_job` call anywhere in the file

`memory_service.extract_and_store()` is never called from any route handler.
`memory_service.recall()` IS called in PATH A (`conversation_service.py` line
143) to retrieve memories, but since nothing writes to `memory_entries` via the
conversation flow, recall returns empty results for all users in production.

### Is `generate_insight_task` ever enqueued?

**No.** Same grep result — the task is defined and registered but no
`enqueue_job("generate_insight_task")` call exists anywhere in the codebase.

### Verdict

**ORPHANED — both tasks are silently broken in production today.**

`memory_entries` accumulates no new rows through normal conversation use.
`insights` accumulates no new rows. The `GET /api/v1/memory` and
`GET /api/v1/insights` endpoints return only data that may have been seeded
manually or in an earlier version of the code.

This means the memory recall at `conversation_service.py` line 143 always
returns `[]` in practice — it is fetching from an empty or stale table.

**Action required (not in this PR):** After PATH A port is stabilised, add an
`enqueue_job("extract_memory_task", ...)` call in `conversation_service.py`
after the `db.commit()` at line 282, passing `user_id`, `conversation_id`,
`persona_db.id`, `user_text`, and `full_response`. This restores memory
extraction without changing PATH A's streaming behaviour (the task runs
asynchronously in the ARQ worker).

`generate_insight_task` can remain orphaned for now — it requires at least 4
memory entries to produce output and can be wired up in a later PR after
memory extraction is live again.

---

## Section 7: Auto-Title Status

### Does PATH A generate titles?

**No.** A search of `conversation_service.py` and `routers/conversations.py`
finds no reference to `generate_conversation_title`, `conv.title`, or any
title-setting logic in the send-message flow.

`Conversation.title` is set to `None` at creation and never updated by PATH A.

### Where title generation lives today

`workers/arq_worker.py` line 100: `generate_conversation_title` task.
Enqueued only from `routers/messages.py` line 198–206 (PATH B), when
`conv.message_count == 3` (i.e., after the first user/assistant exchange,
accounting for the opening invocation).

### What must be added to PATH A

After the response is committed and `conv.message_count` is updated at
`conversation_service.py` lines 273–282, enqueue the title task when
`message_count == 3 and conv.title is None`. The ARQ queue is available
on `app.state.arq_queue` (see `main.py` line 40); PATH A's generator does not
have access to `app.state` directly — the router must pass the queue in,
or the enqueue must happen in the router after `StreamingResponse` completes.

**Open design question (not resolved in this PR):** `StreamingResponse` begins
yielding immediately; the generator runs until complete. The router function
returns the `StreamingResponse` object before the generator finishes. There
is no natural "after completion" hook in the router. Options:
- Pass `arq_queue` into `stream_response` as a parameter and enqueue from
  within the generator (after `db.commit()`).
- Add a background task via FastAPI's `BackgroundTasks`.

PATH B uses `request.app.state.arq_queue` (line 200) in the router body, which
runs before the response is returned — feasible because PATH B is non-streaming.
For PATH A, passing the queue into the generator is the cleanest approach.

---

## Section 8: Error Handling

### LLM call failure in PATH A

`llm_client.stream()` is called inside an `async for` loop in
`conversation_service.stream_response()` (lines 211–217). There is **no
try/except** around this call.

If the Anthropic API raises an exception mid-stream:
- The generator raises the exception internally.
- FastAPI's `StreamingResponse` catches it and closes the response body.
- The client sees the SSE connection close without a `{"type": "done"}` event.
- No error event is ever sent to the client.
- The user message has already been saved (line 199) but the assistant message
  is not saved (step 9 never reached).
- The database session is not explicitly committed or rolled back in this path.

### Retry logic

**None in PATH A.** `llm_client.stream()` makes a single attempt with no retry.

By contrast, PATH B's `llm_service.call_llm()` (`services/llm_service.py`
lines 76–105) retries up to 3 times with exponential backoff
(`asyncio.sleep(2**attempt)`) on `RateLimitError`, `APIStatusError >= 500`,
`APIConnectionError`, and `APITimeoutError`.

### Error response format compatibility

PATH A never returns `LLMErrorResponse` or `persona_voice`. For a 429 (rate
limit), it raises `HTTPException(status_code=429, detail={"message": ...,
"limit": ..., "plan": ...})`. There is no in-stream error event type for LLM
failure — the stream simply closes.

The `LLMErrorResponse` + `persona_voice` pattern is entirely PATH B specific
today (`schemas/__init__.py` lines 326-328, `services/persona_voice.py`).

### Insertion points for error handling port

Two changes needed:

1. **Retry logic:** Wrap the `llm_client.stream()` loop in a try/except and
   add retry logic similar to `llm_service.py` lines 76–105. Since streaming
   cannot be retried mid-stream, the retry must restart the entire generator
   or, more practically, retry only before the first chunk is yielded (i.e.,
   switch to buffer mode unconditionally and retry the buffer fill).

2. **In-stream error event:** Add a `{"type": "error", "error_code": str,
   "persona_voice": str}` event type and yield it before closing the generator
   on LLM failure. This requires access to the `persona` object (already loaded)
   and `get_error_voice()` (importable from `services/persona_voice.py` which
   is currently PATH B-only but can be shared).

**Open question for founder:** Should the rate-limit 429 response in PATH A
become a structured `LLMErrorResponse` JSON body (breaking change for any
client already parsing the plain dict), or should a new in-stream
`{"type": "rate_limited", ...}` event be added instead?

---

## Section 9: PATH B Deletion Scope

For each PATH B file, the table below shows what references it, what can be
deleted, and what must be retained or migrated.

### `routers/messages.py`

- Referenced by: `main.py` line 13 (import) and `tests/routers/test_messages.py`
- **Can delete** after port is complete and all 37 tests in `test_messages.py`
  are ported or retired.

### `services/llm_service.py`

- Imported by: `routers/messages.py` and `tests/services/test_llm_service.py`
- Contains: `call_llm()`, `LLMResponse`, `MODEL_FREE`, `MODEL_PRO`,
  `MEMORY_WINDOW_FREE`, `MEMORY_WINDOW_PRO`
- **Can delete** after `MODEL_FREE`/`MODEL_PRO` constants are copied into
  `conversation_service.py` (or a shared constants file).
- **9 tests** in `test_llm_service.py` would be deleted.

### `services/rate_limit_service.py`

**Cannot delete the entire file.** The file contains two distinct sections:

| Section | Function | Caller |
|---------|----------|--------|
| OTP/auth rate limiting (old) | `check_and_increment()` | `routers/auth.py` line 18 |
| Message rate limiting (C8) | `check_rate_limit()`, `RateLimitResult`, `FREE_DAILY_LIMIT_PER_PERSONA`, `next_utc_midnight()` | `routers/messages.py` only |

After the port, the C8 section (`check_rate_limit` and supporting
code at lines 47–104) will be **kept and reused by PATH A**. Only
`routers/messages.py`'s import of `rate_limit_service` as a module goes away.

**Tests:** `tests/services/test_rate_limit_service.py` tests both sections.
The `check_and_increment` tests must be kept. The `check_rate_limit` tests
must also be kept (they validate PATH A's new rate-limiting behaviour).
File cannot be deleted.

### `services/persona_voice.py`

- Imported by: `routers/messages.py` only
- **Recommended: keep and reuse in PATH A** for the in-stream error event
  (Section 8). The fallback dict and `get_error_voice()` function are short and
  self-contained. Importing it into `conversation_service.py` adds no new
  dependency.

### `services/tier_service.py`

- Imported by: `routers/messages.py`, `services/llm_service.py`,
  `services/rate_limit_service.py` (lazy import at line 77)
- **Cannot delete.** `get_user_tier()` will be imported by PATH A after the
  port (`conversation_service.py` or `routers/conversations.py`).
- `tests/services/test_tier_service.py` must be kept.

### `workers/arq_worker.py` — `generate_conversation_title` task

- Currently enqueued only from `routers/messages.py`
- **Keep and reuse.** After the port, PATH A will enqueue this task.
- The task itself uses a direct `anthropic.AsyncAnthropic` client
  (`arq_worker.py` line 120) with `claude-haiku-4-5-20251001` hardcoded
  (line 122) — no tier routing in title generation, which is correct.

### Schema classes (`schemas/__init__.py`)

| Class | Lines | Status |
|-------|-------|--------|
| `MessageCreateRequest` | 291–295 | Delete (PATH B input schema) |
| `MessageResponse` | 297–309 | Delete (PATH B response schema) |
| `ConversationSummary` | 311–319 | Delete (PATH B response schema) |
| `MessageEnvelope` | 321–323 | Delete (PATH B response schema) |
| `LLMErrorResponse` | 326–328 | **Keep and reuse** in PATH A error events |

### Tests

| File | Tests | Action |
|------|-------|--------|
| `tests/routers/test_messages.py` | 37 | Delete after port |
| `tests/services/test_llm_service.py` | 9 | Delete after `llm_service.py` is deleted |
| `tests/services/test_rate_limit_service.py` | Covers both sections | Keep — `check_rate_limit` tests validate PATH A |

---

## Section 10: Rituals Integration

### Call chain from `POST /rituals/{id}/start` to first persona message

1. **`routers/rituals.py` line 41:** `POST /api/v1/rituals/{ritual_id}/start`
2. **Line 67:** Calls `conversation_service.create(... ritual_id=ritual_id)` which creates a `Conversation` row with a `ritual_id` FK and inserts the persona's `opening_invocation` as the first assistant message.
3. **Lines 76–104:** The ritual router overrides the opening message with the Jinja2-rendered `ritual.prompt_template` (replacing the generic opening invocation with the ritual-specific prompt).
4. **Line 107:** A `UserRitualCompletion` row is inserted.
5. The router returns the `ConversationOut` with `title=ritual.name`.
6. The user then sends messages to **`POST /api/v1/conversations/{id}/messages`** (PATH A), using the `conversation_id` returned in step 5.

### Does the ritual flow use PATH A's `stream_response`?

**Yes.** There is no separate streaming path for rituals. After the ritual
conversation is created, all user messages flow through PATH A's `send_message`
handler and `conversation_service.stream_response()`. The `stream_response`
function has no awareness of `ritual_id` — it operates purely on
`conversation_id`.

### Tier routing impact on ritual messages

**Yes — ritual messages will automatically pick up tier routing after the port.**
Since ritual messages go through PATH A's `stream_response`, adding `user_plan`-
based model selection (Section 1) will apply to ritual messages as well. A pro
user's ritual conversations will use Sonnet; a free user's ritual conversations
will use Haiku. This is the desired outcome.

### Rate limit impact on ritual messages

**Open question — requires founder decision.**

After the port, PATH A will call `rate_limit_service.check_rate_limit(user_id,
persona_id)`. Ritual messages will count against the per-persona daily limit
(5/day for free tier). Current behaviour: ritual messages count against the
cross-persona daily limit (10/day for free tier).

**Concrete scenario:** A free user starts a ritual with Marcus Aurelius and
sends 5 messages. They are then blocked from sending any further messages to
Marcus Aurelius that day — including non-ritual conversations. They could still
switch to a different persona.

Two options:
- **Option A (simplest):** Count ritual messages against the daily limit. Free
  users have 5 ritual messages per persona per day.
- **Option B (ritual exemption):** Pass `skip_rate_limit=True` when the
  conversation has a `ritual_id`. Requires reading `conv.ritual_id` before the
  rate-limit check in the router (the row is already loaded at that point).

Recommend surfacing to founder before implementing. The port should not silently
change ritual message limits without a deliberate decision.

---

## Section 11: Recommended Porting Sequence

### Prerequisite: create shared module for PATH B constants

Before any port PR, extract `MODEL_FREE`, `MODEL_PRO`, `MEMORY_WINDOW_FREE`,
`MEMORY_WINDOW_PRO` from `services/llm_service.py` into a constants file or
directly into `conversation_service.py`. This avoids importing from a file
that will eventually be deleted.

### C-RECON-3: Tier-aware model selection in PATH A

**Changes:**
- `services/conversation_service.py`: Add model resolution from `user_plan`
  before the `llm_client.stream()` calls (lines 211, 215). Pass `model=` arg.
- `services/conversation_service.py`: Add tier-aware history window (line 187).
- No router changes needed — `user_plan` already flows in.

**Effort:** Small (2 lines of logic, 2 call sites).
**Dependencies:** None.
**Tests to add:** Confirm Haiku model used for free-tier calls; Sonnet for pro.

### C-RECON-4: Per-persona rate limit in PATH A

**Changes:**
- `routers/conversations.py`: Replace lines 141–163 with a call to
  `rate_limit_service.check_rate_limit()`.
- Add `X-RateLimit-*` headers to the `StreamingResponse` (requires wrapping
  or restructuring since headers must be set before the body starts).
- Decide ritual rate-limit policy (Section 10) before implementing.

**Effort:** Medium (rate limit logic is straightforward; SSE header timing
requires care — headers must be set at `StreamingResponse` construction time,
not inside the generator).
**Dependencies:** Founder decision on ritual rate-limit policy.
**Tests to add:** Free-tier blocked at 5/persona; pro unlimited; headers present.

### C-RECON-5: Auto-title generation in PATH A

**Changes:**
- `routers/conversations.py` or `services/conversation_service.py`: Pass
  `arq_queue` into `stream_response` and enqueue `generate_conversation_title`
  after `db.commit()` when `message_count == 3 and title is None`.
- `main.py`: No change needed — `arq_queue` is already on `app.state`.

**Effort:** Small (same pattern as PATH B).
**Dependencies:** C-RECON-3 (must know path is live before adding side effects).
**Tests to add:** Title enqueued on 3rd message; not enqueued otherwise.

### C-RECON-6: In-stream error handling + persona voice

**Changes:**
- `services/conversation_service.py`: Wrap `llm_client.stream()` calls in
  try/except; yield `{"type": "error", "error_code": ..., "persona_voice": ...}`
  on failure; add retry logic (buffer mode required for retry to be meaningful).
- Import `get_error_voice` from `services/persona_voice.py` into
  `conversation_service.py`.
- Add `LLMErrorResponse` (or equivalent) for the rate-limit 429 response
  in `routers/conversations.py` (pending founder decision on format).

**Effort:** Medium (retry logic in a streaming generator is non-trivial;
buffer mode simplifies this but changes streaming behaviour).
**Dependencies:** C-RECON-3, C-RECON-4.
**Tests to add:** LLM timeout → error event; retries exhausted → error event.

### C-RECON-7: Memory extraction wiring

**Changes:**
- `services/conversation_service.py`: After `db.commit()` (line 282), enqueue
  `extract_memory_task` with user_id, conversation_id, persona_id, user_text,
  full_response.

**Effort:** Small (same ARQ pattern as title generation).
**Dependencies:** C-RECON-5 (ARQ queue passing already established).
**Tests to add:** Task enqueued after each successful exchange.

### C-RECON-8: PATH B deletion

**Changes:**
- Delete `routers/messages.py`
- Delete `services/llm_service.py`
- Remove PATH B-only schemas from `schemas/__init__.py`
- Remove PATH B router from `main.py`
- Delete `tests/routers/test_messages.py`
- Delete `tests/services/test_llm_service.py`
- Remove `DAILY_LIMITS` dict from `routers/conversations.py`

**Effort:** Small (deletions and cleanup).
**Dependencies:** All preceding ports complete and deployed. Frontend confirmed
not consuming PATH B (`POST /api/v1/messages`) — **verify with frontend team
before this PR.**
**Tests:** Confirm `test_rate_limit_service.py` passes (kept), `test_tier_service.py`
passes (kept).

### Summary table

| PR | Change | Effort | Depends on |
|----|--------|--------|------------|
| C-RECON-3 | Tier routing (model + history window) | Small | — |
| C-RECON-4 | Per-persona rate limit + headers | Medium | Founder decision on rituals |
| C-RECON-5 | Auto-title generation | Small | C-RECON-3 |
| C-RECON-6 | Error handling + persona voice | Medium | C-RECON-3, C-RECON-4 |
| C-RECON-7 | Memory extraction wiring | Small | C-RECON-5 |
| C-RECON-8 | PATH B deletion | Small | All above + frontend confirmation |

---

*Report generated by Claude Code as part of the C-RECON-2 investigation task.
No source files were modified. All findings are based on reading code on branch
`chore/c-recon-2-path-a-investigation` at HEAD of main (commit `8514383`).*
