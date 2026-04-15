---
type: codebase-function
file: eos_ai/reality_engine.py
line: 140
generated: 2026-04-12
---

# RealityIntelligenceEngine.scan_market_signals

**File:** [[eos_ai-reality_engine-py]] | **Line:** 140
**Signature:** `scan_market_signals(venture_id) → list[dict]`

**Class:** [[eos_ai-reality_engine-py-RealityIntelligenceEngine]]

Scan market signals using live web data via ScraplingConnector,
augmented by venture context reasoning.

Returns list of dicts: {signal_type, content, confidence, source, tier}.
Skips ventures with insufficient data (all TODOs) to avoid fabrication.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-memory-py-ConversationMemory-search]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-_venture_scan_ready]]
- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-classify_signal]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-to_agent_context]]

## Called By

- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-process_signal_queue]]
