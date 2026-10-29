"""
Data models for the Manga & Manhwa Downloader.
Provides type-safe dataclasses for manga metadata, chapters, download configurations,
and progress tracking events.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import re


@dataclass
class Manga:
    """Represents a manga/manhwa series."""
    id: str
    title: str
    url: str
    provider: str
    cover_url: str = ""
    description: str = ""
    status: str = "Unknown"
    genres: list[str] = field(default_factory=list)

    @property
    def clean_title(self) -> str:
        """Sanitizes the title for filesystem folder naming."""
        sanitized = re.sub(r'[\\/*?:"<>|]', "", self.title)
        return " ".join(sanitized.split()).strip()


@dataclass
class Chapter:
    """Represents an individual chapter of a manga/manhwa series."""
    id: str
    number: float  # Numerical chapter number for sorting (e.g. 1.0, 15.5)
    raw_number: str  # Original string representation (e.g. "1", "15.5", "Prologue")
    title: str
    url: str
    manga_title: str
    provider: str
    scanlator: str = ""
    release_date: str = ""

    @property
    def clean_title(self) -> str:
        """Generates a clean, readable name for file saving."""
        if self.title and self.title.strip() and self.title.lower() != f"chapter {self.raw_number}".lower():
            name = f"Chapter {self.raw_number} - {self.title}"
        else:
            name = f"Chapter {self.raw_number}"
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()


@dataclass
class DownloadOptions:
    """Configuration options for chapter downloads."""
    output_dir: str
    format: Literal["cbz", "pdf", "images"] = "cbz"
    max_workers: int = 4
    delay_between_requests: float = 0.1
    max_retries: int = 3
    timeout: int = 20


@dataclass
class ProgressUpdate:
    """Event emitted during downloading to update the UI or CLI."""
    state: Literal["idle", "searching", "fetching_chapters", "downloading", "converting", "completed", "error", "cancelled"]
    message: str = ""
    chapter_index: int = 0
    total_chapters: int = 0
    page_index: int = 0
    total_pages: int = 0
    error: Optional[Exception] = None
