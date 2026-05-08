from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.repository import _get_repo_or_404
from app.auth.router import current_active_user
from app.auth.user import User
from app.db.connection import get_session
from app.db.repository import (
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
)

router = APIRouter(tags=["conversations"])


class ConversationCreateResponse(BaseModel):
    conversation_id: str


class ConversationResponse(BaseModel):
    id: str
    repo_id: str
    user_id: str
    title: str | None = None
    created_at: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    nodes_used: dict | list | None = None
    created_at: str


async def _get_owned_conversation_or_404(
    conversation_id: str,
    user: User,
    session: AsyncSession,
) -> dict:
    row = await get_conversation(session, conversation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if str(row["user_id"]) != str(user.id):
        raise HTTPException(status_code=403, detail="Not your conversation")
    return row


@router.post("/repositories/{repo_id}/conversations", response_model=ConversationCreateResponse)
async def create_conversation_route(
    repo_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> ConversationCreateResponse:
    await _get_repo_or_404(repo_id, user, session)
    conversation_id = await create_conversation(session, repo_id, str(user.id))
    return ConversationCreateResponse(conversation_id=conversation_id)


@router.get("/repositories/{repo_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations_route(
    repo_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[ConversationResponse]:
    await _get_repo_or_404(repo_id, user, session)
    rows = await list_conversations(session, repo_id, str(user.id))
    return [
        ConversationResponse(
            id=row["id"],
            repo_id=row["repo_id"],
            user_id=str(row["user_id"]),
            title=row["title"],
            created_at=row["created_at"].isoformat(),
        )
        for row in rows
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages_route(
    conversation_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    await _get_owned_conversation_or_404(conversation_id, user, session)
    rows = await list_messages(session, conversation_id)
    return [
        MessageResponse(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            nodes_used=row["nodes_used"],
            created_at=row["created_at"].isoformat(),
        )
        for row in rows
    ]