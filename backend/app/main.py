from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import API_PREFIX, APP_NAME

app = FastAPI(title=APP_NAME)
app.include_router(health_router, prefix=API_PREFIX)
