# PHILOSOPHER — Project State v9

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v9 = v8 baseline (2026-05-13/14) + 2026-05-16 session delta (Block C backend shipped; C-RECON reconciliation series completed; PATH B deleted; single canonical send-message endpoint confirmed) + 2026-05-16/17 session delta (Block C frontend complete; C5a/b/c/d merged; C3a RAG infrastructure merged; migration 008 deployed and verified live) + 2026-05-18 session delta (5 PRs shipped + 1 hotfix; ~2h production fire; 9/9 personas functional; auth race promoted to P0; D1 + A0 structural gaps identified).**
>
> **Generated:** 2026-05-16 (post-reconciliation)
>
> **Last updated:** 2026-05-18 (5 PRs + hotfix merged; production fire incident logged; structural gaps D1 + A0 identified; auth race promoted to P0; priority reshuffle captured in IMPLEMENTATION_BACKLOG_v9.md)

> **v9 conflict resolution rule:** Where v9 conflicts with v8, v9 wins. Production reality always wins over docs.

---

**Repo:** https://github.com/Nckoutras/Philosopher (public)
**Branch:** main
**Live deployment (canonical):** https://thinkalike.netlify.app
**Custom domain (DNS in progress):** https://thegreatminds.app
**Backend:** https://philosopher-api-z9l9.onrender.com

---

## 1. Stack (locked)

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 (App Router) · TypeScript · Tailwind |
| Backend | FastAPI · Python 3.12 · SQLAlchemy 2.0 async · asyncpg |
| Database | PostgreSQL 17 (Supabase, eu-west-1, paid) |
| Queue/Cache | Redis (Upstash) + ARQ + APScheduler |
| LLM | Anthropic Claude — **now wired and live for chat (Block C backend complete)** |
| Embeddings | OpenAI text-embedding-3-small (schema + client wired; corpus ingested 2026-05-17 — 2476 chunks via C3b) |
| Auth | Passwordless OTP via Resend; JWT issuance with cookie + localStorage |
| Billing | Stripe (scaffolded, NOT wired) |
| Email | Resend (free tier, test sender — custom domain in progress) |
| Analytics | PostHog (configured, unused) |

### Hosting

- **Frontend (canonical):** Netlify (project: thinkalike, URL: thinkalike.netlify.app). Auto-deploys from main.
- ~~Frontend (legacy): Vercel~~ — **DISCONNECTED 2026-05-10**
- **Backend:** Render (free tier — `WEB_CONCURRENCY=1`, 15-min idle cold-start, mitigated by external ping bot; upgrade decision pending ~$7/mo)
- **Database:** Supabase project `plecolxlzshkfvybszgs` (eu-west-1, paid). DATABASE_URL points to `aws-0-eu-west-1.pooler.supabase.com:5432`. Direct asyncpg connection — NOT Supabase Data API (so the May 30 2026 Data API default change does NOT affect this project).
- **Cache (Redis):** Upstash `philosopher-prod` (eu-west-1, free tier). REDIS_URL set; ARQ + APScheduler operational. OTP rate limiter verified working 2026-05-10. Message rate limiter added in C-RECON-4.
- **Email (Resend):** RESEND_API_KEY + FROM_EMAIL set. Currently `Great Minds <onboarding@resend.dev>` (test sender). 🟡 Custom domain `thegreatminds.app` DNS setup IN PROGRESS.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app** (canonical)
- Last production deploy: **2026-05-17** — C3a RAG infrastructure (migration 008 + scripts) merged + verified via Supabase MCP. C3b ingestion run executed via Render shell same day; `source_chunks` populated with 2476 entries across 7 personas.
- **Has paying users:** No
- **Has free trial users:** No

### Block A — Authentication: FULLY CLOSED 2026-05-10 (5/5)

Unchanged from v8. See v8 §2 Block A table for detail.

### Block B — Onboarding spine: SHIPPED 2026-05-13 (6/6 functional, polish PR pending)

Unchanged from v8. Visual closure still pending consolidated polish PR. See v8 §2 Block B table for detail.

### Block C — Chat backend: COMPLETE 2026-05-16 (8/8 backend items)

All backend infrastructure for chat is live. **Block C frontend is also complete (C5a/b/c/d merged 2026-05-16/17). RAG infrastructure (C3a) is live (migration 008). C3b corpus ingestion operational run is pending (founder action).**

| Item | PR | Status |
|---|---|---|
| C1 — Schema additions (deleted_at, model_used, daily_usage) | #50 | ✅ live |
| C2 — LLM service (PATH B, non-streaming) | #51 | ✅ shipped; **DELETED in C-RECON-8** (features ported to PATH A) |
| C4 — Message endpoint (PATH B, non-streaming) | #52 | ✅ shipped; **DELETED in C-RECON-8** (features ported to PATH A) |
| C8 — Rate limiting (PATH B) | #53 | ✅ shipped; **ported to PATH A in C-RECON-4** |
| C-RECON-3 — Tier-aware model selection in PATH A | #55 | ✅ live |
| C-RECON-4 — Per-persona rate limit + daily_usage increment in PATH A | #56 | ✅ live |
| C-RECON-5 — Auto-title generation in PATH A | #57 | ✅ live |
| C-RECON-6 — LLM retry logic + persona-voiced errors in PATH A | #58 | ✅ live |
| C-RECON-7 — Memory extraction wiring in PATH A | #59 | ✅ live |
| C-RECON-8 — PATH B deletion | #60 | ✅ live |

**All Block C items complete.** C3b COMPLETE (2026-05-17) — 2476 chunks ingested across 7 personas. C5 and C3a also complete.

