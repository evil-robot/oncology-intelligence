#!/usr/bin/env python3
"""
Comprehensive Google Trends data fetcher using SerpAPI.

Pulls:
- Interest over time (weekly for past year)
- Interest by region (all US states)
- Related queries (top & rising)
- Related topics
- Expands taxonomy with discovered terms
"""

import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from serpapi import GoogleSearch
from openai import OpenAI

DATABASE_URL = os.environ.get('DATABASE_URL')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
SERPAPI_KEY = os.environ.get('SERPAPI_KEY')

if not SERPAPI_KEY:
    print("ERROR: SERPAPI_KEY environment variable is required")
    sys.exit(1)

print("=" * 70)
print("Oncology & Rare Disease Intelligence - Full Google Trends Fetch (SerpAPI)")
print("=" * 70)

# Initialize
openai_client = OpenAI(api_key=OPENAI_API_KEY)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

# Rate limiting (SerpAPI is more forgiving than pytrends)
REQUEST_DELAY = 0.5  # seconds between requests


def serpapi_search(params: dict) -> dict:
    """Execute a SerpAPI Google Trends search."""
    params["api_key"] = SERPAPI_KEY
    params["engine"] = "google_trends"
    search = GoogleSearch(params)
    return search.get_dict()


def safe_request(func, *args, **kwargs):
    """Execute a request with rate limiting and error handling."""
    time.sleep(REQUEST_DELAY)
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"  Warning: Request failed: {e}")
        time.sleep(5)  # Extra delay on error
        return None


# ============================================
# Step 1: Get all existing terms
# ============================================
print("\n[1/6] Loading existing terms...")
cur.execute("SELECT id, term, category, subcategory FROM search_terms")
existing_terms = {row[1]: {"id": row[0], "category": row[2], "subcategory": row[3]} for row in cur.fetchall()}
print(f"  Found {len(existing_terms)} existing terms")

# ============================================
# Step 2: Fetch interest over time for all terms
# ============================================
print("\n[2/6] Fetching interest over time...")

term_list = list(existing_terms.keys())
trend_records = []

# SerpAPI supports up to 5 comma-separated queries for TIMESERIES
for i in range(0, len(term_list), 5):
    batch = term_list[i:i+5]
    print(f"  Batch {i//5 + 1}/{(len(term_list)+4)//5}: {batch[:2]}...")

    try:
        # Interest over time (TIMESERIES supports multiple queries)
        params = {
            "q": ",".join(batch),
            "date": "today 12-m",
            "geo": "US",
            "data_type": "TIMESERIES",
        }
        results = safe_request(serpapi_search, params)

        if results:
            iot_data = results.get("interest_over_time", {})
            timeline = iot_data.get("timeline_data", [])

            for point in timeline:
                timestamp = point.get("timestamp")
                if not timestamp:
                    continue
                dt = datetime.fromtimestamp(int(timestamp))

                for val in point.get("values", []):
                    query = val.get("query", "")
                    interest = val.get("extracted_value", 0)

                    if query in existing_terms:
                        term_id = existing_terms[query]["id"]
                        trend_records.append((
                            term_id,
                            dt,
                            'weekly',
                            'US',
                            'United States',
                            'country',
                            int(interest)
                        ))

        # Interest by region (GEO_MAP_0 only supports single query)
        for term in batch:
            params = {
                "q": term,
                "date": "today 12-m",
                "geo": "US",
                "data_type": "GEO_MAP_0",
            }
            ibr_results = safe_request(serpapi_search, params)

            if ibr_results:
                regions = ibr_results.get("interest_by_region", [])
                term_id = existing_terms[term]["id"]

                for region in regions:
                    geo_code = region.get("geo", "")
                    location = region.get("location", "")
                    interest = region.get("extracted_value", 0)

                    if interest > 0 and geo_code:
                        trend_records.append((
                            term_id,
                            datetime.utcnow(),
                            'snapshot',
                            geo_code,
                            location,
                            'state',
                            int(interest)
                        ))

    except Exception as e:
        print(f"  Error processing batch: {e}")
        time.sleep(5)

