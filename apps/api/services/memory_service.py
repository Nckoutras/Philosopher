import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models import MemoryEntry, Insight
from schemas import THEME_VALUES
from services.llm_client import llm_client
from services.embedding_client import embedding_client
from services.output_gate import output_is_unsafe
from services.safety_event_log import STAGE_INSIGHT_OUTPUT
from text_utils import dominant_language, language_directive, language_matches
from config import config

logger = logging.getLogger(__name__)

# ── Hybrid recall (Memory-v2 Ruling #5, design §2) ────────────────────────────
# Memory rows differ in one way that matters more than any other: SOME ARE THE
# PERSON'S OWN WORDS, THE REST ARE A MODEL'S INFERENCE ABOUT THEM. `stated` is
# text they typed, distilled; `self_portrait` is a pill they tapped. Neither can
# be wrong ABOUT them the way `belief`/`pattern`/`struggle` can — those are an
# LLM's reading, written at confidence >= 0.65, and a confident wrong one is the
# "λάθος μνήμη" Ruling #5 forbids. So the two kinds get two lanes, and the whole
# precision budget is spent on the lane where wrongness lives.
#
# Lane A (standing): exempt from the relevance floor — self-authored material
# does not have to earn its place by cosine score — but bounded, so it cannot
# flood the block.
#
# Lane A IS A CLOSED TWO-TYPE SET (Ruling #5; O-2 declined to widen it for
# `onboarding_profile`). Everything else is inferred BY CONSTRUCTION — the lane
# test is `entry_type NOT IN standing`, never an allow-list. That matters
# because `entry_type` is not validated on write: extraction stores the LLM's
# `type` field verbatim (`entry.get("type", "pattern")` below is a fallback for
# a MISSING key, not a whitelist), so an unrecognised or future type can exist
# in the table. With a catch-all it lands in Lane B, floor-gated and quota'd.
# With an allow-list it would be silently dropped from recall. `self_portrait_shift`
# is the live example and is Lane B by this rule (design §2b, ruled 2026-09-03).
STANDING_TYPES = ("stated", "self_portrait")

RECALL_TOTAL_BUDGET = 8      # rows in the prompt block, both lanes together
STANDING_CAP = 3             # Lane A, all standing types together
STANDING_PER_TYPE = 2        # Lane A, any one type
INFERRED_CAP = 5             # Lane B before Lane A's unfilled slots spill in
INFERRED_PER_TYPE = 2        # Lane B, any one type — stops one prolific type

# Lane B's relevance floor, replacing the 0.70 literal that had stood unmeasured
# since the initial commit. Ruling #5 buys precision with recall in as many words
# ("never a wrong memory in, even if one goes missing"), so the floor rises.
# 0.75 is a SHIP-AND-TUNE value (O-1): no measurement of either number against
# real embeddings exists, and a synthetic-vector test can pin that the floor is
# ENFORCED but not where it belongs. Named so it moves without touching the query.
INFERRED_SCORE_FLOOR = 0.75

# ── "These two rows say the same thing" — ONE definition, two readers ─────────
#
# MOVED HERE FROM THE RECURRENCE BLOCK BELOW (D3), unchanged in value. It was
# always the memory domain's only ROW-TO-ROW similarity constant; it now has a
# second reader, so it sits with the recall constants rather than inside the
# section named after its first one.
#
# Reader 1 — `find_recurrences`: a prior entry this similar means the person has
# returned to a theme, and that is worth a card.
# Reader 2 — `compose_recall`'s diversity guard (D3): two candidates this similar
# say one thing, and the second one should not spend a slot saying it again.
#
# THE TWO READINGS ARE THE SAME FACT, USED TWICE — which is why this is one
# constant and not two. A pair over this line is a restatement; recurrence turns
# that into an insight, and recall declines to print it twice.
#
# CALIBRATION, MEASURED (D3, production 2026-09-16). 0.75 was inherited from the
# recurrence path and was NOT chosen for this job, so it was checked against real
# rows before being reused. Of 109,309 active same-user pairs: 0 above 0.95, 2
# above 0.90, 96 above this line. Every founder pair sampled in the 0.75-0.80
# band — the band nearest the line, where a wrong threshold does its damage — was
# a genuine restatement rather than a neighbouring thought, e.g. "User feels they
# have no friends and is experiencing loneliness" beside "User feels isolated and
# lacks meaningful friendships" at 0.798. An earlier D3 draft proposed ~0.85 for
# this guard; that was over-cautious and the measurement is why it is not 0.85.
#
# NOT the same axis as INFERRED_SCORE_FLOOR above, which compares a row to the
# QUERY. This compares a row to ANOTHER ROW. Both happen to read 0.75 today and
# they are unrelated; changing one must not drag the other.
DUPLICATE_SIM_THRESHOLD = 0.75
RECURRENCE_SIM_THRESHOLD = DUPLICATE_SIM_THRESHOLD  # first reader's historical name

# Candidates, not the answer. ROW_NUMBER ranks WITHIN each entry_type so one
# prolific type cannot crowd the others out before Python ever sees the rows,
# and the floor is applied to the inferred branch only. `compose_recall` then
# applies the caps and the spillover.
#
# The lane test is `entry_type = ANY(:standing_types)` / `<> ALL(...)` — the
# catch-all form, for the reason given on STANDING_TYPES.
#
# `near_dupe_ids` IS COMPUTED HERE RATHER THAN IN PYTHON, and the choice is about
# the hot path. The alternative — return `embedding` and compare in
# `compose_recall` — would ship up to ~22 candidate vectors of 1536 floats on
# EVERY chat turn (pgvector renders them as text, ~20KB each) to answer a
# question the database can answer where the vectors already live. What crosses
# the wire instead is a short array of ids.
#
# The comparison is over the CANDIDATE SET, not the table: `candidates` is
# referenced twice so Postgres materialises it, and `memory_entries` is still
# scanned exactly once (pinned by the plan test, T-9).
#
# ACROSS TYPES, DELIBERATELY. The per-type quota cannot bound a cross-type
# duplicate, and those are real: a `struggle` row and a `pattern` row in
# production say the same thing at 0.772. Restricting this to same-type pairs
# would miss exactly the duplicates nothing else catches.
#
# Module-level so tests can EXPLAIN the REAL query rather than a copy that can
# drift from it (T-9).
RECALL_SQL = """
    WITH scored AS (
        SELECT id, entry_type, content, confidence, created_at, embedding,
               1 - (embedding <=> CAST(:query_vec AS vector)) AS score,
               ROW_NUMBER() OVER (
                   PARTITION BY entry_type
                   ORDER BY embedding <=> CAST(:query_vec AS vector),
                            created_at DESC, id
               ) AS rank_in_type
        FROM memory_entries
        WHERE user_id = :user_id
          AND is_active = TRUE
          AND embedding IS NOT NULL
    ),
    candidates AS (
        SELECT id, entry_type, content, confidence, created_at, embedding, score
        FROM scored
        WHERE (entry_type = ANY(CAST(:standing_types AS text[]))
               AND rank_in_type <= :standing_per_type)
           OR (entry_type <> ALL(CAST(:standing_types AS text[]))
               AND rank_in_type <= :inferred_per_type
               AND score > :floor)
    )
    SELECT c.id, c.entry_type, c.content, c.confidence, c.created_at, c.score,
           ARRAY(
               SELECT o.id
               FROM candidates o
               WHERE o.id <> c.id
                 AND 1 - (c.embedding <=> o.embedding) >= :dup_threshold
           ) AS near_dupe_ids
    FROM candidates c
"""


