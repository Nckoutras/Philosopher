# MEM2-C-1 — callback arm comparison

Run: `2026-10-05_mem2c1`. Rates are call-1 judge verdicts; see `judge_self_agreement` for the noise floor.

## groups

```
{
  "callback|all|all": {
    "completions": 264,
    "judged": 260,
    "callback_rate_on_offer": "32.4% (70/216)",
    "any_callback_rate": "27.3% (71/260)",
    "fidelity_among_callbacks": "92.9% (65/70)",
    "sharpens_among_callbacks": "100.0% (70/70)",
    "timing_conflict_among_callbacks": "1.4% (1/70)",
    "where_or_to_whom_among_callbacks": "4.2% (3/71)",
    "asks_confirmation_among_callbacks": "0.0% (0/71)",
    "misuse_ineligible_rate": "1.5% (4/260)",
    "misuse_by_kind": {
      "self_portrait": 4
    },
    "misuse_rate_in_B": "0.0% (0/44)",
    "repetition_R_then_R2": "73.7% (14/19)",
    "escalation_R2_control": "13.6% (6/44)",
    "escalation_L2_after_affirmation": "11.9% (5/42)",
    "escalation_L1_same_session": "18.2% (8/44)",
    "listening_e_source_shown": "6.6% (16/241)",
    "listening_d": "99.6% (240/241)",
    "listening_a": "55.2% (133/241)",
    "in_band": "56.8% (150/264)",
    "mean_words": 63.3,
    "mean_words_with_callback": 73.8,
    "lao_tzu_in_band": "70.8% (17/24)",
    "reply_language_matches": "98.5% (260/264)"
  },
  "callback|free|all": {
    "completions": 132,
    "judged": 131,
    "callback_rate_on_offer": "17.4% (19/109)",
    "any_callback_rate": "15.3% (20/131)",
    "fidelity_among_callbacks": "84.2% (16/19)",
    "sharpens_among_callbacks": "100.0% (19/19)",
    "timing_conflict_among_callbacks": "5.3% (1/19)",
    "where_or_to_whom_among_callbacks": "5.0% (1/20)",
    "asks_confirmation_among_callbacks": "0.0% (0/20)",
    "misuse_ineligible_rate": "0.8% (1/131)",
    "misuse_by_kind": {
      "self_portrait": 1
    },
    "misuse_rate_in_B": "0.0% (0/22)",
    "repetition_R_then_R2": "57.1% (4/7)",
    "escalation_R2_control": "18.2% (4/22)",
    "escalation_L2_after_affirmation": "14.3% (3/21)",
    "escalation_L1_same_session": "27.3% (6/22)",
    "listening_e_source_shown": "11.3% (14/124)",
    "listening_d": "100.0% (124/124)",
    "listening_a": "60.5% (75/124)",
    "in_band": "59.8% (79/132)",
    "mean_words": 65.8,
    "mean_words_with_callback": 77.9,
    "lao_tzu_in_band": "66.7% (8/12)",
    "reply_language_matches": "97.0% (128/132)"
  },
  "callback|free|el": {
    "completions": 66,
    "judged": 66,
    "callback_rate_on_offer": "9.1% (5/55)",
    "any_callback_rate": "7.6% (5/66)",
    "fidelity_among_callbacks": "60.0% (3/5)",
    "sharpens_among_callbacks": "100.0% (5/5)",
    "timing_conflict_among_callbacks": "0.0% (0/5)",
    "where_or_to_whom_among_callbacks": "0.0% (0/5)",
    "asks_confirmation_among_callbacks": "0.0% (0/5)",
    "misuse_ineligible_rate": "0.0% (0/66)",
    "misuse_by_kind": {},
    "misuse_rate_in_B": "0.0% (0/11)",
    "repetition_R_then_R2": "50.0% (1/2)",
    "escalation_R2_control": "9.1% (1/11)",
    "escalation_L2_after_affirmation": "9.1% (1/11)",
    "escalation_L1_same_session": "27.3% (3/11)",
    "listening_e_source_shown": "15.6% (10/64)",
    "listening_d": "100.0% (64/64)",
    "listening_a": "60.9% (39/64)",
    "in_band": "57.6% (38/66)",
    "mean_words": 62.5,
    "mean_words_with_callback": 72.2,
    "lao_tzu_in_band": "66.7% (4/6)",
    "reply_language_matches": "93.9% (62/66)"
  },
  "callback|free|en": {
    "completions": 66,
    "judged": 65,
    "callback_rate_on_offer": "25.9% (14/54)",
    "any_callback_rate": "23.1% (15/65)",
    "fidelity_among_callbacks": "92.9% (13/14)",
    "sharpens_among_callbacks": "100.0% (14/14)",
    "timing_conflict_among_callbacks": "7.1% (1/14)",
    "where_or_to_whom_among_callbacks": "6.7% (1/15)",
    "asks_confirmation_among_callbacks": "0.0% (0/15)",
    "misuse_ineligible_rate": "1.5% (1/65)",
    "misuse_by_kind": {
      "self_portrait": 1
    },
    "misuse_rate_in_B": "0.0% (0/11)",
    "repetition_R_then_R2": "60.0% (3/5)",
    "escalation_R2_control": "27.3% (3/11)",
    "escalation_L2_after_affirmation": "20.0% (2/10)",
    "escalation_L1_same_session": "27.3% (3/11)",
    "listening_e_source_shown": "6.7% (4/60)",
    "listening_d": "100.0% (60/60)",
    "listening_a": "60.0% (36/60)",
    "in_band": "62.1% (41/66)",
    "mean_words": 69.0,
    "mean_words_with_callback": 80.0,
    "lao_tzu_in_band": "66.7% (4/6)",
    "reply_language_matches": "100.0% (66/66)"
  },
  "callback|pro|all": {
    "completions": 132,
    "judged": 129,
    "callback_rate_on_offer": "47.7% (51/107)",
    "any_callback_rate": "39.5% (51/129)",
    "fidelity_among_callbacks": "96.1% (49/51)",
    "sharpens_among_callbacks": "100.0% (51/51)",
    "timing_conflict_among_callbacks": "0.0% (0/51)",
    "where_or_to_whom_among_callbacks": "3.9% (2/51)",
    "asks_confirmation_among_callbacks": "0.0% (0/51)",
    "misuse_ineligible_rate": "2.3% (3/129)",
    "misuse_by_kind": {
      "self_portrait": 3
    },
    "misuse_rate_in_B": "0.0% (0/22)",
    "repetition_R_then_R2": "83.3% (10/12)",
    "escalation_R2_control": "9.1% (2/22)",
    "escalation_L2_after_affirmation": "9.5% (2/21)",
    "escalation_L1_same_session": "9.1% (2/22)",
    "listening_e_source_shown": "1.7% (2/117)",
    "listening_d": "99.1% (116/117)",
    "listening_a": "49.6% (58/117)",
    "in_band": "53.8% (71/132)",
    "mean_words": 60.8,
    "mean_words_with_callback": 72.3,
    "lao_tzu_in_band": "75.0% (9/12)",
    "reply_language_matches": "100.0% (132/132)"
  },
  "callback|pro|el": {
    "completions": 66,
    "judged": 63,
    "callback_rate_on_offer": "26.9% (14/52)",
    "any_callback_rate": "22.2% (14/63)",
    "fidelity_among_callbacks": "92.9% (13/14)",
    "sharpens_among_callbacks": "100.0% (14/14)",
    "timing_conflict_among_callbacks": "0.0% (0/14)",
    "where_or_to_whom_among_callbacks": "14.3% (2/14)",
    "asks_confirmation_among_callbacks": "0.0% (0/14)",
    "misuse_ineligible_rate": "0.0% (0/63)",
    "misuse_by_kind": {},
    "misuse_rate_in_B": "0.0% (0/11)",
    "repetition_R_then_R2": "75.0% (3/4)",
    "escalation_R2_control": "18.2% (2/11)",
    "escalation_L2_after_affirmation": "0.0% (0/10)",
    "escalation_L1_same_session": "0.0% (0/11)",
    "listening_e_source_shown": "0.0% (0/62)",
    "listening_d": "100.0% (62/62)",
    "listening_a": "56.5% (35/62)",
    "in_band": "39.4% (26/66)",
    "mean_words": 53.4,
    "mean_words_with_callback": 61.7,
    "lao_tzu_in_band": "66.7% (4/6)",
    "reply_language_matches": "100.0% (66/66)"
  },
  "callback|pro|en": {
    "completions": 66,
    "judged": 66,
    "callback_rate_on_offer": "67.3% (37/55)",
    "any_callback_rate": "56.1% (37/66)",
    "fidelity_among_callbacks": "97.3% (36/37)",
    "sharpens_among_callbacks": "100.0% (37/37)",
    "timing_conflict_among_callbacks": "0.0% (0/37)",
    "where_or_to_whom_among_callbacks": "0.0% (0/37)",
    "asks_confirmation_among_callbacks": "0.0% (0/37)",
    "misuse_ineligible_rate": "4.5% (3/66)",
    "misuse_by_kind": {
      "self_portrait": 3
    },
    "misuse_rate_in_B": "0.0% (0/11)",
    "repetition_R_then_R2": "87.5% (7/8)",
    "escalation_R2_control": "0.0% (0/11)",
    "escalation_L2_after_affirmation": "18.2% (2/11)",
    "escalation_L1_same_session": "18.2% (2/11)",
    "listening_e_source_shown": "3.6% (2/55)",
    "listening_d": "98.2% (54/55)",
    "listening_a": "41.8% (23/55)",
    "in_band": "68.2% (45/66)",
    "mean_words": 68.1,
    "mean_words_with_callback": 76.3,
    "lao_tzu_in_band": "83.3% (5/6)",
    "reply_language_matches": "100.0% (66/66)"
  },
  "ruling6|all|all": {
    "completions": 264,
    "judged": 264,
    "callback_rate_on_offer": "0.5% (1/220)",
    "any_callback_rate": "2.3% (6/264)",
    "fidelity_among_callbacks": "100.0% (1/1)",
    "sharpens_among_callbacks": "100.0% (1/1)",
    "timing_conflict_among_callbacks": "0.0% (0/1)",
    "where_or_to_whom_among_callbacks": "33.3% (2/6)",
    "asks_confirmation_among_callbacks": "0.0% (0/6)",
    "misuse_ineligible_rate": "1.5% (4/264)",
    "misuse_by_kind": {
      "background": 1,
      "flagged": 1,
      "self_portrait": 2
    },
    "misuse_rate_in_B": "2.3% (1/44)",
    "repetition_R_then_R2": "0.0% (0/1)",
    "escalation_R2_control": "11.4% (5/44)",
    "escalation_L2_after_affirmation": "13.6% (6/44)",
    "escalation_L1_same_session": "13.6% (6/44)",
    "listening_e_source_shown": "12.1% (31/257)",
    "listening_d": "100.0% (257/257)",
    "listening_a": "58.4% (150/257)",
    "in_band": "50.0% (132/264)",
    "mean_words": 60.0,
    "mean_words_with_callback": 57.0,
    "lao_tzu_in_band": "70.8% (17/24)",
    "reply_language_matches": "95.1% (251/264)"
  },
  "ruling6|free|all": {
    "completions": 132,
    "judged": 132,
    "callback_rate_on_offer": "0.9% (1/110)",
    "any_callback_rate": "4.5% (6/132)",
    "fidelity_among_callbacks": "100.0% (1/1)",
    "sharpens_among_callbacks": "100.0% (1/1)",
    "timing_conflict_among_callbacks": "0.0% (0/1)",
    "where_or_to_whom_among_callbacks": "33.3% (2/6)",
    "asks_confirmation_among_callbacks": "0.0% (0/6)",
    "misuse_ineligible_rate": "3.0% (4/132)",
    "misuse_by_kind": {
      "background": 1,
      "flagged": 1,
      "self_portrait": 2
    },
    "misuse_rate_in_B": "4.5% (1/22)",
    "repetition_R_then_R2": "0.0% (0/1)",
    "escalation_R2_control": "13.6% (3/22)",
    "escalation_L2_after_affirmation": "18.2% (4/22)",
    "escalation_L1_same_session": "27.3% (6/22)",
    "listening_e_source_shown": "19.7% (25/127)",
    "listening_d": "100.0% (127/127)",
    "listening_a": "65.4% (83/127)",
    "in_band": "56.8% (75/132)",
    "mean_words": 65.5,
    "mean_words_with_callback": 57.0,
    "lao_tzu_in_band": "75.0% (9/12)",
    "reply_language_matches": "90.9% (120/132)"
  },
  "ruling6|free|el": {
    "completions": 66,
    "judged": 66,
    "callback_rate_on_offer": "0.0% (0/55)",
    "any_callback_rate": "4.5% (3/66)",
    "fidelity_among_callbacks": "n/a (0)",
    "sharpens_among_callbacks": "n/a (0)",
    "timing_conflict_among_callbacks": "n/a (0)",
    "where_or_to_whom_among_callbacks": "33.3% (1/3)",
    "asks_confirmation_among_callbacks": "0.0% (0/3)",
    "misuse_ineligible_rate": "4.5% (3/66)",
    "misuse_by_kind": {
      "flagged": 1,
      "self_portrait": 2
    },
    "misuse_rate_in_B": "9.1% (1/11)",
    "repetition_R_then_R2": "n/a (0)",
    "escalation_R2_control": "9.1% (1/11)",
    "escalation_L2_after_affirmation": "9.1% (1/11)",
    "escalation_L1_same_session": "18.2% (2/11)",
    "listening_e_source_shown": "24.6% (16/65)",
    "listening_d": "100.0% (65/65)",
    "listening_a": "69.2% (45/65)",
    "in_band": "47.0% (31/66)",
    "mean_words": 62.6,
    "mean_words_with_callback": null,
    "lao_tzu_in_band": "83.3% (5/6)",
    "reply_language_matches": "81.8% (54/66)"
  },
  "ruling6|free|en": {
    "completions": 66,
    "judged": 66,
    "callback_rate_on_offer": "1.8% (1/55)",
    "any_callback_rate": "4.5% (3/66)",
    "fidelity_among_callbacks": "100.0% (1/1)",
    "sharpens_among_callbacks": "100.0% (1/1)",
    "timing_conflict_among_callbacks": "0.0% (0/1)",
    "where_or_to_whom_among_callbacks": "33.3% (1/3)",
    "asks_confirmation_among_callbacks": "0.0% (0/3)",
    "misuse_ineligible_rate": "1.5% (1/66)",
    "misuse_by_kind": {
      "background": 1
    },
    "misuse_rate_in_B": "0.0% (0/11)",
    "repetition_R_then_R2": "0.0% (0/1)",
    "escalation_R2_control": "18.2% (2/11)",
    "escalation_L2_after_affirmation": "27.3% (3/11)",
    "escalation_L1_same_session": "36.4% (4/11)",
    "listening_e_source_shown": "14.5% (9/62)",
    "listening_d": "100.0% (62/62)",
    "listening_a": "61.3% (38/62)",
    "in_band": "66.7% (44/66)",
    "mean_words": 68.4,
    "mean_words_with_callback": 57.0,
    "lao_tzu_in_band": "66.7% (4/6)",
    "reply_language_matches": "100.0% (66/66)"
  },
  "ruling6|pro|all": {
    "completions": 132,
    "judged": 132,
    "callback_rate_on_offer": "0.0% (0/110)",
    "any_callback_rate": "0.0% (0/132)",
    "fidelity_among_callbacks": "n/a (0)",
    "sharpens_among_callbacks": "n/a (0)",
    "timing_conflict_among_callbacks": "n/a (0)",
    "where_or_to_whom_among_callbacks": "n/a (0)",
    "asks_confirmation_among_callbacks": "n/a (0)",
    "misuse_ineligible_rate": "0.0% (0/132)",
    "misuse_by_kind": {},
    "misuse_rate_in_B": "0.0% (0/22)",
    "repetition_R_then_R2": "n/a (0)",
    "escalation_R2_control": "9.1% (2/22)",
    "escalation_L2_after_affirmation": "9.1% (2/22)",
    "escalation_L1_same_session": "0.0% (0/22)",
    "listening_e_source_shown": "4.6% (6/130)",
    "listening_d": "100.0% (130/130)",
    "listening_a": "51.5% (67/130)",
    "in_band": "43.2% (57/132)",
    "mean_words": 54.6,
    "mean_words_with_callback": null,
    "lao_tzu_in_band": "66.7% (8/12)",
    "reply_language_matches": "99.2% (131/132)"
  },
  "ruling6|pro|el": {
    "completions": 66,
    "judged": 66,
    "callback_rate_on_offer": "0.0% (0/55)",
    "any_callback_rate": "0.0% (0/66)",
    "fidelity_among_callbacks": "n/a (0)",
    "sharpens_among_callbacks": "n/a (0)",
    "timing_conflict_among_callbacks": "n/a (0)",
    "where_or_to_whom_among_callbacks": "n/a (0)",
    "asks_confirmation_among_callbacks": "n/a (0)",
    "misuse_ineligible_rate": "0.0% (0/66)",
    "misuse_by_kind": {},
    "misuse_rate_in_B": "0.0% (0/11)",
    "repetition_R_then_R2": "n/a (0)",
    "escalation_R2_control": "9.1% (1/11)",
    "escalation_L2_after_affirmation": "18.2% (2/11)",
    "escalation_L1_same_session": "0.0% (0/11)",
    "listening_e_source_shown": "3.1% (2/65)",
    "listening_d": "100.0% (65/65)",
    "listening_a": "49.2% (32/65)",
    "in_band": "25.8% (17/66)",
    "mean_words": 49.5,
    "mean_words_with_callback": null,
    "lao_tzu_in_band": "50.0% (3/6)",
    "reply_language_matches": "98.5% (65/66)"
  },
  "ruling6|pro|en": {
    "completions": 66,
    "judged": 66,
    "callback_rate_on_offer": "0.0% (0/55)",
    "any_callback_rate": "0.0% (0/66)",
    "fidelity_among_callbacks": "n/a (0)",
    "sharpens_among_callbacks": "n/a (0)",
    "timing_conflict_among_callbacks": "n/a (0)",
    "where_or_to_whom_among_callbacks": "n/a (0)",
    "asks_confirmation_among_callbacks": "n/a (0)",
    "misuse_ineligible_rate": "0.0% (0/66)",
    "misuse_by_kind": {},
    "misuse_rate_in_B": "0.0% (0/11)",
    "repetition_R_then_R2": "n/a (0)",
    "escalation_R2_control": "9.1% (1/11)",
    "escalation_L2_after_affirmation": "0.0% (0/11)",
    "escalation_L1_same_session": "0.0% (0/11)",
    "listening_e_source_shown": "6.2% (4/65)",
    "listening_d": "100.0% (65/65)",
    "listening_a": "53.8% (35/65)",
    "in_band": "60.6% (40/66)",
    "mean_words": 59.7,
    "mean_words_with_callback": null,
    "lao_tzu_in_band": "83.3% (5/6)",
    "reply_language_matches": "100.0% (66/66)"
  }
}
```

