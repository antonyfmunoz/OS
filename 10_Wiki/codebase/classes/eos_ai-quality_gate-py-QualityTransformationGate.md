---
type: codebase-class
file: eos_ai/quality_gate.py
line: 40
generated: 2026-05-07
---

# QualityTransformationGate

**File:** [[eos_ai-quality_gate-py]] | **Line:** 40

*No docstring.*

## Methods

- [[eos_ai-quality_gate-py-QualityTransformationGate-__init__]]`(ctx)` — 
- [[eos_ai-quality_gate-py-QualityTransformationGate-transform]]`(output, input_text, classified_signal, bis_context) → TransformationResult` — Transform output through the four values.
- [[eos_ai-quality_gate-py-QualityTransformationGate-get_enhancement_prompt]]`(result, classified) → str` — Returns quality requirement prompt injected BEFORE generation.
- [[eos_ai-quality_gate-py-QualityTransformationGate-_apply_reality]]`(output, input_text, classified) → tuple[float, str, list[str]]` — Reality lens: is this grounded in what is actually true?
- [[eos_ai-quality_gate-py-QualityTransformationGate-_apply_intelligence]]`(output, input_text, classified) → tuple[float, str, list[str]]` — Intelligence lens: highest quality reasoning available?
- [[eos_ai-quality_gate-py-QualityTransformationGate-_apply_personalization]]`(output, input_text, classified, bis_context) → tuple[float, str, list[str]]` — Personalization lens: specific to this person's exact situation?
- [[eos_ai-quality_gate-py-QualityTransformationGate-_apply_execution]]`(output, input_text, classified) → tuple[float, str, list[str]]` — Execution lens: does this produce action?
