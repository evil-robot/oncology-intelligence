"""
Story Builder API — LLM-guided user story creation + database-backed sprint management.
Kanban board, CRUD operations, and sprint tracking.
"""

import json
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..config import get_settings
from ..database import get_db
from ..models import Story, Sprint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stories", tags=["stories"])

settings = get_settings()

# OpenAI client (reuse from config)
ai_client = None
if settings.openai_api_key:
    try:
        ai_client = OpenAI(api_key=settings.openai_api_key)
    except Exception:
        pass


VALID_STATUSES = ["backlog", "ready", "in_progress", "review", "done", "archived"]
VALID_TRANSITIONS = {
    "backlog": ["ready", "archived"],
    "ready": ["backlog", "in_progress", "archived"],
    "in_progress": ["ready", "review", "archived"],
    "review": ["in_progress", "done", "archived"],
    "done": ["review", "archived"],
    "archived": ["backlog"],
}
VALID_PRIORITIES = ["Critical", "High", "Medium", "Low"]
BOARD_STATUSES = ["backlog", "ready", "in_progress", "review", "done"]


# --- Pydantic Models ---

class StoryCreate(BaseModel):
    epic: str
    feature: str
    user_story: str
    priority: str = "Medium"
    story_points: int = 3
    assigned_to: str = ""
    dependency: str = ""
    sprint_id: Optional[int] = None
    sprint: Optional[str] = None  # Accept sprint_id string like "2026-S1" from wizard
    demo_critical: bool = False
    acceptance_criteria: str = ""
    notes: str = ""


class StoryUpdate(BaseModel):
    epic: Optional[str] = None
    feature: Optional[str] = None
    user_story: Optional[str] = None
    priority: Optional[str] = None
    story_points: Optional[int] = None
    assigned_to: Optional[str] = None
    dependency: Optional[str] = None
    sprint_id: Optional[int] = None
    demo_critical: Optional[bool] = None
    acceptance_criteria: Optional[str] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None


class StatusUpdate(BaseModel):
    status: str


class SprintCreate(BaseModel):
    sprint_id: str  # "2026-S1"
    theme: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    demo_target: str = ""
    release_version: str = ""
    status: str = "planning"
    owner: str = ""
    risks: str = ""


class SprintUpdate(BaseModel):
    theme: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    demo_target: Optional[str] = None
    release_version: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    risks: Optional[str] = None


class AssistRequest(BaseModel):
    step: str  # "idea", "story", "criteria", "refine"
    input_text: str
    context: Optional[dict] = None


class AssistResponse(BaseModel):
    suggestion: str
    structured: Optional[dict] = None


class SheetContext(BaseModel):
    epics: List[str]
    sprints: List[dict]
    features: List[str]
    assignees: List[str]


# --- Story CRUD ---

@router.get("")
async def list_stories(
    sprint_id: Optional[int] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List stories with optional filters."""
    q = db.query(Story).filter(Story.status != "archived")

    if sprint_id is not None:
        q = q.filter(Story.sprint_id == sprint_id)
    if status:
        q = q.filter(Story.status == status)
    if priority:
        q = q.filter(Story.priority == priority)
    if assigned_to:
        q = q.filter(Story.assigned_to == assigned_to)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (Story.epic.ilike(pattern))
            | (Story.feature.ilike(pattern))
            | (Story.user_story.ilike(pattern))
        )

    stories = q.order_by(Story.sort_order, Story.id).all()
    return [_story_to_dict(s) for s in stories]


@router.post("")
async def create_story(data: StoryCreate, db: Session = Depends(get_db)):
    """Create a new story."""
    # Resolve sprint string to sprint_id if provided
    resolved_sprint_id = data.sprint_id
    if not resolved_sprint_id and data.sprint:
        sprint = db.query(Sprint).filter(Sprint.sprint_id == data.sprint).first()
        if sprint:
            resolved_sprint_id = sprint.id

    # Get max sort_order for the status column
    max_order = db.query(func.max(Story.sort_order)).filter(
        Story.status == "backlog"
    ).scalar() or 0

    story = Story(
        epic=data.epic,
        feature=data.feature,
        user_story=data.user_story,
        priority=data.priority,
        story_points=data.story_points,
        assigned_to=data.assigned_to,
        dependency=data.dependency,
        sprint_id=resolved_sprint_id,
        demo_critical=data.demo_critical,
        acceptance_criteria=data.acceptance_criteria,
        notes=data.notes,
        status="backlog",
        sort_order=max_order + 1,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return {"status": "ok", "message": "Story saved to backlog", "story": _story_to_dict(story)}


@router.get("/board")
async def get_board(
    sprint_id: Optional[int] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    epic: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get stories grouped by status column for the Kanban board."""
    q = db.query(Story).filter(Story.status.in_(BOARD_STATUSES))

    if sprint_id is not None:
        q = q.filter(Story.sprint_id == sprint_id)
    if priority:
        q = q.filter(Story.priority == priority)
    if assigned_to:
        q = q.filter(Story.assigned_to == assigned_to)
    if epic:
        q = q.filter(Story.epic == epic)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (Story.epic.ilike(pattern))
            | (Story.feature.ilike(pattern))
            | (Story.user_story.ilike(pattern))
        )

    stories = q.order_by(Story.sort_order, Story.id).all()

    # Group by status
    columns = {s: [] for s in BOARD_STATUSES}
    for story in stories:
        columns[story.status].append(_story_to_dict(story))

    # Compute totals
    total_points = sum(s.story_points or 0 for s in stories)
    done_points = sum(s.story_points or 0 for s in stories if s.status == "done")

    return {
        "columns": columns,
        "total_points": total_points,
        "done_points": done_points,
        "story_count": len(stories),
    }


