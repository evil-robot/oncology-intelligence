"""API routes for comparing data across regions and time periods."""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from app.database import get_db
from app.models import TrendData, SearchTerm, DataSource

router = APIRouter()


# Human-readable names for geo codes
GEO_NAMES = {
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "AU": "Australia",
    "DE": "Germany",
    "FR": "France",
    "JP": "Japan",
}

# Human-readable labels for timeframes
TIMEFRAME_LABELS = {
    "today 1-m": "1 Month",
    "today 3-m": "3 Months",
    "today 12-m": "1 Year",
    "today 5-y": "5 Years",
    "all": "All Time (since 2004)",
}


@router.get("/sources")
async def get_data_sources(db: Session = Depends(get_db)):
    """Get list of all data sources (regions and timeframes) that have been fetched."""

    # Get distinct geo codes from trend data
    geo_codes = db.query(distinct(TrendData.geo_code)).filter(
        TrendData.geo_code.isnot(None),
        ~TrendData.geo_code.like("US-%")  # Exclude state-level for now
    ).all()

    sources = []
    for (geo_code,) in geo_codes:
        if not geo_code:
            continue

        # Get date range for this geo
        date_range = db.query(
            func.min(TrendData.date),
            func.max(TrendData.date)
        ).filter(TrendData.geo_code == geo_code).first()

        # Get term count
        term_count = db.query(func.count(distinct(TrendData.term_id))).filter(
            TrendData.geo_code == geo_code
        ).scalar()

        # Get data point count
        data_points = db.query(func.count(TrendData.id)).filter(
            TrendData.geo_code == geo_code
        ).scalar()

        sources.append({
            "geo_code": geo_code,
            "geo_name": GEO_NAMES.get(geo_code, geo_code),
            "date_start": date_range[0].isoformat() if date_range[0] else None,
            "date_end": date_range[1].isoformat() if date_range[1] else None,
            "terms_count": term_count,
            "data_points": data_points,
        })

    return {"sources": sources}


@router.get("/regions")
async def compare_regions(
    db: Session = Depends(get_db),
    term: Optional[str] = Query(None, description="Search term to compare"),
    term_id: Optional[int] = Query(None, description="Term ID to compare"),
    regions: str = Query("US,GB", description="Comma-separated region codes"),
):
    """Compare search interest for a term across different regions."""

    region_list = [r.strip().upper() for r in regions.split(",")]

    # Find the term
    if term_id:
        search_term = db.query(SearchTerm).filter(SearchTerm.id == term_id).first()
    elif term:
        search_term = db.query(SearchTerm).filter(
            SearchTerm.term.ilike(f"%{term}%")
        ).first()
    else:
        return {"error": "Provide either term or term_id"}

    if not search_term:
        return {"error": "Term not found", "term": term}

    # Get trend data for each region
    comparison = {
        "term": search_term.term,
        "term_id": search_term.id,
        "category": search_term.category,
        "regions": []
    }

    for geo_code in region_list:
        trends = db.query(TrendData).filter(
            TrendData.term_id == search_term.id,
            TrendData.geo_code == geo_code,
            TrendData.geo_level == "country"
        ).order_by(TrendData.date).all()

        if trends:
            data_points = [
                {"date": t.date.isoformat(), "interest": t.interest}
                for t in trends
            ]
            avg_interest = sum(t.interest or 0 for t in trends) / len(trends)

            comparison["regions"].append({
                "geo_code": geo_code,
                "geo_name": GEO_NAMES.get(geo_code, geo_code),
                "data_points": data_points,
                "avg_interest": round(avg_interest, 1),
                "max_interest": max(t.interest or 0 for t in trends),
                "min_interest": min(t.interest or 0 for t in trends),
                "date_range": {
                    "start": trends[0].date.isoformat(),
                    "end": trends[-1].date.isoformat(),
                }
            })
        else:
            comparison["regions"].append({
                "geo_code": geo_code,
                "geo_name": GEO_NAMES.get(geo_code, geo_code),
                "data_points": [],
                "error": "No data available for this region"
            })

    return comparison


@router.get("/top-terms")
async def compare_top_terms(
    db: Session = Depends(get_db),
    regions: str = Query("US,GB", description="Comma-separated region codes"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(10, le=50),
):
    """Get top terms by average interest for each region."""

    region_list = [r.strip().upper() for r in regions.split(",")]

    results = {"regions": []}

    for geo_code in region_list:
        # Query for average interest by term
        query = db.query(
            SearchTerm.id,
            SearchTerm.term,
            SearchTerm.category,
            func.avg(TrendData.interest).label("avg_interest"),
            func.count(TrendData.id).label("data_points")
        ).join(TrendData).filter(
            TrendData.geo_code == geo_code
        ).group_by(SearchTerm.id, SearchTerm.term, SearchTerm.category)

        if category:
            query = query.filter(SearchTerm.category == category)

        top_terms = query.order_by(func.avg(TrendData.interest).desc()).limit(limit).all()

        results["regions"].append({
            "geo_code": geo_code,
            "geo_name": GEO_NAMES.get(geo_code, geo_code),
            "top_terms": [
                {
                    "term_id": t.id,
                    "term": t.term,
                    "category": t.category,
                    "avg_interest": round(t.avg_interest, 1) if t.avg_interest else 0,
                    "data_points": t.data_points
                }
                for t in top_terms
            ]
        })

    return results


@router.get("/category-comparison")
async def compare_categories(
    db: Session = Depends(get_db),
    regions: str = Query("US,GB", description="Comma-separated region codes"),
):
    """Compare average interest by category across regions."""

    region_list = [r.strip().upper() for r in regions.split(",")]

    results = {"categories": {}, "regions": region_list}

    for geo_code in region_list:
        # Get average interest by category
        category_data = db.query(
            SearchTerm.category,
            func.avg(TrendData.interest).label("avg_interest"),
            func.count(distinct(SearchTerm.id)).label("term_count")
        ).join(TrendData).filter(
            TrendData.geo_code == geo_code,
            SearchTerm.category.isnot(None)
        ).group_by(SearchTerm.category).all()

        for cat in category_data:
            if cat.category not in results["categories"]:
                results["categories"][cat.category] = {}

            results["categories"][cat.category][geo_code] = {
                "avg_interest": round(cat.avg_interest, 1) if cat.avg_interest else 0,
                "term_count": cat.term_count
            }

    return results
