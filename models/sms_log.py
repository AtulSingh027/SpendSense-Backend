from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from configs.db_config import Base

class SMSLog(Base):
    __tablename__ = 'sms_raw_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    sender_id = Column(String(20))
    raw_text = Column(Text, nullable=False)
    received_at = Column(DateTime, nullable=False)
    parse_status = Column(String(20), default='pending')
    parser_used = Column(String(50))
    parse_error = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    