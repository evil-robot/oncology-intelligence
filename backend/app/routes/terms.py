"""Search term API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import SearchTerm, RelatedQuery

router = APIRouter()


class TermResponse(BaseModel):
    """Search term data for API response."""

    id: int
    term: str
    category: str
    subcategory: Optional[str]
    x: Optional[float]
    y: Optional[float]
    z: Optional[float]
    cluster_id: Optional[int]

    class Config:
        from_attributes = True


class TaxonomyResponse(BaseModel):
    """Taxonomy structure response."""

    categories: list[dict]
    total_terms: int


@router.get("/", response_model=list[TermResponse])
async def list_terms(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None),
    subcategory: Optional[str] = Query(None),
    cluster_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """List search terms with optional filtering."""
    query = db.query(SearchTerm)

    if category:
        query = query.filter(SearchTerm.category == category)
    if subcategory:
        query = query.filter(SearchTerm.subcategory == subcategory)
    if cluster_id:
        query = query.filter(SearchTerm.cluster_id == cluster_id)
    if search:
        query = query.filter(SearchTerm.term.ilike(f"%{search}%"))

    terms = query.offset(offset).limit(limit).all()
    return [TermResponse.model_validate(t) for t in terms]


@router.get("/taxonomy", response_model=TaxonomyResponse)
async def get_taxonomy(db: Session = Depends(get_db)):
    """Get taxonomy structure with categories and counts."""
    from sqlalchemy import func

    # Get category counts
    category_counts = (
        db.query(SearchTerm.category, func.count(SearchTerm.id))
        .group_by(SearchTerm.category)
        .all()
    )

    categories = []
    for category, count in category_counts:
        # Get subcategories for this category
        subcategory_counts = (
            db.query(SearchTerm.subcategory, func.count(SearchTerm.id))
            .filter(SearchTerm.category == category)
            .group_by(SearchTerm.subcategory)
            .all()
        )

        categories.append({
            "name": category,
            "count": count,
            "subcategories": [
                {"name": sub or "general", "count": cnt}
                for sub, cnt in subcategory_counts
            ],
        })

    total = db.query(func.count(SearchTerm.id)).scalar()

    return TaxonomyResponse(categories=categories, total_terms=total)


@router.get("/{term_id}", response_model=TermResponse)
async def get_term(term_id: int, db: Session = Depends(get_db)):
    """Get a specific search term."""
    term = db.query(SearchTerm).filter(SearchTerm.id == term_id).first()
    if not term:
        return {"error": "Term not found"}, 404
    return TermResponse.model_validate(term)


@router.get("/{term_id}/similar")
async def get_similar_terms(
    term_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(10, le=50),
):
    """Find semantically similar terms using vector similarity."""
    term = db.query(SearchTerm).filter(SearchTerm.id == term_id).first()
    if not term or term.embedding is None:
        return {"error": "Term not found or has no embedding"}, 404

    # Use pgvector similarity search
    similar = (
        db.query(SearchTerm)
        .filter(SearchTerm.id != term_id)
        .filter(SearchTerm.embedding.isnot(None))
        .order_by(SearchTerm.embedding.cosine_distance(term.embedding))
        .limit(limit)
        .all()
    )

    return [
        {
            "id": t.id,
            "term": t.term,
            "category": t.category,
            "cluster_id": t.cluster_id,
        }
        for t in similar
    ]


@router.get("/{term_id}/related")
async def get_related_queries(
    term_id: int,
    db: Session = Depends(get_db),
    query_type: Optional[str] = Query(None, description="Filter by type: rising_query, top_query, rising_topic, top_topic"),
):
    """Get related queries and topics discovered for this term."""
    query = db.query(RelatedQuery).filter(RelatedQuery.source_term_id == term_id)

    if query_type:
        query = query.filter(RelatedQuery.query_type == query_type)

    results = query.order_by(RelatedQuery.extracted_value.desc()).all()

    return {
        "term_id": term_id,
        "count": len(results),
        "related": [
            {
                "id": rq.id,
                "query": rq.query,
                "query_type": rq.query_type,
                "topic_type": rq.topic_type,
                "value": rq.value,
                "extracted_value": rq.extracted_value,
                "is_promoted": rq.is_promoted,
                "promoted_term_id": rq.promoted_term_id,
            }
            for rq in results
        ],
    }


@router.get("/discovered/all")
async def list_discovered_terms(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
):
    """List terms that were auto-discovered from related queries."""
    terms = (
        db.query(SearchTerm)
        .filter(SearchTerm.subcategory.like("discovered:%"))
        .order_by(SearchTerm.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": t.id,
            "term": t.term,
            "category": t.category,
            "subcategory": t.subcategory,
            "parent_term_id": t.parent_term_id,
            "cluster_id": t.cluster_id,
        }
        for t in terms
    ]
