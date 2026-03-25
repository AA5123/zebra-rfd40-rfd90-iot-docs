Retrieves the **scanner's identity card** — model, serial number, SKU, and all firmware versions.

**Command details:**

| Property | Value |
|---|---|
| Pattern Name | Reader Identity and Firmware Retrieval |
| Communication Type | Bidirectional (Cloud to Device, Device to Cloud) |
| Applies To | RFD40 Series, RFD90 Series |

**Response fields:**

| Field | What it tells you |
|---|---|
| `firmwareVersion` | Main device firmware version |
| `model` | Scanner model — RFD40 or RFD90 |
| `serialNumber` | Unique device serial number |
| `sku` | Stock Keeping Unit — encodes model, features, and region (e.g. `RFD4031-G10B700-US`) |
| `detailedVersions.scannerFirmware` | Barcode scanner module firmware |
| `detailedVersions.radioFirmware` | RFID radio module firmware |
| `detailedVersions.iotcVersion` | IoT Connector software version |

**Typical use cases:**
- Inventory — collect model/serial/SKU across all scanners for asset tracking.
- Firmware management — check which scanners need firmware updates.

**MQTT topics for this command:**

- Command topic (Cloud to Device):
  `<tenantId>/CTRL/clients/cmnd/<deviceSerial>`
- Response topic (Device to Cloud):
  `<tenantId>/CTRL/clients/resp/<deviceSerial>`

**Example:**
- Command: `zebra/CTRL/clients/cmnd/RFD40-12345678`
- Response: `zebra/CTRL/clients/resp/RFD40-12345678`

Ensure these topic paths match your configured endpoint topics.