def _ordered(rows: list) -> list:
    """Score DESC, then created_at DESC, then id ASC.

    Three stable sorts rather than one composite key, because the key would have
    to negate a datetime to sort it descending alongside an ascending id. Python's
    sort is stable, so sorting by the LEAST significant field first and the most
    significant last produces the lexicographic order without that trick.

    The tie-break is not decoration: identical inputs must render an identical
    block. A prompt that reorders between two identical turns is untestable, and
    it moves text that sits after the cache breakpoint for no reason.
    """
    xs = sorted(rows, key=lambda r: str(r.id))
    xs.sort(key=lambda r: r.created_at, reverse=True)
    xs.sort(key=lambda r: r.score, reverse=True)
    return xs


def _near_dupes(row) -> frozenset:
    """The ids this candidate restates, as computed by RECALL_SQL.

    `getattr` WITH A DEFAULT, NOT `row.near_dupe_ids`. compose_recall is a public
    pure function and its other caller is a test suite of hand-built rows; a row
    without the column must compose exactly as it did before the guard existed
    rather than raise. The risk that buys — a real query silently losing the
    column and the guard going quiet — is covered where it belongs, by a db_live
    test that asserts RECALL_SQL returns it.

    COMPARED AS STRINGS, and that is not tidying. These ids cross a raw-driver
    boundary: `recall` runs `text(RECALL_SQL)`, so asyncpg decodes a `uuid` column
    to `uuid.UUID` while the models declare `UUID(as_uuid=False)` and every
    hand-built test row uses `str`. A set of UUIDs intersected with a set of `str`
    is EMPTY rather than an error — the guard would do nothing, on every turn, and
    every unit test would still pass. Normalising both sides here makes the
    comparison independent of which driver produced the row.
    """
    return frozenset(str(x) for x in (getattr(row, "near_dupe_ids", None) or ()))


def _select(rows: list, *, per_type: int, limit: int, already: list) -> list:
    """Greedy pick: per-type quota, diversity guard, hard limit — in ONE pass.

    Replaces `_take_per_type(...)[:limit]`. Slicing after the fact cannot express
    the guard: a dropped duplicate has to free its slot for the next-best
    distinct row, so the cut has to happen DURING the walk, not after it. K stays
    full; it is not shortened by deduplication.

    A duplicate is skipped BEFORE the type quota is charged — it never occupied a
    slot, so it must not spend one on its way out.

    `already` is the rows chosen by an earlier lane. Lane B therefore dedupes
    against Lane A as well as against itself, which is the point: if the person's
    own stated words are already in the block, an inferred restatement of them
    adds nothing. Nothing dedupes backwards — Lane A is chosen first and is never
    revisited.

    Input order is preserved among survivors: this only ever drops rows, never
    reorders them, so `_ordered`'s ranking still governs the block.
    """
    seen: Counter = Counter()
    kept: list = []
    # str() on both sides — see _near_dupes for why the comparison cannot be left
    # to whatever type the driver produced.
    kept_ids = {str(r.id) for r in already}
    for r in rows:
        if len(kept) >= limit:
            break
        if seen[r.entry_type] >= per_type:
            continue
        if kept_ids & _near_dupes(r):
            continue
        seen[r.entry_type] += 1
        kept.append(r)
        kept_ids.add(str(r.id))
    return kept


def compose_recall(
    rows: list,
    *,
    standing_types: tuple = STANDING_TYPES,
    standing_cap: int = STANDING_CAP,
    standing_per_type: int = STANDING_PER_TYPE,
    inferred_cap: int = INFERRED_CAP,
    inferred_per_type: int = INFERRED_PER_TYPE,
    floor: float = INFERRED_SCORE_FLOOR,
    total_budget: int = RECALL_TOTAL_BUDGET,
) -> list:
    """Candidate rows in → the block's rows out. PURE: no session, no query.

    This is where Ruling #5 actually lives, and it is a plain function on purpose
    — the SQL is what needs a live Postgres to verify, while the caps, the quota,
    the spillover and the ordering are arithmetic and belong in unit tests.

    Lane A (standing) is taken first: per-type capped, then capped in total, with
    NO floor. Lane B (everything else) must clear `floor`, is per-type capped, and
    receives Lane A's unfilled slots — one way only. A floor-less lane has to stay
    bounded, so nothing ever spills from B back into A.

    Rows are re-filtered and re-ranked here rather than trusted from the query:
    the SQL's window is an optimisation that fetches fewer rows, not the authority
    on the answer. That keeps this function meaningful against any input a test
    hands it.

    THE DIVERSITY GUARD (D3). A candidate that restates a row already chosen is
    skipped, and the slot goes to the next distinct row instead. "Restates" is
    DUPLICATE_SIM_THRESHOLD, computed in RECALL_SQL and arriving as
    `near_dupe_ids`; see that constant for why it is shared with recurrence and
    what the production data says about where it sits.

    WHAT THIS FIXES, stated because the caps LOOK like they already covered it.
    They do not. `INFERRED_PER_TYPE = 2` bounds how many rows of one type appear,
    which is a different question from whether two of them say the same thing —
    and it is no bound at all across types. Measured in production: of the 11
    same-user pairs above 0.85, TEN would have had both members inside the
    per-type cap, i.e. one fact spending two of Lane B's five slots. One such
    pair spans two types, where the quota could never have helped.

    This only ever DROPS rows; it never reorders them, and it never invents one.
    Deduplication does not shorten the block — the limit is applied during the
    walk, so a skipped duplicate frees its slot rather than losing it.
    """
    standing_set = set(standing_types)

    standing_rows = [r for r in rows if r.entry_type in standing_set]
    inferred_rows = [
        r for r in rows
        if r.entry_type not in standing_set and r.score > floor
    ]

    # Lane A is clamped by the BUDGET as well as by its own cap. Without the
    # min, a caller asking for fewer rows than the person has standing rows would
    # get more than it asked for: Lane B's room would clamp to 0 while Lane A had
    # already overshot. total_budget is the total, including Lane A.
    standing = _select(
        _ordered(standing_rows),
        per_type=standing_per_type,
        limit=min(standing_cap, total_budget),
        already=[],
    )

    # Spillover, expressed both ways and clamped by the smaller. The two agree
    # whenever STANDING_CAP + INFERRED_CAP == RECALL_TOTAL_BUDGET; the min is what
    # keeps the total honest if one constant is later tuned without the others.
    #
    # LANE A's LENGTH IS MEASURED AFTER the guard, so a duplicate dropped from
    # Lane A hands its slot to Lane B rather than to nobody. The budget is spent
    # either way — that is what "K stays full" means here.
    inferred_room = min(
        inferred_cap + (standing_cap - len(standing)),
        total_budget - len(standing),
    )
    inferred = _select(
        _ordered(inferred_rows),
        per_type=inferred_per_type,
        limit=max(inferred_room, 0),
        already=standing,
    )

    # Standing first: it is the stable frame the persona reads the topical matches
    # against. The reverse buries that frame under whatever this turn matched.
    return standing + inferred


