"""The crisis response answers in the language the person wrote in.

WHY THIS MATTERS MORE THAN IT LOOKS. Everything else in this PR is about
HEARING a Greek speaker in crisis. This is about ANSWERING one. If the gate
fires correctly and then replies in English, the app has visibly stopped the
conversation and then failed to communicate — which is arguably worse than the
silence it replaced, because the person now knows something happened and cannot
read what.

THE TRIPWIRE. The Greek template currently holds a PENDING_COPY placeholder,
and test_greek_safety_copy_is_not_a_placeholder FAILS while it does. That test
is RED by design on this branch and goes green in the commit that pastes the
founder-approved Greek copy. It is a gate, not a chore: crisis copy is the last
thing between a person in crisis and no help at all, and a placeholder reaching
production there is not a cosmetic defect.

Greeklish routes to GREEK since SAFETY-003 (founder ruling 2026-09-28). It used
to route to English, deliberately and on the record: dominant_language counts
codepoints, so latin-script Greek reads as English. The ruling reversed that for
the crisis response only, through safety_service.crisis_language (Greek script OR
any greeklish lexicon entry). dominant_language itself is unchanged, and the
tests below pin both halves: the detector still says English, the crisis
response now answers in Greek.
"""
import inspect
from pathlib import Path

import pytest

from services.prompt_builder import PromptBuilder
from services.safety_service import crisis_language
from text_utils import dominant_language

PENDING = "PENDING_COPY"


@pytest.fixture
def builder():
    return PromptBuilder()


# ── The tripwire ──────────────────────────────────────────────────────────────

def test_greek_safety_copy_is_not_a_placeholder(builder):
    """RED until the founder-approved Greek crisis copy is pasted in.

    Do not satisfy this by deleting the assertion or by machine-translating the
    English template. The English copy is country-neutral by design; the Greek
    one has to be written, with Greek crisis-support guidance.
    """
    response = builder.build_safety_response(language="Greek")
    assert PENDING not in response, (
        "The Greek crisis response is still a placeholder. Paste the approved "
        "copy into prompts/safety_response_el.jinja2."
    )


# ── Routing ───────────────────────────────────────────────────────────────────

def test_greek_input_selects_the_greek_template(builder):
    greek = builder.build_safety_response(language="Greek")
    english = builder.build_safety_response(language="English")
    assert greek != english, "Greek and English crisis responses are identical"


def test_english_is_the_default(builder):
    assert builder.build_safety_response() == builder.build_safety_response(language="English")


def test_an_unknown_language_falls_back_to_english(builder):
    """Never an empty response on this path. An English crisis message is worse
    than a Greek one for a Greek speaker and far better than none."""
    assert builder.build_safety_response(language="Klingon") == \
           builder.build_safety_response(language="English")


@pytest.mark.parametrize("text,expected", [
    ("θέλω να αυτοκτονήσω", "Greek"),
    ("δεν αντέχω άλλο", "Greek"),
    ("i want to kill myself", "English"),
    ("den antexo allo", "English"),          # the DETECTOR still says English (unchanged)
    ("", "English"),                          # empty -> English, never a crash
])
def test_language_routing_of_real_crisis_inputs(text, expected):
    assert dominant_language([text]) == expected


@pytest.mark.parametrize("text,expected", [
    ("θέλω να αυτοκτονήσω", "Greek"),
    ("i want to kill myself", "English"),
    # FLIPPED DELIBERATELY — SAFETY-003 ruling 2026-09-28: greeklish -> the Greek
    # crisis text (112 / 1018 / 10306). It was "English, by design" until then.
    ("den antexo allo", "Greek"),
    ("thelo na pethano", "Greek"),
    ("8elw na pe8anw", "Greek"),
    ("den thelo pia na zo", "Greek"),
    ("", "English"),
])
def test_the_crisis_response_language(text, expected):
    assert crisis_language([text]) == expected


