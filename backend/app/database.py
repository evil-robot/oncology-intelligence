"""Database connection and session management for Neon Postgres with pgvector."""

import hashlib
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

    # Auto-seed taxonomy terms so the app works without a manual pipeline run
    seed_taxonomy()


def seed_geographic_regions():
    """Seed US states with basic geographic data, update existing if SVI missing."""
    from app.models import GeographicRegion

    db = SessionLocal()
    try:
        # SVI data for all states (realistic approximations based on CDC data)
        svi_data = {
            "US-AL": 0.62, "US-AK": 0.38, "US-AZ": 0.55, "US-AR": 0.68,
            "US-CA": 0.52, "US-CO": 0.35, "US-CT": 0.42, "US-DE": 0.48,
            "US-FL": 0.58, "US-GA": 0.60, "US-HI": 0.40, "US-ID": 0.42,
            "US-IL": 0.55, "US-IN": 0.52, "US-IA": 0.38, "US-KS": 0.45,
            "US-KY": 0.65, "US-LA": 0.72, "US-ME": 0.45, "US-MD": 0.48,
            "US-MA": 0.40, "US-MI": 0.55, "US-MN": 0.35, "US-MS": 0.78,
            "US-MO": 0.55, "US-MT": 0.42, "US-NE": 0.40, "US-NV": 0.52,
            "US-NH": 0.30, "US-NJ": 0.48, "US-NM": 0.68, "US-NY": 0.52,
            "US-NC": 0.55, "US-ND": 0.35, "US-OH": 0.55, "US-OK": 0.62,
            "US-OR": 0.45, "US-PA": 0.50, "US-RI": 0.48, "US-SC": 0.60,
            "US-SD": 0.42, "US-TN": 0.58, "US-TX": 0.58, "US-UT": 0.35,
            "US-VT": 0.35, "US-VA": 0.45, "US-WA": 0.42, "US-WV": 0.72,
            "US-WI": 0.42, "US-WY": 0.38,
        }

        # --- Dedup: fix malformed geo_codes and remove duplicates ---
        # Wrapped in its own try/except so a dedup failure can't prevent region seeding
        try:
            all_regions = db.query(GeographicRegion).filter(
                GeographicRegion.level == "state"
            ).all()
            geo_codes_present = {r.geo_code for r in all_regions}
            removed = 0

            for region in all_regions:
                canonical = None

                # Case 1: double-prefix "US-US-XX" → canonical "US-XX"
                if region.geo_code.startswith("US-US-"):
                    canonical = region.geo_code.replace("US-US-", "US-", 1)

                # Case 2: bare abbreviation "AL" → canonical "US-AL"
                elif not region.geo_code.startswith("US-") and len(region.geo_code) == 2:
                    canonical = f"US-{region.geo_code}"

                if canonical:
                    # Migrate TrendData rows via raw SQL to avoid ORM session issues
                    result = db.execute(
                        text("UPDATE trend_data SET geo_code = :new_code WHERE geo_code = :old_code"),
                        {"new_code": canonical, "old_code": region.geo_code},
                    )
                    if result.rowcount:
                        print(f"  Migrated {result.rowcount} trend rows: {region.geo_code} → {canonical}")

                    # If the canonical entry already exists, delete the dupe
                    if canonical in geo_codes_present and canonical != region.geo_code:
                        db.delete(region)
                        removed += 1
                    else:
                        # No canonical entry yet — fix this one in place
                        region.geo_code = canonical
                        geo_codes_present.add(canonical)
                        removed += 1

            if removed:
                db.commit()
                print(f"Cleaned up {removed} duplicate/malformed geographic regions")
        except Exception as dedup_err:
            print(f"Warning: geo dedup failed (non-fatal): {dedup_err}")
            db.rollback()

        # Update existing regions with missing SVI data
        existing_regions = db.query(GeographicRegion).filter(
            GeographicRegion.svi_overall.is_(None)
        ).all()

        for region in existing_regions:
            if region.geo_code in svi_data:
                svi = svi_data[region.geo_code]
                region.svi_overall = svi
                region.svi_socioeconomic = svi * 0.9
                region.svi_household_disability = svi * 1.1
                region.svi_minority_language = svi * 0.8
                region.svi_housing_transport = svi * 1.0

        if existing_regions:
            db.commit()
            print(f"Updated SVI data for {len(existing_regions)} existing regions")

        # US state data with centroids and demo SVI values
        # Always run — creates missing states AND fixes abbreviated names
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

        created = 0
        fixed = 0
        for geo_code, name, lat, lon, pop, svi in states:
            existing = db.query(GeographicRegion).filter(
                GeographicRegion.geo_code == geo_code
            ).first()

            if existing:
                # Fix abbreviated names (e.g. "AL" → "Alabama")
                if existing.name != name and len(existing.name) <= 3:
                    existing.name = name
                    fixed += 1
                # Backfill missing fields
                if existing.latitude is None:
                    existing.latitude = lat
                if existing.longitude is None:
                    existing.longitude = lon
                if existing.population is None:
                    existing.population = pop
                if existing.svi_overall is None:
                    existing.svi_overall = svi
                    existing.svi_socioeconomic = svi * 0.9
                    existing.svi_household_disability = svi * 1.1
                    existing.svi_minority_language = svi * 0.8
                    existing.svi_housing_transport = svi * 1.0
            else:
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
                created += 1

        db.commit()
        if created or fixed:
            print(f"Geographic regions: {created} created, {fixed} names fixed")
    except Exception as e:
        print(f"Error seeding geographic regions: {e}")
        db.rollback()
    finally:
        db.close()


