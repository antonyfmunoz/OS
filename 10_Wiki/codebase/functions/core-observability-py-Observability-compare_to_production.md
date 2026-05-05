---
type: codebase-function
file: core/observability.py
line: 345
generated: 2026-04-12
---

# Observability.compare_to_production

**File:** [[core-observability-py]] | **Line:** 345
**Signature:** `compare_to_production() → dict[str, Any]`

**Class:** [[core-observability-py-Observability]]

Compare *this* observability view to production.

Useful when this instance is bound to a sandbox via ``env_root=``
— you get a side-by-side of key metrics without running two
reports manually.

## Calls

- [[core-observability-py-Observability-snapshot]]
