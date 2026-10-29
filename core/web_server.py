"""
Lightweight Cross-Platform Web Server for MangaVerse.
Zero external dependencies (uses standard library http.server).
Enables MangaVerse to run seamlessly on Android (Termux/Pydroid 3),
Linux headless servers, macOS, and Windows via any web browser.
"""

import http.server
import json
import os
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Optional

from .models import Manga, Chapter, DownloadOptions, ProgressUpdate
from .providers import list_providers, get_provider, detect_provider_from_url
from .downloader import MangaDownloader
from .utils import get_default_download_dir, open_folder, is_android


# State storage for web session
class WebState:
    current_downloader: Optional[MangaDownloader] = None
    latest_progress: dict = {
        "state": "idle",
        "message": "Ready to download",
        "percent": 0,
        "logs": ["MangaVerse Web Server running."],
    }
    selected_manga: Optional[Manga] = None
    manga_chapters: list[Chapter] = []
    lock = threading.Lock()


def progress_callback(update: ProgressUpdate):
    """Callback triggered during active download."""
    with WebState.lock:
        pct = 0
        if update.total_chapters > 0:
            pct = int((update.chapter_index / update.total_chapters) * 100)

        WebState.latest_progress["state"] = update.state
        WebState.latest_progress["message"] = update.message
        WebState.latest_progress["percent"] = pct
        if update.message:
            WebState.latest_progress["logs"].append(f"[{update.state.upper()}] {update.message}")
            if len(WebState.latest_progress["logs"]) > 50:
                WebState.latest_progress["logs"].pop(0)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>MangaVerse Web — Cross-Platform Downloader</title>
