# VIOLET — Technical & Functional Specification

**Product:** VIOLET (Visual Intelligence Layer for Oncology Trends & Evidence Triangulation)
**Company:** SuperTruth Inc.
**Owner:** JAS (jas@evilrobot.com)
**Classification:** CONFIDENTIAL & PROPRIETARY

| Field | Value |
|-------|-------|
| Version | 0.10.0-alpha |
| Last Updated | February 12, 2026 |
| Repository | oncology-intelligence |
| Deployment | Railway.app (frontend + backend), Neon (database) |
| Live URL | https://violet.supertruth.ai |

### Revision History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | Jan 2026 | Initial technical spec — architecture, data model, pipeline, API |
| 0.9.0 | Feb 2026 | Added Question Surface, vulnerability window, evidence triangulation |
| 0.9.3 | Feb 2026 | Cluster explainability, geo dedup, N+1 query fixes |
| 0.9.4 | Feb 11, 2026 | Story Builder, Google Sheets sprint integration, full functional spec rewrite |
| 0.9.5 | Feb 11, 2026 | Category-aware embedding context for better cross-domain cluster separation |
| 0.9.6 | Feb 11, 2026 | QA pass: fix HTTPException returns, null dereferences, pipeline rollback, taxonomy dedup, frontend crash bugs |
| 0.9.7 | Feb 11, 2026 | QA phase 2: CORS restriction, chat rate limiting, WebGL memory fix, cascade deletes, pipeline transaction safety, responsive layout, stale copy cleanup |
| 0.10.0 | Feb 12, 2026 | Story Builder: replaced Google Sheets with DB-backed CRUD, added Kanban board page, Sprint/Story models, status lifecycle, import script |

---

## 1. Executive Summary

VIOLET is SuperTruth Inc.'s oncology and rare disease intelligence platform. It transforms Google search behavior — what people search, when they search, and how they phrase their fear — into a navigable 3D semantic map that overlays five intelligence layers: trend time-series, geographic health equity, temporal anxiety patterns, human question phrasing, and multi-source evidence triangulation.

The platform serves two audiences:
- **Researchers and clinicians** who need to see the landscape of oncology search behavior across 750+ curated terms, 25 disease categories, and 50 US states
- **Product and operations teams** who use the integrated Story Builder and Kanban board to plan, track, and ship features

VIOLET answers three questions simultaneously: **What** exists in the search field (structural intelligence), **When** people search (anxiety intelligence — 2am search spikes), and **How** they phrase it when they're scared (narrative intelligence — People Also Ask phrasing). These three layers combined produce **behavioral signal intelligence**.

This is not a medical tool. It does not diagnose, treat, or recommend. It reveals the hidden structure of how people search when confronting cancer and rare disease.

---

## 2. What Is Behavioral Signal Intelligence?

### 2.1 The Problem

When a parent searches "is my child's bruising leukemia" at 2am, that search is not a data point — it's a signal. Traditional analytics tools count searches. VIOLET reads the signal: the fear, the timing, the geography, the phrasing.

Oncology search behavior is fundamentally different from commercial search behavior. People searching about cancer are not comparison shopping. They are scared, overwhelmed, and often isolated. The way they search reveals:

- **What they know** — the medical vocabulary (or lack of it) in their queries
- **What they fear** — the questions they ask ("is it hereditary?", "will my child survive?")
- **When they're most vulnerable** — late-night searches when clinics are closed and anxiety peaks
- **Where resources are missing** — high-vulnerability communities with high search intent but few oncology centers

### 2.2 How VIOLET Solves It

VIOLET ingests ~750 curated oncology search terms, generates semantic embeddings (OpenAI), clusters them (HDBSCAN), projects them into 3D space (UMAP), and overlays five intelligence layers:

1. **Trend Intelligence** — 5-year time-series from Google Trends showing interest patterns
2. **Geographic Equity** — CDC Social Vulnerability Index mapped against search intensity
3. **Anxiety Patterns** — 24-hour hourly search data revealing "2am anxiety" windows
4. **Question Surface** — People Also Ask and autocomplete queries — the literal fear phrased
5. **Evidence Triangulation** — ClinicalTrials.gov, PubMed, FDA, Google Scholar, News, Patents

### 2.3 The Five Layers

| Layer | Data Source | What It Reveals |
|-------|-----------|-----------------|
| Structural | OpenAI embeddings + HDBSCAN + UMAP | Semantic relationships between diseases, treatments, concerns |
| Temporal | SerpAPI Google Trends (5yr + hourly) | When interest spikes, seasonal patterns, 2am anxiety |
| Geographic | CDC SVI + Google Trends by state | Where vulnerable populations search without nearby resources |
| Narrative | SerpAPI PAA + Autocomplete | How people phrase fear ("is it normal to...", "will my child...") |
| Evidentiary | 6 external APIs | What clinical evidence exists, how strong it is |

---

## 3. Product Overview

### 3.1 Vision & Mission

**Vision:** Make the invisible architecture of oncology search behavior visible, navigable, and actionable.

**Mission:** Provide researchers, clinicians, patient advocates, and caregivers with the world's most comprehensive view of how people search when confronting cancer and rare disease — and surface the gaps where people search but resources don't exist.

### 3.2 Target Users

| Persona | Role | What They Do in VIOLET |
|---------|------|----------------------|
| Researcher | Academic/pharma research | Explore term clusters, discover emerging search patterns, triangulate evidence |
| Clinician | Oncologist/rare disease specialist | Understand patient concerns, see what questions patients ask before appointments |
| Patient Advocate | Nonprofit/foundation leader | Identify underserved communities, map search-to-resource gaps |
| Caregiver | Parent/family of patient | (Indirect) — VIOLET surfaces the questions caregivers ask at 2am |
| Data Analyst | SuperTruth internal | Run pipelines, manage taxonomy, QA data quality |
| Product Owner | SuperTruth team (JAS, Dustin) | Sprint planning via Story Builder, feature prioritization |

### 3.3 Core Capabilities

