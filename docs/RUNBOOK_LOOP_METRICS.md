# Runbook — the launch gates and the loops that feed them (Blueprint §16)

Every Blueprint §16 gate, and for each: the query or the PostHog insight that
answers it, its green/red thresholds, and whether it is computable **today**.

`RUNBOOK_LETTER_METRICS.md` is the Weekly Letter gate's own detail and is not
duplicated here — this file states the gate and links there.

**Written 2026-09-15 (Γ-5).** Every "computable" claim below was checked against
the code on that date. A claim in a runbook is a claim about the past unless it
was re-verified; re-check before trusting one, and mark what you did not check.

---

## 0. SQL is authoritative. PostHog is the cross-check.

**Where a gate has a SQL form, the SQL number is the one that counts.** This is
not a preference about tooling; the two instruments measure different
populations.

PostHog's browser SDK does not initialize, set a cookie, or send a byte until the
user presses Accept (`apps/web/lib/analytics.ts`). So every **web** event is
consent-gated, and a gate computed from one is really measuring *consent × the
thing*. Server-side events do not have that problem — the API has the user's id
whatever the banner says — but they are still absent for anyone who used the
product before the event shipped, where SQL can look backwards over rows that
already exist.

| Fires from | Events | Consent-gated |
| --- | --- | --- |
| **Browser** (`apps/web/lib/analyticsEvents.ts`) | `$pageview`, `landing_view`, `signup_started`, `first_reply_rendered`, `letter_action`, `paywall_viewed`, `upgrade_clicked` | **Yes — all of them** |
| **Server** (`apps/api/constants.py`) | the other 20, including all three letter events, `conversation_resumed`, `message_sent`, `memory_feedback`, every billing event | No |

One consequence worth stating once, because it looks like a bug in a dashboard:
**`letter_action` (discuss / ritual / share) is consent-gated while
`letter_delivered`, `letter_open_to_app` and `letter_write_back` are not.** Those
four will never reconcile. That is correct behaviour, not drift.

---

## 1. The gates

Thresholds are Blueprint §16, verbatim.

| Gate | Green | Red | Status |
| --- | --- | --- | --- |
| **Activation** | ≥35% cold signups hit 3 conv / 2 threads / 72h | <15% after 2 onboarding iterations | ✅ **SQL, §2 below** |
| **Paid renewal** | ≥70% month-2 renewal on n≥75 monthly subs | <55% | ⏸ **post-Stripe — unverified** |
| **Memory trust** | <2% wrong/outdated feedback per surfaced memory reference on n≥500 | >5%, or recurring identity/date conflation | ⚠️ **newly computable, §3** |
| **Weekly Letter** | ≥20% delivered letters → authenticated return in 72h | <8% after testing | ✅ **SQL — `RUNBOOK_LETTER_METRICS.md`** |
| **Organic share** | ≥3% share landing → signup **and** ≥20% activated users share | <1% signup after 1,000 external visitors | 🚫 **blocked — no share attribution** |
| **Unit cost** | paid-user variable AI ≤30% net sub revenue, no heavy-user tail | >40% median, or a loss-making segment | ⏸ **post-Stripe — unverified** |
| **Safety / privacy** | deletion + export automated; multilingual safety tested; no silent retention failures | any deletion gap, or unsafe routing | ◐ **qualitative, §5** |

### Why the four non-green ones are not green

- **Paid renewal / Unit cost** — both need live Stripe subscriptions, and the
  revenue path is blocked outside this repository (`HANDOFF_BRIEF_v30` §6: the
  upgrade page says €99.99, the founder observed €149 charged, live mode is not
  open). Neither is a measurement gap; there is nothing to measure yet. **Not
  re-verified this rotation** — carried from that document.
- **Organic share** — `share_created {artifact_type}` records that a share
  artefact was MADE. Nothing records that a share was *landed on*: there is no
  share token, no attributed inbound URL, and `signup_started {source, device}`
  carries no share provenance. Both halves of this gate are therefore
  uncomputable, and closing it is an attribution feature (P3), not an analytics
  change. **Recorded as blocked, deliberately not worked around** — a proxy
  number here would be worse than an absent one.
