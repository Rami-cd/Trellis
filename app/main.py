from fastapi import FastAPI
from pathlib import Path
import os
from app.auth.router import router as auth_router
from app.api.repository import router as repository_router

app = FastAPI(title="Trellis Backend")

app.include_router(auth_router)
app.include_router(repository_router)

REPO_PATH = Path(os.environ.get("TRELLIS_REPO_PATH", "/repos/target"))

@app.get("/health")
def health():
    return {"status": "ok"}