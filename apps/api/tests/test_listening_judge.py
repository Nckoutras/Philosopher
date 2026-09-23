"""The Listening judge: the quote audit, and the calibration sample.

No API calls. Everything here is the parts that must be right BEFORE money is
spent — the parser that decides what counts as a finding, and the selection rule
that decides what gets judged.

Run: cd apps/api && pytest tests/test_listening_judge.py -v
"""
import collections
import json
from pathlib import Path

import pytest

from evals import listening as L

B3 = Path(__file__).resolve().parent.parent / "evals/results/2026-09-22T12-59_b3"
REPLY = ("You keep saying the launch is next quarter. Three quarters have gone. "
         "That is not a plan slipping; it is a plan doing its job. What would you "
         "lose if it shipped?")


def _j(**over):
    base = {c: {"v": False, "q": ""} for c in L.CRITERIA}
    base.update(over)
    return json.dumps(base)


# ── the quote audit ─────────────────────────────────────────────────────────

def test_all_no_parses_clean():
    v, err = L.parse_verdict(_j(), REPLY)
    assert err == ""
    assert all(v[c][0] is False for c in L.CRITERIA)


def test_a_yes_with_a_verbatim_quote_is_accepted():
    q = "That is not a plan slipping; it is a plan doing its job."
    v, err = L.parse_verdict(_j(c={"v": True, "q": q}), REPLY)
    assert err == ""
    assert v["c"] == (True, q)


def test_a_yes_whose_quote_is_NOT_in_the_reply_is_a_parse_failure():
    """THE POINT OF THE WHOLE MECHANISM. A judge that flags a fault and cannot
    point at the words has not found the fault, and counting it would put
    unfalsifiable rows into the result."""
    v, err = L.parse_verdict(
        _j(a={"v": True, "q": "you are avoiding the real question"}), REPLY)
    assert v == {}
    assert "not verbatim" in err


def test_a_yes_with_no_quote_at_all_is_a_parse_failure():
    v, err = L.parse_verdict(_j(b={"v": True, "q": ""}), REPLY)
    assert v == {} and "no quote" in err


def test_whitespace_reflow_in_a_quote_is_tolerated():
    """A model that re-wraps a line has still quoted the reply. One that
    paraphrases has not, and the test above is what catches that."""
    q = "That is not a plan slipping;\n   it is a plan doing its job."
    v, err = L.parse_verdict(_j(c={"v": True, "q": q}), REPLY)
    assert err == "", err


def test_case_differences_are_tolerated():
    v, err = L.parse_verdict(
        _j(c={"v": True, "q": "THAT IS NOT A PLAN SLIPPING"}), REPLY)
    assert err == ""


def test_a_NO_may_carry_a_stray_quote_without_failing():
    """Only a yes is evidence. A no with leftover text is sloppy, not wrong, and
    failing it would discard a usable row."""
    v, err = L.parse_verdict(_j(d={"v": False, "q": "whatever"}), REPLY)
    assert err == "" and v["d"][0] is False


@pytest.mark.parametrize("bad", [
    "not json at all",
    '{"a":{"v":true,"q":"x"}}',                         # missing criteria
    '{"a":{"v":"yes","q":""},"b":{"v":false,"q":""},'
    '"c":{"v":false,"q":""},"d":{"v":false,"q":""},"e":{"v":false,"q":""}}',
])
def test_malformed_output_is_an_error_not_a_verdict(bad):
    v, err = L.parse_verdict(bad, REPLY)
    assert v == {} and err


def test_a_fenced_code_block_is_unwrapped():
    v, err = L.parse_verdict("```json\n" + _j() + "\n```", REPLY)
    assert err == "", err


def test_there_is_no_mild_tier():
    """Binary only, by founder ruling. A non-boolean v is refused rather than
    coerced — coercing "slightly" to True is exactly the silent judgement the
    ruling removed."""
    v, err = L.parse_verdict(
        '{"a":{"v":"mild","q":"x"},"b":{"v":false,"q":""},"c":{"v":false,"q":""},'
        '"d":{"v":false,"q":""},"e":{"v":false,"q":""}}', REPLY)
    assert v == {} and "not a boolean" in err


# ── what the judge is shown ─────────────────────────────────────────────────

def test_the_persona_is_not_named_to_the_judge():
    """Knowing a reply is Lao Tzu's would lean criterion (c) before it is made."""
    block = L.conversation_block("I am tired.", REPLY)
    for slug in ("lao_tzu", "Lao Tzu", "socrates", "Socrates"):
        assert slug not in block
    assert "I am tired." in block and REPLY in block


def test_the_rubric_states_the_inverted_criterion():
    assert "this is the one question where YES is the good answer" in L.RUBRIC


def test_the_rubric_does_not_ban_ending_on_a_question():
    """Three readings showed preferred replies ending on questions. If this
    sentence is ever removed, criterion (b) silently becomes 'ends with a
    question', which is the thing it was written NOT to be."""
    assert "Ending on a question is NOT itself a fault" in L.RUBRIC


