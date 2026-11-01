"""
Anime Discovery & Episode Guide module for MangaVerse.
Powered by the official AniList GraphQL API (free, open, legal, zero API key required).
Provides anime search, episode counts, airing schedules, genres, synopsis,
scores, and official streaming links.
"""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


ANILIST_API_URL = "https://graphql.anilist.co"


@dataclass
class AnimeItem:
    """Represents an anime title and its metadata."""
    id: int
    title_english: str
    title_romaji: str
    title_native: str
    format: str
    status: str
    episodes: Optional[int]
    duration: Optional[int]
    season: Optional[str]
    season_year: Optional[int]
    average_score: Optional[int]
    genres: List[str]
    description: str
    cover_image_large: str
    cover_image_medium: str
    banner_image: Optional[str]
    studios: List[str]
    next_airing_episode: Optional[int] = None
    next_airing_time_seconds: Optional[int] = None
    trailer_url: Optional[str] = None
    external_links: List[Dict[str, str]] = field(default_factory=list)

    @property
    def display_title(self) -> str:
        return self.title_english or self.title_romaji or self.title_native or "Unknown Anime"

    @property
    def score_text(self) -> str:
        return f"{self.average_score}%" if self.average_score else "N/A"

    @property
    def year_text(self) -> str:
        if self.season_year:
            return f"{self.season or ''} {self.season_year}".strip()
        return "Unknown"

    @property
    def episodes_text(self) -> str:
        if self.episodes:
            return f"{self.episodes} Episodes"
        if self.status == "RELEASING":
            return "Airing (Ongoing)"
        return "Unknown"


class AnimeService:
    """Service to interact with the AniList GraphQL API."""

    @staticmethod
    def _post_graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        req = urllib.request.Request(
            ANILIST_API_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MangaVerse/2.0 (Open-Source Comic & Anime Explorer)",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("data", {})
        except urllib.error.URLError as e:
            return {"error": str(e)}

    @classmethod
    def search_anime(cls, query: str, limit: int = 10) -> List[AnimeItem]:
        """Search for anime series by title."""
        gql = """
        query ($search: String, $perPage: Int) {
          Page(page: 1, perPage: $perPage) {
            media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
              id
              title {
                english
                romaji
                native
              }
              format
              status
              episodes
              duration
              season
              seasonYear
              averageScore
              genres
              description(asHtml: false)
              coverImage {
                large
                medium
              }
              bannerImage
              studios(isMain: true) {
                nodes {
                  name
                }
              }
              nextAiringEpisode {
                episode
                timeUntilAiring
              }
              trailer {
                id
                site
              }
              externalLinks {
                site
                url
              }
            }
          }
        }
        """
        data = cls._post_graphql(gql, {"search": query, "perPage": limit})
        media_list = data.get("Page", {}).get("media", [])
        return [cls._parse_media_item(m) for m in media_list]

    @classmethod
    def get_trending_anime(cls, limit: int = 10) -> List[AnimeItem]:
        """Fetches current trending anime globally."""
        gql = """
        query ($perPage: Int) {
          Page(page: 1, perPage: $perPage) {
            media(type: ANIME, sort: TRENDING_DESC) {
              id
              title {
                english
                romaji
                native
              }
              format
              status
              episodes
              duration
              season
              seasonYear
              averageScore
              genres
              description(asHtml: false)
              coverImage {
                large
                medium
              }
              bannerImage
              studios(isMain: true) {
                nodes {
                  name
                }
              }
              nextAiringEpisode {
                episode
                timeUntilAiring
              }
              trailer {
                id
                site
              }
              externalLinks {
                site
                url
              }
            }
          }
        }
        """
        data = cls._post_graphql(gql, {"perPage": limit})
        media_list = data.get("Page", {}).get("media", [])
        return [cls._parse_media_item(m) for m in media_list]

    @classmethod
    def get_anime_by_id(cls, anime_id: int) -> Optional[AnimeItem]:
        """Fetches detailed info for a single anime by ID."""
        gql = """
        query ($id: Int) {
          Media(id: $id, type: ANIME) {
            id
            title {
              english
              romaji
              native
            }
            format
            status
            episodes
            duration
            season
            seasonYear
            averageScore
            genres
            description(asHtml: false)
            coverImage {
              large
              medium
            }
            bannerImage
            studios(isMain: true) {
              nodes {
                name
              }
            }
            nextAiringEpisode {
              episode
              timeUntilAiring
            }
            trailer {
              id
              site
            }
            externalLinks {
              site
              url
            }
          }
        }
        """
        data = cls._post_graphql(gql, {"id": anime_id})
        media = data.get("Media")
        if media:
            return cls._parse_media_item(media)
        return None

    @staticmethod
    def _parse_media_item(m: Dict[str, Any]) -> AnimeItem:
        title = m.get("title") or {}
        cover = m.get("coverImage") or {}
        studios_data = m.get("studios", {}).get("nodes", [])
        studios = [s["name"] for s in studios_data if "name" in s]

        next_ep = m.get("nextAiringEpisode")
        next_ep_num = next_ep["episode"] if next_ep else None
        next_time = next_ep["timeUntilAiring"] if next_ep else None

        trailer = m.get("trailer")
        trailer_url = None
        if trailer and trailer.get("site") == "youtube" and trailer.get("id"):
            trailer_url = f"https://www.youtube.com/watch?v={trailer['id']}"

        links = []
        for l in m.get("externalLinks", []) or []:
            if l.get("site") and l.get("url"):
                links.append({"site": l["site"], "url": l["url"]})

        desc = m.get("description") or "No synopsis available."
        # Clean HTML tags if any slipped through
        import re
        desc = re.sub(r"<[^>]+>", "", desc).strip()

        return AnimeItem(
            id=m["id"],
            title_english=title.get("english") or "",
            title_romaji=title.get("romaji") or "",
            title_native=title.get("native") or "",
            format=m.get("format") or "TV",
            status=m.get("status") or "UNKNOWN",
            episodes=m.get("episodes"),
            duration=m.get("duration"),
            season=m.get("season"),
            season_year=m.get("seasonYear"),
            average_score=m.get("averageScore"),
            genres=m.get("genres") or [],
            description=desc,
            cover_image_large=cover.get("large") or "",
            cover_image_medium=cover.get("medium") or "",
            banner_image=m.get("bannerImage"),
            studios=studios,
            next_airing_episode=next_ep_num,
            next_airing_time_seconds=next_time,
            trailer_url=trailer_url,
            external_links=links,
        )
