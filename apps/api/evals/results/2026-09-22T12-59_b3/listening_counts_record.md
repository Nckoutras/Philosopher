# Step B — the binary flag was length-biased, and it inverted the answer

**2026-09-23.** All **98 deep replies** across baseline / arm B / B3, re-judged
with a COUNT rubric instead of yes/no. 1 parse failure (baseline). **$0.597**,
plus **~$0.75 lost** to a crashed first attempt — see the note at the end.

Everything is held identical to the binary run except the answer type: same two
criteria, same definitions word-for-word (verified by test; they differ only in
grammatical number, because counting needs the plural), same verbatim-quote
audit, same model, same settings.

---

## The result, and it reverses the ranking

| arm | n | mean words | **binary (a)** | mean (a) count | **(a) per 100 words** | (c) per 100 words |
|---|---|---|---|---|---|---|
| baseline | 32 | 50.9 | 84% | 1.88 | **3.68** | 1.90 |
| arm B | 33 | 62.3 | **59%** | 1.82 | **2.92** | 1.51 |
| **B3** | 33 | **126.9** | 82% | **2.42** | **1.91** | **0.98** |

**On the binary flag B3 looked worst. On density it is decisively best.**

| per-reply (a) density, Welch | | |
|---|---|---|
| baseline → arm B | 3.76 → 3.10 | ns (p=0.11) |
| **arm B → B3** | 3.10 → **1.92** | **p=0.0003 SIG** |
| **baseline → B3** | 3.76 → **1.92** | **p<0.0001 SIG** |

| per-reply (a) raw count, Welch | | |
|---|---|---|
| baseline → arm B | 1.88 → 1.82 | ns |
| **arm B → B3** | 1.82 → **2.42** | **p=0.009 SIG** |
| **baseline → B3** | 1.88 → **2.42** | **p=0.008 SIG** |

---

## WHAT THIS MEANS, WITH BOTH READINGS STATED

**The binary flag was confounded with length**, as suspected. B3's deep replies
are twice as long as arm B's, and a per-reply "does it contain X" question is
mechanically easier to trip in a longer reply. The 82% vs 59% gap that motivated
a DEEP fix is **not** evidence that B3's wording over-interprets more.

**But density and raw count disagree, and neither is obviously the right
measure:**

- **Density says B3 is the most restrained text measured.** Per 100 words it
  over-interprets at roughly half baseline's rate and two thirds of arm B's.
- **Raw count says a reader meets MORE over-interpretation in a B3 deep reply**
  — 2.42 passages against 1.82 — because the reply is twice as long.

Both are true. Which matters depends on whether over-interpretation is
experienced per reply or per unit of reading, **and that is a product judgement,
not a measurement one.** It is not settled here.

**(c) oracular moves the same way**: 1.90 → 1.51 → 0.98 per 100 words. B3 is the
least oracular text by density, while its binary rate was the highest (76%).

---

## What step A was for, and whether it still is

A was designed to test whether length drives the deep (a) rate — by shortening
B3's deep band and re-measuring. **B has largely answered that**: length drove
the *binary* metric, and B3's text is better per word.

A is now a different question: **would shortening B3's deep replies give the low
density AND a low raw count?** That is plausible — the density is already the
best of the three — but it trades measured depth for fewer flagged passages, and
the deep band was widened deliberately after the first blind read chose longer
replies in 6 of 7 decided pairs.

**Not run. Founder decision, because B changed what A means.**

---

## A $0.75 mistake, recorded because it was avoidable

The first count run made all 99 API calls and then died on a `TypeError`:
`write_csv()` had no `count` parameter while `main()` passed one. Every
judgement was lost. Two of my edits to the same file had silently failed to
apply (CRLF mismatch in the patch text) while a third applied, leaving the caller
and the callee disagreeing — and nothing exercised that path until the paid run
reached it.

Fixed three ways: `write_csv` and `judge_all` now take `count`; `main()`
**pre-flights the write with one synthetic row before any API call** and refuses
with exit 2 if it fails; and a test asserts the pre-flight precedes
`judge_all` in source order. The rule the pre-flight encodes: *a long paid run
must never reach its write step for the first time with the data already in
memory and nowhere else.*

---

# FOUNDER RULINGS — 2026-09-23

**1. NO DEEP CHANGE. NO ARM A.** B3's DEEP is the best text measured by density.
**The binary flag was the defect, not the wording.** The DEEP block ships
unchanged; the deep band stays as shipped.

This closes a line of work that began from two premises that did not survive
checking — that B3's three changes had not reached DEEP (they had), and that
B3's deep path had regressed (it had not; a per-reply flag met replies twice as
long). Recorded that way deliberately: the investigation was worth its ~$2.50
because it stopped a wording change to the best-performing text.

**2. THE PER-REPLY vs PER-WORD QUESTION IS OPEN, and deferred to real user
feedback.** Density says B3 over-interprets least per word; raw count says a
reader meets more of it per reply (2.42 vs arm B's 1.82). Both are true and no
measurement settles which matters. It is a question about how a reply is
experienced, so it waits for users rather than for another arm.

**3. DENSITY IS NOW THE STANDARD (a)/(c) METRIC. The binary rate is reported
ALONGSIDE it, never alone.**

The reason is this run: on the binary flag the three arms rank
baseline 84% / arm B 59% / B3 82%, and by density they rank
3.68 / 2.92 / 1.91 — **a complete inversion of which text is best.** A binary
per-reply flag cannot compare arms whose replies differ in length, and every arm
in this project changes reply length.

Enforced rather than remembered: `listening.summarise_density()` computes both
and returns them together, and a test asserts it never returns one without the
other. The three stored binary runs remain valid as binary runs; they are simply
not a ranking on their own.
