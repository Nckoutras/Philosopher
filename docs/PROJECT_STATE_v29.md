# GREAT MINDS — Project State v29

> **Range covered:** `#616` … `#632` (17 squash-merges on `main` since `e840053c`).
> **Verification SHA:** `93aa06932de12a03c4c523f47733bf9897c44d0f`.
> **Date:** 2026-09-11.
>
> Backend and web measurements were both taken at `93aa0693`. Every number below was
> executed at that SHA, not carried.
>
> **This rotation's own PR number is deliberately not asserted.** The range above is
> what is on `main`.
>
> **Companion documents:** `IMPLEMENTATION_BACKLOG_v29.md`, `HANDOFF_BRIEF_v29.md`,
> `reports/STRATEGY_P2_RETENTION_2026-09.md` (updated in place). v28 files are
> preserved byte-identical.

---

## ⚠️ PROVENANCE

**Every claim below is either VERIFIED THIS ROTATION with its method stated inline,
or explicitly marked FOUNDER-REPORTED.** "Unchanged." is not evidence and is not used
as such. Every carried backlog item was re-verified against the code before being
written.

**Methods used this rotation:** `pytest -q`, `vitest run` and `tsc --noEmit` executed
at `93aa0693`; `alembic heads` executed; a revision-id script over all 59 migration
files; the FastAPI app's `openapi()` generated **in-process**; `WorkerSettings`
imported and its `functions` and `cron_jobs` counted; the persona registry, the four
safety lexicon bands and the universal forbidden lexicon imported and counted; the
question bank parsed; `git ls-remote --heads`; `git log` and `git show` across the
range and against v28's own verification SHA; live source reads.

**No database, no Stripe dashboard, no Sentry project, no Render or Netlify
dashboard, no email inbox and no production logs were consulted.** Every claim that
would require any of those is marked FOUNDER-REPORTED.

**One instruction in this rotation's brief could not be reproduced** and is reported
rather than written up as a correction — see §3d. Writing a correction for a defect
that does not exist would be the exact failure the 2026-08-18 log entry describes.

---

## 1. What this cycle did

Three threads. The first is the whole of the cycle's weight; the other two are
infrastructure and hygiene.

### 1a. The language class — two production observations, six PRs, eighteen prompts

**It started as two production observations, both Indonesian.** On **2026-09-10** an
English conversation titled *"Illusion of information control"* produced an
**Indonesian council matter** twice — **mobile at 10:27** and **desktop at 10:20** —
and the two were **different sentences**. Both founder-observed in production. The
difference between them is what settled the diagnosis: the matter was being
**LLM-composed per tap**, not stored once and re-served, which is why the fix had to
be in the prompt and not in a cache.

**It was never reproduced offline**, and nothing in this class rests on a
reproduction. #626's own commit message records why: the transcript was not
available and that environment had no `ANTHROPIC_API_KEY`, so `display_brief` could
not be run even once. The guard was required on the evidence of the two observations
alone.

The council prefill is not display text: it lands in the matter TEXTAREA, so the
person submits, as their own words, a sentence they never wrote. That is what made it
a P0 rather than a cosmetic glitch.

**The cause was not a bug in a function. It was a construct.**
`COUNCIL_DISPLAY_BRIEF_PROMPT` asked the model to write "in the same language the
person used" — an instruction to **infer** — and nothing checked what came back. Two
halves, both missing: the prompt did not state a language, and no code read the
output.

**And the same construct existed in seventeen more places.** Measured at `93aa0693`:

```
grep -rn "language_directive(" --include=*.py apps/api | grep -v tests \
  | grep -v "def language_directive" | grep -v text_utils.py | wc -l
→ 17
```

Those seventeen call sites are prompts that now state a computed language and did not
before. With the display brief itself that is **eighteen prompts** in the class. The
two letter prompts were already fixed in August 2026 by the same doctrine, using a
`{language}` template field rather than an appended directive.

**The six PRs, as one shape rather than six entries:**

