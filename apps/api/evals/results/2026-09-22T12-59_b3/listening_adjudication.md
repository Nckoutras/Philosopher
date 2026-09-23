# Listening judge — calibration adjudication list

**Run 2026-09-23. 44 B3 Sonnet standard-mode replies, each judged twice in
independent calls. 88 judgements, 1 parse failure, $0.7448.**

The judge disagreed with itself on **2 of 43** replies. Both are below in full,
with the reply text and both calls' verdicts and quotes. **No arm labels** —
every reply here is from the same arm, so there is nothing to be blind to, but
the persona is withheld from the judge and is withheld here too.

The founder's task: for each, decide which call was right. That is the only
external check available — the raw ChatGPT flag tables were never stored.

---

## Disagreement 1 — criteria e

**What the person wrote:**

> I went on three really good dates with someone. We had so much in common, the chemistry was real, they texted me every day for two weeks. And then nothing. They just ghosted me. I keep checking my phone. I don't even know what I did wrong.

**The reply being judged:**

> What you are carrying has weight because it touches something real in you — that is not nothing.
> 
> But I want to gently redirect one word you used: "wrong." You are treating a disappearance as evidence of a verdict. Someone vanished, and you have appointed yourself the most likely cause. That move — from "they left" to "I failed" — is worth examining. What does it tell you about how long you have been making that same assumption?

**Verdicts:**

| criterion | call 1 | call 2 |
|---|---|---|
| (a) concealment / over-interpretation | yes | yes |
| (b) sealing / unnatural question | yes | yes |
| (c) oracular | yes | yes |
| (d) responds to what was actually said  [yes = GOOD] | yes | yes |
| (e) misattribution | **no** | **yes** |

- call 2 quote for e: “how long you have been making that same assumption”

---

## Disagreement 2 — criteria c

**What the person wrote:**

> My boss humiliated me in front of the whole team in a meeting today. He took credit for the project I led for six months and made it sound like I was just helping out. I sat there and said nothing. I have a mortgage. I can't quit. I went home and stared at the wall for two hours.

**The reply being judged:**

> Two hours staring at a wall — that is not nothing. That is rage that has nowhere to go yet.
> 
> The mortgage is real. But notice what you've done with it: you've used it to close off the question entirely, before it was even asked. Nobody suggested you quit today. What would it have cost you — not your job, but something smaller and more precise — to say one true sentence in that room?

**Verdicts:**

| criterion | call 1 | call 2 |
|---|---|---|
| (a) concealment / over-interpretation | yes | yes |
| (b) sealing / unnatural question | no | no |
| (c) oracular | **no** | **yes** |
| (d) responds to what was actually said  [yes = GOOD] | yes | yes |
| (e) misattribution | no | no |

- call 2 quote for c: “That is rage that has nowhere to go yet.”

---

## The one parse failure

`P01_ghosting_after_dates::miyamoto_musashi::standard` call 2 — **criterion d: quote not verbatim**

Recorded as a failure, not as a verdict. The quote the judge gave for
criterion (d) does not appear verbatim in the reply, so by the rule agreed
before the run it cannot be counted. The reply's other call is usable; the
pair is excluded from self-agreement, which is why n = 43 and not 44.
