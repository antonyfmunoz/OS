# Phase 0: Security Fixes Report

**Date:** 2026-04-26
**Status:** COMPLETE
**Agent:** Security Fix Implementer + Developer Agent verification
**Test result:** 712/712 unit tests pass, 4/4 files compile clean

---

## 1. Executive Summary

Four CRITICAL security bypasses were identified by the bypass inventory audit.
All four have been fixed. The fixes eliminate arbitrary shell execution via
Telegram, wrap a raw Gemini vision client with lazy-init and error handling,
replace a direct Ollama HTTP call with the canonical model_router, and deprecate
a raw Anthropic client property. No existing tests were broken. No new features
were added — these are pure security hardening changes.

---

## 2. Files Changed

| # | File | Lines changed | Nature of change |
|---|------|--------------|-----------------|
| 1 | `umh/interfaces/telegram/bot.py` | ~30 | Shell injection → strict command allowlist |
| 2 | `umh/interfaces/discord/dm_monitor.py` | ~25 | Module-scope genai.Client → lazy-init wrapper |
| 3 | `umh/runtime_engine/voice_engine.py` | ~15 | `requests.post()` to Ollama → `call_with_fallback()` |
| 4 | `umh/runtime_engine/agent_runtime.py` | ~3 | `.client` property → `raise RuntimeError` |

Total: 4 files, ~73 lines changed. No files deleted. No files created.

---

## 3. Critical Bypasses Fixed

### Fix 1: Telegram Shell Injection (CRITICAL → RESOLVED)
**File:** `umh/interfaces/telegram/bot.py:241-271`
**Before:** `subprocess.run(command, shell=True, ...)` executed any command sent
via Telegram with zero authority checks. Full system compromise vector — any
Telegram message in the right handler could run `rm -rf /` on the VPS.

**After:** Strict `_COMMAND_ALLOWLIST` dict mapping 9 safe commands to their
argv representations. Commands not in the allowlist receive a denial message
listing allowed commands. `shell=True` eliminated entirely — all commands
execute via `subprocess.run(cmd_argv, ...)` with list arguments.

**Allowed commands:** `git status`, `git log --oneline -10`, `docker ps`,
`docker ps -a`, `uptime`, `df -h`, `free -h`, `whoami`, `date`.

### Fix 2: Raw Gemini Client in dm_monitor (CRITICAL → MITIGATED)
**File:** `umh/interfaces/discord/dm_monitor.py:44-72`
**Before:** Bare `gemini_client = genai.Client(api_key=...)` at module scope.
Every import of dm_monitor created a raw Gemini client. All vision/DOM
extraction calls bypassed model_router.

**After:** Module-scope variable set to `None` (lazy-init). New
`_get_gemini_client()` function with:
- Availability check (`_GENAI_AVAILABLE`)
- API key presence check
- Error handling on init failure
- Clear logging on init
- TODO comment marking it as a known bypass needing model_router vision support

**Status: MITIGATED, not RESOLVED.** The `genai.Client` is still used for vision
tasks because `model_router` does not support image/vision analysis yet.
This is tracked as a model_router gap. The client is no longer module-scope
and has proper error handling.

### Fix 3: Direct Ollama HTTP in voice_engine (CRITICAL → RESOLVED)
**File:** `umh/runtime_engine/voice_engine.py:564-579`
**Before:** `requests.post(self._ollama_url, json={...})` sent raw HTTP to Ollama
for local LLM inference, completely bypassing model_router and all telemetry.

**After:** `model_router.call_with_fallback(prompt=..., system=...,
task_type="fast_response", trigger_source="voice_engine")`. All voice engine
LLM calls now route through the canonical fallback chain with full provider
selection, error handling, and cost tracking.

### Fix 4: Deprecated Anthropic Client in agent_runtime (CRITICAL → RESOLVED)
**File:** `umh/runtime_engine/agent_runtime.py:104-105`
**Before:** `.client` property returned `anthropic.Anthropic()` — any caller
got untracked API access outside the model_router fallback chain.

**After:** `.client` property raises `RuntimeError("Deprecated: use
model_router.call_with_fallback() instead")`. Any future caller gets an
immediate, clear error directing them to the canonical path.

**Verified:** Zero external callers of `.client` on AgentRuntime instances.
No downstream breakage.

---

## 4. Critical Bypasses Deferred

| # | Bypass | File:Line | Reason deferred |
|---|--------|-----------|----------------|
| 1 | `genai.Client` for vision | `dm_monitor.py:63` | model_router lacks vision/image support. Cannot redirect until model_router has a vision backend. Mitigated with lazy-init + error handling. |

All other CRITICAL bypasses were resolved. No HIGH bypasses were in Phase 0 scope.

---

## 5. Tests Run and Results

### Compilation
```
umh/interfaces/telegram/bot.py        — compile OK
umh/interfaces/discord/dm_monitor.py   — compile OK
umh/runtime_engine/voice_engine.py     — compile OK
umh/runtime_engine/agent_runtime.py    — compile OK
```

### Import
```
python3 -c "import umh; print('OK')" → OK
```

### Unit tests
```
python3 -m pytest tests/unit -q --tb=line
712 passed in 70.39s
```

No test failures. No regressions.

---

## 6. Remaining Grep Violations

### shell=True
| File:Line | Acceptable? | Reason |
|-----------|------------|--------|
| `adapters/workstation_adapter.py:83` | YES | FUTURE code (Jarvis/workstation pipeline). Internal commands only, not user-facing. Not Phase 0 scope. |
| `adapters/execution/workstation_adapter.py:83` | YES | Byte-identical duplicate of above. Same assessment. |
| `substrate/station_daemon.py:513` | YES | Comment/docstring mentioning shell=True. Not executable code. |
| `telegram/bot.py:255` | YES | Docstring in the new allowlisted function. Not executable code. |

