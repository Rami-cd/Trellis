from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.user import User
from app.auth.router import current_active_user
from app.db.connection import get_session
from app.db.repository import (
    upsert_repository,
    get_repository,
    get_repositories_by_user,
    delete_repository,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])

class RepositoryCreate(BaseModel):
    name: str
    path: str
    languages: list[str] = []

class RepositoryResponse(BaseModel):
    id: str
    name: str
    path: str
    languages: list[str] = []

async def _get_repo_or_404(
    repo_id: str,
    user: User,
    session: AsyncSession,
) -> dict:
    row = await get_repository(session, repo_id)

    if not row:
        raise HTTPException(status_code=404, detail="Repository not found")
    if str(row["user_id"]) != str(user.id):
        raise HTTPException(status_code=403, detail="Not your repository")

    return row


@router.post("/", response_model=RepositoryResponse)
async def create_repository(
    body: RepositoryCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> RepositoryResponse:
    repo_id = str(uuid.uuid4())

    await upsert_repository(
        session,
        repo_id=repo_id,
        name=body.name,
        path=body.path,
        languages=body.languages,
        user_id=str(user.id),
    )

    return RepositoryResponse(
        id=repo_id,
        name=body.name,
        path=body.path,
        languages=body.languages,
    )


@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[RepositoryResponse]:
    rows = await get_repositories_by_user(session, str(user.id))

    return [
        RepositoryResponse(
            id=row["id"],
            name=row["name"],
            path=row["path"],
            languages=list(row["languages"]),
        )
        for row in rows
    ]


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository_route(
    repo_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> RepositoryResponse:
    row = await _get_repo_or_404(repo_id, user, session)

    return RepositoryResponse(
        id=row["id"],
        name=row["name"],
        path=row["path"],
        languages=list(row["languages"]),
    )


@router.delete("/{repo_id}", status_code=204, response_model=None)
async def delete_repository_route(
    repo_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _get_repo_or_404(repo_id, user, session)
    await delete_repository(session, repo_id)