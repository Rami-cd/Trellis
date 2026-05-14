"""add content_hash to code_nodes

Revision ID: a2c3d4e5f6a7
Revises: 7fa1177d302d
Create Date: 2026-05-14 00:00:00.000000
"""

from __future__ import annotations

import hashlib

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a2c3d4e5f6a7"
down_revision = "7fa1177d302d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "code_nodes",
        sa.Column("content_hash", sa.Text(), nullable=True),
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("""
            SELECT id, raw_source
            FROM code_nodes
        """)
    ).mappings().all()

    updates = [
        {
            "node_id": row["id"],
            "content_hash": hashlib.sha256(
                (row["raw_source"] or "").encode("utf-8")
            ).hexdigest(),
        }
        for row in rows
    ]
    if updates:
        bind.execute(
            sa.text("""
                UPDATE code_nodes
                SET content_hash = :content_hash
                WHERE id = :node_id
            """),
            updates,
        )

    op.alter_column(
        "code_nodes",
        "content_hash",
        existing_type=sa.Text(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("code_nodes", "content_hash")
