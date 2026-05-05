# Execution Backend Design: Replacing NullExecutionBackend

Date: 2026-04-26
Status: Draft
Author: Developer Agent

---

## 1. Current Problem

### What execute() does today

`umh/execution/engine.py:execute()` is the canonical single entry point for all
execution in the UMH layer. It:

1. Calls `get_execution_observer().on_request(request)` (no-op today)
2. Calls `get_execution_backend().execute(request)` — **this is where it breaks**
3. Calls `get_execution_observer().on_result(result)` (no-op today)
4. Returns the `ExecutionResult`

### What NullExecutionBackend returns

`umh/execution/interfaces.py:38-53` — `NullExecutionBackend` always returns:
```
ExecutionResult(status=REJECTED, error="No execution backend configured")
```
Its `can_handle()` always returns `False`.

### Why the file `umh/adapters/umh_execution.py` does not exist

The `_default_backend()` function in `interfaces.py:88-96` tries to discover a
platform adapter via:
```python
discover_platform_adapter("umh.adapters.umh_execution", "get_execution_backend_adapter")
```
**This file does not exist.** The discovery returns `None`, so the system falls
back to `NullExecutionBackend()` every time.

### Why production works despite this

Production works because the call graph **never reaches `execute()` for real LLM
work**. The actual production path is:

```
Discord bot → EOSGateway.handle()
  → _route_agent_task()
    → SessionRuntime.run()
      → run_with_strategies()
        → FOR GENERATE/ANALYZE: call_with_fallback() directly (bypasses execute())
        → FOR ALL OTHERS: run_via_umh() → execute() → NullBackend → REJECTED
```

For strategy-eligible task types (GENERATE, ANALYZE), `multi_strategy.py`
calls `model_router.call_with_fallback()` directly at line 349 — this is
the real LLM call that produces responses. The winner is then committed
via `commit_pipeline.commit_winner()`.

For non-eligible task types, `run_via_umh()` is called, which builds an
`ExecutionRequest` and routes through `execute()`. Since the backend is Null,
this returns REJECTED. The `run_via_umh()` function then returns a SpineResult
containing the error message `"No execution backend configured"`.

### What breaks (non-strategy-eligible task types)

Any task type NOT in `{"generate", "analyze"}` that flows through `run_via_umh()`
gets REJECTED. This includes:

- **SUMMARIZE** — summarization requests
- **SCORE** — scoring/rating requests
- **CLASSIFY** — classification requests
- **FAST_RESPONSE** — quick utility calls
- **JOURNAL** — journaling/logging

These task types either:
1. Return the error string silently (user sees "No execution backend configured"), or
2. Are rescued by upstream code that detects the failure and falls through to
   `ExecutionSpine().run()` or direct `call_with_fallback()` calls elsewhere

### The translate_and_run() dead code path

`umh/gateway/entry.py:98` defines `translate_and_run()` — described as "the ONLY
entry point for external signals." It calls `umh.run.run()` which is a 9-stage
pipeline that uses `dispatch_prompt()` at stage 8.

`dispatch_prompt()` routes through the adapter registry (`get_adapter("llm")`),
not through `execute()`. So it would work if called. But **zero production
interfaces call `translate_and_run()`**. No Discord bot handler, no Telegram
handler, no webhook handler wires to it. `translate_and_run` is re-exported
from `umh/gateway/__init__.py` but has no callers.

The only callers of `utility_llm_call()` (which routes through
`lightweight_execute()` → `execute()` → NullBackend → REJECTED) are:
- `gateway.py` email instruction handler (line 424)
- `gateway.py` web search (line 868)
- `gateway.py` classify_intent (line 1762)
- `discord/bot.py`, `dm_monitor.py`, `intent_handler.py`, `cc_command_handler.py`
- `webhooks/calendly.py`
- `workstation/business.py`

All of these get empty strings back because `utility_llm_call()` checks for
`status == "succeeded"` and the NullBackend returns REJECTED.

---

