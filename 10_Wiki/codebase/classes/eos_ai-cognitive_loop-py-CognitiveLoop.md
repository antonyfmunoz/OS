---
type: codebase-class
file: eos_ai/cognitive_loop.py
line: 233
generated: 2026-04-11
---

# CognitiveLoop

**File:** [[eos_ai-cognitive_loop-py]] | **Line:** 233

Full cognitive loop. Wraps AgentRuntime with:
  - PERCEIVE:  load venture context and recent memory
  - UNDERSTAND: prompt enhancement for vague inputs
  - PLAN:      authority check before any execution
  - EXECUTE:   agent runtime call
...

## Methods

- [[eos_ai-cognitive_loop-py-CognitiveLoop-__init__]]`(ctx)` — 
- [[eos_ai-cognitive_loop-py-CognitiveLoop-run]]`(input, session_id, cm, agent, task_type, venture_id, skill_name, workflow_id, channel, max_iterations) → CognitiveResult` — 
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_maybe_compact]]`() → None` — Check if the session message list is approaching the token limit.
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_enhance_prompt]]`(prompt) → str` — Expand prompts shorter than the trust-adjusted threshold into precise,
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_verify_output]]`(output, original_prompt, task_type) → dict` — Quick quality check. Returns {'passes': bool, 'issues': str|None}.
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_reflect]]`(prompt, output, iterations) → dict` — Extract insight from the run. Only meaningful when iterations > 0
- [[eos_ai-cognitive_loop-py-CognitiveLoop-process_in_order]]`(input, agent, task_type, venture_id) → 'CognitiveResult'` — Process a message and attach a monotonic turn number to the result.
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_infer_action_type]]`(task_type) → str` — Map TaskType to authority engine action type string.
- [[eos_ai-cognitive_loop-py-CognitiveLoop-_map_task_to_domain]]`(task_type, context) → str | None` — Map a TaskType + context to the most relevant knowledge domain key.
