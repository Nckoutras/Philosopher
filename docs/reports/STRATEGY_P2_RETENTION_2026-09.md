# P2 — Retention. Strategy skeleton

**Founder-locked:** 2026-09-08. **Re-locked:** 2026-09-11 — one item inserted at
position 2, and the start gate's third condition changed hands.
**Recorded at SHA:** `93aa06932de12a03c4c523f47733bf9897c44d0f`.

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
| 2 | Tranches merged | ✅ **met** — #612–#614; the bank is complete at 360/360 |
| 3 | **Founder** post-v2 memory read | ⏳ pending |
| 4 | First v2 Sunday letter | ⏳ pending |

Conditions 3 and 4 are **qualitative and founder-reported**. They are not test
results and no measurement substitutes for them: the question is whether the memory
reads as *recognition* to the person it is about, and whether the letter reads as
having been written to them.

**Condition 3 changed hands on 2026-09-11, and the bias is named rather than
hidden.** It was to be a tester's read (Dimitris / Komninos). Dimitris is
unavailable, so it is now explicitly a **founder** read. That is a weaker instrument
and this document says so: the person who built the memory is the person judging
whether it reads as recognition, and the failure mode of that arrangement is that it
passes. It is recorded as a known weakness of the gate rather than as an equivalent
substitute. If an outside reader becomes available before P2 opens, prefer them.

**If either report is negative, P2 opens with v2 tuning instead of with the build
order below.** That is the whole reason the gate is qualitative. A negative read
means the foundation P2 is meant to build retention on does not yet hold, and adding
surfaces on top of it would multiply the defect across five features rather than fix
it in one.

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

### 2. The epistemic loop — NEW, inserted 2026-09-11

**Everything this product infers about a person is currently terminal.** A council
verdict, a mirror reading, a counterview, a shift classification — each is generated,
shown once, and never recalled into anything. `ring_true` is the clearest case: the
column exists, the user can set it, and **nothing reads it**. Not recall, not the
letters, not the next verdict. So the product asks people whether its interpretation
of them was right, and then discards the answer. Meanwhile every item below this one
compounds on interpretations nobody has confirmed: Threads groups by inferred theme,
Chapter narrates by inferred arc, contextual rituals fire on inferred occasion. The
intent of this item is to close the loop — that a reading the person confirmed is
worth more than one they did not, that a reading they rejected stops being repeated
back to them, and that the difference is visible to the system rather than only to
them. It is inserted at position 2 rather than appended because it is cheaper now
than after three more surfaces have been built on unconfirmed ground, and because
Continue the Thread is the surface that first makes a stale interpretation visible.

### 3. Return to This

Distinct from Continue the Thread: this is the person marking something themselves,
rather than the room deciding. Something said in passing turns out to matter, and
there is currently no way to say "come back to this with me later" — a saved line is
an artefact to look at, not an appointment to keep. The intent is a lightweight
forward commitment the room honours, which also gives the product its first
user-authored signal about what matters, as opposed to what the model inferred. It
now sits after the epistemic loop because that signal and the confirmation signal are
the same kind of thing, and building the storage for one twice would be the exact
duplication Rule 1 exists to prevent.

### 4. Contextual rituals v1

Rituals today fire on a schedule, and a schedule knows nothing about the person's
week. The intent is that a ritual can be occasioned — arising from what has actually
been happening rather than from the clock — so that the prompt arrives because
something in their material called for it. v1 means the narrowest usable version of
that, not a general rules engine, and it comes after the items above because all of
them create the signals a contextual ritual would key off.

### 5. Threads — the investigation flagship

The largest and least specified item, and the one most likely to duplicate existing
infrastructure: a thread is arguably a conversation, a saved line, a memory entry and
a mirror period all at once, and every one of those already exists with its own
schema and its own readers. **This item opens with an investigation-only PR producing
a comparison report, and nothing else.** It is named the flagship because it is the
case CLAUDE.md Rule 1 was written for — the 2026-05-16 entry describes exactly this
shape. The intent, once the ground is known, is that a person can see the shape of a
preoccupation across time rather than as a list of separate sessions.

### 6. Chapter

