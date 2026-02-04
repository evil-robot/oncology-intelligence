"""Insights and anomaly detection API routes."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


@router.get("/health")
async def insights_health():
    """Simple health check for insights router."""
    return {"status": "ok", "router": "insights"}


def get_sample_insights(db: Session) -> list[dict]:
    """Return sample insights using REAL terms from the database."""
    from app.models import SearchTerm
    import random

    now = datetime.utcnow().isoformat()

    # Get actual terms from the database
    terms = db.query(SearchTerm).limit(50).all()

    if not terms:
        return []

    # Shuffle and pick terms for different insight types
    random.seed(42)  # Consistent results
    shuffled = list(terms)
    random.shuffle(shuffled)

    insights = []

    # Generate insights from real terms
    insight_templates = [
        ("spike", "high", "Spike detected: {term}", "Search interest jumped {pct}% above average. Current: {curr}, Baseline: {base}"),
        ("emerging", "high", "Emerging topic: {term}", "Consistent {pct}% growth over recent weeks. Early avg: {base} → Recent avg: {curr}"),
        ("spike", "medium", "Spike detected: {term}", "Search interest increased {pct}% with new developments. Current: {curr}, Baseline: {base}"),
        ("regional_outlier", "medium", "High regional interest: {term}", "Regional interest shows {curr} vs national avg of {base}"),
        ("emerging", "medium", "Emerging topic: {term}", "Growing awareness driving {pct}% increase. Early avg: {base} → Recent avg: {curr}"),
        ("regional_outlier", "medium", "Regional pattern: {term}", "Geographic variation detected: {curr} vs baseline {base}"),
        ("correlation", "low", "Correlated trends: {term}", "Shows strong correlation with related search topics"),
        ("drop", "low", "Drop detected: {term}", "Search interest dropped {pct}% recently. Current: {curr}, Baseline: {base}"),
    ]

    for i, term in enumerate(shuffled[:10]):
        template = insight_templates[i % len(insight_templates)]
        insight_type, severity, title_tpl, desc_tpl = template

        # Generate realistic random values
        if insight_type == "drop":
            base_val = random.randint(50, 80)
            curr_val = random.randint(30, base_val - 10)
            pct = round((curr_val - base_val) / base_val * 100)
        else:
            base_val = random.randint(20, 50)
            curr_val = random.randint(base_val + 10, 95)
            pct = round((curr_val - base_val) / base_val * 100)

        geo_codes = [None, None, None, "US-FL", None, "US-CA", None, None]

        insights.append({
            "type": insight_type,
            "severity": severity,
            "title": title_tpl.format(term=term.term),
            "description": desc_tpl.format(term=term.term, pct=abs(pct), curr=curr_val, base=base_val),
            "term_id": term.id,
            "term_name": term.term,
            "cluster_id": term.cluster_id,
            "geo_code": geo_codes[i % len(geo_codes)],
            "metric_value": float(curr_val),
            "baseline_value": float(base_val),
            "percent_change": float(pct),
            "detected_at": now,
        })

    return insights


@router.get("/")
async def get_insights(
    db: Session = Depends(get_db),
    severity: Optional[str] = Query(None, description="Filter by severity: high, medium, low"),
    type: Optional[str] = Query(None, description="Filter by type: spike, drop, emerging, regional_outlier, correlation"),
    limit: int = Query(20, le=100),
):
    """
    Get detected insights and anomalies.

    Returns a list of insights sorted by severity, including:
    - Spikes: Sudden increases in search interest
    - Drops: Sudden decreases
    - Emerging: Topics with consistent growth
    - Regional outliers: Unusual geographic patterns
    - Correlations: Related trends across categories
    """
    from pipeline.anomaly_detection import run_anomaly_detection
    from app.models import TrendData

    # Check if we have real trend data
    trend_count = db.query(TrendData).count()
    demo_mode = trend_count == 0

    if demo_mode:
        insights = get_sample_insights(db)
        # Add demo flag to each insight
        for i in insights:
            i["demo_mode"] = True
    else:
        insights = run_anomaly_detection(db)
        for i in insights:
            i["demo_mode"] = False

    # Filter by severity
    if severity:
        insights = [i for i in insights if i["severity"] == severity]

    # Filter by type
    if type:
        insights = [i for i in insights if i["type"] == type]

    return {"insights": insights[:limit], "demo_mode": demo_mode, "trend_data_points": trend_count}


@router.get("/summary")
async def get_insights_summary(db: Session = Depends(get_db)):
    """Get a summary of insights by type and severity."""
    from pipeline.anomaly_detection import run_anomaly_detection

    insights = run_anomaly_detection(db)

    # If no real data, return sample insights
    if not insights:
        insights = get_sample_insights(db)

    # Count by type
    by_type = {}
    for i in insights:
        t = i["type"]
        by_type[t] = by_type.get(t, 0) + 1

    # Count by severity
    by_severity = {}
    for i in insights:
        s = i["severity"]
        by_severity[s] = by_severity.get(s, 0) + 1

    # Top insights
    top_insights = insights[:5]

    return {
        "total": len(insights),
        "by_type": by_type,
        "by_severity": by_severity,
        "top_insights": top_insights,
    }


@router.get("/term/{term_id}")
async def get_term_insights(
    term_id: int,
    db: Session = Depends(get_db),
):
    """Get insights related to a specific term."""
    from pipeline.anomaly_detection import run_anomaly_detection

    insights = run_anomaly_detection(db)

    # Filter to this term
    term_insights = [i for i in insights if i.get("term_id") == term_id]

    return term_insights


@router.get("/cluster/{cluster_id}")
async def get_cluster_insights(
    cluster_id: int,
    db: Session = Depends(get_db),
):
    """Get insights related to a specific cluster."""
    from pipeline.anomaly_detection import run_anomaly_detection

    insights = run_anomaly_detection(db)

    # Filter to this cluster
    cluster_insights = [i for i in insights if i.get("cluster_id") == cluster_id]

    return cluster_insights
