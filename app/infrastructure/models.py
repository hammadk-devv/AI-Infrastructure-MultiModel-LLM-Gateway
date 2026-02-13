from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, text, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column



class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class ApiKeyModel(Base):
    """SQLAlchemy model backing the ApiKey domain entity."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(length=64),
        primary_key=True,
    )
    org_id: Mapped[str] = mapped_column(String(length=64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(length=64), nullable=False)
    name: Mapped[str] = mapped_column(String(length=255), nullable=False)

    # Stable SHA-256 hash of the full key, used for lookups and indexing.
    key_hash: Mapped[str] = mapped_column(
        String(length=64),
        nullable=False,
        unique=True,
    )

    # Bcrypt hash stored for at-rest security.
    bcrypt_hash: Mapped[str] = mapped_column(String(length=255), nullable=False)

    preview: Mapped[str] = mapped_column(String(length=16), nullable=False)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Permissions, including rate limits, stored as JSON for flexibility.
    permissions: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_api_keys_key_hash", "key_hash", unique=True),
        Index("ix_api_keys_org_id", "org_id"),
        Index("ix_api_keys_user_id", "user_id"),
    )


class ConversationModel(Base):
    """Conversation aggregate."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(length=36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(length=64), nullable=False)
    org_id: Mapped[str] = mapped_column(String(length=64), nullable=False)
    title: Mapped[str] = mapped_column(String(length=255), nullable=False)
    # Use a different attribute name to avoid clashing with DeclarativeBase.metadata,
    # but keep the underlying column name as "metadata".
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(
        String(length=16),
        nullable=False,
        default="active",
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_conversations_user_id", "user_id"),
        Index("idx_conversations_created_at", "created_at"),
    )


class MessageModel(Base):
    """Message belonging to a conversation."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(length=36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(length=36),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(length=50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_calls: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    provider: Mapped[str] = mapped_column(String(length=50), nullable=False)
    model: Mapped[str] = mapped_column(String(length=100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # tsvector column for full-text search; managed via migrations/triggers.
    search_vector: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    __table_args__ = (
        Index(
            "idx_messages_conversation_created",
            "conversation_id",
            "created_at",
        ),
    )


class ModelConfigModel(Base):
    """Configuration for LLM models."""

    __tablename__ = "model_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    context_window: Mapped[int] = mapped_column(Integer, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    capabilities: Mapped[str] = mapped_column(String, nullable=False, default="[]")
    cost_per_1k_input: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    cost_per_1k_output: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)
    priority: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("uq_model_provider_name", "provider", "model_name", unique=True),
        Index("ix_model_configs_active_priority", "is_active", "priority"),
        Index("ix_model_configs_capabilities", "capabilities"),
    )


class AuditLogModel(Base):
    """Audit logs for configuration changes with tamper-evident chaining."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True) # user_id
    event_type: Mapped[str] = mapped_column(String(50), nullable=False) # action
    target_type: Mapped[str] = mapped_column(String(50), nullable=False) # entity_type
    target_id: Mapped[str] = mapped_column(String(64), nullable=False) # entity_id
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    
    # Cryptographic chaining
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        Index("ix_audit_logs_target", "target_type", "target_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_hash", "hash", unique=True),
    )
