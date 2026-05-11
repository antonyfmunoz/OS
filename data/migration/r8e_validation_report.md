# R8e Validation Report — External Consumer Namespace Migration

> Generated: 2026-05-11
> Wave: R8e — Migrate external consumers to canonical runtime namespace

---

## Summary

| Metric | Value |
|--------|-------|
| Files modified | 323 |
| Lines changed | 1,671 (symmetric: 1,671 insertions, 1,671 deletions) |
| `from eos_ai.X` → `from runtime.X` | 1,142 sites |
| `import eos_ai.X` → `import runtime.X` | 34 sites |
| `load_dotenv(eos_ai/.env)` → `load_dotenv(runtime/.env)` | 43 sites |
| `__import__("eos_ai.X")` → `__import__("runtime.X")` | 3 sites |
| `importlib.*("eos_ai.X")` → `importlib.*("runtime.X")` | 4 sites |
| `mock.patch("eos_ai.X")` → `mock.patch("runtime.X")` | 22 sites |
| File path refs (`eos_ai/X.py`) → `runtime/X.py` | ~75 sites |
| Comment/docstring updates | ~348 sites |
| Test baseline | 8684/2691/495 (exact match) |
| Module identity | PASS |
| Replay identity | PASS |
| Singleton identity | PASS |
| Cold boot | 0.079s (improved from 0.118s) |
| Regressions | 0 |

## Scope

### Directories migrated
- `services/` — 15 files (discord_bot.py, heartbeat.py, handlers/, etc.)
- `scripts/` — 158 files (smoke tests, operational tooling, graph tools, etc.)
- `tests/` — 150 files (unit tests, integration tests, legacy tests)

### NOT touched
- `archive/` — per R8e requirements
- `eos_ai/` — shims remain active
- `runtime/` — already canonical (R8c)
- `scripts/r8b_generate_bridges.py` — migration tool
- `scripts/r8d_generate_shims.py` — migration tool
- `scripts/r8_import_graph_snapshot.py` — migration tool
- `scripts/r8_compare_import_graphs.py` — migration tool

## Migration Categories

### 1. Import rewrites (1,176 sites)
Standard `from eos_ai.X import Y` → `from runtime.X import Y` and
`import eos_ai.X as Y` → `import runtime.X as Y`.

### 2. Env path rewrites (43 sites)
`load_dotenv(..., 'eos_ai', '.env')` → `load_dotenv(..., 'runtime', '.env')`.
`eos_ai/.env` is a symlink to `runtime/.env`, so both paths resolve to the
same file. The rewrite removes the symlink dependency.

### 3. Dynamic import rewrites (7 sites)
- `__import__("eos_ai.agent_teams")` → `__import__("runtime.agent_teams")`
  in `services/discord_bot.py` (2 lazy imports + 1 world_pulse import)
- `importlib.util.find_spec("eos_ai.substrate.X")` → `importlib.util.find_spec("runtime.substrate.X")`
  in 3 smoke test scripts
- `importlib.import_module("eos_ai.substrate.X")` → `importlib.import_module("runtime.substrate.X")`
  in 1 smoke test script

### 4. mock.patch target rewrites (22 sites)
All `patch("eos_ai.substrate.X.Y")` targets updated to `patch("runtime.substrate.X.Y")`.
These MUST match the import path used by the test's imports — since tests now
import from `runtime.*`, patch targets must too.

Files affected:
- `tests/test_phase94d6_local_worker_auto_loop.py` (10 patch targets)
- `tests/test_phase94d7_visible_browser_launch_backend.py` (3 patch targets)
- `tests/legacy/platforms/eos/test_voice_runtime.py` (3 patch targets)
- `tests/legacy/broken/test_windows_desktop_relay_client.py` (6 patch targets)

### 5. File path rewrites (~75 sites)
- HOT_PATH_FILES lists: `"eos_ai/gateway.py"` → `"runtime/gateway.py"`
- `open()` calls reading source: `open(f"{_ROOT}/eos_ai/substrate/X.py")` → `runtime/substrate/`
- `os.path.join()` paths: `os.path.join(_ROOT, "eos_ai", "X.py")` → `runtime`
- CLI command strings: `python3 eos_ai/substrate/X.py` → `python3 runtime/substrate/X.py`
- Filesystem watcher dirs: `["eos_ai", ...]` → `["runtime", ...]`
- Palace builder wings: `"wing": "eos_ai"` → `"wing": "runtime"`

