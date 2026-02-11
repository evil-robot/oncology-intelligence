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
import secrets
import base64
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import init_db
from app.routes import clusters, terms, trends, geography, pipeline, insights, chat, compare, triangulation, questions, stories

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Authentication middleware."""

    def __init__(self, app, username: str, password: str):
        super().__init__(app)
        self.username = username
        self.password = password

    async def dispatch(self, request: Request, call_next):
        # Skip auth for health check endpoints
        if request.url.path in ["/", "/api/health"]:
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")

        if auth_header is None or not auth_header.startswith("Basic "):
            return Response(
                content="Authentication required",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="SuperTruth Violet"'},
            )

        # Decode and verify credentials
        try:
            encoded_credentials = auth_header.split(" ")[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)

            # Use secrets.compare_digest to prevent timing attacks
            if not (
                secrets.compare_digest(username, self.username)
                and secrets.compare_digest(password, self.password)
            ):
                return Response(
                    content="Invalid credentials",
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="SuperTruth Violet"'},
                )
        except Exception:
            return Response(
                content="Invalid authorization header",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="SuperTruth Violet"'},
            )

        return await call_next(request)


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

# CORS middleware — restrict to known origins (configurable via CORS_ORIGINS env var)
cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info(f"CORS allowed origins: {cors_origins}")

# Include routers
app.include_router(clusters.router, prefix="/api/clusters", tags=["clusters"])
app.include_router(terms.router, prefix="/api/terms", tags=["terms"])
app.include_router(trends.router, prefix="/api/trends", tags=["trends"])
app.include_router(geography.router, prefix="/api/geography", tags=["geography"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(compare.router, prefix="/api/compare", tags=["compare"])
app.include_router(triangulation.router, prefix="/api/triangulate", tags=["triangulation"])
app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
app.include_router(chat.router)
app.include_router(stories.router, tags=["stories"])


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
