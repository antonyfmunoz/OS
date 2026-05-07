---
type: codebase-class
file: core/capabilities.py
line: 85
generated: 2026-05-07
---

# Capability

**File:** [[core-capabilities-py]] | **Line:** 85

A single execution resource available to the system.

Attributes:
    name:            Unique identifier (e.g. "claude_opus", "local_python").
    type:            Resource category: "llm", "local", "api", "human".
...

## Methods

- [[core-capabilities-py-Capability-effective_quality]]`() → float` — Quality adjusted by observed success rate.
- [[core-capabilities-py-Capability-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
