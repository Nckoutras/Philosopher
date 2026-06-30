// ─────────────────────────────────────────────────────────────────────────────────────
// Self-Portrait "The Room notices" observation pools (Phase A).
//
// One short, calm observation is shown AFTER a user answers a question — a remark
// about HOW they answered, never a count, score, streak, or word of praise.
//
// KEY = (category × pill-index). Both are known on the client at tap time:
//   • `category` ships in the public question shape (SelfPortraitQuestion.category)
//   • `pillIndex` is the index of the chosen pill (0–3)
// so this whole mechanism is frontend-only — no API field, no migration.
//
// There are 12 categories × 4 pill-indices = 48 "cells". Each cell holds a POOL of
// lines. The displayed line is picked deterministically from the pool by
// `fnv1a(questionId) % pool.length`, so:
//   • the SAME question always yields the SAME line (stable on reopen / revisit), and
//   • two DIFFERENT questions in the same cell get DIFFERENT lines (no collision,
//     never the same line twice running).
//
// The pill INDEX loosely tracks a stance archetype in the question bank
// (0 ≈ lean-in / engage · 1 ≈ withdraw / contrast · 2 ≈ defer / negotiate ·
// 3 ≈ friction / ambivalence). It is a SOFT convention, not a hard contract, so the
// lines fit the category + that rough stance, not a precise verb.
//
// AUTHORED CONTENT — this is the final hand-authored set (the_wise_room_micro_
// observations.json): 12 categories × 4 pill-arrays × 8 lines = 384 observations.
// To revise, replace the matching strings in OBSERVATIONS; the shape (4 arrays per
// category, non-empty pools) must hold. Type aliases, OBSERVATION_CATEGORIES,
// fnv1a(), and observationFor() below are the mechanism — leave them untouched.
// ─────────────────────────────────────────────────────────────────────────────────────

/** A category's four pools, ordered by pill index 0→3. */
export type CategoryObservations = readonly [
  readonly string[],
  readonly string[],
  readonly string[],
  readonly string[],
]

/** category slug → its four (pill-index) pools. */
export type ObservationPools = Readonly<Record<string, CategoryObservations>>

// The 12 bank categories. Kept here as the canonical client-side list so a missing
// key is obvious. (Mirrors the API's question_bank categories.)
export const OBSERVATION_CATEGORIES = [
  'conflict',
  'desire',
  'family',
  'fear',
  'friendship',
  'identity',
  'meaning',
  'money',
  'mortality',
  'relationships',
  'solitude',
  'work_and_ambition',
] as const

