# -*- coding: utf-8 -*-
"""The post-generation output list matches whole phrases, not substrings (ruling 2026-09-25).

check_output compared phrases with `p in normalized`, a plain substring test, and the
list held ordinary reflective English. Measured 2026-09-25: six of six sentences about
mortality — the product's subject — were flagged. Since #739 the same list gates eleven
more surfaces (letters, mirrors, insights, You-vs-You …), so a false positive there
withholds a letter or ends a comparison.

Ruled: word boundaries; drop "least painful", "most effective way to", "best method",
"method would be", "where to buy"; keep "way to end" only as "way to end it" / "way to
end your life". Two drops are NARROWED rather than removed so a genuinely
method-seeking sentence is still caught: "most effective way to die", "least painful
way to die". Plural forms of kept phrases are listed explicitly, because strict
boundaries no longer let "lethal dose" match "lethal doses".

Run: cd apps/api && pytest tests/test_output_lexicon_word_bounded.py -v
"""
import pytest

from services.safety_lexicons import OUTPUT_RISK_EN, OUTPUT_RISK_GL, OUTPUT_RISK_GR
from services.safety_service import safety_service

# The measured false positives: ordinary prose about death and loss.
PHILOSOPHICAL = [
    "The only way to endure the fact of death is to stop arguing with it.",
    "Perhaps the least painful truth is that everything ends.",
    "The most effective way to live with mortality is to attend to today.",
    "Accepting death as inevitable was, then, a method would be too strong a word.",
    "There is no best method for grief.",
    "You found a way to endorse your own fear without obeying it.",
    "Grief is not a problem with a way to end its hold on you by next week.",
    "Where to buy the time to mourn is the question the week never answers.",
]

# Method-seeking output that must still be caught.
HARMFUL = [
    "A lethal dose of that medication is",
    "Lethal doses vary by weight",
    "The way to end it would be",
    "If you are looking for a way to end your life",
    "the easiest way to die is",
    "the most effective way to die would be",
    "the least painful way to die is",
    "There are painless ways to go",
    "Painless methods include",
    "how to jump from",
    "how to end your life",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("text", PHILOSOPHICAL)
async def test_reflective_prose_about_death_is_not_flagged(text):
    assert (await safety_service.check_output(text)).level == "none"


@pytest.mark.asyncio
@pytest.mark.parametrize("text", HARMFUL)
async def test_method_seeking_output_is_still_flagged(text):
    result = await safety_service.check_output(text)
    assert result.level == "high" and result.category == "output_harm"


@pytest.mark.asyncio
@pytest.mark.parametrize("phrase", OUTPUT_RISK_GR + OUTPUT_RISK_GL)
async def test_every_greek_and_greeklish_phrase_still_matches_in_a_sentence(phrase):
    """The Greek entries are whole words and phrases, so boundaries keep every one."""
    result = await safety_service.check_output(f"Αυτό είναι: {phrase}, και τίποτα άλλο.")
    assert result.level == "high", phrase


def test_the_ruled_drops_are_gone():
    for dropped in ("least painful", "most effective way to", "best method",
                    "method would be", "where to buy", "way to end"):
        assert dropped not in OUTPUT_RISK_EN, dropped


@pytest.mark.asyncio
async def test_a_flag_is_the_phrase_that_matched_not_a_longer_word():
    result = await safety_service.check_output("It was a lethal dosed error.")
    assert result.level == "none", "'lethal dose' must not match inside 'dosed'"
