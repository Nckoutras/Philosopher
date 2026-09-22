# Haiku directive placement — H1 and H2, and what they falsified

**Two runs, 2026-09-22.** `2026-09-22T14-28_h1` and `2026-09-22T14-30_h2`.
110 completions each, **Haiku only**, 0 errors, `git_dirty false`,
`prompt_set_hash 0a2a2d868600bb26`, `persona_config_hash be4c9e3d3d7e7959` —
both identical to arm B3, so all three arms are comparable by the manifest's own
gates. Branch `feat/evals-placement-arms`, base `fe29d361` (shipped in #702).

**Cost $0.4738 + $0.4709 = $0.9447**, against a $1.20 ceiling. Under, and this
time the projection method was the one the B3 overrun taught: expected output
tokens, not the previous run's total.

The text is byte-identical in all three arms. Only the position changes:
B3 appends the block last, H1 moves it to the top, H2 places it at top **and**
last. `tests/test_arm_placement.py` pins that by construction.

---

## THE HYPOTHESIS IS FALSIFIED, AND ITS OPPOSITE IS CLOSER TO TRUE

MODEL-001 records that "Haiku substantially ignores a directive appended last",
and the placement experiment followed from that sentence. If it were right,
moving the block to the top should have helped.

**It did the reverse. H1 is the worst of the three arms.**

| Haiku, n=110 | B3 (last) | H1 (top) | H2 (top+last) |
|---|---|---|---|
| mean words | 125.5 | **144.7** | **115.3** |
| in-band | 14% | 12% | **24%** |
| over the ceiling | 84% | 86% | **75%** |
| ends with a question | 87% | 80% | 87% |
| no opening | 6% | 2% | 2% |
| notice-family | 8.2% | 10.9% | 10.9% |
| universal lexicon | 0 | 0 | 0 |
| persona lexicon | 2 | 4 | **0** |
| modern leak | 2 | 1 | 1 |

Paired by `sample_id` — the same 110 prompts run in every arm, so the paired
test is the correct one and it has far more power than comparing two means:

| | mean diff | t | p | direction |
|---|---|---|---|---|
| B3 → H1 | **+19.1w** | +6.00 | <0.00001 | longer on 79/110 prompts |
| B3 → H2 | **−10.2w** | −4.03 | 0.00006 | shorter on 70/110 |
| H1 → H2 | **−29.3w** | −8.50 | <0.00001 | shorter on 88/110 |

**So the effect is not placement. It is REPETITION.** Being first is worse than
being last; being in both places is better than either. A single copy of the
directive is under-weighted wherever it sits, and what moved the number was
saying it twice.

## WHAT DOES NOT SURVIVE THE SIGNIFICANCE TEST, STATED PLAINLY

The **length** result is robust. The **in-band rate** is not:

| McNemar, exact, in-band yes/no on the same prompt | gained | lost | p |
|---|---|---|---|
| B3 → H1 | 12 | 14 | 0.845 — ns |
| B3 → H2 | 19 | 8 | **0.052 — misses 0.05** |
| H1 → H2 | 24 | 11 | 0.041 — significant |

**H2's headline 14% → 24% does not clear significance against B3.** It clears it
against H1. Reporting "H2 nearly doubles the in-band rate" would be reporting a
number that a second run could fail to reproduce. The honest statement is: H2
makes replies reliably shorter, and the in-band rate follows in the same
direction without yet being distinguishable from noise at n=110.

## DEEP MODE IS STILL BROKEN, AND PLACEMENT BARELY TOUCHES IT

| deep, n=33 | B3 | H1 | H2 |
|---|---|---|---|
| mean words | 174.4 | 197.7 | 165.4 |
| over the reflective ceiling | 31/33 | 31/33 | **28/33** |

The deep path already carries two length sentences by decision, and H2 gives it
a third — all three citing the same ceiling. **Three copies still leave 28 of 33
replies over it.** Whatever is wrong with Haiku on deep mode is not a
dosage problem, and no further repetition arm is worth running.

## WHAT THIS DOES NOT SAY

- **It is not a proposal.** No production change is implied. H2's win is a
  measured 10 words on the free path, and the free path's length policy is
  deferred until there are users to measure (MODEL-001).
- **Sonnet was not re-run** and is not affected. Its numbers are locked at B3's
  76% in-band; the Pro path shipped in #702 and nothing here touches it.
- **Even H2 is far below Sonnet.** 24% against 76%. Placement and repetition
  move Haiku a little; they do not make it obedient.
- **The notice-family rate got WORSE in both arms** (8.2% → 10.9%), which is a
  second instance of the B3 finding that the prompt-level ban behaves
  differently on Haiku than on Sonnet. Not chased here.

## THE CORRECTION THIS OWES MODEL-001

MODEL-001's sentence — "Haiku substantially ignores a directive appended last" —
should now read: **Haiku under-weights a single copy of the length directive
wherever it is placed, and the LAST position is better than the first.** The
original sentence was an inference from one arm's position; H1 is the experiment
that tested it directly, and it came out the other way.

That correction is the return on ~$0.94. It is also the second time in this
sequence that a plausible reading of a metric survived until somebody ran the
arm that could falsify it — the first being "the free tier breaks the voice",
which the blind read killed.
