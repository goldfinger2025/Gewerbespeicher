"""
Gewerbespeicher Planner API
Main FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.api.v1.router import router as v1_router

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
    logger.info("🚀 Starting Gewerbespeicher Planner API...")
    logger.info(f"📦 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔗 Database: {settings.DATABASE_URL[:30]}...")
    yield
    # Shutdown
    logger.info("👋 Shutting down...")


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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
