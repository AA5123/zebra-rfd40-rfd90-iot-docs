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
    "Device Status": (
        "Check what the scanner **is** — its identity, health, and regional settings.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `get_status` | Real-time health — battery, temperature, radio state, power source, clock sync, terminal connection |\n"
        "| `get_version` | Scanner identity — model, serial number, SKU, and firmware versions (main, scanner, radio, IoTC) |\n"
        "| `get_current_region` | Regulatory radio config — country, frequency channels, power limits, frequency hopping, LBT |\n\n"
        "All three are **read-only** commands. Use them for monitoring dashboards, firmware audits, and compliance checks."
    ),
    "Device Configuration": (
        "Read or write the scanner's **complete configuration** in a single command.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `get_config` | Retrieve everything — equivalent to calling get_version + get_status + get_current_region + get_wifi + get_eth + get_endpoint_config + get_installed_certificate at once |\n"
        "| `set_config` | Apply configuration changes — Wi-Fi, endpoint, events, and more in one payload |\n\n"
        "`get_config` is read-only. `set_config` is the primary way to push settings to one or many scanners."
    ),
    "Network Configuration": (
        "Manage the scanner's **Wi-Fi and Ethernet** network connections.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `get_wifi` | Current Wi-Fi status — connected SSID, IP address, signal, security type |\n"
        "| `set_wifi` | Configure Wi-Fi — add/update SSID, set security (WPA2/WPA3/Enterprise), IP settings |\n"
        "| `delete_wifi_profile` | Remove a saved Wi-Fi profile by SSID |\n"
        "| `get_eth` | Ethernet status — link state, speed, IP address, 802.1X security |\n\n"
        "The scanner supports both Wi-Fi and Ethernet simultaneously. Wi-Fi profiles are stored on device and auto-connect on reboot."
    ),
    "MQTT Endpoint Configuration": (
        "Configure **where the scanner sends data** — the MQTT broker connection.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `config_endpoint` | Set up or update the MQTT broker — URL, port, protocol, credentials, topics, TLS settings |\n"
        "| `get_endpoint_config` | Retrieve the current MQTT endpoint configuration |\n\n"
        "The scanner communicates with your backend via MQTT. These commands control the broker URL, publish/subscribe topics, QoS levels, keep-alive, and reconnect behavior."
    ),
    "Certificate Management": (
        "Manage **TLS/SSL certificates** for secure MQTT and Wi-Fi Enterprise connections.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `install_certificate` | Upload a certificate (CA, client, MQTT, Wi-Fi) to the scanner |\n"
        "| `delete_certificate` | Remove an installed certificate by name |\n"
        "| `get_installed_certificate` | List all certificates currently installed on the device |\n\n"
        "Certificates are required for MQTT-TLS connections and WPA2/WPA3 Enterprise Wi-Fi authentication."
    ),
    "System Operations": (
        "Perform **system-level actions** on the scanner.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `reboot` | Restart the scanner — applies pending configuration changes |\n"
        "| `set_os` | Trigger a firmware update on the device |\n\n"
        "⚠️ Both commands interrupt normal scanner operation. `reboot` requires no active inventory. `set_os` requires sufficient battery level."
    ),
    "Inventory Control": (
        "**Start and stop** RFID tag reading (inventory) operations.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `control_operation` | Start or stop an RFID inventory scan |\n\n"
        "When started, the scanner continuously reads RFID tags and publishes tag data events to the MQTT broker. Use `stop` to end the scan."
    ),
    "Operating Mode": (
        "Configure **how the scanner reads tags** — mode, power, and session settings.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `set_operating_mode` | Set the RFID operating mode — transmit power, session, tag population, and more |\n"
        "| `get_operating_mode` | Retrieve the current RFID operating mode settings |\n\n"
        "Operating mode controls the RF parameters that affect read range, speed, and tag population handling."
    ),
    "Tag Filtering": (
        "Filter **which tags are reported** after an inventory scan.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `set_post_filter` | Define filter rules — match by EPC pattern, memory bank, or mask to include/exclude specific tags |\n"
        "| `get_post_filter` | Retrieve the current tag filter configuration |\n\n"
        "Post-filters are applied after the radio reads tags, reducing noise by only reporting tags that match your criteria."
    ),
    "Device Health": (
        "Periodic **heartbeat events** sent by the scanner to confirm it is alive and connected.\n\n"
        "| Event | Purpose |\n"
        "|---|---|\n"
        "| `heartBeatEVT` | Periodic health pulse — battery status, inventory state, and connectivity confirmation |\n\n"
        "Heartbeat interval is configurable via `set_config` → `eventConfiguration` → `heartbeatConfiguration`. If heartbeats stop arriving, the scanner may be offline or disconnected."
    ),
    "Alerts": (
        "**Alert events** triggered by significant device state changes.\n\n"
        "| Event | Purpose |\n"
        "|---|---|\n"
        "| `alerts` | Full alert details — battery, temperature, power, network, firmware, and antenna alerts |\n"
        "| `alert_short` | Compact alert summary for lightweight monitoring |\n\n"
        "Alerts are push-based — the scanner publishes them automatically when a threshold is crossed or a state changes. Enable/disable specific alerts via `set_config` → `eventConfiguration`."
    ),
    "Exceptions": (
        "**Exception events** for errors and unexpected conditions.\n\n"
        "| Event | Purpose |\n"
        "|---|---|\n"
        "| `exceptionEVT` | Error reports — radio failures, configuration errors, and other exceptional conditions |\n\n"
        "Exceptions indicate something went wrong that may require operator attention or automated recovery."
    ),
    "MQTT Connectivity": (
        "**MQTT connection state** change events.\n\n"
        "| Event | Purpose |\n"
        "|---|---|\n"
        "| `mqttConnEVT` | Broker connection/disconnection events — tracks when the scanner connects to or loses connection with the MQTT broker |\n\n"
        "Use these events to monitor broker connectivity across your fleet and trigger reconnection alerts."
    ),
    "Event Configuration": (
        "Configure **which events** the scanner publishes to the MQTT broker.\n\n"
        "| Command | Purpose |\n"
        "|---|---|\n"
        "| `config_events` | Enable or disable specific events and alerts — heartbeat, battery, temperature, network, firmware, NTP, etc. |\n\n"
        "Event configuration controls which device events are forwarded to the broker. You can also set the heartbeat interval and choose what data to include in heartbeats."
    ),
    "Tag Data Event": (
        "**RFID tag read data** published during an active inventory scan.\n\n"
        "| Event | Purpose |\n"
        "|---|---|\n"
        "| `dataEVT` | Tag data — EPC, RSSI, antenna, timestamp, and optional memory bank data for each tag read |\n\n"
        "Tag data events stream continuously while inventory is running. Each event contains one or more tag reads with EPC (Electronic Product Code), signal strength, and read metadata."
    ),
}

