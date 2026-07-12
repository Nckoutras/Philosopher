import asyncio
import json
import time
import logging
import os
from datetime import date
from uuid import UUID
from typing import AsyncGenerator

import anthropic

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update

from models import Conversation, DailyUsage, Message, Persona, SafetyEvent, SavedLine, User, WeeklyLetter
from personas import get_persona, is_persona_accessible
from services.safety_service import safety_service
from services.memory_service import memory_service
from services.retrieval_service import retrieval_service
from services.llm_client import llm_client
from services.prompt_builder import prompt_builder
from services.preferences_service import get_user_preferences
from services.profile_text import profile_to_display
from services.analytics_service import analytics_service
from services.persona_voice import get_error_voice
import services.rate_limit_service as rate_limit_service
from services.postprocessing_service import (
    POSTPROCESSING_ENABLED,
    check_universal_forbidden,
    check_brevity,
    CheckAction,
    _build_regen_directive,
    _deterministic_strip,
)
from services.phenomenology_bridge_service import phenomenology_bridge_service

MODEL_FREE = "claude-haiku-4-5-20251001"
MODEL_PRO = "claude-sonnet-4-6"
MEMORY_WINDOW_FREE = 5
MEMORY_WINDOW_PRO = 20

# Gravity-gated conclusion assessment (async, off the chat critical path).
# First assessment fires at CONCLUSION_MIN_DEPTH messages, then every
# CONCLUSION_CADENCE messages thereafter. Tunable.
CONCLUSION_MIN_DEPTH = 8
CONCLUSION_CADENCE = 6

logger = logging.getLogger(__name__)

SSE_SAFETY_TOKEN = "\n\n[PHILOSOPHER_SAFETY_OVERRIDE]\n\n"

# Phase 4 — Modern Phenomenology Bridge feature flag.
# Default off. Enabled in production via Render env var after smoke test.
PHENOMENOLOGY_BRIDGE_ENABLED = (
    os.getenv("PHENOMENOLOGY_BRIDGE_ENABLED", "false").lower() == "true"
)

CROSS_MIND_NOTE = (
    "NOTE ON OTHER VOICES: Earlier in this exchange, the seeker invited other "
    "thinkers to weigh in. Their contributions are marked inline as \"[Name]: …\". "
    "Those words are not yours. If the seeker asks what you make of something "
    "another thinker said, engage with it directly, in your own voice and "
    "judgement. Never prefix or bracket your own reply with a name — speak "
    "plainly as yourself."
)

GUEST_ENTRANCE = (
    "ENTERING AN ONGOING REFLECTION: You have just been invited into a conversation "
    "that is already underway. Before you respond, take in the last several turns as a "
    "whole — what the seeker is actually wrestling with — rather than reacting only to "
    "their final line, which may be a fragment or an aside. Open by orienting yourself to "
    "where the exchange truly is, in your own voice. If the thread is genuinely unclear or "
    "too thin to engage honestly, it is better to ask the seeker what they would like from "
    "you than to guess or perform."
)

# Go-deeper is the ONE place a reply breaks past the normal length ceiling (U)
# into the persona's deeper "reflective" band. The directive is identical for
# free and Pro — the free limit caps quantity (3/day), never depth.
_DEEPEN_FALLBACK_WORDS = 90  # used only if a persona lacks reflective_reply_max_words


def _deepen_directive(persona) -> str:
    """Build the go-deeper system directive, sized to the persona's deeper band
    (response_length_words.reflective_reply_max_words), which exceeds the normal
    standard ceiling U. This is what makes go-deeper feel satisfying."""
    spec = getattr(persona, "response_length_words", None)
    target = None
    if spec is not None:
        target = spec.reflective_reply_max_words
    target = target or _DEEPEN_FALLBACK_WORDS
    return (
        "GOING DEEPER: The seeker has asked you to take this further. This is the one reply "
        "where you do NOT hold to your usual brevity — open up and develop the thought fully. "
        f"You have real room here: up to about {target} words. Use it to go deep, not to pad — "
        "every sentence must earn its place, but do not cut the reflection short.\n\n"
        "Refuse the surface of what they just said. Name what they are circling but not saying — "
        "the evasion, the flattering story, the question beneath the question — and then develop "
        "it: trace where it comes from, what it costs them, what it would mean to face it. Bring "
        "the psychological depth and the harder truth they came back for, worked through rather "
        "than merely announced.\n\n"
        "Speak with your full weight, unmistakably in your own voice, carrying the flavour of your "
        "actual thought and work — the ideas and stance you are known for, never generic "
        "philosophy. Land somewhere that gives them more to sit with, not less.\n\n"
        "Depth means NEW layers — material you have not yet touched in this conversation. "
        "Re-elaborating an interpretation you already gave, at greater length, is not depth; "
        "it is repetition with more words."
    )

SEEDED_OPENING_DIRECTIVE = (
    "OPENING A SEEDED REFLECTION: The seeker has handed you a topic to begin from, "
    "not a question of their own. This is your first turn. Do NOT open by asking them "
    "what they think, where they would start, or what they mean — they came to hear YOU.\n\n"
    "Lead with your own position on this topic, stated sharply and in your unmistakable "
    "voice. Not a balanced overview, not a neutral summary, not throat-clearing — the "
    "actual view that only you would hold, carrying the flavour of your own thought and "
    "work. Stake a claim. Say the thing only you would say.\n\n"
    "Then, and only then, close with a SINGLE invitation to go further on one specific "
    "aspect — phrased as an invitation, never an interrogation. Something in the spirit of "
    "\"I'd want to hear where this lands for you, especially on X\": one open door, not a "
    "stack of questions, not a quiz. The invitation is the last beat, after the position — "
    "never the whole reply.\n\n"
    "This overrides, for THIS opening turn ONLY, any rule that you usually lead with a "
    "question or that a fixed fraction of replies must end in a question. Socrates: you too "
    "lead with a position here — but it may be a sharp provocation, a claim sly enough to "
    "itch, rather than a flat thesis. Remain unmistakably yourself; simply do not open on a "
    "question. Your normal questioning resumes on the next turn.\n\n"
    "Stay within your usual length and register. One clean opening move: a position, then a door."
)

REVISIT_OPENING = (
    "REVISIT — this is your first turn. You have just read the weekly letter below, written "
    "about this person based on their week of reflection. Do NOT summarise the letter back to "
    "them. Instead, deliver your own sharp, candid read on who this person is and what they are "
    "doing — as only you would see it. A clear-eyed jolt in service of their clarity, not a "
    "comfort. Be blunt and specific; name the pattern you see. This is honest provocation, never "
    "contempt: do not demean them, do not attack their worth, never use clinical or diagnostic "
    "language. Stay unmistakably in your own voice and register, within your usual length. Do NOT "
    "open or close with a question. End with a SINGLE genuine invitation to take it further — an "
    "open door, not an interrogation (in the spirit of: \"I'd be interested to hear how that "
    "lands for you\"). Respond in the same language as the letter."
)

