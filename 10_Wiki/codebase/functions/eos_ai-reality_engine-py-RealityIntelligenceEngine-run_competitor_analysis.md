---
type: codebase-function
file: eos_ai/reality_engine.py
line: 422
generated: 2026-05-07
---

# RealityIntelligenceEngine.run_competitor_analysis

**File:** [[eos_ai-reality_engine-py]] | **Line:** 422
**Signature:** `run_competitor_analysis(venture_id, competitor) → dict`

**Class:** [[eos_ai-reality_engine-py-RealityIntelligenceEngine]]

Deep analysis of a specific competitor.
Reasons from known data in VentureKnowledgeBase.
Returns: positioning, offer_structure, target_icp, weaknesses,
         opportunities, threat_level.

## Calls

- [[eos_ai-strategy_engine-py-_parse_labeled_sections]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-to_agent_context]]

## Called By

- [[eos_ai-reality_engine-py-RealityIntelligenceEngine-generate_truth_report]]
