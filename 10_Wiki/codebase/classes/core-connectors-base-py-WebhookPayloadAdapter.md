---
type: codebase-class
file: core/connectors/base.py
line: 171
generated: 2026-05-07
---

# WebhookPayloadAdapter

**File:** [[core-connectors-base-py]] | **Line:** 171

Parse a raw webhook payload dict into signal records.

Handles common patterns:
- Single event dict with "event"/"type" key
- Batch with "events" list

## Methods

- [[core-connectors-base-py-WebhookPayloadAdapter-parse]]`(payload) → list[dict[str, Any]]` — 