| Capability | Description |
|-----------|-------------|
| 3D Semantic Map | Interactive Three.js visualization of 750+ search terms in clustered 3D space |
| Cluster Navigation | Click clusters to isolate, fly through space with WASD controls or auto-tour |
| Trend Analysis | 5-year time-series per term/cluster with spike/drop/emerging detection |
| SDOH Overlay | Vulnerability-adjusted search intensity (Interest x (1+SVI)) by US state |
| Anxiety Window | 24-hour hourly heatmaps showing late-night search patterns |
| Question Surface | Cross-term search of People Also Ask + autocomplete questions |
| Evidence Triangulation | 6-source lookup: ClinicalTrials, PubMed, FDA, Scholar, News, Patents |
| Multi-Region Compare | Side-by-side term/category comparison across geographies |
| AI Chat | Conversational interface with full database context injection |
| Anomaly Detection | Automatic spike, drop, emerging term, and regional outlier flagging |
| Auto Taxonomy Expansion | Pipeline auto-discovers and promotes breakout search terms |
| Story Builder | LLM-guided user story wizard + database-backed Kanban board |
| Demo Mode | Full synthetic data generation for demos without API keys |

### 3.4 Explicit Non-Goals

VIOLET intentionally does **not**:
- Provide medical advice, diagnosis, or treatment recommendations
- Store or process individual patient data (HIPAA scope excluded)
- Predict disease outcomes or survival rates
- Replace clinical decision support systems
- Perform real-time search monitoring (data is batch-processed)
- Serve as a consumer-facing product (research/internal only)

### 3.5 Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| 3D Semantic Map | Live | Full UMAP + HDBSCAN pipeline, interactive Three.js |
| Trend Time-Series | Live | SerpAPI, 5-year data, per-term and per-cluster |
| SDOH Overlay | Live | CDC SVI 2020, all 50 states, vulnerability-adjusted scoring |
| Question Surface | Live | PAA + autocomplete, cross-term search |
| Anxiety Window | Live | 24-hour hourly patterns, anxiety index |
| Evidence Triangulation | Live | 6 external APIs, on-demand queries |
| Multi-Region Compare | Live | Country-level comparison |
| AI Chat | Live | GPT-4o-mini with database context |
| Anomaly Detection | Live | Spike/drop/emerging/regional detection |
| Auto Taxonomy Expansion | Live | Breakout term promotion, capped at 50/run |
| Story Builder | Live | LLM wizard + DB-backed Kanban board (replaced Sheets) |
| Cluster Explainability | Planned (S1) | Proximity index, scale index, narrative generator |
| Pipeline Scheduler | Planned | Automated daily/weekly runs |
| Export/Reporting | Planned | PDF/CSV export of insights |

---

## 4. System Architecture

### 4.1 High-Level Architecture

```
User (Browser)
   │
   ▼
Next.js Frontend (Railway)
   │  Three.js 3D Canvas + React panels
   │  Zustand state management
   │  Middleware auth (cookie-based)
   │
   ▼
FastAPI Backend (Railway)
   │  11 API route modules + chat
   │  Pipeline orchestrator (8 steps)
   │
   ├──▶ PostgreSQL + pgvector (Neon)
   │     SearchTerm, Cluster, TrendData, GeographicRegion,
   │     RelatedQuery, HourlyPattern, QuestionSurface, Post,
   │     Sprint, Story
   │
   ├──▶ OpenAI API
   │     Embeddings (text-embedding-3-small)
   │     Chat (gpt-4o-mini)
   │     Story Builder assist (gpt-4o-mini)
   │
   ├──▶ SerpAPI
   │     Google Trends, PAA, Autocomplete,
   │     Scholar, News, Patents
   │
   └──▶ External APIs (on-demand, not stored)
         ClinicalTrials.gov, PubMed, FDA openFDA
```

### 4.2 Application Layers

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| Presentation | Next.js 14, React 18, Three.js | 3D visualization, panels, Story Builder |
| Styling | Tailwind CSS 3.4, glass morphism | Dark theme, responsive layout |
| State | Zustand 4.4 | Client-side selection, filters, camera state |
| API Gateway | FastAPI + Uvicorn | REST endpoints, CORS, middleware |
| Business Logic | Python route handlers | Data aggregation, anomaly detection, LLM orchestration |
| Pipeline | Python orchestrator | 8-step ETL: taxonomy → embed → cluster → trends → discover → questions → hourly → SDOH |
| Storage | PostgreSQL + pgvector (Neon) | Relational data + vector similarity search |
| External | SerpAPI, OpenAI, ClinicalTrials, PubMed, FDA | Data sources and integrations |

### 4.3 Directory Structure

