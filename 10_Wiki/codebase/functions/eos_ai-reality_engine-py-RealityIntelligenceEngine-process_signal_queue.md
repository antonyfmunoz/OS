---
type: codebase-function
file: eos_ai/reality_engine.py
line: 328
generated: 2026-04-12
---

# RealityIntelligenceEngine.process_signal_queue

**File:** [[eos_ai-reality_engine-py]] | **Line:** 328
**Signature:** `process_signal_queue() → dict`

**Class:** [[eos_ai-reality_engine-py-RealityIntelligenceEngine]]

Run scan_market_signals() for each venture, classify, and route by tier.

Routing:
  CRITICAL   → publish to event bus immediately + Telegram alert
  HIGH       → publish to event bus (included in next morning brief)
...

## Calls

- [[eos_ai-event_bus-py-EventBus-publish]]
- [[eos_ai-memory-py-AgentMemory-log_event]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-scan_market_signals]]
- [[eos_ai-reality_engine-py-_notify]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-list_ventures]]
