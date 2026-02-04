"""Database connection and session management for Neon Postgres with pgvector."""

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pgvector.sqlalchemy import Vector

from app.config import get_settings

settings = get_settings()

# Create engine with connection pooling suitable for serverless
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with pgvector extension and tables."""
    with engine.connect() as conn:
        # Enable pgvector extension
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Create all tables
    Base.metadata.create_all(bind=engine)


def get_db_connection():
    """Get a raw psycopg2 connection for direct SQL queries."""
    return psycopg2.connect(settings.database_url)