## callback_arm_by_candidate_cosine

```
{
  "-1.00-0.30": {
    "offered": 91,
    "used": "30.8% (28/91)",
    "sharpens_given_used": "100.0% (28/28)",
    "production_recall_would_include_candidate": "0.0% (0/91)"
  },
  "0.30-0.40": {
    "offered": 62,
    "used": "35.5% (22/62)",
    "sharpens_given_used": "100.0% (22/22)",
    "production_recall_would_include_candidate": "0.0% (0/62)"
  },
  "0.40-0.50": {
    "offered": 55,
    "used": "30.9% (17/55)",
    "sharpens_given_used": "100.0% (17/17)",
    "production_recall_would_include_candidate": "0.0% (0/55)"
  },
  "0.50-0.60": {
    "offered": 8,
    "used": "37.5% (3/8)",
    "sharpens_given_used": "100.0% (3/3)",
    "production_recall_would_include_candidate": "0.0% (0/8)"
  }
}
```

## callback_arm_by_age

```
{
  "a few weeks ago": {
    "offered": 40,
    "used": "10.0% (4/40)",
    "faithful_given_used": "100.0% (4/4)",
    "timing_conflict_given_used": "0.0% (0/4)"
  },
  "some months ago": {
    "offered": 39,
    "used": "46.2% (18/39)",
    "faithful_given_used": "83.3% (15/18)",
    "timing_conflict_given_used": "5.6% (1/18)"
  },
  "last week": {
    "offered": 40,
    "used": "22.5% (9/40)",
    "faithful_given_used": "88.9% (8/9)",
    "timing_conflict_given_used": "0.0% (0/9)"
  },
  "a few days ago": {
    "offered": 57,
    "used": "45.6% (26/57)",
    "faithful_given_used": "96.2% (25/26)",
    "timing_conflict_given_used": "0.0% (0/26)"
  },
  "a couple of months ago": {
    "offered": 40,
    "used": "32.5% (13/40)",
    "faithful_given_used": "100.0% (13/13)",
    "timing_conflict_given_used": "0.0% (0/13)"
  }
}
```

