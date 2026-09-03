# Memory-v2 — Design

**Mode:** design only. No production code, no migration file, no test changed.
**Date:** 2026-09-03
**Baseline SHA (from `git ls-remote origin refs/heads/main`):**
`8d1ae05850ee46f6aec593ed5b6605641a690ebe`
**Companion:** `MEMORY_V2_INVESTIGATION_2026-09-03.md`, committed in this same PR.
That report is baselined at `b0148f73` — **eight commits older than this design.**
§1 below reconciles the two; read it before trusting any claim the report makes
about current behaviour.

All eight open questions in §7 were **resolved by the founder on 2026-09-03** and
are recorded there with their rulings. One of them — O-3 — surfaced a safety hole
during enumeration; §4c records it and PR-0 in §6 closes it.

No production database was queried. Everything below is read from code at
`8d1ae058`.

---

## 0. The rulings, verbatim

**Provenance.** claude.ai planning thread "Docs rotation v27 diff review and
merge", 2026-09-03. Ruling #1 was locked by the founder's reply *"πρωτα το
memory. μετα οτι πεις ως σειρα"* — delegating the ordering, and the framing of
rulings 2–10, to the planning assistant; 2–10 were proposed immediately after and
confirmed. Corroborated by the founder-authored context handoff ("10 rulings
LOCKED") and by six of the ten being implemented the same day (#595–#601).

Quoted in the original Greek. The English line under each is a gloss for readers
of this document, **not** the ruling — where the two could be read differently,
the Greek governs.

> **Ruling 1:** (a) αξιόπιστο recall → (d) μνήμη παντού. Τα (b)/(c) εκτός scope.

*Reliable recall first, then memory everywhere. (b) visibility and (c) evolution
are out of scope.*

> **2:** Portrait fix standalone, πριν το v2 — δύο PRs: watermark (tiny) πρώτα,
> scoring μετά.

*The portrait fix ships standalone, ahead of v2, as two PRs: the watermark (tiny)
first, the scoring after.*

> **3:** Το οκτάγωνο γίνεται answer-sensitive με per-pill weights ΜΟΝΟ στις 15
> free ερωτήσεις αρχικά. Εγώ παράγω draft weights → εσύ εγκρίνεις (όπως το copy)
> → μετά υλοποίηση. Οι 345 αργότερα, σταδιακά.

*The octagon becomes answer-sensitive via per-pill weights, initially on the 15
free questions ONLY. I draft the weights → you approve them (as with copy) → then
implementation. The other 345 later, gradually.*

> **4:** Council: μνήμη ΜΟΝΟ στο synthesis step — κρατάμε το cache των 4 member
> calls.

*Council: memory ONLY at the synthesis step — we keep the cache on the four member
calls.*

> **5:** Recall υβριδικό: always-include `stated`/`self_portrait`, top-k με type
> quota για τα υπόλοιπα. Προτεραιότητα: ποτέ λάθος μνήμη μέσα, έστω κι αν λείψει
> μία.

*Hybrid recall: always-include `stated`/`self_portrait`, top-k with a type quota
for the rest. Priority: never a wrong memory in, even if one goes missing.*

> **6:** Το "hold probabilistically" αντικαθίσταται με directive «χρησιμοποίησέ
> το όταν είναι σχετικό, μην το απαγγέλλεις». Χωρίς A/B.

*"Hold probabilistically" is replaced with the directive "use it when it is
relevant, do not recite it". No A/B.*

> **7:** Νεκρό stale-cron: σβήνεται. Cascade: migration σε SET NULL μέσα στο v2
> (real-Postgres run). Endpoints χωρίς caller → στο 8.

*The dead stale-cron: deleted. Cascade: a migration to SET NULL, inside v2 (with a
real-Postgres run). Endpoints with no caller → fold into 8.*

> **8:** Νεκρές επιφάνειες: ξεχωριστό cleanup PR, εκτός v2.

*Dead surfaces: a separate cleanup PR, outside v2.*

> **9:** Extraction σε another_mind/go_deeper: αναβολή, καταγράφεται ως
> deliberate-for-now.

*Extraction on another_mind/go_deeper: deferred, recorded as deliberate-for-now.*

> **10:** TD-57: fix-first· memory-scoped DB fixture υποχρεωτικά ΠΡΙΝ από όποιο
> v2 PR αγγίζει DDL ή recall SQL.

*TD-57: fix-first; a memory-scoped DB fixture is mandatory BEFORE any v2 PR that
touches DDL or recall SQL.*

### 0a. Recorded correction to Ruling #7

**The `/memory` endpoints were KEPT, not deleted.** Ruling #7 routed
"endpoints χωρίς caller" into ruling #8's cleanup; during that cleanup the founder
approved keeping them, because they back **privacy policy §7 (rectification)** —
the policy promises a user can correct what is held about them, and `PATCH`/`DELETE
/memory/{id}` are the mechanism that promise rests on. Caller count is not the
test for an endpoint a published policy commits to.

`memory_router` is still mounted at [main.py:118](apps/api/main.py#L118); the two
web helpers still have zero callers ([api.ts:1246-1252](apps/web/lib/api.ts#L1246-L1252)).
Recorded here as a correction. **Not re-opened by this design.**

### 0b. Recorded widening of Ruling #7c

Ruling #7 says *"Cascade: migration σε SET NULL"* without naming a table, and the
investigation discussed `memory_entries`. On 2026-09-03 the founder **explicitly
widened it to cover `insights.conversation_id` as well** — derived-data FKs to SET
NULL, one logical change — on the rationale that *"deleting a thread must not erase
what the room learned"* applies to insights *a fortiori*, as the visible spine of
every letter.

The widening is **contingent on PR-0 shipping first**; §4c is why.

---

## 1. DRIFT — the investigation report vs. current main

The report is baselined at `b0148f73`. Between that SHA and `8d1ae058` sit eight
commits, seven of them memory-domain. **Six of the ten rulings are already
implemented.** Every claim below was re-verified against code at `8d1ae058` per
Rule 1; nothing is carried from the report on trust.

| # | Ruling | Status at `8d1ae058` | Evidence |
|---|---|---|---|
| 1 | scope (a)→(d) | product decision; (d) is this document's §3 | — |
| 2 | portrait standalone, two PRs | **DONE**, split as ruled | #595 watermark, #596 scoring |
| 3 | per-pill weights, 15 free only | **DONE** — and exactly the §3d shape: share-of-achievable scoring, render-only max-normalize, weight-1 fallback for unweighted questions | [self_portrait.py:238-271](apps/api/services/self_portrait.py#L238-L271) |
| 4 | Council: synthesis only | **DONE** — members `memories=[]` with a "do not fix this" comment; synthesis recalls | [council_service.py:246-252](apps/api/services/council_service.py#L246-L252), [:352](apps/api/services/council_service.py#L352) |
| 5 | hybrid recall | **NOT DONE** — `recall` is unchanged | [memory_service.py:252-289](apps/api/services/memory_service.py#L252-L289) |
| 6 | use directive replaces the hedge | **DONE** | [system_base.jinja2:153-156](apps/api/prompts/system_base.jinja2#L153-L156), [prompt_builder.py:33-38](apps/api/services/prompt_builder.py#L33-L38) |
| 7a | dead stale-cron deleted | **DONE** — deleted, not re-thresholded; tombstone at [cron.py:495](apps/api/workers/cron.py#L495) | #599 |
| 7b | endpoints | **KEPT** — see §0a | — |
| 7c | cascade → SET NULL | **NOT DONE** — head is `056_deletion_fks`; `conversation_id` still `ondelete="CASCADE"`. Widened to two tables, see §0b | [models/__init__.py](apps/api/models/__init__.py) |
| 8 | dead surfaces, separate PR | **DONE** | #599 |
| 9 | another_mind / go_deeper extraction | **DEFERRED by ruling** — still one enqueue site | [conversation_service.py:1116](apps/api/services/conversation_service.py#L1116) |
| 10 | memory-scoped DB fixture before DDL/recall-SQL | **DONE — the gate is satisfied** | [tests/db_live/](apps/api/tests/db_live/), [backend-ci.yml:100-152](.github/workflows/backend-ci.yml#L100-L152) |

### 1a. What #599 removed, that the report describes as present

The report's §1a table and §1e job table both describe surfaces that no longer
exist. `memory_service.py` is **488 lines, not 516**:

- `MemoryService.get_user_memories` — **gone**
- `MemoryService.deactivate` — **gone**
- `generate_insight_task` and `INSIGHT_PROMPT` — **gone** (0 grep hits)
- the weekly `stale_memory` cron — **gone**; the report's finding (4) is closed by
  deletion, not by fixing the threshold
- the `feeds` field on the question bank — **gone** (0 of 360 questions carry it)

`recall`, `extract_and_store`, `_insight_gate_blocked` and `detect_recurrence`
are unchanged in body.

### 1b. What gained a caller

`memory_service.recall` now has **four** call sites, not three. The fourth is the
Council synthesis ([council_service.py:352](apps/api/services/council_service.py#L352)),
and it does **not** go through `build_system` — it composes its own block from
`MEMORY_USE_DIRECTIVE`, the shared Python constant, so the same copy governs both
paths. [prompt_builder.py:31](apps/api/services/prompt_builder.py#L31) records the
constraint explicitly: *a third wording may not appear anywhere.* Any surface this
design adds inherits that rule.

### 1c. Does any drift invalidate a ruling's premise?

**No.** Checked one by one: #5's premise (flat cosine, `top_k=6`, hard 0.70 cut, no
recency/confidence/type weighting) holds byte-for-byte at `8d1ae058`. #7c's premise
(hard delete + `ON DELETE CASCADE`) holds — [conversations.py:781-793](apps/api/routers/conversations.py#L781-L793)
still hard-deletes and both FKs are untouched by any migration after 013. #1(d)'s
premise holds for every surface §3 names.

Two premises **improved** rather than broke: #10's fixture now exists and is green,
so the gate it sets is already satisfied; and #4's synthesis-side recall is a
working reference implementation this design extends rather than replaces.

One report claim is **superseded**: §3's "no test file for `memory_service` at all"
is no longer true — [tests/db_live/test_memory_recall_and_cascades.py](apps/api/tests/db_live/test_memory_recall_and_cascades.py)
covers seven behaviours, and [tests/services/test_council_synthesis_memory.py](apps/api/tests/services/test_council_synthesis_memory.py)
covers the synthesis path. The gap is narrower than the report describes, not
absent.

---

## 2. Ruling #5 — hybrid recall

### 2a. Target behaviour

Recall today is one flat cosine query over every active row, ordered by pure vector
distance, cut at 0.70, capped at 6. It has no notion that the rows differ in *kind*.
They differ in one way that matters more than any other:

**Some memory rows are the person's own words. The rest are a model's inference
about them.**

`stated` is text the user typed, distilled. `self_portrait` is a pill the user
tapped. Those cannot be *wrong about the person* in the way `belief`, `pattern` or
`struggle` can — those are an LLM's reading, written at confidence ≥ 0.65, and a
confident wrong one is exactly the "λάθος μνήμη" the ruling forbids.

That is why the ruling separates them, and it is the whole architecture:

- **Lane A — standing.** `stated` and `self_portrait`. Exempt from the relevance
  threshold, because self-authored material does not need to earn its place by
  cosine score. Bounded, so it cannot flood the block.
- **Lane B — inferred.** Everything else. Subject to a **raised** floor and a
  **per-type quota**, so no single prolific type takes every slot and no weak match
  gets in.

The precision priority lands entirely on Lane B, which is where wrongness lives.
Lane A is safe *because* of what it is, not because of what it scores. This is not
a reinterpretation of the ruling — it is the reason the ruling names those two types
and no others.

### 2b. Slot budget

| Lane | Types | Cap | Per-type cap | Floor |
|---|---|---|---|---|
| A — standing | `stated`, `self_portrait` | 3 | 2 | **none** |
| B — inferred | `belief`, `value`, `struggle`, `pattern`, `milestone`, `counterview_belief`, `onboarding_profile` | 5 | 2 | `INFERRED_SCORE_FLOOR` |
| | | **8 total** | | |

Unfilled Lane A slots flow to Lane B (a user with no quiz answers and no ritual
text still gets up to 8). Lane B slots never flow to Lane A — a floor-less lane
must stay bounded. Spillover into Lane B costs no precision: every row it admits
already cleared the floor.

Eight rather than six because Lane A now occupies slots that were previously
contested. Holding the total at 6 would mean hybrid recall delivers *fewer*
inferred memories than today, which inverts the intent. Eight `[TYPE] content`
lines is a small block against the ~200-line system prompt it sits in.

`onboarding_profile` sits in **Lane B**, per **O-2**: it is self-authored like
`stated`, but the ruling names exactly two always-include types and the founder
declined to widen them. At most 2 rows per user
([profile_text.py:69-79](apps/api/services/profile_text.py#L69-L79)), so the
practical difference is small either way.

### 2c. Ordering inside the block

Lane A first, then Lane B by descending score. Standing self-description frames how
the persona reads the topical matches; the reverse ordering buries the frame under
whatever this turn happened to match. Deterministic tie-break on `created_at DESC,
id` so the same inputs always render the same block — a prompt that reorders
between identical turns is untestable and defeats prefix caching.

### 2d. Query shape

One round trip, ranking per type inside the database:

```sql
WITH scored AS (
    SELECT id, entry_type, content, confidence, created_at,
           1 - (embedding <=> CAST(:query_vec AS vector)) AS score,
           ROW_NUMBER() OVER (
               PARTITION BY entry_type
               ORDER BY embedding <=> CAST(:query_vec AS vector),
                        created_at DESC, id
           ) AS rank_in_type
    FROM memory_entries
    WHERE user_id = :user_id
      AND is_active = TRUE
      AND embedding IS NOT NULL
)
SELECT id, entry_type, content, confidence, created_at, score
FROM scored
WHERE (entry_type = ANY(:standing_types) AND rank_in_type <= :standing_per_type)
   OR (entry_type <> ALL(:standing_types)
       AND rank_in_type <= :inferred_per_type
       AND score > :floor)
```

The SQL returns **candidates**. Lane caps, spillover and final ordering are applied
in Python by a **pure function over the returned rows** — see §5a; that is what makes
most of this testable without a database.

Two properties of the current signature are preserved, and both are load-bearing:
the returned objects keep `.entry_type` and `.content` (the Jinja block at
[system_base.jinja2:159-161](apps/api/prompts/system_base.jinja2#L159-L161) and the
Council f-string at [council_service.py:354](apps/api/services/council_service.py#L354)
both read exactly those), and `query_embedding` still lets a caller pass a vector it
has already computed — the chat turn embeds once for recall and retrieval together
([conversation_service.py:658](apps/api/services/conversation_service.py#L658)).

### 2e. On the HNSW index — a claim this design does not assert

`ix_memory_entries_embedding_hnsw_cosine`
([008:52-56](apps/api/db/migrations/versions/008_hnsw_vector_indexes.py#L52-L56)) is
an approximate-nearest-neighbour index over the **whole table**. Recall is
**user-scoped**, and a highly selective non-vector filter is the known-difficult case
for HNSW: the planner either post-filters an ANN scan (walking many index entries to
find rows belonging to one user) or abandons the index for a scan under
`idx_memory_user (user_id, is_active)`.

The window-function rewrite removes any possibility of an ANN top-k shortcut — it
ranks the user's full active set. That is very likely fine: a user's active memory
count is tens to low hundreds, and 1536-dimension distance over a few hundred rows is
trivial work. **But this design does not assert that as fact.** Which plan runs today,
and which runs after the rewrite, is an `EXPLAIN` question, and the db_live fixture
can now answer it — see §5b, T-9.

Stated plainly because it cuts both ways: if the current query *is* getting a
degenerate HNSW plan, that is a pre-existing property this design would fix by
accident, not a regression it introduces.

### 2f. The `self_portrait` embedding distortion

`self_portrait` rows are rendered as
`Asked “<full scenario question>”, they answered: <pill>.`
([self_portrait.py:430-442](apps/api/services/self_portrait.py#L430-L442)). The
question runs long; the pill is two to five words. The embedding is therefore
dominated by **the wording of the question asked**, not by **the stance the person
took** — so cosine-ranking these rows ranks them by question topic.

Lane A blunts the impact — these rows no longer have to clear a threshold, so the
distortion costs relevance ordering within at most two slots, never presence. It does
not remove it.

**O-6 resolved: option (a), accept and name.** Revisit only if it becomes visible in
use. The alternatives, recorded with their cost so the decision can be re-taken
without re-deriving it:

| | Approach | Cost |
|---|---|---|
| **(a) — chosen** | Accept. Question topic is a serviceable relevance proxy. | zero |
| (b) | Re-render statements stance-first, re-embed every `self_portrait` row | one embed per row per user — a backfill job, real spend |
| (c) | Rank Lane A by `created_at DESC`, never by cosine | zero, but "most recent quiz taps" is a worse proxy than "same topic" |

### 2g. The floor

`INFERRED_SCORE_FLOOR` replaces the hard-coded `0.70` for Lane B. The ruling's
priority — *never a wrong memory in, even if one goes missing* — explicitly buys
precision with recall, so the floor rises.

**O-1 resolved: ship-and-tune at 0.75.** A named, tunable module constant; measured
against real usage post-launch. No calibration phase ahead of the change.

The number is recorded honestly as unvalidated. 0.70 has stood since the initial
commit with no measurement of its behaviour on real embeddings anywhere in the repo,
and 0.75 inherits that status. A synthetic-vector test pins *that the floor is
enforced* (§5b, T-1); it cannot tell you where the floor belongs. The post-launch
measurement is what settles that, and the constant is named so it can be moved
without touching the query.

---

## 3. Ruling #1(d) — memory everywhere

"Everywhere" is a direction, not an instruction to inject memory into every prompt.
The design question the ruling actually poses is *which surfaces speak to the person
as someone the room knows* — and some deliberately do not.

Every `build_system` call site and every prompt-composing surface at `8d1ae058`:

| Surface | Memory today | v2 | Why |
|---|---|---|---|
| chat `stream_response` [:702](apps/api/services/conversation_service.py#L702) | flat top-6 | **hybrid** | inherits from `recall` |
| `stream_another_mind` [:1214](apps/api/services/conversation_service.py#L1214) | flat top-6 | **hybrid** | inherits |
| `stream_go_deeper` [:1476](apps/api/services/conversation_service.py#L1476) | flat top-6 | **hybrid** | inherits |
| Council synthesis [:352](apps/api/services/council_service.py#L352) | flat top-6 (#598) | **hybrid** | inherits |
| Council members [:244](apps/api/services/council_service.py#L244) | `memories=[]` | **unchanged — cold** | Ruling #4, and the whole-prompt cache across four calls rests on it |
| reading revisit [:542](apps/api/services/conversation_service.py#L542) | `memories=[]` | **unchanged — cold** | **O-8 resolved: stays cold.** A single opening line is the surface where a name-dropped memory would be most conspicuous. Recorded alongside Ruling #9 as deliberate-for-now |
| weekly letter [arq_worker.py:1643](apps/api/workers/arq_worker.py#L1643) | portrait statements, insights, rituals — **no memory rows** | **add standing lane, `stated` only** | see §3a |
| monthly letter [arq_worker.py:1977](apps/api/workers/arq_worker.py#L1977) | same | **same** | same |
| weekly mirror [insight_mirror_service.py:130](apps/api/services/insight_mirror_service.py#L130) | seeded from an `Insight` + that conversation's messages | **unchanged** | already memory-derived: an Insight *is* the subsystem's other output. The mirror holds up one moment; widening it dilutes what it is |
| counterview | writes `counterview_belief`, reads nothing | **unchanged — deliberately cold** | it tests **one** belief the person just typed. Other memories dilute the adversarial frame. (PR-0 changes its safety handling, not its memory intake — §4c) |
| future-self note [scheduled_emails.py:87-101](apps/api/routers/scheduled_emails.py#L87-L101) | writes `stated`, reads nothing | **unchanged — deliberately cold** | the person writing to themselves. No persona speaks, so there is nobody to know them |
| `self_portrait_summary` [:105-122](apps/api/services/self_portrait_summary.py#L105-L122) | 8 recent rows, direct read | **unchanged** | already memory-fed, by recency — correct for a summary, where relevance has no query to be relevant to |
| `self_comparison_service` [:138-147](apps/api/services/self_comparison_service.py#L138-L147) | 8 `self_portrait_shift`, direct read | **unchanged** | a purpose-built selection, not a recall problem |
| `self_model_service` [:22-45](apps/api/services/self_model_service.py#L22-L45) | then/now windows, direct read | **unchanged** | same |

**Net effect of O-8:** ruling #1(d)'s rollout in this design is the four recall
callers plus the two letters. Every other surface is either already memory-fed by a
purpose-built selection, or cold on purpose and recorded as such.

### 3a. Query-free surfaces, and why Lane A generalises

A chat turn has a query: the user's message. **A letter does not.** It covers a week
or a month, and there is no single text to embed.

This is where the two-lane split pays a second dividend: **Lane A never needed a
query.** Its members are selected by type and bounded by count; cosine only *orders*
them. Drop the ordering and the lane still stands. So the same accessor serves both:

```
standing_memories(db, user_id, types=..., limit=..., query_embedding=None)
    query_embedding given  → cosine-ranked  (chat, council)
    query_embedding None   → created_at DESC (letters)
```

**Letters take `stated` only — never `self_portrait`.** They already carry a
`<self_portrait>` block built from `profile.answers` via `answers_to_statements`
(capped at `MAX_LETTER_STATEMENTS = 12`, [arq_worker.py:1610-1616](apps/api/workers/arq_worker.py#L1610-L1616)).
Injecting `self_portrait` memory rows would render the same quiz answers twice, in
two different sentence shapes, in one prompt. `stated` — the person's own words from
Council, mirrors, counterview and future-self notes — is the material the letter has
no other route to.

Proposed shape, ≤4 rows, inserted between `portrait_block` and `rituals_block` so
standing material sits together and the week stays last:

```
<what_you_know>
- ...
</what_you_know>
```

`LETTER_PROMPT` and `MONTHLY_PROMPT` each need one new guardrail paragraph
introducing the block, in the voice of the existing `<self_portrait>` and
`<rituals>` paragraphs. **That text is founder-approved copy** (this is exactly the
#597 pattern) — drafted in the PR-3 brief, approved before implementation, never
written straight into a diff (**O-7**). It must not become a third wording of the
memory directive; §1b's constraint applies.

---

## 4. Ruling #7c — the SET NULL migration (design, not written)

### 4a. The change

**File and revision id: `057_memory_conv_fk_set_null`** — 26 chars, filename ==
revision id, per C-04. The allowlist that grandfathers 013 and 014 is closed
([check_migration_naming.py:42-45](.github/scripts/check_migration_naming.py#L42-L45)).

`down_revision = '056_deletion_fks'`.

Per **O-3**, the migration covers **both** derived-data FKs that 013 set to CASCADE:

```
UP    ALTER TABLE memory_entries DROP CONSTRAINT memory_entries_conversation_id_fkey;
      ALTER TABLE memory_entries ADD  CONSTRAINT memory_entries_conversation_id_fkey
          FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL;

      ALTER TABLE insights DROP CONSTRAINT insights_conversation_id_fkey;
      ALTER TABLE insights ADD  CONSTRAINT insights_conversation_id_fkey
          FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL;

DOWN  ... the same two pairs, restoring ON DELETE CASCADE, in reverse order.
```

`conversation_id` is already nullable on both tables
([models/__init__.py](apps/api/models/__init__.py), `Mapped[str | None]`), so no type
change is needed — the same property 056 relied on for `safety_events`.

Both models' `ondelete="CASCADE"` must change to `"SET NULL"` in the same PR. They do
not create the constraints (migrations do), but a model that contradicts the schema is
how the next reader gets it wrong.

013 left two categories side by side — "derived data, safe to lose with parent"
(`memory_entries`, `insights`) against "preserve the row, null the ref"
(`safety_events`, `user_ritual_completions`). 057 moves the first pair into the
second category. The docstring should say that in those terms, because the categories
are the reasoning, not the clauses.

**DOWN is honest but lossy in effect**: restoring CASCADE does not re-attach rows
already orphaned, and a subsequent conversation delete will not remove them because
their `conversation_id` is NULL. The docstring must say so. Per C-05 this creates no
table, so RLS does not apply — 052 already covers both tables; the docstring should
say that explicitly rather than leave a reader wondering, as 053, 054 and 056 each do.

### 4b. Blast radius — every reader of `memory_entries.conversation_id`

| Reader | Effect of SET NULL |
|---|---|
| `recall` | none — never reads `conversation_id` |
| `detect_recurrence` [:380-390](apps/api/services/memory_service.py#L380-L390) | **behaviour change, in the safe direction.** The chat branch excludes candidates with `AND conversation_id != :conversation_id`; for an orphan that predicate is NULL, so the row is **not** matched. Orphans become invisible as recurrence evidence. Today those rows do not exist at all, so this is **no regression** — it is an opportunity not taken. `source_count`, which counts distinct prior conversations, stays correct precisely because orphans are excluded |
| `_insight_gate_blocked` | none — reads `insights.conversation_id`, covered in §4c |
| `self_model_service`, `self_portrait_summary`, `self_comparison_service` | none — filter on `user_id`, `entry_type`, `is_active` |
| `data_export_service` [:220-224](apps/api/services/data_export_service.py#L220-L224) | none — exports all rows for the user |
| `routers/billing.py` [:322-323](apps/api/routers/billing.py#L322-L323) | none — counts `self_portrait` rows, which carry NULL already |
| account deletion | none — `user_id` CASCADE still destroys every row; pinned by [test_memory_recall_and_cascades.py:250](apps/api/tests/db_live/test_memory_recall_and_cascades.py#L250) |

### 4c. Addendum — every reader of `insights.conversation_id` (the O-3 widening)

This enumeration is the reason PR-0 exists. Every row was read at `8d1ae058`.

| Reader | Reads | Effect of SET NULL |
|---|---|---|
| `_insight_gate_blocked` [memory_service.py:325](apps/api/services/memory_service.py#L325) | `Insight.conversation_id == conversation_id` — the per-conversation dedup half of the shared gate | **none.** An orphan matches no live conversation, so it cannot block a new insight. Today it does not exist; after, it exists and is invisible to the gate. No regression |
| `detect_recurrence` insight writes [memory_service.py:357](apps/api/services/memory_service.py#L357), [:483](apps/api/services/memory_service.py#L483) | passes `conversation_id` to the gate and the log line; writes a new `Insight` | **none** — writes only |
| **`counterview_service` safety gate** [:130-134](apps/api/services/counterview_service.py#L130-L134) | `insight.conversation_id is not None` → fetch that conversation's user messages → suppress on `medium`/`high`/`critical` | **UNSAFE → mitigated by PR-0.** See below |
| `insight_mirror_service` [:95-105](apps/api/services/insight_mirror_service.py#L95-L105) | the same guard, the same fetch, feeding a safety gate at [:112](apps/api/services/insight_mirror_service.py#L112) and an empty gate at [:116](apps/api/services/insight_mirror_service.py#L116) | **safe.** `messages = []` → the empty gate (`< INSIGHT_MIRROR_MIN_MESSAGES`, = 2 at [:18](apps/api/services/insight_mirror_service.py#L18)) returns `status="empty"` **before** generation. The safety gate being vacuous does not matter, because nothing is generated |
| `GET /insights` [routers/memory.py:76-89](apps/api/routers/memory.py#L76-L89) | `conversation_id` as an **optional** filter; the base query is `user_id` + `is_dismissed` | orphans stop appearing under `?conversation_id=`; they still appear in the unfiltered list, which is what makes the counterview path reachable |
| weekly-letter insight spine [arq_worker.py:1583-1590](apps/api/workers/arq_worker.py#L1583-L1590) | `user_id` + `is_dismissed` + a `created_at` window — **never** `conversation_id` | orphans now persist in the spine of future letters. **This is the ruling's intent**, landing as designed |
| monthly-letter insight spine [arq_worker.py:1946-1953](apps/api/workers/arq_worker.py#L1946-L1953) | same | same |
| `data_export_service` [:237-238](apps/api/services/data_export_service.py#L237-L238) | `user_id` only | none — orphans export, correctly |
| `routers/mirrors.py` | no `conversation_id` read ([:70](apps/api/routers/mirrors.py#L70) is a comment) | none |
| account deletion | `insights.user_id` CASCADE, untouched by 057 | none |

**The unsafe reader, in full.** [counterview_service.py:130](apps/api/services/counterview_service.py#L130)
guards a safety check on `insight.conversation_id is not None`. Its own comment states
the purpose: *"the source conversation may carry a high/critical user message even if
the distilled insight text reads clean — suppress on that too."* An orphaned insight
skips it, and the path is reachable end to end:

1. The user deletes a conversation. Today its insights are destroyed; after 057 they
   survive with `conversation_id = NULL`.
2. `GET /insights` still lists them — the base query filters `user_id` and
   `is_dismissed` only ([routers/memory.py:82-84](apps/api/routers/memory.py#L82-L84)).
3. `POST /insights/{id}/counterview` ([routers/memory.py:137](apps/api/routers/memory.py#L137))
   resolves the insight by `id` + `user_id`, with no conversation requirement
   ([counterview_service.py:96-103](apps/api/services/counterview_service.py#L96-L103)).
   Today this returns 404, because the row is gone.
4. The gate at :130 is skipped, and generation proceeds on the anchor-text check at
   [:120](apps/api/services/counterview_service.py#L120) alone.

The layer written for exactly this case is removed for exactly the insights it was
written for. **The mirror path has the identical guard and is safe** — because a
downstream floor catches the empty message list. Counterview has no such floor: an
empty list simply makes `any(...)` False and generation continues. Same shape,
opposite outcome, which is why it does not survive a glance.

**Mitigation — PR-0, merged before 057.** Treat `source == "insight"` with a NULL
`conversation_id` as **suppressed** rather than skipped: provenance cannot be verified,
so the counterview does not run. It fails closed. The product cost is that an orphaned
insight can never be counterviewed — nothing a user has today, since that call is a 404
today.

**No existing test pins insight cascade behaviour in either direction.** A repo-wide
`grep -rln "Insight" apps/api/tests/` returns **zero files**; the only occurrence
anywhere in the suite is a docstring line at
[db_live/test_memory_recall_and_cascades.py:13](apps/api/tests/db_live/test_memory_recall_and_cascades.py#L13)
naming the insight gate as deliberate follow-up. So unlike `memory_entries` — whose
cascade is pinned at [:215](apps/api/tests/db_live/test_memory_recall_and_cascades.py#L215)
and must be **inverted** by PR-1 — the insight cascade has nothing to rewrite and a gap
to fill. That is worse, not better: no test would have caught this hole, and none would
catch it reopening. PR-1 must **add** the insight cascade tests that do not exist, not
merely adjust one that does.

**Recorded as a TD candidate for the next docs rotation:** the production-grade fix is
to **persist the safety verdict on the insight at write time**, so the check survives
its conversation and does not depend on an FK. That is a schema change plus a backfill
plus a change to every insight writer. PR-0's fail-closed guard does not block it, and
should be replaced by it when it lands.

### 4d. Three consequences that are not bugs, and must not be discovered later

**(i) Deleting a thread stops erasing what was learned in it.** That is the ruling's
entire point, and it is also a change in what a user is likely to expect from a
delete button. The explore copy already promises the room "carries it into later
conversations" ([explore/page.tsx:135-138](apps/web/app/app/(tabs)/explore/page.tsx#L135-L138)),
so the *product* is consistent after this change and inconsistent before it.

**O-5 resolved: yes — one line is added to the delete-conversation confirmation,
inside PR-1's scope.** Founder copy, approved in the PR-1 brief before implementation.

**(ii) Memory now has no expiry at all.** #599 deleted the stale-memory cron because
it could never match a row — correct, it was dead. But the ruling replaced it with
nothing, and #7c removes the one forgetting mechanism that actually fired. After both
land, **no code path in the product ever deactivates a memory row**, except the
`/memory` endpoints of §0a, which have no UI. Rows accumulate for the life of the
account.

**O-4 resolved: unbounded growth accepted for v1.** Recorded as a **TD candidate for
the next docs rotation** — *no forgetting mechanism exists after #7a + #7c*. It is not
a defect in either ruling; it is a gap that only exists once both land, which is why it
is written down here rather than found later.

**(iii) Orphaned insights become reachable objects.** They persist in letter spines
and in the unfiltered insights list. §4c enumerates what reads them; PR-0 closes the
one path where that reachability is unsafe.

### 4e. Why this migration needs a real Postgres, and what CI does about it

Ruling #7 says "real-Postgres run" and Ruling #10 gates DDL PRs on the fixture. The
gate is satisfied: `db-tests` runs `pgvector/pgvector:pg16` as a service container and
builds the schema **by migrations**, not `create_all` — deliberately, because
`ON DELETE` clauses live only in migrations and a `create_all` schema would pass tests
production would fail ([conftest.py](apps/api/tests/db_live/conftest.py)).

Two properties of that job are design constraints, not trivia:

**The job gates on `paths: apps/api/**`** ([backend-ci.yml:5-13](.github/workflows/backend-ci.yml#L5-L13)).
PR-0 and the 057 migration PR both trigger it. **A docs-only PR — including this one —
produces no backend run at all**, which on the PR page is visually identical to a
passing one. That is the 2026-09-01 failure-log corollary, and it applies to reading
this PR's own checks.

**Production's database is not reproducible from migrations alone.** The fixture
found it: `alembic upgrade head` fails on an empty database because `049_quotes_expand`
UPDATEs 88 quote rows that no migration inserts, and `db/seed_quotes.py` can no longer
stand in for them — its data file has grown to the current 198-row corpus, so running
it at 048-state inserts 049's own rows ahead of 049 and trips
`uq_quotes_persona_locator_text`. The fixture therefore stages: upgrade to 048,
reconstruct the pre-049 corpus by subtraction, upgrade to head.

That is a **disaster-recovery** property, not a test inconvenience, and it is design
input for any memory DDL: every migration this design adds must be exercised through
that staged path, and anyone reasoning about a rebuild must not assume `upgrade head`
works. Recorded verbatim in the fixture docstring; it belongs in the next docs rotation
and is out of scope here.

---

## 5. Failure modes, and where each is tested

### 5a. The testability move

**Lane composition is extracted as a pure function** over already-fetched rows:

```
compose_recall(rows, *, standing_types, standing_cap, standing_per_type,
                        inferred_cap, inferred_per_type, floor) -> list[row]
```

The SQL fetches candidates; this function applies caps, spillover and ordering. It
takes no session and issues no query, so caps, quotas, spillover, tie-breaks and
ordering are ordinary unit tests. What remains for the database is what only the
database can answer: that the *right rows arrived* — pgvector arithmetic, window
ranking, and the ON DELETE clause.

Per C-06: any mock feeding this function must set **every** field it reads
(`entry_type`, `content`, `score`, `created_at`, `id`) — a `MagicMock` missing `score`
compares as a Mock and silently reorders the block instead of raising. Prefer a small
real row class, as the ring-true tests do.

### 5b. Failure modes

| # | Failure mode | Where tested |
|---|---|---|
| F-1 | A wrong (low-score) inferred memory reaches the prompt | **db_live** T-1 |
| F-2 | One prolific type consumes every slot | **unit** (compose) + **db_live** T-2 |
| F-3 | A `stated` / `self_portrait` row is dropped for scoring below the floor | **db_live** T-3 |
| F-4 | Lane A floods the block when the user has many quiz answers | **unit** (compose) |
| F-5 | Recall crosses users | **db_live** — already covered, [:159](apps/api/tests/db_live/test_memory_recall_and_cascades.py#L159) |
| F-6 | Inactive / embedding-less rows leak in | **db_live** — already covered, [:173](apps/api/tests/db_live/test_memory_recall_and_cascades.py#L173) |
| F-7 | Recall failure breaks a chat turn / council / letter | **unit** — fail-open at all five call sites |
| F-8 | The prompt block reorders between identical turns | **unit** (deterministic tie-break) |
| F-9 | Deleting a conversation destroys its memories **or its insights** | **db_live** T-4 — the memory half exists at [:215](apps/api/tests/db_live/test_memory_recall_and_cascades.py#L215) and **inverts**; the insight half does not exist and must be written |
| F-10 | Deleting a user fails to destroy memories **or insights** | **db_live** — the memory half is covered at [:250](apps/api/tests/db_live/test_memory_recall_and_cascades.py#L250) and must stay green through 057; the insight half is new |
| F-11 | Orphans distort `detect_recurrence`'s `source_count` or the per-conversation insight gate | **db_live** T-5 |
| **F-15** | **An orphaned insight reaches counterview generation without a conversation-level safety check** | **unit, in PR-0** — `source="insight"` with `conversation_id IS NULL` → `status="suppressed"`, no LLM call. **Pinned in db_live once 057 lands**: delete the conversation, then assert the surviving insight cannot generate a counterview |
| F-12 | A third wording of the memory directive appears | **unit** — extend [test_prompts.py:75](apps/api/tests/test_prompts.py#L75) and [test_council_synthesis_memory.py:140](apps/api/tests/services/test_council_synthesis_memory.py#L140) to the letters |
| F-13 | The letter renders quiz answers twice | **unit** — assert no `self_portrait` row in `<what_you_know>` |
| F-14 | Recall regresses to a pathological query plan | **db_live** T-9 (`EXPLAIN`) |

New db_live tests: **T-1** floor enforced from both sides for inferred types; **T-2**
per-type quota under a lopsided corpus; **T-3** a below-floor `stated` row is still
returned; **T-4** conversation delete **preserves** the row and NULLs the FK, for
`memory_entries` **and** `insights`; **T-5** an orphan is excluded from recurrence
candidates and from the per-conversation insight gate, and `source_count` stays
correct; **T-9** `EXPLAIN` on the composed query, asserting a plan shape rather than a
timing.

**F-9 is the one to watch, and it is now two things.**
`test_deleting_a_conversation_destroys_the_memories_extracted_from_it` is a *correct*
test of *current* behaviour that 057 deliberately reverses — it must be rewritten in
the migration's own PR, with its docstring naming the ruling; not deleted, and not left
to fail. The insight half has no test at all (§4c), so PR-1 writes it from scratch. The
2026-08-23 corollary applies to the first: an assertion that changes meaning is
unverified text until re-read against the new intent.

---

## 6. PR decomposition

One logical change each (P-02), riskiest first, with the safety fix ahead of the
change that would expose the hole. Ruling #10's gate is satisfied before any of them —
the fixture exists and is green at `8d1ae058`.

**PR-0 — fail-closed counterview guard** *(no dependency; must merge before PR-1)*
[counterview_service.py:130](apps/api/services/counterview_service.py#L130): an insight
with a NULL `conversation_id` yields `status="suppressed"` instead of skipping the
conversation-level safety check. Unit test for F-15.
*It ships first, and alone, for two reasons. It is a safety change and belongs in a PR
that is only a safety change. And it must land before 057, or there is a window in
which orphaned insights exist and the gate is open.*
Small enough to review in one sitting; that is the point.

**PR-1 — `057_memory_conv_fk_set_null`** *(depends on: **PR-0 merged**)*
The migration over **both** tables, plus both models' `ondelete`. Inverts F-9's memory
test, **writes the insight cascade tests that do not exist**, adds T-4 and T-5. Carries
**O-5's delete-confirmation copy line**, founder-approved in the PR-1 brief before
implementation — that copy is user-facing text about the behaviour this migration
changes, so it belongs with it rather than trailing it.
*Riskiest of the remaining three: production DDL, runs on deploy, and the DOWN cannot
restore orphaned rows.*
Note it has a **user-visible side effect on its own**: memories that would previously
have vanished with a deleted thread now persist and are recallable by today's flat
query. That is the ruling's intent, landing one PR early.

**PR-2 — hybrid recall** *(no dependency on PR-0 or PR-1)*
`compose_recall` + the windowed SQL + `INFERRED_SCORE_FLOOR = 0.75` and the lane
constants. Unit tests for composition; T-1, T-2, T-3, T-9 in db_live.
**No call-site changes** — all four existing callers keep calling `recall` and get the
new behaviour. That is deliberate: it keeps the blast radius inside one function and
makes the diff reviewable against the SQL.
*Second-riskiest: it changes the hottest read path in the product.*

**PR-3 — letters receive standing memory** *(depends on: PR-2 for `standing_memories`)*
`<what_you_know>` in the weekly and monthly letters, `stated` only, ≤4 rows, plus one
guardrail paragraph in each prompt.
**Blocked on copy approval** before implementation (**O-7**), per SKILL.md §3 and the
#597 pattern.

**Cut from the decomposition:** the reading-revisit PR. **O-8** ruled the revisit stays
cold, so there is nothing to ship.

**Parallel, non-code:** Pro per-pill weight authoring for the remaining 345 questions
(investigation §3e) — planning assistant drafts, founder approves, per Ruling #3's
"οι 345 αργότερα, σταδιακά". A content track, not a PR in this decomposition. Until it
completes, a Pro user's octagon is a mixture of weighted and weight-1 questions;
whether that mixture is an acceptable shipping state was left open by §3e and is not
resolved here.

**Deferred by ruling, recorded not designed:**
- extraction on `another_mind` / `go_deeper` (Ruling #9, *deliberate-for-now*). Still
  one enqueue site ([conversation_service.py:1116](apps/api/services/conversation_service.py#L1116));
  both surfaces read memory and write none.
- memory in the reading revisit (**O-8**, *deliberate-for-now*, recorded alongside
  Ruling #9).

**TD candidates for the next docs rotation** — both created by decisions recorded in
this document, neither a defect:
1. **No forgetting mechanism exists after #7a + #7c** (§4d-ii, O-4).
2. **Persist the safety verdict on the insight at write time** (§4c) — the
   production-grade replacement for PR-0's fail-closed guard.

**Out of scope by Ruling #1:** (b) memory visibility — note that §0a's kept endpoints
are the backend half of it, with no UI — and (c) supersession / decay / stance
evolution.

---

## 7. Open questions — all resolved by the founder, 2026-09-03

Recorded with their rulings. Nothing in this section is open.

**O-1 — What is `INFERRED_SCORE_FLOOR`?**
**RESOLVED — ship-and-tune.** `INFERRED_SCORE_FLOOR = 0.75` as a named tunable
constant; measure against real usage post-launch. No calibration phase. (§2g)

**O-2 — Which lane does `onboarding_profile` belong to?**
**RESOLVED — `onboarding_profile` stays in Lane B.** The ruling's two always-include
types are not widened. (§2b)

**O-3 — Does the SET NULL migration also cover `insights.conversation_id`?**
**RESOLVED — both tables, contingent on PR-0 shipping first — founder ruled Option (A)
2026-09-03.** Derived-data FKs → SET NULL as one logical change. The founder explicitly
widened ruling #7c's letter, on the rationale that *"deleting a thread must not erase
what the room learned"* applies to insights a fortiori, as the visible spine of every
letter. The enumeration this triggered found one reader where SET NULL was unsafe
([counterview_service.py:130](apps/api/services/counterview_service.py#L130)); PR-0
closes it before 057 lands. (§0b, §4a, §4c, §6)

**O-4 — Does v2 need a replacement forgetting mechanism?**
**RESOLVED — unbounded growth accepted for v1.** Recorded as a TD candidate for the
next docs rotation: no forgetting mechanism exists after #7a + #7c. (§4d-ii, §6)

**O-5 — Does the delete-conversation copy change?**
**RESOLVED — yes.** One line added to the delete-conversation confirmation, inside
PR-1's scope. Copy is founder-approved in the PR-1 brief before implementation.
(§4d-i, §6)

**O-6 — The `self_portrait` embedding distortion.**
**RESOLVED — option (a), accept and name.** Revisit only if visible in use. (§2f)

**O-7 — The letter's `<what_you_know>` guardrail paragraph.**
**RESOLVED — procedural.** The guardrail paragraph is approved in the PR-3 brief,
before implementation. (§3a, §6)

**O-8 — Does the reading revisit get memory?**
**RESOLVED — the revisit stays COLD.** PR-4 is cut from the decomposition; the revisit
is recorded alongside Ruling #9 as deliberate-for-now. (§3, §6)

---

## 8. What was checked and found absent (Rule 2)

- No parallel memory implementation. One service, one table, one recall function,
  now four callers.
- No migration after 013 alters `memory_entries` or `insights` structure; 008 swapped
  the vector index, 015 added FK indexes, 047 added `insights.theme`, 052 enabled RLS,
  056 does not touch either. Head is `056_deletion_fks`.
- No ARQ task, cron job, Stripe webhook handler, admin endpoint or scheduled-email
  path reads `memory_entries` beyond the readers tabulated in §4b, or
  `insights.conversation_id` beyond those in §4c. The weekly stale-memory cron that
  used to is gone (#599).
- `counterview_service`, `reflections_feed_service` and `retrieval_service` contain
  zero references to `MemoryEntry`, `memory_entries` or `memory_service`.
  `insight_mirror_service` reads `Insight`, never `MemoryEntry`.
- No test file anywhere in `apps/api/tests/` references the `Insight` model
  (`grep -rln "Insight"` → zero files). The insight cascade is untested in both
  directions.
- No frontend surface reads or writes a memory row. `getMemory` / `deleteMemory` still
  have zero callers; `/app/explore/memory` is a static explainer with no API call.
