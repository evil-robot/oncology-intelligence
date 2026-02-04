#!/usr/bin/env python3
"""Initialize database and seed with sample data."""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'backend', '.env'))

import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment")
    sys.exit(1)

print(f"Connecting to database...")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

print("Creating pgvector extension and tables...")

# Create extension and tables
cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

cur.execute("""
CREATE TABLE IF NOT EXISTS clusters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    centroid_x FLOAT,
    centroid_y FLOAT,
    centroid_z FLOAT,
    centroid_embedding vector(1536),
    color VARCHAR(7),
    size FLOAT DEFAULT 1.0,
    term_count INTEGER DEFAULT 0,
    avg_search_volume FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS search_terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(500) NOT NULL UNIQUE,
    normalized_term VARCHAR(500) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    parent_term_id INTEGER REFERENCES search_terms(id),
    embedding vector(1536),
    x FLOAT,
    y FLOAT,
    z FLOAT,
    cluster_id INTEGER REFERENCES clusters(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    url VARCHAR(2000),
    source VARCHAR(100),
    source_id VARCHAR(100),
    summary TEXT,
    content_type VARCHAR(50),
    embedding vector(1536),
    x FLOAT,
    y FLOAT,
    z FLOAT,
    cluster_id INTEGER REFERENCES clusters(id),
    published_at TIMESTAMP,
    relevance_score FLOAT,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS geographic_regions (
    id SERIAL PRIMARY KEY,
    geo_code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    level VARCHAR(20) NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    population INTEGER,
    svi_overall FLOAT,
    svi_socioeconomic FLOAT,
    svi_household_disability FLOAT,
    svi_minority_language FLOAT,
    svi_housing_transport FLOAT,
    median_income INTEGER,
    uninsured_rate FLOAT,
    pediatric_oncology_centers INTEGER,
    intent_intensity FLOAT,
    vulnerability_adjusted_intent FLOAT,
    updated_at TIMESTAMP DEFAULT NOW()
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS trend_data (
    id SERIAL PRIMARY KEY,
    term_id INTEGER NOT NULL REFERENCES search_terms(id),
    date TIMESTAMP NOT NULL,
    granularity VARCHAR(20) DEFAULT 'weekly',
    geo_code VARCHAR(10),
    geo_name VARCHAR(100),
    geo_level VARCHAR(20),
    interest INTEGER,
    interest_normalized FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',
    config JSONB
)
""")

print("✓ Tables created")

print("Seeding sample data...")

# Insert clusters
cur.execute("""
INSERT INTO clusters (id, name, centroid_x, centroid_y, centroid_z, color, size, term_count) VALUES
(1, 'Leukemia / ALL / AML', -2.5, 1.2, 0.8, '#6366f1', 1.4, 12),
(2, 'Brain Tumors / DIPG', 1.8, 2.1, -1.2, '#ec4899', 1.2, 10),
(3, 'Neuroblastoma / Solid Tumors', 2.2, -1.5, 1.5, '#14b8a6', 1.1, 9),
(4, 'Treatment / Chemotherapy', -1.0, -2.2, -0.5, '#f59e0b', 1.3, 11),
(5, 'Support / Resources', -3.0, -0.5, 2.0, '#8b5cf6', 1.0, 8),
(6, 'Survivorship / Late Effects', 0.5, 0.3, -2.5, '#22c55e', 0.9, 7)
ON CONFLICT (id) DO NOTHING
""")

