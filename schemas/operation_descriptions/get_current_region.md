Retrieves the **regulatory radio configuration** of the scanner — which country's rules it follows, what frequencies it can use, and power limits.

**Response fields:**

| Field | What it tells you |
|---|---|
| `country` | The country this scanner is configured for (e.g. United States, Germany) |
| `regulatoryStandard` | The radio regulation it follows (e.g. FCC for US, ETSI for Europe) |
| `frequencyHopping` | Whether the scanner automatically switches between frequency channels |
| `lbtEnabled` | Whether Listen Before Talk is enabled (required in some regions like Japan/EU) |
| `maxTxPowerSupported` | Maximum allowed transmit power in dBm |
| `minTxPowerSupported` | Minimum transmit power in dBm |
| `channelData` | List of all available frequency channels (in kHz) the scanner can use |

**Typical use cases:**
- Compliance auditing — verify scanners are configured for the correct country before deployment.
- RF planning — check available channels and power limits for site planning.
- Multi-region management — confirm scanners shipped to different countries have the right region settings.