| PR | What it settled |
|---|---|
| **#626** | The display brief: compute the language from the person's own turns, state it, and check the answer. Wrote the function-word test. Named the rest of the class as follow-up. |
| **#627** | The three memory writers (`MEMORY_EXTRACTION`, `DISTILL_TO_MEMORY`, `SELF_PORTRAIT_SUMMARY`). Promoted `language_directive` / `language_matches` into `text_utils` so there is one detector. |
| **#628** | The dilemma that reaches an input box is **dropped** on mismatch rather than logged. Established the line: editable input blocks, display logs. |
| **#630** | Seven prompts — counterview ×3, insight mirror, You-vs-You ×3. Added `EN_MIN_TOKENS`. |
| **#631** | Seven more — weekly/preview mirror, conclusion, shift, recurrence, council synthesis, council distill, conversation title. Closed the class. |
| **#632** | Repaired a false-reject defect #630 shipped — granularity, not threshold. |

**End state, pinned by a test rather than by a sentence:**

> **No prompt in the product asks a model to infer its output language.**

`tests/test_last_prompt_language.py::test_every_prompt_in_the_product_is_enumerated_here_or_already_done`
walks `services/*.py`, `workers/*.py` and `prompts/*.jinja2` and **fails if a
prompt-bearing module appears that is not accounted for**. Executed this rotation:
passes. The claim is therefore re-checkable by running one test, rather than by
trusting this paragraph.

The chat system prompt (`prompts/system_base.jinja2`) states no language and is
listed in that test as *states none, mirrors the conversation*. That is not
inference: it says nothing, and the model answers each turn in the language of the
turn it is answering. A one-shot generator reading a whole transcript is a different
thing, and is what every defect in this class has been.

#### The three measurement lessons, each with its number

**(i) A guard built on a detector that cannot see the defect is a no-op.** Executed
at `93aa0693`:

```python
dominant_language(["Sepertinya kamu sedang bergulat dengan keputusan…"]) → 'English'
```

`dominant_language` counts Greek codepoints against Latin ones. It answers *which
script*, and calls every Latin-script language English. The first defect it had to
catch was an **Indonesian** brief for an **English** conversation — so the obvious
guard, "does the output language match the input language", compares `'English'` to
`'English'`, passes, and ships the exact string it exists to stop. The
function-word-ratio test was written because of this and nothing else: the same
Indonesian string scores **0.000**.

**(ii) `EN_MIN_TOKENS = 6` exists because short text carries no ratio signal.**
Counterview titles are 2–4 words by prompt rule. Measured:

| sample | tokens | ratio | with the threshold |
|---|---|---|---|
| `"Quiet ambition"` | 2 | **0.000** | accepted |
| `"Choosing badly"` | 2 | **0.000** | accepted |
| `"Ambition and rest"` | 3 | 0.333 | accepted |

Without the threshold, a quarter of correct English titles were nulled. The stated
cost: under six tokens only the script test runs, so a *short* Latin-script
non-English string passes.

**(iii) Calibration is per-register, and the repair was granularity, not threshold.**
#630 applied the ratio **per verdict**, and a counterview verdict is capped at 10
words in a compressed register. Measured on 15 fresh in-register English verdicts,
**3 fell below the floor — 20%**:

```
"Ambition dressed as duty exhausts everyone eventually."   0.143
"Comfort chose this; principle merely signed it."          0.286
"The convenient story flatters whoever tells it."          0.286
```

Each is correct English; each was replaced, for the reader, by *"There wasn't a clear
case to make against this just yet."* **No floor fixes it** — at that length the
distributions overlap, correct English bottoming at 0.143 and wrong-language topping
at 0.125. #632 changed the granularity instead: **script per item, ratio over the
join**. Joined, the same responses read 0.292–0.600 against 0.071. False rejects fell
to ~1%. The trade is recorded in code and in a test: one *Latin-script* wrong item
beside correct ones is diluted away — **84 of 360 such combinations blocked, so 77%
would ship** — accepted, because a whole response in one wrong language is still
caught 45/45 and that is the failure this class was built from.

### 1b. Infrastructure and trust surfaces

- **Google OAuth enabled and brand-verified** (FOUNDER-REPORTED). OPS-008 was
  verify-then-fix; the verify step distinguished "flag off" from "credentials
  missing". Closes OPS-008.
