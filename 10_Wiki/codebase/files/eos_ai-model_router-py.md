---
type: codebase-file
path: eos_ai/model_router.py
module: eos_ai.model_router
lines: 1116
size: 40671
tags: [critical]
generated: 2026-04-12
---

# eos_ai/model_router.py

> **CRITICAL FILE** — Core infrastructure. Read before modifying.

ModelRouter — standalone multi-model router for EOS.

Provides task-type-aware model selection and universal call dispatch
across Anthropic, Perplexity, Groq, Gemini, and Ollama.

...

**Lines:** 1116 | **Size:** 40,671 bytes

## Depends On

- [[eos_ai-cc_sdk-py]]

## Used By

- [[scripts-substrate_router_claude_primary_smoke_test-py]]
- [[scripts-substrate_voice_router_responder_smoke_test-py]]

## Contains

- **class** [[eos_ai-model_router-py-RoutingResult]] — 0 methods
- **class** [[eos_ai-model_router-py-ModelProvider]] — 0 methods
- **class** [[eos_ai-model_router-py-TaskType]] — 0 methods
- **class** [[eos_ai-model_router-py-ModelConfig]] — 0 methods
- **class** [[eos_ai-model_router-py-ModelRouter]] — 10 methods
- **fn** [[eos_ai-model_router-py-_estimate_quality_score]]`(output, provider) → float`
- **fn** [[eos_ai-model_router-py-_should_escalate]]`(output, provider) → bool`
- **fn** [[eos_ai-model_router-py-_ollama_available]]`() → bool`
- **fn** [[eos_ai-model_router-py-get_router]]`(ctx) → ModelRouter`
- **fn** [[eos_ai-model_router-py-_claude_cli_backend_enabled]]`() → bool`
- **fn** [[eos_ai-model_router-py-_is_ceo_agent]]`(agent_type) → bool`
- **fn** [[eos_ai-model_router-py-call_with_fallback]]`(prompt, system, task_type, trigger_source, agent_type, force_opus) → RoutingResult`
- **fn** [[eos_ai-model_router-py-_stamp_trace]]`(provider, model, latency_ms, result) → None`
- **fn** [[eos_ai-model_router-py-adversarial_code_review]]`(code_or_plan, context) → str`

## Import Statements

```python
import os
import time
import logging
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from eos_ai.cc_sdk import query_cc_sync
from eos_ai.cc_sdk import CCResult
```
