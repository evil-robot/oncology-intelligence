"""SQLAlchemy models for the VIOLET oncology & rare disease intelligence system."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON, Index, Boolean
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.config import get_settings

settings = get_settings()
EMBEDDING_DIM = settings.embedding_dimensions


class SearchTerm(Base):
    """Individual search terms/queries in our taxonomy."""

    __tablename__ = "search_terms"

    id = Column(Integer, primary_key=True)
    term = Column(String(500), nullable=False, unique=True, index=True)
    normalized_term = Column(String(500), nullable=False, index=True)
    category = Column(String(100), index=True)  # e.g., "diagnosis", "treatment", "symptom"
    subcategory = Column(String(100))
    parent_term_id = Column(Integer, ForeignKey("search_terms.id"), nullable=True)

    # Embedding for semantic similarity
    embedding = Column(Vector(EMBEDDING_DIM))

    # 3D coordinates from UMAP dimensionality reduction
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)

    # Cluster assignment
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cluster = relationship("Cluster", back_populates="terms")
    trend_data = relationship("TrendData", back_populates="term", cascade="all, delete-orphan")
    parent = relationship("SearchTerm", remote_side=[id], foreign_keys=[parent_term_id])
    related_queries = relationship("RelatedQuery", foreign_keys="RelatedQuery.source_term_id", back_populates="source_term", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_search_terms_embedding", embedding, postgresql_using="ivfflat"),
    )


class Cluster(Base):
    """Semantic clusters of related search terms."""

    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Centroid coordinates in 3D space
    centroid_x = Column(Float)
    centroid_y = Column(Float)
    centroid_z = Column(Float)

    # Centroid embedding (average of all term embeddings)
    centroid_embedding = Column(Vector(EMBEDDING_DIM))

    # Visual properties
    color = Column(String(7))  # Hex color code
    size = Column(Float, default=1.0)  # Relative size for visualization

    # Stats
    term_count = Column(Integer, default=0)
    avg_search_volume = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships — nullify term/post cluster_id on cluster delete (not cascade delete)
    terms = relationship("SearchTerm", back_populates="cluster", passive_deletes=True)
    posts = relationship("Post", back_populates="cluster", passive_deletes=True)


class TrendData(Base):
    """Google Trends data for search terms over time and geography."""

    __tablename__ = "trend_data"

    id = Column(Integer, primary_key=True)
    term_id = Column(Integer, ForeignKey("search_terms.id"), nullable=False, index=True)

    # Time dimension
    date = Column(DateTime, nullable=False, index=True)
    granularity = Column(String(20), default="weekly")  # daily, weekly, monthly

    # Geographic dimension
    geo_code = Column(String(10), index=True)  # US, US-CA, etc.
    geo_name = Column(String(100))
    geo_level = Column(String(20))  # country, state, metro

    # Metrics
    interest = Column(Integer)  # 0-100 relative interest
    interest_normalized = Column(Float)  # Normalized across time range

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    term = relationship("SearchTerm", back_populates="trend_data")

    __table_args__ = (
        Index("ix_trend_data_term_date_geo", "term_id", "date", "geo_code"),
    )


class GeographicRegion(Base):
    """Geographic regions with SDOH (Social Determinants of Health) data."""

    __tablename__ = "geographic_regions"

    id = Column(Integer, primary_key=True)
    geo_code = Column(String(10), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    level = Column(String(20), nullable=False)  # state, county, metro

    # Geographic coordinates (for mapping)
    latitude = Column(Float)
    longitude = Column(Float)

    # Population data
    population = Column(Integer)

    # CDC Social Vulnerability Index (SVI) components
    svi_overall = Column(Float)  # 0-1, higher = more vulnerable
    svi_socioeconomic = Column(Float)
    svi_household_disability = Column(Float)
    svi_minority_language = Column(Float)
    svi_housing_transport = Column(Float)

    # Additional SDOH metrics
    median_income = Column(Integer)
    uninsured_rate = Column(Float)
    pediatric_oncology_centers = Column(Integer)  # Count of nearby centers

    # Computed metrics
    intent_intensity = Column(Float)  # Aggregate search intensity
    vulnerability_adjusted_intent = Column(Float)  # Intent weighted by SVI

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Post(Base):
    """Content/resources associated with clusters (your content, PubMed, etc.)."""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(2000))
    source = Column(String(100))  # "internal", "pubmed", "news", "curated"
    source_id = Column(String(100))  # External ID (e.g., PMID)

    # Content
    summary = Column(Text)
    content_type = Column(String(50))  # article, video, tool, clinical_trial

    # Embedding for semantic matching
    embedding = Column(Vector(EMBEDDING_DIM))

    # 3D coordinates (positioned near relevant cluster)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)

    # Cluster assignment
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=True)

    # Metadata
    published_at = Column(DateTime)
    relevance_score = Column(Float)
    is_featured = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cluster = relationship("Cluster", back_populates="posts")

    __table_args__ = (
        Index("ix_posts_embedding", embedding, postgresql_using="ivfflat"),
    )


class RelatedQuery(Base):
    """Related queries and topics discovered from Google Trends via SerpAPI."""

    __tablename__ = "related_queries"

    id = Column(Integer, primary_key=True)
    source_term_id = Column(Integer, ForeignKey("search_terms.id"), nullable=False, index=True)

    # The related query or topic
    query = Column(String(500), nullable=False)
    query_type = Column(String(20), nullable=False)  # "rising_query", "top_query", "rising_topic", "top_topic"
    topic_type = Column(String(100))  # For topics: "Disease", "Drug", "Treatment", etc.

    # Value: percentage for rising (e.g., 450), or relative score for top (0-100)
    value = Column(String(50))  # Raw value string (e.g., "Breakout", "+450%", "100")
    extracted_value = Column(Integer)  # Numeric value

    # Whether this query was promoted to a full SearchTerm in the taxonomy
    is_promoted = Column(Boolean, default=False)
    promoted_term_id = Column(Integer, ForeignKey("search_terms.id"), nullable=True)

    discovered_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    source_term = relationship("SearchTerm", foreign_keys=[source_term_id], back_populates="related_queries")

    __table_args__ = (
        Index("ix_related_queries_source_type", "source_term_id", "query_type"),
    )


class HourlyPattern(Base):
    """Aggregated hourly search patterns for terms — the 'vulnerability window' data.

    Stores the average search intensity by hour of day, derived from 7-day hourly
    Google Trends data. Used to identify late-night search anxiety patterns.
    """

    __tablename__ = "hourly_patterns"

    id = Column(Integer, primary_key=True)
    term_id = Column(Integer, ForeignKey("search_terms.id"), nullable=False, index=True)

    # Aggregated hourly averages (JSON: {0: 12.5, 1: 8.3, ..., 23: 45.2})
    hourly_avg = Column(JSON)

    # Day of week averages (JSON: {"Mon": 25.0, "Tue": 30.1, ...})
    day_of_week_avg = Column(JSON)

    # Computed vulnerability metrics
    peak_hours = Column(JSON)  # List of top 3 hours [22, 23, 21]
    anxiety_index = Column(Float)  # Late-night / daytime ratio (>1.0 = more night searching)
    late_night_avg = Column(Float)  # Average interest 11pm-4am
    daytime_avg = Column(Float)  # Average interest 8am-6pm

    # When this pattern was last computed
    fetched_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    term = relationship("SearchTerm")


class QuestionSurface(Base):
    """People Also Ask questions and autocomplete questions for search terms.

    Stores actual human questions discovered from Google's 'People Also Ask' feature
    and autocomplete suggestions. This is the 'narrative layer' — the literal phrasing
    of fear, hope, and confusion that people type at 2am.
    """

    __tablename__ = "question_surface"

    id = Column(Integer, primary_key=True)
    source_term_id = Column(Integer, ForeignKey("search_terms.id"), nullable=False, index=True)

    # The actual human question
    question = Column(String(1000), nullable=False)  # "Is BRCA testing covered by insurance?"
    snippet = Column(Text)  # Answer snippet from PAA
    source_title = Column(String(500))  # Source page title
    source_url = Column(String(2000))  # Source link

    # Source classification
    source_type = Column(String(50), default="people_also_ask")  # "people_also_ask" or "autocomplete"
    rank = Column(Integer)  # Position in PAA results (1-based)

    fetched_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    term = relationship("SearchTerm")

    __table_args__ = (
        Index("ix_question_surface_term", "source_term_id"),
        Index("ix_question_surface_type", "source_term_id", "source_type"),
    )


class DataSource(Base):
    """Track data sources (region + timeframe combinations) that have been fetched."""

    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True)
    geo_code = Column(String(10), nullable=False, index=True)  # US, GB, CA, etc.
    geo_name = Column(String(100))  # United States, United Kingdom, etc.
    timeframe = Column(String(50), nullable=False)  # today 12-m, today 5-y, etc.
    timeframe_label = Column(String(50))  # "1 Year", "5 Years", etc.

    # Date range of the data
    data_start_date = Column(DateTime)
    data_end_date = Column(DateTime)

    # Fetch metadata
    fetched_at = Column(DateTime, default=datetime.utcnow)
    terms_fetched = Column(Integer, default=0)
    trend_points = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_data_sources_geo_time", "geo_code", "timeframe"),
    )


class Sprint(Base):
    """Sprints for product development planning."""

    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True)
    sprint_id = Column(String(20), unique=True, nullable=False, index=True)  # "2026-S1"
    theme = Column(String(300))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    demo_target = Column(String(300))
    release_version = Column(String(50))
    status = Column(String(20), default="planning")  # planning, active, completed, cancelled
    owner = Column(String(100))
    risks = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stories = relationship("Story", back_populates="sprint")


class Story(Base):
    """User stories for sprint planning and the Kanban board."""

    __tablename__ = "stories"

    id = Column(Integer, primary_key=True)
    epic = Column(String(300), index=True)
    feature = Column(String(300))
    user_story = Column(Text)
    priority = Column(String(20))  # Critical, High, Medium, Low
    story_points = Column(Integer)  # Fibonacci: 1,2,3,5,8,13
    status = Column(String(30), default="backlog", index=True)  # backlog, ready, in_progress, review, done, archived
    assigned_to = Column(String(100), index=True)
    dependency = Column(String(500))
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)
    demo_critical = Column(Boolean, default=False)
    acceptance_criteria = Column(Text)
    notes = Column(Text)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sprint = relationship("Sprint", back_populates="stories")


class PipelineRun(Base):
    """Track pipeline execution for monitoring and debugging."""

    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True)
    pipeline_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Metrics
    records_processed = Column(Integer, default=0)
    errors = Column(JSON, default=list)

    # Config used for this run
    config = Column(JSON)
