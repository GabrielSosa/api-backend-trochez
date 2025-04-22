from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)  # PostgreSQL will use SERIAL type
    user_type_id = Column(Integer, ForeignKey("user_types.user_type_id"), nullable=False)
    name = Column(String(100), nullable=False)
    password = Column(String(100), nullable=False)
    email = Column(String(45), nullable=False)
    profile_picture_url = Column(String(150), nullable=True)
    change_pass = Column(Boolean, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_date = Column(DateTime, nullable=False, server_default=func.now())
    updated_date = Column(DateTime, nullable=True, server_default=func.now(), onupdate=func.now())