## 2. Current Call Graph

### Production path (working — strategy-eligible)

```
Discord/Telegram Interface
  │
  ▼
EOSGateway.handle()                    [umh/runtime_engine/gateway.py]
  │
  ├─ _handle_automation()              short-circuit, no LLM
  ├─ _handle_email_instruction()       calls utility_llm_call() → FAILS SILENTLY
  ├─ _requires_approval()              pattern match, no LLM
  │
  ▼
_route_agent_task()
  │
  ├─ InputIntelligence.process()       prompt enrichment
  ├─ IntentRouter.route()              agent routing
  ├─ _inject_agent_context()           context injection
  │
  ▼
SessionRuntime.run()                   [umh/runtime_engine/session_runtime.py]
  │
  ├─ Goal blending / exploration
  │
  ▼
run_with_strategies()                  [umh/runtime_engine/multi_strategy.py]
  │
  ├── is_strategy_eligible(task_type)?
  │     │
  │     ├─ YES (GENERATE, ANALYZE):
  │     │    │
  │     │    ▼
  │     │  generate_candidates()
  │     │    │
  │     │    ▼
  │     │  call_with_fallback()        ← DIRECT LLM CALL (bypasses execute())
  │     │    │                           [umh/runtime_engine/model_router.py]
  │     │    ▼
  │     │  evaluate_outcome()          deterministic scoring
  │     │    │
  │     │    ▼
  │     │  select_best() → commit_winner() → SpineResult
  │     │
  │     └─ NO (SCORE, CLASSIFY, SUMMARIZE, FAST_RESPONSE, JOURNAL, etc.):
  │          │
  │          ▼
  │        run_via_umh()               [umh/runtime_engine/execution_spine.py]
  │          │
  │          ▼
  │        execute()                   [umh/execution/engine.py]
  │          │
  │          ▼
  │        NullExecutionBackend        [umh/execution/interfaces.py]
  │          │
  │          ▼
  │        ExecutionResult(REJECTED)
  │          │
  │          ▼
  │        SpineResult("No execution backend configured")
  │
  ▼
SpineResult → EOSGateway → Discord/Telegram
```

### Dead path (never called)

```
[No interface]
  │
  ▼
translate_and_run()                    [umh/gateway/entry.py]
  │
  ▼
umh.run.run()                          [umh/run.py]
  │
  ├─ classify_input()
  ├─ compile_intent()
  ├─ WorldModel.get_context_for_prompt()
  ├─ GoalRegistry
  ├─ route_to_capability()
  ├─ check_governance()
  │
  ▼
dispatch_prompt()                      [umh/execution/engine.py]
  │
  ▼
get_adapter("llm").generate()          ← Uses adapter registry, NOT execute()
  │
  ▼
RunResult → UMHOutput → [nobody]
```

### Utility path (broken)

```
utility_llm_call()                     [umh/gateway/entry.py]
  │
  ▼
lightweight_execute()                  [umh/execution/engine.py]
  │
  ▼
execute()
  │
  ▼
NullExecutionBackend → REJECTED → returns ""
```

### Parallel working path (ExecutionSpine pipeline — used within run_via_umh fallbacks)

```
ExecutionSpine().run()                 [umh/runtime_engine/execution_spine.py]
  │
  ▼
_build_default_pipeline()              9 stages
  │
  ▼
ExecutionPipeline.run()                [umh/execution/pipeline.py]
  │
  ├─ AuthorityCheckStage
  ├─ PromptEnhancementStage
  ├─ ContextAssemblyStage
  ├─ LLMGenerationStage ──────────────► call_with_fallback()  ← WORKS
  ├─ QualityVerificationStage
  ├─ StageFilterStage
  ├─ OutcomeEvaluationStage
  ├─ CommitStage
  └─ ResponseFooterStage
  │
  ▼
SpineResult (with full pipeline metadata)
```

---

## 3. Why NullExecutionBackend Causes Bypasses

### Chain of causation

