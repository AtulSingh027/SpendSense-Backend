from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SMSIngestRequest(BaseModel):
    sender_id: str = Field(..., max_length=20, min_length=2, description="Sender ID of the SMS (e.g. AXISBK)")
    raw_text: str = Field(..., min_length=1, description="Full text of the received SMS")
    received_at: datetime = Field(..., description="Timestamp of when the SMS was received")


class SMSBulkIngestRequest(BaseModel):
    sms_list: List[SMSIngestRequest] = Field(..., min_length=1, description="List of SMS logs to ingest")


class SMSIngestResponse(BaseModel):
    sms_log_id: int
    parsed: bool
    transaction_id: Optional[int] = None
    duplicate: bool = False


class SMSBulkIngestResponse(BaseModel):
    total_received: int
    processed: int
    parsed_count: int
    failed_count: int
    duplicate_count: int
    results: List[SMSIngestResponse]
