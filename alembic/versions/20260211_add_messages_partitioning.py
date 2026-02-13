"""Partition messages table by created_at (monthly RANGE partitions).

Zero-downtime-ish approach:
- If an existing non-partitioned messages table exists, rename it to messages_old.
- Create a new partitioned messages table with the same schema.
- Create a trigger to auto-create monthly partitions on demand.
- Backfill data from messages_old into the new messages table.

This migration assumes PostgreSQL 12+.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa  # noqa: F401
from sqlalchemy import text


revision = "20260211_add_messages_partitioning"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Detect whether a legacy messages table exists.
    has_messages = conn.execute(
        text(
            """
            SELECT to_regclass('public.messages') IS NOT NULL AS exists
            """,
        ),
    ).scalar()

    if has_messages:
        conn.execute(text("ALTER TABLE public.messages RENAME TO messages_old"))

    # 2. Create the new partitioned messages table if it does not exist.
    #    We define the schema explicitly to avoid depending on messages_old.
    conn.execute(
        text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'messages'
              ) THEN
                CREATE TABLE public.messages (
                  id VARCHAR(36) PRIMARY KEY,
                  conversation_id VARCHAR(36) NOT NULL,
                  role VARCHAR(50) NOT NULL,
                  content TEXT NOT NULL,
                  tokens INTEGER NOT NULL,
                  latency_ms INTEGER NOT NULL,
                  tool_calls JSONB NOT NULL DEFAULT '{}'::jsonb,
                  provider VARCHAR(50) NOT NULL,
                  model VARCHAR(100) NOT NULL,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) PARTITION BY RANGE (created_at);
              END IF;
            END;
            $$;
            """,
        ),
    )

    # 3. Default partition (for out-of-range/future dates as a safety net).
    conn.execute(
        text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1
                FROM pg_inherits
                JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
                JOIN pg_class child ON pg_inherits.inhrelid = child.oid
                WHERE parent.relname = 'messages' AND child.relname = 'messages_default'
              ) THEN
                CREATE TABLE public.messages_default PARTITION OF public.messages DEFAULT;
              END IF;
            END;
            $$;
            """,
        ),
    )

    # 4. Function to create monthly partitions on demand and ensure local indexes.
    conn.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION public.messages_create_partition_and_route()
            RETURNS TRIGGER AS $$
            DECLARE
              partition_start TIMESTAMPTZ;
              partition_end   TIMESTAMPTZ;
              partition_name  TEXT;
              full_name       TEXT;
            BEGIN
              partition_start := date_trunc('month', NEW.created_at);
              partition_end   := (partition_start + interval '1 month');
              partition_name  := format('messages_y%sm%s',
                                        to_char(partition_start, 'YYYY'),
                                        to_char(partition_start, 'MM'));
              full_name := format('public.%I', partition_name);

              IF NOT EXISTS (
                SELECT 1
                FROM pg_inherits
                JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
                JOIN pg_class child ON pg_inherits.inhrelid = child.oid
                WHERE parent.relname = 'messages'
                  AND child.relname = partition_name
              ) THEN
                EXECUTE format(
                  'CREATE TABLE %s PARTITION OF public.messages
                     FOR VALUES FROM (%L) TO (%L)',
                  full_name, partition_start, partition_end
                );

                -- Local index on (conversation_id, created_at) for pagination.
                EXECUTE format(
                  'CREATE INDEX IF NOT EXISTS %I ON %s (conversation_id, created_at)',
                  partition_name || '_conversation_created_idx',
                  full_name
                );
              END IF;

              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """,
        ),
    )

    # 5. Trigger to create partitions before insert; PostgreSQL will route rows.
    conn.execute(
        text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1
                FROM pg_trigger
                WHERE tgname = 'messages_partition_trigger'
              ) THEN
                CREATE TRIGGER messages_partition_trigger
                BEFORE INSERT ON public.messages
                FOR EACH ROW EXECUTE FUNCTION public.messages_create_partition_and_route();
              END IF;
            END;
            $$;
            """,
        ),
    )

    # 6. Backfill from legacy messages_old if it exists.
    if has_messages:
        conn.execute(
            text(
                """
                INSERT INTO public.messages (
                  id,
                  conversation_id,
                  role,
                  content,
                  tokens,
                  latency_ms,
                  tool_calls,
                  provider,
                  model,
                  created_at
                )
                SELECT
                  id,
                  conversation_id,
                  role,
                  content,
                  tokens,
                  latency_ms,
                  tool_calls,
                  provider,
                  model,
                  created_at
                FROM public.messages_old
                ORDER BY created_at, id;
                """,
            ),
        )

        # Optionally keep messages_old as an archive; do not drop automatically.


def downgrade() -> None:
    conn = op.get_bind()

    # Best-effort rollback: drop partitioned table and restore messages_old if present.
    has_old = conn.execute(
        text("SELECT to_regclass('public.messages_old') IS NOT NULL"),
    ).scalar()

    if has_old:
        conn.execute(text("DROP TABLE IF EXISTS public.messages CASCADE"))
        conn.execute(text("ALTER TABLE public.messages_old RENAME TO messages"))
    else:
        conn.execute(text("DROP TABLE IF EXISTS public.messages CASCADE"))

