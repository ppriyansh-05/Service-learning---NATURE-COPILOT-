"""
Local development server for the Van Udyan dashboard (frontend/).
Same as `python -m http.server`, but sends Cache-Control: no-cache so browsers always pick up
edited HTML/CSS/JS files instead of serving stale cached copies.

Usage: python scripts/serve_frontend.py [port]   (default port 5173)
"""

import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
    handler = partial(NoCacheHandler, directory=FRONTEND_DIR)
    print(f"Serving {FRONTEND_DIR} at http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