The longest horizon and the last item: a period of a life has a shape that is only
visible once it has closed, and the product accumulates the material to show that but
has no surface for it. The intent is something that reads as a chapter rather than as
a report — closer to the weekly letter than to the octagon. It is last because it
depends on Threads for its unit, and because it is the item most likely to be wrong
if built before the earlier items have taught what people actually return for.

---

## RULED OUT — with the reason each

Recorded so that a later session does not re-propose them as new ideas. None of these
is forbidden forever; each is refused **at this stage**, for a stated reason.

| Ruled out | Why |
|---|---|
| **A ritual router** | A general rules engine for occasioning rituals is the v2 of an item whose v1 does not exist. It would be designed against guesses about which occasions matter, and every guess would become schema. Contextual rituals v1 is deliberately the narrowest usable version instead. |
| **Decision / outcome tables** | Modelling a person's decisions and their outcomes turns a reflective companion into a tracker, and asks the product to be right about consequences. It also creates a schema whose rows are only ever as good as the user's willingness to report back — which is the same unverified-inference problem the epistemic loop exists to fix, with a table around it. |
| **A ten-class ontology** | A fixed taxonomy of what a person's material can be about. It would be authored before the evidence, applied to everything, and then defended. The product already has themes and entry types that grew from use; a ten-class scheme replaces something empirical with something tidy. |
| **Email open pixels** | Tracking whether a letter was opened. Rejected on product grounds rather than technical ones: a letter that is read months later, or read and not opened in a tracked client, is not a failure, and instrumenting intimacy with a beacon changes what the letter is. Delivery is already recorded; that is the measurable part and it is enough. |
| **Treating verdicts as truth without confirmation** | The status quo, named explicitly so that leaving it in place counts as a decision rather than an omission. It is what item 2 exists to end. |

---

## SUCCESS TESTS — founder-locked 2026-09-11

**Provenance, stated plainly because this document spent its cycle policing
unverified claims.** These five tests were **written for this document** from the
founder's locked bullets, *informed by* the external review — they are **not**
transcribed from it. The review's own text was not in hand when they were drafted, so
no sentence below should be attributed to it. They are locked as written.

They are stated as tests that can fail, not as targets to be reached.

1. **Return without a prompt.** Does a person open the product on a day nothing was
   sent to them? Scheduled surfaces (letters, rituals) make returns easy to
   manufacture; an unprompted open is the only one that says the product is wanted.
2. **A confirmed reading is reused.** After item 2, can a reading the person marked
   as true be shown to have changed a later output — and can a rejected one be shown
   to have stopped appearing? If neither is demonstrable, the loop was built and not
   closed.
3. **The second week beats the first.** Retention at week 2 measured against week 1
   for the same cohort, rather than aggregate DAU, which a single burst of onboarding
   flatters.
4. **The person recognises themselves.** The qualitative read of the start gate,
   repeated after each build item rather than only once. It is the only test here
   that cannot be gamed by shipping more surfaces.
5. **Nothing added made the room noisier.** Each item is additive; the failure mode
   of all five together is a product that pesters. A build item that raises returns
   and also raises opt-outs has not passed.

---

## SOURCE DOCUMENTS

The exchange behind this update took place on **2026-09-09**. Both documents are
committed **verbatim** under `docs/reports/` so that the reasoning is readable
without reconstruction from this summary:

- `docs/reports/P2_EXTERNAL_REVIEW_2026-09-09.md` — the external review as received.
- `docs/reports/P2_EXTERNAL_REVIEW_REPLY_2026-09-09.md` — **the reviewer's revised
  position after seven challenges.** It is the reply, not a document about the
  epistemic loop; the loop is one of the things it arrives at, not its subject.

Read them in that order. The second supersedes the first wherever they differ, which
is the point of committing both rather than only the conclusion.

> **⚠️ PENDING TEXT.** Both filenames are fixed and referenced above; **the founder
> is placing both files in this directory, byte-identical, before the PR opens.**
> This rotation deliberately creates **no stubs** — an empty or paraphrased file
> under either name would be worse than an absent one, because a later reader would
> take it for the source. If the PR merges without them, this block stays until they
> land.

---

## What this document is not

It is not a commitment to build all six, and not an ordering that survives evidence
against it. It is the order to *investigate* in, so that each investigation can assume
the ones before it. Anything here becomes work only after its own Rule 1 pass, its
own brief, and its own founder approval.
