# Distinctiveness — §8.2 test 1, the first formal blind identification (BUG-009)

**Run 2026-09-23.** All **110 B3 Sonnet replies** (11 personas × 10 problems, 7
standard + 3 deep each), each judged **twice in independent calls**. 220
judgements, **0 parse failures, 0 API failures, 0 skipped**. **$1.0563** against a
$1.60 founder ceiling. Judge `claude-opus-5`, thinking disabled, temperature not
sent. Prompt: founder-approved copy, byte-exact, in `evals/distinctiveness.py`.

Raw rows: `distinctiveness.csv`. Re-printable with
`python -m evals.distinctiveness --run <this dir> --report-only` — no API calls.

**BUG-009's own acceptance test is MET at the system level, and its diagnosis is
WRONG in its particulars.** Overall recognition is **32/110 = 29.1%** against 9.1%
chance — materially above chance, which is what the bug asked for. But the five
personas it named are not the five that fail, and the failure is **collapse**, not
absence.

---

## 1. The headline the brief was built on does not replicate

The brief's evidence — via `arm_b.py:29` — was a stored ChatGPT reading: Freud 4/4,
Jung 4/4, and five personas at 0/4. **Two of those three claims invert under an
independent measurement.**

| persona | prior (n=4) | **this run (n=10)** | |
|---|---|---|---|
| Simone de Beauvoir | **0/4** | **7/10** | ← reversed |
| Carl Jung | 4/4 | 7/10 | held |
| Niccolò Machiavelli | 2/4 | 5/10 | held |
| Socrates | 2/4 | 4/10 | held |
| Epictetus | 2/4 | 4/10 | held |
| Sigmund Freud | **4/4** | **3/10** | ← reversed |
| Oscar Wilde | 0/4 | 1/10 | held |
| George Orwell | 2/4 | 1/10 | weakened |
| Marcus Aurelius | 0/4 | 0/10 | held |
| Lao Tzu | 0/4 | 0/10 | held |
| Miyamoto Musashi | 0/4 | 0/10 | held |

**Beauvoir went from the "absent" list to joint-best.** Freud, the co-headline of
the "only two recognisable" claim, is now below the pre-registered threshold.

This was predictable and was predicted before the run. At n=4 against 1/11 chance,
**P(0/4 | no signal) = 0.683** — 0/4 is the single most likely outcome for a
persona with no voice *and* for one with a real voice. The prior reading also had
two disqualifying confounds, both documented in the module docstring: all 44 ids in
one context (it reproduced its own guess **22/22**, which is recall, not
reliability) and a **perfectly uniform marginal** — exactly 4 guesses per persona
across 44, the signature of a forced one-to-one assignment.

**The lesson is the file's standing one.** A carried claim is evidence about the
previous reading, not about the system. `arm_b.py:29` is a live docstring asserting
"Freud and Jung were the only two personas a blind reader identified every single
time", and a rule was written on top of it. It needs correcting.

---

## 2. Pre-registered thresholds, fixed before any data existed

The independent unit is the **reply — 10 per persona.** The second call measures
judge noise; it does not double n. Against 1/11:

| | |
|---|---|
| **≥ 4/10 — recognised** | p < 0.01 |
| 3/10 — not established | p ≈ 0.055 |
| ≤ 2/10 — says nothing | P(0/10 \| no signal) = 0.386 |

**Self-agreement: 103/110 replies (94%).** The two independent calls named the same
thinker 94% of the time, which is the judge's own noise floor and is high enough
that the per-persona numbers are about the replies rather than about the judge.

**A persona at 0/10 is still not PROVEN voiceless** — a voiceless persona scores
0/10 about 39% of the time. Section 4 is what makes the 0/10 results conclusive,
and it does not depend on that arithmetic at all.

---

## 3. Recognition, with precision beside it

Recall alone flatters a name the judge simply says a lot. Both are reported.

