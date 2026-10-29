"""
MangaDex Official API Provider.
Leverages the official MangaDex v5 REST API (api.mangadex.org) for high-fidelity manga,
cover art, scanlation metadata, and MangaDex@Home distributed image delivery.
"""

from typing import Optional
from .base import BaseProvider
from ..models import Manga, Chapter


class MangaDexProvider(BaseProvider):
    """
    Provider utilizing the official MangaDex REST API.
    Features rich metadata, cover art resolution, and multi-language support.
    """

    API_BASE = "https://api.mangadex.org"
    COVERS_BASE = "https://uploads.mangadex.org/covers"

    def __init__(self, name: str = "mangadex", language: str = "en"):
        super().__init__(name=name, base_url=self.API_BASE)
        self.language = language

    def search(self, query: str) -> list[Manga]:
        """Searches MangaDex database using the official v5 API."""
        results: list[Manga] = []
        url = f"{self.API_BASE}/manga"
        params = {
            "title": query.strip(),
            "limit": 15,
            "order[relevance]": "desc",
            "includes[]": ["cover_art"],
            "contentRating[]": ["safe", "suggestive", "erotica"],
        }

        try:
            resp = self.session.get(url, params=params, timeout=12)
            if resp.status_code != 200:
                return results

            data = resp.json().get("data", [])
            for item in data:
                manga_id = item.get("id", "")
                attrs = item.get("attributes", {})

                # Extract best title (prefer English, fallback to first available)
                title_dict = attrs.get("title", {})
                title = title_dict.get("en")
                if not title:
                    alt_titles = attrs.get("altTitles", [])
                    for alt in alt_titles:
                        if "en" in alt:
                            title = alt["en"]
                            break
                if not title:
                    title = next(iter(title_dict.values())) if title_dict else "Unknown Title"

                # Extract cover filename from relationships
                cover_filename = ""
                for rel in item.get("relationships", []):
                    if rel.get("type") == "cover_art":
                        cover_filename = rel.get("attributes", {}).get("fileName", "")
                        break

                cover_url = ""
                if cover_filename and manga_id:
                    cover_url = f"{self.COVERS_BASE}/{manga_id}/{cover_filename}.256.jpg"

                # Description
                desc_dict = attrs.get("description", {})
                desc = desc_dict.get("en", "")

                status = attrs.get("status", "unknown").capitalize()

                results.append(
                    Manga(
                        id=manga_id,
                        title=title,
                        url=f"https://mangadex.org/title/{manga_id}",
                        provider=self.name,
                        cover_url=cover_url,
                        description=desc,
                        status=status,
                    )
                )

        except Exception:
            pass

        return results

    def get_chapters(self, manga: Manga) -> list[Chapter]:
        """
        Fetches all available hosted chapters for a manga from MangaDex.
        Paginates feed results and filters out external licensed links.
        Deduplicates multiple scanlation groups by chapter number.
        """
        chapters_by_num: dict[float, Chapter] = {}
        offset = 0
        limit = 100

        while True:
            feed_url = f"{self.API_BASE}/manga/{manga.id}/feed"
            params = {
                "translatedLanguage[]": [self.language],
                "order[chapter]": "asc",
                "limit": limit,
                "offset": offset,
            }

            try:
                resp = self.session.get(feed_url, params=params, timeout=12)
                if resp.status_code != 200:
                    break

                json_data = resp.json()
                data = json_data.get("data", [])
                if not data:
                    break

                for item in data:
                    attrs = item.get("attributes", {})
                    # Skip external redirect chapters (Webnovel, MangaPlus, etc.)
                    if attrs.get("externalUrl") or attrs.get("pages", 0) <= 0:
                        continue

                    chap_str = attrs.get("chapter") or "0"
                    try:
                        chap_num = float(chap_str)
                    except ValueError:
                        chap_num = 0.0

                    chap_id = item.get("id", "")
                    chap_title = attrs.get("title") or ""
                    release_date = attrs.get("publishAt", "")

                    chapter = Chapter(
                        id=chap_id,
                        number=chap_num,
                        raw_number=chap_str,
                        title=chap_title,
                        url=f"https://mangadex.org/chapter/{chap_id}",
                        manga_title=manga.title,
                        provider=self.name,
                        release_date=release_date,
                    )

                    # Deduplicate: if duplicate chapter exists, keep the latest one
                    if chap_num not in chapters_by_num:
                        chapters_by_num[chap_num] = chapter
                    else:
                        existing = chapters_by_num[chap_num]
                        if release_date > existing.release_date:
                            chapters_by_num[chap_num] = chapter

                total = json_data.get("total", 0)
                offset += limit
                if offset >= total or offset >= 1000:  # Safety cap at 1000 chapters
                    break

            except Exception:
                break

        # Sort chapters ascending
        sorted_chapters = sorted(chapters_by_num.values(), key=lambda c: (c.number, c.raw_number))
        return sorted_chapters

    def get_chapter_pages(self, chapter: Chapter) -> list[str]:
        """
        Retrieves direct image URLs from MangaDex@Home server for the given chapter.
        """
        page_urls: list[str] = []
        url = f"{self.API_BASE}/at-home/server/{chapter.id}"

        try:
            resp = self.session.get(url, timeout=12)
            if resp.status_code != 200:
                return page_urls

            data = resp.json()
            base_url = data.get("baseUrl", "")
            chap_data = data.get("chapter", {})
            hash_code = chap_data.get("hash", "")
            filenames = chap_data.get("data", [])

            if base_url and hash_code and filenames:
                for fn in filenames:
                    page_urls.append(f"{base_url}/data/{hash_code}/{fn}")

        except Exception:
            pass

        return page_urls
