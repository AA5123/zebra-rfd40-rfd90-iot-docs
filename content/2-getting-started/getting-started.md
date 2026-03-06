---
title: Getting Started
description: Step-by-step guide to making your first successful API call.
---

## 2. Getting Started

A step-by-step guide to making your first successful API call.

### 2.1. Prerequisites

To use the IoT Connector (Control and Data interfaces), you need:

1. **MQTT broker** — e.g. Mosquitto, EMQX, or HiveMQ (see [support.txt](support.txt) for Mosquitto setup).
2. **Wi‑Fi (or Ethernet) connection** — The reader and your MQTT client must reach the broker.
3. **MQTT client** — To publish commands and subscribe to responses and events (e.g. MQTTX, or your own app).
4. **RFD40/90 sled** — With firmware that supports the IoT Connector.

For **Management** and **Event** endpoints, configuration is done via the **123RFID Desktop** application. For **Control** and **Data** endpoints, use the **IOTC_DataCtrlUtil** utility or **ZETI** commands (see Annexure in support documentation).

### 2.2. Initial Device and Network Configuration

1. **Connect the device to Wi‑Fi**  
   Configure Wi‑Fi (and certificates if using WPA-Enterprise/TLS) via 123RFID Desktop or the test utility. Ensure the reader can reach the MQTT broker.

2. **Configure Control and Data endpoints**  
   Using the IOTC Data & Control utility (or ZETI):
   - Add endpoint configuration: type (control, data1), name, protocol (MQTT or MQTT TLS), broker URL, port (1883/8883), tenant ID, keep-alive, credentials if required.
   - Activate the endpoint and **reboot the device** so it connects to the broker.

3. **Note publish and subscribe topics**  
   From the utility or `get_endpoint_config`, note:
   - **Publish topic** (where you send commands): `<Tenant ID>/<Publish Topic>/<Device Serial No>`
   - **Subscribe topics** for: command responses, events/alerts, data events, LWT.

4. **Connect your MQTT client** to the same broker and subscribe to the device's response and event topics; use the publish topic to send commands.

### 2.3. Verifying Connectivity (Using get_status)

Before running inventory or other commands, confirm the device is reachable and the Control endpoint is working:

1. **Publish** a **get_status** command to the device's **publish topic** with a JSON body, for example:

```json
{
  "command": "get_status",
  "requestId": "verify-001"
}
```

2. **Subscribe** to the **command response** topic for that device. You should receive a response containing status information and a `response.code` (e.g. `0` for success).

3. If you get no response, check:
   - Broker is running and reachable from the reader and from your client.
   - Endpoint is activated and device has been rebooted after activation.
   - Topic names match exactly (tenant ID, publish/subscribe topics, device serial number).
   - Wi‑Fi (or Ethernet) is connected and stable.

Once `get_status` returns successfully, you can proceed to [Control Interface](openapi) operations (e.g. `set_operating_mode`, `control_operation`) and subscribe to the **Data** topic for tag events.

