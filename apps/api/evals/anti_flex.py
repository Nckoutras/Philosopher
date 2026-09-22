"""Anti-flex matcher for the §8.2 eval harness.

WHY THIS EXISTS. `anti_flexing.never_unprompted` is populated for all 11 personas
and READ BY NOTHING — not `system_base.jinja2`, not `check_persona_forbidden`,
not any service. Measured: of the 90 topics across the 11 lists, exactly 5 (6%)
are reachable by `check_persona_forbidden`, because that function scores the
persona's forbidden LEXICON, which is mostly pop-philosophy cliché rather than
self-reference. Marcus's lexicon is "amor fati", "the obstacle is the way",
"trust the universe"; his never_unprompted is Rome, the Senate, the legions,
Faustina, Rusticus. They barely overlap.

So the topics need their own matcher, and the topics are not phrases — they are
prose descriptions ("own teachers (Rusticus, Apollonius, Fronto)"). The surface
forms live in philosopher_brain/evals/anti_flex_terms.json, hand-authored and
founder-approved, each entry carrying one example that must hit and one that
must not. tests/test_anti_flex_terms.py runs all 180.

THIS IS SCORED, NEVER GATED. It runs in the harness against a stored completion.
It is not wired into any production path and must not be: production's only
persona-lexicon gate is `check_persona_forbidden`, whose 1.09% firing rate was
measured over 826 replies before it was wired (UAT2-004).

THE THREE RULES THAT DO THE WORK
--------------------------------

1. CASE SENSITIVITY IS PER CHARACTER, NOT PER TERM. An uppercase character in
   the term must be uppercase in the reply; a lowercase character matches either
   case. This keeps the discriminator that matters —

       'the Senate'      does NOT match "a senate of your own making"
       'Meditations'     does NOT match "your meditations are circling"
       'the Shadow'      does NOT match "a shadow over everything"
       'The Prince'      does NOT match "the prince you work for"

   — while still matching at the start of a sentence:

       'my master'       DOES match "My master broke my leg"
       'the Enchiridion' DOES match "The Enchiridion begins with this"

   A per-TERM rule (case-sensitive iff the term contains any capital) fails that
   second group for every mixed-case term beginning with an article. Four of the
   five failures in the first validation pass were exactly that.

2. A TERM THE USER USED IS EXEMPT, for that sample, matched case-insensitively.
   From eval_suite_spec.md Test 3: "A reply that mentions a peer because the
   USER mentioned the peer is exempt." This is what keeps 'Athens' in a user's
   holiday from scoring as a Socrates flex, without hand-tuning the term list.

3. COVERAGE IS DECLARED. Every entry carries coverage full | partial | framed.
   `partial` means the set is unbounded by construction (Wilde's epigrams,
   Machiavelli's aphorisms, Orwell's anecdotes) and the list catches the
   most-recited. `framed` means the bare term is ordinary language and only the
   naming frame is a hit ('wu wei means', not 'wu wei'). A run summary that does
   not carry the split invites reading a clean sheet as "no flexing", which for
   the 13 non-full entries it does not mean.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

TERMS_PATH = (
    Path(__file__).resolve().parent.parent
    / "philosopher_brain" / "evals" / "anti_flex_terms.json"
)


@dataclass
class AntiFlexHit:
    entry_id: str
    never_unprompted: str
    coverage: str
    matched: str          # the term or regex that fired
    matched_text: str     # the span as it appears in the reply


@dataclass
class AntiFlexResult:
    persona_slug: str
    passed: bool
    hits: list[AntiFlexHit] = field(default_factory=list)
    entries_checked: int = 0


@lru_cache(maxsize=1)
def load_terms(path: str | None = None) -> dict:
    p = Path(path) if path else TERMS_PATH
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _term_pattern(term: str) -> str:
    """Per-character case rule — see rule 1 in the module docstring.

    Boundaries are (?<!\\w) / (?!\\w) rather than \\b, because terms are
    multi-word and may begin or end with non-word characters ("Sant'Andrea",
    "Niten Ichi-ryū").
    """
    out = []
    for ch in term:
        if ch.isupper():
            out.append(re.escape(ch))
        elif ch.islower():
            out.append("[" + re.escape(ch) + re.escape(ch.upper()) + "]")
        else:
            out.append(re.escape(ch))
    return r"(?<!\w)" + "".join(out) + r"(?!\w)"


@lru_cache(maxsize=4096)
def _compiled(term: str) -> re.Pattern:
    return re.compile(_term_pattern(term))


def _user_used(term: str, user_text: str) -> bool:
    """Rule 2. Fully case-insensitive: the user may type 'athens' and still have
    put the word in the conversation."""
    if not user_text:
        return False
    return re.search(
        r"(?<!\w)" + re.escape(term) + r"(?!\w)", user_text, re.IGNORECASE
    ) is not None


def entry_hits(entry: dict, reply: str, user_text: str = "") -> list[AntiFlexHit]:
    """Every term/regex in ONE entry that fires on `reply`."""
    hits: list[AntiFlexHit] = []
    for term in entry.get("terms", []):
        if _user_used(term, user_text):
            continue
        m = _compiled(term).search(reply)
        if m:
            hits.append(AntiFlexHit(
                entry_id=entry["id"],
                never_unprompted=entry["never_unprompted"],
                coverage=entry["coverage"],
                matched=term,
                matched_text=m.group(0),
            ))
    for spec in entry.get("regexes", []):
        flags = re.IGNORECASE if spec.get("ignorecase") else 0
        m = re.search(spec["pattern"], reply, flags)
        if not m:
            continue
        if user_text and re.search(spec["pattern"], user_text, flags):
            continue
        hits.append(AntiFlexHit(
            entry_id=entry["id"],
            never_unprompted=entry["never_unprompted"],
            coverage=entry["coverage"],
            matched=f"/{spec['pattern']}/",
            matched_text=m.group(0),
        ))
    return hits


def check_anti_flex(reply: str, persona_slug: str, user_text: str = "") -> AntiFlexResult:
    """Score one reply against one persona's never_unprompted surface forms.

    `user_text` is the user message that produced the reply. Passing it is not
    optional in the harness: without it every persona that names a peer the user
    named scores a false hit, which is the exemption the spec requires.
    """
    entries = load_terms()["personas"].get(persona_slug, [])
    hits: list[AntiFlexHit] = []
    for entry in entries:
        hits.extend(entry_hits(entry, reply, user_text))
    return AntiFlexResult(
        persona_slug=persona_slug,
        passed=(len(hits) == 0),
        hits=hits,
        entries_checked=len(entries),
    )


def coverage_summary(persona_slug: str | None = None) -> dict[str, int]:
    """full / partial / framed counts — for the run manifest.

    The harness records this beside the hit count so a zero is read as "no hits
    on N fully-covered topics", never as "no flexing".
    """
    data = load_terms()["personas"]
    slugs = [persona_slug] if persona_slug else list(data)
    out: dict[str, int] = {}
    for s in slugs:
        for e in data[s]:
            out[e["coverage"]] = out.get(e["coverage"], 0) + 1
    return out
