---
title: Getting Started
description: Step-by-step guide to making your first successful API call.
---

## 2. Getting Started

A step-by-step guide to configure IoT Connector and make your first successful command call.

### 2.0. Where API Documentation Fits

This documentation is split into two parts so developers can find information quickly:

1. **Guides** (Introduction, Overview, Getting Started, Tutorials, Troubleshooting): setup flow, architecture, and usage patterns.
2. **API Reference** (OpenAPI and AsyncAPI): exact commands, schemas, payload fields, response codes, and topic contracts.

For RFD40/90 IoT Connector, most application developers integrate through REST-style definitions and MQTT message contracts. For this reason, API Reference is a dedicated section and is not mixed into long-form guides.

Use this page to complete environment setup and first connectivity checks, then move to API Reference for command-level integration.

### 2.1. Before You Begin

To use IoT Connector (Control and Data interfaces), you need:

1. **RFD40/90 reader** with firmware that supports IoT Connector.
2. **MQTT broker** such as Mosquitto, EMQX, or HiveMQ.
3. **MQTT client** to publish commands and subscribe to responses/events (for example, MQTTX).
4. **Network connectivity** so both the reader and client can reach the broker over Wi-Fi or Ethernet.
5. **Certificates** if you use MQTT TLS (port 8883).

For Management and Event endpoints, use 123RFID Desktop. For Control and Data endpoints, use IOTC_DataCtrlUtil or ZETI commands.

### 2.2. IoT Connector Endpoints at a Glance

IoT Connector supports these endpoint types:

1. **Management**: Inbound commands and outbound responses for device management.
2. **Event**: Outbound asynchronous health/events/alerts.
3. **Control**: Inbound commands and outbound responses for RFID operations.
4. **Data**: Outbound tag and barcode event data.

![Figure 2-1. IoT Connector endpoint model](../../docs/assets/getting-started/figure-2-1-endpoint-model.png)

*Figure 2-1. IoT Connector endpoint model showing Management, Event, Control, and Data flows.*

### 2.3. Step 1: Connect the Reader to the Network

1. Configure Wi-Fi (or Ethernet) on the reader.
2. If secure connectivity is required, install certificates first.
3. Confirm the reader can reach the MQTT broker network.

![Figure 2-2. Reader network connection setup](../../docs/assets/getting-started/figure-2-2-network-setup.png)

*Figure 2-2. Reader network setup in the configuration tool before endpoint provisioning.*

### 2.4. Step 2: Configure Control and Data Endpoints

Use IOTC_DataCtrlUtil or ZETI to create endpoint configurations.

For each endpoint, configure:

1. **Endpoint type**: `control`, `data1` (and `data2` when available).
2. **Name**: Unique endpoint name.
3. **Protocol**: `MQTT` (1883) or `MQTT TLS` (8883).
4. **Broker URL**: Hostname or IP address.
5. **Tenant ID**.
6. **Keep Alive** and reconnection delays.
7. **Authentication**: Username and password (if required).

After saving the endpoint:

1. Activate the endpoint.
2. Reboot the device so the broker connection starts with the new configuration.

![Figure 2-3. Endpoint configuration form](../../docs/assets/getting-started/figure-2-3-endpoint-config.png)

*Figure 2-3. Control/Data endpoint configuration fields in IOTC_DataCtrlUtil.*

![Figure 2-4. Endpoint activation status](../../docs/assets/getting-started/figure-2-4-endpoint-activation.png)

*Figure 2-4. Endpoint activation result before device reboot.*

### 2.5. Step 3: Confirm Topic Configuration

Use the endpoint configuration output to confirm publish and subscribe topics.

Publish topic format:

```text
<Tenant ID>/<Configured Publish Topic>/<Device Serial Number>
```

Subscribe topic format:

```text
<Tenant ID>/<Configured Subscribe Topic>/<Device Serial Number>
```

Typical subscribe channels:

1. Command response topic.
2. Alert and event topic.
3. Data events topic.
4. Last will and testament topic.

![Figure 2-5. Topic mapping example](../../docs/assets/getting-started/figure-2-5-topic-mapping.png)

*Figure 2-5. Example topic mapping using tenant ID, configured topic path, and device serial number.*

### 2.6. Step 4: Verify Connectivity with get_status

Before running inventory commands, verify that Control endpoint messaging works end-to-end.

1. Connect your MQTT client to the same broker.
2. Subscribe to the reader command response topic.
3. Publish a `get_status` command to the reader publish topic.

Example request:

```json
{
  "command": "get_status",
  "requestId": "verify-001"
}
```

Expected result:

1. You receive a response on the command response topic.
2. The payload includes status details and a success response code.

![Figure 2-6. get_status command and response](../../docs/assets/getting-started/figure-2-6-get-status.png)

*Figure 2-6. Publishing `get_status` and validating a successful response on the response topic.*

### 2.7. If Verification Fails

If you do not receive a response:

1. Confirm broker service is running.
2. Confirm reader and client are both connected to the broker network.
3. Confirm endpoint is activated.
4. Confirm device was rebooted after endpoint activation.
5. Confirm tenant ID, topic path, and device serial number match exactly.
6. Confirm credentials and certificates (for MQTT TLS).

### 2.8. Next Steps

After `get_status` succeeds:

1. Configure operating mode and filters from API Reference.
2. Send `control_operation` commands to start and stop inventory.
3. Subscribe to Data topics to validate tag event output.

See also:

1. MQTT protocol and topic conventions.
2. API Reference for command schemas.
3. Troubleshooting for endpoint and message-flow failures.

