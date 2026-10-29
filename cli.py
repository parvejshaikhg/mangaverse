"""
Command Line Interface (CLI) for MangaVerse.
Allows power users, scripts, and headless servers to search and download manga/manhwa.
"""

import argparse
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles to prevent cp1252 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core import (
    Manga,
    get_provider,
    list_providers,
    detect_provider_from_url,
    MangaDownloader,
    DownloadOptions,
    ProgressUpdate,
)
from core.utils import get_default_download_dir


def print_progress(update: ProgressUpdate):
    """Console progress reporter."""
    if update.total_chapters > 0:
        pct = (update.chapter_index / update.total_chapters) * 100
        print(f"[{pct:5.1f}%] {update.message}")
    else:
        print(f"[*] {update.message}")


def handle_search(args):
    """Executes search and prints table to console."""
    provider = get_provider(args.source)
    print(f"\n🔎 Searching for '{args.query}' using provider '{provider.name}'...\n")
    results = provider.search(args.query)

    if not results:
        print("❌ No matching manga/manhwa found.")
        return

    print(f"Found {len(results)} matches:\n")
    print(f"{'#':<3} | {'Title':<45} | {'Status':<10} | {'URL'}")
    print("-" * 90)
    for idx, manga in enumerate(results, start=1):
        clean_t = manga.title[:42] + "..." if len(manga.title) > 42 else manga.title
        print(f"{idx:<3} | {clean_t:<45} | {manga.status:<10} | {manga.url}")
    print()


def handle_download(args):
    """Executes chapter downloads via CLI arguments."""
    provider = None
    target_url = args.target

    # Check if target is a direct URL or title search
    if target_url.startswith("http://") or target_url.startswith("https://"):
        provider = detect_provider_from_url(target_url) or get_provider(args.source)
        slug = target_url.rstrip("/").split("/")[-1]
        title = slug.replace("-", " ").title()
        manga = Manga(id=slug, title=title, url=target_url, provider=provider.name)
        print(f"Direct URL provided: {target_url} (Detected: {manga.title})")
    else:
        provider = get_provider(args.source)
        print(f"\n🔎 Searching for '{target_url}' on {provider.name}...")
        results = provider.search(target_url)
        if not results:
            print(f"❌ Could not find any series matching '{target_url}'.")
            return
        manga = results[0]

    print(f"\n📖 Selected Series: {manga.title}")
    print(f"⏳ Fetching chapter index...")
    chapters = provider.get_chapters(manga)

    if not chapters:
        print("❌ No chapters found for this title.")
        return

    print(f"Total available chapters: {len(chapters)} (Ch. {chapters[0].raw_number} to Ch. {chapters[-1].raw_number})")

    # Filter chapters
    target_chapters = []
    if args.all:
        target_chapters = chapters
    elif args.chapter is not None:
        target_chapters = [c for c in chapters if abs(c.number - args.chapter) < 0.01]
        if not target_chapters:
            print(f"❌ Chapter {args.chapter} not found.")
            return
    elif args.range:
        parts = args.range.split("-")
        if len(parts) != 2:
            print("❌ Invalid range format. Use START-END (e.g. 1-10).")
            return
        start, end = float(parts[0]), float(parts[1])
        target_chapters = [c for c in chapters if start <= c.number <= end]
        if not target_chapters:
            print(f"❌ No chapters found in range {start}-{end}.")
            return
    else:
        # Default to latest 1 chapter
        target_chapters = [chapters[-1]]
        print(f"No chapter specified. Defaulting to latest chapter (Ch. {chapters[-1].raw_number}).")

    print(f"Preparing to download {len(target_chapters)} chapter(s) to format '{args.format.upper()}'...")

    options = DownloadOptions(
        output_dir=args.output,
        format=args.format,
        max_workers=args.workers,
    )

    downloader = MangaDownloader(
        provider=provider,
        options=options,
        progress_callback=print_progress,
    )

    completed = downloader.download_chapters_batch(
        chapters=target_chapters,
        manga=manga,
    )

    print(f"\n✨ All done! Successfully saved {len(completed)} file(s) in: {Path(args.output).resolve()}\n")


def main():
    parser = argparse.ArgumentParser(
        description="MangaVerse CLI — High-performance Manga & Manhwa Downloader",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Sources command
    subparsers.add_parser("sources", help="List all available content sources")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for manga/manhwa by title")
    search_parser.add_argument("query", help="Manga or manhwa title to search")
    search_parser.add_argument(
        "--source",
        choices=list(list_providers().keys()),
        default="roliascan",
        help="Source to search from (default: roliascan)",
    )

    # Download command
    download_parser = subparsers.add_parser("download", help="Download manga/manhwa chapters")
    download_parser.add_argument("target", help="Manga title or direct series URL")
    download_parser.add_argument(
        "--source",
        choices=list(list_providers().keys()),
        default="roliascan",
        help="Source provider (default: roliascan)",
    )
    download_parser.add_argument("--chapter", type=float, help="Download a specific single chapter number")
    download_parser.add_argument("--range", help="Download chapter range (e.g. 1-10)")
    download_parser.add_argument("--all", action="store_true", help="Download all available chapters")
    download_parser.add_argument(
        "--format",
        choices=["cbz", "pdf", "images"],
        default="cbz",
        help="Export format (default: cbz)",
    )
    download_parser.add_argument(
        "--output",
        default=str(get_default_download_dir()),
        help=f"Destination directory (default: {get_default_download_dir()})",
    )
    download_parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent download threads (default: 4)",
    )

    args = parser.parse_args()

    if args.command == "sources":
        print("\nRegistered Manga & Manhwa Sources:")
        for k, v in list_providers().items():
            print(f"  • {k:<12}: {v}")
        print()
    elif args.command == "search":
        handle_search(args)
    elif args.command == "download":
        handle_download(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