print(f"  Collected {len(trend_records)} trend records")

# ============================================
# Step 3: Fetch related queries & topics
# ============================================
print("\n[3/6] Fetching related queries and topics...")

new_terms = []

# Key seed terms for discovery
seed_terms = [
    "pediatric oncology",
    "childhood cancer",
    "childhood leukemia",
    "pediatric brain tumor",
    "neuroblastoma",
    "childhood cancer treatment",
    "pediatric cancer clinical trials",
]

for seed in seed_terms:
    print(f"  Expanding: {seed}")

    try:
        # Related queries
        params = {
            "q": seed,
            "date": "today 12-m",
            "geo": "US",
            "data_type": "RELATED_QUERIES",
        }
        results = safe_request(serpapi_search, params)

        if results:
            related = results.get("related_queries", {})
            for query_type in ['rising', 'top']:
                queries = related.get(query_type, [])
                for item in queries:
                    query = item.get("query", "")
                    value = item.get("extracted_value", item.get("value", 0))

                    if query and query.lower() not in [t.lower() for t in existing_terms]:
                        keywords = ['child', 'pediatric', 'cancer', 'tumor', 'leukemia', 'oncology', 'kid']
                        if any(kw in query.lower() for kw in keywords):
                            new_terms.append({
                                "term": query,
                                "source": seed,
                                "type": query_type,
                                "value": value if isinstance(value, (int, float)) else 0
                            })

        # Related topics
        params["data_type"] = "RELATED_TOPICS"
        results = safe_request(serpapi_search, params)

        if results:
            topics = results.get("related_topics", {})
            for topic_type in ['rising', 'top']:
                topic_list = topics.get(topic_type, [])
                for item in topic_list:
                    title = item.get("topic", {}).get("title", "")
                    if title and title.lower() not in [t.lower() for t in existing_terms]:
                        keywords = ['child', 'pediatric', 'cancer', 'tumor', 'leukemia', 'oncology']
                        if any(kw in title.lower() for kw in keywords):
                            new_terms.append({
                                "term": title,
                                "source": seed,
                                "type": f"topic_{topic_type}",
                                "value": item.get("extracted_value", item.get("value", 0))
                            })

    except Exception as e:
        print(f"  Error: {e}")
        time.sleep(5)

print(f"  Discovered {len(new_terms)} potential new terms")

# ============================================
# Step 4: Add new discovered terms
# ============================================
print("\n[4/6] Adding discovered terms to database...")

# Deduplicate and filter
seen = set(t.lower() for t in existing_terms)
unique_new = []
for t in new_terms:
    if t["term"].lower() not in seen:
        seen.add(t["term"].lower())
        unique_new.append(t)

# Limit to top 50 by value
unique_new = sorted(unique_new, key=lambda x: x.get("value", 0), reverse=True)[:50]

added_count = 0
for term_data in unique_new:
    term = term_data["term"]

    # Categorize using simple rules
    term_lower = term.lower()
    if any(w in term_lower for w in ['leukemia', 'all ', 'aml']):
        category, subcategory = 'diagnosis', 'leukemia'
    elif any(w in term_lower for w in ['brain', 'glioma', 'tumor']):
        category, subcategory = 'diagnosis', 'brain_tumor'
    elif any(w in term_lower for w in ['neuroblastoma', 'sarcoma', 'wilms']):
        category, subcategory = 'diagnosis', 'solid_tumor'
    elif any(w in term_lower for w in ['chemo', 'treatment', 'therapy', 'radiation']):
        category, subcategory = 'treatment', 'general'
    elif any(w in term_lower for w in ['support', 'help', 'resource']):
        category, subcategory = 'support', 'general'
    elif any(w in term_lower for w in ['survivor', 'long term', 'late effect']):
        category, subcategory = 'survivorship', 'general'
    elif any(w in term_lower for w in ['symptom', 'sign']):
        category, subcategory = 'symptoms', 'general'
    else:
        category, subcategory = 'diagnosis', 'general'

    try:
        cur.execute("""
            INSERT INTO search_terms (term, normalized_term, category, subcategory)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (term) DO NOTHING
            RETURNING id
        """, (term, term.lower(), category, subcategory))

        result = cur.fetchone()
        if result:
            existing_terms[term] = {"id": result[0], "category": category, "subcategory": subcategory}
            added_count += 1
            print(f"  + {term} ({category}/{subcategory})")

    except Exception as e:
        print(f"  Failed to add {term}: {e}")

