# Execution Unification Plan

**Date:** 2026-04-26
**Status:** PROPOSED — awaiting audit synthesis before execution
**Risk Level:** HIGH — touches the canonical execution path
**Prerequisite:** All 5 audit agents must complete and findings must be synthesized
**Bypass Inventory:** 71 patterns found (4 CRITICAL, 11 HIGH, 15 MEDIUM, 19 LOW, 22 INFO)

---

## Problem Statement

UMH currently has multiple execution paths that bypass the canonical `execute()` pipeline:

1. **Canonical path:** interface → `gateway/entry.py` → `runtime_engine/gateway.py` → `execution/engine.py:execute()` → `execution/pipeline.py` → 7 stages → result
2. **Lightweight path:** `gateway/entry.py:utility_llm_call()` → `execution/engine.py:lightweight_execute()` → `execute()` with reduced stages
3. **Spine path:** `runtime_engine/execution_spine.py:run_via_umh()` → builds pipeline inline, calls stages directly
4. **Direct model_router:** 6+ files call `model_router.call_with_fallback()` directly, bypassing all pipeline stages
5. **Direct provider:** 1-2 files instantiate LLM clients directly (`anthropic.Anthropic()`, `genai.Client()`)

## Goal

Every LLM call, execution action, memory write, and feedback signal routes through `execute()` or a sanctioned lightweight variant. The control plane invariant holds for all paths.

## Constraints

- NO file deletion
- NO package moves or renames
- NO breaking existing imports
- NO modifying service runtime behavior without explicit approval
- Tests must remain green throughout
- Each step must be independently verifiable

---

## Phase 0: Critical Security Fix (URGENT)

The bypass inventory discovered a **critical shell injection** that must be fixed before any other work.

### Step 0.1: Fix Telegram arbitrary shell execution
**File:** `umh/interfaces/telegram/bot.py:242`
**Finding:** `subprocess.run(command, shell=True, ...)` executes any command sent via Telegram with zero authority checks. Full system compromise vector.
**Fix:** Replace `shell=True` with allowlisted commands behind authority engine checks, or remove the raw shell capability entirely.
**Risk:** CRITICAL — this is a live security vulnerability.
**Priority:** Before next deploy.

### Step 0.2: Fix direct Ollama HTTP bypass
**File:** `umh/runtime_engine/voice_engine.py:572`
**Finding:** `requests.post()` to Ollama for LLM inference. Complete bypass of model_router.
**Fix:** Route through `model_router.call_with_fallback()` with Ollama backend.

### Step 0.3: Deprecate raw Anthropic client property
**File:** `umh/runtime_engine/agent_runtime.py:115`
**Finding:** `.client` property returns raw `anthropic.Anthropic()`. Any caller gets untracked API access.
**Fix:** Replace with `raise RuntimeError("Use model_router.call_with_fallback() instead")`.

---

## Phase 1: Safe Debt Elimination (NO RISK)

These changes are purely additive or remove confirmed dead code. They cannot break anything.

### Step 1.1: Delete duplicate files
**Files:** 
- `umh/execution/system_graph.py` (duplicate of `runtime_engine/system_graph.py`)
- `umh/execution/system_registry.py` (duplicate of `runtime_engine/system_registry.py`)
- `umh/execution/system_selector.py` (duplicate of `runtime_engine/system_selector.py`)

**Verification:** `grep -rn 'from umh.execution.system_' umh/ --include='*.py'` returns zero hits from production code.

**Risk:** ZERO — these files have zero production importers.

### Step 1.2: Eliminate cognitive_loop.py deprecated shim
**File:** `umh/runtime_engine/cognitive_loop.py`

**Current state:** Deprecated 2026-04-21. Only used as a shim — `context_builder.py` imports `format_response_footer` from it.

**Change:**
1. In `umh/runtime_engine/context_builder.py`, change:
   `from umh.runtime_engine.cognitive_loop import format_response_footer`
   to:
   `from umh.runtime_engine.execution_spine import format_response_footer`
2. Verify `format_response_footer` exists in `execution_spine.py`
3. Delete `cognitive_loop.py`

**Verification:** `python3 -c "from umh.runtime_engine.context_builder import ContextBuilder; print('OK')"`

