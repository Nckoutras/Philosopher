# Arm E — the hypothesis held, the gate failed by two instances, and it shipped anyway.

**2026-09-23.** 77 Sonnet standard replies, all 11 personas, arm `e`, bridge on,
0 errors. Shape clauses 1 and 3 removed; clause 2's hedge kept **verbatim**. Judged
for distinctiveness (154 judgements, 92% self-agreement) and density (77, 0 parse
failures). Control and arm D judgements reused unchanged.

| | |
|---|---|
| generation | $0.5868 |
| distinctiveness | $0.7153 |
| density | $0.4436 |
| **total** | **$1.7457** (estimate $1.72, ceiling $2.20) |

`persona_config_hash` `23cf9ac6c6ca0cb3` on all three sides; `arm_directive_hash`
control `7965ddb987428b8a` → D `fb648d7bb909ae0a` → E `e45badf3494b09f7`.

---

## FOUNDER OVERRIDE, 2026-09-23 — ARM E SHIPPED

**The decision rule below was applied as written and returned "ship nothing". The
founder then overrode it, and shipped arm E.** Both the rule's verdict and the
override are kept here; the verdict is not edited away, because the override is only
legible beside the thing it overrode.

> *"The 10% gate was mine, set arbitrarily; arm E missed it by 1.3 instances on a
> measure with one read per reply and p=0.453. It dominates both the control and arm
> D on both axes. Refusing a real gain over a non-significant miss serves the
> threshold, not the product."*

**The arithmetic the override rests on.** The gate permitted 1.848 (a)-instances per
100 words; over arm E's 6,100 words that is **112.7 instances**. Arm E returned
**114**. **It would have passed at 112.** The (a) difference from control is
**p = 0.453** on a single read per reply — a measure with no reliability figure at
all, because the density protocol is one call.

Against that: the three previously-unnameable personas went from **1 naming in 154 to
15 (p = 0.0004)**, no column was left empty, and (a) came in *below* arm D while
distinctiveness came in *above* it.

**What shipped:** arm E's `FIRST_MESSAGE` text, into
`services/reply_directive.py`. **`STANDARD` and `DEEP` are untouched — and also
unmeasured.** They carry their own shape clauses in different wording, and no arm has
ever exercised them, because every §8.2 sample is a first message. They are kept
because nothing tested them, not because they tested well.

**`arm_b3.FIRST_MESSAGE` was frozen as an inline literal in the same change.** It had
been a re-export of the production string; leaving it so would have silently
redefined `--arm b3` to generate arm E's replies under B3's name, with nothing
failing. This is convention C-01 applied to an eval arm.

---

## The rule as it stood, and what it returned

The rule, set before the run:

> *the three dead personas named at a rate ≥ arm D's **AND** (a) density within 10%
> of control → ship. Otherwise → ship nothing; §8.2 closes.*

| condition | result | |
|---|---|---|
| three dead personas named ≥ arm D | **15 vs 10** | **PASS** |
| (a) density within 10% of control | **+11.3%** (allowed +10%) | **FAIL** |

**The rule returned: ship nothing.** That verdict was overridden the same day — see
the section above. It is preserved here as written.

---

## The hypothesis was right, and it was not enough

Arm E was built on a single prediction: that the distinctiveness gain came from
shape clauses 1 and 3, and the (a) cost from clause 2's hedge. **Both halves held.**

| | control | arm D | **arm E** |
|---|---|---|---|
| recognition, all 11 | 23/77 — 29.9% | 29/77 — 37.7% | **32/77 — 41.6%** |
| **3 dead personas, named** (of 154) | 1 | 10 | **15** |
| Socrates marginal | 32% | 19% | **19%** |
| names never proposed | Marcus, Lao Tzu | none | **none** |
| **(a) / 100 words** | **1.68** | 2.01 (+19.6%) | **1.87 (+11.3%)** |
| (c) / 100 words | 1.16 | 1.23 | 1.23 |
| replies containing any "?" | 96% | 79% | 82% |
| median words | 78 | 79 | 77 |