```
oncology-intelligence/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware, router registration
│   │   ├── config.py             # Pydantic Settings (env vars)
│   │   ├── database.py           # PostgreSQL connection, schema init, taxonomy auto-seed
│   │   ├── models.py             # All SQLAlchemy models
│   │   └── routes/
│   │       ├── clusters.py       # Cluster listing, 3D viz data
│   │       ├── terms.py          # Taxonomy, similarity, questions
│   │       ├── trends.py         # Time-series, vulnerability window
│   │       ├── geography.py      # Regional SDOH heatmaps
│   │       ├── insights.py       # Anomaly detection
│   │       ├── questions.py      # Question Surface cross-term search
│   │       ├── compare.py        # Multi-region comparison
│   │       ├── triangulation.py  # External evidence APIs
│   │       ├── pipeline.py       # Pipeline management
│   │       ├── chat.py           # Conversational AI
│   │       ├── cluster_compare.py # Cluster pair comparison + LLM explanation
│   │       └── stories.py        # Story Builder (DB-backed CRUD + Kanban board + LLM)
│   ├── pipeline/
│   │   ├── orchestrator.py       # 8-step pipeline coordinator
│   │   ├── taxonomy.py           # 749+ seed terms, 20 categories
│   │   ├── embeddings.py         # OpenAI embedding generation
│   │   ├── clustering.py         # UMAP + HDBSCAN
│   │   ├── trends_fetcher.py     # SerpAPI Google Trends client
│   │   ├── question_fetcher.py   # SerpAPI PAA + autocomplete client
│   │   ├── anomaly_detection.py  # Spike/drop/emerging detection
│   │   ├── sdoh_loader.py        # CDC SVI data loader
│   │   └── external_data.py      # ClinicalTrials, PubMed, FDA, News, Scholar, Patents
│   ├── data/
│   │   └── sample_data.json      # Demo seed data
│   ├── Dockerfile
│   ├── Procfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx            # Root layout, metadata
│   │   ├── page.tsx              # Main 3-column dashboard
│   │   ├── globals.css           # Tailwind + glass morphism + animations
│   │   ├── login/page.tsx        # Password auth page
│   │   ├── story-builder/page.tsx       # LLM-guided story creation wizard
│   │   ├── story-builder/board/page.tsx # Kanban board (5-column status view)
│   │   └── api/auth/route.ts     # Cookie-based auth endpoint
│   ├── components/
│   │   ├── ClusterVisualization.tsx   # 3D engine (~850 lines)
│   │   ├── FilterPanel.tsx           # Search + category browser
│   │   ├── DetailPanel.tsx           # Term/cluster detail + questions
│   │   ├── InsightsPanel.tsx         # Anomaly dashboard
│   │   ├── VulnerabilityInsightsPanel.tsx  # SDOH × interest heatmap
│   │   ├── VulnerabilityWindow.tsx   # 24-hour anxiety patterns
│   │   ├── DataSourcesPanel.tsx      # Evidence triangulation
│   │   ├── PipelinePanel.tsx         # Pipeline control + stats
│   │   ├── ChatPanel.tsx             # AI conversation
│   │   ├── ClusterComparisonPopup.tsx # AI-explained cluster pair comparison
│   │   ├── ExplainerPanel.tsx        # Guided tour modal
│   │   ├── RegionComparisonPanel.tsx # Multi-region analysis
│   │   ├── ViewControls.tsx          # Label/connection toggles
│   │   ├── StatsBar.tsx              # Header stats
│   │   ├── SuperTruthLogo.tsx        # SVG branding
│   │   └── Tooltip.tsx               # Smart-positioning tooltips
│   ├── lib/
│   │   ├── api.ts                # API client + type definitions
│   │   └── store.ts              # Zustand global state
│   ├── middleware.ts             # Auth middleware (cookie check, login redirect)
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js            # Standalone output, API_URL
│   └── tailwind.config.js        # Custom colors, 24-col grid
├── scripts/
│   ├── init_and_seed.py
│   ├── seed_database.py
│   └── run_pipeline.py
├── VIOLET_SPEC.md                # THIS FILE
└── CLAUDE.md                     # Session instructions for Claude
```

---

## 5. Technology Stack

### 5.1 Runtime Dependencies — Frontend

| Package | Version | Purpose |
|---------|---------|---------|
| next | 14.1.0 | React framework with App Router |
| react / react-dom | 18.2.0 | UI library |
| three | 0.160.0 | 3D rendering engine |
| @react-three/fiber | 8.15.0 | React bindings for Three.js |
| @react-three/drei | 9.96.0 | Three.js helpers (OrbitControls, etc.) |
| recharts | 2.10.0 | 2D charts (trend lines, heatmaps) |
| zustand | 4.4.0 | Lightweight state management |
| swr | 2.2.0 | Data fetching with caching |
| d3-scale / d3-scale-chromatic | 4.x | Color scales and data mapping |
| lucide-react | 0.312.0 | Icon library |

### 5.2 Runtime Dependencies — Backend

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.109+ | REST API framework |
| uvicorn | 0.27+ | ASGI server |
| sqlalchemy | 2.0+ | ORM |
| psycopg2-binary | 2.9+ | PostgreSQL driver |
| pgvector | 0.2+ | Vector similarity in PostgreSQL |
| openai | 1.12+ | Embeddings + chat completions |
| google-search-results | 2.4+ | SerpAPI client |
| google-api-python-client | 2.100+ | Google Sheets API |
| google-auth | 2.25+ | Service account authentication |
| umap-learn | 0.5+ | Dimensionality reduction (1536 → 3D) |
| hdbscan | 0.8+ | Density-based clustering |
| scikit-learn | 1.4+ | ML utilities |
| pandas / numpy | 2.2+ / 1.26+ | Data processing |
| pydantic / pydantic-settings | 2.6+ / 2.1+ | Request validation, env config |

---

## 6. Authentication & Authorization

### 6.1 Authentication Flow

VIOLET uses cookie-based password authentication via Next.js middleware.

1. User visits any page → middleware checks for `violet_auth` cookie
2. If missing → redirect to `/login`
3. User enters password → `POST /api/auth` validates against `BASIC_AUTH_PASSWORD` env var
4. If valid → sets `violet_auth=authenticated` cookie → redirect to requested page
5. All subsequent requests pass through with cookie present

### 6.2 Middleware Configuration

The middleware (`frontend/middleware.ts`) protects all routes except:
- `/login` — the auth page itself
- `/api/auth` — the auth endpoint
- `/_next/static`, `/_next/image`, `favicon.ico` — static assets

### 6.3 Backend Authentication

The backend API restricts CORS to configured origins (configurable via `CORS_ORIGINS` env var, defaults to `https://violet.supertruth.ai,http://localhost:3000,http://localhost:3001`). The chat endpoint has rate limiting (20 requests/minute per IP). The frontend handles user authentication. This is acceptable because:
- CORS restricts which origins can call the API
- Railway networking keeps the backend service internal
- Chat rate limiting prevents abuse
- Future: API key auth for programmatic access

### 6.4 Sprint Data Storage

Sprint and story data is stored in PostgreSQL (same Neon database as all other VIOLET data). The `sprints` and `stories` tables are auto-created by `Base.metadata.create_all()` on startup. Historical data was migrated from Google Sheets via `scripts/import_sheets.py`.

---

## 7. Core Functional Modules

### 7.1 3D Semantic Map (ClusterVisualization.tsx)

The heart of VIOLET. An interactive Three.js scene rendering 750+ search terms as glowing spheres in 3D semantic space.

