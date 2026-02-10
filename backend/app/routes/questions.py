"""Question Surface API routes — cross-term question search and discovery."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import QuestionSurface, SearchTerm

router = APIRouter()


@router.get("/top")
async def get_top_questions(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by term category"),
    source_type: Optional[str] = Query(None, description="Filter: people_also_ask or autocomplete"),
    limit: int = Query(30, le=100),
):
    """
    Get the most common questions across all terms.

    Returns questions ranked by how frequently they appear across different terms,
    revealing the universal anxieties in oncology search behavior.
    """
    query = (
        db.query(QuestionSurface, SearchTerm)
        .join(SearchTerm, QuestionSurface.source_term_id == SearchTerm.id)
    )

    if category:
        query = query.filter(SearchTerm.category == category)

    if source_type:
        query = query.filter(QuestionSurface.source_type == source_type)

    results = query.order_by(QuestionSurface.rank).limit(limit).all()

    return {
        "count": len(results),
        "questions": [
            {
                "id": q.id,
                "question": q.question,
                "snippet": q.snippet,
                "source_type": q.source_type,
                "term_id": term.id,
                "term": term.term,
                "category": term.category,
            }
            for q, term in results
        ],
    }


@router.get("/search")
async def search_questions(
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, le=50),
):
    """
    Search across all questions by text.

    Find questions containing specific phrases like "insurance", "survival rate",
    "hereditary", etc. to discover patterns in how people phrase their fears.
    """
    results = (
        db.query(QuestionSurface, SearchTerm)
        .join(SearchTerm, QuestionSurface.source_term_id == SearchTerm.id)
        .filter(QuestionSurface.question.ilike(f"%{q}%"))
        .order_by(QuestionSurface.rank)
        .limit(limit)
        .all()
    )

    return {
        "query": q,
        "count": len(results),
        "questions": [
            {
                "id": qs.id,
                "question": qs.question,
                "snippet": qs.snippet,
                "source_type": qs.source_type,
                "term_id": term.id,
                "term": term.term,
                "category": term.category,
            }
            for qs, term in results
        ],
    }


@router.get("/stats")
async def get_question_stats(
    db: Session = Depends(get_db),
):
    """
    Get statistics about the Question Surface layer.

    Returns counts by source type, category coverage, and total questions.
    """
    total = db.query(func.count(QuestionSurface.id)).scalar() or 0

    by_type = dict(
        db.query(QuestionSurface.source_type, func.count(QuestionSurface.id))
        .group_by(QuestionSurface.source_type)
        .all()
    )

    terms_with_questions = (
        db.query(func.count(func.distinct(QuestionSurface.source_term_id))).scalar() or 0
    )

    total_terms = db.query(func.count(SearchTerm.id)).scalar() or 0

    return {
        "total_questions": total,
        "by_source_type": by_type,
        "terms_with_questions": terms_with_questions,
        "total_terms": total_terms,
        "coverage_pct": round(terms_with_questions / max(total_terms, 1) * 100, 1),
    }