- **`api.thewiseroom.app`** (FOUNDER-REPORTED). The API now answers on the product
  domain rather than the Render host. Closes OPS-009.
- **`PUBLIC_ASSET_BASE_URL` and `FROM_EMAIL` defaults (#629).**
  `PUBLIC_ASSET_BASE_URL` defaulted to `https://thinkalike.netlify.app` — an earlier
  name for this product — and was confirmed unset on Render, so the default was live:
  every OTP email loaded its logo from that host and every future-self email printed
  the hostname to the reader as visible link text. **The root cause was absence, not
  a wrong value:** the variable appeared in no `.env.example`, no DEPLOY_NOTES row
  and no ops checklist. Verified now present in all three
  (`grep -c PUBLIC_ASSET_BASE_URL` → `.env.example` 2, `DEPLOY_NOTES.md` 1, backlog
  checklist 1).
- **The fair-use toast (#623)** and **the counterview paywall defect (#624).** Two
  caps arrive as the same 429 and only `error_code` separates them; a Pro subscriber
  hitting the cost cap was being shown the upgrade wall — selling them a tier they
  already own and filing a false `upgrade_clicked` against it. Verified:
  `apps/web/app/app/counterview/page.tsx:126` branches on
  `e.errorCode === 'fair_use_limit'` before the upgrade path, and two test files now
  exercise the rendered notice (`lib/__tests__/fairUseToast.test.tsx`,
  `app/app/counterview/__tests__/fairUsePaywall.test.tsx`). Closes TD-63.

### 1c. Hygiene closed

| Item | Method that verified the closure | Result |
|---|---|---|
| **TD-58** | `grep -nE "passlib\|bcrypt" requirements.txt`; `grep -rl` over `**/*.py` | absent from requirements; **0** importing files |
| **TD-60** | `grep -c "casefold\|unicodedata" services/postprocessing_service.py` | **2** (was 0); `.lower()`/`IGNORECASE` sites down 9 → 5 |
| **TD-61** | lexicon bands imported and counted at both SHAs | **219** entries / **76** Greek-script (v28: 210 / 73) — see §3a |
| **TD-63** | `ls` of the two new web test files | both present; the refusal path now renders in tests |
| **TD-64** | source read of `tests/db_live/test_letter_catch_up.py:353` | `committed.track("2026-W40")` — the row is now cleaned up |
| **TD-69** | `git ls-files apps/web/.env.production`; read `layout.tsx:40` | **0** tracked; fallback now `https://thewiseroom.app` |
| **26 stale branches** | `git ls-remote --heads origin \| grep -v main \| wc -l` | **0** — every one deleted. Closes NIKOS-ACTION 10. |

---

## 2. Verified state — every row executed or read at `93aa0693`

| Claim | Method | Result |
|---|---|---|
| Backend suite | `pytest -q` executed | **1716 passed, 45 skipped, 0 failed** (v28: 1099) |
| CI failure baseline | file read | **0 quarantined entries** — any red is new |
| Web unit suite | `vitest run` executed | **13 failed / 272 passed** (285); 6 failed files / 38 passed (44). The same 13 as v26–v28; passing count +24 |
| Web typecheck | `tsc --noEmit` executed | **11 errors** — unchanged |
| Alembic | `alembic heads` executed | single head, **`059_job_run`** |
| Migration naming (C-04) | script over all files in `db/migrations/versions` | **59 files, 0 length violations**; longest id `024_saved_line_conclusion_source` (**32 chars exactly**); **2** documented filename≠revision exceptions (`013`, `014`) |
| API surface | `openapi()` in-process | **93 paths / 113 operations** |
| ARQ tasks | `len(WorkerSettings.functions)` | **12** |
| ARQ cron jobs | `len(WorkerSettings.cron_jobs)` | **4** |
| ARQ timezone | attribute read | `UTC`, set explicitly |
| APScheduler jobs | `id="…"` count in `workers/cron.py` | **5** — `daily_rituals`, `stripe_reconcile`, `future_self_emails`, `weekly_mirror`, `preview_mirror` |
| Question bank | parsed | **360 / 360 weighted**, 0 unweighted |
| Personas | `PERSONA_REGISTRY` imported | **11**, of which **3** are `tier="free"` (`lao_tzu`, `marcus_aurelius`, `socrates`) |
| Persona forbidden lexicons | registry imported, `forbidden_lexicon_persona_specific` counted | **11 of 11** carry one (v28: 8 of 11) |
| Safety lexicons | four bands imported and counted | **219** entries — HIGH 95, MEDIUM 50, OUTPUT 22, LOW 52; **76** contain Greek script |
| Safety lexicon shape | source read | each band is `_EN + _GR + _GL` — the third tier is **greeklish** |
| Universal forbidden lexicon | `len(_UNIVERSAL_PHRASES)` | **210** phrases across **12** categories (v28: 123) |
| Prompts stating a computed language | `grep -c language_directive(` (non-test) | **17** call sites, plus the `{language}` field in the display brief and both letters |
| The enumeration test | `pytest` executed | `test_every_prompt_in_the_product_is_enumerated_here_or_already_done` **passes** |
| Live-DB tests | `pytest tests/db_live --collect-only -q` | **45 tests** across 4 files |
| Stale-`running` threshold | source read | `STALE_RUNNING_AFTER = timedelta(hours=2)` |
| Free daily ceiling | source read + registry count | `FREE_DAILY_LIMIT_PER_PERSONA = 5` × 3 reachable personas = **15/day**; `PRO_DAILY_FAIR_USE_LIMIT = 150`; a grep for `monthly_limit\|FREE_MONTHLY\|per_month` returns **nothing** |
| Upgrade page price | source read | still displays **"€99.99 / year"** |
| Greek crisis number | `grep -c 1018 prompts/safety_response_el.jinja2` | **0** — still country-neutral |
| `.env.production` | `git ls-files` | **untracked** (TD-69) |
| `metadataBase` fallback | `layout.tsx:40` read | `https://thewiseroom.app` |
| `_is_null_reply` callers | grep, non-test | **0 production callers** — definition + one docstring mention only |
| Insight→counterview route | `grep -c "rate_limit\|check_limit\|fair_use" routers/memory.py` | **0** — still uncapped |
| Remote branches | `git ls-remote --heads origin` | **1** — `main` only |

### ⚠️ FOUNDER-REPORTED — not verified by this rotation

Recorded because the founder observed them. This document checked none of them.

1. **Google OAuth is enabled and the brand is verified** in production.
2. **`api.thewiseroom.app` serves the API.**
3. **The two original observations** — 2026-09-10, an English conversation titled
   *"Illusion of information control"* producing an **Indonesian** council matter on
   mobile at 10:27 and on desktop at 10:20, with **different sentences** each time.
   Both in production. This document did not see either; it records that the founder
   did, and the per-tap difference between them is the evidence that the matter is
   composed per request rather than stored.
4. **`FROM_EMAIL` set on both services (2026-09-07); OTP and future-self email
   deliver from `hello@thewiseroom.app`.**
5. **The worker and API are deployed** at a post-#632 SHA.
6. **Migrations `055`–`059` are applied on production** (`alembic_version` not read).
7. **Sentry is initialised in production.**
8. **OPS-006**: €149 was charged against a locked price of €99.99. Test-mode closed;
   live-mode pending.
9. **`BETA_GRANT_PRO_TO_ALL`'s production value on Render.** Defaults `False`.
10. **The "1.85× the heaviest usage day" figure** behind the fair-use cap — measured
    against the production database in #11's Step-1, **not re-read since**.
11. **The audience decision of 2026-09-11** — see §3c.

**The Sunday 2026-09-13 run is deliberately NOT in this list.** It has not happened.
See `HANDOFF_BRIEF_v29` §1, which carries the queries and an explicitly empty result
placeholder.

---

## 3. Corrections to prior docs

### 3a. Safety lexicon: 210 / 73 → **219 / 76**, and the bands were re-cut

v28 reported **210 entries, 73 Greek-script**. Both were correct at v28's SHA —
verified by extracting `services/safety_lexicons.py` at `e840053c` and counting it
the same way as HEAD. At `93aa0693` the figures are **219 / 76**.

The net is +9, but the change is not additive. TD-61's native review **re-banded**:

| band | v28 | v29 | change |
|---|---|---|---|
| HIGH | 88 | **95** | +7 |
| MEDIUM | 59 | **50** | −9 |
| OUTPUT | 33 | **22** | −11 |
| LOW | 30 | **52** | +22 |

MEDIUM false positives moved down to LOW and generic OUTPUT phrases were removed
(#618), then Greek entries were added (#622). A reader who saw only "+9" would
conclude nine phrases were appended and nothing else moved, which is wrong about
three of the four bands.

**Also corrected:** each band is `_EN + _GR + _GL`. The third tier is **greeklish** —
Greek typed in Latin characters. v28 did not name it, and it matters because
`dominant_language` reads greeklish as English by design, so those entries are the
only thing covering a greeklish typist.

### 3b. Universal forbidden lexicon: 123 → **210**; personas 8/11 → **11/11**

`len(_UNIVERSAL_PHRASES)` is **210** across 12 categories, not 123 (TD-60 part 2,
#622). And every persona now carries a persona-specific forbidden lexicon:
`forbidden_lexicon_persona_specific` is set on **11 of 11**. v28 recorded 8 of 11,
naming `lao_tzu`, `niccolo_machiavelli` and `oscar_wilde` as the three without. All
three now have one.

**Note the attribute name.** It is `forbidden_lexicon_persona_specific`, not
`forbidden_lexicon`. A count taken against the wrong attribute returns 0/11 and reads
exactly like a catastrophic regression. This rotation made that error before catching
it, and records the correct name so the next measurement is the same measurement.

### 3c. ⚠️ The "Greek-first audience" premise is FALSE

**This is the correction most likely to mislead the next reader, and it invalidates
the framing — not the content — of several carried items.**

**FOUNDER DECISION, 2026-09-11: the target audience is English-speaking.** Greek
support remains as a **safety net**, not as go-to-market.

The premise appears in the v28 documents in two places, both now superseded:

- `HANDOFF_BRIEF_v28.md:199` — *"for a product whose first audience is Greek"*, in
  the TD-61 standing risk.
- `IMPLEMENTATION_BACKLOG_v28.md:97` — *"persona-voice enforcement silently does
  nothing for the product's first audience"*, in TD-60.

Both sentences were **the justification for the priority**, not for the work. The
work in each case was correct and has landed. What changes is how the next reader
should rank anything similar: **Greek coverage is no longer the highest-value axis it
was presented as.** TD-61's native review is done and its value was real; a future
"we should also do X for Greek" argument no longer inherits first-audience priority
from these documents.

The decision is recorded in code, not only here, at three sites verified this
rotation:

- `services/self_portrait_summary.py:274` — *"the bank is English by design (founder
  decision 2026-09-11)"*
- `services/self_comparison_service.py:77` — the same decision, cited for why
  `forming_reflection` takes its language as an argument
- `tests/test_memory_language_guard.py:37` — *"the audience is English-speaking and
  that copy is correct. No Greek set, no migration."*

**What does NOT change:** the safety lexicons stay (a distressed Greek speaker is a
safety case regardless of go-to-market), `safety_response_el.jinja2` stays, UX-02
stays blocked on its own terms, and **the language class was never about Greek at
all** — both observed production defects were **Indonesian** output for **English**
input. Greek enters this class only as the *other direction* the guard must catch,
and it is the direction the script test covers for free at any length. No
Greek-language defect was ever observed.

### 3d. The brief's PR-citation correction could not be reproduced

The rotation brief asked for a correction reading *"v28 cited a PR number for the
memory guard that does not exist on `main`"*. **Checked and not reproducible.**

Method: every `#NNN` citation in all three v28 documents extracted and tested against
the set of PR numbers in `git log --format=%s`:

```
PROJECT_STATE_v28.md      30 PR numbers cited, 0 not on main
IMPLEMENTATION_BACKLOG_v28.md  11 cited, 0 not on main
HANDOFF_BRIEF_v28.md       9 cited, 0 not on main
```

Widened to every `.md` under `docs/`: **0 files** cite a PR number ≥ 400 that is
absent from `main`. The memory-guard PRs are `#627` (`31a21d6f`, *"Fix/memory
language guard"*) and `#628` (`545777d1`), both present — and both landed *after*
v28, so v28 could not have cited them.

**No correction is written for it.** Inventing one would be precisely the failure the
2026-08-18 log entry describes.

**Resolved after the check: the instruction's source was this rotation's own brief,
not any v28 document.** The missing `#628` reference was in the brief text, and the
founder accepted that on review. So there is **no doc defect here to hunt for** — a
future reader who sees this section should not go looking for one. What the episode
actually establishes is the method: extracting every `#NNN` from `docs/` and testing
it against `git log --format=%s` is cheap, and it answers the question in one command
rather than by recollection.

**The content-not-title rule is restated anyway, with a real instance from this
cycle.** Squash merges rewrite the SHA, so an ancestry check cannot answer whether
work landed. This rotation met that twice:

- Both `fix/remaining-prompt-language` (#630) and `fix/last-four-prompt-language`
  (#631) were refused by `git branch -d` as *"not fully merged"* **after** they had
  merged. Deletion required `-D`, and the safe check was `git diff main <branch>`
  returning empty plus a marker grep on `main` — not the branch pointer.
- Each rotation brief's base check was done the same way: #631 confirmed #630 by
  `grep -c EN_MIN_TOKENS text_utils.py` and by running #630's test file, not by
  reading the merge title.

### 3e. #626's own follow-up enumeration listed a file with no prompt

#626's commit message named the remaining members of the class and included
**`quote_suggest.py`**. It has no prompt: `services/quote_suggest.py` is 67 lines of
theme ranking, with no `llm_client` import, no `system=` argument and no I/O at all.
Verified by reading the file. It was removed from the enumeration in #630 and is
recorded here so the claim is not carried into a fourth document.

---

## 4. Lessons — only the ones that changed behaviour

1. **A guard built on a detector that cannot see the defect is a no-op that reads as
   a fix.** `dominant_language` returns `'English'` for Indonesian. An OUT guard
   comparing input language to output language would have shipped the exact string it
   was written to stop, and would have looked like protection in review.
2. **Calibration does not transfer across registers.** The 0.30 floor was measured on
   multi-sentence briefs (0.536–0.733). Applied to 10-word aphoristic verdicts it
   rejected **20%** of correct English. The samples that validate a threshold have to
   come from the surface it will run on.
3. **The check must sit where the object is selected, not after it.** #628's dilemma
   guard was first written after selection; a mismatching dilemma would take the slot
   and then be discarded, and the Greek belief behind it would never be reached. The
   test moved **inside** the candidate loop, twelve lines earlier.
4. **A variable absent from `.env.example`, the deploy notes and the checklist will
   never be set.** `PUBLIC_ASSET_BASE_URL` was invisible, not forgotten — zero
   mentions across all of `docs/`. It survived because its wrong default *succeeded*:
   the old host still answered 200, so nothing 404'd and nothing was logged. **A
   default that quietly succeeds at the wrong thing is worse than one that fails.**
5. **Encoding: any Greek content sent to an executing agent goes base64 with a
   sha256.** The C1 byte range was silently dropped once this cycle. A transport that
   corrupts a lexicon entry produces a safety gate that passes its tests and misses
   the phrase it was written for.
6. **`git check-ignore` reports nothing for a tracked file.** `.gitignore`'s `.env.*`
   rule only ignores *untracked* files, which is why `apps/web/.env.production` sat
   tracked for months while the ignore rule read as covering it (TD-69).
7. **"always" in a PR description is a claim with a history.** `git log -S` the
   phrase before repeating it. Several claims in this cycle's briefs were inverted
   from what the code did — the mirror's "both roles" premise among them (§1a of
   `HANDOFF_BRIEF_v29`).

---

## 5. What is not in this document

The open backlog, with every item re-verified, is in `IMPLEMENTATION_BACKLOG_v29.md`.
The Sunday 2026-09-13 run — which has **not happened** — has its section, its queries
and an explicitly empty result placeholder in `HANDOFF_BRIEF_v29.md` §1. The P2 build
order, re-locked 2026-09-11 with the epistemic loop inserted at position 2, is in
`reports/STRATEGY_P2_RETENTION_2026-09.md`.
