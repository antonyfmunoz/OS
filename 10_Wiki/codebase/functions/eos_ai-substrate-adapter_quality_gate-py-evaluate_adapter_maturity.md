---
type: codebase-function
file: eos_ai/substrate/adapter_quality_gate.py
line: 170
generated: 2026-05-07
---

# evaluate_adapter_maturity

**File:** [[eos_ai-substrate-adapter_quality_gate-py]] | **Line:** 170
**Signature:** `evaluate_adapter_maturity(entry) → AdapterQualityReport`

Extended quality check including mastery maturity (Phase 96.6).

Goes beyond has_tool_mastery (boolean flag) to validate the mastery
pack's actual content — completeness requirements, failure modes,
anti-patterns, and validation checklist must all be populated.

## Calls

- [[eos_ai-substrate-adapter_quality_gate-py-_score_and_gaps]]
- [[eos_ai-substrate-adapter_quality_gate-py-adapter_tool_mastery_is_mature]]
- [[eos_ai-substrate-adapter_quality_gate-py-evaluate_adapter_quality]]
