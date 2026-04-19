import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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
                await arq_queue.enqueue(
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

    scheduler.start()
    logger.info("Cron scheduler started with 3 jobs")


def shutdown_cron():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Cron scheduler stopped")
