#!/usr/bin/env python3
"""Generate separate HTML pages from markdown with shared sidebar. Reads from content/; sidebar is auto-generated from headings."""
import os
import re
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(ROOT, "content")
DOCS_DIR = os.path.join(ROOT, "docs")
TOC_PATH = os.path.join(ROOT, "toc.json")

# Section order and mapping: (content path, output html, nav label). Sidebar children are auto-generated from ### and #### headings.
PAGES = [
    ("1-introduction/introduction.md", "introduction.html", "1. Introduction"),
    ("2-getting-started/getting-started.md", "quick-start-guide.html", "2. Quick Start Guide"),
]


def strip_front_matter(text):
    if text.strip().startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def md_to_html(md):
    """Minimal markdown to HTML for our content."""
    html = md
    # If a page uses ### directly under # (no ## present), promote heading levels
    # so section numbering does not start with 0.x in the rendered content.
    has_h2 = re.search(r"^##\s+.+$", html, flags=re.MULTILINE) is not None
    has_h3 = re.search(r"^###\s+.+$", html, flags=re.MULTILINE) is not None
    if not has_h2 and has_h3:
        html = re.sub(r"^####\s+(.+)$", r"### \1", html, flags=re.MULTILINE)
        html = re.sub(r"^###\s+(.+)$", r"## \1", html, flags=re.MULTILINE)

    # Fenced code blocks ```lang ... ``` → keep inner text untouched apart from escaping.
    html = re.sub(
        r"```(\w*)\n(.*?)```",
        lambda m: "<pre><code>\n" + _escape(m.group(2)) + "\n</code></pre>",
        html,
        flags=re.DOTALL,
    )

    # Headings with stable slug IDs; strip leading "N." / "N.N." so CSS counters can add numbering
    def _strip_heading_number(text, pattern):
        m = re.match(pattern, text.strip())
        return m.group(2).strip() if m and m.lastindex >= 2 else text.strip()

    def _h4(m):
        text = m.group(1)
        display = _strip_heading_number(text, r"^(\d+\.\d+(?:\.\d+)?\.?)\s+(.+)$")
        return f'<h4 id="{_slugify(text)}">{display}</h4>'

    def _h3(m):
        text = m.group(1)
        display = _strip_heading_number(text, r"^(\d+\.\d+\.?)\s+(.+)$")
        return f'<h3 id="{_slugify(text)}">{display}</h3>'

    def _h2(m):
        text = m.group(1)
        display = _strip_heading_number(text, r"^(\d+\.)\s+(.+)$")
        return f'<h2 id="{_slugify(text)}">{display}</h2>'

    def _h1(m):
        text = m.group(1)
        return f'<h1 id="{_slugify(text)}">{text}</h1>'

    html = re.sub(r"^#### (.+)$", _h4, html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", _h3, html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", _h2, html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", _h1, html, flags=re.MULTILINE)
    html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    # Images: ![alt](src)
    html = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: '<img src="' + m.group(2) + '" alt="' + _html_escape(m.group(1)) + '" loading="lazy" />',
        html,
    )
    def link_sub(m):
        text, url = m.group(1), m.group(2)
        if url in (
            "introduction",
            "rfid-fundamentals",
            "system-architecture",
            "quick-start-guide",
            "tutorials",
            "troubleshooting",
            "appendices",
            "getting-started",
            "overview",
            "mqtt-protocol",
            "data-models",
            "error-handling",
        ):
            return '<a href="' + url + '.html">' + text + "</a>"
        if url == "openapi":
            return '<a href="api-reference.html">' + text + "</a>"
        return '<a href="' + url + '">' + text + "</a>"
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_sub, html)
    def replace_table_block(m):
        block = m.group(0)
        lines = [l for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            return block
        out = ["<table>"]
        out.append("<thead><tr>")
        for c in _split_table_row(lines[0]):
            out.append("<th>" + c.strip() + "</th>")
        out.append("</tr></thead><tbody>")
        for line in lines[1:]:
            if re.match(r"^\|[\s\-:]+\|", line.strip()) and not re.search(r"[a-zA-Z0-9*]", line):
                continue
            out.append("<tr>")
            for c in _split_table_row(line):
                out.append("<td>" + c.strip() + "</td>")
            out.append("</tr>")
        out.append("</tbody></table>")
        return "\n".join(out)
    html = re.sub(r"(?m)^\|.+\|\n(?:\|.+\|\n)*", replace_table_block, html)
    html = re.sub(r"^---$", "<hr>", html, flags=re.MULTILINE)
    # Merge indented continuation lines into the previous "N. item" line so one <ol> per section
    lines = html.split("\n")
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\d+)\.\s+(.+)$", line)
        if m:
            parts = [m.group(2).rstrip()]
            i += 1
            def is_bullet_line(ln):
                t = ln.lstrip()
                return len(t) > 0 and t[0] in "-\u2010\u2011\u2012\u2013\u2014\u2015"  # hyphen, en/em dash
            while i < len(lines) and lines[i].strip() != "" and lines[i].startswith((" ", "\t")) and not re.match(r"^\d+\.\s+", lines[i]) and not is_bullet_line(lines[i]):
                parts.append(lines[i].strip())
                i += 1
            merged.append(m.group(1) + ". " + " ".join(parts))
            continue
        merged.append(line)
        i += 1
    html = "\n".join(merged)
    # Ordered lists: convert "N. text" lines to <OLITEM>, wrap in <ol>, then replace with <li>
    html = re.sub(r"^(\d+)\.\s+(.+)$", r"<OLITEM>\2</OLITEM>", html, flags=re.MULTILINE)
    def wrap_ol(m):
        block = m.group(0).replace("<OLITEM>", "<li>").replace("</OLITEM>", "</li>")
        return "<ol>\n" + block + "</ol>\n"
    html = re.sub(r"(?:<OLITEM>[^\n]+</OLITEM>\n?)+", wrap_ol, html)
    # Unordered lists: convert "- text" (optional leading indent) to <ULITEM>
    html = re.sub(r"^\s*-\s+(.+)$", r"<ULITEM>\1</ULITEM>", html, flags=re.MULTILINE)
    def wrap_ul(m):
        block = m.group(0).replace("<ULITEM>", "<li>").replace("</ULITEM>", "</li>")
        return "<ul>\n" + block + "</ul>\n"
    html = re.sub(r"(?:<ULITEM>[^\n]+</ULITEM>\n?)+", wrap_ul, html)
    lines = html.split("\n")
    result = []
    in_para = False
    in_pre = False
    for line in lines:
        stripped = line.strip()
        # Track <pre> blocks so we don't inject <p> inside code
        if "<pre" in stripped:
            in_pre = True
        if "</pre>" in stripped:
            # Flush any open paragraph before closing pre
            if in_para:
                result.append("</p>")
                in_para = False
            result.append(line)
            in_pre = False
            continue

        if in_pre:
            # Inside a <pre> block, pass lines through unchanged
            result.append(line)
            continue

        if stripped == "":
            if in_para:
                result.append("</p>")
                in_para = False
            result.append("")
        elif line.startswith("<") or line.startswith("|") or re.match(r"^<?(h[1-6]|pre|ul|ol|table|hr)", line.strip()):
            if in_para:
                result.append("</p>")
                in_para = False
            result.append(line)
        else:
            if not in_para:
                result.append("<p>")
                in_para = True
            result.append(line)
    if in_para:
        result.append("</p>")
    html = "\n".join(result)
    html = re.sub(r"<p>\s*<ul>", "<ul>", html)
    html = re.sub(r"</ul>\s*</p>", "</ul>", html)
    return html


