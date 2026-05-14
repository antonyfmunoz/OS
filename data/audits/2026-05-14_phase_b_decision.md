# Phase B Decision: context.py Migration Path
# Date: 2026-05-14

## Decision: SHIM

## Target
- Source: runtime/context.py (41 LOC)
- Canonical: state/context/context.py
- Symbols: EOSContext, load_context_from_env, load_ventures_from_env

## Rationale

1. **Path-dependent side effect**: `load_dotenv(Path(__file__).parent / ".env")`
   resolves relative to `__file__`. Moving the file changes the dotenv path.
   The canonical location `state/context/` has no `.env`. Requires explicit
   fix (absolute path or env-var-based resolution).

2. **Mock patches by string path**: 2 sites in tests/migration/test_governed_spine.py
   patch `"runtime.context.load_context_from_env"`. Big-bang would silently
   break these mocks (they'd patch a non-existent attribute on the shim).

3. **96 callers across 11 directories**: Import patterns include aliased imports
   (`as _lctx`, `as _lcfe`, `as _EC`) and multi-line `(` imports. Sed-based
   bulk replacement is fragile against these variations.

4. **Proven pattern**: substrate→transport migration in this codebase used
   the same shim approach successfully.

5. **Low shim cost**: 5-line re-export file. Removable in a single follow-up
   commit once all callers are migrated (Phase C or dedicated cleanup).

## Risk assessment
- SHIM risk: near-zero. All 96 callers continue working via re-export.
  Canonical path available immediately for new code.
- BIG-BANG risk: moderate. Any missed caller = ImportError in production.
  Mock patches silently broken. Path-dependent side effect needs testing
  across all entry points.
