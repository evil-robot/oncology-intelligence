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
    - Google Scholar via SerpAPI (academic papers with citations)
    - Google News via SerpAPI (structured news coverage)
    - Google Patents via SerpAPI (patent filings / innovation pipeline)
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
    """Search Google News via SerpAPI."""
    from pipeline.external_data import GoogleNewsClient

    client = GoogleNewsClient()
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


@router.get("/scholar")
async def search_scholar(
    query: str = Query(..., description="Search term"),
    max_results: int = Query(10, le=20),
):
    """Search Google Scholar via SerpAPI."""
    from pipeline.external_data import GoogleScholarClient

    client = GoogleScholarClient()
    try:
        articles = await client.search(query, max_results=max_results)
        return {
            "query": query,
            "count": len(articles),
            "articles": [a.to_dict() for a in articles],
            "source": "Google Scholar",
            "source_url": "https://scholar.google.com",
        }
    finally:
        await client.close()


@router.get("/patents")
async def search_patents(
    query: str = Query(..., description="Search term"),
    max_results: int = Query(10, le=20),
):
    """Search Google Patents via SerpAPI."""
    from pipeline.external_data import GooglePatentsClient

    client = GooglePatentsClient()
    try:
        patents = await client.search(query, max_results=max_results)
        return {
            "query": query,
            "count": len(patents),
            "patents": [p.to_dict() for p in patents],
            "source": "Google Patents",
            "source_url": "https://patents.google.com",
        }
    finally:
        await client.close()


@router.get("/sources")
async def list_data_sources():
    """List all available data sources and their status."""
    return {
        "core_data": [
            {
                "id": "google_trends",
                "name": "Google Trends",
                "description": "Search interest data powering the visualization — collected via SerpAPI and stored in our database",
                "url": "https://trends.google.com",
                "data_type": "time_series",
                "update_frequency": "configurable",
                "coverage": "United States",
                "stored": True,
            },
        ],
        "evidence_sources": [
            {
                "id": "clinical_trials",
                "name": "ClinicalTrials.gov",
                "description": "Registry of clinical studies — queried on-demand for evidence triangulation",
                "url": "https://clinicaltrials.gov",
                "data_type": "trials",
                "update_frequency": "real-time API",
                "coverage": "Global (494K+ studies)",
                "stored": False,
            },
            {
                "id": "pubmed",
                "name": "PubMed",
                "description": "Biomedical literature — queried on-demand for research context",
                "url": "https://pubmed.ncbi.nlm.nih.gov",
                "data_type": "publications",
                "update_frequency": "real-time API",
                "coverage": "36M+ citations",
                "stored": False,
            },
            {
                "id": "google_scholar",
                "name": "Google Scholar",
                "description": "Academic research with citation counts — identifies high-impact papers via SerpAPI",
                "url": "https://scholar.google.com",
                "data_type": "publications",
                "update_frequency": "real-time via SerpAPI",
                "coverage": "Global academic literature",
                "stored": False,
            },
            {
                "id": "openfda",
                "name": "FDA openFDA",
                "description": "Drug approvals and safety data — queried on-demand",
                "url": "https://open.fda.gov",
                "data_type": "regulatory",
                "update_frequency": "real-time API",
                "coverage": "US FDA regulated products",
                "stored": False,
            },
            {
                "id": "google_news",
                "name": "Google News",
                "description": "Structured news coverage — queried via SerpAPI for media context",
                "url": "https://news.google.com",
                "data_type": "news",
                "update_frequency": "real-time via SerpAPI",
                "coverage": "Global",
                "stored": False,
            },
            {
                "id": "google_patents",
                "name": "Google Patents",
                "description": "Patent filings — tracks innovation pipeline and upcoming treatments via SerpAPI",
                "url": "https://patents.google.com",
                "data_type": "patents",
                "update_frequency": "real-time via SerpAPI",
                "coverage": "100+ patent offices worldwide",
                "stored": False,
            },
            {
                "id": "cdc_svi",
                "name": "CDC Social Vulnerability Index",
                "description": "Social determinants of health overlay for geographic analysis",
                "url": "https://www.atsdr.cdc.gov/placeandhealth/svi",
                "data_type": "demographics",
                "update_frequency": "annual",
                "coverage": "US counties and states",
                "stored": False,
            },
        ]
    }
