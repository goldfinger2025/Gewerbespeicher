"""
Health Check Endpoints
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """API Health Check"""
    return {
        "status": "healthy",
        "service": "gewerbespeicher-api",
        "version": "0.1.0"
    }
