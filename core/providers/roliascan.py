"""
RoliaScan Provider Engine.
Scrapes manga, manhwa, and chapters from https://roliascan.xyz/
Supports batch-paginated chapter fetching, search indices, and high-resolution webtoon panels.
"""

import urllib.parse
from bs4 import BeautifulSoup
from typing import Optional

from .base import BaseProvider
from ..models import Manga, Chapter


class RoliaScanProvider(BaseProvider):
    """
    Provider implementation for RoliaScan (https://roliascan.xyz/).
    Features fast search, offset-based chapter batch pagination, and webtoon reader scraping.
    """

    def __init__(self, name: str = "RoliaScan (Primary Manhwa)", base_url: str = "https://roliascan.xyz"):
        super().__init__(name=name, base_url=base_url)

    def search(self, query: str) -> list[Manga]:
        """Searches RoliaScan database by title."""
        results: list[Manga] = []
        encoded_query = urllib.parse.quote_plus(query.strip())
        search_url = f"{self.base_url}/search?q={encoded_query}"

        try:
            resp = self.session.get(search_url, timeout=12)
            if resp.status_code != 200:
                return results

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("article.row-card")

            for card in cards:
                title_elem = card.select_one(".row-card__title")
                if not title_elem:
                    continue

                title = self.clean_text(title_elem.text)
                href = title_elem.get("href", "").strip()
                if not href:
                    continue

                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                manga_id = href.rstrip("/").split("/")[-1]

                # Cover image
                poster_img = card.select_one(".row-card__poster img")
                cover_url = ""
                if poster_img:
                    cover_url = (
                        poster_img.get("data-src")
                        or poster_img.get("src")
                        or poster_img.get("data-lazy-src")
                        or ""
                    ).strip()

                # Type / Status
                type_pill = card.select_one(".type-pill")
                manga_type = self.clean_text(type_pill.text) if type_pill else "Manhwa"

                results.append(
                    Manga(
                        id=manga_id,
                        title=title,
                        url=full_url,
                        provider=self.name,
                        cover_url=cover_url,
                        status=manga_type,
                        genres=[manga_type],
                    )
                )

        except Exception:
            pass

        return results

    def get_chapters(self, manga: Manga) -> list[Chapter]:
        """
        Retrieves all chapters for the given manga from RoliaScan.
        Uses RoliaScan's offset-based chapter batch endpoint (/manga/{id}/chapters?lang=EN&offset=N)
        with automatic pagination to retrieve all available chapters.
        """
        chapters: list[Chapter] = []
        seen_urls = set()
        manga_slug = manga.url.rstrip("/").split("/")[-1]

        # RoliaScan uses batching with offset=0, 200, 400...
        offset = 0
        batch_size = 200
        headers = {"X-Requested-With": "XMLHttpRequest"}

        while True:
            batch_url = f"{self.base_url}/manga/{manga_slug}/chapters?lang=EN&offset={offset}"
            try:
                resp = self.session.get(batch_url, headers=headers, timeout=15)
                if resp.status_code != 200 or not resp.text.strip():
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                links = soup.find_all("a", href=lambda h: h and "/read/" in h)

                if not links:
                    break

                batch_added = 0
                for a in links:
                    href = a.get("href", "").strip()
                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)
                    batch_added += 1

                    full_ch_url = href if href.startswith("http") else f"{self.base_url}{href}"
                    raw_text = self.clean_text(a.get("title") or a.text)
                    ch_num = self.extract_chapter_number(raw_text or href)
                    raw_num_str = f"{ch_num:g}" if ch_num > 0 else "0"

                    ch_id = href.rstrip("/").split("/")[-1]

                    chapters.append(
                        Chapter(
                            id=ch_id,
                            number=ch_num,
                            raw_number=raw_num_str,
                            title=raw_text or f"Chapter {raw_num_str}",
                            url=full_ch_url,
                            manga_title=manga.title,
                            provider=self.name,
                        )
                    )

                if len(links) < batch_size or batch_added == 0:
                    break

                offset += batch_size
                if offset >= 2000:  # Safety boundary
                    break

            except Exception:
                break

        # Fallback to main manga page if AJAX returned nothing
        if not chapters:
            try:
                resp = self.session.get(manga.url, timeout=15)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    links = soup.select("ul.chapter-list-item a, section.m-list a[href*='/read/']")
                    for a in links:
                        href = a.get("href", "").strip()
                        if not href or href in seen_urls:
                            continue
                        seen_urls.add(href)

                        full_ch_url = href if href.startswith("http") else f"{self.base_url}{href}"
                        raw_text = self.clean_text(a.get("title") or a.text)
                        ch_num = self.extract_chapter_number(raw_text or href)
                        raw_num_str = f"{ch_num:g}" if ch_num > 0 else "0"
                        ch_id = href.rstrip("/").split("/")[-1]

                        chapters.append(
                            Chapter(
                                id=ch_id,
                                number=ch_num,
                                raw_number=raw_num_str,
                                title=raw_text or f"Chapter {raw_num_str}",
                                url=full_ch_url,
                                manga_title=manga.title,
                                provider=self.name,
                            )
                        )
            except Exception:
                pass

        # Sort chapters ascending by numerical order (Chapter 1, 2, 3...)
        chapters.sort(key=lambda c: (c.number, c.raw_number))
        return chapters

    def get_chapter_pages(self, chapter: Chapter) -> list[str]:
        """
        Fetches the direct high-resolution webtoon image links from RoliaScan reader.
        """
        page_urls: list[str] = []
        headers = {"Referer": self.base_url}

        try:
            resp = self.session.get(chapter.url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return page_urls

            soup = BeautifulSoup(resp.text, "html.parser")
            img_elements = soup.select("section.chapter-reader img, .reader-area img, .reading-content img, figure img")

            seen_urls = set()
            for img in img_elements:
                src = (
                    img.get("data-src")
                    or img.get("src")
                    or img.get("data-lazy-src")
                    or ""
                ).strip()

                if not src:
                    continue

                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = self.base_url + src

                lower_src = src.lower()
                # Skip site UI icons or logos
                if any(bad in lower_src for bad in ["logo", "banner", "advertisement", "icon", ".svg"]):
                    continue

                if src not in seen_urls:
                    seen_urls.add(src)
                    page_urls.append(src)

        except Exception:
            pass

        return page_urls
