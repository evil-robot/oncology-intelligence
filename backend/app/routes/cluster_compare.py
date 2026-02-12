"""
Cluster comparison endpoint — computes proximity metrics and generates
an AI explanation for why two clusters are positioned near or far apart
in VIOLET's 3D semantic space.
"""

import math
import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.models import Cluster, SearchTerm
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CompareRequest(BaseModel):
    cluster_a_id: int
    cluster_b_id: int


class ClusterSummary(BaseModel):
    id: int
    name: str
    term_count: int
    avg_search_volume: Optional[float]
    top_categories: list[str]
    top_terms: list[str]


class CompareMetrics(BaseModel):
    proximity_index: int          # 0-100 cosine similarity of embeddings
    spatial_proximity: int        # 0-100 normalised Euclidean distance
    euclidean_distance_3d: float  # raw distance in scene units
    shared_categories: list[str]
    shared_subcategories: list[str]


class CompareResponse(BaseModel):
    cluster_a: ClusterSummary
    cluster_b: ClusterSummary
    metrics: CompareMetrics
    explanation: str
    fallback: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MAX_DIAGONAL = 24.2  # approx bounding cube diagonal for normalisation


def _cluster_summary(cluster: Cluster, terms: list[SearchTerm]) -> ClusterSummary:
    """Build a ClusterSummary from a Cluster + its member terms."""
    categories: dict[str, int] = {}
    for t in terms:
        if t.category:
            categories[t.category] = categories.get(t.category, 0) + 1

    top_cats = sorted(categories, key=categories.get, reverse=True)[:5]
    top_terms = [t.term for t in terms[:5]]

    return ClusterSummary(
        id=cluster.id,
        name=cluster.name,
        term_count=cluster.term_count or len(terms),
        avg_search_volume=cluster.avg_search_volume,
        top_categories=top_cats,
        top_terms=top_terms,
    )


def _cosine_similarity_np(a: list[float], b: list[float]) -> float:
    """Numpy fallback for cosine similarity when pgvector isn't available."""
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _proximity_index(db: Session, cluster_a: Cluster, cluster_b: Cluster) -> tuple[int, bool]:
    """Cosine similarity of centroid_embedding vectors, 0-100.

    Uses pgvector `<=>` operator when both embeddings exist; falls back to
    numpy if either is null.  Returns (score, is_estimated) where is_estimated
    is True when no embeddings were available and the score is a placeholder.
    """
    if cluster_a.centroid_embedding is not None and cluster_b.centroid_embedding is not None:
        try:
            row = db.execute(
                text(
                    "SELECT 1 - (c1.centroid_embedding <=> c2.centroid_embedding) AS sim "
                    "FROM clusters c1, clusters c2 "
                    "WHERE c1.id = :a AND c2.id = :b"
                ),
                {"a": cluster_a.id, "b": cluster_b.id},
            ).fetchone()
            if row and row[0] is not None:
                return max(0, min(100, round(row[0] * 100))), False
        except Exception as exc:
            logger.warning("pgvector cosine failed, falling back to numpy: %s", exc)

    # Numpy fallback
    ea = list(cluster_a.centroid_embedding) if cluster_a.centroid_embedding is not None else None
    eb = list(cluster_b.centroid_embedding) if cluster_b.centroid_embedding is not None else None
    if ea and eb:
        return max(0, min(100, round(_cosine_similarity_np(ea, eb) * 100))), False
    return 50, True  # estimated — no embeddings available


def _spatial_proximity(cluster_a: Cluster, cluster_b: Cluster) -> tuple[int, float]:
    """Euclidean distance of centroid_x/y/z normalised to 0-100 and raw distance."""
    dx = (cluster_a.centroid_x or 0) - (cluster_b.centroid_x or 0)
    dy = (cluster_a.centroid_y or 0) - (cluster_b.centroid_y or 0)
    dz = (cluster_a.centroid_z or 0) - (cluster_b.centroid_z or 0)
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    score = max(0, round(100 * (1 - dist / MAX_DIAGONAL)))
    return score, round(dist, 2)


def _category_overlap(terms_a: list[SearchTerm], terms_b: list[SearchTerm]):
    """Set intersection of categories and subcategories."""
    cats_a = {t.category for t in terms_a if t.category}
    cats_b = {t.category for t in terms_b if t.category}
    subs_a = {t.subcategory for t in terms_a if t.subcategory}
    subs_b = {t.subcategory for t in terms_b if t.subcategory}
    return sorted(cats_a & cats_b), sorted(subs_a & subs_b)


# ---------------------------------------------------------------------------
# LLM explanation
# ---------------------------------------------------------------------------

