# Arm B3 — result, and the three rulings that passed it

**Run `2026-09-22T12-59_b3`.** 220 completions, 0 errors, `git_dirty false`,
`prompt_set_hash 0a2a2d868600bb26`, `persona_config_hash be4c9e3d3d7e7959`,
`arm_directive_hash 7965ddb987428b8a`, git `8902fe22` on `feat/b2-clean`.

**Cost $1.3698 — over the $1.30 ceiling by $0.07.** Cause was output tokens:
Sonnet's mean reply went 64.3 → 93.8 words, which the wider bands made
foreseeable and nobody projected. Founder ruling: noted, no action, and future
ceilings are to be projected from expected output tokens rather than from the
previous run's total.

---

## B vs B3, Sonnet judged

| metric | arm B | B3 | Δ |
|---|---|---|---|
| mean words | 64.3 | 93.8 | +29.5 |
| **in-band** | 57% | **76%** | **+19** |
| ends with a question | 88% | 86% | −1.8 |
| no question | 7% | 8% | +0.9 |
| no_opening | 4% | 2% | −1.8 |
| stance narrow | 14% | 7% | −6.4 |
| stance any | 42% | 43% | +0.9 |
| **notice-family** | 12.7% | **6.4%** | **−6.4** |
| universal lexicon | 1 | **0** | |
| persona lexicon | 2 | 2 | |
| anti-flex | 0 | 0 | |
| modern leak | 1 | 2 | |

Haiku, reported not judged: mean 104.0 → 125.5, **in-band 43% → 14%**,
notice-family 6.4% → **8.2%** (up), deep-mode mean 144.4 → 174.4 with **31 of 33
over the reflective ceiling**.

---

## The three rulings (founder, 2026-09-22)

**1. The 30% stance-family stop does NOT trigger.** `direct_claim` reached 47% of
Sonnet's stance hits, over the 30% threshold — but that threshold was written to
catch a NEW replacement tic produced by the ban. `direct_claim` is a
pre-existing grammatical category, at 38% before the ban and 44% on Haiku, not a
phrase formula. No further stance-family chasing.

*Worth keeping in view for whoever writes the next stop condition: as written it
fired on something it was not aimed at, and it would have fired on arm B too.*

**2. notice-family 6.4% against a 5% target is a PASS** — the gap is 1.4 points,
which is one reply on n=110.

**3. Haiku is accepted as-is for this ship and does not block.** It ignored the
old band too; 104 → 125 is drift, not regression. The directive-placement
experiment (same directive at the TOP of the system prompt, and a top+last arm)
moves to **immediately after the production PR**, and its success criteria
include deep-mode mean against the reflective ceiling — currently 174 words with
31 of 33 over.

**B3 PASSES the decision rule.**

---

## What the ban actually did

The notice-family ban is the first prompt-level *forbidden phrase* tried on this
problem, after two directive-wording attempts moved it not at all:

| | Sonnet | Haiku |
|---|---|---|
| baseline | 3.6% | 4.5% |
| arm B | 12.7% | 6.4% |
| arm B2 | 12.7% | 6.4% |
| **B3 (banned)** | **6.4%** | **8.2%** |

**Sonnet halved. Haiku rose.** B2 had struck the example wordings from the
directive specifically so "What I notice" would stop being example one, and the
rate was identical to the reply — which is what made the ban worth trying. The
split result is consistent with MODEL-001's line, except that this instruction
sits mid-prompt in `DO NOT USE:` rather than appended last, so "Haiku ignores
late directives" does not fully explain it.

---

## Next, in order

1. **blind3** — `blind3_pairs.md` and `blind3_pairs_swapped.md`, 11 Sonnet
   standard-mode pairs, B vs B3. Founder reads each in **its own fresh chat**;
   reading both in one chat is what contaminated blind2 reading 1.
   **Gate: NEITHER = 0, and arm-B preference not greater than 14:8.**
2. **The one production PR** from `feat/b2-clean` — full diff, parity test
   against the shipped prompt, the test literals listed, P-04 smoke on merge.
3. **The Haiku placement experiment.**
4. **The Listening judge**, which builds after the PR merges.
