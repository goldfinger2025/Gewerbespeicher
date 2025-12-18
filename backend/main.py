"""
Gewerbespeicher Planner API
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api.v1.router import router as v1_router
from app.database import init_db, close_db

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Gewerbespeicher Planner API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL[:30]}...")
    logger.info(f"CORS Origins: {settings.ALLOWED_ORIGINS}")

    # Initialize database tables
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await close_db()


# Initialize FastAPI Application
app = FastAPI(
    title="Gewerbespeicher Planner API",
    description="""
    KI-gestützte Planung und Angebotserstellung für PV-Speichersysteme.

    ## Features
    - 🔋 PV + Speicher Simulation
    - 📊 Wirtschaftlichkeitsberechnung
    - 🤖 KI-Angebotserstellung mit Claude
    - 📄 PDF-Generierung
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add Rate Limiter to app state
app.state.limiter = limiter

# Add Rate Limit Exception Handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Zu viele Anfragen. Bitte warten Sie einen Moment.",
            "retry_after": str(exc.detail)
        }
    )

# CORS Middleware - Must be added BEFORE routes to handle preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight response for 10 minutes
)

# Include API Routes
app.include_router(v1_router, prefix="/api/v1")


# Health Check Endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "service": "gewerbespeicher-api"
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API info"""
    return {
        "message": "🔋 Gewerbespeicher Planner API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


# Run with: python main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
