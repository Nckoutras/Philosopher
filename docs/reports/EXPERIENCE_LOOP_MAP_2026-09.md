# EXPERIENCE_LOOP_MAP — 2026-09

**Status:** investigation only. No code, no branch, no proposals.
**Purpose:** the CLAUDE.md Rule 1 enumeration pass for P2 item 1 (Continue the
Thread) and item 2 (Epistemic loop).
**Read against:** `main` at `dba36c2d`, migration head `059_job_run`.
**Method:** live code only. Every claim below carries a `file:line` and was read
this session, not carried from a prior document.

## Findings

1. **AI verdicts are terminal.** No mirror, council, counterview or you-vs-you
   output is ever read back into any prompt — generated, shown, saved, never
   consulted again. The letter reading its own prior letters is the sole
   exception. (§2)
2. **Nothing is ever confirmed or rejected.** No confirm/reject/accuracy field
   exists on `memory_entries` or `insights` anywhere in the schema, and
   `ring_true` — the nearest thing to a user verdict — is stored on two tables
   and read by no prompt, no recall, no ranking. (§2, §5)
3. **Nothing links a letter to a conversation.** `weekly_letters` is
   period-scoped with no `conversation_id`, and every letter door creates a new
   thread rather than reopening one. (§4)
4. **The mirror ring-true note has no input.** Column, safety gate and memory
   write are all built; the mirror page contains zero textareas, so the note can
   never be sent. (§3)
5. **The you-vs-you note writes no memory even if sent.** Unlike the mirror, that
   route enqueues no memory task at all — the note would be a stored string and
   nothing more. (§3)
6. **Pattern insights fall through to a generic chip.** The named-door map covers
   four types; `pattern`, the most common, lands on the untyped "Reflect in the
   Mirror" fallback. (§3)

This document enumerates and names gaps. It does not design anything.

---

## 0. The two mechanisms everything else hangs off

Two things recur often enough that the rest of the map is unreadable without
them.

**The memory lanes.** `memory_entries` rows are split into two lanes by
`entry_type`, and the split is epistemic, not structural
(`services/memory_service.py:37`):

- **Lane A (`STANDING_TYPES = ("stated", "self_portrait")`)** — the person's own
  words or their own tap. Exempt from the relevance floor, capped at 3 rows
  (`:39-41`).
- **Lane B (everything else)** — a model's inference about them. Must clear
  `INFERRED_SCORE_FLOOR = 0.75` (`:51`), capped at 5.

The lane test is a catch-all (`entry_type NOT IN standing`), never an allow-list,
so an unrecognised type lands in Lane B rather than vanishing. `entry_type` is
**not validated on write** — extraction stores the LLM's own `type` string
verbatim (`:347`).

Two read paths exist and they are not interchangeable:
- `recall()` (`:412`) — cosine-ranked against a query. Used where there is a
  query to embed.
- `standing_memories()` (`:451`) — Lane A by recency, query-free. Used where
  there is no single text to embed (letters).

**The prefill convention.** A door that leads into chat seeds the composer
through `sessionStorage`, read-and-cleared on chat mount
(`apps/web/app/app/chat/conv/[id]/page.tsx:238-239`). Keys: `chat_prefill_<convId>`
for chat, bare `council_prefill` / `council_source` / `council_conversation_id`
for the Council. **No table, no column, no API.** This is the existing
zero-schema mechanism for carrying context across a door.

---

## 1. Surface map — reads, writes, leads

### Chat (send a message)

- **Reads:** memory via `recall()` (`services/conversation_service.py:658`),
  both lanes, budget 8. RAG source chunks. Persona config. Not insights, not
  prior verdicts.
- **Writes:** `messages`. Then, asynchronously and only when the exchange was
  safety-clean: `extract_memory_task` (`:1115`) → up to N `memory_entries` of
  LLM-chosen type (`memory_service.py:343-347`), and at most one `Insight`
  promoted from a dilemma/belief/aspiration signal (`:372-400`).
  `assess_conclusion_task` (`:1136`) on a depth cadence.
  `generate_conversation_title` at ≥2 messages (`:1106`).
