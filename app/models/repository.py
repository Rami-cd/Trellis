from sqlalchemy import Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.connection import Base
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from datetime import datetime

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class RepositoryLanguage(Base):
    __tablename__ = "repository_languages"

    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), primary_key=True)
    language: Mapped[str] = mapped_column(Text, primary_key=True)