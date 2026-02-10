"""
Pipeline orchestrator - coordinates all pipeline components.

Runs the full data pipeline:
1. Load/expand taxonomy
2. Generate embeddings
3. Cluster terms
4. Fetch search trends + related queries/topics via SerpAPI
5. Expand taxonomy from discovered related queries
6. Load SDOH data
7. Persist everything to database
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models import SearchTerm, Cluster, TrendData, GeographicRegion, PipelineRun, RelatedQuery, HourlyPattern, QuestionSurface
from pipeline.taxonomy import get_seed_terms, TaxonomyTerm
from pipeline.trends_fetcher import (
    TrendsFetcher,
    transform_interest_over_time,
    transform_interest_by_region,
    transform_related_queries,
    transform_related_topics,
    aggregate_hourly_patterns,
)
from pipeline.question_fetcher import QuestionFetcher
from pipeline.embeddings import EmbeddingGenerator, compute_centroid
from pipeline.clustering import ClusteringPipeline, get_cluster_color, generate_cluster_name
from pipeline.sdoh_loader import SDOHLoader, STATE_CENTROIDS

logger = logging.getLogger(__name__)

# Minimum "rising" value to consider a related query worth promoting to taxonomy
PROMOTION_THRESHOLD = 200  # 200% growth or "Breakout"
# Maximum number of new terms to discover per pipeline run
MAX_DISCOVERED_TERMS = 50


class PipelineOrchestrator:
    """Orchestrates the full data pipeline."""

    def __init__(self, db: Session):
        self.db = db
        self.trends_fetcher = TrendsFetcher()
        self.question_fetcher = QuestionFetcher()
        self.embedding_generator = EmbeddingGenerator()
        self.clustering_pipeline = ClusteringPipeline()
        self.sdoh_loader = SDOHLoader()

    async def run_full_pipeline(
        self,
        fetch_trends: bool = True,
        timeframe: str = "today 5-y",  # 5 years of historical data
        geo: str = "US",
    ) -> PipelineRun:
        """
        Run the complete data pipeline.

        Args:
            fetch_trends: Whether to fetch fresh search trend data via SerpAPI
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

            # Step 4: Fetch trends + related data (if enabled)
            if fetch_trends:
                logger.info("Step 4: Fetching search trends via SerpAPI...")
                await self._fetch_trends(timeframe, geo)

                # Step 5: Expand taxonomy from discovered related queries
                logger.info("Step 5: Expanding taxonomy from discoveries...")
                new_terms = await self._expand_taxonomy_from_related()
                if new_terms:
                    # Embed and cluster the new terms
                    logger.info(f"Step 5b: Embedding {len(new_terms)} discovered terms...")
                    await self._generate_embeddings(new_terms)
                    logger.info("Step 5c: Re-clustering with discovered terms...")
                    await self._cluster_terms()

            # Step 6: Fetch People Also Ask questions (Question Surface)
            if fetch_trends:
                logger.info("Step 6: Fetching People Also Ask questions (Question Surface)...")
                await self._fetch_questions()

            # Step 7: Fetch hourly patterns for vulnerability window
            if fetch_trends:
                logger.info("Step 7: Fetching hourly patterns (vulnerability window)...")
                await self._fetch_hourly_patterns(geo)

            # Step 8: Load SDOH data
            logger.info("Step 8: Loading SDOH data...")
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
        """
        Fetch search trend data for all terms via SerpAPI.

        For each term, fetches:
        - Interest over time (5-year timeseries)
        - Interest by region (all US states)
        - Related queries (rising + top)
        - Related topics (rising + top)
        """
        terms = self.db.query(SearchTerm).all()
        total = len(terms)

        # Clear old trend data to avoid duplicates on re-run
        logger.info("Clearing old trend data before refresh...")
        self.db.query(TrendData).delete()
        self.db.query(RelatedQuery).delete()
        self.db.commit()

        for i, term in enumerate(terms):
            logger.info(f"Fetching trends {i + 1}/{total}: {term.term}")

            result = self.trends_fetcher.fetch_term(
                term.term,
                timeframe=timeframe,
                geo=geo,
                include_regions=True,
                include_related=True,
                include_topics=True,
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
                geo_code_full = f"US-{record['geo_code']}" if not record['geo_code'].startswith('US-') else record['geo_code']
                region = self.db.query(GeographicRegion).filter(
                    GeographicRegion.geo_code == geo_code_full
                ).first()

                if not region:
                    state_abbr = geo_code_full.replace("US-", "")
                    centroid = STATE_CENTROIDS.get(state_abbr, (0, 0))
                    region = GeographicRegion(
                        geo_code=geo_code_full,
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

            # Store related queries
            for record in transform_related_queries(result):
                if not record["query"]:
                    continue
                rq = RelatedQuery(
                    source_term_id=term.id,
                    query=record["query"],
                    query_type=record["query_type"],
                    topic_type=record.get("topic_type"),
                    value=record["value"],
                    extracted_value=record["extracted_value"],
                )
                self.db.add(rq)

            # Store related topics
            for record in transform_related_topics(result):
                if not record["query"]:
                    continue
                rt = RelatedQuery(
                    source_term_id=term.id,
                    query=record["query"],
                    query_type=record["query_type"],
                    topic_type=record.get("topic_type"),
                    value=record["value"],
                    extracted_value=record["extracted_value"],
                )
                self.db.add(rt)

            # Commit every 10 terms to avoid large transaction
            if (i + 1) % 10 == 0:
                self.db.commit()
                logger.info(f"Committed batch {i + 1}/{total}")

        self.db.commit()
        logger.info(f"Fetched trends for {total} terms")

    async def _expand_taxonomy_from_related(self) -> list[SearchTerm]:
        """
        Discover new search terms from related queries found during trend fetching.

        Promotes high-value rising queries (≥200% growth or "Breakout") that aren't
        already in the taxonomy. This automatically expands coverage into emerging
        areas of search interest.

        Returns:
            List of newly created SearchTerm objects
        """
        # Get all rising queries/topics with high growth
        rising_queries = self.db.query(RelatedQuery).filter(
            RelatedQuery.query_type.in_(["rising_query", "rising_topic"]),
            RelatedQuery.is_promoted == False,
            RelatedQuery.extracted_value >= PROMOTION_THRESHOLD,
        ).order_by(RelatedQuery.extracted_value.desc()).all()

        if not rising_queries:
            logger.info("No high-growth related queries to promote")
            return []

        # Get existing term names for deduplication
        existing_terms = set(
            t[0].lower() for t in self.db.query(SearchTerm.term).all()
        )

        new_terms = []
        promoted_count = 0

        for rq in rising_queries:
            if promoted_count >= MAX_DISCOVERED_TERMS:
                break

            normalized = rq.query.lower().strip()
            if normalized in existing_terms or len(normalized) < 3:
                continue

            # Get the source term's category to inherit
            source_term = self.db.query(SearchTerm).filter(
                SearchTerm.id == rq.source_term_id
            ).first()
            if not source_term:
                continue

            # Create new term
            new_term = SearchTerm(
                term=rq.query,
                normalized_term=normalized,
                category=source_term.category,
                subcategory=f"discovered:{rq.query_type}",
                parent_term_id=source_term.id,
            )
            self.db.add(new_term)
            existing_terms.add(normalized)

            # Mark as promoted
            rq.is_promoted = True

            new_terms.append(new_term)
            promoted_count += 1

        if new_terms:
            self.db.commit()
            # Update promoted_term_id references
            for new_term, rq in zip(new_terms, [r for r in rising_queries if r.is_promoted]):
                rq.promoted_term_id = new_term.id
            self.db.commit()

            logger.info(f"Discovered and promoted {len(new_terms)} new terms from related queries")
        else:
            logger.info("No new unique terms to promote from related queries")

        return new_terms

    async def _fetch_hourly_patterns(self, geo: str) -> None:
        """
        Fetch 7-day hourly search data for all terms and compute vulnerability patterns.

        This creates the "Search Anxiety Window" — hourly search patterns that reveal
        when people are searching (especially late-night anxiety searches at 2am).
        """
        terms = self.db.query(SearchTerm).all()
        total = len(terms)

        # Clear old hourly patterns
        self.db.query(HourlyPattern).delete()
        self.db.commit()

        patterns_stored = 0

        for i, term in enumerate(terms):
            logger.info(f"Fetching hourly patterns {i + 1}/{total}: {term.term}")

            hourly_df = self.trends_fetcher.fetch_hourly(
                term.term,
                geo=geo,
                window="now 7-d",
            )

            if hourly_df is None or hourly_df.empty:
                continue

            # Aggregate into hour-of-day patterns
            patterns = aggregate_hourly_patterns(hourly_df)
            if not patterns:
                continue

            pattern = HourlyPattern(
                term_id=term.id,
                hourly_avg=patterns.get("hourly_avg"),
                day_of_week_avg=patterns.get("day_of_week"),
                peak_hours=patterns.get("peak_hours"),
                anxiety_index=patterns.get("anxiety_index"),
                late_night_avg=patterns.get("late_night_avg"),
                daytime_avg=patterns.get("daytime_avg"),
            )
            self.db.add(pattern)
            patterns_stored += 1

            # Commit every 10 terms
            if (i + 1) % 10 == 0:
                self.db.commit()

        self.db.commit()
        logger.info(f"Stored hourly patterns for {patterns_stored}/{total} terms")

    async def _fetch_questions(self) -> None:
        """
        Fetch People Also Ask questions and autocomplete questions for all terms.

        This creates the 'Question Surface' — the literal human phrasing of questions
        around each oncology term. These are the 2am questions, the scared-parent
        questions, the questions that reveal intent behind the search terms.
        """
        terms = self.db.query(SearchTerm).all()
        total = len(terms)

        # Clear old question data
        self.db.query(QuestionSurface).delete()
        self.db.commit()

        questions_stored = 0

        for i, term in enumerate(terms):
            logger.info(f"Fetching questions {i + 1}/{total}: {term.term}")

            try:
                result = self.question_fetcher.fetch_all_questions(
                    term.term,
                    paa_pages=2,
                    max_prefixes=5,
                )

                for q in result.questions:
                    question = QuestionSurface(
                        source_term_id=term.id,
                        question=q.question,
                        snippet=q.snippet,
                        source_title=q.source_title,
                        source_url=q.source_url,
                        source_type=q.source_type,
                        rank=q.rank,
                    )
                    self.db.add(question)
                    questions_stored += 1

            except Exception as e:
                logger.warning(f"Failed to fetch questions for '{term.term}': {e}")

            # Commit every 10 terms
            if (i + 1) % 10 == 0:
                self.db.commit()
                logger.info(f"Committed questions batch {i + 1}/{total}")

        self.db.commit()
        logger.info(f"Stored {questions_stored} questions for {total} terms")

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
