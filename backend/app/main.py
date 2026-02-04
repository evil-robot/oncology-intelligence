"""
FastAPI application for Oncology & Rare Disease Search Intelligence.

Provides REST API for:
- Cluster and term data
- Trend data by time and geography
- SDOH overlay data
- Pipeline management
- Cross-region comparison
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routes import clusters, terms, trends, geography, pipeline, insights, chat, compare, triangulation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Pediatric Oncology Search Intelligence",
    description="API for analyzing pediatric oncology search trends with SDOH overlay",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.railway.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(clusters.router, prefix="/api/clusters", tags=["clusters"])
app.include_router(terms.router, prefix="/api/terms", tags=["terms"])
app.include_router(trends.router, prefix="/api/trends", tags=["trends"])
app.include_router(geography.router, prefix="/api/geography", tags=["geography"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(compare.router, prefix="/api/compare", tags=["compare"])
app.include_router(triangulation.router, prefix="/api/triangulate", tags=["triangulation"])
app.include_router(chat.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Pediatric Oncology Search Intelligence",
        "version": "0.1.0",
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "database": "connected",
    }