@router.get("/context", response_model=SheetContext)
async def get_context(db: Session = Depends(get_db)):
    """Fetch existing epics, sprints, features, assignees from DB for dropdowns."""
    epics = [r[0] for r in db.query(Story.epic).distinct().filter(Story.epic.isnot(None), Story.epic != "").all()]
    features = [r[0] for r in db.query(Story.feature).distinct().filter(Story.feature.isnot(None), Story.feature != "").all()]
    assignees = [r[0] for r in db.query(Story.assigned_to).distinct().filter(Story.assigned_to.isnot(None), Story.assigned_to != "").all()]

    sprints = db.query(Sprint).order_by(Sprint.id.desc()).all()
    sprint_list = [
        {
            "id": s.sprint_id,
            "db_id": s.id,
            "theme": s.theme or "",
            "start": s.start_date.isoformat() if s.start_date else "",
            "end": s.end_date.isoformat() if s.end_date else "",
            "version": s.release_version or "",
            "status": s.status or "",
        }
        for s in sprints
    ]

    return SheetContext(
        epics=epics,
        sprints=sprint_list,
        features=features,
        assignees=assignees or ["JAS Bots", "Dustin", "JAS"],
    )


@router.get("/sprints")
async def list_sprints(db: Session = Depends(get_db)):
    """List all sprints."""
    sprints = db.query(Sprint).order_by(Sprint.id.desc()).all()
    return [_sprint_to_dict(s) for s in sprints]


