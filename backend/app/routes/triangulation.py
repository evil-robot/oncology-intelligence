"""API routes for data triangulation from external sources."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SearchTerm

router = APIRouter()


@router.get("/term/{term_id}")
async def get_term_triangulation(
    term_id: int,
    db: Session = Depends(get_db),
):
    """
    Get triangulation data for a specific term from multiple sources.

    Returns data from:
    - ClinicalTrials.gov (active clinical trials)
    - FDA openFDA (drug approvals, safety data)
    - PubMed (research publications)
    - News (media coverage)
    """
    from pipeline.external_data import get_term_triangulation as fetch_triangulation

    # Get term from database
    term = db.query(SearchTerm).filter(SearchTerm.id == term_id).first()
    if not term:
        return {"error": "Term not found"}

    # Fetch triangulation data
    data = await fetch_triangulation(term.term, term.category)
    data["term_id"] = term_id

    return data


@router.get("/search")
async def search_triangulation(
    query: str = Query(..., description="Search term"),
    category: Optional[str] = Query(None, description="Category filter"),
):
    """
    Search for triangulation data by query string.
    """
    from pipeline.external_data import get_term_triangulation as fetch_triangulation

    data = await fetch_triangulation(query, category)
    return data


@router.get("/clinical-trials")
async def search_clinical_trials(
    query: str = Query(..., description="Search term"),
    status: str = Query("RECRUITING", description="Trial status filter"),
    max_results: int = Query(10, le=50),
):
    """Search ClinicalTrials.gov directly."""
    from pipeline.external_data import ClinicalTrialsClient

    client = ClinicalTrialsClient()
    try:
        trials = await client.search(query, status=status, max_results=max_results)
        return {
            "query": query,
            "count": len(trials),
            "trials": [t.to_dict() for t in trials],
            "source": "ClinicalTrials.gov",
            "source_url": "https://clinicaltrials.gov",
        }
    finally:
        await client.close()


@router.get("/pubmed")
async def search_pubmed(
    query: str = Query(..., description="Search term"),
    max_results: int = Query(10, le=50),
    days_back: int = Query(365, description="Search articles from last N days"),
):
    """Search PubMed directly."""
    from pipeline.external_data import PubMedClient

    client = PubMedClient()
    try:
        articles = await client.search(query, max_results=max_results, days_back=days_back)
        return {
            "query": query,
            "count": len(articles),
            "articles": [a.to_dict() for a in articles],
            "source": "PubMed/NCBI",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov",
        }
    finally:
        await client.close()


@router.get("/fda")
async def search_fda(
    drug_name: str = Query(..., description="Drug name to search"),
    max_results: int = Query(10, le=50),
):
    """Search FDA openFDA directly."""
    from pipeline.external_data import OpenFDAClient

    client = OpenFDAClient()
    try:
        approvals = await client.search_drug_approvals(drug_name, max_results=max_results)
        adverse = await client.search_adverse_events(drug_name, max_results=5)

        return {
            "drug_name": drug_name,
            "approvals": {
                "count": len(approvals),
                "items": [a.to_dict() for a in approvals],
            },
            "adverse_events": {
                "count": len(adverse),
                "items": [a.to_dict() for a in adverse],
            },
            "source": "FDA openFDA",
            "source_url": "https://open.fda.gov",
        }
    finally:
        await client.close()


@router.get("/news")
async def search_news(
    query: str = Query(..., description="Search term"),
    max_results: int = Query(10, le=20),
):
    """Search health news."""
    from pipeline.external_data import NewsClient

    client = NewsClient()
    try:
        articles = await client.search_health_news(query, max_results=max_results)
        return {
            "query": query,
            "count": len(articles),
            "articles": [a.to_dict() for a in articles],
            "source": "Google News",
            "source_url": "https://news.google.com",
        }
    finally:
        await client.close()


@router.get("/sources")
async def list_data_sources():
    """List all available data sources and their status."""
    return {
        "sources": [
            {
                "id": "google_trends",
                "name": "Google Trends",
                "description": "Search interest over time and by region",
                "url": "https://trends.google.com",
                "data_type": "time_series",
                "update_frequency": "daily",
                "coverage": "Global",
            },
            {
                "id": "clinical_trials",
                "name": "ClinicalTrials.gov",
                "description": "Registry of clinical studies from around the world",
                "url": "https://clinicaltrials.gov",
                "data_type": "trials",
                "update_frequency": "daily",
                "coverage": "Global (494K+ studies)",
            },
            {
                "id": "pubmed",
                "name": "PubMed",
                "description": "Biomedical literature from MEDLINE and life science journals",
                "url": "https://pubmed.ncbi.nlm.nih.gov",
                "data_type": "publications",
                "update_frequency": "daily",
                "coverage": "36M+ citations",
            },
            {
                "id": "openfda",
                "name": "FDA openFDA",
                "description": "Drug approvals, adverse events, and safety data",
                "url": "https://open.fda.gov",
                "data_type": "regulatory",
                "update_frequency": "weekly",
                "coverage": "US FDA regulated products",
            },
            {
                "id": "cdc_svi",
                "name": "CDC Social Vulnerability Index",
                "description": "Social determinants of health by geography",
                "url": "https://www.atsdr.cdc.gov/placeandhealth/svi",
                "data_type": "demographics",
                "update_frequency": "annual",
                "coverage": "US counties and states",
            },
            {
                "id": "news",
                "name": "Health News",
                "description": "Recent news coverage of health topics",
                "url": "https://news.google.com",
                "data_type": "news",
                "update_frequency": "real-time",
                "coverage": "Global",
            },
        ]
    }
