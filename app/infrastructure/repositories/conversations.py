from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Select, desc, func, select, text, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.conversations import Conversation, ConversationStatus, Message
from app.infrastructure.models import ConversationModel, MessageModel


@dataclass(slots=True)
class ConversationPage:
    items: list[Conversation]
    next_cursor: str | None


@dataclass(slots=True)
class MessagePage:
    items: list[Message]
    next_cursor: str | None


class ConversationRepository:
    """Async repository for conversations and messages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_conversation(
        self,
        *,
        id: str,
        user_id: str,
        org_id: str,
        title: str,
        metadata: dict[str, Any],
    ) -> Conversation:
        model = ConversationModel(
            id=id,
            user_id=user_id,
            org_id=org_id,
            title=title,
            metadata_json=metadata,
            status=ConversationStatus.ACTIVE.value,
        )
        self._session.add(model)
        await self._session.commit()
        return self._to_domain_conversation(model)

    async def get_conversation(self, conv_id: str) -> Conversation | None:
        model = await self._session.get(ConversationModel, conv_id)
        if model is None:
            return None
        return self._to_domain_conversation(model)

    async def list_conversations(
        self,
        *,
        user_id: str,
        limit: int,
        cursor: str | None = None,
    ) -> ConversationPage:
        stmt: Select[tuple[ConversationModel]] = select(ConversationModel).where(
            ConversationModel.user_id == user_id,
        )
        if cursor:
            cursor_created_at, cursor_id = self._decode_cursor(cursor)
            stmt = stmt.where(
                (ConversationModel.created_at < cursor_created_at)
                | (
                    (ConversationModel.created_at == cursor_created_at)
                    & (ConversationModel.id < cursor_id)
                ),
            )
        stmt = stmt.order_by(
            desc(ConversationModel.created_at),
            desc(ConversationModel.id),
        ).limit(limit + 1)

        result = await self._session.execute(stmt)
        rows: Sequence[ConversationModel] = result.scalars().all()

        items = [self._to_domain_conversation(m) for m in rows[:limit]]
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = self._encode_cursor(last.created_at, last.id)
        return ConversationPage(items=items, next_cursor=next_cursor)

    async def add_message(
        self,
        *,
        message: Message,
    ) -> None:
        model = MessageModel(
            id=message.id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            tokens=message.tokens,
            latency_ms=message.latency_ms,
            tool_calls=message.tool_calls,
            provider=message.provider,
            model=message.model,
            created_at=message.created_at,
        )
        self._session.add(model)
        await self._session.execute(
            text(
                """
                UPDATE conversations
                SET last_message_at = :created_at, updated_at = :created_at
                WHERE id = :conversation_id
                """,
            ),
            {
                "created_at": message.created_at,
                "conversation_id": message.conversation_id,
            },
        )
        await self._session.commit()

        # SQLite-compatible batch insert
        stmt = insert(MessageModel).values(
            [
                {
                    "id": m.id,
                    "conversation_id": m.conversation_id,
                    "role": m.role,
                    "content": m.content,
                    "tokens": m.tokens,
                    "latency_ms": m.latency_ms,
                    "tool_calls": m.tool_calls,
                    "provider": m.provider,
                    "model": m.model,
                    "created_at": m.created_at,
                }
                for m in messages
            ],
        )
        # Use prefixes or other methods if needed, but for now we just try/except or skip conflict
        # SQLite insert or ignore:
        stmt = stmt.prefix_with("OR IGNORE")
        await self._session.execute(stmt)
        await self._session.commit()

    async def list_messages(
        self,
        *,
        conversation_id: str,
        limit: int,
        cursor: str | None = None,
    ) -> MessagePage:
        stmt: Select[tuple[MessageModel]] = select(MessageModel).where(
            MessageModel.conversation_id == conversation_id,
        )
        if cursor:
            cursor_created_at, cursor_id = self._decode_cursor(cursor)
            stmt = stmt.where(
                (MessageModel.created_at < cursor_created_at)
                | (
                    (MessageModel.created_at == cursor_created_at)
                    & (MessageModel.id < cursor_id)
                ),
            )
        stmt = stmt.order_by(
            desc(MessageModel.created_at),
            desc(MessageModel.id),
        ).limit(limit + 1)
        result = await self._session.execute(stmt)
        rows: Sequence[MessageModel] = result.scalars().all()
        items = [self._to_domain_message(m) for m in rows[:limit]]
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = self._encode_cursor(last.created_at, last.id)
        return MessagePage(items=items, next_cursor=next_cursor)

    async def get_metrics_summary(self, hours: int) -> dict[str, Any]:
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Calculate totals
        stmt = select(
            func.sum(MessageModel.tokens).label("total_tokens"),
            func.count(MessageModel.id).label("total_requests"),
            func.avg(MessageModel.latency_ms).label("avg_latency")
        ).where(MessageModel.created_at >= start_time)
        
        result = await self._session.execute(stmt)
        row = result.fetchone()
        
        return {
            "total_tokens": row.total_tokens or 0,
            "total_requests": row.total_requests or 0,
            "avg_latency": row.avg_latency or 0,
        }

    async def get_model_performance(self, hours: int) -> list[dict[str, Any]]:
        start_time = datetime.now() - timedelta(hours=hours)
        
        stmt = select(
            MessageModel.model,
            MessageModel.provider,
            func.count(MessageModel.id).label("requests"),
            func.avg(MessageModel.latency_ms).label("avg_latency"),
            func.sum(MessageModel.tokens).label("total_tokens")
        ).where(MessageModel.created_at >= start_time).group_by(MessageModel.model, MessageModel.provider)
        
        result = await self._session.execute(stmt)
        return [
            {
                "model_name": row.model,
                "provider": row.provider,
                "requests": row.requests,
                "avg_latency": row.avg_latency,
                "total_tokens": row.total_tokens,
                "success_rate": 100.0, # Placeholder until error tracking is better
                "total_cost": (row.total_tokens / 1000) * 0.01 # Rough estimation
            }
            for row in result.fetchall()
        ]

    async def list_all_conversations(self, limit: int = 100) -> list[Conversation]:
        stmt = select(ConversationModel).order_by(desc(ConversationModel.created_at)).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_domain_conversation(m) for m in result.scalars().all()]

    @staticmethod
    def _encode_cursor(created_at: datetime, id_: str) -> str:
        return f"{created_at.isoformat()}::{id_}"

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, str]:
        created_at_str, id_ = cursor.split("::", 1)
        return datetime.fromisoformat(created_at_str), id_

    @staticmethod
    def _to_domain_conversation(model: ConversationModel) -> Conversation:
        return Conversation(
            id=model.id,
            user_id=model.user_id,
            org_id=model.org_id,
            title=model.title,
            metadata=model.metadata_json or {},
            status=ConversationStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_message_at=model.last_message_at,
        )

    @staticmethod
    def _to_domain_message(model: MessageModel) -> Message:
        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            role=model.role,
            content=model.content,
            provider=model.provider,
            model=model.model,
            tokens=model.tokens,
            latency_ms=model.latency_ms,
            tool_calls=model.tool_calls or [],
            created_at=model.created_at,
        )

