"""
Google Trends data fetcher using pytrends.

Fetches interest-over-time and interest-by-region data for pediatric oncology terms.
Handles rate limiting and batch processing.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

import pandas as pd
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)


@dataclass
class TrendResult:
    """Result from a Google Trends query."""

    term: str
    interest_over_time: Optional[pd.DataFrame]
    interest_by_region: Optional[pd.DataFrame]
    related_queries: Optional[dict]
    fetched_at: datetime


class TrendsFetcher:
    """Fetches Google Trends data with rate limiting and error handling."""

    def __init__(
        self,
        hl: str = "en-US",
        tz: int = 360,
        timeout: tuple = (10, 25),
        retries: int = 3,
        backoff_factor: float = 1.5,
    ):
        self.pytrends = TrendReq(hl=hl, tz=tz, timeout=timeout, retries=retries, backoff_factor=backoff_factor)
        self.request_delay = 2.0  # Seconds between requests to avoid rate limiting

    def fetch_term(
        self,
        term: str,
        timeframe: str = "today 12-m",
        geo: str = "US",
        include_regions: bool = True,
        include_related: bool = True,
    ) -> TrendResult:
        """
        Fetch all trend data for a single term.

        Args:
            term: Search term to fetch
            timeframe: Time range (e.g., "today 12-m", "2023-01-01 2024-01-01")
            geo: Geographic region (e.g., "US", "US-CA")
            include_regions: Whether to fetch interest by region
            include_related: Whether to fetch related queries

        Returns:
            TrendResult with all fetched data
        """
        logger.info(f"Fetching trends for: {term}")

        interest_over_time = None
        interest_by_region = None
        related_queries = None

        try:
            # Build payload
            self.pytrends.build_payload([term], cat=0, timeframe=timeframe, geo=geo)
            time.sleep(self.request_delay)

            # Interest over time
            try:
                interest_over_time = self.pytrends.interest_over_time()
                if not interest_over_time.empty:
                    interest_over_time = interest_over_time.drop(columns=["isPartial"], errors="ignore")
                logger.debug(f"Got {len(interest_over_time)} time points for {term}")
            except Exception as e:
                logger.warning(f"Failed to get interest_over_time for {term}: {e}")

            time.sleep(self.request_delay)

            # Interest by region
            if include_regions:
                try:
                    interest_by_region = self.pytrends.interest_by_region(
                        resolution="REGION", inc_low_vol=True, inc_geo_code=True
                    )
                    logger.debug(f"Got {len(interest_by_region)} regions for {term}")
                except Exception as e:
                    logger.warning(f"Failed to get interest_by_region for {term}: {e}")

                time.sleep(self.request_delay)

            # Related queries
            if include_related:
                try:
                    related_queries = self.pytrends.related_queries()
                    logger.debug(f"Got related queries for {term}")
                except Exception as e:
                    logger.warning(f"Failed to get related_queries for {term}: {e}")

        except Exception as e:
            logger.error(f"Error fetching trends for {term}: {e}")

        return TrendResult(
            term=term,
            interest_over_time=interest_over_time,
            interest_by_region=interest_by_region,
            related_queries=related_queries,
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

            # Extra delay between batches to be nice to the API
            if (i + 1) % 5 == 0:
                logger.info("Batch delay...")
                time.sleep(5)

        return results

    def fetch_comparison(
        self,
        terms: list[str],
        timeframe: str = "today 12-m",
        geo: str = "US",
    ) -> Optional[pd.DataFrame]:
        """
        Fetch comparative interest over time for up to 5 terms.

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
            self.pytrends.build_payload(terms, cat=0, timeframe=timeframe, geo=geo)
            time.sleep(self.request_delay)

            df = self.pytrends.interest_over_time()
            if not df.empty:
                df = df.drop(columns=["isPartial"], errors="ignore")
            return df

        except Exception as e:
            logger.error(f"Error fetching comparison: {e}")
            return None

    def get_related_topics(self, term: str, geo: str = "US") -> dict:
        """Fetch related topics for term expansion."""
        try:
            self.pytrends.build_payload([term], geo=geo)
            time.sleep(self.request_delay)
            return self.pytrends.related_topics()
        except Exception as e:
            logger.error(f"Error fetching related topics for {term}: {e}")
            return {}


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
            "date": date.to_pydatetime(),
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