# Insert search terms
terms = [
    (1, 'childhood leukemia', 'childhood leukemia', 'diagnosis', 'leukemia', -2.3, 1.0, 0.6, 1),
    (2, 'acute lymphoblastic leukemia children', 'acute lymphoblastic leukemia children', 'diagnosis', 'leukemia', -2.7, 1.4, 0.9, 1),
    (3, 'ALL in children', 'all in children', 'diagnosis', 'leukemia', -2.4, 1.1, 1.0, 1),
    (4, 'acute myeloid leukemia pediatric', 'acute myeloid leukemia pediatric', 'diagnosis', 'leukemia', -2.6, 1.3, 0.5, 1),
    (5, 'AML children', 'aml children', 'diagnosis', 'leukemia', -2.5, 1.5, 0.7, 1),
    (6, 'pediatric brain tumor', 'pediatric brain tumor', 'diagnosis', 'brain_tumor', 1.6, 2.0, -1.0, 2),
    (7, 'childhood brain cancer', 'childhood brain cancer', 'diagnosis', 'brain_tumor', 1.9, 2.2, -1.3, 2),
    (8, 'medulloblastoma', 'medulloblastoma', 'diagnosis', 'brain_tumor', 2.0, 2.3, -1.1, 2),
    (9, 'DIPG', 'dipg', 'diagnosis', 'brain_tumor', 1.7, 1.9, -1.4, 2),
    (10, 'diffuse intrinsic pontine glioma', 'diffuse intrinsic pontine glioma', 'diagnosis', 'brain_tumor', 1.8, 2.4, -1.2, 2),
    (11, 'neuroblastoma', 'neuroblastoma', 'diagnosis', 'solid_tumor', 2.0, -1.3, 1.4, 3),
    (12, 'wilms tumor', 'wilms tumor', 'diagnosis', 'solid_tumor', 2.3, -1.6, 1.6, 3),
    (13, 'rhabdomyosarcoma', 'rhabdomyosarcoma', 'diagnosis', 'solid_tumor', 2.4, -1.4, 1.3, 3),
    (14, 'osteosarcoma children', 'osteosarcoma children', 'diagnosis', 'solid_tumor', 2.1, -1.7, 1.7, 3),
    (15, 'pediatric chemotherapy', 'pediatric chemotherapy', 'treatment', 'chemotherapy', -0.8, -2.0, -0.4, 4),
    (16, 'chemo for kids', 'chemo for kids', 'treatment', 'chemotherapy', -1.1, -2.3, -0.6, 4),
    (17, 'pediatric radiation therapy', 'pediatric radiation therapy', 'treatment', 'radiation', -1.2, -2.1, -0.3, 4),
    (18, 'proton therapy children', 'proton therapy children', 'treatment', 'radiation', -0.9, -2.4, -0.7, 4),
    (19, 'bone marrow transplant children', 'bone marrow transplant children', 'treatment', 'transplant', -1.0, -2.0, -0.5, 4),
    (20, 'CAR-T therapy pediatric', 'car-t therapy pediatric', 'treatment', 'immunotherapy', -0.7, -2.5, -0.4, 4),
    (21, 'childhood cancer support groups', 'childhood cancer support groups', 'support', 'community', -2.8, -0.4, 1.9, 5),
    (22, 'pediatric oncology hospital', 'pediatric oncology hospital', 'support', 'facility', -3.1, -0.6, 2.1, 5),
    (23, 'childrens cancer center near me', 'childrens cancer center near me', 'support', 'facility', -3.2, -0.3, 1.8, 5),
    (24, 'childhood cancer financial assistance', 'childhood cancer financial assistance', 'support', 'financial', -2.9, -0.7, 2.2, 5),
    (25, 'childhood cancer survivor', 'childhood cancer survivor', 'survivorship', 'general', 0.4, 0.2, -2.4, 6),
    (26, 'late effects childhood cancer', 'late effects childhood cancer', 'survivorship', 'late_effects', 0.6, 0.4, -2.6, 6),
    (27, 'long term effects pediatric cancer treatment', 'long term effects pediatric cancer treatment', 'survivorship', 'late_effects', 0.3, 0.1, -2.3, 6),
    (28, 'childhood cancer survivor clinic', 'childhood cancer survivor clinic', 'survivorship', 'follow_up', 0.7, 0.5, -2.7, 6),
]

for t in terms:
    cur.execute("""
        INSERT INTO search_terms (id, term, normalized_term, category, subcategory, x, y, z, cluster_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (term) DO NOTHING
    """, t)

print(f"✓ Inserted {len(terms)} search terms")

# Insert posts
cur.execute("""
INSERT INTO posts (id, title, url, source, x, y, z, cluster_id) VALUES
(1, 'Understanding Childhood Leukemia: A Parents Guide', '#', 'curated', -2.2, 1.6, 0.4, 1),
(2, 'Latest Research in Pediatric Brain Tumors', '#', 'pubmed', 2.1, 2.5, -0.9, 2),
(3, 'Neuroblastoma Treatment Options 2024', '#', 'curated', 2.5, -1.2, 1.8, 3),
(4, 'Managing Chemotherapy Side Effects in Children', '#', 'internal', -0.6, -1.8, -0.2, 4),
(5, 'Finding Support: Resources for Families', '#', 'curated', -3.3, -0.2, 2.3, 5)
ON CONFLICT (id) DO NOTHING
""")

print("✓ Inserted 5 posts")

# Insert geographic regions
cur.execute("""
INSERT INTO geographic_regions (geo_code, name, level, latitude, longitude, population, svi_overall) VALUES
('US-CA', 'California', 'state', 36.116203, -119.681564, 39538223, 0.52),
('US-TX', 'Texas', 'state', 31.054487, -97.563461, 29145505, 0.58),
('US-NY', 'New York', 'state', 42.165726, -74.948051, 20201249, 0.48),
('US-FL', 'Florida', 'state', 27.766279, -81.686783, 21538187, 0.55),
('US-IL', 'Illinois', 'state', 40.349457, -88.986137, 12812508, 0.51),
('US-PA', 'Pennsylvania', 'state', 40.590752, -77.209755, 13002700, 0.49),
('US-OH', 'Ohio', 'state', 40.388783, -82.764915, 11799448, 0.54),
('US-GA', 'Georgia', 'state', 33.040619, -83.643074, 10711908, 0.57)
ON CONFLICT (geo_code) DO NOTHING
""")

print("✓ Inserted 8 geographic regions")

# Reset sequences
cur.execute("SELECT setval('clusters_id_seq', (SELECT COALESCE(MAX(id), 1) FROM clusters))")
cur.execute("SELECT setval('search_terms_id_seq', (SELECT COALESCE(MAX(id), 1) FROM search_terms))")
cur.execute("SELECT setval('posts_id_seq', (SELECT COALESCE(MAX(id), 1) FROM posts))")

cur.close()
conn.close()

print("\n✅ Database initialized and seeded successfully!")
print("\nYou can now access:")
print("  - API: http://localhost:8000")
print("  - API Docs: http://localhost:8000/docs")
