"""
Provider Registry and Factory.
Manages available manga and manhwa content sources.
"""

from typing import Optional
from .base import BaseProvider
from .roliascan import RoliaScanProvider
from .madara import MadaraProvider
from .mangadex import MangaDexProvider

_PROVIDERS: dict[str, BaseProvider] = {
    "roliascan": RoliaScanProvider(name="RoliaScan (Primary Manhwa)", base_url="https://roliascan.xyz"),
    "mangaread": MadaraProvider(name="MangaRead (Top Manhwa)", base_url="https://www.mangaread.org"),
    "manhwatop": MadaraProvider(name="ManhwaTop (Webtoons)", base_url="https://manhwatop.com"),
    "mangadex": MangaDexProvider(name="MangaDex (Official API)", language="en"),
}


def get_provider(key: str) -> BaseProvider:
    """Retrieves a provider instance by its identifier key."""
    normalized = key.lower().strip()
    if normalized in _PROVIDERS:
        return _PROVIDERS[normalized]
    raise ValueError(f"Unknown provider '{key}'. Available: {list(_PROVIDERS.keys())}")


def list_providers() -> dict[str, str]:
    """Returns a dictionary of provider key -> display name."""
    return {k: p.name for k, p in _PROVIDERS.items()}


def detect_provider_from_url(url: str) -> Optional[BaseProvider]:
    """Attempts to match an input URL to one of our registered providers."""
    lower_url = url.lower()
    if "roliascan.xyz" in lower_url:
        return _PROVIDERS["roliascan"]
    elif "mangadex.org" in lower_url:
        return _PROVIDERS["mangadex"]
    elif "mangaread.org" in lower_url:
        return _PROVIDERS["mangaread"]
    elif "manhwatop.com" in lower_url:
        return _PROVIDERS["manhwatop"]
    return None
