from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from configs.db_config import get_db
from helpers.middelwares.auth_middelware import get_current_user
from models.sms_log import SMSLog
from models.transaction import Transaction
from services.summary_service import recompute_for_date

from schemas.sms import (
    SMSBulkIngestRequest,
    SMSBulkIngestResponse,
    SMSIngestRequest,
    SMSIngestResponse,
)
from services.sms_parser.register import parse_sms

router = APIRouter(prefix="/sms", tags=["SMS"])


def _process_single_sms(
    db: Session, sms_data: SMSIngestRequest, user_id: int, background_tasks: BackgroundTasks
) -> SMSIngestResponse:
    """
    Core business logic helper to ingest, parse, log, and store transaction.
    """
    # 1. Log the raw SMS
    log = SMSLog(
        user_id=user_id,
        sender_id=sms_data.sender_id,
        raw_text=sms_data.raw_text,
        received_at=sms_data.received_at,
        parse_status="pending",
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # 2. Run the strategy parser
    try:
        result, parser_used = parse_sms(sms_data.sender_id, sms_data.raw_text)
    except Exception as e:
        log.parse_status = "failed"
        log.parse_error = str(e)
        db.commit()
        return SMSIngestResponse(
            sms_log_id=log.id,
            parsed=False,
            transaction_id=None,
            duplicate=False,
        )

    if not result:
        log.parse_status = "failed"
        db.commit()
        return SMSIngestResponse(
            sms_log_id=log.id,
            parsed=False,
            transaction_id=None,
            duplicate=False,
        )

    # 3. Log parser success
    log.parse_status = "parsed"
    log.parser_used = parser_used
    db.commit()

    # 4. Deduplication: Check if transaction already exists for this bank_ref_id
    if result.bank_ref_id:
        existing = db.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.bank_ref_id == result.bank_ref_id,
            )
        ).scalar_one_or_none()
        if existing:
            return SMSIngestResponse(
                sms_log_id=log.id,
                parsed=True,
                transaction_id=existing.id,
                duplicate=True,
            )

    # 5. Insert new Transaction
    txn = Transaction(
        user_id=user_id,
        sms_log_id=log.id,
        amount=result.amount,
        txn_type=result.txn_type,
        merchant_raw=result.merchant_raw,
        upi_app=result.upi_app,
        app_label_source="unknown",
        source="sms",
        bank_ref_id=result.bank_ref_id,
        txn_timestamp=sms_data.received_at,
    )
    db.add(txn)
    try:
        db.commit()
        db.refresh(txn)

        # Recompute summaries for the period containing this new transaction
        background_tasks.add_task(recompute_for_date, db, user_id, txn.txn_timestamp)
    except IntegrityError:
        # Handle concurrent requests race condition
        db.rollback()
        if result.bank_ref_id:
            existing = db.execute(
                select(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.bank_ref_id == result.bank_ref_id,
                )
            ).scalar_one_or_none()
            if existing:
                return SMSIngestResponse(
                    sms_log_id=log.id,
                    parsed=True,
                    transaction_id=existing.id,
                    duplicate=True,
                )
        raise

    return SMSIngestResponse(
        sms_log_id=log.id,
        parsed=True,
        transaction_id=txn.id,
        duplicate=False,
    )


@router.post(
    "/ingest",
    response_model=SMSIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single SMS",
)
def ingest(
    sms_data: SMSIngestRequest,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log raw SMS to database, try to parse transaction details, and save the
    transaction if parsed successfully. Performs deduplication based on bank_ref_id.
    """
    return _process_single_sms(db, sms_data, current_user_id, background_tasks)


@router.post(
    "/ingest/bulk",
    response_model=SMSBulkIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest multiple SMS in bulk",
)
def ingest_bulk(
    body: SMSBulkIngestRequest,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Bulk ingest historical SMS. Iterates over list, parsing and logging each.
    Continues processing the list even if a single item fails database insertion.
    """
    results = []
    parsed_count = 0
    failed_count = 0
    duplicate_count = 0

    for sms_item in body.sms_list:
        try:
            res = _process_single_sms(db, sms_item, current_user_id, background_tasks)
            results.append(res)
            if res.parsed:
                parsed_count += 1
                if res.duplicate:
                    duplicate_count += 1
            else:
                failed_count += 1

        except Exception as e:
            db.rollback()
            failed_count += 1
            # We don't have a database ID for the log since it rolled back,
            # but we record the failure in bulk stats.

    return SMSBulkIngestResponse(
        total_received=len(body.sms_list),
        processed=len(results),
        parsed_count=parsed_count,
        failed_count=failed_count,
        duplicate_count=duplicate_count,
        results=results,
    )