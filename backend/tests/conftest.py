"""
Shared Pytest Configuration
Several test modules reset data/processed/*_store.json and delete data/uploads/upload_* in their
cleanup fixtures. This session fixture snapshots that real NGO data before the test run and
restores it afterwards, so running the suite never destroys field observations or photos.
"""

import os
import shutil
import tempfile
import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
UPLOADS_DIR = os.path.join(BASE_DIR, "data", "uploads")
STORE_FILES = ["ngo_observations_store.json", "planted_plants_store.json"]


@pytest.fixture(autouse=True, scope="session")
def preserve_real_ngo_data():
    backup_dir = tempfile.mkdtemp(prefix="van_udyan_test_backup_")
    for name in STORE_FILES:
        src = os.path.join(PROCESSED_DIR, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(backup_dir, name))
    if os.path.isdir(UPLOADS_DIR):
        shutil.copytree(UPLOADS_DIR, os.path.join(backup_dir, "uploads"))

    yield

    for name in STORE_FILES:
        saved = os.path.join(backup_dir, name)
        target = os.path.join(PROCESSED_DIR, name)
        if os.path.exists(saved):
            shutil.copy2(saved, target)
        elif os.path.exists(target):
            os.remove(target)
    saved_uploads = os.path.join(backup_dir, "uploads")
    if os.path.isdir(saved_uploads):
        shutil.rmtree(UPLOADS_DIR, ignore_errors=True)
        shutil.copytree(saved_uploads, UPLOADS_DIR)
    shutil.rmtree(backup_dir, ignore_errors=True)
