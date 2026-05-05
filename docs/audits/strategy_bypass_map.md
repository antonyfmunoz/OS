# LLM Bypass Map — UMH Execution Spine

Generated: 2026-04-26
Phase: 1B — Route consolidation planning

## Architecture Summary

**Canonical path:**
```
caller → execute() → SpineExecutionBackend → model_router.call_with_fallback() → provider
```

**Shortcut (still canonical):**
```
caller → utility_llm_call(prompt, system, operation) → lightweight_execute() → execute() → backend
```

**Two `call_with_fallback` functions exist:**

| Function | Location | Returns | Notes |
|----------|----------|---------|-------|
| Module-level | `umh/runtime_engine/model_router.py:call_with_fallback()` | `RoutingResult` dataclass | EOS-specific: CLI tmux, CC SDK, CEO detection, trace stamping |
| Class-level | `umh/adapters/model_router.py:ModelRouter.call_with_fallback()` | `str` | Generic: simple priority-ordered fallback, no trace |

**`ModelRouter.call(model_config, prompt)` — even more direct.** No fallback, single provider call, returns `str`.

---

## Summary Table — All Bypass Call Sites

| # | File | Line | Function Called | TaskType | max_tokens | system | try/except | Classification |
|---|------|------|----------------|----------|------------|--------|------------|----------------|
| 1 | `umh/runtime_engine/email_gps.py` | 525 | class `call_with_fallback` | FAST_RESPONSE | 15 | no | yes | SAFE_REDIRECT |
| 2 | `umh/runtime_engine/email_gps.py` | 593 | class `call_with_fallback` | CONVERSATION | 200 | no | yes | SAFE_REDIRECT |
| 3 | `umh/runtime_engine/email_gps.py` | 629 | class `call_with_fallback` | FAST_RESPONSE | default (1000) | no | yes | SAFE_REDIRECT |
| 4 | `umh/runtime_engine/multi_strategy.py` | 349 | module `call_with_fallback` | passthrough | none | yes (strategy) | yes | NEEDS_ADAPTATION |
| 5 | `umh/stages/llm_generation.py` | 24 | module `call_with_fallback` | passthrough | none | yes (context) | yes | SANCTIONED_BYPASS |
| 6 | `umh/runtime_engine/voice_engine.py` | 567 | module `call_with_fallback` | fast_response | none | yes | yes | SAFE_REDIRECT |
| 7 | `umh/execution/runtime.py` | 247 | class `call_with_fallback` | mapped | passthrough | passthrough | yes | SANCTIONED_BYPASS |
| 8 | `umh/substrate/voice_eos_responder.py` | 244 | module `call_with_fallback` | fast_response | none | yes | yes | SAFE_REDIRECT |
| 9 | `umh/substrate/meeting_intelligence.py` | 502 | module `call_with_fallback` | summarize | none | yes | yes | SAFE_REDIRECT |
| 10 | `umh/substrate/meeting_intelligence.py` | 1280 | module `call_with_fallback` | summarize | none | yes | yes | SAFE_REDIRECT |
| 11 | `umh/runtime_engine/quality_gate.py` | 51 | `router.call()` | FAST_RESPONSE (routed) | default (1000) | no | yes | SAFE_REDIRECT |
| 12 | `umh/runtime_engine/daily_sync.py` | 223 | `router.call()` | FAST_RESPONSE (routed) | default (1000) | no | yes | SAFE_REDIRECT |
| 13 | `umh/runtime_engine/daily_sync.py` | 255 | `router.call()` | FAST_RESPONSE (routed) | default (1000) | no | yes | SAFE_REDIRECT |
| 14 | `umh/runtime_engine/daily_sync.py` | 292 | `router.call()` | FAST_RESPONSE (routed) | default (1000) | no | yes | SAFE_REDIRECT |
| 15 | `umh/runtime_engine/decision_log.py` | 129 | `router.call()` | ANALYSIS (routed) | 150 | no | yes | SAFE_REDIRECT |
| 16 | `umh/runtime_engine/agent_runtime.py` | 260 | module `call_with_fallback` | passthrough | none | yes (assembled) | no (outer) | SANCTIONED_BYPASS |
| 17 | `umh/adapters/umh_execution.py` | 77 | module `call_with_fallback` | passthrough | none | passthrough | yes | ALREADY_CANONICAL |
| 18 | `umh/interfaces/discord/dm_monitor.py` | 464 | direct `genai.Client` | N/A (vision) | N/A | N/A | yes | SANCTIONED_BYPASS |
| 19 | `umh/runtime_engine/embedding_engine.py` | 53 | direct `genai.Client` | N/A (embeddings) | N/A | N/A | yes | SANCTIONED_BYPASS |

