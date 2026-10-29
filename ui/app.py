"""
Modern Desktop Graphical User Interface (GUI) for MangaVerse.
Upgraded with a vibrant Cyber-Dark / Indigo & Emerald visual theme,
asynchronous cover art preview, colorful status badges, quick chapter presets,
and rich real-time progress feeds.
"""

import io
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageDraw
import requests
from tkinter import filedialog, messagebox

try:
    from core.models import Manga, Chapter, DownloadOptions, ProgressUpdate
    from core.providers import list_providers, get_provider, detect_provider_from_url
    from core.downloader import MangaDownloader
    from core.utils import get_default_download_dir, open_folder
except (ImportError, ValueError):
    from ..core.models import Manga, Chapter, DownloadOptions, ProgressUpdate
    from ..core.providers import list_providers, get_provider, detect_provider_from_url
    from ..core.downloader import MangaDownloader
    from ..core.utils import get_default_download_dir, open_folder

# ==========================================
# Vibrant Modern Color Palette
# ==========================================
PALETTE = {
    "bg": "#0B0E14",             # Deep obsidian background
    "header_bg": "#10141E",      # Top navigation header
    "card_bg": "#151924",        # Elevated primary cards
    "card_border": "#222A3B",    # Card border contour
    "card_hover": "#1C2333",     # Card interactive hover
    "card_selected": "#241E38",  # Selected manga card background
    "inner_bg": "#1A202E",       # Nested control boxes
    "input_bg": "#0F131D",       # Form inputs
    "input_border": "#2A344A",   # Input outlines
    "purple": "#7C3AED",         # Brand Electric Purple
    "purple_hover": "#6D28D9",
    "purple_soft": "#A78BFA",
    "cyan": "#06B6D4",           # Vibrant Cyan
    "cyan_hover": "#0891B2",
    "cyan_soft": "#67E8F9",
    "emerald": "#10B981",        # Radiant Emerald (Download)
    "emerald_hover": "#059669",
    "emerald_soft": "#6EE7B7",
    "rose": "#EF4444",           # Coral Rose (Cancel/Error)
    "rose_hover": "#DC2626",
    "amber": "#F59E0B",          # Warning / Ongoing badge
    "text_white": "#F8FAFC",     # Ultra-crisp primary text
    "text_muted": "#94A3B8",     # Secondary text
    "text_dim": "#64748B",       # Footers / disabled
}


