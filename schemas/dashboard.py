from decimal import Decimal
from pydantic import BaseModel
from typing import List, Optional


class DashboardTodayResponse(BaseModel):
    total_amount: Decimal
    count: int
    difference: Decimal
    diff_percent: float
    is_higher: bool


class DashboardCurrentMonthResponse(BaseModel):
    total_amount: Decimal
    count: int
    last_month_total: Decimal
    difference: Decimal
    diff_percent: float
    is_higher: bool


class CategoryBreakdownItem(BaseModel):
    category_name: str
    amount: Decimal
    percentage: float


class DashboardBreakdownResponse(BaseModel):
    total_amount: Decimal
    categories: List[CategoryBreakdownItem]




class UPIAppBreakdownItem(BaseModel):
    app: str
    app_label_source: str
    amount: Decimal
    percentage: float


class DashboardUPIBreakdownResponse(BaseModel):
    total_spend: Decimal
    items: List[UPIAppBreakdownItem]
    period_start: str   # ISO-8601 in IST for display
    period_end: str     # ISO-8601 in IST for display


class UPIManualSpendResponse(BaseModel):
    upi_spend: Decimal
    manual_spend: Decimal
    filter_type: str
    period_start: str   # ISO-8601 in IST for display
    period_end: str     # ISO-8601 in IST for display
