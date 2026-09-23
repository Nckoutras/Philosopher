# This run measured nothing. It is kept as the evidence that it measured nothing.

**2026-09-23.** 30 Sonnet replies (marcus_aurelius, lao_tzu, miyamoto_musashi ×
10 problems), arm `b3`, bridge on, 0 errors, **$0.2193**.

It was generated to test an approved voice fix. **The fix could not have had any
effect**, because all four approved diffs edited `PersonaConfig.character_anchors`,
and that field reaches no code that runs — see **TD-94**.

**The proof is in this directory's own `manifest.json`:**

```
persona_config_hash: be4c9e3d3d7e7959     <- identical to 2026-09-22T12-59_b3
prompt_set_hash:     0a2a2d868600bb26     <- identical to b3
```

`run.py:persona_config_hash()` hashes **the rendered prompt**. An identical hash
after a config edit means the edit does not reach the prompt. Independently: 21 of
the 30 samples have `system_prompt_chars` byte-identical to their B3 counterparts.
The 9 that differ are the deep ones, by a constant +73 chars — the register clause
reaching DEEP, a founder-ruled change since B3 recorded in `evals/arm_b3.py`, and
unrelated to the edits.

**The replies here differ from B3's only by sampling noise.** They were NOT judged.
Running the distinctiveness judge over them would have cost ~$0.29 to measure the
temperature of a decoder, and the run was stopped instead.

**Do not diff this against B3 and read the difference as a voice change.** That is
the one wrong use of this directory, and it is why this file sits next to the data
rather than in a commit message.

The persona edits that produced it were reverted in the same session — they asserted,
in a field nothing reads, behaviour that the rendered `system_fragment` forbids.
