---
type: codebase-class
file: core/optimizer.py
line: 506
generated: 2026-04-12
---

# Optimizer

**File:** [[core-optimizer-py]] | **Line:** 506

Owns the analyze → propose pipeline.

## Methods

- [[core-optimizer-py-Optimizer-__init__]]`() → None` — 
- [[core-optimizer-py-Optimizer-gather_context]]`() → dict[str, Any]` — 
- [[core-optimizer-py-Optimizer-analyze]]`() → list[Proposal]` — 
- [[core-optimizer-py-Optimizer-persist]]`(proposals) → int` — 
- [[core-optimizer-py-Optimizer-run_once]]`() → dict[str, Any]` — 
- [[core-optimizer-py-Optimizer-count_pending]]`() → int` — Count proposals in the log with status=pending (scans entire log).
- [[core-optimizer-py-Optimizer-_update_state]]`(added) → None` — 
