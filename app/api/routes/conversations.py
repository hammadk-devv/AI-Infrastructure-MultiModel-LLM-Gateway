from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_request_context
from app.application.auth.context import RequestContext
from app.domain.conversations import (
    Conversation,
    Message,
    conversation_to_export_json,
)
from app.infrastructure.db import get_db_session
from app.infrastructure.repositories.conversations import (
    ConversationPage,
    ConversationRepository,
    MessagePage,
)


router = APIRouter(tags=["conversations"])


@router.get("/conversations", response_model=dict[str, Any])
async def list_conversations(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ConversationRepository(session)
    page: ConversationPage = await repo.list_conversations(
        user_id=ctx.principal.user_id,
        limit=limit,
        cursor=cursor,
    )
    return {
        "items": [asdict(c) for c in page.items],
        "next_cursor": page.next_cursor,
    }


@router.post("/conversations", response_model=dict[str, Any])
async def create_conversation(
    payload: dict[str, Any],
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    title = str(payload.get("title") or "Conversation")
    metadata = dict(payload.get("metadata") or {})
    repo = ConversationRepository(session)
    conv = await repo.create_conversation(
        id=str(uuid4()),
        user_id=ctx.principal.user_id,
        org_id=ctx.principal.org_id,
        title=title,
        metadata=metadata,
    )
    return asdict(conv)


@router.get("/conversations/{conversation_id}", response_model=dict[str, Any])
async def get_conversation(
    conversation_id: str,
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ConversationRepository(session)
    conv = await repo.get_conversation(conversation_id)
    if conv is None or conv.user_id != ctx.principal.user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return asdict(conv)


@router.get("/conversations/{conversation_id}/messages", response_model=dict[str, Any])
async def list_messages(
    conversation_id: str,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ConversationRepository(session)
    conv = await repo.get_conversation(conversation_id)
    if conv is None or conv.user_id != ctx.principal.user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    page: MessagePage = await repo.list_messages(
        conversation_id=conversation_id,
        limit=limit,
        cursor=cursor,
    )
    return {
        "items": [asdict(m) for m in page.items],
        "next_cursor": page.next_cursor,
    }


@router.post("/conversations/{conversation_id}/messages", response_model=dict[str, Any])
async def add_message(
    conversation_id: str,
    payload: dict[str, Any],
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ConversationRepository(session)
    conv = await repo.get_conversation(conversation_id)
    if conv is None or conv.user_id != ctx.principal.user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message = Message(
        id=str(uuid4()),
        conversation_id=conversation_id,
        role=str(payload.get("role") or "user"),
        content=str(payload.get("content") or ""),
        provider=str(payload.get("provider") or ""),
        model=str(payload.get("model") or ""),
        tokens=int(payload.get("tokens") or 0),
        latency_ms=int(payload.get("latency_ms") or 0),
        tool_calls=list(payload.get("tool_calls") or []),
    )
    await repo.add_message(message=message)
    return asdict(message)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    repo = ConversationRepository(session)
    conv = await repo.get_conversation(conversation_id)
    if conv is None or conv.user_id != ctx.principal.user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # Soft-delete via status; optimistic locking could be added via updated_at checks.
    await session.execute(
        text(
            "UPDATE conversations SET status = 'deleted' WHERE id = :id",
        ),
        {"id": conversation_id},
    )
    await session.commit()
    return Response(status_code=204)


@router.get("/conversations/search", response_model=dict[str, Any])
async def search_conversations(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    repo = ConversationRepository(session)
    messages = await repo.search_messages(
        user_id=ctx.principal.user_id,
        query=q,
        limit=limit,
    )
    return {
        "items": [asdict(m) for m in messages],
    }