def _escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _slugify(text: str) -> str:
    """Generate a URL-friendly slug from a heading."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "section"


def _html_escape(s: str) -> str:
    """Escape for HTML text content."""
    if not s:
        return ""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def normalize_mqtt_responses(spec: dict) -> None:
    """Replace HTTP-like 200 response keys with MQTT-friendly default responses."""
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return

    for _, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "delete", "patch", "head", "options"):
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue
            responses = op.get("responses")
            if not isinstance(responses, dict):
                continue

            if "200" in responses:
                if "default" not in responses:
                    responses["default"] = responses["200"]
                del responses["200"]

            # Make response wording reader-friendly for MQTT docs.
            if "default" in responses and isinstance(responses["default"], dict):
                desc = str(responses["default"].get("description", "")).strip().lower()
                if desc in ("", "success", "ok", "successful", "example response payload"):
                    responses["default"]["description"] = "Response"


def generate_api_reference_html(spec: dict) -> str:
    """Generate static HTML for the API Reference from the OpenAPI spec. No Redoc; same layout as other docs."""
    paths = spec.get("paths") or {}
    tag_groups = spec.get("x-tagGroups") or []

    # Build tag -> [(path, method, operation), ...]
    tag_to_ops = {}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "delete", "patch"):
            if method not in path_item:
                continue
            op = path_item[method]
            if not isinstance(op, dict):
                continue
            tags = op.get("tags") or []
            t = tags[0] if tags else "Other"
            tag_to_ops.setdefault(t, []).append((path, method.upper(), op))

    notice = """<div class="api-ref-notice" style="background:#0f172a;color:#94a3b8;padding:0.6rem 2rem;font-size:0.9rem;border-left:4px solid #38bdf8;margin-bottom:1.5rem;">
