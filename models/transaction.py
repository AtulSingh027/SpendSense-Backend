from sqlalchemy import Column, Integer, String, Float, DateTime, Text, UniqueConstraint, Numeric
from sqlalchemy.sql import func
from configs.db_config import Base

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    sms_log_id = Column(Integer)
    amount = Column(Numeric(12,2), nullable=False)
    txn_type = Column(String(10), nullable=False)
    merchant_raw = Column(String(255))
    merchant_clean = Column(String(255))
    category_id = Column(Integer)
    upi_app = Column(String(30))
    app_label_source = Column(String(20), default='unknown')
    app_label_confidence = Column(Float)
    source = Column(String(10), nullable=False)
    bank_ref_id = Column(String(100))
    txn_timestamp = Column(DateTime, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    #make unique constraint on user_id and bank_ref_id
    __table_args__ = (
        UniqueConstraint('user_id', 'bank_ref_id', name='uq_user_bank_ref'),
    )

    