# Repeat go-deepers on the SAME reply push to a NEW angle — they do NOT shorten.
# (Depth is the whole point now; the prior "cut to one sentence" escalation was
# removed so it stops fighting the deeper band.)
DEEPEN_ESCALATION = {
    2: " ESCALATION (second deepening of this SAME reply): do not repeat the angle you just "
       "took — open a genuinely new layer. Go further beneath, not shorter.",
    3: " ESCALATION (third deepening): reach the deepest layer you honestly can — the root, "
       "stated plainly. Still developed, not clipped.",
}

TURN_LIMIT   = {'free': 3, 'pro': 5, 'premium': 5}
THREAD_LIMIT = {'free': 15, 'pro': 30, 'premium': 30}

# Adaptive response length (§ adaptive-length brief). Match reply size to the
# size of the user's message at the EXTREMES only — short input → shorter reply,
# long/developed input → fuller reply — while leaving the typical (medium) case
# untouched. Bands are drawn from the persona's existing standard_reply_words
# (L, U); the long tier is capped at the existing ceiling U and never exceeds it
# (a fuller "satisfying" reply is reserved for go-deeper). Caller gates this
# behind distress and the first-message cap.
ADAPTIVE_LENGTH_SHORT_MAX_WORDS = 15   # input ≤ this → short tier
ADAPTIVE_LENGTH_LONG_MIN_WORDS = 50    # input ≥ this → long tier
ADAPTIVE_LENGTH_SHORT_FRACTION = 0.34  # short reply upper = L + round(span * this)
ADAPTIVE_LENGTH_LONG_FRACTION = 0.5    # long reply lower  = L + round(span * this)


def _length_directive_for_input(user_text: str, persona) -> str | None:
    """Return a system-prompt length directive sized to the user's input, or None.

    None means "no directive" → the prompt is byte-identical to before. That is
    the case for medium-sized input, or when the persona has no standard band.
    Distress and first-message gating are the caller's responsibility (this only
    looks at input size and the persona band).
    """
    spec = getattr(persona, "response_length_words", None)
    if spec is None or spec.standard_reply_words is None:
        return None

    low, high = spec.standard_reply_words
    span = high - low
    word_count = len(user_text.split())

    if word_count <= ADAPTIVE_LENGTH_SHORT_MAX_WORDS:
        lo, hi = low, low + round(span * ADAPTIVE_LENGTH_SHORT_FRACTION)
        return (
            f"LENGTH FOR THIS REPLY: the person wrote only a line or two. Match them — "
            f"answer briefly, about {lo}–{hi} words. Never exceed {high} words."
        )
    if word_count >= ADAPTIVE_LENGTH_LONG_MIN_WORDS:
        lo, hi = low + round(span * ADAPTIVE_LENGTH_LONG_FRACTION), high
        return (
            f"LENGTH FOR THIS REPLY: the person wrote at length and developed their thought. "
            f"You may answer more fully, about {lo}–{hi} words — but never exceed {high} "
            f"words, and never pad to fill space."
        )
    # Medium input: no directive — typical behaviour is unchanged.
    return None


