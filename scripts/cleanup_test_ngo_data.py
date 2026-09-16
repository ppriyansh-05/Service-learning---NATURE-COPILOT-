"""
Controlled Cleanup Script for Phase 7 & Phase 9 Test Data
Resets the NGO observations JSON store and removes synthetic test upload images from data/uploads/.
"""

import os
import sys
import json
import glob

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.data_service import DataService, get_base_dir

def perform_test_data_cleanup():
    print("=" * 70)
    print("      CONTROLLED TEST DATA CLEANUP — PHASE 7 & 9 NGO OBSERVATIONS")
    print("=" * 70)

    store_path = os.path.join(get_base_dir(), "data", "processed", "ngo_observations_store.json")
    uploads_dir = os.path.join(get_base_dir(), "data", "uploads")

    # 1. Inspect existing store records
    existing_records = []
    if os.path.exists(store_path):
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                existing_records = json.load(f)
        except Exception:
            pass

    print(f"Total NGO store records found: {len(existing_records)}")
    test_records = [r for r in existing_records if r.get("source") == "NGO / New Upload"]
    print(f"Confirmed test-generated NGO records: {len(test_records)}")

    # 2. Reset store to empty list [] and clear AI predictions repository
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    print(f"[CLEANUP] Reset '{store_path}' -> 0 records.")

    DataService._ai_predictions_repository.clear()
    ai_legacy_file = os.path.join(get_base_dir(), "data", "processed", "ai_predictions_store.json")
    if os.path.exists(ai_legacy_file):
        try:
            os.remove(ai_legacy_file)
            print(f"[CLEANUP] Removed legacy file '{ai_legacy_file}'.")
        except Exception:
            pass

    # 3. Clean synthetic test uploaded images in data/uploads/
    upload_files = glob.glob(os.path.join(uploads_dir, "upload_*"))
    removed_count = 0
    for file_path in upload_files:
        try:
            os.remove(file_path)
            removed_count += 1
        except Exception as e:
            print(f"Failed to remove {file_path}: {e}")
    print(f"[CLEANUP] Removed {removed_count} synthetic test image files from '{uploads_dir}'.")

    # 4. Verify post-cleanup database state
    records, total_count, _ = DataService.get_observations(limit=10000)
    inat_count = sum(1 for r in records if r.get("source") == "iNaturalist")
    ngo_count = sum(1 for r in records if r.get("source") == "NGO / New Upload")

    print("-" * 70)
    print(f"POST-CLEANUP VERIFICATION:")
    print(f"  - Total Observations: {total_count}")
    print(f"  - iNaturalist Records: {inat_count} (Expected: 227)")
    print(f"  - NGO / New Upload Records: {ngo_count} (Expected: 0)")

    success = (inat_count == 227 and ngo_count == 0)
    status_str = "CLEANUP SUCCESSFUL — 0 NGO TEST RECORDS REMAIN" if success else "CLEANUP FAILED"
    print(f"OVERALL STATUS: {status_str}")
    print("=" * 70)
    return success

if __name__ == "__main__":
    success = perform_test_data_cleanup()
    sys.exit(0 if success else 1)
