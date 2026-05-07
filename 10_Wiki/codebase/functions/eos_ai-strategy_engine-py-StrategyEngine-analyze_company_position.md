---
type: codebase-function
file: eos_ai/strategy_engine.py
line: 141
generated: 2026-05-07
---

# StrategyEngine.analyze_company_position

**File:** [[eos_ai-strategy_engine-py]] | **Line:** 141
**Signature:** `analyze_company_position(org_id) → dict`

**Class:** [[eos_ai-strategy_engine-py-StrategyEngine]]

Load all venture data + 30-day activity for the org.
Reason from first principles about where the company actually is.
Returns structured dict with 6 strategic dimensions.

## Calls

- [[eos_ai-strategy_engine-py-_parse_labeled_sections]]
- [[eos_ai-strategy_engine-py-_query_30d_stats]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-list_ventures]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-to_agent_context]]

## Called By

- [[eos_ai-strategy_engine-py-StrategyEngine-analyze_portfolio_strategy]]