**Sub-components:**
- **DataPoint** — Search term sphere with glow, hover/selection animations, color gradient cyan→pink
- **ClusterOrb** — Cluster center icosahedron with rotating wireframe rings
- **BoundingCube** — 12-edge wireframe boundary (12×12×12 space)
- **DataConnections** — Lines from terms to cluster centroids
- **AmbientParticles** — 600 starfield background particles
- **FlyControls** — WASD first-person navigation
- **AutoPilot** — Cinematic Catmull-Rom spline camera tour
- **CameraController** — Smooth lerp to store-controlled position on selection
- **SelectionRing** — Pulsing ring overlay for comparison-selected clusters (cyan=A, pink=B)
- **ComparisonConnection** — Dashed line with glow connecting cluster pair A↔B

**Interaction:** Click cluster A → highlighted with pulsing ring + "A" badge. Click cluster B → both highlighted, dashed line connects them. Click third cluster → replaces B, keeps A. Click A again → clears comparison. ESC or click empty space → clears comparison. Click term → detail panel opens. Show All → reset to full galaxy view `[0,0,15]`.

**Comparison pair state** in Zustand (`store.ts`): `comparison: { clusterA: Cluster | null, clusterB: Cluster | null }`. Actions: `setComparisonCluster(cluster)`, `clearComparison()`. Selector: `useComparison()`.

### 7.2 Filter & Search (FilterPanel.tsx)

- Real-time fuzzy search across all terms
- Expandable category accordion (25 categories with color coding)
- Click subcategory → fills search box with subcategory name AND zooms camera to those terms in 3D space (via `focusOnSubcategory` store action)
- Geography dropdown (50 US states)
- Click category → camera animates to category centroid

### 7.3 Detail Panel (DetailPanel.tsx)

Appears on term/cluster selection. Contains:
- Header: type badge, name, category tag
- Trend chart: Recharts LineChart, 90-day time series
- Similar Terms: top 5 semantic neighbors via pgvector cosine distance
- People Also Ask: top 10 questions with snippets and source links
- Top Regions: top 5 states by interest
- Google Search link

### 7.4 Anomaly Detection (InsightsPanel.tsx)

Automatic pattern detection across the dataset:

| Type | What It Detects |
|------|----------------|
| Spike | Sudden interest increase (>2σ above rolling mean) |
| Drop | Sudden interest decrease |
| Emerging | New terms with accelerating growth |
| Regional Outlier | State-level interest significantly above national average |
| Seasonal Anomaly | Out-of-season interest patterns |
| Correlation | Co-moving term pairs |

Severity levels: high, medium, low. Clickable cards fly camera to the relevant term. Each card shows a `Crosshair` icon (lucide-react) to signal "navigate to" rather than "expand."

### 7.5 SDOH Vulnerability Analysis (VulnerabilityInsightsPanel.tsx)

Cross-references search intent with CDC Social Vulnerability Index:

**Formula:** `Vulnerability-Adjusted Score = Interest × (1 + SVI)`

This surfaces communities where high search interest meets high social vulnerability — places where people are searching but resources may be scarce. Sortable by combined score, interest, or vulnerability. Expandable rows show calculation breakdown.

### 7.6 Anxiety Window (VulnerabilityWindow.tsx)

24-hour hourly search pattern analysis. Two views:

1. **Hourly Heatmap** — 24-column grid, color-coded purple→pink→red, late-night zone (11pm-4am) highlighted
2. **Most Anxious** — Terms ranked by `anxiety_index = late_night_avg / daytime_avg`

Terms with anxiety_index > 1.0 are night-skewed — people search these more when clinics are closed.

### 7.7 Question Surface (Questions endpoint + DetailPanel)

Captures the literal language of fear. Sources:
- **People Also Ask** — Google's related questions (2 pages per term via SerpAPI)
- **Autocomplete** — Seeded with 10 question prefixes: "how do I", "where can I", "what is", "is it normal to", "can I", "why does", "what are the symptoms of", "what happens if", "how long does", "should I"

Cross-term search at `/api/questions/search?q=...` finds questions across the entire dataset.

### 7.8 Evidence Triangulation (DataSourcesPanel.tsx)

On-demand multi-source evidence lookup for any term:

| Source | API | Data |
|--------|-----|------|
| ClinicalTrials.gov | REST API | Active trials, phases, locations |
| PubMed | E-utilities | Published research, citations |
| FDA openFDA | REST API | Drug approvals, adverse events |
| Google Scholar | SerpAPI | Academic papers, citation counts |
| Google News | SerpAPI | Recent news coverage |
| Google Patents | SerpAPI | Patent filings |

Evidence strength badge per source. Results are fetched on-demand, not stored.

### 7.9 Multi-Region Comparison (RegionComparisonPanel.tsx)

Compare a single term across multiple countries/states, or compare top terms across regions. Category-level comparison shows which disease areas generate the most interest per geography.

### 7.10 AI Chat (ChatPanel.tsx)

Floating expandable chat window. OpenAI gpt-4o-mini with full database context injection:
- Total terms, clusters, trend points
- Top trending terms (30-day)
- Cluster membership
- Category breakdown
- High-vulnerability regions
- Recent search spikes

Conversation history (last 10 messages). Suggested follow-up questions based on context.

### 7.11 Story Builder (`/story-builder`)

LLM-guided user story creation wizard for sprint planning. Designed for Dustin (and any team member) to create well-structured stories without touching a spreadsheet.

**Design:** Dark theme with animated particle network (60 canvas particles with proximity connections), gradient orbs, glass-morphism cards, SuperTruth logo + VIOLET badge, pulsing AI indicator.

**4-Step Wizard:**

| Step | Name | What Happens |
|------|------|-------------|
| 01 | Ideate | Describe idea in plain language → AI extracts epic, feature, user story |
| 02 | Shape | Refine story, set priority/points/sprint/assignee (dropdowns from DB) |
| 03 | Define | AI generates acceptance criteria, set dependencies and notes |
| 04 | Ship | Review card preview → saves to backlog in database |