- **Leads:** the insight door chip on the last assistant message
  (`components/chat/QuickActionsRow.tsx:12-18`), another-mind sheet, Council
  chip, deep-mode toggle. Insights are fetched per-conversation and globally
  (`app/app/chat/conv/[id]/page.tsx:159`, `:170`).

### Deep mode

- A sticky per-conversation flag read at `conversation_service.py:794`, gated by
  `check_deep_mode_limit` for free users (`:802`). It changes the prompt, not
  the data. **Reads and writes nothing of its own.** No door out.

### Another-mind

- **Reads:** `recall()` (`conversation_service.py:1200`).
- **Writes:** messages only. No insight promotion on this path.
- **Leads:** stays in the same conversation.

### Go-deeper

- **Reads:** `recall()` (`conversation_service.py:1462`).
- **Writes:** messages only.
- **Leads:** stays in the conversation.

### Council

- **Reads:** `recall()` against the matter text (`services/council_service.py:355`).
- **Writes:** `council_sessions` / `council_responses` (`:321`). **Plus one
  conditional memory write:** if and only if the matter came from chat *and* was
  edited by the user, `distill_user_text_to_memory_task` runs with source
  `council_edit` (`:421`) → a `stated`, confidence-1.0 Lane A row. Never for a
  direct or unedited council.
- **Leads:** save → reflections feed as `council_verdict`
  (`reflections_feed_service.py:104`).

### Counterview

- **Reads:** the seeding `Insight` when entered via `?insightId=`
  (`services/counterview_service.py:98`). Does **not** read memory.
- **Writes:** `counterviews` / `counterview_responses` / `counterview_turns`.
  Two conditional memory writes: the typed belief on the voluntary path
  (`routers/counterview.py:195` → `counterview_belief_task`,
  `arq_worker.py:614`, `entry_type="counterview_belief"` → **Lane B**), and a
  user rebuttal (`counterview_service.py:662`, source `counterview_rebuttal` →
  `stated`, **Lane A**).
- **Leads:** save → reflections feed as `counterview_verdict` (`:162`).

### You-vs-you (self-comparison)

- **Reads:** `memory_entries` where `entry_type = "self_portrait_shift"`
  (`services/self_comparison_service.py:139-145`) — a direct table read, not
  `recall()`. Plus conversation messages.
- **Writes:** `self_comparisons`, including `ring_true` / `ring_true_note`
  (`models/__init__.py:404`). **No memory write of any kind** — see §3.
- **Leads:** save → reflections feed as `yvy_sentence` (`:195`).

### Mirror (weekly / preview / insight-seeded)

- **Reads:** conversation messages for the period. The insight-seeded variant
  reads its `Insight` (`services/insight_mirror_service.py:62`). Does not read
  memory.
- **Writes:** `mirrors` with a JSONB payload, plus `ring_true` /
  `ring_true_note` / `ring_true_at` (`models/__init__.py:331-333`). When a note
  is present, `distill_user_text_to_memory_task` with source `mirror_ring_true`
  (`routers/mirrors.py:149`) → Lane A. **In practice this never fires — see §3.**
- **Leads:** "Continue with {host}" **creates a new conversation**
  (`app/app/mirror/page.tsx:262`); "Take it to the Council" seeds
  `council_prefill` from the mirror thread (`:612`). Save → reflections feed as
  `mirror_verdict` (`:63`).

### Self-portrait

- **Reads:** the user's own quiz answers from `user_preferences`.
- **Writes:** on each answer, `seed_self_portrait_memory_task`
  (`routers/preferences.py:361`) → a `self_portrait` row (**Lane A**,
  confidence 0.8, `arq_worker.py:814`) and, when the answer changed, a
  `self_portrait_shift` row (**Lane B** by the catch-all rule,
  `arq_worker.py:843`). Old rows of the same `source_turn` are deactivated, not
  deleted.
- **Leads:** "Take it to {name}" creates a new conversation and seeds
  `chat_prefill` from a frozen per-axis template
  (`app/app/(tabs)/self-portrait/page.tsx:530`).

### Onboarding profile

- **Writes:** `seed_profile_memory_task` (`routers/preferences.py:97`) →
  `onboarding_profile` rows. **Lane B** — Ruling #5 / O-2 explicitly declined to
  widen Lane A for this type (`memory_service.py:28-30`).

