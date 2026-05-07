---
type: codebase-function
file: eos_ai/reality_engine.py
line: 281
generated: 2026-05-07
---

# RealityIntelligenceEngine.classify_signal

**File:** [[eos_ai-reality_engine-py]] | **Line:** 281
**Signature:** `classify_signal(signal) → str`

**Class:** [[eos_ai-reality_engine-py-RealityIntelligenceEngine]]

Classify signal into CRITICAL / HIGH / NORMAL / BACKGROUND.

Rules-based — fast, no LLM call. Tier logic:
  CRITICAL  — platform policy change, direct competitive threat, market disruption
  HIGH      — new competitor, ICP language shift, unexpected content performance
...

## Calls

- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]

## Called By

- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-scan_market_signals]]
