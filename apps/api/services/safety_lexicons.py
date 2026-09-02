"""Risk lexicons for the safety gates — English, Greek, and greeklish.

WHY THIS FILE EXISTS SEPARATELY. These lists are reviewable CONTENT, not logic.
A Greek speaker has to be able to read them line by line without reading a
matcher around them, and the matcher has to be readable without scrolling past
two hundred phrases. safety_service.py owns the mechanism; this owns the words.

THE ASYMMETRY THAT DECIDES EVERY CLOSE CALL. A false positive shows a caring,
plain-language message to somebody who was safe. A false negative leaves a
person in crisis talking to Nietzsche. Those are not comparable costs, so an
entry that is merely PROBABLY innocent still goes in. Spec §10.4: "A beautiful
persona response is worthless if it is unsafe."

THREE SCRIPTS, TWO NORMALISATION REGIMES.

  Greek-script entries are stored PRE-NORMALISED — casefolded, accents stripped,
  final sigma folded to sigma. `θέλω να πεθάνω` is stored `θελω να πεθανω`. The
  normaliser in safety_service applies the same transform to incoming text, so
  Θέλω / θέλω / θελω / ΘΕΛΩ all collide onto one stored form. An import-time
  assertion in safety_service fails the process if any entry here is not equal
  to its own normalised form, so a contributor who types accents cannot ship a
  silently dead entry.

  Greeklish entries are latin script and are their OWN lists. The normaliser
  does not transliterate — `pethano` and `πεθάνω` are unrelated strings to it —
  so greeklish cannot be folded into the Greek lists and must be enumerated.
  Greeks type Greek in latin characters constantly, and the target audience does
  it on phones by default, so this is not an edge case.

  Greeklish has no standard orthography. The same word appears as `thelo`,
  `thelw`, `8elo`, `8elw` — `8` and `9` for θ, `w` for ω, `y`/`u`/`i` for
  υ/η/ι. Common variants are enumerated rather than guessed at with a fuzzy
  matcher: a wrong fuzzy match on a safety gate is worse than a missing variant,
  because it is invisible.

SUBSTRING SAFETY. Matching is substring, exactly as the English lists have
always worked. That makes short latin entries dangerous: a bare `den` would fire
inside "sudden" and "garden". Every greeklish entry here is therefore either
multi-word or a distinctive single word with no common English superstring, and
tests/test_safety_greek.py scans this repository's own English prose (persona
system prompts, letter prompts) asserting ZERO hits from any Greek or greeklish
entry. That test is what keeps this list honest as it grows.
"""

# ── English ───────────────────────────────────────────────────────────────────
# Unchanged from the original safety_service definitions, moved here so all four
# bands of all three scripts sit side by side.

RISK_HIGH_EN = [
    "kill myself", "end my life", "ending my life", "suicide", "want to die",
    "take my life", "taking my life", "don't want to be alive", "wish i was dead",
    "self harm", "cutting myself", "hurt myself", "overdose",
    "not worth living", "better off dead", "can't keep living",
    "planning to end", "goodbye forever", "end it all", "ending it all",
    "no reason to live", "ready to die", "want it to be over",
]

RISK_MEDIUM_EN = [
    "can't go on", "no point anymore", "no point to anything", "hopeless",
    "disappear", "nothing matters", "can't take it anymore", "want to disappear",
    "everyone would be better without me", "so done with everything",
    "exhausted with living", "tired of existing", "don't see the point",
    "feel invisible", "world would be better without me",
]

OUTPUT_RISK_EN = [
    "lethal dose", "how to jump", "best method", "painless way",
    "painless method", "want to jump", "where to buy",
    "most effective way to", "easiest way to die", "least painful",
    "method would be", "way to end", "how to end your life",
]

# Promoted from an inline list inside check_input. It was the only one of the
# four bands not visible at module level, which made it the one nobody would
# think to mirror in another language — exactly the drift this move prevents.
LOW_SIGNALS_EN = [
    "tired", "exhausted", "burden", "alone", "no one cares", "failure",
    "worthless",
]


# ── Greek (pre-normalised: no accents, no final sigma, lowercase) ─────────────

