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
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#7C3AED">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="MangaVerse">
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
.tabs-nav {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--card-border);
  padding-bottom: 12px;
}
.tab-btn {
  background: var(--card);
  color: var(--muted);
  border: 1px solid var(--card-border);
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}
.tab-btn.active {
  background: var(--purple);
  color: #fff;
  border-color: var(--purple);
}
.anime-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.anime-card {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;
}
.anime-card:hover {
  transform: translateY(-3px);
  border-color: var(--purple);
}
.anime-card-img {
  width: 100%;
  height: 280px;
  object-fit: cover;
  background: #111;
}
.anime-card-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}
.anime-card-title {
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text);
  line-height: 1.3;
}
.anime-badge-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.badge-score {
  background: #065F46;
  color: #34D399;
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 700;
}
.badge-ep {
  background: #3730A3;
  color: #A5B4FC;
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 700;
}
.badge-status {
  background: #1E293B;
  color: #94A3B8;
  font-size: 0.75rem;
  padding: 2px 6px;
  border-radius: 4px;
}
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: none;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 1000;
}
.modal-content {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  max-width: 700px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  padding: 20px;
  position: relative;
}
.modal-close {
  position: absolute;
  top: 14px;
  right: 14px;
  background: var(--inner);
  border: 1px solid var(--card-border);
  color: var(--text);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-weight: bold;
}
</style>
</head>
<body>
<div class="header">
  <div class="brand">📚 MANGA VERSE <span class="badge">CROSS-PLATFORM</span></div>
  <div style="display:flex; gap:8px; align-items:center;">
    <button class="badge" id="install-btn" style="display:none; cursor:pointer; background:#10B981; border:none; padding:5px 12px;" onclick="installApp()">📲 Install App</button>
    <div class="platform-tag" id="platform-label">⚡ Multi-Platform Engine</div>
  </div>
</div>

<div class="tabs-nav">
  <button id="tab-btn-manga" class="tab-btn active" onclick="switchTab('manga')">📚 Manga &amp; Manhwa Downloader</button>
  <button id="tab-btn-anime" class="tab-btn" onclick="switchTab('anime')">🎬 Anime Explorer &amp; Guide</button>
</div>

<!-- ================= MANGA SECTION ================= -->
<div id="manga-section">
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
</div>

<!-- ================= ANIME SECTION ================= -->
<div id="anime-section" style="display:none;">
  <div class="search-card">
    <div class="search-row">
      <input type="text" id="anime-search-input" placeholder="Search anime title (e.g. Solo Leveling, Attack on Titan, Demon Slayer)..." onkeypress="if(event.key==='Enter')triggerAnimeSearch()">
      <button class="btn-primary" onclick="triggerAnimeSearch()">🔍 Search Anime</button>
      <button class="btn-chip" onclick="loadTrendingAnime()" style="background:var(--purple); color:#fff; padding:10px 16px;">🔥 Top Trending</button>
    </div>
  </div>

  <div class="panel">
    <div class="panel-title">
      <span id="anime-heading">Top Trending Anime</span>
      <span class="badge" id="anime-count">0 items</span>
    </div>
    <div class="anime-grid" id="anime-results">
      <p style="color:var(--muted); text-align:center; padding: 40px; grid-column: 1/-1;">Loading trending anime...</p>
    </div>
  </div>
</div>

<!-- ================= ANIME DETAILS MODAL ================= -->
<div class="modal-overlay" id="anime-modal" onclick="if(event.target===this)closeAnimeModal()">
  <div class="modal-content">
    <div class="modal-close" onclick="closeAnimeModal()">✕</div>
    <div id="anime-modal-body"></div>
  </div>
</div>

<script>
let activeManga = null;
let activeChapters = [];
let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const btn = document.getElementById('install-btn');
  if (btn) btn.style.display = 'inline-block';
});

function installApp() {
  if (deferredPrompt) {
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(() => {
      const btn = document.getElementById('install-btn');
      if (btn) btn.style.display = 'none';
      deferredPrompt = null;
    });
  }
}

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

// ================= ANIME MODULE JAVASCRIPT =================
function switchTab(tab) {
  const mangaBtn = document.getElementById('tab-btn-manga');
  const animeBtn = document.getElementById('tab-btn-anime');
  const mangaSec = document.getElementById('manga-section');
  const animeSec = document.getElementById('anime-section');

  if (tab === 'anime') {
    mangaBtn.classList.remove('active');
    animeBtn.classList.add('active');
    mangaSec.style.display = 'none';
    animeSec.style.display = 'block';
    if (!window.animeLoaded) {
      loadTrendingAnime();
      window.animeLoaded = true;
    }
  } else {
    animeBtn.classList.remove('active');
    mangaBtn.classList.add('active');
    animeSec.style.display = 'none';
    mangaSec.style.display = 'block';
  }
}

