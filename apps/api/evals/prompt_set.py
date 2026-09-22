"""The fixed prompt set: 110 samples, 33 of them deep.

WHERE 110 COMES FROM. `philosopher_brain/evals/ten_modern_problems.json` holds
10 modern situations and `PERSONA_REGISTRY` holds 11 personas. 10 x 11 = 110,
which is the founder-locked run size. The JSON is the only fixed prompt set that
exists in this repository — brain, tests and the UAT filings were all checked and
there is no other.

TWO STALE FIELDS IN THAT JSON, deliberately not read here. `personas_strong_fit`
and `personas_weak_fit` name `nietzsche`, `freud`, `jung` and `de_beauvoir` —
four slugs that do not exist in PERSONA_REGISTRY, and there has never been a
Nietzsche persona. `minimum_replies_required: 6` is from the same six-persona
world. Every persona gets every problem here; fit is not consulted. The fields
are left in the JSON rather than edited out, because the file is also the record
of what the suite was designed against.

MODE. Every sample is a FIRST MESSAGE — that is what the prompt set contains,
and it is the position the JSON's own `_implementation_notes` describe. 33 of
them (3 problems x 11 personas) are additionally flagged DEEP, which in
production means `conversations.deep_mode` is on and `_deepen_directive` is
appended. That combination is not a corner case: a deep-mode first reply is
instructed up to `reflective_reply_max_words` and must still keep its
`first_message_max_words` cap, which is exactly the orthogonality step 0 built
`check_brevity(..., reflective=)` for. Without deep samples the mode branch would
ship untested by the instrument that is supposed to exercise it.

WHY THESE THREE PROBLEMS. P03 (burnout, existential_work), P08 (recurring dream,
depth_symbolic) and P10 (running out of time, mortality_time) spread the deep set
across three categories rather than clustering it in one register. P08 also
carries `expected_phenomenology_match: null` — the only problem that does — so at
least eleven deep samples are generated with the phenomenology bridge NOT firing.
That keeps mode and bridge from being perfectly confounded across the deep set,
which they would be if all three deep problems had a bridge match.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from personas import PERSONA_REGISTRY

PROBLEMS_PATH = (
    Path(__file__).resolve().parent.parent
    / "philosopher_brain" / "evals" / "ten_modern_problems.json"
)

# Founder-locked, 2026-09-22. Changing this changes what a run measures, so it
# is a constant with a reason rather than a CLI flag.
DEEP_PROBLEM_IDS = frozenset({
    "P03_burnout_anxiety_at_30",
    "P08_recurring_dream_water",
    "P10_running_out_of_time",
})

# English-only v1 (founder-locked). The JSON carries user_message_el beside every
# user_message_en; the Greek arm is a later run, not a v1 one.
MESSAGE_FIELD = "user_message_en"


@dataclass(frozen=True)
class Sample:
    problem_id: str
    persona_slug: str
    mode: str                      # "standard" | "deep"
    user_message: str
    category: str
    forbidden_modern_terms: tuple[str, ...]

    @property
    def sample_id(self) -> str:
        return f"{self.problem_id}::{self.persona_slug}::{self.mode}"

    @property
    def deep(self) -> bool:
        return self.mode == "deep"


def load_problems() -> list[dict]:
    with open(PROBLEMS_PATH, encoding="utf-8") as fh:
        return json.load(fh)["problems"]


def build_samples() -> list[Sample]:
    """The 110, in a stable order: problem-major, then registry order.

    Stable ordering matters for diffing two runs — a row in `scores.csv` should
    mean the same thing in both files without a join on anything but sample_id,
    and a reader comparing two runs by eye should see the same sequence.
    """
    samples: list[Sample] = []
    for problem in load_problems():
        pid = problem["id"]
        mode = "deep" if pid in DEEP_PROBLEM_IDS else "standard"
        terms = tuple(
            problem.get("auto_grade_checks", {}).get("forbidden_modern_terms_in_reply", [])
        )
        for slug in PERSONA_REGISTRY:
            samples.append(Sample(
                problem_id=pid,
                persona_slug=slug,
                mode=mode,
                user_message=problem[MESSAGE_FIELD],
                category=problem["category"],
                forbidden_modern_terms=terms,
            ))
    return samples


def prompt_set_hash() -> str:
    """Digest of every input a run consumed — PROMPTS AND SCORING DATA BOTH.

    Recorded in the manifest and gated by compare.py. Two runs scored against
    different inputs are not comparable, and the failure is silent without this:
    the sample_ids line up perfectly either way.

    IT COVERS forbidden_modern_terms, AND IT DID NOT USED TO. The first version
    hashed sample_id and user_message only. Editing a problem's
    `auto_grade_checks.forbidden_modern_terms_in_reply` therefore changed what a
    run MEASURED while leaving the hash identical — so compare.py would have
    passed its gate and attributed the whole move in modern_leak_rate to
    whatever the arm changed. Found when the founder ruled "phone" out of P01
    and predicted the hash would move: it did not.

    `mode` needs no entry of its own; it is already part of sample_id.
    """
    NUL = bytes([0])
    UNIT = chr(31)
    h = hashlib.sha256()
    for s in build_samples():
        h.update(s.sample_id.encode("utf-8"))
        h.update(NUL)
        h.update(s.user_message.encode("utf-8"))
        h.update(NUL)
        # scoring input, not prompt input — see the docstring
        h.update(UNIT.join(s.forbidden_modern_terms).encode("utf-8"))
        h.update(NUL)
    return h.hexdigest()[:16]
