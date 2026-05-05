# Phase 1: Execution Wiring Plan

**Date:** 2026-04-26
**Status:** PROPOSED — depends on Phase 0 completion (DONE) and ExecutionBackend creation
**Risk Level:** MEDIUM — each step is LOW individually, but cumulative surface is broad
**Prerequisite:** Phase 0 security fixes complete. ExecutionBackend design approved.

---

## 1. Current State

### Working production path (strategy-eligible)
```
Discord/Telegram → EOSGateway.handle() → SessionRuntime.run()
  → run_with_strategies() → call_with_fallback() → SpineResult
```
This path works because `multi_strategy.py` calls `call_with_fallback()` directly
for GENERATE/ANALYZE task types, bypassing `execute()` entirely.

### Broken canonical path (non-strategy-eligible)
```
run_via_umh() → execute() → NullExecutionBackend → REJECTED
```
All non-strategy types (SUMMARIZE, SCORE, CLASSIFY, FAST_RESPONSE, JOURNAL)
hit NullExecutionBackend and silently fail.

### Broken utility path
```
utility_llm_call() → lightweight_execute() → execute() → NullBackend → ""
```
13 callers across 7 files receive empty strings for every utility LLM call.

### Dead gateway path
```
translate_and_run() → umh.run.run() → dispatch_prompt() → adapter
```
Zero production callers. Not wired to any interface.

---

## 2. Target State

After Phase 1, the canonical path works:
```
execute() → SpineExecutionBackend → call_with_fallback() → ExecutionResult(SUCCEEDED)
```

This automatically fixes:
- `run_via_umh()` — returns real LLM output instead of REJECTED
- `utility_llm_call()` — returns non-empty strings to all 13 callers
- `lightweight_execute()` — returns SUCCEEDED instead of REJECTED

What does NOT change in Phase 1:
- `multi_strategy.py` still calls `call_with_fallback()` directly (SANCTIONED)
- `LLMGenerationStage` still calls `call_with_fallback()` directly (it IS the pipeline stage)
- `meeting_intelligence.py` still calls `call_with_fallback()` directly (SANCTIONED — real-time latency)
- `voice_eos_responder.py` still calls `call_with_fallback()` directly (SANCTIONED — avoids DB writes)
- `translate_and_run()` remains unwired (Phase 3 decision)

---

## 3. Entrypoints to Wire

### Step 1: Create SpineExecutionBackend (the keystone)
**New file:** `umh/adapters/umh_execution.py`
**Design:** See `docs/plans/execution_backend_design.md` for full specification.
**What it does:** Implements `ExecutionBackend` protocol, delegates to `call_with_fallback()`.
**Why it works:** `_default_backend()` in `execution/interfaces.py:88-96` already tries to discover
this exact module path. Creating the file automatically replaces NullExecutionBackend.
**Risk:** LOW — purely additive. No existing files change.

**Verification:**
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.adapters.umh_execution import get_execution_backend_adapter
b = get_execution_backend_adapter()
print(f'{type(b).__name__} — can_handle llm_generate: {b.can_handle(\"llm_generate\")}')
"
```

### Step 2: Verify automatic registration
**No file changes** — just validate that `get_execution_backend()` returns `SpineExecutionBackend`.

**Verification:**
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.execution.interfaces import reset_execution_backend, get_execution_backend
reset_execution_backend()
b = get_execution_backend()
assert type(b).__name__ != 'NullExecutionBackend', 'Still Null!'
print(f'Backend: {type(b).__name__} — OK')
"
```

### Step 3: Verify utility_llm_call() starts returning real results
**No file changes** — the 13 callers already route through `lightweight_execute()` → `execute()`.
With the real backend, they'll start producing output.

**Callers that will automatically start working:**

| # | File:Line | What it does | Current behavior |
|---|-----------|-------------|-----------------|
| 1 | `gateway.py:429` | Email instruction extraction | Returns empty → instruction ignored |
| 2 | `gateway.py:870` | Web search | Returns empty → no search results |
| 3 | `gateway.py:1764` | Intent classification | Returns empty → falls to regex |
| 4 | `bot.py:3240` | Quick draft generation | Returns empty → no draft |
| 5 | `dm_monitor.py:577` | DM classification | Returns empty → no classification |
| 6 | `intent_handler.py:238` | Intent classification | Returns empty → fallback |
| 7 | `cc_command_handler.py:38` | CC draft | Returns empty → no output |
| 8 | `cc_command_handler.py:102` | Date extraction | Returns empty → no date |
| 9 | `cc_command_handler.py:479` | Calendar extraction | Returns empty → no events |
| 10 | `calendly.py:408` | Follow-up draft | Returns empty → no draft |
| 11 | `business.py:372` | Workstation business task | Returns empty → no output |

