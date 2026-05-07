---
type: codebase-class
file: core/connectors/base.py
line: 67
generated: 2026-05-07
---

# Connector

**File:** [[core-connectors-base-py]] | **Line:** 67

Base class for all real data connectors.

## Inherits From

- `ABC`

## Inherited By

- [[core-connectors-content-py-ContentConnector]]
- [[core-connectors-crm-py-CrmConnector]]
- [[core-connectors-email-py-EmailConnector]]

## Methods

- [[core-connectors-base-py-Connector-__init__]]`() → None` — 
- [[core-connectors-base-py-Connector-healthcheck]]`() → bool` — Return True if the data source is reachable.
- [[core-connectors-base-py-Connector-fetch_signals]]`() → list[RealSignal]` — Pull raw data from source and return normalized signals.
- [[core-connectors-base-py-Connector-normalize]]`(raw) → list[RealSignal]` — Convert a raw data record into normalized RealSignal(s).
- [[core-connectors-base-py-Connector-last_sync]]`() → float` — Unix timestamp of last successful fetch.
- [[core-connectors-base-py-Connector-_mark_synced]]`() → None` — 