# ── the calibration sample ──────────────────────────────────────────────────

@pytest.mark.skipif(not (B3 / "completions.jsonl").exists(),
                    reason="B3 completions.jsonl is gitignored; local runs only")
class TestSelection:
    def test_it_is_44_replies(self):
        assert len(L.select_calibration(B3)) == 44

    def test_four_per_persona(self):
        c = collections.Counter(r["persona_slug"] for r in L.select_calibration(B3))
        assert set(c.values()) == {4} and len(c) == 11

    def test_problems_are_spread_not_clustered(self):
        """The first version of the rule shuffled every persona with one shared
        seed, so every persona drew the SAME permutation: 11x P01, 11x P06,
        10x P07, 1x P09. Three problems carried three quarters of the set."""
        c = collections.Counter(r["problem_id"] for r in L.select_calibration(B3))
        assert max(c.values()) - min(c.values()) <= 2, dict(c)

    def test_the_eleven_blind3_replies_are_all_in(self):
        chosen = {r["sample_id"] for r in L.select_calibration(B3)}
        fixed = set(L.blind3_b3_sample_ids(B3))
        assert len(fixed) == 11
        assert fixed <= chosen

    def test_it_is_deterministic(self):
        a = [r["sample_id"] for r in L.select_calibration(B3)]
        b = [r["sample_id"] for r in L.select_calibration(B3)]
        assert a == b == sorted(a)

    def test_deep_replies_are_excluded(self):
        assert all(r["mode"] != "deep" for r in L.select_calibration(B3))

    def test_only_sonnet_replies(self):
        assert all(r["plan"] == "pro" for r in L.select_calibration(B3))


# ── cost, so a surprise bill is a failing test rather than a surprise ───────

def test_the_opus_price_is_the_current_one_not_the_retired_one():
    """$15/$75 is Opus 4.1, retired. Opus 5 is $5/$25, verified against the
    pricing page 2026-09-23. The first estimate in this workstream used the
    retired rate and was 3x too high."""
    assert (L.PRICE_IN, L.PRICE_OUT) == (5.0, 25.0)


def test_temperature_is_not_sent_because_opus_5_rejects_it():
    """The ratified design said temperature 0. Opus 5 returns
    400 `temperature` is deprecated for this model, and all 88 judgements of the
    first attempt failed on it. Sending it again would fail an entire run, so it
    is pinned here rather than left to memory."""
    import inspect
    assert L.TEMPERATURE is None
    assert L.JUDGE_MODEL == "claude-opus-5"
    assert "temperature=" not in inspect.getsource(L.judge_one)


# ── the mode flag, and why it exists ───────────────────────────────────────

@pytest.mark.skipif(not (B3 / "completions.jsonl").exists(),
                    reason="B3 completions.jsonl is gitignored; local runs only")
class TestModes:
    """THE FIRST FULL RUN JUDGED 77 REPLIES AND WOULD HAVE BEEN REPORTED AS 110.

    The CLI's non-calibration path filtered `mode != "deep"`, so "the full B3
    Sonnet 110" silently meant the 77 standard-mode replies. It was caught on a
    row count, not by anything in the code. These tests are the mechanism that
    replaces noticing — the repository's own failure log is mostly about habits
    standing in for mechanisms.
    """

    def test_all_is_110_standard_is_77_deep_is_33(self):
        assert len(L._pro_completions(B3, "all")) == 110
        assert len(L._pro_completions(B3, "standard")) == 77
        assert len(L._pro_completions(B3, "deep")) == 33

    def test_standard_and_deep_partition_all(self):
        """No reply may be in neither bucket, or a 'full' run silently drops it."""
        a = {r["sample_id"] for r in L._pro_completions(B3, "all")}
        s = {r["sample_id"] for r in L._pro_completions(B3, "standard")}
        d = {r["sample_id"] for r in L._pro_completions(B3, "deep")}
        assert s | d == a
        assert s & d == set()

    def test_the_default_is_standard_and_is_therefore_not_the_full_run(self):
        """Stated as a test rather than a comment: a bare --run is 77, not 110.
        The CLI prints the mode on every run so the number is never unlabelled."""
        assert L.build_parser_default_mode() == "standard"

    def test_the_calibration_set_is_standard_only_by_design(self):
        """Not an oversight of the same kind: the deep band is a different
        instruction, and calibrating across both would mix two populations."""
        assert all(r["mode"] != "deep" for r in L.select_calibration(B3))


# ── the COUNT variant, and the write pre-flight ────────────────────────────

