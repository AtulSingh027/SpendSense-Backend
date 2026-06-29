"""
Tests for services/summary_service.py

Validates:
  - recompute_month upserts correct totals, category/app/source breakdowns
  - recompute_week upserts correct weekly totals
  - recompute_for_date convenience helper hits both month + week
  - Upsert idempotency (calling twice doesn't duplicate rows)
  - Credits vs debits handled correctly
  - Empty period produces zeroed-out summary rows
  - User isolation (user A's data doesn't leak into user B's summary)
  - week_start_for returns the correct Monday
"""

import random
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from configs.db_config import SessionLocal
from models.category import Category
from models.monthly_summary import MonthlySummary
from models.transaction import Transaction
from models.user import User
from models.weekly_summary import WeeklySummary
from services.summary_service import (
    recompute_for_date,
    recompute_month,
    recompute_week,
    week_start_for,
)

IST = ZoneInfo("Asia/Kolkata")


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user_a(db):
    """Create a test user and clean up all their data after the test."""
    phone = f"+91{random.randint(1000000000, 9999999999)}"
    user = User(phone_number=phone, password_hash="fakehash", full_name="Test User A")
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user

    # Cleanup: transactions → summaries → categories → user
    db.query(Transaction).filter(Transaction.user_id == user.id).delete()
    db.query(MonthlySummary).filter(MonthlySummary.user_id == user.id).delete()
    db.query(WeeklySummary).filter(WeeklySummary.user_id == user.id).delete()
    db.query(Category).filter(Category.user_id == user.id).delete()
    db.delete(user)
    db.commit()


@pytest.fixture
def user_b(db):
    """Second user for isolation tests."""
    phone = f"+91{random.randint(1000000000, 9999999999)}"
    user = User(phone_number=phone, password_hash="fakehash", full_name="Test User B")
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user

    db.query(Transaction).filter(Transaction.user_id == user.id).delete()
    db.query(MonthlySummary).filter(MonthlySummary.user_id == user.id).delete()
    db.query(WeeklySummary).filter(WeeklySummary.user_id == user.id).delete()
    db.delete(user)
    db.commit()