- **Memory trust** — see §3. It became computable *across all three surfaces*
  only with Γ-5, and `n≥500` is far away: production held 22 users and 26 weekly
  letters on 2026-09-14.

---

## 2. Activation — the query

**One interpretive choice, stated because it is a choice.** §16 says "3
conversations / 2 threads". This runbook reads that as: **three conversations
the person actually spoke in, of which at least two became real exchanges
(≥2 user messages).** A conversation with a single message is a door opened; a
thread is a door walked through, and the gate plainly distinguishes them. If
that is not what §16 meant, change the two constants in the CTE — nothing else
in the query depends on the reading.

Counted from `messages.role = 'user'` rather than `conversations.message_count`:
that column increments by **two** per exchange (user + assistant) and the
opening invocation is written into it as well, so "≥2 user messages" is not
`message_count >= 4` in every case. Counting the rows removes the arithmetic.

```sql
-- Activation: cold signups reaching 3 conversations / 2 threads within 72h.
WITH bounds AS (
  SELECT 3 AS min_conversations, 2 AS min_threads, interval '72 hours' AS window
),
cohort AS (                     -- cold signups only: exclude admins and staff
  SELECT u.id, u.created_at
  FROM users u
  WHERE u.is_admin = false
    AND u.created_at >= :cohort_start      -- psql: '2026-09-01'. From a DRIVER,
                                           -- bind a tz-aware datetime — see below
    AND u.created_at <  now() - interval '72 hours'   -- must have had the full window
),
acts AS (
  SELECT c.user_id,
         c.id AS conversation_id,
         count(*) FILTER (WHERE m.role = 'user') AS user_messages
  FROM conversations c
  JOIN cohort co ON co.id = c.user_id
  JOIN messages m ON m.conversation_id = c.id
  CROSS JOIN bounds b
  WHERE c.deleted_at IS NULL
    AND m.created_at <= co.created_at + b.window
  GROUP BY c.user_id, c.id
  HAVING count(*) FILTER (WHERE m.role = 'user') >= 1
),
per_user AS (
  SELECT co.id AS user_id,
         count(a.conversation_id)                                    AS conversations,
         count(a.conversation_id) FILTER (WHERE a.user_messages >= 2) AS threads
  FROM cohort co
  LEFT JOIN acts a ON a.user_id = co.id
  GROUP BY co.id
)
SELECT
  count(*)                                                       AS cohort_size,
  count(*) FILTER (WHERE conversations >= (SELECT min_conversations FROM bounds)
                     AND threads       >= (SELECT min_threads FROM bounds)) AS activated,
  round(100.0 * count(*) FILTER (WHERE conversations >= (SELECT min_conversations FROM bounds)
                                   AND threads       >= (SELECT min_threads FROM bounds))
        / nullif(count(*), 0), 1)                                AS pct
FROM per_user;
```

**Three things this query is careful about, each of which would silently inflate
or deflate the number:**

1. **`created_at < now() - 72h`** — a user who signed up an hour ago has not
   failed the gate, they have not finished it. Without this line every recent
   signup counts as a miss and the percentage falls as the product grows.
2. **`m.created_at <= co.created_at + window`**, not `c.created_at` — the window
   is on the ACTIVITY, not on when the conversation row was made. A thread
   created inside the window and spoken in a week later is not activation.
3. **`c.deleted_at IS NULL`** — a soft-deleted conversation was still an act, but
   the Library treats it as gone; counting it would report activation the person
   cannot see. Deliberately excluded; flip it if you disagree, but say which you
   ran.