def test_greeklish_routing_is_a_decision_not_an_accident():
    """SAFETY-003 ruling 2026-09-28 — FLIPPED from "greeklish answers in English".

    dominant_language still counts Greek vs latin codepoints and still calls
    greeklish English; that is asserted, because letters and memory rely on it.
    The crisis response no longer uses it alone: the greeklish entry that trips
    the gate also routes the answer to the Greek template.
    """
    from services.safety_service import SafetyService
    import asyncio

    result = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        SafetyService().check_input("den antexo allo thelo na pethano")
    )
    assert result.level == "high", "greeklish must still trip the gate"
    assert dominant_language(["den antexo allo thelo na pethano"]) == "English"
    assert crisis_language(["den antexo allo thelo na pethano"]) == "Greek"


def test_english_prose_about_greek_topics_stays_english():
    """The greeklish clause must not capture English. These mention Greece and
    Greek words in English and match no greeklish entry."""
    for text in ("I want to kill myself after reading Plato in Athens",
                 "Is eudaimonia the same as happiness?",
                 "My father died on Saturday. I keep going to call him."):
        assert crisis_language([text]) == "English", text


# ── Constraints the Greek template inherits from the English one ──────────────

def test_no_user_name_parameter_still(builder):
    """Adding `language` must not have opened a name-injection path."""
    sig = inspect.signature(builder.build_safety_response)
    assert "user_name" not in sig.parameters
    assert set(sig.parameters) == {"level", "language"}


def test_greek_template_carries_no_country_specific_numbers():
    """No OTHER country's numbers in the Greek template.

    Narrowed 2026-09-16. This once stood for "no helpline number at all", per the
    2026-09-02 ruling; the founder reversed that and the Greek template now
    carries 1018/10306 (see the test below). What survives the reversal is the
    part that was always right: a Greek speaker must never be handed a US or UK
    number. The numbers listed here are exactly the ones that would be wrong.
    """
    path = Path(__file__).resolve().parents[1] / "prompts" / "safety_response_el.jinja2"
    body = path.read_text(encoding="utf-8")
    for number in ("988", "741741", "116123"):
        assert number not in body, f"country-specific number {number} in Greek template"


def test_greek_copy_is_single_for_all_suppression_levels(builder):
    """Same rule as English: one copy, no level-differentiated crisis text."""
    high = builder.build_safety_response(level="high", language="Greek")
    medium = builder.build_safety_response(level="medium", language="Greek")
    critical = builder.build_safety_response(level="critical", language="Greek")
    assert high == medium == critical


# ── The approved Greek helplines (2026-09-16) ─────────────────────────────────

GREEK_HELPLINES = ("1018", "10306", "112")


def test_the_greek_template_carries_the_approved_helplines():
    """Founder-approved 2026-09-16, reversing the 2026-09-02 no-numbers ruling.

    Checked against the FILE and by NUMBER, because this is the assertion that
    would catch the failure the original ruling was afraid of: a number silently
    edited, dropped in a reword, or lost to a bad merge. A crisis response that
    has quietly stopped naming a helpline looks completely normal on screen.

      1018  — Γραμμή Παρέμβασης για την Αυτοκτονία (ΚΛΙΜΑΚΑ), 24/7
      10306 — Γραμμή Ψυχοκοινωνικής Υποστήριξης, 24/7, free
      112   — EU emergency

    These were verified against published sources, NOT by dialling them. This
    test proves the numbers are present and unchanged since the lock; it cannot
    prove they still ring. That obligation is named in the template header.
    """
    path = Path(__file__).resolve().parents[1] / "prompts" / "safety_response_el.jinja2"
    body = path.read_text(encoding="utf-8")
    rendered = PromptBuilder().build_safety_response(level="high", language="Greek")

    for number in GREEK_HELPLINES:
        assert number in body, f"helpline {number} missing from the Greek template"
        # Present in the FILE is not present in the OUTPUT — a number stranded in
        # the jinja comment header would pass the check above and reach nobody.
        assert number in rendered, f"helpline {number} never reaches the rendered response"


# ── The English crisis text (SAFETY-003, founder ruling 2026-09-28) ──────────

