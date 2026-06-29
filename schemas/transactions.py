from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class TransactionCreate(BaseModel):
    """Client-facing schema for manual transaction creation.
    Server-managed fields (app_label_source, app_label_confidence, bank_ref_id)
    are intentionally excluded — the server decides these values."""
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    txn_type: str = Field(..., pattern="^(debit|credit)$")
    merchant_raw: str | None = None
    category_id: int | None = None
    upi_app: str | None = None
    source: str = Field(..., pattern="^(sms|manual)$")
    txn_timestamp: datetime
    notes: str | None = None


class TransactionUpdate(BaseModel):
    """Client-facing schema for transaction updates.
    Server-managed fields (app_label_source, app_label_confidence, bank_ref_id)
    are intentionally excluded — when upi_app is set, the server auto-flips
    app_label_source to 'user_labeled' and clears app_label_confidence."""
    amount: Decimal | None = Field(None, gt=0, decimal_places=2)
    txn_type: str | None = None
    merchant_raw: str | None = None
    category_id: int | None = None
    upi_app: str | None = None
    source: str | None = None
    txn_timestamp: datetime | None = None
    notes: str | None = None


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    sms_log_id: int | None = None
    amount: Decimal
    txn_type: str
    merchant_raw: str | None = None
    merchant_clean: str | None = None
    category_id: int | None = None
    upi_app: str | None = None
    app_label_source: str | None = None
    app_label_confidence: float | None = None
    source: str
    bank_ref_id: str | None = None
    txn_timestamp: datetime
    notes: str | None = None
    category_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[TransactionResponse]