print(f"  Added {added_count} new terms")

# ============================================
# Step 5: Insert trend data
# ============================================
print("\n[5/6] Saving trend data to database...")

if trend_records:
    # Clear old trend data
    cur.execute("DELETE FROM trend_data")

    execute_values(
        cur,
        """INSERT INTO trend_data (term_id, date, granularity, geo_code, geo_name, geo_level, interest)
           VALUES %s""",
        trend_records
    )
    print(f"  Inserted {len(trend_records)} trend records")

# ============================================
# Step 6: Generate embeddings for new terms
# ============================================
print("\n[6/6] Generating embeddings for new terms...")

cur.execute("SELECT id, term, category FROM search_terms WHERE embedding IS NULL")
terms_needing_embeddings = cur.fetchall()

for term_id, term, category in terms_needing_embeddings:
    try:
        text = f"Oncology and rare disease search query about {category}: {term}"
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=1536
        )
        embedding = response.data[0].embedding

        cur.execute(
            "UPDATE search_terms SET embedding = %s WHERE id = %s",
            (embedding, term_id)
        )
        print(f"  Embedded: {term}")
        time.sleep(0.1)

    except Exception as e:
        print(f"  Failed: {term} - {e}")

# ============================================
# Run UMAP clustering
# ============================================
print("\n[Bonus] Running UMAP clustering on all terms...")

try:
    import umap

    cur.execute("SELECT id, embedding FROM search_terms WHERE embedding IS NOT NULL")
    rows = cur.fetchall()

    if len(rows) >= 5:
        ids = [r[0] for r in rows]
        embeddings = np.array([r[1] for r in rows])

        reducer = umap.UMAP(n_components=3, n_neighbors=min(15, len(rows)-1), min_dist=0.1, random_state=42)
        coords_3d = reducer.fit_transform(embeddings)
        coords_3d = (coords_3d - coords_3d.mean(axis=0)) / (coords_3d.std(axis=0) + 0.001) * 3

        for i, term_id in enumerate(ids):
            cur.execute(
                "UPDATE search_terms SET x = %s, y = %s, z = %s WHERE id = %s",
                (float(coords_3d[i, 0]), float(coords_3d[i, 1]), float(coords_3d[i, 2]), term_id)
            )

        print(f"  Updated coordinates for {len(ids)} terms")

        # Update cluster centroids
        cur.execute("SELECT DISTINCT cluster_id FROM search_terms WHERE cluster_id IS NOT NULL")
        for (cluster_id,) in cur.fetchall():
            cur.execute(
                "SELECT AVG(x), AVG(y), AVG(z) FROM search_terms WHERE cluster_id = %s",
                (cluster_id,)
            )
            centroid = cur.fetchone()
            if centroid[0]:
                cur.execute(
                    "UPDATE clusters SET centroid_x=%s, centroid_y=%s, centroid_z=%s WHERE id=%s",
                    (centroid[0], centroid[1], centroid[2], cluster_id)
                )

except Exception as e:
    print(f"  UMAP failed: {e}")

# ============================================
# Summary
# ============================================
print("\n" + "=" * 70)
print("COMPLETE!")
print("=" * 70)

cur.execute("SELECT COUNT(*) FROM search_terms")
print(f"  Total terms: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM search_terms WHERE embedding IS NOT NULL")
print(f"  Terms with embeddings: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM trend_data")
print(f"  Trend data points: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(DISTINCT geo_code) FROM trend_data WHERE geo_level = 'state'")
print(f"  States with data: {cur.fetchone()[0]}")

print("\nRefresh http://localhost:3000 to see updated data!")

cur.close()
conn.close()
