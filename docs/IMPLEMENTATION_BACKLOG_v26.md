# GREAT MINDS — Implementation Backlog v26

> **Range covered:** `#549` … `#563`. **Verification SHA:** `ef3e2d89`. **Date:** 2026-08-23.
>
> This rotation's own PR number is not asserted. See `PROJECT_STATE_v26.md` for the
> verified-state table and the methods behind every number quoted here.

---

## ⚠️ PROVENANCE

Every item is VERIFIED THIS ROTATION with its method, or MARKED UNVERIFIED / UNCARRIED.
**No database was consulted** — the Supabase MCP connector disconnected mid-session. Items
needing live data are marked, not softened.

---

## 1. Closed this cycle — with the evidence

| Item | Closed by | Verification |
|---|---|---|
| **TD-45** — 29 red harnesses | #560, #562 | `pytest` executed: **578 passed, 0 failed**; baseline file **0 entries** |
| **TD-51** — RTL auto-cleanup never registers | #551 | `vitest` executed: **13 failed**, matching v25's measured 62 → 13 prediction |
| **A18c** — ring-true notes never safety-checked | #557 | `grep -c safety`: `mirrors.py` 1 → **14**, `self_comparison.py` 0 → **10**. v25 required both surfaces; both were done |
| **npm ci** | #559 | `web-build.yml` runs `npm ci --no-audit --no-fund` |
| **OPS-005** | (already closed by 052, recorded in v25) | carried, not re-verified — see UNCARRIED |

### TD-50 — backend CI: mechanism CLOSED, operation ⚠️ UNVERIFIED

**Verified present:** `.github/workflows/` holds **2** files; `.github/scripts/` holds
**2**. The pytest job compares by test id against a committed baseline, and there is a
single-head check plus a C-04 checker.

**Not verified:** that any of it is green on `main`. #558 pinned CI to Python **3.12** to
match `apps/api/Dockerfile`, while the baseline was captured on the only interpreter
available locally, **3.10.4**. Decision B of that PR set a checkpoint — read the first
Actions run, prune anything that passes on 3.12, and report individually anything that
fails there and not on 3.10. **That checkpoint has never been read, across seven merges.**

This matters more now than when it was set. The baseline is at zero, so a 3.10 ↔ 3.12
divergence leaves `main` red with nothing absorbing it. Queue item 1.

---

## 2. Open — P0 (launch blockers)

Carried from v25. **None of these moved this cycle** and none was re-verified against live
systems, because no live system was reachable. Treat the detail as v25's, not as re-checked.

- 🔴 **OPS-006** — Stripe price objects still hold the old amounts; display and charge
  disagree. ⚠️ **not re-verified** (needs Stripe access).
- 🔴 **TD-28 operational remainder** — live keys, live price IDs, live-mode webhook,
  **`ENV=production`** (see CORR-17 — the setting is `ENV`, not `ENVIRONMENT`),
  `API_BASE_URL`.
- 🔴 **OPS-002 / OPS-003** — the stale subscription rows; decide before the key switch so
  post-switch logs are readable. ⚠️ **not re-verified** (needs DB).
- 🟢 **Pricing — LOCKED 2026-08-06.** €11.99/mo · €99.99/yr, single Pro tier. Carried
  unchanged; the willingness-to-pay validation was deliberately never run — a named,
  accepted risk.

---

## 3. Open — P1

### TD-44 — `cache_read > 0` never confirmed in production ⚠️ UNVERIFIED

Carried. **Now answerable**, which is new: migration `054_token_components` stores the
buckets separately, so once messages accumulate post-deploy this is a query rather than a
log hunt.

```sql
SELECT count(*)                          AS n,
       round(avg(input_tokens))          AS avg_input,
       round(avg(cache_creation_tokens)) AS avg_cache_write,
       round(avg(cache_read_tokens))     AS avg_cache_read,
       round(avg(tokens_used - (input_tokens + cache_creation_tokens
                                + cache_read_tokens))) AS avg_output
FROM messages
WHERE input_tokens IS NOT NULL;
```

Expect `cache_read_tokens = 0` on free-tier rows: `_history_cache_control` withholds the
breakpoint below Pro, deliberately, because Haiku's 4,096-token cache minimum sits at the
size of a free-tier prompt. That is correct behaviour, and it is now visible as a `0`
rather than hidden inside a sum.

### TD-46 / TD-47 — the enforcement decisions, still unmade

- **TD-47** ⚠️ **re-verified this rotation:** `apps/web/next.config.js` still sets
  `ignoreBuildErrors: true` (`:5`) and `ignoreDuringBuilds: true` (`:8`), so
  `npm run build` validates nothing. Method: direct read.
- **TD-46** — whether vitest failures should block. The measurement exists; the decision
  does not. Pairs with TD-52 below, which is 1 of the 13.

### TD-52 — FilterPills toast spy (NEW number, pre-existing failure)

One of the 13 frontend failures. **Sourced this rotation**, contrary to the session note
that recorded it as untriaged:

`components/reflections/__tests__/FilterPills.test.tsx:65`
```
expect(toast).toHaveBeenCalledWith('Coming soon', expect.any(Object))
→ expected "spy" to be called with arguments: [ 'Coming soon', Any<Object> ]
```