1. **No `umh/adapters/umh_execution.py` exists** — the adapter discovery in
   `_default_backend()` returns `None`.

2. **`NullExecutionBackend` is instantiated** — becomes the singleton backend.

3. **`execute()` always returns REJECTED** — for any `ExecutionRequest` routed
   through it.

4. **`run_via_umh()` returns error strings** — it checks for
   `result.status == SUCCEEDED`, gets REJECTED, and returns
   `SpineResult("No execution backend configured")`.

5. **`utility_llm_call()` returns empty strings** — it checks for
   `result.status.value == "succeeded"`, gets REJECTED, returns `""`.

6. **Developers discovered the bypass was necessary** — to make production work,
   `multi_strategy.py` was written to call `call_with_fallback()` directly for
   strategy-eligible types. The `LLMGenerationStage` in the spine pipeline also
   calls `call_with_fallback()` directly.

7. **The bypass became the canonical path** — new features built on top of the
   working bypass rather than fixing the root cause.

### Files that bypass execute() because of NullBackend

| File | Bypass Method | Why |
|------|--------------|-----|
| `umh/runtime_engine/multi_strategy.py` | `call_with_fallback()` directly | Candidate generation for GENERATE/ANALYZE |
| `umh/stages/llm_generation.py` | `call_with_fallback()` directly | LLM stage in the 9-stage spine pipeline |
| `umh/runtime_engine/agent_runtime.py` | `call_with_fallback()` via `_router_call` | Agent runtime dispatch |
| `umh/runtime_engine/email_gps.py` | `get_router()` directly | Email classification |
| `umh/runtime_engine/ceo_agent.py` | `get_router()` directly | CEO agent primitives |
| `umh/runtime_engine/quality_gate.py` | `get_router()` directly | Quality scoring |
| `umh/runtime_engine/daily_sync.py` | `get_router()` directly | Daily sync summaries |
| `umh/runtime_engine/decision_log.py` | `get_router()` directly | Decision detection |
| `umh/runtime_engine/world_pulse.py` | `get_router()` directly | World pulse generation |
| `umh/substrate/voice_eos_responder.py` | `call_with_fallback()` directly | Voice response |
| `umh/substrate/meeting_intelligence.py` | `call_with_fallback()` directly | Meeting analysis |

---

## 4. Minimal RealExecutionBackend Design

### Goal

Create a backend that satisfies the `ExecutionBackend` protocol and delegates
LLM calls to the existing working infrastructure. This is NOT a rewrite — it is
a thin adapter that makes `execute()` work by routing to code that already works.

### Interface specification

The `ExecutionBackend` protocol requires exactly two methods:

```python
class ExecutionBackend(Protocol):
    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...
    def can_handle(self, operation: str) -> bool: ...
```

### Implementation: `umh/adapters/umh_execution.py`

