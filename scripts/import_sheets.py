#!/usr/bin/env python3
"""
One-time import: Google Sheets → Database for sprints + stories.

Reads Sprint Dashboard and Sprint Backlog from the existing Google Sheet
and inserts them into the new `sprints` and `stories` DB tables.

Usage:
    cd /path/to/oncology-intelligence
    python scripts/import_sheets.py

Requires:
    - GOOGLE_SERVICE_ACCOUNT_JSON_B64 env var (or local SA key file)
    - GOOGLE_SHEET_ID env var (defaults to the known sheet ID)
    - DATABASE_URL env var pointing to Neon/Postgres
"""

import os
import sys
import json
import base64
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "15mAK33N2hLYHnygVqqNVnY1NZxqjtXCG7LOMiE6JTUE")
SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH", os.path.expanduser("~/.config/google/violet-mcp-key.json"))
GOOGLE_SA_JSON_B64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64", "")


def get_sheets_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    b64_creds = GOOGLE_SA_JSON_B64 or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64", "")

    if b64_creds:
        sa_json = base64.b64decode(b64_creds)
        sa_info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
    elif os.path.exists(SERVICE_ACCOUNT_PATH):
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=scopes)
    else:
        raise RuntimeError("No Google Sheets credentials found")

    return build('sheets', 'v4', credentials=creds)


STATUS_MAP = {
    "Not Started": "backlog",
    "To Do": "backlog",
    "Planned": "ready",
    "Ready": "ready",
    "In Progress": "in_progress",
    "In Review": "review",
    "Review": "review",
    "Done": "done",
    "Complete": "done",
    "Completed": "done",
    "Cancelled": "archived",
    "Archived": "archived",
}


def parse_bool(val: str) -> bool:
    return val.strip().lower() in ("yes", "true", "1", "y")


def parse_int(val: str, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def parse_date(val: str):
    from datetime import datetime
    if not val or not val.strip():
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(val.strip(), fmt)
        except ValueError:
            continue
    return None


def main():
    logger.info("Connecting to Google Sheets...")
    service = get_sheets_service()

    # --- Import Sprints ---
    logger.info("Reading Sprint Dashboard...")
    try:
        dashboard = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range="'Sprint Dashboard'!A1:J20"
        ).execute().get('values', [])
    except Exception as e:
        logger.error(f"Failed to read Sprint Dashboard: {e}")
        dashboard = []

    # --- Import Backlog ---
    logger.info("Reading Sprint Backlog...")
    try:
        backlog = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range="'Sprint Backlog'!A1:L200"
        ).execute().get('values', [])
    except Exception as e:
        logger.error(f"Failed to read Sprint Backlog: {e}")
        backlog = []

    if not dashboard and not backlog:
        logger.error("No data found in either sheet. Aborting.")
        return

    # Connect to DB
    from backend.app.database import SessionLocal, init_db
    from backend.app.models import Sprint, Story

    logger.info("Connecting to database...")
    init_db()
    db = SessionLocal()

    try:
        # Import sprints
        sprint_map = {}  # sprint_id string -> Sprint DB object
        if len(dashboard) > 1:
            headers = dashboard[0]
            logger.info(f"Sprint Dashboard headers: {headers}")
            for row in dashboard[1:]:
                if len(row) < 4:
                    continue
                sprint_id_str = row[0].strip()
                if not sprint_id_str:
                    continue

                existing = db.query(Sprint).filter(Sprint.sprint_id == sprint_id_str).first()
                if existing:
                    logger.info(f"  Sprint {sprint_id_str} already exists, skipping")
                    sprint_map[sprint_id_str] = existing
                    continue

                sprint = Sprint(
                    sprint_id=sprint_id_str,
                    theme=row[1].strip() if len(row) > 1 else "",
                    start_date=parse_date(row[2]) if len(row) > 2 else None,
                    end_date=parse_date(row[3]) if len(row) > 3 else None,
                    demo_target=row[4].strip() if len(row) > 4 else "",
                    release_version=row[5].strip() if len(row) > 5 else "",
                    owner=row[6].strip() if len(row) > 6 else "",
                    risks=row[8].strip() if len(row) > 8 else "",
                    status=STATUS_MAP.get(row[9].strip(), "planning") if len(row) > 9 else "planning",
                )
                db.add(sprint)
                db.flush()
                sprint_map[sprint_id_str] = sprint
                logger.info(f"  Imported sprint: {sprint_id_str}")

            db.commit()
            logger.info(f"Imported {len(sprint_map)} sprints")

        # Import stories
        if len(backlog) > 1:
            headers = backlog[0]
            logger.info(f"Sprint Backlog headers: {headers}")
            # Expected columns: Epic, Feature, User Story, Priority, Story Points,
            #                    Status, Assigned To, Dependency, Sprint, Demo Critical,
            #                    Acceptance Criteria, Notes
            imported = 0
            for row in backlog[1:]:
                if len(row) < 3:
                    continue
                epic = row[0].strip() if len(row) > 0 else ""
                if not epic:
                    continue

                feature = row[1].strip() if len(row) > 1 else ""
                user_story = row[2].strip() if len(row) > 2 else ""
                priority = row[3].strip() if len(row) > 3 else "Medium"
                story_points = parse_int(row[4], 3) if len(row) > 4 else 3
                raw_status = row[5].strip() if len(row) > 5 else "Not Started"
                assigned_to = row[6].strip() if len(row) > 6 else ""
                dependency = row[7].strip() if len(row) > 7 else ""
                sprint_str = row[8].strip() if len(row) > 8 else ""
                demo_critical = parse_bool(row[9]) if len(row) > 9 else False
                acceptance_criteria = row[10].strip() if len(row) > 10 else ""
                notes = row[11].strip() if len(row) > 11 else ""

                status = STATUS_MAP.get(raw_status, "backlog")
                sprint_db_id = sprint_map.get(sprint_str, None)

                story = Story(
                    epic=epic,
                    feature=feature,
                    user_story=user_story,
                    priority=priority if priority in ("Critical", "High", "Medium", "Low") else "Medium",
                    story_points=story_points,
                    status=status,
                    assigned_to=assigned_to,
                    dependency=dependency,
                    sprint_id=sprint_db_id.id if sprint_db_id else None,
                    demo_critical=demo_critical,
                    acceptance_criteria=acceptance_criteria,
                    notes=notes,
                    sort_order=imported,
                )
                db.add(story)
                imported += 1

            db.commit()
            logger.info(f"Imported {imported} stories")

        logger.info("Import complete!")

    except Exception as e:
        db.rollback()
        logger.error(f"Import failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
