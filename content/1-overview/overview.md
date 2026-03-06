---
title: Overview
description: High-level introduction to the RFD40/RFD90 IoT Connector API.
---

## 1. Overview

A high-level introduction to the API, its architecture, and purpose.

### 1.1. Purpose of This Document

This document describes the **Zebra IoT Connector** API for **RFD40** and **RFD90** handheld RFID readers. It is intended for developers and integrators who need to:

- Configure and manage readers over the network (Wi‑Fi or Ethernet).
- Control RFID operations (start/stop inventory, operating modes, filters).
- Receive tag and barcode data and device events (health, alerts, errors) in real time.

The API is built on **MQTT** with **JSON**-formatted payloads, so it can be used from cloud or on-premise applications without proprietary protocols.

### 1.2. Supported Devices

| Device | Description |
|--------|-------------|
| **RFD40** | Zebra handheld RFID reader (IoT Connector capable). |
| **RFD90** | Zebra handheld RFID reader (IoT Connector capable). |

Both are referred to as **RFD40/90** or **RFD4090** in Zebra materials. Management and Event endpoints can be configured with the **123RFID Desktop** application; Control and Data endpoints use the **IOTC Data & Control utility** or **ZETI commands** (see [Getting Started](getting-started)).

### 1.3. System Architecture

The IoT Connector exposes **four interfaces**, each configurable to a different MQTT endpoint:

| # | Endpoint type | Direction | Role |
|---|----------------|-----------|------|
| 1 | **Management** | In/Out | Device management: firmware, configuration. Synchronous command/response. |
| 2 | **Event** | Out | Asynchronous messages: heartbeats, health, alerts, errors, warnings. |
| 3 | **Control** | In/Out | RFID control: start/stop inventory, operating mode, post-filters. Synchronous command/response. |
| 4 | **Data** | Out | Tag and barcode events (EPC, TID, RSSI, etc.) for inventory and access results. |

- **Management** and **Event** are often used with Enterprise Mobility Management (EMM) solutions (e.g. 42gears, SOTI).
- **Control** and **Data** are used by your application to run inventories and receive tag data.

### 1.4. Communication Protocol (MQTT + JSON)

- **Protocol:** MQTT (optionally MQTT over TLS on port 8883; unsecured on 1883).
- **Payload format:** JSON. All commands and responses use a `command` (or equivalent) field and a `requestId` for correlation.
- **Topics:**  
  - **Publish (to device):** `<Tenant ID>/<Publish Topic>/<Device Serial No>`  
  - **Subscribe (from device):** separate topics for command responses, events/alerts, data events, and Last Will and Testament (LWT).

Details of topic layout and message flow are in [MQTT Communication Protocol](mqtt-protocol).