### Future-self

- **Reads:** nothing.
- **Writes:** `scheduled_emails`, with an optional `prediction` at schedule time
  and a `review_text` on open (`models/__init__.py:609-612`). The note →
  `distill_user_text_to_memory_task` source `future_self_note`
  (`routers/scheduled_emails.py:101`) → Lane A.
- **Leads:** review → reflections feed as `future_self_review` (`:228`).

### Weekly / monthly letter

- **Reads:** the widest read in the product. Period messages, the self-portrait
  block, `Insight` rows, **`standing_memories()`** (Lane A only, query-free —
  `arq_worker.py:1715` weekly, `:2107` monthly), **prior letters including their
  own generated text** (`:1606-1629`), and **prior write-backs** (`:1653-1657`).
  `self_portrait` is deliberately excluded from the standing block to avoid
  duplicating the portrait block.
- **Writes:** `weekly_letters`, plus `write_back_text` / `write_back_at` from
  the reader (`routers/weekly_letters.py:142-143`) → also
  `distill_user_text_to_memory_task` source `letter_write_back` (`:156`) → Lane A.
- **Leads:** see §4.

### Reflections feed

- **Reads only.** Merges seven item kinds into one `saved_at`-descending list
  (`services/reflections_feed_service.py`): `line` (:35), `mirror_verdict` (:63),
  `council_verdict` (:104), `counterview_verdict` (:162), `yvy_sentence` (:195),
  `future_self_review` (:228), `quote` (:263). Writes nothing.
- **Leads:** **this is the one surface that reopens an existing conversation**
  rather than creating a new one — `router.push('/app/chat/conv/' + item.conversation_id)`
  (`app/app/(tabs)/reflections/page.tsx:305`, `:341`).

### Insights

- **Reads:** `GET /insights` scoped to a conversation or global
  (`routers/memory.py:75`).
- **Writes:** `is_dismissed` only (`:92`).
- **Leads:** the four typed doors in `apps/web/lib/useInsightDoors.ts`.
  `insights/page.tsx:135` also reopens an existing conversation from a recent
  saved line.

---

## 2. Epistemic status of every write

Three kinds of text exist in this product, and only two of them are ever stored
as memory.

| Kind | Where it is written | Lane | Confidence |
|---|---|---|---|
| **User-stated** — the person's own words, distilled | council edit, counterview rebuttal, mirror ring-true note, letter write-back, future-self note (all via `distill_user_text_to_memory_task`) | **A** (`stated`) | 1.0 |
| **User-tapped** — a pill they chose | self-portrait answer (`arq_worker.py:814`) | **A** (`self_portrait`) | 0.8 |
| **User-typed, undistilled** | counterview belief (`arq_worker.py:614`) | **B** (`counterview_belief`) | 0.7 |
| **User-stated, onboarding** | `arq_worker.py:750` | **B** (`onboarding_profile`) | — |
| **AI-inferred about the user** | chat extraction (`memory_service.py:347`) — belief/value/struggle/pattern/milestone | **B** | ≥0.65 |
| **AI-inferred, derived** | `self_portrait_shift` (`arq_worker.py:843`) | **B** | 0.8 |
| **AI-inferred, promoted** | `Insight` rows — signal (`memory_service.py:395`) and recurrence (`:683`) | *not memory at all* | n/a |

### Where does a ritual verdict go?

A **ritual verdict** — the mirror payload, the council responses, the
counterview responses, the you-vs-you comparison — is the AI's *output about the
user*. It is written to its own table and to the reflections feed if saved.

**It is never written to `memory_entries`. It is never recalled.**

Verified: no call site reads `Mirror.payload`, `CouncilResponse` or
`SelfComparison` into any prompt. The only reads of those tables outside their
own service are the reflections feed, the data export, and
`image_service.py:310` (share-card persona names).

The **one exception** is the letter, which reads its own prior letters back into
`<prior_letters>` (`arq_worker.py:1606-1629`). That is a letter→letter loop
inside a single engine, not a general recall path.

So the shape of the epistemic system today is:

- **User words flow forward.** Five surfaces route the person's own text into
  Lane A, where it is floor-exempt and reaches chat, council and letters.
- **AI verdicts do not flow forward.** They are terminal: generated, displayed,
  optionally saved for the human to re-read, and never consulted again.
- **AI inferences about the user flow forward, unverified.** Lane B rows and
  `Insight` rows are written from LLM output at a confidence threshold and are
  recalled without the user ever having seen, let alone confirmed, most of them.

### Is anything ever confirmed or rejected?

**There is no confirm/reject field anywhere in the schema.** Grepped across
`models/__init__.py` and all 59 migrations: no `is_confirmed`, `is_accurate`,
`user_verdict`, or equivalent on `memory_entries` or `insights`. What exists:

- `Insight.is_dismissed` (`models/__init__.py:313`) — a **hide**, not a verdict.
  It removes the card; it does not tell the system the observation was wrong,
  and nothing downstream reads it as a signal about accuracy.
- `MemoryEntry.is_active` (`:291`) — a deactivation used for supersession
  (self-portrait re-answers, onboarding re-seeds), never user-driven.
- `MemoryEntry.confidence` (`:289`) — set at write time by the extractor, never
  updated afterwards by anything.

The nearest thing to a user verdict in the product is `ring_true` on mirrors
(`:331`) and on self-comparisons (`:403`) — a three-value enum
`yes | partly | no`. It is stored and **never read by anything**: no prompt, no
recall, no ranking. See §5.

---

## 3. Dead, unreachable, or one-sided

### The mirror ring-true note — backend complete, no input exists

Confirms the v26 "0 inputs" finding and explains it structurally.

The backend is fully built: a `ring_true_note` column (`models/__init__.py:332`),
a pre-persistence safety gate that runs *before* any attribute assignment
(`routers/mirrors.py:106-131`), and a memory enqueue on a non-empty note
(`:149`).

**The mirror page contains zero textareas.** `grep -c "textarea" = 0`, and the
handler calls `api.setRingTrue(mirror.id, value)` with **no note argument**
(`app/app/mirror/page.tsx:231-240`). The three chips submit and the UI prints
"Noted." (`:588`).

So `Mirror.ring_true_note` is unreachable from the product, and with it the
safety gate and the only Lane A write the mirror could ever produce.

### The you-vs-you note — same shape, and it writes less

`api.setSelfComparisonRingTrue(comparisonId, value)` is likewise called with no
note (`app/app/you-vs-you/page.tsx:151`), while the backend accepts one
(`routers/self_comparison.py:39`, max 280 chars) and safety-gates it (`:114-137`).

**Asymmetry worth recording:** even if a note were sent, this surface — unlike
the mirror — **does not enqueue a memory task at all**. `grep enqueue
routers/self_comparison.py` returns only a comment (`:116`). The mirror's note
would become a Lane A memory; the you-vs-you note would become a stored string
and nothing else.

### The generic doorway chip — removed in one place, live in another

The brief lists this as possibly dead. Measured, it is neither dead nor generic:

- `QuickActionsRow.tsx:12-18` maps five types to five named chips and the comment
  states the generic fallback **was deliberately removed**: *"Null/unknown types
  get NO chip — the old generic 'Insight' fallback is gone."*
- `InsightCard.tsx:43-52` still has a trailing `else → 'Reflect in the Mirror'`.

That `else` is **reachable**, because `pattern` falls through to it — and
`pattern` is the most common type, being the recurrence-detector default
(`memory_service.py:645`, `:669`). It is unreachable only for types that are
never written.

### Insight types declared but never written

`models/__init__.py:310` documents `pattern | shift | question | challenge`.
Only five values are ever produced: `dilemma`, `belief`, `aspiration`
(signal promotion, `memory_service.py:372`), and `pattern` / `shift`
(recurrence, `:656` — the classifier is constrained to exactly those two).
**`question` and `challenge` are never written by any code path.**

### `assess_conclusion_task`

Enqueued on a depth cadence (`conversation_service.py:1136`). Its output is not
part of the memory or insight loop and does not appear on any surface mapped
here.

---

## 4. The letter

