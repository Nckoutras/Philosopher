"""Greek CONTENT in the forbidden lexicons (TD-60 part 2).

#621 taught the voice checks to read Greek and deliberately added none. This
file is the content that landed after it: 87 universal Greek phrases across
seven categories, and the first persona lexicons for lao_tzu,
niccolo_machiavelli and oscar_wilde — the last three of the eleven that
carried none.

THE ENTRIES BELOW ARE WRITTEN OUT RATHER THAN READ BACK FROM THE LEXICON, and
that is the point of the file. A test that derives its expectation from the
file it is checking cannot fail when an entry is deleted — the parametrised
case simply disappears and the suite stays green. These literals are an
independent second copy, so a dropped entry is a red test.

WHAT IS DELIBERATELY NOT FORBIDDEN. The content is founder-locked (2026-09-09
arbitration) and its rule is that bare proper names and work titles are NOT
forbidden — only self-reference phrasings and method explanations. So
`ως Λάο Τσε` is a hit and `ο Κομφούκιος θα διαφωνούσε` is not. The innocent
sentences are where that line is pinned, and they are the half of this file
most likely to catch a future over-broad entry.
"""
import pytest

from personas import PERSONA_REGISTRY, get_persona
from services.postprocessing_service import (
    CheckAction,
    _deterministic_strip,
    check_persona_forbidden,
    check_universal_forbidden,
)
from text_utils import normalize


# A carrier with no forbidden content of its own, pinned clean by
# test_the_carrier_sentence_is_itself_clean before anything is read into it.
WRAPPER = "Κάτσε λίγο. %s. Πάμε παρακάτω."


