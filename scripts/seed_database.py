#!/usr/bin/env python3
"""
Seed the database with sample data for demo purposes.

Usage:
    python scripts/seed_database.py
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import SessionLocal, init_db
from app.models import SearchTerm, Cluster, Post, GeographicRegion


def load_sample_data():
    """Load sample data from JSON file."""
    data_path = Path(__file__).parent.parent / "backend" / "data" / "sample_data.json"
    with open(data_path) as f:
        return json.load(f)


def seed_database():
    """Seed the database with sample data."""
    print("Initializing database...")
    init_db()

    print("Loading sample data...")
    data = load_sample_data()

    db = SessionLocal()

    try:
        # Clear existing data
        print("Clearing existing data...")
        db.query(Post).delete()
        db.query(SearchTerm).delete()
        db.query(Cluster).delete()
        db.query(GeographicRegion).delete()
        db.commit()

        # Insert clusters
        print(f"Inserting {len(data['clusters'])} clusters...")
        cluster_map = {}
        for c in data["clusters"]:
            cluster = Cluster(
                id=c["id"],
                name=c["name"],
                centroid_x=c["x"],
                centroid_y=c["y"],
                centroid_z=c["z"],
                color=c["color"],
                size=c["size"],
                term_count=c["termCount"],
            )
            db.add(cluster)
            cluster_map[c["id"]] = cluster
        db.commit()

        # Insert terms
        print(f"Inserting {len(data['terms'])} terms...")
        for t in data["terms"]:
            term = SearchTerm(
                id=t["id"],
                term=t["term"],
                normalized_term=t["term"].lower(),
                category=t["category"],
                subcategory=t.get("subcategory"),
                x=t["x"],
                y=t["y"],
                z=t["z"],
                cluster_id=t.get("clusterId"),
            )
            db.add(term)
        db.commit()

        # Insert posts
        print(f"Inserting {len(data['posts'])} posts...")
        for p in data["posts"]:
            post = Post(
                id=p["id"],
                title=p["title"],
                url=p.get("url"),
                source=p["source"],
                x=p["x"],
                y=p["y"],
                z=p["z"],
                cluster_id=p.get("clusterId"),
            )
            db.add(post)
        db.commit()

        # Insert regions
        print(f"Inserting {len(data['regions'])} regions...")
        for r in data["regions"]:
            region = GeographicRegion(
                geo_code=r["geo_code"],
                name=r["name"],
                level="state",
                latitude=r["latitude"],
                longitude=r["longitude"],
                population=r.get("population"),
                svi_overall=r.get("svi_overall"),
            )
            db.add(region)
        db.commit()

        print("Database seeded successfully!")
        print(f"  - {len(data['clusters'])} clusters")
        print(f"  - {len(data['terms'])} terms")
        print(f"  - {len(data['posts'])} posts")
        print(f"  - {len(data['regions'])} regions")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