**What `read_url` opens.** `read_url = f"{config.FRONTEND_URL}/app/letters/{letter.id}"`
(`arq_worker.py:1339`), passed to the email template at `:1350` and rendered as
"Read it in the app →" (`:1275`). It opens the **letter**, at
`apps/web/app/app/letters/[id]/page.tsx`. Nothing else.

**Is there a per-conversation deep link?** Yes, the route exists and is used
widely — `/app/chat/conv/{id}` — but **the letter does not use it to reopen
anything.** The letter's persona tap calls `api.createConversation(...)` and
pushes the **new** conversation's id (`app/app/letters/[id]/page.tsx:131`),
seeding the composer with a template built from the letter title (`:120-129`):

> `This week's letter touched on something I'm not done with — "{title}". I'd like to look at it with you.`

Of the twelve `/app/chat/conv/` pushes in the web app, only three reopen an
existing thread — `reflections/page.tsx:305` and `:341`, and
`insights/page.tsx:135`. Every other door, the letter included, **creates a new
conversation**.

**What "the conversation the letter is about" would mean today.** It has no
referent in the data. `weekly_letters` is period-scoped: `period_start` /
`period_end` / `kind` with a uniqueness index on `(user_id, period_start, kind)`
(`models/__init__.py:354-356`, `:384`). There is **no `conversation_id` column
on `weekly_letters`**, and the letter is generated from every message in the
period across every persona, plus insights, plus standing memory. A week is
routinely many conversations.

The nearest available referents, all indirect:

- `Insight.conversation_id` (`models/__init__.py:307`) — the insights a letter
  is built from each carry the conversation they were raised in. **Nullable and
  `ON DELETE SET NULL`**, deliberately: *"the 'what the room noticed' spine of
  every letter outlives the thread it was raised in."* So it is a hint, not a
  key, and it is null for any deleted thread.
- `MemoryEntry.conversation_id` (`:285`) — same `SET NULL` treatment (migration
  057), and null by construction for every task-written row
  (`counterview_belief`, `onboarding_profile`, `self_portrait`, and all five
  `distill_user_text_to_memory_task` sources pass `None`).
- `payload.title` — free text, no id.

---

## 5. Raw material for the two P2 items

Enumeration of what exists. No design.

### Item 1 — "Continue the thread", reusable with zero new tables

- **A reopen route that already works:** `/app/chat/conv/{id}`, exercised by
  `reflections/page.tsx:305`, `:341`, `insights/page.tsx:135`.
- **A prefill convention that needs no schema:** `chat_prefill_<convId>` written
  before the push, read-and-cleared on mount
  (`app/app/chat/conv/[id]/page.tsx:238-239`), 600-char cap by convention. Five
  surfaces already use it.
- **A worked precedent for prefilling from a letter:** the suggested-persona tap
  already composes a first message from letter content
  (`letters/[id]/page.tsx:120-129`) — it just aims at a new conversation.
- **Conversation identity on the letter's own inputs:** `Insight.conversation_id`
  (`models/__init__.py:307`), populated for chat-derived insights, nullable and
  `SET NULL` on thread delete.
- **Titles exist:** `generate_conversation_title` runs at ≥2 messages
  (`conversation_service.py:1106`), so a reopened thread has a human label.

**The gap:** nothing links a letter to a conversation. The link would have to be
derived at read time from the insights the letter was built from, or stored.
Both are outside this document.

### Item 2 — confirm/reject

**What exists for a verdict today:**

- `ring_true` on `mirrors` (`models/__init__.py:331`) and on `self_comparisons`
  (`:403`) — `yes | partly | no`, `CheckConstraint`-enforced, with a
  `ring_true_at` timestamp. **Written by the UI, read by nothing.** The full
  contract: `POST /mirrors/{id}/ring-true` (`routers/mirrors.py:91`) and
  `PATCH /self-comparison/{id}/ring-true` (`routers/self_comparison.py:97`);
  both safety-gate an optional note before persisting anything; the mirror
  enqueues a Lane A memory from the note, the self-comparison does not.
- `Insight.is_dismissed` (`:313`) — hide only, via
  `PATCH /insights/{id}/dismiss` (`routers/memory.py:92`), with a 5-second
  client-side undo before the call commits
  (`apps/web/lib/useInsightDoors.ts:71-83`).

