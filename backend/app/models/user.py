from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
import uuid

from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    verification_code = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
