"""Trends API routes."""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.database import get_db
from app.models import TrendData, SearchTerm, Cluster, HourlyPattern

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


def generate_sample_trend_data(term_id: int, days: int = 90) -> list[dict]:
    """Generate sample trend data for demo mode."""
    import random
    import math
    random.seed(term_id)  # Consistent data per term

    data = []
    base_interest = 30 + random.random() * 40  # 30-70 base

    for i in range(days):
        date = datetime.utcnow() - timedelta(days=days - i)
        # Add some variation: trend + seasonality + noise
        trend = i * 0.1 * (1 if random.random() > 0.5 else -1)
        seasonality = 10 * math.sin(i * 0.1)
        noise = random.gauss(0, 8)
        interest = max(0, min(100, base_interest + trend + seasonality + noise))

        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "interest": round(interest),
        })

    return data


@router.get("/term/{term_id}")
async def get_term_trends(
    term_id: int,
    db: Session = Depends(get_db),
    geo_code: Optional[str] = Query(None),  # Allow any geo_code
    days: int = Query(365, description="Number of days to fetch"),
):
    """Get trend data for a specific term."""
    term = db.query(SearchTerm).filter(SearchTerm.id == term_id).first()
    if not term:
        return {"error": "Term not found"}, 404

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Try to get real data - try with geo_code first, then without
    query = db.query(TrendData).filter(TrendData.term_id == term_id).filter(TrendData.date >= cutoff)

    if geo_code:
        trends = query.filter(TrendData.geo_code == geo_code).order_by(TrendData.date).all()
    else:
        trends = []

    # If no data with specific geo_code, try country level
    if not trends:
        trends = query.filter(TrendData.geo_level == 'country').order_by(TrendData.date).all()

    # If still no data, try any data for this term
    if not trends:
        trends = query.order_by(TrendData.date).all()

    # If still no real data, generate sample data for demo
    if not trends:
        return {
            "term_id": term.id,
            "term": term.term,
            "data": generate_sample_trend_data(term_id, min(days, 90)),
            "demo_mode": True,
        }

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
        "demo_mode": False,
    }


@router.get("/cluster/{cluster_id}")
async def get_cluster_trends(
    cluster_id: int,
    db: Session = Depends(get_db),
    geo_code: Optional[str] = Query(None),
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
        return {"cluster_id": cluster_id, "cluster_name": cluster.name, "data": [], "demo_mode": True}

    # Try to aggregate trends by date
    query = (
        db.query(TrendData.date, func.avg(TrendData.interest).label("avg_interest"))
        .filter(TrendData.term_id.in_(term_ids))
        .filter(TrendData.date >= cutoff)
    )

    if geo_code:
        aggregated = query.filter(TrendData.geo_code == geo_code).group_by(TrendData.date).order_by(TrendData.date).all()
    else:
        aggregated = []

    # If no data with specific geo_code, try country level
    if not aggregated:
        aggregated = query.filter(TrendData.geo_level == 'country').group_by(TrendData.date).order_by(TrendData.date).all()

    # If still no data, try any data
    if not aggregated:
        aggregated = query.group_by(TrendData.date).order_by(TrendData.date).all()

    # If still no real data, generate sample data for demo
    if not aggregated:
        return {
            "cluster_id": cluster.id,
            "cluster_name": cluster.name,
            "data": generate_sample_trend_data(cluster_id, min(days, 90)),
            "demo_mode": True,
        }

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
        "demo_mode": False,
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


@router.get("/vulnerability/top-anxious")
async def get_most_anxious_terms(
    db: Session = Depends(get_db),
    limit: int = Query(20, le=100),
):
    """
    Get terms with the highest anxiety index (most late-night searching).
    These are the terms where people are most likely searching at 2am.
    """
    patterns = (
        db.query(HourlyPattern, SearchTerm)
        .join(SearchTerm, HourlyPattern.term_id == SearchTerm.id)
        .filter(HourlyPattern.anxiety_index.isnot(None))
        .order_by(HourlyPattern.anxiety_index.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "term_id": term.id,
            "term": term.term,
            "category": term.category,
            "cluster_id": term.cluster_id,
            "anxiety_index": round(pattern.anxiety_index, 2),
            "late_night_avg": pattern.late_night_avg,
            "daytime_avg": pattern.daytime_avg,
            "peak_hours": pattern.peak_hours,
        }
        for pattern, term in patterns
    ]


@router.get("/vulnerability/{term_id}")
async def get_vulnerability_window(
    term_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the 'vulnerability window' for a term — hourly search patterns
    that reveal when people are searching, especially late-night anxiety searches.
    """
    term = db.query(SearchTerm).filter(SearchTerm.id == term_id).first()
    if not term:
        return {"error": "Term not found"}, 404

    pattern = db.query(HourlyPattern).filter(
        HourlyPattern.term_id == term_id
    ).first()

    if not pattern:
        import math
        import random
        random.seed(term_id)
        hourly = {}
        for h in range(24):
            base = 30 + 20 * math.sin((h - 14) * math.pi / 12)
            hourly[h] = round(max(5, base + random.gauss(0, 5)), 1)

        late_vals = [hourly[h] for h in [23, 0, 1, 2, 3, 4]]
        day_vals = [hourly[h] for h in range(8, 19)]
        late_avg = round(sum(late_vals) / len(late_vals), 1)
        day_avg = round(sum(day_vals) / len(day_vals), 1)

        return {
            "term_id": term.id,
            "term": term.term,
            "hourly_avg": hourly,
            "day_of_week": {"Mon": 35, "Tue": 38, "Wed": 40, "Thu": 37, "Fri": 32, "Sat": 28, "Sun": 30},
            "peak_hours": sorted(hourly, key=hourly.get, reverse=True)[:3],
            "anxiety_index": round(late_avg / max(day_avg, 0.1), 2),
            "late_night_avg": late_avg,
            "daytime_avg": day_avg,
            "demo_mode": True,
        }

    return {
        "term_id": term.id,
        "term": term.term,
        "hourly_avg": pattern.hourly_avg,
        "day_of_week": pattern.day_of_week_avg,
        "peak_hours": pattern.peak_hours,
        "anxiety_index": pattern.anxiety_index,
        "late_night_avg": pattern.late_night_avg,
        "daytime_avg": pattern.daytime_avg,
        "demo_mode": False,
    }