```python
class SpineExecutionBackend:
    """Routes ExecutionRequests through the 9-stage ExecutionSpine pipeline.

    This is the real backend that replaces NullExecutionBackend.
    For LLM_CALL class requests, delegates to ExecutionSpine.run().
    """

    def can_handle(self, operation: str) -> bool:
        return operation in {
            "llm_generate",
            "classify_intent",
            "summarize",
            "extract_entities",
            "short_response",
            "validation",
            "utility",
        }

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Route through ExecutionSpine for LLM calls."""
        if request.execution_class == ExecutionClass.LLM_CALL:
            return self._execute_llm(request)
        return self._reject(request, "Unsupported execution class")

    def _execute_llm(self, request: ExecutionRequest) -> ExecutionResult:
        """Delegate to model_router.call_with_fallback()."""
        from umh.runtime_engine.model_router import call_with_fallback
        from umh.core.clock import iso_now, now_ms

        start = now_ms()
        try:
            routing_result = call_with_fallback(
                prompt=request.inputs.get("prompt", ""),
                system=request.inputs.get("system_prompt") or None,
                agent_type=request.context.agent_type or "executive_assistant",
                task_type=request.inputs.get("task_type"),
            )

            if not routing_result or not routing_result.output:
                return self._reject(request, "Empty response from model chain")

            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.SUCCEEDED,
                outputs={
                    "text": routing_result.output,
                    "iterations": 1,
                    "was_enhanced": False,
                },
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=now_ms() - start,
                model_used=f"{routing_result.provider}/{routing_result.model}",
                tokens_used={
                    "input": routing_result.input_tokens,
                    "output": routing_result.output_tokens,
                    "total": routing_result.tokens_used,
                },
                cost_usd=routing_result.cost_usd,
            )
        except Exception as e:
            return ExecutionResult(
                execution_id=request.execution_id,
                correlation_id=request.correlation_id,
                causal_event_id=request.causal_event_id,
                operation=request.operation,
                status=ExecutionStatus.FAILED,
                outputs={},
                error=str(e),
                started_at=iso_now(),
                completed_at=iso_now(),
                latency_ms=now_ms() - start,
            )

    def _reject(self, request, reason):
        return ExecutionResult(
            execution_id=request.execution_id,
            correlation_id=request.correlation_id,
            causal_event_id=request.causal_event_id,
            operation=request.operation,
            status=ExecutionStatus.REJECTED,
            outputs={},
            error=reason,
        )
```

### What it delegates to

The backend delegates directly to `model_router.call_with_fallback()` — the same
function that `multi_strategy.py` and `LLMGenerationStage` already use
successfully. This is the lowest-risk option because it uses proven, production-
tested code.

It does NOT delegate to `ExecutionPipeline` or `ExecutionSpine.run()` because:
- `ExecutionSpine.run()` builds a full 9-stage pipeline including LLM call,
  quality check, footer, etc. — this would create circular delegation when
  `run_via_umh()` calls `execute()` which calls `ExecutionSpine.run()`.
- The backend's job is to execute the LLM call, not run the full pipeline.

### Registration via adapter discovery

The file must be placed at `umh/adapters/umh_execution.py` and expose a
factory function:

```python
def get_execution_backend_adapter():
    return SpineExecutionBackend()

def get_execution_observer_adapter():
    return None  # or a real observer later
```

This matches what `interfaces.py:89-92` already tries to discover:
```python
discover_platform_adapter("umh.adapters.umh_execution", "get_execution_backend_adapter")
```

### Sync vs async

The `ExecutionBackend` protocol is synchronous (`def execute(...)` not
`async def`). The `model_router.call_with_fallback()` function is also
synchronous. No async change needed.

### Configuration / initialization

Zero configuration required. The backend is stateless — it discovers
`call_with_fallback` at call time via lazy import. The adapter discovery
in `_default_backend()` handles registration automatically.

---

## 5. Migration Steps (ordered, smallest-first)

### Step 1: Create the backend (LOW risk)

Create `umh/adapters/umh_execution.py` with `SpineExecutionBackend` and the
two factory functions. This file currently does not exist — nothing breaks
by creating it.

Verification:
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.adapters.umh_execution import get_execution_backend_adapter
backend = get_execution_backend_adapter()
print(f'Backend: {type(backend).__name__}')
print(f'Can handle llm_generate: {backend.can_handle(\"llm_generate\")}')
"
```

### Step 2: Verify automatic registration (LOW risk)

The existing `_default_backend()` in `interfaces.py` already tries to
discover `umh.adapters.umh_execution.get_execution_backend_adapter`.
Creating the file automatically replaces NullBackend.

Verification:
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.execution.interfaces import reset_execution_backend, get_execution_backend
reset_execution_backend()
backend = get_execution_backend()
print(f'Backend type: {type(backend).__name__}')
assert type(backend).__name__ != 'NullExecutionBackend', 'Still using NullBackend!'
print('Registration OK')
"
```

### Step 3: Verify run_via_umh() works (MEDIUM risk)

Test that `run_via_umh()` now returns successful results instead of REJECTED.