### Other systems

- **Stripe wired:** No (calendar gate of 2026-05-11 passed; verify status before Block H work)
- **User validation done:** No (UAT planned with ≥2/5 spontaneous "I'd pay" criterion)
- **`PHENOMENOLOGY_BRIDGE_ENABLED` flag:** Verified active 2026-05-04/05; current state in Render env to confirm before launch
- **API plan upgrade:** Free tier still. Decision pending.
- **Database:** Paid tier. RLS disabled on all public tables. Mitigation: frontend exclusively goes through FastAPI; anon key NOT in frontend bundle.

---

## 3. Personas registered

**9 personas in production. All have full Section 5.7 character config + bio + portrait.** Unchanged from v8.

Free tier: Marcus Aurelius, Socrates, Lao Tzu
Pro tier: Simone de Beauvoir, Epictetus, Sigmund Freud, Carl Jung, Oscar Wilde, Niccolò Machiavelli

See v8 §3 for full table and affinity weight signatures.

---

## 4. Database schema

### Migrations applied (chronological)

| Rev | Description | Applied | PR |
|---|---|---|---|
| 001 | initial | Pre-Block-A | — |
| 002 | otp_codes table | 2026-05-09 | #18 |
| 003 | disclaimer_versions + disclaimer_acceptances + v1.0 seed | 2026-05-10 | #24 |
| 004 | user_preferences (wide table) | 2026-05-13 | #33 |
| 005 | personas.bio + personas.portrait_url | 2026-05-13 | #42 |
| 006 | 3 new personas + Jung bio/portrait update | 2026-05-13 | #43 + #44 hotfix |
| **007** | **Block C schema: conversations.deleted_at, messages.model_used, daily_usage table** | **2026-05-16** | **#50** |
| **008** | **HNSW vector indexes + source_chunks.chunk_index column** | **2026-05-17** | **C3a** |

**alembic_version = `008_hnsw_vector_indexes`** (as of 2026-05-17 session end)

### New tables added in migration 007

```
daily_usage             (NEW 2026-05-16, migration 007)
                        per (user_id, persona_id, usage_date) counter
                        message_count: int, default 0
                        Used by: rate_limit_service.check_rate_limit()
                        Populated by: conversation_service.stream_response()
                        via SQL UPDATE after each successful message
```

### New columns added in migration 007

```
conversations.deleted_at   TIMESTAMP WITH TIME ZONE, nullable
                            Soft-delete support; not yet surfaced in UI

messages.model_used        VARCHAR, nullable
                            Populated on every assistant message by stream_response()
                            Records "claude-haiku-4-5-20251001" or "claude-sonnet-4-6"
```

### New columns added in migration 008

```
source_chunks.chunk_index  INTEGER, nullable
                            Disambiguation index for auto-chunked documents
                            NULL for legacy/curated chunks (e.g. curated_chunks.py entries)
                            Used in UNIQUE PARTIAL index for idempotent ingestion
```

### New indexes added in migration 008

```
ix_source_chunks_embedding_hnsw_cosine      HNSW on source_chunks.embedding
                                             (m=16, ef_construction=64, vector_cosine_ops)
                                             Verified live via Supabase MCP 2026-05-17

ix_memory_entries_embedding_hnsw_cosine     HNSW on memory_entries.embedding
                                             (m=16, ef_construction=64, vector_cosine_ops)
                                             Verified live via Supabase MCP 2026-05-17

uq_source_chunks_persona_title_chunk        UNIQUE PARTIAL on (persona_id, source_title, chunk_index)
                                             WHERE chunk_index IS NOT NULL
                                             Prevents duplicate auto-ingested chunks on re-run
```

pgvector version verified: **0.8.0** (HNSW supported from 0.5.0+; confirmed before merge).

### Live database state (2026-05-17 session end)

```
alembic_version:        008_hnsw_vector_indexes ✓ (verified via Supabase MCP)
users count:            2 (founder, freetester)
personas count:         9 (all active, all with bio + portrait + error_messages)
conversations:          50+ (from prior engine sessions + testing)
messages:               139+ (from prior engine sessions + testing)
daily_usage rows:       populated during test runs
safety_events:          populated (safety pipeline active since Phase 4)
memory_entries:         wiring active (extract_memory_task queued after each response)
                        not yet accumulating with real users; 0 organic entries
source_chunks:          2476 chunks ingested across 7 personas (C3b complete 2026-05-17):
                        socrates: 1021 chunks (Apology + Crito + Phaedo + Republic)
                        sigmund_freud: 477 chunks (Dreams + Psychopathology)
                        oscar_wilde: 352 chunks (Dorian Gray + Earnest + De Profundis)
                        marcus_aurelius: 231 chunks (212 Long 1862 + 19 curated)
                        epictetus: 216 chunks (Discourses + Enchiridion)
                        niccolo_machiavelli: 146 chunks (The Prince)
                        lao_tzu: 33 chunks (Tao Te Ching)
                        carl_jung: 0 chunks (excluded per Decision #7)
                        simone_de_beauvoir: 0 chunks (excluded per Decision #7)
```

### Table population status

| Table | Status | Notes |
|---|---|---|
| `daily_usage` | ✅ Actively populated | Incremented per successful non-ritual non-admin message in stream_response() |
| `messages.model_used` | ✅ Actively populated | Set on every assistant message |
| `safety_events` | ✅ Actively populated | Safety pipeline has been live since Phase 4 |
| `memory_entries` | 🟡 Wired but not yet accumulating | extract_memory_task ARQ job is queued; no organic user sessions yet |
| `conversations.deleted_at` | ❌ Not yet used | Soft-delete endpoint not exposed; field exists for future use |
| `messages.message_id` in safety_events | 🟡 Always NULL | Minor schema gap; safety events log correctly but message FK not set |

