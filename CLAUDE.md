# CLAUDE.md — Session Instructions for VIOLET

## First: Get Briefed
Read `VIOLET_SPEC.md` in this repo root before doing anything. It contains the full product and technical specification for VIOLET — architecture, data model, pipeline, API endpoints, frontend components, design system, and key decisions.

## Standing Rule: Keep the Spec Updated
**After making any code changes**, update `VIOLET_SPEC.md` to reflect what changed. This includes:
- New or modified API endpoints
- New or changed database models/fields
- New frontend components or significant UI changes
- Pipeline step changes
- New environment variables
- Design system changes
- File structure changes

Update the relevant section(s) in the spec before committing. The spec is the single source of truth that briefs Claude in every new session — if it's stale, future sessions start with wrong context.

## Project Context
- **Product:** VIOLET (Visual Intelligence Layer for Oncology Trends & Evidence Triangulation)
- **Company:** SuperTruth Inc.
- **Owner:** JAS (jas@evilrobot.com)
- **Repo:** oncology-intelligence
- **Stack:** FastAPI + Next.js + PostgreSQL/pgvector + Three.js
- **Deployment:** Railway.app (frontend + backend), Neon (database)
