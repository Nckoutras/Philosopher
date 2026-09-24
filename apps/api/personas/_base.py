from dataclasses import dataclass, field
from typing import Optional

from ._models import (
    CharacterAnchor,
    RegisterRange,
    AntiFlexingRules,
    ResponseLengthSpec,
    ForbiddenLexicon,
    BehavioralParameters,
    RegisterOverride,
    ConversationalMoves,
    EmotionalAcknowledgment,
)


@dataclass
class PersonaConfig:
    """A persona's full definition. NOT ALL OF IT REACHES THE MODEL.

    READ THIS BEFORE EDITING A PERSONA TO CHANGE ITS BEHAVIOUR. Only twelve of
    these fields are rendered into the system prompt by `system_base.jinja2`.
    Editing any other field changes the repo and changes nothing the model sees.

    RENDERED — these twelve reach the prompt, and are the only levers on voice:

        challenge_level        questioning_pattern     tone
        challenge_style        sentence_structure      vocabulary_register
        conversational_moves   system_fragment         voice_calibration_examples
        emotional_acknowledgment                       forbidden_phrases
        guards                 -- last in the cached block; OVERRIDES the rest

    NOT RENDERED, but read by code elsewhere — real fields, different consumers:

        slug, name, era, tradition, tier, tagline, avatar_emoji,
        opening_invocation                  -- identity, routing, UI
        retrieval_top_k                     -- services/retrieval_service.py
        response_length_words               -- evals/run.py (arm bands)
        forbidden_lexicon_persona_specific  -- services/postprocessing_service.py

    NOT RENDERED AND READ BY NOTHING — authoring intent only, zero runtime effect
    (verified 2026-09-23 by grep across services/ routers/ workers/ evals/ scripts/
    and the template; each has 0 consumers):

        character_anchors                   -- see TD-94, and the note below
        anti_flexing
        behavioral_parameters
        behavioral_parameters_by_register
        register_range
        worldview
        uses_personal_anecdote

    `character_anchors` IS DOCUMENTATION, NOT ENFORCEMENT — founder ruling
    2026-09-23 (TD-94). It is the Section 5.7 design record and is kept for that.
    It is NOT deleted, and it is NOT wired into the prompt: rendering all eleven
    personas' anchors at once would invalidate every stored §8.2 baseline in a
    single step and surface eleven latent anchor/fragment contradictions
    simultaneously. Wiring them in is its own decision, deliberately not taken as
    a side effect of a voice fix.

    **An anchor can therefore contradict what actually ships, and one does.**
    `marcus_aurelius`'s `anchor_private_admonition_not_public_instruction` says he
    "speaks as one who has first judged himself", while his `system_fragment` —
    which renders — says *never volunteer ... "I wrote to myself…"*. The prompt
    wins. When an anchor and a rendered field disagree, the rendered field is what
    the product does, and the anchor is a statement of intent that was never
    connected.

    WHY THIS DOCSTRING EXISTS. Four diffs against `character_anchors` were written,
    reviewed and approved as a voice fix on 2026-09-23. All four were inert. Nobody
    checked whether the field was rendered, because nothing here said. The list
    above is the answer to the question that was never asked.

    `anti_flexing` is the instructive case for how this happened: it is dead, and
    anti-flexing still works — because all 11 personas duplicate it as an
    "ANTI-FLEXING:" line inside `system_fragment`, which does render. A dead field
    beside working behaviour reads exactly like a live one.
    """

    # Identity
    slug: str
    name: str
    era: str
    tradition: str
    tier: str  # free | pro | premium

    # Avatar & display
    tagline: str
    avatar_emoji: str  # placeholder until real artwork

    # Voice
    worldview: str
    tone: str
    sentence_structure: str
    vocabulary_register: str
    forbidden_phrases: list[str] = field(default_factory=list)

    # Behaviour
    questioning_pattern: str = ""
    challenge_level: int = 3          # 1=gentle 5=relentless
    challenge_style: str = ""
    uses_personal_anecdote: bool = True

    # Retrieval
    retrieval_top_k: int = 4

    # UX
    opening_invocation: str = ""

    # System prompt fragment
    system_fragment: str = ""

    # Voice calibration: paired WRONG/RIGHT examples injected into system prompt
    voice_calibration_examples: list[dict] = field(default_factory=list)

    # Persona guards (SAFETY-001 ruling 2026-09-24). Prompt text, not a gate: each
    # entry is rendered under the "WHEN SOMEONE IS BEING HARMED, OR IS IN CRISIS"
    # section, the LAST block before the cache sentinel, whose heading states that
    # it overrides every instruction above it — this persona's own lines included.
    # Guards say what to do, never which line they cancel; the lines each one
    # overrides are recorded in a comment beside it in the persona module.
    # Drawn only from the `critical: true` promises in philosopher_brain/personas/
    # *.yaml. A guard changes what the persona SAYS; it cannot stop the persona
    # from being called — nothing detects these situations (SAFETY-001).
    guards: list[str] = field(default_factory=list)

    # Section 5.7 — Phase 1 schema extension (all optional, all None by default)
    #
    # MOST OF THIS BLOCK IS NOT RENDERED. Of the seven fields below, only
    # response_length_words and forbidden_lexicon_persona_specific are read by any
    # running code — and neither by the prompt template. See the class docstring
    # for the full split and TD-94 for the ruling. Editing an unrendered field to
    # change how a persona SPEAKS is a no-op, and the manifest's
    # persona_config_hash will not move.
    character_anchors: Optional[list[CharacterAnchor]] = None   # DOC ONLY — not rendered (TD-94)
    register_range: Optional[RegisterRange] = None              # DOC ONLY — not rendered
    anti_flexing: Optional[AntiFlexingRules] = None             # DOC ONLY — duplicated in system_fragment
    response_length_words: Optional[ResponseLengthSpec] = None              # LIVE — evals/run.py arm bands
    forbidden_lexicon_persona_specific: Optional[ForbiddenLexicon] = None   # LIVE — postprocessing_service
    behavioral_parameters: Optional[BehavioralParameters] = None            # DOC ONLY — not rendered
    behavioral_parameters_by_register: Optional[dict[str, RegisterOverride]] = None  # DOC ONLY — not rendered
    conversational_moves: Optional[ConversationalMoves] = None
    emotional_acknowledgment: Optional[EmotionalAcknowledgment] = None

    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)
