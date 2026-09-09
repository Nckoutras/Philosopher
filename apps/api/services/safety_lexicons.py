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

SHORT FORMS SUBSUME LONG ONES — DO NOT RE-ADD THE LONG ONE. Matching is substring
and the first hit wins, so an entry that CONTAINS an existing entry can never
fire: `να αυτοκτονησω` already matches inside `παω να αυτοκτονησω`, and adding the
longer phrase adds a line that is unreachable by construction. In a list whose
whole value is that a reviewer can read it and know what is covered, a dead line
is a false claim about coverage. Before adding a phrase, check whether a shorter
entry already matches inside it.

NATIVE REVIEW — 2026-09-09. First pass by ChatGPT, arbitration by the founder;
the first time these lists were read by a Greek speaker rather than only tested.
Two facts about the MECHANISM drove most of the changes, and they are why several
phrases moved DOWN a band rather than being deleted:

  * MEDIUM suppresses the persona exactly as HIGH does
    (`SafetyResult.should_suppress_persona` is
    `level in ("medium", "high", "critical")`). A MEDIUM false positive therefore
    replaces the philosopher with crisis copy. `δεν εχει νοημα` — "there's no
    point" — is a routine sentence in a philosophy app, and it was MEDIUM. It and
    its kin are now LOW, which logs the signal and keeps the persona.
  * An OUTPUT hit replaces the WHOLE persona response, so a generic OUTPUT phrase
    erases innocent answers: `πιο αποτελεσματικοσ τροποσ` — "the most effective
    way" — would have deleted a reply about how to talk to your father. Generic
    method-SHAPED phrases are removed; the explicitly lethal ones stay.

Nothing left HIGH except `αντιο για παντα`, which is as often a breakup as a
goodbye. The deliberately over-triggering `αυτοκτονια` and `αυτοκτονω` are KEPT,
under the asymmetry above.
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
    "θα αυτοκτονησω",              # I will kill myself         (added 2026-09-09)
    "να αυτοκτονησω",              # to kill myself
    "σκεφτομαι να αυτοκτονησω",    # I'm thinking of killing myself
    "αυτοκτονια",                  # suicide
    "αυτοκτονω",                   # I kill myself
    "να δωσω τελοσ στη ζωη μου",   # to put an end to my life
    "δινω τελοσ στη ζωη μου",      # I am ending my life
    "τελειωνω τη ζωη μου",         # I am ending my life
    "να τελειωσω τη ζωη μου",      # to end my life
    "θα τελειωσω τη ζωη μου",      # I will end my life         (added 2026-09-09)
    "βαζω τελοσ στη ζωη μου",      # I am putting an end to my life  (added)
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
    "κοβομαι",                     # I cut myself (the other common term)
    "χαραζω τα χερια μου",         # I cut my arms              (added 2026-09-09)
    "κοβω τον εαυτο μου",          # I cut myself
    "να βλαψω τον εαυτο μου",      # to harm myself
    "να κανω κακο στον εαυτο μου", # to do harm to myself
    "υπερβολικη δοση",             # overdose
    "ειμαι ετοιμοσ να πεθανω",     # I am ready to die (m.)
    "ειμαι ετοιμη να πεθανω",      # I am ready to die (f.)
    "θελω να τελειωσουν ολα",      # I want it all to be over
    # "αντιο για παντα" moved to LOW_SIGNALS_GR 2026-09-09 — as often a breakup.
]

RISK_MEDIUM_GR = [
    "δεν αντεχω αλλο",             # I can't take it anymore
    "δε αντεχω αλλο",              # variant negation
    "δεν παει αλλο",               # it can't go on
    # Moved to LOW 2026-09-09: "δεν εχει νοημα", "δεν βλεπω νοημα", "απελπισια"
    # and its gendered forms. The two TIPOTA forms below STAY: "nothing matters"
    # is not generic meaning-talk. MEDIUM is scanned before LOW, so they still
    # win on text that contains both.
    "τιποτα δεν εχει νοημα",       # nothing matters
    "δεν εχει νοημα τιποτα",       # nothing matters (inverted)
    "θελω να εξαφανιστω",          # I want to disappear
    "να εξαφανιστω",               # to disappear
    "ολοι θα ηταν καλυτερα χωρισ εμενα",  # everyone would be better without me
    "θα ηταν καλυτερα χωρισ εμενα",       # would be better off without me
    "κουραστηκα να ζω",            # I'm tired of living
    "βαρεθηκα να ζω",              # I'm sick of living
    "δεν αντεχω τη ζωη μου",       # I can't stand my life
    "νιωθω αορατοσ",               # I feel invisible (m.)
    "νιωθω αορατη",                # I feel invisible (f.)
    # "τα παρατησα ολα" moved to LOW_SIGNALS_GR 2026-09-09.
]

