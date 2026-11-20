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


def is_arabic_script(text: str) -> bool:
    return any(
        "\u0600" <= char <= "\u06ff"
        or "\u0750" <= char <= "\u077f"
        or "\u08a0" <= char <= "\u08ff"
        or "\ufb50" <= char <= "\ufdff"
        or "\ufe70" <= char <= "\ufeff"
        for char in text
    )


async def greeting_events(answer: str) -> AsyncIterator[str]:
    yield event("sources", {"sources": []})
    yield event("delta", {"text": answer})
    yield event("done", {"status": "complete"})


async def chat_events(request: ChatRequest, sources: list[dict], evidence: list[dict], key: str) -> AsyncIterator[str]:
    yield event("sources", {"sources": sources})
    if not evidence:
        answer = (
            "لم أجد معلومات ذات صلة في البيانات المتاحة."
            if is_arabic_script(request.message)
            else "I could not find relevant information in the indexed data."
        )
        yield event("delta", {"text": answer})
        yield event("done", {"status": "complete"})
        return
    try:
        async for text in groq_tokens(request, evidence, key):
            yield event("delta", {"text": text})
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.warning("Groq request failed with HTTP %s.", status)
        if status in (401, 403):
            message = "Groq authentication failed. Check the API key and account access."
        elif status == 429:
            message = "Groq rate limit reached. Please try again later."
        elif status in (400, 404):
            message = "Groq rejected the request. Check the configured model and account access."
        else:
            message = "The language model is unavailable. Please try again."
        yield event("error", {"code": "upstream_unavailable", "message": message})
        return
    except httpx.TimeoutException:
        logger.warning("Groq request timed out.")
        yield event("error", {"code": "upstream_unavailable", "message": "The language model timed out. Please try again."})
        return
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as exc:
        logger.warning("Groq streaming request failed: %s.", type(exc).__name__)
        yield event("error", {"code": "upstream_unavailable", "message": "The language model is unavailable. Please try again."})
        return
    yield event("done", {"status": "complete"})


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    greeting = request.message.casefold().strip(" \t\r\n!.,?؟،")
    greetings = {
        "hi": "Hello! How can I help you explore DarGlobal or Wasalt?",
        "hello": "Hello! How can I help you explore DarGlobal or Wasalt?",
        "hey": "Hello! How can I help you explore DarGlobal or Wasalt?",
        "مرحبا": "مرحباً! كيف يمكنني مساعدتك في استكشاف دار جلوبال أو وصلت؟",
        "السلام عليكم": "وعليكم السلام! كيف يمكنني مساعدتك في استكشاف دار جلوبال أو وصلت؟",
    }
    if greeting in greetings:
        return StreamingResponse(
            greeting_events(greetings[greeting]),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
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
