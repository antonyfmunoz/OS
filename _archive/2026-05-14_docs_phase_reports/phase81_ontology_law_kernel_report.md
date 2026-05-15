# Phase 81: Reality-Derived Universal Ontology + Law Kernel v1

**Status**: Complete
**Date**: 2026-05-03
**Invariants**: 491-520 (30 invariants)
**Hard Rules**: 17

## Summary

Phase 81 introduces a typed, reality-derived ontology layer to UMH. The kernel
encodes 16 universal primitives, 14 universal laws, 5 domain projection sets,
and 6 correspondence maps. All modules are read-only, advisory, deterministic,
and serializable. No execution, mutation, adapter calls, or LLM calls.

## Modules Created

| Module | Purpose |
|--------|---------|
| `umh/ontology/__init__.py` | Package init |
| `umh/ontology/primitives.py` | 20 PrimitiveTypes, 16 universal primitives, projections, instances |
| `umh/ontology/laws.py` | 13 LawTypes, 14 universal laws, domain law projections, classification |
| `umh/ontology/abstraction.py` | 13 abstraction layers, nodes, paths, ordering |
| `umh/ontology/domain_projection.py` | 14 DomainTypes, 5 projection sets (business, software, human, content, UMH) |
| `umh/ontology/correspondence.py` | 6 correspondence maps with explicit analogy breaks |
| `umh/ontology/law_application.py` | Advisory law application to context strings |
| `umh/ontology/validation.py` | Kernel validation: primitives, laws, projections, full kernel |
| `umh/ontology/views.py` | UI-safe read models for all ontology data |

## Modules Modified

| Module | Change |
|--------|--------|
| `umh/registry/contracts.py` | +5 RegistryType values (PRIMITIVE, LAW, DOMAIN_PROJECTION, CORRESPONDENCE_MAP, ONTOLOGY) |
| `umh/registry/bridges.py` | +4 bridge functions for ontology items |
| `umh/registry/catalog.py` | +4 try/except blocks loading ontology bridges |
| `umh/control/api.py` | +8 GET endpoints under /ontology |
| `umh/control/cli.py` | +6 commands (ontology-status, -primitives, -laws, -projections, -correspondence, -validate) |
| `umh/observability/system_status.py` | +check_ontology_kernel(), +ontology_kernel_status field |
| `umh/observability/operator_views.py` | +ontology_summary in dashboard snapshot |
| `umh/interface/views.py` | +ontology_summary field on OperatorDashboardSnapshot |

## Key Design Decisions

1. **Primitives are NOT domain-specific.** All 16 defaults have `scope=UNIVERSAL`.
   Domain expressions are projections that point back to universal IDs.

2. **Laws declare failure conditions.** Every universal law has explicit
   `failure_conditions` — this is validated and enforced.

3. **Correspondence maps declare analogy breaks.** No mapping is assumed valid.
   Each map lists where the analogy fails.

4. **Law application is advisory.** `apply_law_to_context()` returns analysis,
   never mutates or triggers execution.

5. **Validation is explicit.** `validate_ontology_kernel()` takes explicit args,
   never auto-loads to prevent hidden coupling.

## Counts

- 16 universal primitives
- 14 universal laws
- 5 domain projection sets (25 primitive projections, ~20 law projections)
- 6 correspondence maps
- 8 API endpoints
- 6 CLI commands
- 156 tests (all passing)

## Verification

```bash
python3 -m pytest tests/test_phase81_ontology_law_kernel.py -v  # 156 passed
python3 -m umh.control.cli ontology-status --json                # kernel view
python3 -m umh.control.cli ontology-validate --json              # valid=true, 0 issues
```

## What This Prepares

The ontology kernel is infrastructure for future phases:
- World modeling (applying primitives to real contexts)
- Composition (combining laws for multi-law analysis)
- Simulation (projecting law effects forward)
- Self-recursion (UMH modeling itself via UMH_INTERNAL domain)

None of these are implemented in Phase 81. The kernel provides the typed
foundation they will build on.
