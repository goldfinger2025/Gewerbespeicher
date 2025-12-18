"""
API v1 Router
Combines all endpoint routers
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    projects,
    simulations,
    offers,
    health,
    components,
    optimize,
    analytics,
    integrations,
    tenants,
    api_keys,
    gewerbe,
)

router = APIRouter()

# Include all endpoint routers
router.include_router(
    health.router,
    tags=["Health"]
)

router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

router.include_router(
    tenants.router,
    prefix="/tenants",
    tags=["Tenants"]
)

router.include_router(
    api_keys.router,
    prefix="/api-keys",
    tags=["API Keys"]
)

router.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"]
)

router.include_router(
    simulations.router,
    prefix="/simulations",
    tags=["Simulations"]
)

router.include_router(
    offers.router,
    prefix="/offers",
    tags=["Offers"]
)

router.include_router(
    components.router,
    prefix="/components",
    tags=["Components"]
)

router.include_router(
    optimize.router,
    prefix="/ai",
    tags=["AI & Optimization"]
)

router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"]
)

router.include_router(
    integrations.router,
    prefix="/integrations",
    tags=["Integrations"]
)

router.include_router(
    gewerbe.router,
    prefix="/gewerbe",
    tags=["Gewerbespeicher"]
)
