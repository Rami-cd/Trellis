from datetime import datetime
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.connection import Base

class IndexingJob(Base):
    __tablename__ = "indexing_jobs"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    repo_id: Mapped[str | None] = mapped_column(ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        __import__('sqlalchemy').Index("ix_jobs_user_id", "user_id"),
        __import__('sqlalchemy').Index("ix_jobs_status", "status"),
        __import__('sqlalchemy').Index("ix_jobs_repo_id", "repo_id"),
    )