**Database Integration:**
- Stories and sprints stored in PostgreSQL (`stories` and `sprints` tables)
- `GET /api/stories/context` — reads existing epics/sprints/features/assignees for dropdowns
- `POST /api/stories/assist` — LLM-powered story assistance (4 step types)
- `POST /api/stories` — creates story in database with status "backlog"

### 7.12 Story Board (`/story-builder/board`)

Kanban board showing all stories organized by status column.

**Design:** Same dark theme as Story Builder. Full-width 5-column grid, sticky header with sprint selector and progress bar.

**Components:**
- **BoardHeader** — Sprint selector dropdown, "New Story" button, sprint progress bar (done points / total points)
- **BoardFilters** — Priority, assignee, epic filters + text search
- **BoardColumn** — One per status, color-coded header, scrollable story cards
- **StoryCard** — Compact card: priority dot, feature name, points badge, assignee initial
- **StoryDetailDrawer** — Right-side slide panel on card click. Full editable fields, status transition buttons, archive

**Column Colors:**
- Backlog: gray | Ready: blue | In Progress: violet | Review: amber | Done: emerald

**Story Lifecycle:**
```
backlog → ready → in_progress → review → done → archived
```
Board shows 5 columns (archived hidden). Status transitions enforced by API.

### 7.13 Pipeline Management (PipelinePanel.tsx)

Stats grid (terms, trend points, regions, related queries, discovered terms, questions). Run button triggers the 8-step pipeline with animated progress indicator.

### 7.14 Cluster Comparison Popup (ClusterComparisonPopup.tsx)

Fixed-position overlay that auto-appears when both comparison clusters (A and B) are selected in the 3D view. Calls `POST /api/clusters/compare` to fetch proximity metrics and an AI-generated narrative explanation.

- **Auto-trigger:** Watches `useComparison()` — popup shows when both `clusterA` and `clusterB` are non-null.
- **Auto-dismiss:** Clears when comparison is cleared (ESC / click empty / "Show All").
- **Session cache:** `useRef<Map>` keyed by `"${aId}-${bId}"` — re-selecting the same pair shows cached result instantly.
- **Layout:** `position: fixed`, centered, `z-[1000]` (above 3D `Html` labels at z-index 200-300), 480px wide, glass morphism background (`rgba(5,5,20,0.92)` + `backdrop-filter: blur(16px)`), cyan/pink badges matching SelectionRing colors.
- **Content:** Header with A↔B cluster names, proximity index gauge (red→yellow→green), term count scale, shared category pills (purple), AI explanation body.

### 7.15 Demo Mode

When no real pipeline data exists, VIOLET generates realistic synthetic data for every endpoint:
- Trend time-series: 90-day data with seeded pseudorandom for reproducibility
- Geographic interest: MD5 hash of geo_code produces deterministic varied values per state
- Insights: Sample anomalies spread across actual taxonomy categories
- Questions: Template-based PAA questions per term
- Vulnerability windows: Synthetic hourly patterns with realistic anxiety profiles

Demo mode is flagged in responses (`demo_mode: true`) so the UI shows appropriate banners.

---

## 8. Data Model

### 8.1 Core Tables

**SearchTerm** — The primary entity. Every search term in the taxonomy becomes a positioned point in 3D space.

| Column | Type | Description |
|--------|------|-------------|
| id | int (PK) | Auto-increment |
| term | varchar(500) | Unique search string, e.g. "BRCA gene mutation" |
| normalized_term | varchar(500) | Lowercase indexed version |
| category | varchar(100) | High-level: pediatric_oncology, adult_oncology, treatment, rare_genetic, etc. |
| subcategory | varchar(100) | Fine-grained: leukemia, brain_tumor, immunotherapy, etc. |
| parent_term_id | int (FK) | Hierarchical parent relationship |
| embedding | vector(1536) | OpenAI text-embedding-3-small |
| x, y, z | float | 3D coordinates from UMAP reduction |
| cluster_id | int (FK) | Semantic cluster assignment |

**Cluster** — Semantic groupings auto-generated by HDBSCAN.

| Column | Type | Description |
|--------|------|-------------|
| id | int (PK) | Auto-increment |
| name | varchar(200) | Auto-generated from member term names |
| description | text | Optional context |
| centroid_x/y/z | float | 3D center point |
| centroid_embedding | vector(1536) | Average embedding of members |
| color | varchar(7) | Hex color for visualization |
| size | float | Relative visual size (default 1.0) |
| term_count | int | Cached member count |
| avg_search_volume | float | Computed from TrendData |

**TrendData** — Time-series search interest from Google Trends.

| Column | Type | Description |
|--------|------|-------------|
| id | int (PK) | Auto-increment |
| term_id | int (FK) | Parent search term |
| date | date | Data point date |
| geo_code | varchar(10) | e.g. "US", "US-CA" |
| geo_level | varchar(20) | "country", "state", "metro" |
| interest | int | 0-100 relative search interest |
| granularity | varchar(20) | "daily", "weekly", "monthly" |

**GeographicRegion** — US states with CDC Social Vulnerability Index.

| Column | Type | Description |
|--------|------|-------------|
| id | int (PK) | Auto-increment |
| geo_code | varchar(10) | Unique, e.g. "US-MS" |
| name | varchar(100) | "Mississippi" |
| level | varchar(20) | "state", "county", "metro", "country" |
| latitude, longitude | float | Centroid coordinates |
| population | int | Census data |
| svi_overall | float | 0-1, higher = more vulnerable |
| svi_socioeconomic | float | Poverty, unemployment, income, education |
| svi_household_disability | float | Disability, age, single parents |
| svi_minority_language | float | Race/ethnicity, language barriers |
| svi_housing_transport | float | Housing type, crowding, no car |
| uninsured_rate | float | Healthcare access |
| pediatric_oncology_centers | int | Nearby specialized centers |
| vulnerability_adjusted_intent | float | Interest × (1 + SVI) |

### 8.2 Intelligence Tables

**RelatedQuery** — Discovered related searches for automatic taxonomy expansion.