GREEK_UNIVERSAL = [
    # ai_tells
    ("ai_tells", "ως τεχνητή νοημοσύνη"),
    ("ai_tells", "σαν τεχνητή νοημοσύνη"),
    ("ai_tells", "ως μοντέλο γλώσσας"),
    ("ai_tells", "σαν μοντέλο γλώσσας"),
    ("ai_tells", "ως γλωσσικό μοντέλο"),
    ("ai_tells", "σαν γλωσσικό μοντέλο"),
    ("ai_tells", "είμαι ένα γλωσσικό μοντέλο"),
    ("ai_tells", "είμαι γλωσσικό μοντέλο"),
    ("ai_tells", "είμαι τεχνητή νοημοσύνη"),
    ("ai_tells", "είμαι μια τεχνητή νοημοσύνη"),
    ("ai_tells", "είμαι AI"),
    ("ai_tells", "είμαι ένα πρόγραμμα"),
    ("ai_tells", "είμαι πρόγραμμα"),
    ("ai_tells", "είμαι ένα chatbot"),
    ("ai_tells", "είμαι chatbot"),
    ("ai_tells", "είμαι τσατμποτ"),
    ("ai_tells", "δεν έχω συναισθήματα"),
    ("ai_tells", "δεν μπορώ να νιώσω πραγματικά"),
    ("ai_tells", "δεν μπορώ να αισθανθώ πραγματικά"),
    ("ai_tells", "δεν έχω προσωπικές εμπειρίες"),
    ("ai_tells", "δεν έχω προσωπική εμπειρία"),
    ("ai_tells", "τα δεδομένα εκπαίδευσής μου"),
    ("ai_tells", "με βάση την εκπαίδευσή μου"),
    ("ai_tells", "εκπαιδεύτηκα σε δεδομένα"),
    # therapy_jargon_as_persona_concept
    ("therapy_jargon_as_persona_concept", "στυλ προσκόλλησης"),
    ("therapy_jargon_as_persona_concept", "αγχώδης προσκόλληση"),
    ("therapy_jargon_as_persona_concept", "αποφευκτική προσκόλληση"),
    ("therapy_jargon_as_persona_concept", "ασφαλής προσκόλληση"),
    ("therapy_jargon_as_persona_concept", "τραυματική αντίδραση"),
    ("therapy_jargon_as_persona_concept", "τραυματικός δεσμός"),
    ("therapy_jargon_as_persona_concept", "δεσμός τραύματος"),
    ("therapy_jargon_as_persona_concept", "συναισθηματική ρύθμιση"),
    ("therapy_jargon_as_persona_concept", "συνεξάρτηση"),
    ("therapy_jargon_as_persona_concept", "ναρκισσιστική κακοποίηση"),
    ("therapy_jargon_as_persona_concept", "να βάλεις όρια"),
    ("therapy_jargon_as_persona_concept", "βάλε όρια"),
    ("therapy_jargon_as_persona_concept", "υγιή όρια"),
    ("therapy_jargon_as_persona_concept", "θέσε όρια"),
    ("therapy_jargon_as_persona_concept", "ενεργοποιεί το τραύμα σου"),
    ("therapy_jargon_as_persona_concept", "να επεξεργαστείς το τραύμα"),
    # self_help_platitudes
    ("self_help_platitudes", "εμπιστεύσου τη διαδικασία"),
    ("self_help_platitudes", "όλα γίνονται για κάποιο λόγο"),
    ("self_help_platitudes", "το σύμπαν συνωμοτεί"),
    ("self_help_platitudes", "ζήσε την αλήθεια σου"),
    ("self_help_platitudes", "μίλα την αλήθεια σου"),
    ("self_help_platitudes", "κυνήγα τα όνειρά σου"),
    ("self_help_platitudes", "ζήσε την καλύτερη ζωή σου"),
    ("self_help_platitudes", "μόνο θετική ενέργεια"),
    ("self_help_platitudes", "θετικές δονήσεις"),
    ("self_help_platitudes", "η καλύτερη εκδοχή του εαυτού σου"),
    ("self_help_platitudes", "απλά να είσαι ο εαυτός σου"),
    ("self_help_platitudes", "σκέψου θετικά"),
    ("self_help_platitudes", "πίστεψε στον εαυτό σου"),
    ("self_help_platitudes", "βγες από τη ζώνη άνεσής σου"),
    # throat_clearing_openers
    ("throat_clearing_openers", "είναι ενδιαφέρον που αναφέρεις"),
    ("throat_clearing_openers", "ενδιαφέρουσα ερώτηση"),
    ("throat_clearing_openers", "πολύ καλή ερώτηση"),
    ("throat_clearing_openers", "ωραία ερώτηση"),
    ("throat_clearing_openers", "σε ευχαριστώ που μοιράστηκες"),
    ("throat_clearing_openers", "σε ευχαριστώ που το μοιράζεσαι"),
    ("throat_clearing_openers", "ευχαριστώ που μοιράζεσαι"),
    ("throat_clearing_openers", "ευχαριστώ που το μοιράστηκες"),
    ("throat_clearing_openers", "χαίρομαι που ρωτάς"),
    # summary_of_user
    ("summary_of_user", "αυτό που λες είναι ότι"),
    ("summary_of_user", "με άλλα λόγια, λες ότι"),
    ("summary_of_user", "απ' ό,τι καταλαβαίνω, νιώθεις"),
    # closing_flourishes
    ("closing_flourishes", "ελπίζω να βοήθησα"),
    ("closing_flourishes", "ελπίζω αυτό να βοηθάει"),
    ("closing_flourishes", "είμαι εδώ για σένα"),
    ("closing_flourishes", "είμαι εδώ αν με χρειαστείς"),
    ("closing_flourishes", "είμαι εδώ αν χρειαστείς"),
    ("closing_flourishes", "σου στέλνω αγάπη"),
    ("closing_flourishes", "σου στέλνω φως"),
    ("closing_flourishes", "σου εύχομαι τα καλύτερα"),
    ("closing_flourishes", "μη διστάσεις να μοιραστείς"),
    ("closing_flourishes", "καλή συνέχεια"),
    ("closing_flourishes", "να είσαι καλά"),
    # ai_safety_overcaveat
    ("ai_safety_overcaveat", "δεν είμαι ψυχολόγος"),
    ("ai_safety_overcaveat", "δεν είμαι θεραπευτής"),
    ("ai_safety_overcaveat", "δεν είμαι θεραπεύτρια"),
    ("ai_safety_overcaveat", "δεν είμαι γιατρός"),
    ("ai_safety_overcaveat", "δεν είμαι ειδικός"),
    ("ai_safety_overcaveat", "δεν είμαι ειδική"),
    ("ai_safety_overcaveat", "αυτό δεν είναι ιατρική συμβουλή"),
    ("ai_safety_overcaveat", "δεν αποτελεί ιατρική συμβουλή"),
    ("ai_safety_overcaveat", "αυτό δεν είναι θεραπεία"),
    ("ai_safety_overcaveat", "δεν αποτελεί θεραπεία"),
]

