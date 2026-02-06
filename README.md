# Oncology & Rare Disease Intelligence

A visual analytics platform for exploring oncology and rare disease search trends with external data triangulation from ClinicalTrials.gov, PubMed, FDA, and news sources.

![Dashboard Preview](docs/preview.png)

## Features

- **3D Semantic Clustering**: Navigate search terms in 3D space, clustered by semantic similarity using OpenAI embeddings + UMAP
- **Google Trends Integration**: Pulls interest-over-time and geographic interest data via SerpAPI
- **SDOH Overlay**: CDC Social Vulnerability Index data at state/county level for health equity analysis
- **Interactive Dashboard**: Filter by category, geography, and time; drill into cluster details
- **Content Mapping**: Associate curated resources, PubMed articles, or your own content with search clusters

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           GITHUB                                     │
│                    (repo + CI/CD actions)                           │
└─────────────────────────────────────────────────────────────────────┘
                                 │
           ┌─────────────────────┴─────────────────────┐
           ▼                                           ▼
┌─────────────────────────┐              ┌─────────────────────────────┐
│       RAILWAY           │              │          AZURE              │
│  ┌───────────────────┐  │              │  ┌─────────────────────┐   │
│  │ Next.js Frontend  │  │              │  │ Blob Storage        │   │
│  │ (dashboard + 3D)  │  │              │  │ (SDOH data, exports)│   │
│  └───────────────────┘  │              │  └─────────────────────┘   │
│  ┌───────────────────┐  │              │                            │
│  │ FastAPI Backend   │  │              │                            │
│  │ (API + pipeline)  │  │              │                            │
│  └───────────────────┘  │              │                            │
└───────────┬─────────────┘              └─────────────────────────────┘
            │
            ▼
┌─────────────────────────┐              ┌─────────────────────────────┐
│         NEON            │              │         OPENAI              │
│  Postgres + pgvector    │              │  text-embedding-3-small     │
│  (terms, clusters, geo) │              │  (semantic embeddings)      │
└─────────────────────────┘              └─────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL with pgvector (or Neon account)
- OpenAI API key

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/pediatric-oncology-intelligence.git
cd pediatric-oncology-intelligence

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### 2. Setup Database (Neon)

1. Create a new project at [neon.tech](https://neon.tech)
2. Enable the pgvector extension:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
3. Copy the connection string to your `.env` file

### 3. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e .

# Initialize database
python -c "from app.database import init_db; init_db()"

# Seed with sample data (for demo)
python ../scripts/seed_database.py

# Run the API
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### 4. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set API URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev
```

The dashboard will be available at `http://localhost:3000`

## Running the Full Pipeline

To fetch real Google Trends data and generate embeddings:

```bash
cd backend
source .venv/bin/activate

# Run pipeline (this takes a while due to rate limiting)
python -c "
from app.database import SessionLocal
from pipeline.orchestrator import run_pipeline
import asyncio

db = SessionLocal()
asyncio.run(run_pipeline(db, fetch_trends=True))
"
```

Or trigger via API:

```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"fetch_trends": true, "timeframe": "today 12-m", "geo": "US"}'
```

## Deployment

### Railway

1. Install Railway CLI: `npm install -g @railway/cli`
2. Login: `railway login`
3. Create project: `railway init`
4. Add services:
   ```bash
   # Backend
   cd backend && railway up --service backend

   # Frontend
   cd frontend && railway up --service frontend
   ```
5. Set environment variables in Railway dashboard

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API key for embeddings |
| `SERPAPI_KEY` | SerpAPI key for Google Trends data |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure blob storage (optional) |
| `NEXT_PUBLIC_API_URL` | Backend API URL for frontend |

## API Reference

### Clusters

- `GET /api/clusters/` - List all clusters
- `GET /api/clusters/visualization` - Get 3D visualization data
- `GET /api/clusters/{id}` - Get cluster details

### Terms

- `GET /api/terms/` - List search terms
- `GET /api/terms/taxonomy` - Get taxonomy structure
- `GET /api/terms/{id}/similar` - Find similar terms

### Trends

- `GET /api/trends/term/{id}` - Get trend data for a term
- `GET /api/trends/cluster/{id}` - Get aggregated cluster trends
- `GET /api/trends/top` - Get top trending terms

### Geography

- `GET /api/geography/regions` - List regions with SDOH
- `GET /api/geography/heatmap` - Get geographic heatmap data

### Pipeline

- `POST /api/pipeline/run` - Trigger pipeline execution
- `GET /api/pipeline/stats` - Get data statistics

## Data Sources

- **Google Trends**: Via SerpAPI (reliable, structured API)
- **SDOH**: CDC Social Vulnerability Index (SVI)
- **Embeddings**: OpenAI text-embedding-3-small

## Project Structure

```
pediatric-oncology-intelligence/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── database.py       # Database connection
│   │   └── routes/           # API route handlers
│   ├── pipeline/
│   │   ├── taxonomy.py       # Search term definitions
│   │   ├── trends_fetcher.py # Google Trends integration
│   │   ├── embeddings.py     # OpenAI embedding generation
│   │   ├── clustering.py     # UMAP + HDBSCAN clustering
│   │   ├── sdoh_loader.py    # CDC SVI data loader
│   │   └── orchestrator.py   # Pipeline coordination
│   └── data/
│       └── sample_data.json  # Demo data
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Main dashboard
│   │   └── layout.tsx        # App layout
│   ├── components/
│   │   ├── ClusterVisualization.tsx  # 3D viz
│   │   ├── FilterPanel.tsx   # Filters sidebar
│   │   └── DetailPanel.tsx   # Selection details
│   └── lib/
│       ├── api.ts            # API client
│       └── store.ts          # State management
├── scripts/
│   └── seed_database.py      # Database seeding
└── .github/
    └── workflows/
        └── deploy.yml        # CI/CD pipeline
```

## License

MIT

## Acknowledgments

- CDC for Social Vulnerability Index data
- Google Trends for search interest data
- OpenAI for embedding models
