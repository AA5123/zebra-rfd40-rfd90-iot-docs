#!/usr/bin/env python3
"""
generate_openapi.py
-------------------
Auto-discovers JSON schema files from schemas/commands/, schemas/response/,
and schemas/events/ and generates docs/openapi.yaml.

Each JSON schema must include an "x-tag" field that maps it to a sidebar group.
Sidebar groups and tag descriptions are defined in schemas/tag_config.json.
Optional rich operation descriptions live in schemas/operation_descriptions.json.

Usage:
    python scripts/generate_openapi.py
"""

import json
import os
import sys
import re
from collections import OrderedDict

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SCHEMAS_DIR = os.path.join(PROJECT_ROOT, "schemas")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "docs", "openapi.yaml")

COMMANDS_DIR = os.path.join(SCHEMAS_DIR, "commands")
RESPONSE_DIR = os.path.join(SCHEMAS_DIR, "response")
EVENTS_DIR = os.path.join(SCHEMAS_DIR, "events")

TAG_CONFIG_PATH = os.path.join(SCHEMAS_DIR, "tag_config.json")
ERROR_CODES_PATH = os.path.join(SCHEMAS_DIR, "error_codes.json")
OP_DESCRIPTIONS_DIR = os.path.join(SCHEMAS_DIR, "operation_descriptions")

COMMAND_PDFS_DIR = os.path.join(PROJECT_ROOT, "docs", "command-pdfs")
GITHUB_PAGES_BASE = "https://aa5123.github.io/zebra-rfd40-rfd90-iot-docs/command-pdfs"

# Files to skip during auto-discovery (legacy/monolithic files)
SKIP_FILES = {"dev_mgt.json"}

# Response description overrides (command -> label)
RESPONSE_DESCRIPTIONS = {
    "get_status": "get_status response",
    "get_version": "get_version response",
    "get_current_region": "get_current_region response",
    "get_config": "get_config response",
}

# Per-operation request body descriptions
REQUEST_BODY_DESCRIPTIONS = {
    "get_status": "The get_status command requires only the standard envelope fields. No additional configuration parameters are needed.",
}

# Per-operation response payload descriptions
RESPONSE_PAYLOAD_DESCRIPTIONS = {
    "get_status": "The response contains standard envelope fields, a deviceStatus object with device telemetry data, and a response object indicating success or failure.",
}


