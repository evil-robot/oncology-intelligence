"""
Pipeline orchestrator - coordinates all pipeline components.

Runs the full data pipeline:
1. Load/expand taxonomy
2. Fetch Google Trends data
3. Generate embeddings
4. Cluster terms
5. Load SDOH data
6. Persist everything to database
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models import SearchTerm, Cluster, TrendData, GeographicRegion, PipelineRun
from pipeline.taxonomy import get_seed_terms, TaxonomyTerm
from pipeline.trends_fetcher import TrendsFetcher, transform_interest_over_time, transform_interest_by_region
from pipeline.embeddings import EmbeddingGenerator, compute_centroid
from pipeline.clustering import ClusteringPipeline, get_cluster_color, generate_cluster_name
from pipeline.sdoh_loader import SDOHLoader, STATE_CENTROIDS

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the full data pipeline."""

    def __init__(self, db: Session):
        self.db = db
        self.trends_fetcher = TrendsFetcher()
        self.embedding_generator = EmbeddingGenerator()
        self.clustering_pipeline = ClusteringPipeline()
        self.sdoh_loader = SDOHLoader()

    async def run_full_pipeline(
        self,
        fetch_trends: bool = True,
        timeframe: str = "today 12-m",
        geo: str = "US",
    ) -> PipelineRun:
        """
        Run the complete data pipeline.

        Args:
            fetch_trends: Whether to fetch fresh Google Trends data
            timeframe: Time range for trends
            geo: Geographic region for trends

        Returns:
            PipelineRun record with status and metrics
        """
        run = PipelineRun(
            pipeline_name="full_pipeline",
            status="running",
            config={"fetch_trends": fetch_trends, "timeframe": timeframe, "geo": geo},
        )
        self.db.add(run)
        self.db.commit()

        try:
            # Step 1: Load taxonomy
            logger.info("Step 1: Loading taxonomy...")
            terms = await self._load_taxonomy()
            run.records_processed = len(terms)

            # Step 2: Generate embeddings
            logger.info("Step 2: Generating embeddings...")
            await self._generate_embeddings(terms)

            # Step 3: Cluster terms
            logger.info("Step 3: Clustering terms...")
            await self._cluster_terms()

            # Step 4: Fetch trends (if enabled)
            if fetch_trends:
                logger.info("Step 4: Fetching Google Trends...")
                await self._fetch_trends(timeframe, geo)

            # Step 5: Load SDOH data
            logger.info("Step 5: Loading SDOH data...")
            await self._load_sdoh_data()

            # Complete
            run.status = "completed"
            run.completed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            run.status = "failed"
            run.errors = [str(e)]
            run.completed_at = datetime.utcnow()

        self.db.commit()
        return run

    async def _load_taxonomy(self) -> list[SearchTerm]:
        """Load seed taxonomy into database."""
        seed_terms = get_seed_terms()
        db_terms = []

        for term_data in seed_terms:
            # Check if term exists
            existing = self.db.query(SearchTerm).filter(
                SearchTerm.term == term_data.term
            ).first()

            if existing:
                db_terms.append(existing)
                continue

            # Create new term
            db_term = SearchTerm(
                term=term_data.term,
                normalized_term=term_data.term.lower().strip(),
                category=term_data.category,
                subcategory=term_data.subcategory,
            )
            self.db.add(db_term)
            db_terms.append(db_term)

        self.db.commit()

        # Set parent relationships
        for term_data in seed_terms:
            if term_data.parent:
                child = self.db.query(SearchTerm).filter(
                    SearchTerm.term == term_data.term
                ).first()
                parent = self.db.query(SearchTerm).filter(
                    SearchTerm.term == term_data.parent
                ).first()
                if child and parent:
                    child.parent_term_id = parent.id

        self.db.commit()
        return db_terms

    async def _generate_embeddings(self, terms: list[SearchTerm]) -> None:
        """Generate embeddings for all terms."""
        terms_needing_embeddings = [t for t in terms if t.embedding is None]

        if not terms_needing_embeddings:
            logger.info("All terms already have embeddings")
            return

        texts = [t.term for t in terms_needing_embeddings]
        embeddings = self.embedding_generator.embed_batch(texts)

        for term, embedding in zip(terms_needing_embeddings, embeddings):
            if embedding:
                term.embedding = embedding

        self.db.commit()

    async def _cluster_terms(self) -> None:
        """Cluster terms and create cluster records."""
        # Get all terms with embeddings
        terms = self.db.query(SearchTerm).filter(
            SearchTerm.embedding.isnot(None)
        ).all()

        if len(terms) < 3:
            logger.warning("Not enough terms with embeddings for clustering")
            return

        # Extract embeddings
        embeddings = np.array([t.embedding for t in terms])

        # Run clustering
        result = self.clustering_pipeline.fit_transform(embeddings)

        # Create cluster records
        cluster_map = {}  # label -> Cluster
        for label in set(result.labels):
            if label == -1:
                continue  # Skip noise

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

            # Compute centroid embedding
            cluster_embeddings = [t.embedding for t in cluster_terms if t.embedding]
            if cluster_embeddings:
                cluster.centroid_embedding = compute_centroid(cluster_embeddings)

            self.db.add(cluster)
            self.db.flush()  # Get ID
            cluster_map[label] = cluster

        # Update terms with coordinates and cluster assignment
        for i, term in enumerate(terms):
            term.x = float(result.coordinates[i, 0])
            term.y = float(result.coordinates[i, 1])
            term.z = float(result.coordinates[i, 2])

            label = result.labels[i]
            if label in cluster_map:
                term.cluster_id = cluster_map[label].id

        self.db.commit()

    async def _fetch_trends(self, timeframe: str, geo: str) -> None:
        """Fetch Google Trends data for all terms."""
        terms = self.db.query(SearchTerm).all()

        for term in terms:
            result = self.trends_fetcher.fetch_term(
                term.term,
                timeframe=timeframe,
                geo=geo,
            )

            # Store interest over time
            for record in transform_interest_over_time(result, geo):
                trend = TrendData(
                    term_id=term.id,
                    date=record["date"],
                    geo_code=record["geo_code"],
                    geo_level=record["geo_level"],
                    interest=record["interest"],
                )
                self.db.add(trend)

            # Store interest by region
            for record in transform_interest_by_region(result):
                # Find or create region
                region = self.db.query(GeographicRegion).filter(
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
                    self.db.add(region)
                    self.db.flush()

                trend = TrendData(
                    term_id=term.id,
                    date=datetime.utcnow(),  # Snapshot date
                    geo_code=region.geo_code,
                    geo_name=region.name,
                    geo_level="state",
                    interest=record["interest"],
                )
                self.db.add(trend)

        self.db.commit()

    async def _load_sdoh_data(self) -> None:
        """Load SDOH data and update geographic regions."""
        county_df = await self.sdoh_loader.load_county_svi()
        if county_df.empty:
            logger.warning("Could not load SDOH data")
            return

        state_df = self.sdoh_loader.aggregate_to_state(county_df)

        for _, row in state_df.iterrows():
            geo_code = row.get("geo_code", "")
            if not geo_code:
                continue

            region = self.db.query(GeographicRegion).filter(
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
                self.db.add(region)

            # Update SDOH fields
            region.population = int(row["population"]) if "population" in row else None
            region.svi_overall = float(row["svi_overall"]) if "svi_overall" in row else None
            region.svi_socioeconomic = float(row["svi_socioeconomic"]) if "svi_socioeconomic" in row else None
            region.svi_household_disability = float(row["svi_household_disability"]) if "svi_household_disability" in row else None
            region.svi_minority_language = float(row["svi_minority_language"]) if "svi_minority_language" in row else None
            region.svi_housing_transport = float(row["svi_housing_transport"]) if "svi_housing_transport" in row else None
            region.uninsured_rate = float(row["uninsured_rate"]) if "uninsured_rate" in row else None

        self.db.commit()


async def run_pipeline(db: Session, **kwargs) -> PipelineRun:
    """Convenience function to run the pipeline."""
    orchestrator = PipelineOrchestrator(db)
    return await orchestrator.run_full_pipeline(**kwargs)
