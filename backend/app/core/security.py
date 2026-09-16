"""
Security and Authorization Module for Van Udyan Biodiversity Intelligence Platform.
Enforces password protection for NGO data mutation endpoints (editing, status changes, deletions)
while preserving open public access for viewing, searching, uploading, exporting, and report generation.
"""

from fastapi import Header, HTTPException, status
from app.core.config import settings


def verify_ngo_admin_password(
    x_ngo_admin_password: str = Header(None, alias="X-NGO-Admin-Password")
) -> str:
    """
    Dependency verifying that the provided X-NGO-Admin-Password header matches
    the configured RSWF NGO administrative password.
    Returns 401 Unauthorized if missing or invalid.
    Never exposes or logs the plaintext password.
    """
    if not x_ngo_admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NGO administrative password is required for editing or deleting records."
        )

    expected_password = settings.NGO_ADMIN_PASSWORD
    if x_ngo_admin_password != expected_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid NGO administrative password."
        )

    return x_ngo_admin_password
