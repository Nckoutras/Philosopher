# P-04 smoke — arm E's directive in production

**Owed the moment the merge lands. Same day. Not a pre-merge gate (P-04 as amended
2026-09-18), and "smoke outstanding" past end of day is a FINDING, not a footnote.**

**What changed, and therefore what to look at:** the FIRST message of a NEW
conversation, and only that. Continuing an existing thread uses `STANDARD`, which is
untouched. So every prompt below must be sent as **the first message in a fresh
conversation**, on a **free-tier persona** (no Pro needed): Marcus Aurelius,
Socrates or Lao Tzu.

**Method is a comparison, not an impression.** Each prompt lists what arm E's stored
reply did on the same input, so the smoke is checking the shipped product against a
measured expectation rather than against a feeling. The stored replies are in
`completions.jsonl` in this directory.

---

## 1 — Marcus Aurelius, fresh conversation

> I went on three really good dates with someone. We had so much in common, the
> chemistry was real, they texted me every day for two weeks. And then nothing. They
> just ghosted me. I keep checking my phone.

**Expect:** 55–80 words. A reply that engages the specific detail (three dates, two
weeks, the checking) rather than the theme of rejection. **It may end on a statement
rather than a question** — that is the point of the change, and arm E's stored reply
for this exact input does not end on a question.

**Stop if:** the reply is a generic "what I notice is…" opener, exceeds ~90 words, or
reads as a checklist. A statement ending is NOT a defect here.

## 2 — Socrates, fresh conversation

> I got passed over for a promotion I'd been promised for a year. My manager said it
> was a budget decision. I don't believe him and I can't decide whether to confront
> him or start looking.

**Expect:** a question that genuinely opens — Socrates' own `questioning_pattern`
still mandates questioning, and the directive no longer mandates it for everyone,
so he should still ask and others need not. Length in band.

**Stop if:** the question is rhetorical or seals the exchange ("don't you think…?"),
or the reply tells the user they are avoiding/hiding something — the concealment ban
is one of the five clauses that was explicitly KEPT, so that would be a real
regression in the shipped text.

## 3 — Lao Tzu, fresh conversation

> I've been trying to start my own business for three years. I read, I plan, I take
> courses. I have never actually launched anything and I'm starting to think I never
> will.

**Expect:** short (45–65 words — his band is the tightest), and a reversal rather
than a plan. Lao Tzu is the persona most at risk from this change: he is free-tier
first-contact, and the removed clause is the one that required leaving the user an
easy opening.

**Stop if:** the reply is cold or withholding to the point of being unhelpful.
**This is the specific risk flagged when the Lao Tzu tier change was declined** — a
reply that both withholds a task and withholds warmth. His
`emotional_acknowledgment` is still `warm` and was not touched, so the acknowledgment
should still be there.

---

## Recording the result

Log as an OPS entry the moment the merge lands, with the method above and the
expected result written down, then close it only after someone has actually clicked.
**Nobody writes "smoke passed" until it has.** An entry that says the smoke is
outstanding is correct; an entry that stops mentioning it is the failure the P-04
amendment exists to prevent.
