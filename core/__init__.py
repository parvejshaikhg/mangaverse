"""
Core package for Manga & Manhwa Downloader.
"""

from .models import Manga, Chapter, DownloadOptions, ProgressUpdate
from .downloader import MangaDownloader
from .exporter import ChapterExporter
from .providers import get_provider, list_providers, detect_provider_from_url

__all__ = [
    "Manga",
    "Chapter",
    "DownloadOptions",
    "ProgressUpdate",
    "MangaDownloader",
    "ChapterExporter",
    "get_provider",
    "list_providers",
    "detect_provider_from_url",
]
