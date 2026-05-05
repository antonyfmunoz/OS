# UMH Test & Import Integrity Report

**Date:** 2026-04-26
**Branch:** main
**Commit:** 67b619d

---

## 1. Import Health

### umh top-level import: OK

`import umh` succeeds without error.

### Legacy import references in umh/: 0

No references to `eos_ai`, `eos.`, `core.`, `scripts.`, or `services.` found in `umh/**/*.py`.
Legacy namespace migration is complete.

### Missing module imports in umh/ source: 9

These are `from umh.X import Y` statements in production code where `umh.X` does not exist on disk:

| File | Line | Missing Module |
|------|------|---------------|
| `umh/runtime_engine/voice_interface.py` | 32 | `umh.runtime_engine.media_processor` |
| `umh/substrate/plan_executor.py` | 41 | `umh.substrate.adaptive_orchestration_policy` |
| `umh/substrate/plan_executor.py` | 47 | `umh.substrate.context_budget` |
| `umh/substrate/plan_executor.py` | 48 | `umh.substrate.orchestration_record` |
| `umh/substrate/trigger_adapters.py` | 25 | `umh.substrate.workflow_events` |
| `umh/substrate/workflow_driver.py` | 46 | `umh.substrate.workflow_events` |
| `umh/substrate/intent_coordinator.py` | 110 | `umh.substrate.workflow_events` |
| `umh/interfaces/discord/bot.py` | 157 | `umh.runtime_engine.onboarding_engine` |
| `umh/interfaces/discord/dm_monitor.py` | 24 | `umh.runtime_engine.error_handler` |

**Most critical:** `umh.substrate.workflow_events` is imported by 3 production modules and causes cascading import failures across `intent_coordinator`, `workflow_driver`, and `trigger_adapters`. Any code path touching orchestration bootstrap will crash at import time.

---

## 2. Test Results

### Summary (pytest-compatible files only)

| Metric | Count |
|--------|-------|
| Total test files | 225 |
| Script-style (not pytest-compatible) | 59 |
| Pytest-compatible | 166 |
| Collection errors | 16 + 11 = 27 |
| **Passed** | **4,470** |
| **Failed** | **28** |
| **Errors (runtime)** | **11** |

### Pass rate (collected tests): 97.4% (4,470 / 4,509)

### Failed tests by file (28 total)

**tests/test_execution_spine.py** (8 failures)
- Root cause: `AttributeError: module 'umh.runtime_engine' has no attribute 'context'`
- The module `umh.runtime_engine.context` does not exist. Tests mock a path that no longer exists.

**tests/test_llm_outcomes.py** (12 failures)
- Root cause: `TypeError: build_llm_prompt() got an unexpected keyword argument 'outcome_summary'`
- Tests expect an `outcome_summary` kwarg that was removed or never added to `build_llm_prompt()`.

**tests/test_intent_memory.py** (3 failures)
- Root cause: `AssertionError: 'decision_blocked_by_memory' not in event types`
- Decision engine behavior changed; memory guard no longer emits the expected event type.

**tests/test_llm_integration.py** (2 failures)
- Root cause: `ModuleNotFoundError: No module named 'umh.runtime_engine.substrate'`
- Test imports from a subpackage that does not exist.

**tests/test_llm_replay.py** (1 failure)
- Root cause: `AssertionError: 'no_active_intents' != 'intent_type_excluded'`
- Behavior change in skip reason string.

**tests/unit/test_umh_mvp.py** (2 failures — flaky)
- Tests passed on isolated re-run (74/74 passed). Likely module state pollution from prior tests in full suite run.

### Collection errors (27 total across 16 + 11 files)

