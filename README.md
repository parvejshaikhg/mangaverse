# 📚 MangaVerse — Universal Manga & Manhwa Downloader

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20macOS%20%7C%20Linux-8B5CF6?style=for-the-badge)]()
[![UI](https://img.shields.io/badge/Interfaces-Desktop%20GUI%20%7C%20Web%20UI%20%7C%20CLI-06B6D4?style=for-the-badge)]()
[![License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)](LICENSE)

**MangaVerse** is a modern, high-speed multi-threaded comic archiver that allows you to search, stream, and download manga and manhwa chapters across **Windows**, **macOS**, and **Linux**.

Chapters can be exported into standard digital comic formats (**CBZ** for e-readers, **PDF** for documents, or raw sequentially numbered image folders).

---

## 🌟 Supported Platforms

| Platform | Interface | Launch Command | Default Save Path |
| :--- | :--- | :--- | :--- |
| **🪟 Windows** | Desktop GUI / Web / CLI | Double-click `run_windows.bat` | `~/Downloads/MangaVerse` |
| **🍎 macOS** | Desktop GUI / Web / CLI | `./run_unix.sh` | `~/Downloads/MangaVerse` |
| **🐧 Linux** | Desktop GUI / Web / CLI | `./run_unix.sh` | `~/Downloads/MangaVerse` |

---

## ✨ Features

- **🎨 Multi-Interface Support**:
  - **Desktop GUI**: Sleek Cyber-Dark desktop interface built with CustomTkinter.
  - **Embedded Web UI**: Zero-dependency embedded web server (`python main.py --web`) accessible in any modern browser.
  - **Terminal CLI**: Scriptable command-line interface for headless servers and automation.
- **⚡ Multi-Threaded Engine**: Concurrent image downloads using `concurrent.futures.ThreadPoolExecutor` for high-speed page retrieval.
- **🔄 Multi-Source Catalog**:
  - **RoliaScan (Primary)**: High-resolution official manhwa releases directly from [roliascan.xyz](https://roliascan.xyz/) with batch-paginated chapter indexing.
  - **MangaRead**: High-resolution Korean manhwa & action series.
  - **ManhwaTop**: Extensive webtoon catalog with full archive chapters.
  - **MangaDex**: Official REST API v5 support with global scanlations and multi-language support.
  - **Direct URL**: Paste any supported series URL to download directly.
- **📦 Multi-Format Packaging**:
  - **CBZ (Comic Book Zip)**: Compatible with Panels, CDisplayEx, YACReader.
  - **PDF**: Unified document with automatic color space conversion (RGB normalization via Pillow).
  - **Raw Images**: Sequential folder of high-resolution `.jpg` / `.png` / `.webp` panels.

---

## 🚀 Quick Start by Operating System

### 🪟 Windows Setup

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/parvejshaikhg/mangaverse.git
   cd mangaverse
   ```
2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Run the app**:
   - Double-click **`run_windows.bat`** (or run `python main.py`).

---

### 🍎 macOS Setup

1. **Clone & install**:
   ```bash
   git clone https://github.com/parvejshaikhg/mangaverse.git
   cd mangaverse
   pip3 install -r requirements.txt
   ```
2. **Launch**:
   ```bash
   chmod +x run_unix.sh
   ./run_unix.sh
   ```
   *(Or launch the Web UI in your browser: `python3 main.py --web`)*

---

### 🐧 Linux Setup (Ubuntu / Debian / Arch / Fedora)

1. **Install Tkinter & dependencies**:
   ```bash
   # Debian / Ubuntu / Mint:
   sudo apt update && sudo apt install -y python3 python3-pip python3-tk

   # Arch Linux:
   sudo pacman -S python python-pip tk

   # Fedora:
   sudo dnf install python3 python3-pip python3-tkinter
   ```
2. **Clone & launch**:
   ```bash
   git clone https://github.com/parvejshaikhg/mangaverse.git
   cd mangaverse
   pip install -r requirements.txt
   chmod +x run_unix.sh
   ./run_unix.sh
   ```
   *(For headless servers without a GUI display, run `python3 main.py --web`)*

---

## 💻 Command Line Interface (CLI)

MangaVerse includes a scriptable CLI for automation and headless environments:

```bash
# List all registered content sources
python main.py sources

# Search for any title
python main.py search "Solo Leveling"

# Download Chapter 1 to CBZ
python main.py download "Nano Machine" --chapter 336 --format cbz

# Download a range of chapters (e.g. 1 to 10) to PDF
python main.py download "Solo Leveling" --range 1-10 --format pdf

# Launch the zero-dependency Web UI
python main.py --web --port 5000
```
