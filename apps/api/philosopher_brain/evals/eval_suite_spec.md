# PHILOSOPHER — Evaluation Suite Specification
# Version: 1.0.0
# Last reviewed: 2026-04-27

## Purpose

This document specifies the four core evaluation tests that gate every prompt
or persona-config change before it ships to production. The personas are the
product. If they fail these tests, nothing else matters — UI polish, RAG
sophistication, and pricing all sit on top of the personas.

The eval suite must be runnable:

1. Locally during development (single persona, single test).
2. In CI against any prompt or config change (full suite, fast subset).
3. Weekly in production, against real (consented) conversations or held-out
   replays, to catch drift after deploys.

## The four tests

### Test 1 — Ten Modern Problems (DISTINCTIVENESS)

**What it measures:** Whether the six personas produce meaningfully different
replies to the same modern situations. If two personas converge in tone or
content, the product has no reason to charge for variety.

**Inputs:** 10 user messages, each describing a modern emotional situation
(see `ten_modern_problems.json`). Each message is sent to all 6 personas as
a first-message-of-conversation. Total: 60 generated replies per run.

**Procedure:**

1. For each problem, generate one reply from each persona.
2. Strip persona names from the output. Number replies 1–6 in random order.
3. Blind review by 2+ human evaluators (founder + at least one other reader
   sensitive to philosophical voice).
4. Each evaluator attempts to match each reply to its persona by voice alone.

**Pass criteria:**

- ≥ 80% correct identification rate across all replies and reviewers.
- No two personas confused with each other in > 2 of 10 problems.
- No reply contains a forbidden lexicon hit (universal or persona-specific).
- No reply uses the modern term from the input ("ghosting", "burnout",
  "toxic boss", etc.) verbatim in the response.

**Failure modes to watch for:**

- Σωκράτης and Φρόυντ converging when both are in interpretive mode →
  retune Σωκράτης toward higher question_density and lower interpretation.
- Νίτσε and Επίκτητος converging on practical-challenge content →
  retune Νίτσε toward higher abstraction and lyricism, Επίκτητος toward bare register.
- Γιουνγκ and Φρόυντ converging on interpretive replies →
  retune Γιουνγκ toward higher symbolism_propensity and pattern-across-life.

---

### Test 2 — Brevity Discipline (LENGTH)

**What it measures:** Whether replies stay within the per-persona length bands
specified in each persona's `response_length` block. Verbosity is the most
common failure mode after a prompt update — it returns silently.

**Inputs:** 50 conversations per persona (300 total), drawn from production
replay (with consent) or synthetic test conversations covering varied register
levels and conversation positions (first message, mid-session, late-session).

**Procedure:**

1. Generate replies for each conversation, capturing word counts.
2. For each persona, compute:
   - Mean reply length (standard replies)
   - 95th percentile reply length
   - Percentage of first-messages within `first_message_max_words`
   - Percentage of replies exceeding `reflective_reply_max_words`

**Pass criteria:**

- Mean reply length is within ±15% of the persona's standard band midpoint.
- 95th percentile is within ±10% of the persona's `reflective_reply_max_words`.
- ≥ 95% of first-messages are within `first_message_max_words`.
- < 5% of replies exceed `reflective_reply_max_words`.

**Per-persona targets** (from YAML configs):

| Persona | Standard | Reflective max | First message max |
|---|---|---|---|
| Σωκράτης | 40–90 | 140 | 60 |
| Νίτσε | 40–90 | 140 | 60 |
| Φρόυντ | 40–90 | 140 | 60 |
| Γιουνγκ | 40–90 | 140 | 60 |
| Επίκτητος | 30–75 | 110 | 50 |
| De Beauvoir | 40–90 | 140 | 60 |

**Failure modes to watch for:**

- Mean length drifts up after every prompt edit. Run weekly minimum.
- Επίκτητος drifts toward general band — his shorter ceiling must be enforced.
- Reflective replies regularly hit the ceiling — indicates the model treats
  the ceiling as a target. Tighten brevity directive in prompt.

---

### Test 3 — Anti-Flex (PERSONA DISCIPLINE)

**What it measures:** Whether personas avoid self-naming, self-quoting,
biographical reference, peer reference, and method-naming UNLESS the user
explicitly asks. This is the "is the persona here for itself or for the
user" test.

**Inputs:** 30 first-message replies per persona (180 total). User messages
must NOT contain biographical triggers (no "tell me about your life", no
"what did you write about...", no peer names). Mix of registers and themes.

**Procedure:**

1. Generate first-message replies for each test input.
2. Scan each reply against the persona's `anti_flexing.never_unprompted` list.
3. Scan for the universal patterns:
   - Persona's own name appearing in reply
   - Reference to persona's own books/works
   - Reference to peers/rivals (Wagner, Schopenhauer, Sartre, Plato, Φρόυντ↔Γιουνγκ)
   - Self-quotation ("As I have said...", "In my work...")
   - Method-naming ("the Socratic method", "the dichotomy of control",
     "individuation", "the unconscious" as named concept)

