from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base

class UserType(Base):
    __tablename__ = "user_types"

    user_type_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(45), nullable=False)
    code = Column(String(45), nullable=False)
    description = Column(String(100), nullable=False)
    created_date = Column(DateTime, nullable=False, server_default="CURRENT_TIMESTAMP")
    pages = Column(String(450), nullable=True) 