# ── Recurrence detection (Insight Slice 1) ─────────────────────────────────────
# A factual recurrence detector: when a memory the user just raised has surfaced
# before in OTHER conversations, write a durable Insight naming the recurring
# thread. Constants are named here so they are trivial to tune.
# RECURRENCE_SIM_THRESHOLD now lives with the recall constants at the top of this
# module — it gained a second reader (the D3 diversity guard) and one definition
# of "these two rows say the same thing" serves both. Its value is unchanged.
RECURRENCE_MIN_PRIOR = 1          # how many prior-conversation matches → recurrence
RECURRENCE_THROTTLE_HOURS = 6     # min spacing between 'pattern' insights per user

RECURRENCE_PROMPT = """You name a recurring thread in someone's reflections — factually, not therapeutically.

You are given something the person raised just now, and one or more things they said earlier in OTHER conversations that closely echo it.

Write a single observation that names WHAT keeps returning. Rules:
- At most 2 sentences. Plain, grounded, observational.
- Name the recurring theme concretely. Do not interpret motive or character.
- No therapy-speak. No diagnosis. Never say "you always" or "you never".
- Address the person as "you". No preamble, no quotation marks.
- Never quote the person and never paraphrase their sentences one-to-one.
- Distill the essence. You may reuse the person's own key concept-words as anchors, but reframe — name the pattern one level above the instance.
- If find-and-replace on their words could produce your line, rewrite it.
- Make no claim the material does not support.

Example: "The question of whether to leave your job has come up again — it surfaced weeks ago in a different conversation, and here it is once more." """

# ── Shift detection (Insight Slice 2) ──────────────────────────────────────────
# One classify+phrase call: given a just-raised memory and the prior memories that
# echo it, decide whether the person's STANCE has changed ('shift') or merely
# recurred ('pattern'), and phrase the observation in one shot. STRONGLY biased to
# 'pattern' — LLMs over-detect narrative change; 'shift' is reserved for genuine
# directional movement of the position. Shifts are hedged to a certainty ladder.
SHIFT_CLASSIFY_PROMPT = """You compare something a person raised just now against closely-related things they said earlier, in OTHER conversations, and decide whether their STANCE on the theme has actually changed.

Return JSON only — no markdown, no preamble — exactly: {"insight_type": "pattern" | "shift", "content": "..."}

Classification (default to "pattern"):
- "pattern" is the DEFAULT. Choose it whenever the theme simply recurs and the person's position is essentially unchanged. Different wording, new examples, fresh emphasis, or a more detailed retelling of the SAME stance is still "pattern".
- "shift" ONLY when there is genuine DIRECTIONAL change in the stance itself — the position moved or reversed (e.g. from wanting to leave → wanting to stay; from certainty → doubt; from resisting → accepting). Rephrasing or paraphrase variation is NOT a shift. When in doubt, it is a pattern.

Write "content" as a single observation, at most 2 sentences, addressed to the person as "you". Plain, grounded, observational. No therapy-speak, no diagnosis, never "you always"/"you never", no preamble, no quotation marks.

For "pattern": name the recurring theme concretely — a familiar thread returning.

For "shift": HEDGE the claim to how clearly the change shows in the material. Match the language to your confidence, and never state a tentative shift as a certain fact:
- low confidence    → "Something may be beginning to shift — ..."
- medium confidence → "It seems as though ..."
- high confidence   → "It's quite likely that ..." or "What you once called X, you now seem to name Y."

No-verbatim rule (both types): never quote the person and never paraphrase their sentences one-to-one. Reuse their key concept-words as anchors, but reframe — name it one level above the instance. If find-and-replace on their words could produce your line, rewrite it. Make no claim the material does not support.

Example pattern: {"insight_type": "pattern", "content": "The question of whether to leave your job has come up again — it surfaced weeks ago in a different conversation, and here it is once more."}
Example shift: {"insight_type": "shift", "content": "It seems as though the certainty you once had about leaving has loosened; where you spoke of escape, you now weigh what staying might be worth."}"""

# ── Single-text → memory distillation (reusable) ───────────────────────────────
# Turn a person's OWN words into one clean, third-person memory statement. Generic
# by design (no council/ritual wording) so later #4 surfaces (Counterview, Future
# Self, Mirror) reuse it unchanged. Cheap: a word-count pre-filter skips trivial
# text BEFORE any LLM call, and the one LLM call rides the default memory model
# (Haiku via config.ANTHROPIC_MEMORY_MODEL). Returns None on trivial/empty/NONE.
MIN_DISTILL_WORDS = 6

