# The Listening judge on B3 Sonnet — the first real run

**2026-09-23.** All **110** B3 Sonnet replies (77 standard, 33 deep), one call
each, **0 parse failures**, **$0.9672** against a ~$1.17 estimate. Model
`claude-opus-5`, thinking disabled, no temperature. Rows: `listening_full.csv`.

Run in two passes — the first judged only the 77 standard-mode replies, because
the CLI's default path excluded deep. The `--mode` flag exists now so that
"110" cannot silently mean 77 again.

---

## The five rates

| | n | (a) concealment | (b) sealing | (c) oracular | (d) responds | (e) misattribution |
|---|---|---|---|---|---|---|
| **ALL** | 110 | **62%** | 6% | **57%** | 100% | 4% |

*(d) is not reported as an indicator, per the calibration ruling: 110/110 yes,
zero variance. It is measuring the corpus, not the product.*

## Per persona

| persona | n | (a) | (b) | (c) | (e) |
|---|---|---|---|---|---|
| marcus_aurelius | 10 | **90%** | 0% | 70% | 10% |
| simone_de_beauvoir | 10 | **90%** | 0% | 50% | 0% |
| oscar_wilde | 10 | 80% | **30%** | **90%** | 0% |
| carl_jung | 10 | 70% | 20% | 80% | 10% |
| epictetus | 10 | 70% | 10% | 30% | 0% |
| lao_tzu | 10 | 50% | 0% | **90%** | **20%** |
| niccolo_machiavelli | 10 | 50% | 0% | 40% | 0% |
| sigmund_freud | 10 | 50% | 0% | 50% | 0% |
| socrates | 10 | 50% | 10% | 30% | 0% |
| george_orwell | 10 | 40% | 0% | 50% | 0% |
| miyamoto_musashi | 10 | 40% | 0% | 50% | 0% |

---

## THE ANSWER TO THE QUESTION ASKED: concealment is SPREAD, not concentrated

**All 11 personas show it.** The range is 4–9 hits of 10. The top three personas
hold 38% of the hits where an even spread would be 27% — a lean, not a
concentration. Chi-square across the eleven: **χ² = 15.10, df = 10, against a
critical 18.31 at p=0.05 — the personas do NOT differ significantly.**

**So this is not a persona problem and cannot be fixed persona by persona.** It
is a property of the shared directive, which is where a fix has to go.

## THE REAL CONCENTRATION IS DEEP MODE, AND IT IS SEVERE

| | standard (n=77) | deep (n=33) | |
|---|---|---|---|
| (a) concealment | 53% | **82%** | z=+2.83, **p=0.005** |
| (c) oracular | 49% | **76%** | z=+2.57, **p=0.010** |
| (b) sealing | 6% | 6% | ns |

**Four in five deep replies tell the person something about their inner state.**

This was not looked for and it is the most actionable thing in the run. The DEEP
directive asks for exactly this — *"Go materially deeper: connect the person's own
details, develop an interpretation, or move toward a conclusion their words
reasonably support"* — while the same block carries the concealment ban two
sentences later. **The two instructions pull against each other, and on the deep
path the "go deeper" half is winning.**

Deep mode is also the path already known to be worst on length: 31 of 33 replies
over the reflective ceiling on Haiku, and the one place three copies of the
ceiling changed nothing (H1/H2). It is now the worst path on two independent
instruments.

## Where the two aphoristic personas sit

Oscar Wilde 90% and Lao Tzu 90% on (c) are the highest, and both are personas
whose voice is aphoristic by design. **The judge cannot tell "oracular" from "in
character" and was never asked to** — the rubric wording is "shaped to be
quotable rather than said to this particular person", which is a real distinction
but a fine one. Before any action on (c), those two need a founder read: if
Wilde's epigrams are the product working, the metric needs a per-persona
expectation rather than one threshold.

Wilde is also the only persona with a notable (b) sealing rate, 30% against a 6%
corpus average.

## (e) misattribution, 4%

Four hits, in lao_tzu (2), marcus_aurelius (1) and carl_jung (1). Low, and
**likely an under-count**: the calibration's founder-adjudicated split showed one
call catching a true misattribution the other missed, and κ for (e) is +0.66, the
lowest of the five. It fires without any profile present — a reply can invent an
attribution from nothing — which overturned the pre-run prediction that it could
not. The production defect it was written for (PROMPT-002, a profile cited as
speech) still cannot appear on harness data.

---

## What this run does NOT establish

- **No threshold.** There is no prior run to compare against; these are the first
  Listening numbers that exist. 62% concealment is a baseline, not a regression.
- **Nothing about Haiku.** Sonnet only.
- **Nothing about arm B or the baseline.** Judging those would say whether B3
  made concealment better or worse, and would cost ~$1 each.
- **(d) remains uninformative** until a corpus with hard cases exists.

## Suggested next, for founder ruling — nothing proposed as a fix yet

1. **A founder read of the deep-mode flags.** The 27 deep replies flagged on (a),
   with quotes, to confirm the judge is seeing what the number says.
2. **Wilde and Lao Tzu on (c)** — in character, or a defect?
3. Only then, a directive question: whether the DEEP block's "develop an
   interpretation" and its concealment ban can both stand as written.
