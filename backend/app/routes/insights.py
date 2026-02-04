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
    """Return sample insights using REAL terms from the database, spread across categories."""
    from app.models import SearchTerm
    import random
    from collections import defaultdict

    now = datetime.utcnow().isoformat()

    # Get actual terms from the database grouped by category
    all_terms = db.query(SearchTerm).all()

    if not all_terms:
        return []

    # Group terms by category
    terms_by_category = defaultdict(list)
    for term in all_terms:
        if term.category:
            terms_by_category[term.category].append(term)

    # Use deterministic random for consistent demo results
    random.seed(42)

    insights = []

    # Priority categories for insights - reflecting actual taxonomy
    priority_categories = [
        ("treatment", "spike", "high", "Treatment breakthrough: {term}", "Search interest surged {pct}% following recent developments. Current: {curr}, Baseline: {base}"),
        ("emerging", "emerging", "high", "Emerging therapy: {term}", "Consistent {pct}% growth in searches as clinical data emerges. Early avg: {base} → Recent avg: {curr}"),
        ("clinical_trials", "spike", "medium", "Clinical trial interest: {term}", "Search volume up {pct}% - possibly new trial results announced. Current: {curr}, Baseline: {base}"),
        ("pediatric_oncology", "regional_outlier", "high", "Regional concern: {term}", "Florida showing {curr} search interest vs national avg of {base} - potential cluster"),
        ("rare_genetic", "emerging", "medium", "Rising awareness: {term}", "Awareness growing with {pct}% increase in searches. Early avg: {base} → Recent avg: {curr}"),
        ("adult_oncology", "spike", "medium", "Spike detected: {term}", "Search interest increased {pct}% in recent weeks. Current: {curr}, Baseline: {base}"),
        ("symptoms", "regional_outlier", "medium", "Geographic pattern: {term}", "California shows elevated searches at {curr} vs national avg {base}"),
        ("caregiver", "emerging", "medium", "Growing need: {term}", "Caregiver searches up {pct}% - may indicate resource gap. Early avg: {base} → Recent avg: {curr}"),
        ("diagnosis", "spike", "low", "Diagnostic interest: {term}", "Search interest for diagnostic testing up {pct}%. Current: {curr}, Baseline: {base}"),
        ("survivorship", "correlation", "low", "Correlated trends: {term}", "Shows strong correlation with treatment completion searches"),
        ("costs", "spike", "medium", "Financial concern: {term}", "Searches about costs spiked {pct}% - affordability concerns. Current: {curr}, Baseline: {base}"),
        ("rare_neurological", "emerging", "medium", "Emerging awareness: {term}", "Neurological condition searches growing {pct}%. Early avg: {base} → Recent avg: {curr}"),
        ("prevention", "spike", "low", "Screening interest: {term}", "Prevention searches up {pct}% - possibly awareness campaign. Current: {curr}, Baseline: {base}"),
        ("integrative", "regional_outlier", "low", "Regional pattern: {term}", "West Coast shows higher interest at {curr} vs national {base}"),
        ("rare_cancer", "emerging", "high", "Rare cancer awareness: {term}", "Searches growing {pct}% - may indicate unmet need. Early avg: {base} → Recent avg: {curr}"),
    ]

    geo_map = {
        3: "US-FL",
        6: "US-CA",
        13: "US-WA",
    }

    for i, (category, insight_type, severity, title_tpl, desc_tpl) in enumerate(priority_categories):
        # Get a term from this category if available
        if category in terms_by_category and terms_by_category[category]:
            term = random.choice(terms_by_category[category])
        else:
            # Fallback to any term
            term = random.choice(all_terms)

        # Generate realistic random values based on insight type
        if insight_type == "drop":
            base_val = random.randint(50, 80)
            curr_val = random.randint(30, base_val - 10)
            pct = round((curr_val - base_val) / base_val * 100)
        else:
            base_val = random.randint(20, 50)
            curr_val = random.randint(base_val + 10, 95)
            pct = round((curr_val - base_val) / base_val * 100)

        insights.append({
            "type": insight_type,
            "severity": severity,
            "title": title_tpl.format(term=term.term),
            "description": desc_tpl.format(term=term.term, pct=abs(pct), curr=curr_val, base=base_val),
            "term_id": term.id,
            "term_name": term.term,
            "cluster_id": term.cluster_id,
            "geo_code": geo_map.get(i),
            "metric_value": float(curr_val),
            "baseline_value": float(base_val),
            "percent_change": float(pct),
            "detected_at": now,
        })

    # Sort by severity for display
    severity_order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda x: severity_order.get(x["severity"], 2))

    return insights


@router.get("/")
@router.get("")  # Support both with and without trailing slash
async def get_insights(
    db: Session = Depends(get_db),
    severity: Optional[str] = Query(None, description="Filter by severity: high, medium, low"),
    insight_type: Optional[str] = Query(None, alias="type", description="Filter by type: spike, drop, emerging, regional_outlier, correlation"),
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
    if insight_type:
        insights = [i for i in insights if i["type"] == insight_type]

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
