import logging
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from configs.db_config import get_db
from helpers.middelwares.auth_middelware import get_current_user
from models.transaction import Transaction
from models.category import Category
from models.sms_log import SMSLog
from services.summary_service import recompute_for_date
from schemas.transactions import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transaction", tags=["transaction"])


@router.get(
    "/",
    response_model=TransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all transactions",
)
def get_all_transactions(
    category_id: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    source: Optional[str] = Query(None),
    upi_app: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        filters = [Transaction.user_id == current_user_id]

        if category_id is not None:
            filters.append(Transaction.category_id == category_id)

        if month is not None:
            filters.append(extract("month", Transaction.txn_timestamp) == month)

        if year is not None:
            filters.append(extract("year", Transaction.txn_timestamp) == year)

        if from_date is not None:
            filters.append(Transaction.txn_timestamp >= from_date)

        if to_date is not None:
            filters.append(Transaction.txn_timestamp < (to_date + timedelta(days=1)))

        if source is not None:
            filters.append(Transaction.source == source)

        if upi_app is not None:
            app_lower = upi_app.lower()
            if app_lower in ["gpay", "googlepay", "google_pay"]:
                filters.append(func.lower(Transaction.upi_app).in_(["gpay", "googlepay", "google_pay"]))
            elif app_lower in ["phonepe", "phone_pay", "phonepay"]:
                filters.append(func.lower(Transaction.upi_app).in_(["phonepe", "phone_pay", "phonepay"]))
            elif app_lower in ["paytm", "pay_tm"]:
                filters.append(func.lower(Transaction.upi_app).in_(["paytm", "pay_tm"]))
            elif app_lower in ["unknown", "other"]:
                filters.append(
                    (func.lower(Transaction.upi_app).in_(["unknown", "other"])) |
                    (Transaction.upi_app == None) |
                    (Transaction.upi_app == "")
                )
            else:
                filters.append(func.lower(Transaction.upi_app) == app_lower)
        

        total = db.scalar(
            select(func.count()).select_from(Transaction).where(*filters)
        )

        query = (
            select(Transaction, Category.name.label("category_name"))
            .outerjoin(Category, Transaction.category_id == Category.id)
            .where(*filters)
            .order_by(Transaction.txn_timestamp.desc())
            .offset(offset)
            .limit(limit)
        )

        results = db.execute(query).all()
        transactions = []
        for txn, category_name in results:
            txn.category_name = category_name
            transactions.append(txn)

        return TransactionListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=transactions,
        )

    except Exception as e:
        logger.exception("Failed to fetch transactions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch transactions.",
        )


@router.get(
    "/{id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get transaction by ID",
)
def get_transaction_by_id(
    id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = db.execute(
            select(
                Transaction,
                Category.name.label("category_name"),
                SMSLog.raw_text.label("sms_raw_text")
            )
            .outerjoin(Category, Transaction.category_id == Category.id)
            .outerjoin(SMSLog, Transaction.sms_log_id == SMSLog.id)
            .where(Transaction.id == id)
        ).first()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )

        transaction, category_name, sms_raw_text = result
        if transaction.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this transaction.",
            )

        transaction.category_name = category_name
        transaction.sms_raw_text = sms_raw_text
        return transaction

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch transaction by ID")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch transaction.",
        )


@router.post(
    "/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual transaction",
)
def create_transaction(
    body: TransactionCreate,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        transaction = Transaction(
            user_id=current_user_id,
            amount=body.amount,
            txn_type=body.txn_type,
            merchant_raw=body.merchant_raw,
            category_id=body.category_id,
            upi_app=body.upi_app,
            app_label_source="user_labeled" if body.upi_app else "unknown",
            source=body.source,
            txn_timestamp=body.txn_timestamp,
            notes=body.notes,
            # bank_ref_id intentionally omitted — manual entries never have one
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        # Recompute summaries for the affected month + week in the background
        background_tasks.add_task(recompute_for_date, db, current_user_id, transaction.txn_timestamp)

        category_name = None
        if transaction.category_id:
            category_name = db.scalar(
                select(Category.name).where(Category.id == transaction.category_id)
            )
        transaction.category_name = category_name
        return transaction

    except Exception as e:
        logger.exception("Failed to create transaction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create transaction.",
        )


@router.patch(
    "/{id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update a transaction",
)
def update_transaction(
    id: int,
    body: TransactionUpdate,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        transaction = db.execute(
            select(Transaction).where(Transaction.id == id)
        ).scalars().first()

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )

        if transaction.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this transaction.",
            )

        update_data = body.model_dump(exclude_unset=True)

        # Capture old timestamp BEFORE applying changes — if the date moves
        # to a different month/week, we need to recompute the OLD period too.
        old_txn_timestamp = transaction.txn_timestamp

        # Business rule: when user sets upi_app via edit screen,
        # auto-promote app_label_source to "user_labeled" — this is what
        # makes the field trustworthy as ML training data later.
        if "upi_app" in update_data:
            update_data["app_label_source"] = "user_labeled"
            update_data["app_label_confidence"] = None  # user override beats any model score

        for key, value in update_data.items():
            setattr(transaction, key, value)

        db.commit()
        db.refresh(transaction)

        # Recompute summaries — always recompute the new period,
        # and also recompute the old period if the timestamp changed.
        background_tasks.add_task(recompute_for_date, db, current_user_id, transaction.txn_timestamp)
        if old_txn_timestamp != transaction.txn_timestamp:
            background_tasks.add_task(recompute_for_date, db, current_user_id, old_txn_timestamp)

        category_name = None
        if transaction.category_id:
            category_name = db.scalar(
                select(Category.name).where(Category.id == transaction.category_id)
            )
        transaction.category_name = category_name
        return transaction

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update transaction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update transaction.",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a transaction",
)
def delete_transaction(
    id: int,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        transaction = db.execute(
            select(Transaction).where(Transaction.id == id)
        ).scalars().first()

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found.",
            )

        if transaction.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this transaction.",
            )

        # Capture timestamp before deletion for summary recompute
        txn_timestamp = transaction.txn_timestamp

        db.delete(transaction)
        db.commit()

        # Recompute summaries for the period that lost this transaction
        background_tasks.add_task(recompute_for_date, db, current_user_id, txn_timestamp)

        return {
            "success": True,
            "message": "Transaction deleted successfully",
            "transaction_id": id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete transaction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete transaction.",
        )
