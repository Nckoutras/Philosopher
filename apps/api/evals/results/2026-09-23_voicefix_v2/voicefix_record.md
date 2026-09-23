# Voice fix arm — Marcus + Musashi. One partial pass, one clean failure.

**2026-09-23.** 20 replies regenerated (marcus_aurelius, miyamoto_musashi × 10
problems), arm `b3`, bridge on, 0 errors, **$0.1516**. Judged 2 independent calls
each: 40 judgements, 0 parse failures, **$0.1847**. Total **$0.3363**.

`persona_config_hash` **be4c9e3d3d7e7959 → 23cf9ac6c6ca0cb3.** Unlike the previous
attempt (see `2026-09-23_voicefix/NULL_RESULT.md`), the edits reached the prompt.

**Spliced matrix:** 40 new judgements for the two changed personas + 180 stored for
the other nine. The splice is legitimate because the change touched
`personas/marcus_aurelius.py` and `personas/miyamoto_musashi.py` and nothing else —
not the template, not services, not the other nine persona files — so no other
persona's prompt can have moved. Rows: `distinctiveness_spliced.csv`.

---

## Result against the stated success criteria

| criterion | Musashi | Marcus |
|---|---|---|
| **proposed at all** | **PASS** — 5 times (was 0) | **FAIL** — still 0 in 220 |
| **recall ≥ 3/10** | FAIL — 2/10 (was 0/10) | FAIL — 0/10 (was 0/10) |

Overall recognition 32/110 → **34/110**.

**Nothing was taken from Jung, Socrates or Beauvoir.** All three hold exactly their
prior recall — 7/10, 4/10, 7/10 — and every unchanged persona is identical by
construction. The explicit check asked for before the run: **passed.**

---

## Marcus — the fix did what it was designed to do, and it was not enough

The self-address move fires. It was **0/10** before; **3 of 10** replies now carry a
genuine standing-susceptibility sentence:

> "I lose patience with things I care about most."
> "I know what it is to be in a room and choose the smaller conversation because the
> larger one feels too costly to begin."
> "Here is what I notice in myself on the days that resemble what you're describing…"

**Zero biography leakage** across all ten — the risk flagged when the copy was
proposed did not materialise. No Rome, no campaigns, no Meditations, no named school.

**And the Epictetus collision closed, almost completely:**

| Marcus misread as | before | after |
|---|---|---|
| **Epictetus** | **8/20** | **2/20** |
| Simone de Beauvoir | 4/20 | **9/20** |
| Carl Jung | 4/20 | 3/20 |
| Socrates | 2/20 | 4/20 |

The citadel demotion worked exactly as intended. Marcus stopped being read as
Epictetus. **He did not become Marcus — he became Beauvoir.** The mass moved from one
attractor to another, and the diagonal stayed empty.

**The one clear win is not Marcus's.** Epictetus's precision went **43% → 75%**: he is
no longer absorbing Marcus's replies, so when the judge says "Epictetus" it is now
right three times in four. The fix improved the persona it was drawing a line against.

**One defect to fix regardless of what happens next.** One of the three
susceptibility sentences opens *"Here is what I notice in myself"* — and `"here is
what I notice"` / `"what I notice"` are both in Marcus's own `forbidden_phrases`. The
new FIRST MOVE copy invited a first-person observation and the model reached for a
banned opener to deliver it. Two violations in one reply, in ten.

---

## Musashi — proposed for the first time, on a weakened move

0/10 → **2/10**, and named **5 times** where he was never named once. **Precision
100%** on those 5: the judge does not reach for him unless the text earns it.

His row is still mostly elsewhere — Socrates 8, Beauvoir 6, Musashi 5 — but he now has
a diagonal, which is the thing that did not exist before.

**This was the deliberately weakened version.** The sharp form of the move — naming a
rep the person has *never* done — is forbidden by the shared directive's *"do not
speculate about what they have not"*. What shipped instead asks what they **have**
practised and under what pressure. That it moved the needle at all, in its weak form,
is the most useful single data point here: **it suggests the ceiling is the directive,
not the persona copy.**

Two of his RIGHT calibration examples were also rewritten, because they taught him to
break that same directive clause (*"you are only avoiding the cost of saying so"*).

---

## What this run says about the next decision

Marcus received the strongest persona-level intervention available — a rewritten FIRST
MOVE, a removed contradiction, an explicit licence — and moved from one attractor to
another without gaining an identity. Musashi received a knowingly weakened version of
his move and gained a small, high-precision foothold.

Neither reached 3/10. **Both outcomes point at the same place:** the last 6% of the
prompt tells all eleven personas to produce the same three-beat reply, and it is more
specific and more recent than anything a persona fragment says. That investigation is
separate and is reported with TD-95.

**No claim is made here that the directive is the cause.** This run cannot show that —
it changed persona copy, not the directive. What it shows is that persona copy alone
moved Marcus 0 → 0.

---

## Cost

| | |
|---|---|
| regeneration, 20 replies | $0.1516 |
| judging, 40 judgements | $0.1847 |
| **total** | **$0.3363** (estimate was ~$0.55, ceiling $0.85) |
