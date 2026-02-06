"""
Google Trends data fetcher using SerpAPI.

Fetches interest-over-time and interest-by-region data for oncology and rare disease terms.
Replaces the previous pytrends-based implementation with the reliable SerpAPI Google Trends API.

SerpAPI data_type options:
  - TIMESERIES: Interest over time (up to 5 queries)
  - GEO_MAP_0: Interest by region (single query)
  - GEO_MAP: Compared breakdown by region (up to 5 queries)
  - RELATED_QUERIES: Related queries (single query)
  - RELATED_TOPICS: Related topics (single query)
"""

import time
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import pandas as pd
from serpapi import GoogleSearch

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TrendResult:
    """Result from a Google Trends query."""

    term: str
    interest_over_time: Optional[pd.DataFrame]
    interest_by_region: Optional[pd.DataFrame]
    related_queries: Optional[dict]
    related_topics: Optional[dict]
    fetched_at: datetime


class TrendsFetcher:
    """Fetches Google Trends data via SerpAPI with rate limiting and error handling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        request_delay: float = 0.5,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.serpapi_key
        if not self.api_key:
            raise ValueError("SERPAPI_KEY is required. Set it in your .env file or pass it directly.")
        self.request_delay = request_delay  # SerpAPI is much faster than pytrends, less delay needed

    def _search(self, params: dict) -> dict:
        """Execute a SerpAPI search and return parsed results."""
        params["api_key"] = self.api_key
        params["engine"] = "google_trends"
        search = GoogleSearch(params)
        return search.get_dict()

    def _fetch_interest_over_time(
        self,
        term: str,
        date: str = "today 12-m",
        geo: str = "US",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch interest over time for a single term.

        Returns DataFrame with columns: date, interest
        """
        try:
            params = {
                "q": term,
                "date": date,
                "geo": geo,
                "data_type": "TIMESERIES",
            }
            results = self._search(params)
            time.sleep(self.request_delay)

            iot_data = results.get("interest_over_time", {})
            timeline = iot_data.get("timeline_data", [])

            if not timeline:
                logger.warning(f"No interest_over_time data for '{term}'")
                return None

            records = []
            for point in timeline:
                # Parse date — SerpAPI returns date strings like "Jan 1 – 7, 2024"
                # Use the timestamp if available, otherwise parse the date string
                date_str = point.get("date", "")
                values = point.get("values", [])

                # Find the value matching our term
                interest = 0
                for val in values:
                    if val.get("query", "").lower() == term.lower():
                        interest = val.get("extracted_value", 0)
                        break
                else:
                    # If no exact match, use the first value
                    if values:
                        interest = values[0].get("extracted_value", 0)

                # Try to parse a usable date from the timestamp or date string
                timestamp = point.get("timestamp")
                if timestamp:
                    dt = datetime.fromtimestamp(int(timestamp))
                else:
                    # Use the start of the date range
                    try:
                        # Date format: "Jan 1 – 7, 2024" or "Jan 2024"
                        clean_date = date_str.split("–")[0].split("—")[0].strip().rstrip(",").strip()
                        # Try various formats
                        for fmt in ["%b %d %Y", "%b %d, %Y", "%b %Y", "%Y-%m-%d"]:
                            try:
                                dt = datetime.strptime(clean_date, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            continue  # Skip this point if we can't parse the date
                    except Exception:
                        continue

                records.append({
                    "date": dt,
                    term: interest,
                })

            if not records:
                return None

            df = pd.DataFrame(records)
            df = df.set_index("date")
            logger.debug(f"Got {len(df)} time points for '{term}'")
            return df

        except Exception as e:
            logger.warning(f"Failed to get interest_over_time for '{term}': {e}")
            return None

    def _fetch_interest_by_region(
        self,
        term: str,
        date: str = "today 12-m",
        geo: str = "US",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch interest by region for a single term.

        Returns DataFrame with columns: geoCode, geoName, interest
        """
        try:
            params = {
                "q": term,
                "date": date,
                "geo": geo,
                "data_type": "GEO_MAP_0",
            }
            results = self._search(params)
            time.sleep(self.request_delay)

            regions = results.get("interest_by_region", [])

            if not regions:
                logger.warning(f"No interest_by_region data for '{term}'")
                return None

            records = []
            for region in regions:
                geo_code = region.get("geo", "")
                location = region.get("location", "")
                interest = region.get("extracted_value", 0)

                records.append({
                    "geoCode": geo_code,
                    "geoName": location,
                    term: interest,
                })

            df = pd.DataFrame(records)
            df = df.set_index("geoName")
            logger.debug(f"Got {len(df)} regions for '{term}'")
            return df

        except Exception as e:
            logger.warning(f"Failed to get interest_by_region for '{term}': {e}")
            return None

    def _fetch_related_queries(
        self,
        term: str,
        date: str = "today 12-m",
        geo: str = "US",
    ) -> Optional[dict]:
        """Fetch related queries for a single term."""
        try:
            params = {
                "q": term,
                "date": date,
                "geo": geo,
                "data_type": "RELATED_QUERIES",
            }
            results = self._search(params)
            time.sleep(self.request_delay)

            related = results.get("related_queries", {})
            logger.debug(f"Got related queries for '{term}'")
            return related if related else None

        except Exception as e:
            logger.warning(f"Failed to get related_queries for '{term}': {e}")
            return None

    def fetch_term(
        self,
        term: str,
        timeframe: str = "today 12-m",
        geo: str = "US",
        include_regions: bool = True,
        include_related: bool = True,
        include_topics: bool = True,
    ) -> TrendResult:
        """
        Fetch all trend data for a single term.

        Args:
            term: Search term to fetch
            timeframe: Time range (e.g., "today 12-m", "today 5-y", "2023-01-01 2024-01-01")
            geo: Geographic region (e.g., "US", "US-CA")
            include_regions: Whether to fetch interest by region
            include_related: Whether to fetch related queries
            include_topics: Whether to fetch related topics

        Returns:
            TrendResult with all fetched data
        """
        logger.info(f"Fetching trends for: {term}")

        # SerpAPI uses 'date' parameter with same format as pytrends 'timeframe'
        date_param = timeframe

        interest_over_time = self._fetch_interest_over_time(term, date=date_param, geo=geo)

        interest_by_region = None
        if include_regions:
            interest_by_region = self._fetch_interest_by_region(term, date=date_param, geo=geo)

        related_queries = None
        if include_related:
            related_queries = self._fetch_related_queries(term, date=date_param, geo=geo)

        related_topics = None
        if include_topics:
            related_topics = self._fetch_related_topics(term, date=date_param, geo=geo)

        return TrendResult(
            term=term,
            interest_over_time=interest_over_time,
            interest_by_region=interest_by_region,
            related_queries=related_queries,
            related_topics=related_topics,
            fetched_at=datetime.utcnow(),
        )

    def fetch_batch(
        self,
        terms: list[str],
        timeframe: str = "today 12-m",
        geo: str = "US",
        **kwargs,
    ) -> list[TrendResult]:
        """
        Fetch trends for multiple terms with rate limiting.

        Args:
            terms: List of search terms
            timeframe: Time range
            geo: Geographic region
            **kwargs: Additional arguments passed to fetch_term

        Returns:
            List of TrendResult objects
        """
        results = []
        total = len(terms)

        for i, term in enumerate(terms):
            logger.info(f"Processing term {i + 1}/{total}: {term}")
            result = self.fetch_term(term, timeframe=timeframe, geo=geo, **kwargs)
            results.append(result)

            # Brief delay between terms (SerpAPI is more forgiving than pytrends)
            if (i + 1) % 10 == 0:
                logger.info("Batch delay...")
                time.sleep(2)

        return results

    def fetch_comparison(
        self,
        terms: list[str],
        timeframe: str = "today 12-m",
        geo: str = "US",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch comparative interest over time for up to 5 terms.

        SerpAPI's TIMESERIES data_type supports up to 5 comma-separated queries.

        Args:
            terms: List of 2-5 terms to compare
            timeframe: Time range
            geo: Geographic region

        Returns:
            DataFrame with interest over time for all terms
        """
        if len(terms) > 5:
            logger.warning("Google Trends only allows 5 terms per comparison, truncating")
            terms = terms[:5]

        try:
            params = {
                "q": ",".join(terms),
                "date": timeframe,
                "geo": geo,
                "data_type": "TIMESERIES",
            }
            results = self._search(params)

            iot_data = results.get("interest_over_time", {})
            timeline = iot_data.get("timeline_data", [])

            if not timeline:
                return None

            records = []
            for point in timeline:
                row = {}
                timestamp = point.get("timestamp")
                if timestamp:
                    row["date"] = datetime.fromtimestamp(int(timestamp))
                else:
                    continue

                for val in point.get("values", []):
                    query = val.get("query", "")
                    row[query] = val.get("extracted_value", 0)

                records.append(row)

            if not records:
                return None

            df = pd.DataFrame(records).set_index("date")
            return df

        except Exception as e:
            logger.error(f"Error fetching comparison: {e}")
            return None

    def _fetch_related_topics(
        self,
        term: str,
        date: str = "today 12-m",
        geo: str = "US",
    ) -> Optional[dict]:
        """Fetch related topics for a single term."""
        try:
            params = {
                "q": term,
                "date": date,
                "geo": geo,
                "data_type": "RELATED_TOPICS",
            }
            results = self._search(params)
            time.sleep(self.request_delay)

            related = results.get("related_topics", {})
            logger.debug(f"Got related topics for '{term}'")
            return related if related else None

        except Exception as e:
            logger.warning(f"Failed to get related_topics for '{term}': {e}")
            return None

    def get_related_topics(self, term: str, geo: str = "US") -> dict:
        """Fetch related topics for term expansion (convenience method)."""
        result = self._fetch_related_topics(term, geo=geo)
        return result or {}

    def fetch_hourly(
        self,
        term: str,
        geo: str = "US",
        window: str = "now 7-d",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch hourly interest data for a term over a recent window.

        Google Trends provides hourly resolution for short timeframes:
          - "now 1-H": past hour (minute resolution)
          - "now 4-H": past 4 hours (minute resolution)
          - "now 1-d": past 24 hours (8-minute resolution)
          - "now 7-d": past 7 days (hourly resolution)

        Returns DataFrame with columns: datetime, hour, day_of_week, interest
        """
        try:
            params = {
                "q": term,
                "date": window,
                "geo": geo,
                "data_type": "TIMESERIES",
            }
            results = self._search(params)
            time.sleep(self.request_delay)

            iot_data = results.get("interest_over_time", {})
            timeline = iot_data.get("timeline_data", [])

            if not timeline:
                logger.warning(f"No hourly data for '{term}'")
                return None

            records = []
            for point in timeline:
                timestamp = point.get("timestamp")
                if not timestamp:
                    continue

                dt = datetime.fromtimestamp(int(timestamp))
                values = point.get("values", [])
                interest = 0
                for val in values:
                    if val.get("query", "").lower() == term.lower():
                        interest = val.get("extracted_value", 0)
                        break
                else:
                    if values:
                        interest = values[0].get("extracted_value", 0)

                records.append({
                    "datetime": dt,
                    "hour": dt.hour,
                    "day_of_week": dt.weekday(),  # 0=Mon, 6=Sun
                    "interest": interest,
                })

            if not records:
                return None

            df = pd.DataFrame(records)
            logger.debug(f"Got {len(df)} hourly points for '{term}'")
            return df

        except Exception as e:
            logger.warning(f"Failed to get hourly data for '{term}': {e}")
            return None


def transform_interest_over_time(
    result: TrendResult,
    geo_code: str = "US",
) -> list[dict]:
    """
    Transform interest_over_time DataFrame to records for database insertion.

    Returns list of dicts with keys: term, date, interest, geo_code
    """
    if result.interest_over_time is None or result.interest_over_time.empty:
        return []

    records = []
    df = result.interest_over_time

    for date, row in df.iterrows():
        records.append({
            "term": result.term,
            "date": date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date,
            "interest": int(row[result.term]) if result.term in row else 0,
            "geo_code": geo_code,
            "geo_level": "country" if len(geo_code) == 2 else "state",
        })

    return records


def transform_interest_by_region(result: TrendResult) -> list[dict]:
    """
    Transform interest_by_region DataFrame to records for database insertion.

    Returns list of dicts with keys: term, geo_code, geo_name, interest
    """
    if result.interest_by_region is None or result.interest_by_region.empty:
        return []

    records = []
    df = result.interest_by_region.reset_index()

    for _, row in df.iterrows():
        geo_code = row.get("geoCode", row.get("geoName", ""))
        records.append({
            "term": result.term,
            "geo_code": geo_code,
            "geo_name": row.get("geoName", row.name if hasattr(row, "name") else ""),
            "interest": int(row[result.term]) if result.term in row else 0,
            "geo_level": "state",
        })

    return records


def transform_related_queries(result: TrendResult) -> list[dict]:
    """
    Transform related_queries dict to records for database insertion.

    Returns list of dicts with keys: query, query_type, value, extracted_value
    """
    if not result.related_queries:
        return []

    records = []

    # Process rising queries
    for item in result.related_queries.get("rising", []):
        records.append({
            "query": item.get("query", ""),
            "query_type": "rising_query",
            "topic_type": None,
            "value": str(item.get("value", "")),
            "extracted_value": item.get("extracted_value", 0),
        })

    # Process top queries
    for item in result.related_queries.get("top", []):
        records.append({
            "query": item.get("query", ""),
            "query_type": "top_query",
            "topic_type": None,
            "value": str(item.get("value", "")),
            "extracted_value": item.get("extracted_value", 0),
        })

    return records


def transform_related_topics(result: TrendResult) -> list[dict]:
    """
    Transform related_topics dict to records for database insertion.

    Returns list of dicts with keys: query, query_type, topic_type, value, extracted_value
    """
    if not result.related_topics:
        return []

    records = []

    # Process rising topics
    for item in result.related_topics.get("rising", []):
        topic = item.get("topic", {})
        records.append({
            "query": topic.get("title", ""),
            "query_type": "rising_topic",
            "topic_type": topic.get("type", ""),
            "value": str(item.get("value", "")),
            "extracted_value": item.get("extracted_value", 0),
        })

    # Process top topics
    for item in result.related_topics.get("top", []):
        topic = item.get("topic", {})
        records.append({
            "query": topic.get("title", ""),
            "query_type": "top_topic",
            "topic_type": topic.get("type", ""),
            "value": str(item.get("value", "")),
            "extracted_value": item.get("extracted_value", 0),
        })

    return records


def aggregate_hourly_patterns(df: pd.DataFrame) -> dict:
    """
    Aggregate raw hourly data into hour-of-day patterns.

    Takes the raw hourly DataFrame from fetch_hourly() and computes:
    - Average interest per hour of day (0-23)
    - Peak hours (highest search activity)
    - Late-night anxiety index (11pm-4am average vs daytime average)

    Returns dict with keys: hourly_avg, peak_hours, anxiety_index, late_night_avg, daytime_avg
    """
    if df is None or df.empty:
        return {}

    # Average interest by hour of day
    hourly_avg = df.groupby("hour")["interest"].mean().to_dict()
    # Fill missing hours with 0
    hourly_avg = {h: round(hourly_avg.get(h, 0), 1) for h in range(24)}

    # Find peak hours (top 3)
    sorted_hours = sorted(hourly_avg.items(), key=lambda x: x[1], reverse=True)
    peak_hours = [h for h, _ in sorted_hours[:3]]

    # Late night = 11pm-4am (hours 23, 0, 1, 2, 3, 4)
    late_night_hours = {23, 0, 1, 2, 3, 4}
    late_night_values = [v for h, v in hourly_avg.items() if h in late_night_hours]
    late_night_avg = round(sum(late_night_values) / max(len(late_night_values), 1), 1)

    # Daytime = 8am-6pm (hours 8-18)
    daytime_hours = set(range(8, 19))
    daytime_values = [v for h, v in hourly_avg.items() if h in daytime_hours]
    daytime_avg = round(sum(daytime_values) / max(len(daytime_values), 1), 1)

    # Anxiety index: ratio of late-night to daytime (>1.0 means more searching at night)
    anxiety_index = round(late_night_avg / max(daytime_avg, 0.1), 2)

    # Day of week patterns
    dow_avg = df.groupby("day_of_week")["interest"].mean().to_dict()
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_of_week = {dow_names[d]: round(dow_avg.get(d, 0), 1) for d in range(7)}

    return {
        "hourly_avg": hourly_avg,
        "peak_hours": peak_hours,
        "anxiety_index": anxiety_index,
        "late_night_avg": late_night_avg,
        "daytime_avg": daytime_avg,
        "day_of_week": day_of_week,
    }
