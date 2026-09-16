"""
Application Configuration Settings Module
Reads configuration settings from environment variables safely without hard-coded secrets.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env if present (keeps secrets out of source code)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    PROJECT_NAME: str = "Van Udyan Biodiversity Intelligence Platform API"
    API_V1_STR: str = "/api/v1"

    @property
    def DATABASE_URL(self) -> str:
        url = os.environ.get("DATABASE_URL")
        if url:
            return url

        host = os.environ.get("PGHOST", "localhost")
        port = os.environ.get("PGPORT", "5432")
        user = os.environ.get("PGUSER", "postgres")
        password = os.environ.get("PGPASSWORD", "postgres")
        dbname = os.environ.get("PGDATABASE", "van_udyan_db")

        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    @property
    def PLANTNET_API_KEY(self) -> str:
        return os.environ.get("PLANTNET_API_KEY", "")

    @property
    def NGO_ADMIN_PASSWORD(self) -> str:
        return os.environ.get("NGO_ADMIN_PASSWORD", "rswf-admin-pass")

    CORS_ORIGINS: list = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

settings = Settings()
