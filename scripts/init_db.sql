-- Initialize Pediatric Oncology Intelligence Database
-- Run this in your Neon SQL Editor or via psql

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Clusters table
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
);

-- Search terms table
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
);

-- Posts table
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
);

-- Geographic regions table
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
);

-- Trend data table
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
);

-- Pipeline runs table
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',
    config JSONB
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_search_terms_category ON search_terms(category);
CREATE INDEX IF NOT EXISTS ix_search_terms_cluster ON search_terms(cluster_id);
CREATE INDEX IF NOT EXISTS ix_trend_data_term_date ON trend_data(term_id, date);
CREATE INDEX IF NOT EXISTS ix_geographic_regions_geo_code ON geographic_regions(geo_code);

-- Confirmation
SELECT 'Database initialized successfully!' as status;
