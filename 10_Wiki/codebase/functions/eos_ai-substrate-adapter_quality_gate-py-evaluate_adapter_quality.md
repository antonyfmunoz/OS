---
type: codebase-function
file: eos_ai/substrate/adapter_quality_gate.py
line: 119
generated: 2026-05-07
---

# evaluate_adapter_quality

**File:** [[eos_ai-substrate-adapter_quality_gate-py]] | **Line:** 119
**Signature:** `evaluate_adapter_quality(entry) → AdapterQualityReport`

Run all quality checks and produce a report.

## Calls

- [[eos_ai-substrate-adapter_quality_gate-py-_score_and_gaps]]
- [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_docs]]
- [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_no_secret_policy]]
- [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_required_contracts]]
- [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_safety_policy]]
- [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_tests]]
- [[eos_ai-substrate-adapter_quality_gate-py-adapter_has_tool_mastery]]

## Called By

- [[eos_ai-substrate-adapter_quality_gate-py-build_adapter_quality_report]]
- [[eos_ai-substrate-adapter_quality_gate-py-evaluate_adapter_maturity]]