**Arm E dominates arm D on both axes at once** — more of the dead personas named
(15 vs 10) *and* less over-interpretation (1.87 vs 2.01). Putting the hedge back
recovered roughly **42% of arm D's (a) regression** while *improving* rather than
costing distinctiveness. Restoring the hedge did not restore the Socrates attractor
(19% in both arms), which is the clean confirmation that clause 3 — not clause 2 —
was what built it.

**Arm E vs control on the dead personas: 1 → 15 of 154, Fisher p = 0.0004.** That is
the strongest single result in this investigation.

---

## The gate failed by two instances, and the measure it failed on is noise

Stating this plainly because the rule was applied as written and the margin is
small enough that a reader will want the number:

- Threshold: 1.68 × 1.10 = **1.848 per 100 words**. Over arm E's 6,100 words that
  permits **112.7 instances**.
- Arm E returned **114**. It is over by **1.3 instances**, and would have passed at
  **112**.
- The (a) difference from control is **p = 0.453** — the judge found 101 instances
  in the control and 114 here, and that difference is not distinguishable from
  sampling noise on a single read per reply.

**The rule was fixed in advance precisely so this call would not be made after
seeing the numbers, and it has been applied as written.** The margin is recorded
here so the decision can be revisited deliberately, as a decision, rather than
re-litigated inside a report. Two things would change the answer and neither is
available today: a density measure with more than one read per reply (the current
protocol is 1 call, so there is no reliability figure on it at all), or a larger n
than 77.

---

## What §8.2 established, and what it did not

**Established:**

- BUG-009's acceptance test is met at the system level — recognition is 3–4× chance
  — but its diagnosis was wrong in particulars. Beauvoir, named in the bug as
  absent, is among the best recognised; Freud, named as one of the only two
  recognisable, is mid-table.
- The failure is **collapse, not absence.** Three personas (Marcus, Lao Tzu,
  Musashi) were never proposed at all in 220 judgements, and three names absorbed
  73% of all guesses.
- **Persona-level repair does not fix it.** Marcus received the strongest available
  persona change and moved 0/10 → 0/10, relocating from one attractor to another.
- **The shared directive is a real cause, and the effect is large and specific.**
  Removing two shape clauses took the three dead personas from 1 naming in 154 to
  15, emptied no column, and left the other eight personas unmoved.
- The cost of doing so is a rise in over-interpretation that this instrument cannot
  resolve at n=77.

**OPEN AND DEFERRED — §8.2 closes with these three explicitly unresolved.** Founder
ruling 2026-09-23. They are deferred, not answered, and not closed:

1. **The (a) rise is unresolved at n=77.** Arm E's over-interpretation is 11.3% above
   control at p=0.453, measured on a single read per reply. It could be a real
   regression the run was too small to confirm, or noise. **Resolving it needs a
   density protocol with more than one call per reply — there is currently no
   reliability figure on that measure at all — or a larger n.**
2. **`STANDARD` and `DEEP` carry their own shape clauses, untested.** They prescribe
   a shape in different wording from `FIRST_MESSAGE`, and **no arm has ever exercised
   them**, because every §8.2 sample is a first message. They ship unchanged because
   nothing measured them. `tests/test_shipped_directive_is_arm_e.py` pins their shape
   clauses so this stays visible rather than being assumed handled.
3. **No human has read arm E's replies.** 92–94% judge self-agreement is internal
   consistency, not correctness. The whole result rests on one LLM judge that nobody
   has checked against a person on this corpus.

**Also true, and not a deferral:** retrieval is not a variable anywhere in this. Every
reply in every arm was generated with `passages=[]` (RETRIEVAL-001).

**The arms remain in the harness.** `arm_d.py` and `arm_e.py` ship as eval code
with their results stored, so re-opening this needs a decision and a run, not a
reconstruction.
