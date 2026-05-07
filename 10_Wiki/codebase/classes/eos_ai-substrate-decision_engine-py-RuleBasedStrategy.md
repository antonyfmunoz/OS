---
type: codebase-class
file: eos_ai/substrate/decision_engine.py
line: 146
generated: 2026-05-07
---

# RuleBasedStrategy

**File:** [[eos_ai-substrate-decision_engine-py]] | **Line:** 146

Decision strategy that evaluates rules in priority order.

First matching rule wins. Deterministic: same state + same rules
→ same output, always.

## Methods

- [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy-__init__]]`(rules) → None` — 
- [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy-name]]`() → str` — 
- [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy-add_rule]]`(rule) → None` — Add a rule and maintain priority sort.
- [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy-rules]]`() → list[Rule]` — Read-only access to the sorted rule list.
- [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy-evaluate]]`(state) → DecisionOutput | None` — Evaluate rules in priority order. First match wins.