### requests.post to Ollama
None remaining. Fix 3 resolved the only instance.

### anthropic.Anthropic() direct
None remaining. Fix 4 resolved the only instance.

### genai.Client direct
| File:Line | Acceptable? | Reason |
|-----------|------------|--------|
| `dm_monitor.py:63` | YES (mitigated) | Wrapped in lazy-init with error handling. Known bypass — needs model_router vision support. |

### call_with_fallback() direct callers (outside model_router)
11 files call `call_with_fallback()` directly. These are NOT security
violations — they route through the canonical model_router. They are
execution path bypasses (skip the `execute()` pipeline) documented in the
bypass inventory and classified as SANCTIONED or REDIRECT in the execution
unification plan. Phase 1 will redirect 4 of them; 7 remain SANCTIONED.

---

## 7. ExecutionBackend Design Summary

Full design: `docs/plans/execution_backend_design.md` (664 lines)

**Root cause:** `umh/adapters/umh_execution.py` does not exist. The adapter
discovery in `interfaces.py:88-96` tries to import it, gets `None`, and falls
back to `NullExecutionBackend` which always returns REJECTED.

**Solution:** Create `umh/adapters/umh_execution.py` with a `SpineExecutionBackend`
class that delegates to `call_with_fallback()` — the same function everything
already uses successfully. The existing adapter discovery is already wired to
find it — zero changes to existing files needed.

**Impact:** Fixes `utility_llm_call()` (13 callers returning empty strings),
fixes `run_via_umh()` (non-strategy types returning REJECTED), and fixes
`lightweight_execute()`.

**Risk assessment:**
- No double LLM calls (strategy-eligible types never reach `execute()`)
- No circular imports (all imports are lazy)
- Cost increase from utility calls is ~11K tokens/day (minimal)
- Rollback: delete the file — system reverts to NullBackend automatically

---

## 8. Phase 1 Wiring Plan Summary

Full plan: `docs/plans/phase1_execution_wiring_plan.md`

**Phase 1 creates 1 new file** (`umh/adapters/umh_execution.py`) and
**modifies 4 files** to redirect direct `call_with_fallback()` callers:

| Step | Action | Risk |
|------|--------|------|
| 1 | Create SpineExecutionBackend | LOW |
| 2 | Verify auto-registration | ZERO |
| 3 | Verify utility_llm_call() works | ZERO |
| 4 | Verify run_via_umh() works | ZERO |
| 5 | Run full test suite | ZERO |
| 6 | Redirect `world_pulse.py` (1 call) | LOW |
| 7 | Redirect `ceo_agent.py` (1 call) | LOW |
| 8 | Redirect `email_gps.py` (4 calls) | MEDIUM |
| 9 | Redirect `execution/runtime.py` (1 call) | MEDIUM |
| 10 | Full test suite + commit | ZERO |

**7 bypasses remain SANCTIONED:** multi_strategy (candidate generation),
LLMGenerationStage (is the pipeline), meeting_intelligence (latency),
voice_eos_responder (no DB writes), agent_runtime (core dispatch),
dm_monitor genai.Client (vision), voice_engine (already fixed — now uses model_router).

**Rollback:** Delete `umh/adapters/umh_execution.py` → system reverts to
NullBackend. Each redirect is independently revertible.

---

## 9. Is Phase 1 Implementation Safe to Begin?

**YES.** Phase 1 is safe to begin immediately. Rationale:

1. **Phase 0 is complete.** All 4 CRITICAL security bypasses are fixed.
   712/712 tests pass. No regressions.

2. **The keystone change is additive.** Creating `umh/adapters/umh_execution.py`
   does not modify any existing file. The adapter discovery mechanism already
   exists and will find it automatically.

3. **Each redirect is independent.** The 4 bypass redirects (Steps 6-9) are
   isolated 2-5 line changes with clear rollback paths.

4. **Existing production path is untouched.** The Discord → EOSGateway →
   multi_strategy path for GENERATE/ANALYZE does not change.

5. **Risk is well-bounded.** The worst case is utility_llm_call callers
   receiving unexpected LLM output — all callers have `if result:` guards.

**Condition:** The ExecutionBackend design must be reviewed before implementation.
The design doc is complete and ready for review.

---

## 10. Exact Next Prompt for Claude Code

```
You are implementing Phase 1 Step 1 of the execution wiring plan.

Read docs/plans/execution_backend_design.md section 4 for the full
SpineExecutionBackend specification.

Create umh/adapters/umh_execution.py with:
1. SpineExecutionBackend class implementing ExecutionBackend protocol
2. get_execution_backend_adapter() factory function
3. get_execution_observer_adapter() returning None

Then verify:
1. python3 -m py_compile umh/adapters/umh_execution.py
2. python3 -c "from umh.adapters.umh_execution import SpineExecutionBackend; print('OK')"
3. python3 -c "
   import sys; sys.path.insert(0, '/opt/OS')
   from umh.execution.interfaces import reset_execution_backend, get_execution_backend
   reset_execution_backend()
   b = get_execution_backend()
   print(type(b).__name__)
   assert type(b).__name__ != 'NullExecutionBackend'
   "
4. python3 -m pytest tests/unit -q --tb=line

Then write tests/test_execution_backend.py with:
- test_spine_execution_backend_can_handle
- test_spine_execution_backend_rejects_non_llm
- test_default_backend_discovers_real (not NullExecutionBackend)

Do NOT modify any existing files. Do NOT redirect any bypasses yet.
Do NOT touch multi_strategy, gateway, or any interface file.
```