<strong style="color:#e2e8f0;">MQTT API</strong> — These are not REST endpoints. Publish the JSON payload to your MQTT command topic; responses come on the command response topic. See <a href="mqtt-protocol.html" style="color:#38bdf8;">MQTT Communication Protocol</a>.
</div>
"""
    out = [notice]
    out.append("<p>All operations are listed below by interface. Publish the JSON payload to your MQTT command topic; see <a href=\"openapi.yaml\"><code>openapi.yaml</code></a> for full request/response schemas and examples.</p>")
    out.append("<h2 id=\"on-this-page\">On this page</h2><ul>")
    for group in tag_groups:
        group_name = group.get("name") or "Operations"
        group_slug = _slugify(group_name)
        out.append(f'<li><a href="#{group_slug}">{_html_escape(group_name)}</a></li>')
    out.append("</ul>")

    for group in tag_groups:
        group_name = group.get("name") or "Operations"
        group_tags = group.get("tags") or []
        group_slug = _slugify(group_name)
        out.append(f'<h2 id="{group_slug}">{_html_escape(group_name)}</h2>')
        for tag in group_tags:
            ops = tag_to_ops.get(tag, [])
            if not ops:
                continue
            tag_slug = _slugify(tag)
            out.append(f'<h3 id="{tag_slug}">{_html_escape(tag)}</h3>')
            for path, method, op in ops:
                summary = op.get("summary") or path.strip("/")
                desc = op.get("description") or ""
                op_id = _slugify(path.strip("/") + "-" + method.lower())
                out.append(f'<h4 id="{op_id}">{method} {path}</h4>')
                if summary and summary != path.strip("/"):
                    out.append(f"<p><strong>{_html_escape(summary)}</strong></p>")
                if desc:
                    out.append(f"<p>{_html_escape(desc)}</p>")
                out.append('<p class="main-text-muted" style="font-size:0.9rem;">Publish JSON to your MQTT command topic. See <code>openapi.yaml</code> for request/response schemas.</p>')

    return "\n".join(out)


def _split_table_row(line):
    if not line.strip().startswith("|"):
        return []
    parts = line.split("|")
    return [p.strip() for p in parts[1:-1] if True]


def extract_headings(md_path):
    """Extract ### and #### heading text from a markdown file (for sidebar children).

    Returns a list of (level, text) tuples where level is "h3" or "h4" so we can
    style depth differently in the sidebar.
    """
    if not os.path.isfile(md_path):
        return []
    with open(md_path, "r", encoding="utf-8") as f:
        content = strip_front_matter(f.read())
    headings = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("#### "):
            headings.append(("h4", line[5:].strip()))
        elif line.startswith("### "):
            headings.append(("h3", line[4:].strip()))
    return headings


def _strip_heading_number_for_label(text):
    """Remove leading 'N.' or 'N.N.' or 'N.N.N.' from heading text for sidebar label."""
    m = re.match(r"^(\d+\.(?:\d+\.)*\d*\.?)\s+(.+)$", text.strip())
    return m.group(2).strip() if m else text.strip()


def _nav_label_html(label: str) -> str:
    """Render a nav label with number/text split so wrapping aligns consistently."""
    raw = (label or "").strip()
    m = re.match(r"^(\d+(?:\.\d+)*\.?)\s+(.+)$", raw)
    if not m:
        return f'<span class="nav-label-text">{_html_escape(raw)}</span>'
    num = _html_escape(m.group(1))
    text = _html_escape(m.group(2))
    return f'<span class="nav-label"><span class="nav-label-num">{num}</span><span class="nav-label-text">{text}</span></span>'


def build_toc_from_content():
    """Build sidebar items from PAGES: each section gets children from ### and #### headings in its markdown.
    Sidebar labels get consistent numbering: 3.1., 3.2., 3.1.1, 3.1.2, etc.
    """
    items = [{"href": "index.html", "label": "Home"}]
    for md_rel_path, html_name, title in PAGES:
        path = os.path.join(CONTENT_DIR, md_rel_path)
        headings = extract_headings(path)
        # Parse section number from title (e.g. "3. MQTT Communication Protocol" -> 3)
        section_num_match = re.match(r"^(\d+)\.", title)
        section_num = section_num_match.group(1) if section_num_match else "1"
        h3_num = 0
        h4_num = 0
        children = []
        for level, text in headings:
            display_text = _strip_heading_number_for_label(text)
            if level == "h3":
                h3_num += 1
                h4_num = 0
                label = f"{section_num}.{h3_num}. {display_text}"
            else:
                h4_num += 1
                label = f"{section_num}.{h3_num}.{h4_num} {display_text}"
            child = {
                "href": html_name + "#" + _slugify(text),
                "label": label,
            }
            if level == "h4":
                child["depth"] = 2
            children.append(child)
        items.append({"href": html_name, "label": title, "children": children})
    items.append({"href": "api-reference.html", "label": "3. API Reference"})
    return items


def load_toc():
    """Load nav title from toc.json (optional); sidebar items are always built from content headings."""
    title = "RFD40 / RFD90 API"
    if os.path.isfile(TOC_PATH):
        try:
            with open(TOC_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            title = data.get("title", title)
        except (json.JSONDecodeError, IOError):
            pass
    items = build_toc_from_content()
    return title, items


def sidebar(current):
    nav_title, nav_items = load_toc()
    current_base = current.split("#")[0]
    title_text = _html_escape(nav_title)
    lines = [
        '<div class="sidebar">',
        '  <div class="nav-brand"><img class="nav-brand-logo" src="assets/zebra-logo.jpg?v=2" alt="Zebra logo" loading="lazy" /></div>',
        '  <div class="nav-title"><div class="nav-title-main">' + title_text + '</div><div class="nav-title-sub">User Guide</div></div>',
    ]

    def is_group_expanded(item):
        href = item.get("href", "")
        children = item.get("children") or []
        if current_base == href:
            return True
        return any((c.get("href") or "").split("#")[0] == current_base for c in children)

    def render_items(items, level=0):
        indent = "  " * (level + 1)
        for item in items:
            href = item["href"]
            label = item["label"]
            children = item.get("children") or []
            if children:
                expanded = is_group_expanded(item)
                group_cls = "nav-group" + ("" if expanded else " collapsed")
                group_id = _slugify(href) + "-children"
                lines.append(f'{indent}<div class="{group_cls}" data-nav-group>')
                toggle_classes = "nav-group-toggle" + (" active" if current_base == href else "")
                toggle_expanded = "true" if expanded else "false"
                lines.append(f'{indent}  <a href="{href}" class="{toggle_classes}" aria-expanded="{toggle_expanded}" aria-controls="{group_id}">{_nav_label_html(label)}</a>')
                lines.append(f'{indent}  <div class="nav-group-children" id="{group_id}">')
                for c in children:
                    chref = c["href"]
                    clabel = c["label"]
                    depth = c.get("depth", 1)
                    # Base class for all sub-items, plus depth-specific class
                    sub_classes = ["nav-sub"]
                    if depth == 2:
                        sub_classes.append("nav-sub-depth2")
                    if current == chref:
                        sub_classes.append("active")
                    ccls = ' class="' + " ".join(sub_classes) + '"'
                    lines.append(f'{indent}    <a href="{chref}"{ccls}>{_nav_label_html(clabel)}</a>')
                lines.append(f'{indent}  </div>')
                lines.append(f'{indent}</div>')
            else:
                is_home = (label.strip().lower() == "home")
                if is_home:
                    cls = ' class="active"' if current_base == href else ""
                    lines.append(f'{indent}<a href="{href}"{cls}>{_nav_label_html(label)}</a>')
                else:
                    # Render as a nav-group (same style as expandable items) but with no children
                    group_cls = "nav-group" + ("" if current_base == href else " collapsed")
                    toggle_classes = "nav-group-toggle" + (" active" if current_base == href else "")
                    lines.append(f'{indent}<div class="{group_cls}" data-nav-group>')
                    lines.append(f'{indent}  <a href="{href}" class="{toggle_classes}">{_nav_label_html(label)}</a>')
                    lines.append(f'{indent}</div>')

    render_items(nav_items)
    lines.append("</div>")
    return "\n".join(lines)


NAV_SCRIPT = """
  <script>
    (function() {
            var body = document.body;
            var tocToggle = document.getElementById('toc-toggle');
            var tocBackdrop = document.getElementById('toc-backdrop');
            var sidebar = document.querySelector('.sidebar');
            var navGroups = Array.prototype.slice.call(document.querySelectorAll('.nav-group'));
            var mobileMedia = window.matchMedia('(max-width: 768px)');
            var storageKey = 'docs.tocCollapsedDesktop';

            function syncExpandedAria() {
                navGroups.forEach(function(group) {
                    var toggle = group.querySelector('.nav-group-toggle');
                    if (!toggle) {
                        return;
                    }
                    toggle.setAttribute('aria-expanded', (!group.classList.contains('collapsed')).toString());
                });
            }

            function syncActiveLink() {
                if (!sidebar) {
                    return;
                }
                var path = window.location.pathname.split('/').pop() || 'index.html';
                var hash = window.location.hash;
                var links = Array.prototype.slice.call(sidebar.querySelectorAll('a'));
                links.forEach(function(link) { link.classList.remove('active'); });

                var target = null;
                if (hash) {
                    target = sidebar.querySelector('a[href="' + path + hash + '"]');
                }
                if (!target) {
                    target = sidebar.querySelector('a[href="' + path + '"]');
                }
                if (!target) {
                    return;
                }

                target.classList.add('active');
                var parentGroup = target.closest('.nav-group');
                if (parentGroup) {
                    navGroups.forEach(function(group) {
                        if (group !== parentGroup) {
                            group.classList.add('collapsed');
                        }
                    });
                    parentGroup.classList.remove('collapsed');
                    var parentToggle = parentGroup.querySelector('.nav-group-toggle');
                    if (parentToggle) {
                        parentToggle.classList.add('active');
                    }
                }
                syncExpandedAria();
            }

            function readDesktopPreference() {
                try {
                    return window.localStorage.getItem(storageKey) === '1';
                } catch (e) {
                    return false;
                }
            }

            function writeDesktopPreference(collapsed) {
                try {
                    window.localStorage.setItem(storageKey, collapsed ? '1' : '0');
                } catch (e) {
                    // Ignore storage errors.
                }
            }

            function setCollapsed(collapsed, persistDesktop) {
                body.classList.toggle('sidebar-collapsed', collapsed);
                if (tocBackdrop) {
                    var showBackdrop = mobileMedia.matches && !collapsed;
                    tocBackdrop.classList.toggle('visible', showBackdrop);
                    tocBackdrop.setAttribute('aria-hidden', (!showBackdrop).toString());
                }
                if (tocToggle) {
                    tocToggle.textContent = collapsed ? '☰' : '◀';
                    tocToggle.setAttribute('aria-label', collapsed ? 'Show navigation' : 'Hide navigation');
                    tocToggle.setAttribute('aria-expanded', (!collapsed).toString());
                }
                if (persistDesktop && !mobileMedia.matches) {
                    writeDesktopPreference(collapsed);
                }
            }

            var startCollapsed = mobileMedia.matches ? true : readDesktopPreference();
            setCollapsed(startCollapsed, false);

            if (tocToggle) {
                tocToggle.addEventListener('click', function() {
                    var nowCollapsed = !body.classList.contains('sidebar-collapsed');
                    setCollapsed(nowCollapsed, true);
                });
            }

            if (tocBackdrop) {
                tocBackdrop.addEventListener('click', function() {
                    setCollapsed(true, false);
                });
            }

            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && mobileMedia.matches && !body.classList.contains('sidebar-collapsed')) {
                    setCollapsed(true, false);
                }
            });

            if (mobileMedia.addEventListener) {
                mobileMedia.addEventListener('change', function(e) {
                    if (e.matches) {
                        setCollapsed(true, false);
                    } else {
                        setCollapsed(readDesktopPreference(), false);
                    }
                });
            }

      document.querySelectorAll('.nav-group-toggle').forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
          var group = toggle.closest('.nav-group');
                    if (!group) {
                        return;
                    }
                    var hasChildren = !!group.querySelector('.nav-group-children');
                    if (hasChildren) {
                        /* Has sub-items: just toggle expand/collapse, no navigation */
                        e.preventDefault();
                        var willExpand = group.classList.contains('collapsed');
                        if (willExpand) {
                            navGroups.forEach(function(other) {
                                if (other !== group) {
                                    other.classList.add('collapsed');
                                    var otherToggle = other.querySelector('.nav-group-toggle');
                                    if (otherToggle) {
                                        otherToggle.classList.remove('active');
                                    }
                                }
                            });
                            group.classList.remove('collapsed');
                            toggle.classList.add('active');
                        } else {
                            group.classList.add('collapsed');
                            toggle.classList.remove('active');
                        }
                        syncExpandedAria();
                    }
                    /* No children (leaf): let the default <a> navigation happen */
        });
      });

            document.querySelectorAll('.sidebar a').forEach(function(link) {
                link.addEventListener('click', function() {
                    if (mobileMedia.matches) {
                        setCollapsed(true, false);
                    }
                });
            });

            window.addEventListener('hashchange', syncActiveLink);
            syncExpandedAria();
            syncActiveLink();
    })();
  </script>