RISK_HIGH_GR = [
    "θελω να πεθανω",              # I want to die
    "θελω να αυτοκτονησω",         # I want to kill myself
    "να αυτοκτονησω",              # to kill myself
    "σκεφτομαι να αυτοκτονησω",    # I'm thinking of killing myself
    "αυτοκτονια",                  # suicide
    "αυτοκτονω",                   # I kill myself
    "να δωσω τελοσ στη ζωη μου",   # to put an end to my life
    "δινω τελοσ στη ζωη μου",      # I am ending my life
    "τελειωνω τη ζωη μου",         # I am ending my life
    "να τελειωσω τη ζωη μου",      # to end my life
    "δεν θελω να ζω",              # I don't want to live
    "δε θελω να ζω",               # I don't want to live (short negation)
    "δεν αντεχω να ζω",            # I can't bear to live
    "δεν θελω να υπαρχω",          # I don't want to exist
    "μακαρι να πεθαινα",           # I wish I were dying/dead
    "μακαρι να μην υπηρχα",        # I wish I had never existed
    "καλυτερα νεκροσ",             # better off dead (m.)
    "καλυτερα νεκρη",              # better off dead (f.)
    "καλυτερα να πεθανω",          # better that I die
    "δεν αξιζει να ζω",            # not worth living
    "η ζωη μου δεν αξιζει",        # my life is not worth it
    "αυτοτραυματισμοσ",            # self-harm
    "χαραζομαι",                   # I cut myself (the common Greek term)
    "κοβω τον εαυτο μου",          # I cut myself
    "να βλαψω τον εαυτο μου",      # to harm myself
    "να κανω κακο στον εαυτο μου", # to do harm to myself
    "υπερβολικη δοση",             # overdose
    "ειμαι ετοιμοσ να πεθανω",     # I am ready to die (m.)
    "ειμαι ετοιμη να πεθανω",      # I am ready to die (f.)
    "θελω να τελειωσουν ολα",      # I want it all to be over
    "αντιο για παντα",             # goodbye forever
]

RISK_MEDIUM_GR = [
    "δεν αντεχω αλλο",             # I can't take it anymore
    "δε αντεχω αλλο",              # variant negation
    "δεν παει αλλο",               # it can't go on
    "δεν εχει νοημα",              # there's no point
    "τιποτα δεν εχει νοημα",       # nothing matters
    "δεν εχει νοημα τιποτα",       # nothing matters (inverted)
    "δεν βλεπω νοημα",             # I don't see the point
    "απελπισια",                   # despair
    "απελπισμενοσ",                # despairing (m.)
    "απελπισμενη",                 # despairing (f.)
    "θελω να εξαφανιστω",          # I want to disappear
    "να εξαφανιστω",               # to disappear
    "ολοι θα ηταν καλυτερα χωρισ εμενα",  # everyone would be better without me
    "θα ηταν καλυτερα χωρισ εμενα",       # would be better off without me
    "κουραστηκα να ζω",            # I'm tired of living
    "βαρεθηκα να ζω",              # I'm sick of living
    "δεν αντεχω τη ζωη μου",       # I can't stand my life
    "νιωθω αορατοσ",               # I feel invisible (m.)
    "νιωθω αορατη",                # I feel invisible (f.)
    "τα παρατησα ολα",             # I've given up on everything
]

OUTPUT_RISK_GR = [
    "θανατηφορα δοση",             # lethal dose
    "θανατηφορο χαπι",             # lethal pill
    "ανωδυνοσ τροποσ",             # painless way
    "ανωδυνη μεθοδοσ",             # painless method
    "πιο αποτελεσματικοσ τροποσ",  # most effective way
    "ευκολοτεροσ τροποσ να πεθανεισ",  # easiest way to die
    "λιγοτερο επωδυνοσ",           # least painful
    "τροποσ για να τελειωσει",     # a way for it to end
    "πωσ να τελειωσεισ τη ζωη σου",# how to end your life
    "πωσ να πηδηξεισ",             # how to jump
    "που να αγορασεισ",            # where to buy
]

LOW_SIGNALS_GR = [
    "κουρασμενοσ",                 # tired (m.)
    "κουρασμενη",                  # tired (f.)
    "εξαντλημενοσ",                # exhausted (m.)
    "εξαντλημενη",                 # exhausted (f.)
    "κανεισ δεν νοιαζεται",        # no one cares
    "νιωθω βαροσ",                 # I feel like a burden
    "ειμαι μονοσ",                 # I am alone (m.)
    "ειμαι μονη",                  # I am alone (f.)
    "αποτυχια",                    # failure
    "αναξιοσ",                     # worthless (m.)
    "αναξια",                      # worthless (f.)
]


