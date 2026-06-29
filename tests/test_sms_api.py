import random
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import app
from configs.db_config import SessionLocal
from models.sms_log import SMSLog
from models.transaction import Transaction
from models.user import User

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def authenticated_headers(db_session):
    """
    Creates a unique test user, registers/logs them in, and returns auth headers.
    Cleans up the user after tests finish.
    """
    # Create unique random phone number
    rand_phone = f"+91{random.randint(1000000000, 9999999999)}"
    password = "TestPassword123"

    # Register
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"phone_number": rand_phone, "password": password, "full_name": "Test User"},
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
        db_session.delete(user)
        db_session.commit()


# ═══════════════════════════════════════════════════════════════════════
#  SINGLE INGEST TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_single_ingest_hdfc_success(authenticated_headers, db_session):
    headers, user_id = authenticated_headers
    sms_time = datetime.now(timezone.utc).isoformat()
    sms_payload = {
        "sender_id": "VM-HDFCBK",
        "raw_text": "Rs.250.00 debited from a/c **1234 to VPA merchant@ybl on 25-06-26. Ref 987654321012.",
        "received_at": sms_time,
    }

    res = client.post("/api/v1/sms/ingest", json=sms_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["parsed"] is True
    assert data["duplicate"] is False
    assert data["transaction_id"] is not None
    assert data["sms_log_id"] is not None

    # Check DB logs
    log = db_session.get(SMSLog, data["sms_log_id"])
    assert log is not None
    assert log.user_id == user_id
    assert log.parse_status == "parsed"
    assert log.parser_used == "HDFCParser"

    # Check DB transaction
    txn = db_session.get(Transaction, data["transaction_id"])
    assert txn is not None
    assert txn.user_id == user_id
    assert txn.amount == 250.0
    assert txn.txn_type == "debit"
    assert txn.merchant_raw == "merchant@ybl"
    assert txn.bank_ref_id == "987654321012"
    assert txn.upi_app == "phonepe"


def test_single_ingest_duplicate(authenticated_headers, db_session):
    """Sending the exact same ref twice should return duplicate=True and same txn ID."""
    headers, _ = authenticated_headers
    sms_time = datetime.now(timezone.utc).isoformat()
    sms_payload = {
        "sender_id": "VM-HDFCBK",
        "raw_text": "Rs.500.00 debited from a/c **1234 to VPA merchant@ybl. Ref 112233445566.",
        "received_at": sms_time,
    }

    # First ingest
    res1 = client.post("/api/v1/sms/ingest", json=sms_payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["duplicate"] is False

    # Duplicate ingest
    res2 = client.post("/api/v1/sms/ingest", json=sms_payload, headers=headers)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["parsed"] is True
    assert data2["duplicate"] is True
    assert data2["transaction_id"] == data1["transaction_id"]


def test_single_ingest_unparseable(authenticated_headers, db_session):
    headers, user_id = authenticated_headers
    sms_time = datetime.now(timezone.utc).isoformat()
    sms_payload = {
        "sender_id": "PROMO",
        "raw_text": "Get 50% cashback on your next purchase!",
        "received_at": sms_time,
    }

    res = client.post("/api/v1/sms/ingest", json=sms_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["parsed"] is False
    assert data["transaction_id"] is None
    assert data["sms_log_id"] is not None

    # Check DB logs shows failed status
    log = db_session.get(SMSLog, data["sms_log_id"])
    assert log is not None
    assert log.parse_status == "failed"


# ═══════════════════════════════════════════════════════════════════════
#  BULK INGEST TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_bulk_ingest_success(authenticated_headers, db_session):
    headers, user_id = authenticated_headers
    sms_time = datetime.now(timezone.utc).isoformat()

    # We send 3 messages:
    # 1. Axis debit (valid)
    # 2. BOB credit (valid)
    # 3. Promo SMS (invalid/unparseable)
    # 4. Axis debit duplicate of 1 (duplicate)
    payload = {
        "sms_list": [
            {
                "sender_id": "AXISBK",
                "raw_text": "INR 10.00 debited\nA/c no. XX9454\nUPI/P2M/654325545108/MAA UMIYA GENERAL S\nAxis Bank",
                "received_at": sms_time,
            },
            {
                "sender_id": "BOB",
                "raw_text": "Dear BOB UPI User: Your account is credited with INR 40.00 by UPI Ref No 570617317389; AvlBal: Rs222.46 - BOB",
                "received_at": sms_time,
            },
            {
                "sender_id": "PROMO",
                "raw_text": "Flash Sale! Upgrade your account now for 20% discount.",
                "received_at": sms_time,
            },
            {
                "sender_id": "AXISBK",
                "raw_text": "INR 10.00 debited\nA/c no. XX9454\nUPI/P2M/654325545108/MAA UMIYA GENERAL S\nAxis Bank",
                "received_at": sms_time,
            },
        ]
    }

    res = client.post("/api/v1/sms/ingest/bulk", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_received"] == 4
    assert data["processed"] == 4
    assert data["parsed_count"] == 3  # 2 success + 1 duplicate (which is still parsed=True)
    assert data["failed_count"] == 1
    assert data["duplicate_count"] == 1

    # Verify Axis debit transaction
    axis_txn = db_session.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.bank_ref_id == "654325545108"
        )
    ).scalars().all()
    # Should only be one Axis transaction in DB (duplicate rejected)
    assert len(axis_txn) == 1
    assert axis_txn[0].amount == 10.0
    assert axis_txn[0].merchant_raw == "MAA UMIYA GENERAL S"


# ═══════════════════════════════════════════════════════════════════════
#  SECURITY TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_unauthorized_endpoints():
    payload = {
        "sender_id": "VM-HDFCBK",
        "raw_text": "Rs.250.00 debited from a/c **1234 to VPA merchant@ybl. Ref 987654321012.",
        "received_at": datetime.now(timezone.utc).isoformat(),
    }

    # No token
    res1 = client.post("/api/v1/sms/ingest", json=payload)
    assert res1.status_code == 401

    # Invalid token
    res2 = client.post(
        "/api/v1/sms/ingest",
        json=payload,
        headers={"Authorization": "Bearer invalid_token_xyz"},
    )
    assert res2.status_code == 401

    # Bulk no token
    res3 = client.post("/api/v1/sms/ingest/bulk", json={"sms_list": [payload]})
    assert res3.status_code == 401
