from fastapi import FastAPI
from pathlib import Path
import os
from app.auth.router import router as auth_router
from app.api.repository import router as repository_router
from app.api.indexing import router as indexing_router
from app.api.conversations import router as conversations_router
from app.api.chat import router as chat_router
from app.api.upload import router as upload_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Trellis Backend")

raw_origins = os.getenv("CORS_ORIGINS") or "http://localhost:3000,http://127.0.0.1:3000"
origins = [
    origin.strip()
    for origin in raw_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(repository_router)
app.include_router(indexing_router)
app.include_router(conversations_router)
app.include_router(chat_router)
app.include_router(upload_router)

REPO_PATH = Path(os.environ.get("TRELLIS_REPO_PATH", "/repos/target"))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug-cors")
def debug_cors():
    return {"origins": origins}
