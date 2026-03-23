Retrieves the **current Wi-Fi configuration** of the scanner — connected network, IP address, signal, and security settings.

**Command details:**

- Pattern Name: Wi-Fi Configuration Retrieval
- Communication Type: Bidirectional (Cloud to Device, Device to Cloud)
- MQTT Version: 3.1.1
- API Version: V1.1
- Document Version: 1.0.0
- Last Updated: 2026-03-12
- Applies To: RFD40 Series, RFD90 Series

**Response fields:**

| Field | What it tells you |
|---|---|
| `interfaceName` | Wi-Fi interface identifier (e.g. `wlan0`) |
| `status` | Whether the Wi-Fi interface is Enabled or Disabled |
| `hostname` | The scanner's network hostname |
| `macAddress` | Wi-Fi MAC address |
| `accessPoint.essid` | The SSID of the connected Wi-Fi network |
| `accessPoint.status` | Connection state — Connected or Disconnected |
| `accessPoint.securityType` | Security protocol — WPA2Personal, WPA2Enterprise, WPA3Personal, Open |
| `accessPoint.isPreferred` | Whether this is the preferred network |
| `accessPoint.autoConn` | Whether the scanner auto-connects to this network |
| `ipv4Configuration.ipAddress` | Current IP address assigned to the scanner |
| `ipv4Configuration.subnetMask` | Subnet mask |
| `ipv4Configuration.gateway` | Default gateway |
| `ipv4Configuration.enableDhcp` | Whether DHCP is enabled or using static IP |
| `ipv4Configuration.dnsServer` | DNS server address |

**Typical use cases:**
- Network troubleshooting — verify the scanner is connected to the correct SSID with a valid IP.
- Fleet monitoring — check Wi-Fi status across all scanners from a central dashboard.
- Security audit — confirm scanners are using WPA2/WPA3 Enterprise, not open networks.

**MQTT topics for this command:**

- Command topic (Cloud to Device):
  `<tenantId>/CTRL/clients/cmnd/<deviceSerial>`
- Response topic (Device to Cloud):
  `<tenantId>/CTRL/clients/resp/<deviceSerial>`

**Example:**
- Command: `zebra/CTRL/clients/cmnd/RFD40-12345678`
- Response: `zebra/CTRL/clients/resp/RFD40-12345678`

Ensure these topic paths match your configured endpoint topics.
