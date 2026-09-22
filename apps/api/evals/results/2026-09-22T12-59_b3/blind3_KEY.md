# Blind read 3 — ANSWER KEY

**Do not open until all eleven are marked.**

Arm B vs arm B3. **Sonnet only, standard mode, first messages.**

Deterministic selection (personas in registry order x the seven standard problems, round-robin, no problem more than twice); pair order and sides shuffled with seed `20260922`. Replies verbatim from each run's completions.jsonl.

| # | persona | problem | A | A words | B | B words |
|---|---|---|---|---|---|---|
| 1 | george_orwell | P04_aging_mother_caregiving | arm B3 | 113 | arm B | 98 |
| 2 | sigmund_freud | P02_toxic_boss_meeting | arm B3 | 86 | arm B | 57 |
| 3 | lao_tzu | P05_fear_of_starting_business | arm B3 | 72 | arm B | 49 |
| 4 | simone_de_beauvoir | P04_aging_mother_caregiving | arm B3 | 106 | arm B | 79 |
| 5 | niccolo_machiavelli | P09_should_i_have_kids | arm B | 74 | arm B3 | 92 |
| 6 | oscar_wilde | P01_ghosting_after_dates | arm B3 | 62 | arm B | 60 |
| 7 | marcus_aurelius | P06_partner_doesnt_see_me | arm B3 | 77 | arm B | 33 |
| 8 | carl_jung | P01_ghosting_after_dates | arm B | 71 | arm B3 | 78 |
| 9 | epictetus | P02_toxic_boss_meeting | arm B3 | 77 | arm B | 52 |
| 10 | miyamoto_musashi | P07_envy_of_friend_success | arm B | 68 | arm B3 | 82 |
| 11 | socrates | P05_fear_of_starting_business | arm B | 53 | arm B3 | 55 |

A is arm B in **4 of 11** pairs, arm B3 in **7**.

## Gate

NEITHER = 0, and arm-B preference not greater than 14:8 across the two readings (22 votes). Two fresh chats, one file each — reading them in one chat is what contaminated blind2 reading 1.

## What B3 changed from B

Register sentence (FIRST_MESSAGE only), "challenge what they have said; do not speculate about what they have not", a target number beside the range, the notice-family banned at prompt level, and the cleaned persona fragments with the B2 bands. B2's question rule is NOT in B3.

Sonnet measured: mean 64.3 -> 93.8 words, in-band 57% -> 76%, notice-family 12.7% -> 6.4%, universal lexicon 1 -> 0, ends-with-a-question 88% -> 86%.
