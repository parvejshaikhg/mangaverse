#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# MangaVerse 1-Command Android Termux Setup & Launcher
# ==============================================================================

set -e

echo "========================================================"
echo "  📱 Setting up MangaVerse for Android (Termux)"
echo "========================================================"
echo ""

# 1. Request shared storage access so comic readers can find downloaded chapters
echo "[1/4] Checking storage access permissions..."
if [ ! -d "$HOME/storage" ]; then
    echo "Requesting storage permission. Please tap 'ALLOW' on your phone..."
    termux-setup-storage
    sleep 3
fi

# 2. Update packages and install python + build tools
echo "[2/4] Installing Python and media libraries..."
pkg update -y
pkg install -y python git clang libjpeg-turbo libpng

# 3. Install Python dependencies
echo "[3/4] Installing Python requirements..."
pip install --upgrade pip
pip install requests pillow beautifulsoup4

# 4. Create alias for quick launching anytime
echo "[4/4] Creating quick launch shortcut 'mangaverse'..."
mkdir -p "$PREFIX/bin"
cat << 'EOF' > "$PREFIX/bin/mangaverse"
#!/data/data/com.termux/files/usr/bin/bash
cd "$HOME/manga-verse" || cd "$(dirname "$0")"
python main.py "$@"
EOF
chmod +x "$PREFIX/bin/mangaverse"

echo ""
echo "========================================================"
echo "  ✨ MangaVerse Android Installation Complete!"
echo "========================================================"
echo "To run MangaVerse anytime on your phone, simply type:"
echo "    mangaverse"
echo ""
echo "Or start the mobile Web UI directly:"
echo "    python main.py --web"
echo ""
echo "Downloads will be saved to: /sdcard/Download/MangaVerse"
echo "========================================================"
echo ""

# Launch web UI immediately
python main.py --web
