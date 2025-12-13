"""
API v1 Router
Combines all endpoint routers
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, projects, simulations, offers, health, components, optimize

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
