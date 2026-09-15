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
