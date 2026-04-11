---
type: codebase-function
file: eos_ai/strategy_engine.py
line: 225
generated: 2026-04-11
---

# StrategyEngine.analyze_portfolio_strategy

**File:** [[eos_ai-strategy_engine-py]] | **Line:** 225
**Signature:** `analyze_portfolio_strategy() → dict`

**Class:** [[eos_ai-strategy_engine-py-StrategyEngine]]

Run company position analysis for every company in the portfolio,
then reason across all of them to produce portfolio-level strategy.

## Calls

- [[eos_ai-agent_runtime-py-AgentRuntime-run]]
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]
- [[eos_ai-strategy_engine-py-StrategyEngine-analyze_company_position]]
- [[eos_ai-strategy_engine-py-_parse_labeled_sections]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-list_ventures]]

## Called By

- [[eos_ai-strategy_engine-py-StrategyEngine-weekly_strategy_review]]