**Verification:**
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.execution.interfaces import reset_execution_backend
reset_execution_backend()
from umh.gateway.entry import utility_llm_call
result = utility_llm_call('Reply with OK', operation='wiring_test')
assert result, 'Still empty!'
print(f'utility_llm_call returned: {result[:80]}')
"
```

### Step 4: Verify run_via_umh() works for non-strategy types
**No file changes** — `run_via_umh()` already calls `execute()`.

**Verification:**
```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.execution.interfaces import reset_execution_backend
reset_execution_backend()
from umh.runtime_engine.execution_spine import run_via_umh
result = run_via_umh(
    message='Summarize: The sky is blue.',
    unified_context=None,
    agent_type='executive_assistant',
    task_type='summarize',
)
assert 'No execution backend' not in str(result)
print(f'run_via_umh: {str(result)[:100]}')
"
```

---

## 4. Bypasses to Redirect (Phase 1 scope)

These files call `call_with_fallback()` or `get_router()` directly and SHOULD
be redirected to `utility_llm_call()` or `lightweight_execute()` for
observability. Each is a 2-5 line change.

### Priority order (least risk first)

| # | File | Calls | Current pattern | Target pattern | Risk |
|---|------|-------|----------------|---------------|------|
| 1 | `world_pulse.py:206` | 1 | `router.call_with_fallback()` | `utility_llm_call()` | LOW |
| 2 | `ceo_agent.py:193` | 1 | `router.call_with_fallback()` | `utility_llm_call(force_opus=True)` | LOW |
| 3 | `email_gps.py:296,529,597,633` | 4 | `router.call_with_fallback()` | `utility_llm_call()` | MEDIUM |
| 4 | `execution/runtime.py:247` | 1 | `router.call_with_fallback()` | `lightweight_execute()` | MEDIUM |

### SANCTIONED — do NOT redirect in Phase 1

| File | Reason |
|------|--------|
| `multi_strategy.py:349` | Intentional multi-candidate generation — pipeline overhead defeats purpose |
| `stages/llm_generation.py:24` | IS the pipeline LLM stage — cannot redirect to itself |
| `meeting_intelligence.py:502,1280` | Real-time latency requirement |
| `voice_eos_responder.py:244` | Documented: avoids DB writes for voice pipeline |
| `agent_runtime.py:256` | Core agent dispatch — redirect only after full testing |
| `dm_monitor.py` genai.Client | Vision bypass — needs model_router vision support first |

---

## 5. Files Involved (complete list)

### Files that change in Phase 1

| File | Change | Lines affected | Risk |
|------|--------|---------------|------|
| `umh/adapters/umh_execution.py` | **NEW** — SpineExecutionBackend | ~90 lines | LOW |
| `tests/test_execution_backend.py` | **NEW** — backend tests | ~60 lines | LOW |
| `umh/runtime_engine/world_pulse.py` | Redirect 1 call | ~3 lines | LOW |
| `umh/runtime_engine/ceo_agent.py` | Redirect 1 call | ~3 lines | LOW |
| `umh/runtime_engine/email_gps.py` | Redirect 4 calls | ~12 lines | MEDIUM |
| `umh/execution/runtime.py` | Redirect 1 call | ~3 lines | MEDIUM |

### Files that do NOT change

| File | Reason |
|------|--------|
| `umh/execution/engine.py` | Already correct — calls `get_execution_backend()` |
| `umh/execution/interfaces.py` | Already correct — discovery wired to `umh.adapters.umh_execution` |
| `umh/execution/pipeline.py` | Unchanged — pipeline stages work |
| `umh/gateway/entry.py` | Unchanged — `utility_llm_call()` already routes through `execute()` |
| `umh/runtime_engine/execution_spine.py` | Unchanged — `run_via_umh()` already calls `execute()` |
| `umh/runtime_engine/session_runtime.py` | Unchanged — delegates to `multi_strategy` |
| `umh/runtime_engine/multi_strategy.py` | SANCTIONED bypass |
| `umh/runtime_engine/gateway.py` | Unchanged — its `utility_llm_call()` calls will start working |

---

## 6. Behavioral Preservation Contracts

### Production path must remain identical
The Discord bot → EOSGateway → SessionRuntime → multi_strategy path for
GENERATE/ANALYZE must not change. Test: send a message via Discord, verify
response quality and latency are unchanged.

### Empty-string callers must handle non-empty gracefully
All 13 `utility_llm_call()` callers currently receive `""`. After the backend
fix, they receive real text. Every caller must be audited for:
- `if result:` guards (present in all known callers — safe)
- String length assumptions
- JSON parse expectations

### run_via_umh() callers must handle real SpineResult
`run_via_umh()` currently returns `SpineResult("No execution backend configured")`.
After fix, returns real LLM output. Callers must handle non-error SpineResult.

### Cost implications
utility_llm_call() callers will begin consuming tokens. Expected additional load:
- Email instruction extraction: ~200 tokens/call, ~5 calls/day = ~1K tokens/day
- Web search: ~300 tokens/call, ~10 calls/day = ~3K tokens/day
- Intent classification: ~100 tokens/call, ~50 calls/day = ~5K tokens/day
- Other utility calls: ~2K tokens/day
- **Total estimate:** ~11K additional tokens/day, well within budget

---

## 7. Test Plan

### Pre-deployment
```bash
# 1. Import check
python3 -c "import umh; print('OK')"