export const OBSERVATIONS: ObservationPools = {
  conflict: [
    [
      "You tend to meet friction before it hardens. You prefer clarity while the room is still warm.",
      "You lean toward saying the thing early, before silence begins to edit it for you.",
      "You would rather face the difficult edge than keep walking around it politely.",
      "You tend to trust honest tension more than a peace that depends on pretending.",
      "You move toward conflict when it feels like truth is being left unattended.",
      "You prefer the clean discomfort of naming something to the slow ache of avoidance.",
      "You tend to believe a direct conversation can spare everyone a longer confusion.",
      "You lean toward repair through contact, not distance. The door matters more open than elegant.",
    ],
    [
      "You tend to step back when tension enters. You prefer distance before words become careless.",
      "You would rather let heat settle than add your voice to a room already too loud.",
      "You lean toward restraint, especially when speaking might make the shape of things worse.",
      "You tend to protect quiet when conflict starts asking for performance.",
      "You prefer not to meet every spark as if it were a fire worth tending.",
      "You lean away from confrontation when it seems more hungry than useful.",
      "You tend to choose silence when the exchange feels unlikely to hold anything gently.",
      "You would rather leave some things untouched than force honesty through a narrow door.",
    ],
    [
      "You tend to weigh peace against truth, trying not to let either claim the whole table.",
      "You lean toward careful timing. Not every truth, for you, arrives ready to be spoken.",
      "You prefer to test the ground before placing the full weight of your position there.",
      "You tend to look for the narrow path where honesty can enter without breaking everything.",
      "You would rather negotiate the shape of a conflict than surrender to its first demand.",
      "You lean toward partial disclosure when the whole truth feels too sharp for the moment.",
      "You tend to hold back one sentence until you know what it might cost.",
      "You prefer measured contact, keeping enough distance to think and enough closeness to care.",
    ],
    [
      "You tend to feel conflict as a room with no easy exit. Even silence can feel involved.",
      "You lean toward resentment when too much has been left unnamed for too long.",
      "You may resist the argument and still carry it with you after everyone has gone quiet.",
      "You tend to feel trapped between speaking and swallowing the cost of not speaking.",
      "You lean into the tension unwillingly, as if the matter has already taken too much space.",
      "You tend to distrust easy peace when your own discomfort has not been given a place.",
      "You may hold your ground with one hand and search for the door with the other.",
      "You tend to feel the weight of what was avoided as much as what was said.",
    ],
  ],
  desire: [
    [
      "You tend to meet desire more honestly once it is named. You prefer truth over concealment.",
      "You lean toward wanting without excessive apology, even when composure has to loosen.",
      "You tend to trust the pull of longing when it arrives with a clear enough face.",
      "You would rather acknowledge appetite than dress it as something more acceptable.",
      "You lean toward moving closer to what calls you, before caution makes it abstract.",
      "You tend to let desire speak plainly when it has waited long enough in the corner.",
      "You prefer the risk of wanting to the smaller safety of denying the want.",
      "You tend to give longing a chair at the table, not the whole house.",
    ],
    [
      "You tend to step away from wanting when it feels likely to make you less steady.",
      "You lean toward refusal when desire begins to sound too expensive for the soul.",
      "You would rather keep your hands clean than chase something that may leave a mark.",
      "You tend to distrust longing when it arrives dressed as urgency.",
      "You prefer distance from desire when it seems to bargain with your better judgment.",
      "You lean away from what pulls too strongly, especially when it asks for surrender.",
      "You tend to protect yourself from wanting by giving silence a practical name.",
      "You would rather lose a possible sweetness than be ruled by a hunger you do not respect.",
    ],
    [
      "You tend to negotiate with desire, allowing it a voice but not the final signature.",
      "You lean toward wanting carefully, measuring the pull against what it might disturb.",
      "You prefer to keep longing near enough to understand, far enough to govern.",
      "You tend to make room for desire only after it has survived your questioning.",
      "You would rather approach wanting through small permissions than grand declarations.",
      "You lean toward compromise, letting desire breathe without letting it rearrange everything.",
      "You tend to test whether a longing is true or simply loud.",
      "You prefer a slower yes, one that has passed through both appetite and restraint.",
    ],
    [
      "You tend to feel desire as both invitation and disturbance. Wanting rarely arrives empty-handed.",
      "You lean toward ambivalence when longing asks for more freedom than you feel able to give.",
      "You may want the door open and resent how much wind comes through it.",
      "You tend to feel caught between hunger and the life built to contain it.",
      "You lean toward irritation when desire exposes what has been patiently managed.",
      "You may carry a want like a secret argument with your own composure.",
      "You tend to distrust desire most when it reveals how much you still care.",
      "You may feel longing less as permission than as pressure wearing a beautiful coat.",
    ],
  ],
  family: [
    [
      "You tend to move toward family bonds, even when they ask for patience you did not plan.",
      "You lean toward connection where history still has a voice in the room.",
      "You would rather keep the thread alive than let distance make the story simpler.",
      "You tend to treat family as something to face, not simply something to inherit.",
      "You lean toward staying present where old ties still carry unfinished meaning.",
      "You prefer engagement with family, even when closeness arrives with complicated weather.",
      "You tend to believe some bonds deserve attention before they become only memory.",
      "You move toward the shared table, aware that love often brings its own noise.",
    ],
    [
      "You tend to step back when family closeness begins to blur the edges of yourself.",
      "You lean toward distance when old roles start speaking louder than the present person.",
      "You would rather protect your quiet than keep proving yourself inside familiar rooms.",
      "You tend to resist family claims when they arrive as obligation rather than care.",
      "You prefer not to confuse loyalty with constant availability.",
      "You lean away from inherited expectations when they feel too eager to name you.",
      "You tend to guard your inner space when family history asks to enter uninvited.",
      "You would rather disappoint a pattern than disappear inside it politely.",
    ],
    [
      "You tend to negotiate family closeness, giving some access while keeping certain rooms private.",
      "You lean toward measured loyalty, neither abandoning the bond nor handing it everything.",
      "You prefer to stay connected in ways that still leave room for your own weather.",
      "You tend to balance affection with boundaries, even when both feel unfinished.",
      "You would rather offer what is real than perform what family scripts expect.",
      "You lean toward partial presence when full closeness feels too costly.",
      "You tend to keep one hand on the thread and one hand on the door.",
      "You prefer a bond with breathing space to a closeness that forgets where you end.",
    ],
    [
      "You tend to feel family as both shelter and pressure, a house with beautiful difficult rooms.",
      "You lean toward resentment when care arrives tangled with expectation.",
      "You may feel claimed by family even when you are trying to stand apart.",
      "You tend to carry old roles like coats someone else keeps handing back.",
      "You may want closeness and still resist the price it seems to ask.",
      "You lean toward frustration when love is used as a reason not to change.",
      "You tend to feel trapped when family history speaks as if the future were already decided.",
      "You may hold affection and exhaustion in the same hand, neither fully canceling the other.",
    ],
  ],
  fear: [
    [
      "You tend to move toward fear when it blocks the path. You prefer seeing its shape clearly.",
      "You lean toward facing what unsettles you before imagination makes it larger.",
      "You would rather meet the shadow directly than let it rule from the edge of the room.",
      "You tend to treat fear as information, not a command.",
      "You lean into uncertainty when avoidance begins to feel more costly than contact.",
      "You prefer the honest tremor of approach to the long suspense of retreat.",
      "You tend to stand near what frightens you until it becomes more specific.",
      "You move toward fear with a wish to know whether it is warning, memory, or weather.",
    ],
    [
      "You tend to step back from fear when it asks for more than the moment can hold.",
      "You lean toward protection before explanation. Distance comes before interpretation.",
      "You would rather keep away from what unsettles you than pretend it has no teeth.",
      "You tend to respect fear enough not to rush past it.",
      "You prefer not to make bravery a performance when caution feels more truthful.",
      "You lean away from the edge when the view costs too much steadiness.",
      "You tend to give fear space, especially when closeness would only make it louder.",
      "You would rather preserve your footing than test every frightening door.",
    ],
    [
      "You tend to bargain with fear, listening without letting it take the whole sentence.",
      "You lean toward cautious movement, one step close and one step held in reserve.",
      "You prefer to understand the danger before deciding how much of yourself to bring.",
      "You tend to test fear slowly, as if crossing a room in low light.",
      "You would rather make fear precise than either obey it or dismiss it entirely.",
      "You lean toward measured exposure, close enough to learn and far enough to breathe.",
      "You tend to let caution and curiosity argue quietly before you move.",
      "You prefer a negotiated courage, one that keeps its eyes open.",
    ],
    [
      "You tend to feel fear as both signal and weight. It can warn you and hold you still.",
      "You lean toward ambivalence when fear makes safety feel both necessary and limiting.",
      "You may resent how much space fear takes, even when part of you trusts it.",
      "You tend to feel caught between the wish to move and the need to remain intact.",
      "You may carry fear like an unpaid debt, present even when no one mentions it.",
      "You lean toward frustration when caution becomes a room rather than a tool.",
      "You tend to feel fear most sharply when it begins choosing on your behalf.",
      "You may resist fear and still find yourself arranging life around its furniture.",
    ],
  ],
  friendship: [
    [
      "You tend to move toward friendship with openness, letting warmth arrive before perfect certainty.",
      "You lean toward showing up when the bond asks for presence, not theory.",
      "You would rather risk closeness than keep affection safely under glass.",
      "You tend to give friendship a generous first reading.",
      "You lean into shared life when it feels honest, even if it remains imperfect.",
      "You prefer friendships that can hold unpolished truth without making it dramatic.",
      "You tend to value the person who stays in the room after the cleverness ends.",
      "You move toward friends when the bond feels alive enough to deserve tending.",
    ],
    [
      "You tend to step back when friendship begins to demand more access than feels true.",
      "You lean toward selectiveness, keeping the circle small enough to mean something.",
      "You would rather have fewer bonds than maintain a crowded room of obligations.",
      "You tend to resist friendships that trade closeness for constant performance.",
      "You prefer distance when warmth begins to feel managed or expected.",
      "You lean away from easy intimacy when it arrives faster than trust.",
      "You tend to protect your solitude from friendships that confuse availability with care.",
      "You would rather let a bond thin than keep feeding what no longer feels mutual.",
    ],
    [
      "You tend to negotiate friendship through rhythm, closeness at times and space at others.",
      "You lean toward bonds that can breathe without requiring constant proof.",
      "You prefer to give what you can honestly sustain, not what the moment pressures you to offer.",
      "You tend to keep friendship warm without letting it consume your private weather.",
      "You would rather adjust the distance than abandon the bond entirely.",
      "You lean toward measured intimacy, letting trust gather slowly rather than declare itself.",
      "You tend to answer friendship with care, but not always with full access.",
      "You prefer bonds that survive pauses without turning them into accusations.",
    ],
    [
      "You tend to feel friendship as a tender place where imbalance becomes hard to ignore.",
      "You lean toward frustration when closeness begins to feel like quiet accounting.",
      "You may want the bond and resent the effort required to keep it alive.",
      "You tend to notice when friendship asks for more than it returns.",
      "You may feel trapped between loyalty and the wish to be less available.",
      "You lean toward ambivalence when affection and fatigue sit too close together.",
      "You tend to carry small disappointments until they begin to form a weather system.",
      "You may remain present while part of you has already stepped slightly back.",
    ],
  ],
  identity: [
    [
      "You tend to move toward a clearer sense of yourself when the question becomes direct.",
      "You lean toward owning the shape you have become, even where it still changes.",
      "You would rather name yourself honestly than remain agreeable and blurred.",
      "You tend to meet identity as something lived, not merely explained.",
      "You lean into the parts of yourself that have waited too long for language.",
      "You prefer a self that can be seen without being overdecorated.",
      "You tend to trust the quiet fact of who you are becoming.",
      "You move toward self-recognition when disguise begins to feel heavier than exposure.",
    ],
    [
      "You tend to resist being too quickly defined, even by words that sound flattering.",
      "You lean away from fixed identity when it starts to feel like a smaller room.",
      "You would rather remain partly unnamed than be placed neatly on someone else's shelf.",
      "You tend to distrust labels that arrive before the full person has spoken.",
      "You prefer the freedom of uncertainty to a definition that closes too fast.",
      "You lean away from identities that feel inherited, borrowed, or overly tidy.",
      "You tend to keep part of yourself beyond easy description.",
      "You would rather be difficult to summarize than easy to misunderstand.",
    ],
    [
      "You tend to negotiate identity, holding several versions without forcing them into one portrait.",
      "You lean toward a self that changes shape without losing its deeper thread.",
      "You prefer to define yourself in pencil where life still moves.",
      "You tend to balance belonging with the need to remain privately unclaimed.",
      "You would rather revise the self than defend an outdated costume.",
      "You lean toward partial certainty, enough to stand and not enough to become rigid.",
      "You tend to let identity gather slowly from choices, not declarations alone.",
      "You prefer a self with room for contradiction over a story that is too polished.",
    ],
    [
      "You tend to feel identity as both anchor and argument, something claimed and contested.",
      "You lean toward ambivalence when the self you show does not match the self you sense.",
      "You may feel trapped by versions of you that other people still recognize.",
      "You tend to resent definitions that once protected you but now feel too tight.",
      "You may carry yourself as a question that others keep trying to answer.",
      "You lean toward friction when belonging seems to require a smaller version of you.",
      "You tend to feel the strain between being known and being simplified.",
      "You may want recognition and still distrust the frame it arrives in.",
    ],
  ],
  meaning: [
    [
      "You tend to move toward meaning when life asks for more than function.",
      "You lean toward finding the deeper thread beneath ordinary choices.",
      "You would rather live with purpose in view than drift only by convenience.",
      "You tend to notice where the day wants to become part of a larger sentence.",
      "You lean into meaning when the surface answer feels too thin.",
      "You prefer a life that can explain itself beyond schedules and outcomes.",
      "You tend to search for the quiet reason behind the visible motion.",
      "You move toward the question of why before the machinery of how takes over.",
    ],
    [
      "You tend to step back from grand meaning when it begins to sound too decorated.",
      "You lean toward the concrete, trusting what can be held more than what can be declared.",
      "You would rather keep life honest than dress it in borrowed significance.",
      "You tend to resist meaning when it arrives as a slogan instead of a felt truth.",
      "You prefer plain reality to a noble story that does not quite fit.",
      "You lean away from explanations that make life sound tidier than it is.",
      "You tend to trust the small fact over the large pronouncement.",
      "You would rather let meaning remain quiet than force it to speak beautifully.",
    ],
    [
      "You tend to negotiate meaning between the ordinary day and the larger question underneath.",
      "You lean toward purpose that can survive contact with practical life.",
      "You prefer meanings that are lived in fragments rather than announced as monuments.",
      "You tend to let significance gather slowly from repeated choices.",
      "You would rather keep meaning flexible enough to change with the person carrying it.",
      "You lean toward a quiet why, not one that needs constant ceremony.",
      "You tend to balance usefulness with depth, as if both deserve a seat.",
      "You prefer a purpose that breathes, not one that demands obedience.",
    ],
    [
      "You tend to feel meaning most sharply when it seems absent, thin, or too far away.",
      "You lean toward restlessness when the visible life fails to answer the hidden question.",
      "You may resent how ordinary days can cover the larger hunger beneath them.",
      "You tend to feel caught between wanting purpose and distrusting easy versions of it.",
      "You may carry a quiet argument with the life that appears to be working.",
      "You lean toward ambivalence when meaning feels necessary and unreachable at once.",
      "You tend to feel trapped by routines that do not explain why they matter.",
      "You may sense the deeper question even when the day gives you no proper place for it.",
    ],
  ],
  money: [
    [
      "You tend to meet money as something to handle directly, not whisper around.",
      "You lean toward engagement where value, security, and choice are openly on the table.",
      "You would rather look at the numbers than be ruled by their shadow.",
      "You tend to treat money as a practical language with emotional weather underneath.",
      "You lean into financial questions when avoidance begins to cost more than clarity.",
      "You prefer naming material needs without pretending they are less human than other needs.",
      "You tend to see money as a tool that deserves attention, not worship.",
      "You move toward decisions when the facts are visible enough to stand on.",
    ],
    [
      "You tend to step back when money begins to occupy too much of the inner room.",
      "You lean away from choices that make value sound only financial.",
      "You would rather protect meaning than chase a number that keeps changing its appetite.",
      "You tend to resist money when it starts speaking louder than judgment.",
      "You prefer distance from financial pressure when it begins to flatten other forms of wealth.",
      "You lean away from transactions that ask you to forget the person behind them.",
      "You tend to distrust money when it arrives with a claim on your dignity.",
      "You would rather have less leverage than let money write the whole story.",
    ],
    [
      "You tend to negotiate money carefully, balancing security with the life it is meant to serve.",
      "You lean toward measured choices where practical needs and personal values can both breathe.",
      "You prefer money decisions that leave room for both caution and appetite.",
      "You tend to weigh the visible cost against the quieter cost of saying no.",
      "You would rather make financial choices in daylight, with neither panic nor romance.",
      "You lean toward enoughness, while still listening to ambition when it knocks.",
      "You tend to balance keeping and spending as two different forms of care.",
      "You prefer value that can be counted, but not only counted.",
    ],
    [
      "You tend to feel money as both protection and pressure, a shield that can become a wall.",
      "You lean toward resentment when financial choices start feeling less like choices.",
      "You may feel caught between wanting freedom and managing the cost of it.",
      "You tend to carry money worries beyond the moment where the calculation ends.",
      "You may resent how easily numbers enter rooms where trust should have stood.",
      "You lean toward ambivalence when security asks for more sacrifice than expected.",
      "You tend to feel trapped when money becomes the reason every road narrows.",
      "You may want ease around money and still hear the old arithmetic underneath.",
    ],
  ],
  mortality: [
    [
      "You tend to move toward mortality as a fact worth facing, not a door to avoid.",
      "You lean toward looking directly at finitude when it clarifies what deserves your hours.",
      "You would rather let mortality sharpen life than leave it waiting in the dark.",
      "You tend to meet endings with a wish to understand what they reveal.",
      "You lean into the briefness of life when it makes the present less abstract.",
      "You prefer honest contact with limits over a comfort built from not looking.",
      "You tend to let the thought of ending make choices more serious, not smaller.",
      "You move toward the hard fact because it can return the day to its proper size.",
    ],
    [
      "You tend to step back from mortality when its presence makes the room too narrow.",
      "You lean toward ordinary life when final questions begin to darken the walls.",
      "You would rather keep endings at a distance than let them interrupt every hour.",
      "You tend to protect the day from thoughts that arrive too heavily dressed.",
      "You prefer not to give mortality more authority than the living moment requires.",
      "You lean away from finality when it turns reflection into shadow.",
      "You tend to trust life more when it is not constantly measured against its ending.",
      "You would rather let the limit remain quiet unless it truly needs to speak.",
    ],
    [
      "You tend to negotiate mortality, allowing it near enough to matter but not enough to govern.",
      "You lean toward remembering the limit without letting it steal the whole light.",
      "You prefer to let finitude guide gently, not stand over every decision.",
      "You tend to hold endings in view while still making room for ordinary pleasures.",
      "You would rather make peace with mortality in portions than all at once.",
      "You lean toward a practical tenderness with time, aware it is both common and rare.",
      "You tend to balance seriousness with the small mercy of forgetting.",
      "You prefer to honor the limit without building your whole house around it.",
    ],
    [
      "You tend to feel mortality as both clarifying and unbearable, a truth that does not soften easily.",
      "You lean toward ambivalence when endings make life feel precious and fragile at once.",
      "You may resent the limit even as it gives weight to what you love.",
      "You tend to feel trapped between accepting time and wanting more of it.",
      "You may carry finality like a quiet pressure behind ordinary decisions.",
      "You lean toward friction when the facts of life refuse negotiation.",
      "You tend to feel the ending most when something living asks to be held longer.",
      "You may want peace with mortality and still find yourself arguing with the clock.",
    ],
  ],
  relationships: [
    [
      "You tend to move toward closeness when the bond feels worth the exposure.",
      "You lean into connection where honesty can sit beside tenderness without disguise.",
      "You would rather risk being seen than remain perfectly protected and partly absent.",
      "You tend to meet intimacy as a living conversation, not a solved arrangement.",
      "You lean toward staying present when love asks for more truth than comfort.",
      "You prefer bonds where affection has a voice and silence is not the whole method.",
      "You tend to give closeness a real chance before retreating into explanation.",
      "You move toward the other when distance starts to feel less safe than lonely.",
    ],
    [
      "You tend to step back when closeness begins to ask for more of you than feels fair.",
      "You lean toward self-protection when intimacy starts blurring your inner borders.",
      "You would rather keep your footing than be absorbed by the weather of another person.",
      "You tend to resist bonds that make love sound like constant surrender.",
      "You prefer distance when closeness arrives with too many unspoken conditions.",
      "You lean away from intimacy that feels hungry for proof.",
      "You tend to protect private ground when relationship begins to feel like occupation.",
      "You would rather be alone with yourself than accompanied by someone who misplaces you.",
    ],
    [
      "You tend to negotiate closeness, letting love come near without handing it the whole map.",
      "You lean toward bonds that can hold both affection and breathing space.",
      "You prefer intimacy with clear edges, where two people remain two people.",
      "You tend to offer care in ways that do not require self-erasure.",
      "You would rather adjust the distance than call the whole bond false.",
      "You lean toward a measured yes, one that still remembers your own room.",
      "You tend to balance tenderness with caution, listening to both.",
      "You prefer a relationship that can survive honest pauses and uneven weather.",
    ],
    [
      "You tend to feel relationships as places where longing and frustration share a narrow hallway.",
      "You lean toward resentment when closeness begins to feel unevenly carried.",
      "You may want the bond and still feel cornered by its demands.",
      "You tend to notice when love becomes a pattern of small negotiations you never agreed to.",
      "You may feel trapped between staying open and protecting what remains private.",
      "You lean toward ambivalence when tenderness comes tied to exhaustion.",
      "You tend to carry unspoken disappointments until they begin to color the whole room.",
      "You may remain close while part of you quietly keeps account.",
    ],
  ],
  solitude: [
    [
      "You tend to move toward solitude as a place where your thoughts can hear themselves.",
      "You lean into aloneness when the world has been speaking too loudly.",
      "You would rather meet yourself in quiet than keep borrowing noise for company.",
      "You tend to treat solitude as a room of return, not a punishment.",
      "You lean toward private space when clarity needs fewer witnesses.",
      "You prefer aloneness that restores the outline of your own mind.",
      "You tend to trust silence when it begins to reveal what the day covered.",
      "You move toward solitude when being with yourself feels more honest than being available.",
    ],
    [
      "You tend to step back from solitude when it begins to echo too much.",
      "You lean toward company when aloneness makes the room feel larger than necessary.",
      "You would rather stay connected than let silence gather too much authority.",
      "You tend to resist isolation when it starts dressing itself as wisdom.",
      "You prefer voices nearby when your own thoughts become too circular.",
      "You lean away from solitude when it feels less like rest and more like absence.",
      "You tend to trust shared life to interrupt the weight of being alone.",
      "You would rather have imperfect company than a silence that grows too deep.",
    ],
    [
      "You tend to negotiate solitude, taking enough quiet without vanishing from the world.",
      "You lean toward a rhythm between withdrawal and return.",
      "You prefer aloneness with a door, not a locked room.",
      "You tend to make space for yourself while keeping the thread of connection within reach.",
      "You would rather step aside briefly than disappear behind your own walls.",
      "You lean toward solitude as a measure, not a permanent address.",
      "You tend to balance private thought with the warmth of being known.",
      "You prefer quiet that clears you, not quiet that claims you.",
    ],
    [
      "You tend to feel solitude as both refuge and risk, a room that changes with the hour.",
      "You lean toward ambivalence when quiet becomes too necessary or too heavy.",
      "You may want to be alone and still resent how alone it can feel.",
      "You tend to feel trapped when withdrawal protects you and isolates you at once.",
      "You may carry silence as shelter in one moment and burden in the next.",
      "You lean toward frustration when solitude stops restoring you and starts repeating itself.",
      "You tend to feel the pull of retreat even while longing to be reached.",
      "You may keep your distance and still hope someone understands the signal.",
    ],
  ],
  work_and_ambition: [
    [
      "You tend to move toward ambition when it gives shape to your effort.",
      "You lean into work when it feels like a place to test your seriousness.",
      "You would rather engage the climb than wonder from below what it might have required.",
      "You tend to meet ambition as a force to be handled, not hidden.",
      "You lean toward responsibility when the work matters enough to claim you.",
      "You prefer striving with open eyes to pretending you do not want the next horizon.",
      "You tend to give your effort a direction before the day scatters it.",
      "You move toward the task when it offers both difficulty and meaning.",
    ],
    [
      "You tend to step back when ambition starts asking for too much of your life.",
      "You lean away from work that mistakes exhaustion for importance.",
      "You would rather keep your soul intact than be decorated by a title that empties you.",
      "You tend to resist ambition when it begins to sound like someone else's hunger.",
      "You prefer work that serves life, not life rearranged to serve work.",
      "You lean away from ladders that narrow the view as you climb.",
      "You tend to distrust success when it requires too much private disappearance.",
      "You would rather decline a prize than become fluent in a language you do not respect.",
    ],
    [
      "You tend to negotiate ambition, wanting growth without handing work the whole kingdom.",
      "You lean toward effort that leaves room for the rest of your life to remain real.",
      "You prefer achievement that does not require forgetting why it mattered.",
      "You tend to balance the next horizon with the cost of reaching it.",
      "You would rather move deliberately than be carried by urgency wearing a suit.",
      "You lean toward useful ambition, ambitious enough to matter and grounded enough to survive.",
      "You tend to measure work by both outcome and inner price.",
      "You prefer a climb with air in it, not only height.",
    ],
    [
      "You tend to feel ambition as both engine and chain, giving movement and demanding tribute.",
      "You lean toward resentment when work takes more from you than it admits.",
      "You may want the ascent and still feel trapped by what it requires.",
      "You tend to notice when achievement begins to cost the very life it promised to improve.",
      "You may feel caught between hunger for more and fatigue from proving.",
      "You lean toward ambivalence when success brings authority but not ease.",
      "You tend to carry work inside you long after the visible day has ended.",
      "You may resent the ladder while still knowing exactly where the next rung is.",
    ],
  ],
}

/**
 * FNV-1a 32-bit hash (tiny, dependency-free). Deterministic per question id, so the
 * picked observation is stable across reopens and revisits for the same question.
 */
function fnv1a(str: string): number {
  let h = 0x811c9dc5
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i)
    // 32-bit FNV prime multiply via Math.imul; >>> 0 keeps it unsigned.
    h = Math.imul(h, 0x01000193)
  }
  return h >>> 0
}

/**
 * The single observation line for a given answer, or null if no pool covers it
 * (unknown category, out-of-range pill index, or an empty pool — the caller then
 * shows nothing rather than a blank/placeholder). Deterministic: the same
 * (questionId) always resolves to the same line within its cell.
 */
export function observationFor(
  category: string,
  pillIndex: number,
  questionId: string,
): string | null {
  const cell = OBSERVATIONS[category]
  if (!cell) return null
  if (pillIndex < 0 || pillIndex >= cell.length) return null
  const pool = cell[pillIndex]
  if (!pool || pool.length === 0) return null
  return pool[fnv1a(questionId) % pool.length] ?? null
}
