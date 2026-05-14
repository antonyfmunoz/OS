# Transport Orphan Archive — 2026-05-14

## Reason

These modules from `runtime/transport/` have zero external callers
AND are not transitively required by any production-reachable module.
They were transitively loaded by the eager-import `__init__.py` before
the PEP 562 lazy-import rewrite (Wave 0.5). Post-rewrite + Phase C,
they have no consumers.

## Classification

Full classification: `data/audits/2026-05-14_transport_orphan_classification.md`

| Category | Count |
|----------|-------|
| TRUE_ORPHAN (zero deps from PROD) | 95 |
| Test files (tested archived modules) | 5 |
| **Total archived** | **100** |

Initial attempt archived 148 modules. Transitive closure analysis
revealed 53 had hard import-time dependencies from the 15 PROD modules.
All 53 restored. Final archive: 95 transport modules + 5 test files.

## Verification

Every module confirmed either:
1. Zero external callers, OR
2. Only script/test callers AND not transitively imported by PROD modules

AST-based transitive closure verified 15 PROD modules import cleanly
after archive (15/15 production smoke).

## Init cleanup

`__init__.py` trimmed from 474 → 62 lines. 54 → 4 registered modules.
All `_d()` deferred registrations removed (orphans + phantom files).
Remaining: `storage`, `capability_tagging`, `station_daemon`, `station_helpers`.
