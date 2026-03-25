## Overview

The `get_status` command retrieves the current status of a Zebra handheld RFID reader. The response includes power source information, radio activity and connection state, device temperature, system time, Network Time Protocol (NTP) synchronization details, terminal connection status, and battery health metrics.

Use this command to monitor device health, verify connectivity before starting operations, and collect telemetry data for fleet management dashboards. The command requires no configuration parameters beyond the standard envelope fields.

> **Note •** The `deviceStatus` object in the response is optional. When the device cannot retrieve status information (response code `3`), the response omits this object.

**Command details:**

| | |
|---|---|
| Pattern Name | Device Status Retrieval |
| Communication Type | Bidirectional (Cloud to Device, Device to Cloud) |
| Applies To | RFD40 Series, RFD90 Series |

**Response fields:**

| Field | What it tells you |
|---|---|
| `powerSource` | How the scanner is powered — DC, Wall Charger, USB, or Cradle |
| `radioActivity` | Whether the RFID radio is currently active or idle |
| `radioConnection` | Whether the radio module is connected or disconnected |
| `hostname` | The scanner's network hostname |
| `systemTime` | Current device clock in ISO 8601 format |
| `temperature` | Internal temperature in °C — monitor for overheating |
| `ntp` | Clock sync status — offset (ms drift) and reach (sync success history) |
| `terminalConnection` | Paired phone/tablet — connection status and type (Bluetooth, USB, CIO) |
| `batteryStatus` | Battery capacity (mAh), charge %, health (Good/Average/Poor), charge state |

## Use Cases

### Fleet Health Monitoring

A warehouse management platform polls all readers at five-minute intervals using `get_status`. The system collects `batteryStatus.chargePercentage`, `temperature`, and `radioConnection` values from each device. When `chargePercentage` drops below 20 or `temperature` exceeds 45 degrees Celsius, the platform generates an alert and schedules the device for charging or cooldown.

### Pre-Operation Readiness Check

Before starting an inventory scan, a mobile application sends `get_status` to verify that `radioConnection` is `CONNECTED` and `batteryStatus.stateOfHealth` is not `POOR`. If either condition fails, the application prompts the operator to reconnect the sled or replace the battery before proceeding with `control_operation`.

### Battery Replacement Planning

A device management system tracks `batteryStatus.stateOfHealth` across the fleet over time. When a device transitions from `GOOD` to `AVERAGE`, the system adds the device to a scheduled replacement queue. Devices reporting `POOR` state of health are flagged for immediate battery swap.

### Time Synchronization Verification

An enterprise system queries `get_status` to check the `ntp.offset` and `ntp.reach` values. A high offset indicates clock drift that can cause timestamp mismatches in tag event data. The system triggers an NTP resynchronization when the offset exceeds the configured threshold.

### Terminal Connection Diagnostics

A field service technician troubleshoots connectivity issues between an RFD40 sled and a host mobile computer. The technician sends `get_status` and checks `terminalConnection.status` and `terminalConnection.type` to confirm whether the sled is connected over Bluetooth, USB, or CIO, and whether the connection is active.

**Download pdf:** 📄 [Download get_status as PDF](https://aa5123.github.io/zebra-rfd40-rfd90-iot-docs/command-pdfs/get_status.pdf)