**Binding `:cohort_start` from code, not from psql (TD-76).** Pasted into psql,
`'2026-09-01'` is a literal and Postgres casts it. Bound through a driver it is a
**parameter**, and asyncpg refuses a `str` for a `timestamptz` with
*"expected datetime.date or datetime.datetime instance, got 'str'"* — it does not
coerce. Pass a **tz-aware** `datetime`: a naive one is read in the server's
timezone, which silently shifts the cohort floor by the server's offset and moves
the gate. This is the third time this exact trap has cost a red run in this
repository; see the CLAUDE.md failure log.

**This is a query and not an event, on purpose.** Activation is a *state*
derivable from rows that already exist, so this answers for the 22 users who
predate any instrumentation — which an event could never do retroactively.

---

## 3. Memory trust — what Γ-5 changed

The gate is "<2% wrong/outdated feedback per surfaced memory reference". The
verdict vocabulary is `yes | partly | no` on three surfaces, and `no` is the
gate's numerator.

**Until Γ-5, only one of the three surfaces was counted.** Ring-true is "one
speech act, one contract, three surfaces" (`models.Insight`) — insights, mirrors,
you-vs-you — and `memory_feedback` fired from the insights router alone. Mirror
and self-comparison verdicts were written to their own `ring_true` columns and
reached no dashboard. The recognition rate anyone read before 2026-09-15 was
drawn from roughly a third of the verdicts the product collects.

Γ-5 adds `surface` to the event and fires it from all three. **The event is the
cross-check; the SQL below is the gate**, and the SQL also covers every verdict
given before the events existed.

```sql
-- Memory trust: the 'no' rate per surface, and overall.
SELECT COALESCE(v.surface, 'ALL SURFACES')            AS surface,
       count(*)                                       AS verdicts,
       count(*) FILTER (WHERE v.ring_true = 'no')     AS wrong,
       round(100.0 * count(*) FILTER (WHERE v.ring_true = 'no')
             / nullif(count(*), 0), 1)                AS pct_wrong
FROM (
  SELECT 'insight'         AS surface, ring_true FROM insights          WHERE ring_true IS NOT NULL
  UNION ALL
  SELECT 'mirror',              ring_true FROM mirrors                  WHERE ring_true IS NOT NULL
  UNION ALL
  SELECT 'self_comparison',     ring_true FROM self_comparisons         WHERE ring_true IS NOT NULL
) v
GROUP BY ROLLUP (v.surface)
ORDER BY GROUPING(v.surface), v.surface;
```

**Two deliberate choices in that last block, because both look like oversights.**

`COALESCE(..., 'ALL SURFACES')` labels the ROLLUP grand-total row, which
Postgres otherwise returns with `surface = NULL`. A real surface value can never
be NULL — all three union branches are literals — so the label is unambiguous.
`ORDER BY GROUPING(v.surface)` puts that row last by what it *means* rather than
by where NULLs happen to sort.

**`pct_wrong` is deliberately left NULL when there are no verdicts, and must not
be coalesced to 0.** "Nobody has answered yet" and "people answered and none were
wrong" are opposite facts, and 0 would report a passing gate on an empty table.
This is the same `nullif` distinction the activation query makes, for the same
reason. Against an empty database this query returns exactly one row —
`('ALL SURFACES', 0, 0, NULL)` — and that is the query working, not a bug.

**The denominator is not what the gate asks for, and the difference matters.**
§16 says "per surfaced memory reference". This counts per *answered* card. There
is no record of a card being surfaced and ignored: "seen" exists only as
`wr_roomnoticed_seen` in the browser's `localStorage`
(`apps/web/components/today/RoomNoticedCard.tsx`) — per-device, never sent to the
server. So this query measures "of the people who answered, how many said no",
which is a **stricter** reading than the gate: someone who ignored a wrong card
is invisible.

An impression event would close that gap and was **rejected** (Γ-5 ruling): the
denominator it would buy is not worth a new event firing on every render, and
`insights.created_at` + `is_dismissed` already bound the "created but not
answered" population from SQL. Revisit only if §16 is read strictly enough to
need the true denominator.

**`n≥500` is far away.** 22 users on 2026-09-14. Read the per-surface counts, not
the percentage, until the counts are real.

