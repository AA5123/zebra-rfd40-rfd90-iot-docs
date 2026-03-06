# RFD40 / RFD90 IoT Connector API Reference

API documentation for the **Zebra IoT Connector** (RFD40/90 handheld RFID readers) — MQTT + JSON over Wi‑Fi or Ethernet.

---

## Folder structure

```
d:\RFID index\
├── content/                    # Source: guide content (Markdown)
│   ├── 1-overview/
│   │   └── overview.md
│   ├── 2-getting-started/
│   │   └── getting-started.md
│   ├── 3-mqtt-protocol/
│   │   └── mqtt-protocol.md
│   ├── 4-api-reference/       # API Reference pages are built from YAML specs
│   │   └── README.md
│   ├── 5-data-models/
│   │   └── data-models.md
│   └── 6-error-handling/
│       └── error-handling.md
├── docs/                       # Built site (HTML, CSS, specs) — served to browser
│   ├── index.html
│   ├── overview.html, getting-started.html, ...
│   ├── api-reference.html
│   ├── css/
│   │   └── docs.css
│   ├── openapi.yaml            # OpenAPI (for Redoc; command payloads)
│   └── asyncapi.yaml           # AsyncAPI (MQTT topics & messages)
├── scripts/
│   ├── build_pages.py          # content/*.md → docs/*.html; sidebar auto-generated from ### / #### headings
│   └── serve_docs.py           # Serves docs/ on http://localhost:8080/
├── toc.json                    # Sidebar title only; nav items are built from content
├── README.md
├── support.txt                 # Product and setup notes (hierarchical)
└── START-DOCS.bat              # Double-click to start server
```

---

## Quick start (view the docs)

1. **Double‑click `START-DOCS.bat`** (or run `python scripts\serve_docs.py`).
2. Open **http://localhost:8080/** in your browser, then **index.html** for Home.
3. Use the **sidebar** to navigate; sections are collapsible. Numbering (1.1, 1.2, …) is automatic in the main content and in the sidebar.
4. Press **Ctrl+C** in the server window to stop.

---

## Rebuilding after edits

- **Guide content:** edit Markdown in **`content/<section>/`** (e.g. `content/1-overview/overview.md`), then run **`python scripts\build_pages.py`**. The sidebar updates automatically from `###` and `####` headings.
- **New top-level section:** add a folder and file under `content/` (e.g. `content/7-advanced-topics/advanced-topics.md`), add one entry to the **`PAGES`** list in **`scripts/build_pages.py`**, then run **`python scripts\build_pages.py`**.
- **Sidebar title:** edit **`toc.json`** (only the `title` field is used).
- **OpenAPI:** edit **`docs/openapi.yaml`**; Redoc on the API Reference page loads it from the server.

---

## Features

- **Hierarchical headings:** Use `##`, `###`, and `####` in Markdown; the main content shows automatic numbering (1., 1.1., 1.1.1.).
- **Collapsible sidebar:** Section groups expand/collapse; the current section stays expanded.
- **Dark, enterprise-style theme** for the sidebar and consistent styling for tables, code, and lists.
