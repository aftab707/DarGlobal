from fastapi import FastAPI

from app.core.config import API_PREFIX, APP_NAME
from app.api.chat import router as chat_router
from app.api.health import router as health_router

app = FastAPI(title=APP_NAME)
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)