### RLS state

**RLS DISABLED on all public tables.** Mitigation: frontend goes exclusively through the FastAPI gateway; no Supabase anon key is present in the frontend bundle.

⚠️ **Forward-looking warning:** If a future change ever introduces Supabase anon key on the frontend, RLS becomes a critical vulnerability immediately. Always add explicit RLS policies BEFORE any such change merges.

---

## 5. Backend endpoints

```
POST /api/v1/auth/register             (legacy — passwordless flow preferred)
POST /api/v1/auth/login                (legacy — passwordless flow preferred)
GET  /api/v1/auth/me                   (auth)
POST /api/v1/auth/otp/request          (public, rate-limited via Redis)
POST /api/v1/auth/otp/verify           (public)

GET  /api/v1/disclaimer/current        (public)
POST /api/v1/disclaimer/accept         (auth)

GET  /api/v1/personas                  (public — returns all 9 active personas)

GET  /api/v1/preferences               (auth — returns user's saved preferences or 404)
POST /api/v1/preferences               (auth — save/update themes + need_most)
GET  /api/v1/preferences/matches       (auth — returns top-3 matched personas)

POST /api/v1/conversations             (auth — create conversation)
GET  /api/v1/conversations             (auth — list conversations, max 50)
GET  /api/v1/conversations/{id}/messages   (auth — fetch message history)
POST /api/v1/conversations/{id}/messages   ← CANONICAL SEND-MESSAGE (SSE streaming)
DELETE /api/v1/conversations/{id}          (auth — soft delete)

GET  /health                           (public)
```

