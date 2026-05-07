---
type: codebase-function
file: eos_ai/strategy_engine.py
line: 353
generated: 2026-05-07
---

# StrategyEngine.weekly_strategy_review

**File:** [[eos_ai-strategy_engine-py]] | **Line:** 353
**Signature:** `weekly_strategy_review() → str`

**Class:** [[eos_ai-strategy_engine-py-StrategyEngine]]

Full Sunday strategy review. Analyzes portfolio, compares signals,
writes to orchestrator/strategy/YYYY-WW.md.
Returns the full text for Telegram.

## Calls

- [[eos_ai-strategy_engine-py-StrategyEngine-analyze_portfolio_strategy]]
- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-get]]
