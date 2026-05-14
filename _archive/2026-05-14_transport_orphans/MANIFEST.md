# Transport Orphan Archive — 2026-05-14

## Reason

These modules from `runtime/transport/` have zero external callers
(or only non-production callers in scripts/tests). They were
transitively loaded by the eager-import `__init__.py` before the
PEP 562 lazy-import rewrite (Wave 0.5). Post-rewrite + Phase C,
they have no consumers.

## Classification

Full classification: `data/audits/2026-05-14_transport_orphan_classification.md`

| Category | Count |
|----------|-------|
| TRUE_ORPHAN (no init registration) | 73 |
| TRUE_ORPHAN (init-registered, registrations removed) | 32 |
| SCRIPT_ONLY callers (non-production) | 39 |
| TEST_ONLY callers (non-production) | 4 |
| **Total archived** | **148** |

## Verification

Every module confirmed 0 production callers via:
```
grep -rlE "from runtime\.transport\.<module>\b|import runtime\.transport\.<module>\b" \
  --include="*.py" --exclude-dir=_archive --exclude-dir=__pycache__ . \
  | grep -v "runtime/transport/"
```

SCRIPT_ONLY/TEST_ONLY modules have callers only in scripts/ or tests/
(smoke tests, diagnostics, test fixtures) — not production code.

## Init cleanup

32 init-registered orphans had their `_m()`/`_d()` registrations
removed from `runtime/transport/__init__.py`. The remaining 22
registrations serve the 15 production-caller modules.