### 6. String-based module references (~100 sites)
Smoke test module-check lists:
`"eos_ai.gateway"` → `"runtime.gateway"` (used in `sys.modules` verification)

### 7. Comment/docstring updates (~248 sites)
Module path references in docstrings, comments, and usage examples.

## Double-Rewrite Bug Fix

**Issue**: `eos_ai.runtime.work_state` was a depth-flattened shim path
(eos_ai/runtime/ → runtime/). The bulk sed rewrote it to
`runtime.runtime.work_state` — double `runtime`.

**Affected files**: `tests/test_work_state.py`, `tests/test_provider_state.py`,
`services/discord_bot.py`, `services/handlers/intent_handler.py`

**Fix**: Post-sed pass to collapse `runtime.runtime.` → `runtime.`.

## Preserved Legacy Validators

72 `eos_ai` string references intentionally preserved in legacy tests.
These are:
- `assert "import eos_ai" not in source` — R8c validators checking runtime/
  code doesn't import from bridges
- Test function names: `test_no_eos_ai_imports`, `test_imports_without_eos_ai`
- Docstring descriptions of validation purpose
- String test data: `classify_command("python3 -c 'from eos_ai import foo'")`

These MUST stay — they validate that the canonical runtime layer doesn't
depend on the compatibility shim layer.

## Identity Verification

### Module Identity (PASS)
```
PASS: eos_ai.db is runtime.db
```

### Replay Identity (PASS)
```
PASS: eos_ai.db.get_conn is runtime.db.get_conn
```

### Depth-Flattened Identity (PASS)
```
PASS: eos_ai.runtime.work_state is runtime.work_state
PASS: eos_ai.runtime.work_state._measure_pressure is runtime.work_state._measure_pressure
```

### Singleton Identity (PASS)
```
runtime.provider_state.get_system_state() is eos_ai.provider_state.get_system_state()
```

## Daemon Bootstrap Verification

All service entry-point imports verified:
```
runtime.model_router.call_with_fallback  — OK
runtime.agent_runtime.AgentRuntime       — OK
runtime.memory.AgentMemory               — OK
runtime.db.get_conn                      — OK
runtime.context.load_context_from_env    — OK
runtime.work_state.Pressure              — OK
runtime.work_state._measure_pressure     — OK
runtime.work_state.record_signal         — OK
runtime.provider_state.get_system_state  — OK
runtime.agent_teams.run_team_task        — OK
runtime.world_pulse.WorldPulse           — OK
```

## Cold Boot Timing

| Metric | R8d | R8e | Delta |
|--------|-----|-----|-------|
| Cold boot avg | 0.118s | 0.079s | -33% |

Improvement expected: external consumers now import directly from `runtime.*`
without traversing the shim layer.

## Test Baseline Comparison

| Metric | R8d | R8e | Delta |
|--------|-----|-----|-------|
| Passed | 8,684 | 8,684 | 0 |
| Failed | 2,691 | 2,691 | 0 |
| Errors | 495 | 495 | 0 |

**Zero regressions.**

## Rollback Command

```bash
git checkout HEAD -- services/ scripts/ tests/
```

## R8f Readiness Assessment

**Status: READY**

R8e is complete. External consumers now import directly from `runtime.*`:
- 323 files migrated (1,671 symmetric line changes)
- All identity guarantees preserved
- eos_ai/ shim layer still active for any unmigrated consumers
- Test baseline unchanged
- Daemon bootstrap verified
- Cold boot improved 33%

**R8f scope:** Remove the eos_ai/ compatibility shim layer. After R8e, the
only consumers of eos_ai/ shims are:
1. Legacy test validators (checking runtime/ doesn't use bridges — correct)
2. Any external/untracked consumers not in services/scripts/tests/

Before R8f: audit for any remaining live consumers of `eos_ai.*` imports
outside the migrated scope.
