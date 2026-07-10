# Counterview — share-card title + user-quote contrast (item 7)

**Branch:** `feat/counterview-share-title` · **Migration:** 044 · **Date:** 2026-07-10

## What shipped

The public counterview share card stopped printing the user's raw confession
(`anchor_text`) and now prints a 2-4 word **terrain title** generated on the same LLM
call as the verdicts. The in-app card keeps showing the confession but at higher
contrast so it reads clearly as "your words" against the personas' verdicts.

## Changes

### 1. Migration 044 (`044_counterview_title`)
- `ALTER TABLE counterviews ADD COLUMN title TEXT` — additive, nullable. Id 21 chars
  (≤32, C-04); filename == revision id; `down_revision = '043_future_self_prediction'`
  (sole child, no branch). Old rows stay NULL.
- Model: `Counterview.title: Mapped[str | None]` added after `still_stands`.

### 2. Creation (`services/counterview_service.py`)
- **Prompt:** appended the approved TITLE block to `COUNTERVIEW_PROMPT` (terrain, 2-4
  words, §5.7 register, same language as the belief, form-varied, nearest-honest-theme
  when vague). JSON contract gained a `title` sibling key alongside `still_stands`.
- **Parse:** `_extract_verdicts` reads `title` from the SAME JSON and returns a 3-tuple
  `(verdicts, still_stands, title)`; all three "empty" return paths updated to
  `None, None, None`. `_call_llm` propagates the 3-tuple.
- **Retry:** the tightening retry adopts the retry response's `title` wholesale, same as
  its verdicts + still_stands.
- **Clean:** new `_clean_title` mirrors `_clean_still_stands` — strips surrounding quotes
  and trailing sentence punctuation, hard-nulls > `TITLE_MAX_WORDS` (4), and passes the
  same output-safety gate. `_write_counterview` gained a `title` param.
- **C-01 field-level:** a failed / empty / over-length / safety-flagged title is nulled
  only — it NEVER blocks the counterview, whose verdicts already passed. Non-generated
  statuses (empty / suppressed) store `title = NULL`.

### 3. Shared card (`services/image_service.py`)
- `_render_counterview_card` param `anchor_text` → `title`; step 7 now renders the title
  in **Cormorant Medium 46, ink, prominent** (was italic sepia 30). `if title:` guard —
  a NULL title omits the line entirely; the card **never** falls back to printing
  `anchor_text`. `generate_counterview_share_image` passes `title=cv.title`.

### 4. In-app card (`components/reflections/CounterviewVerdictCard.tsx`)
- The `anchor_text` quote stays; contrast raised for legibility as "your words":

  ```diff
  - <p className="font-cormorant text-[15px] italic text-sepia leading-snug mb-[12px]">
  + <p className="font-cormorant text-[15px] italic text-ink leading-snug mb-[12px]">
  ```
  Only `text-sepia → text-ink`. Already full opacity (no opacity class). Italic + size
  unchanged.

## Verification
- `py_compile` clean on all four changed Python files + the migration.
- Migration chain verified: 042 → 043 → 044, 044 the sole child of 043.
- All call sites of the changed-arity functions (`_call_llm`, `_extract_verdicts`,
  `_render_counterview_card`) updated; no external callers.
- `pytest -k counterview`: 6 passed. **2 pre-existing failures** in
  `test_counterview_rebuttal.py` (`test_serializer_rebuttals_remaining_zero_at_cap`,
  `test_serializes_deeper_and_turns_without_collision`) — confirmed identical on clean
  origin/main via stash. Root cause is a MagicMock leaking into `CounterviewOut.still_stands`
  pydantic validation (a test-mock gap from migration 041), unrelated to this change and
  out of scope.

## Not touched (scoped out)
- `reflections_feed_service.py` / `ReflectionFeedCounterview` — title is share-card only;
  the in-app feed schema is unchanged. If title is ever wanted in-app, that schema + the
  serializer would need it.
- The pre-existing rebuttal test-mock failures above (separate fix).
