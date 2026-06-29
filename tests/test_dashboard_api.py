import random
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient

from app import app
from configs.db_config import SessionLocal
from models.transaction import Transaction
from models.category import Category
from models.user import User

client = TestClient(app)
IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user_1(db_session):
    """Creates user 1, returns token headers and user ID."""
    rand_phone = f"+91{random.randint(1000000000, 9999999999)}"
    password = "Password123"

    reg_res = client.post(
        "/api/v1/auth/register",
        json={"phone_number": rand_phone, "password": password, "full_name": "User One"},
    )
    assert reg_res.status_code == 201
    auth_data = reg_res.json()
    token = auth_data["access_token"]
    user_id = auth_data["user"]["id"]

    headers = {"Authorization": f"Bearer {token}"}
    yield headers, user_id

    # Cleanup
    user = db_session.get(User, user_id)
    if user:
        # Delete related transactions first
        db_session.query(Transaction).filter(Transaction.user_id == user_id).delete()
        db_session.delete(user)
        db_session.commit()


@pytest.fixture
def test_user_2(db_session):
    """Creates user 2, returns token headers and user ID."""
    rand_phone = f"+91{random.randint(1000000000, 9999999999)}"
    password = "Password123"

    reg_res = client.post(
        "/api/v1/auth/register",
        json={"phone_number": rand_phone, "password": password, "full_name": "User Two"},
    )
    assert reg_res.status_code == 201
    auth_data = reg_res.json()
    token = auth_data["access_token"]
    user_id = auth_data["user"]["id"]

    headers = {"Authorization": f"Bearer {token}"}
    yield headers, user_id

    # Cleanup
    user = db_session.get(User, user_id)
    if user:
        # Delete related transactions first
        db_session.query(Transaction).filter(Transaction.user_id == user_id).delete()
        db_session.delete(user)
        db_session.commit()


# ---------------------------------------------------------------------------
# Today Endpoint Tests
# ---------------------------------------------------------------------------

