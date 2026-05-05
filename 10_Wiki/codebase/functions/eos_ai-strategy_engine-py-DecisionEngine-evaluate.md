---
type: codebase-function
file: eos_ai/strategy_engine.py
line: 411
generated: 2026-04-12
---

# DecisionEngine.evaluate

**File:** [[eos_ai-strategy_engine-py]] | **Line:** 411
**Signature:** `evaluate(decision, context, venture_id) → dict`

**Class:** [[eos_ai-strategy_engine-py-DecisionEngine]]

6-step structured decision evaluation.
Each step is a focused CognitiveLoop call that builds on the last.
Returns all 6 steps + final recommendation.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-memory-py-AgentMemory-log_event]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
