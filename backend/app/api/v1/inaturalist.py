"""OAuth connection and approval-gated publishing to iNaturalist.

Only RSWF-owned planted trees that have been NGO-verified/corrected can be
published. OAuth credentials are encrypted at rest; the NGO admin password
is required for the final publish action.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.core.security import verify_ngo_admin_password
from app.services import photo_storage, state_sync
from app.services.data_service import load_ngo_observations_store, save_ngo_observations_store

router = APIRouter(prefix="/inaturalist", tags=["iNaturalist Publishing"])
log = logging.getLogger("van-udyan.inaturalist")

INAT_SITE = "https://www.inaturalist.org"
OAUTH_STATE_MAX_AGE = 10 * 60
STORE_KEY = "inaturalist_oauth"
_STORE_PATH = Path(__file__).resolve().parents[4] / "data" / "processed" / "inaturalist_oauth.json"
_PHOTO_PATH = re.compile(r"^/uploads/(upload_[A-Za-z0-9_]+\.(?:jpg|jpeg|png|webp))$", re.IGNORECASE)


def _redirect_uri() -> str:
    configured = settings.INATURALIST_REDIRECT_URI
    if configured:
        return configured
    if settings.BACKEND_PUBLIC_URL:
        return settings.BACKEND_PUBLIC_URL + settings.API_V1_STR + "/inaturalist/oauth/callback"
    raise HTTPException(status_code=503, detail="Configure INATURALIST_REDIRECT_URI or BACKEND_PUBLIC_URL on the backend.")


def _frontend_redirect(result: str) -> RedirectResponse:
    base = settings.FRONTEND_PUBLIC_URL.rstrip("/")
    if not base:
        # Do not send the user to an unrelated host if the deployment URL is missing.
        raise HTTPException(status_code=503, detail="Configure FRONTEND_PUBLIC_URL on the backend.")
    return RedirectResponse(f"{base}/?inat={result}#verify", status_code=303)


def _require_oauth_config() -> None:
    missing = []
    if not settings.INATURALIST_CLIENT_ID:
        missing.append("INATURALIST_CLIENT_ID")
    if not settings.INATURALIST_CLIENT_SECRET:
        missing.append("INATURALIST_CLIENT_SECRET")
    if not settings.INATURALIST_TOKEN_ENCRYPTION_KEY:
        missing.append("INATURALIST_TOKEN_ENCRYPTION_KEY")
    if not settings.FRONTEND_PUBLIC_URL:
        missing.append("FRONTEND_PUBLIC_URL")
    if missing:
        raise HTTPException(
            status_code=503,
            detail="iNaturalist publishing is not configured on the backend. Missing: " + ", ".join(missing),
        )
    _redirect_uri()


def _fernet() -> Fernet:
    try:
        return Fernet(settings.INATURALIST_TOKEN_ENCRYPTION_KEY.encode("ascii"))
    except Exception as exc:
        raise RuntimeError("INATURALIST_TOKEN_ENCRYPTION_KEY must be a valid Fernet key.") from exc


def _signed_state() -> str:
    # Signed timestamp + random nonce gives the callback a short-lived CSRF guard
    # without relying on per-process memory (the service may run multiple workers).
    import secrets
    payload = f"{int(time.time())}.{secrets.token_urlsafe(24)}"
    signature = hmac.new(
        settings.INATURALIST_CLIENT_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}.{signature}".encode("utf-8")).decode("ascii").rstrip("=")


def _validate_state(state: str) -> bool:
    try:
        padded = state + ("=" * (-len(state) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        timestamp_text, nonce, signature = decoded.split(".", 2)
        payload = f"{timestamp_text}.{nonce}"
        timestamp = int(timestamp_text)
        age = int(time.time()) - timestamp
        expected = hmac.new(
            settings.INATURALIST_CLIENT_SECRET.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return 0 <= age <= OAUTH_STATE_MAX_AGE and hmac.compare_digest(signature, expected)
    except Exception:
        return False


def _read_encrypted_store() -> dict[str, Any] | None:
    # Supabase/Postgres state is authoritative in deployment; local encrypted
    # storage is only the development fallback.
    if state_sync.is_enabled():
        try:
            from sqlalchemy import text
            from app.db.session import engine
            with engine.connect() as conn:
                row = conn.execute(text("SELECT value FROM app_state WHERE key = :k"), {"k": STORE_KEY}).fetchone()
            if row is not None:
                value = row[0]
                return value if isinstance(value, dict) else json.loads(value)
        except Exception as exc:
            log.error("Could not read encrypted iNaturalist OAuth state from database: %s", exc)
            if settings.IS_PRODUCTION:
                raise RuntimeError("Could not read the encrypted iNaturalist connection from durable storage.") from exc
    if _STORE_PATH.exists():
        try:
            value = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except Exception as exc:
            log.warning("Could not read local iNaturalist OAuth store: %s", exc)
    return None


def _load_token_record() -> dict[str, Any] | None:
    stored = _read_encrypted_store()
    if not stored or not stored.get("ciphertext"):
        return None
    try:
        raw = _fernet().decrypt(stored["ciphertext"].encode("ascii"))
        value = json.loads(raw.decode("utf-8"))
        return value if isinstance(value, dict) and value.get("access_token") else None
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        log.error("Stored iNaturalist OAuth credentials could not be decrypted; reconnect required.")
        return None


def _save_token_record(record: dict[str, Any]) -> None:
    ciphertext = _fernet().encrypt(json.dumps(record).encode("utf-8")).decode("ascii")
    value = {"ciphertext": ciphertext, "updated_at": datetime.now(timezone.utc).isoformat()}
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(value), encoding="utf-8")
    pushed = state_sync.push(STORE_KEY, value)
    if settings.IS_PRODUCTION and not pushed:
        raise RuntimeError("Could not persist the iNaturalist connection to durable database storage.")


def _update_record(record_id: int, changes: dict[str, Any]) -> dict[str, Any]:
    records = load_ngo_observations_store()
    record = next((item for item in records if int(item.get("id", -1)) == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="RSWF observation not found. iNaturalist reference records cannot be published.")
    record.update(changes)
    save_ngo_observations_store(records)
    return record


def _eligible_record(record_id: int) -> dict[str, Any]:
    records = load_ngo_observations_store()
    record = next((item for item in records if int(item.get("id", -1)) == record_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="RSWF observation not found. Public iNaturalist records are read-only.")
    if record.get("observation_type") != "planted_rswf":
        raise HTTPException(status_code=400, detail="Only RSWF planted-tree records can be published.")
    if str(record.get("identification_status", "")).lower() not in {"verified", "corrected"}:
        raise HTTPException(status_code=400, detail="Verify or correct the species with an NGO reviewer before publishing.")
    upload_state = str(record.get("inaturalist_upload_status", "")).lower()
    remote_id = record.get("inaturalist_observation_id")
    if upload_state in {"publishing", "photo_uploading"}:
        started = record.get("inaturalist_upload_started_at")
        try:
            started_at = datetime.fromisoformat(str(started))
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            stale = (datetime.now(timezone.utc) - started_at).total_seconds() > 15 * 60
        except (TypeError, ValueError):
            stale = True
        if not stale:
            raise HTTPException(status_code=409, detail="This record is already being published.")
        # Recover stale locks after a worker restart. If the remote ID was saved,
        # retry only the photo; otherwise permit a fresh attempt with a warning in the UI.
        upload_state = "photo_failed" if remote_id else "failed"
        record["inaturalist_upload_status"] = upload_state
        record["inaturalist_upload_error"] = "Recovered a stale publishing lock; retry after checking iNaturalist."
        record["inaturalist_upload_started_at"] = None
        save_ngo_observations_store(records)
    # A remote observation with a failed photo upload can be retried safely by
    # attaching the photo to the same remote ID, never by creating a duplicate.
    if (record.get("observation_url") or remote_id) and not (remote_id and upload_state == "photo_failed"):
        raise HTTPException(status_code=409, detail="This record is already published or is being published.")
    if not record.get("scientific_name"):
        raise HTTPException(status_code=400, detail="A verified scientific name is required.")
    photo_url = str(record.get("photo_url") or "")
    if not _PHOTO_PATH.fullmatch(photo_url):
        raise HTTPException(status_code=400, detail="A stored RSWF upload photo is required.")
    try:
        lat = float(record.get("latitude"))
        lon = float(record.get("longitude"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Valid GPS coordinates are required.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        raise HTTPException(status_code=400, detail="Valid GPS coordinates are required.")
    observed_on = str(record.get("observed_on") or "")
    try:
        date.fromisoformat(observed_on[:10])
    except ValueError:
        raise HTTPException(status_code=400, detail="A valid observation date (YYYY-MM-DD) is required.")
    photo_name = _PHOTO_PATH.fullmatch(photo_url).group(1)
    photo_bytes = photo_storage.read_bytes(photo_name)
    if not photo_bytes:
        raise HTTPException(status_code=400, detail="The stored observation photo is unavailable.")
    record["_publish_photo_name"] = photo_name
    record["_publish_photo_bytes"] = photo_bytes
    record["_publish_latitude"] = lat
    record["_publish_longitude"] = lon
    return record


def _resolve_taxon_id(access_token: str, scientific_name: str) -> int:
    response = requests.get(
        f"{INAT_SITE}/taxa/autocomplete.json",
        params={"q": scientific_name, "per_page": 10},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json()
    if isinstance(results, dict):
        results = results.get("results", [])
    exact = next(
        (taxon for taxon in results if str(taxon.get("name", "")).casefold() == scientific_name.casefold()),
        None,
    )
    if not exact or not exact.get("id"):
        raise ValueError(f"iNaturalist could not find an exact taxon match for '{scientific_name}'. Review the taxonomy before publishing.")
    return int(exact["id"])


@router.get("/status")
def inaturalist_status():
    configured = bool(
        settings.INATURALIST_CLIENT_ID
        and settings.INATURALIST_CLIENT_SECRET
        and settings.INATURALIST_TOKEN_ENCRYPTION_KEY
        and settings.FRONTEND_PUBLIC_URL
        and (settings.INATURALIST_REDIRECT_URI or settings.BACKEND_PUBLIC_URL)
    )
    try:
        record = _load_token_record()
    except Exception:
        log.exception("Failed to load iNaturalist connection state.")
        record = None
    return {
        "configured": configured,
        "connected": bool(record),
        "username": record.get("username") if record else None,
    }


@router.post("/connect")
def connect_inaturalist(_admin: str = Depends(verify_ngo_admin_password)):
    """Only an authenticated NGO administrator may connect/replace the publishing account."""
    _require_oauth_config()
    params = {
        "client_id": settings.INATURALIST_CLIENT_ID,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "write",
        "state": _signed_state(),
    }
    return {"authorization_url": f"{INAT_SITE}/oauth/authorize?{urlencode(params)}"}


@router.get("/oauth/callback")
def inaturalist_oauth_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
):
    if error:
        return _frontend_redirect("cancelled")
    if not code or not state or not _validate_state(state):
        return _frontend_redirect("error")
    try:
        _require_oauth_config()
        token_response = requests.post(
            f"{INAT_SITE}/oauth/token",
            data={
                "client_id": settings.INATURALIST_CLIENT_ID,
                "client_secret": settings.INATURALIST_CLIENT_SECRET,
                "code": code,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
        token_response.raise_for_status()
        token_payload = token_response.json()
        access_token = token_payload.get("access_token")
        if not access_token:
            raise RuntimeError("iNaturalist did not return an access token.")
        user_response = requests.get(
            f"{INAT_SITE}/users/edit.json",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20,
        )
        user_response.raise_for_status()
        user_payload = user_response.json()
        user = user_payload.get("results", user_payload) if isinstance(user_payload, dict) else {}
        if isinstance(user, list):
            user = user[0] if user else {}
        username = (user.get("login") or user.get("user", {}).get("login") or user.get("name") or "").strip()
        _save_token_record({
            "access_token": access_token,
            "username": username or "Connected iNaturalist account",
            "connected_at": datetime.now(timezone.utc).isoformat(),
        })
        return _frontend_redirect("connected")
    except Exception:
        log.exception("iNaturalist OAuth callback failed.")
        return _frontend_redirect("error")


@router.post("/publish/{observation_id}")
def publish_observation(
    observation_id: int,
    _admin: str = Depends(verify_ngo_admin_password),
):
    token_record = _load_token_record()
    if not token_record:
        raise HTTPException(status_code=401, detail="Connect an iNaturalist account before publishing.")
    record = _eligible_record(observation_id)
    photo_name = record.pop("_publish_photo_name")
    photo_bytes = record.pop("_publish_photo_bytes")
    latitude = record.pop("_publish_latitude")
    longitude = record.pop("_publish_longitude")
    access_token = token_record["access_token"]
    remote_id = record.get("inaturalist_observation_id")
    upload_state = str(record.get("inaturalist_upload_status", "")).lower()

    # Persist a lock before contacting iNaturalist, reducing accidental duplicate
    # submissions from double-clicks or concurrent requests.
    _update_record(observation_id, {
        "inaturalist_upload_status": "publishing" if not (remote_id and upload_state == "photo_failed") else "photo_uploading",
        "inaturalist_upload_started_at": datetime.now(timezone.utc).isoformat(),
        "inaturalist_upload_error": None,
    })
    try:
        if not remote_id:
            taxon_id = _resolve_taxon_id(access_token, str(record["scientific_name"]).strip())
            description = str(record.get("notes") or "").strip()
            provenance = "Planted by RSWF at Van Udyan, Bavdhan, Pune. Species identification verified by an NGO reviewer."
            if record.get("zone"):
                provenance += f" Monitoring zone: {record['zone']}."
            if description:
                description = description + "\n\n" + provenance
            else:
                description = provenance
            form_data = {
                "observation[taxon_id]": str(taxon_id),
                "observation[species_guess]": str(record["scientific_name"]).strip(),
                "observation[observed_on_string]": str(record["observed_on"])[:10],
                "observation[time_zone]": "Asia/Kolkata",
                "observation[latitude]": str(latitude),
                "observation[longitude]": str(longitude),
                "observation[location_is_exact]": "true",
                "observation[place_guess]": "Bavdhan Van Udyan, Pune, Maharashtra, India",
                "observation[description]": description,
                "observation[tag_list]": "Van Udyan, RSWF, Bavdhan, Pune",
            }
            response = requests.post(
                f"{INAT_SITE}/observations.json",
                data=form_data,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=60,
            )
            if response.status_code >= 400:
                log.warning("iNaturalist observation creation failed (status=%s, response_length=%s)", response.status_code, len(response.content or b""))
                raise RuntimeError(f"iNaturalist rejected the observation (HTTP {response.status_code}). Check the account, species and metadata, then retry.")
            payload = response.json()
            if isinstance(payload, list):
                payload = payload[0] if payload else {}
            if isinstance(payload, dict) and isinstance(payload.get("results"), list):
                payload = payload["results"][0] if payload["results"] else {}
            remote_id = payload.get("id") if isinstance(payload, dict) else None
            if not remote_id:
                raise RuntimeError("iNaturalist returned no observation ID; check your iNaturalist account before retrying.")
            remote_id = int(remote_id)
            url = f"{INAT_SITE}/observations/{remote_id}"
            # Save the remote ID before photo upload. If the photo upload fails,
            # a retry attaches the photo to this same observation instead of duplicating it.
            _update_record(observation_id, {
                "observation_url": url,
                "inaturalist_observation_id": remote_id,
                "inaturalist_upload_status": "photo_uploading",
                "inaturalist_upload_started_at": datetime.now(timezone.utc).isoformat(),
                "inaturalist_upload_error": None,
            })
        else:
            remote_id = int(remote_id)
            url = str(record.get("observation_url") or f"{INAT_SITE}/observations/{remote_id}")
            _update_record(observation_id, {
                "observation_url": url,
                "inaturalist_observation_id": remote_id,
                "inaturalist_upload_status": "photo_uploading",
                "inaturalist_upload_error": None,
            })

        photo_ext = os.path.splitext(photo_name)[1].lower()
        mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(photo_ext, "image/jpeg")
        photo_response = requests.post(
            f"{INAT_SITE}/observation_photos.json",
            data={"observation_photo[observation_id]": str(remote_id)},
            files={"file": (photo_name, photo_bytes, mime)},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=90,
        )
        if photo_response.status_code >= 400:
            log.warning("iNaturalist photo upload failed (status=%s, response_length=%s)", photo_response.status_code, len(photo_response.content or b""))
            raise RuntimeError(f"The observation was created, but iNaturalist rejected the photo (HTTP {photo_response.status_code}). Retry to attach the photo to the same record.")
        _update_record(observation_id, {
            "observation_url": url,
            "inaturalist_observation_id": remote_id,
            "inaturalist_upload_status": "published",
            "inaturalist_upload_started_at": None,
            "inaturalist_uploaded_at": datetime.now(timezone.utc).isoformat(),
            "inaturalist_upload_error": None,
        })
        return {
            "success": True,
            "observation_id": observation_id,
            "inaturalist_observation_id": remote_id,
            "observation_url": url,
            "status": "published",
        }
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Publishing RSWF observation %s to iNaturalist failed.", observation_id)
        try:
            # Keep the remote ID if the observation was created; this enables a
            # safe photo-only retry and prevents a duplicate remote observation.
            current_records = load_ngo_observations_store()
            current = next((item for item in current_records if int(item.get("id", -1)) == observation_id), None)
            if current and current.get("inaturalist_observation_id"):
                failure_status = "photo_failed"
            else:
                failure_status = "failed"
            _update_record(observation_id, {
                "inaturalist_upload_status": failure_status,
                "inaturalist_upload_started_at": None,
                "inaturalist_upload_error": str(exc)[:300],
            })
        except Exception:
            log.exception("Could not persist failed iNaturalist publishing state.")
        raise HTTPException(status_code=502, detail=str(exc) or "iNaturalist publishing failed.") from exc
