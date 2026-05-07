---
type: codebase-function
file: core/connectors/base.py
line: 84
generated: 2026-05-07
---

# Connector.normalize

**File:** [[core-connectors-base-py]] | **Line:** 84
**Signature:** `normalize(raw) → list[RealSignal]`

**Class:** [[core-connectors-base-py-Connector]]

Convert a raw data record into normalized RealSignal(s).

## Called By

- [[core-connectors-content-py-ContentConnector-fetch_signals]]
- [[core-connectors-content-py-ContentConnector-from_webhook]]
- [[core-connectors-crm-py-CrmConnector-fetch_signals]]
- [[core-connectors-crm-py-CrmConnector-from_webhook]]
- [[core-connectors-email-py-EmailConnector-fetch_signals]]
- [[core-connectors-email-py-EmailConnector-from_webhook]]

## Decorators

- `@abstractmethod`
