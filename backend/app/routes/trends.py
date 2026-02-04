"""Trends API routes."""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.database import get_db
from app.models import TrendData, SearchTerm, Cluster

router = APIRouter()


class TrendPointResponse(BaseModel):
    """Single trend data point."""

    date: datetime
    interest: int
    geo_code: str


class TermTrendResponse(BaseModel):
    """Trend data for a term."""

    term_id: int
    term: str
    data: list[TrendPointResponse]


class ClusterTrendResponse(BaseModel):
    """Aggregated trend data for a cluster."""

    cluster_id: int
    cluster_name: str
    data: list[dict]


@router.get("/term/{term_id}")
async def get_term_trends(
    term_id: int,
    db: Session = Depends(get_db),
    geo_code: Optional[str] = Query("US"),
    days: int = Query(365, description="Number of days to fetch"),
):
    """Get trend data for a specific term."""
    term = db.query(SearchTerm).filter(SearchTerm.id == term_id).first()
    if not term:
        return {"error": "Term not found"}, 404

    cutoff = datetime.utcnow() - timedelta(days=days)

    trends = (
        db.query(TrendData)
        .filter(TrendData.term_id == term_id)
        .filter(TrendData.date >= cutoff)
        .filter(TrendData.geo_code == geo_code)
        .order_by(TrendData.date)
        .all()
    )

    return {
        "term_id": term.id,
        "term": term.term,
        "data": [
            {
                "date": t.date.isoformat(),
                "interest": t.interest,
            }
            for t in trends
        ],
    }


@router.get("/cluster/{cluster_id}")
async def get_cluster_trends(
    cluster_id: int,
    db: Session = Depends(get_db),
    geo_code: Optional[str] = Query("US"),
    days: int = Query(365),
):
    """Get aggregated trend data for all terms in a cluster."""
    cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
    if not cluster:
        return {"error": "Cluster not found"}, 404

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get term IDs in cluster
    term_ids = (
        db.query(SearchTerm.id)
        .filter(SearchTerm.cluster_id == cluster_id)
        .all()
    )
    term_ids = [t[0] for t in term_ids]

    if not term_ids:
        return {"cluster_id": cluster_id, "cluster_name": cluster.name, "data": []}

    # Aggregate trends by date
    aggregated = (
        db.query(TrendData.date, func.avg(TrendData.interest).label("avg_interest"))
        .filter(TrendData.term_id.in_(term_ids))
        .filter(TrendData.date >= cutoff)
        .filter(TrendData.geo_code == geo_code)
        .group_by(TrendData.date)
        .order_by(TrendData.date)
        .all()
    )

    return {
        "cluster_id": cluster.id,
        "cluster_name": cluster.name,
        "data": [
            {
                "date": row.date.isoformat(),
                "interest": round(row.avg_interest, 1),
            }
            for row in aggregated
        ],
    }


@router.get("/top")
async def get_top_trending(
    db: Session = Depends(get_db),
    geo_code: Optional[str] = Query("US"),
    days: int = Query(30),
    limit: int = Query(20),
):
    """Get top trending terms by recent interest."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    top_terms = (
        db.query(
            SearchTerm.id,
            SearchTerm.term,
            SearchTerm.category,
            SearchTerm.cluster_id,
            func.avg(TrendData.interest).label("avg_interest"),
        )
        .join(TrendData)
        .filter(TrendData.date >= cutoff)
        .filter(TrendData.geo_code == geo_code)
        .group_by(SearchTerm.id)
        .order_by(func.avg(TrendData.interest).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": t.id,
            "term": t.term,
            "category": t.category,
            "cluster_id": t.cluster_id,
            "avg_interest": round(t.avg_interest, 1),
        }
        for t in top_terms
    ]


@router.get("/comparison")
async def compare_terms(
    db: Session = Depends(get_db),
    term_ids: str = Query(..., description="Comma-separated term IDs"),
    geo_code: Optional[str] = Query("US"),
    days: int = Query(365),
):
    """Compare trend data for multiple terms."""
    ids = [int(i.strip()) for i in term_ids.split(",") if i.strip().isdigit()]

    if not ids or len(ids) > 5:
        return {"error": "Provide 1-5 term IDs"}, 400

    cutoff = datetime.utcnow() - timedelta(days=days)

    terms = db.query(SearchTerm).filter(SearchTerm.id.in_(ids)).all()
    term_map = {t.id: t.term for t in terms}

    result = {}
    for term_id in ids:
        if term_id not in term_map:
            continue

        trends = (
            db.query(TrendData)
            .filter(TrendData.term_id == term_id)
            .filter(TrendData.date >= cutoff)
            .filter(TrendData.geo_code == geo_code)
            .order_by(TrendData.date)
            .all()
        )

        result[term_map[term_id]] = [
            {"date": t.date.isoformat(), "interest": t.interest}
            for t in trends
        ]

    return result
