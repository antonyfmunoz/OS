---
type: codebase-function
file: core/connectors/email.py
line: 148
generated: 2026-05-07
---

# EmailConnector.from_webhook

**File:** [[core-connectors-email-py]] | **Line:** 148
**Signature:** `from_webhook(payload) → list[RealSignal]`

**Class:** [[core-connectors-email-py-EmailConnector]]

Parse a webhook payload into email signals.

## Calls

- [[core-connectors-base-py-Connector-normalize]]
- [[core-connectors-base-py-WebhookPayloadAdapter-parse]]
- [[core-connectors-email-py-EmailConnector-normalize]]