---

## 4. The four loops, and the dashboard

Nine PostHog insights. **Names and feeding events only — not built in this PR.**
PostHog's UI is not code-reviewable, so the definitions live here and the boards
are assembled by hand from them.

| Insight | Type | Events |
| --- | --- | --- |
| `funnel_signup_to_first_reply` | Funnel | `landing_view` → `signup_started` → `signup_completed` → `conversation_started` → `first_reply_rendered` |
| `funnel_letter_loop` | Funnel | `letter_delivered` → `letter_open_to_app` → `letter_write_back` |
| `letter_loop_by_host` | Breakdown | the same three, by `host` |
| `funnel_resume_loop` | Funnel | `conversation_resumed` → `message_sent` |
| `resume_by_gap` | Breakdown | `conversation_resumed` by `gap_bucket` |
| `recognition_verdicts` | Breakdown | `memory_feedback` by `verdict`, then by `surface` |
| `funnel_council_loop` | Funnel | `council_started` → `council_completed` → `council_saved` |
| `funnel_paywall_to_paid` | Funnel | `paywall_viewed` → `upgrade_clicked` → `checkout_started` → `subscription_activated` |
| `caps_hit_by_kind` | Trend | `usage_cap_hit` by `cap_kind`, `tier` |

### Closure state of each shipped loop

| Loop | Opens | Closes | Complete |
| --- | --- | --- | --- |
| **Letter** | `letter_delivered` | `letter_open_to_app` → `letter_write_back` | ✅ since Γ-5 |
| **Open-thread** | `conversation_resumed` | `message_sent`, joined on `conversation_id` | ✅ since Γ-5 |
| **Recognition** | card render *(not recorded, by decision)* | `memory_feedback {surface}` | ◐ closure yes, denominator no |
| **Council** | `council_started` | `council_completed` → `council_saved` | ✅ |

**`funnel_resume_loop` needs the `conversation_id` join, and a person-level
funnel alone is not good enough.** `conversation_resumed` carried no
`conversation_id` before Γ-5, so the only reading available was "this person
resumed, then this person sent a message" — which scores *resumed thread A, then
messaged thread B* as a closure. That false positive is invisible and it flatters
the loop. Both events now carry the id; match on it.

`council_saved` carries no properties, so the council funnel's last step cannot
be broken down by `source`. Person-level funnels still work. Left as-is (Γ-5
ruling).

---

## 5. Safety / privacy — qualitative, with the pins that exist

No percentage. The gate is "deletion and export automated, multilingual safety
tested, no silent retention failures", and what can be pointed at is:

- **Rights, pinned to code:** `apps/api/tests/test_privacy_policy_claims.py` —
  15 tests, one per Art. right at policy §7 (access, rectification, erasure,
  portability). Closes TD-59.
- **Export completeness:** `apps/api/tests/test_data_export.py` — the TD-62
  guard asserts every user-scoped mapped class is either exported or documented
  as excluded, so a new table fails CI until someone rules on it. Note its stated
  blind spot: it keys on `user_id`, so a table holding user data with no
  `user_id` column is invisible to it.
- **Deletion:** `tests/routers/test_account_deletion_endpoint.py`, plus the
  cascade tests in `tests/db_live/test_memory_recall_and_cascades.py` which run
  against real Postgres because `ON DELETE` clauses live in the migrations and
  not in the models.
- **Backups:** `.github/workflows/db-backup.yml` and `docs/RUNBOOK_RESTORE.md`.
  A backup nobody has restored is a hypothesis — the restore drill is the
  evidence, not the workflow being green.
- **Analytics never carries content:** `tests/test_analytics_call_sites.py` walks
  the AST of every `track()` call and rejects f-strings, concatenations,
  `.format()`, slices and long string literals as property values. It is a smoke
  alarm, not a lock, and it is the reason a leak into a dashboard has to be
  deliberate rather than accidental.