Verification:
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.execution.interfaces import reset_execution_backend
reset_execution_backend()
from umh.runtime_engine.execution_spine import run_via_umh
result = run_via_umh(
    message='What is 2+2?',
    unified_context=None,
    agent_type='executive_assistant',
    task_type='fast_response',
)
print(f'Result: {result[:100]}')
print(f'Model: {result.model_used}')
assert 'No execution backend configured' not in str(result)
print('run_via_umh OK')
"
```

### Step 4: Verify utility_llm_call() works (MEDIUM risk)

Test that `utility_llm_call()` now returns non-empty strings.

Verification:
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.execution.interfaces import reset_execution_backend
reset_execution_backend()
from umh.gateway.entry import utility_llm_call
result = utility_llm_call('Classify: hello', operation='test')
print(f'Result: {result[:100]}')
assert result, 'utility_llm_call returned empty!'
print('utility_llm_call OK')
"
```

### Step 5: Wire translate_and_run() to an interface (MEDIUM risk)

This is a separate task from the backend fix. Options:

1. **Minimal:** Add a Discord command or webhook endpoint that calls
   `translate_and_run()`.
2. **Full:** Refactor `_route_agent_task()` in `gateway.py` to call
   `translate_and_run()` instead of building its own routing.

Recommendation: defer this step. The priority is fixing the backend.
`translate_and_run()` uses `umh.run.run()` which is a separate 9-stage
pipeline from the production `ExecutionSpine` — merging them is a larger
architectural decision.

### Step 6: Redirect bypasses one at a time (LOW risk per file)

After Steps 1-4 are verified, identify which direct `call_with_fallback()`
callers could be replaced with `execute()` or `lightweight_execute()`.

Priority order (by risk/value):
1. `utility_llm_call()` callers — these already route through
   `lightweight_execute()` → `execute()`, so they will just start working
   with no code changes.
2. `email_gps.py`, `decision_log.py`, `daily_sync.py`, `quality_gate.py`,
   `world_pulse.py`, `ceo_agent.py` — these use `get_router()` directly.
   Convert to `utility_llm_call()` or `lightweight_execute()` for
   observability.
3. `multi_strategy.py` — this intentionally bypasses the pipeline for
   candidate generation (no side effects). Keep the bypass.
4. `LLMGenerationStage` — this IS the pipeline stage. Keep the direct call.

---

## 6. Tests Required

### New tests

| Test | What it validates |
|------|------------------|
| `test_spine_execution_backend_succeeds` | `SpineExecutionBackend.execute()` returns SUCCEEDED for LLM_CALL requests |
| `test_spine_execution_backend_rejects_non_llm` | Returns REJECTED for non-LLM execution classes |
| `test_spine_execution_backend_handles_error` | Returns FAILED (not raises) on LLM errors |
| `test_spine_execution_backend_can_handle` | `can_handle()` returns True for known operations |
| `test_default_backend_discovers_real` | `_default_backend()` returns `SpineExecutionBackend`, not Null |
| `test_run_via_umh_succeeds` | `run_via_umh()` returns non-error SpineResult |
| `test_utility_llm_call_returns_text` | `utility_llm_call()` returns non-empty string |
| `test_lightweight_execute_succeeds` | `lightweight_execute()` returns SUCCEEDED result |

### Existing tests that need updating

| Test file | What changes |
|-----------|-------------|
| Any test that asserts NullExecutionBackend is the default | Now expects SpineExecutionBackend |
| Any test that mocks `get_execution_backend` | May need to account for real backend |
| Tests that expect `run_via_umh()` to return error strings | Now expect real responses |

### Acceptance criteria

1. `python3 -c "from umh.adapters.umh_execution import SpineExecutionBackend"` succeeds
2. `get_execution_backend()` returns `SpineExecutionBackend`, not `NullExecutionBackend`
3. `run_via_umh()` returns a SpineResult with actual LLM output for all task types
4. `utility_llm_call()` returns non-empty strings
5. `lightweight_execute()` returns `ExecutionResult(status=SUCCEEDED)`
6. Existing production path (multi_strategy for GENERATE/ANALYZE) is unaffected
7. Gateway email instruction handler, web search, and classify_intent start working