DISTILL_TO_MEMORY_PROMPT = """You convert a person's own words into ONE clean memory statement about them.

You are given text the person wrote themselves — their own framing of a matter they wanted considered. Rewrite it as a single, third-person memory statement in the shape "User ..." — factual, grounded, one sentence, no interpretation beyond what they stated.

Return ONLY the statement, no preamble, no quotation marks. If the text holds nothing meaningful to remember, return exactly: NONE"""


async def distill_to_memory(text: str) -> str | None:
    """Distil a person's own text into ONE third-person memory statement ("User …").

    Pre-filter: text with fewer than MIN_DISTILL_WORDS words returns None WITHOUT any
    LLM call (trivial edits cost nothing past this check). Otherwise one Haiku
    completion (default memory model) produces the statement; an empty reply or the
    sentinel NONE → None. Generic (no council-specific wording) so #4b/c/d reuse it.
    """
    text = (text or "").strip()
    if len(text.split()) < MIN_DISTILL_WORDS:
        return None
    # The input IS the person's own words, so it is the language signal. Computed,
    # not inferred — the prompt used to ask the model to match "the same language
    # as the input" and it answered in English for Greek input 20 times out of 20.
    language = dominant_language([text])
    raw = await llm_client.complete(
        system=DISTILL_TO_MEMORY_PROMPT + language_directive(language),
        user=text,
        max_tokens=160,
    )
    statement = (raw or "").strip()
    # Strip wrapping quotes if the model added them despite instructions.
    if len(statement) >= 2 and statement[0] in "\"'" and statement[-1] in "\"'":
        statement = statement[1:-1].strip()
    if not statement or statement.upper() == "NONE":
        return None
    # OBSERVABILITY, NOT ENFORCEMENT — and the difference is deliberate. A council
    # brief in the wrong language is display text and dropping it costs the reader
    # nothing (they keep their raw prefill). Dropping a memory row loses a fact
    # about the person that nothing else records. So this logs and keeps the write:
    # the IN directive above is the fix, this is how we find out if it stops working.
    if not language_matches(statement, language):
        logger.warning(
            "memory_language_mismatch",
            extra={"site": "distill_to_memory", "expected_language": language,
                   "got_script": dominant_language([statement])},
        )
    return statement


MEMORY_EXTRACTION_PROMPT = """You are a memory extraction system for a philosophical companion app.

Given a conversation exchange (user message + assistant response), extract memorable observations about the user.
Focus on: beliefs, values, ongoing struggles, recurring patterns, personal milestones, stated goals.

Return a JSON array only. No explanation. No markdown.
Each item: {"type": "belief|value|struggle|pattern|milestone|dilemma|aspiration", "content": "...", "confidence": 0.0-1.0, "theme": "<one theme slug or omit>"}

Rules:
- Only extract what is genuinely stated or clearly implied. Do not infer beyond the text.
- Content should be 1-2 concise sentences about the USER, not the conversation.
- Confidence > 0.8 = stated explicitly. 0.6-0.8 = clearly implied. Below 0.6 = skip it.
- Return [] if nothing meaningful is extractable.
- Max 3 entries per exchange.
- "dilemma": a live decision the user is ACTIVELY weighing between two courses of action, stated in THIS exchange. Not general uncertainty, not a decision already made in the past, not the assistant's framing. Content = one sentence naming the two sides in the user's own voice, first person (it is placed in the user's own input field verbatim).
- "belief": write content as the belief ITSELF — a single declarative sentence in the user's own voice, not "You believe that…". e.g. "If I don't handle everything myself, it won't be done right." This text is used verbatim as a Counterview anchor.
- "aspiration": a genuine reach toward who the user wants to BECOME, or a direction/change they are resolving to make — stated with real weight in THIS exchange. NOT a passing wish, a casual preference, or an offhand goal. Only when they articulate the person they want to be or a change they mean to commit to. Content = one sentence in the user's own voice, first person, naming the direction.
- "theme" (OPTIONAL): the single best-fitting life-theme for this item, one of: separation, anxiety, fear, grief, acceptance, work, relationships, purpose, dilemma, controversy, doubt, freedom. Omit the field entirely if none clearly fits. Only meaningful for "dilemma" and "belief"; may be omitted for other types.

Example output:
[
  {"type": "struggle", "content": "User is experiencing conflict between career ambitions and desire for stability.", "confidence": 0.85},
  {"type": "value", "content": "User places high importance on honesty in relationships.", "confidence": 0.75},
  {"type": "dilemma", "content": "I'm weighing whether to leave a secure job for one that feels meaningful but far less certain.", "confidence": 0.9, "theme": "work"},
  {"type": "belief", "content": "If I don't handle everything myself, it won't be done right.", "confidence": 0.85, "theme": "work"}
]"""


# ── Signal types whose content lands in the user's OWN INPUT FIELD ────────────
# EDITABLE INPUT IS THE LINE, not verbatim display, and only one of the three
# signal types crosses it:
#
#   dilemma     content -> sessionStorage 'council_prefill' (useInsightDoors.ts)
#               -> setMatter(prefill) (council/page.tsx) -> the matter TEXTAREA.
#               The user can submit it as their own words without noticing.
#   belief      content -> the counterview anchor, generated from server-side and
#               rendered read-only in a <p> labelled "Your insight". The page's
#               `belief` state is written only by the user typing.
#   aspiration  routes to the Future Self ritual and carries no content at all.
#
# So belief and aspiration keep the log-only path the other extraction types
# have: a wrong-language card is a visible glitch, while wrong-language text in
# an input box is something a person may submit believing they wrote it. That
# distinction is what made #626 a P0.
#
# THE COST IS REAL AND NOT RECOVERABLE, and it is the accepted trade. A dropped
# dilemma is not deferred or retried — the exchange has passed, and the person
# loses that Council door until the same dilemma resurfaces in a later one. We
# would rather lose the door than put a sentence they never wrote in the box
# they type into.
VERBATIM_INPUT_SIGNAL_TYPES = ("dilemma",)


RECURRENCE_LIMIT = 20             # candidates pulled per cosine search, before the threshold