"""

def wrap(title, current_href, body_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} - RFD40 / RFD90 IOT developer guide</title>
  <link href="https://fonts.googleapis.com/css?family=Inter:400,600,700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="css/docs.css" />
</head>
<body>
    <header class="doc-header">
        <button id="toc-toggle" class="toc-toggle" type="button" aria-label="Hide navigation" aria-expanded="true">◀</button>
        <div class="doc-header-title">RFD40 / RFD90 IOT developer guide</div>
    </header>
    <div id="toc-backdrop" class="toc-backdrop" aria-hidden="true"></div>
    <div class="layout-shell">
    <div class="layout">
{sidebar(current_href)}
    <main class="main">
{body_html}
    </main>
  </div>
    </div>
{NAV_SCRIPT}
</body>
</html>"""


def main():
    for md_rel_path, html_name, title in PAGES:
        path = os.path.join(CONTENT_DIR, md_rel_path)
        with open(path, "r", encoding="utf-8") as f:
            md = strip_front_matter(f.read())
        body = md_to_html(md)
        out_path = os.path.join(DOCS_DIR, html_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(wrap(title, html_name, body))
        print("Generated docs/" + html_name)

    home_body = """
<h1>RFD40 / RFD90 IOT developer guide</h1>
<p>Comprehensive developer documentation for Zebra RFD40/RFD90 handheld RFID readers.</p>
<hr>
<h2>Documentation</h2>
<ul>
  <li><a href="introduction.html">1. Introduction</a> — About the document, supported devices, key capabilities, related docs, and support.</li>
  <li><a href="quick-start-guide.html">2. Quick Start Guide</a> — Prerequisites, setup, endpoint configuration, and first inventory.</li>
  <li><a href="api-reference.html">3. API Reference</a> — Complete reference documentation for supported reader APIs.</li>
</ul>
<h2>Command PDFs</h2>
<ul>
    <li><a href="command-pdfs/get_status.pdf">get_status.pdf</a> — One-command PDF with description, request/response fields, and examples.</li>
</ul>
"""
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(wrap("Home", "index.html", home_body.strip()))
    print("Generated docs/index.html (Home)")

    # API Reference: our sidebar + iframe with RapiDoc (single-column read layout)
    openapi_path = os.path.join(DOCS_DIR, "openapi.yaml")
    redoc_standalone_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>API Reference - RFD40 / RFD90 IOT developer guide</title>
  <link href="https://fonts.googleapis.com/css?family=Inter:400,600,700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="css/redoc-zebra.css?v=14" />
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; height: 100%; }
    body { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; background: #fff; }
    rapi-doc { width: 100%; height: 100%; }
    rapi-doc::part(section-operation-summary) { font-size: 1.1rem; }
  </style>
</head>
<body>
  <rapi-doc
    spec-url="openapi.yaml"
    render-style="read"
    show-header="false"
    show-side-nav="true"
    nav-bg-color="#ffffff"
    nav-text-color="#333333"
    nav-hover-bg-color="#f2f3f3"
    nav-hover-text-color="#0073bb"
    nav-accent-color="#0073bb"
    primary-color="#2563eb"
    bg-color="#ffffff"
    text-color="#333333"
    header-color="#1e293b"
    font-size="regular"
    regular-font="Inter, Segoe UI, system-ui, sans-serif"
    mono-font="Consolas, Monaco, monospace"
    schema-style="table"
    schema-expand-level="1"
    default-schema-tab="example"
    show-method-in-nav-bar="false"
    use-path-in-nav-bar="false"
    allow-try="false"
    allow-server-selection="false"
    allow-authentication="false"
  >
  </rapi-doc>

  <script type="module" src="https://unpkg.com/rapidoc/dist/rapidoc-min.js"></script>
  <script>
  (function() {
    /* After RapiDoc loads, hide HTTP method badges (POST/GET) since this is MQTT */
    function hideHttpMethods() {
      var rd = document.querySelector('rapi-doc');
      if (!rd || !rd.shadowRoot) return;
      var style = rd.shadowRoot.querySelector('style[data-mqtt-hide]');
      if (!style) {
        style = document.createElement('style');
        style.setAttribute('data-mqtt-hide', '1');
        style.textContent = [
          /* Hide HTTP method badges */
          '.m-btn.primary { display: none !important; }',
          '.method-fg { display: none !important; }',
          '.req-res-title .method { display: none !important; }',
          '.endpoint-head .method { display: none !important; }',
          '.nav-bar-tag .method { display: none !important; }',
          '.path { display: none !important; }',
          /* Compact request/response body examples */
          'textarea { min-height: 40px !important; max-height: 180px !important; height: auto !important; resize: vertical !important; font-size: 13px !important; padding: 8px !important; }',
          'pre { max-height: 250px !important; overflow: auto !important; padding: 8px 12px !important; font-size: 13px !important; }',
          '.tab-content { padding: 0 !important; }',
          '.tab-panels { padding: 0 !important; }',
          '.table-title { padding: 6px 0 !important; }',
        ].join('\\n');
        rd.shadowRoot.appendChild(style);
      }
    }
    /* Poll for initial setup */
    var attempts = 0;
    var poll = setInterval(function() {
      hideHttpMethods();
      processAllBlocks();
      if (++attempts > 30) clearInterval(poll);
    }, 500);

    /* Process all pre and textarea blocks: add copy, resize.
       Recursively walks shadow roots since RapiDoc nests components. */
    function processAllBlocks() {
      var rd = document.querySelector('rapi-doc');
      if (!rd) return;
      walkShadowRoots(rd);
    }

    function walkShadowRoots(node) {
      if (node.shadowRoot) {
        addCopyToElement(node.shadowRoot);
        var children = node.shadowRoot.querySelectorAll('*');
        for (var c = 0; c < children.length; c++) {
          if (children[c].shadowRoot) walkShadowRoots(children[c]);
        }
      }
      /* Also check child elements in case they have shadow roots */
      var kids = node.querySelectorAll('*');
      for (var k = 0; k < kids.length; k++) {
        if (kids[k].shadowRoot) walkShadowRoots(kids[k]);
      }
    }

    function addCopyToElement(root) {
      /* <pre> blocks (response examples) */
      var pres = root.querySelectorAll('pre');
      for (var i = 0; i < pres.length; i++) {
        var pre = pres[i];
        if (pre.getAttribute('data-copy-added')) continue;
        pre.setAttribute('data-copy-added', '1');
        pre.style.position = 'relative';
        var btn = document.createElement('button');
        btn.textContent = 'Copy';
        btn.style.cssText = 'position:absolute;top:4px;right:4px;padding:3px 10px;font-size:11px;cursor:pointer;background:#e2e8f0;border:1px solid #cbd5e1;border-radius:4px;color:#334155;z-index:10;';
        btn.onclick = (function(el, b) {
          return function() {
            var t = el.textContent.replace('Copy','').replace('Copied!','').trim();
            navigator.clipboard.writeText(t);
            b.textContent = 'Copied!';
            setTimeout(function(){ b.textContent = 'Copy'; }, 1500);
          };
        })(pre, btn);
        pre.appendChild(btn);
      }
      /* <textarea> blocks (request body examples) — make read-only, compact, with copy button */
      var tas = root.querySelectorAll('textarea');
      for (var j = 0; j < tas.length; j++) {
        var ta = tas[j];
        if (ta.getAttribute('data-copy-added')) continue;
        ta.setAttribute('data-copy-added', '1');
        /* Make read-only */
        ta.readOnly = true;
        ta.setAttribute('readonly', 'readonly');
        /* Style to match response pre blocks */
        ta.style.cssText = 'background:#f8f9fa;border:1px solid #e2e8f0;border-radius:6px;padding:12px 16px;font-family:Consolas,Monaco,monospace;font-size:13px;width:100%;resize:none;cursor:default;color:#333;line-height:1.5;box-sizing:border-box;';
        /* Auto-size to content */
        ta.style.height = 'auto';
        ta.style.height = Math.min(ta.scrollHeight + 8, 250) + 'px';
        ta.style.overflow = ta.scrollHeight > 250 ? 'auto' : 'hidden';
        /* Wrap textarea in a relative container for copy button positioning */
        var wrapper = document.createElement('div');
        wrapper.style.cssText = 'position:relative;width:100%;';
        ta.parentElement.insertBefore(wrapper, ta);
        wrapper.appendChild(ta);
        /* Copy button inside wrapper */
        var btn2 = document.createElement('button');
        btn2.textContent = 'Copy';
        btn2.style.cssText = 'position:absolute;top:6px;right:6px;padding:3px 10px;font-size:11px;cursor:pointer;background:#e2e8f0;border:1px solid #cbd5e1;border-radius:4px;color:#334155;z-index:10;';
        btn2.onclick = (function(textarea, button) {
          return function() {
            navigator.clipboard.writeText(textarea.value);
            button.textContent = 'Copied!';
            setTimeout(function(){ button.textContent = 'Copy'; }, 1500);
          };
        })(ta, btn2);
        wrapper.appendChild(btn2);
      }
    }

    /* MutationObserver: catch lazily rendered content (operations render on scroll) */
    function startObserver() {
      var rd = document.querySelector('rapi-doc');
      if (!rd || !rd.shadowRoot) {
        setTimeout(startObserver, 300);
        return;
      }
      var observer = new MutationObserver(function() {
        hideHttpMethods();
        processAllBlocks();
      });
      observer.observe(rd.shadowRoot, { childList: true, subtree: true });
      /* Also observe nested shadow roots */
      var all = rd.shadowRoot.querySelectorAll('*');
      for (var i = 0; i < all.length; i++) {
        if (all[i].shadowRoot) {
          observer.observe(all[i].shadowRoot, { childList: true, subtree: true });
        }
      }
    }
    startObserver();
  })();
  </script>
</body>
</html>"""
    with open(os.path.join(DOCS_DIR, "api-reference-redoc.html"), "w", encoding="utf-8") as f:
        f.write(redoc_standalone_html)
    print("Generated docs/api-reference-redoc.html")

    api_ref_body = """<iframe src="api-reference-redoc.html?v=25" title="API Reference" class="api-ref-iframe"></iframe>"""
    api_ref_html = """<!DOCTYPE html>
<html lang="en" class="layout-api-ref-page">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>4. API Reference - RFD40 / RFD90 IOT developer guide</title>
  <link href="https://fonts.googleapis.com/css?family=Inter:400,600,700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="css/docs.css" />
  <link rel="stylesheet" href="css/api-reference.css" />
  <style>
        html, body { height: 100%; margin: 0; overflow: hidden; }
        .layout-api-ref { height: 100%; min-height: 0; overflow: hidden; display: flex; flex-direction: row; }
        .layout-api-ref .main-api-ref { flex: 1; min-height: 0; height: 100%; display: flex; flex-direction: column; overflow: hidden; padding: 0; }
        .layout-api-ref .api-ref-iframe { flex: 1; min-height: 0; height: 100%; width: 100%; border: none; display: block; }
  </style>
</head>
<body>
    <header class="doc-header">
        <button id="toc-toggle" class="toc-toggle" type="button" aria-label="Hide navigation" aria-expanded="true">◀</button>
        <div class="doc-header-title">RFD40 / RFD90 IOT developer guide</div>
    </header>
    <div id="toc-backdrop" class="toc-backdrop" aria-hidden="true"></div>
    <div class="layout-shell">
  <div class="layout layout-api-ref">
""" + sidebar("api-reference.html") + """
    <main class="main main-api-ref">
""" + api_ref_body + """
    </main>
  </div>
    </div>
""" + NAV_SCRIPT + """
</body>
</html>"""
    with open(os.path.join(DOCS_DIR, "api-reference.html"), "w", encoding="utf-8") as f:
        f.write(api_ref_html)
    print("Generated docs/api-reference.html")

    openapi_path = os.path.join(DOCS_DIR, "openapi.yaml")
    with open(openapi_path, "r", encoding="utf-8") as f:
        spec = json.load(f)
    normalize_mqtt_responses(spec)
    # Remove branding metadata so Redoc does not render a logo block in API sidebar/header.
    if isinstance(spec.get("info"), dict) and "x-logo" in spec["info"]:
        del spec["info"]["x-logo"]
    with open(openapi_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=4, ensure_ascii=False)
    print("Cleaned docs/openapi.yaml.")


if __name__ == "__main__":
    main()