**Multilingual safety testing is the part with no pin here.** Say so rather than
implying the list above covers it.

---

## 6. What is NOT measurable, listed so it stays visible

1. **Share attribution** — blocks the Organic share gate entirely. P3.
2. **Card impressions** — the recognition gate's true denominator. Rejected by
   ruling, §3.
3. **Signed-out letter clicks** — closed by #654 (`returnTo`), see
   `RUNBOOK_LETTER_METRICS.md`.
4. **Non-Pro letter opens** — the letter endpoint is Pro-gated and answers 403
   before stamping, so a lapsed subscriber clicking their own letter is
   invisible. Still open.
5. **Consent-declining users' web events** — structural, and the reason §0 puts
   SQL first.
6. **Semantic sameness** — §7's metric is lexical because `messages` carries no
   embedding. The gap, and what closing it costs, is stated there.

---

## 7. Sameness — the D2 metric

**Added 2026-09-16 (D2).** The teardown's churn cause #2: *"answers converge
around turn 30-50"*. This section is the instrument and the pre-fix baseline.
Every future anti-sameness intervention is judged against the numbers below.

### 7a. The ruled metric is not computable, and this is why

D2 ruled for **cosine between a persona's own replies at turn gap N**. It cannot
be a SQL query today: **`messages` has no embedding column.** Only
`memory_entries` and `source_chunks` carry `Vector(1536)`, and pgvector cannot
help without a vector to compare. `pg_trgm` is not installed either (checked
2026-09-16: the database has `vector`, `pgcrypto`, `pg_stat_statements`,
`postgres_fdw`, `plpgsql`, `supabase_vault`, `uuid-ossp` — and nothing else).

**What closing it would cost**, so the decision is costed rather than deferred
vaguely: an `embedding` column on `messages`, a backfill of the 809 existing
assistant rows, and an embed on every reply thereafter. The embedding itself is
trivial — `text-embedding-3-small`, the whole existing corpus is ~97k tokens,
about **$0.002** — so the real cost is the migration, the write path, and the
storage, not the API. **Not proposed here.** §7b is what runs without it.

### 7b. Lexical recurrence, against a control

Word-set overlap (Jaccard) between a persona's own replies in the same
conversation, banded by turn gap.

**The absolute number is meaningless; the RATIO TO THE CONTROL is the metric.**
Two replies by the same persona always share vocabulary — that is the persona.
The control row measures exactly that floor: same voice, *different*
conversations. Within-conversation similarity above the control is topic
coherence, which is wanted. **Convergence would show as the wide-gap ratio RISING
toward, or past, the narrow-gap ratio** — the persona saying at turn 30 what it
said at turn 5.

