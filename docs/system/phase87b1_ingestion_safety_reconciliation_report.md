# Phase 87B.1 — Ingestion Safety Validation Reconciliation

**Date**: 2026-05-03
**Status**: Complete
**Extends**: Phase 87B (Tool-Agnostic Onboarding Context Ingestion v1)
**Tests**: 164 passing (Phase 87B), 509 total (86 + 87 + 87A + 87B)
**Safety**: 10 modules checked, 0 violations, 0 warnings, 10 scanned paths
**Hard rules**: 20

## Problem Statement

During Phase 87B, an intermediate safety validation output showed
"Modules checked: 0" while the final report correctly stated 10 modules
checked with 0 violations. This discrepancy needed root cause analysis
and a fix to prevent false positives.

## Root Cause Analysis

`check_all_ingestion_modules()` used `Path(__file__).parent` to locate
the ingestion directory. This pattern works correctly under normal import
conditions but has three failure modes:

1. **Timing**: If called before all modules are written to disk (during a
   build), it returns only the modules that exist at call time — potentially 0.
2. **Path resolution**: If `__file__` is not set (frozen imports, zip packages,
   certain test runners), `Path(__file__)` raises or resolves to an unexpected
   location.
3. **Silent false positive**: When 0 modules are found, the function returned
   `all_safe: True` because `total_violations == 0` is vacuously true for an
   empty scan. This is the critical bug — an empty scan should never be "safe."

The most likely cause of the observed "Modules checked: 0" output was a
validation call during the build process before all ingestion modules
were written to disk.

## Fix Applied

### `umh/ingestion/safety.py` — `check_all_ingestion_modules()`

| Change | Before | After |
|--------|--------|-------|
| Dir parameter | `Path(__file__).parent` hardcoded | `ingestion_dir` parameter with `Path(__file__).parent` default |
| Non-existent dir | No check — glob returns empty | Returns `all_safe: False` + warning |
| Empty scan | `all_safe: True` (vacuous truth) | `all_safe: False` + "No Python modules found" warning |
| Scanned paths | Not tracked | `scanned_paths` list in return dict |
| Warning count | Not tracked | `warning_count` field in return dict |

### Return dict (post-fix)

```python
{
    "modules_checked": int,     # count of .py files scanned (excludes __init__)
    "total_violations": int,    # sum of all violation categories
    "warning_count": int,       # per-module parse warnings + scan-level warnings
    "all_safe": bool,           # True only if modules_checked > 0 AND violations == 0
    "scanned_paths": list[str], # full paths of every scanned file
    "results": list[dict],      # per-module safety results
    "warnings": list[str],      # scan-level warnings (empty dir, missing dir)
}
```

## New Tests (8)

| Test | Validates |
|------|-----------|
| `test_module_count_positive` | modules_checked > 0 |
| `test_scanned_paths_returned` | scanned_paths present, correct length, all .py |
| `test_warning_count_returned` | warning_count field present, == 0 for clean scan |
| `test_explicit_dir_parameter` | explicit ingestion_dir=/opt/OS/umh/ingestion works |
| `test_nonexistent_dir_returns_warning` | missing dir → all_safe=False, warning present |
| `test_empty_dir_returns_warning` | empty dir → all_safe=False, "No Python modules" warning |
| `test_detects_forbidden_module_prefix` | AST detects `from umh.execution.runner import run` |
| `test_detects_network_listener_pattern` | AST detects `def start_server()` |

## Files Modified

| File | Change | Risk |
|------|--------|------|
| `umh/ingestion/safety.py` | Added ingestion_dir param, guards, scanned_paths, warning_count | LOW |
| `tests/test_phase87b_onboarding_context_ingestion.py` | 8 new tests in TestSafety (7 → 15) | LOW |
| `docs/system/phase87b_onboarding_context_ingestion_report.md` | Safety Reconciliation section + updated counts | LOW |

## Regression

- **Phase 87B tests**: 164/164 passing (156 original + 8 reconciliation)
- **Phase 87A tests**: 146/146 passing (unchanged)
- **Phase 87 tests**: 118/118 passing (unchanged)
- **Phase 86 tests**: 81/81 passing (unchanged)
- **Combined**: 509/509 passing

## Safety Validation (Post-Fix)

```
modules_checked:  10
total_violations: 0
warning_count:    0
all_safe:         True
scanned_paths:    10 (contracts, onboarding, permissions, review_policy,
                      routing, safety, source_classes, source_registry,
                      tool_stack, views)
```
