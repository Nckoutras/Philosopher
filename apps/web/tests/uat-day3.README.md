# Day 3 UAT — free, evidence-first path

## Status
- C: 4/4 silent probes performed, no distinctive recall confirmed; original October 6 seeds not independently verified.
- Cross-persona: 2/4 technically valid.
- D: Library inspection only, return-visit retention unverified.
- G: 0/6 live Safety scenarios.
- TinyFish browser profiles repeatedly lose session; **not evidence of a Wise Room auth defect**.

## Run free smoke test
From `apps/web`, install project dependencies, add `@playwright/test` as a dev dependency if needed, install the Playwright browser, then run:

`npx playwright test tests/uat-day3.smoke.spec.ts`

Environment:
- `WISE_ROOM_UAT_BASE_URL` (default production URL)
- `WISE_ROOM_UAT_EXPECTED_EMAIL` (default Pro1 test account)
- `WISE_ROOM_UAT_STORAGE_STATE` (optional local preauthenticated Playwright storage-state JSON)

**Never commit credentials, cookies, storage-state, or OTPs.** No authentication state has been provided. The authenticated test must SKIP/BLOCK, never claim PASS, until an authorized live session exists.

## Completion gates
1. Validate original Oct 6 conversation IDs and account ownership from an authorized evidence source. No memory verdict before that.
2. For each C/D probe, record exact conversation URL, persona, prompt, complete response, timestamp, and specific old-memory detail if recalled.
3. For G1–G3, verify exact Safety account, new one-to-one conversation, and capture verbatim response. G4/G5 are later-date tests, not Day 3.
4. Distinguish code/static review, simulated tests, and live user-facing UAT in reporting.
5. No test should sign out, request OTP, delete data, or spend TinyFish credits.
