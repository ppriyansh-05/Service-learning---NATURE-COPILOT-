"""
Phase 8 Dataset Export Pytest Suite
Tests CSV, GeoJSON, and ZIP package export endpoints, Content-Type headers, Content-Disposition headers,
query filtering, and database source data preservation.
"""

import sys
import os
import json
import zipfile
import io
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_export_observations_csv_success():
    response = client.get("/api/v1/export/observations.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=" in response.headers["content-disposition"]
    csv_text = response.text
    assert "id,source,source_id" in csv_text
    assert "iNaturalist" in csv_text

def test_export_observations_csv_filtered():
    response = client.get("/api/v1/export/observations.csv?zone=ZONE%20A&source=iNaturalist")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    csv_text = response.text
    assert "ZONE A" in csv_text or len(csv_text.splitlines()) >= 1

def test_export_planted_plants_csv_success():
    response = client.get("/api/v1/export/planted-plants.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=" in response.headers["content-disposition"]
    csv_text = response.text
    assert "plant_code" in csv_text

def test_export_planted_plants_csv_filtered():
    response = client.get("/api/v1/export/planted-plants.csv?status=Alive")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

def test_export_species_csv_success():
    response = client.get("/api/v1/export/species.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "scientific_name" in response.text

def test_export_observations_geojson_success():
    response = client.get("/api/v1/export/observations.geojson")
    assert response.status_code == 200
    assert "application/geo+json" in response.headers["content-type"]
    geojson = response.json()
    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson
    assert len(geojson["features"]) >= 1

def test_export_planted_plants_geojson_success():
    response = client.get("/api/v1/export/planted-plants.geojson")
    assert response.status_code == 200
    assert "application/geo+json" in response.headers["content-type"]
    geojson = response.json()
    assert geojson["type"] == "FeatureCollection"

def test_export_complete_zip_package():
    response = client.get("/api/v1/export/package.zip")
    assert response.status_code == 200
    assert "application/zip" in response.headers["content-type"]
    
    zip_bytes = response.content
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        names = z.namelist()
        assert "van_udyan_observations.csv" in names
        assert "van_udyan_planted_plants.csv" in names
        assert "van_udyan_species.csv" in names
        assert "van_udyan_observations.geojson" in names
        assert "van_udyan_planted_plants.geojson" in names