<style>
:root {
  --bg: #0B0E14;
  --card: #151924;
  --card-border: #222A3B;
  --inner: #1A202E;
  --input: #0F131D;
  --purple: #7C3AED;
  --purple-hover: #6D28D9;
  --cyan: #06B6D4;
  --emerald: #10B981;
  --emerald-hover: #059669;
  --rose: #EF4444;
  --text: #F8FAFC;
  --muted: #94A3B8;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background-color: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  padding: 16px;
  line-height: 1.5;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--card-border);
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}
.brand {
  font-size: 1.4rem;
  font-weight: 800;
  color: #A78BFA;
  display: flex;
  align-items: center;
  gap: 8px;
}
.badge {
  font-size: 0.75rem;
  background: var(--purple);
  padding: 3px 8px;
  border-radius: 6px;
  color: #FFF;
  font-weight: 700;
}
.platform-tag {
  font-size: 0.8rem;
  background: #064E3B;
  color: #6EE7B7;
  padding: 4px 10px;
  border-radius: 12px;
  font-weight: 600;
}
.search-card {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.search-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
select, input, button {
  font-size: 0.95rem;
  border-radius: 8px;
  border: 1px solid var(--card-border);
  padding: 10px 14px;
  outline: none;
  color: var(--text);
  background: var(--input);
}
select { flex: 1; min-width: 180px; background: var(--inner); }
input[type="text"] { flex: 3; min-width: 220px; }
button {
  cursor: pointer;
  font-weight: 700;
  transition: all 0.2s ease;
}
.btn-primary { background: var(--purple); border-color: var(--purple); }
.btn-primary:hover { background: var(--purple-hover); }
.btn-emerald { background: var(--emerald); border-color: var(--emerald); width: 100%; padding: 14px; font-size: 1.1rem; }
.btn-emerald:hover { background: var(--emerald-hover); }
.btn-rose { background: var(--rose); border-color: var(--rose); }
.btn-chip { background: var(--inner); font-size: 0.8rem; padding: 6px 12px; }
.btn-chip:hover { background: var(--purple); }
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}
@media (min-width: 860px) {
  .grid { grid-template-columns: 1fr 1.1fr; }
}
.panel {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.panel-title {
  font-size: 1.1rem;
  font-weight: 700;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.results-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 480px;
  overflow-y: auto;
}
.result-card {
  background: var(--inner);
  border: 1px solid var(--card-border);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.result-info { flex: 1; }
.result-title { font-weight: 700; font-size: 0.95rem; }
.result-meta { font-size: 0.8rem; color: var(--muted); margin-top: 2px; }
.showcase {
  background: var(--inner);
  border: 1px solid var(--card-border);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  gap: 14px;
}
.cover-thumb {
  width: 90px;
  height: 130px;
  border-radius: 6px;
  object-fit: cover;
  background: #111;
  border: 1px solid var(--card-border);
}
.showcase-details { flex: 1; }
.progress-bar-bg {
  width: 100%;
  height: 12px;
  background: var(--input);
  border-radius: 6px;
  overflow: hidden;
  margin: 8px 0;
}
.progress-bar-fill {
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, var(--purple), var(--cyan));
  transition: width 0.3s ease;
}
.terminal {
  background: #07090E;
  border: 1px solid var(--card-border);
  border-radius: 8px;
  padding: 10px;
  font-family: monospace;
  font-size: 0.8rem;
  color: var(--muted);
  max-height: 120px;
  overflow-y: auto;
  white-space: pre-wrap;
}
.chips-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
</style>
</head>
<body>
<div class="header">
  <div class="brand">📚 MANGA VERSE <span class="badge">CROSS-PLATFORM</span></div>
  <div class="platform-tag" id="platform-label">⚡ Multi-Platform Engine</div>
</div>

<div class="search-card">
  <div class="search-row">
    <select id="source-select"></select>
    <input type="text" id="search-input" placeholder="Search title (e.g. Nano Machine, Solo Leveling) or paste URL...">
    <button class="btn-primary" onclick="triggerSearch()">🔍 Search</button>
  </div>
</div>

<div class="grid">
  <!-- Left Column: Search Results -->
  <div class="panel">
    <div class="panel-title">
      <span>Catalog Results</span>
      <span class="badge" id="results-count">0 found</span>
    </div>
    <div class="results-list" id="results-list">
      <p style="color:var(--muted); text-align:center; padding: 30px;">Search for any title to browse chapters!</p>
    </div>
  </div>

  <!-- Right Column: Series Showcase & Controls -->
  <div class="panel">
    <div class="panel-title">Download Configuration</div>
    <div class="showcase">
      <img id="manga-cover" class="cover-thumb" src="" alt="Cover" style="display:none;">
      <div class="showcase-details">
        <h3 id="manga-title">No Series Selected</h3>
        <p id="manga-meta" style="font-size:0.85rem; color:var(--muted); margin: 6px 0;">Select a series from the left to load chapters.</p>
        <span class="badge" id="manga-chapters-badge" style="display:none;">0 Chapters</span>
      </div>
    </div>

    <div>
      <label style="font-size:0.8rem; color:var(--muted); font-weight:700;">DOWNLOAD SCOPE</label>
      <div class="chips-row" style="margin: 6px 0 10px 0;">
        <button class="btn-chip" onclick="setScope('first5')">⚡ First 5</button>
        <button class="btn-chip" onclick="setScope('latest10')">🔥 Latest 10</button>
        <button class="btn-chip" onclick="setScope('all')">📦 All</button>
      </div>
      <div style="display:flex; gap:10px;">
        <input type="number" id="from-ch" placeholder="From Ch" style="width:50%;">
        <input type="number" id="to-ch" placeholder="To Ch" style="width:50%;">
      </div>
    </div>

    <div>
      <label style="font-size:0.8rem; color:var(--muted); font-weight:700;">OUTPUT FORMAT</label>
      <select id="format-select" style="width:100%; margin-top:4px;">
        <option value="cbz">CBZ (Comic Reader)</option>
        <option value="pdf">PDF (Document)</option>
        <option value="images">Images (Folder)</option>
      </select>
    </div>

    <div>
      <label style="font-size:0.8rem; color:var(--muted); font-weight:700;">SAVE DESTINATION</label>
      <input type="text" id="dest-path" style="width:100%; margin-top:4px;">
    </div>

    <div style="display:flex; gap:10px;">
      <button class="btn-emerald" id="start-btn" onclick="startDownload()">🚀 START DOWNLOAD</button>
      <button class="btn-rose" id="cancel-btn" onclick="cancelDownload()" style="display:none;">⏹ Cancel</button>
    </div>

    <!-- Live Telemetry -->
    <div>
      <div style="display:flex; justify-content:space-between; font-size:0.85rem; font-weight:700;">
        <span id="status-text">Status: Idle</span>
        <span id="percent-text">0%</span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="progress-bar"></div>
      </div>
    </div>

    <div class="terminal" id="terminal-feed">MangaVerse Web Engine ready.</div>
  </div>
</div>

<script>
let activeManga = null;
let activeChapters = [];

async function init() {
  const res = await fetch('/api/init');
  const data = await res.json();
  document.getElementById('platform-label').innerText = 'Platform: ' + data.platform;
  document.getElementById('dest-path').value = data.default_dir;

  const select = document.getElementById('source-select');
  select.innerHTML = '';
  for (const [k, v] of Object.entries(data.sources)) {
    const opt = document.createElement('option');
    opt.value = k;
    opt.innerText = v;
    select.appendChild(opt);
  }

  setInterval(pollProgress, 600);
}

async function triggerSearch() {
  const q = document.getElementById('search-input').value.trim();
  const source = document.getElementById('source-select').value;
  if (!q) return;

  document.getElementById('results-list').innerHTML = '<p style="color:var(--muted); text-align:center; padding:30px;">Searching servers across catalog...</p>';
  const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&source=${encodeURIComponent(source)}`);
  const results = await res.json();

  document.getElementById('results-count').innerText = results.length + ' found';
  const list = document.getElementById('results-list');
  list.innerHTML = '';

  if (results.length === 0) {
    list.innerHTML = '<p style="color:var(--muted); text-align:center; padding:30px;">No series found. Try another keyword!</p>';
    return;
  }

  results.forEach(m => {
    const card = document.createElement('div');
    card.className = 'result-card';
    card.innerHTML = `
      <div class="result-info">
        <div class="result-title">${m.title}</div>
        <div class="result-meta">${m.status || 'Manhwa'} • ${m.provider}</div>
      </div>
      <button class="btn-primary" style="padding:6px 12px; font-size:0.85rem;">Select →</button>
    `;
    card.querySelector('button').onclick = () => selectManga(m);
    list.appendChild(card);
  });
}

async function selectManga(m) {
  activeManga = m;
  document.getElementById('manga-title').innerText = m.title;
  document.getElementById('manga-meta').innerText = 'Fetching chapters from ' + m.provider + '...';
  
  if (m.cover_url) {
    const img = document.getElementById('manga-cover');
    img.src = m.cover_url;
    img.style.display = 'block';
  }

  const res = await fetch(`/api/chapters?url=${encodeURIComponent(m.url)}&source=${encodeURIComponent(m.provider)}`);
  activeChapters = await res.json();

  if (activeChapters.length > 0) {
    const first = activeChapters[0].raw_number;
    const last = activeChapters[activeChapters.length - 1].raw_number;
    document.getElementById('manga-meta').innerText = `Available: Ch. ${first} to Ch. ${last}`;
    const badge = document.getElementById('manga-chapters-badge');
    badge.innerText = activeChapters.length + ' Chapters';
    badge.style.display = 'inline-block';
    
    document.getElementById('from-ch').value = first;
    document.getElementById('to-ch').value = activeChapters[Math.min(4, activeChapters.length - 1)].raw_number;
  }
}

function setScope(type) {
  if (!activeChapters.length) return;
  const first = activeChapters[0].raw_number;
  const last = activeChapters[activeChapters.length - 1].raw_number;
  if (type === 'first5') {
    document.getElementById('from-ch').value = first;
    document.getElementById('to-ch').value = activeChapters[Math.min(4, activeChapters.length - 1)].raw_number;
  } else if (type === 'latest10') {
    const fromIdx = Math.max(0, activeChapters.length - 10);
    document.getElementById('from-ch').value = activeChapters[fromIdx].raw_number;
    document.getElementById('to-ch').value = last;
  } else if (type === 'all') {
    document.getElementById('from-ch').value = first;
    document.getElementById('to-ch').value = last;
  }
}

async function startDownload() {
  if (!activeManga) {
    alert('Please search and select a series first.');
    return;
  }

  const fromVal = parseFloat(document.getElementById('from-ch').value);
  const toVal = parseFloat(document.getElementById('to-ch').value);
  const format = document.getElementById('format-select').value;
  const dest = document.getElementById('dest-path').value;

  const payload = {
    manga: activeManga,
    from: isNaN(fromVal) ? null : fromVal,
    to: isNaN(toVal) ? null : toVal,
    format: format,
    output_dir: dest
  };

  document.getElementById('start-btn').disabled = true;
  document.getElementById('cancel-btn').style.display = 'inline-block';

  await fetch('/api/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

async function cancelDownload() {
  await fetch('/api/cancel', { method: 'POST' });
}

async function pollProgress() {
  try {
    const res = await fetch('/api/progress');
    const data = await res.json();
    document.getElementById('status-text').innerText = data.message;
    document.getElementById('percent-text').innerText = data.percent + '%';
    document.getElementById('progress-bar').style.width = data.percent + '%';

    if (data.logs && data.logs.length) {
      document.getElementById('terminal-feed').innerText = data.logs.slice(-15).join('\\n');
    }

    if (data.state === 'completed' || data.state === 'error' || data.state === 'cancelled') {
      document.getElementById('start-btn').disabled = false;
      document.getElementById('cancel-btn').style.display = 'none';
    }
  } catch (e) {}
}

window.onload = init;
</script>
</body>
</html>
"""


class MangaVerseHandler(http.server.BaseHTTPRequestHandler):
    """HTTP Request Handler dispatching JSON APIs and serving the responsive web UI."""

    def log_message(self, format, *args):
        """Suppress standard HTTP server access logs to keep terminal output clean."""
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        elif path == "/api/init":
            platform_name = "Android (Termux/Mobile)" if is_android() else sys.platform.capitalize()
            data = {
                "platform": platform_name,
                "default_dir": str(get_default_download_dir()),
                "sources": list_providers(),
            }
            self._send_json(data)
            return

        elif path == "/api/search":
            query = params.get("q", [""])[0]
            source_key = params.get("source", ["roliascan"])[0]
            try:
                provider = detect_provider_from_url(query) or get_provider(source_key)
                if query.startswith("http://") or query.startswith("https://"):
                    slug = query.rstrip("/").split("/")[-1]
                    title = slug.replace("-", " ").title()
                    results = [Manga(id=slug, title=title, url=query, provider=provider.name)]
                else:
                    results = provider.search(query)

                out = [
                    {
                        "id": m.id,
                        "title": m.title,
                        "url": m.url,
                        "cover_url": m.cover_url,
                        "provider": m.provider,
                        "status": m.status,
                    }
                    for m in results
                ]
                self._send_json(out)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        elif path == "/api/chapters":
            url = params.get("url", [""])[0]
            source_key = params.get("source", ["roliascan"])[0]
            try:
                provider = detect_provider_from_url(url) or get_provider(source_key)
                slug = url.rstrip("/").split("/")[-1]
                manga = Manga(id=slug, title=slug, url=url, provider=provider.name)
                chapters = provider.get_chapters(manga)
                WebState.manga_chapters = chapters
                out = [
                    {
                        "id": c.id,
                        "number": c.number,
                        "raw_number": c.raw_number,
                        "title": c.title,
                        "url": c.url,
                    }
                    for c in chapters
                ]
                self._send_json(out)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        elif path == "/api/progress":
            with WebState.lock:
                self._send_json(WebState.latest_progress)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/cancel":
            if WebState.current_downloader:
                WebState.current_downloader.cancel()
            self._send_json({"status": "cancelled"})
            return

        elif path == "/api/download":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len)
            payload = json.loads(post_body.decode("utf-8"))

            manga_dict = payload.get("manga", {})
            from_ch = payload.get("from")
            to_ch = payload.get("to")
            fmt = payload.get("format", "cbz")
            out_dir = payload.get("output_dir", str(get_default_download_dir()))

            manga = Manga(
                id=manga_dict.get("id", ""),
                title=manga_dict.get("title", ""),
                url=manga_dict.get("url", ""),
                provider=manga_dict.get("provider", "roliascan"),
            )

            # Filter target chapters
            all_ch = WebState.manga_chapters
            if from_ch is not None and to_ch is not None:
                min_c, max_c = min(from_ch, to_ch), max(from_ch, to_ch)
                target_chapters = [c for c in all_ch if min_c <= c.number <= max_c]
            else:
                target_chapters = list(all_ch)

            def run_bg_download():
                provider = detect_provider_from_url(manga.url) or get_provider("roliascan")
                options = DownloadOptions(
                    output_dir=out_dir,
                    format=fmt,
                    max_workers=4,
                )
                WebState.current_downloader = MangaDownloader(
                    provider=provider,
                    options=options,
                    progress_callback=progress_callback,
                )
                WebState.current_downloader.download_chapters_batch(
                    chapters=target_chapters,
                    manga=manga,
                )

            threading.Thread(target=run_bg_download, daemon=True).start()
            self._send_json({"status": "download_started", "total": len(target_chapters)})
            return

        self.send_error(404, "Not Found")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def start_web_ui(port: int = 5000, open_browser: bool = True):
    """Launches the zero-dependency web server."""
    # Try preferred port, fallback to random open port if occupied
    for p in [port, 5001, 8080, 8888, 0]:
        try:
            server = socketserver.TCPServer(("0.0.0.0", p), MangaVerseHandler)
            actual_port = server.server_address[1]
            break
        except OSError:
            continue

    url = f"http://localhost:{actual_port}"
    print(f"\n========================================================")
    print(f"🚀 MangaVerse Web UI is running!")
    print(f"🌐 Access locally in your browser: {url}")
    if is_android():
        print(f"📱 Running on Android. Downloads will save to /sdcard/Download/MangaVerse")
    print(f"========================================================\n")

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web server...")
        server.server_close()
