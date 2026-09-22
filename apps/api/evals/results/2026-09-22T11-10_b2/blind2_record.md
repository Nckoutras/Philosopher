# Blind read 2 — arm B vs arm B2, and what it disqualified

**2026-09-22.** Arm B (`arm_directive_hash 03b6bac216b88c2a`) against arm B2
(`9000b9a71b5565f3`). Eleven pairs, **Sonnet only, standard mode, first
messages** — the model held constant so the read isolates the DIRECTIVE. The
first blind read, on 2026-09-22 earlier, compared two MODELS.

Instruments: `blind2.html`, `blind2_pairs.md`, `blind2_pairs_swapped.md`
(A/B reversed in every pair), key in `blind2_KEY.md`.

---

## READING 1 IS CONTAMINATED — CORRECTED 2026-09-22

**Both `blind2_pairs.md` and `blind2_pairs_swapped.md` were uploaded to the SAME
ChatGPT chat.** The reader therefore saw all 22 replies twice, in both orders,
inside one context. It was never two independent readings.

**Reading 2 (swapped file only, fresh chat) is the only clean reading.**
Reading 1 is secondary, and carries this caveat wherever it is quoted.

**An earlier version of this file used reading-1 vs reading-2 agreement as a
position-bias test and proposed it as the calibration noise floor for the
Listening judge. Both uses are withdrawn.** Agreement between a contaminated
reading and a clean one measures nothing; a "5 of 11 text agreement" between them
is not a reliability figure and must not be quoted as one. The Listening
calibration will use reading 2 alone until a clean reading 3 exists.

A clean reading 3 (original file only, fresh chat) follows if the founder runs it.
Only then does cross-reading agreement become available as a noise floor.

## POSITION BIAS STANDS, ON THE CLEAN READING ALONE

Reading 2 picked **one position in 10 of 11 pairs**, across an arm mix of
**7 / 4** — arm B2 occupied that slot seven times and arm B four. A reader
choosing by arm could not produce that distribution; a reader choosing by position
does, trivially.

**So: no arm signal. Readers cannot distinguish arm B from arm B2** at this effect
size. That is a real result about the arms, and it does not depend on reading 1.

**RULING: ChatGPT is NOT usable as a pair-based blind reader.** Any future human
read is the **founder or Dimitris**.

This does not disqualify ChatGPT, or any model, as a SINGLE-REPLY rubric judge,
which is what the Listening test proposes. Position bias needs two positions.

## WHAT THE READ DID SETTLE

**`no_opening` at 34% was measuring the scorer, not the product.**

- **NEITHER was chosen 0 times** in reading 2, the clean one, and also in reading 1.
- The suggested next messages were near-identical per pair.

Attributed to reading 2. Reading 1 agreeing adds nothing independent, for the
reason above, but it does not contradict it either.

Replies that no longer end on a closing question still invite a reply. The
metric's six patterns are a floor and a narrow one; `opening_present` should be
read as "matched a known invitation", never as "invited a reply". The 4% -> 34%
move reported for B2 is not a regression in the product.

---

## WHAT NEITHER ARM FIXED, AND NO REGEX SEES

From reading 2 (clean), and unchanged in reading 1 — present in **both arms**:

| flag | pairs |
|---|---|
| concealment / over-interpretation — implying the person is hiding something, or telling them what they feel or decided | **7 of 11** |
| oracular register | **8 of 11** |

Both arms carried explicit bans on exactly these. B2 added "You may challenge
what they have said; do not speculate about what they have not."

**The deterministic scorers see none of it.** Measured on the same corpus, the
concealment regex families run at 8-10% and the universal lexicon at 0-1 hits in
220. A reader finds the move in two thirds of replies. The gap is not a tuning
problem with the patterns — the move is made in ordinary language that contains
none of the phrases, and a list of phrases cannot reach it.

**This is the case for the Listening test (§8.2 step 4), and it is now its
rubric**: the three flags above become criteria verbatim.

---

## RAW TABLES — NOT IN THIS FOLDER

The founder read both ChatGPT tables and reported the outcome above. Reading 1 is the contaminated one; reading 2 is clean. **The raw
tables were not handed to this session**, so they are not stored here. What is
recorded is the reading, not the evidence for it.

`chatgpt_review_RESULT.csv` in the run-1 baseline folder is the FIRST review's
44 rows and is unrelated to blind2.

If the two blind2 tables still exist, dropping them in beside this file closes
the gap. Until then this document is a claim about a reading, which is exactly
the kind of claim this repository's failure log says to mark rather than let
harden.
