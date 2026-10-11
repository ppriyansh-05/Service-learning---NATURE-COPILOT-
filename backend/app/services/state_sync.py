"""
State persistence layer for the JSON stores that live under data/processed/.

Local dev writes those stores to disk. Cloud deployments add a Postgres `app_state` table on
top so NGO observations, planted plants and health-check visits survive a redeploy on hosts
with ephemeral local disk (Render free, Fly.io machines after restart, etc.).

Flow:
  - On backend startup: pull_all() copies the authoritative DB rows down to disk.
  - On every save:       push(key, value) writes the JSON file first (keeps local dev / tests
                         working), then upserts the same blob into the DB.
  - When no DATABASE_URL is reachable: everything degrades gracefully to JSON-only.

Keys currently synced:
  ngo_observations, planted_plants, plant_monitoring, ai_predictions.
"""

import json
import logging
import os
import threading
from typing import Any, Optional

from app.core.config import settings

log = logging.getLogger("van-udyan.state_sync")

_lock = threading.Lock()
_enabled: Optional[bool] = None  # None = not probed yet; True/False = decided


def _env_opt_in() -> bool:
    """
    state_sync is opt-in — set ENABLE_STATE_SYNC=true in your deployment environment.
    Default is OFF so local dev / tests never leak data into (or pull data from) the DB.
    """
    v = os.environ.get("ENABLE_STATE_SYNC", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _try_create_table() -> bool:
    """Creates the app_state table on first use. Returns True on success."""
    try:
        from sqlalchemy import text
        from app.db.session import engine
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """))
        return True
    except Exception as e:
        log.info("state_sync: database unavailable, falling back to local JSON only (%s)", e)
        return False


def is_enabled() -> bool:
    """True when the Postgres sync layer is both opted into (ENABLE_STATE_SYNC) and reachable."""
    global _enabled
    if not _env_opt_in():
        return False
    if _enabled is None:
        with _lock:
            if _enabled is None:
                _enabled = _try_create_table()
    return _enabled


def pull(key: str, local_json_path: str) -> bool:
    """
    Copies the DB row for `key` into local_json_path if the DB has newer or non-existent-locally data.
    Returns True if the local file was written from the DB.
    """
    if not is_enabled():
        return False
    try:
        from sqlalchemy import text
        from app.db.session import engine
        with engine.connect() as conn:
            row = conn.execute(text("SELECT value FROM app_state WHERE key = :k"), {"k": key}).fetchone()
        if row is None:
            # DB has nothing yet; keep local JSON as the source of truth
            return False
        value = row[0]
        os.makedirs(os.path.dirname(local_json_path), exist_ok=True)
        with open(local_json_path, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2)
        return True
    except Exception as e:
        log.warning("state_sync.pull(%s) failed: %s", key, e)
        return False


def push(key: str, value: Any) -> bool:
    """Upserts the JSON-serialisable `value` into the DB under `key`. Silent no-op when disabled."""
    if not is_enabled():
        return False
    try:
        from sqlalchemy import text
        from app.db.session import engine
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO app_state (key, value, updated_at)
                    VALUES (:k, CAST(:v AS JSONB), now())
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value, updated_at = now()
                """),
                {"k": key, "v": json.dumps(value)},
            )
        return True
    except Exception as e:
        log.warning("state_sync.push(%s) failed: %s", key, e)
        return False


# Default (key -> file path) mapping for the stores we persist across redeploys
def _processed_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "processed"))


DEFAULT_KEYS = {
    "ngo_observations": "ngo_observations_store.json",
    "planted_plants": "planted_plants_store.json",
    "plant_monitoring": "plant_monitoring_store.json",
    "ai_predictions": "ai_predictions_store.json",
}


def pull_all() -> dict:
    """Pulls every known store from the DB into its JSON file. Called once at app startup."""
    results = {}
    for key, filename in DEFAULT_KEYS.items():
        path = os.path.join(_processed_dir(), filename)
        results[key] = pull(key, path)
    return results


def push_all_from_disk() -> dict:
    """
    One-time: upload every local JSON store to the DB. Called by the migration script to seed
    a fresh cloud database from an existing local install.
    """
    results = {}
    for key, filename in DEFAULT_KEYS.items():
        path = os.path.join(_processed_dir(), filename)
        if not os.path.exists(path):
            results[key] = False
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                value = json.load(f)
            results[key] = push(key, value)
        except Exception as e:
            log.warning("state_sync.push_all_from_disk(%s) failed: %s", key, e)
            results[key] = False
    return results
