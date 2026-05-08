import json
from sqlalchemy import Text, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.connection import Base
from pgvector.sqlalchemy import Vector

class CodeNode(Base):
    __tablename__ = "code_nodes"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    qualified_name: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_nodes_repo_path", "repo_id", "path"),
        Index("ix_nodes_name_trgm", "name", postgresql_using="gin",
              postgresql_ops={"name": "gin_trgm_ops"}),
    )

class CodeEdge(Base):
    __tablename__ = "code_edges"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("code_nodes.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[str | None] = mapped_column(ForeignKey("code_nodes.id", ondelete="SET NULL"), nullable=True)
    target_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_edges_source_id", "source_id"),
        Index("ix_edges_target_id", "target_id"),
        Index("ix_edges_source_type", "source_id", "type"),
        Index("ix_edges_target_ref_trgm", "target_ref", postgresql_using="gin",
              postgresql_ops={"target_ref": "gin_trgm_ops"}),
    )

class CodeEmbedding(Base):
    __tablename__ = "code_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("code_nodes.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)

    __table_args__ = (
        UniqueConstraint("node_id", "chunk_index", name="uq_embeddings_node_chunk"),
        Index("ix_embeddings_node_id", "node_id"),
        Index(
            "ix_embeddings_vector",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )