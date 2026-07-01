import random
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import app
from configs.db_config import SessionLocal
from models.category import Category
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
        db_session.delete(user)
        db_session.commit()


# ═══════════════════════════════════════════════════════════════════════
#  CATEGORIES API TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_category_lifecycle(test_user_1, test_user_2, db_session):
    headers_1, uid_1 = test_user_1
    headers_2, uid_2 = test_user_2

    # 1. Create custom category for User 1
    cat_payload = {"name": "CustomFood", "icon": "food-icon"}
    res = client.post("/api/v1/categories/create", json=cat_payload, headers=headers_1)
    assert res.status_code == 201
    cat_data = res.json()
    assert cat_data["name"] == "CustomFood"
    assert cat_data["user_id"] == uid_1
    assert cat_data["is_system"] is False
    cat_id = cat_data["id"]

    # 2. Try to create duplicate category name for same User 1 (should fail 409)
    res_dup = client.post("/api/v1/categories/create", json=cat_payload, headers=headers_1)
    assert res_dup.status_code == 409

    # 3. Create same category name for User 2 (should succeed, since unique is per user)
    res_user2 = client.post("/api/v1/categories/create", json=cat_payload, headers=headers_2)
    assert res_user2.status_code == 201

    # 4. Get all categories for User 1 (should contain CustomFood + system seeded categories)
    res_list = client.get("/api/v1/categories/", headers=headers_1)
    assert res_list.status_code == 200
    categories = res_list.json()
    assert len(categories) > 0
    names = [c["name"] for c in categories]
    assert "CustomFood" in names
    # Ensure system categories like Food, Bills, etc. exist
    assert any(c["is_system"] for c in categories)

    # 5. Get category by ID (User 1 can see their own custom category)
    res_get = client.get(f"/api/v1/categories/{cat_id}", headers=headers_1)
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "CustomFood"

    # 6. User 2 tries to get User 1's custom category (should fail 403)
    res_get_unauthorized = client.get(f"/api/v1/categories/{cat_id}", headers=headers_2)
    assert res_get_unauthorized.status_code == 403

    # 7. Update custom category (User 1 updates CustomFood -> CustomDrinks)
    update_payload = {"name": "CustomDrinks", "icon": "drink-icon"}
    res_update = client.put(f"/api/v1/categories/{cat_id}", json=update_payload, headers=headers_1)
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "CustomDrinks"

    # 8. User 2 tries to update User 1's category (should fail 403)
    res_update_unauth = client.put(f"/api/v1/categories/{cat_id}", json=update_payload, headers=headers_2)
    assert res_update_unauth.status_code == 403

    # 9. Find a system category (where is_system == True)
    system_cat = db_session.execute(
        select(Category).where(Category.is_system == True)
    ).scalars().first()
    assert system_cat is not None
    sys_cat_id = system_cat.id

    # 10. User 1 tries to update a system category (should fail 403)
    res_sys_update = client.put(f"/api/v1/categories/{sys_cat_id}", json={"name": "NewSystemName"}, headers=headers_1)
    assert res_sys_update.status_code == 403

    # 11. User 1 tries to delete system category (should fail 403)
    res_sys_del = client.delete(f"/api/v1/categories/{sys_cat_id}", headers=headers_1)
    assert res_sys_del.status_code == 403

    # 12. User 2 tries to delete User 1's custom category (should fail 403)
    res_del_unauth = client.delete(f"/api/v1/categories/{cat_id}", headers=headers_2)
    assert res_del_unauth.status_code == 403

    # 13. Delete custom category (User 1 deletes CustomDrinks)
    res_del = client.delete(f"/api/v1/categories/{cat_id}", headers=headers_1)
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

    # Check database cleanup
    db_session.rollback()
    deleted_cat = db_session.get(Category, cat_id)
    assert deleted_cat is None