def _ist_to_utc_naive(dt: datetime) -> datetime:
    """Helper: IST-aware datetime → naive UTC (matching DB storage)."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _make_txn(user_id, amount, txn_type, source, timestamp_utc, category_id=None, upi_app=None):
    """Helper to build a Transaction object."""
    return Transaction(
        user_id=user_id,
        amount=amount,
        txn_type=txn_type,
        source=source,
        txn_timestamp=timestamp_utc,
        category_id=category_id,
        upi_app=upi_app,
    )


# ── week_start_for ──────────────────────────────────────────────────

class TestWeekStartFor:
    def test_monday_returns_itself(self):
        monday = date(2026, 6, 29)  # a Monday
        assert monday.weekday() == 0
        assert week_start_for(monday) == monday

    def test_sunday_returns_previous_monday(self):
        sunday = date(2026, 7, 5)  # a Sunday
        assert sunday.weekday() == 6
        assert week_start_for(sunday) == date(2026, 6, 29)

    def test_wednesday(self):
        wednesday = date(2026, 7, 1)
        assert wednesday.weekday() == 2
        assert week_start_for(wednesday) == date(2026, 6, 29)


# ── recompute_month ─────────────────────────────────────────────────

class TestRecomputeMonth:
    def test_basic_monthly_totals(self, db, user_a):
        """Debits summed in total_spent, credits in total_credit, count correct."""
        ts = _ist_to_utc_naive(datetime(2026, 6, 15, 14, 0, tzinfo=IST))

        db.add_all([
            _make_txn(user_a.id, 500.00, "debit", "manual", ts),
            _make_txn(user_a.id, 300.00, "debit", "sms", ts, upi_app="PhonePe"),
            _make_txn(user_a.id, 2000.00, "credit", "manual", ts),
        ])
        db.commit()

        recompute_month(db, user_a.id, 2026, 6)

        row = db.query(MonthlySummary).filter_by(user_id=user_a.id, year=2026, month=6).first()
        assert row is not None
        assert float(row.total_spent) == 800.00
        assert float(row.total_credit) == 2000.00
        assert row.txn_count == 3

    def test_category_breakdown(self, db, user_a):
        """category_breakdown JSON contains per-category debit sums."""
        cat = Category(user_id=user_a.id, name="Food")
        db.add(cat)
        db.commit()

        ts = _ist_to_utc_naive(datetime(2026, 6, 10, 10, 0, tzinfo=IST))

        db.add_all([
            _make_txn(user_a.id, 200.00, "debit", "manual", ts, category_id=cat.id),
            _make_txn(user_a.id, 150.00, "debit", "manual", ts, category_id=cat.id),
            _make_txn(user_a.id, 400.00, "debit", "manual", ts),  # uncategorized
        ])
        db.commit()

        recompute_month(db, user_a.id, 2026, 6)

        row = db.query(MonthlySummary).filter_by(user_id=user_a.id, year=2026, month=6).first()
        assert row.category_breakdown[str(cat.id)] == 350.00
        assert row.category_breakdown["uncategorized"] == 400.00

    def test_app_and_source_breakdown(self, db, user_a):
        """app_breakdown and source_breakdown contain correct debit sums."""
        ts = _ist_to_utc_naive(datetime(2026, 6, 20, 12, 0, tzinfo=IST))

        db.add_all([
            _make_txn(user_a.id, 100.00, "debit", "sms", ts, upi_app="GPay"),
            _make_txn(user_a.id, 250.00, "debit", "sms", ts, upi_app="PhonePe"),
            _make_txn(user_a.id, 75.00, "debit", "manual", ts),
        ])
        db.commit()

        recompute_month(db, user_a.id, 2026, 6)

        row = db.query(MonthlySummary).filter_by(user_id=user_a.id, year=2026, month=6).first()
        assert row.app_breakdown["GPay"] == 100.00
        assert row.app_breakdown["PhonePe"] == 250.00
        assert row.source_breakdown["sms"] == 350.00
        assert row.source_breakdown["manual"] == 75.00

    def test_upsert_idempotency(self, db, user_a):
        """Calling recompute_month twice doesn't create duplicate rows."""
        ts = _ist_to_utc_naive(datetime(2026, 6, 5, 9, 0, tzinfo=IST))
        db.add(_make_txn(user_a.id, 100.00, "debit", "manual", ts))
        db.commit()

        recompute_month(db, user_a.id, 2026, 6)
        recompute_month(db, user_a.id, 2026, 6)

        count = db.query(MonthlySummary).filter_by(user_id=user_a.id, year=2026, month=6).count()
        assert count == 1

    def test_upsert_updates_on_change(self, db, user_a):
        """Adding a new transaction and recomputing updates the existing row."""
        ts = _ist_to_utc_naive(datetime(2026, 6, 5, 9, 0, tzinfo=IST))
        db.add(_make_txn(user_a.id, 100.00, "debit", "manual", ts))
        db.commit()
        recompute_month(db, user_a.id, 2026, 6)

        row = db.query(MonthlySummary).filter_by(user_id=user_a.id, year=2026, month=6).first()
        assert float(row.total_spent) == 100.00

        # Add another transaction and recompute
        db.add(_make_txn(user_a.id, 250.00, "debit", "sms", ts, upi_app="GPay"))
        db.commit()
        recompute_month(db, user_a.id, 2026, 6)

        db.refresh(row)
        assert float(row.total_spent) == 350.00
        assert row.txn_count == 2

    def test_empty_month(self, db, user_a):
        """Recomputing a month with no transactions produces zeroed-out row."""
        recompute_month(db, user_a.id, 2026, 1)

        row = db.query(MonthlySummary).filter_by(user_id=user_a.id, year=2026, month=1).first()
        assert row is not None
        assert float(row.total_spent) == 0.00
        assert float(row.total_credit) == 0.00
        assert row.txn_count == 0

    def test_december_boundary(self, db, user_a):
        """Month 12 doesn't crash (year rollover edge case)."""
        ts = _ist_to_utc_naive(datetime(2026, 12, 25, 10, 0, tzinfo=IST))
        db.add(_make_txn(user_a.id, 999.00, "debit", "manual", ts))
        db.commit()

        recompute_month(db, user_a.id, 2026, 12)

        row = db.query(MonthlySummary).filter_by(user_id=user_a.id, year=2026, month=12).first()
        assert float(row.total_spent) == 999.00


# ── recompute_week ──────────────────────────────────────────────────

