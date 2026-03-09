#!/usr/bin/env python3
"""
generate_openapi.py
-------------------
Reads JSON schema files from schemas/commands/, schemas/response/, and schemas/events/
and generates docs/openapi.yaml with proper x-tagGroups categorization.

Usage:
    python scripts/generate_openapi.py
"""

import json
import os
import sys
from collections import OrderedDict

import yaml

# ---------------------------------------------------------------------------
# Configuration: map each JSON file to its tag and group
# ---------------------------------------------------------------------------

# x-tagGroups define the top-level sidebar groups
TAG_GROUPS = OrderedDict([
    ("Management", [
        "Device Status",
        "Device Configuration",
        "Network Configuration",
        "MQTT Endpoint Configuration",
        "Certificate Management",
        "System Operations",
    ]),
    ("Control", [
        "Inventory Control",
        "Operating Mode",
        "Tag Filtering",
    ]),
    ("Events", [
        "Device Health",
        "Alerts",
        "Exceptions",
        "MQTT Connectivity",
        "Event Configuration",
    ]),
    ("Data", [
        "Tag Data Event",
    ]),
])

# Tag descriptions (shown when you click a tag heading in Redoc)
TAG_DESCRIPTIONS = {
    "Device Status": "Device Status: get_status, get_version, get_current_region",
    "Device Configuration": "Device Configuration: get_config, set_config",
    "Network Configuration": "Network Configuration: get_wifi, set_wifi, delete_wifi_profile, get_eth",
    "MQTT Endpoint Configuration": "MQTT Endpoint Configuration: config_endpoint, get_endpoint_config",
    "Certificate Management": "Certificate Management: install_certificate, delete_certificate, get_installed_certificate",
    "System Operations": "System Operations: reboot, set_os",
    "Inventory Control": "Inventory Control: control_operation (start/stop)",
    "Operating Mode": "Operating Mode: set_operating_mode, get_operating_mode",
    "Tag Filtering": "Tag Filtering: set_post_filter, get_post_filter",
    "Device Health": "Device Health: heartBeatEVT",
    "Alerts": "Alerts: alerts, alert_short",
    "Exceptions": "Exceptions: exceptionEVT",
    "MQTT Connectivity": "MQTT Connectivity: mqttConnEVT",
    "Event Configuration": "Event Configuration: config_events",
    "Tag Data Event": "Tag Data Event: dataEVT",
}

# Map: operation filename (without .json) -> (tag name, source folder key)
# Source folder key: "dev_mgmt", "control", or "events"
OPERATION_MAP = OrderedDict([
    # --- Management > Device Status ---
    ("get_status",               ("Device Status",                "dev_mgmt")),
    ("get_version",              ("Device Status",                "dev_mgmt")),
    ("get_current_region",       ("Device Status",                "dev_mgmt")),
    # --- Management > Device Configuration ---
    ("get_config",               ("Device Configuration",         "dev_mgmt")),
    ("set_config",               ("Device Configuration",         "dev_mgmt")),
    # --- Management > Network Configuration ---
    ("get_wifi",                 ("Network Configuration",        "dev_mgmt")),
    ("set_wifi",                 ("Network Configuration",        "dev_mgmt")),
    ("delete_wifi_profile",      ("Network Configuration",        "dev_mgmt")),
    ("get_eth",                  ("Network Configuration",        "dev_mgmt")),
    # --- Management > MQTT Endpoint Configuration ---
    ("config_endpoint",          ("MQTT Endpoint Configuration",  "dev_mgmt")),
    ("get_endpoint_config",      ("MQTT Endpoint Configuration",  "dev_mgmt")),
    # --- Management > Certificate Management ---
    ("install_certificate",      ("Certificate Management",       "dev_mgmt")),
    ("delete_certificate",       ("Certificate Management",       "dev_mgmt")),
    ("get_installed_certificate",("Certificate Management",       "dev_mgmt")),
    # --- Management > System Operations ---
    ("reboot",                   ("System Operations",            "dev_mgmt")),
    ("set_os",                   ("System Operations",            "dev_mgmt")),
    # --- Control > Inventory Control ---
    ("control_operation",        ("Inventory Control",            "control")),
    # --- Control > Operating Mode ---
    ("set_operating_mode",       ("Operating Mode",               "control")),
    ("get_operating_mode",       ("Operating Mode",               "control")),
    # --- Control > Tag Filtering ---
    ("set_post_filter",          ("Tag Filtering",                "control")),
    ("get_post_filter",          ("Tag Filtering",                "control")),
    # --- Events > Device Health ---
    ("heartBeatEVT",             ("Device Health",                "events")),
    # --- Events > Alerts ---
    ("alerts",                   ("Alerts",                       "events")),
    ("alert_short",              ("Alerts",                       "events")),
    # --- Events > Exceptions ---
    ("exceptionEVT",             ("Exceptions",                   "events")),
    # --- Events > MQTT Connectivity ---
    ("mqttConnEVT",              ("MQTT Connectivity",            "events")),
    # --- Events > Event Configuration ---
    ("config_events",            ("Event Configuration",          "dev_mgmt")),
    # --- Data > Tag Data Event ---
    ("dataEVT",                  ("Tag Data Event",               "events")),
])

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


