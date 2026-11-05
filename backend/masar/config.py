"""Central settings. Everything is configurable through ../.env."""
from __future__ import annotations

import os
import secrets
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]          # .../masar
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

DUCKDB_PATH = DATA_DIR / "masar.duckdb"      # analytics store (synthetic bank + market history)
SQLITE_PATH = DATA_DIR / "app.sqlite"        # app state (users, audit log, alerts, live events)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "").strip()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
WEB_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

# Synthetic data window (12 months ending "today" of the demo)
AS_OF = date(2026, 11, 5)
HISTORY_MONTHS = 12

DEMO_PASSWORD = "Masar@2026"


def _jwt_secret() -> str:
    env = os.getenv("JWT_SECRET", "").strip()
    if env:
        return env
    f = DATA_DIR / ".jwt_secret"
    if not f.exists():
        f.write_text(secrets.token_urlsafe(48))
    return f.read_text().strip()


JWT_SECRET = _jwt_secret()
JWT_HOURS = 8
COOKIE_NAME = "masar_session"
