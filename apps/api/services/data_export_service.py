"""Data export — GDPR Art. 15 (access) and Art. 20 (portability).

The privacy policy §7 has promised both since #577. #588 delivered erasure; this
delivers the other half. A right named in a legal document with nothing behind
it is the same defect class, and it fails the same way: silently, until the
first person asks.

WHAT THIS ANSWERS. "What do you hold about me, in a form I can take elsewhere."
So it is deliberately generous about inclusion and deliberately strict about
three things:

  NO EMBEDDINGS. memory_entries.embedding is a 1536-dimension vector — 21,504
  bytes of JSON per row. For a user with 800 memories that is 17 MB, roughly
  double the entire rest of the export, and it is machine state rather than
  anything the person wrote or would recognise.

  NO INTERNAL TELEMETRY. Token counts, latencies, model ids, retrieval ids.
  These are facts about our infrastructure that happen to be stored next to the
  user's words; they are not the user's data and they are not portable.

  NO OTHER-PARTY LEDGERS. stripe_events and subscription_events are Stripe's
  record of what was billed; safety_events is an audit trail that #588
  ANONYMISES on deletion — exporting it would hand back the very thing deletion
  is designed to sever. disclaimer_acceptances keeps its consent record but
  drops ip_address and user_agent for the same reason: security audit trail,
  answerable on individual request, not by bulk download.

SOFT-DELETED ROWS ARE INCLUDED, with deleted_at populated. We still hold them,
so an export that omitted them would be answering a different question than the
one asked. The header block says so in a line the reader will see, because a
"deleted" conversation reappearing in a download is otherwise a surprise.

IDS. Rows carry the ids needed to JOIN them (a message's conversation_id, a
saved line's message_id) and nothing else. Persona, ritual and quote references
are resolved to slugs and text at export time, because `persona_id` is a UUID
that means nothing outside this database and the point of portability is that
the file survives leaving it.

SIZE. Synchronous by design: measured against production, the heaviest real
user holds 380 messages and 68KB of content. The guard in the router exists for
the shape of the problem rather than its current size — messages dominate the
payload, and the failure mode without a guard is a hung request rather than an
error anyone can act on.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Conversation,
    CouncilCase,
    CouncilResponse,
    CouncilSave,
    CouncilSession,
    Counterview,
    CounterviewResponse,
    CounterviewSave,
    CounterviewTurn,
    DailyUsage,
    DisclaimerAcceptance,
    DisclaimerVersion,
    Insight,
    MemoryEntry,
    Message,
    Mirror,
    MirrorSave,
    Persona,
    Quote,
    Ritual,
    SavedLine,
    SavedQuote,
    ScheduledEmail,
    SelfComparison,
    SelfComparisonSave,
    Subscription,
    User,
    UserPreference,
    UserRitualCompletion,
    WeeklyLetter,
)

logger = logging.getLogger(__name__)

# Bumped only when the SHAPE changes in a way a consumer would have to handle.
# Adding a field is not a break; renaming, removing or re-nesting one is.
SCHEMA_VERSION = 1


def _iso(value: Optional[datetime]) -> Optional[str]:
    """UTC ISO-8601 with an explicit Z. None passes through.

    Rows written before a column was timezone-aware can come back naive; those
    are treated as UTC rather than dropped, because every writer in this
    codebase uses datetime.now(timezone.utc) and a naive value is a storage
    artefact, not a different instant.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def _scalars(db: AsyncSession, stmt) -> list:
    return list((await db.execute(stmt)).scalars().all())


