"""
Recompute monthly / weekly summary rows for a single user + period.

Called from:
  - BackgroundTasks after every transaction create / update / delete
  - Nightly scheduler as a safety net
"""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, func, case
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from models.transaction import Transaction
from models.monthly_summary import MonthlySummary
from models.weekly_summary import WeeklySummary

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


# ── helpers ──────────────────────────────────────────────────────────

def week_start_for(d: date) -> date:
    """Monday of the calendar week containing *d*."""
    return d - timedelta(days=d.weekday())


def _ist_to_naive_utc(dt: datetime) -> datetime:
    """Convert an IST-aware datetime to a naive UTC datetime (for DB comparison)."""
    from datetime import timezone
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


# ── core aggregation ─────────────────────────────────────────────────

def _aggregate(db: Session, user_id: int, start: datetime, end: datetime) -> dict:
    """
    Aggregate transactions for a user within [start, end).
    Both boundaries should be naive-UTC datetimes matching how txn_timestamp is stored.
    """
    base_filter = [
        Transaction.user_id == user_id,
        Transaction.txn_timestamp >= start,
        Transaction.txn_timestamp < end,
    ]

    # totals
    totals = db.execute(
        select(
            func.coalesce(func.sum(case((Transaction.txn_type == "debit", Transaction.amount), else_=0)), 0),
            func.coalesce(func.sum(case((Transaction.txn_type == "credit", Transaction.amount), else_=0)), 0),
            func.count(Transaction.id),
        ).where(*base_filter)
    ).first()
    total_spent, total_credit, txn_count = totals

    # category breakdown (debits only)
    category_rows = db.execute(
        select(Transaction.category_id, func.sum(Transaction.amount))
        .where(*base_filter, Transaction.txn_type == "debit")
        .group_by(Transaction.category_id)
    ).all()
    category_breakdown = {
        str(cid) if cid else "uncategorized": float(amt)
        for cid, amt in category_rows
    }

    # app breakdown (debits only)
    app_rows = db.execute(
        select(Transaction.upi_app, func.sum(Transaction.amount))
        .where(*base_filter, Transaction.txn_type == "debit")
        .group_by(Transaction.upi_app)
    ).all()
    app_breakdown = {
        (app or "unknown"): float(amt)
        for app, amt in app_rows
    }

    # source breakdown (debits only)
    source_rows = db.execute(
        select(Transaction.source, func.sum(Transaction.amount))
        .where(*base_filter, Transaction.txn_type == "debit")
        .group_by(Transaction.source)
    ).all()
    source_breakdown = {src: float(amt) for src, amt in source_rows}

    return {
        "total_spent": float(total_spent),
        "total_credit": float(total_credit),
        "txn_count": int(txn_count),
        "category_breakdown": category_breakdown,
        "app_breakdown": app_breakdown,
        "source_breakdown": source_breakdown,
    }


# ── recompute functions ──────────────────────────────────────────────

def recompute_month(db: Session, user_id: int, year: int, month: int):
    """Recompute and upsert the monthly summary for one user + month."""
    # IST-anchored boundaries → naive UTC for DB queries
    start_ist = datetime(year, month, 1, tzinfo=IST)
    if month == 12:
        end_ist = datetime(year + 1, 1, 1, tzinfo=IST)
    else:
        end_ist = datetime(year, month + 1, 1, tzinfo=IST)

    start_utc = _ist_to_naive_utc(start_ist)
    end_utc = _ist_to_naive_utc(end_ist)

    agg = _aggregate(db, user_id, start_utc, end_utc)

    stmt = mysql_insert(MonthlySummary).values(
        user_id=user_id,
        year=year,
        month=month,
        total_spent=agg["total_spent"],
        total_credit=agg["total_credit"],
        category_breakdown=agg["category_breakdown"],
        app_breakdown=agg["app_breakdown"],
        source_breakdown=agg["source_breakdown"],
        txn_count=agg["txn_count"],
    )
    stmt = stmt.on_duplicate_key_update(
        total_spent=stmt.inserted.total_spent,
        total_credit=stmt.inserted.total_credit,
        category_breakdown=stmt.inserted.category_breakdown,
        app_breakdown=stmt.inserted.app_breakdown,
        source_breakdown=stmt.inserted.source_breakdown,
        txn_count=stmt.inserted.txn_count,
    )
    db.execute(stmt)
    db.commit()
    logger.info("Recomputed monthly summary: user=%s year=%s month=%s", user_id, year, month)


def recompute_week(db: Session, user_id: int, ws: date):
    """Recompute and upsert the weekly summary for one user + week."""
    # IST-anchored boundaries → naive UTC
    start_ist = datetime.combine(ws, datetime.min.time(), tzinfo=IST)
    end_ist = start_ist + timedelta(days=7)

    start_utc = _ist_to_naive_utc(start_ist)
    end_utc = _ist_to_naive_utc(end_ist)

    agg = _aggregate(db, user_id, start_utc, end_utc)

    stmt = mysql_insert(WeeklySummary).values(
        user_id=user_id,
        week_start=ws,
        total_spent=agg["total_spent"],
        app_breakdown=agg["app_breakdown"],
        source_breakdown=agg["source_breakdown"],
        txn_count=agg["txn_count"],
    )
    stmt = stmt.on_duplicate_key_update(
        total_spent=stmt.inserted.total_spent,
        app_breakdown=stmt.inserted.app_breakdown,
        source_breakdown=stmt.inserted.source_breakdown,
        txn_count=stmt.inserted.txn_count,
    )
    db.execute(stmt)
    db.commit()
    logger.info("Recomputed weekly summary: user=%s week_start=%s", user_id, ws)


# ── convenience: recompute both for a given transaction date ─────────

def recompute_for_date(db: Session, user_id: int, txn_dt: datetime):
    """Recompute both month + week summaries that contain txn_dt (IST-based)."""
    ist_dt = txn_dt.replace(tzinfo=None) if txn_dt.tzinfo is None else txn_dt
    # Convert to IST to get the right calendar month/week
    if ist_dt.tzinfo is None:
        # Stored as naive UTC → convert to IST
        from datetime import timezone
        ist_dt = ist_dt.replace(tzinfo=timezone.utc).astimezone(IST)

    recompute_month(db, user_id, ist_dt.year, ist_dt.month)
    recompute_week(db, user_id, week_start_for(ist_dt.date()))
