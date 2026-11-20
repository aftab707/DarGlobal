import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
os.environ["LANGSMITH_TRACING"] = "false"

APP_NAME = "DarGlobal and Wasalt Chatbot"
API_PREFIX = "/api"