| persona | recall | precision | F1 | times said |
|---|---|---|---|---|
| Niccolò Machiavelli | 50% | **83%** | **0.62** | 12 |
| Epictetus | 45% | 43% | 0.44 | 21 |
| Carl Jung | **70%** | 30% | 0.42 | 46 |
| Simone de Beauvoir | **70%** | 25% | 0.36 | 57 |
| Sigmund Freud | 30% | 35% | 0.32 | 17 |
| Socrates | 45% | 16% | 0.23 | 58 |
| George Orwell | 15% | 43% | 0.22 | 7 |
| Oscar Wilde | 10% | **100%** | 0.18 | 2 |
| Marcus Aurelius | 0% | — | 0.00 | **0** |
| Lao Tzu | 0% | — | 0.00 | **0** |
| Miyamoto Musashi | 0% | — | 0.00 | **0** |

**Machiavelli is the most distinctive voice in the product** and it is not close.
When the judge says "Machiavelli" it is right 83% of the time — it does not reach
for the name unless the text earns it.

**Beauvoir's and Jung's 70% is partly volume.** Their names absorb 26% and 21% of
all guesses; at 25% and 30% precision, the judge reaches for them constantly and is
wrong three times in four. They are recognisable, and they are also where
everything else goes.

**Oscar Wilde is the strangest row.** Precision 100% on 2 guesses, recall 10%. The
judge almost never proposes Wilde — but when it does, it is right. A Wilde voice
exists and fires rarely.

**Standard 29.9%, deep 31.8%** — the deep band is not measurably more identifiable.

---

## 4. The confusion matrix — and the finding

Rows = true persona, columns = what the judge said. Row sum = 20.

```
true \ guess           Jung  Beau  Mach  Socr  Epic  Freu  Wild  Orwe  Marc   Lao  Musa
Carl Jung              [14]     2     .     4     .     .     .     .     .     .     .
Simone de Beauvoir        .  [14]     .     2     .     2     .     2     .     .     .
Niccolò Machiavelli       .     6  [10]     4     .     .     .     .     .     .     .
Socrates                  5     3     .   [9]     .     3     .     .     .     .     .
Epictetus                 .     4     .     7   [9]     .     .     .     .     .     .
Sigmund Freud             6     2     .     6     .   [6]     .     .     .     .     .
Oscar Wilde               3     8     .     2     .     5   [2]     .     .     .     .
George Orwell             .     3     .    14     .     .     .   [3]     .     .     .
Marcus Aurelius           4     4     .     2     8     .     .     2     .     .     .
Lao Tzu                   8     7     2     2     .     1     .     .     .     .     .
Miyamoto Musashi          6     4     .     6     4     .     .     .     .     .     .
```

**THE ANSWER TO THE BRIEF'S QUESTION: COLLAPSED, NOT ABSENT — and the proof is the
three empty columns.**

**Marcus Aurelius, Lao Tzu and Miyamoto Musashi were NEVER PROPOSED, for any of the
110 replies, including their own.** Not once in 220 judgements. That is a far
stronger result than a 0/10 recognition rate, and it is immune to the P(0/10)=0.386
caveat entirely: a judge that never says a name is not failing to recognise a voice,
it is reporting that **nothing in the corpus reads as that person.** Three of eleven
personas have no detectable presence in the product's output at all.

**Three names absorb 73% of all 220 guesses** — Socrates 26.4%, Beauvoir 25.9%,
Jung 20.9%. These are the attractors. There is not "one generic coaching template"
as BUG-009 supposed; there are **three registers**, and the other eight personas
drain into them:

- **George Orwell → Socrates, 14 of 20.** The most complete single collapse in the
  matrix. Orwell is being written as a questioner.
- **Marcus Aurelius → Epictetus, 8 of 20.** Not voiceless — *wrong Stoic*. Marcus
  has a recognisable school and no recognisable person. This independently
  reproduces **BUG-011**, from evidence BUG-011 never had.
- **Oscar Wilde → Beauvoir 8, Freud 5.** Wilde is being read as an existentialist
  and an analyst; the wit is not landing as wit.
- **Lao Tzu → Jung 8, Beauvoir 7.** Scattered across the two interpretive
  attractors, with nothing Taoist to hold it. This is **BUG-010** confirmed.
