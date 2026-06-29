from models.category import Category
from decimal import Decimal
import logging
from datetime import datetime, timezone, time, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from configs.db_config import get_db
from helpers.middelwares.auth_middelware import get_current_user
from helpers.date_filter import FilterType, resolve_date_range
from models.transaction import Transaction
from models.monthly_summary import MonthlySummary
from schemas.dashboard import (
    DashboardUPIBreakdownResponse,
    UPIAppBreakdownItem,
    DashboardTodayResponse,
    DashboardCurrentMonthResponse,
    DashboardBreakdownResponse,
    CategoryBreakdownItem,
    UPIManualSpendResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

IST = ZoneInfo("Asia/Kolkata")


#---------------------- Helpers ----------------------------------------------------------------------

def _ist_day_bounds_utc(target_date) -> Tuple[datetime, datetime]:
    """Day boundaries computed in IST, returned as naive UTC for DB comparison."""
    start_ist = datetime.combine(target_date, time.min, tzinfo=IST)
    end_ist = datetime.combine(target_date, time.max, tzinfo=IST)
    return (
        start_ist.astimezone(timezone.utc).replace(tzinfo=None),
        end_ist.astimezone(timezone.utc).replace(tzinfo=None),
    )


def _ist_month_bounds_utc(year: int, month: int) -> Tuple[datetime, datetime]:
    """Month boundaries computed in IST, returned as naive UTC for DB comparison."""
    start_ist = datetime(year, month, 1, 0, 0, 0, tzinfo=IST)
    
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
        
    start_of_next_month_ist = datetime(next_year, next_month, 1, 0, 0, 0, tzinfo=IST)
    end_ist = start_of_next_month_ist - timedelta(microseconds=1)
    
    return (
        start_ist.astimezone(timezone.utc).replace(tzinfo=None),
        end_ist.astimezone(timezone.utc).replace(tzinfo=None),
    )


def _get_yesterday_spend(user_id: int, db: Session):
    today_ist = datetime.now(IST).date()
    yesterday_ist = today_ist - timedelta(days=1)
    start_of_yesterday, end_of_yesterday = _ist_day_bounds_utc(yesterday_ist)

    stmt = (
        select(
            func.coalesce(func.sum(Transaction.amount), 0).label("total_amount")
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.txn_type == "debit",
            Transaction.txn_timestamp >= start_of_yesterday,
            Transaction.txn_timestamp <= end_of_yesterday
        )
    )

    result = db.execute(stmt).first()
    return result.total_amount if result else 0


def _get_previous_month_spend(user_id: int, db: Session):
    now_ist = datetime.now(IST)
    current_year = now_ist.year
    current_month = now_ist.month

    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year

    start_of_previous_month, end_of_previous_month = _ist_month_bounds_utc(prev_year, prev_month)

    stmt = (
        select(
            func.coalesce(func.sum(Transaction.amount), 0).label("total_amount")
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.txn_type == "debit",
            Transaction.txn_timestamp >= start_of_previous_month,
            Transaction.txn_timestamp <= end_of_previous_month
        )
    )

    result = db.execute(stmt).first()
    return result.total_amount if result else 0


#---------------------- Apis-----------------------------------------------------------------------

@router.get(
    "/today",
    response_model=DashboardTodayResponse,
    status_code=status.HTTP_200_OK,
    summary="Get today's total spend and transaction count",
)
def get_today_spend(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the sum of all debit transactions (expenses) and their count
    for the current user on the current day in IST, queried using UTC timestamps.
    """
    try:
        # Calculate current IST day boundaries, converted to naive UTC
        today_ist = datetime.now(IST).date()
        start_of_today, end_of_today = _ist_day_bounds_utc(today_ist)

        # Query sum and count of debit transactions within boundaries
        stmt = (
            select(
                func.coalesce(func.sum(Transaction.amount), 0).label("total_amount"),
                func.count(Transaction.id).label("count")
            )
            .where(
                Transaction.user_id == current_user_id,
                Transaction.txn_type == "debit",
                Transaction.txn_timestamp >= start_of_today,
                Transaction.txn_timestamp <= end_of_today
            )
        )

        result = db.execute(stmt).first()
        total_amount = result.total_amount if result else 0
        count = result.count if result else 0

        # Compare with yesterday and show in frontend
        yesterday_amount = _get_yesterday_spend(current_user_id, db)
        difference = total_amount - yesterday_amount
        
        if yesterday_amount > 0:
            diff_percent = float((difference / yesterday_amount) * 100)
            diff_percent = round(abs(diff_percent), 2)
            is_higher = difference > 0
        else:
            if total_amount > 0:
                diff_percent = 100.00
                is_higher = True
            else:
                diff_percent = 0.00
                is_higher = False

        return DashboardTodayResponse(
            total_amount=total_amount,
            count=count,
            difference=difference,
            diff_percent=diff_percent,
            is_higher=is_higher,
        )

    except Exception as e:
        logger.exception("Failed to fetch today's dashboard spend")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve today's dashboard data.",
        )


@router.get(
    "/current-month",
    response_model=DashboardCurrentMonthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current month's total spend and transaction count",
)
def get_current_month_spend(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the sum of all debit transactions (expenses) and their count
    for the current user on the current month in IST, queried using UTC timestamps.
    """
    try:
        # Calculate current IST month boundaries, converted to naive UTC
        now_ist = datetime.now(IST)
        start_of_current_month, end_of_current_month = _ist_month_bounds_utc(now_ist.year, now_ist.month)

        # Query sum and count of debit transactions within boundaries
        stmt = (
            select(
                func.coalesce(func.sum(Transaction.amount), 0).label("total_amount"),
                func.count(Transaction.id).label("count")
            )
            .where(
                Transaction.user_id == current_user_id,
                Transaction.txn_type == "debit",
                Transaction.txn_timestamp >= start_of_current_month,
                Transaction.txn_timestamp <= end_of_current_month
            )
        )

        result = db.execute(stmt).first()
        total_amount = result.total_amount if result else 0
        count = result.count if result else 0

        # Compare with previous month spend
        previous_month_amount = _get_previous_month_spend(current_user_id, db)
        difference = total_amount - previous_month_amount
        
        if previous_month_amount > 0:
            diff_percent = float((difference / previous_month_amount) * 100)
            diff_percent = round(abs(diff_percent), 2)
            is_higher = difference > 0
        else:
            if total_amount > 0:
                diff_percent = 100.00
                is_higher = True
            else:
                diff_percent = 0.00
                is_higher = False

        return DashboardCurrentMonthResponse(
            total_amount=total_amount,
            count=count,
            last_month_total=previous_month_amount,
            difference=difference,
            diff_percent=diff_percent,
            is_higher=is_higher,
        )

    except Exception as e:
        logger.exception("Failed to fetch current month's dashboard spend")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve current month's dashboard data.",
        )


@router.get(
    '/breakdown',
    response_model=DashboardBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Pie Chart BreakDown Category wise"
)
def get_category_breakdown(
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        now_ist = datetime.now(IST)

        row = db.query(MonthlySummary).filter_by(
            user_id=current_user_id, year=now_ist.year, month=now_ist.month
        ).first()

        breakdown = row.category_breakdown if row else {}
        total_amount = Decimal(str(row.total_spent)) if row else Decimal("0")

        if not breakdown:
            return DashboardBreakdownResponse(total_amount=total_amount, categories=[])

        # Resolve category IDs → names in one query
        cat_ids = [int(k) for k in breakdown if k != "uncategorized"]
        cat_name_map = {}
        if cat_ids:
            rows = db.execute(
                select(Category.id, Category.name).where(Category.id.in_(cat_ids))
            ).all()
            cat_name_map = {str(cid): name for cid, name in rows}

        categories = []
        for key, amt in breakdown.items():
            cat_name = cat_name_map.get(key, "Uncategorized") if key != "uncategorized" else "Uncategorized"
            amount = Decimal(str(amt))
            percentage = round(float((amount / total_amount) * 100), 2) if total_amount > 0 else 0.00
            categories.append(
                CategoryBreakdownItem(category_name=cat_name, amount=amount, percentage=percentage)
            )

        # Sort descending by amount (matching previous behavior)
        categories.sort(key=lambda x: x.amount, reverse=True)

        return DashboardBreakdownResponse(total_amount=total_amount, categories=categories)

    except Exception as e:
        logger.exception("Failed to fetch category breakdown")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category breakdown.",
        )
    

@router.get(
    "/upi-manual-spend",
    response_model=UPIManualSpendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get total UPI and Manual spend, filterable by day / week / month / custom",
)
def get_upi_manual_spend(
    filter_type: FilterType = Query(
        FilterType.month,
        description="Period granularity: day | week | month | custom",
    ),
    custom_start: Optional[str] = Query(
        None,
        description="Required when filter_type=custom. ISO-8601 date e.g. 2024-06-01",
    ),
    custom_end: Optional[str] = Query(
        None,
        description="Required when filter_type=custom. ISO-8601 date e.g. 2024-06-30",
    ),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # Parse custom date strings when filter_type is custom
        parsed_start = datetime.fromisoformat(custom_start) if custom_start else None
        parsed_end = datetime.fromisoformat(custom_end) if custom_end else None

        start_utc, end_utc = resolve_date_range(filter_type, parsed_start, parsed_end)

        stmt = (
            select(
                func.coalesce(
                    func.sum(case((Transaction.source == "sms", Transaction.amount), else_=0)),
                    0,
                ).label("upi_spend"),
                
                func.coalesce(
                    func.sum(case((Transaction.source == "manual", Transaction.amount), else_=0)),
                    0,
                ).label("manual_spend"),
            )
            .where(
                Transaction.user_id == current_user_id,
                Transaction.txn_type == "debit",
                Transaction.txn_timestamp >= start_utc,
                Transaction.txn_timestamp <= end_utc,
            )
        )

        result = db.execute(stmt).first()
        upi_spend = result.upi_spend if result else 0
        manual_spend = result.manual_spend if result else 0

        # Convert UTC bounds back to IST strings for the frontend
        period_start_ist = start_utc.replace(tzinfo=timezone.utc).astimezone(IST)
        period_end_ist = end_utc.replace(tzinfo=timezone.utc).astimezone(IST)

        return UPIManualSpendResponse(
            upi_spend=upi_spend,
            manual_spend=manual_spend,
            filter_type=filter_type.value,
            period_start=period_start_ist.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
            period_end=period_end_ist.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch UPI / Manual spend totals")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve UPI / Manual spend data.",
        )


@router.get(
    "/upi-apps-breakdown",
    response_model=DashboardUPIBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Get UPI apps wise breakdown with period filter",
)
def get_upi_apps_breakdown(
    filter_type: FilterType = Query(
        FilterType.month,
        description="Period granularity: day | week | month | custom",
    ),
    custom_start: Optional[str] = Query(
        None,
        description="Required when filter_type=custom. ISO-8601 date e.g. 2024-06-01",
    ),
    custom_end: Optional[str] = Query(
        None,
        description="Required when filter_type=custom. ISO-8601 date e.g. 2024-06-30",
    ),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns a breakdown of UPI app expenditures for the authenticated user,
    grouped by UPI app (e.g. PhonePe, GPay, Paytm) with spend amounts and percentages.
    """
    try:
        # Parse custom date strings when filter_type is custom
        parsed_start = datetime.fromisoformat(custom_start) if custom_start else None
        parsed_end = datetime.fromisoformat(custom_end) if custom_end else None

        start_utc, end_utc = resolve_date_range(filter_type, parsed_start, parsed_end)

        # Query all debit transactions where source='sms' (UPI transactions)
        stmt = (
            select(
                Transaction.upi_app,
                Transaction.app_label_source,
                func.coalesce(func.sum(Transaction.amount), 0).label("amount")
            )
            .where(
                Transaction.user_id == current_user_id,
                Transaction.txn_type == "debit",
                Transaction.txn_timestamp >= start_utc,
                Transaction.txn_timestamp <= end_utc,
                Transaction.source == "sms"
            )
            .group_by(Transaction.upi_app, Transaction.app_label_source)
        )

        results = db.execute(stmt).fetchall()

        # Group and accumulate by app name (handling None/empty values as 'Unknown')
        app_data = {}
        total_spend = Decimal('0.00')

        for row in results:
            raw_app = row.upi_app
            app_name = raw_app.strip() if (raw_app and raw_app.strip()) else "Unknown"
            app_src = "unlabeled" if app_name == "Unknown" else (row.app_label_source or "unknown")
            amount = row.amount or Decimal('0.00')

            if app_name not in app_data:
                app_data[app_name] = {
                    "app_label_source": app_src,
                    "amount": Decimal('0.00')
                }
            app_data[app_name]["amount"] += amount
            total_spend += amount

        # Build response items and calculate percentages
        items = []
        for app_name, info in app_data.items():
            amount = info["amount"]
            percentage = 0.00
            if total_spend > 0:
                percentage = round(float((amount / total_spend) * 100), 2)
            
            items.append(
                UPIAppBreakdownItem(
                    app=app_name,
                    app_label_source=info["app_label_source"],
                    amount=amount,
                    percentage=percentage
                )
            )

        # Sort by amount descending
        items.sort(key=lambda x: x.amount, reverse=True)

        # Convert UTC bounds back to IST for period start/end response
        period_start_ist = start_utc.replace(tzinfo=timezone.utc).astimezone(IST)
        period_end_ist = end_utc.replace(tzinfo=timezone.utc).astimezone(IST)

        return DashboardUPIBreakdownResponse(
            total_spend=total_spend,
            items=items,
            period_start=period_start_ist.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
            period_end=period_end_ist.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch UPI apps breakdown")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve UPI apps breakdown.",
        )