## judge_self_agreement

```
{
  "cb": "99.6% (521/523)",
  "ff": "99.4% (520/523)",
  "es": "98.9% (517/523)",
  "tm": "100.0% (523/523)",
  "at": "99.8% (522/523)",
  "cf": "100.0% (523/523)",
  "sh": "99.6% (521/523)"
}
```

## judge_failures

```
{
  "callback": 8,
  "listening": 30
}
```

## in_band_by_persona

```
{
  "carl_jung": {
    "callback": "62.5% (15/24)",
    "ruling6": "62.5% (15/24)"
  },
  "epictetus": {
    "callback": "58.3% (14/24)",
    "ruling6": "37.5% (9/24)"
  },
  "george_orwell": {
    "callback": "54.2% (13/24)",
    "ruling6": "37.5% (9/24)"
  },
  "lao_tzu": {
    "callback": "70.8% (17/24)",
    "ruling6": "70.8% (17/24)"
  },
  "marcus_aurelius": {
    "callback": "58.3% (14/24)",
    "ruling6": "62.5% (15/24)"
  },
  "miyamoto_musashi": {
    "callback": "50.0% (12/24)",
    "ruling6": "50.0% (12/24)"
  },
  "niccolo_machiavelli": {
    "callback": "62.5% (15/24)",
    "ruling6": "37.5% (9/24)"
  },
  "oscar_wilde": {
    "callback": "50.0% (12/24)",
    "ruling6": "41.7% (10/24)"
  },
  "sigmund_freud": {
    "callback": "70.8% (17/24)",
    "ruling6": "50.0% (12/24)"
  },
  "simone_de_beauvoir": {
    "callback": "50.0% (12/24)",
    "ruling6": "75.0% (18/24)"
  },
  "socrates": {
    "callback": "37.5% (9/24)",
    "ruling6": "25.0% (6/24)"
  }
}
```