def load_json(filepath):
    """Load a JSON file preserving key order."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def load_tag_config():
    """Load tag_config.json with tag groups and descriptions."""
    if os.path.exists(TAG_CONFIG_PATH):
        return load_json(TAG_CONFIG_PATH)
    print(f"  WARNING: {TAG_CONFIG_PATH} not found, using empty config")
    return {"tag_groups": {}, "tag_descriptions": {}}


def load_operation_descriptions():
    """Load operation descriptions from individual .md files in operation_descriptions/."""
    descriptions = {}
    if os.path.isdir(OP_DESCRIPTIONS_DIR):
        for filename in os.listdir(OP_DESCRIPTIONS_DIR):
            if filename.endswith(".md"):
                op_name = filename[:-3]  # strip .md
                filepath = os.path.join(OP_DESCRIPTIONS_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    descriptions[op_name] = f.read().strip()
    return descriptions


def load_error_codes():
    """Load error_codes.json and return a dict mapping command -> list of error code entries."""
    if not os.path.exists(ERROR_CODES_PATH):
        print(f"  WARNING: {ERROR_CODES_PATH} not found, skipping error codes")
        return {}
    all_codes = load_json(ERROR_CODES_PATH).get("codes", [])
    cmd_map = {}  # command_name -> [code entries]
    for entry in all_codes:
        for cmd in entry.get("commands", []):
            if cmd == "*":
                continue  # wildcard handled separately
            cmd_map.setdefault(cmd, []).append(entry)
    # Prepend code 0 (Success) to every command
    code_zero = [e for e in all_codes if e.get("code") == 0]
    for cmd in cmd_map:
        cmd_map[cmd] = code_zero + cmd_map[cmd]
    return cmd_map


def load_example_descriptions():
    """Load the example_description.json mapping file."""
    path = os.path.join(SCHEMAS_DIR, "example_description.json")
    if os.path.exists(path):
        return load_json(path)
    return {}


def find_command_pdf(op_name):
    """
    Check if a PDF exists for this command in docs/command-pdfs/.
    Looks for: {op_name}.pdf, {op_name}_formatted.pdf
    Returns the URL to the best match, or None.
    """
    if not os.path.isdir(COMMAND_PDFS_DIR):
        return None
    # Prefer plain, fall back to _formatted (legacy)
    for suffix in [".pdf", "_formatted.pdf"]:
        filename = op_name + suffix
        if os.path.exists(os.path.join(COMMAND_PDFS_DIR, filename)):
            return f"{GITHUB_PAGES_BASE}/{filename}"
    return None


def discover_operations():
    """
    Auto-discover all command and event JSON files.
    Returns a list of (operation_name, tag_name, source_folder, request_path) tuples.
    """
    operations = []

    # Scan commands/ subfolders (dev_mgmt/, control/, etc.)
    if os.path.isdir(COMMANDS_DIR):
        for subfolder in sorted(os.listdir(COMMANDS_DIR)):
            subfolder_path = os.path.join(COMMANDS_DIR, subfolder)
            if not os.path.isdir(subfolder_path):
                continue
            for filename in sorted(os.listdir(subfolder_path)):
                if not filename.endswith(".json") or filename in SKIP_FILES:
                    continue
                filepath = os.path.join(subfolder_path, filename)
                op_name = filename[:-5]  # strip .json
                try:
                    data = load_json(filepath)
                    tag = data.get("x-tag")
                    if not tag:
                        print(f"  WARNING: {filepath} has no x-tag, skipping")
                        continue
                    operations.append((op_name, tag, subfolder, filepath))
                except Exception as e:
                    print(f"  WARNING: Error reading {filepath}: {e}")

    # Scan events/
    if os.path.isdir(EVENTS_DIR):
        for filename in sorted(os.listdir(EVENTS_DIR)):
            if not filename.endswith(".json") or filename in SKIP_FILES:
                continue
            filepath = os.path.join(EVENTS_DIR, filename)
            op_name = filename[:-5]  # strip .json
            try:
                data = load_json(filepath)
                tag = data.get("x-tag")
                if not tag:
                    print(f"  WARNING: {filepath} has no x-tag, skipping")
                    continue
                operations.append((op_name, tag, "events", filepath))
            except Exception as e:
                print(f"  WARNING: Error reading {filepath}: {e}")

    return operations


def get_response_path(operation, source):
    """Return the filesystem path for a response schema."""
    if source == "events":
        return None  # events don't have response files
    return os.path.join(RESPONSE_DIR, source, f"{operation}.json")


def extract_examples(schema, title, example_data):
    """
    Extract examples from a schema's 'examples' array.
    Uses example_description.json for labels/descriptions.
    """
    if "examples" not in schema:
        return {}
    examples = schema["examples"]
    if not isinstance(examples, list) or len(examples) == 0:
        return {}

    result = OrderedDict()
    descriptions = example_data.get(title, {})
    desc_keys = list(descriptions.keys()) if descriptions else []

    for i, example in enumerate(examples):
        if i < len(desc_keys):
            label = desc_keys[i]
            desc = descriptions[label]
        else:
            label = f"example{i + 1}"
            desc = None
        entry = OrderedDict()
        if desc:
            entry["description"] = desc
        entry["value"] = example
        result[label] = entry
    return result


def extract_schema(raw_schema, json_file_path=None):
    """
    Extract the OpenAPI schema from a raw JSON schema file.
    Resolves $ref references to YAML files by loading and inlining them.
    """
    SKIP_KEYS = {"title", "x-stoplight", "x-tag", "examples", "description"}
    schema = OrderedDict()
    for key, value in raw_schema.items():
        if key not in SKIP_KEYS:
            schema[key] = _resolve_refs(value, json_file_path)
    if "type" not in schema:
        schema["type"] = "object"
    return schema


def _resolve_refs(obj, base_path):
    """Recursively resolve $ref pointers in a schema object."""
    if isinstance(obj, dict):
        if "$ref" in obj:
            ref_path = obj["$ref"]
            # Resolve relative to the JSON file's directory
            if base_path and not os.path.isabs(ref_path):
                abs_ref = os.path.normpath(
                    os.path.join(os.path.dirname(base_path), ref_path)
                )
            else:
                abs_ref = ref_path
            if os.path.exists(abs_ref):
                try:
                    with open(abs_ref, "r", encoding="utf-8") as f:
                        ref_content = yaml.safe_load(f)
                    if isinstance(ref_content, dict):
                        # Strip non-schema keys from the resolved YAML too
                        clean = OrderedDict()
                        for k, v in ref_content.items():
                            if k not in ("title", "x-stoplight", "examples"):
                                clean[k] = _resolve_refs(v, abs_ref)
                        return clean
                except Exception:
                    pass
            # If we can't resolve, drop the $ref and return empty object
            return OrderedDict([("type", "object")])
        else:
            result = OrderedDict()
            for k, v in obj.items():
                result[k] = _resolve_refs(v, base_path)
            return result
    elif isinstance(obj, list):
        return [_resolve_refs(item, base_path) for item in obj]
    else:
        return obj


def filter_response_code_description(schema, error_codes_for_cmd):
    """Replace the code field description in a response schema with only the relevant error codes."""
    if not error_codes_for_cmd:
        return
    # Navigate to response.properties.code
    props = schema.get("properties", {})
    response_obj = props.get("response", {})
    if isinstance(response_obj, dict):
        resp_props = response_obj.get("properties", {})
        code_field = resp_props.get("code")
        if isinstance(code_field, dict) and "description" in code_field:
            lines = ["Response code indicating success or failure."]
            for e in error_codes_for_cmd:
                lines.append(f"- **{e['code']}** \u2014 {e['description']}")
            code_field["description"] = "\n".join(lines)
            # Update maximum to match actual range
            max_code = max(e["code"] for e in error_codes_for_cmd)
            code_field["maximum"] = max_code


def sort_operations(operations, tag_config):
    """
    Sort operations to match the order defined in tag_config.json tag_groups.
    Operations whose tag appears earlier in the config appear first.
    Within the same tag, uses explicit operation_order if defined,
    otherwise falls back to alphabetical order.
    """
    tag_groups = tag_config.get("tag_groups", {})
    op_order = tag_config.get("operation_order", {})

    # Build a tag -> (group_index, tag_index) mapping for sorting
    tag_order = {}
    for g_idx, (group_name, tags) in enumerate(tag_groups.items()):
        for t_idx, tag_name in enumerate(tags):
            tag_order[tag_name] = (g_idx, t_idx)

    def sort_key(op_tuple):
        op_name, tag, source, filepath = op_tuple
        order = tag_order.get(tag, (999, 999))
        # Use explicit operation order if defined for this tag
        if tag in op_order:
            try:
                op_idx = op_order[tag].index(op_name)
            except ValueError:
                op_idx = 999
            return (order[0], order[1], op_idx)
        return (order[0], order[1], op_name)

    return sorted(operations, key=sort_key)


def build_openapi():
    """Build the complete OpenAPI structure."""
    tag_config = load_tag_config()
    op_descriptions = load_operation_descriptions()
    example_data = load_example_descriptions()
    error_codes_map = load_error_codes()

    tag_groups = tag_config.get("tag_groups", {})
    tag_descriptions = tag_config.get("tag_descriptions", {})

    # Auto-discover operations
    operations = discover_operations()
    operations = sort_operations(operations, tag_config)

    print(f"  Discovered {len(operations)} operations")

    # Collect all tags that are actually used
    used_tags = OrderedDict()
    for op_name, tag, source, filepath in operations:
        if tag not in used_tags:
            used_tags[tag] = True

    # --- Info ---
    openapi = OrderedDict()
    openapi["openapi"] = "3.0.0"
    openapi["info"] = OrderedDict([
        ("title", "RFD40 / RFD90 API reference document"),
        ("version", "v2"),
        ("description",
         "MQTT-based API for managing and controlling Zebra RFD40 and RFD90 RFID readers. "
         "Send JSON command payloads to the MQTT command topic and receive responses on the response topic."),
    ])

    # --- Tags ---
    tags = []
    all_tag_names = set()
    for group_tags in tag_groups.values():
        for tag_name in group_tags:
            if tag_name not in all_tag_names:
                all_tag_names.add(tag_name)
                tag_entry = OrderedDict()
                tag_entry["name"] = tag_name
                if tag_name in tag_descriptions:
                    tag_entry["description"] = tag_descriptions[tag_name]
                tags.append(tag_entry)

    # Add any tags found in schemas but not in tag_config (auto-discovered new tags)
    for tag_name in used_tags:
        if tag_name not in all_tag_names:
            all_tag_names.add(tag_name)
            tag_entry = OrderedDict()
            tag_entry["name"] = tag_name
            tags.append(tag_entry)
            print(f"  NEW TAG discovered: '{tag_name}' (not in tag_config.json - add it for sidebar ordering)")

    openapi["tags"] = tags

    # --- x-tagGroups ---
    x_tag_groups = []
    for group_name, group_tags in tag_groups.items():
        x_tag_groups.append(OrderedDict([
            ("name", group_name),
            ("tags", list(group_tags)),
        ]))

    # Auto-add a group for uncategorized tags
    all_grouped_tags = set()
    for grp in tag_groups.values():
        all_grouped_tags.update(grp)
    uncategorized = [t for t in used_tags if t not in all_grouped_tags]
    if uncategorized:
        x_tag_groups.append(OrderedDict([
            ("name", "Other"),
            ("tags", uncategorized),
        ]))
        print(f"  NEW GROUP 'Other' created for tags: {uncategorized}")

    openapi["x-tagGroups"] = x_tag_groups

    # --- Paths ---
    paths = OrderedDict()
    skipped = []

    for op_name, tag_name, source, req_path in operations:
        try:
            req_schema = load_json(req_path)
        except (json.JSONDecodeError, Exception) as e:
            skipped.append(f"  SKIP {op_name}: error reading {req_path}: {e}")
            continue

        title = req_schema.get("title", op_name)
        # Priority: operation_descriptions.json > JSON file description
        description = op_descriptions.get(op_name) or req_schema.get("description", None)

        # Remove legacy footer text if present
        if isinstance(description, str):
            description = re.sub(r"\n\n\*\*Supported readers:\*\*\s*RFD40,\s*RFD90\s*$", "", description).strip()

        # Auto-add PDF download link at top of description (below heading)
        pdf_url = find_command_pdf(op_name)
        if pdf_url and isinstance(description, str) and "Download pdf:" not in description and "Download PDF]" not in description:
            pdf_link = f"\U0001F4C4 [Download PDF]({pdf_url})\n\n"
            description = pdf_link + description
        elif pdf_url and isinstance(description, str) and "Download pdf:" in description:
            # Remove existing PDF link from wherever it is, then prepend
            description = re.sub(r'\n*\*\*Download pdf:\*\*.*?\n*', '', description).strip()
            description = re.sub(r'\n*\U0001F4C4 \[Download PDF\].*?\n*', '', description).strip()
            pdf_link = f"\U0001F4C4 [Download PDF]({pdf_url})\n\n"
            description = pdf_link + description
        elif pdf_url and not description:
            description = f"\U0001F4C4 [Download PDF]({pdf_url})"

        # Build the operation
        op = OrderedDict()
        op["tags"] = [tag_name]
        op["summary"] = op_name
        if description:
            op["description"] = description

        if source == "events":
            # Events: payload goes under Response (device publishes this), no Request Body
            evt_examples = extract_examples(req_schema, title, example_data)
            evt_schema_clean = extract_schema(req_schema, req_path)
            evt_content = OrderedDict()
            evt_content["application/json"] = OrderedDict()
            evt_content["application/json"]["schema"] = evt_schema_clean
            if evt_examples:
                evt_content["application/json"]["examples"] = evt_examples

            op["responses"] = OrderedDict([
                ("default", OrderedDict([
                    ("description", f"{op_name} event payload"),
                    ("content", evt_content),
                ])),
            ])
        else:
            # Commands: payload goes under Request Body, response from response/ folder
            req_examples = extract_examples(req_schema, title, example_data)
            req_schema_clean = extract_schema(req_schema, req_path)
            req_content = OrderedDict()
            req_content["application/json"] = OrderedDict()
            req_content["application/json"]["schema"] = req_schema_clean
            if req_examples:
                req_content["application/json"]["examples"] = req_examples

            op["requestBody"] = OrderedDict([
                ("description", REQUEST_BODY_DESCRIPTIONS.get(op_name, "")),
                ("required", True),
                ("content", req_content),
            ])

            # Build response
            resp_path = get_response_path(op_name, source)
            if resp_path and os.path.exists(resp_path):
                try:
                    resp_schema = load_json(resp_path)
                    resp_title = resp_schema.get("title", op_name)
                    resp_examples = extract_examples(resp_schema, resp_title, example_data)

                    resp_schema_clean = extract_schema(resp_schema, resp_path)
                    # Filter the code field description to only show relevant error codes
                    filter_response_code_description(resp_schema_clean, error_codes_map.get(op_name, []))
                    resp_content = OrderedDict()
                    resp_content["application/json"] = OrderedDict()
                    resp_content["application/json"]["schema"] = resp_schema_clean
                    if resp_examples:
                        resp_content["application/json"]["examples"] = resp_examples

                    resp_desc = RESPONSE_PAYLOAD_DESCRIPTIONS.get(op_name, "")

                    op["responses"] = OrderedDict([
                        ("default", OrderedDict([
                            ("description", resp_desc),
                            ("content", resp_content),
                        ])),
                    ])
                except (json.JSONDecodeError, Exception):
                    op["responses"] = OrderedDict([
                        ("200", OrderedDict([("description", "Success")])),
                    ])
            else:
                op["responses"] = OrderedDict([
                    ("200", OrderedDict([("description", "Success")])),
            ])

        # Inject filtered error codes as x-error-codes extension + description table
        error_codes_for_cmd = error_codes_map.get(op_name, [])
        if error_codes_for_cmd:
            op["x-error-codes"] = [
                OrderedDict([
                    ("code", e["code"]),
                    ("description", e["description"]),
                    ("iot_status_code", e["iot_status_code"]),
                ])
                for e in error_codes_for_cmd
            ]
            # Append markdown table to description so RapiDoc renders it
            ec_lines = [
                "\n\n## Status / Error Codes\n",
                "| Code | Status Constant | Description |",
                "|------|----------------|-------------|",
            ]
            for e in error_codes_for_cmd:
                ec_lines.append(
                    f"| {e['code']} | `{e['iot_status_code']}` | {e['description']} |"
                )
            ec_table = "\n".join(ec_lines)
            current_desc = op.get("description", "")
            # Remove any previous error codes table (idempotent)
            current_desc = re.sub(r"\n\n## Status / Error Codes\n.*", "", current_desc, flags=re.DOTALL)
            op["description"] = current_desc + ec_table

        paths[f"/{op_name}"] = OrderedDict([("post", op)])

    openapi["paths"] = paths

    return openapi, skipped


def main():
    import subprocess

    print("Generating OpenAPI spec (pass 1 - for PDF generation) ...")
    openapi, skipped = build_openapi()

    # Write initial spec (PDFs need this to generate)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(openapi, f, indent=4, ensure_ascii=False)

    # Auto-generate PDFs for all commands
    print("\nGenerating command PDFs ...")
    export_script = os.path.join(SCRIPT_DIR, "export_command_pdf.py")
    commands = [path.lstrip("/") for path in openapi["paths"]]
    pdf_count = 0
    for cmd in commands:
        result = subprocess.run(
            [sys.executable, export_script, cmd],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True,
        )
        if result.returncode == 0 and "Generated PDF" in result.stdout:
            pdf_count += 1
        elif result.returncode != 0:
            print(f"  WARNING: PDF export failed for {cmd}: {result.stderr.strip()}")
    print(f"  {pdf_count} PDFs generated in docs/command-pdfs/")

    # Rebuild OpenAPI spec (pass 2 - now PDF links will be auto-injected)
    print("\nRegenerating OpenAPI spec (pass 2 - with PDF links) ...")
    openapi, skipped = build_openapi()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(openapi, f, indent=4, ensure_ascii=False)

    # Count stats
    n_paths = len(openapi["paths"])
    n_tags = len(openapi["tags"])
    n_groups = len(openapi["x-tagGroups"])

    print(f"  {n_groups} tag groups, {n_tags} tags, {n_paths} endpoints")
    print(f"  Written to {OUTPUT_PATH}")

    if skipped:
        print("\nWarnings:")
        for s in skipped:
            print(s)

    # Auto-rebuild HTML pages
    print("\nRebuilding HTML pages ...")
    build_script = os.path.join(SCRIPT_DIR, "build_pages.py")
    subprocess.run([sys.executable, build_script], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    main()