| Column | Type | Description |
|--------|------|-------------|
| source_term_id | int (FK) | Parent search term |
| query | varchar(500) | The related search string |
| query_type | varchar(50) | rising_query, top_query, rising_topic, top_topic |
| value | varchar(100) | Raw: "+450%", "Breakout", "100" |
| extracted_value | float | Numeric: 450, -1 (Breakout), 100 |
| is_promoted | bool | Whether promoted to taxonomy |

**HourlyPattern** — Temporal search behavior / anxiety patterns.

| Column | Type | Description |
|--------|------|-------------|
| term_id | int (FK) | Parent search term |
| hourly_avg | JSON | {0: 45, 1: 52, ..., 23: 68} |
| peak_hours | JSON | Top 3 hours, e.g. [22, 23, 21] |
| anxiety_index | float | late_night_avg / daytime_avg (>1.0 = night-skewed) |

**QuestionSurface** — Literal human question phrasing.

| Column | Type | Description |
|--------|------|-------------|
| source_term_id | int (FK) | Parent search term |
| question | varchar(1000) | Full question text |
| snippet | text | Google's answer preview |
| source_url | varchar(2000) | URL of answering page |
| source_type | varchar(50) | "people_also_ask" or "autocomplete" |
| rank | int | Position in search results |

**Post** — External resources positioned in 3D semantic space.

| Column | Type | Description |
|--------|------|-------------|
| title | varchar(500) | Resource title |
| url | varchar(2000) | External URL |
| source | varchar(100) | "pubmed", "clinical_trial", etc. |
| embedding | vector(1536) | For semantic positioning |
| x, y, z | float | 3D coordinates near relevant cluster |
| cluster_id | int (FK) | Associated cluster |

### 8.3 Sprint Planning Tables

**Sprint** — Development sprint containers.

| Column | Type | Description |
|--------|------|-------------|
| id | int (PK) | Auto-increment |
| sprint_id | varchar(20) | Unique human-readable: "2026-S1" |
| theme | varchar(300) | Sprint theme |
| start_date / end_date | datetime | Sprint window |
| demo_target | varchar(300) | Demo target description |
| release_version | varchar(50) | e.g. "v0.2.0" |
| status | varchar(20) | planning, active, completed, cancelled |
| owner | varchar(100) | Sprint owner |
| risks | text | Risk notes |

**Story** — User stories for the Kanban board.

| Column | Type | Description |
|--------|------|-------------|
| id | int (PK) | Auto-increment |
| epic | varchar(300) | Epic name (indexed) |
| feature | varchar(300) | Feature name |
| user_story | text | "As a... I want... So that..." |
| priority | varchar(20) | Critical, High, Medium, Low |
| story_points | int | Fibonacci: 1, 2, 3, 5, 8, 13 |
| status | varchar(30) | backlog, ready, in_progress, review, done, archived (indexed) |
| assigned_to | varchar(100) | Assignee name (indexed) |
| dependency | varchar(500) | Dependency notes |
| sprint_id | int (FK → sprints.id) | Sprint assignment (nullable) |
| demo_critical | bool | Whether story is demo-critical |
| acceptance_criteria | text | Numbered criteria |
| notes | text | Implementation notes |
| sort_order | int | Board ordering within column |

---

## 9. Data Pipeline

The pipeline is an 8-step sequential ETL process coordinated by `PipelineOrchestrator`.

| Step | Name | What It Does |
|------|------|-------------|
| 1 | Load Taxonomy | Loads 749+ seed terms from taxonomy.py, creates SearchTerm records, 20 categories |
| 2 | Generate Embeddings | OpenAI text-embedding-3-small, batches of 100, **category-aware context** (each term prefixed with its disease-domain, e.g. "Rare genetic and inherited disorder: muscular dystrophy" vs "Adult cancer and oncology: lymphoma") |
| 3 | Cluster & Project | UMAP (1536→3D), HDBSCAN clustering, update coordinates and cluster assignments |
| 4 | Fetch Trends | SerpAPI Google Trends: interest-over-time, by-region, related queries/topics. 5-year, US. Commits every 10 terms |
| 5 | Expand Taxonomy | Promote related queries with ≥200% growth or "Breakout" status. Max 50 new terms/run |
| 6 | Fetch Questions | SerpAPI PAA (2 pages/term) + autocomplete (10 prefix seeds). 8-15 questions/term |
| 7 | Fetch Hourly | SerpAPI 7-day hourly data. Compute anxiety_index, peak hours, day-of-week patterns |
| 8 | Load SDOH | CDC SVI 2020 county CSV, population-weighted state aggregation |

**Clustering parameters:** UMAP (n_neighbors=10, min_dist=0.5, spread=2.0, metric=cosine), HDBSCAN (min_cluster_size=5, min_samples=3, metric=euclidean)

---

## 10. API Reference

### 10.1 Cluster Endpoints (`/api/clusters`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List all clusters (filterable by category) |
| GET | `/visualization` | 3D data: clusters + terms + posts with coordinates |
| GET | `/{cluster_id}` | Detail with member terms and posts |

### 10.2 Term Endpoints (`/api/terms`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Searchable, filterable term catalog |
| GET | `/taxonomy` | Categories with counts and subcategories |
| GET | `/{term_id}` | Full term detail |
| GET | `/{term_id}/similar` | Semantic neighbors (pgvector cosine) |
| GET | `/{term_id}/related` | Related queries from Google Trends |
| GET | `/{term_id}/questions` | People Also Ask questions |
| GET | `/discovered/all` | Auto-discovered terms from pipeline |

### 10.3 Trend Endpoints (`/api/trends`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/term/{term_id}` | Time-series for single term |
| GET | `/cluster/{cluster_id}` | Aggregated cluster trends |
| GET | `/top` | Highest interest terms |
| GET | `/comparison` | Side-by-side term comparison |
| GET | `/vulnerability/{term_id}` | Hourly anxiety pattern |
| GET | `/vulnerability/top-anxious` | Most night-searched terms |

