"""
Main FastAPI Application Entry Point
Initializes FastAPI app, configures CORS middleware, registers v1 API routers, mounts static uploads directory, and configures exception handlers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sys
import os

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.api.v1 import health, observations, species, zones, geography, map, statistics, planted_plants, export, analytics, reports

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Geospatial Biodiversity Mapping, Monitoring & AI Analytics System for RSWF NGO",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Uploads Directory
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
uploads_dir = os.path.join(base_dir, "data", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Register Health Endpoints
app.include_router(health.router)

# Register API v1 Routers
api_v1_prefix = settings.API_V1_STR
app.include_router(observations.router, prefix=api_v1_prefix)
app.include_router(species.router, prefix=api_v1_prefix)
app.include_router(zones.router, prefix=api_v1_prefix)
app.include_router(geography.router, prefix=api_v1_prefix)
app.include_router(map.router, prefix=api_v1_prefix)
app.include_router(statistics.router, prefix=api_v1_prefix)
app.include_router(planted_plants.router, prefix=api_v1_prefix)
app.include_router(export.router, prefix=api_v1_prefix)
app.include_router(analytics.router, prefix=api_v1_prefix)
app.include_router(reports.router, prefix=api_v1_prefix)

@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "Welcome to Van Udyan Biodiversity Intelligence Platform API",
        "documentation": "/docs",
        "health": "/health",
        "api_v1": "/api/v1/observations"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
