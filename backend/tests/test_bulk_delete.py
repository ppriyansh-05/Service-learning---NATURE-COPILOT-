import pytest

from app.services import data_service
from app.services.data_service import DataService


def test_bulk_delete_observations_removes_only_ngo_records(monkeypatch):
    store = {
        "records": [
            {"id": 10, "source": "NGO / New Upload", "scientific_name": "Neem"},
            {"id": 20, "source": "NGO / New Upload", "scientific_name": "Peepal"},
        ]
    }
    monkeypatch.setattr(
        data_service,
        "load_ngo_observations_store",
        lambda: list(store["records"]),
    )
    monkeypatch.setattr(
        data_service,
        "save_ngo_observations_store",
        lambda records: store.update(records=list(records)),
    )

    def protect_inaturalist_record(obs_id):
        if obs_id == 20 or obs_id == 999:
            raise PermissionError("Original iNaturalist records are read-only.")

    monkeypatch.setattr(
        DataService,
        "protect_inaturalist_record",
        staticmethod(protect_inaturalist_record),
    )

    result = DataService.bulk_delete_ngo_observations([10, 20, 404, 10, 999])

    assert result["requested_count"] == 4
    assert result["deleted_ids"] == [10]
    assert result["deleted_count"] == 1
    assert {item["id"]: item["reason"] for item in result["skipped"]} == {
        20: "read_only_inaturalist",
        404: "not_found_or_not_ngo_owned",
        999: "read_only_inaturalist",
    }
    assert [record["id"] for record in store["records"]] == [20]


def test_bulk_delete_planted_plants_deduplicates_ids_and_reports_missing(monkeypatch):
    store = {
        "records": [
            {"id": 1, "plant_code": "VU-001"},
            {"id": 2, "plant_code": "VU-002"},
            {"id": 3, "plant_code": "VU-003"},
        ]
    }
    monkeypatch.setattr(
        data_service,
        "load_planted_plants_store",
        lambda: list(store["records"]),
    )
    monkeypatch.setattr(
        data_service,
        "save_planted_plants_store",
        lambda records: store.update(records=list(records)),
    )

    result = DataService.bulk_delete_planted_plants([2, 99, 2, 3])

    assert result["requested_count"] == 3
    assert result["deleted_ids"] == [2, 3]
    assert result["deleted_count"] == 2
    assert result["skipped"] == [{"id": 99, "reason": "not_found"}]
    assert [record["id"] for record in store["records"]] == [1]


def test_bulk_delete_empty_selection_does_not_write(monkeypatch):
    writes = []
    monkeypatch.setattr(data_service, "load_planted_plants_store", lambda: [{"id": 1}])
    monkeypatch.setattr(data_service, "save_planted_plants_store", lambda records: writes.append(records))

    result = DataService.bulk_delete_planted_plants([])

    assert result == {
        "requested_count": 0,
        "deleted_count": 0,
        "deleted_ids": [],
        "skipped": [],
    }
    assert writes == []