async function loadTrendingAnime() {
  document.getElementById('anime-heading').innerText = 'Top Trending Anime Globally';
  document.getElementById('anime-results').innerHTML = '<p style="color:var(--muted); text-align:center; padding:40px; grid-column:1/-1;">Fetching trending anime from AniList...</p>';
  try {
    const res = await fetch('/api/anime/trending');
    const items = await res.json();
    renderAnimeCards(items);
  } catch (e) {
    document.getElementById('anime-results').innerHTML = '<p style="color:var(--rose); text-align:center; padding:40px; grid-column:1/-1;">Failed to load anime. Please try again.</p>';
  }
}

async function triggerAnimeSearch() {
  const q = document.getElementById('anime-search-input').value.trim();
  if (!q) return;
  document.getElementById('anime-heading').innerText = `Results for "${q}"`;
  document.getElementById('anime-results').innerHTML = '<p style="color:var(--muted); text-align:center; padding:40px; grid-column:1/-1;">Searching anime catalog...</p>';
  try {
    const res = await fetch(`/api/anime/search?q=${encodeURIComponent(q)}`);
    const items = await res.json();
    renderAnimeCards(items);
  } catch (e) {
    document.getElementById('anime-results').innerHTML = '<p style="color:var(--rose); text-align:center; padding:40px; grid-column:1/-1;">Search error. Please try again.</p>';
  }
}

