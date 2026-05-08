from datetime import datetime
from sqlalchemy import Text, ARRAY, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.connection import Base

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    focus_node_id: Mapped[str | None] = mapped_column(ForeignKey("code_nodes.id", ondelete="SET NULL"), nullable=True)
    active_node_ids: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    last_query_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        __import__('sqlalchemy').Index("ix_sessions_expires_at", "expires_at"),
    )