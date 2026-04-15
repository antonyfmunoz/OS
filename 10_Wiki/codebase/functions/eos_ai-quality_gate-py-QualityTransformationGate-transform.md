---
type: codebase-function
file: eos_ai/quality_gate.py
line: 46
generated: 2026-04-12
---

# QualityTransformationGate.transform

**File:** [[eos_ai-quality_gate-py]] | **Line:** 46
**Signature:** `transform(output, input_text, classified_signal, bis_context) → TransformationResult`

**Class:** [[eos_ai-quality_gate-py-QualityTransformationGate]]

Transform output through the four values.
Each value applies its lens. Output becomes qualitatively new.
Called AFTER generation to score and log what landed.

## Calls

- [[eos_ai-quality_gate-py-QualityTransformationGate-_apply_execution]]
- [[eos_ai-quality_gate-py-QualityTransformationGate-_apply_intelligence]]
- [[eos_ai-quality_gate-py-QualityTransformationGate-_apply_personalization]]
- [[eos_ai-quality_gate-py-QualityTransformationGate-_apply_reality]]