# 2. Unit tests
python3 -m pytest tests/unit -q --tb=line

# 3. Backend-specific tests
python3 -m pytest tests/test_execution_backend.py -v

# 4. Verify NullBackend replaced
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.execution.interfaces import reset_execution_backend, get_execution_backend
reset_execution_backend()
b = get_execution_backend()
assert type(b).__name__ == 'SpineExecutionBackend'
print('Backend OK')
"

# 5. Verify utility_llm_call works
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from umh.execution.interfaces import reset_execution_backend
reset_execution_backend()
from umh.gateway.entry import utility_llm_call
r = utility_llm_call('Reply with the word WORKING', operation='test')
print(f'utility_llm_call: {r[:80]}')
"
```

### Post-deployment (manual)
1. Send a Discord message — verify normal GENERATE/ANALYZE response
2. Trigger an email instruction — verify extraction now works
3. Check Discord intent classification — verify it uses LLM instead of regex fallback
4. Monitor token cost for 48 hours

---

## 8. Rollback Plan

### Immediate rollback (no deploy needed)
Delete `umh/adapters/umh_execution.py`. The adapter discovery in
`_default_backend()` automatically falls back to NullExecutionBackend.
System returns to current behavior (utility calls return empty, non-strategy
types return REJECTED).

### Selective rollback
If only one redirect causes issues, revert that single file's change.
Each redirect is independent — reverting one doesn't affect others.

### Emergency runtime override
```python
from umh.execution.interfaces import set_execution_backend
from umh.execution.interfaces import NullExecutionBackend
set_execution_backend(NullExecutionBackend())
```

---

## 9. Dependencies

| Dependency | Status | Blocks |
|-----------|--------|--------|
| Phase 0 security fixes | **DONE** — all 4 applied, 712 tests pass | Nothing |
| ExecutionBackend design doc | **DONE** — `docs/plans/execution_backend_design.md` | Step 1 |
| model_router working | **WORKING** — production-tested | Step 1 |
| Adapter discovery wired | **WORKING** — `interfaces.py:88-96` already looks for the file | Step 2 |
| Vision support in model_router | **NOT DONE** — blocks dm_monitor redirect | Not Phase 1 |
| translate_and_run wiring | **NOT DONE** — Phase 3 decision | Not Phase 1 |

---

## 10. Execution Order

```
Step 1: Create umh/adapters/umh_execution.py ──── LOW risk, additive
  │
  ▼
Step 2: Verify auto-registration ──────────────── ZERO risk, read-only check
  │
  ▼
Step 3: Verify utility_llm_call() works ───────── ZERO risk, read-only check
  │
  ▼
Step 4: Verify run_via_umh() works ────────────── ZERO risk, read-only check
  │
  ▼
Step 5: Run full test suite ───────────────────── ZERO risk
  │
  ▼
Step 6: Redirect world_pulse.py ───────────────── LOW risk, 1 call
  │
  ▼
Step 7: Redirect ceo_agent.py ────────────────── LOW risk, 1 call
  │
  ▼
Step 8: Redirect email_gps.py ────────────────── MEDIUM risk, 4 calls
  │
  ▼
Step 9: Redirect execution/runtime.py ────────── MEDIUM risk, 1 call
  │
  ▼
Step 10: Full test suite + deploy ─────────────── Commit
```

Each step has its own verification command. If any step fails, stop and
investigate before proceeding. Each redirect is independently revertible.

---

## 11. What Phase 1 Does NOT Do

| Item | Why deferred |
|------|-------------|
| Wire `translate_and_run()` to interfaces | Phase 3 — requires deciding canonical pipeline |
| Redirect `multi_strategy.py` | SANCTIONED — intentional bypass |
| Redirect `meeting_intelligence.py` | SANCTIONED — real-time latency |
| Redirect `voice_eos_responder.py` | SANCTIONED — avoids DB writes |
| Redirect `dm_monitor.py` Gemini | Needs model_router vision support |
| Delete duplicate files | Phase 1.3 — needs import path verification first |
| Remove `cognitive_loop.py` | Phase 1.2 — needs `format_response_footer` move |
| Unify `EOSGateway` and `translate_and_run` | Phase 3 — architectural decision |
| Create stub modules for missing imports | Phase 1.5 — needs investigation |