---

## Detailed Analysis

### ALREADY_CANONICAL (1 site)

#### 17. `umh/adapters/umh_execution.py:77` — SpineExecutionBackend

This IS the canonical backend. `execute()` calls this. It calls module-level
`call_with_fallback()`. No redirect needed — this is the destination.

---

### SANCTIONED_BYPASS (5 sites)

These must remain direct and should NOT be redirected.

#### 5. `umh/stages/llm_generation.py:24` — LLMGenerationStage

**Why sanctioned:** This is Stage 4 of the ExecutionSpine pipeline. It runs
INSIDE the `ExecutionSpine.run()` call chain. Redirecting it through
`execute()` would create infinite recursion (execute → stages → llm_generation → execute).

The SpineExecutionBackend (`umh/adapters/umh_execution.py`) exists for callers
who use `execute()` OUTSIDE the spine. LLMGenerationStage is for callers who
go through the full 9-stage pipeline via `ExecutionSpine.run()`. Both
ultimately reach `model_router.call_with_fallback()`. Different paths, same
terminal. Correct by design.

#### 7. `umh/execution/runtime.py:247` — execute_with_fallback()

**Why sanctioned:** This is the UMH-layer generic execution runtime. It calls
class-level `ModelRouter.call_with_fallback()` (the simpler adapter version).
This is the OTHER legitimate terminal — it exists for the `execute()` pathway
when SpineExecutionBackend is not loaded. Both paths converge at the adapter
router. Not a bypass; it's a parallel canonical endpoint.

#### 16. `umh/runtime_engine/agent_runtime.py:260` — AgentRuntime.run()

**Why sanctioned:** AgentRuntime.run() is the EOS orchestration layer. It
assembles soul docs, skills, venture context, memory, and authority before
calling module-level `call_with_fallback()`. This is the main agent dispatch
for the 9-stage pipeline. Cannot be redirected through `utility_llm_call()`
because it needs the full `RoutingResult` dataclass (model used, tokens,
cost, latency) to build `AgentResult`. It also needs `raw_input` passthrough
for the Claude CLI tmux backend. Could eventually wrap in an execute() call
but would require `execute()` to support RoutingResult return or a new
execution class. Defer to Phase 2.

#### 18. `umh/interfaces/discord/dm_monitor.py:464` — Gemini Vision

**Why sanctioned:** Direct `genai.Client` for image/vision analysis
(extracting DM messages from Instagram screenshots). The model router does
not support multimodal/vision inputs. Already documented in-file as a known
bypass. Will resolve when model_router gains vision support (tracked
separately).

#### 19. `umh/runtime_engine/embedding_engine.py:53` — Gemini Embeddings

**Why sanctioned:** Embedding generation is a fundamentally different API
(embed_content, not generate_content). Not an LLM text completion call.
Router has no embedding abstraction. Correct to stay direct.

---

### NEEDS_ADAPTATION (1 site)

#### 4. `umh/runtime_engine/multi_strategy.py:349` — generate_candidates()