### 10.4 Geography Endpoints (`/api/geography`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/regions` | All US states (filterable by level) |
| GET | `/regions/{geo_code}` | Region detail with SDOH |
| GET | `/heatmap` | Interest + vulnerability for map |
| GET | `/sdoh-summary` | SVI statistics and high-vulnerability regions |

### 10.5 Insight Endpoints (`/api/insights`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Detected anomalies sorted by severity |
| GET | `/summary` | Counts by type/severity |
| GET | `/term/{term_id}` | Anomalies for specific term |
| GET | `/cluster/{cluster_id}` | Anomalies in cluster |

### 10.6 Question Endpoints (`/api/questions`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/top` | Most frequent questions across all terms |
| GET | `/search?q=...` | Full-text search across all questions |
| GET | `/stats` | Coverage statistics |

### 10.7 Triangulation Endpoints (`/api/triangulate`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/term/{term_id}` | Multi-source evidence for a term |
| GET | `/search` | Search any query across sources |
| GET | `/clinical-trials` | ClinicalTrials.gov direct search |
| GET | `/pubmed` | PubMed direct search |
| GET | `/fda` | FDA openFDA |
| GET | `/news` | Google News |
| GET | `/scholar` | Google Scholar with citation counts |
| GET | `/patents` | Google Patents |
| GET | `/sources` | List all data sources |

### 10.8 Compare Endpoints (`/api/compare`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sources` | Available geo/timeframe combinations |
| GET | `/regions` | Single term across multiple countries |
| GET | `/top-terms` | Top N terms per region |
| GET | `/category-comparison` | Category averages by region |

### 10.9 Chat Endpoints (`/api/chat`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/` | Conversational AI (gpt-4o-mini + database context) |
| GET | `/suggestions` | Starter questions |

### 10.10 Story Builder Endpoints (`/api/stories`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List/filter stories (?sprint_id, ?status, ?priority, ?assigned_to, ?search) |
| POST | `/` | Create story (saves to backlog) |
| GET | `/{id}` | Get single story |
| PATCH | `/{id}` | Update story fields |
| PATCH | `/{id}/status` | Move story status (with transition validation) |
| DELETE | `/{id}` | Archive a story (soft delete) |
| GET | `/board` | Stories grouped by status column for Kanban board |
| GET | `/context` | Existing epics, sprints, features, assignees from DB |
| POST | `/assist` | LLM story writing assistance (steps: idea, story, criteria, refine) |
| GET | `/sprints` | List all sprints |
| POST | `/sprints` | Create sprint |
| PATCH | `/sprints/{id}` | Update sprint |

### 10.11 Cluster Comparison Endpoint (`/api/clusters/compare`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/compare` | Compare two clusters — returns proximity metrics + AI-generated explanation |

**Request body:** `{ cluster_a_id: int, cluster_b_id: int }`

**Response:** `cluster_a` & `cluster_b` summaries (id, name, term_count, avg_search_volume, top_categories, top_terms), `metrics` (proximity_index 0-100, spatial_proximity 0-100, euclidean_distance_3d, shared_categories, shared_subcategories), `explanation` (AI narrative or template fallback), `fallback` (bool).

**Proximity Index** (0-100): cosine similarity of `centroid_embedding` vectors via pgvector `<=>`. Falls back to numpy when embeddings are null. Returns `(score, is_estimated)` — when no embeddings exist, `is_estimated=True` and the LLM prompt instructs the model to rely on spatial proximity instead.

**Spatial Proximity** (0-100): Euclidean distance of centroid_x/y/z normalized against ~24.2-unit bounding cube diagonal.

**LLM:** gpt-4o-mini, temp 0.6, max_tokens 400. When proximity index is estimated, the system prompt tells the LLM to use spatial proximity as primary closeness indicator. Fallback template also uses spatial proximity when estimated.

### 10.12 Pipeline Endpoints (`/api/pipeline`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/runs` | Pipeline execution history |
| GET | `/runs/{run_id}` | Specific run status |
| POST | `/run` | Trigger full pipeline (background) |
| GET | `/stats` | Current data volume |

---

## 11. LLM Integration

### 11.1 Models Used

| Context | Model | Purpose |
|---------|-------|---------|
| Embeddings | text-embedding-3-small | 1536-dim semantic vectors for terms and posts |
| Chat | gpt-4o-mini | Conversational AI with database context |
| Story Builder | gpt-4o-mini | User story generation, acceptance criteria, sizing |
| Cluster Compare | gpt-4o-mini | Narrative explanation of cluster pair proximity (temp 0.6, max 400 tokens) |

### 11.2 Chat Configuration

- Temperature: 0.7
- Max tokens: 1000
- Conversation history: last 10 messages
- System prompt: domain-specific oncology/rare disease context
- Data injection: real-time database summary (terms, clusters, trends, regions, spikes)

### 11.3 Story Builder LLM

- Temperature: 0.7
- Max tokens: 800
- Response format: JSON object (structured output)
- 4 prompt templates: idea extraction, story refinement, criteria generation, review
- Fallback: static templates when OpenAI unavailable

---

## 12. Security & Data Protection

### 12.1 Authentication

- Frontend: cookie-based password auth via Next.js middleware
- Backend: CORS restricted to configured origins, chat rate-limited (20 req/min per IP)
- Google Sheets: GCP service account with scoped credentials
- No individual user data stored; no PII processing

### 12.2 Data Classification

- **Public data**: Google Trends (aggregated search behavior), CDC SVI (government data), PubMed/ClinicalTrials (public databases)
- **Proprietary data**: Taxonomy curation, clustering output, anomaly detection logic, vulnerability-adjusted scoring formula
- **Sensitive credentials**: API keys (OpenAI, SerpAPI), database URL, GCP service account key

### 12.3 What VIOLET Does NOT Store

- Individual search queries from real users
- Patient data, medical records, or PHI
- IP addresses or user tracking data
- Raw Google Trends data (only aggregated interest scores)

### 12.4 Credential Management

All secrets stored as environment variables on Railway. Never committed to git. Service account key base64-encoded for cloud deployment.

---

## 13. Infrastructure & Deployment

### 13.1 Railway Configuration

