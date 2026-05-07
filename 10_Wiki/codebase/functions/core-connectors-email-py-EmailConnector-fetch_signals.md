---
type: codebase-function
file: core/connectors/email.py
line: 54
generated: 2026-05-07
---

# EmailConnector.fetch_signals

**File:** [[core-connectors-email-py]] | **Line:** 54
**Signature:** `fetch_signals() → list[RealSignal]`

**Class:** [[core-connectors-email-py-EmailConnector]]

Pull email metrics from configured source.

## Calls

- [[core-connectors-base-py-Connector-_mark_synced]]
- [[core-connectors-base-py-Connector-normalize]]
- [[core-connectors-base-py-CsvFileAdapter-load]]
- [[core-connectors-base-py-JsonFileAdapter-load]]
- [[core-connectors-base-py-LogFileAdapter-load]]
- [[core-connectors-email-py-EmailConnector-_fetch_from_api]]
- [[core-connectors-email-py-EmailConnector-normalize]]
