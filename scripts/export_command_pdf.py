#!/usr/bin/env python3
"""Export a single API command from docs/openapi.yaml to HTML/PDF.

Usage:
    python scripts/export_command_pdf.py get_status

Output:
    docs/command-pdfs/<command>.html
    docs/command-pdfs/<command>.pdf (if Edge/Chrome headless is available)
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def load_spec(spec_path: Path) -> Dict[str, Any]:
    text = spec_path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if yaml is None:
            raise RuntimeError("openapi.yaml is not valid JSON and PyYAML is unavailable")
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            raise RuntimeError("Failed to parse OpenAPI document")
        return data


def get_command_operation(spec: Dict[str, Any], command: str) -> Dict[str, Any]:
    path_key = f"/{command}"
    paths = spec.get("paths", {})
    if path_key not in paths:
        raise KeyError(f"Command not found: {path_key}")
    post = paths[path_key].get("post")
    if not isinstance(post, dict):
        raise KeyError(f"No POST operation found for {path_key}")
    return post


def format_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return html.escape(json.dumps(v, ensure_ascii=False))
    return html.escape(str(v))


def flatten_schema(
    schema: Dict[str, Any],
    prefix: str = "",
    required_here: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    props = schema.get("properties", {})
    required = set(required_here or schema.get("required", []) or [])

    for name, prop in props.items():
        if not isinstance(prop, dict):
            continue
        full_name = f"{prefix}.{name}" if prefix else name
        ptype = prop.get("type", "object")
        enum = prop.get("enum", [])
        example = prop.get("example", "")
        desc = prop.get("description", "")
        req = "Yes" if name in required else "No"

        type_text = str(ptype)
        if enum:
            type_text += " (enum)"

        rows.append(
            {
                "field": full_name,
                "type": html.escape(type_text),
                "required": req,
                "description": str(desc),
                "example": format_value(example),
            }
        )

        if ptype == "object" and isinstance(prop.get("properties"), dict):
            rows.extend(flatten_schema(prop, prefix=full_name))

    return rows


def build_example_from_schema(schema: Dict[str, Any]) -> Any:
    """Build a best-effort example payload from a JSON schema object."""
    if not isinstance(schema, dict):
        return None

    if "example" in schema:
        return schema.get("example")
    if "default" in schema:
        return schema.get("default")

    enum_vals = schema.get("enum")
    if isinstance(enum_vals, list) and enum_vals:
        return enum_vals[0]

    stype = schema.get("type")
    if stype == "object":
        props = schema.get("properties", {})
        if not isinstance(props, dict):
            return {}
        out: Dict[str, Any] = {}
        required = schema.get("required", []) or []
        for name, prop in props.items():
            if not isinstance(prop, dict):
                continue
            child = build_example_from_schema(prop)
            if child is not None:
                out[name] = child
            elif name in required:
                out[name] = ""
        return out

    if stype == "array":
        items = schema.get("items", {})
        item_example = build_example_from_schema(items if isinstance(items, dict) else {})
        return [item_example] if item_example is not None else []

    if stype == "integer":
        return 0
    if stype == "number":
        return 0
    if stype == "boolean":
        return False
    if stype == "string":
        return ""

    # Unknown type - return None so callers can decide whether to include.
    return None


def table_html(rows: List[Dict[str, str]], title: str) -> str:
    if not rows:
        return f"<h3>{html.escape(title)}</h3><p>No fields available.</p>"
    out = [f"<h3>{html.escape(title)}</h3>"]
    out.append("<table>")
    out.append("<thead><tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th><th>Example</th></tr></thead>")
    out.append("<tbody>")
    for r in rows:
        out.append(
            "<tr>"
            f"<td><code>{r['field']}</code></td>"
            f"<td>{r['type']}</td>"
            f"<td>{r['required']}</td>"
            f"<td>{render_table_description(r['description'])}</td>"
            f"<td><code>{r['example']}</code></td>"
            "</tr>"
        )
    out.append("</tbody></table>")
    return "\n".join(out)


def choose_browser_executable() -> Optional[str]:
    candidates = [
        "msedge",
        "chrome",
        "chromium",
        r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    ]
    for c in candidates:
        if os.path.isabs(c):
            if Path(c).exists():
                return c
        else:
            resolved = shutil.which(c)
            if resolved:
                return resolved
    return None


def _render_inline(text: str) -> str:
    rendered = html.escape(text)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    return rendered


def render_table_description(text: str) -> str:
    """Render field description text for table cells in a readable format."""
    if not text:
        return ""
    lines = [ln.rstrip() for ln in str(text).splitlines() if ln.strip()]
    if not lines:
        return ""

    bullet_lines = [ln.strip() for ln in lines if ln.strip().startswith("-")]
    non_bullet_lines = [ln.strip() for ln in lines if not ln.strip().startswith("-")]

    parts: List[str] = []
    if non_bullet_lines:
        parts.append(_render_inline(" ".join(non_bullet_lines)))
    if bullet_lines:
        parts.append("<ul>" + "".join(f"<li>{_render_inline(ln.lstrip('- ').strip())}</li>" for ln in bullet_lines) + "</ul>")

    return "".join(parts)


def render_markdown_like(text: str) -> str:
    """Render a small markdown subset used in command descriptions.

    Supports:
    - bold (**x**)
    - inline code (`x`)
    - bullet lists (- x)
    - markdown tables
    - paragraph blocks
    """
    if not text.strip():
        return "<p>No description available.</p>"

    lines = text.splitlines()
    out: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        # Table block
        if "|" in line and i + 1 < len(lines) and re.match(r"^\|?\s*[-:| ]+\|?\s*$", lines[i + 1].strip()):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows: List[List[str]] = []
            while i < len(lines):
                row_line = lines[i].strip()
                if not row_line or "|" not in row_line:
                    break
                rows.append([c.strip() for c in row_line.strip("|").split("|")])
                i += 1

            out.append("<table><thead><tr>" + "".join(f"<th>{_render_inline(h)}</th>" for h in header) + "</tr></thead><tbody>")
            for row in rows:
                out.append("<tr>" + "".join(f"<td>{_render_inline(c)}</td>" for c in row) + "</tr>")
            out.append("</tbody></table>")
            continue

        # Bullet list block
        if line.lstrip().startswith("- "):
            out.append("<ul>")
            while i < len(lines):
                li = lines[i].rstrip()
                if not li.lstrip().startswith("- "):
                    break
                out.append(f"<li>{_render_inline(li.lstrip()[2:])}</li>")
                i += 1
            out.append("</ul>")
            continue

        # Standalone bold heading line like **Command details:**
        if re.match(r"^\*\*[^*]+\*\*:?$", line.strip()):
            content = line.strip().strip(":")
            content = content.strip("*")
            out.append(f"<h3>{html.escape(content)}</h3>")
            i += 1
            continue

        # Paragraph block
        para_parts = [line.strip()]
        i += 1
        while i < len(lines):
            nxt = lines[i].rstrip()
            if not nxt.strip():
                break
            if nxt.lstrip().startswith("- "):
                break
            if "|" in nxt and i + 1 < len(lines) and re.match(r"^\|?\s*[-:| ]+\|?\s*$", lines[i + 1].strip()):
                break
            if re.match(r"^\*\*[^*]+\*\*:?$", nxt.strip()):
                break
            para_parts.append(nxt.strip())
            i += 1

        out.append(f"<p>{_render_inline(' '.join(para_parts))}</p>")

    return "\n".join(out)


def build_html(command: str, op: Dict[str, Any]) -> str:
    summary = op.get("summary", command)
    description = op.get("description", "")

    req_schema = (
        op.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    resp_container = op.get("responses", {}).get("default") or op.get("responses", {}).get("200", {})
    resp_schema = (
        resp_container.get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )

    req_rows = flatten_schema(req_schema) if isinstance(req_schema, dict) else []
    resp_rows = flatten_schema(resp_schema) if isinstance(resp_schema, dict) else []

    req_examples = (
        op.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("examples", {})
    )
    resp_examples = (
        resp_container.get("content", {})
        .get("application/json", {})
        .get("examples", {})
    )

    # Fallback: derive examples from schema when explicit examples are missing.
    if (not isinstance(req_examples, dict) or not req_examples) and isinstance(req_schema, dict):
        derived_req = build_example_from_schema(req_schema)
        if derived_req is not None:
            req_examples = {
                "Generated Example": {
                    "value": derived_req
                }
            }

    if (not isinstance(resp_examples, dict) or not resp_examples) and isinstance(resp_schema, dict):
        derived_resp = build_example_from_schema(resp_schema)
        if derived_resp is not None:
            resp_examples = {
                "Generated Example": {
                    "value": derived_resp
                }
            }

    def examples_to_html(examples: Any, title: str) -> str:
        if not isinstance(examples, dict) or not examples:
            return f"<h3>{html.escape(title)}</h3><p>No examples available.</p>"
        out = [f"<h3>{html.escape(title)}</h3>"]
        for name, ex in examples.items():
            val = ex.get("value") if isinstance(ex, dict) else ex
            out.append(f"<h4>{html.escape(str(name))}</h4>")
            out.append("<pre><code>" + html.escape(json.dumps(val, indent=2, ensure_ascii=False)) + "</code></pre>")
        return "\n".join(out)

    # Remove PDF download link from description (avoid self-referencing in PDF)
    if isinstance(description, str):
        description = re.sub(r"\n\n\*\*Download pdf:\*\*[^\n]*", "", description).strip()

    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>{html.escape(command)} Command Spec</title>
<style>
@page {{ size: A4; margin: 18mm 16mm 18mm 16mm; }}
* {{ box-sizing: border-box; }}

/* ── Base ── */
body {{
    font-family: Helvetica, Arial, sans-serif;
    margin: 0;
    color: #1a1a1a;
    font-size: 10pt;
    line-height: 1.55;
    background: #fff;
}}

/* ── Document Header Bar ── */
.doc-header-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 3px solid #003d6b;
    padding-bottom: 10px;
    margin-bottom: 20px;
}}
.doc-header-bar .brand {{
    font-weight: 700;
    font-size: 9pt;
    color: #003d6b;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    font-family: Helvetica, Arial, sans-serif;
}}
.doc-header-bar .doc-ref {{
    font-size: 8.5pt;
    color: #546a7b;
    font-style: italic;
    font-family: Helvetica, Arial, sans-serif;
}}

/* ── Document Footer Bar ── */
.doc-footer-bar {{
    margin-top: 36px;
    border-top: 2px solid #003d6b;
    padding-top: 10px;
    display: flex;
    justify-content: space-between;
    font-size: 8pt;
    color: #546a7b;
    font-family: Helvetica, Arial, sans-serif;
}}

/* ── Headings ── */
h1, h2, h3, h4 {{ margin: 0 0 10px; font-family: Helvetica, Arial, sans-serif; }}
h1 {{
    font-size: 16pt;
    font-weight: 700;
    letter-spacing: 0.3px;
    margin-bottom: 4px;
    color: #003d6b;
    padding-bottom: 6px;
    border-bottom: 2px solid #003d6b;
}}
h2 {{
    margin-top: 24pt;
    font-size: 13pt;
    font-weight: 700;
    color: #003d6b;
    page-break-after: avoid;
}}
h3 {{
    margin-top: 18pt;
    font-size: 11pt;
    font-weight: 700;
    color: #1a1a1a;
    page-break-after: avoid;
}}
h4 {{
    margin: 18pt 0 6px;
    font-size: 10.5pt;
    font-weight: 700;
    color: #1a1a1a;
}}

/* ── Text ── */
p {{ margin: 8px 0; }}
ul {{ margin: 6px 0 10px 20px; padding: 0; }}
li {{ margin: 4px 0; }}
strong {{ color: #1a1a1a; }}

/* ── Note callouts ── */
.note, blockquote {{
    background: #e8f0f8;
    border-left: 4px solid #003d6b;
    border-radius: 4px;
    padding: 8px 12px;
    margin: 12pt 0 8px;
    font-size: 10pt;
    color: #1a1a1a;
}}

/* ── Code ── */
pre, code {{ font-family: "Courier New", Courier, monospace; }}
code {{
    background: #eaecf0;
    border: 1px solid #c0c4cc;
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 9.5pt;
    color: #1a1a1a;
}}
pre {{
    background: #f0f2f5;
    border: 1px solid #8a94a6;
    border-left: 4px solid #003d6b;
    border-radius: 4px;
    padding: 12px 14px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
    color: #1a1a1a;
    font-size: 9pt;
    line-height: 1.5;
    margin: 8pt 0;
}}
pre code {{
    background: none;
    border: none;
    padding: 0;
    font-size: 9pt;
}}

/* ── Tables ── */
table {{
    border-collapse: collapse;
    width: 100%;
    margin-top: 10px;
    table-layout: fixed;
    border: 1.5px solid #003d6b;
    overflow: hidden;
}}
th, td {{
    border: 1px solid #8a94a6;
    padding: 7px 9px;
    vertical-align: top;
    font-size: 10pt;
    word-break: break-word;
}}
th {{
    background: #003d6b;
    color: #ffffff;
    text-align: left;
    font-weight: 600;
    font-size: 9.5pt;
    letter-spacing: 0.3px;
    font-family: Helvetica, Arial, sans-serif;
    border-color: #002d50;
}}
tr:nth-child(odd) td {{ background: #ffffff; }}
tr:nth-child(even) td {{ background: #f7f9fb; }}

/* ── Meta line ── */
.meta {{
    color: #546a7b;
    margin-bottom: 16px;
    font-size: 10pt;
    padding: 6px 10px;
    background: #e8f0f8;
    border-left: 4px solid #003d6b;
    border-radius: 4px;
}}

/* ── Download button (screen only) ── */
.download-bar {{
    display: flex;
    justify-content: flex-end;
    margin-bottom: 12px;
}}
.download-bar a {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #003d6b;
    color: #fff;
    text-decoration: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 10pt;
    font-weight: 600;
    transition: background 0.2s;
}}
.download-bar a:hover {{ background: #005a9e; }}
.download-bar a svg {{ fill: #fff; width: 16px; height: 16px; }}
@media print {{
    .download-bar {{ display: none; }}
}}

/* ── Print rules ── */
tr, td, th {{ page-break-inside: avoid; }}
h2, h3 {{ page-break-inside: avoid; }}
</style>
</head>
<body>
<div class=\"download-bar\">
  <a href=\"{html.escape(command)}.pdf\" download title=\"Download as PDF\">
    <svg viewBox=\"0 0 24 24\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M5 20h14v-2H5v2zm7-18v12.17l3.59-3.58L17 12l-5 5-5-5 1.41-1.41L12 14.17V2z\"/></svg>
    Download PDF
  </a>
</div>
<div class=\"doc-header-bar\">
    <span class=\"brand\">ZEBRA TECHNOLOGIES</span>
    <span class=\"doc-ref\">{html.escape(command)} &mdash; RFD40 / RFD90 IoT Connector API Reference</span>
</div>
<h1>{html.escape(summary)}</h1>
<div class=\"meta\">Command: <code>{html.escape(command)}</code></div>
<h2>Description</h2>
{render_markdown_like(str(description))}
<h2>Request</h2>
{table_html(req_rows, 'Request Fields')}
{examples_to_html(req_examples, 'Request Examples')}
<h2>Response</h2>
{table_html(resp_rows, 'Response Fields')}
{examples_to_html(resp_examples, 'Response Examples')}
<div class=\"doc-footer-bar\">
    <span>API Version: V1.1 &nbsp;|&nbsp; Document Version: 1.0.0</span>
    <span>Zebra Confidential</span>
</div>
</body>
</html>
"""