def _generate_explanation(
    summary_a: ClusterSummary,
    summary_b: ClusterSummary,
    metrics: CompareMetrics,
    proximity_estimated: bool = False,
) -> tuple[str, bool]:
    """Call GPT-4o-mini for a narrative explanation. Returns (text, is_fallback)."""

    if not settings.openai_api_key:
        return _fallback_explanation(summary_a, summary_b, metrics, proximity_estimated), True

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)

        system = (
            "You are an oncology research assistant for VIOLET. You explain relationships "
            "between disease-topic clusters in a 3D semantic space built from 750+ oncology "
            "search term embeddings (UMAP + HDBSCAN). Write 3-4 short paragraphs: "
            "(1) Are they close or far? Use the spatial proximity and proximity index to "
            "judge closeness. If proximity index is marked as estimated, rely on spatial "
            "proximity instead. "
            "(2) WHY — reference specific shared terms/categories. "
            "(3) Scale differences — which cluster has more search footprint? "
            "(4) Shared subcategories or overlaps. "
            "Under 200 words, flowing prose, no math, no ML jargon."
        )

        user_prompt = (
            f"Compare these two clusters:\n\n"
            f"Cluster A: \"{summary_a.name}\" — {summary_a.term_count} terms, "
            f"top categories: {', '.join(summary_a.top_categories) or 'none'}, "
            f"top terms: {', '.join(summary_a.top_terms) or 'none'}, "
            f"avg search volume: {summary_a.avg_search_volume if summary_a.avg_search_volume is not None else 'unknown'}\n\n"
            f"Cluster B: \"{summary_b.name}\" — {summary_b.term_count} terms, "
            f"top categories: {', '.join(summary_b.top_categories) or 'none'}, "
            f"top terms: {', '.join(summary_b.top_terms) or 'none'}, "
            f"avg search volume: {summary_b.avg_search_volume if summary_b.avg_search_volume is not None else 'unknown'}\n\n"
            f"Proximity index: {metrics.proximity_index}/100"
            f"{' (estimated — no embedding vectors available)' if proximity_estimated else ''}\n"
            f"Spatial proximity: {metrics.spatial_proximity}/100\n"
            f"3D distance: {metrics.euclidean_distance_3d}\n"
            f"Shared categories: {', '.join(metrics.shared_categories) or 'none'}\n"
            f"Shared subcategories: {', '.join(metrics.shared_subcategories) or 'none'}"
        )

        if proximity_estimated:
            user_prompt += (
                "\n\nNote: Proximity index is estimated (no embedding vectors available "
                "for these clusters). Use spatial proximity as the primary indicator of closeness."
            )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_tokens=400,
        )
        content = response.choices[0].message.content
        if not content:
            return _fallback_explanation(summary_a, summary_b, metrics, proximity_estimated), True
        return content, False

    except Exception as exc:
        logger.warning("OpenAI call failed, using fallback: %s", exc)
        return _fallback_explanation(summary_a, summary_b, metrics, proximity_estimated), True


def _fallback_explanation(
    summary_a: ClusterSummary,
    summary_b: ClusterSummary,
    metrics: CompareMetrics,
    proximity_estimated: bool = False,
) -> str:
    """Template-based explanation when LLM is unavailable."""
    # When proximity index is estimated (no embeddings), use spatial proximity instead
    score = metrics.spatial_proximity if proximity_estimated else metrics.proximity_index
    if score >= 70:
        relation = "closely positioned" if proximity_estimated else "highly similar"
    elif score >= 40:
        relation = "moderately close" if proximity_estimated else "moderately related"
    else:
        relation = "spatially distant" if proximity_estimated else "semantically distinct"

    if proximity_estimated:
        parts = [
            f'"{summary_a.name}" and "{summary_b.name}" are {relation} '
            f"based on their spatial proximity ({metrics.spatial_proximity}/100)."
        ]
    else:
        parts = [
            f'"{summary_a.name}" and "{summary_b.name}" are {relation} '
            f"with a proximity index of {metrics.proximity_index}/100."
        ]

    if metrics.shared_categories:
        parts.append(
            f"They share the following topic areas: {', '.join(metrics.shared_categories)}."
        )

    a_count = summary_a.term_count
    b_count = summary_b.term_count
    if a_count != b_count:
        bigger, smaller = (summary_a, summary_b) if a_count > b_count else (summary_b, summary_a)
        parts.append(
            f'"{bigger.name}" has a larger search footprint with {bigger.term_count} terms '
            f'compared to {smaller.term_count} in "{smaller.name}".'
        )

    if metrics.shared_subcategories:
        parts.append(
            f"They also overlap in subcategories: {', '.join(metrics.shared_subcategories)}."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/compare", response_model=CompareResponse)
def compare_clusters(req: CompareRequest, db: Session = Depends(get_db)):
    """Compare two clusters — returns metrics and an AI-generated explanation."""

    if req.cluster_a_id == req.cluster_b_id:
        raise HTTPException(status_code=400, detail="Cannot compare a cluster with itself")

    cluster_a = db.query(Cluster).filter(Cluster.id == req.cluster_a_id).first()
    cluster_b = db.query(Cluster).filter(Cluster.id == req.cluster_b_id).first()

    if not cluster_a:
        raise HTTPException(status_code=404, detail=f"Cluster {req.cluster_a_id} not found")
    if not cluster_b:
        raise HTTPException(status_code=404, detail=f"Cluster {req.cluster_b_id} not found")

    # Load member terms
    terms_a = db.query(SearchTerm).filter(SearchTerm.cluster_id == req.cluster_a_id).all()
    terms_b = db.query(SearchTerm).filter(SearchTerm.cluster_id == req.cluster_b_id).all()

    # Compute metrics
    prox_idx, prox_estimated = _proximity_index(db, cluster_a, cluster_b)
    spatial_score, euclidean_dist = _spatial_proximity(cluster_a, cluster_b)
    shared_cats, shared_subs = _category_overlap(terms_a, terms_b)

    summary_a = _cluster_summary(cluster_a, terms_a)
    summary_b = _cluster_summary(cluster_b, terms_b)

    metrics = CompareMetrics(
        proximity_index=prox_idx,
        spatial_proximity=spatial_score,
        euclidean_distance_3d=euclidean_dist,
        shared_categories=shared_cats,
        shared_subcategories=shared_subs,
    )

    explanation, is_fallback = _generate_explanation(summary_a, summary_b, metrics, prox_estimated)

    return CompareResponse(
        cluster_a=summary_a,
        cluster_b=summary_b,
        metrics=metrics,
        explanation=explanation,
        fallback=is_fallback,
    )
