"""
Question Surface fetcher — pulls actual human questions from Google.

Uses two SerpAPI engines:
1. google_related_questions: "People Also Ask" boxes with full questions + answer snippets
2. google_autocomplete: Autocomplete suggestions seeded with question prefixes

This is the 'narrative layer' of VIOLET — it captures how people phrase their fear,
not just the structural terms they search for.
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

from serpapi import GoogleSearch

from app.config import get_settings

logger = logging.getLogger(__name__)

# Question prefixes used to seed autocomplete with interrogative phrasing
QUESTION_PREFIXES = [
    "how do I",
    "where can I",
    "what is",
    "is it normal to",
    "can I",
    "why does",
    "what are the symptoms of",
    "what happens if",
    "how long does",
    "should I",
]


@dataclass
class QuestionResult:
    """A single question discovered from PAA or autocomplete."""

    question: str
    snippet: Optional[str] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    source_type: str = "people_also_ask"  # "people_also_ask" or "autocomplete"
    rank: int = 0


@dataclass
class TermQuestions:
    """All questions discovered for a single search term."""

    term: str
    questions: list[QuestionResult] = field(default_factory=list)


class QuestionFetcher:
    """Fetches human questions from Google PAA and autocomplete via SerpAPI."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        request_delay: float = 0.5,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.serpapi_key
        if not self.api_key:
            raise ValueError("SERPAPI_KEY is required.")
        self.request_delay = request_delay

    def _search(self, params: dict) -> dict:
        """Execute a SerpAPI search and return parsed results."""
        params["api_key"] = self.api_key
        search = GoogleSearch(params)
        return search.get_dict()

    def fetch_paa(
        self,
        term: str,
        num_pages: int = 2,
        gl: str = "us",
        hl: str = "en",
    ) -> list[QuestionResult]:
        """
        Fetch People Also Ask questions for a term.

        Uses SerpAPI's google_related_questions engine which returns actual
        interrogative phrases from Google's PAA boxes.

        Args:
            term: Search term to get PAA questions for
            num_pages: Number of pages to fetch (each returns ~4 questions)
            gl: Country code
            hl: Language code

        Returns:
            List of QuestionResult objects with question text, snippets, and sources
        """
        questions = []
        next_page_token = None

        for page in range(num_pages):
            try:
                params = {
                    "engine": "google_related_questions",
                    "q": term,
                    "gl": gl,
                    "hl": hl,
                }

                if next_page_token:
                    params["next_page_token"] = next_page_token

                results = self._search(params)
                time.sleep(self.request_delay)

                related_questions = results.get("related_questions", [])

                if not related_questions:
                    logger.debug(f"No PAA results for '{term}' (page {page + 1})")
                    break

                for i, item in enumerate(related_questions):
                    question_text = item.get("question", "")
                    if not question_text:
                        continue

                    questions.append(QuestionResult(
                        question=question_text,
                        snippet=item.get("snippet"),
                        source_title=item.get("title"),
                        source_url=item.get("link"),
                        source_type="people_also_ask",
                        rank=len(questions) + 1,
                    ))

                # Get pagination token for next page
                # The token comes from the first question's next_page_token field
                if related_questions:
                    next_page_token = related_questions[0].get("next_page_token")
                    if not next_page_token:
                        break
                else:
                    break

            except Exception as e:
                logger.warning(f"Failed to fetch PAA for '{term}' (page {page + 1}): {e}")
                break

        logger.debug(f"Got {len(questions)} PAA questions for '{term}'")
        return questions

    def fetch_question_completions(
        self,
        term: str,
        gl: str = "us",
        hl: str = "en",
        max_prefixes: int = 5,
    ) -> list[QuestionResult]:
        """
        Fetch autocomplete suggestions seeded with question prefixes.

        Combines the term with interrogative prefixes like "how do I", "where can I",
        "is it normal to", etc. to discover natural language questions people actually type.

        Args:
            term: Base search term
            gl: Country code
            hl: Language code
            max_prefixes: Maximum number of question prefixes to try

        Returns:
            List of QuestionResult objects from autocomplete
        """
        questions = []
        seen_questions = set()

        for prefix in QUESTION_PREFIXES[:max_prefixes]:
            try:
                query = f"{prefix} {term}"
                params = {
                    "engine": "google_autocomplete",
                    "q": query,
                    "gl": gl,
                    "hl": hl,
                }

                results = self._search(params)
                time.sleep(self.request_delay)

                suggestions = results.get("suggestions", [])

                for suggestion in suggestions:
                    text = suggestion.get("value", "")
                    if not text or text.lower() in seen_questions:
                        continue

                    # Only keep suggestions that look like questions
                    # (start with a question word or contain a question mark)
                    text_lower = text.lower()
                    is_question = (
                        text.endswith("?")
                        or any(text_lower.startswith(w) for w in [
                            "how", "what", "where", "when", "why", "who",
                            "is", "are", "can", "should", "does", "do", "will",
                        ])
                    )

                    if is_question:
                        seen_questions.add(text_lower)
                        questions.append(QuestionResult(
                            question=text,
                            snippet=None,
                            source_title=None,
                            source_url=None,
                            source_type="autocomplete",
                            rank=len(questions) + 1,
                        ))

            except Exception as e:
                logger.warning(f"Failed autocomplete for '{prefix} {term}': {e}")
                continue

        logger.debug(f"Got {len(questions)} autocomplete questions for '{term}'")
        return questions

    def fetch_all_questions(
        self,
        term: str,
        paa_pages: int = 2,
        max_prefixes: int = 5,
        gl: str = "us",
        hl: str = "en",
    ) -> TermQuestions:
        """
        Fetch all questions for a term from both PAA and autocomplete.

        Combines and deduplicates results from both sources, prioritizing
        PAA questions (which have richer metadata) over autocomplete.

        Args:
            term: Search term
            paa_pages: Number of PAA pages to fetch
            max_prefixes: Number of autocomplete prefixes to try
            gl: Country code
            hl: Language code

        Returns:
            TermQuestions with deduplicated questions from all sources
        """
        logger.info(f"Fetching questions for: {term}")

        # Fetch from both sources
        paa_questions = self.fetch_paa(term, num_pages=paa_pages, gl=gl, hl=hl)
        autocomplete_questions = self.fetch_question_completions(
            term, gl=gl, hl=hl, max_prefixes=max_prefixes,
        )

        # Deduplicate: PAA takes priority (has snippets + sources)
        seen = set()
        all_questions = []

        for q in paa_questions:
            normalized = q.question.lower().strip().rstrip("?")
            if normalized not in seen:
                seen.add(normalized)
                all_questions.append(q)

        for q in autocomplete_questions:
            normalized = q.question.lower().strip().rstrip("?")
            if normalized not in seen:
                seen.add(normalized)
                all_questions.append(q)

        # Re-rank after deduplication
        for i, q in enumerate(all_questions):
            q.rank = i + 1

        return TermQuestions(term=term, questions=all_questions)
