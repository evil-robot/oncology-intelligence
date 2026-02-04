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

    # Seed geographic regions if empty
    seed_geographic_regions()


def seed_geographic_regions():
    """Seed US states with basic geographic data if table is empty."""
    from app.models import GeographicRegion

    db = SessionLocal()
    try:
        # Check if we have any regions
        count = db.query(GeographicRegion).count()
        if count > 0:
            return  # Already seeded

        # US state data with centroids and demo SVI values
        states = [
            ("US-AL", "Alabama", 32.806671, -86.791130, 5024279, 0.62),
            ("US-AK", "Alaska", 61.370716, -152.404419, 733391, 0.38),
            ("US-AZ", "Arizona", 33.729759, -111.431221, 7151502, 0.55),
            ("US-AR", "Arkansas", 34.969704, -92.373123, 3011524, 0.68),
            ("US-CA", "California", 36.116203, -119.681564, 39538223, 0.52),
            ("US-CO", "Colorado", 39.059811, -105.311104, 5773714, 0.35),
            ("US-CT", "Connecticut", 41.597782, -72.755371, 3605944, 0.42),
            ("US-DE", "Delaware", 39.318523, -75.507141, 989948, 0.48),
            ("US-FL", "Florida", 27.766279, -81.686783, 21538187, 0.58),
            ("US-GA", "Georgia", 33.040619, -83.643074, 10711908, 0.60),
            ("US-HI", "Hawaii", 21.094318, -157.498337, 1455271, 0.40),
            ("US-ID", "Idaho", 44.240459, -114.478828, 1839106, 0.42),
            ("US-IL", "Illinois", 40.349457, -88.986137, 12812508, 0.55),
            ("US-IN", "Indiana", 39.849426, -86.258278, 6785528, 0.52),
            ("US-IA", "Iowa", 42.011539, -93.210526, 3190369, 0.38),
            ("US-KS", "Kansas", 38.526600, -96.726486, 2937880, 0.45),
            ("US-KY", "Kentucky", 37.668140, -84.670067, 4505836, 0.65),
            ("US-LA", "Louisiana", 31.169546, -91.867805, 4657757, 0.72),
            ("US-ME", "Maine", 44.693947, -69.381927, 1362359, 0.45),
            ("US-MD", "Maryland", 39.063946, -76.802101, 6177224, 0.48),
            ("US-MA", "Massachusetts", 42.230171, -71.530106, 7029917, 0.40),
            ("US-MI", "Michigan", 43.326618, -84.536095, 10077331, 0.55),
            ("US-MN", "Minnesota", 45.694454, -93.900192, 5706494, 0.35),
            ("US-MS", "Mississippi", 32.741646, -89.678696, 2961279, 0.78),
            ("US-MO", "Missouri", 38.456085, -92.288368, 6154913, 0.55),
            ("US-MT", "Montana", 46.921925, -110.454353, 1084225, 0.42),
            ("US-NE", "Nebraska", 41.125370, -98.268082, 1961504, 0.40),
            ("US-NV", "Nevada", 38.313515, -117.055374, 3104614, 0.52),
            ("US-NH", "New Hampshire", 43.452492, -71.563896, 1377529, 0.30),
            ("US-NJ", "New Jersey", 40.298904, -74.521011, 9288994, 0.48),
            ("US-NM", "New Mexico", 34.840515, -106.248482, 2117522, 0.68),
            ("US-NY", "New York", 42.165726, -74.948051, 20201249, 0.52),
            ("US-NC", "North Carolina", 35.630066, -79.806419, 10439388, 0.55),
            ("US-ND", "North Dakota", 47.528912, -99.784012, 779094, 0.35),
            ("US-OH", "Ohio", 40.388783, -82.764915, 11799448, 0.55),
            ("US-OK", "Oklahoma", 35.565342, -96.928917, 3959353, 0.62),
            ("US-OR", "Oregon", 44.572021, -122.070938, 4237256, 0.45),
            ("US-PA", "Pennsylvania", 40.590752, -77.209755, 13002700, 0.50),
            ("US-RI", "Rhode Island", 41.680893, -71.511780, 1097379, 0.48),
            ("US-SC", "South Carolina", 33.856892, -80.945007, 5118425, 0.60),
            ("US-SD", "South Dakota", 44.299782, -99.438828, 886667, 0.42),
            ("US-TN", "Tennessee", 35.747845, -86.692345, 6910840, 0.58),
            ("US-TX", "Texas", 31.054487, -97.563461, 29145505, 0.58),
            ("US-UT", "Utah", 40.150032, -111.862434, 3271616, 0.35),
            ("US-VT", "Vermont", 44.045876, -72.710686, 643077, 0.35),
            ("US-VA", "Virginia", 37.769337, -78.169968, 8631393, 0.45),
            ("US-WA", "Washington", 47.400902, -121.490494, 7614893, 0.42),
            ("US-WV", "West Virginia", 38.491226, -80.954453, 1793716, 0.72),
            ("US-WI", "Wisconsin", 44.268543, -89.616508, 5893718, 0.42),
            ("US-WY", "Wyoming", 42.755966, -107.302490, 576851, 0.38),
        ]

        for geo_code, name, lat, lon, pop, svi in states:
            region = GeographicRegion(
                geo_code=geo_code,
                name=name,
                level="state",
                latitude=lat,
                longitude=lon,
                population=pop,
                svi_overall=svi,
                svi_socioeconomic=svi * 0.9,
                svi_household_disability=svi * 1.1,
                svi_minority_language=svi * 0.8,
                svi_housing_transport=svi * 1.0,
            )
            db.add(region)

        db.commit()
        print(f"Seeded {len(states)} US states into geographic_regions")
    except Exception as e:
        print(f"Error seeding geographic regions: {e}")
        db.rollback()
    finally:
        db.close()


def get_db_connection():
    """Get a raw psycopg2 connection for direct SQL queries."""
    return psycopg2.connect(settings.database_url)
