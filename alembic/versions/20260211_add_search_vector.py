"""Add search_vector tsvector column and GIN/trigram indexes for messages.

This migration assumes the messages table is already partitioned.
Indexes are created concurrently per-partition to avoid long table locks.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa  # noqa: F401
from sqlalchemy import text


revision = "20260211_add_search_vector"
down_revision = "20260211_add_messages_partitioning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Ensure pg_trgm is available for trigram indexes.
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    # 1. Add GENERATED ALWAYS tsvector column on parent; cascades to partitions.
    conn.execute(
        text(
            """
            ALTER TABLE public.messages
            ADD COLUMN IF NOT EXISTS search_vector tsvector
            GENERATED ALWAYS AS (
              setweight(to_tsvector('english', coalesce(content, '')), 'A')
            ) STORED;
            """,
        ),
    )

    # 2. Create GIN and trigram indexes concurrently on each existing partition.
    partitions = conn.execute(
        text(
            """
            SELECT child.relname
            FROM pg_inherits
            JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
            JOIN pg_class child  ON pg_inherits.inhrelid = child.oid
            JOIN pg_namespace ns ON parent.relnamespace = ns.oid
            WHERE parent.relname = 'messages'
              AND ns.nspname = 'public';
            """,
        ),
    ).scalars().all()

    ctx = op.get_context()
    with ctx.autocommit_block():
        for relname in partitions:
            gin_index = f"{relname}_search_gin_idx"
            trigram_index = f"{relname}_content_trgm_idx"

            conn.execute(
                text(
                    f"""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS {gin_index}
                    ON public.{relname} USING GIN (search_vector);
                    """,
                ),
            )

            conn.execute(
                text(
                    f"""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS {trigram_index}
                    ON public.{relname} USING GIN (content gin_trgm_ops);
                    """,
                ),
            )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop indexes on partitions, then drop the column.
    partitions = conn.execute(
        text(
            """
            SELECT child.relname
            FROM pg_inherits
            JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
            JOIN pg_class child  ON pg_inherits.inhrelid = child.oid
            JOIN pg_namespace ns ON parent.relnamespace = ns.oid
            WHERE parent.relname = 'messages'
              AND ns.nspname = 'public';
            """,
        ),
    ).scalars().all()

    ctx = op.get_context()
    with ctx.autocommit_block():
        for relname in partitions:
            gin_index = f"{relname}_search_gin_idx"
            trigram_index = f"{relname}_content_trgm_idx"
            conn.execute(text(f"DROP INDEX IF EXISTS public.{gin_index}"))
            conn.execute(text(f"DROP INDEX IF EXISTS public.{trigram_index}"))

    conn.execute(
        text(
            "ALTER TABLE public.messages DROP COLUMN IF EXISTS search_vector",
        ),
    )