function renderAnimeCards(items) {
  const container = document.getElementById('anime-results');
  document.getElementById('anime-count').innerText = `${items.length} items`;
  container.innerHTML = '';
  if (!items || items.length === 0) {
    container.innerHTML = '<p style="color:var(--muted); text-align:center; padding:40px; grid-column:1/-1;">No anime found matching your search.</p>';
    return;
  }
  items.forEach(a => {
    const card = document.createElement('div');
    card.className = 'anime-card';
    card.onclick = () => showAnimeDetails(a.id);
    card.innerHTML = `
      <img class="anime-card-img" src="${a.cover || ''}" alt="${a.title}" loading="lazy">
      <div class="anime-card-body">
        <div class="anime-card-title">${a.title}</div>
        <div class="anime-badge-row">
          <span class="badge-score">⭐ ${a.score}</span>
          <span class="badge-ep">${a.episodes}</span>
          <span class="badge-status">${a.format}</span>
        </div>
        <div style="font-size:0.75rem; color:var(--muted); margin-top:4px;">
          ${a.genres ? a.genres.slice(0, 3).join(', ') : ''}
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

async function showAnimeDetails(id) {
  const modal = document.getElementById('anime-modal');
  const body = document.getElementById('anime-modal-body');
  body.innerHTML = '<p style="color:var(--muted); text-align:center; padding:40px;">Loading anime details...</p>';
  modal.style.display = 'flex';

  try {
    const res = await fetch(`/api/anime/info?id=${id}`);
    const a = await res.json();
    if (a.error) {
      body.innerHTML = `<p style="color:var(--rose); text-align:center; padding:30px;">${a.error}</p>`;
      return;
    }

    let linksHtml = '';
    if (a.links && a.links.length) {
      linksHtml = '<div style="margin-top:14px;"><label style="font-size:0.8rem; color:var(--muted); font-weight:700;">OFFICIAL & STREAMING PLATFORMS</label><div class="chips-row" style="margin-top:6px;">' +
        a.links.map(l => `<a href="${l.url}" target="_blank" rel="noopener" class="btn-chip" style="text-decoration:none; color:#67E8F9;">🌐 ${l.site} ↗</a>`).join('') +
        '</div></div>';
    }

    let trailerHtml = '';
    if (a.trailer) {
      trailerHtml = `<a href="${a.trailer}" target="_blank" rel="noopener" class="btn-chip" style="text-decoration:none; color:#F59E0B; margin-top:6px; display:inline-block;">▶ Watch Trailer on YouTube ↗</a>`;
    }

    body.innerHTML = `
      <div style="display:flex; gap:16px; flex-wrap:wrap;">
        <img src="${a.cover}" style="width:140px; height:200px; border-radius:8px; object-fit:cover; border:1px solid var(--card-border);">
        <div style="flex:1; min-width:220px;">
          <h2 style="font-size:1.3rem; color:var(--text);">${a.title}</h2>
          <p style="color:var(--muted); font-size:0.85rem; margin-top:2px;">${a.title_native || ''}</p>
          <div class="anime-badge-row" style="margin: 10px 0;">
            <span class="badge-score">⭐ Score: ${a.score}</span>
            <span class="badge-ep">📺 ${a.episodes}</span>
            <span class="badge-status">Status: ${a.status}</span>
          </div>
          <p style="font-size:0.85rem; color:var(--muted); line-height:1.4;">
            <strong>Format:</strong> ${a.format} &bull; <strong>Year:</strong> ${a.year} &bull; <strong>Studio:</strong> ${a.studios ? a.studios.join(', ') : 'N/A'}
          </p>
          ${trailerHtml}
        </div>
      </div>

      <div style="margin-top:16px;">
        <label style="font-size:0.8rem; color:var(--muted); font-weight:700;">GENRES</label>
        <div style="color:var(--cyan); font-size:0.85rem; margin-top:4px;">${a.genres ? a.genres.join(' &bull; ') : 'N/A'}</div>
      </div>

      <div style="margin-top:14px;">
        <label style="font-size:0.8rem; color:var(--muted); font-weight:700;">SYNOPSIS</label>
        <p style="font-size:0.88rem; color:var(--text); line-height:1.6; margin-top:4px; max-height:180px; overflow-y:auto; background:var(--inner); padding:10px; border-radius:6px;">
          ${a.description || 'No description available.'}
        </p>
      </div>

      ${linksHtml}
    `;
  } catch (e) {
    body.innerHTML = '<p style="color:var(--rose); text-align:center; padding:30px;">Error loading details.</p>';
  }
}

function closeAnimeModal() {
  document.getElementById('anime-modal').style.display = 'none';
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

        elif path == "/manifest.json":
            manifest = {
                "name": "MangaVerse - Manga & Manhwa Downloader",
                "short_name": "MangaVerse",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#0B0E14",
                "theme_color": "#7C3AED",
                "icons": [
                    {
                        "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%237C3AED'/><text x='50%' y='55%' font-size='50' text-anchor='middle' dominant-baseline='middle' fill='white'>📚</text></svg>",
                        "sizes": "192x192 512x512",
                        "type": "image/svg+xml",
                    }
                ],
            }
            self._send_json(manifest)
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

        elif path == "/api/anime/search":
            q = params.get("q", [""])[0]
            try:
                from .anime import AnimeService
                results = AnimeService.search_anime(q, limit=12)
                out = [
                    {
                        "id": a.id,
                        "title": a.display_title,
                        "title_native": a.title_native,
                        "format": a.format,
                        "status": a.status,
                        "episodes": a.episodes_text,
                        "year": a.year_text,
                        "score": a.score_text,
                        "genres": a.genres,
                        "description": a.description,
                        "cover": a.cover_image_large,
                        "banner": a.banner_image,
                        "trailer": a.trailer_url,
                        "links": a.external_links,
                    }
                    for a in results
                ]
                self._send_json(out)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        elif path == "/api/anime/trending":
            try:
                from .anime import AnimeService
                results = AnimeService.get_trending_anime(limit=12)
                out = [
                    {
                        "id": a.id,
                        "title": a.display_title,
                        "title_native": a.title_native,
                        "format": a.format,
                        "status": a.status,
                        "episodes": a.episodes_text,
                        "year": a.year_text,
                        "score": a.score_text,
                        "genres": a.genres,
                        "description": a.description,
                        "cover": a.cover_image_large,
                        "banner": a.banner_image,
                        "trailer": a.trailer_url,
                        "links": a.external_links,
                    }
                    for a in results
                ]
                self._send_json(out)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        elif path == "/api/anime/info":
            anime_id_str = params.get("id", [""])[0]
            try:
                from .anime import AnimeService
                anime_id = int(anime_id_str)
                a = AnimeService.get_anime_by_id(anime_id)
                if not a:
                    self._send_json({"error": "Anime not found"}, status=404)
                    return
                out = {
                    "id": a.id,
                    "title": a.display_title,
                    "title_native": a.title_native,
                    "format": a.format,
                    "status": a.status,
                    "episodes": a.episodes_text,
                    "duration": a.duration,
                    "year": a.year_text,
                    "score": a.score_text,
                    "genres": a.genres,
                    "studios": a.studios,
                    "description": a.description,
                    "cover": a.cover_image_large,
                    "banner": a.banner_image,
                    "trailer": a.trailer_url,
                    "next_episode": a.next_airing_episode,
                    "links": a.external_links,
                }
                self._send_json(out)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
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