class TestCounts:
    """The count rubric exists because a binary per-reply flag is length-biased:
    B3's deep replies run 127 words against arm B's 62, and pooled across arms
    replies over 120 words are flagged 96% of the time."""

    R = "The cat sat on the mat. A dog barked twice."

    def test_counts_and_quotes_parse(self):
        v, err = L.parse_counts(
            '{"a":{"n":2,"q":["The cat sat","A dog barked"]},"c":{"n":0,"q":[]}}', self.R)
        assert err == ""
        assert v["a"][0] == 2 and v["c"] == (0, [])

    def test_n_must_equal_the_number_of_quotes(self):
        """Otherwise a judge can claim three instances and evidence one."""
        v, err = L.parse_counts('{"a":{"n":3,"q":["The cat sat"]},"c":{"n":0,"q":[]}}', self.R)
        assert v == {} and "but 1 quotes" in err

    def test_every_quote_must_still_be_verbatim(self):
        v, err = L.parse_counts(
            '{"a":{"n":1,"q":["the hamster sang"]},"c":{"n":0,"q":[]}}', self.R)
        assert v == {} and "not verbatim" in err

    def test_the_two_rubrics_define_the_criteria_identically(self):
        """A difference between the binary and count readings must be about the
        QUESTION asked, not about a rewritten definition."""
        # Whitespace-normalised: the two rubrics wrap their lines differently, so
        # a raw substring test fails on a line break rather than on a wording
        # change. That is exactly the false alarm this test must not produce.
        flat_bin = " ".join(L.RUBRIC.split())
        flat_cnt = " ".join(L.RUBRIC_COUNT.split())
        for phrase in ("hiding, avoiding, evading, or failing to",
                       "Asserting their inner state as settled fact is",
                       "quotable rather than said to this particular person"):
            assert phrase in flat_bin, phrase
            assert phrase in flat_cnt, phrase
        # (c) differs by ONE grammatical number — the binary rubric says "a line
        # shaped to be quotable", the count rubric "lines shaped to be quotable",
        # because counting requires the plural. That is the only divergence, and
        # asserting the singular form here is what caught it.
        assert "a line shaped" in flat_bin and "lines shaped" in flat_cnt

    def test_count_mode_writes_its_own_schema(self, tmp_path):
        j = L.Judgement(sample_id="s", persona_slug="p", problem_id="P", mode="deep",
                        plan="pro", call=1, verdicts={"a": (2, ["x", "y"]), "c": (0, [])})
        p = tmp_path / "c.csv"
        L.write_csv(p, [j], count=True)
        head = p.read_text(encoding="utf-8").splitlines()[0]
        assert "a_n" in head and "c_n" in head
        assert "b_v" not in head, "count mode asks only (a) and (c)"

    def test_write_csv_accepts_count_which_is_how_a_paid_run_was_lost(self):
        """write_csv once did not take `count` while main() passed it. All 99
        API calls completed and the process died on the TypeError, losing every
        judgement and ~$0.75. main() now pre-flights the write before spending."""
        import inspect
        assert "count" in inspect.signature(L.write_csv).parameters
        assert "count" in inspect.signature(L.judge_all).parameters
        src = inspect.getsource(L.main)
        assert src.index("write_csv(out, [_probe]") < src.index("asyncio.run(judge_all"), \
            "the write pre-flight must come BEFORE any API call"


class TestDensityIsTheStandardMetric:
    """FOUNDER RULING 2026-09-23: density is the standard (a)/(c) metric and the
    binary rate is never reported alone.

    The reason is measured, not stylistic. On the same 98 deep replies the two
    disagree about which arm is best, completely:

        binary (a):        baseline 84%   arm B 59%   B3 82%
        (a) per 100 words: baseline 3.68  arm B 2.92  B3 1.91

    Every arm in this project changes reply length, so a per-reply flag can never
    rank arms by itself.
    """

    COUNTS = [{"sample_id": "s1", "a_n": "2", "c_n": "1"},
              {"sample_id": "s2", "a_n": "0", "c_n": "0"}]
    WORDS = {"s1": 100, "s2": 100}
    BINARY = [{"sample_id": "s1", "a_v": "1", "c_v": "1"},
              {"sample_id": "s2", "a_v": "0", "c_v": "0"}]

    def test_it_returns_density_and_the_binary_rate_together(self):
        out = L.summarise_density(self.COUNTS, self.WORDS, self.BINARY)
        assert out["a"]["per_100_words"] == 1.0
        assert out["a"]["binary_rate"] == 50.0
        assert out["c"]["per_100_words"] == 0.5

    def test_the_binary_rate_cannot_be_returned_without_density(self):
        """The whole point: reporting one without the other must take deliberate
        effort, so the shape enforces it."""
        for rows in (self.BINARY, None):
            out = L.summarise_density(self.COUNTS, self.WORDS, rows)
            for c in L.COUNT_CRITERIA:
                assert "per_100_words" in out[c]
                assert "binary_rate" in out[c]

    def test_binary_rate_is_None_when_no_binary_run_exists(self):
        out = L.summarise_density(self.COUNTS, self.WORDS, None)
        assert out["a"]["binary_rate"] is None
        assert out["a"]["per_100_words"] == 1.0

    def test_it_carries_the_denominator_so_a_rate_is_never_unanchored(self):
        out = L.summarise_density(self.COUNTS, self.WORDS, self.BINARY)
        assert out["a"]["n_replies"] == 2
        assert out["a"]["total_words"] == 200