class ConversationService:

    # ── Create conversation ───────────────────────────────────────────────────
    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        persona_slug: str,
        ritual_id: str | None = None,
        user_plan: str = "free",
        skip_opening: bool = False,
    ) -> Conversation:
        persona_config = get_persona(persona_slug)
        if not persona_config:
            raise ValueError(f"Unknown persona: {persona_slug}")
        if not is_persona_accessible(persona_config, user_plan):
            raise PermissionError(f"Persona {persona_slug} requires plan upgrade")

        # Fetch persona DB record (for FK)
        result = await db.execute(select(Persona).where(Persona.slug == persona_slug))
        persona = result.scalar_one_or_none()
        if not persona:
            raise ValueError(f"Persona {persona_slug} not in database")

        # When skip_opening=True we always want a fresh conversation with no
        # opening_invocation, so bypass the dedup check entirely. A dedup'd
        # row could already have an opening message even though message_count==0.
        if not skip_opening:
            ritual_filter = (
                Conversation.ritual_id.is_(None) if ritual_id is None
                else Conversation.ritual_id == ritual_id
            )
            dedup_result = await db.execute(
                select(Conversation)
                .where(
                    Conversation.user_id == user_id,
                    Conversation.persona_id == persona.id,
                    Conversation.message_count == 0,
                    ritual_filter,
                )
                .order_by(Conversation.created_at.desc())
                .limit(1)
            )
            existing = dedup_result.scalar_one_or_none()
            if existing:
                # A reused empty conversation may lack its opening message (e.g. created
                # earlier via skip_opening=True then abandoned). Ensure it has one before
                # returning, so a fresh no-topic chat always shows the persona's opening.
                if persona_config.opening_invocation:
                    has_opening = await db.execute(
                        select(Message.id)
                        .where(
                            Message.conversation_id == existing.id,
                            Message.role == "assistant",
                        )
                        .limit(1)
                    )
                    if has_opening.scalar_one_or_none() is None:
                        db.add(
                            Message(
                                conversation_id=existing.id,
                                user_id=user_id,
                                role="assistant",
                                content=persona_config.opening_invocation,
                            )
                        )
                        await db.flush()
                return existing

        conv = Conversation(
            user_id=user_id,
            persona_id=persona.id,
            ritual_id=ritual_id,
        )
        db.add(conv)
        await db.flush()

        if not skip_opening and persona_config.opening_invocation:
            opening = Message(
                conversation_id=conv.id,
                user_id=user_id,
                role="assistant",
                content=persona_config.opening_invocation,
            )
            db.add(opening)
        await db.flush()
        return conv

    # ── Create cross-persona conversation ────────────────────────────────────
    async def create_cross_persona(
        self,
        db: AsyncSession,
        user_id: str,
        saved_line_id: str,
        target_persona_slug: str,
    ) -> Conversation:
        """Create a new empty conversation seeded from a saved line.

        Sets source_saved_line_id and source_persona_slug for analytics and
        frontend pre-fill. No bootstrap message is created; the user sends
        the first message after the draft is pre-filled from localStorage.
        """
        # Load saved line + verify ownership
        sl_result = await db.execute(
            select(SavedLine).where(
                SavedLine.id == saved_line_id,
                SavedLine.user_id == user_id,
                SavedLine.deleted_at.is_(None),
            )
        )
        saved_line = sl_result.scalar_one_or_none()
        if not saved_line:
            raise ValueError("Saved line not found")

        # Load source persona (for source_persona_slug)
        src_persona_result = await db.execute(
            select(Persona).where(Persona.id == saved_line.persona_id)
        )
        source_persona = src_persona_result.scalar_one()

        # Load and validate target persona
        tgt_persona_result = await db.execute(
            select(Persona).where(Persona.slug == target_persona_slug)
        )
        target_persona = tgt_persona_result.scalar_one_or_none()
        if not target_persona:
            raise ValueError(f"Persona not found: {target_persona_slug}")
        if target_persona.slug == source_persona.slug:
            raise ValueError("Target persona must differ from source persona")

        # Create the conversation record
        conv = Conversation(
            user_id=user_id,
            persona_id=target_persona.id,
            source_saved_line_id=saved_line_id,
            source_persona_slug=source_persona.slug,
        )
        db.add(conv)
        await db.flush()
        return conv

    # ── Create reading-revisit conversation ───────────────────────────────────
    async def create_reading_revisit(
        self,
        db: AsyncSession,
        user_id: str,
        weekly_letter_id: str,
        target_persona_slug: str,
        user_plan: str = "free",
    ) -> Conversation:
        """Create a conversation whose FIRST assistant message is the chosen
        persona's sharp, candid read on the user — generated (non-stream) from
        the weekly letter's content. Mirrors create()'s opening-message shape.
        """
        # Load weekly letter + verify ownership and generated state
        wl_result = await db.execute(
            select(WeeklyLetter).where(
                WeeklyLetter.id == weekly_letter_id,
                WeeklyLetter.user_id == user_id,
            )
        )
        letter = wl_result.scalar_one_or_none()
        if not letter or letter.status != "generated":
            raise ValueError("Weekly letter not found")

        # Resolve + access-gate the target persona (config drives both)
        persona_config = get_persona(target_persona_slug)
        if not persona_config:
            raise ValueError(f"Unknown persona: {target_persona_slug}")
        if not is_persona_accessible(persona_config, user_plan):
            raise PermissionError(f"Persona {target_persona_slug} requires plan upgrade")

        # Persona DB record (for FK)
        persona_result = await db.execute(select(Persona).where(Persona.slug == target_persona_slug))
        persona_db = persona_result.scalar_one_or_none()
        if not persona_db:
            raise ValueError(f"Persona {target_persona_slug} not in database")

        conv = Conversation(user_id=user_id, persona_id=persona_db.id)
        db.add(conv)
        await db.flush()

        # Assemble the reading from payload fields IN ORDER, skipping empties.
        # status/suggested_persona_slug are intentionally ignored.
        payload = letter.payload or {}
        assembled_reading = "\n\n".join(
            str(payload[k]).strip()
            for k in ("title", "opening", "references", "pull_quote", "forward_gesture")
            if payload.get(k)
        )

        # build_system FIRST (its safety/HARD-RULES layer must stay) — APPEND only.
        # build_system takes the PersonaConfig, never the DB row.
        system_prompt = prompt_builder.build_system(
            persona=persona_config, memories=[], passages=[]
        ) + "\n\n" + REVISIT_OPENING

        # One non-stream completion. The user turn carrying the reading is NOT persisted.
        text = await llm_client.complete(
            system=system_prompt,
            user=f"<letter>\n{assembled_reading}\n</letter>",
            model=MODEL_PRO,
            max_tokens=1024,
        )

        # ── SECOND SAFETY LAYER (post-generation) ────────────────────────────
        # This is the app's sharpest dynamically-generated content, so it MUST
        # pass the same post-gen gate as the streaming path. On suppression we
        # replace the text with the app-voice safe line, log the event, and mark
        # the row persona_override — byte-for-byte the stream_response handling.
        safety_out = await safety_service.check_output(text)
        if safety_out.should_suppress_persona:
            logger.warning(
                "post_gen_safety_override",
                extra={
                    "persona_slug": persona_config.slug,
                    "safety_level": safety_out.level,
                    "conversation_id": str(conv.id),
                    "user_id": str(user_id),
                    "exposed_content_first_100": text[:100],
                },
            )
            await self._log_safety_event(db, user_id, conv.id, None, safety_out, "post_generation")
            text = prompt_builder.build_safety_response(level=safety_out.level)

        await self._save_message(
            db, conv, user_id, "assistant", text,
            safety_level=safety_out.level,
            persona_override=safety_out.should_suppress_persona,
        )
        await db.commit()
        return conv

    # ── Stream response ───────────────────────────────────────────────────────
    async def stream_response(
        self,
        session_factory,
        conversation_id: str,
        user_id: str,
        user_text: str,
        user_plan: str = "free",
        user_name: str | None = None,
        is_admin: bool = False,
        arq_queue=None,
        seeded_opening: bool = False,
    ) -> AsyncGenerator[str, None]:
        # §5 pool-leak fix: this generator takes a session FACTORY, not a
        # request-scoped session. DB work happens in short-lived sessions in
        # Phase A (pre-stream) and Phase C (post-stream); the LLM token stream
        # (Phase B) holds NO pooled session. Values needed after a session
        # closes are snapshotted into plain locals so no detached ORM attribute
        # is ever lazy-loaded.
        start = time.monotonic()

        # ══ PHASE A — PRE-STREAM DB (short-lived session) ════════════════════
        async with session_factory() as db:
            # Load conversation + persona
            result = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if not conv:
                raise ValueError("Conversation not found")
            # Sticky guest: the responder is the active mind when set, else the
            # immutable home persona. This same resolved id is snapshotted below
            # as conv_persona_id so quota consumption and memory provenance follow
            # whoever actually answered (acceptance: active guest's quota).
            responder_persona_id = conv.active_persona_id or conv.persona_id
            persona_result = await db.execute(select(Persona).where(Persona.id == responder_persona_id))
            persona_db = persona_result.scalar_one()
            persona = get_persona(persona_db.slug)

            # ── 1. PRE-GENERATION SAFETY ─────────────────────────────────────
            safety_in = await safety_service.check_input(user_text, user_id)
            if safety_in.should_log:
                await self._log_safety_event(db, user_id, conversation_id, None, safety_in, "pre_generation")
            if safety_in.should_suppress_persona:
                # Save user message first
                user_msg = await self._save_message(db, conv, user_id, "user", user_text, safety_level=safety_in.level)
                safe_text = prompt_builder.build_safety_response(level=safety_in.level)
                await self._save_message(db, conv, user_id, "assistant", safe_text, safety_level=safety_in.level, persona_override=True)
                await db.commit()
                analytics_service.track("safety_event_pre", user_id, {"risk_level": safety_in.level, "category": safety_in.category})
                yield f"data: {json.dumps({'type': 'safety', 'level': safety_in.level})}\n\n"
                for chunk in self._chunk_text(safe_text):
                    yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            # ── 2. RECALL MEMORY ─────────────────────────────────────────────
            memories = []
            try:
                memories = await memory_service.recall(db, user_id, user_text, top_k=6)
            except Exception as e:
                logger.warning(f"Memory recall failed: {e}")
                await db.rollback()

            # ── 3. RETRIEVE PASSAGES ─────────────────────────────────────────
            passages = []
            try:
                passages = await retrieval_service.retrieve(db, user_text, persona)
            except Exception as e:
                logger.warning(f"Retrieval failed: {e}")
                await db.rollback()

            # ── 3.5. PHENOMENOLOGY BRIDGE LOOKUP (Phase 4) ───────────────────
            # If a modern term in the user's message maps to a phenomenological
            # essence, the persona will see the timeless translation in its
            # system prompt and engage with that — without naming the modern
            # term back. Feature-flagged; fail-open on any error.
            phenomenology_bridge = None
            if PHENOMENOLOGY_BRIDGE_ENABLED:
                try:
                    phenomenology_bridge = phenomenology_bridge_service.lookup(
                        user_message=user_text,
                        persona_slug=persona.slug,
                    )
                except Exception as e:
                    logger.warning(
                        f"Phenomenology bridge lookup failed for "
                        f"persona={persona.slug}: {e}. Proceeding without bridge."
                    )
                    # phenomenology_bridge stays None

            # ── 3.8. ONBOARDING PROFILE (guaranteed, NOT recall) ─────────────
            # Self-reported pills surface in the system prompt on turn 1, regardless
            # of message similarity — unlike memories (cosine-recalled). Fail-open.
            profile_view = None
            try:
                pref = await get_user_preferences(user_id, db)
                profile_view = profile_to_display(pref.profile if pref else None)
            except Exception as e:
                logger.warning(f"Profile load failed: {e}")
                await db.rollback()

            # ── 4. BUILD SYSTEM PROMPT ───────────────────────────────────────
            system_prompt = prompt_builder.build_system(
                persona=persona,
                memories=memories,
                passages=passages,
                phenomenology_bridge=phenomenology_bridge,
                profile=profile_view,
            )

            # ── 5. BUILD MESSAGE HISTORY ─────────────────────────────────────
            history_result = await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    # CONCLUSION EXCLUSION: distilled conclusion rows must NEVER enter
                    # the LLM context window. message_kind is NOT NULL (default
                    # 'standard'), so this filter is byte-equivalent to the prior
                    # behaviour for all existing/standard/go_deeper rows.
                    Message.message_kind != 'conclusion',
                )
                .order_by(Message.created_at.asc())
                .limit(MEMORY_WINDOW_PRO if user_plan in ("pro", "premium") else MEMORY_WINDOW_FREE)
            )
            history = history_result.scalars().all()
            # Cross-mind awareness: label every assistant turn NOT authored by the
            # current responder so it reads as another mind's words. The responder
            # is the sticky active guest when set, else home (persona_id None =>
            # home). When the responder is home and no guest turns exist, this is
            # byte-identical to the prior behaviour.
            _foreign = [
                m for m in history
                if m.role == "assistant" and (m.persona_id or conv.persona_id) != responder_persona_id
            ]
            if _foreign:
                _pid_set = {conv.persona_id, responder_persona_id} | {m.persona_id for m in history if m.persona_id}
                _name_rows = await db.execute(
                    select(Persona.id, Persona.name).where(Persona.id.in_(_pid_set))
                )
                _id_to_name = {r.id: r.name for r in _name_rows.all()}
                lm_messages = self._build_lm_messages(
                    history, conv.persona_id, responder_persona_id, _id_to_name
                )
                system_prompt = system_prompt + "\n\n" + CROSS_MIND_NOTE
            else:
                lm_messages = [
                    {"role": m.role, "content": m.content}
                    for m in history
                    if m.role in ("user", "assistant")
                ]
            # W3 fix: Anthropic API requires messages to start with a user turn.
            # opening_invocation and cross-persona bootstrap both save an initial
            # assistant message with no preceding user message in the DB. Strip any
            # leading assistant turns so the API call is always user-first.
            while lm_messages and lm_messages[0]["role"] == "assistant":
                lm_messages.pop(0)
            lm_messages.append({"role": "user", "content": user_text})

            # Seeded opening: the seeker handed the persona a topic to begin from
            # (no opening_invocation exists on these conversations). For this first
            # turn only, steer the persona to lead with its own position and close
            # with an invitation — not a question. Gated to an empty prior history
            # so it never affects later turns.
            history_len = len(history)
            if seeded_opening and history_len == 0:
                system_prompt = system_prompt + "\n\n" + SEEDED_OPENING_DIRECTIVE

            # Pro sticky DEEP MODE (read site). When the conversation's deep_mode
            # flag is on AND the sender is Pro/premium, every normal reply is deep
            # (the persona's reflective band, exceeding the normal ceiling U).
            # Defense-in-depth: the Pro/premium check here means a stale deep_mode
            # on a downgraded account is inert (no depth) even though the flag
            # persists — independent of the Pro-gated set endpoint. Distress still
            # wins: skipped unless safety level is "none". Deep mode REPLACES the
            # adaptive-length directive (they are mutually exclusive for this turn).
            deep_mode_active = (
                conv.deep_mode
                and user_plan in ("pro", "premium")
                and safety_in.level == "none"
            )
            if deep_mode_active:
                system_prompt = system_prompt + "\n\n" + _deepen_directive(persona)
            # Adaptive response length: size the reply to the user's input size.
            # Gated AFTER safety so distress always wins — any non-"none" safety
            # level (the surviving case is "low"/distress_signal; medium+ already
            # returned a safety response above) suppresses the directive, keeping
            # the grounded/short default. Skipped for the first message
            # (history_len <= 1), whose own first_message cap governs, and for
            # medium-sized input (helper returns None → prompt unchanged).
            elif history_len > 1 and safety_in.level == "none":
                length_directive = _length_directive_for_input(user_text, persona)
                if length_directive:
                    system_prompt = system_prompt + "\n\n" + length_directive

            # ── 6. SAVE USER MESSAGE ─────────────────────────────────────────
            # Commit (not just flush) so the user turn is durably persisted
            # before the session is released for the token-stream phase.
            user_msg = await self._save_message(db, conv, user_id, "user", user_text, safety_level=safety_in.level)
            await db.commit()

            # Snapshot every value Phase B / Phase C / analytics need, while the
            # session is still open. After this block the only detached access
            # is conv.id (a loaded PK scalar) inside _save_message — safe, no
            # lazy load. Re-loading conv in Phase C is intentionally avoided so
            # the DB execute sequence stays identical to the prior behaviour.
            user_msg_created_at = user_msg.created_at
            retrieval_ids = [str(p.id) for p in passages]
            retrieval_hit = len(passages) > 0
            memory_hit = len(memories) > 0
            conv_message_count = conv.message_count
            conv_title = conv.title
            conv_ritual_id = conv.ritual_id
            # Resolved responder (active guest or home) — drives DailyUsage quota
            # consumption and memory-extraction provenance below (Gaps 1 & 3).
            conv_persona_id = responder_persona_id
        # ── Phase A session closed — pool freed for the token stream ─────────

        # ══ PHASE B — TOKEN STREAM (no pooled session held) ══════════════════
        # Chunks are yielded to the client as they arrive. Retries apply only
        # when no chunks have been sent yet (connection-phase failures).
        model = MODEL_PRO if user_plan in ("pro", "premium") else MODEL_FREE
        full_response = ""
        yield f"data: {json.dumps({'type': 'start'})}\n\n"

        _llm_success = False
        _last_llm_error: Exception | None = None
        _buf: list[str] = []
        _chunks_yielded = False

        for attempt in range(3):
            _buf = []
            _chunks_yielded = False
            try:
                async for chunk in llm_client.stream(
                    system=system_prompt, messages=lm_messages, model=model
                ):
                    _buf.append(chunk)
                    _chunks_yielded = True
                    yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
                full_response = "".join(_buf)
                _llm_success = True
                break
            except anthropic.RateLimitError as exc:
                _last_llm_error = exc
                if _chunks_yielded:
                    break
                await asyncio.sleep(2**attempt)
            except anthropic.APIStatusError as exc:
                _last_llm_error = exc
                if _chunks_yielded or exc.status_code < 500:
                    break
                await asyncio.sleep(2**attempt)
            except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
                _last_llm_error = exc
                if _chunks_yielded:
                    break
                await asyncio.sleep(2**attempt)

        if not _llm_success:
            # User message already committed in Phase A; nothing further to
            # persist on LLM failure — just surface the error and end.
            persona_voice_text = get_error_voice(persona, "llm_unavailable")
            error_event = {
                "type": "error",
                "error_code": "llm_unavailable",
                "persona_voice": persona_voice_text,
            }
            logger.error(
                f"LLM stream failed for persona={persona.slug}: {_last_llm_error}"
            )
            yield f"data: {json.dumps(error_event)}\n\n"
            return

        # ══ PHASE C1 — POST-GEN SAFETY + POSTPROCESSING (no session held) ════
        # SAFETY OVERRIDE BYPASS — non-negotiable invariant (Decision D).
        # Already-streamed persona content is replaced client-side by safety
        # response. Postprocessing MUST NOT touch safety override content.
        # No pooled session is held here: the correction path may itself stream
        # from the LLM, which must never pin a DB connection (§5).
        safety_out = await safety_service.check_output(full_response)
        if safety_out.should_suppress_persona:
            logger.warning(
                "post_gen_safety_override",
                extra={
                    "persona_slug": persona.slug,
                    "safety_level": safety_out.level,
                    "conversation_id": str(conversation_id),
                    "user_id": str(user_id),
                    "exposed_content_first_100": full_response[:100],
                },
            )
            yield f"data: {json.dumps({'type': 'safety_override', 'level': safety_out.level})}\n\n"
            safe_text = prompt_builder.build_safety_response(level=safety_out.level)
            for chunk in self._chunk_text(safe_text):
                yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
            full_response = safe_text
        elif POSTPROCESSING_ENABLED:
            # ── POSTPROCESSING — inline check + streaming correction ─────────
            # Initial chunks already yielded above. If they fail the forbidden-
            # lexicon check, stream a correction in real-time via `correction`
            # event. Frontend fades original and shows the new stream.
            conv_position = "first_message" if history_len <= 1 else "mid_session"
            _fb  = check_universal_forbidden(full_response)
            _brv = check_brevity(full_response, persona, conv_position)
            _triggered = [c for c in (_fb,) if c.action == CheckAction.REGENERATE]  # brevity no longer forces a regenerate/correction; it stays a prompt-level nudge
            if _triggered:
                hit_categories = sorted(set(
                    h.category for c in _triggered for h in c.hits if h.category
                ))
                logger.info(
                    "postprocessing_correction_triggered",
                    extra={
                        "persona_slug": persona.slug,
                        "hit_categories": hit_categories,
                        "conversation_id": str(conversation_id),
                        "user_id": str(user_id),
                        "original_response_first_50": full_response[:50],
                    },
                )
                yield f"data: {json.dumps({'type': 'correction'})}\n\n"
                directive = _build_regen_directive(_triggered, 0, persona)
                correction_buf: list[str] = []
                try:
                    async for chunk in llm_client.stream(
                        system=system_prompt + "\n\n" + directive,
                        messages=lm_messages,
                        model=model,
                    ):
                        correction_buf.append(chunk)
                        yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
                    correction_text = "".join(correction_buf)
                    _fb2  = check_universal_forbidden(correction_text)
                    _brv2 = check_brevity(correction_text, persona, conv_position)
                    if _fb2.action in (CheckAction.PASS, CheckAction.SKIP) and _brv2.action in (CheckAction.PASS, CheckAction.SKIP):
                        logger.info(
                            "postprocessing_correction_passed",
                            extra={
                                "persona_slug": persona.slug,
                                "conversation_id": str(conversation_id),
                                "user_id": str(user_id),
                            },
                        )
                        full_response = correction_text
                    else:
                        stripped = _deterministic_strip(correction_text, [_fb2, _brv2])
                        logger.warning(
                            "postprocessing_correction_stripped",
                            extra={
                                "persona_slug": persona.slug,
                                "hit_categories": sorted(set(
                                    h.category for c in (_fb2, _brv2) for h in c.hits if h.category
                                )),
                                "word_count": _brv2.word_count,
                                "conversation_id": str(conversation_id),
                                "user_id": str(user_id),
                            },
                        )
                        full_response = stripped
                except Exception as e:
                    logger.error(
                        "postprocessing_correction_failed",
                        extra={
                            "persona_slug": persona.slug,
                            "error": str(e)[:200],
                            "conversation_id": str(conversation_id),
                            "user_id": str(user_id),
                        },
                    )
                    # full_response stays as original initial response

        latency_ms = int((time.monotonic() - start) * 1000)

        # ══ PHASE C2 — PERSIST ASSISTANT MSG + METADATA (fresh session) ══════
        # All gate/metadata inputs were snapshotted in Phase A. conv.message_count
        # is the pre-update value (the UPDATE below is a SQL expression and does
        # not refresh the in-memory attribute), so these match the prior
        # single-session behaviour exactly.
        async with session_factory() as db:
            # ── POST-GEN SAFETY EVENT LOG (deferred from C1 — needs a session) ─
            if safety_out.should_suppress_persona:
                await self._log_safety_event(db, user_id, conversation_id, None, safety_out, "post_generation")

            # ── SAVE ASSISTANT MESSAGE ───────────────────────────────────────
            # `conv` is detached from the Phase A session; _save_message reads
            # only conv.id (a loaded PK scalar — safe, no lazy load).
            assistant_msg = await self._save_message(
                db, conv, user_id, "assistant", full_response,
                retrieval_ids=retrieval_ids,
                safety_level=max(safety_in.level, safety_out.level, key=lambda l: ["none","low","medium","high","critical"].index(l)),
                persona_override=safety_out.should_suppress_persona,
                latency_ms=latency_ms,
            )

            # ── UPDATE CONVERSATION METADATA ─────────────────────────────────
            new_message_count = (conv_message_count or 0) + 2
            prior_pairs = (conv_message_count or 0) // 2
            await db.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(
                    message_count=Conversation.message_count + 2,
                    last_message_at=user_msg_created_at,
                )
            )

            # ── INCREMENT DAILY USAGE ────────────────────────────────────────
            # Skip for admins, ritual conversations, and safety-suppressed responses.
            if not is_admin and conv_ritual_id is None and not safety_out.should_suppress_persona:
                today = date.today()
                usage_result = await db.execute(
                    select(DailyUsage).where(
                        DailyUsage.user_id == user_id,
                        DailyUsage.persona_id == conv_persona_id,
                        DailyUsage.usage_date == today,
                    )
                )
                usage = usage_result.scalar_one_or_none()
                if usage:
                    usage.message_count += 1
                else:
                    db.add(DailyUsage(
                        user_id=user_id,
                        persona_id=conv_persona_id,
                        usage_date=today,
                        message_count=1,
                    ))

            await db.commit()
            assistant_msg_id = assistant_msg.id
        # ── Phase C2 session closed — fire side-effects with no session held ─

        if (
            arq_queue is not None
            and new_message_count >= 2
            and conv_title is None
        ):
            await arq_queue.enqueue_job(
                "generate_conversation_title", str(conversation_id)
            )

        if arq_queue is not None and not safety_out.should_suppress_persona:
            # Dilemma/belief signal insights are only promoted when the WHOLE exchange
            # was safety-clean; pass that as a trailing flag (the task defaults it False,
            # so a stale-queued job without the arg stays safe).
            safety_ok = safety_in.level == "none" and safety_out.level == "none"
            await arq_queue.enqueue_job(
                "extract_memory_task",
                str(user_id),
                str(conversation_id),
                str(conv_persona_id),
                user_text,
                full_response,
                prior_pairs,
                safety_ok,
            )

        # Gravity-gated conclusion: assess (and maybe distill) only at cadence,
        # never before min-depth, and never when the persona is safety-suppressed
        # (same gate as memory extraction above). The task itself decides whether
        # the conversation is save-worthy yet — it may emit nothing.
        if (
            arq_queue is not None
            and not safety_out.should_suppress_persona
            and new_message_count >= CONCLUSION_MIN_DEPTH
            and (new_message_count - CONCLUSION_MIN_DEPTH) % CONCLUSION_CADENCE == 0
        ):
            await arq_queue.enqueue_job(
                "assess_conclusion_task", str(conversation_id), str(user_id)
            )

        # ── ANALYTICS ────────────────────────────────────────────────────────
        analytics_service.track("message_sent", user_id, {
            "persona_slug": persona.slug,
            "conversation_id": conversation_id,
            "safety_level": safety_in.level,
            "retrieval_hit": retrieval_hit,
            "memory_hit": memory_hit,
            "latency_ms": latency_ms,
        })

        yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg_id})}\n\n"

    # ── Stream another mind ───────────────────────────────────────────────────
    async def stream_another_mind(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        target_persona_slug: str,
        user_plan: str = "free",
        user_name: str | None = None,
        is_admin: bool = False,
        arq_queue=None,
    ) -> AsyncGenerator[str, None]:
        # Load conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise ValueError("Conversation not found")

        # Resolve target persona (config + DB record)
        persona = get_persona(target_persona_slug)
        target_result = await db.execute(select(Persona).where(Persona.slug == target_persona_slug))
        target_db = target_result.scalar_one()

        # Fetch the most recent user message — used for memory/retrieval queries
        # and as the final user turn the guest responds to.
        last_user_result = await db.execute(
            select(Message.content)
            .where(Message.conversation_id == conversation_id, Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_user_text: str = last_user_result.scalar_one_or_none() or ""

        # ── 1. RECALL MEMORY ─────────────────────────────────────────────────
        memories = []
        try:
            memories = await memory_service.recall(db, user_id, last_user_text, top_k=6)
        except Exception as e:
            logger.warning(f"Memory recall failed (another_mind): {e}")
            await db.rollback()

        # ── 2. RETRIEVE PASSAGES (target persona) ────────────────────────────
        passages = []
        try:
            passages = await retrieval_service.retrieve(db, last_user_text, persona)
        except Exception as e:
            logger.warning(f"Retrieval failed (another_mind): {e}")
            await db.rollback()

        # ── 3. BUILD SYSTEM PROMPT (target persona) ──────────────────────────
        system_prompt = prompt_builder.build_system(
            persona=persona,
            memories=memories,
            passages=passages,
        )
        system_prompt = system_prompt + "\n\n" + GUEST_ENTRANCE

        # ── 4. BUILD MESSAGE HISTORY ─────────────────────────────────────────
        # Use same window limits as regular chat.
        history_result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                # CONCLUSION EXCLUSION: distilled conclusion rows must NEVER enter
                # the LLM context window. message_kind is NOT NULL (default
                # 'standard'), so this filter is byte-equivalent to the prior
                # behaviour for all existing/standard/go_deeper rows.
                Message.message_kind != 'conclusion',
            )
            .order_by(Message.created_at.asc())
            .limit(MEMORY_WINDOW_PRO if user_plan in ("pro", "premium") else MEMORY_WINDOW_FREE)
        )
        history = history_result.scalars().all()
        # Cross-mind awareness: the guest responder sees the home persona and
        # any other brought-in personas as other minds. Label every assistant
        # turn not authored by the guest itself (persona_id None => home).
        _responder_id = target_db.id
        _foreign = [
            m for m in history
            if m.role == "assistant" and (m.persona_id or conv.persona_id) != _responder_id
        ]
        if _foreign:
            _pid_set = {conv.persona_id, _responder_id} | {m.persona_id for m in history if m.persona_id}
            _name_rows = await db.execute(
                select(Persona.id, Persona.name).where(Persona.id.in_(_pid_set))
            )
            _id_to_name = {r.id: r.name for r in _name_rows.all()}
            lm_messages = self._build_lm_messages(
                history, conv.persona_id, _responder_id, _id_to_name
            )
            system_prompt = system_prompt + "\n\n" + CROSS_MIND_NOTE
        else:
            lm_messages = [
                {"role": m.role, "content": m.content}
                for m in history
                if m.role in ("user", "assistant")
            ]
        # Strip leading assistant turns (same invariant as stream_response).
        while lm_messages and lm_messages[0]["role"] == "assistant":
            lm_messages.pop(0)
        # Strip trailing assistant turns so lm_messages ends at the last user
        # turn (the message the guest persona is responding to).
        while lm_messages and lm_messages[-1]["role"] == "assistant":
            lm_messages.pop()
        # Explicit guarantee: append last_user_text as the final turn.
        # Handles the window-cutoff case (MEMORY_WINDOW_FREE=5 may not reach the
        # most recent user message) and ensures recall/retrieval/lm_messages all
        # key off exactly the same text. Skip when no user message exists.
        if last_user_text and (not lm_messages or lm_messages[-1]["content"] != last_user_text):
            lm_messages.append({"role": "user", "content": last_user_text})

        # ── 5. STREAM FROM LLM ───────────────────────────────────────────────
        model = MODEL_PRO if user_plan in ("pro", "premium") else MODEL_FREE
        yield f"data: {json.dumps({'type': 'start', 'brought_in': True, 'persona_slug': persona.slug, 'persona_name': persona.name})}\n\n"

        _llm_success = False
        _last_llm_error: Exception | None = None
        _buf: list[str] = []
        _chunks_yielded = False

        for attempt in range(3):
            _buf = []
            _chunks_yielded = False
            try:
                async for chunk in llm_client.stream(
                    system=system_prompt, messages=lm_messages, model=model
                ):
                    _buf.append(chunk)
                    _chunks_yielded = True
                    yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
                _llm_success = True
                break
            except anthropic.RateLimitError as exc:
                _last_llm_error = exc
                if _chunks_yielded:
                    break
                await asyncio.sleep(2**attempt)
            except anthropic.APIStatusError as exc:
                _last_llm_error = exc
                if _chunks_yielded or exc.status_code < 500:
                    break
                await asyncio.sleep(2**attempt)
            except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
                _last_llm_error = exc
                if _chunks_yielded:
                    break
                await asyncio.sleep(2**attempt)

        if not _llm_success:
            persona_voice_text = get_error_voice(persona, "llm_unavailable")
            error_event = {
                "type": "error",
                "error_code": "llm_unavailable",
                "persona_voice": persona_voice_text,
            }
            logger.error(f"LLM stream failed (another_mind) for persona={persona.slug}: {_last_llm_error}")
            yield f"data: {json.dumps(error_event)}\n\n"
            await db.commit()
            return

        full_response = "".join(_buf)

        # ── 6. PERSIST ASSISTANT MESSAGE WITH TARGET PERSONA ID ───────────────
        assistant_msg = await self._save_message(
            db, conv, user_id, "assistant", full_response,
            retrieval_ids=[str(p.id) for p in passages],
            persona_id=target_db.id,
        )
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                message_count=Conversation.message_count + 1,
                last_message_at=assistant_msg.created_at,
            )
        )
        await db.commit()

        yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id})}\n\n"

    # ── Stream go deeper ─────────────────────────────────────────────────────
    async def stream_go_deeper(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        user_plan: str = "free",
        user_name: str | None = None,
        is_admin: bool = False,
        arq_queue=None,
    ) -> AsyncGenerator[str, None]:
        # Load conversation
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise ValueError("Conversation not found")

        # Resolve responder (sticky active guest when set, else home persona).
        responder_persona_id = conv.active_persona_id or conv.persona_id
        home_result = await db.execute(select(Persona).where(Persona.id == responder_persona_id))
        target_db = home_result.scalar_one()
        persona = get_persona(target_db.slug)

        # ── LIMIT ENFORCEMENT ────────────────────────────────────────────────
        thread_result = await db.execute(
            select(func.count()).select_from(Message).where(
                Message.conversation_id == conv.id,
                Message.message_kind == 'go_deeper',
            )
        )
        thread_count = thread_result.scalar()

        last_std_result = await db.execute(
            select(func.max(Message.created_at)).where(
                Message.conversation_id == conv.id,
                Message.role == 'assistant',
                Message.message_kind == 'standard',
            )
        )
        last_std_at = last_std_result.scalar()

        turn_filter = [
            Message.conversation_id == conv.id,
            Message.message_kind == 'go_deeper',
        ]
        if last_std_at:
            turn_filter.append(Message.created_at > last_std_at)
        turn_result = await db.execute(
            select(func.count()).select_from(Message).where(*turn_filter)
        )
        turn_count = turn_result.scalar()

        tier = user_plan if user_plan in ('pro', 'premium') else 'free'
        if thread_count >= THREAD_LIMIT[tier]:
            yield f"data: {json.dumps({'type': 'limit', 'scope': 'thread', 'tier': tier})}\n\n"
            return
        if turn_count >= TURN_LIMIT[tier]:
            yield f"data: {json.dumps({'type': 'limit', 'scope': 'turn', 'tier': tier})}\n\n"
            return
        level = turn_count + 1

        # FREE DAILY GO-DEEPER LIMIT — the conversion gate (Pro/premium unlimited).
        # Keyed on the conversation's HOME persona (conv.persona_id), NOT the
        # resolved responder: otherwise a free user could reset the bucket by
        # switching sticky guests (~3/persona × N personas/day). Keying on the
        # immutable home makes the limit stable per conversation. Per (user, home
        # persona, day); secondary to the per-conversation / per-turn caps above.
        # Skipped for admins and ritual conversations, matching the message gate.
        if not is_admin and conv.ritual_id is None:
            gd_limit = await rate_limit_service.check_go_deeper_limit(
                db, UUID(user_id), UUID(conv.persona_id), user_tier=tier
            )
            if not gd_limit.allowed:
                yield f"data: {json.dumps({'type': 'limit', 'scope': 'daily', 'tier': tier})}\n\n"
                return

        # Fetch the most recent user message — used for memory/retrieval queries
        # and as the final user turn the guest responds to.
        last_user_result = await db.execute(
            select(Message.content)
            .where(Message.conversation_id == conversation_id, Message.role == "user")
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_user_text: str = last_user_result.scalar_one_or_none() or ""

        # ── 1. RECALL MEMORY ─────────────────────────────────────────────────
        memories = []
        try:
            memories = await memory_service.recall(db, user_id, last_user_text, top_k=6)
        except Exception as e:
            logger.warning(f"Memory recall failed (go_deeper): {e}")
            await db.rollback()

        # ── 2. RETRIEVE PASSAGES (target persona) ────────────────────────────
        passages = []
        try:
            passages = await retrieval_service.retrieve(db, last_user_text, persona)
        except Exception as e:
            logger.warning(f"Retrieval failed (go_deeper): {e}")
            await db.rollback()

        # ── 3. BUILD SYSTEM PROMPT (target persona) ──────────────────────────
        system_prompt = prompt_builder.build_system(
            persona=persona,
            memories=memories,
            passages=passages,
        )
        system_prompt = system_prompt + "\n\n" + _deepen_directive(persona) + DEEPEN_ESCALATION.get(level, "")

        # ── 4. BUILD MESSAGE HISTORY ─────────────────────────────────────────
        # Use same window limits as regular chat.
        history_result = await db.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                # CONCLUSION EXCLUSION: distilled conclusion rows must NEVER enter
                # the LLM context window. message_kind is NOT NULL (default
                # 'standard'), so this filter is byte-equivalent to the prior
                # behaviour for all existing/standard/go_deeper rows.
                Message.message_kind != 'conclusion',
            )
            .order_by(Message.created_at.asc())
            .limit(MEMORY_WINDOW_PRO if user_plan in ("pro", "premium") else MEMORY_WINDOW_FREE)
        )
        history = history_result.scalars().all()
        # Cross-mind awareness: the guest responder sees the home persona and
        # any other brought-in personas as other minds. Label every assistant
        # turn not authored by the guest itself (persona_id None => home).
        _responder_id = target_db.id
        _foreign = [
            m for m in history
            if m.role == "assistant" and (m.persona_id or conv.persona_id) != _responder_id
        ]
        if _foreign:
            _pid_set = {conv.persona_id, _responder_id} | {m.persona_id for m in history if m.persona_id}
            _name_rows = await db.execute(
                select(Persona.id, Persona.name).where(Persona.id.in_(_pid_set))
            )
            _id_to_name = {r.id: r.name for r in _name_rows.all()}
            lm_messages = self._build_lm_messages(
                history, conv.persona_id, _responder_id, _id_to_name
            )
            system_prompt = system_prompt + "\n\n" + CROSS_MIND_NOTE
        else:
            lm_messages = [
                {"role": m.role, "content": m.content}
                for m in history
                if m.role in ("user", "assistant")
            ]
        # Strip leading assistant turns (same invariant as stream_response).
        while lm_messages and lm_messages[0]["role"] == "assistant":
            lm_messages.pop(0)
        # Strip trailing assistant turns so lm_messages ends at the last user
        # turn (the message the guest persona is responding to).
        while lm_messages and lm_messages[-1]["role"] == "assistant":
            lm_messages.pop()
        # Explicit guarantee: append last_user_text as the final turn.
        # Handles the window-cutoff case (MEMORY_WINDOW_FREE=5 may not reach the
        # most recent user message) and ensures recall/retrieval/lm_messages all
        # key off exactly the same text. Skip when no user message exists.
        if last_user_text and (not lm_messages or lm_messages[-1]["content"] != last_user_text):
            lm_messages.append({"role": "user", "content": last_user_text})

        # ── 5. STREAM FROM LLM ───────────────────────────────────────────────
        model = MODEL_PRO if user_plan in ("pro", "premium") else MODEL_FREE
        yield f"data: {json.dumps({'type': 'start', 'deepen': True, 'persona_slug': persona.slug, 'persona_name': persona.name})}\n\n"

        _llm_success = False
        _last_llm_error: Exception | None = None
        _buf: list[str] = []
        _chunks_yielded = False

        for attempt in range(3):
            _buf = []
            _chunks_yielded = False
            try:
                async for chunk in llm_client.stream(
                    system=system_prompt, messages=lm_messages, model=model
                ):
                    _buf.append(chunk)
                    _chunks_yielded = True
                    yield f"data: {json.dumps({'type': 'chunk', 'data': chunk})}\n\n"
                _llm_success = True
                break
            except anthropic.RateLimitError as exc:
                _last_llm_error = exc
                if _chunks_yielded:
                    break
                await asyncio.sleep(2**attempt)
            except anthropic.APIStatusError as exc:
                _last_llm_error = exc
                if _chunks_yielded or exc.status_code < 500:
                    break
                await asyncio.sleep(2**attempt)
            except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
                _last_llm_error = exc
                if _chunks_yielded:
                    break
                await asyncio.sleep(2**attempt)

        if not _llm_success:
            persona_voice_text = get_error_voice(persona, "llm_unavailable")
            error_event = {
                "type": "error",
                "error_code": "llm_unavailable",
                "persona_voice": persona_voice_text,
            }
            logger.error(f"LLM stream failed (go_deeper) for persona={persona.slug}: {_last_llm_error}")
            yield f"data: {json.dumps(error_event)}\n\n"
            await db.commit()
            return

        full_response = "".join(_buf)

        # ── 6. PERSIST ASSISTANT MESSAGE WITH TARGET PERSONA ID ───────────────
        assistant_msg = await self._save_message(
            db, conv, user_id, "assistant", full_response,
            retrieval_ids=[str(p.id) for p in passages],
            persona_id=target_db.id,
            message_kind='go_deeper',
        )
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                message_count=Conversation.message_count + 1,
                last_message_at=assistant_msg.created_at,
            )
        )

        # Consume one daily go-deeper for the free-tier limit. Keyed on the HOME
        # persona (conv.persona_id) — same bucket as the check above, so switching
        # sticky guests cannot reset the limit. Reached only on a successful
        # generation (a mid-stream failure returns earlier, before this), so a
        # failed go-deeper never consumes the user's daily allowance. Skipped for
        # admins and ritual conversations, matching the check.
        if not is_admin and conv.ritual_id is None:
            today = date.today()
            gd_usage_result = await db.execute(
                select(DailyUsage).where(
                    DailyUsage.user_id == user_id,
                    DailyUsage.persona_id == conv.persona_id,
                    DailyUsage.usage_date == today,
                )
            )
            gd_usage = gd_usage_result.scalar_one_or_none()
            if gd_usage:
                gd_usage.go_deeper_count += 1
            else:
                db.add(DailyUsage(
                    user_id=user_id,
                    persona_id=conv.persona_id,
                    usage_date=today,
                    go_deeper_count=1,
                ))

        await db.commit()

        yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_msg.id})}\n\n"

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _build_lm_messages(self, history, home_persona_id, responder_persona_id, id_to_name):
        """Build the LLM message list, labelling assistant turns spoken by a
        mind other than the responder as "[Name]: ...". The responder's own
        turns and all user turns pass through unchanged. A turn's author is its
        persona_id, or the home persona when persona_id is None."""
        out = []
        for m in history:
            if m.role not in ("user", "assistant"):
                continue
            if m.role == "assistant":
                author_id = m.persona_id or home_persona_id
                if author_id != responder_persona_id:
                    name = id_to_name.get(author_id)
                    if name:
                        out.append({"role": "assistant", "content": f"[{name}]: {m.content}"})
                        continue
            out.append({"role": m.role, "content": m.content})
        return out

    async def _save_message(
        self, db, conv, user_id, role, content,
        retrieval_ids=None, safety_level="none",
        persona_override=False, latency_ms=None,
        persona_id=None, message_kind: str = 'standard',
    ) -> Message:
        msg = Message(
            conversation_id=conv.id,
            user_id=user_id,
            role=role,
            content=content,
            retrieval_ids=retrieval_ids,
            safety_level=safety_level,
            persona_override=persona_override,
            latency_ms=latency_ms,
            persona_id=persona_id,
            message_kind=message_kind,
        )
        db.add(msg)
        await db.flush()
        return msg

    async def _log_safety_event(self, db, user_id, conversation_id, message_id, safety_result, stage):
        event = SafetyEvent(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            trigger_stage=stage,
            risk_level=safety_result.level,
            category=safety_result.category,
            action_taken="suppressed" if safety_result.should_suppress_persona else "logged",
            raw_flags={"flags": safety_result.raw_flags, "trigger": safety_result.trigger},
        )
        db.add(event)
        await db.flush()

    def _chunk_text(self, text: str, size: int = 20):
        """Split text into small chunks for SSE simulation."""
        for i in range(0, len(text), size):
            yield text[i:i+size]


conversation_service = ConversationService()
