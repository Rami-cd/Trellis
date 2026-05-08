from __future__ import annotations

import asyncio
import shutil
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import current_active_user
from app.auth.user import User
from app.db.connection import get_session
from app.db.repository import upsert_repository

router = APIRouter(prefix="/repositories", tags=["upload"])

REPOS_ROOT = Path("/repos")


class UploadRepositoryResponse(BaseModel):
    repo_id: str
    path: str


def _name_from_git_url(url: str) -> str:
    trimmed = url.rstrip("/")
    name = trimmed.rsplit("/", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name or "repository"


def _safe_extract_zip(archive_path: Path, target_dir: Path) -> None:
    with zipfile.ZipFile(archive_path) as zip_file:
        for member in zip_file.infolist():
            member_path = (target_dir / member.filename).resolve()
            if target_dir.resolve() not in member_path.parents and member_path != target_dir.resolve():
                raise ValueError("Zip file contains invalid paths")
        zip_file.extractall(target_dir)


@router.post("/upload", response_model=UploadRepositoryResponse)
async def upload_repository(
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> UploadRepositoryResponse:
    if (file is None and not url) or (file is not None and url):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of file or url",
        )

    repo_id = str(uuid.uuid4())
    user_id = str(user.id)
    repo_dir = REPOS_ROOT / user_id / repo_id
    archive_path = repo_dir.parent / f"{repo_id}.zip"

    try:
        repo_dir.parent.mkdir(parents=True, exist_ok=True)

        if file is not None:
            if not file.filename or not file.filename.lower().endswith(".zip"):
                raise HTTPException(status_code=400, detail="Uploaded file must be a zip archive")

            repo_dir.mkdir(parents=True, exist_ok=False)

            with archive_path.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    output.write(chunk)

            _safe_extract_zip(archive_path, repo_dir)
            archive_path.unlink(missing_ok=True)
            name = Path(file.filename).stem
        else:
            name = _name_from_git_url(url or "")
            process = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                "--depth",
                "1",
                url or "",
                str(repo_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                error_message = stderr.decode("utf-8", errors="replace").strip() or "git clone failed"
                raise HTTPException(status_code=400, detail=error_message)

        await upsert_repository(
            session,
            repo_id=repo_id,
            name=name,
            path=str(repo_dir),
            languages=[],
            user_id=user_id,
        )

        return UploadRepositoryResponse(repo_id=repo_id, path=str(repo_dir))
    except Exception:
        shutil.rmtree(repo_dir, ignore_errors=True)
        archive_path.unlink(missing_ok=True)
        raise
    finally:
        if file is not None:
            await file.close()
