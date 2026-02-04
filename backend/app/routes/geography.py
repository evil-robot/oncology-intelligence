"""Geography and SDOH API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.database import get_db
from app.models import GeographicRegion, TrendData, SearchTerm

router = APIRouter()


class RegionResponse(BaseModel):
    """Geographic region data."""

    geo_code: str
    name: str
    level: str
    latitude: Optional[float]
    longitude: Optional[float]
    population: Optional[int]
    svi_overall: Optional[float]
    svi_socioeconomic: Optional[float]
    svi_household_disability: Optional[float]
    svi_minority_language: Optional[float]
    svi_housing_transport: Optional[float]
    uninsured_rate: Optional[float]

    class Config:
        from_attributes = True


class RegionWithIntentResponse(RegionResponse):
    """Region with search intent metrics."""

    intent_intensity: Optional[float]
    top_terms: list[dict]


@router.get("/regions", response_model=list[RegionResponse])
async def list_regions(
    db: Session = Depends(get_db),
    level: Optional[str] = Query("state"),
):
    """List all geographic regions."""
    query = db.query(GeographicRegion)
    if level:
        query = query.filter(GeographicRegion.level == level)

    regions = query.all()
    return [RegionResponse.model_validate(r) for r in regions]


@router.get("/regions/{geo_code}", response_model=RegionWithIntentResponse)
async def get_region(
    geo_code: str,
    db: Session = Depends(get_db),
):
    """Get detailed region data including SDOH and search intent."""
    region = db.query(GeographicRegion).filter(
        GeographicRegion.geo_code == geo_code
    ).first()

    if not region:
        return {"error": "Region not found"}, 404

    # Calculate intent intensity (average interest across all terms)
    intent = (
        db.query(func.avg(TrendData.interest))
        .filter(TrendData.geo_code == geo_code)
        .scalar()
    )

    # Get top terms for this region
    top_terms = (
        db.query(
            SearchTerm.id,
            SearchTerm.term,
            SearchTerm.category,
            func.avg(TrendData.interest).label("avg_interest"),
        )
        .join(TrendData)
        .filter(TrendData.geo_code == geo_code)
        .group_by(SearchTerm.id)
        .order_by(func.avg(TrendData.interest).desc())
        .limit(10)
        .all()
    )

    return RegionWithIntentResponse(
        **RegionResponse.model_validate(region).model_dump(),
        intent_intensity=round(intent, 2) if intent else None,
        top_terms=[
            {
                "id": t.id,
                "term": t.term,
                "category": t.category,
                "avg_interest": round(t.avg_interest, 1),
            }
            for t in top_terms
        ],
    )


def generate_demo_regional_interest(geo_code: str, term_id: Optional[int] = None) -> float:
    """Generate consistent but varied demo interest for a region."""
    import hashlib
    # Create a hash from just the geo_code to get unique values per state
    # This ensures each state has a different interest level
    seed_str = f"interest-{geo_code}"
    hash_val = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    # Generate interest between 25-95 for good variation
    base_interest = 25 + (hash_val % 70)

    # If a specific term is selected, add some variation
    if term_id:
        term_seed = f"{geo_code}-term-{term_id}"
        term_hash = int(hashlib.md5(term_seed.encode()).hexdigest()[:8], 16)
        # Add/subtract up to 15 points based on term
        adjustment = (term_hash % 30) - 15
        base_interest = max(10, min(100, base_interest + adjustment))

    return float(base_interest)


@router.get("/heatmap")
async def get_heatmap_data(
    db: Session = Depends(get_db),
    cluster_id: Optional[int] = Query(None),
    term_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
):
    """
    Get geographic heatmap data for visualization.

    Returns regions with their search intensity and SDOH metrics.
    """
    # Base query for regions
    regions = db.query(GeographicRegion).filter(
        GeographicRegion.level == "state"
    ).all()

    # Check if we have any trend data at all
    trend_count = db.query(TrendData).count()
    demo_mode = trend_count == 0

    # Build term filter
    term_filter = []
    if cluster_id:
        term_ids = (
            db.query(SearchTerm.id)
            .filter(SearchTerm.cluster_id == cluster_id)
            .all()
        )
        term_filter = [t[0] for t in term_ids]
    elif term_id:
        term_filter = [term_id]
    elif category:
        term_ids = (
            db.query(SearchTerm.id)
            .filter(SearchTerm.category == category)
            .all()
        )
        term_filter = [t[0] for t in term_ids]

    result = []
    for region in regions:
        if demo_mode:
            # Generate demo interest data
            interest = generate_demo_regional_interest(region.geo_code, term_id or cluster_id)
        else:
            # Calculate interest for this region from real data
            interest_query = db.query(func.avg(TrendData.interest)).filter(
                TrendData.geo_code == region.geo_code
            )
            if term_filter:
                interest_query = interest_query.filter(TrendData.term_id.in_(term_filter))

            interest = interest_query.scalar() or 0

        result.append({
            "geo_code": region.geo_code,
            "name": region.name,
            "latitude": region.latitude,
            "longitude": region.longitude,
            "interest": round(interest, 1) if interest else 0,
            "svi_overall": region.svi_overall,
            "population": region.population,
            # Computed metric: interest adjusted by vulnerability
            "vulnerability_adjusted_intent": (
                round(interest * (1 + (region.svi_overall or 0)), 1)
                if interest else 0
            ),
            "demo_mode": demo_mode,
        })

    return result


@router.get("/sdoh-summary")
async def get_sdoh_summary(db: Session = Depends(get_db)):
    """Get summary statistics for SDOH metrics."""
    regions = db.query(GeographicRegion).filter(
        GeographicRegion.level == "state",
        GeographicRegion.svi_overall.isnot(None),
    ).all()

    if not regions:
        return {"error": "No SDOH data available"}

    svi_values = [r.svi_overall for r in regions if r.svi_overall is not None]

    return {
        "total_regions": len(regions),
        "svi_stats": {
            "min": round(min(svi_values), 3),
            "max": round(max(svi_values), 3),
            "avg": round(sum(svi_values) / len(svi_values), 3),
        },
        "high_vulnerability_regions": [
            {"geo_code": r.geo_code, "name": r.name, "svi": r.svi_overall}
            for r in sorted(regions, key=lambda x: x.svi_overall or 0, reverse=True)[:10]
        ],
    }
