import json
import logging
import os
import sqlite3
from typing import AsyncIterator

import httpx
from chromadb.errors import ChromaError
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest
from app.services.chat import groq_tokens, retrieve

router = APIRouter()
logger = logging.getLogger(__name__)


def event(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def chat_events(request: ChatRequest, sources: list[dict], evidence: list[dict], key: str) -> AsyncIterator[str]:
    yield event("sources", {"sources": sources})
    if not evidence:
        yield event("delta", {"text": "I could not find relevant information in the indexed data."})
        yield event("done", {"status": "complete"})
        return
    try:
        async for text in groq_tokens(request, evidence, key):
            yield event("delta", {"text": text})
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        logger.warning("Groq streaming request failed.")
        yield event("error", {"code": "upstream_unavailable", "message": "The language model is unavailable. Please try again."})
        return
    yield event("done", {"status": "complete"})


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured.")
    try:
        sources, evidence = await run_in_threadpool(retrieve, request.message)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, sqlite3.Error, ChromaError):
        logger.warning("Chat index is unavailable.", exc_info=True)
        raise HTTPException(status_code=503, detail="Search index is unavailable.") from None
    return StreamingResponse(
        chat_events(request, sources, evidence, key),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