def load_json(filepath):
    """Load a JSON file preserving key order."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def load_example_descriptions():
    """Load the example_description.json mapping file."""
    path = os.path.join(SCHEMAS_DIR, "example_description.json")
    if os.path.exists(path):
        return load_json(path)
    return {}


def get_request_path(operation, source):
    """Return the filesystem path for a request schema."""
    if source == "events":
        return os.path.join(EVENTS_DIR, f"{operation}.json")
    elif source == "control":
        return os.path.join(COMMANDS_DIR, "control", f"{operation}.json")
    else:  # dev_mgmt
        return os.path.join(COMMANDS_DIR, "dev_mgmt", f"{operation}.json")


def get_response_path(operation, source):
    """Return the filesystem path for a response schema."""
    if source == "events":
        return None  # events don't have response files
    elif source == "control":
        return os.path.join(RESPONSE_DIR, "control", f"{operation}.json")
    else:  # dev_mgmt
        return os.path.join(RESPONSE_DIR, "dev_mgmt", f"{operation}.json")


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
    SKIP_KEYS = {"title", "x-stoplight", "examples", "description"}
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


def build_openapi():
    """Build the complete OpenAPI structure."""
    example_data = load_example_descriptions()

    # --- Info ---
    openapi = OrderedDict()
    openapi["openapi"] = "3.0.0"
    openapi["info"] = OrderedDict([
        ("title", "RFD40 / RFD90 IOT developer guide"),
        ("version", "v2"),
        ("description",
         "**This is an MQTT API, not REST.** There are no HTTP endpoints. "
         "Each operation is a **command payload**: publish JSON to the MQTT "
         "**command topic** (`<Tenant ID>/<Publish Topic>/<Device Serial No>`). "
         "Device replies are received on your configured **command response** topic. "
         "Use this API reference for payload schemas/examples and see "
         "**Getting Started** plus **MQTT Communication Protocol** for end-to-end flow."),
    ])

    # --- Tags ---
    tags = []
    all_tag_names = set()
    for group_tags in TAG_GROUPS.values():
        for tag_name in group_tags:
            if tag_name not in all_tag_names:
                all_tag_names.add(tag_name)
                tag_entry = OrderedDict()
                tag_entry["name"] = tag_name
                if tag_name in TAG_DESCRIPTIONS:
                    tag_entry["description"] = TAG_DESCRIPTIONS[tag_name]
                tags.append(tag_entry)
    openapi["tags"] = tags

    # --- x-tagGroups ---
    x_tag_groups = []
    for group_name, group_tags in TAG_GROUPS.items():
        x_tag_groups.append(OrderedDict([
            ("name", group_name),
            ("tags", list(group_tags)),
        ]))
    openapi["x-tagGroups"] = x_tag_groups

    # --- Paths ---
    paths = OrderedDict()
    skipped = []

    for operation, (tag_name, source) in OPERATION_MAP.items():
        req_path = get_request_path(operation, source)
        if not os.path.exists(req_path):
            skipped.append(f"  SKIP {operation}: request file not found at {req_path}")
            continue

        try:
            req_schema = load_json(req_path)
        except (json.JSONDecodeError, Exception) as e:
            skipped.append(f"  SKIP {operation}: error reading {req_path}: {e}")
            continue

        title = req_schema.get("title", operation)
        description = req_schema.get("description", None)

        # Build request body
        req_examples = extract_examples(req_schema, title, example_data)
        req_schema_clean = extract_schema(req_schema, req_path)
        req_content = OrderedDict()
        req_content["application/json"] = OrderedDict()
        req_content["application/json"]["schema"] = req_schema_clean
        if req_examples:
            req_content["application/json"]["examples"] = req_examples

        # Build the operation
        op = OrderedDict()
        op["tags"] = [tag_name]
        op["summary"] = operation
        if description:
            op["description"] = description
        op["requestBody"] = OrderedDict([
            ("required", True),
            ("content", req_content),
        ])

        # Build response
        resp_path = get_response_path(operation, source)
        if resp_path and os.path.exists(resp_path):
            try:
                resp_schema = load_json(resp_path)
                resp_title = resp_schema.get("title", operation)
                resp_examples = extract_examples(resp_schema, resp_title, example_data)

                resp_schema_clean = extract_schema(resp_schema, resp_path)
                resp_content = OrderedDict()
                resp_content["application/json"] = OrderedDict()
                resp_content["application/json"]["schema"] = resp_schema_clean
                if resp_examples:
                    resp_content["application/json"]["examples"] = resp_examples

                op["responses"] = OrderedDict([
                    ("200", OrderedDict([
                        ("description", "Success"),
                        ("content", resp_content),
                    ])),
                ])
            except (json.JSONDecodeError, Exception):
                op["responses"] = OrderedDict([
                    ("200", OrderedDict([("description", "Success")])),
                ])
        elif source == "events":
            # Events: show a description-only response
            op["responses"] = OrderedDict([
                ("200", OrderedDict([
                    ("description", "This is an asynchronous event published by the device. No request/response cycle."),
                ])),
            ])
        else:
            op["responses"] = OrderedDict([
                ("200", OrderedDict([("description", "Success")])),
            ])

        paths[f"/{operation}"] = OrderedDict([("post", op)])

    openapi["paths"] = paths

    return openapi, skipped


def main():
    print("Generating OpenAPI spec from schemas/ ...")
    openapi, skipped = build_openapi()

    # Write as JSON (Redoc reads JSON fine; extension is .yaml for compatibility)
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
    import subprocess
    build_script = os.path.join(SCRIPT_DIR, "build_pages.py")
    subprocess.run([sys.executable, build_script], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    main()
