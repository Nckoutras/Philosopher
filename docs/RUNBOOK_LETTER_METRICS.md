# Runbook — the Sunday letter's return gate (Blueprint §16)

The gate: **≥20% of delivered letters cause an authenticated return within 72h.**

This file holds the two queries that answer it, and the difference between them.
Both run against production Postgres — no PostHog required. That is deliberate:
PostHog's browser SDK does not load before a user accepts the analytics cookie
([`lib/analytics.ts`](../apps/web/lib/analytics.ts)), and a delivery gate that
only counts consenting readers is not a delivery measurement.

---

## The two forms, and why there are two

Everything lives on one row of `weekly_letters`:

| Column | Written by | Means |
| --- | --- | --- |
| `email_sent_at` | [`arq_worker.py`](../apps/api/workers/arq_worker.py), after the send commits | an email left the building |
| `read_at` | `GET /weekly-letters/{id}`, first authenticated fetch | someone opened this letter, **from any door** |
| `email_opened_at` | the same endpoint, when the request carries `?src=email` | someone opened it **from the email**, the first time |

`read_at` predates the gate and answers a weaker question than §16 asks. The
Home card and the letters list write it exactly as an email click does, so
**Form A over-counts**: it cannot tell a letter that pulled someone back from a
letter someone happened to find while already in the app. Form B is the gate as
written.

Run both. The spread between them is itself the interesting number — it is the
size of the in-app discovery path, which no other metric reports.

### Form A — returned within 72h (any door)

```sql
SELECT
  count(*)                                                                  AS delivered,
  count(*) FILTER (WHERE read_at IS NOT NULL
                     AND read_at <= email_sent_at + interval '72 hours')    AS returned_72h,
  round(100.0 * count(*) FILTER (WHERE read_at IS NOT NULL
                     AND read_at <= email_sent_at + interval '72 hours')
        / nullif(count(*), 0), 1)                                           AS pct
FROM weekly_letters
WHERE kind = 'weekly'
  AND email_sent_at IS NOT NULL;
```

### Form B — email-caused return within 72h (the §16 gate)

```sql
SELECT
  count(*)                                                                  AS delivered,
  count(*) FILTER (WHERE email_opened_at IS NOT NULL
                     AND email_opened_at <= email_sent_at + interval '72 hours') AS email_returns_72h,
  round(100.0 * count(*) FILTER (WHERE email_opened_at IS NOT NULL
                     AND email_opened_at <= email_sent_at + interval '72 hours')
        / nullif(count(*), 0), 1)                                           AS pct
FROM weekly_letters
WHERE kind = 'weekly'
  AND email_sent_at IS NOT NULL
  AND email_sent_at >= '2026-09-20';   -- see "When Form B becomes valid"
```

### Per-week, either form

```sql
SELECT
  to_char(period_start, 'IYYY-"W"IW')                                       AS week,
  count(*)                                                                  AS delivered,
  count(*) FILTER (WHERE email_opened_at <= email_sent_at + interval '72 hours') AS email_returns,
  count(*) FILTER (WHERE read_at        <= email_sent_at + interval '72 hours') AS any_door_returns
FROM weekly_letters
WHERE kind = 'weekly' AND email_sent_at IS NOT NULL
GROUP BY 1 ORDER BY 1 DESC;
```

`to_char(..., 'IYYY-"W"IW')` produces the same bucket the `letter_delivered` and
`letter_open_to_app` events send as `week` (`strftime('%G-W%V')`), so a PostHog
funnel and this query group identically.

---

## When Form B becomes valid

`email_opened_at` starts existing at migration `062_letter_email_opened`, and
starts being *written* only for letters whose email carried `?src=email` — i.e.
**letters delivered after Γ-1 reaches production.** Every row older than that has
`email_opened_at IS NULL` because nothing could have written it, not because
nobody returned.

**So Form B must be date-floored to the first delivery after the Γ-1 deploy, or
it reports a false 0%.** The floor in the query above is the first Sunday send
after the merge; correct it to the actual deploy date if it slipped.

---

## Two known under-counts in Form B

Both push the number **down**, never up. Form B is a floor on email-caused
returns, which is the safe direction for a gate you must clear — but it means a
narrow miss is not a clear fail.

1. ~~**Signed-out clickers are lost entirely.**~~ **CLOSED by #654 (2026-09-14),
   corrected here 2026-09-15.** This entry said "there is no `returnTo`
   mechanism"; there is one, and preserving `?src=email` across the sign-in round
   trip is the assertion that feature exists for
   (`apps/web/app/auth/__tests__/returnTo.test.tsx`). A signed-out click now
   lands back on the letter with its marker intact and IS attributed.

   **Two consequences for reading this gate.** Form B undercounts every delivery
   before the #654 deploy and stops undercounting after it, so a rate computed
   across that boundary mixes two different instruments — split the window or
   floor it at the deploy. And this was described as "the single largest known
   gap in the measurement", which means the pre-#654 numbers are a floor that was
   lower than anyone reading them assumed.

   *Left struck through rather than deleted: a runbook that quietly edits away a
   known gap gives a reader no way to tell which claim their old number was
   computed under.*
2. **Non-Pro readers cannot be counted.** The endpoint is Pro-gated and answers
   403 before reaching the stamp, so a lapsed subscriber clicking their letter
   is invisible here. **Still open** (re-checked 2026-09-15).

Item 2 does not affect Form A's `read_at` any differently — both forms lose those
people. The difference is only that Form B is the one being read as a gate.

---

## Cross-check against PostHog

`letter_delivered {week, host}` and `letter_open_to_app {week, host}` are the
event twins of `email_sent_at` and `email_opened_at`, and join on `week` + `host`.
Use them for the funnel view; use the SQL above for the gate itself.

**If the PostHog numerator is zero while the SQL is not**, check
`POSTHOG_API_KEY` on the **worker** Render service, not just the API service —
they are separate processes and `letter_delivered` fires only from the worker.
An unset key there makes `analytics_service.track` a `logger.debug` and the
delivery half of the funnel disappears in silence.