APPROVED_ENGLISH = (
    "Some of what you've shared sounds heavy, and your safety matters more than this conversation.\n"
    "\n"
    "If you are in immediate danger, call your local emergency number now.\n"
    "\n"
    "In the US, call or text 988. In the UK and Ireland, call Samaritans on 116 123. "
    "Anywhere else, find a free, confidential helpline at findahelpline.com. You can "
    "also reach out to a trusted person near you, or a qualified mental health professional.\n"
    "\n"
    "The Wise Room can offer reflection, but it cannot provide crisis support, "
    "diagnosis or medical treatment. This conversation will pause here so that comes first."
)


def test_the_english_crisis_text_is_the_approved_copy_verbatim():
    """COPY LOCK. Approved verbatim by the founder, 2026-09-28. It replaced the
    country-neutral text this file used to pin ("The reversal is Greek-only"):
    the ruling gave English speakers resources too — US 988, UK/Ireland 116 123,
    and findahelpline.com for everywhere else. A reword goes through the founder."""
    rendered = PromptBuilder().build_safety_response(level="high", language="English")
    assert rendered == APPROVED_ENGLISH


def test_the_english_template_carries_no_greek_numbers():
    """What survives from the old country-neutral test: an English speaker is
    never handed the Greek helplines."""
    rendered = PromptBuilder().build_safety_response(level="high", language="English")
    for number in ("1018", "10306"):
        assert number not in rendered, f"Greek helpline {number} in the English copy"


# ── SAFETY-003: the resources, the links, and the rotation list stay one set ──

# THE ROTATION RE-CHECK LIST (SAFETY-003, founder ruling 2026-09-28). Every entry
# is re-verified on every doc rotation; a dead entry is launch-blocking. The same
# list, with sources and verification dates, is in the SAFETY-003 backlog entry.
CRISIS_RESOURCES = {"988", "116 123", "findahelpline.com", "112", "1018", "10306"}

_WEB = Path(__file__).resolve().parents[3] / "apps" / "web" / "lib" / "crisisLinks.tsx"


def _rendered_crisis_texts() -> str:
    b = PromptBuilder()
    return b.build_safety_response(language="English") + "\n" + b.build_safety_response(language="Greek")


def test_crisis_resources_are_linked_and_listed():
    """One set, three places: the copy, the web links, the rotation list.

    A number added to the copy without a link would be untappable; a link for a
    number the copy dropped would be dead code nobody re-checks; a resource off
    the rotation list would never be re-verified. Checked here, in the backend
    job, because the web tests run under continue-on-error (TD-86)."""
    import re
    rendered = _rendered_crisis_texts()
    for resource in CRISIS_RESOURCES:
        assert resource in rendered, f"{resource} is on the list but in neither template"

    # No OTHER phone-like number (3+ digits, optionally one space group) may appear.
    numbers = set(re.findall(r"(?<!\d)\d{3}(?: \d{3})?(?!\d)|(?<!\d)\d{4,}(?!\d)", rendered))
    assert numbers <= CRISIS_RESOURCES, f"unlisted numbers in the crisis copy: {numbers - CRISIS_RESOURCES}"

    web_keys = set(re.findall(r"^\s*'([^']+)':\s*'(?:tel:|https://)", _WEB.read_text(encoding="utf-8"), re.M))
    assert web_keys == CRISIS_RESOURCES, f"web links {web_keys} != rotation list {CRISIS_RESOURCES}"


def test_every_crisis_call_site_uses_crisis_language():
    """SAFETY-003 wiring. A build_safety_response call that picks its language with
    dominant_language alone would send greeklish back to English."""
    import re
    services = Path(__file__).resolve().parents[1] / "services"
    calls = 0
    for path in services.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for m in re.finditer(r"build_safety_response\((.*?)\)\s*$", src, re.S | re.M):
            if path.name == "prompt_builder.py":
                continue
            calls += 1
            assert "language=crisis_language(" in m.group(1), f"{path.name}: {m.group(0)[:120]!r}"
    assert calls == 9, f"expected the 9 known crisis call sites, found {calls}"