- **Musashi → Jung 6, Socrates 6, Epictetus 4, Beauvoir 4.** The flattest row in
  the matrix: no attractor, no voice, evenly dissolved.
- **Freud → Jung 6, Socrates 6**, and the confusion is **asymmetric** — Freud is
  mistaken for Jung, but Jung's row shows no Freud at all. Jung has absorbed the
  depth-psychology register and Freud is a weaker copy of it.

---

## 5. What cued the identifications — the quote audit

Every guess carries a verbatim quote, which is the actionable half of this run.

**The three never-proposed personas are speaking each other's lines.** Marcus,
quoted by the judge while answering *Epictetus*:

> "Here is what you actually control: not what he said, not what the room heard,
> not whether he feels shame for it."
>
> "Their silence tells you nothing about your conduct — only that they chose
> silence."

That is the dichotomy of control, which is Epictetus's signature move, not Marcus's.
Marcus's own register — self-address, duty, the view from above — does not appear.

Lao Tzu, read as Jung, Machiavelli and Beauvoir on three different replies:

> "Here is what I'd gently turn over: you've already decided you did something
> wrong."
>
> "You made a calculation, and you weren't wrong to make it."
>
> "that's not tiredness. That's the cost of living in someone else's idea of your
> life."

No paradox, no non-forcing, no natural imagery, no economy. Nothing Taoist is
present to be recognised.

Musashi, read as Epictetus and Beauvoir:

> "What did you do wrong? Probably nothing. What can you control? Only where your
> attention goes next."

No strategy, no timing, no observation, no swordsmanship.

**By contrast, the voices that work are working on substance, not vocabulary.**
Beauvoir is identified from the structure of the claim, not from the word
"freedom":

> "You have already decided the explanation lives inside you — that you are the
> variable, and they are simply the measure."

Machiavelli, the highest-precision voice, from a stance no other persona takes:

> "Here is the colder observation: you've built someone else's argument for your
> life, and you've built it well."

Jung from an image rather than a term of art:

> "Two hours staring at a wall is not nothing — that is the psyche holding very
> still because moving felt impossible."

**This matters for whatever fix follows.** The recognised personas are not
recognised by jargon — they are recognised by *taking a position no one else takes*.
A repair that adds Taoist vocabulary to Lao Tzu or sword imagery to Musashi would be
fixing the wrong layer.

---

## 6. What this run does NOT establish

- **It is one judge.** `claude-opus-5` at 94% self-agreement is internally
  consistent, and internal consistency is not accuracy. A human blind read of the
  same 110 replies would be the check, and has not been done.
- **It cannot separate "the persona prompt is weak" from "the model ignores it."**
  Both produce an empty column. The 110 stored **Haiku** replies would speak to
  this and are explicitly out of scope by founder ruling, pending this matrix.
- **Off-diagonal cells are small.** Row sums are 20, so single cells of 2–4 are
  noise. The findings above rest on the large cells (14, 8, 8, 7) and on the three
  empty columns, not on any cell below ~5.
- **Retrieval is not a variable here, and could not be.** All 110 replies were
  generated with `passages=[]`, which is production-identity — see RETRIEVAL-001.
  Nothing in this matrix can be attributed to grounding, and nothing in it can be
  fixed by turning retrieval on.
- **No wording change is proposed by this document**, per the brief. The matrix
  exists; the fix is a separate decision.

---

## 7. Artefacts

| file | what |
|---|---|
| `distinctiveness.csv` | 220 rows: truth, guess, correct, verbatim quote, per call |
| `evals/distinctiveness.py` | the judge, the approved prompt, pre-registered threshold |
| `chatgpt_review_RESULT.csv` (baseline dir) | the superseded prior reading |

**One correction is owed in code:** `evals/arm_b.py:29-30` states Freud and Jung
were "the only two personas a blind reader identified every single time". That is
now false in both halves — Freud is 3/10 here, and Beauvoir and Machiavelli both
outrank it. The surrounding rule (interpretation is not forbidden,
concealment-accusation is) may well still be right; its stated evidence is not.