**What it does:** Generates N candidate responses with varied prompt
strategies. Each candidate calls module-level `call_with_fallback()` with a
modified system prompt and prompt directive per strategy.

**Why it needs adaptation:** It passes `system` (strategy-modified system
prompt), `agent_type`, and `task_type` through. `utility_llm_call()` currently
accepts only `prompt`, `system`, and `operation`. It lacks:
- `agent_type` passthrough (needed for CEO detection / force_opus)
- `task_type` passthrough (needed for correct routing)
- Returns `str` but this site needs `RoutingResult` to extract `.output`

**Risk:** MEDIUM. Multi-strategy is the quality multiplier for generate/analyze
tasks. Breaking it degrades response quality for all non-trivial prompts.

**Estimated daily calls:** 5-15 (only fires for GENERATE/ANALYZE tasks, each
producing 2-4 candidates).

**Path to redirect:** Either extend `utility_llm_call` with optional
`task_type` and `agent_type` kwargs, or create a `utility_llm_call_rich()`
variant that returns RoutingResult. Alternatively, since the `run_via_umh`
fallback paths already exist in the same file, consider routing all candidate
generation through a per-candidate `execute()` call with the strategy baked
into the system prompt.

---

### SAFE_REDIRECT (10 sites)

All of these can be replaced with `utility_llm_call(prompt, system, operation)`.
They return `str`, have no special routing needs, are inside try/except, and
use standard task types.

#### Priority Order (safest first)

**Batch 1 — Pure classification/extraction (lowest risk, highest frequency)**

| Priority | Site | File | Call | Daily est. | Risk |
|----------|------|------|------|-----------|------|
| 1 | #11 | `quality_gate.py:51` | `router.call()` | 5-10 | LOW — returns JSON, no special routing |
| 2 | #15 | `decision_log.py:129` | `router.call()` | 2-5 | LOW — returns JSON, max_tokens=150 (default ok) |
| 3 | #1 | `email_gps.py:525` | class `cwf` | 20-50 | LOW — email classification, max_tokens=15 (will use default, acceptable) |
| 4 | #3 | `email_gps.py:629` | class `cwf` | 10-30 | LOW — action item extraction |

**Batch 2 — Structured generation (medium frequency)**

| Priority | Site | File | Call | Daily est. | Risk |
|----------|------|------|------|-----------|------|
| 5 | #12 | `daily_sync.py:223` | `router.call()` | 1 | LOW — runs once at 6am |
| 6 | #13 | `daily_sync.py:255` | `router.call()` | 1 | LOW — runs once at 6am |
| 7 | #14 | `daily_sync.py:292` | `router.call()` | 1 | LOW — runs once at 6am |
| 8 | #2 | `email_gps.py:593` | class `cwf` | 5-15 | LOW — draft response |

**Batch 3 — Realtime voice/meeting (latency-sensitive)**

| Priority | Site | File | Call | Daily est. | Risk |
|----------|------|------|------|-----------|------|
| 9 | #6 | `voice_engine.py:567` | module `cwf` | 0-10 | MEDIUM — voice path, latency matters |
| 10 | #8 | `voice_eos_responder.py:244` | module `cwf` | 0-20 | MEDIUM — voice path, has role routing |
| 11 | #9 | `meeting_intelligence.py:502` | module `cwf` | 0-5 | MEDIUM — meeting summarization |
| 12 | #10 | `meeting_intelligence.py:1280` | module `cwf` | 0-5 | MEDIUM — intervention refinement |

---

## Impact Assessment

### Current state
- **17 total LLM call sites** outside the canonical execute() path
- **1 already canonical** (SpineExecutionBackend itself)
- **5 sanctioned bypasses** (cannot/should not redirect)
- **1 needs adaptation** (multi_strategy candidate generation)
- **10 safe to redirect** to `utility_llm_call()`

