"""
Core Download Engine.
Orchestrates multi-threaded image downloads, rate limiting, error recovery,
and progress reporting across single chapters or batch chapter ranges.
"""

import os
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional

import requests

from .models import Manga, Chapter, DownloadOptions, ProgressUpdate
from .providers.base import BaseProvider
from .exporter import ChapterExporter


class MangaDownloader:
    """
    High-performance download manager for manga and manhwa chapters.
    Features:
    - Multi-threaded page downloading via ThreadPoolExecutor
    - Resilient retry logic for flaky network connections
    - Clean cancellation mechanics via threading.Event
    - Real-time progress callback hooks for GUI and CLI interfaces
    """

    def __init__(
        self,
        provider: BaseProvider,
        options: DownloadOptions,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
    ):
        self.provider = provider
        self.options = options
        self.progress_callback = progress_callback
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        """Signals the downloader to stop processing remaining chapters and pages."""
        self.cancel_event.set()

    def _notify(self, update: ProgressUpdate) -> None:
        """Emits progress updates to the subscriber."""
        if self.progress_callback:
            try:
                self.progress_callback(update)
            except Exception:
                pass

    def download_chapter(
        self,
        chapter: Chapter,
        manga: Manga,
        chapter_idx: int = 1,
        total_chapters: int = 1,
    ) -> Optional[Path]:
        """
        Downloads all pages of a single chapter, verifies content,
        and packages into the requested format (CBZ, PDF, Images).
        """
        if self.cancel_event.is_set():
            return None

        self._notify(
            ProgressUpdate(
                state="downloading",
                message=f"Fetching page links for {chapter.clean_title}...",
                chapter_index=chapter_idx,
                total_chapters=total_chapters,
            )
        )

        page_urls = self.provider.get_chapter_pages(chapter)
        if not page_urls:
            self._notify(
                ProgressUpdate(
                    state="error",
                    message=f"No image pages found for {chapter.clean_title}.",
                    chapter_index=chapter_idx,
                    total_chapters=total_chapters,
                )
            )
            return None

        total_pages = len(page_urls)
        self._notify(
            ProgressUpdate(
                state="downloading",
                message=f"Downloading {total_pages} pages for {chapter.clean_title}...",
                chapter_index=chapter_idx,
                total_chapters=total_chapters,
                page_index=0,
                total_pages=total_pages,
            )
        )

        temp_chapter_dir = Path(tempfile.mkdtemp(prefix="manga_dl_"))
        downloaded_count = 0

        try:
            # Multi-threaded concurrent download of chapter pages
            with ThreadPoolExecutor(max_workers=self.options.max_workers) as executor:
                future_to_page = {
                    executor.submit(
                        self._download_single_page, url, idx, temp_chapter_dir
                    ): idx
                    for idx, url in enumerate(page_urls, start=1)
                }

                for future in as_completed(future_to_page):
                    if self.cancel_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        self._notify(
                            ProgressUpdate(
                                state="cancelled",
                                message="Download cancelled by user.",
                                chapter_index=chapter_idx,
                                total_chapters=total_chapters,
                            )
                        )
                        return None

                    page_idx = future_to_page[future]
                    success = future.result()
                    if success:
                        downloaded_count += 1
                        self._notify(
                            ProgressUpdate(
                                state="downloading",
                                message=f"Downloaded page {downloaded_count}/{total_pages}",
                                chapter_index=chapter_idx,
                                total_chapters=total_chapters,
                                page_index=downloaded_count,
                                total_pages=total_pages,
                            )
                        )

            if downloaded_count < total_pages * 0.8:  # If more than 20% failed
                raise IOError(
                    f"Too many pages failed ({downloaded_count}/{total_pages} succeeded)"
                )

            # Exporter conversion
            self._notify(
                ProgressUpdate(
                    state="converting",
                    message=f"Packaging {chapter.clean_title} to {self.options.format.upper()}...",
                    chapter_index=chapter_idx,
                    total_chapters=total_chapters,
                    page_index=total_pages,
                    total_pages=total_pages,
                )
            )

            # Destination directory: output_dir / Manga Title / Chapter Name
            manga_dir = Path(self.options.output_dir) / manga.clean_title
            exported_path = ChapterExporter.export(
                temp_dir=temp_chapter_dir,
                destination_folder=manga_dir,
                file_stem=chapter.clean_title,
                export_format=self.options.format,
            )

            return exported_path

        finally:
            # Always clean up temporary files
            shutil.rmtree(temp_chapter_dir, ignore_errors=True)

    def _download_single_page(self, url: str, index: int, target_dir: Path) -> bool:
        """Downloads a single image page with retry mechanisms."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": self.provider.base_url,
        }

        # Determine extension
        ext = ".jpg"
        for candidate in [".jpg", ".jpeg", ".png", ".webp"]:
            if candidate in url.lower():
                ext = candidate
                break

        target_file = target_dir / f"{index:03d}{ext}"

        for attempt in range(1, self.options.max_retries + 1):
            if self.cancel_event.is_set():
                return False

            try:
                time.sleep(self.options.delay_between_requests)
                resp = requests.get(
                    url,
                    headers=headers,
                    timeout=self.options.timeout,
                    stream=True,
                )

                if resp.status_code == 200:
                    content = resp.content
                    if len(content) > 1024:  # At least 1KB to ensure it's a real image
                        with open(target_file, "wb") as f:
                            f.write(content)
                        return True

            except Exception:
                time.sleep(0.5 * attempt)

        return False

    def download_chapters_batch(
        self,
        chapters: list[Chapter],
        manga: Manga,
    ) -> list[Path]:
        """Downloads a collection of chapters in sequence."""
        self.cancel_event.clear()
        total_chapters = len(chapters)
        completed_paths: list[Path] = []

        self._notify(
            ProgressUpdate(
                state="downloading",
                message=f"Starting batch download of {total_chapters} chapters...",
                chapter_index=0,
                total_chapters=total_chapters,
            )
        )

        for idx, chapter in enumerate(chapters, start=1):
            if self.cancel_event.is_set():
                break

            try:
                out_path = self.download_chapter(
                    chapter=chapter,
                    manga=manga,
                    chapter_idx=idx,
                    total_chapters=total_chapters,
                )
                if out_path:
                    completed_paths.append(out_path)
            except Exception as e:
                self._notify(
                    ProgressUpdate(
                        state="error",
                        message=f"Error downloading {chapter.clean_title}: {e}",
                        chapter_index=idx,
                        total_chapters=total_chapters,
                        error=e,
                    )
                )

        if self.cancel_event.is_set():
            self._notify(
                ProgressUpdate(
                    state="cancelled",
                    message="Batch download cancelled.",
                    chapter_index=len(completed_paths),
                    total_chapters=total_chapters,
                )
            )
        else:
            self._notify(
                ProgressUpdate(
                    state="completed",
                    message=f"Successfully downloaded {len(completed_paths)}/{total_chapters} chapters!",
                    chapter_index=total_chapters,
                    total_chapters=total_chapters,
                )
            )

        return completed_paths
