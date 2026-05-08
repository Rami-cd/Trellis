from datetime import datetime
from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.connection import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        __import__('sqlalchemy').Index("ix_conversations_user_id", "user_id"),
        __import__('sqlalchemy').Index("ix_conversations_repo_id", "repo_id"),
    )

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(__import__('uuid').uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    nodes_used: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        __import__('sqlalchemy').Index("ix_messages_conversation_id", "conversation_id"),
    )