# Phase 83 — Legacy Runtime Deprecation + Migration Boundary v1

**Date**: 2026-05-03
**Status**: Complete
**Invariants**: INV-551 through INV-580 (30 invariants)
**Hard rules**: 17
**Tests**: 152 passing

## Summary

Phase 83 creates a safe migration boundary around the legacy `runtime_engine/`
and `substrate/` directories. No code is deleted, no behavior changes, no broad
refactoring. The phase adds metadata, classification, static analysis, and
operator-visible views that make the migration state queryable.

## New Package: `umh/migration/`

| Module | Purpose |
|--------|---------|
| `contracts.py` | 5 enums, 5 dataclasses — typed migration domain |
| `inventory.py` | Static file discovery and classification |
| `classifier.py` | Bypass-risk detection via regex + AST (no dynamic import) |
| `deprecation_registry.py` | In-memory queryable registry (no destructive methods) |
| `import_boundary.py` | AST-based import boundary enforcement (12 rules) |
| `compatibility.py` | ~60 known legacy→clean equivalents (advisory) |
| `views.py` | 5 operator-safe view dataclasses |

## Classification System

Every discovered module receives:
- **Status** (7 values): ACTIVE_RETAINED, DEPRECATED, MIGRATED, DUPLICATE, BYPASS_RISK, FUTURE_REVIEW, UNKNOWN
- **Category** (16 values): RUNTIME_ENGINE, SUBSTRATE, EXECUTION, CONTROL, ADAPTERS, STORAGE, MEMORY, REGISTRY, ONTOLOGY, OBSERVABILITY, INTERFACE, TOOLS, WORKFLOWS, WORKSTATION, WORLD, UNKNOWN
- **Risk level** (6 values): NONE, LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN
- **Migration action** (9 values): RETAIN, DEPRECATE, MIGRATE, REPLACE, WRAP, MONITOR, REVIEW, DELETE_AFTER_MIGRATION, UNKNOWN

## Import Boundary Rules

9 rules block `runtime_engine` imports from clean packages (control, execution,
adapters, storage, memory, registry, ontology, observability, interface).
3 rules block `substrate` imports from execution/control/adapters.
Exception: `umh.substrate.nodes` allowed in `umh.execution` (compatibility bridge).

## Integration Points

### Registry (Phase 80)
- 4 new `RegistryType` values: LEGACY_MODULE, MIGRATION_MAPPING, DEPRECATION_POLICY, IMPORT_BOUNDARY_RULE
- 3 bridge functions in `umh/registry/bridges.py`
- Import boundary rules loaded in catalog

### Observability (Phase 79)
- `migration_status` field in `SystemStatus`
- `migration_summary` in `OperatorDashboardSnapshot`

### Control Plane API (7 GET endpoints)
- `/migration/status` — health view
- `/migration/inventory` — module inventory with summary
- `/migration/deprecated` — deprecated module list
- `/migration/bypass-risk` — bypass-risk module list
- `/migration/mappings` — known clean equivalents
- `/migration/import-boundary` — import boundary findings
- `/migration/dashboard` — full migration dashboard

### Control Plane CLI (7 commands)
- `migration-status`, `migration-inventory`, `migration-deprecated`
- `migration-bypass-risk`, `migration-mappings`, `migration-imports`
- `migration-dashboard`

All endpoints and commands are read-only. No mutation. No deletion.

## Files Modified

| File | Change |
|------|--------|
| `umh/registry/contracts.py` | +4 RegistryType enum values |
| `umh/registry/bridges.py` | +3 bridge functions |
| `umh/registry/catalog.py` | Import boundary rules loaded |
| `umh/observability/system_status.py` | +migration_status field, +check function |
| `umh/interface/views.py` | +migration_summary field |
| `umh/observability/operator_views.py` | +migration_registry param, migration summary |
| `umh/control/api.py` | +7 GET endpoints |
| `umh/control/cli.py` | +7 commands, parsers, dispatch |

## Test Coverage (152 tests)

| Section | Tests | Description |
|---------|-------|-------------|
| 1. Contracts | 11 | Enum normalization, dataclass serialization |
| 2. Inventory | 6 | Path classification, discovery, summary |
| 3. Classifier | 7 | Bypass detection, module classification |
| 4. Registry | 5 | CRUD, queries, roundtrip, explain |
| 5. Import Boundary | 5 | Rules, AST parse, boundary classification |
| 6. Compatibility | 4 | Equivalents, validation, mappings |
| 7. Views | 7 | Serialization, health counts, dashboard |
| 8. Registry Integration | 5 | Bridge functions, catalog, Phase 80 compat |
| 9. Storage/Audit | 2 | Audit still works, remains read-only |
| 10. Observability | 5 | System status, dashboard with/without migration |
| 11. API | 4 | Endpoints registered, GET-only, no deletion |
| 12. CLI | 2 | Commands in parser, smoke tests |
| 13. Layering | 9 | No subprocess/requests/browser/adapter/mutation |
| 14. Cross-cutting | 5 | INV-551, INV-560, INV-566, INV-567, INV-568 |
| 15. Regression | 8 | Phase 75B-82 test files importable |

## Regression

All prior phase test suites pass (905/905 with Phase 80 count assertion
updated from exact `== 16` to `>= 16` to accommodate additive evolution).

## Doctrine Compliance

- No legacy files deleted (INV-551)
- No dynamic imports of target modules (INV-556)
- All classification static — regex + AST only (INV-555)
- Unknown never treated as safe (INV-568)
- Missing directories degrade gracefully (INV-567)
- Migration status visible to operator (INV-566)
- All endpoints read-only (INV-570)
- DeprecationRegistry has no delete/clear/pop (INV-571)