# ── Greeklish (latin script; own lists, not transliterated at runtime) ────────
# Every entry is multi-word or a distinctive single word — see SUBSTRING SAFETY
# in the module docstring, and the English-corpus test that enforces it.

RISK_HIGH_GL = [
    "thelo na pethano", "thelw na pethanw", "thelo na pethanw",
    "8elo na pethano", "8elw na pe8anw", "thelo na pe8ano",
    "na autoktoniso", "na aftoktoniso", "na aytoktoniso",
    "aftoktonia", "autoktonia",
    "den thelo na zo", "den thelw na zw", "de thelo na zo",
    "den antexo na zo", "den antexw na zw",
    "na dwsw telos sti zoi mou", "na doso telos sti zoi mou",
    "teleiono ti zoi mou", "teleiwnw ti zwi mou",
    "kalytera nekros", "kalytera nekri",
    "makari na pethaina", "makari na pe8aina",
    "den axizei na zo", "den axizei na zw",
    "xarazomai", "aytotraymatismos", "aftotravmatismos",
    "na vlapso ton eafto mou", "na kano kako ston eafto mou",
    "yperboliki dosi", "iperboliki dosi",
    "antio gia panta",
]

RISK_MEDIUM_GL = [
    "den antexo allo", "den antexw allo", "de antexo allo",
    "den paei allo",
    "den exei noima", "tipota den exei noima", "den exei noima tipota",
    "den vlepo noima", "den vlepw noima",
    "apelpisia", "apelpismenos", "apelpismeni",
    "thelo na eksafanisto", "thelw na eksafanistw",
    "na eksafanisto", "na eksafanistw",
    "kourastika na zo", "kourastika na zw",
    "vare8ika na zo", "barethika na zo",
    "den antexo ti zoi mou", "den antexw ti zwi mou",
    "niotho aoratos", "niw8w aoratos",
]

OUTPUT_RISK_GL = [
    "thanatifora dosi", "anodynos tropos", "anwdynos tropos",
    "anodyni methodos", "pio apotelesmatikos tropos",
    "eukoloteros tropos na pethaneis", "ligotero epodynos",
    "tropos gia na teleiosei", "pos na teleioseis ti zoi sou",
]

LOW_SIGNALS_GL = [
    "kourasmenos", "kourasmeni", "eksantlimenos", "eksantlimeni",
    "kaneis den noiazetai", "niotho baros", "niw8w baros",
    "eimai monos", "eimai moni", "apotyxia", "anaksios", "anaksia",
]


# ── Assembled bands ───────────────────────────────────────────────────────────
# The matcher walks these. Order within a band does not matter: the first hit
# wins and every entry in a band produces the same level.

RISK_HIGH = RISK_HIGH_EN + RISK_HIGH_GR + RISK_HIGH_GL
RISK_MEDIUM = RISK_MEDIUM_EN + RISK_MEDIUM_GR + RISK_MEDIUM_GL
OUTPUT_RISK_PHRASES = OUTPUT_RISK_EN + OUTPUT_RISK_GR + OUTPUT_RISK_GL
LOW_SIGNALS = LOW_SIGNALS_EN + LOW_SIGNALS_GR + LOW_SIGNALS_GL

# Greek-script bands, kept addressable for the import-time normalisation
# assertion and for the tests that need to iterate one script at a time.
GREEK_BANDS = {
    "RISK_HIGH_GR": RISK_HIGH_GR,
    "RISK_MEDIUM_GR": RISK_MEDIUM_GR,
    "OUTPUT_RISK_GR": OUTPUT_RISK_GR,
    "LOW_SIGNALS_GR": LOW_SIGNALS_GR,
}

GREEKLISH_BANDS = {
    "RISK_HIGH_GL": RISK_HIGH_GL,
    "RISK_MEDIUM_GL": RISK_MEDIUM_GL,
    "OUTPUT_RISK_GL": OUTPUT_RISK_GL,
    "LOW_SIGNALS_GL": LOW_SIGNALS_GL,
}

ALL_BANDS = {
    "RISK_HIGH": RISK_HIGH,
    "RISK_MEDIUM": RISK_MEDIUM,
    "OUTPUT_RISK_PHRASES": OUTPUT_RISK_PHRASES,
    "LOW_SIGNALS": LOW_SIGNALS,
}
