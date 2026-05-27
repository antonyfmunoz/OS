# Sprint 1 — Production Stabilization

**Date:** 2026-05-27
**Status:** Complete
**Tests:** 17 passed, 1 skipped (API key gated)

## Fixes Applied

### 1. NodeRegistry Deadlock (P0)
**File:** `transports/node_mesh/registry.py`
**Root cause:** `update_heartbeat()` held `threading.Lock()` then called `_write_snapshot()` which tried to acquire the same lock. Non-reentrant lock = deadlock on every heartbeat.
**Fix:** `threading.Lock()` → `threading.RLock()`. Also replaced silent `except: pass` with `logger.debug()`.

### 2. Missing runtime_execution_result_v1.py (P0)
**Files created:** `substrate/execution/runtime/runtime_execution_result_v1.py`
**Root cause:** Module referenced by both `live_local_runtime_execution_v1.py` and `local_runtime_supervisor_v1.py` was never committed. Broke the entire execution spine import chain.
**Fix:** Created module with `ExecutionOutcome`, `ProofArtifactType`, `ProofArtifact`, `RuntimeExecutionResult`, and `persist_execution_result()` — all matching the exact signatures expected by consumers.

### 3. Missing runtime_presence_state_v1.py (P0)
**Files created:** `substrate/execution/runtime/runtime_presence_state_v1.py`
**Root cause:** Module referenced by `local_runtime_supervisor_v1.py` was never committed. Broke supervisor import chain.
**Fix:** Created module with `WorkstationPresenceState`, `WorkstationPresence`, and `is_execution_capable()`.

### 4. Ghost runtime/.env References (P1)
**Root cause:** 15+ files referenced `/opt/OS/runtime/.env` which does not exist. The actual `.env` is at `/opt/OS/.env`. This caused:
- `context.py` to silently fail to load env → `KeyError: 'EOS_ORG_ID'` crash
- Every service that loaded from this path got zero env vars

**Files fixed (load_dotenv calls):**
- `substrate/state/context/context.py` — also fixed parent traversal (was 3 levels, needed 4) and changed `os.environ["EOS_ORG_ID"]` to `os.environ.get()` for graceful degradation
- `transports/api/operator.py`
- `services/operator_api.py`
- `umh/voice_server.py`
- `scripts/export_pipeline.py`
- `scripts/gws_scanner_cron.py`
- `scripts/notion_setup.py`
- `scripts/build_notion_workspace.py`
- `scripts/discord_setup_channels.py`
- `substrate/execution/feedback.py`
- `substrate/execution/trace.py`
- `substrate/execution/runtime/runtime_bootstrap_state_v1.py`
- `substrate/understanding/embedding/embedding_engine.py` — also fixed parent traversal
- `substrate/execution/media/media_processor.py` (error message)
- `adapters/higgsfield/higgsfield_client.py` (docstring)
- `adapters/models/agent_runtime.py` — fixed to use repo root `.env`

### 5. Smoke Tests
**File created:** `tests/test_sprint1_smoke.py`
**Coverage:** 18 tests across 6 test classes:
- `TestNodeRegistryDeadlock` — RLock type check, heartbeat no-deadlock, node_count
- `TestRuntimeExecutionResultV1` — imports, creation, hash, serialization, failure outcome
- `TestRuntimePresenceStateV1` — imports, transitions, serialization
- `TestSupervisorImportChain` — supervisor + live execution full import chain
- `TestContextEnvLoading` — env present, env missing graceful
- `TestServiceImportSmoke` — registry, operator exists, discord exists, agent_runtime (API-gated)

## Files Changed Summary

| Category | Files | Change |
|----------|-------|--------|
| New modules | 2 | `runtime_execution_result_v1.py`, `runtime_presence_state_v1.py` |
| New tests | 1 | `test_sprint1_smoke.py` |
| Deadlock fix | 1 | `registry.py` |
| Env path fixes | 14 | Various load_dotenv + comments |
| Audit doc | 1 | This file |
| **Total** | **19** | |

## Remaining Risks

1. **`services/.env` still exists separately** — dual env file loading (services/.env + .env) works but is fragile. Future sprint should consolidate to single `.env`.
2. **No integration test for actual heartbeat under load** — the deadlock fix is verified structurally (RLock type) but not under concurrent thread contention.
3. **`adapters/models/agent_runtime.py` loads env from `parents[2]`** — this resolves correctly in the standard repo layout but would break if the file moves.

## Recommended Next Sprint

**Sprint 2 — Architecture Boundary Repair**
- Move substrate-owned concepts (`TaskType`, `AgentRuntime`, `AgentResult`, model routing contracts) out of `adapters/`
- Reduce 107 substrate→adapters dependency violations
- Create clean substrate ports for model execution
- Keep adapters as implementations only