### Estimated daily call volume
- **SAFE_REDIRECT sites:** ~50-150 calls/day combined
- **NEEDS_ADAPTATION:** ~5-15 calls/day
- **SANCTIONED_BYPASS:** ~all remaining traffic (agent dispatch, pipeline stages)

### What redirecting gains
1. **Observability:** All utility calls flow through ExecutionObserver — cost/latency/error tracking unified
2. **Rate limiting:** Utility calls respect the same per-org rate limiter
3. **Backend swappability:** Changing the LLM backend in one place changes it everywhere
4. **Trace correlation:** Every call gets an execution_id and causal chain

### What redirecting risks
- **Latency:** `utility_llm_call()` adds ~1-2ms of overhead (execute() → backend → router). Irrelevant for non-voice paths. Voice paths (sites #6, #8, #9, #10) should be tested.
- **max_tokens loss:** `utility_llm_call()` does not pass `max_tokens`. Sites #1 (15 tokens) and #15 (150 tokens) use non-default values. Impact is minor — the backend will use its own defaults (fast_response capped at 500 by `HAIKU_TOKEN_CAPS`). But email classification returning 500 tokens instead of 15 wastes tokens. Consider adding `max_tokens` to `utility_llm_call()` or accepting the cost.

---

## Redirect Implementation Notes

### For Batch 1-2 (sites using class-level `router.call()` / `router.call_with_fallback()`)

These import from `umh.runtime_engine.model_router` which re-exports from
`umh.adapters.model_router`. They call the class-level API which returns
plain `str`. Replace with:

```python
from umh.gateway.entry import utility_llm_call
result = utility_llm_call(prompt, operation="<descriptive_name>")
```

### For Batch 3 (sites using module-level `call_with_fallback()`)

These already call the EOS-enriched module-level function. They get CLI tmux,
CC SDK escalation, CEO detection, and trace stamping. Redirecting through
`utility_llm_call()` would lose some of those features (trigger_source,
agent_type passthrough). Consider whether those features matter for each
specific site:
- `voice_engine.py` passes `trigger_source="voice_engine"` — useful for tracing but not functional
- `voice_eos_responder.py` passes `agent_type=role` — triggers CEO detection if role matches. Functional. May need adaptation.
- `meeting_intelligence.py` passes `trigger_source="meeting_intelligence"` — tracing only

### For class-level `get_router()` calls passing `ctx`

`email_gps.py` calls `get_router(self.ctx)` but `get_router()` accepts no
arguments. The `ctx` argument is silently ignored. This is harmless but
misleading — should be cleaned up during redirect.

---

## What MUST Stay as Bypass — Summary

| Site | File | Reason |
|------|------|--------|
| LLMGenerationStage | `stages/llm_generation.py` | Inside spine pipeline — redirect = infinite recursion |
| execute_with_fallback | `execution/runtime.py` | IS the generic execution terminal |
| AgentRuntime.run() | `agent_runtime.py` | Main agent dispatch, needs RoutingResult, raw_input |
| Gemini Vision | `dm_monitor.py` | Vision/multimodal — router lacks support |
| Gemini Embeddings | `embedding_engine.py` | Embedding API — fundamentally different operation |
| SpineExecutionBackend | `umh_execution.py` | IS the canonical backend (destination, not bypass) |

---

## Next Steps

1. **Phase 1B-1:** Redirect Batch 1 (sites #11, #15, #1, #3) — pure classification, no risk
2. **Phase 1B-2:** Redirect Batch 2 (sites #12, #13, #14, #2) — daily sync and email draft
3. **Phase 1B-3:** Add `max_tokens` kwarg to `utility_llm_call()` for token-sensitive sites
4. **Phase 1B-4:** Redirect Batch 3 with latency testing (sites #6, #8, #9, #10)
5. **Phase 2:** Adapt multi_strategy (#4) — either extend utility_llm_call or create execute()-based candidate generation
6. **Phase 3:** Consider wrapping AgentRuntime.run() (#16) in execute() with RoutingResult support
