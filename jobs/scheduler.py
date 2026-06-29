"""
Nightly safety-net scheduler.

Recomputes current month + current week summaries for every user at 2 AM IST.
Catches any drift from failed BackgroundTasks (server restart, DB hiccup, etc.).
"""

import logging
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from configs.db_config import SessionLocal
from models.user import User
from services.summary_service import recompute_month, recompute_week, week_start_for

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def _nightly_recompute():
    """Recompute current month + week for all users."""
    db = SessionLocal()
    try:
        today_ist = datetime.now(IST).date()
        user_ids = db.execute(select(User.id)).scalars().all()

        for uid in user_ids:
            try:
                recompute_month(db, uid, today_ist.year, today_ist.month)
                recompute_week(db, uid, week_start_for(today_ist))
            except Exception:
                logger.exception("Nightly recompute failed for user_id=%s", uid)
                db.rollback()
    finally:
        db.close()

    logger.info("Nightly summary recompute finished for %d user(s)", len(user_ids))


# ── scheduler instance ──────────────────────────────────────────────

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(
    _nightly_recompute,
    trigger="cron",
    hour=2,
    minute=0,
    timezone=IST,
    id="nightly_summary_recompute",
    replace_existing=True,
)


def start_scheduler():
    """Call once at app startup."""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started — nightly recompute job scheduled at 02:00 IST")
