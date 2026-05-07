---
type: codebase-function
file: core/connectors/base.py
line: 208
generated: 2026-05-07
---

# aggregate_signals

**File:** [[core-connectors-base-py]] | **Line:** 208
**Signature:** `aggregate_signals(signals) → dict[str, Any]`

Merge multiple RealSignals into one real_data dict.

If the same metric_name appears multiple times, the latest value wins.
All metadata is merged (latest wins on conflicts).