async def find_recurrences(
    db: AsyncSession,
    user_id: str,
    query_entry,
    *,
    exclude_conversation: str | None = None,
    corpus_since: datetime | None = None,
    corpus_until: datetime | None = None,
) -> tuple[list, dict] | None:
    """Cosine-search one memory entry against the rest of this user's memories.

    THE MECHANICS ONLY. No throttle, no classifier, no Insight row, no LLM call of
    any kind — those belong to `detect_recurrence`, which is one caller of this.
    The trajectory snapshot is the other, and it wants raw match sets rather than
    a written card. A source-level test asserts this function stays free of all
    three, because the value of the seam is exactly that it has no side effects.

    Returns `(matches, evidence)` when at least RECURRENCE_MIN_PRIOR rows clear
    RECURRENCE_SIM_THRESHOLD, else None. The caller owns the loop over entries:
    `detect_recurrence` stops at the first hit because it writes one card, and the
    snapshot wants every hit, so a loop in here would force one of them to discard
    work the other needs.

    THE CORPUS BOUNDS ARE NAMED `corpus_*` ON PURPOSE. A period-scoped caller has
    TWO different date filters and conflating them is a silent wrong answer: which
    entries are used as QUERIES (a caller-side selection, never in this SQL) and
    which entries form the CORPUS (the clauses below). A weekly snapshot asks
    "which entries written in W echo entries written BEFORE W", so it selects its
    query entries by period and passes `corpus_until=period_start`. Passing a
    window to the wrong side would compare a week against itself.

    WITH NO BOUNDS THE SQL IS BYTE-IDENTICAL to what this query has always been —
    the clauses are appended to `exclude_clause` rather than occupying a slot of
    their own, because an empty slot leaves an indented blank line and that is not
    the same string. A test pins the lifetime SQL against a frozen literal, and
    that pin is the proof this extraction narrowed nothing.

    `is_active = TRUE` BOUNDS BOTH CALLERS, and the limit is deliberate: THIS
    CORPUS CANNOT SEE SUPERSESSION. A self-portrait re-answer deactivates the row
    it replaces, so "what you used to think" is invisible here — which is exactly
    what a trajectory view would want. That is the deferred version-chain question
    (evolving_beliefs), not a bug, and the shape it would take is a third
    parameter (`include_superseded=False`) that today's callers never pass. It is
    not added now because an unused parameter is a claim about a decision nobody
    has made.

    FILTERED-ANN RECALL, accepted and recorded rather than tuned. A bounded corpus
    turns this into a filtered nearest-neighbour search: Postgres applies the date
    clause DURING the HNSW index scan (ix_memory_entries_embedding_hnsw_cosine,
    migration 008), and if the filter is selective — a heavy week, most recent rows
    in-period — the scan can exhaust `hnsw.ef_search` before finding
    RECURRENCE_LIMIT rows that pass. Rows returned are always genuine matches; the
    risk is QUIET UNDER-RECALL: real echoes that exist and are not found, with
    nothing looking broken. Not tuned because no measurement exists, and because
    `ef_search` is a global knob whose only other user is the request-path
    `recall()`. The two levers, recorded for the day a snapshot reads thin on a
    busy week: raise RECURRENCE_LIMIT on the bounded path, or set `ef_search` for
    that statement. See TD-75.
    """
    if query_entry.embedding is None:
        return None

    # Build the pgvector literal explicitly. NOT str(embedding): if the
    # value is ever a numpy array, str() truncates with "..." and uses
    # space separators → an invalid literal that would be swallowed by
    # the try/except and silently yield zero matches forever.
    vec_literal = "[" + ",".join(repr(float(x)) for x in query_entry.embedding) + "]"

    # Exclude the source's own context so an entry can never match itself.
    # Chat path: exclude the whole source conversation. NULL-conversation
    # source (voluntary belief): exclude only this entry by its own id —
    # `conversation_id != NULL` would exclude every row (SQL 3-valued logic).
    if exclude_conversation is not None:
        filters = "AND conversation_id != :conversation_id"
        params = {"conversation_id": exclude_conversation}
    else:
        filters = "AND id != :self_id"
        params = {"self_id": query_entry.id}

    # Appended to `filters`, never a slot of their own — see the byte-identical
    # note above. Indentation matches the surrounding clauses so the emitted SQL
    # reads the same whether or not the bounds are present.
    if corpus_since is not None:
        filters += "\n                          AND created_at >= :corpus_since"
        params["corpus_since"] = corpus_since
    if corpus_until is not None:
        filters += "\n                          AND created_at < :corpus_until"
        params["corpus_until"] = corpus_until

    result = await db.execute(
        text(f"""
                        SELECT id, content, conversation_id,
                               1 - (embedding <=> CAST(:query_vec AS vector)) AS score
                        FROM memory_entries
                        WHERE user_id = :user_id
                          AND is_active = TRUE
                          AND embedding IS NOT NULL
                          {filters}
                        ORDER BY embedding <=> CAST(:query_vec AS vector)
                        LIMIT {RECURRENCE_LIMIT}
                    """),
        {
            "query_vec": vec_literal,
            "user_id": user_id,
            **params,
        },
    )
    rows = result.fetchall()
    matches = [r for r in rows if r.score >= RECURRENCE_SIM_THRESHOLD]
    if len(matches) < RECURRENCE_MIN_PRIOR:
        return None

    # ── EVIDENCE (060) ────────────────────────────────────────────────────────
    # The rows a caller's insight or snapshot was derived from, kept instead of
    # collapsed. Ids AND a text snippet, no foreign keys: a memory row can be
    # deactivated and 057 lets its conversation be deleted, so a citation that
    # resolved by id alone would stop rendering the thing it cites. Every match
    # above the bar is stored; `shown_to_classifier` records how many of them
    # detect_recurrence's classifier actually sees. The detector's constants are
    # frozen at write time because they are ship-and-tune values, and a citation
    # whose bar is unrecoverable cannot be read.
    evidence = {
        "recurring_entry": {
            "memory_entry_id": str(query_entry.id),
            "text": query_entry.content,
            "conversation_id": (
                str(query_entry.conversation_id)
                if query_entry.conversation_id else None
            ),
        },
        "prior_matches": [
            {
                "memory_entry_id": str(m.id),
                "text": m.content,
                "conversation_id": str(m.conversation_id) if m.conversation_id else None,
                "score": float(m.score),
            }
            for m in matches
        ],
        "shown_to_classifier": len(matches[:5]),
        "detector": {
            "threshold": RECURRENCE_SIM_THRESHOLD,
            "limit": RECURRENCE_LIMIT,
            # NULL means lifetime, which is what detect_recurrence is and must
            # stay. A bounded caller records the bounds it actually used.
            "window": (
                None if (corpus_since is None and corpus_until is None)
                else {
                    "since": _iso_z(corpus_since),
                    "until": _iso_z(corpus_until),
                }
            ),
        },
    }
    return matches, evidence