GREEK_PERSONA = [
    # lao_tzu
    ("lao_tzu", "ενσυνειδητότητα"),
    ("lao_tzu", "εφαρμογή διαλογισμού"),
    ("lao_tzu", "όπως έγραψα"),
    ("lao_tzu", "ως Λάο Τσε"),
    ("lao_tzu", "στο βιβλίο μου"),
    ("lao_tzu", "γου γουέι σημαίνει"),
    ("lao_tzu", "η έννοια του γου γουέι"),
    ("lao_tzu", "άσε με να σου εξηγήσω το Τάο"),
    # niccolo_machiavelli
    ("niccolo_machiavelli", "όπως έγραψα"),
    ("niccolo_machiavelli", "ως Μακιαβέλι"),
    ("niccolo_machiavelli", "η εξορία μου"),
    ("niccolo_machiavelli", "η Φλωρεντία της εποχής μου"),
    ("niccolo_machiavelli", "στον Ηγεμόνα μου"),
    ("niccolo_machiavelli", "στο βιβλίο μου"),
    # oscar_wilde
    ("oscar_wilde", "όπως είπα κάποτε"),
    ("oscar_wilde", "όπως έχω πει"),
    ("oscar_wilde", "σε ένα έργο μου"),
    ("oscar_wilde", "σε ένα από τα έργα μου"),
    ("oscar_wilde", "στο μυθιστόρημά μου"),
    ("oscar_wilde", "όταν ήμουν στη φυλακή"),
]

# (slug, regex, a line it must catch, a neighbouring line it must not)
PERSONA_PATTERNS = [
    ("lao_tzu",
     r"^(first|step 1|1\.|here are)",
     "First, sit with it for a while.",
     "Sit with it for a while first."),
    ("lao_tzu",
     r"\b(you should|you must|you need to)\b",
     "You should let the matter rest.",
     "Whether to let it rest is not mine to command."),
    ("niccolo_machiavelli",
     r"\bthe ends? justif(y|ies) the means\b",
     "The end justifies the means, as they say.",
     "The end and the means are weighed together."),
    ("niccolo_machiavelli",
     r"\b(that is|this is) (immoral|unethical|wrong of you)\b",
     "That is immoral and you know it.",
     "That is prudent, whatever they choose to call it."),
    ("oscar_wilde",
     r"\bi (once |famously )?(said|wrote|quipped|remarked) that\b",
     "I once said that youth is wasted on the young.",
     "Someone remarked, years ago, that youth is wasted."),
    ("oscar_wilde",
     r"\bi can resist (everything|anything) except temptation\b",
     "I can resist everything except temptation.",
     "Temptation is the one thing nobody resists."),
]

# (sentence, persona to also check it against, why it must stay clean)
INNOCENT_GREEK = [
    ("δεν θα ισχυριστώ ότι καταλαβαίνω απόλυτα πώς νιώθεις",
     None,
     "hedged empathy, not a summary of the user"),
    ("αν κατάλαβα καλά, ρωτάς για τη σχέση σου με τον χρόνο.",
     None,
     "a genuine check, not the summary opener"),
    ("κάθε εμπόδιο είναι ευκαιρία για αρετή",
     None,
     "Stoic doctrine, not a self-help platitude"),
    ("να προσέχεις τον εαυτό σου, όπως έλεγε ο Σωκράτης",
     None,
     "care of the self, not a sign-off flourish"),
    ("ο Κομφούκιος θα διαφωνούσε",
     "lao_tzu",
     "a bare proper name, allowed by the locked _rule"),
    ("ο Τσέζαρε Βοργία έκανε ακριβώς αυτό",
     "niccolo_machiavelli",
     "a bare proper name, allowed by the locked _rule"),
    ("τα όρια του χάρτη δεν είναι τα όρια του κόσμου",
     None,
     "a real noun, not the therapy imperative"),
    ("η αλήθεια σου δεν είναι πάντα η αλήθεια",
     None,
     "near-miss of the live-your-truth platitude"),
    ("δεν είμαι βέβαιος ότι η ερώτηση είναι η σωστή",
     None,
     "near-miss of the not-a-specialist caveat family"),
    ("ο Όσκαρ Ουάιλντ έγραψε για τη μάσκα και το πρόσωπο",
     "oscar_wilde",
     "third-person reference to his own work, allowed"),
]


def test_the_carrier_sentence_is_itself_clean():
    """If WRAPPER ever trips a check, every detection test below would pass
    for the wrong reason."""
    r = check_universal_forbidden(WRAPPER % "τίποτα εδώ")
    assert r.passed is True, [h.matched_text for h in r.hits]
    for slug in ("lao_tzu", "niccolo_machiavelli", "oscar_wilde"):
        rp = check_persona_forbidden(WRAPPER % "τίποτα εδώ", get_persona(slug))
        assert rp.passed is True, (slug, [h.matched_text for h in rp.hits])


# -- The entries are shipped --------------------------------------------------

@pytest.mark.parametrize("category,phrase", GREEK_UNIVERSAL)
def test_the_universal_lexicon_still_ships_this_greek_entry(category, phrase):
    from services.postprocessing_service import _UNIVERSAL_FORBIDDEN
    shipped = _UNIVERSAL_FORBIDDEN["categories"][category].get("phrases", [])
    assert phrase in shipped, f"{phrase!r} is gone from {category}"


