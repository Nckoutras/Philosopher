from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import SavedLine, Message, Conversation, Persona
import services.tier_service as tier_service

FREE_SAVE_LIMIT = 3


class FreeSavesLimitError(Exception):
    def __init__(self, limit: int, current_count: int):
        self.limit = limit
        self.current_count = current_count
        super().__init__(f"Free tier save limit of {limit} reached")


class SavedLineNotFoundError(Exception):
    pass


class MessageNotFoundError(Exception):
    pass


class MessageRoleError(Exception):
    pass


class SavedLineAlreadyExistsError(Exception):
    pass


class SavedLinesService:

    async def count_active(self, db: AsyncSession, user_id: str) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(SavedLine)
            .where(SavedLine.user_id == user_id)
            .where(SavedLine.deleted_at.is_(None))
        )
        return result.scalar_one()

    async def create(self, db: AsyncSession, user_id: str, message_id: str) -> SavedLine:
        # 1. Load message and verify ownership
        msg_result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = msg_result.scalar_one_or_none()
        if message is None or message.user_id != user_id:
            raise MessageNotFoundError()

        # 2. Validate role — defense-in-depth; UI only shows Save on assistant bubbles
        if message.role != "assistant":
            raise MessageRoleError()

        # 3. Load conversation, verify ownership (defense-in-depth), get persona_id
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == message.conversation_id)
        )
        conversation = conv_result.scalar_one_or_none()
        if conversation is None or conversation.user_id != user_id:
            raise MessageNotFoundError()

        # 4. Check for existing active save
        existing_result = await db.execute(
            select(SavedLine)
            .where(SavedLine.user_id == user_id)
            .where(SavedLine.message_id == message_id)
            .where(SavedLine.deleted_at.is_(None))
        )
        if existing_result.scalar_one_or_none() is not None:
            raise SavedLineAlreadyExistsError()

        # 5. Free-tier limit check (pro users skip the count query entirely)
        tier = await tier_service.get_user_tier(db, UUID(user_id))
        if tier == "free":
            count = await self.count_active(db, user_id)
            if count >= FREE_SAVE_LIMIT:
                raise FreeSavesLimitError(limit=FREE_SAVE_LIMIT, current_count=count)

        # 6. Create — set saved_at Python-side so it's accessible after commit
        saved_line = SavedLine(
            user_id=user_id,
            message_id=message_id,
            persona_id=conversation.persona_id,
            source_type="manual_save",
            saved_at=datetime.now(timezone.utc),
        )
        db.add(saved_line)
        await db.flush()
        await db.commit()
        return saved_line

    async def list_for_user(
        self,
        db: AsyncSession,
        user_id: str,
        persona_id: str | None = None,
    ) -> list[dict]:
        query = (
            select(
                SavedLine.id,
                SavedLine.message_id,
                SavedLine.persona_id,
                SavedLine.source_type,
                SavedLine.saved_at,
                Message.content.label("message_content"),
                Message.conversation_id,
                Persona.slug.label("persona_slug"),
                Persona.name.label("persona_display_name"),
            )
            .join(Message, SavedLine.message_id == Message.id)
            .join(Persona, SavedLine.persona_id == Persona.id)
            .where(SavedLine.user_id == user_id)
            .where(SavedLine.deleted_at.is_(None))
            .order_by(SavedLine.saved_at.desc())
        )
        if persona_id is not None:
            query = query.where(SavedLine.persona_id == persona_id)

        result = await db.execute(query)
        return [row._asdict() for row in result.all()]

    async def delete(self, db: AsyncSession, user_id: str, saved_line_id: str) -> None:
        result = await db.execute(
            select(SavedLine)
            .where(SavedLine.id == saved_line_id)
            .where(SavedLine.user_id == user_id)
            .where(SavedLine.deleted_at.is_(None))
        )
        saved_line = result.scalar_one_or_none()
        if saved_line is None:
            raise SavedLineNotFoundError()
        saved_line.deleted_at = datetime.now(timezone.utc)
        await db.commit()


saved_lines_service = SavedLinesService()