async def build_export(db: AsyncSession, user: User) -> dict[str, Any]:
    """Assemble the complete export for one user.

    One pass per table, filtered by user_id. No joins beyond the lookup maps,
    because the row counts are small and a readable query per section is worth
    more here than a clever one.
    """
    user_id = user.id

    # ── Lookup maps: UUID -> human-meaningful identifier ──────────────────────
    # Loaded once. personas and rituals are small fixed tables (tens of rows).
    persona_slug = {
        p.id: p.slug for p in await _scalars(db, select(Persona))
    }
    ritual_slug = {
        r.id: r.slug for r in await _scalars(db, select(Ritual))
    }

    # ── Profile ──────────────────────────────────────────────────────────────
    profile: dict[str, Any] = {
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "auth_provider": user.auth_provider,
        "onboarded_at": _iso(user.onboarded_at),
        "weekly_email_opt_out": user.weekly_email_opt_out,
        "created_at": _iso(user.created_at),
    }

    pref = (await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )).scalar_one_or_none()
    preferences = None
    if pref is not None:
        # `profile` JSONB carries the onboarding pills AND the self-portrait quiz
        # answers (services/preferences_service.py). portrait_cache is a derived
        # render cache and is excluded.
        preferences = {
            "themes": pref.themes,
            "other_text": pref.other_text,
            "need_most": pref.need_most,
            "profile": pref.profile,
            "created_at": _iso(pref.created_at),
            "updated_at": _iso(pref.updated_at),
        }

    # ── Subscription summary (no Stripe internals) ───────────────────────────
    sub = (await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )).scalar_one_or_none()
    subscription = None
    if sub is not None:
        subscription = {
            "plan": sub.plan,
            "status": sub.status,
            "interval": sub.interval,
            "current_period_end": _iso(sub.current_period_end),
            "cancel_at_period_end": sub.cancel_at_period_end,
            "pro_since": _iso(sub.pro_since),
        }

    # ── Conversations and messages ───────────────────────────────────────────
    conversations = [
        {
            "id": c.id,
            "persona_slug": persona_slug.get(c.persona_id),
            "title": c.title,
            "message_count": c.message_count,
            "deep_mode": c.deep_mode,
            "last_message_at": _iso(c.last_message_at),
            "created_at": _iso(c.created_at),
            "deleted_at": _iso(c.deleted_at),
        }
        for c in await _scalars(
            db, select(Conversation).where(Conversation.user_id == user_id)
                .order_by(Conversation.created_at)
        )
    ]

    messages = [
        {
            "id": m.id,
            "conversation_id": m.conversation_id,
            "role": m.role,
            "content": m.content,
            "persona_slug": persona_slug.get(m.persona_id),
            "message_kind": m.message_kind,
            "safety_level": m.safety_level,
            "created_at": _iso(m.created_at),
        }
        for m in await _scalars(
            db, select(Message).where(Message.user_id == user_id)
                .order_by(Message.created_at)
        )
    ]

    # ── Memory and insights ──────────────────────────────────────────────────
    # NOTE the absence of `embedding`. See the module docstring; a test asserts
    # no float vector reaches the output.
    memories = [
        {
            "id": me.id,
            "entry_type": me.entry_type,
            "content": me.content,
            "confidence": me.confidence,
            "is_active": me.is_active,
            "conversation_id": me.conversation_id,
            "created_at": _iso(me.created_at),
        }
        for me in await _scalars(
            db, select(MemoryEntry).where(MemoryEntry.user_id == user_id)
                .order_by(MemoryEntry.created_at)
        )
    ]

    insights = [
        {
            "id": i.id,
            "content": i.content,
            "insight_type": i.insight_type,
            "theme": i.theme,
            "is_dismissed": i.is_dismissed,
            "conversation_id": i.conversation_id,
            "created_at": _iso(i.created_at),
        }
        for i in await _scalars(
            db, select(Insight).where(Insight.user_id == user_id)
                .order_by(Insight.created_at)
        )
    ]

    # ── Letters, mirrors, self-comparisons ───────────────────────────────────
    letters = [
        {
            "period_start": _iso(w.period_start),
            "period_end": _iso(w.period_end),
            "kind": w.kind,
            "status": w.status,
            "payload": w.payload,
            "voice_persona_slug": persona_slug.get(w.voice_persona_id),
            "read_at": _iso(w.read_at),
            "write_back_text": w.write_back_text,
            "write_back_at": _iso(w.write_back_at),
            "created_at": _iso(w.created_at),
        }
        for w in await _scalars(
            db, select(WeeklyLetter).where(WeeklyLetter.user_id == user_id)
                .order_by(WeeklyLetter.created_at)
        )
    ]

    mirrors = [
        {
            "id": m.id,
            "period_start": _iso(m.period_start),
            "period_end": _iso(m.period_end),
            "kind": m.kind,
            "status": m.status,
            "payload": m.payload,
            "host_persona_slug": persona_slug.get(m.host_persona_id),
            "ring_true": m.ring_true,
            "ring_true_note": m.ring_true_note,
            "ring_true_at": _iso(m.ring_true_at),
            "created_at": _iso(m.created_at),
        }
        for m in await _scalars(
            db, select(Mirror).where(Mirror.user_id == user_id)
                .order_by(Mirror.created_at)
        )
    ]

    self_comparisons = [
        {
            "id": s.id,
            "prompt": s.prompt,
            "then_start": _iso(s.then_start),
            "then_end": _iso(s.then_end),
            "now_start": _iso(s.now_start),
            "now_end": _iso(s.now_end),
            "payload": s.payload,
            "status": s.status,
            "ring_true": s.ring_true,
            "ring_true_note": s.ring_true_note,
            "created_at": _iso(s.created_at),
        }
        for s in await _scalars(
            db, select(SelfComparison).where(SelfComparison.user_id == user_id)
                .order_by(SelfComparison.created_at)
        )
    ]

    # ── Counterviews, with responses and turns nested ────────────────────────
    cv_rows = await _scalars(
        db, select(Counterview).where(Counterview.user_id == user_id)
            .order_by(Counterview.created_at)
    )
    cv_ids = [c.id for c in cv_rows]
    cv_responses: dict[str, list] = {i: [] for i in cv_ids}
    cv_turns: dict[str, list] = {i: [] for i in cv_ids}
    if cv_ids:
        for r in await _scalars(
            db, select(CounterviewResponse)
                .where(CounterviewResponse.counterview_id.in_(cv_ids))
                .order_by(CounterviewResponse.created_at)
        ):
            cv_responses[r.counterview_id].append({
                "persona_slug": r.persona_slug,
                "round": r.round,
                "position": r.position,
                "verdict": r.verdict,
                "created_at": _iso(r.created_at),
            })
        for t in await _scalars(
            db, select(CounterviewTurn)
                .where(CounterviewTurn.counterview_id.in_(cv_ids))
                .order_by(CounterviewTurn.sequence)
        ):
            cv_turns[t.counterview_id].append({
                "sequence": t.sequence,
                "persona_slug": t.persona_slug,
                "user_text": t.user_text,
                "persona_response": t.persona_response,
                "status": t.status,
                "created_at": _iso(t.created_at),
            })

    counterviews = [
        {
            "id": c.id,
            "source": c.source,
            "anchor_text": c.anchor_text,
            "status": c.status,
            "still_stands": c.still_stands,
            "title": c.title,
            "created_at": _iso(c.created_at),
            "responses": cv_responses.get(c.id, []),
            "turns": cv_turns.get(c.id, []),
        }
        for c in cv_rows
    ]

    # ── Council, with sessions and responses nested ──────────────────────────
    case_rows = await _scalars(
        db, select(CouncilCase).where(CouncilCase.user_id == user_id)
            .order_by(CouncilCase.created_at)
    )
    case_ids = [c.id for c in case_rows]
    sessions_by_case: dict[str, list] = {i: [] for i in case_ids}
    if case_ids:
        session_rows = await _scalars(
            db, select(CouncilSession)
                .where(CouncilSession.case_id.in_(case_ids))
                .order_by(CouncilSession.session_number)
        )
        session_ids = [s.id for s in session_rows]
        responses_by_session: dict[str, list] = {i: [] for i in session_ids}
        if session_ids:
            for r in await _scalars(
                db, select(CouncilResponse)
                    .where(CouncilResponse.session_id.in_(session_ids))
                    .order_by(CouncilResponse.created_at)
            ):
                responses_by_session[r.session_id].append({
                    "persona_slug": r.persona_slug,
                    "position": r.position,
                    "verdict": r.verdict,
                    "quote": r.quote,
                    "quote_source": r.quote_source,
                })
        for s in session_rows:
            sessions_by_case[s.case_id].append({
                "session_number": s.session_number,
                "input_text": s.input_text,
                "synthesis": s.synthesis,
                "synthesis_structured": s.synthesis_structured,
                "matter_edited": s.matter_edited,
                "status": s.status,
                "created_at": _iso(s.created_at),
                "responses": responses_by_session.get(s.id, []),
            })

    council_cases = [
        {
            "id": c.id,
            "source": c.source,
            "status": c.status,
            "session_count": c.session_count,
            "created_at": _iso(c.created_at),
            "closed_at": _iso(c.closed_at),
            "sessions": sessions_by_case.get(c.id, []),
        }
        for c in case_rows
    ]

    # ── Saved things ─────────────────────────────────────────────────────────
    saved_lines = [
        {
            "message_id": s.message_id,
            "persona_slug": persona_slug.get(s.persona_id),
            "source_type": s.source_type,
            "saved_at": _iso(s.saved_at),
            "deleted_at": _iso(s.deleted_at),
        }
        for s in await _scalars(
            db, select(SavedLine).where(SavedLine.user_id == user_id)
                .order_by(SavedLine.saved_at)
        )
    ]

    sq_rows = await _scalars(
        db, select(SavedQuote).where(SavedQuote.user_id == user_id)
            .order_by(SavedQuote.saved_at)
    )
    quote_text: dict[str, Quote] = {}
    if sq_rows:
        quote_text = {
            q.id: q for q in await _scalars(
                db, select(Quote).where(Quote.id.in_([s.quote_id for s in sq_rows]))
            )
        }
    saved_quotes = []
    for s in sq_rows:
        q = quote_text.get(s.quote_id)
        saved_quotes.append({
            # The quote TEXT, not just its id: a bare UUID means nothing once the
            # file leaves this database, which is the whole point of portability.
            "quote_text": q.text_en if q else None,
            "quote_text_original": q.text_original if q else None,
            "persona_slug": q.persona_slug if q else None,
            "source_locator": q.source_locator if q else None,
            "saved_at": _iso(s.saved_at),
            "deleted_at": _iso(s.deleted_at),
        })

    def _simple_saves(rows, parent_attr: str, parent_key: str) -> list[dict]:
        return [
            {
                parent_key: getattr(r, parent_attr),
                "saved_at": _iso(r.saved_at),
                "deleted_at": _iso(r.deleted_at),
            }
            for r in rows
        ]

    mirror_saves = _simple_saves(
        await _scalars(db, select(MirrorSave).where(MirrorSave.user_id == user_id)),
        "mirror_id", "mirror_id",
    )
    council_saves = _simple_saves(
        await _scalars(db, select(CouncilSave).where(CouncilSave.user_id == user_id)),
        "session_id", "council_session_id",
    )
    counterview_saves = _simple_saves(
        await _scalars(db, select(CounterviewSave).where(CounterviewSave.user_id == user_id)),
        "counterview_id", "counterview_id",
    )
    self_comparison_saves = _simple_saves(
        await _scalars(db, select(SelfComparisonSave).where(SelfComparisonSave.user_id == user_id)),
        "self_comparison_id", "self_comparison_id",
    )

    # ── Scheduled (future-self) emails ───────────────────────────────────────
    scheduled_emails = [
        {
            "note": s.note,
            "recipient_email": s.recipient_email,
            "scheduled_for": _iso(s.scheduled_for),
            "status": s.status,
            "sent_at": _iso(s.sent_at),
            "prediction": s.prediction,
            "review_text": s.review_text,
            "review_at": _iso(s.review_at),
            "created_at": _iso(s.created_at),
        }
        for s in await _scalars(
            db, select(ScheduledEmail).where(ScheduledEmail.user_id == user_id)
                .order_by(ScheduledEmail.created_at)
        )
    ]

    # ── Ritual completions and usage ─────────────────────────────────────────
    ritual_completions = [
        {
            "ritual_slug": ritual_slug.get(r.ritual_id),
            "conversation_id": r.conversation_id,
            "completed_at": _iso(r.completed_at),
        }
        for r in await _scalars(
            db, select(UserRitualCompletion)
                .where(UserRitualCompletion.user_id == user_id)
                .order_by(UserRitualCompletion.completed_at)
        )
    ]

    daily_usage = [
        {
            "usage_date": d.usage_date.isoformat() if d.usage_date else None,
            "persona_slug": persona_slug.get(d.persona_id),
            "message_count": d.message_count,
            "go_deeper_count": d.go_deeper_count,
            "deep_mode_count": d.deep_mode_count,
        }
        for d in await _scalars(
            db, select(DailyUsage).where(DailyUsage.user_id == user_id)
                .order_by(DailyUsage.usage_date)
        )
    ]

    # ── Disclaimer acceptances (consent record; NO ip/user-agent) ────────────
    da_rows = await _scalars(
        db, select(DisclaimerAcceptance)
            .where(DisclaimerAcceptance.user_id == user_id)
            .order_by(DisclaimerAcceptance.accepted_at)
    )
    version_string: dict[int, str] = {}
    if da_rows:
        version_string = {
            v.id: v.version_string for v in await _scalars(
                db, select(DisclaimerVersion)
                    .where(DisclaimerVersion.id.in_([d.version_id for d in da_rows]))
            )
        }
    disclaimer_acceptances = [
        {
            "version_string": version_string.get(d.version_id),
            "accepted_at": _iso(d.accepted_at),
            "locale": d.locale,
            "confirmed_age_18": d.confirmed_age_18,
            "confirmed_non_therapy": d.confirmed_non_therapy,
        }
        for d in da_rows
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": _iso(datetime.now(timezone.utc)),
        "user_id": user_id,
        # Stated inside the file because a "deleted" conversation reappearing in
        # a download is otherwise a surprise. We hold these rows until the
        # account is deleted, and the export answers what we hold.
        "records_marked_deleted_are_retained_until_account_deletion": True,
        "profile": profile,
        "preferences": preferences,
        "subscription": subscription,
        "conversations": conversations,
        "messages": messages,
        "memories": memories,
        "insights": insights,
        "letters": letters,
        "mirrors": mirrors,
        "self_comparisons": self_comparisons,
        "counterviews": counterviews,
        "council_cases": council_cases,
        "saved_lines": saved_lines,
        "saved_quotes": saved_quotes,
        "mirror_saves": mirror_saves,
        "council_saves": council_saves,
        "counterview_saves": counterview_saves,
        "self_comparison_saves": self_comparison_saves,
        "scheduled_emails": scheduled_emails,
        "ritual_completions": ritual_completions,
        "daily_usage": daily_usage,
        "disclaimer_acceptances": disclaimer_acceptances,
    }


async def count_messages(db: AsyncSession, user_id: str) -> int:
    """Row count used by the router's size guard, before anything is assembled."""
    from sqlalchemy import func
    return (await db.execute(
        select(func.count()).select_from(Message).where(Message.user_id == user_id)
    )).scalar_one()
