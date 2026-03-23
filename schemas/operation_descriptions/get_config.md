Retrieves the **complete device configuration** in a single response — equivalent to calling `get_version`, `get_status`, `get_current_region`, `get_wifi`, `get_eth`, `get_endpoint_config`, and `get_installed_certificate` all at once.

**Response sections:**

| Section | Contents |
|---|---|
| `readerVersion` | Model, serial number, SKU, firmware versions (main, scanner, radio, IoTC) |
| `deviceStatus` | Power source, radio state, temperature, battery health, NTP sync, terminal connection |
| `currentRegion` | Country, regulatory standard, frequency channels, power limits, frequency hopping, LBT |
| `wifiConfig` | Wi-Fi interface status, connected SSID, IP address, MAC, DHCP, security type |
| `ethConfig` | Ethernet interface status, link speed, IP configuration |
| `epConfig` | Active MQTT endpoint: type, broker URL, port, protocol, credentials, topics, security |
| `installedCerts` | List of installed certificates with type, validity dates, and algorithms |
| `eventConfiguration` | Which events/alerts are enabled (heartbeat, battery, temperature, firmware, network, etc.) |

**Typical use cases:**
- First-time setup — see how a blank scanner is configured before applying changes via `set_config`.
- Troubleshooting — get the full picture when something isn't working.
- Auditing — verify all settings across a fleet of scanners.