# ---------------------------------------------------------------------------
# Enhanced operation descriptions (overrides the JSON file description)
# ---------------------------------------------------------------------------
OPERATION_DESCRIPTIONS = {
    "get_status": (
        "Retrieves **real-time health and status** of the scanner — battery, temperature, "
        "radio, power, clock sync, and terminal connection.\n\n"
        "**Response fields:**\n\n"
        "| Field | What it tells you |\n"
        "|---|---|\n"
        "| `powerSource` | How the scanner is powered — DC, Wall Charger, USB, or Cradle |\n"
        "| `radioActivity` | Whether the RFID radio is currently active or idle |\n"
        "| `radioConnection` | Whether the radio module is connected or disconnected |\n"
        "| `hostname` | The scanner's network hostname |\n"
        "| `systemTime` | Current device clock in ISO 8601 format |\n"
        "| `temperature` | Internal temperature in °C — monitor for overheating |\n"
        "| `ntp` | Clock sync status — offset (ms drift) and reach (sync success history) |\n"
        "| `terminalConnection` | Paired phone/tablet — connection status and type (Bluetooth, USB, CIO) |\n"
        "| `batteryStatus` | Battery capacity (mAh), charge %, health (Good/Average/Poor), charge state |\n\n"
        "**Typical use cases:**\n"
        "- Dashboard monitoring — show live scanner health on a management console.\n"
        "- Battery management — track charge levels across a fleet before a shift starts.\n"
        "- Troubleshooting — check if radio is connected, temperature is normal, clock is synced."
    ),
    "get_version": (
        "Retrieves the **scanner's identity card** — model, serial number, SKU, and all firmware versions.\n\n"
        "**Response fields:**\n\n"
        "| Field | What it tells you |\n"
        "|---|---|\n"
        "| `firmwareVersion` | Main device firmware version |\n"
        "| `model` | Scanner model — RFD40 or RFD90 |\n"
        "| `serialNumber` | Unique device serial number |\n"
        "| `sku` | Stock Keeping Unit — encodes model, features, and region (e.g. `RFD4031-G10B700-US`) |\n"
        "| `detailedVersions.scannerFirmware` | Barcode scanner module firmware |\n"
        "| `detailedVersions.radioFirmware` | RFID radio module firmware |\n"
        "| `detailedVersions.iotcVersion` | IoT Connector software version |\n\n"
        "**Typical use cases:**\n"
        "- Inventory — collect model/serial/SKU across all scanners for asset tracking.\n"
        "- Firmware management — check which scanners need firmware updates."
    ),
    "get_current_region": (
        "Retrieves the **regulatory radio configuration** of the scanner — which country's rules it follows, "
        "what frequencies it can use, and power limits.\n\n"
        "**Response fields:**\n\n"
        "| Field | What it tells you |\n"
        "|---|---|\n"
        "| `country` | The country this scanner is configured for (e.g. United States, Germany) |\n"
        "| `regulatoryStandard` | The radio regulation it follows (e.g. FCC for US, ETSI for Europe) |\n"
        "| `frequencyHopping` | Whether the scanner automatically switches between frequency channels |\n"
        "| `lbtEnabled` | Whether Listen Before Talk is enabled (required in some regions like Japan/EU) |\n"
        "| `maxTxPowerSupported` | Maximum allowed transmit power in dBm |\n"
        "| `minTxPowerSupported` | Minimum transmit power in dBm |\n"
        "| `channelData` | List of all available frequency channels (in kHz) the scanner can use |\n\n"
        "**Typical use cases:**\n"
        "- Compliance auditing — verify scanners are configured for the correct country before deployment.\n"
        "- RF planning — check available channels and power limits for site planning.\n"
        "- Multi-region management — confirm scanners shipped to different countries have the right region settings."
    ),
    "get_config": (
        "Retrieves the **complete device configuration** in a single response — equivalent to calling "
        "`get_version`, `get_status`, `get_current_region`, `get_wifi`, `get_eth`, `get_endpoint_config`, "
        "and `get_installed_certificate` all at once.\n\n"
        "**Response sections:**\n\n"
        "| Section | Contents |\n"
        "|---|---|\n"
        "| `readerVersion` | Model, serial number, SKU, firmware versions (main, scanner, radio, IoTC) |\n"
        "| `deviceStatus` | Power source, radio state, temperature, battery health, NTP sync, terminal connection |\n"
        "| `currentRegion` | Country, regulatory standard, frequency channels, power limits, frequency hopping, LBT |\n"
        "| `wifiConfig` | Wi-Fi interface status, connected SSID, IP address, MAC, DHCP, security type |\n"
        "| `ethConfig` | Ethernet interface status, link speed, IP configuration |\n"
        "| `epConfig` | Active MQTT endpoint: type, broker URL, port, protocol, credentials, topics, security |\n"
        "| `installedCerts` | List of installed certificates with type, validity dates, and algorithms |\n"
        "| `eventConfiguration` | Which events/alerts are enabled (heartbeat, battery, temperature, firmware, network, etc.) |\n\n"
        "**Typical use cases:**\n"
        "- First-time setup — see how a blank scanner is configured before applying changes via `set_config`.\n"
        "- Troubleshooting — get the full picture when something isn't working.\n"
        "- Auditing — verify all settings across a fleet of scanners."
    ),
}

# ---------------------------------------------------------------------------
# Enhanced response descriptions (overrides the default "Response" text)
# ---------------------------------------------------------------------------
RESPONSE_DESCRIPTIONS = {
    "get_status": "get_status response",
    "get_version": "get_version response",
    "get_current_region": "get_current_region response",
    "get_config": "get_config response",
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
        description = OPERATION_DESCRIPTIONS.get(operation) or req_schema.get("description", None)

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

                resp_desc = RESPONSE_DESCRIPTIONS.get(operation, f"{operation} response")

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