**Risk:** LOW — one import change, well-understood.

### Step 1.3: Address 37 duplicate file pairs (17 byte-identical)
**Finding:** The future-trajectory auditor discovered 37 files that exist in both `runtime_engine/` and modular directories (`reasoning/`, `analytics/`, `goals/`, `planning/`, `policy/`, `feedback/`, `world/`, `persistence_layer/`, `signal/`, `strategy/`).

**17 byte-identical pairs** (safe to deduplicate — keep the modular version, update imports):
- `reasoning/causal_memory.py`, `reasoning/context_engine.py`, `reasoning/credit_assignment.py`, `reasoning/influence_scoring.py`, `reasoning/meta_control.py`, `reasoning/meta_generalization.py`
- `analytics/score_distribution.py`, `analytics/signal_orchestrator.py`, `analytics/strategy_pattern_memory.py`
- `planning/directive_engine.py`
- `policy/foresight_engine.py`, `policy/regime_engine.py`, `policy/risk_model.py`, `policy/stability_guard.py`
- `persistence_layer/persistence.py`

**20 diverged pairs** — require manual reconciliation before dedup. NOT Phase 1 work.

**Action for Phase 1:** Document the duplicates. Do NOT delete yet — need to verify import paths are updated first.

### Step 1.4: Fix NullExecutionBackend issue
**Finding:** `run_via_umh()` calls `execute()` which delegates to `NullExecutionBackend` (always returns REJECTED). No real `ExecutionBackend` implementation exists. Production works only because strategy-eligible types call `call_with_fallback()` directly. Non-eligible types (SUMMARIZE, SCORE, CLASSIFY, FAST_RESPONSE, JOURNAL) silently fail.

**Action for Phase 1:** Document this as a known gap. Do NOT fix yet — requires Phase 2 execution path consolidation.

### Step 1.5: Fix missing substrate module imports
**Missing modules referenced by production code:**
- `umh.substrate.workflow_events` — imported by `trigger_adapters.py`, `workflow_driver.py`, `intent_coordinator.py`
- `umh.substrate.task_finalization` — imported by `bot.py`, `cc_receiver.py`
- `umh.substrate.session_readiness` — imported by `cc_receiver.py`

**Options (choose one per module):**
A. Create minimal stub modules that define the expected types
B. Remove the imports if they're in lazy/try-except blocks that won't crash

**Investigation needed:** Check if these imports are guarded (try/except or lazy import) or bare. If bare, they crash at import time — meaning they're currently dead code paths.

**Risk:** LOW — either creating stubs (additive) or removing dead imports.

---

## Phase 2: Execution Path Consolidation (MEDIUM RISK)

### Step 2.1: Audit run_via_umh() callers
**File:** `umh/runtime_engine/execution_spine.py`

**Question:** Who calls `run_via_umh()` and can they be redirected to `execute()`?

**Investigation:**
```bash
grep -rn 'run_via_umh' umh/ --include='*.py' | grep -v 'def run_via_umh'
```

**Expected outcome:** Map every caller. For each, determine:
- Can it use `translate_and_run()` instead? (preferred — goes through gateway)
- Can it use `execute()` directly? (acceptable — goes through pipeline)
- Does it NEED to bypass pipeline stages? (document why)

### Step 2.2: Create execution audit decorator
**New file:** `umh/execution/audit.py` (small, additive)

**Purpose:** A decorator/wrapper that logs every `call_with_fallback()` invocation with caller info. Does NOT change behavior — only adds observability.

```python
def audited_call(original_fn):
    """Wraps call_with_fallback to log bypass callers."""
    @wraps(original_fn)
    def wrapper(*args, **kwargs):
        caller = inspect.stack()[1]
        logger.info(f"LLM call from {caller.filename}:{caller.lineno}")
        return original_fn(*args, **kwargs)
    return wrapper
```

**Risk:** LOW — additive observability, no behavior change.

### Step 2.3: Classify each bypass as REDIRECT or SANCTIONED

For each bypass path discovered in the audit:

| Bypass | Verdict | Rationale |
|---|---|---|
| `utility_llm_call()` | **SANCTIONED** | Already routes through `lightweight_execute()` → `execute()`. Part of gateway API. |
| `email_gps.py` direct calls | **REDIRECT** | Should use `utility_llm_call()` for consistency |
| `world_pulse.py` direct call | **REDIRECT** | Background intelligence — can use `utility_llm_call()` |
| `ceo_agent.py` direct call | **REDIRECT** | CEO strategy — can use `utility_llm_call(force_opus=True)` |
| `multi_strategy.py` direct call | **SANCTIONED** | Candidate generation intentionally calls model multiple times |
| `voice_eos_responder.py` | **SANCTIONED** | Documented: avoids DB writes. Could use lightweight_execute() later. |
| `meeting_intelligence.py` | **SANCTIONED** | Real-time meeting context. Pipeline overhead unacceptable. |
| `dm_monitor.py` genai.Client | **REDIRECT** | Should route through model_router with a vision capability |
| `agent_runtime.py` Anthropic() | **REDIRECT** | Legacy fallback — should use model_router |

### Step 2.4: Redirect REDIRECT bypasses one at a time

For each REDIRECT bypass:
1. Change the direct call to use `utility_llm_call()` or the appropriate gateway function
2. Run the affected file's tests
3. Verify the service still works
4. Commit

**Order (least risk first):**
1. `world_pulse.py` (1 call, background, low impact)
2. `ceo_agent.py` (1 call, strategy, low frequency)
3. `email_gps.py` (4 calls, email processing, medium frequency)
4. `agent_runtime.py` Anthropic client (legacy, needs model_router)
5. `dm_monitor.py` genai.Client (vision, needs model_router vision support)

**Risk per file:** MEDIUM — each is a targeted 1-3 line change with clear rollback.

---

## Phase 3: Spine Unification (HIGH RISK — future)

### Step 3.1: Reconcile execution_spine.py and execution/engine.py

**Current state:**
- `execution/engine.py` defines `execute()` — the canonical pipeline runner
- `runtime_engine/execution_spine.py` defines `run_via_umh()` — builds a pipeline inline

**Target:** `run_via_umh()` should delegate to `execute()` rather than building its own pipeline.

**NOT YET — requires:**
- All Phase 2 bypasses resolved
- Full test coverage of both paths
- Side-by-side comparison of what each path does differently
- Explicit approval

### Step 3.2: Unify gateway layers

**Current state:**
- `gateway/entry.py` — UMHInput/UMHOutput, translate_and_run()
- `runtime_engine/gateway.py` — route to domain handlers

**Target:** Single gateway with clear separation between transport translation and domain routing.

**NOT YET — requires Phase 3.1 complete.**

---

## What Must NOT Be Touched Yet

| Item | Reason |
|---|---|
| `runtime_engine/gateway.py` | 28 imports, fattest node — needs careful extraction |
| `interfaces/discord/bot.py` | 5339 lines, primary interface — needs incremental handler extraction |
| `substrate/__init__.py` | 821 lines, 43 re-exports — functional, cosmetic concern only |
| Any FUTURE file | Not in production path, no urgency |
| Model router fallback chain | Production LLM routing — change only with full rollback plan |
| Docker service configs | Live services — change only with explicit approval |

---

## Verification at Each Phase

After Phase 1:
```bash
python3 -c "import umh; print('OK')"
python3 -m pytest tests/ -q --tb=line
```

After Phase 2 (each step):
```bash
python3 -c "from umh.runtime_engine.[changed_module] import *; print('OK')"
python3 -m pytest tests/ -q --tb=line -k [relevant_test]
```

After Phase 3 (when ready):
```bash
python3 -m pytest tests/ -q
docker compose -f runtime/docker-compose.yml config --quiet
# Manual smoke test of Discord bot
```

---

## Decision Log

| Decision | Rationale | Date |
|---|---|---|
| utility_llm_call() is SANCTIONED | Routes through lightweight_execute() → execute(). Part of official gateway API. | 2026-04-26 |
| multi_strategy.py direct calls SANCTIONED | Intentional multi-candidate generation. Pipeline overhead would defeat purpose. | 2026-04-26 |
| voice/meeting bypasses SANCTIONED | Real-time latency requirements. Pipeline overhead unacceptable for voice. | 2026-04-26 |
| Phase 3 deferred | Too risky without Phase 2 complete and full test coverage. | 2026-04-26 |
