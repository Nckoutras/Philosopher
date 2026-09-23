# Listening judge — the 44-reply calibration sample

**Source run `2026-09-22T12-59_b3`, `prompt_set_hash 0a2a2d868600bb26`,
`persona_config_hash be4c9e3d3d7e7959`.** 44 B3 Sonnet standard-mode replies,
each judged twice in independent calls = 88 judgements.

**THE IDS ARE LISTED HERE BECAUSE THEY CANNOT BE RECOMPUTED FROM THE REPOSITORY.**
`completions.jsonl` is gitignored by convention, so `select_calibration()` needs a
local copy of the run to rebuild this list. Without the ids written down, the
selection rule is a claim about a set nobody can reproduce.

## The rule

1. Pool = B3's `completions.jsonl`, `plan == "pro"`, `mode != "deep"`, no error (77 rows).
2. Each persona's **blind3 B3 reply** is taken first and always (11 rows, one per persona).
3. The remaining 3 per persona are chosen **greedily to even out a global problem
   counter**, personas in sorted order, ties broken by `sample_id`.
4. Sorted by `sample_id`.

No RNG — sorts and a counter only, so the set reproduces without a seed.

**Why step 3 exists:** the first version shuffled each persona's pool with one shared
seed, which hands every persona the same permutation. The set came out 11x P01, 11x
P06, 10x P07 and 1x P09 — three problems carrying three quarters of a calibration
that is supposed to be about how replies handle particular content.

## Balance

Personas: all 11 at 4 each. Problems: P01 7, P02 7, P04 6, P05 6, P06 6, P07 6, P09 6.

## The 44

`*` marks the 11 blind3 replies the founder has already read by eye.

| # | sample_id | blind3 |
|---|---|---|
| 1 | `P01_ghosting_after_dates::carl_jung::standard` | * |
| 2 | `P01_ghosting_after_dates::epictetus::standard` |  |
| 3 | `P01_ghosting_after_dates::lao_tzu::standard` |  |
| 4 | `P01_ghosting_after_dates::miyamoto_musashi::standard` |  |
| 5 | `P01_ghosting_after_dates::oscar_wilde::standard` | * |
| 6 | `P01_ghosting_after_dates::sigmund_freud::standard` |  |
| 7 | `P01_ghosting_after_dates::socrates::standard` |  |
| 8 | `P02_toxic_boss_meeting::epictetus::standard` | * |
| 9 | `P02_toxic_boss_meeting::george_orwell::standard` |  |
| 10 | `P02_toxic_boss_meeting::lao_tzu::standard` |  |
| 11 | `P02_toxic_boss_meeting::niccolo_machiavelli::standard` |  |
| 12 | `P02_toxic_boss_meeting::sigmund_freud::standard` | * |
| 13 | `P02_toxic_boss_meeting::simone_de_beauvoir::standard` |  |
| 14 | `P02_toxic_boss_meeting::socrates::standard` |  |
| 15 | `P04_aging_mother_caregiving::epictetus::standard` |  |
| 16 | `P04_aging_mother_caregiving::george_orwell::standard` | * |
| 17 | `P04_aging_mother_caregiving::marcus_aurelius::standard` |  |
| 18 | `P04_aging_mother_caregiving::niccolo_machiavelli::standard` |  |
| 19 | `P04_aging_mother_caregiving::sigmund_freud::standard` |  |
| 20 | `P04_aging_mother_caregiving::simone_de_beauvoir::standard` | * |
| 21 | `P05_fear_of_starting_business::epictetus::standard` |  |
| 22 | `P05_fear_of_starting_business::lao_tzu::standard` | * |
| 23 | `P05_fear_of_starting_business::marcus_aurelius::standard` |  |
| 24 | `P05_fear_of_starting_business::niccolo_machiavelli::standard` |  |
| 25 | `P05_fear_of_starting_business::sigmund_freud::standard` |  |
| 26 | `P05_fear_of_starting_business::socrates::standard` | * |
| 27 | `P06_partner_doesnt_see_me::carl_jung::standard` |  |
| 28 | `P06_partner_doesnt_see_me::george_orwell::standard` |  |
| 29 | `P06_partner_doesnt_see_me::marcus_aurelius::standard` | * |
| 30 | `P06_partner_doesnt_see_me::miyamoto_musashi::standard` |  |
| 31 | `P06_partner_doesnt_see_me::oscar_wilde::standard` |  |
| 32 | `P06_partner_doesnt_see_me::simone_de_beauvoir::standard` |  |
| 33 | `P07_envy_of_friend_success::carl_jung::standard` |  |
| 34 | `P07_envy_of_friend_success::george_orwell::standard` |  |
| 35 | `P07_envy_of_friend_success::marcus_aurelius::standard` |  |
| 36 | `P07_envy_of_friend_success::miyamoto_musashi::standard` | * |
| 37 | `P07_envy_of_friend_success::oscar_wilde::standard` |  |
| 38 | `P07_envy_of_friend_success::simone_de_beauvoir::standard` |  |
| 39 | `P09_should_i_have_kids::carl_jung::standard` |  |
| 40 | `P09_should_i_have_kids::lao_tzu::standard` |  |
| 41 | `P09_should_i_have_kids::miyamoto_musashi::standard` |  |
| 42 | `P09_should_i_have_kids::niccolo_machiavelli::standard` | * |
| 43 | `P09_should_i_have_kids::oscar_wilde::standard` |  |
| 44 | `P09_should_i_have_kids::socrates::standard` |  |
