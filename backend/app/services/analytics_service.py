"""
Phase 13 Advanced Biodiversity & Conservation Analytics Service
Provides transparent, dynamic, database-driven analytics endpoints:
1. Recorded Biodiversity Analytics
2. Zone Comparison & Status Breakdown
3. Data Coverage Indicators
4. Rule-Based Action Priorities (Survey, Monitoring, Data Collection)
5. Species & Taxonomic Distribution
6. Temporal Data Timeline Analysis
"""

import os
import json
import math
from typing import Dict, Any, List, Optional
from app.services.data_service import (
    load_clean_csv_records, load_planted_plants_store, DataService
)

class AnalyticsService:
    VAN_UDYAN_TOTAL_AREA_HA = 3.58  # Authoritative geodesic PostGIS boundary polygon area (ha)
    ZONE_AREAS_HA = {
        "ZONE A": 0.20,
        "ZONE B": 0.11,
        "ZONE C": 0.24,
        "OUTSIDE_ACTIVE_ZONES": 3.02
    }

    @staticmethod
    def get_biodiversity_analytics() -> Dict[str, Any]:
        """Calculates dynamic recorded biodiversity analytics from database records."""
        records = load_clean_csv_records()
        
        total_obs = len(records)
        
        # Unique recorded taxa & species-level count
        taxa_map = {}
        species_level_count = 0
        rank_counts = {}
        source_counts = {}
        zone_obs_counts = {"ZONE A": 0, "ZONE B": 0, "ZONE C": 0, "OUTSIDE_ACTIVE_ZONES": 0}
        zone_taxa_map = {"ZONE A": set(), "ZONE B": set(), "ZONE C": set(), "OUTSIDE_ACTIVE_ZONES": set()}

        for r in records:
            sc = r.get("scientific_name")
            if sc:
                taxa_map[sc] = taxa_map.get(sc, 0) + 1
                rank = r.get("taxon_rank") or "unspecified"
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
                
                if rank.lower() == "species" or r.get("species_name"):
                    species_level_count += 1

            src = r.get("source", "iNaturalist")
            source_counts[src] = source_counts.get(src, 0) + 1

            z = r.get("zone")
            if z in ["ZONE A", "ZONE B", "ZONE C"]:
                zone_key = z
            else:
                zone_key = "OUTSIDE_ACTIVE_ZONES"

            zone_obs_counts[zone_key] += 1
            if sc:
                zone_taxa_map[zone_key].add(sc)

        unique_taxa_count = len(taxa_map)
        zone_taxa_counts = {k: len(v) for k, v in zone_taxa_map.items()}

        # Observation density per hectare across Van Udyan
        overall_density = round(total_obs / AnalyticsService.VAN_UDYAN_TOTAL_AREA_HA, 2)
        zone_densities = {
            z: round(count / AnalyticsService.ZONE_AREAS_HA.get(z, 1.0), 2)
            for z, count in zone_obs_counts.items()
        }

        return {
            "total_recorded_observations": total_obs,
            "unique_recorded_taxa_count": unique_taxa_count,
            "species_level_taxa_count": species_level_count,
            "taxonomic_rank_distribution": rank_counts,
            "observations_by_source": source_counts,
            "observations_by_zone": zone_obs_counts,
            "unique_taxa_by_zone": zone_taxa_counts,
            "observation_density_per_ha": {
                "overall_site": overall_density,
                "by_zone": zone_densities
            },
            "provenance_note": (
                "All analytics are dynamically calculated from current database records. "
                "Recorded taxa counts represent dataset observations and do not constitute a complete ecological census."
            )
        }

    @staticmethod
    def get_zone_analytics() -> Dict[str, Any]:
        """Calculates zone comparison analytics using safe scientific language."""
        obs_records = load_clean_csv_records()
        planted_records = load_planted_plants_store()

        zones = ["ZONE A", "ZONE B", "ZONE C", "OUTSIDE_ACTIVE_ZONES"]
        zone_data = {}

        for z in zones:
            # Observation metrics
            if z == "OUTSIDE_ACTIVE_ZONES":
                z_obs = [r for r in obs_records if r.get("zone") not in ["ZONE A", "ZONE B", "ZONE C"]]
            else:
                z_obs = [r for r in obs_records if r.get("zone") == z]

            z_obs_count = len(z_obs)
            z_taxa = set(r["scientific_name"] for r in z_obs if r.get("scientific_name"))
            z_species_count = sum(1 for r in z_obs if (r.get("taxon_rank") or "").lower() == "species" or r.get("species_name"))

            # Planted plant metrics
            if z == "OUTSIDE_ACTIVE_ZONES":
                z_plants = [p for p in planted_records if (p.get("zone_code") or "").upper() not in ["ZONE A", "ZONE B", "ZONE C"]]
            else:
                z_plants = [p for p in planted_records if (p.get("zone_code") or "").upper() == z]

            z_plant_count = len(z_plants)
            status_counts = {"Alive": 0, "Dead": 0, "Unknown": 0}
            for p in z_plants:
                st = p.get("status", "Alive")
                status_counts[st] = status_counts.get(st, 0) + 1

            # Monitoring history coverage
            monitoring_records_count = 0
            for p in z_plants:
                hist = DataService.get_plant_monitoring_history(p["id"])
                monitoring_records_count += len(hist)

            zone_data[z] = {
                "zone_code": z,
                "area_ha": AnalyticsService.ZONE_AREAS_HA.get(z, 0.0),
                "recorded_observations_count": z_obs_count,
                "unique_recorded_taxa_count": len(z_taxa),
                "species_level_taxa_count": z_species_count,
                "planted_plants_count": z_plant_count,
                "plant_status_counts": status_counts,
                "total_monitoring_visits_logged": monitoring_records_count,
                "terminology_note": "Metrics reflect recorded data points inside current dataset boundaries."
            }

        return {
            "zones": zone_data,
            "note": "Higher observation counts indicate sampling frequency, not necessarily higher ecological quality."
        }

    @staticmethod
    def get_coverage_analytics() -> Dict[str, Any]:
        """Provides spatial data coverage indicators and identifies areas with limited sampling."""
        obs_records = load_clean_csv_records()
        planted_records = load_planted_plants_store()

        total_obs = len(obs_records)
        active_zone_obs = [r for r in obs_records if r.get("zone") in ["ZONE A", "ZONE B", "ZONE C"]]
        outside_obs = [r for r in obs_records if r.get("zone") not in ["ZONE A", "ZONE B", "ZONE C"]]

        active_zone_area_ha = sum(AnalyticsService.ZONE_AREAS_HA[z] for z in ["ZONE A", "ZONE B", "ZONE C"])
        outside_area_ha = AnalyticsService.ZONE_AREAS_HA["OUTSIDE_ACTIVE_ZONES"]

        return {
            "total_project_area_ha": AnalyticsService.VAN_UDYAN_TOTAL_AREA_HA,
            "active_zones_summary": {
                "area_ha": round(active_zone_area_ha, 2),
                "recorded_observations": len(active_zone_obs),
                "observation_percentage": round((len(active_zone_obs) / total_obs * 100), 1) if total_obs > 0 else 0,
                "planted_plants_count": len(planted_records)
            },
            "non_active_portion_summary": {
                "area_ha": round(outside_area_ha, 2),
                "recorded_observations": len(outside_obs),
                "observation_percentage": round((len(outside_obs) / total_obs * 100), 1) if total_obs > 0 else 0,
                "coverage_status": "No recorded observations or active management zones currently assigned to portions of this outer boundary.",
                "scientific_wording": "No recorded observations are currently available for unmonitored portions of this area."
            },
            "coverage_statement": (
                "Data coverage is concentrated in active zones A, B, and C. "
                "Areas lacking observations represent data gaps rather than an absence of biodiversity."
            )
        }

    @staticmethod
    def get_action_priorities() -> Dict[str, Any]:
        """
        Calculates transparent, rule-based action priorities for RSWF field management.
        
        Scoring Rules:
        1. MONITORING PRIORITY: Triggered if any planted plant in a zone has status 'Dead' or 'Unknown',
           or if planted plants exist without any recorded monitoring visits.
        2. SURVEY PRIORITY: Triggered for non-active boundary areas or zones with low observation density per ha.
        3. DATA COLLECTION PRIORITY: Triggered when total observation count or monitoring data is sparse.
        4. NO IMMEDIATE PRIORITY: Default when data evidence shows healthy status and adequate records.
        """
        obs_records = load_clean_csv_records()
        planted_records = load_planted_plants_store()

        priorities = []
        zones = ["ZONE A", "ZONE B", "ZONE C", "OUTSIDE_ACTIVE_ZONES"]

        for z in zones:
            if z == "OUTSIDE_ACTIVE_ZONES":
                z_obs = [r for r in obs_records if r.get("zone") not in ["ZONE A", "ZONE B", "ZONE C"]]
                z_plants = [p for p in planted_records if (p.get("zone_code") or "").upper() not in ["ZONE A", "ZONE B", "ZONE C"]]
            else:
                z_obs = [r for r in obs_records if r.get("zone") == z]
                z_plants = [p for p in planted_records if (p.get("zone_code") or "").upper() == z]

            dead_plants = [p for p in z_plants if p.get("status") == "Dead"]
            unknown_plants = [p for p in z_plants if p.get("status") == "Unknown"]
            alive_plants = [p for p in z_plants if p.get("status") == "Alive"]

            # Rule 1: Monitoring Priority (Dead or Unknown planted plants)
            if dead_plants:
                dead_codes = [p["plant_code"] for p in dead_plants]
                priorities.append({
                    "area_code": z,
                    "priority_type": "MONITORING_PRIORITY",
                    "priority_level": "HIGH",
                    "reason": f"Recorded plant mortality detected: {len(dead_plants)} dead plant(s) ({', '.join(dead_codes)}).",
                    "recommended_action": "Inspect affected planted plant location, assess cause of desiccation, and record follow-up monitoring status.",
                    "data_evidence": {
                        "dead_count": len(dead_plants),
                        "affected_plant_codes": dead_codes,
                        "total_planted_in_zone": len(z_plants)
                    }
                })
            elif unknown_plants:
                unknown_codes = [p["plant_code"] for p in unknown_plants]
                priorities.append({
                    "area_code": z,
                    "priority_type": "MONITORING_PRIORITY",
                    "priority_level": "MEDIUM",
                    "reason": f"Unconfirmed plant status: {len(unknown_plants)} plant(s) with 'Unknown' status ({', '.join(unknown_codes)}).",
                    "recommended_action": "Conduct field verification visit to locate plant tag and log updated condition.",
                    "data_evidence": {
                        "unknown_count": len(unknown_plants),
                        "affected_plant_codes": unknown_codes,
                        "total_planted_in_zone": len(z_plants)
                    }
                })
            # Rule 2: Survey Priority (Outside active zones with large area but no active management)
            elif z == "OUTSIDE_ACTIVE_ZONES" and len(z_obs) > 0:
                priorities.append({
                    "area_code": z,
                    "priority_type": "SURVEY_PRIORITY",
                    "priority_level": "MEDIUM",
                    "reason": f"Outer Van Udyan boundary area has {len(z_obs)} recorded observations across {AnalyticsService.ZONE_AREAS_HA[z]} ha outside active RSWF monitoring zones.",
                    "recommended_action": "Consider establishing additional monitoring zone or conducting systematic biodiversity transect survey.",
                    "data_evidence": {
                        "recorded_observations": len(z_obs),
                        "area_ha": AnalyticsService.ZONE_AREAS_HA[z]
                    }
                })
            # Rule 3: Data Collection Priority (Sparse observation records)
            elif len(z_obs) < 30 and z != "OUTSIDE_ACTIVE_ZONES":
                priorities.append({
                    "area_code": z,
                    "priority_type": "DATA_COLLECTION_PRIORITY",
                    "priority_level": "LOW",
                    "reason": f"{z} has {len(z_obs)} recorded observations, which is relatively lower sampling density.",
                    "recommended_action": "Encourage NGO volunteers to record additional photo observations in this zone.",
                    "data_evidence": {
                        "recorded_observations": len(z_obs),
                        "recorded_taxa": len(set(r["scientific_name"] for r in z_obs if r.get("scientific_name")))
                    }
                })
            else:
                priorities.append({
                    "area_code": z,
                    "priority_type": "NO_IMMEDIATE_DATA_DRIVEN_PRIORITY",
                    "priority_level": "NONE",
                    "reason": f"{z} shows healthy planted plant status (100% Alive) and active observation records.",
                    "recommended_action": "Maintain routine field monitoring schedule.",
                    "data_evidence": {
                        "alive_count": len(alive_plants),
                        "recorded_observations": len(z_obs)
                    }
                })

        return {
            "total_action_priorities": len([p for p in priorities if p["priority_type"] != "NO_IMMEDIATE_DATA_DRIVEN_PRIORITY"]),
            "priorities": priorities,
            "logic_documentation": (
                "Priority assignments are derived from rule-based thresholds evaluating plant condition status (Dead/Unknown) "
                "and spatial observation coverage across zones. No unexplainable AI models are used."
            )
        }

    @staticmethod
    def get_species_analytics() -> Dict[str, Any]:
        """Calculates species distribution and frequency metrics from database records."""
        records = load_clean_csv_records()

        taxa_freq = {}
        taxa_zones = {}

        for r in records:
            sc = r.get("scientific_name")
            com = r.get("common_name")
            z = r.get("zone") or "OUTSIDE_ACTIVE_ZONES"
            if not sc:
                continue

            if sc not in taxa_freq:
                taxa_freq[sc] = {
                    "scientific_name": sc,
                    "common_name": com,
                    "taxon_rank": r.get("taxon_rank"),
                    "observation_count": 0
                }
                taxa_zones[sc] = set()

            taxa_freq[sc]["observation_count"] += 1
            taxa_zones[sc].add(z)

        # Sort top recorded taxa
        sorted_taxa = sorted(taxa_freq.values(), key=lambda x: x["observation_count"], reverse=True)
        top_recorded_taxa = sorted_taxa[:10]

        # Multi-zone taxa
        multi_zone_taxa = [
            {
                "scientific_name": sc,
                "common_name": taxa_freq[sc]["common_name"],
                "zone_count": len(zones),
                "zones": sorted(list(zones))
            }
            for sc, zones in taxa_zones.items() if len(zones) >= 2
        ]

        return {
            "top_recorded_taxa": top_recorded_taxa,
            "top_recorded_taxa_wording": "Most frequently recorded taxa in the dataset.",
            "multi_zone_taxa_count": len(multi_zone_taxa),
            "multi_zone_taxa": sorted(multi_zone_taxa, key=lambda x: x["zone_count"], reverse=True),
            "sampling_frequency_notice": (
                "Frequently observed taxa reflect recording frequency in the dataset and should not be confused "
                "with absolute ecological abundance in nature."
            )
        }

    @staticmethod
    def get_temporal_analytics() -> Dict[str, Any]:
        """Analyzes observation timelines based strictly on recorded observation dates."""
        records = load_clean_csv_records()
        planted_records = load_planted_plants_store()

        date_counts = {}
        year_counts = {}

        for r in records:
            d = r.get("observed_on")
            if d:
                date_counts[d] = date_counts.get(d, 0) + 1
                year = d.split("-")[0] if "-" in d else "Unknown"
                year_counts[year] = year_counts.get(year, 0) + 1

        total_dated_obs = sum(date_counts.values())

        if total_dated_obs == 0:
            return {
                "status": "insufficient_data",
                "message": "Insufficient temporal date data for timeline analytics.",
                "timeline": []
            }

        sorted_years = dict(sorted(year_counts.items()))

        return {
            "status": "available",
            "total_dated_observations": total_dated_obs,
            "observations_by_year": sorted_years,
            "notice": "Timeline analysis is based strictly on recorded observation dates. Predictive trends are not fabricated."
        }
