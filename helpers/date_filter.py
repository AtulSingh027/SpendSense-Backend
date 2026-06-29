"""
helpers/date_filter.py

Common date-range filter helper.

Usage
-----
Call `resolve_date_range(filter_type, custom_start, custom_end)` to get a
(start_utc, end_utc) pair of naive UTC datetimes you can plug straight into
any SQLAlchemy `.where(Transaction.txn_timestamp >= start, ...)` clause.

Supported filter_type values
-----------------------------
  "day"    → today in IST  (midnight … 23:59:59.999999)
  "week"   → current ISO week Mon–Sun in IST
  "month"  → current calendar month in IST
  "custom" → caller-supplied start / end (treated as IST midnight boundaries)

All input boundaries are computed in IST (Asia/Kolkata) and returned as
naive UTC datetimes so they match the way timestamps are stored in the DB.
"""

from datetime import datetime, time, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
from datetime import timezone
from enum import Enum
from typing import Optional, Tuple
from fastapi import HTTPException, status

IST = ZoneInfo("Asia/Kolkata")


class FilterType(str, Enum):
    day = "day"
    week = "week"
    month = "month"
    custom = "custom"


def _to_naive_utc(dt_ist: datetime) -> datetime:
    """Convert an IST-aware datetime to a naive UTC datetime."""
    return dt_ist.astimezone(timezone.utc).replace(tzinfo=None)


def resolve_date_range(
    filter_type: FilterType,
    custom_start: Optional[datetime] = None,
    custom_end: Optional[datetime] = None,
) -> Tuple[datetime, datetime]:
    """
    Return (start_utc, end_utc) naive UTC datetimes for the requested period.

    Parameters
    ----------
    filter_type   : One of FilterType enum values.
    custom_start  : Required when filter_type == "custom".  Interpreted as the
                    start-of-day boundary in IST if no time component is
                    provided (i.e. time is set to 00:00:00).
    custom_end    : Required when filter_type == "custom".  Interpreted as the
                    end-of-day boundary in IST if no time component is
                    provided (i.e. time is set to 23:59:59.999999).

    Raises
    ------
    HTTPException 422  if filter_type == "custom" and dates are missing /
                       invalid.
    """
    now_ist = datetime.now(IST)

    if filter_type == FilterType.day:
        start_ist = datetime.combine(now_ist.date(), time.min, tzinfo=IST)
        end_ist = datetime.combine(now_ist.date(), time.max, tzinfo=IST)

    elif filter_type == FilterType.week:
        # ISO week: Monday = 0
        weekday = now_ist.weekday()
        monday_ist = (now_ist - timedelta(days=weekday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        sunday_ist = monday_ist + timedelta(days=6)
        start_ist = monday_ist
        end_ist = sunday_ist.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

    elif filter_type == FilterType.month:
        start_ist = datetime(now_ist.year, now_ist.month, 1, 0, 0, 0, tzinfo=IST)
        if now_ist.month == 12:
            next_month_start_ist = datetime(now_ist.year + 1, 1, 1, 0, 0, 0, tzinfo=IST)
        else:
            next_month_start_ist = datetime(
                now_ist.year, now_ist.month + 1, 1, 0, 0, 0, tzinfo=IST
            )
        end_ist = next_month_start_ist - timedelta(microseconds=1)

    elif filter_type == FilterType.custom:
        if custom_start is None or custom_end is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="custom_start and custom_end are required for filter_type=custom.",
            )
        if custom_start > custom_end:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="custom_start must be before custom_end.",
            )
        # Treat naive datetimes as IST
        if custom_start.tzinfo is None:
            custom_start = custom_start.replace(tzinfo=IST)
        if custom_end.tzinfo is None:
            custom_end = custom_end.replace(tzinfo=IST)

        # Expand to full day boundaries in IST
        start_ist = datetime.combine(custom_start.date(), time.min, tzinfo=IST)
        end_ist = datetime.combine(custom_end.date(), time.max, tzinfo=IST)

    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported filter_type: {filter_type}",
        )

    return _to_naive_utc(start_ist), _to_naive_utc(end_ist)
