"""
Abstract Base Provider for Manga & Manhwa Downloader.
Defines the standard interface that all scraper and API providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models import Manga, Chapter


class BaseProvider(ABC):
    """
    Abstract Base Class for Manga/Manhwa content providers.
    Uses Strategy Pattern: each website/API implements its own parser
    while exposing the exact same interface to the downloader engine.
    """

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.session = self._create_resilient_session()

    def _create_resilient_session(self) -> requests.Session:
        """
        Creates a requests Session with automatic exponential backoff retries
        and modern browser headers to minimize connection drops.
        """
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        return session

    @abstractmethod
    def search(self, query: str) -> list[Manga]:
        """Searches the provider for manga/manhwa matching the query."""
        pass

    @abstractmethod
    def get_chapters(self, manga: Manga) -> list[Chapter]:
        """Fetches all available chapters for a given manga series."""
        pass

    @abstractmethod
    def get_chapter_pages(self, chapter: Chapter) -> list[str]:
        """Fetches direct URLs of all image pages for a given chapter."""
        pass

    @staticmethod
    def extract_chapter_number(raw_text: str) -> float:
        """
        Extracts numerical chapter number from text strings like:
        'Chapter 123.5', 'Ch. 45', '#12', 'Solo Leveling 200'
        Defaults to 0.0 if not parsable.
        """
        if not raw_text:
            return 0.0
            
        # Match patterns like "chapter 12.5" or "ch. 12"
        match = re.search(r'(?:chapter|ch\.?|chap\.?)\s*([0-9]+(?:\.[0-9]+)?)', raw_text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
                
        # Fallback to any standalone float/integer
        numbers = re.findall(r'[0-9]+(?:\.[0-9]+)?', raw_text)
        if numbers:
            try:
                return float(numbers[-1])
            except ValueError:
                pass
                
        return 0.0

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """Strips HTML entities and trims whitespace."""
        if not text:
            return ""
        return " ".join(text.replace("\xa0", " ").split()).strip()