@router.post("/sprints")
async def create_sprint(data: SprintCreate, db: Session = Depends(get_db)):
    """Create a new sprint."""
    existing = db.query(Sprint).filter(Sprint.sprint_id == data.sprint_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Sprint {data.sprint_id} already exists")

    sprint = Sprint(
        sprint_id=data.sprint_id,
        theme=data.theme,
        start_date=_parse_date(data.start_date),
        end_date=_parse_date(data.end_date),
        demo_target=data.demo_target,
        release_version=data.release_version,
        status=data.status,
        owner=data.owner,
        risks=data.risks,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return _sprint_to_dict(sprint)


@router.patch("/sprints/{sprint_db_id}")
async def update_sprint(sprint_db_id: int, data: SprintUpdate, db: Session = Depends(get_db)):
    """Update a sprint."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_db_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        if field in ("start_date", "end_date"):
            value = _parse_date(value)
        setattr(sprint, field, value)

    db.commit()
    db.refresh(sprint)
    return _sprint_to_dict(sprint)


@router.get("/{story_id}")
async def get_story(story_id: int, db: Session = Depends(get_db)):
    """Get a single story by ID."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return _story_to_dict(story)


@router.patch("/{story_id}")
async def update_story(story_id: int, data: StoryUpdate, db: Session = Depends(get_db)):
    """Update story fields."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(story, field, value)

    db.commit()
    db.refresh(story)
    return _story_to_dict(story)


@router.patch("/{story_id}/status")
async def update_story_status(story_id: int, data: StatusUpdate, db: Session = Depends(get_db)):
    """Move story to a new status with transition validation."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    new_status = data.status
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

    allowed = VALID_TRANSITIONS.get(story.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move from '{story.status}' to '{new_status}'. Allowed: {allowed}",
        )

    # Get max sort_order for the target column
    max_order = db.query(func.max(Story.sort_order)).filter(
        Story.status == new_status
    ).scalar() or 0

    story.status = new_status
    story.sort_order = max_order + 1
    db.commit()
    db.refresh(story)
    return _story_to_dict(story)


@router.delete("/{story_id}")
async def delete_story(story_id: int, db: Session = Depends(get_db)):
    """Archive a story (soft delete)."""
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story.status = "archived"
    db.commit()
    return {"status": "ok", "message": "Story archived"}


# --- LLM Assist (unchanged) ---

@router.post("/assist", response_model=AssistResponse)
async def assist_story(request: AssistRequest):
    """LLM-powered story writing assistance at each wizard step."""

    if not ai_client:
        return _fallback_assist(request)

    prompts = {
        "idea": """You are a product manager helping write user stories for VIOLET, an oncology & rare disease search intelligence platform.

The user has a rough idea. Help them refine it into:
1. A clear Epic name (the broad capability area)
2. A Feature name (the specific thing being built)
3. A draft user story in "As a [persona], I want [goal] so that [benefit]" format

Valid personas: researcher, clinician, patient advocate, data analyst, product owner, caregiver

Respond in JSON: {"epic": "...", "feature": "...", "user_story": "...", "rationale": "brief explanation of why this matters"}""",

        "story": """You are helping refine a user story for VIOLET (oncology intelligence platform).

Given the epic, feature, and draft story, improve the user story to be:
- Specific and testable
- Properly scoped (not too broad)
- Using the correct persona
- Clear about the value/benefit

Also suggest priority (Critical/High/Medium/Low) and story points (1, 2, 3, 5, 8, 13).

Respond in JSON: {"user_story": "improved story", "priority": "...", "story_points": N, "reasoning": "why this priority/sizing"}""",

        "criteria": """You are writing acceptance criteria for a user story on VIOLET (oncology intelligence platform).

Given the story details, write 3-5 specific, testable acceptance criteria. Each should be:
- Binary (pass/fail)
- Independent
- Written as "Given/When/Then" or numbered requirements

Also suggest any dependencies on other features/data.

Respond in JSON: {"acceptance_criteria": "numbered list as a string", "dependencies": "...", "notes": "implementation hints"}""",

        "refine": """You are doing a final review of a complete user story for VIOLET.

Check for:
- Clarity and completeness
- Proper scoping
- Realistic story points
- Testable acceptance criteria
- Missing dependencies

Suggest any improvements. If it's good, say so.

Respond in JSON: {"feedback": "...", "revised_story": "only if changes needed, else null", "revised_criteria": "only if changes needed, else null", "ship_ready": true/false}"""
    }

    system_prompt = prompts.get(request.step, prompts["idea"])

    user_content = f"User input: {request.input_text}"
    if request.context:
        user_content += f"\n\nCurrent story context: {json.dumps(request.context)}"

    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        return AssistResponse(
            suggestion=content,
            structured=parsed
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")


def _fallback_assist(request: AssistRequest) -> AssistResponse:
    """Provide basic assistance without LLM."""
    templates = {
        "idea": "Try framing your idea as: 'As a [researcher/clinician/caregiver], I want [specific capability] so that [concrete benefit]'. What persona will use this feature?",
        "story": "Good user stories are: Independent, Negotiable, Valuable, Estimable, Small, Testable (INVEST). Make sure yours passes each check.",
        "criteria": "Write 3-5 acceptance criteria as numbered requirements. Each should be pass/fail testable. Example:\n1) API returns results in < 500ms\n2) UI shows loading state during fetch\n3) Error message shown if no data available",
        "refine": "Review your story against INVEST criteria. Check that acceptance criteria are testable and dependencies are listed."
    }
    return AssistResponse(
        suggestion=templates.get(request.step, templates["idea"]),
        structured=None
    )


# --- Helpers ---

def _story_to_dict(story: Story) -> dict:
    return {
        "id": story.id,
        "epic": story.epic,
        "feature": story.feature,
        "user_story": story.user_story,
        "priority": story.priority,
        "story_points": story.story_points,
        "status": story.status,
        "assigned_to": story.assigned_to,
        "dependency": story.dependency,
        "sprint_id": story.sprint_id,
        "sprint_name": story.sprint.sprint_id if story.sprint else None,
        "demo_critical": story.demo_critical,
        "acceptance_criteria": story.acceptance_criteria,
        "notes": story.notes,
        "sort_order": story.sort_order,
        "created_at": story.created_at.isoformat() if story.created_at else None,
        "updated_at": story.updated_at.isoformat() if story.updated_at else None,
    }


def _sprint_to_dict(sprint: Sprint) -> dict:
    return {
        "id": sprint.id,
        "sprint_id": sprint.sprint_id,
        "theme": sprint.theme,
        "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
        "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
        "demo_target": sprint.demo_target,
        "release_version": sprint.release_version,
        "status": sprint.status,
        "owner": sprint.owner,
        "risks": sprint.risks,
        "created_at": sprint.created_at.isoformat() if sprint.created_at else None,
        "updated_at": sprint.updated_at.isoformat() if sprint.updated_at else None,
    }


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
