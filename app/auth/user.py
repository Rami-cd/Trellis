import uuid
from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.connection import Base
from fastapi_users.db import SQLAlchemyBaseUserTableUUID

class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"