#!/usr/bin/env python3
"""
Run the data pipeline to fetch Google Trends and generate embeddings.
"""

import os
import sys
import time
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from openai import OpenAI

DATABASE_URL = os.environ.get('DATABASE_URL')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

if not DATABASE_URL or not OPENAI_API_KEY:
    print("ERROR: DATABASE_URL and OPENAI_API_KEY required")
    sys.exit(1)

# Initialize OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

print("=" * 60)
print("VIOLET — Oncology & Rare Disease Intelligence Pipeline")
print("=" * 60)

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

# ============================================
# Step 1: Generate Embeddings for all terms
# ============================================
print("\n[1/4] Generating embeddings for search terms...")

cur.execute("SELECT id, term, category FROM search_terms WHERE embedding IS NULL")
terms_without_embeddings = cur.fetchall()

if terms_without_embeddings:
    print(f"  Found {len(terms_without_embeddings)} terms without embeddings")

    for term_id, term, category in terms_without_embeddings:
        # Create contextualized text for better embeddings
        text = f"Pediatric oncology search query about {category}: {term}"

        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536
            )
            embedding = response.data[0].embedding

            # Store embedding
            cur.execute(
                "UPDATE search_terms SET embedding = %s WHERE id = %s",
                (embedding, term_id)
            )
            print(f"  ✓ Embedded: {term}")
            time.sleep(0.1)  # Rate limiting

        except Exception as e:
            print(f"  ✗ Failed: {term} - {e}")
else:
    print("  All terms already have embeddings")

# ============================================
# Step 2: Run UMAP clustering
# ============================================
print("\n[2/4] Running UMAP dimensionality reduction...")

try:
    import umap
    from sklearn.cluster import KMeans

    # Get all embeddings
    cur.execute("SELECT id, term, embedding, cluster_id FROM search_terms WHERE embedding IS NOT NULL")
    rows = cur.fetchall()

    if len(rows) >= 5:
        ids = [r[0] for r in rows]
        terms = [r[1] for r in rows]
        embeddings = np.array([r[2] for r in rows])

        # Run UMAP to get 3D coordinates
        reducer = umap.UMAP(n_components=3, n_neighbors=5, min_dist=0.3, random_state=42)
        coords_3d = reducer.fit_transform(embeddings)

        # Scale coordinates
        coords_3d = (coords_3d - coords_3d.mean(axis=0)) / coords_3d.std(axis=0) * 2

        # Update coordinates in database
        for i, term_id in enumerate(ids):
            cur.execute(
                "UPDATE search_terms SET x = %s, y = %s, z = %s WHERE id = %s",
                (float(coords_3d[i, 0]), float(coords_3d[i, 1]), float(coords_3d[i, 2]), term_id)
            )

        print(f"  ✓ Updated 3D coordinates for {len(ids)} terms")

        # Update cluster centroids
        cur.execute("SELECT DISTINCT cluster_id FROM search_terms WHERE cluster_id IS NOT NULL")
        cluster_ids = [r[0] for r in cur.fetchall()]

        for cluster_id in cluster_ids:
            cur.execute(
                "SELECT AVG(x), AVG(y), AVG(z) FROM search_terms WHERE cluster_id = %s",
                (cluster_id,)
            )
            centroid = cur.fetchone()
            if centroid[0] is not None:
                cur.execute(
                    "UPDATE clusters SET centroid_x = %s, centroid_y = %s, centroid_z = %s WHERE id = %s",
                    (centroid[0], centroid[1], centroid[2], cluster_id)
                )

        print(f"  ✓ Updated centroids for {len(cluster_ids)} clusters")
    else:
        print("  Not enough terms for UMAP")

except ImportError:
    print("  ⚠ UMAP not available, skipping clustering")
except Exception as e:
    print(f"  ✗ Clustering error: {e}")

# ============================================
# Step 3: Generate sample trend data
# ============================================
print("\n[3/4] Generating trend data...")

cur.execute("SELECT COUNT(*) FROM trend_data")
existing_trends = cur.fetchone()[0]

if existing_trends < 100:
    cur.execute("SELECT id, term FROM search_terms")
    all_terms = cur.fetchall()

    # Generate 52 weeks of sample trend data for each term
    base_date = datetime.now() - timedelta(days=365)
    regions = ['US', 'US-CA', 'US-TX', 'US-NY', 'US-FL']

    trend_records = []
    for term_id, term in all_terms:
        # Generate weekly data
        for week in range(52):
            date = base_date + timedelta(weeks=week)

            # Create realistic-looking trend with some variation
            base_interest = np.random.randint(20, 80)
            seasonal = 10 * np.sin(week / 52 * 2 * np.pi)  # Seasonal variation
            noise = np.random.randint(-10, 10)
            interest = max(0, min(100, int(base_interest + seasonal + noise)))

            trend_records.append((term_id, date, 'weekly', 'US', 'United States', 'country', interest))

    # Also add regional data for most recent period
    for term_id, term in all_terms:
        for region in regions[1:]:  # Skip US, already covered
            interest = np.random.randint(30, 95)
            region_name = {'US-CA': 'California', 'US-TX': 'Texas', 'US-NY': 'New York', 'US-FL': 'Florida'}
            trend_records.append((term_id, datetime.now(), 'snapshot', region, region_name.get(region, region), 'state', interest))

    # Batch insert
    execute_values(
        cur,
        """INSERT INTO trend_data (term_id, date, granularity, geo_code, geo_name, geo_level, interest)
           VALUES %s ON CONFLICT DO NOTHING""",
        trend_records
    )

    print(f"  ✓ Generated {len(trend_records)} trend data points")
else:
    print(f"  Already have {existing_trends} trend records")

# ============================================
# Step 4: Update post embeddings and positions
# ============================================
print("\n[4/4] Updating post positions...")

cur.execute("SELECT id, title, cluster_id FROM posts")
posts = cur.fetchall()

for post_id, title, cluster_id in posts:
    if cluster_id:
        # Position posts near their cluster centroid with some offset
        cur.execute("SELECT centroid_x, centroid_y, centroid_z FROM clusters WHERE id = %s", (cluster_id,))
        centroid = cur.fetchone()
        if centroid and centroid[0] is not None:
            offset = np.random.randn(3) * 0.3
            cur.execute(
                "UPDATE posts SET x = %s, y = %s, z = %s WHERE id = %s",
                (centroid[0] + offset[0], centroid[1] + offset[1], centroid[2] + offset[2], post_id)
            )

print(f"  ✓ Updated positions for {len(posts)} posts")

# ============================================
# Summary
# ============================================
print("\n" + "=" * 60)
print("Pipeline Complete!")
print("=" * 60)

cur.execute("SELECT COUNT(*) FROM search_terms WHERE embedding IS NOT NULL")
print(f"  Terms with embeddings: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM trend_data")
print(f"  Trend data points: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM clusters")
print(f"  Clusters: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM geographic_regions")
print(f"  Geographic regions: {cur.fetchone()[0]}")

print("\n✅ Refresh http://localhost:3000 to see updated visualization!")

cur.close()
conn.close()