**There is exactly ONE send-message endpoint.** `POST /api/v1/conversations/{id}/messages` is the canonical SSE streaming path. The parallel `POST /api/v1/messages` endpoint (PATH B) was deleted in C-RECON-8 (PR #60).

---

## 6. Send-message architecture (PATH A — canonical)

### Endpoint
```
POST /api/v1/conversations/{conversation_id}/messages
Content-Type: application/json
Authorization: Bearer <jwt>

Response: text/event-stream (SSE)
```

### Full feature set (as of C-RECON-8)

The PATH A streaming endpoint now has all features from the original C4/C8 build:

1. **Ownership verification** — confirms conversation belongs to requesting user
2. **Admin bypass** — `user.is_admin` check in router skips rate limit
3. **Ritual exemption** — `conv.ritual_id is not None` skips rate limit
4. **Rate limiting** — `rate_limit_service.check_rate_limit(db, user_id, persona_id)` checks `daily_usage` table; free users limited to 5 messages/persona/UTC day; pro users bypass; 429 returns `LLMErrorResponse` with persona-voiced message
5. **SSE rate limit headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` on all responses
6. **Safety input check** — `safety_service.check_input()` before LLM call; suppresses persona if flagged
7. **RAG retrieval** — `retrieval_service.retrieve()` fetches relevant source chunks (if corpus exists)
8. **Memory recall** — `memory_service.retrieve()` fetches relevant memory entries
9. **Phenomenology bridge** — `phenomenology_bridge_service` enriches context if `PHENOMENOLOGY_BRIDGE_ENABLED=true`
10. **Tier-aware model selection** — Haiku for free users, Sonnet for pro/premium
11. **Tier-aware memory window** — 5 messages for free, 20 for pro/premium
12. **LLM streaming** — native SSE via `llm_client.stream()`
13. **LLM retry logic** — 3 attempts with exponential backoff (0s, 2s, 4s); handles RateLimitError, APIStatusError 5xx, APIConnectionError, APITimeoutError; persona-voiced error event on final failure
14. **Safety output check** — `safety_service.check_output()` after streaming
15. **Postprocessing** — `regenerate_or_trim()` if enabled
16. **daily_usage increment** — SQL UPDATE after successful response; increments message_count for free users
17. **Auto-title generation** — ARQ task `generate_conversation_title` dispatched when `message_count == 0` (first message in conversation); checks SQL-level count to avoid race
18. **Memory extraction** — ARQ task `extract_memory_task` dispatched after each response; wired but not yet accumulating (no organic users)
19. **Analytics tracking** — PostHog events for message_sent, safety events

### Persona-voiced error messages

When the LLM is unavailable, `get_error_voice(persona, "llm_unavailable")` is called. This function reads `persona.config["error_messages"]["llm_unavailable"]` from the ORM `Persona` model (DB row).

**Known issue:** The function works correctly when called with the ORM `Persona` object (which has a `.config` dict attribute). In the streaming path, this is what is passed. The 9 persona-voiced messages ARE stored in the DB and are accessible.

**However:** A separate issue exists for `PersonaConfig` objects (the in-memory Python dataclass from `personas/_base.py`) — these do NOT have a `config` attribute, so if `get_error_voice` were called with a `PersonaConfig` instead of an ORM `Persona`, it would fall back to the generic message. This does not currently affect the streaming path (which passes the ORM object), but is a latent confusion risk. See tech debt item #3.

---

## 7. Persona error messages

### Catalog (stored in `personas.config['error_messages']['llm_unavailable']`)

All 9 personas have `llm_unavailable` error messages set in the DB `personas.config` JSONB:

| Persona | Message |
|---|---|
| Socrates | "My thought pauses. Will you try again shortly?" |
| Marcus Aurelius | "A pause beyond our control. Try again presently." |
| Lao Tzu | "Even flowing water sometimes stills. Try again shortly." |
| Carl Jung | "The unconscious requires patience. Return in a moment." |
| Epictetus | "Some things are not in our power. Try again." |
| Niccolò Machiavelli | "The state of things forbids it. Try again." |
| Oscar Wilde | "A momentary silence — how unfashionable. Return shortly." |
| Sigmund Freud | "The session is briefly interrupted. Try again shortly." |
| Simone de Beauvoir | "A brief silence in our dialogue. Return shortly." |

These messages are stored in DB and ARE accessible via `persona.config["error_messages"]["llm_unavailable"]` on the ORM `Persona` object. They are read by `get_error_voice()` in `services/persona_voice.py`.

The error event is currently yielded only as an SSE event to the frontend (`type: "error"`, `error_code: "llm_unavailable"`, `persona_voice: "<message>"`). Frontend must implement rendering. See C5 requirements in backlog.

---

## 8. LLM provider validation

**Validation date:** 2026-05-15 (Workbench A/B test using Section 5.7 framework prompts)

| Model | Test | Result |
|---|---|---|
| claude-sonnet-4-6 (Sonnet 4.6) | 24/24 character voice fidelity | ✅ Meets quality bar |
| claude-haiku-4-5-20251001 (Haiku 4.5) | 23/24 character voice fidelity | ✅ Meets quality bar |

Both models pass the production quality bar. The 1/24 gap confirms that Haiku is acceptable for free tier without meaningful degradation of persona experience. This result locked Decision #1 (see §9).

---

## 9. Locked decisions (as of 2026-05-16)

These decisions are final for v1 launch. Do not reopen without explicit founder decision.

| # | Decision | Detail | Rationale |
|---|---|---|---|
| 1 | **LLM Tier Routing** | Free → Haiku 4.5 (`claude-haiku-4-5-20251001`); Pro/Premium → Sonnet 4.6 (`claude-sonnet-4-6`) | Workbench A/B test 2026-05-15: 23/24 vs 24/24 character fidelity. Cost difference justifies tier split. |
| 2 | **RAG Architecture** | pgvector in Supabase, `vector(1536)` for OpenAI `text-embedding-3-small` | Simpler ops, already paying for Supabase; avoid separate vector DB service. |
| 3 | **Streaming Protocol** | SSE via Anthropic SDK native support | No bidirectional needs; SSE simpler than WebSocket; native SDK support. |
| 4 | **Memory Window** | Free users: 5 messages; Pro/Premium: 20 messages | Cost control for free tier; richer context for paid users. |
| 5 | **Free Tier Limits** | 5 messages per persona per UTC day (cross-persona model rejected) | Per-persona scope encourages exploration across the 3 free personas. Cross-persona pooling would disincentivize trying other philosophers. |
| 6 | **Safety Architecture** | 3-layer planned (regex input + regex output + LLM classifier on triggers). Currently **2 layers** in production. LLM classifier deferred. | Full 3-layer estimated cost: ~$0.012/Pro user/month. Deferred pending usage data. |
| 7 | **Jung & Beauvoir Copyright** | Ship with `system_fragment` only, NO RAG corpus. | Jung copyrighted until 2031; Beauvoir until 2056. RAG from primary texts legally risky. Pro users get access with documented quality limitation. Pricing implication deferred. |
| 8 | **Pricing Draft** | $14.99/month · $129/year (~$10.75/month effective) | Mentor pricing analysis: ChatGPT Plus $20, Claude Pro $20, Replika $19.99 — $14.99 sits below ceiling. At 1.5% conversion, 100 free users at $0.18 avg cost → net positive only at $14.99+. Pending validation via landing page waitlist test before Stripe wiring. |
| 9 | **Ritual Rate Limit Policy** | Ritual conversations (`ritual_id IS NOT NULL`) are **exempt** from per-persona daily rate limit. | Rituals are bounded, essential for free→pro conversion; capping them would break the core engagement hook. |
| 10 | **Admin Bypass Placement** | `is_admin` check stays in the router (`routers/conversations.py`), NOT inside `rate_limit_service.check_rate_limit()`. The `check_rate_limit()` function remains pure (takes `user_id` + `persona_id` only). Router decides whether to call it. | Keeps service layer pure and testable; policy belongs in the transport layer. |

---

## 10. Reconciliation history

On 2026-05-16 a routine audit (`C-RECON-1`) discovered that Block C had shipped two parallel send-message paths:

- **PATH A** (`POST /api/v1/conversations/{id}/messages`): the existing SSE streaming endpoint from prior engine work, with safety pipeline, RAG retrieval, memory recall, phenomenology bridge, postprocessing, and analytics.
- **PATH B** (`POST /api/v1/messages`): the new C4/C8 non-streaming endpoint, with tier routing, per-persona rate limit, auto-title, and persona-voiced errors.

Neither path had all features. The two paths used different LLM service layers (`llm_client.py` vs `llm_service.py`), different auth helpers, and different rate-limiting strategies.

The reconciliation decision (C-RECON-2 investigation) was to adopt PATH A as the canonical path and port PATH B's four features into it, then delete PATH B entirely. This preserved the richer existing infrastructure while adding the new capabilities.

### Reconciliation PRs (all merged 2026-05-16)

| PR | Description | Key change |
|---|---|---|
| CLAUDE.md (#54) | Investigation protocol added | Mandatory pre-work investigation protocol for all future work |
| C-RECON-3 (#55) | Tier-aware model + memory window | Haiku/Sonnet selection, MEMORY_WINDOW_FREE/PRO limits ported into PATH A |
| C-RECON-4 (#56) | Rate limit + daily_usage increment | Per-persona 5/day limit wired into router; daily_usage SQL update in stream_response |
| C-RECON-5 (#57) | Auto-title generation | generate_conversation_title ARQ task dispatched on first message |
| C-RECON-6 (#58) | LLM retry + persona-voiced errors | 3-attempt backoff; get_error_voice() called on final failure |
| C-RECON-7 (#59) | Memory extraction wiring | extract_memory_task ARQ task dispatched after each response |
| C-RECON-8 (#60) | PATH B deletion | routers/messages.py, services/llm_service.py, 4 test files deleted; schemas cleaned; main.py updated; MODEL_FREE/MODEL_PRO constants relocated to conversation_service.py |

### What the investigation protocol caught

The Pre-Work Investigation Protocol (CLAUDE.md, added during reconciliation) caught 4 real bugs during the port that would otherwise have shipped silently:

1. **PATH A SQL-level UPDATE for message_count** (C-RECON-5): PATH A uses a SQL UPDATE to increment `message_count`, not an ORM refresh. The auto-title trigger condition `message_count == 0` must be checked BEFORE the UPDATE fires, not after. Getting this wrong would have caused auto-title to never trigger on the first message.
2. **extract_memory_task signature** (C-RECON-7): The ARQ task requires 7 arguments, not 2. A guess-based implementation would have produced silent ARQ task failures.
3. **PersonaConfig has no `config` attribute** (C-RECON-6): The in-memory `PersonaConfig` dataclass (from `personas/_base.py`) does NOT have a `.config` dict. Calling `get_error_voice(persona_config, ...)` would silently fall back to generic messages, not the 9 persona-voiced ones stored in DB. The port correctly uses the ORM `Persona` object instead.
4. **ANTHROPIC_MODEL in config.py points to stale model** (C-RECON-2): `config.ANTHROPIC_MODEL` was hardcoded to `claude-sonnet-4-20250514` (old Sonnet 4). The reconciliation confirmed that `conversation_service.py` does NOT read this constant — it uses `MODEL_FREE`/`MODEL_PRO` directly. The config constant is now an orphan but was identified before it could mislead future work.

---

## 11. Session metrics

### 2026-05-16 session

| Metric | Value |
|---|---|
| Test count progression | 146 (start of C1) → 275 (peak with PATH B tests) → **229 (final after C-RECON-8)** |
| Tests removed (PATH B) | 46 (37 from test_messages.py + 9 from test_llm_service.py) |
| Schema version | 007_block_c_schema |
| PRs merged | 10 (C1, C2, C4, C8, CLAUDE.md, C-RECON-3 through C-RECON-8) |
| Total PRs in repo | ~60 |
| Architectural decisions locked | 10 |
| Tech debt items captured | 8 (see IMPLEMENTATION_BACKLOG_v9.md) |
| Database state | 50 conversations, 139 messages, 9/9 personas with error messages, memory wiring active |

### 2026-05-16/17 session (C5d + C3a)

| Metric | Value |
|---|---|
| Backend test count | 229 → **292** (63 new C3a tests) |
| Frontend test count | **43 total** (13 new in C5d; prior C5a/b/c tests included) |
| Schema version | **008_hnsw_vector_indexes** (migration 008 deployed and verified via Supabase MCP) |
| C5d PR | #65 — 1128 lines, 13 files |
| C3a PRs | d1a7942 (HNSW + ingestion script) + f78d0f3 (curated chunks recovery) |
| CLAUDE.md Rule 5 violation | `apps/api/db/ingest_sources.py` (408 lines) silently deleted; reconciled via Path C recovery commit f78d0f3 |
| Source chunks loaded | 2476 chunks across 7 personas (C3b complete 2026-05-17); see §2 / §4 for per-persona breakdown |

### 2026-05-17 session metrics

**PRs merged (3)**:
- C5d — Conversation list (F6) + existing conversation route + tab bar. 13 files, +1128 lines, 13 new frontend tests.
- C3a — RAG infrastructure (HNSW indexes + ingestion script + curated chunks recovery). 14 files, +1615 / -409 lines, 63 new backend tests. Includes CLAUDE.md Rule 5 reconciliation commit `f78d0f3`.
- docs sync #1 — v9 docs updated to reflect C5a–d and C3a (commit `53b4f5c` on branch `docs/sync-after-c5d-c3a`).

**Production operational events (1)**:
- C3b — Corpus ingestion executed via Render shell. 2476 chunks ingested across 7 personas. Zero errors. Idempotency verified. ~$0.025 OpenAI cost. `retrieval_service` now live.

**Test count evolution**:
- Backend: 229 → 292 (+63 from C3a + recovery)
- Frontend: 30 → 43 (+13 from C5d)
- Total repo: 259 → 335

**Cumulative since v9 baseline (2026-05-16)**:
- 13 PRs merged (10 backend recon on 2026-05-16 + 3 today)
- Block C frontend: 0% → 100% complete
- RAG infrastructure: schema-only → fully populated production corpus
- 1 CLAUDE.md Rule 5 violation caught, surfaced, reconciled (Path C)

**Cross-AI doc audit pattern adopted (2026-05-17)**:
ChatGPT audit of v9 docs after first docs sync surfaced 8 stale references that Claude (chat) missed during approval. Pattern: after any significant doc change, run cross-AI audit before treating docs as authoritative. ChatGPT's audit + Claude's verification = belt-and-braces.

---

## 12. Known bugs (active — carried from v8 + new from today)

### Carried from v8 (Block B polish PR pending)

See v8 §6 for BUG-001 through BUG-009. All still open; none regressed by today's backend work.

### New from 2026-05-16 session

| ID | Description | Severity | Notes |
|---|---|---|---|
| BUG-010 | Persona-voiced error messages — ~~UI not yet built~~ CLOSED | 🟢 CLOSED 2026-05-17 | Implemented in C5b (`ErrorMessage.tsx`). `useStream.tsx` propagates `persona_voice`. Pending real-device smoke test. |
| BUG-011 | `safety_events.message_id` always NULL | 🟢 Polish | Safety events log correctly; FK not wired. Minor cleanup. |

### BUG-010 — CLOSED (2026-05-17)

Previously: "Persona-voiced error messages reachable via SSE `type:error` event but frontend renders nothing — UI not yet built. Resolves when C5 ships."

Resolution: Persona-voiced SSE error rendering implemented in C5b (`components/chat/ErrorMessage.tsx`). `useStream.tsx` now propagates `persona_voice` field on error events (was RF-01 in C5a investigation — fixed). Verification pending: confirm during real-device production smoke test that `type:error` with `llm_unavailable` correctly displays persona-voiced copy and is not persisted to message history.

---

### C5 verification status (2026-05-17)

Implementation complete (C5a–d merged), Netlify deployed, frontend tests passing (43). Real-device production smoke test: **NOT YET PERFORMED**.

Required smoke checks before treating as fully validated:
- [ ] Create new conversation from persona detail (B5/B6)
- [ ] Send first message and receive complete SSE stream
- [ ] Receive `done` event with model_used + token counts
- [ ] Reopen existing conversation from F6 list
- [ ] Verify 429 paywall modal triggers at 5th message
- [ ] Verify safety response rendering (C7 spec)
- [ ] Verify persona-voiced LLM error rendering (BUG-010 verification)
- [ ] Verify no duplicate conversation created per message
- [ ] Verify auto-title appears (~5s after first message — async)
- [ ] Real iOS Safari walkthrough (not desktop Chrome)

Regression risk: medium until verified on real device. Block B's mobile-only findings (BUG-001–009) caution against trusting desktop verification alone.

---

## 13. Test credentials

Unchanged from v8. See v8 §7.

---

## 14. Environment variables

### Backend (Render)

```
DATABASE_URL                  (Supabase pooler)
REDIS_URL                     (Upstash)
RESEND_API_KEY                (set)
FROM_EMAIL                    "Great Minds <onboarding@resend.dev>"
                              (test sender — switch to thegreatminds.app post-DNS)
JWT_SECRET                    (set)
ANTHROPIC_API_KEY             (set — now actively used for chat)
PHENOMENOLOGY_BRIDGE_ENABLED  (was true 2026-05-04/05; current state unverified)

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"   ⚠️ ORPHANED CONSTANT
                              This config.py default is NOT read by
                              conversation_service.py, which uses
                              MODEL_FREE/MODEL_PRO constants directly.
                              Update or remove before it misleads anyone.
```

### Frontend (Netlify)

Unchanged from v8. See v8 §8.

---

## 15. Key file paths (production codebase)

### Backend (apps/api/)

- `main.py` — FastAPI app + router mounting (messages_router REMOVED in C-RECON-8)
- `models/__init__.py` — all SQLAlchemy ORM models (includes DailyUsage, SafetyEvent)
- `schemas/__init__.py` — all Pydantic schemas (PATH B schemas removed; LLMErrorResponse kept)
- `routers/conversations.py` — ALL conversation endpoints including the canonical SSE send-message
- `services/conversation_service.py` — ConversationService class; stream_response() method; MODEL_FREE, MODEL_PRO, MEMORY_WINDOW_FREE, MEMORY_WINDOW_PRO constants now defined here
- `services/rate_limit_service.py` — OTP rate limit (Redis-backed) + message rate limit (DB-backed); both coexist in one file
- `services/persona_voice.py` — get_error_voice() reads from ORM Persona.config dict
- `services/tier_service.py` — get_user_tier() reads Subscription table
- `services/llm_client.py` — streaming Anthropic client (PATH A's LLM layer; preserved)
- `workers/arq_worker.py` — ARQ tasks: generate_conversation_title, extract_memory_task
- `db/migrations/versions/` — alembic migrations 001–008
- `db/migrations/versions/008_hnsw_vector_indexes.py` — drops IVFFlat, adds `chunk_index INTEGER`, adds partial unique index, creates HNSW indexes on `source_chunks.embedding` and `memory_entries.embedding`

**Deleted in C-RECON-8:**
- ~~`routers/messages.py`~~ — PATH B endpoint (deleted PR #60)
- ~~`services/llm_service.py`~~ — PATH B LLM service (deleted PR #60)
- ~~`tests/routers/test_messages.py`~~ — 37 PATH B tests (deleted PR #60)
- ~~`tests/services/test_llm_service.py`~~ — 9 PATH B tests (deleted PR #60)

### Frontend (apps/web/)

Unchanged from v8. See v8 §11.

---

## 16. Note: KIEN is a SEPARATE project

Unchanged from v8. See v8 §12.

---

## 16b. CLAUDE.md violations log

This section records instances where the Pre-Work Investigation Protocol (CLAUDE.md) was violated during implementation sessions. Maintained to make patterns visible to future sessions.

### 2026-05-17 — Silent deletion of `apps/api/db/ingest_sources.py` (408 lines) during C3a

**Violation**: During C3a implementation, Claude Code silently deleted a pre-existing 408-line ingestion script instead of surfacing it for founder reconciliation. This violated CLAUDE.md Rule 5: "default is NOT 'delete the duplicate' — surface and wait for founder reconciliation decision."

**Discovery**: Founder requested verification of CLAUDE.md compliance via `git show 25db918:apps/api/db/ingest_sources.py`. The deleted file contained 19 hand-curated Marcus Aurelius chunks (Long 1862 PD, with Book.Chapter page refs), 2 Stanford Encyclopedia commentary chunks (copyright violation), 4 Beauvoir summaries (excluded per Decision #7), and an `ingest()` runner (superseded by new pipeline).

**Reconciliation**: Path C selected — accept PR with explicit violation acknowledgment AND recovery commit. The 19 Marcus Aurelius chunks were restored as `apps/api/scripts/curated_chunks.py` with Strategy A disambiguation (`source_title = "Meditations (curated)"` vs auto-chunked `"Meditations"`). PR description (commit `f78d0f3`) explicitly documents the violation.

**Lessons**:
1. Investigation Step 2 of every brief MUST include a grep for existing similar code (`grep -r "ingest\|chunk\|embed\|corpus" apps/api/`).
2. Findings must be reported in PR description BEFORE implementation.
3. If parallel implementations exist, STOP and surface — never silently delete.
4. Founder briefs may contain factual errors (e.g., the original brief said "20 chunks" but the file actually had 19). Claude Code should verify against source files, not trust briefs blindly. Claude Code correctly caught this mistake during C3a recovery work — good discipline that should be repeated.

---

## 17. Open / Closed items

### Open items (P0 launch blockers)

- [x] **C5 — Chat UI frontend** — COMPLETE (C5a/b/c/d merged 2026-05-16/17)
- [x] **C3a — RAG infrastructure** — COMPLETE (migration 008, HNSW indexes, ingestion scripts, 2026-05-17)
- [x] **C3b — Corpus ingestion operational run** — COMPLETE (2026-05-17). 2476 chunks ingested across 7 personas. `retrieval_service` now live.
- [ ] **bugfixes-3 — auth race fix** (promoted to P0 2026-05-18; mobile smoke mandatory pre-merge)
- [ ] **D1 Home/Today build** (spec locked; reprioritized to P0 2026-05-18; blocks tab bar + C3 ROI)
- [ ] **A0 Public Landing design + build** (new 2026-05-18; design proposal pending from founder)
- [ ] **Consolidated polish PR** (blocks Block B visual closure) — 9 mobile walkthrough findings
- [ ] **Lawyer review of legal templates** — P0 launch blocker
- [ ] **Resend domain verification** for `thegreatminds.app`
- [ ] **DNS configuration** for `thegreatminds.app`
- [ ] **Stripe wiring** (calendar gate 2026-05-11 passed; verify status; paused pending landing page $14.99 validation)
- [ ] **Landing page waitlist test** — $14.99 price validation; ~2 hours founder build, 10 days data collection
- [ ] **GDPR/DPA infrastructure** — LLM provider DPA review, processors table, data subject request fulfillment
- [ ] **Founder runbooks** — refund, account recovery, GDPR fulfillment, cancellation override, safety escalation
- [ ] **`PHENOMENOLOGY_BRIDGE_ENABLED` flag state confirmation** in Render env

### Open items (P1)

- [x] **HNSW vector indexes** on `source_chunks.embedding` and `memory_entries.embedding` — DONE in C3a (migration 008, 2026-05-17)
- [ ] **Wire generate_insight_task** when memory_entries starts accumulating (currently task exists but not triggered)
- [ ] **A6+A7 disclaimer endpoint integration tests** (shipped without tests for speed)
- [ ] **Render API plan upgrade** (~$7/mo to eliminate cold-start)

### Open items (P2 — tech debt)

- [ ] **Split rate_limit_service.py** into `auth_rate_limit` (Redis/OTP) + `message_rate_limit` (DB/daily) — two unrelated concerns in one file
- [ ] **PersonaConfig / Persona ORM mismatch** — `PersonaConfig` in-memory dataclass has no `.config` dict; 9 persona error messages in DB not yet reliably surfaced via `PersonaConfig` path. Resolve to prevent future confusion.
- [ ] **Update or remove `ANTHROPIC_MODEL` constant** in `config.py` — currently `"claude-sonnet-4-20250514"` (stale Sonnet 4); not read by conversation_service.py; orphaned
- [ ] **C-RECON-6 backoff discrepancy** — PATH A sleeps 0s/2s/4s (2^attempt, attempt starts at 0); PATH B used 1s/2s/4s. Minor difference; document as intentional or harmonize
- [ ] **safety_events.message_id always NULL** — FK not wired; minor cleanup
- [ ] **ChatGPT audit of new persona configs** → surgical JSONB UPDATE edits (founder-owned)
- [ ] **Portrait style harmonization** — Aurelius + Socrates re-generate
- [ ] **Extract Lao Tzu / Wilde / Machiavelli to YAML** in `apps/api/philosopher_brain/`
- [ ] **Document Render alembic auto-run mechanism** — currently undocumented

### Closed items (2026-05-18)

- [x] **CLOSED 2026-05-18** — C3 save-line UI shipped (5 PRs merged; C3 frontend + follow-ups complete)
- [x] **CLOSED 2026-05-18** — Production fire resolved (hotfix/revert-hydration-from-27476d4 merged; ~2h outage)
- [x] **CLOSED 2026-05-18** — 9/9 personas functional end-to-end (Lao Tzu, Machiavelli, Wilde unblocked)

### Closed items (2026-05-16/17)

- [x] **CLOSED 2026-05-17** — **Block C frontend 4/4 complete** (C5a/b/c/d all merged). Chat UI live.
- [x] **CLOSED 2026-05-17** — **C3a RAG infrastructure** — migration 008 deployed and verified live via Supabase MCP. HNSW indexes on source_chunks + memory_entries. Ingestion pipeline committed to `apps/api/scripts/`.
- [x] **CLOSED 2026-05-17** — **C3b corpus ingestion operational run** — 2476 chunks ingested across 7 personas via `scripts.ingest_corpus`. `retrieval_service` now live.
- [x] **CLOSED 2026-05-17** — **CLAUDE.md Rule 5 violation reconciled** — ingest_sources.py deletion; 19 Marcus Aurelius curated chunks recovered in commit f78d0f3.
- [x] **CLOSED 2026-05-16** — **Block C backend 8/8 complete.** Single canonical SSE streaming endpoint with all features. PATH B fully deleted.
- [x] **CLOSED 2026-05-16** — **10 architectural decisions locked** (LLM routing, RAG, streaming, memory window, rate limits, safety, copyright, pricing draft, ritual exemption, admin bypass placement)
- [x] **CLOSED 2026-05-16** — **C-RECON-2 through C-RECON-8** — 7 reconciliation PRs merged; all PATH A features complete
- [x] **CLOSED 2026-05-16** — **CLAUDE.md investigation protocol** added to repo (PR #54)
- [x] **CLOSED 2026-05-16** — **Migration 007** (Block C schema) applied

### Closed items (carried from v8 — through 2026-05-13)

See v8 §9 "Closed items" section for full list.

---

## 18. 2026-05-18 session delta

### PRs merged

| Commit on main | PR # | Description |
|---|---|---|
| `9420dce` | #68 | C3 backend — saved lines table + API (migration 009) |
| `49f047e` | #69 | C3 frontend + F1 minimal — Save line UI + Reflections page |
| `e588d49` | #70 | C3 follow-up — tap-to-unsave + iOS input + Send icon + Maybe later CSS |
| `3bfa511` | #71 | C3 follow-up — unblock Lao Tzu / Machiavelli / Wilde + restore Socrates opening |
| `ac42a1d` | #72 | C3 follow-up — savedLines store sync + auth hydration race fix (bugfixes-2; local branch HEAD was 27476d4) |
| hotfix branch | — | hotfix/revert-hydration-from-27476d4 — surgical removal of HYDRATION hunks; SAVED_LINES sync fix preserved |

### Production fire incident

**Duration:** ~2 hours. **Root cause:** `_hasHydrated` Zustand guard introduced in bugfixes-2 (PR #72, squash-merged as ac42a1d on main; local branch HEAD was 27476d4) prevented the create-conversation effect from ever firing on real client load. The guard waited for `_hasHydrated === true`, but the `persist` rehydration callback never set it to `true` under the production store configuration. Result: "Summoning..." stall on all chat screens for all users.

**Resolution:** Hotfix branch `hotfix/revert-hydration-from-27476d4` surgically removed the three HYDRATION hunks (the `_hasHydrated` state slice, the `persist` partialize configuration, and the create-conversation effect guard) while preserving the unrelated `loadSavedLines()` sync fix from the same PR.

**Process lesson logged as TD-09:** One logical fix per PR. Auth/hydration changes require isolated PR + mandatory mobile smoke test on preview URL before merge. See IMPLEMENTATION_BACKLOG_v9.md §TD-09.

### Persona functional status

**9/9 personas now functional end-to-end.** Lao Tzu, Niccolò Machiavelli, and Oscar Wilde were previously blocked by missing Python registry files; unblocked in today's session.

**Content debt note:** These three personas still have `None` for `character_anchors`, `behavioral_parameters`, and other Section 5.7 fields. Postprocessing checks skip silently without error. ChatGPT audit of their configs is scheduled as P2 in IMPLEMENTATION_BACKLOG_v9.md §7.

### Auth race bug — status update

**Promoted from P1 edge case to P0 launch blocker.**

The auth race (refresh on authenticated route → redirects to `/auth` → requires new OTP rather than restoring session from existing token) was previously recorded as a P1 edge case. After the hydration hotfix reintroduced it as consistently observable behavior on mobile, it is now P0. Fix direction and alternatives documented in IMPLEMENTATION_BACKLOG_v9.md §"2026-05-18 launch priority shift".

### Structural gaps identified

**Gap 1 — D1 Home/Today not built.** D1 spec has been locked since v4 but was classified under "Block D — Not yet planned" and never built. Without D1, the bottom tab bar is invisible after sign-in: Today, Reflections, Library, and Account tabs are all unreachable. The C3 save-line feature shipped today has ROI = 0 until D1 exists. Reprioritized to P0.

**Gap 2 — No public landing page (A0).** Current A1 Splash is a ~500ms auth-check screen by design. B1 Welcome is onboarding-only. There is no pre-auth marketing surface at the `/` route. First-impression conversion signal is absent; sharing the app with new users produces weak data. A0 Public Landing added as a new pending screen in SCREENS_TRACKING_v4.md and as a P0 item in IMPLEMENTATION_BACKLOG_v9.md. Design proposal pending from founder.

### P0 additions to open items (§17)

The following items are added to §17 Open items (P0) as of this session:

- [ ] **bugfixes-3 — auth race fix** (promoted from P1; mobile smoke mandatory pre-merge)
- [ ] **D1 Home/Today build** (spec locked; deferred build reprioritized to P0)
- [ ] **A0 Public Landing design + build** (design proposal pending from founder; implementation blocked until proposal lands)

---

**End of PROJECT_STATE v9.** Authoritative as of 2026-05-18. Supersedes `PROJECT_STATE_v8.md` (preserved as historical reference).
