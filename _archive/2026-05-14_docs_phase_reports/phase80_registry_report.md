# Phase 80: Unified Registry System v1

**Status**: Complete
**Date**: 2026-05-03
**Tests**: 112 passed, 0 failed
**Regression**: 498 prior tests (75B + 76 + 77 + 78 + 79) pass

## Executive Summary

Phase 80 unifies UMH's discovery layer so capabilities, adapters, backends, environments, policies, models, tools, templates, libraries, workstation modes, and future resource metadata can be discovered through one coherent registry interface. Every existing definition is converted to a RegistryItem via compatibility bridges — no existing module is modified or broken.

## Why a Unified Registry Before Active Learning

The MVP harness now executes governed operations, produces outcomes, records feedback, creates memory candidates, and is fully inspectable. Before building active learning, policy adaptation, or autonomous behavior, the system must answer: "What resources exist, and how do I find them?" Without a registry, each consumer reinvents resource discovery — leading to N:M coupling between consumers and providers.

## Files Created (6)

| File | Purpose |
|------|---------|
| `umh/registry/__init__.py` | Registry package |
| `umh/registry/contracts.py` | RegistryType (16), RegistryItemStatus (8), RegistryAuthorityRequirement (6), RegistryItem, RegistryQuery, RegistryQueryResult |
| `umh/registry/bridges.py` | 6 bridge functions: capability/environment/adapter/backend/mode/policy → RegistryItem |
| `umh/registry/catalog.py` | RegistryCatalog class, build_default_registry_catalog() |
| `umh/registry/query.py` | query_registry(), find_capabilities/adapters/backends/environments/policies/workstation_modes(), get_registry_item(), explain_registry_match() |
| `umh/registry/views.py` | RegistryItemView, RegistryCatalogView, RegistryHealthView, builder functions |

## Files Modified (2)

| File | Change |
|------|--------|
| `umh/control/api.py` | 12 read-only registry endpoints under `/registry/` |
| `umh/control/cli.py` | 10 registry CLI handlers, 10 parser entries, 9 dispatch entries |

## API Endpoints Added

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/registry/catalog` | Full registry catalog |
| GET | `/registry/overview` | Catalog summary view |
| GET | `/registry/health` | Registry health status |
| GET | `/registry/query` | Filtered query with type/name/capability/environment/tag/status/risk filters |
| GET | `/registry/items/{item_id}` | Single item detail |
| GET | `/registry/capabilities` | List capabilities (env/risk filters) |
| GET | `/registry/adapters` | List adapters (capability/env filters) |
| GET | `/registry/backends` | List backends (env filter) |
| GET | `/registry/environments` | List environments (capability filter) |
| GET | `/registry/modes` | List workstation modes |
| GET | `/registry/policies` | List governance policies |

## CLI Commands Added

| Command | Purpose |
|---------|---------|
| `registry-catalog` | Full registry catalog |
| `registry-overview` | Catalog summary view |
| `registry-health` | Registry health status |
| `registry-query` | Filtered query with all filters |
| `registry-item` | Single item by ID |
| `registry-capabilities` | List capabilities |
| `registry-environments` | List environments |
| `registry-modes` | List workstation modes |
| `registry-policies` | List governance policies |

## Discovered Items (29 at build time)

| Type | Count | Source |
|------|-------|--------|
| Capability | 9 | umh.capabilities.definitions |
| Environment | 7 | umh.environments.definitions |
| Backend | 3 | umh.execution.backend_registry |
| Workstation Mode | 9 | umh.workstation.modes |
| Policy | 1 | umh.governance.authority |
| Adapter | 0 | (requires adapter_backend instance) |

## Design Decisions

1. **Read-only by design**: All registry modules are stateless readers. No mutations, no executions, no adapter calls.
2. **Compatibility bridges**: Convert existing frozen dataclasses to RegistryItems without modifying source modules.
3. **Sparse-safe**: Missing sources produce empty lists with warnings, not crashes.
4. **Universal envelope**: RegistryItem is the same shape for all 16 resource types — UI can display heterogeneous resources in one list/search.
5. **16 registry types prepared for future**: CAPABILITY, ADAPTER, BACKEND, ENVIRONMENT, POLICY, MODEL, TOOL, TEMPLATE, LIBRARY, WORKSTATION_MODE, RESOURCE, LEVERAGE, METRIC, SCHEMA, WORKFLOW, UNKNOWN. No scoring for future types.
6. **Query limit clamped to 100**: Consistent with observability layer convention.
7. **explain_registry_match**: Evidence-derived match reasons, no causal claims.
8. **No adapter items without instance**: adapter_pack_to_registry_items() requires the actual AdapterExecutionBackend instance. Returns empty if None.
9. **Policy bridge reads active policy**: Discovers the currently registered governance policy at query time.

## Test Coverage (112 tests)

| Class | Tests | Coverage |
|-------|-------|----------|
| TestRegistryType | 4 | Enum count, normalization, all lowercase |
| TestRegistryItemStatus | 2 | Enum count, normalization |
| TestRegistryAuthorityRequirement | 2 | Enum count, normalization |
| TestRegistryItem | 4 | Serialization, from_dict, missing fields, no secrets |
| TestRegistryQuery | 3 | Limit clamping, min, default |
| TestRegistryQueryResult | 2 | Serialization, empty |
| TestCapabilityBridge | 4 | Converts 9, field values, empty, authority mapping |
| TestEnvironmentBridge | 3 | Converts 7, field values, empty |
| TestAdapterBridge | 2 | None → empty, mock backend |
| TestBackendBridge | 3 | Default backends, field values, None → global |
| TestModeBridge | 3 | Converts 9, field values, None → default |
| TestPolicyBridge | 1 | Discovers default |
| TestRegistryCatalog | 14 | Build, by_type/name/id, count, empty, sparse, generated_at |
| TestRegistryQuery | 12 | All filter types, combined, no results, serialization |
| TestTypedFinders | 13 | All finders, by params, get_item |
| TestExplainRegistryMatch | 3 | Type, multi, no match |
| TestRegistryItemView | 3 | From item, serialization, truncation |
| TestRegistryCatalogView | 3 | Default, serialization, empty |
| TestRegistryHealthView | 3 | Default, serialization, empty |
| TestControlAPIFunctions | 10 | All endpoints callable, read-only |
| TestCLICommands | 4 | Parser accepts, query args, item args, dispatch |
| TestLayeringInvariants | 7 | Forbidden imports, no stores, no execution, no mutation, no secrets |
| TestPhase79Compatibility | 5 | All Phase 79 exports, endpoints, CLI commands |
| TestEdgeCases | 5 | Broken adapter, empty catalog, all-filter-miss, round-trip, independence |

## Known Limitations

- No adapter items without passing adapter_backend instance
- No live adapter health checks (would require executing adapters)
- No registry persistence (rebuilt each query from definitions)
- No scoring for RESOURCE/LEVERAGE/METRIC/SCHEMA/WORKFLOW types
- No deduplication across bridges (e.g., same environment appears in both environment and backend items)
- No frontend UI yet
- No cache layer for catalog (fast enough for MVP — sub-millisecond builds)

## Is Phase 81 Safe?

Yes. Phase 80 is purely additive:
- 6 new files, 2 modified files
- All registry modules are read-only
- No execution/governance/routing behavior changes
- No adapter calls from new modules
- No trace/outcome/feedback mutation
- No existing module modified or broken
- All 610 tests pass (112 + 498 regression)
- The system now has unified resource discovery without being more dangerous
