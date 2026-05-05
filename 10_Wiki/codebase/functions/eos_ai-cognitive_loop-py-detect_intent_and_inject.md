---
type: codebase-function
file: eos_ai/cognitive_loop.py
line: 1387
generated: 2026-04-12
---

# detect_intent_and_inject

**File:** [[eos_ai-cognitive_loop-py]] | **Line:** 1387
**Signature:** `detect_intent_and_inject(text, req, ctx) → dict`

Detect founder intent from natural language and inject
the right capability context into the system prompt.

This is what makes DEX conversational — no commands needed.

## Calls

- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]

## Called By

- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
