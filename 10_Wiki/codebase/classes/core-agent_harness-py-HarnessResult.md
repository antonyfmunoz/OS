---
type: codebase-class
file: core/agent_harness.py
line: 82
generated: 2026-04-12
---

# HarnessResult

**File:** [[core-agent_harness-py]] | **Line:** 82

Canonical return value from every harness call.

ok:            operation completed successfully
output:        string or dict result (content + metadata)
error:         short error string when ok=False
...

## Methods

- [[core-agent_harness-py-HarnessResult-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