def _iso_z(value: datetime | None) -> str | None:
    """UTC ISO-8601 with an explicit Z, matching the export's convention.

    Naive values are treated as UTC rather than dropped: every writer in this
    codebase uses datetime.now(timezone.utc), so a naive value is a storage
    artefact and not a different instant.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class MemoryService:

    async def extract_and_store(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str,
        persona_id: str,
        user_text: str,
        assistant_text: str,
        source_turn: int = 0,
        safety_ok: bool = False,
    ) -> list[MemoryEntry]:
        """Extract memory signals from a message pair and persist them.

        `safety_ok` (input+output both level 'none') gates ONLY the dilemma/belief
        signal-insight write below; memory-row persistence is unchanged by it.
        """
        # The USER's turn only. The assistant's reply is in the user block below as
        # context, but it is not evidence of what language the PERSON writes in —
        # and this prompt never said anything about language at all, while every
        # one of its worked examples is English. A model given English examples,
        # an English output shape ("User ..."), and no instruction does the
        # predictable thing: 20 of 20 Greek inputs produced English rows.
        language = dominant_language([user_text])
        try:
            raw = await llm_client.complete(
                system=MEMORY_EXTRACTION_PROMPT + language_directive(language),
                user=f"USER: {user_text}\n\nASSISTANT: {assistant_text}",
                max_tokens=512,
            )
            # Strip markdown code fences if LLM wrapped the JSON
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else ""
            if text.endswith("```"):
                text = text[:-3].rstrip()
            entries_data = json.loads(text)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Memory extraction failed: {e}")
            return []

        saved = []
        for entry in entries_data:
            # Dilemma/aspiration items are insight-only signals (see below) — never memory rows.
            if entry.get("type") in ("dilemma", "aspiration"):
                continue
            if entry.get("confidence", 0) < 0.65:
                continue

            content = entry.get("content", "").strip()
            if not content:
                continue

            # Logged, never blocking — see distill_to_memory. A row that arrives in
            # the wrong language is still a true fact about the person; refusing to
            # store it would lose the fact as well as the language.
            if not language_matches(content, language):
                logger.warning(
                    "memory_language_mismatch",
                    extra={"site": "extract_and_store",
                           "entry_type": entry.get("type"),
                           "expected_language": language,
                           "got_script": dominant_language([content])},
                )

            embedding = await embedding_client.embed(content)

            memory = MemoryEntry(
                user_id=user_id,
                persona_id=persona_id,
                conversation_id=conversation_id,
                entry_type=entry.get("type", "pattern"),
                content=content,
                embedding=embedding,
                confidence=entry.get("confidence", 0.7),
                source_turn=source_turn,
            )
            db.add(memory)
            saved.append(memory)

        await db.flush()

        # ── Dilemma/belief/aspiration → Insight (Slice 2) ─────────────────────
        # Explicitly-stated, chip-worthy signals promoted to an Insight — ONLY when
        # the exchange was safety-clean (safety_ok, level 'none' both ways) and the
        # SAME throttle/dedup gate detect_recurrence uses allows it. At most one write
        # per call; priority order dilemma > belief > aspiration when several qualify.
        # Per-type confidence bar (_SIGNAL_MIN_CONF): dilemma/belief 0.8, aspiration
        # 0.7. content is used verbatim downstream (Council prefill for a dilemma,
        # Counterview anchor for a belief, Future Self door for an aspiration);
        # source_count=None (not a cross-conversation recurrence).
        # Self-contained — a failure here must never break memory persistence.
        if safety_ok:
            try:
                _SIGNAL_MIN_CONF = {"dilemma": 0.8, "belief": 0.8, "aspiration": 0.7}

                def _eligible(e: dict, want: str, thr: float) -> bool:
                    """Candidate test, INSIDE the selection rather than after it.

                    Filtering a chosen signal afterwards would collapse the whole
                    promotion when the top-priority candidate fails: a mismatching
                    dilemma would take the slot and then be discarded, and the
                    Greek belief behind it would never be reached. Rejecting here
                    lets `next()` fall through to the next candidate and the loop
                    advance to the next type, which is the behaviour the priority
                    order already promises.

                    The language test applies ONLY to the types that reach an
                    input field (VERBATIM_INPUT_SIGNAL_TYPES). Everything else is
                    log-only, handled in the memory-row loop above.
                    """
                    if e.get("type") != want:
                        return False
                    if e.get("confidence", 0) < thr:
                        return False
                    content = (e.get("content") or "").strip()
                    if not content:
                        return False
                    if want in VERBATIM_INPUT_SIGNAL_TYPES and not language_matches(
                        content, language
                    ):
                        logger.warning(
                            "memory_language_mismatch",
                            extra={"site": "extract_and_store",
                                   "entry_type": want,
                                   "expected_language": language,
                                   "got_script": dominant_language([content]),
                                   "dropped": True},
                        )
                        return False
                    return True

                signal = None
                for want in ("dilemma", "belief", "aspiration"):
                    thr = _SIGNAL_MIN_CONF[want]
                    signal = next(
                        (e for e in entries_data if _eligible(e, want, thr)),
                        None,
                    )
                    if signal is not None:
                        break
                if signal is not None and await output_is_unsafe(
                    db, signal.get("content"), user_id=user_id,
                    stage=STAGE_INSIGHT_OUTPUT, conversation_id=conversation_id,
                ):
                    # Post-generation safety (founder ruling 2026-09-24): the
                    # insight reaches Today and the letter, so it is not written.
                    # Checked BEFORE the throttle, so a withheld insight never
                    # starts the 6h window.
                    signal = None
                if signal is not None:
                    blocked = await self._insight_gate_blocked(db, user_id, conversation_id)
                    if blocked is None:
                        raw_theme = (signal.get("theme") or "").strip().lower()
                        theme = raw_theme if raw_theme in THEME_VALUES else None
                        db.add(Insight(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            persona_id=persona_id,
                            content=(signal.get("content") or "").strip(),
                            insight_type=signal.get("type"),
                            source_count=None,
                            theme=theme,
                        ))
                        await db.flush()
                        logger.info(
                            "Signal insight written type=%s user=%s conv=%s",
                            signal.get("type"), user_id, conversation_id,
                        )
                    else:
                        logger.info("Signal insight skipped (%s) conv=%s", blocked, conversation_id)
            except Exception as e:
                logger.error("Signal insight write failed conv=%s: %s", conversation_id, e, exc_info=True)

        logger.info(f"Stored {len(saved)} memory entries for user={user_id}")
        return saved

    async def recall(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: int = RECALL_TOTAL_BUDGET,
        query_embedding: list[float] | None = None,
    ) -> list[MemoryEntry]:
        """Retrieve semantically relevant memories for a query — HYBRID (Ruling #5).

        Two lanes, described on STANDING_TYPES above: standing rows enter without
        clearing the floor, inferred rows must clear INFERRED_SCORE_FLOOR and are
        quota'd per type. The SQL fetches CANDIDATES; `compose_recall` decides
        which of them survive, so caps, spillover and ordering are a pure function
        over rows and unit-testable without a database.

        top_k is the TOTAL budget across both lanes, defaulting to
        RECALL_TOTAL_BUDGET. The four callers no longer pass it.

        query_embedding: an optional precomputed embedding of ``query``. When the
        caller already embedded the same text (e.g. the chat turn reuses one vector
        for both recall and retrieval), pass it here to skip a redundant embed. When
        None, embed internally exactly as before.
        """
        query_vec = query_embedding if query_embedding is not None else await embedding_client.embed(query)

        result = await db.execute(
            text(RECALL_SQL),
            {
                "query_vec": str(query_vec),
                "user_id": user_id,
                "standing_types": list(STANDING_TYPES),
                "standing_per_type": STANDING_PER_TYPE,
                "inferred_per_type": INFERRED_PER_TYPE,
                "floor": INFERRED_SCORE_FLOOR,
                "dup_threshold": DUPLICATE_SIM_THRESHOLD,
            }
        )
        return compose_recall(result.fetchall(), total_budget=top_k)

    async def standing_memories(
        self,
        db: AsyncSession,
        user_id: str,
        *,
        limit: int,
    ) -> list[MemoryEntry]:
        """The standing lane WITHOUT a query — most recent `stated` rows first.

        WHY THIS EXISTS SEPARATELY FROM recall(). A chat turn has a query: the
        user's message. A LETTER DOES NOT. It covers a week or a month, and there
        is no single text to embed. Lane A is the half of hybrid recall that never
        needed one — its members are chosen by TYPE and bounded by COUNT, and
        cosine only orders them. Drop the ordering and the lane still stands, which
        is what makes it the right thing to give a query-free surface.

        `stated` ONLY, deliberately. The other standing type, `self_portrait`, is
        already rendered into both letters as the <self_portrait> block, built from
        profile.answers via answers_to_statements — including it here would put the
        same quiz answers in one prompt twice, in two different sentence shapes.
        `stated` is the person's own words from Council, mirrors, counterview and
        future-self notes, and it is the material a letter has no other route to.

        A NARROWING OF DESIGN §3a, RECORDED AS SUCH. The design specified one
        dual-mode accessor — `standing_memories(..., query_embedding=None)` falling
        back to recency, cosine-ranked when given a vector. PR-2 shipped only the
        query-driven half (inside recall's windowed SQL), and PR-3 may not reopen
        recall, so the query-driven mode has no implementation to delegate to and
        no caller that wants it. Building a second cosine path here to satisfy a
        signature would be machinery for nobody. Ruled 2026-09-03; goes to the next
        docs rotation as a correction to §3a rather than an edit to the design doc.

        Ordinary ORM query: no embedding, no vector maths, no LLM, no cost.
        """
        result = await db.execute(
            select(MemoryEntry)
            .where(
                MemoryEntry.user_id == user_id,
                MemoryEntry.entry_type == "stated",
                MemoryEntry.is_active == True,  # noqa: E712 — SQL, not Python truth
            )
            .order_by(MemoryEntry.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _insight_gate_blocked(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str | None,
    ) -> str | None:
        """Shared throttle/dedup gate for ALL insight writes (recurrence AND the
        dilemma/belief signal write) so the guards can never diverge. Returns a block
        reason ("throttle" | "per_conversation") when a write must be skipped, or None
        when it may proceed.

        - "throttle": any non-dismissed insight for this user within the last
          RECURRENCE_THROTTLE_HOURS → skip. Spacing + idempotency vs ARQ's
          at-least-once delivery; max one insight of any type per window.
        - "per_conversation": for a real source conversation, any existing insight in
          it → skip (max one per conversation). A NULL-conversation source (e.g. a
          voluntary counterview belief) is a no-op here (== NULL never matches), so it
          skips this check and leans on the throttle.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=RECURRENCE_THROTTLE_HOURS)
        recent = await db.execute(
            select(Insight.id).where(
                Insight.user_id == user_id,
                Insight.is_dismissed == False,
                Insight.created_at >= cutoff,
            ).limit(1)
        )
        if recent.scalar_one_or_none() is not None:
            return "throttle"

        if conversation_id is not None:
            per_conv = await db.execute(
                select(Insight.id).where(
                    Insight.user_id == user_id,
                    Insight.conversation_id == conversation_id,
                ).limit(1)
            )
            if per_conv.scalar_one_or_none() is not None:
                return "per_conversation"

        return None

    async def detect_recurrence(
        self,
        db: AsyncSession,
        user_id: str,
        conversation_id: str,
        persona_id: str,
        new_entries: list[MemoryEntry],
        *,
        language: str,
    ) -> None:
        """Factual recurrence detector. If a memory the user just raised echoes
        memories from OTHER conversations, write a durable 'pattern' Insight
        naming the recurring thread.

        Safe by construction: wrapped in try/except, NEVER raises into the caller
        (the memory task). Reuses the entries' already-computed embeddings — the
        session uses expire_on_commit=False, so they remain readable post-commit.

        `language` IS AN ARGUMENT, keyword-only and undefaulted, and it is NOT
        derived from the material this function holds. THE MEMORY ROWS ARE NOT A
        SAFE SOURCE: `recurring_entry.content` and every `prior_matches` row is
        model-written, and the guard that watches that writing LOGS RATHER THAN
        BLOCKS (see extract_and_store) — so a wrong-language row is not a legacy
        artifact being aged out, it is a state this system still deliberately
        produces. No floor on row age or count can separate them, and reading a
        language off them would let one wrong row seed a wrong insight.

        Both callers hold something better and free: the person's VERBATIM own
        words — `user_text` in extract_memory_task, `belief` in
        counterview_belief_task. Passing it in also means the insight inherits the
        same language decision extract_and_store already made from the same text,
        rather than a second one derived downstream.
        """
        try:
            if not new_entries:
                return

            # ── DEDUP / THROTTLE (shared gate) ────────────────────────────────
            # The SAME gate the dilemma/belief signal write uses (see
            # _insight_gate_blocked), so a pattern, a shift, and a signal insight can
            # never diverge on spacing or the one-per-conversation rule.
            blocked = await self._insight_gate_blocked(db, user_id, conversation_id)
            if blocked == "throttle":
                logger.info("Recurrence skipped (throttle) user=%s", user_id)
                return
            if blocked == "per_conversation":
                logger.info("Recurrence skipped (one per conversation) conv=%s", conversation_id)
                return

            # ── DETECTION ─────────────────────────────────────────────────────
            # For each freshly-stored entry, cosine-search prior memories from
            # OTHER conversations (mirrors recall(): same str(vector) + CAST AS
            # vector serialization so the param format cannot silently mismatch).
            recurring_entry = None
            prior_matches: list = []
            evidence: dict | None = None
            for entry in new_entries:
                # The loop lives HERE, not in find_recurrences: this caller writes
                # ONE card, so it stops at the first entry that clears the bar.
                # The snapshot caller wants every hit and keeps looping.
                found = await find_recurrences(
                    db, user_id, entry, exclude_conversation=conversation_id,
                )
                if found is not None:
                    prior_matches, evidence = found
                    recurring_entry = entry
                    break

            if recurring_entry is None:
                logger.info("Recurrence: none above threshold for conv=%s", conversation_id)
                return

            # Distinct conversations the theme was noticed across: the distinct
            # prior conversations that cleared the similarity bar, plus this one.
            source_count = len({m.conversation_id for m in prior_matches}) + 1

            # ── CLASSIFY + PHRASE ─────────────────────────────────────────────
            # One call decides pattern vs shift and produces the phrasing. On any
            # ambiguity / empty / parse failure we fall back to the slice-1 plain
            # recurrence phrasing as a 'pattern' — never lose the insight, never
            # surface an unvalidated 'shift'.
            prior_text = "\n".join(f"- {m.content}" for m in prior_matches[:5])
            user_prompt = (
                f"Raised now:\n- {recurring_entry.content}\n\n"
                f"Echoed earlier (other conversations):\n{prior_text}"
            )

            # APPENDED: SHIFT_CLASSIFY_PROMPT carries three literal JSON brace
            # pairs and no real fields, so .format() would raise KeyError on
            # '"insight_type"' rather than fill anything.
            raw = await llm_client.complete(
                system=SHIFT_CLASSIFY_PROMPT + language_directive(language),
                user=user_prompt,
                max_tokens=160,
            )

            insight_type = "pattern"
            content = None
            try:
                parsed = (raw or "").strip()
                if parsed.startswith("```"):
                    parsed = parsed.split("\n", 1)[1] if "\n" in parsed else ""
                if parsed.endswith("```"):
                    parsed = parsed[:-3].rstrip()
                data = json.loads(parsed)
                candidate_type = data.get("insight_type")
                candidate_content = (data.get("content") or "").strip()
                if candidate_type in ("pattern", "shift") and candidate_content:
                    # A wrong-language classification FALLS THROUGH to the plain
                    # recurrence phrasing below rather than dropping out — the same
                    # door a parse failure already takes, and for the same reason
                    # ("never lose the insight, never surface an unvalidated
                    # 'shift'"). The fallback gets its own directive and its own
                    # check, so this is a second chance and not a bypass. Leaving
                    # `content` None is what routes it there.
                    if not language_matches(candidate_content, language):
                        logger.warning(
                            "shift_classify_language_mismatch",
                            extra={"expected_language": language,
                                   "got_script": dominant_language([candidate_content]),
                                   "user_id": user_id,
                                   "conversation_id": conversation_id},
                        )
                    else:
                        insight_type = candidate_type
                        content = candidate_content
            except Exception:
                content = None  # fall through to plain-phrasing fallback

            if content is None:
                # Safe fallback: slice-1 plain recurrence phrasing, always 'pattern'.
                # The only brace-free prompt of the six; appended anyway so every
                # generator in this file reads the same way.
                fallback = await llm_client.complete(
                    system=RECURRENCE_PROMPT + language_directive(language),
                    user=user_prompt,
                    max_tokens=80,
                )
                insight_type = "pattern"
                content = (fallback or "").strip()
                # Last chance used up: write nothing. An Insight is a card the
                # person reads, and unlike a memory row it is NOT the only record of
                # anything — the memory rows this was detected from are untouched,
                # so the theme simply re-triggers on a later conversation. Dropping
                # also costs no budget: _insight_gate_blocked throttles on insights
                # that EXIST, so writing none never starts the 6h window.
                #
                # (That is why the log-only ruling for memory rows does not transfer
                # here. It rested on "nothing else records it", which is true of a
                # memory row and false of an insight derived from one.)
                if content and not language_matches(content, language):
                    logger.warning(
                        "recurrence_language_mismatch",
                        extra={"expected_language": language,
                               "got_script": dominant_language([content]),
                               "user_id": user_id,
                               "conversation_id": conversation_id},
                    )
                    return

            if len(content) >= 2 and content[0] in "\"'" and content[-1] in "\"'":
                content = content[1:-1].strip()
            if not content:
                logger.info("Recurrence: empty phrasing for conv=%s", conversation_id)
                return

            # Post-generation safety (founder ruling 2026-09-24): not written, for the
            # reason the language gate above gives — the memory rows are untouched and
            # the throttle counts only insights that exist, so this costs nothing
            # lasting. The safety_events row is committed on its own.
            if await output_is_unsafe(
                db, content, user_id=user_id, stage=STAGE_INSIGHT_OUTPUT,
                conversation_id=conversation_id,
            ):
                await db.commit()
                return

            db.add(Insight(
                user_id=user_id,
                conversation_id=conversation_id,
                persona_id=persona_id,
                content=content,
                insight_type=insight_type,
                source_count=source_count,
                evidence=evidence,
            ))
            await db.commit()
            logger.info(
                "Insight written type=%s user=%s conv=%s (%s prior matches)",
                insight_type, user_id, conversation_id, len(prior_matches),
            )
        except Exception as e:
            logger.error("detect_recurrence failed for conv=%s: %s", conversation_id, e, exc_info=True)

memory_service = MemoryService()
