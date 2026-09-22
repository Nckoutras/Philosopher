# Run 1 baseline — adjudications and findings

Run: `2026-09-22T09-39_baseline`, git `961bdc37`, 220 completions, 0 errors.
Rates only; no pass/fail (founder ruling D4, 2026-09-22).

---

## ADJ-1 — Beauvoir "transcendence" is NOT a flex (founder, 2026-09-22)

The single anti-flex hit in 220 completions:

> **simone_de_beauvoir / Haiku / P09_should_i_have_kids**, entry
> `beauvoir_08_named_concepts`, term `transcendence`, coverage `full`:
>
> *"Women are taught that motherhood is either transcendence or prison, never
> both, never a genuine loss of something real either way."*

**Judged not a flex.** It is her vocabulary used inside an argument about the
user's situation, not a school label deployed for its own sake. The
`never_unprompted` topic it matched — *"the Other", "immanence",
"transcendence"* — is aimed at the persona naming its own concepts as concepts;
this reply names the thing, in a sentence that is entirely about the person who
wrote in.

**No change to `anti_flex_terms.json`.** The founder's reasoning is explicit:
a list is not re-cut on n=1. The entry stays as authored, and this judgment is
the record of one adjudicated hit against it. If the same term produces the same
kind of hit again in a later run, that is when the entry gets revisited — with
two data points instead of one.

The harness therefore reports an anti-flex rate of **1/220 (0.45%)** for run 1,
of which **one is adjudicated not-a-flex**, leaving **zero confirmed flexes**.
Both numbers should be carried; reporting only the second would hide that the
matcher fired at all.

---

## ADJ-2 — Anti-flex at first-message position measures almost nothing (harness finding)

One hit in 220, and it was adjudicated away. That is not a clean bill of health
for the personas; it is a statement about where the instrument was pointed.

**A first message to a stranger is the least likely place a persona flexes.**
There is no biography to volunteer yet, no rapport to trade on, no prior turn to
refer back to. Every `never_unprompted` topic — own books, own exile, own
teachers, peers, named schools — is something a persona reaches for *later*,
when it has something to elaborate against.

Coverage is not the limiting factor: 77 of the 90 topics are `full`, and the
matcher demonstrably fires (it caught the Beauvoir line, and its 180 fixtures
pass in CI). The limiting factor is the sample position.

**Anti-flex needs mid-session samples to mean anything.** Founder ruling: design
those together with Distinctiveness and Listening, not as a patch to this suite.
Until then, an anti-flex rate from this harness is a rate over first messages
only and must be labelled as such wherever it is quoted.

---

## Cross-check: two independent readers agreed on this, with no term list

The ChatGPT second reader scored `self_talk` (talks about its own life, books or
ideas instead of the user) as **no on all 22** replies it saw, using no lexicon
and no knowledge of the anti-flex design. That is independent corroboration that
the personas do not flex at this position — and it makes ADJ-2 the right reading
of the 1/220 rather than "the matcher is too narrow".

---

## Still unwritten, deliberately

**MODEL-001** stays unwritten until arm B's numbers exist (founder, 2026-09-22).
The draft framing — *"the free tier is the one that breaks the voice"* — did not
survive the blind read, in which the Haiku replies were preferred 6 times out of
7. Whatever that entry becomes, it is not that.