```sql
-- Sameness A: lexical recurrence between a persona's own replies, by turn gap,
-- against a same-voice/other-conversation control. Read the RATIO, not the value.
WITH turns AS (
  SELECT m.id, m.conversation_id, COALESCE(m.persona_id, c.persona_id) AS voice, m.content,
         row_number() OVER (PARTITION BY m.conversation_id ORDER BY m.created_at, m.id) AS turn_no,
         count(*) OVER (PARTITION BY m.conversation_id) AS conv_turns
  FROM messages m
  JOIN conversations c ON c.id = m.conversation_id
  WHERE m.role = 'assistant'
    AND m.message_kind <> 'conclusion'   -- distilled rows are not persona turns
    AND m.persona_override = false       -- app-voice safety replies are not the persona
),
deep AS (SELECT * FROM turns WHERE conv_turns >= 10),
sets AS (
  SELECT d.id, d.conversation_id, d.voice, d.turn_no, array_agg(DISTINCT lower(w)) AS ws
  FROM deep d
  CROSS JOIN LATERAL regexp_split_to_table(d.content, '[^[:alpha:]]+') AS w
  WHERE length(w) >= 5                   -- crude content-word filter; see the caveat
  GROUP BY d.id, d.conversation_id, d.voice, d.turn_no
  HAVING count(DISTINCT lower(w)) >= 8
),
scored AS (
  SELECT 'same conversation' AS kind,
         CASE WHEN b.turn_no - a.turn_no <= 2  THEN 'gap 1-2'
              WHEN b.turn_no - a.turn_no <= 10 THEN 'gap 3-10'
              ELSE 'gap 11+' END AS band,
         CAST(cardinality(ARRAY(SELECT unnest(a.ws) INTERSECT SELECT unnest(b.ws))) AS numeric)
         / nullif(cardinality(ARRAY(SELECT unnest(a.ws) UNION SELECT unnest(b.ws))), 0) AS jac
  FROM sets a
  JOIN sets b ON b.conversation_id = a.conversation_id AND b.turn_no > a.turn_no
  UNION ALL
  SELECT 'CONTROL: same voice, other conversation', 'control',
         CAST(cardinality(ARRAY(SELECT unnest(a.ws) INTERSECT SELECT unnest(b.ws))) AS numeric)
         / nullif(cardinality(ARRAY(SELECT unnest(a.ws) UNION SELECT unnest(b.ws))), 0)
  FROM sets a
  JOIN sets b ON b.voice = a.voice AND b.conversation_id <> a.conversation_id AND b.id > a.id
)
SELECT kind, band, count(*) AS pairs,
       round(CAST(avg(jac) AS numeric), 4) AS mean_jaccard,
       round(CAST(percentile_cont(0.9) WITHIN GROUP (ORDER BY jac) AS numeric), 4) AS p90_jaccard
FROM scored
GROUP BY kind, band
ORDER BY kind, band;
```

**BASELINE — production, 2026-09-16, pre-fix.**

| kind | band | pairs | mean_jaccard | p90 | **ratio to control** |
| --- | --- | ---: | ---: | ---: | ---: |
| CONTROL: same voice, other conversation | control | 2,745 | 0.0096 | 0.0400 | 1.00x |
| same conversation | gap 1-2 | 332 | 0.0606 | 0.1250 | **6.3x** |
| same conversation | gap 3-10 | 861 | 0.0459 | 0.1053 | **4.8x** |
| same conversation | gap 11+ | 661 | 0.0429 | 0.1053 | **4.5x** |

**The ratio FALLS as the gap widens — 6.3x to 4.5x. That is the opposite of the
reported convergence**, and it is the number to beat. A future run where gap 11+
approaches or exceeds gap 1-2 is the signal D2 went looking for.

**Read this with its caveats, which are load-bearing:**

- **Underpowered by reply length.** Deep-thread replies average **31.7 words**,
  which is ~12 distinct words of length >= 5. Set overlap over ~12 items is
  coarse: the *median* pair scores exactly 0.0000 in every band, which is why the
  table reports the mean and p90 instead. Do not read a change under ~1x of
  control as signal.
- **`length(w) >= 5` is a crude stopword filter, not a good one**, and it is not
  language-aware. It admits "about", "there", "would"; for a Greek conversation it
  admits a different set again. The control absorbs most of this — that is its
  second job — but it is the reason §7b is a proxy and §7a is the real metric.
- **Lexical, not semantic, by necessity.** The same idea in different words scores
  0. This instrument cannot see a persona that restates a point in fresh
  vocabulary, which is precisely the failure mode the ADVANCEMENT block
  (`system_base.jinja2`) already forbids in those terms.

### 7c. Structural drift, and the shipped spec it is measured against

The companion instrument, and the discriminating one: HARD RULE 4 in
`apps/api/prompts/system_base.jinja2` specifies an ending mix of **~40% question
/ 40% none / 20% statement-then-question**. Drift toward every reply ending in a
question would be sameness of the most legible kind.

