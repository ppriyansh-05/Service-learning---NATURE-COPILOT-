"""
SQLAlchemy ORM Models Module
Defines relational models matching Phase 4 PostgreSQL/PostGIS schema.
"""

from sqlalchemy import Column, Integer, BigInteger, String, Text, Numeric, Date, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.session import Base

class GeographyBoundary(Base):
    __tablename__ = "geography_boundaries"

    id = Column(Integer, primary_key=True, index=True)
    site_code = Column(String(50), unique=True, nullable=False, default="BAVDHAN_VAN_UDYAN")
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False, default="complete_boundary")
    plus_code = Column(String(50))
    address = Column(Text)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class GeographyZone(Base):
    __tablename__ = "geography_zones"

    id = Column(Integer, primary_key=True, index=True)
    zone_code = Column(String(50), unique=True, nullable=False)
    status = Column(String(50), nullable=False, default="ACTIVE_ZONE")
    description = Column(Text)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TaxonomicTaxa(Base):
    __tablename__ = "taxonomic_taxa"

    id = Column(Integer, primary_key=True, index=True)
    taxon_id = Column(String(50), unique=True)
    scientific_name = Column(String(255), unique=True, nullable=False)
    species_name = Column(String(255))
    common_name = Column(String(255))
    taxon_rank = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Observation(Base):
    __tablename__ = "observations"

    id = Column(BigInteger, primary_key=True, index=True)
    source = Column(String(50), nullable=False, default="iNaturalist")
    source_id = Column(String(100))
    taxon_id = Column(Integer, ForeignKey("taxonomic_taxa.id", ondelete="SET NULL"))
    scientific_name = Column(String(255))
    common_name = Column(String(255))
    observed_on = Column(Date)
    quality_grade = Column(String(50))
    observer = Column(String(100))
    observation_url = Column(Text)
    photo_url = Column(Text)
    latitude = Column(Numeric(10, 8), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)
    zone_id = Column(Integer, ForeignKey("geography_zones.id", ondelete="SET NULL"))
    zone_code = Column(String(50))
    zone_status = Column(String(50), nullable=False, default="OUTSIDE_ACTIVE_ZONES")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    taxon = relationship("TaxonomicTaxa")
    zone_rel = relationship("GeographyZone")

class PlantedPlant(Base):
    __tablename__ = "planted_plants"

    id = Column(BigInteger, primary_key=True, index=True)
    plant_code = Column(String(100), unique=True, nullable=False)
    source = Column(String(50), nullable=False, default="Planted")
    taxon_id = Column(Integer, ForeignKey("taxonomic_taxa.id", ondelete="SET NULL"))
    scientific_name = Column(String(255))
    common_name = Column(String(255))
    planted_on = Column(Date)
    status = Column(String(50), nullable=False, default="Alive")
    latitude = Column(Numeric(10, 8), nullable=False)
    longitude = Column(Numeric(11, 8), nullable=False)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)
    zone_id = Column(Integer, ForeignKey("geography_zones.id", ondelete="SET NULL"))
    zone_code = Column(String(50))
    photo_url = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

class AIPrediction(Base):
    __tablename__ = "ai_predictions"

    id = Column(BigInteger, primary_key=True, index=True)
    observation_id = Column(BigInteger, ForeignKey("observations.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), default="Pl@ntNet")
    organ_used = Column(String(50), default="auto")
    predicted_scientific_name = Column(String(255))
    predicted_common_name = Column(String(255))
    confidence_score = Column(Numeric(5, 4))
    confidence_level = Column(String(50))
    prediction_rank = Column(Integer, default=1)
    model_version = Column(String(50), default="Pl@ntNet-v2")
    top_3_predictions = Column(Text)
    observation = relationship("Observation")

class PlantMonitoring(Base):
    __tablename__ = "plant_monitoring"

    id = Column(BigInteger, primary_key=True, index=True)
    planted_plant_id = Column(BigInteger, ForeignKey("planted_plants.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default="Alive")
    monitoring_date = Column(Date, nullable=False)
    notes = Column(Text)
    photo_url = Column(Text)
    observer = Column(String(255), default="RSWF Field Team")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    planted_plant = relationship("PlantedPlant")
