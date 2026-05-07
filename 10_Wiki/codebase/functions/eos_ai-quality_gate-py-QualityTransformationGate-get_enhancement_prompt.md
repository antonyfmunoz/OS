---
type: codebase-function
file: eos_ai/quality_gate.py
line: 118
generated: 2026-05-07
---

# QualityTransformationGate.get_enhancement_prompt

**File:** [[eos_ai-quality_gate-py]] | **Line:** 118
**Signature:** `get_enhancement_prompt(result, classified) → str`

**Class:** [[eos_ai-quality_gate-py-QualityTransformationGate]]

Returns quality requirement prompt injected BEFORE generation.
Transforms through the prompt — not through regeneration.
Each value below threshold contributes its requirement.
Scores of 0.5 (pre-flight baseline) trigger all four.
