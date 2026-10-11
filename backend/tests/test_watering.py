"""Unit tests for the watering reminder service."""

import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.watering_service import (
    DEFAULT_INTERVAL_DAYS,
    FRESH_INTERVAL_DAYS,
    FRESH_PLANTING_DAYS,
    compute_watering_queue,
    is_monsoon,
    watering_overview,
    watering_status_for,
)


DRY_DAY = datetime.date(2026, 2, 10)   # February — well outside the monsoon window
MONSOON_DAY = datetime.date(2026, 7, 15)


def test_monsoon_window():
    assert is_monsoon(datetime.date(2026, 7, 1))
    assert is_monsoon(datetime.date(2026, 6, 15))
    assert is_monsoon(datetime.date(2026, 9, 30))
    assert not is_monsoon(datetime.date(2026, 6, 14))
    assert not is_monsoon(datetime.date(2026, 10, 1))
    assert not is_monsoon(datetime.date(2026, 2, 10))


def test_dead_plant_skipped():
    s = watering_status_for({"status": "Dead", "planted_on": "2026-01-01"}, DRY_DAY)
    assert s["bucket"] == "skip"
    assert s["interval_days"] is None


def test_opt_out_zero_interval():
    s = watering_status_for({"status": "Alive", "watering_interval_days": 0}, DRY_DAY)
    assert s["bucket"] == "skip"
    assert "turned off" in s["note"]


def test_monsoon_pauses_reminders_even_for_alive_plant():
    s = watering_status_for({"status": "Alive", "planted_on": "2025-01-01"}, MONSOON_DAY)
    assert s["bucket"] == "skip"
    assert "Monsoon" in s["note"]


def test_fresh_planting_uses_short_interval():
    planted = DRY_DAY - datetime.timedelta(days=30)   # 30 days ago
    s = watering_status_for({"status": "Alive", "planted_on": planted.isoformat()}, DRY_DAY)
    assert s["interval_days"] == FRESH_INTERVAL_DAYS


def test_established_planting_uses_default_interval():
    planted = DRY_DAY - datetime.timedelta(days=FRESH_PLANTING_DAYS + 1)
    s = watering_status_for({"status": "Alive", "planted_on": planted.isoformat()}, DRY_DAY)
    assert s["interval_days"] == DEFAULT_INTERVAL_DAYS


def test_overdue_bucket_computed_from_last_watered():
    last = (DRY_DAY - datetime.timedelta(days=10)).isoformat()
    s = watering_status_for({"status": "Alive", "last_watered_on": last}, DRY_DAY)
    assert s["bucket"] == "overdue"
    assert s["days_overdue"] == 10 - DEFAULT_INTERVAL_DAYS


def test_due_today_is_due_soon():
    last = (DRY_DAY - datetime.timedelta(days=DEFAULT_INTERVAL_DAYS)).isoformat()
    s = watering_status_for({"status": "Alive", "last_watered_on": last}, DRY_DAY)
    assert s["bucket"] == "due_soon"
    assert s["note"] == "Due today."


def test_ok_bucket_when_recently_watered():
    last = (DRY_DAY - datetime.timedelta(days=2)).isoformat()
    s = watering_status_for({"status": "Alive", "last_watered_on": last}, DRY_DAY)
    assert s["bucket"] == "ok"


def test_never_watered_old_plant_is_overdue():
    planted = (DRY_DAY - datetime.timedelta(days=365)).isoformat()
    s = watering_status_for({"status": "Alive", "planted_on": planted}, DRY_DAY)
    assert s["bucket"] == "overdue"


def test_never_watered_brand_new_plant_is_not_overdue_yet():
    planted = DRY_DAY.isoformat()  # Planted today
    s = watering_status_for({"status": "Alive", "planted_on": planted}, DRY_DAY)
    assert s["bucket"] == "ok"


def test_queue_sorts_overdue_first():
    plants = [
        {"id": 1, "status": "Alive", "last_watered_on": (DRY_DAY - datetime.timedelta(days=1)).isoformat()},
        {"id": 2, "status": "Alive", "last_watered_on": (DRY_DAY - datetime.timedelta(days=15)).isoformat()},
        {"id": 3, "status": "Dead"},
        {"id": 4, "status": "Alive", "last_watered_on": (DRY_DAY - datetime.timedelta(days=DEFAULT_INTERVAL_DAYS)).isoformat()},
    ]
    queue = compute_watering_queue(plants, DRY_DAY)
    ids = [q["plant_id"] for q in queue]
    assert ids[0] == 2    # most overdue first
    assert ids[-1] == 3   # dead plant last


def test_overview_counts_and_monsoon_flag():
    plants = [
        {"id": 1, "status": "Alive", "last_watered_on": (DRY_DAY - datetime.timedelta(days=15)).isoformat()},
        {"id": 2, "status": "Alive", "last_watered_on": (DRY_DAY - datetime.timedelta(days=1)).isoformat()},
        {"id": 3, "status": "Dead"},
    ]
    ov = watering_overview(plants, DRY_DAY)
    assert ov["is_monsoon"] is False
    assert ov["counts"]["overdue"] == 1
    assert ov["counts"]["ok"] == 1
    assert ov["counts"]["skip"] == 1
    assert ov["needs_water_today"] == 1

    monsoon = watering_overview(plants, MONSOON_DAY)
    assert monsoon["is_monsoon"] is True
    assert monsoon["needs_water_today"] == 0   # all suppressed by monsoon
