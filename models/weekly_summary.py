from sqlalchemy import Column, Date, Integer, JSON, DateTime, Float, UniqueConstraint
from sqlalchemy.sql import func
from configs.db_config import Base


class WeeklySummary(Base):
    __tablename__ = 'weekly_summaries'

    __table_args__ = (
        UniqueConstraint('user_id', 'week_start', name='uq_user_week_start'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    week_start = Column(Date, nullable=False)
    total_spent = Column(Float, default=0)
    app_breakdown = Column(JSON)
    source_breakdown = Column(JSON)
    txn_count = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
