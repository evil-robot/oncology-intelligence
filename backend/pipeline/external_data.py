"""
External data source integrations for triangulating search trends.

Integrates:
- ClinicalTrials.gov - Active clinical trials
- FDA openFDA - Drug approvals and safety
- PubMed - Research publications
- News - Media coverage
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# API endpoints
CLINICALTRIALS_API = "https://clinicaltrials.gov/api/v2/studies"
OPENFDA_API = "https://api.fda.gov/drug"
PUBMED_API = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NEWS_API = "https://newsdata.io/api/1/news"  # Free tier available


@dataclass
class ClinicalTrial:
    nct_id: str
    title: str
    status: str
    phase: str
    conditions: list[str]
    interventions: list[str]
    start_date: Optional[str]
    sponsor: Optional[str]
    enrollment: Optional[int]
    url: str

    def to_dict(self):
        return {
            "nct_id": self.nct_id,
            "title": self.title,
            "status": self.status,
            "phase": self.phase,
            "conditions": self.conditions,
            "interventions": self.interventions,
            "start_date": self.start_date,
            "sponsor": self.sponsor,
            "enrollment": self.enrollment,
            "url": self.url,
        }


@dataclass
class FDADrugEvent:
    drug_name: str
    event_type: str
    date: str
    description: str
    source: str

    def to_dict(self):
        return {
            "drug_name": self.drug_name,
            "event_type": self.event_type,
            "date": self.date,
            "description": self.description,
            "source": self.source,
        }


@dataclass
class PubMedArticle:
    pmid: str
    title: str
    authors: list[str]
    journal: str
    pub_date: str
    abstract: Optional[str]
    url: str

    def to_dict(self):
        return {
            "pmid": self.pmid,
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "pub_date": self.pub_date,
            "abstract": self.abstract,
            "url": self.url,
        }


@dataclass
class NewsArticle:
    title: str
    source: str
    url: str
    published_at: str
    description: Optional[str]

    def to_dict(self):
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "published_at": self.published_at,
            "description": self.description,
        }


class ClinicalTrialsClient:
    """Client for ClinicalTrials.gov API v2."""

    def __init__(self):
        self.base_url = CLINICALTRIALS_API
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        condition: Optional[str] = None,
        status: str = "RECRUITING",
        max_results: int = 10,
    ) -> list[ClinicalTrial]:
        """Search for clinical trials."""
        try:
            params = {
                "format": "json",
                "pageSize": max_results,
                "query.term": query,
            }

            if condition:
                params["query.cond"] = condition

            if status:
                params["filter.overallStatus"] = status

            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            trials = []
            for study in data.get("studies", []):
                protocol = study.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})
                status_module = protocol.get("statusModule", {})
                design_module = protocol.get("designModule", {})
                conditions_module = protocol.get("conditionsModule", {})
                arms_module = protocol.get("armsInterventionsModule", {})
                sponsor_module = protocol.get("sponsorCollaboratorsModule", {})

                nct_id = id_module.get("nctId", "")

                # Get interventions
                interventions = []
                for intervention in arms_module.get("interventions", []):
                    interventions.append(intervention.get("name", ""))

                trials.append(ClinicalTrial(
                    nct_id=nct_id,
                    title=id_module.get("briefTitle", ""),
                    status=status_module.get("overallStatus", ""),
                    phase=", ".join(design_module.get("phases", [])),
                    conditions=conditions_module.get("conditions", []),
                    interventions=interventions,
                    start_date=status_module.get("startDateStruct", {}).get("date"),
                    sponsor=sponsor_module.get("leadSponsor", {}).get("name"),
                    enrollment=design_module.get("enrollmentInfo", {}).get("count"),
                    url=f"https://clinicaltrials.gov/study/{nct_id}",
                ))

            logger.info(f"Found {len(trials)} clinical trials for '{query}'")
            return trials

        except Exception as e:
            logger.error(f"ClinicalTrials.gov API error: {e}")
            return []

    async def close(self):
        await self.client.aclose()


class OpenFDAClient:
    """Client for FDA openFDA API."""

    def __init__(self):
        self.base_url = OPENFDA_API
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_drug_approvals(
        self,
        drug_name: str,
        max_results: int = 10,
    ) -> list[FDADrugEvent]:
        """Search for drug approval events."""
        try:
            # Search drug labels for approval info
            url = f"{self.base_url}/label.json"
            params = {
                "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
                "limit": max_results,
            }

            response = await self.client.get(url, params=params)

            if response.status_code == 404:
                return []

            response.raise_for_status()
            data = response.json()

            events = []
            for result in data.get("results", []):
                openfda = result.get("openfda", {})
                brand_names = openfda.get("brand_name", [])

                events.append(FDADrugEvent(
                    drug_name=brand_names[0] if brand_names else drug_name,
                    event_type="label",
                    date=result.get("effective_time", ""),
                    description=result.get("purpose", [""])[0] if result.get("purpose") else "",
                    source="FDA Drug Labels",
                ))

            logger.info(f"Found {len(events)} FDA records for '{drug_name}'")
            return events

        except Exception as e:
            logger.error(f"OpenFDA API error: {e}")
            return []

    async def search_adverse_events(
        self,
        drug_name: str,
        max_results: int = 5,
    ) -> list[FDADrugEvent]:
        """Search for adverse event reports."""
        try:
            url = f"{self.base_url}/event.json"
            params = {
                "search": f'patient.drug.medicinalproduct:"{drug_name}"',
                "limit": max_results,
            }

            response = await self.client.get(url, params=params)

            if response.status_code == 404:
                return []

            response.raise_for_status()
            data = response.json()

            events = []
            for result in data.get("results", []):
                reactions = result.get("patient", {}).get("reaction", [])
                reaction_str = ", ".join([r.get("reactionmeddrapt", "") for r in reactions[:3]])

                events.append(FDADrugEvent(
                    drug_name=drug_name,
                    event_type="adverse_event",
                    date=result.get("receivedate", ""),
                    description=f"Reported reactions: {reaction_str}",
                    source="FDA Adverse Events",
                ))

            return events

        except Exception as e:
            logger.error(f"OpenFDA adverse events error: {e}")
            return []

    async def close(self):
        await self.client.aclose()


class PubMedClient:
    """Client for PubMed/NCBI E-utilities API."""

    def __init__(self):
        self.base_url = PUBMED_API
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        max_results: int = 10,
        days_back: int = 365,
    ) -> list[PubMedArticle]:
        """Search PubMed for recent articles."""
        try:
            # First, search for PMIDs
            search_url = f"{self.base_url}/esearch.fcgi"
            min_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")

            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "date",
                "mindate": min_date,
                "datetype": "pdat",
            }

            response = await self.client.get(search_url, params=search_params)
            response.raise_for_status()
            search_data = response.json()

            pmids = search_data.get("esearchresult", {}).get("idlist", [])

            if not pmids:
                return []

            # Fetch article details
            fetch_url = f"{self.base_url}/esummary.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
            }

            response = await self.client.get(fetch_url, params=fetch_params)
            response.raise_for_status()
            fetch_data = response.json()

            articles = []
            result = fetch_data.get("result", {})

            for pmid in pmids:
                if pmid not in result:
                    continue

                article_data = result[pmid]

                # Get authors
                authors = []
                for author in article_data.get("authors", [])[:3]:
                    authors.append(author.get("name", ""))

                articles.append(PubMedArticle(
                    pmid=pmid,
                    title=article_data.get("title", ""),
                    authors=authors,
                    journal=article_data.get("source", ""),
                    pub_date=article_data.get("pubdate", ""),
                    abstract=None,  # Would need separate fetch
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                ))

            logger.info(f"Found {len(articles)} PubMed articles for '{query}'")
            return articles

        except Exception as e:
            logger.error(f"PubMed API error: {e}")
            return []

    async def close(self):
        await self.client.aclose()


class NewsClient:
    """Client for news aggregation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search_health_news(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[NewsArticle]:
        """Search for health news articles using free sources."""
        articles = []

        # Try Google News RSS (no API key needed)
        try:
            import xml.etree.ElementTree as ET

            rss_url = f"https://news.google.com/rss/search?q={query}+health&hl=en-US&gl=US&ceid=US:en"
            response = await self.client.get(rss_url)

            if response.status_code == 200:
                root = ET.fromstring(response.content)

                for item in root.findall(".//item")[:max_results]:
                    title = item.find("title")
                    link = item.find("link")
                    pub_date = item.find("pubDate")
                    source = item.find("source")

                    articles.append(NewsArticle(
                        title=title.text if title is not None else "",
                        source=source.text if source is not None else "Google News",
                        url=link.text if link is not None else "",
                        published_at=pub_date.text if pub_date is not None else "",
                        description=None,
                    ))

            logger.info(f"Found {len(articles)} news articles for '{query}'")

        except Exception as e:
            logger.error(f"News search error: {e}")

        return articles

    async def close(self):
        await self.client.aclose()


class ExternalDataAggregator:
    """Aggregates data from all external sources for a given term."""

    def __init__(self):
        self.trials_client = ClinicalTrialsClient()
        self.fda_client = OpenFDAClient()
        self.pubmed_client = PubMedClient()
        self.news_client = NewsClient()

    async def get_triangulation_data(
        self,
        term: str,
        category: Optional[str] = None,
    ) -> dict:
        """Fetch all external data for a term."""

        # Determine search strategy based on category
        is_treatment = category in ["treatment", "adult_oncology", "pediatric_oncology"]
        is_disease = category in ["rare_genetic", "rare_neurological", "rare_autoimmune",
                                   "rare_pulmonary", "rare_metabolic", "rare_immune", "rare_cancer"]

        # Run all API calls concurrently
        tasks = [
            self.trials_client.search(term, max_results=5),
            self.pubmed_client.search(f"{term} clinical", max_results=5),
            self.news_client.search_health_news(term, max_results=5),
        ]

        # Add FDA search for treatments/drugs
        if is_treatment or "therapy" in term.lower() or "treatment" in term.lower():
            tasks.append(self.fda_client.search_drug_approvals(term, max_results=3))
        else:
            async def empty_list():
                return []
            tasks.append(empty_list())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        trials = results[0] if not isinstance(results[0], Exception) else []
        articles = results[1] if not isinstance(results[1], Exception) else []
        news = results[2] if not isinstance(results[2], Exception) else []
        fda_events = results[3] if not isinstance(results[3], Exception) else []

        return {
            "term": term,
            "category": category,
            "clinical_trials": {
                "count": len(trials),
                "items": [t.to_dict() for t in trials],
                "recruiting": sum(1 for t in trials if t.status == "RECRUITING"),
            },
            "publications": {
                "count": len(articles),
                "items": [a.to_dict() for a in articles],
            },
            "fda_data": {
                "count": len(fda_events),
                "items": [e.to_dict() for e in fda_events],
            },
            "news": {
                "count": len(news),
                "items": [n.to_dict() for n in news],
            },
            "summary": {
                "total_sources": sum([
                    1 if trials else 0,
                    1 if articles else 0,
                    1 if fda_events else 0,
                    1 if news else 0,
                ]),
                "evidence_strength": self._calculate_evidence_strength(trials, articles, fda_events, news),
            },
            "fetched_at": datetime.utcnow().isoformat(),
        }

    def _calculate_evidence_strength(self, trials, articles, fda_events, news) -> str:
        """Calculate overall evidence strength."""
        score = 0

        # Clinical trials are strong evidence
        score += len(trials) * 3
        if any(t.status == "RECRUITING" for t in trials):
            score += 5

        # Publications are good evidence
        score += len(articles) * 2

        # FDA data is authoritative
        score += len(fda_events) * 4

        # News indicates public interest
        score += len(news) * 1

        if score >= 20:
            return "strong"
        elif score >= 10:
            return "moderate"
        elif score >= 5:
            return "emerging"
        else:
            return "limited"

    async def close(self):
        await self.trials_client.close()
        await self.fda_client.close()
        await self.pubmed_client.close()
        await self.news_client.close()


# Convenience function for route handlers
async def get_term_triangulation(term: str, category: Optional[str] = None) -> dict:
    """Get triangulation data for a term."""
    aggregator = ExternalDataAggregator()
    try:
        return await aggregator.get_triangulation_data(term, category)
    finally:
        await aggregator.close()
