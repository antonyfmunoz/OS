---
type: codebase-function
file: eos_ai/proactive_engine.py
line: 89
generated: 2026-04-12
---

# ProactiveIntelligenceEngine.scan

**File:** [[eos_ai-proactive_engine-py]] | **Line:** 89
**Signature:** `scan() → list[ProactiveSignal]`

**Class:** [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine]]

Full proactive scan. Returns all signals worth surfacing.
Each scanner is isolated — one failure never blocks others.

## Calls

- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-_scan_inaction]]
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-_scan_primitive_violations]]
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-_scan_reality_divergence]]
- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-_scan_stage_transition]]

## Called By

- [[eos_ai-proactive_engine-py-ProactiveIntelligenceEngine-scan_and_deliver]]
