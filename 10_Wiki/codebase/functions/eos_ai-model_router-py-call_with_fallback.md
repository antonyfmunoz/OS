---
type: codebase-function
file: eos_ai/model_router.py
line: 703
generated: 2026-04-12
---

# call_with_fallback

**File:** [[eos_ai-model_router-py]] | **Line:** 703
**Signature:** `call_with_fallback(prompt, system, task_type, trigger_source, agent_type, force_opus) → RoutingResult`

Main routing entry point for all EOS agent calls.

Task-aware routing:
  fast_response/conversation → Haiku first (fast, cheap)
    escalates to Opus if quality_score < 0.65
...

## Calls

- [[eos_ai-cc_sdk-py-query_cc_sync]]
- [[eos_ai-model_router-py-ModelRouter-_check_availability]]
- [[eos_ai-model_router-py-ModelRouter-call]]
- [[eos_ai-model_router-py-_claude_cli_backend_enabled]]
- [[eos_ai-model_router-py-_is_ceo_agent]]
- [[eos_ai-model_router-py-_should_escalate]]
- [[eos_ai-model_router-py-_stamp_trace]]
- [[eos_ai-model_router-py-get_router]]

## Called By

- [[scripts-substrate_router_claude_primary_smoke_test-py-main]]
