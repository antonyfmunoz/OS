---
type: codebase-class
file: core/connectors/crm.py
line: 29
generated: 2026-05-07
---

# CrmConnector

**File:** [[core-connectors-crm-py]] | **Line:** 29

Ingest CRM / lead pipeline metrics.

## Inherits From

- [[core-connectors-base-py-Connector]]

## Methods

- [[core-connectors-crm-py-CrmConnector-__init__]]`() → None` — 
- [[core-connectors-crm-py-CrmConnector-healthcheck]]`() → bool` — 
- [[core-connectors-crm-py-CrmConnector-fetch_signals]]`() → list[RealSignal]` — 
- [[core-connectors-crm-py-CrmConnector-normalize]]`(raw) → list[RealSignal]` — 
- [[core-connectors-crm-py-CrmConnector-from_webhook]]`(payload) → list[RealSignal]` — 
- [[core-connectors-crm-py-CrmConnector-_fetch_from_api]]`() → list[dict[str, Any]]` — 
