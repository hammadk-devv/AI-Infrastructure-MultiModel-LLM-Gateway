from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass(slots=True)
class Message:
    id: str
    conversation_id: str
    role: str
    content: str
    provider: str
    model: str
    tokens: int
    latency_ms: int
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


@dataclass(slots=True)
class Conversation:
    id: str
    user_id: str
    org_id: str
    title: str
    metadata: dict[str, Any]
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None


def conversation_to_export_json(
    conversation: Conversation,
    messages: list[Message],
) -> dict[str, Any]:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "status": conversation.status.value,
        "metadata": conversation.metadata,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "last_message_at": conversation.last_message_at.isoformat()
        if conversation.last_message_at
        else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "provider": m.provider,
                "model": m.model,
                "tokens": m.tokens,
                "latency_ms": m.latency_ms,
                "tool_calls": m.tool_calls,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


def conversation_to_export_markdown(
    conversation: Conversation,
    messages: list[Message],
) -> str:
    lines: list[str] = []
    lines.append(f"# {conversation.title}")
    lines.append("")
    for m in messages:
        lines.append(f"## {m.role} ({m.provider}/{m.model})")
        lines.append("")
        lines.append(m.content)
        lines.append("")
    return "\n".join(lines)