@pytest.mark.parametrize("slug,phrase", GREEK_PERSONA)
def test_the_persona_lexicon_still_ships_this_greek_entry(slug, phrase):
    lex = get_persona(slug).forbidden_lexicon_persona_specific
    assert lex is not None, f"{slug} lost its lexicon"
    assert phrase in lex.phrases, f"{phrase!r} is gone from {slug}"


# -- Detection, accented, inside a Greek sentence ------------------------------

@pytest.mark.parametrize("category,phrase", GREEK_UNIVERSAL)
def test_a_greek_universal_entry_is_detected_in_its_own_category(category, phrase):
    r = check_universal_forbidden(WRAPPER % phrase)
    assert r.passed is False, f"{phrase!r} did not trip the check"
    assert r.action == CheckAction.REGENERATE
    assert any(h.category == category and h.matched_text == phrase for h in r.hits), (
        f"{phrase!r} hit, but not in {category}: "
        f"{[(h.category, h.matched_text) for h in r.hits]}"
    )


@pytest.mark.parametrize("category,phrase", GREEK_UNIVERSAL)
def test_a_greek_universal_entry_is_actually_stripped(category, phrase):
    """Detection is half of it. #621 fixed the strip; this pins it on content."""
    reply = WRAPPER % phrase
    stripped = _deterministic_strip(reply, [check_universal_forbidden(reply)])
    assert normalize(phrase) not in normalize(stripped), (
        f"{phrase!r} survived the strip: {stripped!r}"
    )


@pytest.mark.parametrize("slug,phrase", GREEK_PERSONA)
def test_a_greek_persona_entry_is_detected_and_stripped(slug, phrase):
    persona = get_persona(slug)
    reply = WRAPPER % phrase
    r = check_persona_forbidden(reply, persona)
    assert r.passed is False, f"{slug}: {phrase!r} did not trip the check"
    assert any(h.matched_text == phrase for h in r.hits)
    stripped = _deterministic_strip(reply, [r])
    assert normalize(phrase) not in normalize(stripped), (
        f"{phrase!r} survived the strip: {stripped!r}"
    )


# -- The persona patterns ------------------------------------------------------

@pytest.mark.parametrize("slug,regex,hit_line,miss_line", PERSONA_PATTERNS)
def test_a_persona_pattern_catches_the_line_it_describes(
        slug, regex, hit_line, miss_line):
    r = check_persona_forbidden(hit_line, get_persona(slug))
    assert r.passed is False, f"{slug}: {hit_line!r} did not trip {regex!r}"
    assert any(h.pattern == regex for h in r.hits), (
        f"{hit_line!r} hit, but not via {regex!r}: {[h.pattern for h in r.hits]}"
    )


@pytest.mark.parametrize("slug,regex,hit_line,miss_line", PERSONA_PATTERNS)
def test_a_persona_pattern_leaves_the_neighbouring_line_alone(
        slug, regex, hit_line, miss_line):
    """The near-miss half. A pattern that catches both lines is too broad."""
    r = check_persona_forbidden(miss_line, get_persona(slug))
    assert r.passed is True, (
        f"{slug}: {miss_line!r} should be clean, hit "
        f"{[(h.matched_text, h.pattern) for h in r.hits]}"
    )


# -- What must NOT be caught --------------------------------------------------

@pytest.mark.parametrize("sentence,slug,why", INNOCENT_GREEK)
def test_an_innocent_greek_sentence_is_left_alone(sentence, slug, why):
    r = check_universal_forbidden(sentence)
    assert r.passed is True, (
        f"universal false positive ({why}): "
        f"{[(h.category, h.matched_text) for h in r.hits]}"
    )
    if slug is not None:
        rp = check_persona_forbidden(sentence, get_persona(slug))
        assert rp.passed is True, (
            f"{slug} false positive ({why}): "
            f"{[(h.matched_text, h.pattern) for h in rp.hits]}"
        )


# -- The migration is complete ------------------------------------------------

def test_every_persona_now_carries_a_lexicon():
    """Was 8 of 11. lao_tzu, niccolo_machiavelli and oscar_wilde were the gap,
    and they are also the three personas with no brain YAML, which is why they
    were left out when the other eight were written."""
    missing = [s for s, p in PERSONA_REGISTRY.items()
               if p.forbidden_lexicon_persona_specific is None]
    assert missing == [], f"personas still without a lexicon: {missing}"
    assert len(PERSONA_REGISTRY) == 11