```sql
-- Sameness B: structural drift by turn depth, against HARD RULE 4's ~40% target.
WITH turns AS (
  SELECT m.conversation_id, m.content,
         row_number() OVER (PARTITION BY m.conversation_id ORDER BY m.created_at, m.id) AS turn_no,
         count(*) OVER (PARTITION BY m.conversation_id) AS conv_turns
  FROM messages m
  WHERE m.role = 'assistant'
    AND m.message_kind <> 'conclusion'
    AND m.persona_override = false
)
SELECT CASE WHEN turn_no <= 2  THEN 'turn 1-2'
            WHEN turn_no <= 5  THEN 'turn 3-5'
            WHEN turn_no <= 10 THEN 'turn 6-10'
            WHEN turn_no <= 20 THEN 'turn 11-20'
            ELSE 'turn 21+' END AS band,
       count(*) AS replies,
       round(100.0 * count(*) FILTER (WHERE rtrim(content) LIKE '%?') / count(*), 1) AS pct_end_question,
       round(avg(array_length(regexp_split_to_array(btrim(content), '\s+'), 1)), 1) AS mean_words,
       round(CAST(stddev_pop(array_length(regexp_split_to_array(btrim(content), '\s+'), 1)) AS numeric), 1) AS sd_words
FROM turns
WHERE conv_turns >= 10
GROUP BY 1
ORDER BY min(turn_no);
```

**BASELINE — production, 2026-09-16, pre-fix.**

| band | replies | pct_end_question | mean_words | sd_words |
| --- | ---: | ---: | ---: | ---: |
| turn 1-2 | 40 | 50.0 | 37.7 | 28.5 |
| turn 3-5 | 60 | 31.7 | 38.5 | 29.4 |
| turn 6-10 | 100 | 31.0 | 38.9 | 34.6 |
| turn 11-20 | 110 | 26.4 | 35.0 | 30.2 |
| turn 21+ | 63 | **12.7** | 32.4 | 23.2 |

Question-endings **decline** with depth rather than saturating, and length holds
roughly flat with no collapse in variance. Against HARD RULE 4's ~40% target the
deep end is **under**-questioning, not interrogating. If anything here is a
finding it is that one, and it is not the reported one.

### 7d. The population problem, which outranks both instruments

Counted under the SAME filters the two queries use — excluding `conclusion` rows
and app-voice (`persona_override`) replies. That distinction is not cosmetic:
unfiltered there are 809 assistant rows across 180 conversations, and quoting
those here would overstate every figure below, including the one this section
turns on.

| | value |
| --- | ---: |
| conversations with a persona reply | 178 |
| persona replies (excl. conclusions and app-voice) | 772 |
| median persona turns per conversation | **2** |
| mean | 4.3 |
| deepest conversation | 47 |
| conversations with >= 10 turns | 20 |
| conversations with >= 20 turns | 6 |
| **conversations with >= 30 turns** | **2** |

**The teardown locates convergence at "turn 30-50". Two conversations in
production have ever reached turn 30** — three, if `conclusion` and app-voice
rows are counted as turns, which the metric deliberately does not. The
`turn 21+` row in §7c is 63 replies drawn from a handful of threads, and those
threads are overwhelmingly likely to be the founder's own.

So the honest reading of both baselines is **not** "sameness is disproved". It is
**"production does not yet contain enough depth to test the claim"**, and the
numbers above are the floor a real cohort will be compared against. Re-run both
when conversations with >= 30 turns reaches roughly **n >= 30** — ten times the
current population, and the first point at which a decile of deep threads is
something other than one person's week.

Until then §7 pairs with `PROTOCOL_FOUNDER_READ_SAMENESS.md`, which reads the few
deep conversations that do exist. Neither replaces the other: the protocol
can see restatement-in-new-words that §7b structurally cannot, and §7 can see a
population the protocol never will.

---

## 8. Unit cost — the depth risk, with the arithmetic

The §1 Unit-cost gate is blocked post-Stripe. **This is a different thing: a
named risk in the same gate, recorded now because D2 measured the inputs.**

History is **unbounded for Pro** — a growing window capped only by
`HISTORY_TOKEN_BUDGET_PRO = 24_000` (`services/conversation_service.py`). Every
reply re-sends the whole conversation, so input cost per reply grows linearly
with depth while the subscription price does not.

