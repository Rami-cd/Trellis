from __future__ import annotations

import asyncio
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.repository import _get_repo_or_404
from app.auth.router import current_active_user
from app.auth.user import User
from app.db.connection import get_session
from app.db.repository import (
    create_conversation,
    create_message,
    fetch_by_repo,
    get_conversation,
    get_nodes_by_ids,
    get_subgraph,
)
from app.llm.gemini import GeminiLLM
from app.llm.embedding.jina_embedder import JinaEmbedder
from app.services.prompt_builder import build_explanation_prompt
from app.services.search.bm25 import BM25Index
from app.services.search.hybrid import HybridSearch
from app.services.search.vector import VectorSearch
from app.schemas.node import CodeNodeType

from typing import AsyncGenerator

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    top_k: int = 5
    depth: int = 2


async def _get_owned_conversation_for_repo_or_404(
    conversation_id: str,
    repo_id: str,
    user: User,
    session: AsyncSession,
) -> dict:
    row = await get_conversation(session, conversation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if str(row["user_id"]) != str(user.id):
        raise HTTPException(status_code=403, detail="Not your conversation")
    if row["repo_id"] != repo_id:
        raise HTTPException(status_code=400, detail="Conversation does not belong to this repository")
    return row


@router.post("/repositories/{repo_id}/chat")
async def chat_route(
    repo_id: str,
    body: ChatRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    await _get_repo_or_404(repo_id, user, session)

    if body.conversation_id is None:
        conversation_id = await create_conversation(session, repo_id, str(user.id))
    else:
        conversation = await _get_owned_conversation_for_repo_or_404(
            body.conversation_id,
            repo_id,
            user,
            session,
        )
        conversation_id = conversation["id"]

    await create_message(
        session,
        conversation_id=conversation_id,
        role="user",
        content=body.message,
        nodes_used=None,
    )

    async def stream() -> AsyncGenerator[str, None]:
        try:
            indexed_nodes = await fetch_by_repo(session, repo_id)
            searchable_nodes = [
                node
                for node in indexed_nodes
                if node.type in {CodeNodeType.FUNCTION, CodeNodeType.CLASS}
            ]
            indexed_node_lookup = {
                node.id: {
                    "id": node.id,
                    "qualified_name": node.qualified_name,
                    "type": node.type.value,
                    "summary": node.summary,
                    "raw_source": node.raw_source,
                }
                for node in indexed_nodes
            }

            bm25 = BM25Index()
            bm25.build(searchable_nodes)

            hybrid = HybridSearch(
                bm25=bm25,
                vector=VectorSearch(session),
                embedder=JinaEmbedder(),
            )
            seed_ids = await hybrid.search(
                body.message,
                repo_id=repo_id,
                top_k=body.top_k,
            )

            subgraph = await get_subgraph(session, seed_ids, depth=body.depth)
            node_index = {
                node["id"]: indexed_node_lookup.get(node["id"], node)
                for node in subgraph["nodes"]
            }
            missing_seed_ids = [node_id for node_id in seed_ids if node_id not in node_index]
            for node in await get_nodes_by_ids(session, missing_seed_ids):
                node_index[node["id"]] = indexed_node_lookup.get(node["id"], node)

            seed_set = set(seed_ids)
            seed_nodes = [node_index[node_id] for node_id in seed_ids if node_id in node_index]
            related_nodes = [
                node_index[node["id"]]
                for node in subgraph["nodes"]
                if node["id"] not in seed_set and node["id"] in node_index
            ]

            prompt = build_explanation_prompt(
                query=body.message,
                seed_nodes=seed_nodes,
                related_nodes=related_nodes,
                edges=subgraph["edges"],
                node_index=node_index,
            )

            llm = GeminiLLM()
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            loop = asyncio.get_running_loop()
            answer_parts: list[str] = []
            stream_error: list[Exception] = []

            def produce_chunks() -> None:
                try:
                    for chunk in llm.generate_stream(prompt):
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as exc:  # pragma: no cover - streamed runtime path
                    stream_error.append(exc)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            producer = threading.Thread(target=produce_chunks, daemon=True)
            producer.start()

            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                answer_parts.append(chunk)
                yield chunk

            if stream_error:
                raise stream_error[0]

            answer = "".join(answer_parts)

            await create_message(
                session,
                conversation_id=conversation_id,
                role="assistant",
                content=answer,
                nodes_used=seed_ids,
            )
        except Exception as exc:
            yield f"error: {exc}\n"
            return

    return StreamingResponse(stream(), media_type="text/plain")