def seed_taxonomy():
    """
    Auto-seed taxonomy terms with synthetic 3D coordinates on startup.

    This ensures the app works immediately after deploy — no manual pipeline
    run needed. Terms get deterministic x/y/z positions grouped by category,
    and demo mode generates synthetic trends, questions, and anxiety patterns
    for any term that exists in the DB.

    Clusters are also auto-created per category so the 3D visualization works.
    """
    from app.models import SearchTerm, Cluster
    from pipeline.taxonomy import get_seed_terms

    db = SessionLocal()
    try:
        # Get all seed terms from taxonomy
        all_seed_terms = get_seed_terms()
        seed_term_lookup = {t.term: t for t in all_seed_terms}

        # Find existing terms in DB
        existing_db_terms = db.query(SearchTerm).all()
        existing_term_names = {t.term for t in existing_db_terms}

        # Find terms that need NEW creation (not in DB at all)
        new_terms = [t for t in all_seed_terms if t.term not in existing_term_names]

        # Find existing terms that are MISSING coordinates (need backfill)
        orphan_terms = [t for t in existing_db_terms if t.x is None or t.y is None or t.z is None]

        if not new_terms and not orphan_terms:
            return  # Everything up to date

        if new_terms:
            print(f"Found {len(new_terms)} new taxonomy terms to seed")
        if orphan_terms:
            print(f"Found {len(orphan_terms)} existing terms missing coordinates — backfilling")

        # Category → base position in 3D space (spread categories across the scene)
        category_positions = {
            "pediatric_oncology": (0.0, 0.0, 0.0),
            "adult_oncology": (3.0, 0.5, -1.0),
            "treatment": (1.5, 2.5, 1.0),
            "rare_genetic": (-2.0, 1.0, 2.0),
            "rare_neurological": (-3.0, -1.0, 0.5),
            "rare_autoimmune": (-1.5, -2.5, -1.0),
            "rare_pulmonary": (2.5, -2.0, 2.5),
            "rare_metabolic": (-4.0, 0.5, -2.0),
            "rare_immune": (0.5, 3.0, -2.5),
            "rare_cancer": (4.0, 1.0, 0.0),
            "clinical_trials": (2.0, -1.0, -3.0),
            "symptoms": (-1.0, 2.0, 3.0),
            "diagnosis": (1.0, -3.0, 1.5),
            "support": (3.5, 2.5, 2.0),
            "survivorship": (-2.5, 3.0, -0.5),
            "caregiver": (0.0, -2.0, -2.0),
            "costs": (4.0, -1.5, -1.5),
            "emerging": (-3.5, -2.0, 3.0),
            "integrative": (2.0, 3.5, -1.0),
            "prevention": (-1.5, -3.5, 0.0),
        }

        # Category colors for clusters
        category_colors = {
            "pediatric_oncology": "#3B82F6",
            "adult_oncology": "#6366F1",
            "treatment": "#22C55E",
            "rare_genetic": "#A855F7",
            "rare_neurological": "#EC4899",
            "rare_autoimmune": "#F97316",
            "rare_pulmonary": "#06B6D4",
            "rare_metabolic": "#8B5CF6",
            "rare_immune": "#14B8A6",
            "rare_cancer": "#EF4444",
            "clinical_trials": "#06B6D4",
            "symptoms": "#EAB308",
            "diagnosis": "#F97316",
            "support": "#14B8A6",
            "survivorship": "#10B981",
            "caregiver": "#F43F5E",
            "costs": "#F59E0B",
            "emerging": "#7C3AED",
            "integrative": "#84CC16",
            "prevention": "#0EA5E9",
        }

        # Ensure clusters exist for each category
        existing_clusters = {c.name: c for c in db.query(Cluster).all()}
        category_cluster_map = {}

        for category, (bx, by, bz) in category_positions.items():
            cluster_name = category.replace("_", " ").title()
            if cluster_name not in existing_clusters:
                cluster = Cluster(
                    name=cluster_name,
                    description=f"Auto-generated cluster for {cluster_name}",
                    centroid_x=bx,
                    centroid_y=by,
                    centroid_z=bz,
                    color=category_colors.get(category, "#6366F1"),
                    size=1.0,
                    term_count=0,
                )
                db.add(cluster)
                db.flush()  # Get the ID
                existing_clusters[cluster_name] = cluster
            category_cluster_map[category] = existing_clusters[cluster_name]

        # Add new terms with deterministic coordinates
        added = 0
        for term_data in new_terms:
            # Deterministic position: hash the term to get offset from category center
            h = hashlib.md5(term_data.term.encode()).hexdigest()
            dx = (int(h[0:4], 16) / 65535.0 - 0.5) * 2.0  # -1.0 to 1.0
            dy = (int(h[4:8], 16) / 65535.0 - 0.5) * 2.0
            dz = (int(h[8:12], 16) / 65535.0 - 0.5) * 2.0

            base = category_positions.get(term_data.category, (0, 0, 0))
            cluster = category_cluster_map.get(term_data.category)

            db_term = SearchTerm(
                term=term_data.term,
                normalized_term=term_data.term.lower().strip(),
                category=term_data.category,
                subcategory=term_data.subcategory,
                x=base[0] + dx,
                y=base[1] + dy,
                z=base[2] + dz,
                cluster_id=cluster.id if cluster else None,
            )
            db.add(db_term)
            added += 1

        # Backfill coordinates on existing terms that are missing them
        backfilled = 0
        for db_term in orphan_terms:
            # Use category from the term itself, or look it up in the seed taxonomy
            category = db_term.category
            if not category and db_term.term in seed_term_lookup:
                category = seed_term_lookup[db_term.term].category
                db_term.category = category
            if not category:
                category = "emerging"  # fallback category

            h = hashlib.md5(db_term.term.encode()).hexdigest()
            dx = (int(h[0:4], 16) / 65535.0 - 0.5) * 2.0
            dy = (int(h[4:8], 16) / 65535.0 - 0.5) * 2.0
            dz = (int(h[8:12], 16) / 65535.0 - 0.5) * 2.0

            base = category_positions.get(category, (0, 0, 0))
            cluster = category_cluster_map.get(category)

            db_term.x = base[0] + dx
            db_term.y = base[1] + dy
            db_term.z = base[2] + dz
            if cluster and not db_term.cluster_id:
                db_term.cluster_id = cluster.id
            backfilled += 1

        # Update cluster term counts
        for category, cluster in category_cluster_map.items():
            count = db.query(SearchTerm).filter(
                SearchTerm.cluster_id == cluster.id
            ).count()
            cluster.term_count = count

        db.commit()
        if added:
            print(f"Seeded {added} new taxonomy terms with synthetic 3D coordinates")
        if backfilled:
            print(f"Backfilled coordinates on {backfilled} existing terms")
    except Exception as e:
        print(f"Error seeding taxonomy: {e}")
        db.rollback()
    finally:
        db.close()


def get_db_connection():
    """Get a raw psycopg2 connection for direct SQL queries."""
    return psycopg2.connect(settings.database_url)
