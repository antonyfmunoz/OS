---
type: codebase-file
path: eos_ai/primitives.py
module: eos_ai.primitives
lines: 932
size: 33761
tags: [critical]
generated: 2026-05-07
---

# eos_ai/primitives.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

Primitives — stage-aware business rules and contextual reasoning engine.

KnowledgePrimitive        — structured principle with validity conditions matrix.
                             Encodes when a principle applies and when it does NOT
                             based on stage, context, and prerequisites.
...

**Lines:** 932 | **Size:** 33,761 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-primitives-py-KnowledgePrimitive]] — 0 methods
- **class** [[eos_ai-primitives-py-PrimitiveRegistry]] — 3 methods
- **class** [[eos_ai-primitives-py-ContextualReasoningEngine]] — 3 methods

## Import Statements

```python
from dataclasses import dataclass
from dataclasses import field
from eos_ai.context import EOSContext
```
