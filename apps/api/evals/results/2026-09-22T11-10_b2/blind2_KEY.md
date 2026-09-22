# Blind read 2 — ANSWER KEY

**Do not open until all eleven are marked.**

Arm B vs arm B2. **Sonnet only, standard mode, first messages.** Holding the model constant isolates the directive: the first blind read compared two MODELS, this one compares two INSTRUCTIONS.

Deterministic selection (personas in registry order x the seven standard problems, round-robin, no problem more than twice); pair order and sides shuffled with seed `20260922`. Replies verbatim from each run's completions.jsonl.

| # | persona | problem | A | A words | B | B words |
|---|---|---|---|---|---|---|
| 1 | george_orwell | P04_aging_mother_caregiving | arm B2 | 80 | arm B | 98 |
| 2 | sigmund_freud | P02_toxic_boss_meeting | arm B2 | 61 | arm B | 57 |
| 3 | lao_tzu | P05_fear_of_starting_business | arm B2 | 43 | arm B | 49 |
| 4 | simone_de_beauvoir | P04_aging_mother_caregiving | arm B2 | 84 | arm B | 79 |
| 5 | niccolo_machiavelli | P09_should_i_have_kids | arm B | 74 | arm B2 | 71 |
| 6 | oscar_wilde | P01_ghosting_after_dates | arm B2 | 50 | arm B | 60 |
| 7 | marcus_aurelius | P06_partner_doesnt_see_me | arm B2 | 60 | arm B | 33 |
| 8 | carl_jung | P01_ghosting_after_dates | arm B | 71 | arm B2 | 59 |
| 9 | epictetus | P02_toxic_boss_meeting | arm B2 | 53 | arm B | 52 |
| 10 | miyamoto_musashi | P07_envy_of_friend_success | arm B | 68 | arm B2 | 68 |
| 11 | socrates | P05_fear_of_starting_business | arm B | 53 | arm B2 | 45 |

A is arm B in **4 of 11** pairs, arm B2 in **7**.

## What B2 changed

Positive question rule (last sentence a statement), register clause (no contemporary slang), a target number beside the range, four named stance forms, and "challenge what they have said; do not speculate about what they have not".

Measured on Sonnet: ends-with-a-question **88% -> 52%**, in-band 57% -> 59%, no_opening **4% -> 34%** (a floor, not a rate). The open question this read answers is whether the replies that no longer end on a question still feel answerable.
