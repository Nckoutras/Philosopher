# Memory-v2 — Investigation Report

**Mode:** investigation only. No code changed, no branch created, no commit, no PR.
**Date:** 2026-09-03
**Baseline SHA (from `git ls-remote origin refs/heads/main`):**
`b0148f73ccda330d811a21d404e79426d0ce3c49`
Local `HEAD` is identical to that SHA; the working tree carries one unrelated
untracked file (`docs/reports/The-Wise-Room-Teardown_2026-08-25.html`).
No production database was queried. Everything below is read from code at that SHA.

---

## 0. Executive summary

Five findings carry the report. Three are defects, two are dead weight.

1. **The octagon is structurally answer-blind.** `portrait_theme_scores`
   ([self_portrait.py:175-216](apps/api/services/self_portrait.py#L175-L216)) iterates
   the *keys* of `answers` and never reads the values. The polygon is a function of
   **which questions were answered**, not of **how**. Proven by execution: the same 15
   free questions answered all-first-pill and all-last-pill produce byte-identical
   scores. The signal does not exist in the data either — the question bank carries
   `theme_tags` per **question**, never per **pill**.
2. **The portrait's cached prose has the same blindness, by a different route.**
   Cache freshness is `len(answers) - watermark < 8`
   ([preferences.py:222-229](apps/api/routers/preferences.py#L222-L229)). Re-answering
   an existing question does not change `len(answers)`, so the Sonnet summary and the
   forming preview never regenerate on a re-answer either. Together with (1), a user
   who re-answers every question sees a bit-for-bit identical portrait. That is exactly
   the UAT symptom.
3. **Council receives zero memories.** `council_service.py:243-247` passes
   `memories=[]` unconditionally, and the service's own analytics comment says so at
   [council_service.py:400-401](apps/api/services/council_service.py#L400-L401). The
   brief's hypothesis (probabilistic top-6, no instruction to use the block) is
   **refuted for Council and confirmed for chat** — Council is not competing for slots,
   it has no slots.
4. **The weekly stale-memory job has never been able to match a row.** It prunes
   `confidence < 0.6` ([cron.py:61-86](apps/api/workers/cron.py#L61-L86)); the lowest
   confidence any writer can produce is 0.65
   ([memory_service.py:178](apps/api/services/memory_service.py#L178)). Both thresholds
   date to `3af5f706` (initial commit) and neither has ever changed. It is a no-op.
5. **Deleting a conversation hard-deletes its memories.**
   `memory_entries.conversation_id` is `ON DELETE CASCADE`
   ([013:16-21](apps/api/db/migrations/versions/013_add_ondelete_conversation_fks.py#L16-L21))
   and `DELETE /conversations/{id}` is a hard delete
   ([conversations.py:781-793](apps/api/routers/conversations.py#L781-L793)). The
   product's own copy says "the room keeps track of what matters to you and carries it
   into later conversations" ([explore/page.tsx:135-138](apps/web/app/app/(tabs)/explore/page.tsx#L135-L138)).

**TD-57 recommendation: pay it down alongside v2, not before.** The two live defects
are both pure-Python and DB-free; the argument is in §3, and it is not a general
endorsement of the current suite.

---

## 1. Domain enumeration (Rule 1)

### 1a. `services/memory_service.py` — every public surface, read from the body

516 lines. Module-level constants: `RECURRENCE_SIM_THRESHOLD = 0.75`,
`RECURRENCE_MIN_PRIOR = 1`, `RECURRENCE_THROTTLE_HOURS = 6`
([:18-20](apps/api/services/memory_service.py#L18-L20)), `MIN_DISTILL_WORDS = 6`
([:72](apps/api/services/memory_service.py#L72)).

| Symbol | Location | What it **actually** does (body, not docstring) |
|---|---|---|
| `distill_to_memory(text)` | [:81-104](apps/api/services/memory_service.py#L81-L104) | Word-count pre-filter (`< 6 words → None`, zero LLM cost), then one Haiku completion under `DISTILL_TO_MEMORY_PROMPT`. Strips wrapping quotes; `""`/`NONE` → `None`. Returns a third-person `"User …"` sentence. Module-level function, **not** a `MemoryService` method. |
| `MemoryService.extract_and_store(...)` | [:136-256](apps/api/services/memory_service.py#L136-L256) | One Haiku call under `MEMORY_EXTRACTION_PROMPT`; strips ``` fences; `json.loads`. **Any** exception → `return []` (the `except (json.JSONDecodeError, Exception)` catches everything). Per item: `dilemma`/`aspiration` are skipped as memory rows; `confidence < 0.65` skipped; empty content skipped; else one embed + one `MemoryEntry` (`entry_type` defaults to `"pattern"`). `db.flush()` — **does not commit** (the ARQ task commits). Then, only when `safety_ok=True`, promotes at most **one** `Insight` from the same parsed payload, priority `dilemma > belief > aspiration`, per-type confidence bar `{dilemma: .8, belief: .8, aspiration: .7}`, gated by `_insight_gate_blocked`. Insight failure is swallowed and never breaks persistence. |
| `MemoryService.recall(...)` | [:258-289](apps/api/services/memory_service.py#L258-L289) | Raw SQL pgvector cosine search over `memory_entries` where `user_id` matches, `is_active`, `embedding IS NOT NULL`. `ORDER BY embedding <=> query` `LIMIT :top_k`. **Ordering is pure vector distance** — no recency, no confidence, no `entry_type` weighting, no per-type quota, no persona scoping. Post-filters `score > 0.70` in Python, so it can and does return fewer than `top_k` (including zero). Returns SQLAlchemy `Row` objects, **not** `MemoryEntry` ORM instances, despite the `-> list[MemoryEntry]` annotation. |
| `MemoryService._insight_gate_blocked(...)` | [:291-330](apps/api/services/memory_service.py#L291-L330) | Shared throttle/dedup for every insight write. `"throttle"` if any non-dismissed insight for the user in the last 6h; `"per_conversation"` if the conversation already has any insight; else `None`. A `NULL` conversation skips the second check by SQL three-valued logic (deliberate, documented). |
| `MemoryService.detect_recurrence(...)` | [:332-486](apps/api/services/memory_service.py#L332-L486) | Whole body in one `try/except` — never raises. Runs the shared gate first. For each new entry with an embedding, cosine-searches the user's **other** conversations (`LIMIT 20`), keeps matches `>= 0.75`, and stops at the first entry with `>= 1` match. Builds the pgvector literal by hand (`repr(float(x))`) rather than `str()`, specifically to survive a numpy array. Then **one** `SHIFT_CLASSIFY_PROMPT` call returning `{"insight_type": "pattern"\|"shift", "content": …}`; on any parse failure it falls back to a second `RECURRENCE_PROMPT` call and forces `"pattern"`. Writes one `Insight` with `source_count = distinct prior conversations + 1` and **commits**. |
| `MemoryService.get_user_memories(...)` | [:488-499](apps/api/services/memory_service.py#L488-L499) | `SELECT … WHERE user_id AND is_active ORDER BY created_at DESC LIMIT 50`. **Zero callers** anywhere in the repo. |
| `MemoryService.deactivate(...)` | [:501-513](apps/api/services/memory_service.py#L501-L513) | Sets `is_active = False` on one owned row; returns `bool`. Does not commit. **Zero callers** anywhere in the repo. |
| `memory_service` | [:516](apps/api/services/memory_service.py#L516) | Module singleton. |

**`SHIFT_CLASSIFY_PROMPT`** ([:44-70](apps/api/services/memory_service.py#L44-L70)) is a
stance-comparison classifier, not a similarity measure. It receives the just-raised
memory plus up to 5 prior matches and must default to `"pattern"`; `"shift"` requires
"genuine DIRECTIONAL change in the stance itself", and its phrasing is hedged in three
confidence bands. It **only ever runs inside `detect_recurrence`**, i.e. only when a
cosine match `>= 0.75` from another conversation already exists — so a stance change
expressed in wording the embedder scores below 0.75 is never classified at all.

**The weekly stale-memory job is not in this file.** It lives in
[cron.py:61-86](apps/api/workers/cron.py#L61-L86) — see §1e. The v27 handoff describes
it as part of what `memory_service` does; that is inaccurate, and the job's actual
behaviour is finding (4).

### 1b. Tables and columns

Read from `models/__init__.py` and `db/migrations/versions/` (migrations live under
`apps/api/db/migrations/versions/`, **not** `apps/api/alembic/`). Head revision at this
SHA is `056_deletion_fks`.

**`memory_entries`** — [models/__init__.py:277-295](apps/api/models/__init__.py#L277-L295)

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | `gen_random_uuid()` |
| `user_id` | UUID FK → `users.id` | **`ON DELETE CASCADE`**, set in [001:100](apps/api/db/migrations/versions/001_initial.py#L100) |
| `persona_id` | UUID FK → `personas.id` | **No `ON DELETE` clause** → `NO ACTION`. Deleting a persona would be blocked by memory rows. `NULL` for every non-chat writer. |
| `conversation_id` | UUID FK → `conversations.id` | **`ON DELETE CASCADE`**, set in [013:16-21](apps/api/db/migrations/versions/013_add_ondelete_conversation_fks.py#L16-L21) ("derived data, safe to lose with parent"). This is finding (5). |
| `entry_type` | `String(50)` | Free text. No enum, no CHECK constraint. Model comment lists only 5 of the 11 values in use. |
| `content` | `Text` NOT NULL | The only field any read path interprets. |
| `embedding` | `Vector(1536)` | `text-embedding-3-small` ([config.py:31](apps/api/config.py#L31)). Nullable; `recall` and `detect_recurrence` both skip `NULL`. |
| `confidence` | `Float` | `server_default 1.0`. Read by exactly one consumer — the dead cron job. |
| `source_turn` | `Integer` | Chat turn index, **except** for `self_portrait` / `self_portrait_shift` rows where it holds `question_key()`, a 31-bit crc32 of the question id, used as a dedup key. Documented overload at [self_portrait.py:315-329](apps/api/services/self_portrait.py#L315-L329). |
| `is_active` | `Boolean` | Soft-delete / supersede flag. |
| `created_at` / `updated_at` | `timestamptz` | `created_at` is the recall-adjacent ordering field everywhere **except** `recall()` itself. |

**Indexes:** `idx_memory_user (user_id, is_active)`
([001:112](apps/api/db/migrations/versions/001_initial.py#L112)); HNSW cosine index
`ix_memory_entries_embedding_hnsw_cosine` (m=16, ef_construction=64), which **replaced**
001's IVFFlat index in [008:38-56](apps/api/db/migrations/versions/008_hnsw_vector_indexes.py#L38-L56);
FK indexes on `conversation_id` and `persona_id` from
[015:24-25](apps/api/db/migrations/versions/015_add_fk_indexes.py#L24-L25). RLS enabled
by the catch-up migration [052:64](apps/api/db/migrations/versions/052_enable_rls.py#L64).

**No dedicated recall-ordering column exists.** There is no `last_recalled_at`, no
`recall_count`, no decay field, no `superseded_by`. There is no unique constraint on
`(user_id, content)` — dedup is purely semantic and only happens inside
`detect_recurrence`, which writes an *Insight*, never merges or suppresses a memory row.

**`entry_type` values written anywhere in the codebase (11):**

| Value | Writer | Confidence |
|---|---|---|
| `belief`, `value`, `struggle`, `pattern`, `milestone` | LLM extraction ([memory_service.py:184-193](apps/api/services/memory_service.py#L184-L193)); `pattern` is also the fallback for an unrecognised type | LLM value, `>= 0.65` |
| `counterview_belief` | [arq_worker.py:588-596](apps/api/workers/arq_worker.py#L588-L596) | 0.7 |
| `stated` | [arq_worker.py:664-674](apps/api/workers/arq_worker.py#L664-L674) | 1.0 |
| `onboarding_profile` | [arq_worker.py:724-733](apps/api/workers/arq_worker.py#L724-L733) | 0.8 |
| `self_portrait` | [arq_worker.py:788-798](apps/api/workers/arq_worker.py#L788-L798) | 0.8 |
| `self_portrait_shift` | [arq_worker.py:817-826](apps/api/workers/arq_worker.py#L817-L826) | 0.8 |

`dilemma` and `aspiration` are extracted by the prompt but **never** become memory rows
([memory_service.py:174-176](apps/api/services/memory_service.py#L174-L176)); they exist
only as `Insight.insight_type`.

**`insights`** — the memory subsystem's only other write target.
`insight_type ∈ {pattern, shift, dilemma, belief, aspiration}`; `source_count`
(`NULL` for signal insights, distinct-conversation count for recurrences); `theme`
(added in [047_insight_theme](apps/api/db/migrations/versions/047_insight_theme.py), validated
against `THEME_VALUES`); `is_dismissed`.

**`user_preferences.profile`** — JSONB. Not part of the memory tables, but it is the
**authoritative store for self-portrait answers** (`profile.answers = {question_id: pill_index}`);
`memory_entries` holds only a rendered sentence per answer.
`user_preferences.portrait_cache` (JSONB, [039_portrait_cache](apps/api/db/migrations/versions/039_portrait_cache.py))
holds `{text, best_fit, answer_count_watermark, generated_at, forming: {...}, last_failed_at}`.

### 1c. Call sites — every caller of the memory domain

**Readers of `memory_service.recall` (3, all in `conversation_service.py`):**

| Caller | Line | Asks for | Does what with it |
|---|---|---|---|
| `stream_response` (main chat) | [:658](apps/api/services/conversation_service.py#L658) | `top_k=6` on the user's message, reusing the turn's single embedding | → `build_system(memories=…)` at [:702-706](apps/api/services/conversation_service.py#L702-L706). Fail-open: exception → `memories=[]` + rollback. |
| `stream_another_mind` (guest persona) | [:1200](apps/api/services/conversation_service.py#L1200) | `top_k=6` on the **last user message in the conversation** | → `build_system` at [:1214-1219](apps/api/services/conversation_service.py#L1214-L1219). Same fail-open. |
| `stream_go_deeper` | [:1462](apps/api/services/conversation_service.py#L1462) | `top_k=6`, same shape | → `build_system` at [:1476-1481](apps/api/services/conversation_service.py#L1476-L1481). Same fail-open. |

**Every other `build_system` caller passes `memories=[]`:**
`create_reading_revisit` ([:542-543](apps/api/services/conversation_service.py#L542-L543)),
`council_service` ([:243-247](apps/api/services/council_service.py#L243-L247)),
`scripts/voice_test_socrates.py:42-44`.

**Direct `MemoryEntry` readers (not via `memory_service`):**

| Caller | Line | Reads | Purpose |
|---|---|---|---|
| `self_model_service.build` | [:22-45](apps/api/services/self_model_service.py#L22-L45) | all active rows **except** `counterview_belief`, `self_portrait`, `self_portrait_shift`, ordered `created_at ASC` | You-vs-You then/now windows (12 each), gated at ≥20 signals and ≥14 days span. Note: `onboarding_profile` and `stated` are **not** excluded, so the ≤2 signup rows count toward the unlock gate and land in the "then" window. |
| `self_portrait_summary._recent_signals` | [:105-122](apps/api/services/self_portrait_summary.py#L105-L122) | latest 8 active, excluding the three self-portrait/counterview types | "quiet signals" block in the portrait-summary prompt |
| `self_comparison_service` | [:138-147](apps/api/services/self_comparison_service.py#L138-L147) | latest 8 `self_portrait_shift` | You-vs-You closing block |
| `arq_worker.generate_insight_task` | [:844-849](apps/api/workers/arq_worker.py#L844-L849) | latest 15 active | **Never enqueued** — see §1e |
| `routers/memory.py` | [:23-70](apps/api/routers/memory.py#L23-L70) | `GET` latest 100 active; `PATCH` content/`is_active`; `DELETE` → soft delete | **No frontend caller** — see §1f |
| `data_export_service` | [:220-224](apps/api/services/data_export_service.py#L220-L224) | all rows for the user, embeddings deliberately excluded | GDPR Art. 15/20 export |
| `routers/billing.py` | [:322-323](apps/api/routers/billing.py#L322-L323) | `COUNT` of `self_portrait` rows in 14 days | Feature-usage telemetry — uses memory rows as a **proxy timestamp** for quiz answers, because `profile.answers` has none |

**Writers — every `enqueue_job` into a memory task:**

| Task | Enqueued from | Trigger |
|---|---|---|
| `extract_memory_task` | [conversation_service.py:1115-1125](apps/api/services/conversation_service.py#L1115-L1125) — **the only site** | Every main-chat turn where the persona was not safety-suppressed |
| `counterview_belief_task` | [counterview.py:195](apps/api/routers/counterview.py#L195) | User types a belief into Counterview |
| `distill_user_text_to_memory_task` | [mirrors.py:150](apps/api/routers/mirrors.py#L150), [scheduled_emails.py:97](apps/api/routers/scheduled_emails.py#L97), [weekly_letters.py:157](apps/api/routers/weekly_letters.py#L157), [council_service.py:384](apps/api/services/council_service.py#L384), [counterview_service.py:642](apps/api/services/counterview_service.py#L642) | User's own text from 5 surfaces |
| `seed_profile_memory_task` | [preferences.py:98](apps/api/routers/preferences.py#L98) | `PATCH /preferences/profile` |
| `seed_self_portrait_memory_task` | [preferences.py:356](apps/api/routers/preferences.py#L356) | `PATCH /preferences/self-portrait`, one per answer tap |

**`stream_another_mind` and `stream_go_deeper` read memory but never write it** — neither
enqueues `extract_memory_task`. All three enqueues in `conversation_service` sit inside
`stream_response` ([:1106, :1115, :1136](apps/api/services/conversation_service.py#L1106-L1136)).

**Not in the domain, verified:** `counterview_service`, `insight_mirror_service`,
`reflections_feed_service` and `retrieval_service` contain **zero** references to
`MemoryEntry`, `memory_entries` or `memory_service`.

### 1d. Prompts that receive memory content, and how it is injected

| Template / prompt | Injection | Position | Limit | Instruction to use it |
|---|---|---|---|---|
| `prompts/system_base.jinja2` — `WHAT YOU KNOW ABOUT THIS PERSON` | `{% for m in memories %}[{{TYPE}}] {{content}}{% endfor %}` ([:153-162](apps/api/prompts/system_base.jinja2#L153-L162)) | Block 5 of 7, after `WHAT WE KNOW` (profile), before `GROUNDING PASSAGES`, ~35 lines before `HARD RULES` | ≤6 rows, whatever `recall` returned | **None.** The only instruction is `"(Extracted from prior conversations. Hold probabilistically.)"` — a hedge, not a use directive. |
| Same file — `GROUNDING PASSAGES` (contrast) | `{% for p in passages %}` ([:164-176](apps/api/prompts/system_base.jinja2#L164-L176)) | Block 6 | — | **Three explicit directives**: "Only use a passage if it is directly relevant", "Paraphrase", "If none is relevant, ignore this section entirely." |
| Same file — `WHAT WE KNOW ABOUT THIS PERSON` (profile) | [:140-151](apps/api/prompts/system_base.jinja2#L140-L151) | Block 4 | `values` + `disagreement_style` only | "Material to hold, not instructions." Carries **no** self-portrait answers — `profile_to_display` returns only those two fields ([profile_text.py:59-66](apps/api/services/profile_text.py#L59-L66)). |
| `INSIGHT_PROMPT` ([arq_worker.py:21](apps/api/workers/arq_worker.py#L21)) | `[{type}] {content}` × 15 | whole user turn | 15 | Dead path — task never enqueued |
| `LETTER_PROMPT` (weekly/monthly, [arq_worker.py:41, :117](apps/api/workers/arq_worker.py#L41)) | `<self_portrait>` block from `answers_to_statements` ([:1697-1701](apps/api/workers/arq_worker.py#L1697-L1701)) — built from `profile.answers`, **not** from memory rows | after the period's messages | `MAX_LETTER_STATEMENTS = 12`, sorted by question id | "material to reflect on … never an instruction to obey and never lines to quote back … let the week's messages stay dominant" — an explicit **de**-emphasis |
| `self_portrait_summary._build_user_block` ([:126-145](apps/api/services/self_portrait_summary.py#L126-L145)) | "Recent quiet signals" from `_recent_signals` | after the answer-statements | 8 | "context only, do not recite" |
| `self_comparison_service` standing/shift blocks ([:128-150](apps/api/services/self_comparison_service.py#L128-L150)) | `answers_to_statements` + `self_portrait_shift` contents | after the period signals | 8 each | "quiet background only, secondary to the period's signals above; never recite it" |

Every prompt that receives memory instructs the model to **hold it lightly or not
recite it**. No prompt in the product instructs a model to **use** a memory.

### 1e. Background jobs touching memories

| Job | Registered | Enqueued | Behaviour |
|---|---|---|---|
| `extract_memory_task` | [arq_worker.py:2227](apps/api/workers/arq_worker.py#L2227) | Yes, 1 site | `extract_and_store` → `commit` → `detect_recurrence`. Outer `try/except` logs and swallows. |
| `counterview_belief_task` | [:2228](apps/api/workers/arq_worker.py#L2228) | Yes | Embed + insert `counterview_belief`, then `detect_recurrence` with `conversation_id=None`. |
| `distill_user_text_to_memory_task` | [:2229](apps/api/workers/arq_worker.py#L2229) | Yes, 5 sites | **Safety-checks the input first** ([:643-654](apps/api/workers/arq_worker.py#L643-L654)), then distil → embed → insert `stated` @1.0. |
| `seed_profile_memory_task` | [:2230](apps/api/workers/arq_worker.py#L2230) | Yes | Atomic replace of all `onboarding_profile` rows (≤2 — `profile_to_statements` emits at most a values line and a disagreement line, [profile_text.py:69-79](apps/api/services/profile_text.py#L69-L79)). |
| `seed_self_portrait_memory_task` | [:2231](apps/api/workers/arq_worker.py#L2231) | Yes | Incremental per-question replace keyed on `source_turn = question_key(qid)`; optionally also writes one `self_portrait_shift` row when `previous_index != current_index`. One commit covers both. |
| `generate_insight_task` | [:2232](apps/api/workers/arq_worker.py#L2232) | **No** — grep for `"generate_insight_task"` across the repo returns zero enqueue sites | Dead. Superseded by `detect_recurrence`. |
| **cron `stale_memory`** | [cron.py:61](apps/api/workers/cron.py#L61) — APScheduler, Sunday 03:00 UTC | Runs weekly | `UPDATE memory_entries SET is_active=false WHERE created_at < now()-90d AND confidence < 0.6 AND is_active`. **Matches zero rows by construction** — see §2c. |

No other cron job touches `memory_entries`.

### 1f. Frontend surfaces

| Surface | File | Status |
|---|---|---|
| `getMemory()` / `deleteMemory()` | [api.ts:1246-1252](apps/web/lib/api.ts#L1246-L1252) | Defined; **zero callers** in `app/`, `components/` or `lib/` |
| `/app/explore/memory` | [page.tsx](apps/web/app/app/explore/memory/page.tsx) | Static explainer page. Contains **no API call at all** — it renders a hand-mirrored replica of the insight chip. |
| `/app/explore` entry copy | [page.tsx:132-148](apps/web/app/app/(tabs)/explore/page.tsx#L132-L148) | Links to the explainer; promises the room "keeps track of what matters to you and carries it into later conversations" |
| Self-portrait radar/observations | [self-portrait/page.tsx:457-470, :1024-1029](apps/web/app/app/(tabs)/self-portrait/page.tsx#L457-L470); [PortraitMap.tsx](apps/web/components/self-portrait/PortraitMap.tsx); [selfPortraitCaption.ts](apps/web/lib/selfPortraitCaption.ts); [selfPortraitObservations.ts](apps/web/lib/selfPortraitObservations.ts) | Consumes `theme_scores` for the octagon, the map, the observation cards, the summary line and the top-axis key — **all five derive from the answer-blind function** |

**There is no UI anywhere that lets a user see, edit, or forget a memory.** Three
endpoints exist for it and nothing calls them. GDPR access is served instead by the
data export ([data_export_service.py:220-224](apps/api/services/data_export_service.py#L220-L224)).

---

## 2. The two known failures, traced to mechanism

### 2a. The self-portrait never changes

**Path:** tap → `PATCH /preferences/self-portrait`
([preferences.py:307-359](apps/api/routers/preferences.py#L307-L359)) → validate against
bank → merge into `profile.answers` → `set_profile` → enqueue
`seed_self_portrait_memory_task` → open portrait → `GET /preferences/self-portrait/portrait`
([preferences.py:175-303](apps/api/routers/preferences.py#L175-L303)) → `portrait_theme_scores(answers)`
→ `theme_scores` on the wire → octagon.

The answers are stored correctly. They are scored — and the scoring function never
reads them.

**Defect 1 — `portrait_theme_scores` reads keys, never values.**
[self_portrait.py:196-216](apps/api/services/self_portrait.py#L196-L216):

```python
for qid in answers or {}:          # iterates KEYS
    q = _BANK.get(qid)
    if q is None: continue
    for tag in (q.get("theme_tags") or []):   # tags belong to the QUESTION
        axis = _TAG_TO_AXIS.get(tag)
        if axis is not None: raw[axis] += 1
```

`answers[qid]` — the pill the person actually chose — is never dereferenced. The
polygon is a function of the answered-question **set**.

Executed at this SHA against the real bank and the real function:

```
free question count: 15
all-first-pill : identity .4407  fear .5  freedom .3391  desire .4382
                 doubt 1.0  duty .5702  connection .7471  meaning .4333
all-last-pill  : identity .4407  fear .5  freedom .3391  desire .4382
                 doubt 1.0  duty .5702  connection .7471  meaning .4333
IDENTICAL: True
```

The signal is absent from the **data model**, not just the function: the bank's 360
questions carry exactly six keys — `id, category, question, pills, theme_tags, feeds` —
and `theme_tags` is per question. Zero questions carry per-pill metadata. There is no
per-answer theme information in the product to score.

A consequence worth stating plainly: the free tier's 15 questions are a **fixed,
deterministic** slice ([self_portrait.py:263-284](apps/api/services/self_portrait.py#L263-L284)),
so **every free user who completes the quiz gets the exact octagon printed above** —
not merely stable across their own sessions, but identical to every other free user's.
The max-normalisation at [:210-215](apps/api/services/self_portrait.py#L210-L215) then
guarantees the shape always fills the frame, which makes an unchanging polygon look
like a deliberate result.

**Defect 2 — the prose has the same blindness by a different route.**
The cached Sonnet summary regenerates only when
`len(answers) - answer_count_watermark >= PORTRAIT_REGEN_DELTA` (8)
([preferences.py:222-229](apps/api/routers/preferences.py#L222-L229); constant at
[self_portrait.py:107](apps/api/services/self_portrait.py#L107)). Re-answering an
existing question writes `answers = {**existing, qid: new_index}`
([preferences.py:346](apps/api/routers/preferences.py#L346)) — the key already exists,
so `len(answers)` is unchanged and the delta stays at whatever it was. The forming
preview uses the identical watermark test at
[preferences.py:255-262](apps/api/routers/preferences.py#L255-L262). Neither ever
regenerates on a re-answer.

**Combined:** for a user who does not answer *new* questions, the octagon, the map, the
observation cards, the caption, the top-axis key, the summary prose and the forming
preview are all bit-for-bit stable no matter what they answer. That is the whole UAT
symptom, with no residue.

**What does still work,** and is worth not breaking: `answer_statement`
([self_portrait.py:331-344](apps/api/services/self_portrait.py#L331-L344)) and
`shift_statement` ([:346-361](apps/api/services/self_portrait.py#L346-L361)) *do* read
the pill index. So the memory rows, the weekly/monthly letters and the You-vs-You
closing all see the real answers. The break is confined to the **portrait read path**.

Also noted: the `feeds` field is present on all 360 questions
(`["persona_context", "sunday_reading", "you_vs_you"]` and similar) and is documented in
the module header at [self_portrait.py:8](apps/api/services/self_portrait.py#L8), but a
repo-wide grep finds **no consumer** in either `apps/api` or `apps/web`. Routing
metadata that was authored and never wired.

### 2b. Council feels generic / memories feel empty

**Council receives no memories at all.** Not a scarce top-6 — zero.

[council_service.py:242-249](apps/api/services/council_service.py#L242-L249), inside the
per-member loop:

```python
system = (
    prompt_builder.build_system(
        persona=persona,
        memories=[],          # ← unconditional
        passages=[],
        phenomenology_bridge=None,
    ) + "\n\n" + COUNCIL_VERDICT_INSTRUCTION.format(...) + role_directive
)
```

The service documents this itself at
[council_service.py:400-401](apps/api/services/council_service.py#L400-L401): *"No
used_memory -- this service passes memories=[] unconditionally."* The single
`build_system` call in the file is that one; the synthesis step builds its own string
from the verdicts and receives no memory either. Council is the only conversational
surface that is also **prompt-cached whole**
([:280](apps/api/services/council_service.py#L280), `cache_whole_system`) — which is
only sound *because* the prompt carries nothing per-user. Any v2 that gives Council
memory pays for that cache.

The one memory interaction Council has is a **write**, not a read: when the user rewrote
the matter in their own words, the edited text is distilled into a `stated` memory
([council_service.py:382-391](apps/api/services/council_service.py#L382-L391)).

**Where the top-6 hypothesis *is* correct — chat.** For `stream_response`,
`stream_another_mind` and `stream_go_deeper` the brief's hypothesis is confirmed on all
three of its clauses, plus a fourth the brief did not name:

1. **`top_k=6`**, from a single flat cosine query with no per-type quota
   ([memory_service.py:269-289](apps/api/services/memory_service.py#L269-L289)).
2. **Probabilistic** — a hard post-filter drops everything at `score <= 0.70`
   ([:289](apps/api/services/memory_service.py#L289)), so the real return is 0–6, and a
   turn that phrases things differently returns nothing at all. Every failure is
   fail-open to `[]` ([conversation_service.py:657-662](apps/api/services/conversation_service.py#L657-L662)).
3. **No instruction to use the block** — confirmed verbatim. The header reads
   `(Extracted from prior conversations. Hold probabilistically.)` and nothing else
   ([system_base.jinja2:153-162](apps/api/prompts/system_base.jinja2#L153-L162)). The
   adjacent passages block gets three explicit directives. The memory block's only
   guidance dampens it.
4. **Portrait memories do compete with chat memories for the six slots, and they
   outnumber them structurally.** A single flat query over all active rows means a user
   who has answered 15 quiz questions carries ≥15 `self_portrait` rows against however
   many the chat extractor produced (≤3 per turn, `confidence >= 0.65`, and only from
   `stream_response`). There is no reservation, no diversity rule, no type weighting.

A fifth mechanism compounds it. The `self_portrait` rows are rendered as
`Asked "<full scenario question>", they answered: "<pill>"`
([self_portrait.py:344](apps/api/services/self_portrait.py#L344)) — a sentence whose
embedding is dominated by the **question's** wording, since the question is long and the
pill is 2–5 words. So cosine recall over those rows matches the *topic of the question
asked*, not the *stance the person took*. Whether that clears 0.70 against ordinary chat
prose is measurable and unmeasured; the report does not assert a number.

**Net answer to the brief's question:** Council gets 0 memories. Chat gets 0–6, drawn
from a pool where quiz answers structurally outnumber conversational signal, ordered by
raw vector distance with no recency or confidence input, and injected under an
instruction that tells the model to hold them loosely.

### 2c. A third defect found while enumerating: the stale-memory job is a no-op

[cron.py:61-86](apps/api/workers/cron.py#L61-L86) deactivates rows with
`created_at < now() - 90 days AND confidence < 0.6 AND is_active`.

No writer in the codebase can produce a row below 0.6:

| Writer | Floor |
|---|---|
| LLM extraction | `if entry.get("confidence", 0) < 0.65: continue` → **0.65** ([memory_service.py:178](apps/api/services/memory_service.py#L178)) |
| `counterview_belief_task` | 0.7 |
| `seed_profile_memory_task` / `seed_self_portrait_memory_task` | 0.8 |
| `distill_user_text_to_memory_task` | 1.0 |
| Column default | 1.0 |

`git log -S` on both thresholds returns only `3af5f706` ("initial commit"): the 0.65
filter and the 0.6 cutoff have both been in place, unchanged, since day one. **The job
has never deactivated a row and cannot.** The comment at
[arq_worker.py:632](apps/api/workers/arq_worker.py#L632) — "auto-protected from the
stale-memory cron, which only prunes <0.6" — is correct about that row and accidentally
describes every row in the table.

Consequence for v2: **memory has no working expiry.** The only forgetting mechanism that
actually fires is the conversation-delete cascade (§2d), which is unbounded and silent.

### 2d. Fourth finding: conversation deletion hard-deletes memories

`DELETE /conversations/{id}` is a hard `db.delete(conv)`
([conversations.py:781-793](apps/api/routers/conversations.py#L781-L793)), and
`memory_entries.conversation_id` carries `ON DELETE CASCADE` since
[013](apps/api/db/migrations/versions/013_add_ondelete_conversation_fks.py#L16-L21),
where it was reasoned as "derived data, safe to lose with parent".

That reasoning was sound for a subsystem whose only job was to help the next turn in the
same conversation. It is no longer what the product promises: the memory is now the
spine of chat recall, the weekly letter, You-vs-You and the insight detector, and the
explore copy tells the user the room *carries it into later conversations*. Tidying old
threads silently destroys the durable record. `onboarding_profile`, `self_portrait`,
`self_portrait_shift` and `counterview_belief` rows are safe (`conversation_id IS NULL`);
`stated` rows from Council/mirror/letters carry a conversation id and are **not**.

This is stated as a finding, not a proposal — the fix direction is a ruling (§4.7).

---

## 3. TD-57 cost assessment

**TD-57 re-verified independently at this SHA,** per Rule 3. Grepping `apps/api/tests/`
for `create_async_engine`, `AsyncSessionLocal()`, `testcontainers`, `pytest_postgresql`
and `DATABASE_URL` returns exactly two hits, and both are comments describing mocks
([test_conversations.py:164](apps/api/tests/routers/test_conversations.py#L164),
[test_cron_stripe_reconcile.py:46](apps/api/tests/services/test_cron_stripe_reconcile.py#L46)).
The backlog's claim holds.

**A second gap the backlog does not name:** across 69 test files there is **no test file
for `memory_service` at all**. The six files that mention it
(`test_conversation_service.py`, `test_token_components.py`, `test_token_logging.py`,
`test_billing_lifecycle.py`, `test_checkout_source.py`, `test_self_portrait_coverage.py`)
reference it incidentally — patching `recall` as a mock, or counting tokens. No test
exercises extraction, recall ordering, the recurrence detector, the shared insight gate,
or the shift classifier. That is a coverage gap independent of TD-57, and cheaper to
close.

### Testability, behaviour by behaviour

| Behaviour | Testable without a live DB? | Why |
|---|---|---|
| `portrait_theme_scores` (defect 1) | **Yes, trivially** | Pure function over a dict and an import-time bank. §2a's proof ran in-process in under a second. |
| Cache-freshness watermark (defect 2) | **Yes** | Integer arithmetic on `len(answers)`; the router path is already mock-tested in `test_self_portrait_coverage.py`. |
| Council `memories=[]` | **Yes** | Assert on the string handed to `build_system`, or on the rendered prompt. `test_prompt_cache.py` already does this shape. |
| `distill_to_memory` pre-filter and NONE handling | **Yes** | One mocked LLM call. |
| Extraction parsing, fence-strip, per-type gates | **Yes** | Pure over a mocked completion — but per C-06, the mock must set every field the branch reads. |
| Prompt injection / block ordering | **Yes** | Jinja render assertion. |
| Stale-cron no-op (defect 3) | **Partly** | A unit test can assert the *thresholds are incompatible* (0.65 > 0.6). Proving no row exists below 0.6 needs the DB. |
| **`recall` ordering and the 0.70 cut** | **No** | pgvector `<=>` and an HNSW index. A mocked `db.execute` returns whatever the test author invented, so "the right memories came back in the right order" is unassertable. |
| **`detect_recurrence` cosine + the "other conversations" exclusion** | **No** | Same, plus the `conversation_id != :id` vs `id != :self_id` NULL-logic branch ([memory_service.py:383-390](apps/api/services/memory_service.py#L383-L390)) is *precisely* a three-valued-logic behaviour a mock cannot enforce. |
| **`_insight_gate_blocked` throttle/dedup** | **No** | Two `SELECT`s whose whole content is a race against concurrent ARQ deliveries. |
| **Per-question dedup via `source_turn = question_key`** | **No** | Correctness is "the `UPDATE` matched the right prior row", i.e. a `WHERE` clause result. |
| **`ON DELETE CASCADE` on `conversation_id` (defect 4)** | **No** | Only the database enforces it. |
| **Atomicity of the seed tasks** | **No** | "The deactivation rolled back with the failed embed" is transaction semantics. |
| **HNSW index actually used** | **No** | Needs `EXPLAIN`. |

Roughly: **6 behaviours are testable today, 7 are not**, and the 7 are the ones that make
memory *memory* — ordering, dedup, cascade, transactions.

### Recommendation

**Pay TD-57 down alongside Memory-v2, not before it.** Three specifics:

1. **The two live defects do not need it.** Both self-portrait defects are pure-Python
   and are provable in unit tests today — §2a's disproof took one in-process run.
   Sequencing a Postgres test harness ahead of a fix whose regression test needs no
   database would delay a user-visible bug behind infrastructure that would not have
   caught it.
2. **v2's *design* does not need it; v2's *merge gate* does.** The rulings in §4 are
   product decisions (what competes for a recall slot, whether recall is deterministic,
   what forgetting means). None is blocked by test infrastructure. But the moment a
   ruling turns into a schema change — a `superseded_by` column, a per-type quota in
   the recall SQL, a decay field, a change to the cascade — it lands in the 7-row half
   of the table above, and merging it against mocks is how "the migration is wrong in a
   way the models do not express" ships. Concretely: any v2 PR that touches
   `memory_entries` DDL or the `recall`/`detect_recurrence` SQL should be gated on the
   harness existing.
3. **What "paying it down" needs to mean here is narrower than a full suite.** The
   memory domain needs a real Postgres with `pgvector`, migrations applied, and a
   per-test transaction rollback — enough to assert ordering under a known set of
   embeddings, one cascade, and one dedup `UPDATE`. That is one `conftest` fixture plus
   a CI service container, not a rewrite of 69 files. It is also reusable by #588's
   cascade and #583's ordering, which the backlog already names as the other victims.

**Practical ordering:** (a) the portrait scoring fix and its unit tests, which need
nothing; (b) the DB fixture, scoped to the memory domain; (c) v2 schema/recall changes
behind it. If (b) proves harder than expected, (a) still ships and the two known
symptoms are half resolved.

---

## 4. Rulings needed from the founder

No design follows until these are answered. They are ordered by what blocks the most.

1. **What must "v2" achieve?** The report can tell you what the system does; it cannot
   tell you what is wanted. The plausible readings are materially different work:
   (a) make recall *reliable* — the right memory shows up when it is relevant;
   (b) make memory *visible* — the user can see and correct what the room believes;
   (c) make memory *evolve* — supersession, decay, stance change over time;
   (d) make memory *reach every surface* — Council, rituals, letters, not just chat.
   Which of these, and in what order?

2. **Is the self-portrait scoring fix a standalone P1 PR, ahead of v2?** It is a
   different subsystem from recall (it reads `profile.answers`, not `memory_entries`),
   it is user-visible today, and it needs no database work. P-02 argues for shipping it
   alone. Confirm — and confirm whether the *prose* half (the watermark) ships in the
   same PR or separately, since they are two independent one-line-ish defects with the
   same symptom.

3. **What is the octagon supposed to measure?** This is a product question, not an
   engineering one, and the fix cannot be specified without it. The bank has no per-pill
   theme data, so any answer-sensitive score requires **authoring new data** across up
   to 360 questions — a per-pill weight, an axis polarity, or something else. Options
   differ by an order of magnitude in cost. Until this is ruled, the only honest
   alternatives are (i) leave it question-set-based and change the label so it does not
   claim to describe the person, or (ii) remove the octagon.

   **UPDATE 2026-09-03 — the founder answered the authoring half of this ruling** with a
   draft of per-pill weights (`tag=weight`, 0–2) for the 15 free-slice questions. What
   follows is verification and measurement of that draft against the bank at
   `b0148f73`. No code was changed; the analysis ran out-of-tree.

   **3a. The draft transcribes clean.**

   | Check | Result |
   |---|---|
   | Question ids vs `free_question_ids()` ([self_portrait.py:276-283](apps/api/services/self_portrait.py#L276-L283)) | 15/15 — exactly the free slice, no extras, none missing |
   | Tag triples vs each question's `theme_tags` | 15/15 match |
   | Pill labels vs `pills`, index by index | 60/60 match |
   | All-zero pills (an answer contributing nothing to any axis) | 0 |
   | Axes with zero dynamic range (i.e. still answer-blind) | 0 — spans run 4 (desire) to 15 (connection) |

   **3b. The weights close defect 1.** Over 4,000 random full profiles the draft yields
   **3,984 distinct octagons**, against today's single polygon shared by every free user
   (§2a). The blindness proved in §2a is genuinely removed by per-pill weights; nothing
   about the *shape* of `portrait_theme_scores` had to change to get there.

   **3c. The weights alone do not settle the outcome — the normalisation denominator
   does.** `_AXIS_PREVALENCE` ([self_portrait.py:157-172](apps/api/services/self_portrait.py#L157-L172))
   is a bank-wide **tag-instance count**, built for a counting numerator. Feeding it a
   weighted numerator leaves it dividing weights by counts. Measured over the same 4,000
   profiles:

   | Variant | Top axis = `doubt` | Next | Axis means |
   |---|---|---|---|
   | **V1** — keep bank-prevalence denominator, then max-normalize | **59.2%** | `connection` 23.0% (two axes = 82%) | `doubt` saturates at 0.895 |
   | **V2** — denominator = share-of-achievable for the answered set | 1.5% | `identity` 31.5%, `desire` 24.1%, `fear` 16.1% | all in 0.46–0.72 |

   This matters because the caption, the top-axis key and the observation cards all key
   off the **top axis**
   ([self-portrait/page.tsx:457-470, :527](apps/web/app/app/(tabs)/self-portrait/page.tsx#L457-L470);
   [selfPortraitCaption.ts](apps/web/lib/selfPortraitCaption.ts);
   [selfPortraitObservations.ts](apps/web/lib/selfPortraitObservations.ts)). Under V1 the
   polygon moves while roughly six users in ten still read the same headline — a partial
   fix that would plausibly land as *still broken*, just differently. Under V2 archetype
   probes separate legibly: all-pill-0 → `identity`, all-pill-1 → `desire`, all-pill-2 →
   `duty`.

   *Caveat on those percentages:* uniform-random pill choice is a neutral probe, not a
   prediction of real users, whose answers correlate.

   **3d. Expected ruling, pending founder sign-off** (recorded here as expected, not
   decided): **V2 share-of-achievable for scoring**, then **max-normalize for rendering
   only** — which preserves the frame-filling contract at
   [self_portrait.py:210-215](apps/api/services/self_portrait.py#L210-L215) without
   changing axis order — and **unweighted questions fall back to weight = 1 per tag**
   (legacy counting), so Pro answers keep contributing until their weights are authored.

   **3e. Two scope gaps the draft surfaces, both still open.**

   - **Three vocabulary tags are unused by the free slice:** `envy` (the `freedom` axis)
     and `grief` / `aging` (the `meaning` axis). Harmless for free users — every axis is
     still fed — but they will appear as soon as Pro questions are weighted, and the
     `freedom` and `meaning` axes are currently scored on a strict subset of their tags.
   - **This is 15 of 360 questions.** The weight = 1 fallback in 3d covers the remaining
     345 arithmetically, but it means a Pro user's octagon is a *mixture* of weighted and
     counted questions until authoring completes. Whether that mixture is acceptable as a
     shipping state, or whether the Pro authoring must land in the same release, is not
     settled by the fallback rule.

4. **Should Council receive memory at all?** Today it receives none, deliberately enough
   to be documented in the code. Giving it memory forfeits the whole-prompt cache
   ([council_service.py:280](apps/api/services/council_service.py#L280)) across four
   member calls per session, which is a real cost. There is also a defensible reading
   where a council of strangers *should* meet the matter cold. Ruling needed: memory in
   Council — yes with the cache cost, no by design, or only in the synthesis step.

5. **Deterministic or probabilistic recall?** Recall is currently one flat cosine query,
   `top_k=6`, hard cut at 0.70, no recency, no confidence, no type quota. The
   alternatives — a reserved slot per type, a recency term, always-include for
   `stated`/`self_portrait`, or a two-stage retrieve-then-rerank — are different systems
   with different costs. Which property matters more: that a relevant memory is *never*
   missed, or that an irrelevant one is *never* injected?

6. **Does the prompt get an instruction to use memory?** Every memory-bearing prompt in
   the product currently tells the model to hold it loosely or not recite it. That
   phrasing was chosen for good reasons (not parroting the user back at them). Changing
   it is the cheapest possible intervention on "feels generic" and the easiest to get
   wrong. Ruling: keep the dampening, replace it with a use directive, or A/B it.

7. **What should forgetting mean?** Three mechanisms exist and none does what the name
   suggests: the weekly cron cannot fire (§2c), `deactivate()` and the `PATCH`/`DELETE`
   endpoints have no caller (§1f), and the conversation cascade hard-deletes without
   warning (§2d). Ruling needed on all three: fix the cron threshold or delete the job;
   build the memory-management UI or remove the endpoints; and change
   `conversation_id` to `SET NULL` (a migration) or accept that deleting a thread
   destroys what the room learned in it.

8. **Should the three dead surfaces be removed as part of v2, or separately?**
   `generate_insight_task` (registered, never enqueued),
   `memory_service.get_user_memories` / `deactivate` (zero callers), and the `feeds`
   field on all 360 bank questions (zero consumers). Each is small; together they are
   the kind of thing that makes the next investigation slower.

9. **Do `another_mind` and `go_deeper` turns deserve memory extraction?** They read
   memory but never write it — the only extraction site is `stream_response`
   ([conversation_service.py:1115](apps/api/services/conversation_service.py#L1115)).
   Whether that is deliberate (guest turns are not the person's own thread) or an
   oversight is a product call.

10. **Does the TD-57 recommendation in §3 stand?** It is a recommendation, not a
    decision: fix-first with a memory-scoped DB fixture landing before any v2 schema or
    recall-SQL change. If the preference is to build the harness first, say so — it
    delays the portrait fix by however long the fixture takes.

---

## 5. What was checked and found absent (Rule 2, "confirm absence")

- No parallel memory implementation exists. One service, one table, one recall function.
  The three `recall` call sites are identical in shape and all in `conversation_service`.
- `counterview_service`, `insight_mirror_service`, `reflections_feed_service` and
  `retrieval_service` contain zero memory references.
- No migration after 013 alters `memory_entries` structure; 008 swapped its vector index,
  015 added FK indexes, 052 enabled RLS. 056 does not touch the table.
- No `alembic/` directory exists at `apps/api/alembic` — migrations are at
  `apps/api/db/migrations/versions/`. Head is `056_deletion_fks`.
- No admin endpoint, Stripe webhook handler, or scheduled-email path reads
  `memory_entries`; the only billing touch is a `COUNT` for feature telemetry.
