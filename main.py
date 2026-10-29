"""
MangaVerse - Universal Manga & Manhwa Downloader
Cross-platform main launcher supporting Desktop GUI, Web UI (Android/Mobile/Headless), and CLI.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.utils import is_gui_available, is_android


def main():
    """
    Intelligently routes execution:
    - If CLI commands provided -> CLI parser
    - If '--web' or '-w' flag -> Launch browser Web UI
    - If GUI display is available -> Launch native Desktop GUI
    - If running on Android / headless server -> Launch browser Web UI automatically
    """
    args = sys.argv[1:]

    # Check for Web UI request
    if "--web" in args or "-w" in args or (len(args) > 0 and args[0] == "web"):
        from core.web_server import start_web_ui
        port = 5000
        for i, a in enumerate(args):
            if a in ["--port", "-p"] and i + 1 < len(args):
                try:
                    port = int(args[i + 1])
                except ValueError:
                    pass
        start_web_ui(port=port)
        return

    # Check for CLI commands (search, download, sources, etc.)
    cli_commands = ["search", "download", "sources", "--help", "-h"]
    if any(cmd in args for cmd in cli_commands):
        from cli import main as cli_main
        cli_main()
        return

    # If explicit GUI requested
    if "--gui" in args or "-g" in args:
        from ui.app import launch
        launch()
        return

    # Default fallback: check if desktop GUI is available
    if is_gui_available():
        from ui.app import launch
        launch()
    else:
        # On Android Termux or headless Linux, seamlessly start the Web UI
        print("[*] Graphical desktop environment not detected (Android / Headless Server).")
        print("[*] Automatically launching MangaVerse Web UI...")
        from core.web_server import start_web_ui
        start_web_ui(port=5000)


if __name__ == "__main__":
    main()
