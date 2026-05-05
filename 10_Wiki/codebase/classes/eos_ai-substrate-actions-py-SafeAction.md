---
type: codebase-class
file: eos_ai/substrate/actions.py
line: 68
generated: 2026-04-12
---

# SafeAction

**File:** [[eos_ai-substrate-actions-py]] | **Line:** 68

A single intent dispatched from EOS to a node.

`payload` is typed loosely as dict for now but each `kind` has an
expected shape — documented inline. Station Daemon implementations
validate strictly; this dataclass stays permissive so tests and
...

## Methods

- [[eos_ai-substrate-actions-py-SafeAction-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
