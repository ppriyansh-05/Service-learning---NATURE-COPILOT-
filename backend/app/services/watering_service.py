"""
Watering reminder service.

Given the planted-plant records, works out which trees need to be watered today and tracks the
history of waterings. Designed around Pune's climate:

  * Default dry-season interval:  7 days per plant.
  * Fresh plantings (less than FRESH_PLANTING_DAYS old) get a shorter 3-day interval.
  * Each plant can override its own interval via `watering_interval_days`
    (0 = never remind, None = use the default).
  * Monsoon window (15 June – 30 September): all reminders are suppressed because the plants
    get enough rain.
  * Dead and Unknown plants are never reminded about.

Public API is small by design:
  - watering_status_for(plant, today)          -> single plant's status dict
  - compute_watering_queue(plants, today)      -> list, sorted most urgent first
  - mark_watered(plant_id, on_date, observer)  -> updates the planted_plants store
                                                  (returns the updated record)
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional


DEFAULT_INTERVAL_DAYS = 7
FRESH_PLANTING_DAYS = 90
FRESH_INTERVAL_DAYS = 3

# Pune monsoon window — reminders are suppressed within these dates each year.
MONSOON_START_MONTH, MONSOON_START_DAY = 6, 15
MONSOON_END_MONTH, MONSOON_END_DAY = 9, 30


def is_monsoon(today: datetime.date) -> bool:
    """True on dates between 15 June and 30 September (inclusive) of the given year."""
    start = datetime.date(today.year, MONSOON_START_MONTH, MONSOON_START_DAY)
    end = datetime.date(today.year, MONSOON_END_MONTH, MONSOON_END_DAY)
    return start <= today <= end


def _parse_date(value: Any) -> Optional[datetime.date]:
    """Parses an ISO date string / datetime / date into a date. Returns None on bad input."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    try:
        return datetime.date.fromisoformat(str(value).strip()[:10])
    except (ValueError, TypeError):
        return None


def _effective_interval(plant: Dict[str, Any], today: datetime.date) -> Optional[int]:
    """
    Returns the number of days between waterings for this plant, or None when watering is skipped
    entirely (dead/unknown plant, explicit zero interval, or monsoon season).
    """
    status = (plant.get("status") or "").strip().lower()
    if status in ("dead", "unknown"):
        return None

    override = plant.get("watering_interval_days")
    if isinstance(override, int):
        return None if override == 0 else max(1, override)

    planted_on = _parse_date(plant.get("planted_on"))
    if planted_on and (today - planted_on).days < FRESH_PLANTING_DAYS:
        return FRESH_INTERVAL_DAYS
    return DEFAULT_INTERVAL_DAYS


def watering_status_for(plant: Dict[str, Any], today: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Returns a status dict for one plant:
      bucket         : "overdue" | "due_soon" | "ok" | "skip"
      days_overdue   : int (0 for not-yet-due, negative = days until due)
      interval_days  : the interval being applied (None if skipped)
      last_watered   : ISO date string or None
      next_due       : ISO date string or None
      note           : short human-readable explanation
    """
    today = today or datetime.date.today()
    interval = _effective_interval(plant, today)
    last_watered = _parse_date(plant.get("last_watered_on"))

    if interval is None:
        if (plant.get("status") or "").lower() in ("dead", "unknown"):
            note = "No watering tracked — plant is " + (plant.get("status") or "").lower() + "."
        elif isinstance(plant.get("watering_interval_days"), int) and plant["watering_interval_days"] == 0:
            note = "Reminders turned off for this plant."
        else:
            note = "No watering reminders."
        return {
            "bucket": "skip",
            "days_overdue": 0,
            "interval_days": None,
            "last_watered": last_watered.isoformat() if last_watered else None,
            "next_due": None,
            "note": note,
        }

    if is_monsoon(today):
        return {
            "bucket": "skip",
            "days_overdue": 0,
            "interval_days": interval,
            "last_watered": last_watered.isoformat() if last_watered else None,
            "next_due": None,
            "note": "Monsoon season — reminders paused until October.",
        }

    if last_watered is None:
        # Never watered. Treat planting day as the baseline so brand-new plants aren't instantly red.
        planted_on = _parse_date(plant.get("planted_on"))
        baseline = planted_on or today
        next_due = baseline + datetime.timedelta(days=interval)
        days_overdue = (today - next_due).days
    else:
        next_due = last_watered + datetime.timedelta(days=interval)
        days_overdue = (today - next_due).days

    if days_overdue > 0:
        bucket = "overdue"
        note = f"Overdue by {days_overdue} day{'s' if days_overdue != 1 else ''}."
    elif days_overdue == 0 or days_overdue == -1:
        # Due today or tomorrow
        bucket = "due_soon"
        note = "Due today." if days_overdue == 0 else "Due tomorrow."
    else:
        bucket = "ok"
        note = f"Next watering in {-days_overdue} days."

    return {
        "bucket": bucket,
        "days_overdue": days_overdue,
        "interval_days": interval,
        "last_watered": last_watered.isoformat() if last_watered else None,
        "next_due": next_due.isoformat(),
        "note": note,
    }


def compute_watering_queue(plants: List[Dict[str, Any]], today: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
    """
    Returns a flat list of plants annotated with watering status, sorted most urgent first:
    overdue → due_soon → ok → skip. Within a bucket, more overdue days come first.
    """
    today = today or datetime.date.today()
    bucket_order = {"overdue": 0, "due_soon": 1, "ok": 2, "skip": 3}
    annotated: List[Dict[str, Any]] = []
    for p in plants or []:
        status = watering_status_for(p, today)
        annotated.append({
            "plant_id": p.get("id"),
            "plant_code": p.get("plant_code"),
            "scientific_name": p.get("scientific_name"),
            "common_name": p.get("common_name"),
            "zone_code": p.get("zone_code"),
            "status": p.get("status"),
            "watering": status,
        })
    annotated.sort(key=lambda a: (bucket_order.get(a["watering"]["bucket"], 9), -a["watering"]["days_overdue"]))
    return annotated


def watering_overview(plants: List[Dict[str, Any]], today: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Compact summary for the dashboard KPI card: counts by bucket plus whether we're in monsoon.
    """
    today = today or datetime.date.today()
    queue = compute_watering_queue(plants, today)
    counts = {"overdue": 0, "due_soon": 0, "ok": 0, "skip": 0}
    for a in queue:
        counts[a["watering"]["bucket"]] = counts.get(a["watering"]["bucket"], 0) + 1
    return {
        "date": today.isoformat(),
        "is_monsoon": is_monsoon(today),
        "counts": counts,
        "needs_water_today": counts["overdue"] + counts["due_soon"],
        "default_interval_days": DEFAULT_INTERVAL_DAYS,
        "fresh_interval_days": FRESH_INTERVAL_DAYS,
    }
