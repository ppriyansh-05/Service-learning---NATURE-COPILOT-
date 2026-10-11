"""
Pydantic Schemas Module
Defines response and request validation models for API endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from datetime import date

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str = "1.0.0"

class DBHealthResponse(BaseModel):
    status: str
    database_connected: bool
    postgis_available: bool
    engine: str = "PostgreSQL + PostGIS"

class ObservationResponse(BaseModel):
    id: int
    source: str
    source_id: Optional[str] = None
    taxon_id: Optional[str] = None
    scientific_name: Optional[str] = None
    common_name: Optional[str] = None
    observed_on: Optional[str] = None
    quality_grade: Optional[str] = None
    observer: Optional[str] = None
    observation_url: Optional[str] = None
    photo_url: Optional[str] = None
    latitude: float
    longitude: float
    zone: Optional[str] = None
    zone_status: str
    # NGO field observations: location source and identification review state
    gps_source: Optional[str] = None
    notes: Optional[str] = None
    identification_status: Optional[str] = None
    identification_confidence: Optional[str] = None
    verification_notes: Optional[str] = None
    ai_top_predictions: Optional[List[Dict[str, Any]]] = None

class PaginatedObservationsResponse(BaseModel):
    page: int
    limit: int
    total_records: int
    total_pages: int
    data: List[ObservationResponse]

class SpeciesResponse(BaseModel):
    id: int
    taxon_id: Optional[str] = None
    scientific_name: str
    species_name: Optional[str] = None
    common_name: Optional[str] = None
    taxon_rank: Optional[str] = None
    record_count: Optional[int] = 0

class PaginatedSpeciesResponse(BaseModel):
    page: int
    limit: int
    total_records: int
    total_pages: int
    data: List[SpeciesResponse]

class ZoneResponse(BaseModel):
    id: int
    zone_code: str
    status: str
    description: Optional[str] = None
    geometry: Dict[str, Any]

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    properties: Dict[str, Any]
    geometry: Dict[str, Any]

class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    name: Optional[str] = None
    features: List[GeoJSONFeature]

class OverviewStatisticsResponse(BaseModel):
    total_observations: int
    unique_species_count: int
    observations_by_zone: Dict[str, int]
    observations_by_source: Dict[str, int]
    observations_by_quality_grade: Dict[str, int]

# =====================================================================
# Phase 7 — Planted Plants & NGO Observations CRUD Schemas
# =====================================================================

VALID_PLANT_STATUSES = {"Alive", "Dead", "Unknown"}

class PlantedPlantCreate(BaseModel):
    plant_code: str = Field(..., description="Unique plant identifier e.g. PL001")
    scientific_name: Optional[str] = Field(None, description="Plant scientific name")
    common_name: Optional[str] = Field(None, description="Plant common name")
    planted_on: Optional[str] = Field(None, description="ISO date format YYYY-MM-DD")
    status: str = Field("Alive", description="Plant health condition: Alive, Dead, or Unknown")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude coordinate")
    zone_code: Optional[str] = Field(None, description="Active zone e.g. ZONE A, ZONE B, ZONE C")
    notes: Optional[str] = Field(None, description="Field observation notes")
    photo_url: Optional[str] = Field(None, description="Plant photo URL reference")
    watering_interval_days: Optional[int] = Field(
        None, ge=0, le=365,
        description="Days between waterings for this plant. 0 = never remind. Omit for the default.",
    )
    last_watered_on: Optional[str] = Field(None, description="ISO date of last watering; blank for never watered.")

    @field_validator("status")

    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_PLANT_STATUSES:
            raise ValueError(f"Status must be one of {VALID_PLANT_STATUSES}. Got '{v}'")
        return v

class PlantedPlantUpdate(BaseModel):
    plant_code: Optional[str] = Field(None, description="Unique plant identifier")
    scientific_name: Optional[str] = Field(None, description="Plant scientific name")
    common_name: Optional[str] = Field(None, description="Plant common name")
    planted_on: Optional[str] = Field(None, description="ISO date format YYYY-MM-DD")
    status: Optional[str] = Field(None, description="Plant health condition: Alive, Dead, or Unknown")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="WGS84 latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="WGS84 longitude coordinate")
    zone_code: Optional[str] = Field(None, description="Active zone")
    notes: Optional[str] = Field(None, description="Field observation notes")
    photo_url: Optional[str] = Field(None, description="Plant photo URL reference")
    watering_interval_days: Optional[int] = Field(None, ge=0, le=365, description="Days between waterings. 0 = never.")
    last_watered_on: Optional[str] = Field(None, description="ISO date of last watering.")

    @field_validator("status")

    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PLANT_STATUSES:
            raise ValueError(f"Status must be one of {VALID_PLANT_STATUSES}. Got '{v}'")
        return v

class PlantedPlantResponse(BaseModel):
    id: int
    plant_code: str
    source: str = "Planted Plants"
    scientific_name: Optional[str] = None
    common_name: Optional[str] = None
    planted_on: Optional[str] = None
    status: str
    latitude: float
    longitude: float
    zone_code: Optional[str] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    watering_interval_days: Optional[int] = None
    last_watered_on: Optional[str] = None
    last_watered_by: Optional[str] = None

class PaginatedPlantedPlantsResponse(BaseModel):
    page: int
    limit: int
    total_records: int
    total_pages: int
    data: List[PlantedPlantResponse]

class NGOObservationCreate(BaseModel):
    scientific_name: Optional[str] = Field(None, description="Species scientific name")
    common_name: Optional[str] = Field(None, description="Species common name")
    observed_on: Optional[str] = Field(None, description="ISO date format YYYY-MM-DD")
    observer: Optional[str] = Field("RSWF NGO Volunteer", description="Observer name")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude coordinate")
    photo_url: Optional[str] = Field(None, description="Photo reference URL")
    notes: Optional[str] = Field(None, description="Observation notes")

class ObservationVerificationRequest(BaseModel):
    decision: str = Field("confirm", description="Verification decision: 'confirm', 'correct', or 'needs_review'")
    selected_prediction_rank: Optional[int] = Field(1, ge=1, le=3, description="Rank of selected AI prediction (1, 2, or 3)")
    scientific_name: Optional[str] = Field(None, description="Species scientific name (required for 'correct' decision)")
    common_name: Optional[str] = Field(None, description="Species common name")
    notes: Optional[str] = Field(None, description="Verification or correction notes/reason")

class PlantMonitoringCreate(BaseModel):
    status: str = Field(..., description="Condition status: 'Alive', 'Dead', or 'Unknown'")
    monitoring_date: Optional[str] = Field(None, description="ISO monitoring date YYYY-MM-DD")
    notes: Optional[str] = Field(None, description="Monitoring visit observation notes")
    photo_url: Optional[str] = Field(None, description="Optional photo URL reference")
    observer: Optional[str] = Field("RSWF Field Team", description="Observer name")

class PlantMonitoringResponse(BaseModel):
    id: int
    planted_plant_id: int
    status: str
    monitoring_date: str
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    observer: str
    created_at: str

class GeotagLocationConfirmRequest(BaseModel):
    photo_url: str = Field(..., description="Uploaded photo URL reference")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="User-confirmed WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="User-confirmed WGS84 longitude")
    observed_on: Optional[str] = Field(None, description="Optional observation date YYYY-MM-DD")
    observer: Optional[str] = Field("RSWF Field Volunteer", description="Observer name")
    notes: Optional[str] = Field(None, description="Optional field remarks")

