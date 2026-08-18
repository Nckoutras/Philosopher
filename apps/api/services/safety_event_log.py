"""One writer for SafetyEvent rows, usable from any surface (A18b).

Until now SafetyEvent had exactly one writer — ConversationService._log_safety_event —
so the table recorded chat and nothing else. Every ritual surface ran safety checks and
acted on them (council, counterview, you-vs-you, future-self all suppress correctly) but
left no operator record at all. A user in distress who works only in rituals was
protected and invisible at the same time.

The body here is character-for-character what the chat writer did; only its shape
changed. `self` was unused, and conversation_id / message_id were pass-throughs into
columns already declared nullable, so nothing about it was ever chat-specific.

Persistence: db.add + flush, never commit — the caller owns the transaction. In request
paths get_db commits on successful teardown (db/session.py); worker tasks commit
explicitly. This is the same contract the chat writer has always relied on.

This module RECORDS. It never decides. No caller's suppression behaviour changes by
adding a call to it.
"""
from models import SafetyEvent

# trigger_stage vocabulary (String(50), no CHECK constraint).
#
# Chat's two values describe WHEN in a generation cycle. Ritual surfaces need to say
# WHICH surface as well, because one person can trip safety in four places in a week and
# an operator has to tell them apart. The {surface}_input shape keeps GROUP BY
# trigger_stage legible and leaves the chat values untouched so existing rows keep their
# meaning.
#
# INPUT SIDE ONLY, deliberately: the record answers "what did this person write", not
# "what did a persona nearly say". The six check_output sites stay unlogged.
STAGE_COUNCIL_INPUT              = "council_input"
STAGE_COUNTERVIEW_INPUT          = "counterview_input"
STAGE_COUNTERVIEW_REBUTTAL_INPUT = "counterview_rebuttal_input"
STAGE_SELF_COMPARISON_INPUT      = "self_comparison_input"
STAGE_SCHEDULED_EMAIL_INPUT      = "scheduled_email_input"


async def log_safety_event(
    db,
    user_id,
    safety_result,
    stage,
    *,
    conversation_id=None,
    message_id=None,
) -> None:
    """Record one safety check. Callers gate on `safety_result.should_log`.

    conversation_id and message_id default to None so a ritual surface — which has
    neither — writes a valid row without inventing anything. Both columns are nullable
    on the model and carry no CHECK constraint.
    """
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
