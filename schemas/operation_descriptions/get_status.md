Retrieves **real-time health and status** of the scanner — battery, temperature, radio, power, clock sync, and terminal connection.

**Download pdf:** 📄 [Download get_status as PDF](https://aa5123.github.io/zebra-rfd40-rfd90-iot-docs/command-pdfs/get_status.pdf)

**Command details:**

- Pattern Name: Reader Health and Status Retrieval
- Communication Type: Bidirectional (Cloud to Device, Device to Cloud)
- MQTT Version: 3.1.1
- API Version: V1.1
- Document Version: 1.0.0
- Last Updated: 2026-03-12
- Applies To: RFD40 Series, RFD90 Series

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

**Typical use cases:**
- Dashboard monitoring — show live scanner health on a management console.
- Battery management — track charge levels across a fleet before a shift starts.
- Troubleshooting — check if radio is connected, temperature is normal, clock is synced.

**MQTT topics for this command:**

- Command topic (Cloud to Device):
  `<tenantId>/CTRL/clients/cmnd/<deviceSerial>`
- Response topic (Device to Cloud):
  `<tenantId>/CTRL/clients/resp/<deviceSerial>`

**Example:**
- Command: `zebra/CTRL/clients/cmnd/RFD40-12345678`
- Response: `zebra/CTRL/clients/resp/RFD40-12345678`

Ensure these topic paths match your configured endpoint topics.