class MangaVerseApp(ctk.CTk):
    """
    Main application window for the Manga & Manhwa Downloader.
    """

    def __init__(self):
        super().__init__()

        # Window & theme setup
        ctk.set_appearance_mode("dark")
        self.title("MangaVerse — Manga & Manhwa Downloader")
        self.geometry("1160x780")
        self.minsize(1020, 700)
        self.configure(fg_color=PALETTE["bg"])

        # State variables
        self.providers_map = list_providers()
        self.current_provider_key = "roliascan"
        self.search_results: list[Manga] = []
        self.selected_manga: Optional[Manga] = None
        self.manga_chapters: list[Chapter] = []
        self.current_downloader: Optional[MangaDownloader] = None
        self.default_output_dir = str(get_default_download_dir())
        self.active_card_frame = None

        # Ensure download directory exists
        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)

        # Pre-generate placeholder cover image
        self.placeholder_cover = self._create_placeholder_cover()

        self._build_ui()

    def _create_placeholder_cover(self) -> ctk.CTkImage:
        """Generates an aesthetic placeholder cover image for anime/manhwa series."""
        img = Image.new("RGB", (110, 160), color="#1A202E")
        draw = ImageDraw.Draw(img)
        draw.rectangle([6, 6, 103, 153], outline="#2A344A", width=2)
        draw.text((28, 65), "MANGA", fill="#7C3AED")
        draw.text((29, 85), "VERSE", fill="#06B6D4")
        return ctk.CTkImage(light_image=img, dark_image=img, size=(110, 160))

    def _build_ui(self):
        """Constructs the application layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ----------------------------------------------------
        # 1. Top Modern Header Bar
        # ----------------------------------------------------
        header_frame = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=PALETTE["header_bg"],
            border_width=1,
            border_color=PALETTE["card_border"],
            height=65,
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)

        brand_badge = ctk.CTkLabel(
            header_frame,
            text="📚 MANGA VERSE",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=PALETTE["purple_soft"],
        )
        brand_badge.grid(row=0, column=0, padx=(22, 10), pady=14, sticky="w")

        pro_pill = ctk.CTkLabel(
            header_frame,
            text="v2.0 PRO",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=PALETTE["purple"],
            text_color=PALETTE["text_white"],
            corner_radius=6,
            padx=8,
            pady=2,
        )
        pro_pill.grid(row=0, column=0, padx=(165, 0), pady=14, sticky="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Next-Gen Manhwa & Manga Downloader • Fast, High-Res, CBZ & PDF",
            font=ctk.CTkFont(size=12),
            text_color=PALETTE["text_muted"],
        )
        subtitle_label.grid(row=0, column=1, padx=(20, 0), pady=14, sticky="w")

        status_chip = ctk.CTkLabel(
            header_frame,
            text="⚡ Multi-Threaded Engine Active",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=PALETTE["emerald_soft"],
            fg_color="#064E3B",
            corner_radius=12,
            padx=12,
            pady=4,
        )
        status_chip.grid(row=0, column=2, padx=(0, 22), pady=14, sticky="e")

        # ----------------------------------------------------
        # 2. Search & Source Selection Bar
        # ----------------------------------------------------
        search_card = ctk.CTkFrame(
            self,
            corner_radius=14,
            fg_color=PALETTE["card_bg"],
            border_width=1,
            border_color=PALETTE["card_border"],
        )
        search_card.grid(row=1, column=0, sticky="ew", padx=20, pady=(15, 12))
        search_card.grid_columnconfigure(1, weight=1)

        source_box = ctk.CTkFrame(search_card, fg_color="transparent")
        source_box.grid(row=0, column=0, padx=(16, 12), pady=12, sticky="w")

        source_title = ctk.CTkLabel(
            source_box,
            text="SOURCE",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=PALETTE["purple_soft"],
        )
        source_title.pack(anchor="w", padx=2, pady=(0, 2))

        self.source_dropdown = ctk.CTkOptionMenu(
            source_box,
            values=[f"{k}: {name}" for k, name in self.providers_map.items()],
            command=self._on_provider_change,
            width=230,
            height=36,
            fg_color=PALETTE["purple"],
            button_color=PALETTE["purple_hover"],
            button_hover_color="#5B21B6",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
        )
        self.source_dropdown.set(f"roliascan: {self.providers_map['roliascan']}")
        self.source_dropdown.pack(anchor="w")

        # Search Input
        input_box = ctk.CTkFrame(search_card, fg_color="transparent")
        input_box.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=12)
        input_box.grid_columnconfigure(0, weight=1)

        search_label = ctk.CTkLabel(
            input_box,
            text="SERIES TITLE OR DIRECT URL",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=PALETTE["text_muted"],
        )
        search_label.grid(row=0, column=0, sticky="w", padx=2, pady=(0, 2))

        self.search_entry = ctk.CTkEntry(
            input_box,
            placeholder_text="Enter title e.g. Nano Machine, Solo Leveling, Pick Me Up, Lookism...",
            placeholder_text_color=PALETTE["text_dim"],
            font=ctk.CTkFont(size=14),
            height=36,
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["input_border"],
            border_width=1,
            corner_radius=8,
            text_color=PALETTE["text_white"],
        )
        self.search_entry.grid(row=1, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda event: self._start_search())

        # Search Button
        self.search_btn = ctk.CTkButton(
            search_card,
            text="🔍 Search Series",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=135,
            height=38,
            fg_color=PALETTE["purple"],
            hover_color=PALETTE["purple_hover"],
            corner_radius=8,
            command=self._start_search,
        )
        self.search_btn.grid(row=0, column=2, padx=(0, 16), pady=(24, 12), sticky="s")

        # ----------------------------------------------------
        # 3. Main Split Workspace (Left = Results, Right = Selected Series & Config)
        # ----------------------------------------------------
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 12))
        workspace.grid_columnconfigure(0, weight=5)  # Results
        workspace.grid_columnconfigure(1, weight=6)  # Config & Showcase
        workspace.grid_rowconfigure(0, weight=1)

        # ----------------------------------------
        # Left: Search Results Container
        # ----------------------------------------
        results_container = ctk.CTkFrame(
            workspace,
            corner_radius=14,
            fg_color=PALETTE["card_bg"],
            border_width=1,
            border_color=PALETTE["card_border"],
        )
        results_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        results_container.grid_rowconfigure(1, weight=1)
        results_container.grid_columnconfigure(0, weight=1)

        results_header_frame = ctk.CTkFrame(results_container, fg_color="transparent")
        results_header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        results_header_frame.grid_columnconfigure(0, weight=1)

        self.results_title_lbl = ctk.CTkLabel(
            results_header_frame,
            text="Catalog Results",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=PALETTE["text_white"],
        )
        self.results_title_lbl.grid(row=0, column=0, sticky="w")

        self.results_count_pill = ctk.CTkLabel(
            results_header_frame,
            text="0 Series",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=PALETTE["inner_bg"],
            text_color=PALETTE["cyan_soft"],
            corner_radius=10,
            padx=10,
            pady=3,
        )
        self.results_count_pill.grid(row=0, column=1, sticky="e")

        self.results_scroll = ctk.CTkScrollableFrame(
            results_container,
            fg_color="transparent",
            scrollbar_button_color=PALETTE["card_border"],
            scrollbar_button_hover_color=PALETTE["purple"],
        )
        self.results_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 12))
        self.results_scroll.grid_columnconfigure(0, weight=1)

        self._show_empty_placeholder("Search for any manga or manhwa title above to browse!")

        # ----------------------------------------
        # Right: Selected Series Details & Download Control Center
        # ----------------------------------------
        config_container = ctk.CTkFrame(
            workspace,
            corner_radius=14,
            fg_color=PALETTE["card_bg"],
            border_width=1,
            border_color=PALETTE["card_border"],
        )
        config_container.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)
        config_container.grid_columnconfigure(0, weight=1)

        # 3.1 Series Showcase Card (With Cover Art Preview!)
        self.showcase_frame = ctk.CTkFrame(
            config_container,
            corner_radius=12,
            fg_color=PALETTE["inner_bg"],
            border_width=1,
            border_color=PALETTE["card_border"],
        )
        self.showcase_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        self.showcase_frame.grid_columnconfigure(1, weight=1)

        # Cover Thumbnail
        self.cover_label = ctk.CTkLabel(
            self.showcase_frame,
            image=self.placeholder_cover,
            text="",
            corner_radius=8,
        )
        self.cover_label.grid(row=0, column=0, rowspan=4, padx=(14, 16), pady=14, sticky="nw")

        # Title & Badges
        self.series_title_label = ctk.CTkLabel(
            self.showcase_frame,
            text="No Series Selected",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=PALETTE["text_white"],
            anchor="w",
            wraplength=340,
            justify="left",
        )
        self.series_title_label.grid(row=0, column=1, sticky="nw", padx=(0, 14), pady=(14, 4))

        # Badges Row
        self.badges_frame = ctk.CTkFrame(self.showcase_frame, fg_color="transparent")
        self.badges_frame.grid(row=1, column=1, sticky="w", padx=(0, 14), pady=(0, 6))

        self.source_badge = ctk.CTkLabel(
            self.badges_frame,
            text="🌐 RoliaScan",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#312E81",
            text_color=PALETTE["purple_soft"],
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.source_badge.pack(side="left", padx=(0, 6))

        self.type_badge = ctk.CTkLabel(
            self.badges_frame,
            text="📖 Manhwa",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#064E3B",
            text_color=PALETTE["emerald_soft"],
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.type_badge.pack(side="left", padx=(0, 6))

        self.series_meta_label = ctk.CTkLabel(
            self.showcase_frame,
            text="Select a series from the left to load chapters and cover art.",
            font=ctk.CTkFont(size=12),
            text_color=PALETTE["text_muted"],
            anchor="w",
            wraplength=340,
            justify="left",
        )
        self.series_meta_label.grid(row=2, column=1, sticky="nw", padx=(0, 14), pady=(0, 10))

        # 3.2 Download Scope & Range Controls
        scope_card = ctk.CTkFrame(
            config_container,
            fg_color=PALETTE["inner_bg"],
            corner_radius=10,
            border_width=1,
            border_color=PALETTE["card_border"],
        )
        scope_card.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        scope_card.grid_columnconfigure(0, weight=1)

        scope_header = ctk.CTkLabel(
            scope_card,
            text="DOWNLOAD SCOPE",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=PALETTE["cyan_soft"],
        )
        scope_header.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        self.scope_segmented = ctk.CTkSegmentedButton(
            scope_card,
            values=["Range", "Single Chapter", "All Chapters"],
            command=self._on_scope_change,
            selected_color=PALETTE["purple"],
            selected_hover_color=PALETTE["purple_hover"],
            unselected_color=PALETTE["input_bg"],
            unselected_hover_color=PALETTE["card_border"],
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.scope_segmented.set("Range")
        self.scope_segmented.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

        # Range Inputs & Quick Preset Chips
        self.range_panel = ctk.CTkFrame(scope_card, fg_color="transparent")
        self.range_panel.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))

        lbl_from = ctk.CTkLabel(self.range_panel, text="From:", font=ctk.CTkFont(size=12, weight="bold"), text_color=PALETTE["text_muted"])
        lbl_from.pack(side="left", padx=(0, 6))

        self.from_ch_entry = ctk.CTkEntry(
            self.range_panel,
            width=70,
            height=30,
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["input_border"],
            font=ctk.CTkFont(weight="bold"),
        )
        self.from_ch_entry.pack(side="left", padx=(0, 12))

        lbl_to = ctk.CTkLabel(self.range_panel, text="To:", font=ctk.CTkFont(size=12, weight="bold"), text_color=PALETTE["text_muted"])
        lbl_to.pack(side="left", padx=(0, 6))

        self.to_ch_entry = ctk.CTkEntry(
            self.range_panel,
            width=70,
            height=30,
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["input_border"],
            font=ctk.CTkFont(weight="bold"),
        )
        self.to_ch_entry.pack(side="left", padx=(0, 16))

        # Quick Preset Buttons
        btn_first5 = ctk.CTkButton(
            self.range_panel,
            text="⚡ First 5",
            width=65,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1E293B",
            hover_color=PALETTE["purple_hover"],
            command=self._preset_first_5,
        )
        btn_first5.pack(side="left", padx=(0, 6))

        btn_latest10 = ctk.CTkButton(
            self.range_panel,
            text="🔥 Latest 10",
            width=75,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1E293B",
            hover_color=PALETTE["purple_hover"],
            command=self._preset_latest_10,
        )
        btn_latest10.pack(side="left")

        # Single Chapter Input (Hidden by default)
        self.single_panel = ctk.CTkFrame(scope_card, fg_color="transparent")
        lbl_single = ctk.CTkLabel(self.single_panel, text="Chapter Number:", font=ctk.CTkFont(size=12, weight="bold"), text_color=PALETTE["text_muted"])
        lbl_single.pack(side="left", padx=(0, 8))
        self.single_ch_entry = ctk.CTkEntry(
            self.single_panel,
            width=90,
            height=30,
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["input_border"],
            font=ctk.CTkFont(weight="bold"),
        )
        self.single_ch_entry.pack(side="left")

        # 3.3 Format & Destination Path Options
        export_card = ctk.CTkFrame(
            config_container,
            fg_color=PALETTE["inner_bg"],
            corner_radius=10,
            border_width=1,
            border_color=PALETTE["card_border"],
        )
        export_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        export_card.grid_columnconfigure(1, weight=1)

        fmt_lbl = ctk.CTkLabel(
            export_card,
            text="FORMAT",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=PALETTE["cyan_soft"],
        )
        fmt_lbl.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        self.format_segmented = ctk.CTkSegmentedButton(
            export_card,
            values=["CBZ (Comic)", "PDF (Book)", "Images (Folder)"],
            selected_color="#0284C7",
            selected_hover_color="#0369A1",
            unselected_color=PALETTE["input_bg"],
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.format_segmented.set("CBZ (Comic)")
        self.format_segmented.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 14), pady=(10, 8))

        path_lbl = ctk.CTkLabel(
            export_card,
            text="SAVE TO",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=PALETTE["text_muted"],
        )
        path_lbl.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 12))

        self.dir_entry = ctk.CTkEntry(
            export_card,
            height=30,
            fg_color=PALETTE["input_bg"],
            border_color=PALETTE["input_border"],
            font=ctk.CTkFont(size=12),
        )
        self.dir_entry.insert(0, self.default_output_dir)
        self.dir_entry.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 12))

        browse_btn = ctk.CTkButton(
            export_card,
            text="📁 Browse",
            width=80,
            height=30,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._browse_directory,
        )
        browse_btn.grid(row=1, column=2, sticky="e", padx=(0, 14), pady=(0, 12))

        # 3.4 Action Buttons
        actions_frame = ctk.CTkFrame(config_container, fg_color="transparent")
        actions_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        actions_frame.grid_columnconfigure(0, weight=3)
        actions_frame.grid_columnconfigure(1, weight=1)

        self.start_btn = ctk.CTkButton(
            actions_frame,
            text="🚀 START DOWNLOAD",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=44,
            fg_color=PALETTE["emerald"],
            hover_color=PALETTE["emerald_hover"],
            corner_radius=8,
            command=self._start_download,
        )
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(
            actions_frame,
            text="⏹ Cancel",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            fg_color=PALETTE["rose"],
            hover_color=PALETTE["rose_hover"],
            corner_radius=8,
            state="disabled",
            command=self._cancel_download,
        )
        self.cancel_btn.grid(row=0, column=1, sticky="ew")

        # ----------------------------------------------------
        # 4. Bottom Activity & Glowing Progress Section
        # ----------------------------------------------------
        bottom_frame = ctk.CTkFrame(
            self,
            corner_radius=14,
            fg_color=PALETTE["card_bg"],
            border_width=1,
            border_color=PALETTE["card_border"],
        )
        bottom_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        bottom_frame.grid_columnconfigure(0, weight=1)

        # Progress telemetry bar
        prog_header = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        prog_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 4))
        prog_header.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            prog_header,
            text="Status: Ready to download",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PALETTE["cyan_soft"],
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self.percent_label = ctk.CTkLabel(
            prog_header,
            text="0%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PALETTE["emerald_soft"],
            anchor="e",
        )
        self.percent_label.grid(row=0, column=1, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(
            bottom_frame,
            height=10,
            fg_color=PALETTE["input_bg"],
            progress_color=PALETTE["cyan"],
            corner_radius=6,
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        # Console Log Header
        console_bar = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        console_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))
        console_bar.grid_columnconfigure(0, weight=1)

        log_tag = ctk.CTkLabel(
            console_bar,
            text="LIVE ACTIVITY FEED",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=PALETTE["purple_soft"],
        )
        log_tag.grid(row=0, column=0, sticky="w")

        open_folder_btn = ctk.CTkButton(
            console_bar,
            text="📂 Open Download Folder",
            height=26,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=PALETTE["cyan"],
            hover_color=PALETTE["cyan_hover"],
            corner_radius=6,
            command=self._open_download_folder,
        )
        open_folder_btn.grid(row=0, column=1, sticky="e")

        self.log_textbox = ctk.CTkTextbox(
            bottom_frame,
            height=85,
            fg_color="#0A0D14",
            border_width=1,
            border_color=PALETTE["card_border"],
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=PALETTE["text_muted"],
        )
        self.log_textbox.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        self._log("READY", "MangaVerse loaded. Select source, search, and download.")

    # ----------------------------------------------------
    # Helper & Event Handlers
    # ----------------------------------------------------
    def _show_empty_placeholder(self, message: str):
        """Displays friendly helper message inside search results."""
        for widget in self.results_scroll.winfo_children():
            widget.destroy()

        placeholder = ctk.CTkLabel(
            self.results_scroll,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=PALETTE["text_dim"],
            wraplength=380,
            justify="center",
        )
        placeholder.pack(expand=True, pady=45)

    def _log(self, level: str, text: str):
        """Appends formatted message to the activity log."""
        self.log_textbox.configure(state="normal")
        icon_map = {
            "READY": "⚡",
            "SEARCH": "🔍",
            "LOAD": "📖",
            "DOWNLOADING": "⬇️",
            "PACKAGING": "📦",
            "SUCCESS": "✨",
            "ERROR": "❌",
            "CANCEL": "⏹",
        }
        icon = icon_map.get(level, "•")
        self.log_textbox.insert("end", f"{icon} [{level}] {text}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _on_provider_change(self, choice: str):
        """Callback when provider dropdown changes."""
        key = choice.split(":")[0].strip()
        self.current_provider_key = key
        self.source_badge.configure(text=f"🌐 {self.providers_map.get(key, key)}")
        self._log("SEARCH", f"Active source switched to: {self.providers_map.get(key, key)}")

    def _on_scope_change(self, value: str):
        """Toggles between Range, Single, and All input fields."""
        if value == "Range":
            self.range_panel.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
            self.single_panel.grid_forget()
        elif value == "Single Chapter":
            self.range_panel.grid_forget()
            self.single_panel.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        else:  # All Chapters
            self.range_panel.grid_forget()
            self.single_panel.grid_forget()

    def _preset_first_5(self):
        """Quick preset: first 5 chapters."""
        if self.manga_chapters:
            first_num = self.manga_chapters[0].raw_number
            to_val = self.manga_chapters[min(4, len(self.manga_chapters) - 1)].raw_number
            self.from_ch_entry.delete(0, "end")
            self.from_ch_entry.insert(0, str(first_num))
            self.to_ch_entry.delete(0, "end")
            self.to_ch_entry.insert(0, str(to_val))

    def _preset_latest_10(self):
        """Quick preset: latest 10 chapters."""
        if self.manga_chapters:
            last_num = self.manga_chapters[-1].raw_number
            from_idx = max(0, len(self.manga_chapters) - 10)
            from_val = self.manga_chapters[from_idx].raw_number
            self.from_ch_entry.delete(0, "end")
            self.from_ch_entry.insert(0, str(from_val))
            self.to_ch_entry.delete(0, "end")
            self.to_ch_entry.insert(0, str(last_num))

    def _browse_directory(self):
        """Opens native folder picker dialog."""
        folder = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if folder:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, folder)

    def _open_download_folder(self):
        """Opens download folder in OS file manager."""
        folder = self.dir_entry.get()
        if not open_folder(folder):
            messagebox.showinfo("Notice", f"Directory '{folder}' does not exist or could not be opened.")

    # ----------------------------------------------------
    # Search Engine Workflow
    # ----------------------------------------------------
    def _start_search(self):
        """Initiates search on background thread to prevent GUI lockup."""
        query = self.search_entry.get().strip()
        if not query:
            return

        self.search_btn.configure(state="disabled", text="Searching...")
        self._show_empty_placeholder("Querying servers across catalog, please wait...")
        self.status_label.configure(text=f"Searching for '{query}'...")
        self._log("SEARCH", f"Searching for '{query}' on {self.current_provider_key}...")

        def run_search():
            try:
                if query.startswith("http://") or query.startswith("https://"):
                    matched_provider = detect_provider_from_url(query) or get_provider(self.current_provider_key)
                    slug = query.rstrip("/").split("/")[-1]
                    title = slug.replace("-", " ").title()
                    direct_manga = Manga(id=slug, title=title, url=query, provider=matched_provider.name)
                    results = [direct_manga]
                else:
                    provider = get_provider(self.current_provider_key)
                    results = provider.search(query)

                self.after(0, lambda: self._display_search_results(results, query))
            except Exception as e:
                self.after(0, lambda: self._handle_search_error(e))

        threading.Thread(target=run_search, daemon=True).start()

    def _handle_search_error(self, error: Exception):
        """Handles search failure."""
        self.search_btn.configure(state="normal", text="🔍 Search Series")
        self._show_empty_placeholder(f"Search failed: {error}")
        self.status_label.configure(text="Search failed.")
        self._log("ERROR", f"Search failure: {error}")

    def _display_search_results(self, results: list[Manga], query: str):
        """Renders search results as sleek interactive cards."""
        self.search_btn.configure(state="normal", text="🔍 Search Series")
        self.search_results = results

        for widget in self.results_scroll.winfo_children():
            widget.destroy()

        if not results:
            self.results_count_pill.configure(text="0 Series")
            self._show_empty_placeholder(f"No series found for '{query}'. Try another keyword or switch source!")
            self.status_label.configure(text="No matches found.")
            self._log("SEARCH", f"No results found for '{query}'.")
            return

        self.results_count_pill.configure(text=f"{len(results)} Series Found")
        self.status_label.configure(text=f"Found {len(results)} matches.")
        self._log("SEARCH", f"Found {len(results)} series matches for '{query}'.")

        for manga in results:
            card = ctk.CTkFrame(
                self.results_scroll,
                fg_color=PALETTE["inner_bg"],
                border_width=1,
                border_color=PALETTE["card_border"],
                corner_radius=10,
            )
            card.pack(fill="x", expand=True, pady=5, padx=3)
            card.grid_columnconfigure(0, weight=1)

            # Title
            title_lbl = ctk.CTkLabel(
                card,
                text=manga.title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=PALETTE["text_white"],
                anchor="w",
                wraplength=270,
                justify="left",
            )
            title_lbl.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))

            # Meta badge row
            meta_box = ctk.CTkFrame(card, fg_color="transparent")
            meta_box.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

            m_type = manga.status or "Manhwa"
            type_pill = ctk.CTkLabel(
                meta_box,
                text=m_type,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="#1E293B",
                text_color=PALETTE["cyan_soft"],
                corner_radius=4,
                padx=6,
                pady=1,
            )
            type_pill.pack(side="left", padx=(0, 6))

            prov_pill = ctk.CTkLabel(
                meta_box,
                text=manga.provider.split("(")[0].strip(),
                font=ctk.CTkFont(size=10),
                text_color=PALETTE["text_muted"],
            )
            prov_pill.pack(side="left")

            select_btn = ctk.CTkButton(
                card,
                text="Select →",
                font=ctk.CTkFont(size=12, weight="bold"),
                width=80,
                height=30,
                fg_color=PALETTE["purple"],
                hover_color=PALETTE["purple_hover"],
                corner_radius=6,
                command=lambda m=manga, c=card: self._select_manga(m, c),
            )
            select_btn.grid(row=0, column=1, rowspan=2, padx=14, pady=10)

    # ----------------------------------------------------
    # Manga Selection & Cover Art Fetching
    # ----------------------------------------------------
    def _select_manga(self, manga: Manga, card_widget=None):
        """Loads selected manga details and fetches its cover art + full chapter list."""
        self.selected_manga = manga
        self.series_title_label.configure(text=manga.title)
        self.source_badge.configure(text=f"🌐 {manga.provider.split('(')[0].strip()}")
        self.type_badge.configure(text=f"📖 {manga.status or 'Manhwa'}")
        self.series_meta_label.configure(text="Fetching available chapters...")

        # Visual selection highlight
        if self.active_card_frame and self.active_card_frame.winfo_exists():
            self.active_card_frame.configure(border_color=PALETTE["card_border"], fg_color=PALETTE["inner_bg"])
        if card_widget and card_widget.winfo_exists():
            card_widget.configure(border_color=PALETTE["purple"], fg_color=PALETTE["card_selected"])
            self.active_card_frame = card_widget

        # Reset cover to placeholder while loading
        self.cover_label.configure(image=self.placeholder_cover)

        # Asynchronously fetch cover art
        if manga.cover_url:
            def load_cover():
                try:
                    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://roliascan.xyz/"}
                    resp = requests.get(manga.cover_url, headers=headers, timeout=6)
                    if resp.status_code == 200:
                        img = Image.open(io.BytesIO(resp.content))
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(110, 160))
                        self.after(0, lambda: self.cover_label.configure(image=ctk_img))
                except Exception:
                    pass
            threading.Thread(target=load_cover, daemon=True).start()

        # Asynchronously fetch chapters
        self._log("LOAD", f"Selected: '{manga.title}'. Fetching chapters...")

        def fetch_chapters():
            try:
                provider = detect_provider_from_url(manga.url) or get_provider(self.current_provider_key)
                chapters = provider.get_chapters(manga)
                self.after(0, lambda: self._on_chapters_loaded(chapters))
            except Exception as e:
                self.after(0, lambda: self._on_chapters_error(e))

        threading.Thread(target=fetch_chapters, daemon=True).start()

    def _on_chapters_loaded(self, chapters: list[Chapter]):
        """Updates UI once chapter list has been received."""
        self.manga_chapters = chapters
        if chapters:
            first_num = chapters[0].raw_number
            last_num = chapters[-1].raw_number
            self.series_meta_label.configure(
                text=f"✅ {len(chapters)} Chapters Available (Ch. {first_num} to Ch. {last_num})\nSource: {self.selected_manga.provider}"
            )
            self._log("LOAD", f"Loaded {len(chapters)} chapters for '{self.selected_manga.title}'.")

            # Preset default range
            self.from_ch_entry.delete(0, "end")
            self.from_ch_entry.insert(0, str(first_num))
            self.to_ch_entry.delete(0, "end")
            end_preview = chapters[min(4, len(chapters) - 1)].raw_number
            self.to_ch_entry.insert(0, str(end_preview))
            self.single_ch_entry.delete(0, "end")
            self.single_ch_entry.insert(0, str(first_num))
        else:
            self.series_meta_label.configure(text="No chapters found for this title on this source.")
            self._log("ERROR", "No chapters found for selected series.")

    def _on_chapters_error(self, error: Exception):
        """Handles chapter listing error."""
        self.series_meta_label.configure(text=f"Failed to load chapters: {error}")
        self._log("ERROR", f"Error loading chapters: {error}")

    # ----------------------------------------------------
    # Download Execution Workflow
    # ----------------------------------------------------
    def _start_download(self):
        """Validates configuration and launches download in a background thread."""
        if not self.selected_manga:
            messagebox.showwarning("Notice", "Please search and select a series first.")
            return

        if not self.manga_chapters:
            messagebox.showwarning("Notice", "No chapters available to download.")
            return

        scope = self.scope_segmented.get()
        target_chapters: list[Chapter] = []

        if scope == "All Chapters":
            target_chapters = list(self.manga_chapters)

        elif scope == "Single Chapter":
            val = self.single_ch_entry.get().strip()
            try:
                target_num = float(val)
                target_chapters = [c for c in self.manga_chapters if abs(c.number - target_num) < 0.01]
                if not target_chapters:
                    messagebox.showwarning("Notice", f"Chapter {val} was not found in this series.")
                    return
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter a valid chapter number.")
                return

        else:  # Range
            try:
                from_num = float(self.from_ch_entry.get().strip())
                to_num = float(self.to_ch_entry.get().strip())
                if from_num > to_num:
                    from_num, to_num = to_num, from_num

                target_chapters = [c for c in self.manga_chapters if from_num <= c.number <= to_num]
                if not target_chapters:
                    messagebox.showwarning("Notice", f"No chapters found in range {from_num} to {to_num}.")
                    return
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid chapter range numbers.")
                return

        format_choice = self.format_segmented.get()
        fmt_map = {"CBZ (Comic)": "cbz", "PDF (Book)": "pdf", "Images (Folder)": "images"}
        selected_fmt = fmt_map.get(format_choice, "cbz")

        options = DownloadOptions(
            output_dir=self.dir_entry.get(),
            format=selected_fmt,
            max_workers=4,
        )

        provider = detect_provider_from_url(self.selected_manga.url) or get_provider(self.current_provider_key)
        self.current_downloader = MangaDownloader(
            provider=provider,
            options=options,
            progress_callback=self._on_download_progress,
        )

        # Update controls
        self.start_btn.configure(state="disabled", fg_color="#065F46")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.percent_label.configure(text="0%")

        # Run download in worker thread
        def run_worker():
            try:
                completed = self.current_downloader.download_chapters_batch(
                    chapters=target_chapters,
                    manga=self.selected_manga,
                )
                self.after(0, lambda: self._on_download_finished(completed))
            except Exception as e:
                self.after(0, lambda: self._on_download_error(e))

        threading.Thread(target=run_worker, daemon=True).start()

    def _on_download_progress(self, update: ProgressUpdate):
        """Thread-safe UI update for progress events."""
        def apply():
            if update.total_chapters > 0:
                fraction = update.chapter_index / update.total_chapters
                self.progress_bar.set(fraction)
                self.percent_label.configure(text=f"{int(fraction * 100)}%")

            self.status_label.configure(text=update.message)
            if update.state == "downloading":
                self._log("DOWNLOADING", update.message)
            elif update.state == "converting":
                self._log("PACKAGING", update.message)
            elif update.state == "cancelled":
                self._log("CANCEL", update.message)

        self.after(0, apply)

    def _on_download_finished(self, completed_paths: list[Path]):
        """Restores UI state after download completes."""
        self.start_btn.configure(state="normal", fg_color=PALETTE["emerald"])
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(1.0)
        self.percent_label.configure(text="100%")
        self.status_label.configure(text=f"✨ Complete! Downloaded {len(completed_paths)} files.")
        self._log("SUCCESS", f"Download batch complete! Saved {len(completed_paths)} files to disk.")

    def _on_download_error(self, error: Exception):
        """Handles fatal download failure."""
        self.start_btn.configure(state="normal", fg_color=PALETTE["emerald"])
        self.cancel_btn.configure(state="disabled")
        self.status_label.configure(text=f"Error: {error}")
        self._log("ERROR", f"Download error: {error}")

    def _cancel_download(self):
        """Signals active downloader to cancel immediately."""
        if self.current_downloader:
            self._log("CANCEL", "Cancelling download operations...")
            self.current_downloader.cancel()
            self.cancel_btn.configure(state="disabled")


def launch():
    """Starts the MangaVerse GUI application."""
    app = MangaVerseApp()
    app.mainloop()


if __name__ == "__main__":
    launch()
