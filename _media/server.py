#!/usr/bin/env python3
"""
media.mattedev.com — Static Asset Server
Blocca accesso diretto al browser, permette richieste da mattedev.com e sottodomini.
"""

import os
import re
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

# ─── Configurazione ───────────────────────────────────────────────────────────

PORT = 3002
ASSETS_DIR = "."  # Stessa cartella dello script
ALLOWED_ORIGIN_PATTERN = re.compile(
    r'^https?://([a-zA-Z0-9-]+\.)?mattedev\.com(:\d+)?$'
)

LANDING_PAGE = """<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>media.mattedev.com</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0a0a0a;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      color: #e5e5e5;
    }

    .card {
      text-align: center;
      padding: 3rem 2.5rem;
      max-width: 480px;
      border: 1px solid #222;
      border-radius: 16px;
      background: #111;
    }

    .icon {
      font-size: 3rem;
      margin-bottom: 1.5rem;
    }

    h1 {
      font-size: 1.4rem;
      font-weight: 600;
      color: #fff;
      margin-bottom: 0.75rem;
    }

    p {
      font-size: 0.95rem;
      color: #888;
      line-height: 1.6;
      margin-bottom: 1.5rem;
    }

    a {
      display: inline-block;
      padding: 0.6rem 1.4rem;
      background: #fff;
      color: #000;
      border-radius: 8px;
      font-weight: 600;
      font-size: 0.9rem;
      text-decoration: none;
      transition: opacity 0.2s;
    }

    a:hover { opacity: 0.85; }

    .footer {
      margin-top: 2rem;
      font-size: 0.78rem;
      color: #444;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">🔒</div>
    <h1>Accesso non consentito</h1>
    <p>
      Questo dominio distribuisce asset statici esclusivamente per uso interno.<br>
      Non è possibile accedere direttamente alle risorse da questo indirizzo.
    </p>
    <a href="https://mattedev.com">Vai su mattedev.com</a>
    <div class="footer">
      © mattedev.com — Tutti i diritti riservati
    </div>
  </div>
</body>
</html>"""


# ─── Handler ──────────────────────────────────────────────────────────────────

class MediaHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ASSETS_DIR, **kwargs)

    def _is_direct_navigation(self):
        """
        Blocca solo quando il browser sta caricando una pagina intera (document).
        - Sec-Fetch-Dest: document  → visita diretta, mostra landing
        - Sec-Fetch-Dest: image/video/font/... → risorsa embeddata, servi
        - Sec-Fetch-Dest assente → curl/bot/tool, servi
        """
        dest = self.headers.get("Sec-Fetch-Dest", "")
        return dest == "document"

    def do_GET(self):
        # Root → mostra sempre la landing page
        if self.path in ("/", ""):
            self._serve_landing()
            return

        # Visita diretta da browser → landing page
        if self._is_direct_navigation():
            self._serve_landing()
            return

        # Tutto il resto (img src, video, fetch, curl...) → servi il file
        super().do_GET()

    def do_HEAD(self):
        if self._is_direct_navigation():
            self.send_response(403)
            self.end_headers()
            return
        super().do_HEAD()

    # Aggiunge header CORS e sicurezza a ogni risposta
    def end_headers(self):
        origin = self.headers.get("Origin", "")
        if origin and ALLOWED_ORIGIN_PATTERN.match(origin.rstrip("/")):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        else:
            self.send_header("Access-Control-Allow-Origin", "*")

        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Cache-Control", "public, max-age=86400")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def _serve_landing(self):
        content = LANDING_PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        # Nessun CORS sulla landing
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        super().end_headers()
        self.wfile.write(content)

    # Silenzia i log nel terminale (opzionale: rimuovi per debug)
    def log_message(self, format, *args):
        print(f"[media] {self.address_string()} — {format % args}")


# ─── Avvio ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(ASSETS_DIR, exist_ok=True)

    server = HTTPServer(("0.0.0.0", PORT), MediaHandler)
    print(f"✓ media.mattedev.com server avviato su porta {PORT}")
    print(f"  Assets: {os.path.abspath(ASSETS_DIR)}")
    print(f"  Origini permesse: *.mattedev.com")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✗ Server fermato.")
        server.server_close()
