---
type: codebase-class
file: core/capabilities.py
line: 37
generated: 2026-05-07
---

# PerformanceRecord

**File:** [[core-capabilities-py]] | **Line:** 37

Running statistics for a single capability.

Updated after every execution.  Persisted to disk so learning
survives restarts.

## Methods

- [[core-capabilities-py-PerformanceRecord-success_rate]]`() → float` — 
- [[core-capabilities-py-PerformanceRecord-avg_latency_s]]`() → float` — 
- [[core-capabilities-py-PerformanceRecord-cost_efficiency]]`() → float` — Cost per successful run.  Lower is better.
- [[core-capabilities-py-PerformanceRecord-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
