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
                "description": html.escape(str(desc)),
                "example": format_value(example),
            }
        )

        if ptype == "object" and isinstance(prop.get("properties"), dict):
            rows.extend(flatten_schema(prop, prefix=full_name))

    return rows


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
            f"<td>{r['description']}</td>"
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


def render_markdown_like(text: str) -> str:
    # Preserve readability without a markdown engine: keep line breaks and code ticks.
    escaped = html.escape(text)
    escaped = escaped.replace("`", "<code>").replace("<code>", "<code>", 1)
    # Better: keep as pre-wrapped paragraph for predictable output.
    return f"<pre class=\"desc\">{escaped}</pre>"


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

    def examples_to_html(examples: Any, title: str) -> str:
        if not isinstance(examples, dict) or not examples:
            return f"<h3>{html.escape(title)}</h3><p>No examples available.</p>"
        out = [f"<h3>{html.escape(title)}</h3>"]
        for name, ex in examples.items():
            val = ex.get("value") if isinstance(ex, dict) else ex
            out.append(f"<h4>{html.escape(str(name))}</h4>")
            out.append("<pre><code>" + html.escape(json.dumps(val, indent=2, ensure_ascii=False)) + "</code></pre>")
        return "\n".join(out)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>{html.escape(command)} Command Spec</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 28px; color: #111; }}
h1, h2, h3 {{ margin: 0 0 10px; }}
h1 {{ font-size: 28px; }}
h2 {{ margin-top: 26px; border-top: 1px solid #ddd; padding-top: 12px; font-size: 21px; }}
h3 {{ margin-top: 18px; font-size: 16px; }}
h4 {{ margin: 14px 0 6px; font-size: 14px; }}
p {{ line-height: 1.45; }}
pre, code {{ font-family: Consolas, "Courier New", monospace; }}
pre {{ background: #f5f7fa; border: 1px solid #d9dde3; border-radius: 6px; padding: 10px; overflow-x: auto; white-space: pre-wrap; }}
pre.desc {{ white-space: pre-wrap; line-height: 1.45; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
th, td {{ border: 1px solid #d6d6d6; padding: 8px; vertical-align: top; font-size: 12px; }}
th {{ background: #f2f2f2; text-align: left; }}
.meta {{ color: #555; margin-bottom: 12px; }}
</style>
</head>
<body>
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
