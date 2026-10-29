"""
Cross-Platform Utilities for MangaVerse.
Provides safe OS detection, directory resolution, and folder opening
across Windows, macOS, Linux, and Android (Termux / Pydroid 3).
"""

import os
import subprocess
import sys
from pathlib import Path


def is_android() -> bool:
    """Detects if the application is running in an Android environment (Termux/Pydroid)."""
    return (
        "ANDROID_ROOT" in os.environ
        or "TERMUX_VERSION" in os.environ
        or os.path.exists("/data/data/com.termux")
    )


def is_macos() -> bool:
    """Detects if the OS is macOS (Darwin)."""
    return sys.platform == "darwin"


def is_windows() -> bool:
    """Detects if the OS is Windows."""
    return sys.platform == "win32"


def is_linux() -> bool:
    """Detects if the OS is desktop/server Linux (excluding Android)."""
    return sys.platform.startswith("linux") and not is_android()


def get_default_download_dir() -> Path:
    """
    Returns the standard downloads folder appropriate for the host platform:
    - Android: /sdcard/Download/MangaVerse (accessible by comic readers like Mihon/Tachiyomi)
    - Windows/macOS/Linux: ~/Downloads/MangaVerse or local project ./downloads
    """
    if is_android():
        sdcard_dl = Path("/sdcard/Download/MangaVerse")
        try:
            sdcard_dl.mkdir(parents=True, exist_ok=True)
            return sdcard_dl
        except Exception:
            pass

    # Standard desktop user downloads directory
    user_home = Path.home()
    standard_dl = user_home / "Downloads" / "MangaVerse"
    try:
        standard_dl.mkdir(parents=True, exist_ok=True)
        return standard_dl
    except Exception:
        # Fallback to local project directory
        local_dl = Path(__file__).parent.parent / "downloads"
        local_dl.mkdir(parents=True, exist_ok=True)
        return local_dl


def open_folder(folder_path: Path | str) -> bool:
    """
    Opens the target folder in the native file manager across all platforms:
    - Windows: explorer.exe / os.startfile
    - macOS: open
    - Linux: xdg-open
    - Android Termux: termux-open
    """
    path_str = str(folder_path)
    if not os.path.exists(path_str):
        return False

    try:
        if is_windows():
            os.startfile(path_str)
            return True
        elif is_macos():
            subprocess.Popen(["open", path_str])
            return True
        elif is_android():
            # Termux native file opener
            if subprocess.call(["which", "termux-open"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                subprocess.Popen(["termux-open", path_str])
                return True
            return False
        else:
            # Linux X11 / Wayland
            if subprocess.call(["which", "xdg-open"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                subprocess.Popen(["xdg-open", path_str])
                return True
            return False
    except Exception:
        return False


def is_gui_available() -> bool:
    """
    Checks if a graphical display environment and Tkinter are functional.
    Returns False in headless Linux environments, SSH sessions, or minimal Termux.
    """
    if is_android():
        # Android Termux by default does not run Tkinter desktop windows
        return False

    if is_linux():
        # Check for X11 / Wayland display variable
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            return False

    try:
        import tkinter
        # Test basic Tcl initialization
        t = tkinter.Tk()
        t.withdraw()
        t.destroy()
        return True
    except Exception:
        return False
