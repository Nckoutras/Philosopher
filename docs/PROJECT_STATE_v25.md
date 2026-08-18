# PHILOSOPHER — Project State v25

> **What this file is:** Live snapshot of the project's current implementation status. Manually maintained.
>
> **v25 = v24 baseline (2026-07-19, captured through PR #520 / `faa18600`) + 2026-07-19→2026-08-18 delta (#522–#548).** A **UAT-response rotation**: nineteen of the twenty-seven PRs in this range close a numbered finding from the tester. Two migrations (**052 RLS**, **053 token_version**), one new service (`safety_event_log`), and two silent-data-loss incidents found from data rather than from anyone looking at the app.
>
> **Migration head 051 → 053_token_version.**
>
> **⚠️ THIS FILE REPLACES AN EARLIER, NEVER-MERGED `PROJECT_STATE_v25.md`.** See §0.
>
> **Generated:** 2026-08-18 (v25 rotation) · **Current main `cace1016`**

> **v25 conflict resolution rule:** Where v25 conflicts with v24 or earlier, v25 wins. **Production reality always wins over docs.**

---

> ## ⚠️ PROVENANCE — read this before trusting any claim below.
>
> **Every factual claim in this file is either (a) VERIFIED THIS ROTATION with its method stated inline, or (b) explicitly MARKED UNVERIFIED.** "Unchanged." is not used as evidence anywhere in this document. Where a claim from a prior document could not be re-checked, it is dropped rather than carried.
>
> **Verification SHA: `cace1016`** (`main` == `origin/main`, `git rev-list --left-right --count main...origin/main` → `0 0`, after `git fetch origin`).
>
> **Methods used this rotation:**
> - **Live code read at `cace1016`** — all file/line references below were opened at this SHA.
> - **Live database queries** against Supabase `bvzeuwzqgnqcghvqghtb` — `alembic_version`, RLS posture via `pg_class`/`pg_policies`, the subscription rows, the `users.token_version` column.
> - **Executed test suites** — backend `pytest` and frontend `vitest` + `tsc`, all run to completion on this machine at this SHA.
> - **`git log` / `git show` derivation** — the PR table in this file was derived from the commit graph, not transcribed from a session note.
>
> **Bounded-verification rule applied:** every grep or slice used to establish a claim below was bounded at both ends and its occurrence count recorded. Counts are quoted inline (e.g. "0 occurrences", "8 call sites") rather than asserted qualitatively.
>
> **What is NOT verified** is collected in §19.3, "UNVERIFIED — stated, not softened". Four items sit there. None of them are hedged elsewhere in the document.

---

## 0. THE FINDING OF THIS ROTATION — a document that was never real

**The v25 rotation was written on 2026-08-06 and never reached the repository.**

| Fact | Method |
|---|---|
| The v25 doc set exists only on a **local, unpushed, unmerged** branch `docs/v25-rotation` @ `b15811c0` | `git merge-base --is-ancestor b15811c0 main` → **NO**; `git ls-remote --heads origin docs/v25-rotation` → **empty output** |
| `docs/` on `main` stopped at **v24** / `SCREENS_TRACKING_v12` | `ls docs/` at `cace1016` — zero files matching `*v25*` or `SCREENS_TRACKING_v13` |
| That branch also carried an unmerged **`CLAUDE.md`** correction | `git show --stat b15811c0` — `CLAUDE.md | 38 +++--` |

So for twelve days the project's documented state was v24, while every downstream reader — including the brief-writing Claude — believed it was v25. The corrections that rotation caught (RLS, dual-tier) were never actually applied to anything.

**This file is that rotation, redone and extended**, renumbered to v25 and covering **#522–#548** so the chain on `main` runs unbroken v24 → v25 with no gap and no fiction. The `b15811c0` branch was **mined, not merged**: every claim carried from it was re-verified at `cace1016` first, and claims that could not be re-verified were dropped. Nothing was cherry-picked wholesale.

### 0.1 The miniature — a document asserting a fact about the future

The never-merged v25 states, in its provenance block and three more times in its body:

> **"#529 — this rotation (docs only). Self-referential; no product surface."**

**#529 is `16b213a7`, `fix(prompt): stop the persona announcing it is an AI mid-conversation`** — a product PR touching `system_base.jinja2`, closing UAT finding A7. Method: `git log -1 --format='%s' 16b213a7`.

The document reserved a PR number for itself, asserted what that number contained, and was wrong — because the PR was never opened and the number was taken by the next piece of real work.

**This is the same disease the document was written to diagnose.** That file's own §19 catalogues six claims copied forward without re-verification, and its session-lesson 13.51 says *"a doc claim repeated without re-verification is a claim about the previous doc, not about the system."* It then made a claim about a **PR that did not exist yet** — the same error pointed forward in time instead of backward. A claim about the future is unverifiable by construction: there was no code to check it against, and no amount of diligence would have caught it.

**Rule adopted:** a rotation document may state the range it covers. It may **not** assert the number, content, or existence of its own PR, or of any PR not yet merged. If the doc PR's number matters, it is recorded **after** the merge, or not at all.

---

## Part A — v25 delta (#522–#548)

> Derived from `git log` at `cace1016`, not transcribed. Each entry names the file(s) actually changed, read at this SHA.

### A1. The chat context window — three PRs, one arc (#522, #532, #533)

**#522 — the window fetched the OLDEST N messages.** All three chat paths built the LLM history with `.order_by(Message.created_at.asc()).limit(MEMORY_WINDOW_*)`, returning the *oldest* N messages, so past turn N the model never saw its own recent output. **User-visible symptom (UAT A2):** the tester quoted the persona's own immediately-preceding sentence back to it and was told *"I didn't say that — you did. And it's worth noticing you put it in my mouth."* A prior "window-cutoff" patch appended the newest user turn, producing `[oldest N] + [newest user turn]` — a context with a **gap in the middle** — which made turn N+1 look normal and turned legible amnesia into confident accusation. Fixed with `.desc()` + limit + `list(reversed(...))`.

**#532 — cache anchor (A10 phase 1).** A cache breakpoint on the message history, deliberately guarded to attach only when nothing had been evicted, because a sliding newest-N window can never hit the cache. Window left at 5/20. Cost only; the commit body states "no behaviour change, no copy change, nothing a user can see."

**#533 — the growing, budget-bounded window (A10 phase 2).** Removes the reason for phase 1's guard: the sliding window is replaced by one that grows and is bounded by token budget rather than message count (`conversation_service.py`, +144/−57).

> **Note for anyone reading v24 or earlier:** the "window 5 / window 20" framing is **superseded**. The window is budget-bounded as of #533. Do not carry the old numbers forward.

### A2. The letters arc — write-backs, and two silent-loss incidents

Seven PRs, and the two most serious defects this rotation were both found from **data**, not from anyone using the app.

- **#531 (A9) — the write-back loop was dishonest on the UI side.** A reader used the write-back field and reported the app had said it would read and answer her reply. The system behaved correctly — there is no live LLM reply in v1; the write-back is stored and re-injected as `<reader_wrote_back>` into the next letter. The **copy** promised something the system does not do. `arq_worker.py` +2, `WriteBackPanel.tsx` +1/−1.
- **#534 (A12) — a write-back could never reach the next letter.** The prior-letters fetch is scoped `voice_persona_id == this week's voice` (`arq_worker.py:1143`, season `:1416`), but the voice is **re-elected weekly** as the user's most-conversed persona over the trailing 7 days (`cron.py:288-307`). A voice change silently orphaned the write-back.
- **#541 (A14) — the same defect on the monthly cadence.**
- **#538 (A13) — write-backs now feed the memory pipeline** (`weekly_letters.py` +29).
- **#544 (A17) — malformed LLM JSON caused SILENT LOSS.** Incident of **2026-08-09**, recorded verbatim in the code comment at [arq_worker.py:243-245](apps/api/workers/arq_worker.py#L243-L245): *"the LLM wrote the letter, an unescaped quote broke `json.loads`, nothing was persisted and arq reported `j_failed=0`."* The failure unwound past the row-writing code into an outer `except` and **reported success**. Fixed with a shared `_parse_letter_payload` that returns `None` instead of raising, plus one retry carrying `JSON_RETRY_DIRECTIVE`, then a visible failure row.
- **#546 (A17b) — the same parse bug in two more generators.** See §A6.
- **#545 / #547 (A18, A18-monthly) — a ritual-only week classified as quiet.** Incident of **2026-08-16**, recorded at [arq_worker.py:290-295](apps/api/workers/arq_worker.py#L290-L295): the dispatch enqueued **zero** letters; the one active user had spent the week in rituals — 1 council, 3 counterview rebuttals, 2 mirror notes, 1 you-vs-you — and sent **0 chat messages**. Eligibility counted only `Message` rows. Now one definition of "ritual activity" serves **both** the cron eligibility count and the generator's quiet-week gate, so the two cannot drift.

### A3. Auth — session survival and revocation (#535, #543)

- **#535 (A11) — an active user was logged out on a fixed 7-day timer.** `JWT_EXPIRE_MINUTES` is 7 days (`config.py:22`), tokens carry a hard `exp`, and `decode_token` validated that and nothing else. Expiry ran from **issue**, not from last use: a user who opened the app every single day was logged out on day 7. In a habit product whose central ritual is weekly, that is a churn event on the cadence of the ritual itself. Added `POST /auth/refresh` (authenticated by `get_current_user` and nothing more) plus `api.refreshSession()` called from `QueryProvider` on load and on foreground return, throttled to 12h.
- **#543 (A16) — sign-out did not revoke anything.** Sign-out was client-side only; a leaked token stayed valid until natural expiry. Added `users.token_version` (**migration 053**), a `"ver"` claim on every minted token, and a comparison in **both** validators — `get_current_user` ([auth.py:57](apps/api/auth.py#L57)) and `get_user_plan_streaming` ([auth.py:97](apps/api/auth.py#L97)). **No mass logout on deploy:** a missing `"ver"` reads as `0`, matching the column default, so pre-A16 tokens age out naturally. The streaming validator's check sits **inside** the session block deliberately — the returned `User` is detached once the session closes, so the comparison must happen while the row is attached.

### A4. Rate limits and the paywall (#536, #540)

- **#536 (A15) — every free user who hit a cap saw a fabricated reset time**, on the conversion surface. `main.py:78-85` configured `CORSMiddleware` **without `expose_headers`**; Starlette defaults it to an empty sequence and emits the header only when non-empty. Web (Netlify) and API (Render) are different origins, so JavaScript could read only the seven CORS-safelisted headers. The backend had been sending correct values the whole time. `lib/api.ts` reads them in **six** places, each with a silent fallback — `Reset` falling back to `new Date().toISOString()`. So the paywall told users their limit "resets today at «the current time»" and showed a limit of 0.
- **#540 (A15b) — council and you-vs-you never sent `X-RateLimit-Reset` at all.**

### A5. Council — members counselled the text, not the person (#530)

UAT A5. The tester pasted a Machiavelli line into chat and pressed "Ask the Council". Three of four members opened by establishing identity — Epictetus: *"That line is not mine. It belongs to Machiavelli."* Freud: *"You are asking me what Machiavelli meant. I am not Machiavelli."* The matter reached each member as a **bare user turn** (`messages = [{"role": "user", "content": effective_matter}]`) with nothing marking it as a person's matter rather than a text to appraise.

**Why the fix went where it did:** investigation ruled out the distil prompt — `COUNCIL_DISTILL_PROMPT` forbids quotation and forbids naming personas, so a successful distillation cannot produce an attributable line, which is how the session knew distillation never ran. **Four separate paths** reach the raw matter (<2 user turns, distil exception, empty completion, `matter_edited`) and all four collapse onto the same hand-off. Framing the hand-off covers every one; fixing any single fallback would have covered one.

### A6. The JSON parse net — one symptom, four sites (#544, #546)

`_parse_letter_payload` ([arq_worker.py:273](apps/api/workers/arq_worker.py#L273)) now serves **four generator families, at 8 call sites** (initial attempt + retry each). Verified by bounded grep — `_parse_letter_payload(` returns 9 occurrences: 1 definition + 8 calls.

| Family | Call sites | Fixed by |
|---|---|---|
| Insight | `:848`, `:862` | **#546 (A17b)** |
| Mirror | `:1225`, `:1237` | **#546 (A17b)** |
| Weekly letter | `:1696`, `:1709` | #544 (A17) |
| Season letter | `:2053`, `:2064` | #544 (A17) |

The reported symptom was **one** letter. A17 fixed the letter family (2 of 4); **two siblings with the identical defect survived that PR** and were closed only by A17b. See §21 L-04.

**A17b also had to distinguish two identical values.** `INSIGHT_PROMPT` asks for bare `null` when no insight is worth surfacing — a **valid** outcome. But `json.loads("null")` returns `None`, which is the same value `_parse_letter_payload` returns on **failure**. Indistinguishable downstream. `_is_null_reply` ([arq_worker.py:256](apps/api/workers/arq_worker.py#L256)) recognises the deliberate-null case from the raw reply, fence-tolerantly, **before** any retry decision.

### A7. Safety events on ritual surfaces (#548) — and the gap it left

Until A18b, `SafetyEvent` had exactly one writer: `ConversationService._log_safety_event`. Ritual surfaces ran safety checks but wrote **no rows**, so the safety record described chat only.

New `services/safety_event_log.py` is the single writer. **Six new call sites**, verified by bounded grep (`log_safety_event(` — 11 occurrences: 1 definition, 4 chat-path, 6 new):

| Surface | Site |
|---|---|
| Council | `council_service.py:164` |
| Counterview | `counterview_service.py:122` |
| Counterview rebuttal | `counterview_service.py:585` |
| Self-comparison | `self_comparison_service.py:177` |
| Scheduled email ×2 | `scheduled_emails.py:68`, `:198` |

**`ConversationService._log_safety_event` became a thin delegate** ([conversation_service.py:1644-1656](apps/api/services/conversation_service.py#L1644-L1656)) with an **unchanged signature**, so the three chat call sites needed no edit. The docstring states the reasoning exactly: *"'chat behaviour is byte-identical' is guaranteed by the diff not touching them, not by anyone re-reading them."* See §21 L-02.

**The decision A18b took:** the **originating surface owns the record**. The weekly and monthly letter blocks therefore write no `SafetyEvent`. This is deliberate — and it is precisely what leaves **A18c** open (§19.4).

### A8. Infrastructure and copy (#537, #539, #542)

- **#537** — `package-lock.json` synced with the already-declared `jsdom@^25.0.0` and `@testing-library/react@^16.0.0`. 69 entries added (all `"dev": true`), 1 changed (`hasown` 2.0.3 → 2.0.4, forced by `jsdom → form-data@4.0.6`), **0 removed**. Ships `docs/reports/WEB_TEST_TYPECHECK_MEASUREMENT_2026-08-13.md`.
- **#539** — upgrade page and Terms aligned to the locked pricing. Verified at `cace1016`: `€99.99 / year` (`upgrade/page.tsx:56`), `€11.99 / month` (`:77`), and the Terms billing sentence (`terms/page.tsx:65`). **⚠️ The Stripe price objects themselves are NOT updated** — the commit body says so explicitly (§19.4, OPS-006).
- **#542** — **migration 052 codifies the live RLS state**, closing OPS-005. See §4.

---

## Changelog v24 → v25 (PR history, newest first)

Derived from `git log` at `cace1016`.

| PR | SHA | Description | UAT |
|---|---|---|---|
| #548 | `cace1016` | feat(safety): ritual surfaces record safety events | A18b |
| #547 | `1715338e` | feat(letters): season letter sees the whole month | A18-monthly |
| #546 | `10f40db2` | fix(workers): extend the JSON parse net to mirror and insight | A17b |
| #545 | `99e50f9b` | feat(letters): weekly letter sees the whole week | A18 |
| #544 | `29c97fb4` | fix(letters): survive malformed LLM JSON | A17 |
| #543 | `7bdb4693` | feat(auth): token revocation via token_version | A16 |
| #542 | `41e9058a` | chore(db): codify live RLS state as migration 052 | (OPS-005) |
| #541 | `e71bc35a` | fix(letters): monthly write-backs survive to next season letter | A14 |
| #540 | `f45f1480` | fix(limits): send X-RateLimit-Reset on council and you-vs-you | A15b |
| #539 | `246a37c0` | fix(pricing): align upgrade page and Terms with locked pricing | — |
| #538 | `e4e8b3ea` | feat(letters): feed write-backs into the memory pipeline | A13 |
| #537 | `eb2f4033` | chore(web): sync package-lock with declared jsdom deps | — |
| #536 | `f51c749e` | fix(cors): expose the X-RateLimit-* headers | A15 |
| #535 | `8fe051e2` | fix(auth): an active user must never be logged out | A11 |
| #534 | `79f52e8b` | fix(letters): a write-back must reach whoever writes the next letter | A12 |
| #533 | `6f202745` | perf(chat): growing, budget-bounded message window | A10 ph2 |
| #532 | `7dc54e0f` | perf(chat): anchor the message history in the prompt cache | A10 ph1 |
| #531 | `c7d0a961` | fix(letters): the write-back loop must be honest on both sides | A9 |
| #530 | `28d71a61` | fix(council): frame the matter so members counsel the person | A5 |
| #529 | `16b213a7` | fix(prompt): stop the persona announcing it is an AI | A7 |
| #528 | `7bdf3014` | fix(billing): retire the Premium tier from frontend and schema | — |
| #527 | `e9ed799d` | fix(cron): never downgrade a subscription Stripe does not recognise | — |
| #526 | `24351c48` | fix(billing): survive the live-key switch | — |
| #525 | `529acf8f` | ci(web): measure typecheck + tests without blocking | — |
| #524 | `b70132c1` | fix(paywall): show save-limit copy instead of daily-limit copy | — |
| #523 | `74f92f54` | fix(mobile): lift chat composer above the Android keyboard | A1 |
| #522 | `f8ced63d` | fix(chat): history window must fetch the newest N messages | A2 |

**#521 was the v24 doc rotation.** This rotation's own PR number is deliberately **not** asserted here — see §0.1.

---

## 1. Stack

**`anthropic` SDK pinned `0.99.0`** — VERIFIED, `requirements.txt:14` read at `cace1016`. No dependency changes on the API side this rotation. One frontend lockfile sync (#537), no `package.json` change (the #537 report records `git diff --exit-code` → 0 on `package.json`).

Remaining stack details are **UNCARRIED from v24** — not re-verified this rotation, so not restated. See `PROJECT_STATE_v24.md §1` and treat that content as unverified.

---

## 2. Production status

- Live URL: **https://thinkalike.netlify.app**
- Current main: **`cace1016`**. **Alembic head `053_token_version`** — see §4.
- **Has paying users:** No. **Has free trial users:** No.

### Other systems — verified items only

- **Stripe:** live-key code hardening landed in #526/#527/#528. **Not re-verified this rotation** beyond the pricing strings — treat the #526–#528 behavioural claims as carried-from-session, not re-checked. What *is* verified: the **price objects still point at the old amounts** (OPS-006).
- **`BETA_GRANT_PRO_TO_ALL`:** ⚠️ **UNVERIFIED.** Code default is `False` ([config.py:50](apps/api/config.py#L50), read at `cace1016`). The **production** value is a Render environment variable and is not readable from this machine; `main.py:41-42` logs a startup warning when enabled, but there is no Render log access from here. **Do not treat this as confirmed off.** See §19.3.
- **Chat context window:** budget-bounded and growing as of #533 (verified against the `6f202745` diff).
- **Safety record:** covers chat **and** council, counterview, counterview-rebuttal, self-comparison, scheduled email as of #548 (§A7). It does **not** cover the mirror ring-true note (A18c).
- **Frontend CI:** typecheck + vitest run non-blocking on `apps/web/**` PRs. **There is no backend CI at all** — see §19.4, TD-50.

---

## 3. Personas registered

**11 personas** — VERIFIED by reading `PERSONA_REGISTRY` at [personas/__init__.py:16-26](apps/api/personas/__init__.py#L16-L26): Marcus Aurelius, Simone de Beauvoir, Carl Jung, Socrates, Epictetus, Sigmund Freud, Lao Tzu, Niccolò Machiavelli, Oscar Wilde, George Orwell, Miyamoto Musashi. No persona work this rotation.

---

## 4. Database schema

### Migration head — VERIFIED by two independent methods, agreeing

**`053_token_version`.**

1. **Chain read** at `cace1016`: 53 migration files; 53 `revision` ids; 52 `down_revision` ids. Set difference (`comm -23`) yields **exactly one** head, `053_token_version`. `uniq -d` on both lists → **zero** duplicate revision ids and **zero** branch points.
2. **Live database:** `select version_num from alembic_version` on `bvzeuwzqgnqcghvqghtb` → **`053_token_version`**.

Chain tail: `049_quotes_expand` → `050_deep_mode_count` → `051_council_matter_edited` → `052_enable_rls` → `053_token_version`. All four revision ids are ≤ 32 characters and each filename equals its revision id (C-04 satisfied).

### New migrations this rotation

**`052_enable_rls`** (#542) — codifies the live RLS posture in the chain. Enables RLS on **34 literal, named** application tables. Deliberately: zero policies, no FORCE — reproducing the *verified production posture* rather than an improved version of it. `alembic_version` is excluded on the stated ground that a migration should not reach into its own plumbing, which is why a **rebuilt database reports 34 and production reports 35 — both correct**. The list is literal rather than reflected, because an `information_schema` loop would enable RLS on whatever happened to exist at run time. **No-op against the live database by construction** (`ENABLE ROW LEVEL SECURITY` on an already-enabled table succeeds and changes nothing). Establishes **C-05**: every future migration creating a public table must enable RLS in the same migration.

**`053_token_version`** (#543) — `users.token_version`, additive, `NOT NULL DEFAULT 0`. **VERIFIED live:** `information_schema.columns` reports `token_version | integer | NO | 0`.

### RLS state — VERIFIED LIVE THIS ROTATION (re-measured, not carried)

Live query against `pg_class` / `pg_namespace` / `pg_policies`:

```
public_tables    = 35
rls_enabled      = 35
force_rls        = 0
policy_count     = 0
distinct_owners  = 1  (postgres)
```

**Meaning:** RLS enabled with no policies and no FORCE → the table owner bypasses RLS entirely, while any non-owner role (the Supabase `anon` / `authenticated` roles behind PostgREST) is denied everything. The auto-generated REST surface is **closed**.

This is the second consecutive rotation to measure this directly. It is recorded as measured **both** times, not carried from the first.

**OPS-005 is CLOSED** — the state now survives a rebuild from the chain (#542). **OPS-004 remains UNVERIFIED** (§19.3).

### Live subscription rows carrying a `stripe_subscription_id` — VERIFIED LIVE

**7 rows.** Aggregated query (grouped by plan/status/id-prefix; a per-email query was refused by the tooling, so no addresses appear here):

| plan | status | id prefix | `current_period_end` null? | rows | In reconcile-cron scope? |
|---|---|---|---|---|---|
| pro | active | `sub_1Te…` | no | **4** | **yes** |
| pro | incomplete | `sub_1Te…` | no | 1 | no — **status only** |
| free | canceled | `sub_bet…` | no | 1 | no — status only |
| free | canceled | `admin_o…` | no | 1 | no — status only |

All five `sub_1Te…` ids are **test-mode** and will not resolve under live keys. Comp grants **do** carry a `stripe_subscription_id` — synthetic (`admin_override`, `sub_beta_…`) — and are excluded from the cron **by status alone, not by a NULL id**. See OPS-002 / OPS-003 (§19.5).

---

## 5. Backend endpoints — new / changed this rotation

Verified by reading each file at `cace1016`.

| Method · Path | Router / Service | Notes |
|---|---|---|
| `POST /auth/refresh` | `routers/auth.py` | **NEW (#535).** Authenticated by `get_current_user` only — that dependency already 401s an expired or malformed token and confirms the user still exists. Returns the same `TokenResponse` as the four other mint sites. |
| `POST /auth/signout` | `routers/auth.py:111-124` | **CHANGED (#543).** Increments `users.token_version`, killing every token on every device. |
| Token validation ×2 | `auth.py:57`, `auth.py:97` | **CHANGED (#543).** Both validators compare the `"ver"` claim. A missing claim reads as `0`. |
| `POST /council/*` | `routers/council.py` | **CHANGED (#540).** Sends `X-RateLimit-Reset` on the weekly-limit 429. |
| `POST /self-comparison/*` | `routers/self_comparison.py` | **CHANGED (#540).** Same. |
| CORS | `main.py` | **CHANGED (#536).** `expose_headers` now set, so the browser can read `X-RateLimit-*` cross-origin. |
| `POST /weekly-letters/*` write-back | `routers/weekly_letters.py` | **CHANGED (#538, #544).** Feeds the memory pipeline; survives malformed JSON. |
| `POST /mirrors/{id}/ring-true` | `routers/mirrors.py:79-115` | **UNCHANGED — and this is the A18c gap.** Writes `ring_true_note` at `:93` with **no safety check**. |

**Endpoints from v24 and earlier are UNCARRIED** — not re-verified this rotation, so not restated here.

---

## 6. System prompt

**`system_base.jinja2` changed this rotation (#529).** Line 4 previously read *"You do not claim to be a real person — you are an AI companion grounded in historical philosophy."* Correct as a boundary, wrong as a speech act: it sat among lines 2–3 as another declarative fact about the assistant, so the model **discharged it by saying it**, in the persona's voice. Nothing marked it as a constraint to observe rather than a proposition to state, and nothing said what to do when asked directly. It also contradicted two existing rules — §5.7.9's forbidden lexicon lists AI tells as never to be produced, and §10.1 places the not-a-real-person boundary at the **product** level, not inside persona speech.

The replacement keeps the honesty constraint as a **prohibition on asserting** (never claim to be the literal person, never invent biography), forbids in-chat disclosure **in both directions**, says why, and supplies the positive instruction the original lacked. Deflection is in character; a system announcement is not.

Other prompt claims are **UNCARRIED** from v24.

---

## 19. Open / Closed items

### 19.1 Corrections applied this rotation

- ✅ **CORR-09 (NEW, and the headline) — the v25 rotation was never merged.** §0. Twelve days of believed-current documentation that existed on one machine only. Includes an unmerged `CLAUDE.md` fix.
- ✅ **CORR-10 (NEW) — a document asserted a fact about a PR that did not exist.** §0.1. `#529` was reserved for the doc rotation and is a product PR.
- ✅ **CORR-11 (NEW) — `.env.local` HAS been git-ignored since 2026-05-28.** It sat on the **P0 "do before any PR" blocker list for twelve rotations**. **Method:** `git check-ignore -v .env.local` → `.gitignore:12:.env.*	.env.local` (also matches `apps/web/.env.local`). **The history is the finding:** the claim was **true when written** in v13 (`#131`, `9fabf0aa`, 2026-05-28) and fixed by **`#132` (`8e073e9d`), the very next commit, the same day** — `git rev-list --count 9fabf0aa..8e073e9d` = **1**. It was then asserted in all three doc files for v13–v24, plus the unmerged v25. **A blocker was true for the length of one commit and tracked for three months.**
- ✅ **CORR-12 (NEW) — there IS a Node runtime on this machine.** **Node v20.18.1 / npm 10.8.2** at `C:\clwn\node-v20.18.1-win-x64`, verified by executing both. The unmerged v25 states "vitest and `tsc` cannot be run locally at all" and instructs "do not claim a frontend test passes". **Both wrong** — this rotation ran the full frontend suite twice and `tsc` once.
- ✅ **CORR-13 (NEW) — "jsdom missing" was a lockfile fact, not a manifest fact.** `jsdom@^25.0.0` was declared in `package.json:37` all along; it was absent from `package-lock.json` until #537. The failure mode was `npm ci`, not the dependency list. Caught by diffing manifest against lockfile rather than trusting either alone.
- ✅ **CORR-14 (NEW) — there is no local Postgres usable for Philosopher.** The PG 16.4 cluster at `C:\clwn\pgdata` is **not** Philosopher's: `pg_start_ops005.log` records `FATAL: role "philosopher" does not exist` (2 occurrences) and `ERROR: extension "vector" is not available` — no pgvector, so the schema could not be stood up even with a role. The neighbouring project at `C:\clwn\cleo-wholesale` is a different product. The server is not currently running (connection refused on 5432).
- ✅ **CORR-15 (NEW) — TD-47's "8 production type errors" was 4.** **Method:** `npm run typecheck` executed at `cace1016`. 11 errors total: **4 production** (`app/app/(tabs)/account/page.tsx:112,114,117` TS18047; `app/auth/oauth/finish/page.tsx:33` TS2345) and **7 test-file**. Neither production file was touched recently, so the discrepancy predates the measurement — most likely the "8" counted **raw output lines** (TS2345 prints across 2 lines).
- ✅ **CORR-16 (NEW) — MIRROR_PROMPT was read as MONTHLY_PROMPT.** Distinct constants: `MONTHLY_PROMPT` at [arq_worker.py:95](apps/api/workers/arq_worker.py#L95), `MIRROR_PROMPT` at [arq_worker.py:147](apps/api/workers/arq_worker.py#L147). **Mechanism:** a slice bounded only at the start runs past the end of one constant into the body of the next, so the reader sees mirror text under a monthly label. This is exactly what the bounded-verification rule exists to prevent, and it happened anyway — see §21 L-01.
- ✅ **CORR-05 (RE-VERIFIED, carried with method) — RLS is ENABLED on all 35 public tables.** Re-measured live this rotation (§4), not carried from the prior document. Now also durable in the chain (#542).
- ✅ **CORR-06 (RE-VERIFIED, carried with method) — dual tier resolution is closed in CODE.** [auth.py:62-69](apps/api/auth.py#L62-L69) read at `cace1016`: `get_current_user_plan` is a thin FastAPI dependency wrapper that calls `get_user_tier` and returns `(user, tier)`. **But `CLAUDE.md` on `main` still carries the false text** — see §19.2.

### 19.2 🔴 FIRST ITEM OF THE NEXT SESSION — the `CLAUDE.md` correction

**Queued as a standalone two-minute follow-up PR so it cannot be lost a second time.** It was written on 2026-08-06, never landed, and the false text has been shaping briefs for months.

- **File:** `CLAUDE.md`
- **Exact line range to replace:** **314–325** (verified at `cace1016`)
- **What is there now (FALSE):** a `### Dual tier resolution (added PR4j-paywall-audit, 2026-05-23)` section stating that `get_current_user_plan` and `get_user_tier` "are two parallel tier-resolution functions with different semantics", that `get_current_user_plan` "returns `"free" | "pro" | "premium"` from `Subscription.plan` directly", and that "the duplication remains".
- **Why it is false:** `get_current_user_plan` has delegated to `get_user_tier` since **#203** (2026-06-03). Verified at [auth.py:62-69](apps/api/auth.py#L62-L69).
- **Correct replacement content:** mark the section CLOSED, keeping the entry precisely *because* it was carried as open for eight rotations; state that `services/tier_service.py:get_user_tier` is the single tier-resolution function, that `auth.py:get_current_user_plan` is a thin FastAPI dependency wrapper delegating to it and returning `(user, tier)`, that every enforcement point resolves through `get_user_tier` including its expiry/status validation and the `BETA_GRANT_PRO_TO_ALL` bypass, and that the deleted text was false from #203 onward.
- **A ready-made draft of this replacement exists** in the unmerged branch: `git show b15811c0 -- CLAUDE.md`. Read it, re-verify it against `auth.py` at the then-current SHA, and land it. **Do not merge the branch to get it.**
- **Also add one Failure Log entry** recording the copied-claim disease. A drafted version is in the same diff.

### 19.3 ⚠️ UNVERIFIED — stated, not softened

These four are unverified. They are not hedged anywhere else in this document, and none should be read as "probably fine".

- ⚠️ **`BETA_GRANT_PRO_TO_ALL` production value.** Code default `False` ([config.py:50](apps/api/config.py#L50)). The live value is a Render env var. **No Render dashboard or log access from this machine. Not determined.** Everything downstream — whether billing defects are currently masked, whether tier gates are live — inherits this uncertainty.
- ⚠️ **OPS-004 — which database role the API connects as.** The §4 RLS posture holds **only** if the API connects as the table owner or a `BYPASSRLS` role. The circumstantial evidence is that queries work today. The `DATABASE_URL` is not readable from the repo. **Not verified directly.**
- ⚠️ **TD-44 — prompt-cache reads.** `cache_read > 0` has still never been confirmed in production logs. Carried unconfirmed since v24. No log access from here.
- ⚠️ **A1 — the Android keyboard fix (#523) has never been run on a device.** Live in production since 2026-08-06.

**The 49 / 13 frontend failure split is NOT in this set — it is VERIFIED.** It was carried as "attributed to the 2026-08-13 report" in an earlier draft of this file and has since been **measured directly**. Method: `npx vitest run` executed at `cace1016` **twice**, with and without `globals: true` in `apps/web/vitest.config.ts`:

| | Tests | Files |
|---|---|---|
| Baseline | **62 failed / 54 passed** (116) | 16 of 24 failing |
| With `globals: true` alone | **13 failed / 103 passed** (116) | 6 of 24 failing |

**49 failures are attributable to that one config line by execution, not by inference.** The remaining 13 are stale assertions against changed components, individually identified in TD-51.

### 19.4 NEW open items logged this rotation

- 🔴 **A18c (NEW, P1) — the mirror ring-true note is never safety-checked at write time.** **Verified at `cace1016`:** `routers/mirrors.py` contains **1** occurrence of the string "safety", and it is a **comment** at `:100` describing gating inside a *downstream* memory task. There is **no safety call in the file**. The note is persisted unchecked at `mirrors.py:93`. The only place that text is ever checked is the weekly/monthly letter block — and per **A18b's decision** that the originating surface owns the record, that check writes **no `SafetyEvent`**. So a user's own words enter the system, are stored, and are surfaced back with no safety record anywhere. Logged in #548's PR description.
  - **⚠️ SIBLING FOUND WHILE VERIFYING THIS — do not fix A18c alone.** `routers/self_comparison.py` contains **0** occurrences of "safety", and its `set_ring_true` handler (`:85-102`) writes `row.ring_true_note = body.note` at `:101` with the same absence of a check. **Two ring-true surfaces, one reported.** Fixing only the reported one would reproduce the A17 → A17b pattern exactly (§21 L-04).
- 🔴 **TD-50 (NEW, P1) — there is no backend CI at all.** **Verified:** `.github/workflows/` contains **exactly one** file, `web-build.yml`, triggered only on `apps/web/**` paths. Consequences, each independent:
  1. **`pytest` never runs in CI.** The 29 red backend tests are invisible to everyone except a human who runs them locally — and this machine is the only place that happens.
  2. **No job enforces C-04** (revision id ≤ 32 chars, filename == revision id). That rule exists *because* violating it crashed a production deploy (#371).
  3. **No job enforces a single migration head.** A branch-point would be discovered at deploy time.
  4. **The web job uses `npm install`, not `npm ci`** — so #537's lockfile sync is not actually enforced by the job that motivated it. A drifted lockfile would still pass.
- 🔴 **OPS-006 (NEW, P0-revenue) — the Stripe price objects still point at the old amounts.** #539 aligned the **strings** on the upgrade page and in the Terms (verified: `upgrade/page.tsx:56,77`, `terms/page.tsx:65`). The commit body of `246a37c0` states plainly: `STRIPE_PRICE_PRO_MONTHLY` / `STRIPE_PRICE_PRO_YEARLY` **"still point at the old price objects — must be recreated at €11.99/€99.99 before the live-key switch."** The app currently displays one price and would charge another.

### 19.5 Carried open items — re-verified this rotation

- 🔴 **TD-45 — 29 red backend tests.** **Re-verified by execution** at `cace1016`: `29 failed, 513 passed` (542 total). Composition unchanged: 17 in `tests/services/test_conversation_service.py` (2 `daily_usage`, 7 `auto_title`, 3 `llm_*`, 5 `memory_extraction`) plus 12 across `tests/routers/test_share.py` (4), `tests/test_postprocessing.py` (3), `tests/test_conversations.py` (2), `tests/services/test_counterview_rebuttal.py` (2), `tests/routers/test_conversations.py` (1). Cause: hard-coded `execute()` call indices in the mock harnesses. **Billing counters, auto-title cadence, LLM retry and memory extraction have no working coverage.** Not a product failure — a broken harness. Compounded by TD-50: nothing in CI would ever report this.
- 🔴 **TD-47 — `npm run build` validates nothing.** **Re-verified:** [next.config.js](apps/web/next.config.js) sets `typescript.ignoreBuildErrors: true` and `eslint.ignoreDuringBuilds: true`. A green Netlify check proves only that a bundle was produced. Real count: **11 typecheck errors, 4 in production code** (CORR-15).
- 🔴 **TD-51 (NEW number, pre-existing defect) — the RTL cleanup gap.** **Verified:** `apps/web/vitest.config.ts` contains **0** occurrences of `globals: true`; `cleanup()` appears **0** times anywhere in `apps/web` outside `node_modules`. RTL's auto-cleanup registers only `if (typeof afterEach === 'function')`, so it never registers; every `render()` leaves a container in `document.body` and `screen.*` queries see all prior renders. **49 of the 62 frontend failures are this one config line — VERIFIED by executing the suite with and without it (62 failed → 13 failed).** The fix is `globals: true` **alone**: no `cleanup()` in `vitest.setup.ts` (RTL registers its own as soon as a global `afterEach` exists, and a manual one would pull RTL and `react-dom` into the 4 node-environment test files that don't need them), and no tsconfig change. The 13-test residue is identified in `IMPLEMENTATION_BACKLOG_v25.md §3` and is a separate PR.
- 🔴 **TD-46** — vitest CI enforcement decision, still unmade. 🔴 **TD-48** — webhook idempotency, deferred by decision. 🔴 **TD-49** — vestigial `userPlan`: **verified 4 occurrences** in `apps/web/lib/api.ts` (`:940`, `:970`, `:1003`, plus the explanatory comment at `:937`), 5 repo-wide in `apps/web`.
- 🔴 **OPS-002 / OPS-003** — the stale subscription rows. Re-verified live (§4). Decide **before** the key switch so post-switch logs are readable.
- 🔴 **CORR-08 follow-up** — the two stale `zoom: 1.15` comments. **Not re-verified this rotation** — treat as unconfirmed until someone opens `globals.css:57`.

### 19.6 Closed this rotation

- [x] **OPS-005** — RLS state is now in the migration chain (#542).
- [x] **A5** council identity-flexing (#530) · **A7** AI-disclosure (#529) · **A9** write-back copy (#531) · **A10** context cost + window (#532/#533) · **A11** session expiry (#535) · **A12** write-back lost on voice change (#534) · **A13** write-backs → memory (#538) · **A14** monthly write-backs (#541) · **A15** fabricated reset time (#536) · **A15b** council/YvY reset header (#540) · **A16** token revocation (#543) · **A17/A17b** malformed JSON silent loss (#544/#546) · **A18/A18-monthly** ritual-only week (#545/#547) · **A18b** ritual safety events (#548).
- [x] **Pricing copy** aligned to the locked decision (#539) — **strings only**, see OPS-006.
- [x] **`.env.local` blocker** — was never real (CORR-11).

### 19.7 Locked decisions

- 🔒 **Pricing — LOCKED 2026-08-06.** Single Pro tier. **€11.99/month, €99.99/year.** No free trial, no founding discount, no Premium in v1. **⚠️ Recorded honestly: the UAT willingness-to-pay validation was deliberately NOT run.** The decision rests on cost model plus competitive analysis only. A named, accepted risk. **Copy now matches; the Stripe price objects do not** (OPS-006).
- 🔒 **A18b — the originating surface owns the safety record.** The letter blocks write no `SafetyEvent`. Deliberate, and the direct cause of A18c's shape.
- 🔒 **C-05 — every migration creating a public table enables RLS in the same migration.** Established by 052.

---

## 20. UAT findings (tester: Marialena) — full table

**⚠️ The single most operationally important fact in this document: of the nineteen findings closed, EIGHTEEN are live in production and NOT ONE has been confirmed by a human being.** They are verified by unit tests and by code reading. No one has opened the app and watched any of them work.

| ID | Finding | Status | Confirmed by a human? |
|---|---|---|---|
| **A1** | On-screen keyboard covers the chat composer (Android) | Fixed #523 | ❌ **LIVE, NEVER SEEN** — and device-untestable from here |
| **A2** | Persona denies its own words, accuses user of fabricating | Fixed #522; window reshaped #533 | ❌ **LIVE, NEVER SEEN** |
| **A3** | Self-Portrait stall | 🔴 **OPEN** — needs logs | — |
| **A4** | "Next" button discoverability | 🔴 **OPEN** | — |
| **A5** | Council disowns a chat-sourced matter | Fixed #530 | ❌ **LIVE, NEVER SEEN** |
| **A6** | Jung latency | 🔴 **OPEN** — needs measurement | — |
| **A7** | AI-disclosure inconsistency | Fixed #529 | ❌ **LIVE, NEVER SEEN** |
| **A8** | **Sign-in screen does not distinguish login from signup** | 🔴 **OPEN — unfixed, with live data consequence** | — |
| **A9** | Write-back promises a reply the system never gives | Fixed #531 | ❌ **LIVE, NEVER SEEN** |
| **A10** | Chat context cost / window shape | Fixed #532 + #533 | ❌ **LIVE, NEVER SEEN** |
| **A11** | Active user logged out after days away | Fixed #535 | ❌ **LIVE, NEVER SEEN** |
| **A12** | Write-back lost when the weekly voice is re-elected | Fixed #534 | ❌ **LIVE, NEVER SEEN** |
| **A13** | Write-backs never reached the memory pipeline | Fixed #538 | ❌ **LIVE, NEVER SEEN** |
| **A14** | Monthly write-backs lost before the next season letter | Fixed #541 | ❌ **LIVE, NEVER SEEN** |
| **A15** | Fabricated reset time on the paywall | Fixed #536 | ❌ **LIVE, NEVER SEEN** |
| **A15b** | Council / you-vs-you sent no reset header | Fixed #540 | ❌ **LIVE, NEVER SEEN** |
| **A16** | Sign-out did not revoke the token | Fixed #543 | ❌ **LIVE, NEVER SEEN** |
| **A17** | Malformed LLM JSON → silent letter loss | Fixed #544 | ❌ **LIVE, NEVER SEEN** |
| **A17b** | Same defect in mirror + insight generators | Fixed #546 | ❌ **LIVE, NEVER SEEN** |
| **A18** | Ritual-only week classified as quiet (weekly) | Fixed #545 | ❌ **LIVE, NEVER SEEN** |
| **A18-monthly** | Same, season letter | Fixed #547 | ❌ **LIVE, NEVER SEEN** |
| **A18b** | Ritual surfaces wrote no safety events | Fixed #548 | ❌ **LIVE, NEVER SEEN** |
| **A18c** | **Mirror ring-true note never safety-checked at write time** | 🔴 **NEW — OPEN** (+ an unreported sibling) | — |

### A8 in detail — the open finding with a live data consequence

**The sign-in screen does not distinguish login from signup.** The tester created **three accounts by accident**.

**Consequence, verified by live query this cycle:** her activity is **split across two accounts** — a yahoo address (her real, primary account) and a gmail address (the accidental one). On **2026-08-09** a weekly letter was generated for the **accidental** account. Her real account received **none**.

This is not a cosmetic onboarding complaint. It is the product's central weekly ritual being delivered to the wrong account while the user's real account looks inactive — and from the inside it would read as the letters feature simply not working. **A8 is unfixed.**

> **Two of this rotation's most serious defects (A17 silent letter loss, A18 zero-letter dispatch) were found in the letters pipeline from data. A8 is a third letters-adjacent defect, also found from data, also still open.** The pattern is that nothing and nobody is watching whether letters actually arrive.

---

## 21. Session lessons

- **L-01 — A check that cannot fail is not a check.** Three incidents this cycle, one shape:
  1. **The one-sided prompt slice.** A slice bounded only at its start ran past `MONTHLY_PROMPT` into `MIRROR_PROMPT` (`arq_worker.py:95` → `:147`). The reader saw mirror text under a monthly label. The slice *could not* have revealed the mistake — it had no end.
  2. **The revert-verify where all the tests still passed.** A new test was checked against the old code to prove it fails without the fix. Everything stayed green. **Green there is a finding, not a pass:** it means the test does not exercise the fix. It was briefly read as reassurance.
  3. **Guards presented as proofs.** A guard clause was offered as evidence that a case is handled. A guard shows the case was *thought about*. Only an execution that reaches the guard shows it *fires*.

  In all three, the artifact was shaped so the failing outcome was unreachable. **Before trusting a check, name the observation that would make it fail. If you cannot name one, you have a ritual, not a check.**
- **L-02 — Prefer guarantees the diff can carry.** Applied deliberately **four times** this rotation:
  - **A17b** added `label: str = "Letter"` to `_parse_letter_payload` — an optional kwarg whose default *is* the existing behaviour, so the letter call sites stayed **byte-identical** and the diff itself proves letters are unchanged.
  - **A18b** made `_log_safety_event` a delegating wrapper with an **unchanged signature**, so the three chat call sites needed no edit. Its docstring says it outright: *"guaranteed by the diff not touching them, not by anyone re-reading them."*
  - **A18 / A18-monthly** put **one** definition of "ritual activity" behind both the cron eligibility count and the generator's quiet-week gate, so the two cannot drift into disagreeing about whether a week happened.

  A reviewer can verify "these call sites did not change" by looking at the diff. Verifying "I re-read them and they are fine" requires trusting a claim. **Prefer the change whose safety is visible in the diff over the change that is merely correct.**
- **L-03 — This shell collapses backslash-backslash inside quoted heredocs.** Any payload containing backslashes must be built with `chr(92)` or written to a file first and re-read — and followed by an **AST or syntax check**, not an eyeball. A doubled backslash silently becomes single, and the result is often still valid code that does the wrong thing. *(Separately: a heredoc large enough to write a full document exceeds this shell's spawn limit — use a file-writing tool for those.)*
- **L-04 — A masking patch is worse than the bug it hides** *(carried from the never-merged v25, re-confirmed twice this rotation with new evidence)*:
  - **The original instance:** the history window returned the oldest N messages for as long as the feature existed. An earlier patch appended the newest user turn "for the window-cutoff case", which made turn N+1 look correct and converted legible amnesia into confident accusation. Locally reasonable, globally harmful.
  - **Re-confirmed by A17's silent-loss family:** **four** JSON parse sites shared one defect; **one** produced the observed symptom; A17 fixed the letter family and left **two siblings** live, closed only by A17b. The symptom is not the bug — it is the one place the bug happened to become visible.
  - **Re-confirmed prospectively by A18c:** two ring-true surfaces write unchecked notes; **one** was reported. Fixing only that one would reproduce the pattern a third time inside a single rotation. **When you find the site, count the family before you fix the site.**
- **L-05 — "Unchanged." is not evidence** *(carried, and this rotation is its proof)*. Every claim in this file states its method or marks itself unverified. Section 0 shows what the alternative costs: a document that catalogued six copied-forward claims was itself never merged, and made a false claim about a PR that did not exist. **A doc claim repeated without re-verification is a claim about the previous doc, not about the system** — and a doc claim about the *future* cannot be verified at all.
- **L-06 (NEW) — verify the delivery, not just the write.** Three defects this rotation (A17, A18, A8) share a shape: the system reported success, or reported nothing, while the user received nothing. `j_failed=0` on a lost letter. A zero-letter dispatch on the most active week on record. A weekly letter delivered to an account its owner did not know she had. **All three were found by querying data. None were found by a person using the app.** Nothing currently watches whether letters arrive.

---

**End of PROJECT_STATE v25.** Authoritative as of 2026-08-18 at `cace1016`. Supersedes `PROJECT_STATE_v24.md` (preserved byte-identical as historical reference). Replaces the never-merged `docs/v25-rotation` draft, which was mined for re-verifiable claims and not merged. Where this file conflicts with v24 or earlier, this file wins.
