#!/usr/bin/env python3
"""Cross-platform static server + hot reload for viz/.

Serves the repo root so ../maps/basic/ works. Watches viz/ and signals
browsers via /__viz_watch (used by hotreload.js).

Usage (macOS / Windows / Linux), from repo root:
  python3 viz/serve.py
  python viz/serve.py
  python viz/serve.py --port 9000
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import threading
import time
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
VIZ_DIR = ROOT / "viz"
WATCH_SUFFIXES = {".html", ".css", ".js", ".md"}


def viz_version() -> str:
    latest = 0.0
    for path in VIZ_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in WATCH_SUFFIXES:
            try:
                latest = max(latest, path.stat().st_mtime)
            except OSError:
                pass
    return f"{latest:.6f}"


class VizHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/__viz_watch", "/viz/__viz_watch"}:
            body = json.dumps({"v": viz_version()}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self) -> None:
        # Avoid stale CSS/JS while iterating on the viewer.
        if self.path.startswith("/viz/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve viz/ with hot reload")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser")
    args = parser.parse_args()

    os.chdir(ROOT)
    handler = partial(VizHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    url = f"http://127.0.0.1:{args.port}/viz/"

    print(f"Serving {ROOT}")
    print(f"Viewer: {url}")
    print("Hot reload: watching viz/ (HTML/CSS/JS)")
    print("Ctrl+C to stop")

    if not args.no_open:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
