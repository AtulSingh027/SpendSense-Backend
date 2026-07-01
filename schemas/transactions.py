from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, condecimal


class TransactionCreate(BaseModel):
    """Client-facing schema for manual transaction creation.
    Server-managed fields (app_label_source, app_label_confidence, bank_ref_id)
    are intentionally excluded — the server decides these values."""
    amount: float
    txn_type: str = Field(..., pattern="^(debit|credit)$")
    merchant_raw: Optional[str] = None
    category_id: Optional[int] = None
    upi_app: Optional[str] = None
    source: str = Field(..., pattern="^(sms|manual)$")
    txn_timestamp: datetime
    notes: Optional[str] = None


class TransactionUpdate(BaseModel):
    """Client-facing schema for transaction updates.
    Server-managed fields (app_label_source, app_label_confidence, bank_ref_id)
    are intentionally excluded — when upi_app is set, the server auto-flips
    app_label_source to 'user_labeled' and clears app_label_confidence."""
    amount: Optional[condecimal(gt=0, decimal_places=2)] = None
    txn_type: Optional[str] = None
    merchant_raw: Optional[str] = None
    category_id: Optional[int] = None
    upi_app: Optional[str] = None
    source: Optional[str] = None
    txn_timestamp: Optional[datetime] = None
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    sms_log_id: Optional[int] = None
    amount: Decimal
    txn_type: str
    merchant_raw: Optional[str] = None
    merchant_clean: Optional[str] = None
    category_id: Optional[int] = None
    upi_app: Optional[str] = None
    app_label_source: Optional[str] = None
    app_label_confidence: Optional[float] = None
    source: str
    bank_ref_id: Optional[str] = None
    txn_timestamp: datetime
    notes: Optional[str] = None
    category_name: Optional[str] = None
    sms_raw_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[TransactionResponse]