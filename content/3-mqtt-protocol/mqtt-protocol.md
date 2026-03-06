---
title: MQTT Communication Protocol
description: Topic structure and message flow for the IoT Connector API.
---

## 3. MQTT Communication Protocol

This section defines how to structure topics and messages to communicate with the API.

### 3.1. Topic Structure and Naming Conventions

Topics follow a consistent pattern. **Publish** and **Subscribe** topics are configured per endpoint (via 123RFID or the Data & Control utility).

#### Publish topic (commands to the device)

Only **one** publish topic is used per device. All commands (Management, Control) are sent to this topic.

**Format:**

```
<Tenant ID>/<User Configured Publish Topic>/<Device Serial No>
```

**Example:**  
Tenant ID `zebra`, publish topic `CTRL/clients/cmnd`, device serial `RFD40-212735201D0053`:

- **Publish topic:** `zebra/CTRL/clients/cmnd/RFD40-212735201D0053`

#### Subscribe topics (from the device)

The device uses **four** subscribe topics. Your application should subscribe to the ones it needs:

| Purpose | Format | Example |
|--------|--------|--------|
| **Command response** | `<Tenant ID>/<Cmd Response Topic>/<Device Serial No>` | `zebra/CTRL/clients/resp/RFD40-212735201D0053` |
| **Alerts & events** | `<Tenant ID>/<Events & Alert Topic>/<Device Serial No>` | `zebra/CTRL/clients/event/RFD40-212735201D0053` |
| **Data events** | `<Tenant ID>/<Data Event Topic>/<Device Serial No>` | `zebra/DATA/clients/data1event/RFD40-212735201D0053` |
| **Last Will and Testament (LWT)** | `<Tenant ID>/<LWT Topic>/<Device Serial No>` | `zebra/CTRL/clients/rfid/RFD40-212735201D0053` |

Tenant ID, topic segments, and device serial number are configured in the endpoint and must match exactly.

### 3.2. Command and Response Flow

- **Synchronous:** You publish a **command** (JSON) to the **publish topic**. The device processes it and publishes a **response** (JSON) to the **command response** subscribe topic.
- **Correlation:** Include a `requestId` in the command and use the same (or matching) value in the response to pair requests with responses.
- **One publish topic:** Both Management and Control commands go to the same publish topic; the device distinguishes them by the `command` field in the payload.

Example flow:

1. Client publishes to `zebra/CTRL/clients/cmnd/RFD40-212735201D0053`:
   ```json
   { "command": "get_status", "requestId": "req-1" }
   ```
2. Device publishes to `zebra/CTRL/clients/resp/RFD40-212735201D0053`:
   ```json
   { "command": "get_status", "requestId": "req-1", "response": { "code": 0, "description": "Success" }, ... }
   ```

### 3.3. Asynchronous Event and Data Flow

- **Events and alerts** are published by the device **without** a prior command. Subscribe to the **Alerts & events** topic for:
  - Heartbeats (e.g. battery, temperature, inventory status).
  - Alerts and notifications (battery, firmware, network, etc.).
  - Errors and warnings.

- **Data events** (tag reads, barcode scans, access results) are published on the **Data events** topic. They are triggered by RFID activity (e.g. after you send `control_operation` start inventory). No request/response pairing; messages stream as tags are read.

- **Last Will and Testament (LWT)** is published by the broker when the device disconnects ungracefully, so you can detect offline readers.

For payload structures of events (e.g. `heartBeatEVT`, `alerts`, `dataEVT`), see [Data Models](data-models) and the [API Reference](openapi) Event and Data sections.