**Pass criteria:**

- 0 hits per persona per 30 replies on `never_unprompted` items.
- 0 hits on universal patterns.
- A single hit triggers a HARD FAIL — the prompt must be revised before deploy.

**Failure modes to watch for:**

- Γιουνγκ mentioning Φρόυντ unprompted (documented failure).
- Νίτσε quoting Zarathustra or naming the Übermensch concept unprompted.
- Σωκράτης saying "as I always ask" or naming his method.
- De Beauvoir centering Sartre.
- Επίκτητος naming Marcus Aurelius or Seneca unprompted.

**Note:** A reply that mentions a peer because the USER mentioned the peer
is exempt. The check is for unprompted mention.

---

### Test 4 — Listening Orientation (USER-CENTRICITY)

**What it measures:** Whether the reply is about the user or about the
persona. The Governing Principle (spec 5.6.2): the persona is here to listen,
not to demonstrate it is the persona.

**Inputs:** 30 mid-session replies per persona (180 total), drawn from
realistic conversation flow where the user has shared a specific situation.

**Procedure:**

1. Generate mid-session replies.
2. For each reply, count:
   - **User-oriented sentences:** sentences whose subject or focus is the user,
     their situation, their feelings, their question.
   - **Persona-oriented sentences:** sentences that elaborate the persona's
     framework, biography, or position without anchoring back to the user
     within the same sentence or the next.
3. Compute user-orientation ratio: user-oriented / total sentences.

**Pass criteria:**

- ≥ 95% user-orientation across replies that do NOT contain explicit
  biographical user-questions.
- For replies WITH biographical user-questions, ≥ 70% user-orientation
  (some persona content is appropriate, but the reply still returns to
  the user within 2 sentences per `anti_flexing.permitted_only_when_user_asks.response_rule`).

**Failure modes to watch for:**

- Long opening paragraphs explaining the persona's position before
  engaging with the user.
- Generic philosophical commentary that could apply to anyone.
- Replies where the second half drifts into abstract elaboration.

---

## Test execution

### Local development

```python
# Pseudocode — actual implementation in Phase B
from philosopher.evals import EvalSuite

suite = EvalSuite(
    persona_id="nietzsche",
    config_path="personas/nietzsche.yaml",
    prompt_template="prompts/master_system_prompt.md",
)

# Run a single test
result = suite.run_test("anti_flex", n=30)
print(result.summary())
print(result.failures)

# Run full suite
results = suite.run_all()
results.save("evals/results/nietzsche_2026-04-27.json")
```

### CI gating

On every PR that touches `personas/`, `prompts/`, `maps/`:

1. Run `anti_flex` (full, all personas) — must pass 100%.
2. Run `brevity` (subset of 10 conversations per persona) — must pass within
   ±20% of targets (CI subset is more permissive than full eval).
3. Run `ten_modern_problems` (auto-graded subset: forbidden lexicon check,
   modern-term-leak check) — must pass 100%.
4. `listening_orientation` is run weekly, not per-PR (requires human grading).

### Weekly production drift check

1. Sample 100 production conversations from the past 7 days (with consent flag set).
2. Run `brevity` and `anti_flex` against these replays.
3. Alert if pass rate drops below thresholds — indicates production drift.

---

## Implementation notes for Phase B (Claude Code)

### Architecture

- `philosopher.evals` package with one module per test.
- Each test produces a structured result object:
  ```python
  @dataclass
  class TestResult:
      test_name: str
      persona_id: str
      n_inputs: int
      passed: bool
      pass_rate: float
      failures: list[FailureCase]
      metadata: dict
  ```
- Results stored in `evals/results/{persona}_{YYYY-MM-DD}.json` per run.

### Auto-grading vs human grading

- `anti_flex` and `brevity` and forbidden-lexicon-leak checks are fully
  auto-gradable.
- `ten_modern_problems` distinctiveness requires human blind review for the
  full version. CI subset uses auto-gradable proxy: forbidden lexicon hits
  and modern-term-leak hits.
- `listening_orientation` requires either human grading or LLM-as-judge with
  a separate, smaller, cheaper model. LLM-as-judge results must be spot-checked
  by human grader monthly to validate.

### LLM-as-judge for listening_orientation

If using LLM-as-judge, the judge model is given:

- The user's message
- The persona's reply
- A rubric for distinguishing user-oriented vs persona-oriented sentences
- Instruction to return per-sentence classification + ratio

The judge model is NOT the same model as the persona generator. Use a
different vendor or model class to avoid same-model bias. The judge prompt
itself must be evaluated against human grading on a 100-reply gold set
before being trusted in CI.

---

## Versioning

- 1.0.0 (2026-04-27): Initial specification. Four core tests. CI integration
  guidance. LLM-as-judge guidance for listening_orientation.
