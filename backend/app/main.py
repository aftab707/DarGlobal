from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

from app.core.config import API_PREFIX, APP_NAME
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.frontend import FrontendFiles
from app.services.chat import vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(vector_store)
    try:
        yield
    finally:
        vector_store.cache_clear()


app = FastAPI(title=APP_NAME, lifespan=lifespan)
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)
frontend_dist = os.environ.get("FRONTEND_DIST")
if frontend_dist:
    app.mount("/", FrontendFiles(directory=frontend_dist, html=True), name="frontend")