class TestRecomputeWeek:
    def test_basic_weekly_totals(self, db, user_a):
        """Weekly summary captures total_spent and txn_count for debits."""
        ws = date(2026, 6, 29)  # Monday
        ts = _ist_to_utc_naive(datetime(2026, 7, 1, 10, 0, tzinfo=IST))  # Wednesday in that week

        db.add_all([
            _make_txn(user_a.id, 200.00, "debit", "manual", ts),
            _make_txn(user_a.id, 300.00, "debit", "sms", ts, upi_app="GPay"),
            _make_txn(user_a.id, 1000.00, "credit", "manual", ts),  # ignored in total_spent
        ])
        db.commit()

        recompute_week(db, user_a.id, ws)

        row = db.query(WeeklySummary).filter_by(user_id=user_a.id, week_start=ws).first()
        assert row is not None
        assert float(row.total_spent) == 500.00
        assert row.txn_count == 3  # all transactions counted

    def test_weekly_app_and_source_breakdown(self, db, user_a):
        ws = date(2026, 6, 29)
        ts = _ist_to_utc_naive(datetime(2026, 6, 30, 14, 0, tzinfo=IST))

        db.add_all([
            _make_txn(user_a.id, 400.00, "debit", "sms", ts, upi_app="PhonePe"),
            _make_txn(user_a.id, 100.00, "debit", "manual", ts),
        ])
        db.commit()

        recompute_week(db, user_a.id, ws)

        row = db.query(WeeklySummary).filter_by(user_id=user_a.id, week_start=ws).first()
        assert row.app_breakdown["PhonePe"] == 400.00
        assert row.source_breakdown["sms"] == 400.00
        assert row.source_breakdown["manual"] == 100.00

    def test_weekly_upsert_idempotency(self, db, user_a):
        ws = date(2026, 6, 29)
        ts = _ist_to_utc_naive(datetime(2026, 6, 30, 10, 0, tzinfo=IST))
        db.add(_make_txn(user_a.id, 50.00, "debit", "manual", ts))
        db.commit()

        recompute_week(db, user_a.id, ws)
        recompute_week(db, user_a.id, ws)

        count = db.query(WeeklySummary).filter_by(user_id=user_a.id, week_start=ws).count()
        assert count == 1

    def test_empty_week(self, db, user_a):
        ws = date(2026, 1, 5)
        recompute_week(db, user_a.id, ws)

        row = db.query(WeeklySummary).filter_by(user_id=user_a.id, week_start=ws).first()
        assert row is not None
        assert float(row.total_spent) == 0.00
        assert row.txn_count == 0


# ── recompute_for_date ──────────────────────────────────────────────

class TestRecomputeForDate:
    def test_recomputes_both_month_and_week(self, db, user_a):
        """recompute_for_date creates/updates both monthly and weekly rows."""
        ts_utc = _ist_to_utc_naive(datetime(2026, 6, 15, 14, 0, tzinfo=IST))

        db.add(_make_txn(user_a.id, 750.00, "debit", "manual", ts_utc))
        db.commit()

        recompute_for_date(db, user_a.id, ts_utc)

        month_row = db.query(MonthlySummary).filter_by(
            user_id=user_a.id, year=2026, month=6
        ).first()
        assert month_row is not None
        assert float(month_row.total_spent) == 750.00

        expected_ws = week_start_for(date(2026, 6, 15))
        week_row = db.query(WeeklySummary).filter_by(
            user_id=user_a.id, week_start=expected_ws
        ).first()
        assert week_row is not None
        assert float(week_row.total_spent) == 750.00


# ── User isolation ──────────────────────────────────────────────────

class TestUserIsolation:
    def test_user_a_data_does_not_appear_in_user_b_summary(self, db, user_a, user_b):
        ts = _ist_to_utc_naive(datetime(2026, 6, 15, 10, 0, tzinfo=IST))

        db.add(_make_txn(user_a.id, 500.00, "debit", "manual", ts))
        db.add(_make_txn(user_b.id, 200.00, "debit", "sms", ts, upi_app="GPay"))
        db.commit()

        recompute_month(db, user_a.id, 2026, 6)
        recompute_month(db, user_b.id, 2026, 6)

        row_a = db.query(MonthlySummary).filter_by(user_id=user_a.id, year=2026, month=6).first()
        row_b = db.query(MonthlySummary).filter_by(user_id=user_b.id, year=2026, month=6).first()

        assert float(row_a.total_spent) == 500.00
        assert float(row_b.total_spent) == 200.00

    def test_weekly_user_isolation(self, db, user_a, user_b):
        ws = date(2026, 6, 29)
        ts = _ist_to_utc_naive(datetime(2026, 6, 30, 10, 0, tzinfo=IST))

        db.add(_make_txn(user_a.id, 800.00, "debit", "manual", ts))
        db.add(_make_txn(user_b.id, 120.00, "debit", "manual", ts))
        db.commit()

        recompute_week(db, user_a.id, ws)
        recompute_week(db, user_b.id, ws)

        row_a = db.query(WeeklySummary).filter_by(user_id=user_a.id, week_start=ws).first()
        row_b = db.query(WeeklySummary).filter_by(user_id=user_b.id, week_start=ws).first()

        assert float(row_a.total_spent) == 800.00
        assert float(row_b.total_spent) == 120.00
