"""
Phase 13 Advanced Biodiversity & Conservation Analytics Router Module
Exposes REST endpoints for recorded biodiversity, zone comparison, coverage analytics,
rule-based action priorities, species distribution, and temporal timeline.
"""

from fastapi import APIRouter, Query, status
from app.services.analytics_service import AnalyticsService
from app.services.insights_service import (
    species_profile,
    verification_queue,
)

router = APIRouter(prefix="/analytics", tags=["Advanced Analytics & Conservation Insights"])

@router.get("/species-profile")
def get_species_profile(name: str = Query(..., min_length=2, description="Scientific name (case-insensitive)")):
    """Aggregate profile for a species — zones, phenology, pins, sources, rarity."""
    return species_profile(name)

@router.get("/verification-queue")
def get_verification_queue(limit: int = Query(50, ge=1, le=200)):
    """NGO observations awaiting human review (public read; verify POST still requires admin)."""
    return verification_queue(limit=limit)

@router.get("/biodiversity")
def get_biodiversity_analytics():
    """Retrieves recorded biodiversity analytics, taxa counts, rank distribution, and source provenance."""
    return AnalyticsService.get_biodiversity_analytics()

@router.get("/zones")
def get_zone_analytics():
    """Retrieves zone-by-zone recorded observation counts, taxa, planted plant status, and monitoring coverage."""
    return AnalyticsService.get_zone_analytics()

@router.get("/coverage")
def get_coverage_analytics():
    """Retrieves data coverage indicators identifying active zones vs unmonitored portions of Van Udyan."""
    return AnalyticsService.get_coverage_analytics()

@router.get("/action-priorities")
def get_action_priorities():
    """
    Retrieves transparent, rule-based field action recommendations (🌿 Areas Requiring Action)
    categorized into Survey Priority, Monitoring Priority, and Data Collection Priority.
    """
    return AnalyticsService.get_action_priorities()

@router.get("/species")
def get_species_analytics():
    """Retrieves top recorded taxa, multi-zone species distribution, and sampling frequency metrics."""
    return AnalyticsService.get_species_analytics()

@router.get("/temporal")
def get_temporal_analytics():
    """Retrieves observation date timeline metrics based strictly on database recorded timestamps."""
    return AnalyticsService.get_temporal_analytics()
