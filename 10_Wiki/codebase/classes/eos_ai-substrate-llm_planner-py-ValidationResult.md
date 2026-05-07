---
type: codebase-class
file: eos_ai/substrate/llm_planner.py
line: 404
generated: 2026-05-07
---

# ValidationResult

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 404

Outcome of validating a proposal against the registry.

schema_hash is explicitly tied to the registry state at validation
time.  Replay strict mode compares this to the current registry
schema_hash before accepting stored proposals.

## Decorators

- `@dataclass`
