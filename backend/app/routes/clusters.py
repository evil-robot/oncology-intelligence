"""Cluster API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Cluster, SearchTerm, Post

router = APIRouter()


class ClusterResponse(BaseModel):
    """Cluster data for API response."""

    id: int
    name: str
    description: Optional[str]
    centroid_x: float
    centroid_y: float
    centroid_z: float
    color: str
    size: float
    term_count: int
    avg_search_volume: Optional[float]

    class Config:
        from_attributes = True


class ClusterDetailResponse(ClusterResponse):
    """Detailed cluster response with terms."""

    terms: list[dict]
    posts: list[dict]


class ClusterVisualizationResponse(BaseModel):
    """Data formatted for 3D visualization."""

    clusters: list[dict]
    terms: list[dict]
    posts: list[dict]


@router.get("/", response_model=list[ClusterResponse])
async def list_clusters(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by term category"),
):
    """List all clusters."""
    query = db.query(Cluster)

    if category:
        # Filter to clusters containing terms in the specified category
        query = query.join(SearchTerm).filter(SearchTerm.category == category).distinct()

    clusters = query.all()
    return [ClusterResponse.model_validate(c) for c in clusters]


@router.get("/visualization", response_model=ClusterVisualizationResponse)
async def get_visualization_data(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None),
    cluster_id: Optional[int] = Query(None),
):
    """
    Get all data needed for 3D visualization.

    Returns clusters, terms, and posts with their 3D coordinates.
    """
    # Build term query
    term_query = db.query(SearchTerm).filter(
        SearchTerm.x.isnot(None),
        SearchTerm.y.isnot(None),
        SearchTerm.z.isnot(None),
    )

    if category:
        term_query = term_query.filter(SearchTerm.category == category)
    if cluster_id:
        term_query = term_query.filter(SearchTerm.cluster_id == cluster_id)

    terms = term_query.all()

    # Get relevant clusters
    cluster_ids = set(t.cluster_id for t in terms if t.cluster_id)
    clusters = db.query(Cluster).filter(Cluster.id.in_(cluster_ids)).all() if cluster_ids else []

    # Get posts for these clusters
    posts = db.query(Post).filter(
        Post.cluster_id.in_(cluster_ids),
        Post.x.isnot(None),
    ).all() if cluster_ids else []

    return ClusterVisualizationResponse(
        clusters=[
            {
                "id": c.id,
                "name": c.name,
                "x": c.centroid_x,
                "y": c.centroid_y,
                "z": c.centroid_z,
                "color": c.color,
                "size": c.size or 1.0,
                "termCount": c.term_count,
            }
            for c in clusters
        ],
        terms=[
            {
                "id": t.id,
                "term": t.term,
                "category": t.category,
                "subcategory": t.subcategory,
                "x": t.x,
                "y": t.y,
                "z": t.z,
                "clusterId": t.cluster_id,
            }
            for t in terms
        ],
        posts=[
            {
                "id": p.id,
                "title": p.title,
                "url": p.url,
                "source": p.source,
                "x": p.x,
                "y": p.y,
                "z": p.z,
                "clusterId": p.cluster_id,
            }
            for p in posts
        ],
    )


@router.get("/{cluster_id}", response_model=ClusterDetailResponse)
async def get_cluster(
    cluster_id: int,
    db: Session = Depends(get_db),
):
    """Get detailed cluster information including terms and posts."""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    terms = db.query(SearchTerm).filter(SearchTerm.cluster_id == cluster_id).all()
    posts = db.query(Post).filter(Post.cluster_id == cluster_id).all()

    return ClusterDetailResponse(
        **ClusterResponse.model_validate(cluster).model_dump(),
        terms=[
            {
                "id": t.id,
                "term": t.term,
                "category": t.category,
                "x": t.x,
                "y": t.y,
                "z": t.z,
            }
            for t in terms
        ],
        posts=[
            {
                "id": p.id,
                "title": p.title,
                "url": p.url,
                "source": p.source,
            }
            for p in posts
        ],
    )
