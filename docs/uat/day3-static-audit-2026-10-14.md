# Day 3 static audit — 2026-10-14

Scope: repository main source inspected via GitHub. **Not an executed test run or live UAT.**

## Confirmed code facts
- `apps/api/services/memory_service.py`: inferred-memory relevance threshold `INFERRED_SCORE_FLOOR = 0.45`; historical 0.75 was reportedly so restrictive that no Lane B recall fired in the documented sample. This is a code comment reporting a prior measurement, **not** independently reproduced here.
- Standing memories (`stated`, `self_portrait`) bypass the relevance floor but are capped. Inferred memories are floor-gated and type-capped. Recall budget 8.
- Near-duplicate memory candidate threshold 0.75; SQL computes candidate-to-candidate similarity and the Python selection removes near duplicates.
- `apps/api/services/safety_gate.py`: Tier A -> CRISIS, B:HIGH on judge failure -> CRISIS, B:MEDIUM on judge failure -> MEDIUM.
- `apps/api/services/safety_judge.py`: 2.5-second timeout, zero SDK retries; invalid responses and API errors return failure.
- `apps/api/tests/services/test_safety_judge.py`: existing unit tests cover timeout, API errors, disabled judge, invalid verdicts, and response shape. **Tests inspected, not executed.**

## Implications for Day 3
- C1–C4 silence alone is **not** proof of broken memory: need source seed rows, active status, embeddings, retrieval scores, and chat injection evidence.
- Safety G1–G3 remain **0 live tests**. Static safeguards do not establish user-facing quality or false-alarm rate.
- Authentication remains blocked; no credentials, OTP or session tokens are in this PR.

## Next validation gates
1. Locate exact Oct 6 seed conversation IDs and memory rows using an authorized production audit path.
2. For each C probe correlate query similarity, selected memory IDs and prompt inclusion; distinguish no write vs no retrieval vs no expression.
3. Run existing safety unit tests in CI and add G1–G3 UI tests only when authenticated test account access is available.
4. Never count skipped tests as passed.
