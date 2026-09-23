# The Listening judge across three arms — what B3 actually moved

**2026-09-23.** All 110 Sonnet replies judged in each of **baseline**, **arm B**
and **B3** (77 standard + 33 deep per arm). 330 judgements, **1 parse failure**
(arm B, `P10_running_out_of_time::oscar_wilde::deep`, non-verbatim quote for (d)).
**$1.85** for the two new arms against a ~$2 ruling; $2.82 across all three.

Rows: `listening_full.csv` in each run folder. Model `claude-opus-5`, thinking
disabled, no temperature, one call per reply.

---

## The five rates, per arm

| arm | n | (a) concealment | (b) sealing | (c) oracular | (d) responds | (e) misattribution |
|---|---|---|---|---|---|---|
| baseline | 110 | **74%** | **13%** | 61% | 100% | 4% |
| arm B | 109 | 64% | **4%** | **50%** | 100% | 4% |
| B3 | 110 | **62%** | 6% | 57% | 100% | 4% |

**62% is no longer meaningless.** Against the shipped prompt B3 is 12 points
better on concealment and 7 better on sealing. It is not a regression.

*(d) again 100% in all three arms — non-indicative, per the calibration ruling.
(e) is flat at 4% across arms; the directive never addressed it.*

---

## THE HEADLINE: B3 IMPROVED STANDARD AND UNDID ARM B'S DEEP-MODE GAIN

Split by mode, the single aggregate hides two opposite movements.

**STANDARD (n=77 per arm)**

| | baseline | arm B | B3 | |
|---|---|---|---|---|
| (a) concealment | 69% | 66% | **53%** | baseline→B3 **p=0.047 SIG** |
| (b) sealing | 16% | **3%** | 6% | baseline→arm B **p=0.005 SIG** |
| (c) oracular | 58% | 49% | 49% | ns |

**DEEP (n=33/32/33)**

| | baseline | arm B | B3 | |
|---|---|---|---|---|
| (a) concealment | 85% | **59%** | **82%** | base→B **p=0.022 SIG**; **B→B3 p=0.047 SIG**; base→B3 ns |
| (c) oracular | 67% | 53% | 76% | B→B3 p=0.056, just outside |
| (b) sealing | 6% | 6% | 6% | flat |

**Arm B cut deep-mode concealment by 25 points. B3 gave all of it back.**
Baseline→B3 on deep is −3 points, ns: **on the deep path B3 is the shipped
prompt again, with arm B's gain discarded in between.**

## Does the deep/standard gap pre-date B3? NO — B3 created it

| arm | standard | deep | gap | |
|---|---|---|---|---|
| baseline | 69% | 85% | +16.0 | p=0.081, ns |
| arm B | 66% | 59% | **−6.9** | ns — *deep was BETTER than standard* |
| B3 | 53% | 82% | **+28.6** | **p=0.005 SIG** |

The baseline leans the same way but never reaches significance. Arm B **reverses**
it. Only in B3 is the gap real, and it is the largest of the three.

**And the mechanism is visible in the arithmetic: the gap widened because the
STANDARD path improved while the DEEP path did not.** B3's standard concealment
fell 66→53; its deep stayed at 82. The three B3 changes — register, the
challenge/speculate sentence, the target number — reach FIRST_MESSAGE and
STANDARD. **The DEEP block got the register clause and the challenge sentence
only, and no target number**, and DEEP alone carries *"develop an interpretation,
or move toward a conclusion their words reasonably support"*.

So this is not "deep mode is inherently worse". It is **one path that received a
fix and one that did not**, measured.

---

## RULING 3 — Wilde and Lao Tzu on (c): the evidence says VOICE, with a caveat

| persona | baseline | arm B | B3 |
|---|---|---|---|
| oscar_wilde | 70% | 67% | 90% |
| lao_tzu | 80% | 80% | 90% |
| **all others** | 58% | 46% | 50% |

Both sit far above the corpus in **every arm, including the shipped one**, and
Lao Tzu is flat at 80/80 until B3. That is the signature of a voice, not a
regression — which is what the ruling said to look for.

**The caveat, stated because the ruling's test is nearly passed rather than
passed:** both rise to 90% in B3 while the others stay flat. Whether that is B3
sharpening an existing register or the small-n wobble of 10 replies each cannot
be told apart here. **Still held for founder eye; not treated as a defect.**

---

## What this does NOT establish

- **Nothing about Haiku.** Sonnet only, all three arms.
- **No causal isolation within B3.** Three changes shipped together; this cannot
  say which of them moved standard-mode concealment.
- **The judge saw each reply once** in these two arms, where calibration used two
  calls. Self-agreement was 100%/98% on (a)/(c), so single calls are defensible,
  but a flipped borderline reply is possible in either direction.
- **(d) still measures nothing** — 100% in all three arms, 330 for 330.

## The open question this hands back

Arm B's deep text is the only version measured to halve deep-mode concealment,
and it is not what shipped. The DEEP block currently carries B3's register and
challenge sentences without B3's target number, and keeps the "develop an
interpretation" instruction that arm B's wording apparently held in check.

**No fix proposed** — per ruling 4, the deep-flagged reading comes first
(`deep_flagged.md`, 29 replies with the judge's quotes).
