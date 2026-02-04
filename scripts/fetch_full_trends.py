#!/usr/bin/env python3
"""
Comprehensive Google Trends data fetcher.

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
from pytrends.request import TrendReq
from openai import OpenAI

DATABASE_URL = os.environ.get('DATABASE_URL')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

print("=" * 70)
print("Pediatric Oncology Intelligence - Full Google Trends Fetch")
print("=" * 70)

# Initialize
pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=3, backoff_factor=1.5)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

# Rate limiting
REQUEST_DELAY = 3  # seconds between requests

def safe_request(func, *args, **kwargs):
    """Execute a pytrends request with rate limiting and error handling."""
    time.sleep(REQUEST_DELAY)
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"  ⚠ Request failed: {e}")
        time.sleep(10)  # Extra delay on error
        return None

# ============================================
# Step 1: Get all existing terms
# ============================================
print("\n[1/6] Loading existing terms...")
cur.execute("SELECT id, term, category, subcategory FROM search_terms")
existing_terms = {row[1]: {"id": row[0], "category": row[1], "subcategory": row[3]} for row in cur.fetchall()}
print(f"  Found {len(existing_terms)} existing terms")

# ============================================
# Step 2: Fetch interest over time for all terms
# ============================================
print("\n[2/6] Fetching interest over time...")

term_list = list(existing_terms.keys())
trend_records = []

# Process in batches of 5 (Google Trends limit)
for i in range(0, len(term_list), 5):
    batch = term_list[i:i+5]
    print(f"  Batch {i//5 + 1}/{(len(term_list)+4)//5}: {batch[:2]}...")

    try:
        pytrends.build_payload(batch, cat=0, timeframe='today 12-m', geo='US')
        time.sleep(REQUEST_DELAY)

        # Interest over time
        iot = pytrends.interest_over_time()
        if iot is not None and not iot.empty:
            iot = iot.drop(columns=['isPartial'], errors='ignore')

            for term in batch:
                if term in iot.columns:
                    term_id = existing_terms[term]["id"]
                    for date, row in iot.iterrows():
                        trend_records.append((
                            term_id,
                            date.to_pydatetime(),
                            'weekly',
                            'US',
                            'United States',
                            'country',
                            int(row[term])
                        ))

        time.sleep(REQUEST_DELAY)

        # Interest by region
        ibr = safe_request(pytrends.interest_by_region, resolution='REGION', inc_low_vol=True, inc_geo_code=True)
        if ibr is not None and not ibr.empty:
            ibr = ibr.reset_index()
            for term in batch:
                if term in ibr.columns:
                    term_id = existing_terms[term]["id"]
                    for _, row in ibr.iterrows():
                        geo_code = f"US-{row.get('geoCode', '')}"
                        geo_name = row.get('geoName', str(row.name) if hasattr(row, 'name') else '')
                        interest = int(row[term]) if row[term] > 0 else 0
                        if interest > 0:
                            trend_records.append((
                                term_id,
                                datetime.utcnow(),
                                'snapshot',
                                geo_code,
                                geo_name,
                                'state',
                                interest
                            ))

    except Exception as e:
        print(f"  ✗ Error processing batch: {e}")
        time.sleep(10)

print(f"  Collected {len(trend_records)} trend records")

# ============================================
# Step 3: Fetch related queries & topics
# ============================================
print("\n[3/6] Fetching related queries and topics...")

new_terms = []
related_data = []

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
        pytrends.build_payload([seed], cat=0, timeframe='today 12-m', geo='US')
        time.sleep(REQUEST_DELAY)

        # Related queries
        related = safe_request(pytrends.related_queries)
        if related and seed in related:
            for query_type in ['top', 'rising']:
                df = related[seed].get(query_type)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        query = row.get('query', '')
                        value = row.get('value', 0)

                        # Add as potential new term if relevant
                        if query and query.lower() not in [t.lower() for t in existing_terms]:
                            # Check if it's pediatric/cancer related
                            keywords = ['child', 'pediatric', 'cancer', 'tumor', 'leukemia', 'oncology', 'kid']
                            if any(kw in query.lower() for kw in keywords):
                                new_terms.append({
                                    "term": query,
                                    "source": seed,
                                    "type": query_type,
                                    "value": value
                                })

        # Related topics
        topics = safe_request(pytrends.related_topics)
        if topics and seed in topics:
            for topic_type in ['top', 'rising']:
                df = topics[seed].get(topic_type)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        title = row.get('topic_title', '')
                        if title and title.lower() not in [t.lower() for t in existing_terms]:
                            keywords = ['child', 'pediatric', 'cancer', 'tumor', 'leukemia', 'oncology']
                            if any(kw in title.lower() for kw in keywords):
                                new_terms.append({
                                    "term": title,
                                    "source": seed,
                                    "type": f"topic_{topic_type}",
                                    "value": row.get('value', 0)
                                })

    except Exception as e:
        print(f"  ✗ Error: {e}")
        time.sleep(10)

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
        print(f"  ✗ Failed to add {term}: {e}")

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
    print(f"  ✓ Inserted {len(trend_records)} trend records")

# ============================================
# Step 6: Generate embeddings for new terms
# ============================================
print("\n[6/6] Generating embeddings for new terms...")

cur.execute("SELECT id, term, category FROM search_terms WHERE embedding IS NULL")
terms_needing_embeddings = cur.fetchall()

for term_id, term, category in terms_needing_embeddings:
    try:
        text = f"Pediatric oncology search query about {category}: {term}"
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
        print(f"  ✓ Embedded: {term}")
        time.sleep(0.1)

    except Exception as e:
        print(f"  ✗ Failed: {term} - {e}")

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

        print(f"  ✓ Updated coordinates for {len(ids)} terms")

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
    print(f"  ⚠ UMAP failed: {e}")

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

print("\n✅ Refresh http://localhost:3000 to see updated data!")

cur.close()
conn.close()
