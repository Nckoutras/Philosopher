# You-vs-You brevity band — STEP 2 (prompt change applied)

**Item:** 6 — You-vs-You brevity band
**Branch:** `fix/yvy-brevity` (fresh off `origin/main` @ `b12d2e2e`)
**Commit:** `fix(yvy): brevity band on the two selves`
**Scope:** prompt-only. No enforcement, no schema change, no voice change.

## What changed

One line in `SELF_SYSTEM_PROMPT` — [apps/api/services/self_comparison_prompts.py:9](../../apps/api/services/self_comparison_prompts.py#L9).

**Before:**
> Answer the user's question in the FIRST PERSON, as this version of them — **a few sentences, plain and honest, in their own register.** Draw ONLY on the material above and the question itself. …

**After:**
> Answer the user's question in the FIRST PERSON, as this version of them — **2-4 short sentences, ~50 words maximum. Say the single thing that matters most from the material above, in their own register, then stop. Brevity is the point — a self-portrait, not an essay.** Draw ONLY on the material above and the question itself. …

The whole clause `a few sentences, plain and honest, in their own register.` was replaced (clean swap — the band text carries its own "in their own register", so no duplicate clause and no stray `.,`).

## What was deliberately NOT changed

- **Voice / behavior rules unchanged:** FIRST PERSON, draw-only-on-material, no-invention of biographical facts, thin-signal "answer in the spirit" rule, no-preamble/no-meta. Both selves (`then` and `now`) use the same prompt — confirmed at [self_comparison_service.py:210](../../apps/api/services/self_comparison_service.py#L210).
- **No word-cap enforcement on the streamed body.** The two selves stream (`llm_client.stream`); post-hoc rejection of an over-length answer would be user-visible and disruptive. The band steers via prompt only. A hard cap is a **named, deferred follow-up** — added only if the prompt band proves insufficient in practice.
- **Closing beats untouched.** `hidden_continuity` (30-word cap) and `sentence_owed` (18-word cap) keep their existing `_closing_line` caps — [self_comparison_service.py:289-290](../../apps/api/services/self_comparison_service.py#L289-L290). Out of scope for this change.

## Verification

The prompt is a template string streamed to the model — no runtime surface to unit-drive here. Correctness of the change is textual: diff confirms exactly one clause replaced, `.format()` placeholders (`{which_label}`, `{signals}`, `{self_portrait}`) intact, no other lines touched.

## Gate

Report + commit + push. No PR (per brief).