**What does not exist:**

- No confirm/reject/accuracy field on `memory_entries` or `insights` — verified
  across the model file and all 59 migrations.
- No read path that would consult one. `recall()` (`memory_service.py:412`)
  ranks by cosine and lane; `compose_recall` (`:117`) applies caps and
  spillover. Neither takes any user-verdict input, and `confidence` is never
  updated after write.
- No admission rule keyed on user feedback. Lane membership is decided purely by
  `entry_type` (`:37`), and the floor purely by cosine (`:51`).

**Minimum schema change, as an observation not a proposal:** the brief expects
one column. Consistent with that, the smallest shape the current code implies is
a single nullable verdict column on the table whose rows are recalled —
`memory_entries` — and/or on `insights`, since those are the two row types that
reach a prompt without the user having confirmed them. Note that a verdict on
`insights` alone would not affect recall at all: insights are not in the recall
path. Any change that is meant to alter what the room says back has to reach
`memory_entries`, because that is the only table `recall()` and
`standing_memories()` read.

---

## 6. Analytics coverage

Two registries, both allow-listed by property name.

**Backend** — `apps/api/constants.py:65-149`, 16 events:
`signup_completed`, `user_signed_in`, `conversation_started`, `message_sent`,
`council_started`, `council_completed`, `council_saved`, `share_created`,
`letter_delivered`, `checkout_started`, `subscription_activated`,
`subscription_canceled`, `account_deleted`, `data_exported`, `usage_cap_hit`,
`safety_event_pre`.

**Frontend** — `apps/web/lib/analyticsEvents.ts`: `landing_view`,
`signup_started`, `first_reply_rendered`, `letter_action`, `paywall_viewed`,
`upgrade_clicked`.

### Paths that emit

| Path | Event |
|---|---|
| Chat send | `message_sent` (`conversation_service.py:1141`), `first_reply_rendered` (web) |
| Conversation create | `conversation_started` — carries `via` and `seeded_topic` |
| Council | `council_started`, `council_completed`, `council_saved` |
| Letter delivery | `letter_delivered`; reader taps → `letter_action` |
| Any cap refusal | `usage_cap_hit` with `cap_kind` + `path` |
| Paywall surfaces | `paywall_viewed`, `upgrade_clicked` |
| Share | `share_created` |

### Paths that emit nothing

- **Counterview** — generation, rebuttal, save. No event of its own; it appears
  in analytics only as `usage_cap_hit {path: "counterview"}` on refusal.
- **Mirror** — generation, ring-true submission, save. `ring_true` is stored and
  neither read nor reported.
- **You-vs-you** — generation, ring-true, save.
- **Self-portrait** — answering, re-answering, the "Take it to {name}" door.
- **Future-self** — schedule, prediction, delivery, review.
- **Insights** — no event on surfacing, on any of the four doors, or on dismiss.
- **Deep mode** — no toggle event.
- **Memory** — no event on extraction, insight promotion, or recall.
- **Reflections feed** — no view or item-tap event.

**The gap in one line:** every event that exists measures acquisition, spend or
refusal. **No event measures whether a loop closed** — whether an insight door
was walked through, whether a verdict rang true, whether a person returned to a
thread. Both P2 items are about loop closure, and there is currently no
instrumentation that would show one closing.

---

## Appendix — the five `distill_user_text_to_memory_task` sources

One task, five call sites, all producing `stated` / confidence 1.0 / Lane A
rows with `conversation_id = None` (`arq_worker.py:~640-700`):

| Source tag | Call site | Condition |
|---|---|---|
| `council_edit` | `services/council_service.py:421` | source is chat **and** matter was edited |
| `counterview_rebuttal` | `services/counterview_service.py:662` | a new rebuttal was generated |
| `mirror_ring_true` | `routers/mirrors.py:149` | non-empty note — **unreachable, §3** |
| `letter_write_back` | `routers/weekly_letters.py:156` | non-empty write-back |
| `future_self_note` | `routers/scheduled_emails.py:101` | non-empty note |

Four of the five are live. The fifth has no input.
