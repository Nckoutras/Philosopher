import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config import config
from db.session import AsyncSessionLocal
from services.email_service import send_email
from services.template_service import render_future_self_email

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def setup_cron(arq_queue):
    """
    Wire all recurring jobs. Call from FastAPI lifespan after arq pool is ready.
    All heavy work is delegated to ARQ workers — cron only enqueues.
    """

    @scheduler.scheduled_job(CronTrigger(hour=8, minute=0), id="daily_rituals")
    async def dispatch_ritual_reminders():
        """08:00 UTC — send ritual reminder emails to users with active rituals."""
        logger.info("Cron: dispatching ritual reminders")
        try:
            from db.session import AsyncSessionLocal
            from models import User, Subscription, UserRitualCompletion, Ritual
            from sqlalchemy import select, func
            from datetime import datetime, timezone, timedelta

            async with AsyncSessionLocal() as db:
                # Find users on pro+ who have done at least one ritual recently
                yesterday = datetime.now(timezone.utc) - timedelta(hours=36)
                result = await db.execute(
                    select(
                        UserRitualCompletion.user_id,
                        UserRitualCompletion.ritual_id,
                        func.max(UserRitualCompletion.completed_at).label("last_done"),
                    )
                    .join(Subscription, Subscription.user_id == UserRitualCompletion.user_id)
                    .where(
                        Subscription.plan != "free",
                        Subscription.status.in_(["active", "trialing"]),
                    )
                    .group_by(UserRitualCompletion.user_id, UserRitualCompletion.ritual_id)
                    .having(func.max(UserRitualCompletion.completed_at) >= yesterday)
                )
                rows = result.all()

            dispatched = 0
            for row in rows:
                await arq_queue.enqueue_job(
                    "send_ritual_reminder_task",
                    str(row.user_id),
                    str(row.ritual_id),
                )
                dispatched += 1

            logger.info(f"Cron: dispatched {dispatched} ritual reminders")
        except Exception as e:
            logger.error(f"Cron ritual reminders failed: {e}", exc_info=True)

    @scheduler.scheduled_job(CronTrigger(day_of_week="sun", hour=3, minute=0), id="stale_memory")
    async def deactivate_stale_memories():
        """Sunday 03:00 UTC — prune low-confidence memories older than 90 days."""
        logger.info("Cron: pruning stale memories")
        try:
            from db.session import AsyncSessionLocal
            from models import MemoryEntry
            from sqlalchemy import update
            from datetime import datetime, timezone, timedelta

            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    update(MemoryEntry)
                    .where(
                        MemoryEntry.created_at < cutoff,
                        MemoryEntry.confidence < 0.6,
                        MemoryEntry.is_active == True,
                    )
                    .values(is_active=False)
                    .returning(MemoryEntry.id)
                )
                deactivated = len(result.fetchall())
                await db.commit()
            logger.info(f"Cron: deactivated {deactivated} stale memory entries")
        except Exception as e:
            logger.error(f"Cron stale memory failed: {e}", exc_info=True)

    @scheduler.scheduled_job(IntervalTrigger(hours=6), id="stripe_reconcile")
    async def reconcile_stripe_subscriptions():
        """Every 6h — catch any Stripe events the webhook may have missed."""
        logger.info("Cron: reconciling Stripe subscriptions")
        try:
            import stripe
            from db.session import AsyncSessionLocal
            from models import Subscription
            from sqlalchemy import select
            from config import config
            from datetime import datetime, timezone

            stripe.api_key = config.STRIPE_SECRET_KEY
            if not config.STRIPE_SECRET_KEY:
                return

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Subscription).where(
                        Subscription.stripe_subscription_id.isnot(None),
                        Subscription.status.in_(["active", "trialing", "past_due"]),
                    )
                )
                subs = result.scalars().all()

                updated = 0
                for sub in subs:
                    try:
                        stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
                        if stripe_sub.status != sub.status:
                            sub.status = stripe_sub.status
                            updated += 1
                    except stripe.error.InvalidRequestError:
                        sub.status = "canceled"
                        sub.plan = "free"
                        updated += 1

                if updated:
                    await db.commit()
                    logger.info(f"Cron: reconciled {updated} subscriptions")
        except Exception as e:
            logger.error(f"Cron Stripe reconcile failed: {e}", exc_info=True)

    @scheduler.scheduled_job(IntervalTrigger(minutes=5), id="future_self_emails")
    async def send_pending_future_self_emails():
        """Every 5 min — deliver scheduled_emails WHERE scheduled_for <= NOW() AND status='pending'.

        Per-row try/except ensures one send failure does not block the rest.
        strftime('%-d') is Linux-only (no zero-padding); this runs on Render (Linux).
        """
        from models import ScheduledEmail, Persona, SavedLine, Message
        from sqlalchemy import select
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ScheduledEmail)
                .where(
                    ScheduledEmail.status == "pending",
                    ScheduledEmail.scheduled_for <= datetime.now(timezone.utc),
                )
                .order_by(ScheduledEmail.scheduled_for.asc())  # oldest due first (M2)
                .limit(50)
            )
            rows = result.scalars().all()

            for row in rows:
                try:
                    persona = await db.get(Persona, row.persona_id)
                    if persona is None:
                        raise ValueError(f"Persona {row.persona_id} not found")

                    # Prefix relative portrait paths with PUBLIC_ASSET_BASE_URL (Q1)
                    portrait_url = persona.portrait_url or ""
                    if portrait_url and not portrait_url.startswith("http"):
                        portrait_url = (
                            config.PUBLIC_ASSET_BASE_URL.rstrip("/")
                            + "/"
                            + portrait_url.lstrip("/")
                        )

                    # Load saved line message content (optional — may be NULL if line deleted)
                    quote_content = None
                    if row.saved_line_id:
                        sl_result = await db.execute(
                            select(Message.content)
                            .join(SavedLine, SavedLine.message_id == Message.id)
                            .where(SavedLine.id == row.saved_line_id)
                        )
                        quote_content = sl_result.scalar_one_or_none()

                    scheduled_display = (
                        f"{row.scheduled_for.strftime('%B')} {row.scheduled_for.day}, {row.scheduled_for.year}"
                    )
                    subject = f"A letter from {persona.name} — {scheduled_display}"
                    html = render_future_self_email(
                        persona_name=persona.name,
                        persona_portrait_url=portrait_url,
                        quote_content=quote_content,
                        note=row.note,
                        scheduled_for_display=scheduled_display,
                        public_base_url=config.PUBLIC_ASSET_BASE_URL,
                    )
                    send_email(to=row.recipient_email, subject=subject, html=html)
                    row.status = "sent"
                    row.sent_at = datetime.now(timezone.utc)
                    logger.info("Sent future-self email id=%s", row.id)
                except Exception as exc:
                    row.status = "failed"
                    row.failure_reason = str(exc)[:500]
                    logger.error(
                        "Failed to send future-self email id=%s: %s", row.id, exc, exc_info=True
                    )

            await db.commit()

    @scheduler.scheduled_job(CronTrigger(day_of_week="mon", hour=6, minute=0), id="weekly_mirror")
    async def dispatch_weekly_mirrors():
        """Monday 06:00 UTC — enqueue a weekly mirror for users with >=5 user messages in the last 7 days."""
        logger.info("Cron: dispatching weekly mirrors")
        try:
            from db.session import AsyncSessionLocal
            from models import Message, Conversation, User
            from sqlalchemy import select, func
            from datetime import datetime, timezone, timedelta

            DEFAULT_HOST = "carl_jung"
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Conversation.user_id, User.mirror_host_slug)
                    .join(Message, Message.conversation_id == Conversation.id)
                    .join(User, User.id == Conversation.user_id)
                    .where(Message.role == "user", Message.created_at >= cutoff)
                    .group_by(Conversation.user_id, User.mirror_host_slug)
                    .having(func.count(Message.id) >= 5)
                )
                rows = result.all()

            for row in rows:
                host = row.mirror_host_slug or DEFAULT_HOST
                await arq_queue.enqueue_job("generate_weekly_mirror_task", str(row.user_id), host, "weekly", 7)
            logger.info(f"Cron: enqueued {len(rows)} weekly mirrors")
        except Exception as e:
            logger.error(f"Cron weekly mirrors failed: {e}", exc_info=True)

    @scheduler.scheduled_job(IntervalTrigger(hours=1), id="preview_mirror")
    async def dispatch_preview_mirrors():
        """Hourly — give a one-time preview mirror to users with >=3 active chats in 72h who have no mirror yet."""
        logger.info("Cron: dispatching preview mirrors")
        try:
            from db.session import AsyncSessionLocal
            from models import Conversation, Mirror
            from sqlalchemy import select, func, distinct
            from datetime import datetime, timezone, timedelta

            DEFAULT_HOST = "carl_jung"
            cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
            async with AsyncSessionLocal() as db:
                eligible = await db.execute(
                    select(Conversation.user_id)
                    .where(Conversation.deleted_at.is_(None), Conversation.last_message_at >= cutoff)
                    .group_by(Conversation.user_id)
                    .having(func.count(distinct(Conversation.id)) >= 3)
                )
                candidate_ids = [r[0] for r in eligible.all()]
                if not candidate_ids:
                    logger.info("Cron: no preview-eligible users")
                    return
                existing = await db.execute(
                    select(distinct(Mirror.user_id)).where(Mirror.user_id.in_(candidate_ids))
                )
                have_mirror = {r[0] for r in existing.all()}
                targets = [uid for uid in candidate_ids if uid not in have_mirror]

            for uid in targets:
                await arq_queue.enqueue_job("generate_weekly_mirror_task", str(uid), DEFAULT_HOST, "preview", 3)
            logger.info(f"Cron: enqueued {len(targets)} preview mirrors")
        except Exception as e:
            logger.error(f"Cron preview mirrors failed: {e}", exc_info=True)

    scheduler.start()
    logger.info("Cron scheduler started with 6 jobs")


def shutdown_cron():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Cron scheduler stopped")
