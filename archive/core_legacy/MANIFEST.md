# Core Legacy Archive Manifest

Archived during convergence Wave 3 — 2026-05-10.

## Why Archived

These directories and files are pre-substrate architecture that predates
the substrate v1 system. They contain zero `_v1.py` files, have no live
service or eos_ai imports, and are only referenced by other pre-substrate
code or dormant tests.

## Directories Archived (6)

| Directory | Files | Classification | Importers |
|-----------|-------|---------------|-----------|
| adapter_engine/ | 5 | dormant reference | tests=4 only |
| adapter_package_manager/ | 34 | dormant reference | tests=32 only |
| connectors/ | 5 | legacy architectural artifact | core-internal only |
| domain/ | 4 | legacy architectural artifact | core-internal only |
| mastery_engine/ | 3 | dormant reference | tests=2 only |
| security/ | 9 | dormant reference | 1 smoke test only |

## Root Files Archived (16)

| File | Classification | Importers |
|------|---------------|-----------|
| capabilities.py | legacy (core=2) | core-internal only |
| composer.py | legacy (core=2, tests=1) | core-internal only |
| context.py | legacy (core=1) | core-internal only |
| dynamics.py | legacy (core=1, tests=1) | core-internal only |
| execution_bridge.py | legacy (core=1) | core-internal only |
| feedback.py | legacy (core=1) | core-internal only |
| improvement_governor.py | legacy (core=1, tests=1) | core-internal only |
| matcher.py | legacy (core=1) | core-internal only |
| memory_evolution.py | legacy (core=1, tests=1) | core-internal only |
| objective.py | legacy (core=2) | core-internal only |
| objective_engine.py | legacy (core=1, tests=1) | core-internal only |
| primitives_extended.py | dead | 0 importers |
| reality_input.py | legacy (core=1) | core-internal only |
| router.py | legacy (core=1) | core-internal only |
| self_improvement.py | dead | 0 importers |
| transformer.py | legacy (core=3) | core-internal only |

## Scripts Archived (1)

| File | Classification | Importers |
|------|---------------|-----------|
| security_smoke_test.py | dormant | 0 importers |

## Associated Legacy Tests

40 test files moved to tests/legacy/ — all import exclusively
from archived core directories/files.

## Directories NOT Archived (blocked — live importers)

| Directory | Reason |
|-----------|--------|
| action_system/ | scr=5, core=9 (transitional) |
| coherence/ | scr=1, core=2 (transitional) |
| environment_bridge/ | eos=3, v1=3 (transitional, substrate deps) |
| orchestrator/ | scr=6, core=4 (transitional) |
| state/ | eos=1, v1=5 (transitional, substrate deps) |
| tool_mastery_author_agent/ | scr=2, core=2 (transitional) |
| tool_mastery_manager/ | scr=2, core=1 (transitional) |
| tool_mastery_research_agent/ | scr=2 (transitional) |

## Root Files NOT Archived (blocked — live importers)

13 root .py files with live script/eos_ai/service importers remain
as transitional runtime dependencies.

## Rollback

```bash
git revert <wave-3-commit>
```
