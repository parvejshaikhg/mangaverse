"""
Automated Test Suite for MangaVerse Downloader.
Verifies providers, chapter scraping, multi-threaded downloading,
and CBZ/PDF packaging end-to-end.
"""

import sys
import unittest
from pathlib import Path
import zipfile
from PIL import Image

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import (
    get_provider,
    list_providers,
    DownloadOptions,
    MangaDownloader,
)


class TestMangaVerse(unittest.TestCase):
    """Test cases for MangaVerse components."""

    def test_01_provider_registry(self):
        """Verifies that all registered providers are properly initialized."""
        providers = list_providers()
        self.assertIn("roliascan", providers)
        self.assertIn("mangaread", providers)
        self.assertIn("manhwatop", providers)
        self.assertIn("mangadex", providers)

    def test_02_search_roliascan(self):
        """Tests searching manhwa on RoliaScan provider."""
        provider = get_provider("roliascan")
        results = provider.search("Nano Machine")
        self.assertGreater(len(results), 0, "Should find at least 1 result for Nano Machine")
        first_manga = results[0]
        self.assertTrue(len(first_manga.title) > 0)
        self.assertTrue(first_manga.url.startswith("http"))

    def test_03_fetch_chapters(self):
        """Tests chapter index scraping."""
        provider = get_provider("mangaread")
        results = provider.search("Solo Leveling")
        self.assertTrue(results)
        chapters = provider.get_chapters(results[0])
        self.assertGreater(len(chapters), 0, "Should retrieve at least one chapter")
        self.assertIsNotNone(chapters[0].number)

    def test_04_download_and_export_cbz(self):
        """Tests downloading 1 chapter and exporting to valid CBZ archive."""
        provider = get_provider("mangaread")
        results = provider.search("Solo Leveling")
        self.assertTrue(results)
        chapters = provider.get_chapters(results[0])
        self.assertTrue(chapters)

        test_output_dir = PROJECT_ROOT / "test_output"
        options = DownloadOptions(
            output_dir=str(test_output_dir),
            format="cbz",
            max_workers=3,
        )

        downloader = MangaDownloader(provider=provider, options=options)
        # Download the first chapter (chapter 0 or 1)
        sample_ch = chapters[0]
        exported_path = downloader.download_chapter(
            chapter=sample_ch,
            manga=results[0],
            chapter_idx=1,
            total_chapters=1,
        )

        self.assertIsNotNone(exported_path, "Exported CBZ path should not be None")
        self.assertTrue(exported_path.exists(), f"File {exported_path} should exist on disk")
        self.assertTrue(exported_path.name.endswith(".cbz"), "File should have .cbz extension")
        self.assertGreater(exported_path.stat().st_size, 1024, "File size should be > 1KB")

        # Verify CBZ is a valid ZIP archive containing images
        with zipfile.ZipFile(exported_path, "r") as zf:
            namelist = zf.namelist()
            self.assertGreater(len(namelist), 0, "CBZ archive should contain image files")
            print(f"\n[Test] CBZ Verified successfully! Contains {len(namelist)} pages, size: {exported_path.stat().st_size // 1024} KB")

    def test_05_download_and_export_pdf(self):
        """Tests exporting to valid PDF document."""
        provider = get_provider("mangaread")
        results = provider.search("Solo Leveling")
        self.assertTrue(results)
        chapters = provider.get_chapters(results[0])
        self.assertTrue(chapters)

        test_output_dir = PROJECT_ROOT / "test_output"
        options = DownloadOptions(
            output_dir=str(test_output_dir),
            format="pdf",
            max_workers=3,
        )

        downloader = MangaDownloader(provider=provider, options=options)
        sample_ch = chapters[0]
        exported_path = downloader.download_chapter(
            chapter=sample_ch,
            manga=results[0],
            chapter_idx=1,
            total_chapters=1,
        )

        self.assertIsNotNone(exported_path)
        self.assertTrue(exported_path.exists())
        self.assertTrue(exported_path.name.endswith(".pdf"))
        self.assertGreater(exported_path.stat().st_size, 1024)
        print(f"[Test] PDF Verified successfully! Size: {exported_path.stat().st_size // 1024} KB\n")


if __name__ == "__main__":
    unittest.main()
