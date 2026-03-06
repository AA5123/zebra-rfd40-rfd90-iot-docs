---
title: Data Models
description: Structure and fields for key JSON objects used in the API.
---

## 5. Data Models

This section describes the structure and fields for key JSON objects used in the API.

### 5.1. Tag Data Fields Explained

Tag data events (published on the **Data** subscribe topic) include the following kinds of fields when enabled via operating mode or access operations:

| Field | Description |
|-------|-------------|
| **EPC** | Electronic Product Code — primary tag identifier. |
| **TID** | Tag Identifier — factory-programmed identifier. |
| **USER** | User memory bank contents (when read via access operations). |
| **PC** | Protocol Control bits. |
| **XPC** | Extended Protocol Control (if supported). |
| **CRC** | Cyclic redundancy check (not included in current tag data events per product notes). |
| **RSSI** | Received Signal Strength Indicator (dBm). |
| **PHASE** | Phase of the backscatter. |
| **SEEN_COUNT** / **SEENCOUNT** | Number of times the tag was seen in the current inventory. |
| **ANTENNA** | Antenna port that read the tag. |
| **CHANNEL** | RF channel. |
| **MAC** / **HOSTNAME** | Device identifiers when included in metadata. |

**Note:** In the **FAST_READ** profile, tag data events are not reported. For memory bank data (e.g. USER) during standard inventory, use **access operations** in `set_operating_mode`; first/last seen times and user-defined strings are not currently supported in tag data events.

### 5.2. Other Key Data Structures

#### Command envelope (request)

All commands share a common pattern:

- **command** (string) — Command name, e.g. `get_status`, `set_operating_mode`, `control_operation`.
- **requestId** (string) — Client-defined ID for correlating with the response.
- Additional fields depend on the command (e.g. `operatingMode`, `postFilterPayload`).

#### Response envelope

- **command** (string) — Echo of the command name.
- **requestId** (string) — Same as in the request.
- **response** — Object with at least:
  - **code** (number) — `0` for success; non-zero for errors (see [Error Handling](error-handling)).
  - **description** (string) — Short status or error message.
- **apiVersion** (optional) — API version string.
- Command-specific payload (e.g. `postFilterPayload`, `operatingModePayload`).

#### Alert / event payloads

- **id** — Event or alert identifier (e.g. `BATTERY_CRITICAL_SET`, `FIRMWARE_DOWNLOAD_SUCCESS`).
- **timestamp** — Time of the event.
- **type** — e.g. `ALERT`, `NOTIFICATION`.
- **priority** — e.g. `LOW`, `HIGH`, `CRITICAL`.
- **messageID** — e.g. `ZEBRA_RFID_HH_ALERTS`.
- **description** — Human-readable description.

#### Endpoint and configuration structures

- **Endpoint configuration** — Includes type (control, data1), name, protocol (MQTT/MQTT TLS), URL, port, tenant ID, keep-alive, reconnection delay, authentication (username/password), and optional certificates.
- **Operating mode** — Includes profiles (e.g. `BALANCED_PERFORMANCE`, `ADVANCED`), `advancedConfigurations` (transmit power, link profile, session, dynamic power), `accessOperations`, `radioStartConditions`, `radioStopConditions`, `query`, `select`, and `tagMetaDataToEnable`.

For full request/response examples, see the [API Reference](openapi) and the OpenAPI spec `openapi.yaml`.

