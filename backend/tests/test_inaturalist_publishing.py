import pytest
from fastapi import HTTPException

from app.api.v1 import inaturalist


def _valid_record(**overrides):
    record = {
        "id": 17,
        "source": "NGO / New Upload",
        "observation_type": "planted_rswf",
        "identification_status": "verified",
        "scientific_name": "Azadirachta indica",
        "common_name": "Neem",
        "observed_on": "2026-10-10",
        "latitude": 18.51,
        "longitude": 73.79,
        "photo_url": "/uploads/upload_test_123.jpg",
        "zone": "ZONE A",
        "notes": "Field verified.",
        "observation_url": None,
    }
    record.update(overrides)
    return record


def test_oauth_state_is_signed_and_valid_for_current_flow(monkeypatch):
    monkeypatch.setenv("INATURALIST_CLIENT_SECRET", "test-oauth-secret")
    state = inaturalist._signed_state()
    assert inaturalist._validate_state(state)
    assert not inaturalist._validate_state(state + "tampered")


def test_unverified_record_cannot_be_published(monkeypatch):
    monkeypatch.setattr(inaturalist, "load_ngo_observations_store", lambda: [
        _valid_record(identification_status="ai_suggested")
    ])
    with pytest.raises(HTTPException) as exc:
        inaturalist._eligible_record(17)
    assert exc.value.status_code == 400
    assert "Verify or correct" in exc.value.detail


def test_non_planted_record_cannot_be_published(monkeypatch):
    monkeypatch.setattr(inaturalist, "load_ngo_observations_store", lambda: [
        _valid_record(observation_type="sighted")
    ])
    with pytest.raises(HTTPException) as exc:
        inaturalist._eligible_record(17)
    assert exc.value.status_code == 400
    assert "planted-tree" in exc.value.detail


def test_verified_planted_record_requires_a_stored_photo(monkeypatch):
    monkeypatch.setattr(inaturalist, "load_ngo_observations_store", lambda: [
        _valid_record(photo_url=None)
    ])
    with pytest.raises(HTTPException) as exc:
        inaturalist._eligible_record(17)
    assert exc.value.status_code == 400
    assert "stored RSWF upload photo" in exc.value.detail


def test_verified_planted_record_requires_exact_date(monkeypatch):
    monkeypatch.setattr(inaturalist, "load_ngo_observations_store", lambda: [
        _valid_record(observed_on="not-a-date")
    ])
    with pytest.raises(HTTPException) as exc:
        inaturalist._eligible_record(17)
    assert exc.value.status_code == 400
    assert "observation date" in exc.value.detail


def test_verified_planted_record_is_eligible_when_photo_and_gps_exist(monkeypatch):
    monkeypatch.setattr(inaturalist, "load_ngo_observations_store", lambda: [_valid_record()])
    monkeypatch.setattr(inaturalist.photo_storage, "read_bytes", lambda name: b"fake-image-bytes")
    record = inaturalist._eligible_record(17)
    assert record["scientific_name"] == "Azadirachta indica"
    assert record["_publish_photo_name"] == "upload_test_123.jpg"
    assert record["_publish_photo_bytes"] == b"fake-image-bytes"
    assert record["_publish_latitude"] == 18.51
    assert record["_publish_longitude"] == 73.79