**The arithmetic, from measured production message sizes** (deep threads, >= 20
messages, 2026-09-16: assistant **31.7** words mean, user **11.4**; ~1.35
tokens/word):

| | tokens |
| --- | ---: |
| static per-persona prompt prefix (mean over 11 personas, measured) | 2,331 |
| variable block (8 memory rows + <= 4 passages + profile) | ~1,272 |
| per turn added to history (1 user + 1 reply) | ~58 |
| **total prompt at turn 40** | **~5,900** |
| total prompt at turn 100 | ~9,400 |
| history budget (24,000) reached at | **~turn 410** |

**A correction, recorded because the ruling rested on it.** D2's ruling states
turn 40 costs *"~30k input tokens per reply"*. Measured, it is **~5.9k** — about
**5x lower**. 30k is roughly what a turn costs once the 24k history budget is
saturated, which these message sizes do not reach until ~turn 410, and which no
production conversation has ever approached (deepest: 48 turns).

**Why the usage columns cannot settle this yet, and must not be quoted as if they
can.** `messages.input_tokens` / `cache_read_tokens` / `cache_creation_tokens`
arrived with migration 054, so almost every row predates them: of 772 assistant
replies, **55** carry usage at all, **1** in the turn 11-20 band and **0** beyond
turn 20. The table above is therefore computed from message SIZES, not from
billed usage. Recompute it from the usage columns once they cover a deep thread;
that is the authoritative version and it does not exist yet.

**No cap is proposed.** A history cap changes what the product *is* — the growing
window is also what makes the prefix cacheable (`_history_cache_control`), so a
cap trades a cost problem for a cache problem. Revisit with beta evidence.

## 9. Council v2 — the trigger that reopens verdict memory

**Status: CLOSED-with-trigger (founder ruling 2026-09-24).** Council does not
remember its own prior verdicts. That was deferred to post-beta on 2026-09-15;
this section is what reopens it.

**The trigger: `users_with_more_than_one_non_admin >= 10`.** Verdict memory is
revisited when ten non-admin users have each run more than one council. **Staff
traffic is not signal**, so the threshold reads the non-admin column; the
all-accounts column stays alongside it so the difference is visible, not hidden.

At the ruling, 2026-09-24: **7 users, 3 with more than one council — of whom 2 are
admin accounts (21 and 25 councils) and 1 is not (6)**. So the trigger read **1**.
**56 cases, 0 reused**: `CouncilCase.session_count` / `CouncilSession.session_number`
are multi-session scaffolding no code path has exercised — every council opens a new
case at session 1. The query was run against production that day and returned
exactly those numbers.

If verdict memory is built, **the synthesis step is the only admissible injection
point** (HANDOFF_BRIEF_v30): the four member calls take `memories=[]` by design, and
per-user text in their prompts would forfeit the prompt cache across all four
Sonnet calls.

```sql
-- Council v2 trigger — verdict memory is revisited when
-- users_with_more_than_one_non_admin >= 10 (founder ruling 2026-09-24).
SELECT
  count(*)                                             AS users,
  count(*) FILTER (WHERE cases > 1)                    AS users_with_more_than_one,
  count(*) FILTER (WHERE cases > 1 AND NOT is_admin)   AS users_with_more_than_one_non_admin,
  coalesce(sum(cases), 0)                              AS cases,
  coalesce(sum(reused), 0)                             AS cases_reused
FROM (
  SELECT c.user_id,
         count(*)                                      AS cases,
         count(*) FILTER (WHERE c.session_count > 1)   AS reused,
         bool_or(u.is_admin)                           AS is_admin
  FROM council_cases c
  JOIN users u ON u.id = c.user_id
  GROUP BY c.user_id
) per_user;
```

One row always, including over an empty table: the outer aggregate has no
`GROUP BY`, so "nobody yet" is a row of zeroes, not an absent row.
