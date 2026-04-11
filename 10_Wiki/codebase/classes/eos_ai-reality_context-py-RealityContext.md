---
type: codebase-class
file: eos_ai/reality_context.py
line: 25
generated: 2026-04-11
---

# RealityContext

**File:** [[eos_ai-reality_context-py]] | **Line:** 25

Produces and caches a structured snapshot of current market reality
for injection into the CognitiveLoop PERCEIVE step.

## Methods

- [[eos_ai-reality_context-py-RealityContext-__init__]]`(ctx)` — 
- [[eos_ai-reality_context-py-RealityContext-_get_founder_pattern]]`() → dict` — Read interaction timestamps from Neon to derive the founder's actual
- [[eos_ai-reality_context-py-RealityContext-get_current_reality]]`() → dict` — Scan all ventures for current market signals and return a structured dict.
- [[eos_ai-reality_context-py-RealityContext-format_for_injection]]`(reality) → str` — Format a reality dict for injection into a CognitiveLoop prompt.
