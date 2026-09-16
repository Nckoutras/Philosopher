# Protocol — reading for sameness

**Written 2026-09-16 (D2-b).** A structured way to read three long conversations
and mark where convergence starts. Pairs with `RUNBOOK_LOOP_METRICS.md` §7; it
does not replace it, and §7 does not replace this.

**Why both.** §7's SQL is lexical: it scores two replies by the words they share.
A persona that makes the same point twice in fresh vocabulary scores **zero**
there — and that is the exact failure the prompt's own ADVANCEMENT block names
(*"not reworded, not as a new image, not as a different move type"*). A reader
catches it and the query cannot. Conversely this protocol has n=3 and one reader;
§7 has 180 conversations and no opinion. Neither is sufficient.

**The bias, named rather than managed.** You built the personas, you know the
prompt, and you will mostly be reading your own conversations — the only ones
deep enough. You will see intended behaviour as intended. That is not correctable
by procedure; it is the reason this is one input and not the verdict. Record what
you saw, not what you concluded.

---

## Step 1 — pick the conversations

```sql
-- The deepest real threads. Exclude your admin account only if you have a
-- non-admin one you actually use; on current data that would leave nothing.
SELECT c.id, p.slug AS persona, count(*) AS assistant_turns,
       min(m.created_at)::date AS started
FROM messages m
JOIN conversations c ON c.id = m.conversation_id
JOIN personas p ON p.id = c.persona_id
WHERE m.role = 'assistant'
  AND m.message_kind <> 'conclusion'
  AND m.persona_override = false
  AND c.deleted_at IS NULL
GROUP BY c.id, p.slug
ORDER BY assistant_turns DESC
LIMIT 5;
```

Take the top 3. **If two of them are the same persona, keep both** — same-persona
convergence across two threads is a stronger observation than one each.

On 2026-09-16 this query returned **47, 39, 27** persona turns for the top three,
each a different persona (Lao Tzu, Wilde, Freud), with six conversations at ≥20
and **two** at ≥30 in total.

Two things follow, and both belong in how you read:

- **The teardown's "turn 30-50" window exists in exactly two threads in the whole
  product**, and the third thread you read stops at 27 — before the window opens.
- **No two of the three share a persona**, so any pattern you find is either
  persona-independent or a coincidence of one voice. You cannot tell which from
  n=3. Say which persona each observation came from.

## Step 2 — read forward, once, without skipping

Read each thread from turn 1 in order. **Do not skim to the end**; the thing being
measured is *when* it starts, which is unrecoverable if you have already read the
later turns.

At each assistant reply, ask one question:

> **Could this reply have been a paraphrase of an earlier reply in this same
> thread?**

Not "is it similar in topic" — a thread stays on topic, and should. The test is
whether the *move* has already been made: the same interpretation, the same
reframe, the same observation, wearing different words.

Mark the **first** turn where the answer is yes. That number is the finding.

## Step 3 — the marking sheet

One row per conversation.

| field | what to record |
| --- | --- |
| conversation | persona slug + total assistant turns |
| **first paraphrase turn** | the turn number from Step 2, or `none` |
| what was restated | one line, in your words |
| which earlier turn it restates | turn number |
| confidence | high / medium / low — low is a real and useful answer |

## Step 4 — the constant-block check

This is the half that localises the cause, and it is the reason the protocol is
worth more than an impression.

Four of the fourteen conversational moves in `apps/api/prompts/system_base.jinja2`
ship with a **literal sentence template** in the prompt. If a persona is
converging on scaffolding rather than on thought, these are where it will show:

| move | the shape shipped in the prompt |
| --- | --- |
| `precision_distinction` | "There is a difference between X and Y; this sounds closer to Y." |
| `reframe` | "You may be treating this as X. Consider it as Y." |
| `pattern_naming` | "The pattern is not X. It is Y." |
| `value_hierarchy` | "Right now, X is outranking Y." |

For each thread, note **how many times each shape appears** — counting close
variants, not just exact matches.

| shape | thread 1 | thread 2 | thread 3 |
| --- | ---: | ---: | ---: |
| difference between X and Y | | | |
| treating this as X / consider as Y | | | |
| the pattern is not X, it is Y | | | |
| X is outranking Y | | | |
| *other phrase you saw 3+ times* | | | |

The prompt instructs rotation — *"do not repeat the kind of move from your last
2-3 replies"*. **Three or more occurrences of one shape inside a ten-turn stretch
is that instruction failing**, and it is a different defect from general
blandness: it points at the moves block, which is 282 tokens of the ~2,331-token
constant prefix, rather than at the model.

Write down any other phrase you notice three or more times, even if it is not in
the table. That free row is the one most likely to find something the code review
could not.

## Step 5 — report

Four lines, to sit beside §7's baseline:

1. First-paraphrase turn for each of the three threads.
2. The single most-repeated shape, and its count.
3. Whether the repetition felt like **the persona being consistent** (wanted) or
   **the persona being stuck** (the defect). These are genuinely hard to tell
   apart and the distinction is the judgement only a reader can make.
4. Anything that changed your mind about the teardown's "turn 30-50" claim.

**Do not fix anything as a result of this read.** D2 ruled the lever deferred
until (a) and (b) both have numbers; this is (b). A fix chosen from three
conversations read by their author is the guesswork the ruling declined.
