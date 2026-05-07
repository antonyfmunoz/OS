---
type: codebase-class
file: core/connectors/base.py
line: 100
generated: 2026-05-07
---

# JsonFileAdapter

**File:** [[core-connectors-base-py]] | **Line:** 100

Read signals from a JSON file.

Expected format: list of dicts with keys matching RealSignal fields,
or a dict with a "signals" key containing that list.

## Methods

- [[core-connectors-base-py-JsonFileAdapter-load]]`(path) → list[dict[str, Any]]` — 
