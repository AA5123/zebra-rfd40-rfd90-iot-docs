---
title: Error Handling
description: Interpreting and troubleshooting errors and failure responses.
---

## 6. Error Handling

A guide to interpreting and troubleshooting errors and failure responses.

### 6.1. Command Failure Responses

When a command fails, the device publishes a response to the **command response** topic with:

- **response.code** — Non-zero value indicating failure. Specific codes are defined in the API/implementation (see your API documentation or OpenAPI examples).
- **response.description** — Short text describing the error (e.g. invalid parameter, not supported, timeout).

Always check `response.code` after sending a command. `0` typically means success; any other value indicates an error. Use `requestId` to match the response to your request.

### 6.2. Troubleshooting Common Issues

#### No Response from Device

- **Broker connectivity:** Ensure the MQTT broker is running and reachable from both the reader and your client (ping, firewall, VPN).
- **Topic:** Verify you are publishing to the **exact** publish topic (tenant ID, topic path, device serial number). No extra spaces or typos.
- **Endpoint state:** Control/Data endpoints must be **activated** and the device **rebooted** after activation. Use the IOTC utility or ZETI to confirm.
- **Wi‑Fi / Ethernet:** Confirm the reader is connected and has an IP. Use 123RFID or the utility to check connection status.
- **Payload:** Ensure the JSON is valid and includes `command` and `requestId`. Check for invalid or unsupported field values.

#### No Tag Data Received

- **Data topic:** Subscribe to the **Data events** topic (e.g. `zebra/DATA/clients/data1event/<SerialNo>`), not only the command response topic.
- **Inventory running:** Tag data is sent only when inventory is **started** via `control_operation` (start). Send a start command and keep the session active.
- **Operating mode:** In **FAST_READ** profile, tag data events are not reported. Use another profile (e.g. CYCLE_COUNT, BALANCED_PERFORMANCE) or ADVANCED with the desired settings.
- **Filters:** Post-filters or select/query settings may exclude all tags. Try with no or minimal filters to confirm tags are read.
- **Antenna / environment:** Verify tags are in range and antenna is connected; check for RF interference or power issues.

#### MQTT Connection Issues

- **Port and protocol:** Use 1883 for MQTT and 8883 for MQTT TLS. Ensure the broker is listening on the expected port.
- **Certificates:** For MQTT TLS, ensure PEM (PKCS#1) certificates are installed on the device and the broker accepts them. Use the utility to add/remove certificates.
- **Credentials:** If the broker requires username/password, configure them in the endpoint and ensure they are correct.
- **Keep-alive and LWT:** Configure keep-alive so the broker does not disconnect idle clients. Use the LWT topic to detect unexpected disconnects.
- **Debug:** Enable debug logs (e.g. ZETI `sa .dp 1`) to see connection attempts and errors on the device.

For further support (e.g. early access features), contact **ZebraRFIDEarlyAccess@zebra.com** as indicated in the product documentation.

