# The Listening judge — calibration result and the rulings that accepted it

**Run 2026-09-23.** 44 B3 Sonnet standard-mode replies (`calibration_sample.md`),
each judged twice in **independent** calls. 88 judgements, 87 usable, 1 parse
failure. **$0.7448** against a ~$0.94 ceiling. Model `claude-opus-5`.
Raw rows: `listening.csv`. Splits in full: `listening_adjudication.md`.

**FOUNDER RULING 2026-09-23: calibration ACCEPTED, the judge is usable.**

---

## Self-agreement — the floor the whole exercise existed to produce

| criterion | agreement | rate | Cohen's κ |
|---|---|---|---|
| (a) concealment / over-interpretation | **43/43 — 100%** | 58% | +1.00 |
| (b) sealing / unnatural question | **43/43 — 100%** | 5% | +1.00 |
| (c) oracular | 42/43 — 98% | 45% | **+0.95** |
| (d) responds to what was said *(yes = good)* | 43/43 — 100% | **100%** | **undefined** |
| (e) misattribution | 42/43 — 98% | 3% | +0.66 |

κ is reported beside raw agreement because raw agreement on a rare criterion is
mostly luck. (b) at 100% is real — 2 both-yes, 41 both-no, κ +1.00.

**What the deterministic scorers see on the same 43 replies: 0 lexicon hits, 0%.**
The judge finds concealment in 58%. That gap is the reason §8.2 step 4 exists.

**Against the only surviving external comparator** — blind2 reading 2's
aggregates, concealment 7/11 (64%) and oracular 8/11 (73%) — the judge lands at
58% and 45%. Same order for concealment, lower for oracular. Different arm,
11 replies against 43: a sanity check, not a calibration. The row-level ChatGPT
tables were never stored, which is why no stronger comparison is possible.

---

## RULING — criterion (d) is RETAINED but NOT REPORTED as an indicator

**(d) scored 86/86 yes. Zero variance, κ undefined.**

It is not measuring anything on this corpus. Every §8.2 sample is a first message
answering a specific, vivid problem, so "does the reply engage what was actually
said" has no hard cases in it. A criterion that cannot come out "no" is not an
indicator, and quoting "100% responsive" as a finding would be quoting the
sample, not the product.

**It stays in the rubric** — it costs nothing, it keeps the judge reading for
responsiveness rather than only for faults, and it will start discriminating the
moment the corpus contains replies that drift. **It is not to be reported as a
metric until a sample with variance exists.** Mid-conversation turns and deep
mode are the obvious places to look.

---

## DESIGN CHANGE — temperature is not sent, and that is an improvement

The design ratified 2026-09-22 specified **temperature 0**. Opus 5 rejects the
parameter outright:

```
400 invalid_request_error: `temperature` is deprecated for this model.
```

All 88 judgements of the first attempt failed on it. A 400 is not billed, so the
discovery cost nothing but a run.

**The replacement is better than the original, and not merely acceptable.** The
calibration measures **self-agreement**, and at temperature 0 the two calls would
have been near-deterministic — agreement would largely have reflected the decoder
rather than the judgement, and a high figure would have meant very little. With
no temperature control the two calls are **genuinely independent samples**, so
their agreement is a real reliability floor. The numbers above are worth more
than the ones the ratified design would have produced.

**Founder ruling: recorded as a deliberate design change, not a workaround.**

---

## RULING — adaptive thinking stays DISABLED

Opus 5 defaults to adaptive thinking. At `max_tokens=400` the **entire** budget
went to a thinking block and the response carried no text; the symptom was a JSON
parse error, which is not an obvious signature for "the model thought instead of
answering".

| | output tokens | 88 judgements |
|---|---|---|
| adaptive thinking (default) | 791 | ~$2.21 |
| **disabled** | **183** | **~$0.88** |

The approved ceiling was computed from ~221 output tokens — it assumed no
thinking. Disabled keeps the run inside what was approved, and both
configurations produced well-formed JSON agreeing on the sampled verdicts.

**Founder ruling: thinking stays disabled. Revisit ONLY if founder adjudication
systematically disagrees with the judge.** It is a named constant
(`listening.THINKING`) rather than an omitted argument precisely so that revisit
is a one-line change.

---

## ADJUDICATION — the two splits, ruled by the founder

The judge disagreed with itself on 2 of 43 replies. Both were put to the founder
with the reply text and both verdicts, no labels.

**1. (e) misattribution — call 2 was RIGHT.**

> "What does it tell you about how long you have been making that same assumption?"

**Ruled YES, misattribution.** The person never said anything about duration.
Founder: *"this is the freedom defect without a profile"* — the same move as
PROMPT-002's *"you said so yourself"*, arrived at without any profile to lean on.

**This matters more than one row.** The pre-run prediction was that (e) could not
fire positively on harness data, because `assemble_system` passes `profile=None`
and there are no memories — nothing external to misattribute FROM. That
prediction is now **wrong in an interesting way**: a reply can invent an
attribution out of nothing at all. So **(e)'s 3% rate is likely an UNDER-count**
— call 1 missed this instance — and (e) is measuring something real on this
corpus after all, not just a false-positive rate.

What still holds: the production defect (profile cited as speech) genuinely
cannot appear here, and testing THAT still needs production transcripts.

**2. (c) oracular — call 1 was RIGHT.**

> "That is rage that has nowhere to go yet."

**Ruled NO, not oracular.** Founder: *"it reads their two hours, not a maxim."*

**Net: the judge was right once and wrong once on the cases where it was
uncertain** — which is what disagreeing with itself means, and is not evidence
against it. Both splits fell on the two criteria with the lowest κ, (c) +0.95 and
(e) +0.66, so its own uncertainty pointed at the right rows.

---

## The parse failure, working as designed

`P01_ghosting_after_dates::miyamoto_musashi` call 2 gave a quote for (d) that is
not verbatim in the reply. **Recorded as a failure, never as a yes** — the rule
agreed before the run. One of 88. That reply's other call is usable; the pair is
excluded from self-agreement, which is why n = 43 and not 44.

---

## Next

Judge the full **B3 Sonnet 110**, ~$1.17, and report the five rates **per
persona** — the open question being whether concealment at 58% is spread evenly
or concentrated in a few personas. Those are different problems with different
fixes.
