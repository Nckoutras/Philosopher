# Arm D — the shape clauses out. Neither pre-declared branch fires.

**2026-09-23.** 77 Sonnet standard replies, all 11 personas, arm `d`, bridge on,
0 errors. Judged for distinctiveness (2 calls, 154 judgements, 94% self-agreement)
and for listening density (a)/(c) (1 call each on arm and control).

**Control = `2026-09-23_baseline_spliced`**, built so the two sides differ *only* in
the directive: 63 replies from B3 (the nine personas untouched by the voice fix) +
14 from `voicefix_v2` (Marcus, Musashi, post-fix). Same `persona_config_hash`
(`23cf9ac6c6ca0cb3`) on both sides; `arm_directive_hash` differs
(`7965ddb987428b8a` → `fb648d7bb909ae0a`). 7 replies per persona on each side.

| | |
|---|---|
| generation | $0.5471 |
| distinctiveness, 154 judgements | $0.7171 |
| density, 77 + 77 judgements | $0.8735 |
| **total** | **$2.1377** (estimate $2.59, ceiling $3.30) |

---

## The result

| measure | control | arm D | p |
|---|---|---|---|
| recognition, all 11 | 23/77 — 29.9% | **29/77 — 37.7%** | 0.394 |
| **the 3 dead personas, NAMED at all** (of 154) | **1** | **10** | **0.0104** |
| the 3 dead personas, recognised | 0/21 | 4/21 | 0.107 |
| the other 8, recognised | 23/56 | 25/56 | — |
| **(a) over-interpretation / 100 words** | 1.68 | **2.01** | 0.178 |
| (c) oracular / 100 words | 1.16 | 1.23 | 0.739 |

**Every persona is proposed at least once under arm D.** The control has two names
that appear in none of its 154 judgements — Marcus Aurelius and Lao Tzu. Arm D has
none. That is the first time in this investigation that no column is empty.

**The gain is where the hypothesis said it would be.** The other eight personas are
flat (23/56 → 25/56); the entire movement is in the three the directive was suspected
of flattening. Their combined naming rate goes from 1 in 154 to 10 in 154, and that
is the only comparison here that clears significance.

**The mechanism is visible in the marginals.** Socrates — the attractor built out of
the question prescription — falls from **32% of all guesses to 19%**. Reply shape
moved with it: replies containing any question fell 96% → 79%, while median length
held (78 → 79 words), so the bands were not disturbed.

---

## NEITHER PRE-DECLARED BRANCH FIRES, and that is the finding

The ruling was set in advance:

> *"If distinctiveness rises and listening density does not worsen, the shape clauses
> come out for everyone… If distinctiveness is flat, the directive is exonerated and
> §8.2 closes."*

**Distinctiveness rose and density worsened.** (a) is up 20% relative. So the first
branch does not apply, and the second is plainly false — the directive is not
exonerated; removing three of its clauses filled two empty columns.

**And the honest caveat runs the other way too: at n=77 this arm is underpowered.**
The headline recognition move is p=0.394 and the (a) regression is p=0.178. Neither
is distinguishable from noise on its own. What survives is the pre-specified
subgroup — the three dead personas, p=0.0104 — and the categorical fact that no
column is empty.

**Do not read "+7.8 points" as the result.** The result is: *the three personas the
directive was suspected of erasing became nameable, the other eight did not move, and
over-interpretation rose by an amount this run cannot resolve.*

---

## The (a) regression has a single likely cause, and it is testable

Of the three removed clauses, exactly one bears on criterion (a):

> *"You may offer an interpretation, but offer it tentatively and ground it in their
> own words"*

That is the hedging instruction. It is the only removed text that constrains **how**
an interpretation is offered rather than **whether** a reply has the three-beat shape.
Removing it and watching over-interpretation rise 20% is the expected consequence, not
a surprise.

**Clauses 1 and 3 — "name something meaningful you notice / take a position" and
"leave an easy opening… one natural, answerable question" — are the two that build the
shape**, and neither has anything to do with (a). The Socrates collapse traces to
clause 3 specifically.

**The arm that is actually indicated has not been run:** remove clauses 1 and 3, KEEP
clause 2's *"offer it tentatively and ground it in their own words"*. If the
distinctiveness gain is carried by 1 and 3 — which the Socrates marginal suggests —
that arm keeps it and gives back the (a) cost. **This is a recommendation, not a
result. No data here separates clause 2's contribution to distinctiveness from the
other two.**

---

## What this does NOT establish

- **Standard mode only.** Every sample is a first message; `STANDARD` and `DEEP` carry
  their own shape clauses and were not touched or measured.
- **One judge.** 94% self-agreement is consistency, not correctness. No human has read
  the 77 arm-D replies.
- **Nothing is claimed about production.** `services/reply_directive.py` is untouched;
  arm D is a harness-local string.
- **The density comparison is 1 call per reply**, per the established protocol, with 1
  parse failure on each side (76/77 usable). It is a single read, not a reliability
  figure.