The spy was not called with that two-argument signature. **Root cause untriaged:** it is
either the component no longer calling `toast` with a second argument, or the mock not
being wired to the module the component imports. Both are one read away; neither was done
this rotation. `QuickActionsRow > Ask harder shows Coming soon toast` fails identically
and is probably the same cause.

### TD-53 — the backend suite makes real network calls (NEW number)

Found during #558's investigation. **Re-verified today, and the number has moved** — see
CORR-18.

`embedding_client.embed()` is called unpatched at `conversation_service.py:643`, `:1173`
and `:1435` (**3** sites, `grep -n`). A full suite run produces **4** genuine
`401 Incorrect API key provided` responses from `api.openai.com` (`pytest --log-cli-level=WARNING`,
counted). The calls are wrapped in `try/except` that logs and continues, so nothing fails —
but the suite depends on those requests failing *fast*.

Not a correctness risk. It is a CI-reliability one: if OpenAI hangs rather than refusing,
the job stalls. Patch the three call sites in the affected tests.

### TD-54 — `next@14.2.15` carries a known advisory (P1)

npm prints it on every install, now on every CI run too. Its own PR, before the live-key
switch. Not touched this cycle by decision.

### TD-55 — `generate_conversation_title` is enqueued on every turn

**Verified:** `conversation_service.py:1083` reads `new_message_count >= 2`, and the ARQ
task has no existing-title guard — it checks only that messages exist, then calls Haiku.
So an untitled conversation enqueues a title job on turn 2 and on every turn after, until
the first result lands and writes a title.

Deliberate since #240 ("title from first exchange"); the redundancy is the side effect, not
the intent. Small, bounded by a race window — but it is redundant spend of exactly the kind
`tokens_used` now exists to measure, and it is invisible in that column because
`complete()` calls are not logged (see §5).

### TD-56 — extract the shape dispatcher when a third consumer appears

Two copies exist by decision: `test_conversation_service.py` (full, with filter-level
discrimination for the two `messages` queries) and `test_conversations.py` (a ~15-line
table-only variant, because `create()`'s queries need nothing more). A third consumer is
the trigger to extract; that PR should migrate both copies so two do not become three.

### A18c follow-up — the self-comparison ring-true note reaches no memory pipeline

**Verified:** `routers/mirrors.py` contains **1** `enqueue_job` (the
`distill_user_text_to_memory_task` at `:149`); `routers/self_comparison.py` contains **0**.
Method: `grep -c enqueue_job` on both.

So a mirror ring-true note becomes a confidence-1.0 memory and a self-comparison one does
not. #557 deliberately left this alone — it was a safety PR. Whether the asymmetry is
intended is undecided.

### Ring-true gate is unreachable from the UI — known state, not a defect

See `PROJECT_STATE_v26.md §4` for the verification. Recorded here so it is not rediscovered
as a bug: the gate is correct, and no user can currently trigger it.

---

## 4. Open — P2 / P3 (carried, not re-verified)

- **TD-48 (P2)** — Stripe webhook has no idempotency or event ordering. Deferred until real
  payment traffic, by decision. ⚠️ **not re-verified this rotation.**
- **TD-49 (P3)** — vestigial `userPlan` params. ⚠️ **Re-verified:** still **4** occurrences
  in `apps/web/lib/api.ts` (`grep -c`). Harmless; clean up when those files are next
  touched.
- **TD-43** — `ritual_id` FK. Carried. ⚠️ **not re-verified.**
- **OPS-001** — ote.gr re-sync. Carried. ⚠️ **not re-verified.**
- **OPS-004** — the API's database role. ⚠️ **UNVERIFIED**, as in v25.

---

## 5. Open questions, not yet items

- **`complete()` calls are unlogged.** Memory extraction, insights, council briefs and
  title generation all use `llm_client.complete()`, which writes nothing to `messages`.
  Per-call attribution would need its own row or table. Until then, `tokens_used` covers
  user-visible assistant messages only — and TD-55's redundant spend is invisible in it.
- **`tokens_used` is volume, not cost.** The four buckets price 1.0× / 1.25× / 0.1×.
  Storing the components (#561) was chosen precisely so the weighting can be applied in SQL
  later and re-applied when prices change. No ceiling threshold has been chosen.
- **The 97.7% cache-read figure is an account-wide Console aggregate**, across all traffic
  including uncached `complete()` calls. It is not a per-message statistic, and it was
  briefly misread as evidence that cache reads were excluded from `tokens_used`. They are
  not: all four buckets are summed, which makes the total invariant to hit rate.

---

## 6. UNCARRIED from v25

**TD-01 … TD-42, and v25 §5–10.** Not re-verified this rotation, so not restated. See
`IMPLEMENTATION_BACKLOG_v25.md` and treat that content as unverified. Exceptions carried
with method are named above (TD-43, TD-44, TD-46 … TD-51, OPS-001 … OPS-006).

**The CORR-01 … CORR-15 set from v25** is not restated. v26 opens at CORR-16
(`PROJECT_STATE_v26.md §5`).
