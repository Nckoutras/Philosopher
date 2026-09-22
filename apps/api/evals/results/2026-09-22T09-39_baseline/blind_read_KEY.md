# Blind read — ANSWER KEY

**Do not open until all eleven pairs are marked.**

Source: `evals/results/2026-09-22T09-39_baseline` (run 1 baseline, 2026-09-22). Standard-mode samples only, no deep.

Selection is deterministic: the eleven personas in registry order against the seven standard-mode problems, round-robin, so no problem appears more than twice. Pair order and the A/B side were shuffled with seed `20260922`.

Replies are verbatim from `completions.jsonl` and were **not** touched by the later rescore, which rewrote only scores.csv, summary.csv and manifest.json.

| # | persona | problem | A | A words | B | B words |
|---|---|---|---|---|---|---|
| 1 | george_orwell | P04_aging_mother_caregiving | Sonnet 4.6 (pro) | 69 | Haiku 4.5 (free) | 141 |
| 2 | sigmund_freud | P02_toxic_boss_meeting | Sonnet 4.6 (pro) | 47 | Haiku 4.5 (free) | 37 |
| 3 | lao_tzu | P05_fear_of_starting_business | Sonnet 4.6 (pro) | 32 | Haiku 4.5 (free) | 51 |
| 4 | simone_de_beauvoir | P04_aging_mother_caregiving | Sonnet 4.6 (pro) | 54 | Haiku 4.5 (free) | 127 |
| 5 | niccolo_machiavelli | P09_should_i_have_kids | Haiku 4.5 (free) | 101 | Sonnet 4.6 (pro) | 41 |
| 6 | oscar_wilde | P01_ghosting_after_dates | Sonnet 4.6 (pro) | 50 | Haiku 4.5 (free) | 70 |
| 7 | marcus_aurelius | P06_partner_doesnt_see_me | Sonnet 4.6 (pro) | 32 | Haiku 4.5 (free) | 49 |
| 8 | carl_jung | P01_ghosting_after_dates | Haiku 4.5 (free) | 92 | Sonnet 4.6 (pro) | 45 |
| 9 | epictetus | P02_toxic_boss_meeting | Sonnet 4.6 (pro) | 52 | Haiku 4.5 (free) | 161 |
| 10 | miyamoto_musashi | P07_envy_of_friend_success | Haiku 4.5 (free) | 112 | Sonnet 4.6 (pro) | 30 |
| 11 | socrates | P05_fear_of_starting_business | Haiku 4.5 (free) | 28 | Sonnet 4.6 (pro) | 38 |

A is Haiku in **4 of 11** pairs, Sonnet in **7**.

## Why this read exists

Run 1 measured Haiku at a mean of 109.5 words, exceeding its persona's stated band on 69.1% of replies; Sonnet at 47.0 words and 2.7%. Every instrument in the harness treats the shorter reply as the better one, because the band is what the prompt asks for.

This read asks the question from the other side: **is the longer reply actually worse to receive?** If it is not, then arm B optimises toward a target nobody chose, and the 69.1% is a finding about a rule rather than about a product.
