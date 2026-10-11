"""
One-time migration from a local Van Udyan install to a fresh Supabase + Render deployment.

Reads DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY and SUPABASE_BUCKET from backend/.env
(or the environment) and:

  1. Creates the PostGIS schema and seeds iNaturalist records + boundary + zones in Supabase
     (same work as scripts/setup_database.py, run against the cloud database).
  2. Uploads every photo in data/uploads/ to the Supabase Storage bucket.
  3. Pushes every JSON store under data/processed/ into the app_state table in Supabase so
     NGO observations, planted plants and visit history show up in the deployed dashboard.

Safe to re-run: the schema uses IF NOT EXISTS, iNaturalist seeding is idempotent on observation_id,
Storage uploads use upsert=true, and app_state upserts by key.

Usage:
    cd backend && venv\\Scripts\\activate   (or source venv/bin/activate)
    cd ..
    python scripts/deploy_initial_data.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# Load backend/.env so this script can be run exactly like the setup script
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / "backend" / ".env")


def _header(text: str) -> None:
    print("\n" + "=" * 72)
    print(f" {text}")
    print("=" * 72)


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"\nMissing environment variable: {name}")
        print("Set it in backend/.env or export it in this shell and re-run.")
        sys.exit(1)
    return value


def main() -> None:
    db_url = _require("DATABASE_URL")
    supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    bucket = os.environ.get("SUPABASE_BUCKET", "van-udyan-photos").strip()

    # 1. Database schema and reference data ----------------------------------------------------
    _header("1/3  Running setup_database.py against the cloud database")
    from scripts.setup_database import setup_database  # type: ignore

    # setup_database already reads DATABASE_URL from the env
    if not setup_database():
        print("Database setup failed; aborting.")
        sys.exit(1)

    # 2. Photos --> Supabase Storage ----------------------------------------------------------
    _header("2/3  Uploading photos to Supabase Storage")
    uploads_dir = ROOT / "data" / "uploads"
    photos = sorted(p for p in uploads_dir.glob("upload_*") if p.is_file())
    if not photos:
        print("No local photos to upload — skipping.")
    elif not (supabase_url and supabase_key):
        print("SUPABASE_URL / SUPABASE_SERVICE_KEY not set — skipping photo upload.")
        print("The deployed backend will not serve existing photos until you upload them.")
    else:
        # Force the photo_storage layer to pick up the Supabase env vars
        os.environ["SUPABASE_URL"] = supabase_url
        os.environ["SUPABASE_SERVICE_KEY"] = supabase_key
        os.environ["SUPABASE_BUCKET"] = bucket
        from app.services import photo_storage  # noqa: E402

        if photo_storage.is_local():
            print("Supabase env vars not detected by photo_storage — skipping.")
        else:
            uploaded = 0
            for photo in photos:
                try:
                    with open(photo, "rb") as f:
                        data = f.read()
                    ext = photo.suffix.lower().lstrip(".") or "jpeg"
                    photo_storage.write_bytes(photo.name, data, content_type=f"image/{ext}")
                    uploaded += 1
                    print(f"  ✓ {photo.name} ({len(data) // 1024} KB)")
                except Exception as e:
                    print(f"  ✗ {photo.name}: {e}")
            print(f"\nUploaded {uploaded} of {len(photos)} photos to bucket '{bucket}'.")

    # 3. JSON stores --> app_state table -------------------------------------------------------
    _header("3/3  Pushing NGO data stores into the cloud database")
    # state_sync is opt-in; this one-time migration always needs it on
    os.environ["ENABLE_STATE_SYNC"] = "true"
    from app.services import state_sync  # noqa: E402

    results = state_sync.push_all_from_disk()
    for key, ok in results.items():
        print(f"  {'✓' if ok else '-'} {key}")

    _header("Done")
    print("Your deployed backend should now serve the same data as your local install.")
    print("Reload the deployed dashboard to see it.")


if __name__ == "__main__":
    main()
