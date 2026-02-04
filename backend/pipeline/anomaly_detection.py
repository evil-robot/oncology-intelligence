"""
Anomaly detection for pediatric oncology search trends.

Identifies:
- Sudden spikes (breakout terms)
- Unusual regional patterns
- Emerging topics
- Seasonal anomalies
- Cross-cluster correlations
"""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func, text

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    SPIKE = "spike"  # Sudden increase in interest
    DROP = "drop"  # Sudden decrease
    EMERGING = "emerging"  # New/growing topic
    REGIONAL_OUTLIER = "regional_outlier"  # Unusual geographic pattern
    SEASONAL_ANOMALY = "seasonal_anomaly"  # Unexpected seasonal behavior
    CORRELATION = "correlation"  # Unusual correlation between terms


class InsightSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Insight:
    """A detected insight/anomaly."""

    type: AnomalyType
    severity: InsightSeverity
    title: str
    description: str
    term_id: Optional[int] = None
    term_name: Optional[str] = None
    cluster_id: Optional[int] = None
    geo_code: Optional[str] = None
    metric_value: Optional[float] = None
    baseline_value: Optional[float] = None
    percent_change: Optional[float] = None
    detected_at: datetime = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "term_id": self.term_id,
            "term_name": self.term_name,
            "cluster_id": self.cluster_id,
            "geo_code": self.geo_code,
            "metric_value": self.metric_value,
            "baseline_value": self.baseline_value,
            "percent_change": self.percent_change,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }


class AnomalyDetector:
    """Detects anomalies and generates insights from trend data."""

    def __init__(
        self,
        spike_threshold: float = 2.0,  # Standard deviations for spike detection
        drop_threshold: float = -1.5,
        min_data_points: int = 4,
        lookback_weeks: int = 12,
    ):
        self.spike_threshold = spike_threshold
        self.drop_threshold = drop_threshold
        self.min_data_points = min_data_points
        self.lookback_weeks = lookback_weeks

    def detect_all(self, db: Session) -> list[Insight]:
        """Run all anomaly detection algorithms and return insights."""
        insights = []

        logger.info("Running anomaly detection...")

        # Detect spikes and drops
        insights.extend(self.detect_spikes_and_drops(db))

        # Detect emerging topics
        insights.extend(self.detect_emerging_topics(db))

        # Detect regional outliers
        insights.extend(self.detect_regional_outliers(db))

        # Detect cross-term correlations
        insights.extend(self.detect_correlations(db))

        # Sort by severity
        severity_order = {InsightSeverity.HIGH: 0, InsightSeverity.MEDIUM: 1, InsightSeverity.LOW: 2}
        insights.sort(key=lambda x: severity_order[x.severity])

        logger.info(f"Detected {len(insights)} insights")
        return insights

    def detect_spikes_and_drops(self, db: Session) -> list[Insight]:
        """Detect sudden spikes or drops in search interest."""
        insights = []

        # Get recent trend data grouped by term (flexible geo_code - country level)
        cutoff = datetime.utcnow() - timedelta(weeks=self.lookback_weeks)

        query = text("""
            SELECT
                t.term_id,
                st.term,
                st.cluster_id,
                array_agg(t.interest ORDER BY t.date) as interests,
                array_agg(t.date ORDER BY t.date) as dates
            FROM trend_data t
            JOIN search_terms st ON t.term_id = st.id
            WHERE t.date >= :cutoff
              AND t.geo_level = 'country'
              AND t.interest IS NOT NULL
            GROUP BY t.term_id, st.term, st.cluster_id
            HAVING COUNT(*) >= :min_points
        """)

        result = db.execute(query, {"cutoff": cutoff, "min_points": self.min_data_points})

        for row in result:
            term_id, term_name, cluster_id, interests, dates = row

            if len(interests) < self.min_data_points:
                continue

            interests = np.array(interests, dtype=float)

            # Calculate rolling statistics
            mean = np.mean(interests[:-1])  # Exclude last point
            std = np.std(interests[:-1])

            if std == 0:
                continue

            # Check last point for anomaly
            last_value = interests[-1]
            z_score = (last_value - mean) / std

            if z_score >= self.spike_threshold:
                pct_change = ((last_value - mean) / mean) * 100 if mean > 0 else 0
                insights.append(Insight(
                    type=AnomalyType.SPIKE,
                    severity=InsightSeverity.HIGH if z_score > 3 else InsightSeverity.MEDIUM,
                    title=f"Spike detected: {term_name}",
                    description=f"Search interest jumped {pct_change:.0f}% above average. "
                               f"Current: {last_value:.0f}, Baseline: {mean:.0f}",
                    term_id=term_id,
                    term_name=term_name,
                    cluster_id=cluster_id,
                    metric_value=float(last_value),
                    baseline_value=float(mean),
                    percent_change=float(pct_change),
                ))

            elif z_score <= self.drop_threshold:
                pct_change = ((last_value - mean) / mean) * 100 if mean > 0 else 0
                insights.append(Insight(
                    type=AnomalyType.DROP,
                    severity=InsightSeverity.MEDIUM,
                    title=f"Drop detected: {term_name}",
                    description=f"Search interest dropped {abs(pct_change):.0f}% below average. "
                               f"Current: {last_value:.0f}, Baseline: {mean:.0f}",
                    term_id=term_id,
                    term_name=term_name,
                    cluster_id=cluster_id,
                    metric_value=float(last_value),
                    baseline_value=float(mean),
                    percent_change=float(pct_change),
                ))

        return insights

    def detect_emerging_topics(self, db: Session) -> list[Insight]:
        """Detect topics with consistent upward trend."""
        insights = []

        cutoff = datetime.utcnow() - timedelta(weeks=8)

        query = text("""
            SELECT
                t.term_id,
                st.term,
                st.cluster_id,
                array_agg(t.interest ORDER BY t.date) as interests
            FROM trend_data t
            JOIN search_terms st ON t.term_id = st.id
            WHERE t.date >= :cutoff
              AND t.geo_level = 'country'
              AND t.interest IS NOT NULL
            GROUP BY t.term_id, st.term, st.cluster_id
            HAVING COUNT(*) >= 4
        """)

        result = db.execute(query, {"cutoff": cutoff})

        for row in result:
            term_id, term_name, cluster_id, interests = row
            interests = np.array(interests, dtype=float)

            if len(interests) < 4:
                continue

            # Check for consistent upward trend
            # Simple: compare first half average to second half
            mid = len(interests) // 2
            first_half = np.mean(interests[:mid])
            second_half = np.mean(interests[mid:])

            if first_half > 0:
                growth = ((second_half - first_half) / first_half) * 100

                if growth > 30:  # 30% growth threshold
                    insights.append(Insight(
                        type=AnomalyType.EMERGING,
                        severity=InsightSeverity.HIGH if growth > 50 else InsightSeverity.MEDIUM,
                        title=f"Emerging topic: {term_name}",
                        description=f"Consistent {growth:.0f}% growth over recent weeks. "
                                   f"Early avg: {first_half:.0f} → Recent avg: {second_half:.0f}",
                        term_id=term_id,
                        term_name=term_name,
                        cluster_id=cluster_id,
                        metric_value=float(second_half),
                        baseline_value=float(first_half),
                        percent_change=float(growth),
                    ))

        return insights

    def detect_regional_outliers(self, db: Session) -> list[Insight]:
        """Detect unusual regional patterns."""
        insights = []

        # Get regional interest for each term
        query = text("""
            SELECT
                st.id as term_id,
                st.term,
                st.cluster_id,
                t.geo_code,
                gr.name as geo_name,
                gr.svi_overall,
                AVG(t.interest) as avg_interest
            FROM trend_data t
            JOIN search_terms st ON t.term_id = st.id
            JOIN geographic_regions gr ON t.geo_code = gr.geo_code
            WHERE t.geo_level = 'state'
              AND t.interest IS NOT NULL
            GROUP BY st.id, st.term, st.cluster_id, t.geo_code, gr.name, gr.svi_overall
        """)

        result = db.execute(query)
        rows = list(result)

        # Group by term
        term_regions = {}
        for row in rows:
            term_id = row.term_id
            if term_id not in term_regions:
                term_regions[term_id] = {
                    "term": row.term,
                    "cluster_id": row.cluster_id,
                    "regions": []
                }
            term_regions[term_id]["regions"].append({
                "geo_code": row.geo_code,
                "geo_name": row.geo_name,
                "svi": row.svi_overall,
                "interest": float(row.avg_interest) if row.avg_interest else 0
            })

        # Find regional outliers for each term
        for term_id, data in term_regions.items():
            regions = data["regions"]
            if len(regions) < 3:
                continue

            interests = np.array([r["interest"] for r in regions])
            mean = np.mean(interests)
            std = np.std(interests)

            if std == 0:
                continue

            for region in regions:
                z_score = (region["interest"] - mean) / std

                if z_score > 2.0:  # Unusually high interest
                    svi_note = ""
                    if region["svi"] and region["svi"] > 0.6:
                        svi_note = " (high vulnerability area)"

                    insights.append(Insight(
                        type=AnomalyType.REGIONAL_OUTLIER,
                        severity=InsightSeverity.MEDIUM,
                        title=f"High regional interest: {data['term']} in {region['geo_name']}",
                        description=f"{region['geo_name']} shows {region['interest']:.0f} interest "
                                   f"vs national avg of {mean:.0f}{svi_note}",
                        term_id=term_id,
                        term_name=data["term"],
                        cluster_id=data["cluster_id"],
                        geo_code=region["geo_code"],
                        metric_value=region["interest"],
                        baseline_value=float(mean),
                        percent_change=float(((region["interest"] - mean) / mean) * 100) if mean > 0 else 0,
                    ))

        return insights

    def detect_correlations(self, db: Session) -> list[Insight]:
        """Detect unusual correlations between search terms."""
        insights = []

        # Get time series for all terms (country level data)
        query = text("""
            SELECT
                term_id,
                array_agg(interest ORDER BY date) as interests
            FROM trend_data
            WHERE geo_level = 'country'
              AND interest IS NOT NULL
            GROUP BY term_id
            HAVING COUNT(*) >= 8
        """)

        result = db.execute(query)
        term_series = {row.term_id: np.array(row.interests, dtype=float) for row in result}

        # Get term names
        term_names = {}
        name_query = text("SELECT id, term, category FROM search_terms")
        for row in db.execute(name_query):
            term_names[row.id] = {"term": row.term, "category": row.category}

        # Find correlations between terms in different categories
        term_ids = list(term_series.keys())
        checked_pairs = set()

        for i, t1 in enumerate(term_ids):
            for t2 in term_ids[i+1:]:
                if (t1, t2) in checked_pairs or (t2, t1) in checked_pairs:
                    continue
                checked_pairs.add((t1, t2))

                if t1 not in term_names or t2 not in term_names:
                    continue

                # Only check cross-category correlations
                if term_names[t1]["category"] == term_names[t2]["category"]:
                    continue

                s1 = term_series[t1]
                s2 = term_series[t2]

                # Align lengths
                min_len = min(len(s1), len(s2))
                if min_len < 8:
                    continue

                s1 = s1[:min_len]
                s2 = s2[:min_len]

                # Calculate correlation
                corr = np.corrcoef(s1, s2)[0, 1]

                if abs(corr) > 0.8:  # Strong correlation
                    insights.append(Insight(
                        type=AnomalyType.CORRELATION,
                        severity=InsightSeverity.LOW,
                        title=f"Correlated trends detected",
                        description=f'"{term_names[t1]["term"]}" and "{term_names[t2]["term"]}" '
                                   f"show {corr:.0%} correlation across different categories",
                        term_id=t1,
                        term_name=term_names[t1]["term"],
                        metric_value=float(corr),
                    ))

        return insights


def run_anomaly_detection(db: Session) -> list[dict]:
    """Run anomaly detection and return insights as dicts."""
    detector = AnomalyDetector()
    insights = detector.detect_all(db)
    return [i.to_dict() for i in insights]