| Error Type | Count | Files |
|------------|-------|-------|
| `umh.substrate.workflow_events` missing | 5 | test_autonomy_policy, test_discord_ingress, test_e2e_active_mode, test_ingress_activation, test_intent_coordinator |
| `umh.runtime_engine.substrate` missing | 1 + 11 | test_llm_integration, test_task_checkpoint (11 tests) |
| Import name missing from existing module | 3 | test_execution_bridge (`create_workstation_run_for_batch`), test_decision_ingress_unification (`_LIFECYCLE_EVENT_TO_INTENT`), test_intent_competition (`_select_winner`), test_llm_quality_layer (`_build_intent_objectives`) |
| Legacy `eos/` path reference | 2 | test_fabric_analytics, test_memory_fabric |
| Module key missing from sys.modules | 2 | test_influence_integration (`umh.runtime_engine.strategy_memory`), test_world_state_reinforcement (`umh.runtime_engine.world_state`) |

---

## 3. Known Pre-existing Issues

### sys.exit() at module level in test files: 89 occurrences across 59 files

These files use a script-style test pattern with module-level `sys.exit()` calls. When pytest collects them, the `sys.exit()` fires during import, causing an `INTERNALERROR` that aborts the entire test run.

**Impact:** A single one of these files appearing before other test files in collection order will kill pytest. The 59 files are spread across `tests/` (47) and `tests/substrate/` (12).

**Pattern:** All follow the same anti-pattern:
```python
# Module-level test execution + sys.exit
PASS, FAIL = 0, 0
# ... test code runs at import time ...
if FAIL > 0:
    sys.exit(1)
sys.exit(0)
```

These tests only work when run directly as `python3 tests/test_foo.py`, not via pytest.

### Files referencing deleted `eos/` namespace: 2

- `tests/test_fabric_analytics.py` references `/opt/OS/eos/fabric_analytics.py`
- `tests/test_memory_fabric.py` references `/opt/OS/eos/memory_fabric.py`

---

## 4. Docker Health

### Config: VALID

Warnings:
- `version` attribute is obsolete (cosmetic, no impact)
- `ANTHROPIC_API_KEY` not set in compose environment (expected; loaded from `.env` at runtime)

### Services (5):

| Service | Container Name |
|---------|---------------|
| os-discord | os-discord |
| os-monitor | os-monitor |
| os-scraper | os-scraper |
| os-webhook | os-webhook |
| os-bot | os-bot |

---

## 5. Verdict

### Is the repo safe for the next refactor wave? YES, with conditions.

The core runtime is healthy. 4,470 tests pass. Zero legacy namespace imports remain in production code. Docker config is valid.

### Must fix before next refactor:

1. **Create `umh/substrate/workflow_events.py`** (or remove/stub the imports)
   - This is the single highest-impact missing module. It cascades into 3 production files and 5+ test files. Any orchestration bootstrap path will crash at import time today.

2. **Guard the 59 script-style test files** from pytest collection.
   Options (pick one):
   - Wrap all module-level code in `if __name__ == "__main__":` guards
   - Rename them to not start with `test_` (e.g., `check_*.py`)
   - Add a `conftest.py` collect_ignore list
   - Add `# pytest: skip-file` markers

3. **Update or remove stale test assertions** in 6 files (28 failures):
   - `test_execution_spine.py` — mock path `umh.runtime_engine.context` no longer exists
   - `test_llm_outcomes.py` — `outcome_summary` kwarg removed from `build_llm_prompt`
   - `test_intent_memory.py` — event type string changed
   - `test_llm_integration.py` — `umh.runtime_engine.substrate` does not exist
   - `test_llm_replay.py` — skip reason string changed
   - `test_task_checkpoint.py` — `umh.runtime_engine.substrate` does not exist

### Should fix (not blocking):

4. Remaining 8 missing module imports in `umh/` production code (media_processor, onboarding_engine, error_handler, adaptive_orchestration_policy, context_budget, orchestration_record). These are behind conditional imports or unused code paths today but will crash if reached.

5. Delete `tests/test_fabric_analytics.py` and `tests/test_memory_fabric.py` — they reference the dead `eos/` namespace.

6. 3 tests import private names that were removed from their modules (`_LIFECYCLE_EVENT_TO_INTENT`, `_select_winner`, `_build_intent_objectives`). These tests need updating to match current APIs.
