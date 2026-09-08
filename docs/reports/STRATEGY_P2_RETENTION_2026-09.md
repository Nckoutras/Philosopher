# P2 — Retention. Strategy skeleton

**Founder-locked:** 2026-09-08. **Recorded at SHA:** `076f74b7`.

This is a skeleton, not a plan. Each item below is **one paragraph of intent**. There
is no design here and no PR decomposition, deliberately: CLAUDE.md Rule 1 requires
that every one of these opens with an investigation that enumerates what already
exists in its domain, reports, and only then designs. Writing briefs now would be
designing against a codebase nobody has re-read.

---

## START GATE

P2 does not open until all four conditions hold.

| # | Condition | Status |
|---|---|---|
| 1 | #6 letter delivery merged | ✅ **met** — #608–#611, verified on `main` |
| 2 | Tranche A merged | ✅ **met** — #612 (and B #613, C #614; the bank is complete at 360/360) |
| 3 | Founder qualitative report (a): a tester's post-v2 memory read | ⏳ pending |
| 4 | Founder qualitative report (b): the first v2 Sunday letter | ⏳ pending |

Conditions 3 and 4 are **qualitative and founder-reported**. They are not test
results and no measurement substitutes for them: the question is whether the memory
reads as *recognition* to the person it is about, and whether the letter reads as
having been written to them.

**If either report is negative, P2 opens with v2 tuning instead of with the build
order below.** That is the whole reason the gate is qualitative. A negative read
means the foundation P2 is meant to build retention on does not yet hold, and adding
surfaces on top of it would multiply the defect across five features rather than fix
it in one.

The two pending reads are NIKOS-ACTION 11 in `IMPLEMENTATION_BACKLOG_v28.md`
(tester: Dimitris / Komninos).

---

## BUILD ORDER

Strict order. Each item assumes the ones before it.

### 1. Continue the Thread

A conversation that ended is not necessarily finished, and today the product treats
those as the same thing — the person returns to a list of past conversations and must
decide, cold, which one to reopen and what they were going to say. The intent is that
the room remembers there was somewhere left to go, and offers it: not a summary of
what was said, but the live end of an unfinished thought. This is first because it is
the smallest change that turns a visit into a return, and because it exercises the
memory work of P1 against a real surface rather than against a letter.

### 2. Return to This

Distinct from Continue the Thread: this is the person marking something themselves,
rather than the room deciding. Something said in passing turns out to matter, and
there is currently no way to say "come back to this with me later" — a saved line is
an artefact to look at, not an appointment to keep. The intent is a lightweight
forward commitment the room honours, which also gives the product its first
user-authored signal about what matters, as opposed to what the model inferred.

### 3. Contextual rituals v1

Rituals today fire on a schedule, and a schedule knows nothing about the person's
week. The intent is that a ritual can be occasioned — arising from what has actually
been happening rather than from the clock — so that the prompt arrives because
something in their material called for it. v1 means the narrowest usable version of
that, not a general rules engine, and it comes after the two items above because both
of them create the signals a contextual ritual would key off.

### 4. Threads — the investigation flagship

The largest and least specified item, and the one most likely to duplicate existing
infrastructure: a thread is arguably a conversation, a saved line, a memory entry and
a mirror period all at once, and every one of those already exists with its own
schema and its own readers. **This item opens with an investigation-only PR producing
a comparison report, and nothing else.** It is named the flagship because it is the
case CLAUDE.md Rule 1 was written for — the 2026-05-16 entry describes exactly this
shape, three hours spent building a parallel implementation of something already
shipped. The intent, once the ground is known, is that a person can see the shape of
a preoccupation across time rather than as a list of separate sessions.

### 5. Chapter

The longest horizon and the last item: a period of a life has a shape that is only
visible once it has closed, and the product accumulates the material to show that but
has no surface for it. The intent is something that reads as a chapter rather than as
a report — closer to the weekly letter than to the octagon. It is last because it
depends on Threads for its unit, and because it is the item most likely to be wrong
if built before the earlier four have taught what people actually return for.

---

## What this document is not

It is not a commitment to build all five, and not an ordering that survives evidence
against it. It is the order to *investigate* in, so that each investigation can assume
the ones before it. Anything here becomes work only after its own Rule 1 pass, its own
brief, and its own founder approval.