| Setting | Frontend | Backend |
|---------|----------|---------|
| Build | Dockerfile (node:20-alpine, multi-stage) | Dockerfile |
| Port | 3000 | 8000 |
| Output | Next.js standalone | Uvicorn |
| Custom Domain | violet.supertruth.ai | (internal) |

### 13.2 Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| DATABASE_URL | PostgreSQL connection (Neon, sslmode=require) | Yes |
| OPENAI_API_KEY | Embeddings + chat + Story Builder assist | Yes |
| SERPAPI_KEY | Google Trends and related engines | Yes |
| BASIC_AUTH_PASSWORD | Frontend login password | Yes (prod) |
| NEXT_PUBLIC_API_URL | Backend URL for frontend | Yes |
| GOOGLE_SERVICE_ACCOUNT_JSON_B64 | Base64 GCP service account key (import script only) | No |
| GOOGLE_SHEET_ID | Sprint management spreadsheet ID (import script only) | No |
| ENVIRONMENT | "development" or "production" | No |
| LOG_LEVEL | Default "INFO" | No |
| AZURE_STORAGE_CONNECTION_STRING | Cloud blob storage | No |

### 13.3 Database (Neon)

PostgreSQL with pgvector extension on Neon serverless. IVFFlat index on embedding columns for fast cosine similarity queries. Auto-seed taxonomy on startup.

---

## 14. UI/UX Specification

### 14.1 Design System

**Typography:**

| Usage | Font | Style |
|-------|------|-------|
| Body | system-ui, -apple-system, BlinkMacSystemFont | Regular 14px |
| Headers | system-ui | Semibold 18-24px |
| Labels | system-ui | Uppercase, tracking-wider, 10-11px |
| Monospace | font-mono | Step indicators, data values |

**Color Palette:**

| Token | Hex | Usage |
|-------|-----|-------|
| Background | #0a0a0f | Page background |
| Surface | #12121a | Panels, cards |
| Border | #1e1e2e | Dividers, outlines |
| Primary | #6366f1 | Buttons, active states (Indigo) |
| Secondary | #ec4899 | Accents, highlights (Pink) |
| Tertiary | #a855f7 | Cluster orbs, gradients (Purple) |
| Accent | #fbbf24 | Selected items (Gold) |
| 3D Cyan | #00d4ff | Data point start gradient |
| 3D Pink | #ff6b9d | Data point end gradient |
| SuperTruth Teal | #0d9488 | Logo, brand color |

**Component Patterns:**
- Glass morphism: `bg-rgba(12,12,20,0.8) backdrop-blur-12px border-rgba(255,255,255,0.1)`
- Glow effects: `box-shadow 0 0 20px rgba(color, 0.3)`
- Transitions: 150-300ms ease-out
- Border radius: 12px (cards), 8px (inputs), full (badges)

### 14.2 Layout

**Main Dashboard:** Three-column layout
- Left sidebar (w-72): FilterPanel, InsightsPanel tabs
- Center (flex-1): Three.js 3D Canvas with control bar
- Right sidebar (w-96): DetailPanel, VulnerabilityPanel tabs

**Story Builder Wizard:** Single-column centered (max-w-3xl), 4-step wizard with particle background

**Story Board:** Full-width 5-column Kanban grid (max-w-[1600px]), sticky header, right-slide detail drawer

**Login:** Centered card with SuperTruth branding and legal disclaimer

### 14.3 Category Colors (25 mapped)

pediatric_oncology → blue-500, adult_oncology → indigo-500, rare_genetic → purple-500, rare_neurological → pink-500, clinical_trials → cyan-500, treatment → green-500, symptoms → yellow-500, diagnosis → orange-500, support → teal-500, survivorship → emerald-500, caregiver → rose-500, costs → amber-500, emerging → violet-500, integrative → lime-500, prevention → sky-500

---

## 15. Key Design Decisions

1. **SerpAPI over pytrends** — pytrends was unreliable and rate-limited. SerpAPI provides structured JSON with consistent rate limits across Trends, PAA, Autocomplete, Scholar, News, and Patents.

2. **Separate QuestionSurface vs RelatedQuery** — Questions (snippets, URLs, titles) have fundamentally different shape than related queries (growth percentages, topic types). Separate models keep the data clean.

3. **UMAP + HDBSCAN** — UMAP preserves both local and global structure better than t-SNE for 3D. HDBSCAN handles noise gracefully and doesn't require specifying cluster count.

4. **pgvector for semantic search** — Cosine similarity queries directly in PostgreSQL without a separate vector database. IVFFlat index keeps queries fast.

5. **Batch commits every 10 terms** — Prevents massive transaction rollbacks if pipeline fails mid-run.

6. **Clear-on-rerun** — Pipeline deletes old data before inserting to avoid duplicates without complex upsert logic.

7. **Auto taxonomy expansion** — Related queries with ≥200% growth auto-promoted to SearchTerms. Capped at 50/run to prevent taxonomy explosion.

8. **Demo mode fallback** — Every endpoint generates realistic synthetic data for demos without API keys.

9. **Auto-seed on startup** — `database.py` seeds all taxonomy terms with deterministic 3D coordinates on startup. Deploying with new terms makes them appear automatically.

10. **Database as sprint source of truth** — Sprint and story data lives in PostgreSQL alongside all other VIOLET data. Stories follow a lifecycle: backlog → ready → in_progress → review → done → archived. The Kanban board provides a visual management interface. Historical data was migrated from Google Sheets.

11. **Base64 credentials for cloud** — OpenAI and SerpAPI keys stored as env vars on Railway. No credential files in production.

---

## 16. How to Brief Claude on VIOLET

When starting a new session, provide this context:

> Read the file VIOLET_SPEC.md in the oncology-intelligence repository root. This is the comprehensive product and technical specification for the VIOLET platform — SuperTruth Inc.'s oncology intelligence tool. It covers product vision, architecture, data models, pipeline steps, API endpoints, frontend components, UI/UX spec, security, deployment, and design decisions. After reading it, you'll be fully briefed on what VIOLET is and how it works.

Or simply: "Read VIOLET_SPEC.md in the repo root and get briefed."
