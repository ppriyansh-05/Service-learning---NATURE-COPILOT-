"""
Dataset Export API Router Module
Provides downloadable CSV, GeoJSON, and combined ZIP package endpoints for database records.
"""

from fastapi import APIRouter, Query, Response
from typing import Optional
from app.services.data_service import DataService

router = APIRouter(prefix="/export", tags=["Dataset Export"])

@router.get("/observations.csv")
def export_observations_csv(
    source: Optional[str] = Query(None, description="Filter by source stream"),
    species: Optional[str] = Query(None, description="Filter by species or common name"),
    zone: Optional[str] = Query(None, description="Filter by active zone"),
    quality_grade: Optional[str] = Query(None, description="Filter by quality grade")
):
    """Download filtered observations dataset as CSV."""
    csv_data = DataService.export_observations_csv(
        source=source, species=species, zone=zone, quality_grade=quality_grade
    )
    filename = "van_udyan_observations.csv"
    if zone or source:
        clean_z = (zone or "all").replace(" ", "_").lower()
        clean_s = (source or "all").replace(" ", "_").lower()
        filename = f"van_udyan_observations_{clean_s}_{clean_z}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/planted-plants.csv")
def export_planted_plants_csv(
    status: Optional[str] = Query(None, description="Filter by status: Alive, Dead, Unknown"),
    zone: Optional[str] = Query(None, description="Filter by zone e.g. ZONE A, ZONE B, ZONE C"),
    species: Optional[str] = Query(None, description="Filter by scientific or common name")
):
    """Download filtered planted plants dataset as CSV."""
    csv_data = DataService.export_planted_plants_csv(status=status, zone=zone, species=species)
    filename = "van_udyan_planted_plants.csv"
    if status or zone:
        clean_st = (status or "all").lower()
        clean_z = (zone or "all").replace(" ", "_").lower()
        filename = f"van_udyan_planted_plants_{clean_st}_{clean_z}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/species.csv")
def export_species_csv(
    species_name: Optional[str] = Query(None, description="Filter by species name"),
    taxon_rank: Optional[str] = Query(None, description="Filter by taxonomic rank")
):
    """Download species/taxa catalog dataset as CSV."""
    csv_data = DataService.export_species_csv(species_name=species_name, taxon_rank=taxon_rank)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="van_udyan_species.csv"'}
    )

@router.get("/observations.geojson")
def export_observations_geojson(
    source: Optional[str] = Query(None, description="Filter by source stream"),
    species: Optional[str] = Query(None, description="Filter by species or common name"),
    zone: Optional[str] = Query(None, description="Filter by active zone"),
    quality_grade: Optional[str] = Query(None, description="Filter by quality grade")
):
    """Download observations spatial dataset as WGS84 GeoJSON FeatureCollection."""
    geojson_data = DataService.export_observations_geojson(
        source=source, species=species, zone=zone, quality_grade=quality_grade
    )
    import json
    return Response(
        content=json.dumps(geojson_data, indent=2),
        media_type="application/geo+json",
        headers={"Content-Disposition": 'attachment; filename="van_udyan_observations.geojson"'}
    )

@router.get("/planted-plants.geojson")
def export_planted_plants_geojson(
    status: Optional[str] = Query(None, description="Filter by status: Alive, Dead, Unknown"),
    zone: Optional[str] = Query(None, description="Filter by zone e.g. ZONE A, ZONE B, ZONE C"),
    species: Optional[str] = Query(None, description="Filter by species")
):
    """Download planted plants spatial dataset as WGS84 GeoJSON FeatureCollection."""
    geojson_data = DataService.export_planted_plants_geojson(status=status, zone=zone, species=species)
    import json
    return Response(
        content=json.dumps(geojson_data, indent=2),
        media_type="application/geo+json",
        headers={"Content-Disposition": 'attachment; filename="van_udyan_planted_plants.geojson"'}
    )

@router.get("/package.zip")
def export_complete_zip_package():
    """Download complete biodiversity dataset package as ZIP archive containing CSVs & GeoJSONs."""
    zip_bytes = DataService.export_complete_zip_package()
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="van_udyan_biodiversity_complete_package.zip"'}
    )
