"""
NGO Approved Species Filter Service.

Loads the Sacred Grove / Devrai Foundation approved species list
(extracted from 'Sacred Grove Plant List - v2.xls') and provides:

  - is_ngo_species(scientific_name)  → bool
  - annotate_predictions(predictions) → same list, each dict gets
      'in_ngo_list'   : True / False
      'ngo_note'      : human-readable explanation
      'marathi_name'  : Marathi common name if in list
      'ngo_type'      : Tree / Shrub / Creeper if in list

The list is loaded once at startup and cached in memory.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# File path
# ---------------------------------------------------------------------------

def _ngo_species_path() -> str:
    base = os.environ.get("DATA_DIR") or os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "processed"
    )
    return os.path.join(base, "ngo_approved_species.json")


# ---------------------------------------------------------------------------
# Loading & caching
# ---------------------------------------------------------------------------

_CACHE: Optional[Dict[str, Any]] = None


def _load() -> Dict[str, Any]:
    """Load the approved-species JSON, caching after first read."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = _ngo_species_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            _CACHE = json.load(f)
    except FileNotFoundError:
        _CACHE = {"_meta": {}, "species": []}
    return _CACHE


def _build_index() -> Dict[str, Dict[str, Any]]:
    """Build a lowercase scientific-name → species-record index."""
    data = _load()
    index: Dict[str, Dict[str, Any]] = {}
    for sp in data.get("species", []):
        key = _norm(sp.get("scientific_name", ""))
        if key:
            index[key] = sp
    return index


_INDEX: Optional[Dict[str, Dict[str, Any]]] = None


def _get_index() -> Dict[str, Dict[str, Any]]:
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


def reload() -> int:
    """Force-reload the JSON from disk (call after admin updates the file). Returns species count."""
    global _CACHE, _INDEX
    _CACHE = None
    _INDEX = None
    data = _load()
    _INDEX = _build_index()
    return len(data.get("species", []))


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _norm(name: str) -> str:
    """Lower-case and collapse whitespace."""
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _genus_match(query: str, index: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Fuzzy fallback: if the full species name is not in the index, try matching
    just the genus (first word). This catches PlantNet variants like
    'Ficus benghalensis var. krishnae' matching 'Ficus benghalensis'.
    Returns the first matching entry or None.
    """
    words = _norm(query).split()
    if len(words) < 2:
        return None
    # Try genus + species epithet
    two_word = " ".join(words[:2])
    if two_word in index:
        return index[two_word]
    # Try just genus (wider match — only used if genus is unique in the list)
    genus = words[0]
    genus_matches = [v for k, v in index.items() if k.startswith(genus + " ")]
    if len(genus_matches) == 1:
        return genus_matches[0]
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_ngo_species(scientific_name: str) -> bool:
    """Return True if scientific_name (or its genus+epithet prefix) is in the NGO list."""
    idx = _get_index()
    key = _norm(scientific_name)
    if key in idx:
        return True
    return _genus_match(scientific_name, idx) is not None


def lookup_species(scientific_name: str) -> Optional[Dict[str, Any]]:
    """Return the full species record from the NGO list, or None if not found."""
    idx = _get_index()
    key = _norm(scientific_name)
    if key in idx:
        return idx[key]
    return _genus_match(scientific_name, idx)


def annotate_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich each PlantNet prediction dict in-place (and return the list) with:
      - in_ngo_list   : bool
      - ngo_note      : str  (shown to the field worker in the UI)
      - marathi_name  : str | None
      - ngo_type      : str | None  (Tree / Shrub / Creeper)
      - ngo_qty_planned : int | None
    """
    for pred in predictions:
        sci = pred.get("scientific_name", "")
        record = lookup_species(sci)
        if record:
            pred["in_ngo_list"] = True
            pred["marathi_name"] = record.get("marathi_name")
            pred["ngo_type"] = record.get("type")
            pred["ngo_qty_planned"] = record.get("qty_planned")
            pred["ngo_note"] = (
                f"✅ In NGO list — {record.get('marathi_name', '')} "
                f"({record.get('type', 'Plant')}, {record.get('qty_planned', '?')} planned)"
            ).strip(" —")
        else:
            pred["in_ngo_list"] = False
            pred["marathi_name"] = None
            pred["ngo_type"] = None
            pred["ngo_qty_planned"] = None
            pred["ngo_note"] = (
                "⚠️ Not in NGO species list — this species was not purchased "
                "or planned for Bavdhan Van Udyan. Prediction may be incorrect."
            )
    return predictions


def get_approved_species_summary() -> Dict[str, Any]:
    """Return meta + flat list of approved species names for the frontend dropdown."""
    data = _load()
    return {
        "meta": data.get("_meta", {}),
        "total": len(data.get("species", [])),
        "species": [
            {
                "scientific_name": sp["scientific_name"],
                "marathi_name": sp.get("marathi_name"),
                "type": sp.get("type"),
                "qty_planned": sp.get("qty_planned"),
            }
            for sp in data.get("species", [])
        ],
    }
