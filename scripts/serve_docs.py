#!/usr/bin/env python3
"""Serve the API docs from the docs/ folder. Serves openapi.yaml as application/json for Redoc."""
import http.server
import os

PORT = 8080
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(ROOT, "docs")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOCS_DIR, **kwargs)

    def guess_type(self, path):
        if path == "/openapi.yaml" or path.endswith("openapi.yaml"):
            return "application/json"
        if path == "/asyncapi.yaml" or path.endswith("asyncapi.yaml"):
            return "application/x-yaml"
        return super().guess_type(path)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()


def main():
    server = http.server.HTTPServer(("", PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print(f"Serving docs at {url}")
    print("  -> Open index.html in your browser.")
    print("  -> Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown_all()
        print("\nStopped.")


if __name__ == "__main__":
    main()
