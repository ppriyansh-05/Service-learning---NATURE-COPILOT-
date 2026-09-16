"""
Pytest API Endpoint Test Suite for FastAPI Backend Services
Tests health endpoints, observation endpoints, species catalog, active zones, boundary GeoJSON, and map endpoints.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Van Udyan Biodiversity Intelligence Platform API"

def test_db_health_check():
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database_connected" in data
    assert "postgis_available" in data

def test_get_observations_paginated():
    response = client.get("/api/v1/observations?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["limit"] == 10
    assert data["total_records"] >= 227
    assert len(data["data"]) == 10

def test_get_observations_filtering():
    # Source filter
    response = client.get("/api/v1/observations?source=iNaturalist")
    assert response.status_code == 200
    assert response.json()["total_records"] >= 227

    # Zone filter
    response = client.get("/api/v1/observations?zone=ZONE%20A")
    assert response.status_code == 200
    assert response.json()["total_records"] >= 60

def test_get_observation_detail_success():
    response = client.get("/api/v1/observations/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "latitude" in data
    assert "longitude" in data

def test_get_observation_detail_not_found():
    response = client.get("/api/v1/observations/999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_get_species():
    response = client.get("/api/v1/species?page=1&limit=20")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] >= 88
    assert len(data["data"]) <= 20

def test_get_zones():
    response = client.get("/api/v1/zones")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    zone_codes = [z["zone_code"] for z in data]
    assert "ZONE A" in zone_codes
    assert "ZONE B" in zone_codes
    assert "ZONE C" in zone_codes

def test_get_geography_boundary():
    response = client.get("/api/v1/geography")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0

def test_get_map_observations_geojson():
    response = client.get("/api/v1/map/observations")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 227
    
    # Check feature structure
    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert feat["geometry"]["type"] == "Point"
    assert len(feat["geometry"]["coordinates"]) == 2
    assert "scientific_name" in feat["properties"]

def test_get_statistics_overview():
    response = client.get("/api/v1/statistics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_observations"] >= 227
    assert data["unique_species_count"] >= 88
    assert data["observations_by_zone"]["ZONE A"] >= 60
    assert data["observations_by_zone"]["ZONE B"] >= 37
    assert data["observations_by_zone"]["ZONE C"] >= 26

def test_openapi_docs():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Van Udyan Biodiversity Intelligence Platform API"