def test_dashboard_today_empty(test_user_1):
    headers, _ = test_user_1

    # Verify that a user with no transactions gets 0.00 spend and 0 count
    res = client.get("/api/v1/dashboard/today", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert float(data["total_amount"]) == 0.00
    assert data["count"] == 0
    assert float(data["difference"]) == 0.00
    assert data["diff_percent"] == 0.00
    assert data["is_higher"] is False


def test_dashboard_today_calculations(test_user_1, db_session):
    headers, uid_1 = test_user_1
    
    # Calculate target dates in IST
    now_ist = datetime.now(IST)
    yesterday_ist = now_ist - timedelta(days=1)
    
    now_utc_naive = now_ist.astimezone(timezone.utc).replace(tzinfo=None)
    yesterday_utc_naive = yesterday_ist.astimezone(timezone.utc).replace(tzinfo=None)

    # 1. Create debit txn today
    t1 = Transaction(
        user_id=uid_1,
        amount=150.50,
        txn_type="debit",
        merchant_raw="Starbucks",
        source="manual",
        txn_timestamp=now_utc_naive,
    )
    # 2. Create another debit txn today
    t2 = Transaction(
        user_id=uid_1,
        amount=300.00,
        txn_type="debit",
        merchant_raw="Airtel",
        source="manual",
        txn_timestamp=now_utc_naive - timedelta(minutes=15),
    )
    # 3. Create credit txn today (should be ignored)
    t3 = Transaction(
        user_id=uid_1,
        amount=1000.00,
        txn_type="credit",
        merchant_raw="Salary Credit",
        source="manual",
        txn_timestamp=now_utc_naive,
    )
    # 4. Create debit txn from yesterday
    t4 = Transaction(
        user_id=uid_1,
        amount=500.00,
        txn_type="debit",
        merchant_raw="Amazon Old",
        source="manual",
        txn_timestamp=yesterday_utc_naive,
    )

    db_session.add_all([t1, t2, t3, t4])
    db_session.commit()

    # Query dashboard today
    res = client.get("/api/v1/dashboard/today", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Today: 150.50 + 300.00 = 450.50, count = 2
    # Yesterday: 500.00
    # Difference: 450.50 - 500.00 = -49.50
    # Percent change: abs(-49.50 / 500.00) * 100 = 9.9%
    # is_higher: False
    assert float(data["total_amount"]) == 450.50
    assert data["count"] == 2
    assert float(data["difference"]) == -49.50
    assert data["diff_percent"] == 9.9
    assert data["is_higher"] is False


def test_dashboard_today_zero_yesterday(test_user_1, db_session):
    headers, uid_1 = test_user_1
    now_ist = datetime.now(IST)
    now_utc_naive = now_ist.astimezone(timezone.utc).replace(tzinfo=None)

    # Create debit txn today
    t1 = Transaction(
        user_id=uid_1,
        amount=150.00,
        txn_type="debit",
        merchant_raw="Starbucks",
        source="manual",
        txn_timestamp=now_utc_naive,
    )

    db_session.add(t1)
    db_session.commit()

    # Query dashboard today
    res = client.get("/api/v1/dashboard/today", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Today: 150.00
    # Yesterday: 0.00
    # Difference: 150.00
    # Percent change: 100.0%
    # is_higher: True
    assert float(data["total_amount"]) == 150.00
    assert float(data["difference"]) == 150.00
    assert data["diff_percent"] == 100.0
    assert data["is_higher"] is True


# ---------------------------------------------------------------------------
# Month Endpoint Tests
# ---------------------------------------------------------------------------

def test_dashboard_month_empty(test_user_1):
    headers, _ = test_user_1

    # Verify that a user with no transactions gets 0.00 spend, 0 count, etc.
    res = client.get("/api/v1/dashboard/current-month", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert float(data["total_amount"]) == 0.00
    assert data["count"] == 0
    assert float(data["last_month_total"]) == 0.00
    assert float(data["difference"]) == 0.00
    assert data["diff_percent"] == 0.00
    assert data["is_higher"] is False


def test_dashboard_month_calculations(test_user_1, db_session):
    headers, uid_1 = test_user_1
    
    # Calculate dates in IST and convert to naive UTC
    now_ist = datetime.now(IST)
    
    start_this_month_ist = datetime(now_ist.year, now_ist.month, 1, 12, 0, 0, tzinfo=IST)
    start_this_month_utc = start_this_month_ist.astimezone(timezone.utc).replace(tzinfo=None)
    
    if now_ist.month == 1:
        prev_month = 12
        prev_year = now_ist.year - 1
    else:
        prev_month = now_ist.month - 1
        prev_year = now_ist.year
    date_prev_month_ist = datetime(prev_year, prev_month, 15, 12, 0, 0, tzinfo=IST)
    date_prev_month_utc = date_prev_month_ist.astimezone(timezone.utc).replace(tzinfo=None)

    # 1. Create debit txn this month (1500.00)
    t1 = Transaction(
        user_id=uid_1,
        amount=1500.00,
        txn_type="debit",
        merchant_raw="Rent",
        source="manual",
        txn_timestamp=start_this_month_utc,
    )
    # 2. Create another debit txn this month (500.00)
    t2 = Transaction(
        user_id=uid_1,
        amount=500.00,
        txn_type="debit",
        merchant_raw="Food",
        source="manual",
        txn_timestamp=start_this_month_utc + timedelta(hours=2),
    )
    # 3. Create credit txn this month (ignored)
    t3 = Transaction(
        user_id=uid_1,
        amount=4000.00,
        txn_type="credit",
        merchant_raw="Refund",
        source="manual",
        txn_timestamp=start_this_month_utc,
    )
    # 4. Create debit txn last month (2500.00)
    t4 = Transaction(
        user_id=uid_1,
        amount=2500.00,
        txn_type="debit",
        merchant_raw="Amazon Old",
        source="manual",
        txn_timestamp=date_prev_month_utc,
    )

    db_session.add_all([t1, t2, t3, t4])
    db_session.commit()

    # Query monthly spend
    res = client.get("/api/v1/dashboard/current-month", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # This Month: 1500.00 + 500.00 = 2000.00, count = 2
    # Last Month: 2500.00
    # Difference: 2000.00 - 2500.00 = -500.00
    # Percent change: abs(-500.00 / 2500.00) * 100 = 20.0%
    # is_higher: False
    assert float(data["total_amount"]) == 2000.00
    assert data["count"] == 2
    assert float(data["last_month_total"]) == 2500.00
    assert float(data["difference"]) == -500.00
    assert data["diff_percent"] == 20.0
    assert data["is_higher"] is False


def test_dashboard_month_zero_last_month(test_user_1, db_session):
    headers, uid_1 = test_user_1
    now_ist = datetime.now(IST)
    start_this_month_ist = datetime(now_ist.year, now_ist.month, 1, 12, 0, 0, tzinfo=IST)
    start_this_month_utc = start_this_month_ist.astimezone(timezone.utc).replace(tzinfo=None)

    # Create debit txn this month
    t1 = Transaction(
        user_id=uid_1,
        amount=600.00,
        txn_type="debit",
        merchant_raw="Shopping",
        source="manual",
        txn_timestamp=start_this_month_utc,
    )

    db_session.add(t1)
    db_session.commit()

    res = client.get("/api/v1/dashboard/current-month", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # This Month: 600.00
    # Last Month: 0.00
    # Difference: 600.00
    # Percent change: 100.0%
    # is_higher: True
    assert float(data["total_amount"]) == 600.00
    assert float(data["last_month_total"]) == 0.00
    assert float(data["difference"]) == 600.00
    assert data["diff_percent"] == 100.0
    assert data["is_higher"] is True


# ---------------------------------------------------------------------------
# Category Breakdown Endpoint Tests
# ---------------------------------------------------------------------------

def test_dashboard_breakdown_empty(test_user_1):
    headers, _ = test_user_1

    res = client.get("/api/v1/dashboard/breakdown", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert float(data["total_amount"]) == 0.00
    assert len(data["categories"]) == 0


def test_dashboard_breakdown_calculations(test_user_1, db_session):
    headers, uid_1 = test_user_1
    now_ist = datetime.now(IST)
    start_this_month_ist = datetime(now_ist.year, now_ist.month, 1, 12, 0, 0, tzinfo=IST)
    start_this_month_utc = start_this_month_ist.astimezone(timezone.utc).replace(tzinfo=None)

    # Create categories
    cat_food = Category(user_id=uid_1, name="Food")
    cat_travel = Category(user_id=uid_1, name="Travel")
    db_session.add_all([cat_food, cat_travel])
    db_session.commit()

    # 1. Debit in Food (5200.00)
    t1 = Transaction(
        user_id=uid_1,
        amount=5200.00,
        txn_type="debit",
        category_id=cat_food.id,
        txn_timestamp=start_this_month_utc,
        source="manual"
    )
    # 2. Debit in Travel (3100.00)
    t2 = Transaction(
        user_id=uid_1,
        amount=3100.00,
        txn_type="debit",
        category_id=cat_travel.id,
        txn_timestamp=start_this_month_utc + timedelta(hours=1),
        source="manual"
    )
    # 3. Uncategorized debit (2800.00)
    t3 = Transaction(
        user_id=uid_1,
        amount=2800.00,
        txn_type="debit",
        category_id=None,
        txn_timestamp=start_this_month_utc + timedelta(hours=2),
        source="manual"
    )
    # 4. Credit txn (should be ignored)
    t4 = Transaction(
        user_id=uid_1,
        amount=1000.00,
        txn_type="credit",
        category_id=cat_food.id,
        txn_timestamp=start_this_month_utc,
        source="manual"
    )

    db_session.add_all([t1, t2, t3, t4])
    db_session.commit()

    # Fetch breakdown
    res = client.get("/api/v1/dashboard/breakdown", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Total spend: 5200.00 + 3100.00 + 2800.00 = 11100.00
    assert float(data["total_amount"]) == 11100.00
    categories = data["categories"]
    assert len(categories) == 3

    # It's sorted descending by amount
    # Item 1: Food
    assert categories[0]["category_name"] == "Food"
    assert float(categories[0]["amount"]) == 5200.00
    # percentage: 5200.00 / 11100.00 * 100 = 46.85
    assert categories[0]["percentage"] == 46.85

    # Item 2: Travel
    assert categories[1]["category_name"] == "Travel"
    assert float(categories[1]["amount"]) == 3100.00
    # percentage: 3100.00 / 11100.00 * 100 = 27.93
    assert categories[1]["percentage"] == 27.93

    # Item 3: Uncategorized
    assert categories[2]["category_name"] == "Uncategorized"
    assert float(categories[2]["amount"]) == 2800.00
    # percentage: 2800.00 / 11100.00 * 100 = 25.23
    assert categories[2]["percentage"] == 25.23


# ---------------------------------------------------------------------------
# General Isolation and Auth Tests
# ---------------------------------------------------------------------------

def test_dashboard_today_isolation(test_user_1, test_user_2, db_session):
    headers_1, uid_1 = test_user_1
    headers_2, uid_2 = test_user_2
    now_ist = datetime.now(IST)
    now_utc_naive = now_ist.astimezone(timezone.utc).replace(tzinfo=None)

    # User 1 has 1 debit today
    t1 = Transaction(
        user_id=uid_1,
        amount=250.00,
        txn_type="debit",
        merchant_raw="GPay merchant",
        source="manual",
        txn_timestamp=now_utc_naive,
    )
    # User 2 has 1 debit today
    t2 = Transaction(
        user_id=uid_2,
        amount=600.00,
        txn_type="debit",
        merchant_raw="Uber rides",
        source="manual",
        txn_timestamp=now_utc_naive,
    )

    db_session.add_all([t1, t2])
    db_session.commit()

    # User 1 sees their own total (250.00)
    res1 = client.get("/api/v1/dashboard/today", headers=headers_1)
    assert res1.status_code == 200
    data1 = res1.json()
    assert float(data1["total_amount"]) == 250.00
    assert data1["count"] == 1

    # User 2 sees their own total (600.00)
    res2 = client.get("/api/v1/dashboard/today", headers=headers_2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert float(data2["total_amount"]) == 600.00
    assert data2["count"] == 1


def test_dashboard_today_unauthorized():
    # Requests without headers should be rejected with 401
    res = client.get("/api/v1/dashboard/today")
    assert res.status_code == 401

# ---------------------------------------------------------------------------
# UPI and Manual Spend Tests
# ---------------------------------------------------------------------------

def test_upi_manual_spend_calculations(test_user_1, db_session):
    headers, uid_1 = test_user_1
    now_ist = datetime.now(IST)
    now_utc_naive = now_ist.astimezone(timezone.utc).replace(tzinfo=None)

    # 1. Create upi transaction (source='sms')
    t1 = Transaction(
        user_id=uid_1,
        amount=840.00,
        txn_type="debit",
        merchant_raw="PhonePe merchant",
        source="sms",
        upi_app="PhonePe",
        txn_timestamp=now_utc_naive,
    )
    # 2. Create manual transaction (source='manual')
    t2 = Transaction(
        user_id=uid_1,
        amount=160.00,
        txn_type="debit",
        merchant_raw="Cash coffee",
        source="manual",
        txn_timestamp=now_utc_naive - timedelta(minutes=5),
    )
    # 3. Create credit transaction (should be ignored)
    t3 = Transaction(
        user_id=uid_1,
        amount=500.00,
        txn_type="credit",
        source="manual",
        txn_timestamp=now_utc_naive,
    )

    db_session.add_all([t1, t2, t3])
    db_session.commit()

    # Query for the current day
    res = client.get("/api/v1/dashboard/upi-manual-spend?filter_type=day", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert float(data["upi_spend"]) == 840.00
    assert float(data["manual_spend"]) == 160.00
    assert data["filter_type"] == "day"
    assert "period_start" in data
    assert "period_end" in data


# ---------------------------------------------------------------------------
# UPI App Breakdown Tests
# ---------------------------------------------------------------------------

def test_upi_apps_breakdown_calculations(test_user_1, db_session):
    headers, uid_1 = test_user_1
    now_ist = datetime.now(IST)
    now_utc_naive = now_ist.astimezone(timezone.utc).replace(tzinfo=None)

    # 1. PhonePe spend (source='sms', amount=4250.00)
    t1 = Transaction(
        user_id=uid_1,
        amount=4250.00,
        txn_type="debit",
        source="sms",
        upi_app="PhonePe",
        app_label_source="regex",
        txn_timestamp=now_utc_naive,
    )
    # 2. GPay spend (source='sms', amount=3100.00)
    t2 = Transaction(
        user_id=uid_1,
        amount=3100.00,
        txn_type="debit",
        source="sms",
        upi_app="GPay",
        app_label_source="regex",
        txn_timestamp=now_utc_naive - timedelta(minutes=10),
    )
    # 3. Unknown app spend (source='sms', upi_app=None, amount=1240.00)
    t3 = Transaction(
        user_id=uid_1,
        amount=1240.00,
        txn_type="debit",
        source="sms",
        upi_app=None,
        app_label_source="unknown",
        txn_timestamp=now_utc_naive - timedelta(minutes=20),
    )
    # 4. Manual transaction (source='manual', amount=1000.00) - should be ignored by upi-apps-breakdown
    t4 = Transaction(
        user_id=uid_1,
        amount=1000.00,
        txn_type="debit",
        source="manual",
        txn_timestamp=now_utc_naive,
    )

    db_session.add_all([t1, t2, t3, t4])
    db_session.commit()

    # Query for the month
    res = client.get("/api/v1/dashboard/upi-apps-breakdown?filter_type=month", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Total UPI spend: 4250 + 3100 + 1240 = 8590.00
    assert float(data["total_spend"]) == 8590.00
    items = data["items"]
    assert len(items) == 3

    # Sorted descending by amount:
    # 1. PhonePe
    assert items[0]["app"] == "PhonePe"
    assert float(items[0]["amount"]) == 4250.00
    # percentage: 4250 / 8590 * 100 = 49.48
    assert items[0]["percentage"] == 49.48

    # 2. GPay
    assert items[1]["app"] == "GPay"
    assert float(items[1]["amount"]) == 3100.00
    # percentage: 3100 / 8590 * 100 = 36.09
    assert items[1]["percentage"] == 36.09

    # 3. Unknown
    assert items[2]["app"] == "Unknown"
    assert items[2]["app_label_source"] == "unlabeled"
    assert float(items[2]["amount"]) == 1240.00
    # percentage: 1240 / 8590 * 100 = 14.44
    assert items[2]["percentage"] == 14.44
