from sqlalchemy import Column, Integer, JSON, DateTime, Float, UniqueConstraint
from sqlalchemy.sql import func
from configs.db_config import Base

class MonthlySummary(Base):
    __tablename__ = 'monthly_summaries'

    __table_args__ = (
        UniqueConstraint('user_id', 'year', 'month', name='uq_user_year_month'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    total_spent = Column(Float, default=0)
    total_credit = Column(Float, default=0)
    category_breakdown = Column(JSON)
    app_breakdown = Column(JSON)
    source_breakdown = Column(JSON)
    txn_count = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    