# ═══════════════════════════════════════════════════════════════════════
#  TRANSACTIONS API TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_transaction_lifecycle(test_user_1, test_user_2, db_session):
    headers_1, uid_1 = test_user_1
    headers_2, uid_2 = test_user_2
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Create transaction for User 1 (no upi_app → app_label_source should be "unknown")
    txn_payload = {
        "amount": 1500.50,
        "txn_type": "debit",
        "merchant_raw": "Amazon Shopping",
        "source": "manual",
        "txn_timestamp": now_iso,
        "notes": "Buying electronics",
    }
    res = client.post("/api/v1/transaction/", json=txn_payload, headers=headers_1)
    assert res.status_code == 201
    txn_data = res.json()
    assert float(txn_data["amount"]) == 1500.50
    assert txn_data["user_id"] == uid_1
    assert txn_data["source"] == "manual"
    assert txn_data["app_label_source"] == "unknown"
    assert txn_data["bank_ref_id"] is None  # manual entries never have bank_ref_id
    assert txn_data["category_name"] is None
    txn_id = txn_data["id"]

    # 2. Get all transactions (should return User 1's transaction)
    res_list = client.get("/api/v1/transaction/", headers=headers_1)
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] == 1
    assert len(list_data["items"]) == 1
    assert list_data["items"][0]["id"] == txn_id
    assert list_data["items"][0]["category_name"] is None

    # 3. Get all transactions for User 2 (should return 0 items)
    res_list_2 = client.get("/api/v1/transaction/", headers=headers_2)
    assert res_list_2.status_code == 200
    assert res_list_2.json()["total"] == 0

    # 4. Get transaction by ID (User 1 success)
    res_get = client.get(f"/api/v1/transaction/{txn_id}", headers=headers_1)
    assert res_get.status_code == 200
    assert float(res_get.json()["amount"]) == 1500.50
    assert res_get.json()["category_name"] is None

    # 5. Get transaction by ID (User 2 unauthorized 403)
    res_get_unauth = client.get(f"/api/v1/transaction/{txn_id}", headers=headers_2)
    assert res_get_unauth.status_code == 403

    # 6. Update transaction — setting upi_app should auto-flip app_label_source to "user_labeled"
    # Create category first for testing category_name join
    cat_payload = {"name": "Electronics", "icon": "elec-icon"}
    cat_res = client.post("/api/v1/categories/create", json=cat_payload, headers=headers_1)
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    update_payload = {
        "amount": 1200.00,
        "notes": "Price dropped",
        "upi_app": "phonepe",
        "category_id": cat_id
    }
    res_update = client.patch(f"/api/v1/transaction/{txn_id}", json=update_payload, headers=headers_1)
    assert res_update.status_code == 200
    updated = res_update.json()
    assert float(updated["amount"]) == 1200.00
    assert updated["notes"] == "Price dropped"
    assert updated["upi_app"] == "phonepe"
    assert updated["app_label_source"] == "user_labeled"  # business rule enforced server-side
    assert updated["app_label_confidence"] is None  # user override clears model confidence
    assert updated["category_name"] == "Electronics"

    # 7. User 2 tries to update User 1's transaction (403)
    res_update_unauth = client.patch(f"/api/v1/transaction/{txn_id}", json=update_payload, headers=headers_2)
    assert res_update_unauth.status_code == 403

    # 8. User 2 tries to delete User 1's transaction (403)
    res_del_unauth = client.delete(f"/api/v1/transaction/{txn_id}", headers=headers_2)
    assert res_del_unauth.status_code == 403

    # 9. User 1 deletes transaction
    res_del = client.delete(f"/api/v1/transaction/{txn_id}", headers=headers_1)
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

    # Verify deleted from DB
    db_session.rollback()
    deleted_txn = db_session.get(Transaction, txn_id)
    assert deleted_txn is None


def test_category_icon_cloudinary_upload(test_user_1, db_session):
    headers_1, uid_1 = test_user_1

    # 1. Create a category with a valid 1x1 transparent base64 PNG data URI
    base64_icon = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    cat_payload = {"name": "CloudinaryCategory", "icon": base64_icon}
    
    res = client.post("/api/v1/categories/create", json=cat_payload, headers=headers_1)
    assert res.status_code == 201
    cat_data = res.json()
    assert cat_data["name"] == "CloudinaryCategory"
    assert cat_data["icon"] is not None
    assert "cloudinary" in cat_data["icon"]
    assert cat_data["icon"].startswith("https://")
    cat_id = cat_data["id"]

    # 2. Update category icon with another base64 string
    new_base64_icon = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    update_payload = {"name": "CloudinaryCategoryUpdated", "icon": new_base64_icon}
    
    res_update = client.put(f"/api/v1/categories/{cat_id}", json=update_payload, headers=headers_1)
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert updated_data["icon"] is not None
    assert "cloudinary" in updated_data["icon"]
    assert updated_data["icon"].startswith("https://")
    assert updated_data["icon"] != cat_data["icon"]

    # Cleanup category from DB
    db_session.rollback()
    category = db_session.get(Category, cat_id)
    if category:
        db_session.delete(category)
        db_session.commit()


