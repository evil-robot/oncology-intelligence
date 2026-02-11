"""Pipeline management API routes."""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import PipelineRun

logger = logging.getLogger(__name__)

router = APIRouter()


class PipelineRunResponse(BaseModel):
    """Pipeline run status."""

    id: int
    pipeline_name: str
    status: str
    started_at: str
    completed_at: Optional[str]
    records_processed: int
    errors: list

    class Config:
        from_attributes = True


class PipelineConfig(BaseModel):
    """Configuration for pipeline run."""

    fetch_trends: bool = True
    timeframe: str = "today 5-y"  # 5 years of data
    geo: str = "US"


@router.get("/runs", response_model=list[PipelineRunResponse])
async def list_pipeline_runs(
    db: Session = Depends(get_db),
    limit: int = 20,
):
    """List recent pipeline runs."""
    runs = (
        db.query(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
        .all()
    )

    return [
        PipelineRunResponse(
            id=r.id,
            pipeline_name=r.pipeline_name,
            status=r.status,
            started_at=r.started_at.isoformat() if r.started_at else "",
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
            records_processed=r.records_processed or 0,
            errors=r.errors or [],
        )
        for r in runs
    ]


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(run_id: int, db: Session = Depends(get_db)):
    """Get status of a specific pipeline run."""
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return PipelineRunResponse(
        id=run.id,
        pipeline_name=run.pipeline_name,
        status=run.status,
        started_at=run.started_at.isoformat() if run.started_at else "",
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        records_processed=run.records_processed or 0,
        errors=run.errors or [],
    )


@router.post("/run")
async def trigger_pipeline(
    config: PipelineConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger a new pipeline run.

    This starts the pipeline in the background and returns immediately.
    Use GET /runs/{run_id} to check status.
    """
    from pipeline.orchestrator import run_pipeline

    # Create initial run record
    run = PipelineRun(
        pipeline_name="full_pipeline",
        status="queued",
        config=config.model_dump(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Schedule background task
    async def run_in_background(run_id: int):
        from app.database import SessionLocal
        async_db = SessionLocal()
        try:
            await run_pipeline(
                async_db,
                fetch_trends=config.fetch_trends,
                timeframe=config.timeframe,
                geo=config.geo,
            )
        except Exception as e:
            logger.error(f"Pipeline run {run_id} failed: {e}")
            # Update the run record with failure status
            try:
                failed_run = async_db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
                if failed_run and failed_run.status != "completed":
                    failed_run.status = "failed"
                    failed_run.errors = [str(e)]
                    failed_run.completed_at = datetime.utcnow()
                    async_db.commit()
            except Exception:
                logger.error(f"Could not update run {run_id} status after failure")
        finally:
            async_db.close()

    background_tasks.add_task(run_in_background, run.id)

    return {
        "message": "Pipeline started",
        "run_id": run.id,
        "status_url": f"/api/pipeline/runs/{run.id}",
    }


@router.get("/stats")
async def get_pipeline_stats(db: Session = Depends(get_db)):
    """Get overall pipeline statistics."""
    from app.models import SearchTerm, Cluster, TrendData, GeographicRegion, RelatedQuery, QuestionSurface
    from sqlalchemy import func

    return {
        "terms": db.query(func.count(SearchTerm.id)).scalar(),
        "terms_with_embeddings": db.query(func.count(SearchTerm.id)).filter(
            SearchTerm.embedding.isnot(None)
        ).scalar(),
        "clusters": db.query(func.count(Cluster.id)).scalar(),
        "trend_data_points": db.query(func.count(TrendData.id)).scalar(),
        "geographic_regions": db.query(func.count(GeographicRegion.id)).scalar(),
        "regions_with_sdoh": db.query(func.count(GeographicRegion.id)).filter(
            GeographicRegion.svi_overall.isnot(None)
        ).scalar(),
        "related_queries": db.query(func.count(RelatedQuery.id)).scalar(),
        "discovered_terms": db.query(func.count(SearchTerm.id)).filter(
            SearchTerm.subcategory.like("discovered:%")
        ).scalar(),
        "questions": db.query(func.count(QuestionSurface.id)).scalar(),
    }
