#!/usr/bin/env python3
"""
Run the data pipeline to populate real data.

Usage:
    python run_pipeline.py                      # Full pipeline with trends (slow, may hit rate limits)
    python run_pipeline.py --no-trends          # Just taxonomy, embeddings, clusters (fast)
    python run_pipeline.py --sample 20          # Fetch trends for only 20 terms

Timeframe options (--timeframe):
    today 1-m   = Past month
    today 3-m   = Past 3 months
    today 12-m  = Past year (default)
    today 5-y   = Past 5 years
    all         = All time (from 2004)

Geographic options (--geo):
    US    = United States (default)
    GB    = United Kingdom
    CA    = Canada
    AU    = Australia
    DE    = Germany
    FR    = France
    JP    = Japan
    (blank) = Worldwide

Examples:
    python run_pipeline.py --timeframe "today 5-y" --geo US --sample 30
    python run_pipeline.py --timeframe "today 12-m" --geo GB
    python run_pipeline.py --no-trends  # Fast: just taxonomy + embeddings + clusters
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add parent to path for imports
sys.path.insert(0, ".")

from app.database import SessionLocal, init_db
from app.models import SearchTerm, Cluster, TrendData, GeographicRegion, Post
from pipeline.taxonomy import get_seed_terms
from pipeline.embeddings import EmbeddingGenerator
from pipeline.clustering import ClusteringPipeline, get_cluster_color, generate_cluster_name
from pipeline.trends_fetcher import TrendsFetcher, transform_interest_over_time, transform_interest_by_region
from pipeline.sdoh_loader import SDOHLoader, STATE_CENTROIDS
import numpy as np


async def run_taxonomy_and_embeddings(db):
    """Load taxonomy and generate embeddings."""
    logger.info("Loading taxonomy...")
    seed_terms = get_seed_terms()
    db_terms = []

    for term_data in seed_terms:
        existing = db.query(SearchTerm).filter(SearchTerm.term == term_data.term).first()
        if existing:
            db_terms.append(existing)
            continue

        db_term = SearchTerm(
            term=term_data.term,
            normalized_term=term_data.term.lower().strip(),
            category=term_data.category,
            subcategory=term_data.subcategory,
        )
        db.add(db_term)
        db_terms.append(db_term)

    db.commit()
    logger.info(f"Loaded {len(db_terms)} terms")

    # Generate embeddings
    logger.info("Generating embeddings (this may take a minute)...")
    embedding_gen = EmbeddingGenerator()
    terms_needing_embeddings = [t for t in db_terms if t.embedding is None]

    if terms_needing_embeddings:
        texts = [t.term for t in terms_needing_embeddings]
        embeddings = embedding_gen.embed_batch(texts)

        for term, embedding in zip(terms_needing_embeddings, embeddings):
            if embedding:
                term.embedding = embedding

        db.commit()
        logger.info(f"Generated {len(embeddings)} embeddings")
    else:
        logger.info("All terms already have embeddings")

    return db_terms


async def run_clustering(db):
    """Cluster terms based on embeddings."""
    logger.info("Clustering terms...")

    # Clear existing cluster assignments first (foreign key constraint)
    db.query(SearchTerm).update({SearchTerm.cluster_id: None})
    db.commit()

    # Now we can safely delete clusters
    db.query(Cluster).delete()
    db.commit()

    terms = db.query(SearchTerm).filter(SearchTerm.embedding.isnot(None)).all()

    if len(terms) < 3:
        logger.warning("Not enough terms with embeddings for clustering")
        return

    embeddings = np.array([t.embedding for t in terms])
    clustering = ClusteringPipeline()
    result = clustering.fit_transform(embeddings)

    cluster_map = {}
    for label in set(result.labels):
        if label == -1:
            continue

        cluster_terms = [terms[i] for i, l in enumerate(result.labels) if l == label]
        term_names = [t.term for t in cluster_terms]

        cluster = Cluster(
            name=generate_cluster_name(term_names),
            centroid_x=float(result.centroids[label][0]),
            centroid_y=float(result.centroids[label][1]),
            centroid_z=float(result.centroids[label][2]),
            color=get_cluster_color(label),
            term_count=len(cluster_terms),
        )
        db.add(cluster)
        db.flush()
        cluster_map[label] = cluster

    for i, term in enumerate(terms):
        term.x = float(result.coordinates[i, 0])
        term.y = float(result.coordinates[i, 1])
        term.z = float(result.coordinates[i, 2])

        label = result.labels[i]
        if label in cluster_map:
            term.cluster_id = cluster_map[label].id

    db.commit()
    logger.info(f"Created {len(cluster_map)} clusters")


async def run_trends(db, timeframe="today 12-m", geo="US", sample_size=None):
    """Fetch Google Trends data."""
    logger.info(f"Fetching Google Trends data (timeframe: {timeframe}, geo: {geo})...")

    terms = db.query(SearchTerm).all()
    if sample_size:
        terms = terms[:sample_size]
        logger.info(f"Fetching trends for {len(terms)} terms (sampled)")

    fetcher = TrendsFetcher()
    total = len(terms)

    for i, term in enumerate(terms):
        logger.info(f"[{i+1}/{total}] Fetching: {term.term}")
        try:
            result = fetcher.fetch_term(term.term, timeframe=timeframe, geo=geo)

            # Store interest over time
            for record in transform_interest_over_time(result, geo):
                trend = TrendData(
                    term_id=term.id,
                    date=record["date"],
                    geo_code=record["geo_code"],
                    geo_level=record["geo_level"],
                    interest=record["interest"],
                )
                db.add(trend)

            # Store interest by region (for US data)
            if geo == "US":
                for record in transform_interest_by_region(result):
                    region = db.query(GeographicRegion).filter(
                        GeographicRegion.geo_code == f"US-{record['geo_code']}"
                    ).first()

                    if not region:
                        centroid = STATE_CENTROIDS.get(record["geo_code"], (0, 0))
                        region = GeographicRegion(
                            geo_code=f"US-{record['geo_code']}",
                            name=record["geo_name"],
                            level="state",
                            latitude=centroid[0],
                            longitude=centroid[1],
                        )
                        db.add(region)
                        db.flush()

                    trend = TrendData(
                        term_id=term.id,
                        date=datetime.utcnow(),
                        geo_code=region.geo_code,
                        geo_name=region.name,
                        geo_level="state",
                        interest=record["interest"],
                    )
                    db.add(trend)

            db.commit()

            # Small delay to avoid rate limiting
            import time
            time.sleep(0.5)

        except Exception as e:
            logger.warning(f"Failed to fetch trends for '{term.term}': {e}")
            continue

    logger.info("Trends fetching complete")


async def run_sdoh(db):
    """Load SDOH data."""
    logger.info("Loading SDOH data...")

    loader = SDOHLoader()
    county_df = await loader.load_county_svi()

    if county_df.empty:
        logger.warning("Could not load SDOH data - using defaults")
        # Create basic state regions
        for abbr, (lat, lng) in STATE_CENTROIDS.items():
            existing = db.query(GeographicRegion).filter(
                GeographicRegion.geo_code == f"US-{abbr}"
            ).first()
            if not existing:
                region = GeographicRegion(
                    geo_code=f"US-{abbr}",
                    name=abbr,
                    level="state",
                    latitude=lat,
                    longitude=lng,
                )
                db.add(region)
        db.commit()
        return

    state_df = loader.aggregate_to_state(county_df)

    for _, row in state_df.iterrows():
        geo_code = row.get("geo_code", "")
        if not geo_code:
            continue

        region = db.query(GeographicRegion).filter(
            GeographicRegion.geo_code == geo_code
        ).first()

        if not region:
            state_abbr = geo_code.replace("US-", "")
            centroid = STATE_CENTROIDS.get(state_abbr, (0, 0))
            region = GeographicRegion(
                geo_code=geo_code,
                name=row.get("state", state_abbr),
                level="state",
                latitude=centroid[0],
                longitude=centroid[1],
            )
            db.add(region)

        region.population = int(row["population"]) if "population" in row else None
        region.svi_overall = float(row["svi_overall"]) if "svi_overall" in row else None

    db.commit()
    logger.info("SDOH data loaded")


async def main():
    parser = argparse.ArgumentParser(description="Run the data pipeline")
    parser.add_argument("--no-trends", action="store_true", help="Skip Google Trends fetching")
    parser.add_argument("--sample", type=int, help="Only fetch trends for N terms")
    parser.add_argument("--reset", action="store_true", help="Clear all data first")
    parser.add_argument(
        "--timeframe",
        default="today 12-m",
        help="Time range: 'today 1-m', 'today 3-m', 'today 12-m', 'today 5-y', 'all'"
    )
    parser.add_argument(
        "--geo",
        default="US",
        help="Geographic region: US, GB, CA, AU, DE, FR, JP, or empty for worldwide"
    )
    args = parser.parse_args()

    # Initialize database
    init_db()
    db = SessionLocal()

    try:
        if args.reset:
            logger.info("Clearing existing data...")
            # Delete in correct order to respect foreign key constraints
            db.query(Post).delete()  # Posts reference clusters
            db.query(TrendData).delete()  # Trends reference search_terms
            db.query(SearchTerm).delete()  # Search terms reference clusters
            db.query(Cluster).delete()
            db.commit()
            logger.info("Data cleared successfully")

        # Run pipeline stages
        await run_taxonomy_and_embeddings(db)
        await run_clustering(db)
        await run_sdoh(db)

        if not args.no_trends:
            await run_trends(
                db,
                timeframe=args.timeframe,
                geo=args.geo,
                sample_size=args.sample
            )

        # Print summary
        term_count = db.query(SearchTerm).count()
        cluster_count = db.query(Cluster).count()
        trend_count = db.query(TrendData).count()
        region_count = db.query(GeographicRegion).count()

        logger.info("=" * 50)
        logger.info("Pipeline complete!")
        logger.info(f"  Terms: {term_count}")
        logger.info(f"  Clusters: {cluster_count}")
        logger.info(f"  Trend data points: {trend_count}")
        logger.info(f"  Geographic regions: {region_count}")
        logger.info("=" * 50)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