def try_generate_pdf(browser: str, html_path: Path, pdf_path: Path) -> Tuple[bool, str]:
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--no-pdf-header-footer",
        f"--print-to-pdf={str(pdf_path)}",
        html_path.resolve().as_uri(),
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=45)
    except subprocess.TimeoutExpired:
        return False, "Timed out while generating PDF via browser"
    except Exception as ex:
        return False, f"Failed to invoke browser: {ex}"

    if completed.returncode != 0:
        err = completed.stderr.strip() or completed.stdout.strip() or "Unknown error"
        return False, err

    if not pdf_path.exists():
        return False, "Browser command completed, but PDF file was not created"

    return True, "OK"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export one API command to HTML/PDF")
    parser.add_argument("command", help="Command name, e.g. get_status")
    parser.add_argument("--spec", default="docs/openapi.yaml", help="Path to OpenAPI spec")
    parser.add_argument("--out-dir", default="docs/command-pdfs", help="Output directory")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    spec_path = (root / args.spec).resolve()
    out_dir = (root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = load_spec(spec_path)
    op = get_command_operation(spec, args.command)

    html_path = out_dir / f"{args.command}.html"
    pdf_path = out_dir / f"{args.command}.pdf"

    page = build_html(args.command, op)
    html_path.write_text(page, encoding="utf-8")

    browser = choose_browser_executable()
    if browser:
        ok, msg = try_generate_pdf(browser, html_path, pdf_path)
        if ok:
            print(f"Generated HTML: {html_path}")
            print(f"Generated PDF:  {pdf_path}")
            return
        print(f"Generated HTML: {html_path}")
        print(f"PDF generation failed: {msg}")
        return

    print(f"Generated HTML: {html_path}")
    print("No Chromium/Edge executable found; PDF was not generated.")


if __name__ == "__main__":
    main()
