from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from configs.db_config import Base

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    name = Column(String(50), nullable=False)
    icon = Column(String(50))
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
