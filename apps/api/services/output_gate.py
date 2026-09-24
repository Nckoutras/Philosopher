"""The post-generation safety gate for non-streamed output — one function, eleven callers.

Chat, another-mind and go-deeper run safety_service.check_output on every reply
(TD-101). Until 2026-09-24 eleven other generators ran nothing: letters, mirrors, the
portrait summary, conclusions, titles, insights, the forming reflection, Council
members and You-vs-You. The last two are streamed, so the text has already been on
screen when this runs (TD-102); they use it for the check and the record, and
answer with a safety_override event exactly as TD-101's chat paths do.

WHAT THIS DOES. Checks the text, and on a positive records a safety_events row
(trigger_stage = the caller's `stage`) and logs a warning carrying ids only, never
content. Returns the SafetyResult (truthy), and the CALLER decides what "not shown" means for its surface
(founder ruling 2026-09-24): a letter or mirror is stored as status='suppressed', the
portrait keeps its previous summary, a conclusion or insight is not written, a title
falls back to the library's default, a forming reflection hides. Never a visible
crisis message in place of the text — a title replaced by a crisis message is worse
than a default title.

`value` may be a string or a parsed JSON payload: every string anywhere inside it is
checked, joined, so a letter is checked across all of its fields at once.

The row is added with flush, never commit: the caller owns the transaction, the same
contract as safety_event_log.log_safety_event.
"""
import logging

from services.safety_event_log import log_safety_event
from services.safety_service import safety_service

logger = logging.getLogger(__name__)


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in _strings(v)]
    return []


async def output_is_unsafe(db, value, *, user_id, stage: str, conversation_id=None):
    """The SafetyResult when this generated output must not be shown, else None.

    Truthy exactly when the caller must withhold, so `if await output_is_unsafe(...)`
    reads as it should; the streamed callers use the result's level in their
    safety_override event. `db` may be None only for a caller with no session in
    reach: the warning is still logged, the row is not written.
    """
    text = "\n".join(s for s in _strings(value) if s.strip())
    if not text:
        return None
    result = await safety_service.check_output(text)
    if not result.should_suppress_persona:
        return None
    logger.warning(
        "post_gen_output_suppressed",
        extra={
            "stage": stage,
            "safety_level": result.level,
            "user_id": str(user_id) if user_id else None,
            "conversation_id": str(conversation_id) if conversation_id else None,
        },
    )
    if db is not None:
        await log_safety_event(db, user_id, result, stage, conversation_id=conversation_id)
    return result
