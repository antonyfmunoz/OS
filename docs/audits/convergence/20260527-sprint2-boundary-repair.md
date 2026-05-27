# Sprint 2 — Architecture Boundary Repair (Phase 1: Type Extraction)

**Date:** 2026-05-27
**Status:** Complete (Phase 1 of 2)
**Tests:** 12 new + 45 existing pass, 1 skipped

## What Changed

### Created: `substrate/contracts/agent_types.py`
Canonical home for types that substrate owns and adapters implement against:
- `TaskType` (20-value enum — superset of both old definitions)
- `AgentResult` (dataclass)
- `RoutingResult` (dataclass)
- `ModelProvider` (12-value enum)
- `COST_PER_MILLION_TOKENS` (cost table)
- `calculate_cost()` (utility)

### Eliminated Duplicate Definitions
- `adapters/models/agent_runtime.py` — removed `TaskType` enum, `AgentResult` dataclass, `COST_PER_MILLION_TOKENS`, `calculate_cost()`. Now re-exports from substrate.
- `adapters/models/model_router.py` — removed `TaskType` enum, `RoutingResult` dataclass, `ModelProvider` enum. Now re-exports from substrate.

### Rewrote 38 Substrate Files
All `from adapters.models.agent_runtime import TaskType/AgentResult/calculate_cost/COST_PER_MILLION_TOKENS` and `from adapters.models.model_router import TaskType/RoutingResult/ModelProvider` in substrate now import from `substrate.contracts.agent_types`.

## Violation Count

| State | substrate→adapters imports |
|-------|--------------------------|
| Before | 116 |
| After | 93 |
| Eliminated | 23 (20%) |

## What Remains (93 violations — Phase 2 scope)

| Category | Count | Fix Pattern |
|----------|-------|------------|
| `AgentRuntime` instantiation | 14 | Factory/DI — substrate defines protocol, adapters register impl |
| `get_router`/`call_with_fallback` | ~40 | Model port protocol in substrate |
| External connectors (GWS, Notion, Scrapling) | ~20 | Adapter port protocols |
| Tool adapters (filesystem, git, shell) | ~10 | Tool port protocols |
| Other (LLMAdapter, adapter registry) | ~9 | Boot registration refactor |

## Backward Compatibility

All adapters re-export from the canonical substrate location. Any external code importing `from adapters.models.agent_runtime import TaskType` continues to work — it gets the exact same object (verified by identity test, not just equality).

## Recommended Next Sprint

**Sprint 3 — Test Recovery** (as originally planned)
- Restore failing tests
- Add timeouts/mocks to hanging tests  
- Add pytest-cov
- Register integration marks

Phase 2 of boundary repair (model port protocol, adapter ports) should follow after test infrastructure is solid.
