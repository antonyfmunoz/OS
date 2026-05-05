---
type: codebase-file
path: eos_ai/reality_context.py
module: eos_ai.reality_context
lines: 154
size: 5608
generated: 2026-04-12
---

# eos_ai/reality_context.py

RealityContext — ambient present-state snapshot.

Wraps RealityIntelligenceEngine to produce a structured dict of current
market signals that can be cached as ambient state and injected into the
CognitiveLoop PERCEIVE step without requiring a fresh LLM call on every
...

**Lines:** 154 | **Size:** 5,608 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-reality_context-py-RealityContext]] — 4 methods

## Import Statements

```python
from eos_ai.context import EOSContext
```