OUTPUT_RISK_GR = [
    "θανατηφορα δοση",             # lethal dose
    "θανατηφορο χαπι",             # lethal pill
    "ευκολοτεροσ τροποσ να πεθανεισ",  # easiest way to die
    "πωσ να τελειωσεισ τη ζωη σου",# how to end your life
    "πωσ να αυτοκτονησεισ",        # how to kill yourself       (added 2026-09-09)
    # REMOVED 2026-09-09 (native review): ανωδυνοσ τροποσ · ανωδυνη μεθοδοσ ·
    # πιο αποτελεσματικοσ τροποσ · λιγοτερο επωδυνοσ · τροποσ για να τελειωσει ·
    # πωσ να πηδηξεισ · που να αγορασεισ. Each is method-SHAPED but not lethal
    # on its own, and an OUTPUT hit replaces the ENTIRE persona response.
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
    # Moved down 2026-09-09 (native review). Real distress signals, but routine
    # enough in a philosophy app that suppressing the persona costs more than it
    # protects. LOW logs the signal and keeps the voice.
    "δεν εχει νοημα",              # there's no point            (was MEDIUM)
    "δεν βλεπω νοημα",             # I don't see the point       (was MEDIUM)
    "απελπισια",                   # despair                     (was MEDIUM)
    "απελπισμενοσ",                # despairing (m.)             (was MEDIUM)
    "απελπισμενη",                 # despairing (f.)             (was MEDIUM)
    "τα παρατησα ολα",             # I gave up on everything     (was MEDIUM)
    "αντιο για παντα",             # goodbye forever             (was HIGH)
    # New this review.
    "ειμαι αχρηστοσ",              # I am useless (m.)
    "ειμαι αχρηστη",               # I am useless (f.)
    "δεν αξιζω τιποτα",            # I am worth nothing
    "νιωθω οτι ειμαι βαροσ",       # I feel that I am a burden
]


# ── Greeklish (latin script; own lists, not transliterated at runtime) ────────
# Every entry is multi-word or a distinctive single word — see SUBSTRING SAFETY
# in the module docstring, and the English-corpus test that enforces it.

RISK_HIGH_GL = [
    "thelo na pethano", "thelw na pethanw", "thelo na pethanw",
    "8elo na pethano", "8elw na pe8anw", "thelo na pe8ano",
    "na autoktoniso", "na aftoktoniso", "na aytoktoniso",
    "tha autoktoniso", "tha aftoktoniso",           # added 2026-09-09
    "aftoktonia", "autoktonia",
    "den thelo na zo", "den thelw na zw", "de thelo na zo",
    "den antexo na zo", "den antexw na zw",
    "na dwsw telos sti zoi mou", "na doso telos sti zoi mou",
    "teleiono ti zoi mou", "teleiwnw ti zwi mou",
    "tha teleioso ti zoi mou", "vazo telos sti zoi mou",   # added 2026-09-09
    "kalytera nekros", "kalytera nekri",
    "makari na pethaina", "makari na pe8aina",
    "den axizei na zo", "den axizei na zw",
    "xarazomai", "aytotraymatismos", "aftotravmatismos",
    "na vlapso ton eafto mou", "na kano kako ston eafto mou",
    "yperboliki dosi", "iperboliki dosi",
    # "antio gia panta" moved to LOW_SIGNALS_GL 2026-09-09.
]

RISK_MEDIUM_GL = [
    "den antexo allo", "den antexw allo", "de antexo allo",
    "den paei allo",
    # Moved to LOW 2026-09-09: "den exei noima", "den vlepo noima",
    # "den vlepw noima", "apelpisia", "apelpismenos", "apelpismeni".
    # The TIPOTA forms stay — see the Greek band above for why.
    "tipota den exei noima", "den exei noima tipota",
    "thelo na eksafanisto", "thelw na eksafanistw",
    "na eksafanisto", "na eksafanistw",
    "kourastika na zo", "kourastika na zw",
    "vare8ika na zo", "barethika na zo",
    "den antexo ti zoi mou", "den antexw ti zwi mou",
    "niotho aoratos", "niw8w aoratos",
    "niotho aorati", "niw8w aorati",                # f. forms, added 2026-09-09
    "tha itan kalytera xoris emena",                # added 2026-09-09; the short
                                                    # form also covers "oloi tha…"
]

OUTPUT_RISK_GL = [
    "thanatifora dosi",
    "eukoloteros tropos na pethaneis", "pos na teleioseis ti zoi sou",
    "pos na autoktoniseis",                         # added 2026-09-09
    # REMOVED 2026-09-09: anodynos tropos · anwdynos tropos · anodyni methodos ·
    # pio apotelesmatikos tropos · ligotero epodynos · tropos gia na teleiosei.
]

LOW_SIGNALS_GL = [
    "kourasmenos", "kourasmeni", "eksantlimenos", "eksantlimeni",
    "kaneis den noiazetai", "niotho baros", "niw8w baros",
    "eimai monos", "eimai moni", "apotyxia", "anaksios", "anaksia",
    # Moved down 2026-09-09 — see LOW_SIGNALS_GR for the reasoning.
    "den exei noima", "den vlepo noima", "den vlepw noima",
    "apelpisia", "apelpismenos", "apelpismeni",
    "antio gia panta",
    # New this review.
    "eimai axristos", "eimai axristi", "den axizo tipota",
    "niotho oti eimai baros",
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
