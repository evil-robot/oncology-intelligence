"""
Story Builder API — LLM-guided user story creation + Google Sheets sync.
Used by the Story Builder web app for sprint planning.
"""

import os
import json
import base64
import tempfile
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import OpenAI
from ..config import get_settings

router = APIRouter(prefix="/api/stories", tags=["stories"])

settings = get_settings()

# Google Sheets config
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "15mAK33N2hLYHnygVqqNVnY1NZxqjtXCG7LOMiE6JTUE")
SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH", os.path.expanduser("~/.config/google/violet-mcp-key.json"))
# Base64-encoded service account JSON (for Railway/cloud deployments)
GOOGLE_SA_JSON_B64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64", "")

# OpenAI client (reuse from config)
ai_client = None
if settings.openai_api_key:
    try:
        ai_client = OpenAI(api_key=settings.openai_api_key)
    except Exception:
        pass


def get_sheets_service():
    """Lazy-init Google Sheets API client. Supports file path or base64 env var."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ['https://www.googleapis.com/auth/spreadsheets']

        if GOOGLE_SA_JSON_B64:
            # Decode base64 credentials from env var (Railway/cloud)
            sa_json = base64.b64decode(GOOGLE_SA_JSON_B64)
            sa_info = json.loads(sa_json)
            creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
        else:
            # Read from file (local dev)
            creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=scopes)

        return build('sheets', 'v4', credentials=creds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Sheets connection failed: {e}")


# --- Models ---

class AssistRequest(BaseModel):
    step: str  # "idea", "story", "criteria", "refine"
    input_text: str
    context: Optional[dict] = None  # Accumulated story fields so far


class AssistResponse(BaseModel):
    suggestion: str
    structured: Optional[dict] = None  # Parsed fields when applicable


class StorySubmission(BaseModel):
    epic: str
    feature: str
    user_story: str
    priority: str  # Critical, High, Medium, Low
    story_points: int
    assigned_to: str
    dependency: str
    sprint: str
    demo_critical: str  # Yes, No
    acceptance_criteria: str
    notes: str


class SheetContext(BaseModel):
    epics: List[str]
    sprints: List[dict]
    features: List[str]
    assignees: List[str]


# --- Endpoints ---

@router.get("/context", response_model=SheetContext)
async def get_sheet_context():
    """Fetch existing epics, sprints, features from the sheet for dropdowns."""
    try:
        service = get_sheets_service()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Sheets connection failed: {e}")

    try:
        # Read Sprint Dashboard for sprint info
        dashboard = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range="'Sprint Dashboard'!A1:J20"
        ).execute().get('values', [])

        # Read Sprint Backlog for epics/features/assignees
        backlog = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range="'Sprint Backlog'!A1:L100"
        ).execute().get('values', [])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google Sheets API error: {e}")

    # Extract unique values (skip header row)
    epics = list(set(row[0] for row in backlog[1:] if len(row) > 0 and row[0]))
    features = list(set(row[1] for row in backlog[1:] if len(row) > 1 and row[1]))
    assignees = list(set(row[6] for row in backlog[1:] if len(row) > 6 and row[6]))

    sprints = []
    for row in dashboard[1:]:
        if len(row) >= 6:
            sprints.append({
                "id": row[0],
                "theme": row[1],
                "start": row[2],
                "end": row[3],
                "version": row[5] if len(row) > 5 else "",
                "status": row[9] if len(row) > 9 else ""
            })

    return SheetContext(
        epics=epics,
        sprints=sprints,
        features=features,
        assignees=assignees or ["JAS Bots", "Dustin", "JAS"]
    )


@router.post("/assist", response_model=AssistResponse)
async def assist_story(request: AssistRequest):
    """LLM-powered story writing assistance at each wizard step."""

    if not ai_client:
        return _fallback_assist(request)

    prompts = {
        "idea": """You are a product manager helping write user stories for VIOLET, a pediatric oncology search intelligence platform.

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


@router.post("/submit")
async def submit_story(story: StorySubmission):
    """Push a completed story to the Sprint Backlog sheet."""
    service = get_sheets_service()

    row = [
        story.epic,
        story.feature,
        story.user_story,
        story.priority,
        str(story.story_points),
        "Not Started",
        story.assigned_to,
        story.dependency,
        story.sprint,
        story.demo_critical,
        story.acceptance_criteria,
        story.notes
    ]

    try:
        service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range="'Sprint Backlog'!A1:L1",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]}
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to write to Google Sheets: {e}")

    return {"status": "ok", "message": f"Story added to {story.sprint} backlog"}


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
