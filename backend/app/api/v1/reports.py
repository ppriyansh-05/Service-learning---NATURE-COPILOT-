"""
Reports REST API Router for Van Udyan Biodiversity Intelligence Platform.
Exposes endpoints for dynamic NGO conservation decision-support reports and SDG analyses in JSON and PDF formats.
"""

from fastapi import APIRouter, Response, HTTPException
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Conservation Reports & SDG Impact"])

@router.get("/conservation", summary="Get NGO Conservation Decision-Support Report Data (JSON)")
def get_conservation_report_json():
    """
    Returns dynamic NGO conservation decision-support report payload in JSON format.
    Derived dynamically from central PostgreSQL/PostGIS database.
    """
    try:
        data = ReportService.get_conservation_report_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating conservation report: {str(e)}")

@router.get("/sdg", summary="Get SDG Impact Analysis Report Data (JSON)")
def get_sdg_report_json():
    """
    Returns SDG contribution analysis report payload in JSON format.
    Mapped directly to measurable database records.
    """
    try:
        data = ReportService.get_conservation_report_data()
        return {
            "title": "Van Udyan Sustainable Development Goals (SDG) Contribution Report",
            "metadata": data["metadata"],
            "sdg_contributions": data["sdg_contributions"],
            "biodiversity_summary": {
                "total_recorded_observations": data["biodiversity_overview"]["total_recorded_observations"],
                "unique_recorded_taxa_count": data["biodiversity_overview"]["unique_recorded_taxa_count"],
                "active_monitoring_zones": 3
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating SDG report: {str(e)}")

@router.get("/conservation.pdf", summary="Download NGO Conservation & Plantation Planning Report (PDF)")
def download_conservation_report_pdf():
    """
    Generates and streams multi-page PDF conservation & plantation planning report.
    Content-Type: application/pdf
    """
    try:
        pdf_bytes = ReportService.generate_conservation_report_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="van_udyan_conservation_plantation_report.pdf"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error compiling PDF report: {str(e)}")

@router.get("/sdg.pdf", summary="Download SDG & Project Report (PDF)")
def download_sdg_report_pdf():
    """
    Generates and streams multi-page PDF SDG & project report.
    Content-Type: application/pdf
    """
    try:
        pdf_bytes = ReportService.generate_conservation_report_pdf()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="van_udyan_sdg_project_report.pdf"'
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error compiling SDG PDF report: {str(e)}")
