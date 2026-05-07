---
type: codebase-class
file: core/connectors/email.py
line: 28
generated: 2026-05-07
---

# EmailConnector

**File:** [[core-connectors-email-py]] | **Line:** 28

Ingest email/DM outreach metrics.

## Inherits From

- [[core-connectors-base-py-Connector]]

## Methods

- [[core-connectors-email-py-EmailConnector-__init__]]`() → None` — 
- [[core-connectors-email-py-EmailConnector-healthcheck]]`() → bool` — Check if data source is available.
- [[core-connectors-email-py-EmailConnector-fetch_signals]]`() → list[RealSignal]` — Pull email metrics from configured source.
- [[core-connectors-email-py-EmailConnector-normalize]]`(raw) → list[RealSignal]` — Convert raw email records to RealSignal list.
- [[core-connectors-email-py-EmailConnector-from_webhook]]`(payload) → list[RealSignal]` — Parse a webhook payload into email signals.
- [[core-connectors-email-py-EmailConnector-_fetch_from_api]]`() → list[dict[str, Any]]` — Fetch from live API. Stub for future integration.
