---
type: codebase-function
file: core/execution_bridge.py
line: 446
generated: 2026-05-07
---

# build_pipeline

**File:** [[core-execution_bridge-py]] | **Line:** 446
**Signature:** `build_pipeline(structure) → Pipeline`

Convert a ComposedStructure into an executable Pipeline.

The primitive trace is injected into the pipeline context so every
step has access to the L0 lineage of the work it's doing.

## Called By

- [[core-execution_bridge-py-execute_composed]]
