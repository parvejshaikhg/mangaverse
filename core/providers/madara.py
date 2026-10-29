"""
Madara Theme Provider Engine.
Supports numerous manhwa/manga aggregator websites built on the popular WordPress Madara theme,
such as MangaRead, ManhwaTop, and similar webtoon sources.
"""

import urllib.parse
from bs4 import BeautifulSoup
from typing import Optional

from .base import BaseProvider
from ..models import Manga, Chapter


class MadaraProvider(BaseProvider):
    """
    Scraper engine for websites using the Madara Manga theme.
    Handles dynamic AJAX chapter listings, lazy-loaded webtoon images,
    and search index queries.
    """

    def __init__(self, name: str, base_url: str):
        super().__init__(name=name, base_url=base_url)

    def search(self, query: str) -> list[Manga]:
        """
        Searches the Madara site for titles matching the query.
        Uses the standard wp-manga search query parameters.
        """
        encoded_query = urllib.parse.quote_plus(query.strip())
        search_url = f"{self.base_url}/?s={encoded_query}&post_type=wp-manga"

        results: list[Manga] = []
        try:
            resp = self.session.get(search_url, timeout=12)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".c-tabs-item__content, .row.c-tabs-item__content")

            for item in items:
                title_elem = item.select_one(".post-title a, h3 a, h4 a")
                if not title_elem:
                    continue

                title = self.clean_text(title_elem.text)
                url = title_elem.get("href", "").strip()
                if not url:
                    continue

                # Cover image
                cover_elem = item.select_one(".tab-thumb img, .item-thumb img")
                cover_url = ""
                if cover_elem:
                    cover_url = (
                        cover_elem.get("data-src")
                        or cover_elem.get("data-lazy-src")
                        or cover_elem.get("src")
                        or ""
                    ).strip()

                # Genres or summary
                genre_elems = item.select(".mg_genres a, .genres a")
                genres = [self.clean_text(g.text) for g in genre_elems if g.text]

                # Status
                status_elem = item.select_one(".mg_status .summary-content, .status .summary-content")
                status = self.clean_text(status_elem.text) if status_elem else "Ongoing"

                manga_id = url.rstrip("/").split("/")[-1]

                results.append(
                    Manga(
                        id=manga_id,
                        title=title,
                        url=url,
                        provider=self.name,
                        cover_url=cover_url,
                        status=status,
                        genres=genres,
                    )
                )

        except Exception as e:
            # Return whatever has been collected so far without crashing
            pass

        return results

    def get_chapters(self, manga: Manga) -> list[Chapter]:
        """
        Retrieves all chapters for the given manga.
        First attempts to fetch via Madara's AJAX endpoint (/ajax/chapters/),
        falling back to scraping the main manga page directly.
        """
        chapters: list[Chapter] = []
        manga_base_url = manga.url.rstrip("/")

        # Method 1: Madara AJAX Endpoint (fastest and includes full chapter list)
        ajax_url = f"{manga_base_url}/ajax/chapters/"
        try:
            resp = self.session.post(ajax_url, timeout=12)
            if resp.status_code == 200 and len(resp.text.strip()) > 100:
                soup = BeautifulSoup(resp.text, "html.parser")
                chapter_items = soup.select(".wp-manga-chapter a")
                if chapter_items:
                    chapters = self._parse_chapter_elements(chapter_items, manga.title)
        except Exception:
            pass

        # Method 2: Fallback to main manga page if AJAX returned nothing
        if not chapters:
            try:
                resp = self.session.get(manga.url, timeout=12)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    chapter_items = soup.select(".wp-manga-chapter a, ul.sub-chap a")
                    chapters = self._parse_chapter_elements(chapter_items, manga.title)
            except Exception:
                pass

        # Sort chapters ascending by chapter number (Chapter 1, 2, 3...)
        chapters.sort(key=lambda c: (c.number, c.raw_number))
        return chapters

    def _parse_chapter_elements(self, elements, manga_title: str) -> list[Chapter]:
        """Helper to convert parsed HTML anchor elements into Chapter objects."""
        parsed_chapters: list[Chapter] = []
        seen_urls = set()

        for a in elements:
            url = a.get("href", "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            raw_text = self.clean_text(a.text)
            ch_num = self.extract_chapter_number(raw_text)
            raw_num_str = f"{ch_num:g}" if ch_num > 0 else "0"

            ch_id = url.rstrip("/").split("/")[-1]

            parsed_chapters.append(
                Chapter(
                    id=ch_id,
                    number=ch_num,
                    raw_number=raw_num_str,
                    title=raw_text,
                    url=url,
                    manga_title=manga_title,
                    provider=self.name,
                )
            )

        return parsed_chapters

    def get_chapter_pages(self, chapter: Chapter) -> list[str]:
        """
        Fetches the direct image links for all pages in the chapter.
        Extracts lazy-loaded webtoon panels from .page-break and .reading-content.
        """
        page_urls: list[str] = []
        headers = {"Referer": self.base_url}

        try:
            resp = self.session.get(chapter.url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return page_urls

            soup = BeautifulSoup(resp.text, "html.parser")
            img_elements = soup.select(".page-break img, .reading-content img, .wp-manga-chapter-img")

            seen_urls = set()
            for img in img_elements:
                src = (
                    img.get("data-src")
                    or img.get("data-lazy-src")
                    or img.get("src")
                    or ""
                ).strip()

                if not src:
                    continue

                # Ensure URL is absolute
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = self.base_url + src

                # Filter out ads or tracking icons
                lower_src = src.lower()
                if any(bad in lower_src for bad in ["logo", "banner", "advertisement", "icon", ".svg"]):
                    continue

                if src not in seen_urls:
                    seen_urls.add(src)
                    page_urls.append(src)

        except Exception:
            pass

        return page_urls