---

## 7. Files Likely to Change

| File | What Changes | Risk Level |
|------|-------------|------------|
| `umh/adapters/umh_execution.py` | **NEW FILE** — SpineExecutionBackend + factory | LOW |
| `umh/execution/interfaces.py` | No changes needed (discovery already wired) | NONE |
| `umh/execution/engine.py` | No changes needed | NONE |
| `umh/runtime_engine/execution_spine.py` | No changes needed (run_via_umh already calls execute()) | NONE |
| `umh/gateway/entry.py` | No changes needed (utility_llm_call already calls lightweight_execute()) | NONE |
| `tests/test_execution_backend.py` | **NEW FILE** — backend tests | LOW |
| `umh/runtime_engine/email_gps.py` | Future: convert get_router() → utility_llm_call() | LOW |
| `umh/runtime_engine/decision_log.py` | Future: convert get_router() → utility_llm_call() | LOW |
| `umh/runtime_engine/daily_sync.py` | Future: convert get_router() → utility_llm_call() | LOW |
| `umh/runtime_engine/quality_gate.py` | Future: convert get_router() → utility_llm_call() | LOW |
| `umh/runtime_engine/ceo_agent.py` | Future: convert get_router() → utility_llm_call() | LOW |
| `umh/runtime_engine/world_pulse.py` | Future: convert get_router() → utility_llm_call() | LOW |

---

## 8. Risks

### What could break

1. **Double LLM calls for strategy-eligible types.** If the backend runs
   through the spine pipeline AND multi_strategy also calls call_with_fallback,
   we could get duplicate calls.
   - **Mitigation:** The backend routes to `call_with_fallback()` directly, not
     to `ExecutionSpine.run()`. For strategy-eligible types, `run_with_strategies()`
     calls `call_with_fallback()` directly and never reaches `run_via_umh()`.
     No double-call risk.

2. **Circular import.** The backend lives in `umh/adapters/` and imports from
   `umh/runtime_engine/model_router.py`. The engine lives in `umh/execution/`
   and calls the backend.
   - **Mitigation:** All imports are lazy (inside methods, not at module level).
     The existing `LLMGenerationStage` already does the same lazy import pattern
     without issues.

3. **Cost increase from utility calls that previously returned empty.** Email
   instruction extraction, web search, and classify_intent currently silently
   fail (return empty). Fixing the backend means they will now make real LLM
   calls, consuming tokens.
   - **Mitigation:** These calls are designed to be made — they just never
     worked. The token cost is minimal (utility calls use FAST_RESPONSE routing).
     Monitor cost for the first 48 hours after deployment.

4. **Unexpected behavior in callers that assume empty returns.** Some callers
   of `utility_llm_call()` may have been coded with the assumption that it
   returns empty strings, and their fallback logic may be the intended path.
   - **Mitigation:** Audit each caller before deployment. The callers listed
     in Section 3 all have `if result:` guards, so non-empty returns will
     be used correctly.

### Rollback strategy

The backend is discovered via adapter bridge. To roll back:

```python
# Emergency: force NullBackend
from umh.execution.interfaces import set_execution_backend
from umh.execution.interfaces import NullExecutionBackend
set_execution_backend(NullExecutionBackend())
```

Or simply delete `umh/adapters/umh_execution.py` — the discovery falls back
to NullBackend automatically.

### Dependencies on other work

- **None for Steps 1-4.** The backend creation is self-contained.
- **Step 5 (translate_and_run wiring)** depends on deciding whether
  `umh.run.run()` or `EOSGateway._route_agent_task()` is the canonical
  path. This is an architectural decision documented separately in
  `docs/plans/execution_unification_plan.md`.
- **Step 6 (bypass redirects)** can proceed independently per-file after
  the backend is verified working.
