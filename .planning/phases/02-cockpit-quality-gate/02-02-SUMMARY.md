---
phase: 02-cockpit-quality-gate
plan: "02"
subsystem: api
tags: [fastapi, extraction, cockpit, entity-routes, product-routes]

# Dependency graph
requires:
  - phase: 02-01
    provides: cockpit_organism_routes.py with configure/inject/mount pattern; cockpit.py at 3142 lines
provides:
  - cockpit_entity_routes.py with 9 entity/product route handlers and configure() injection
  - cockpit.py shrunk from 3142 to 2874 lines (-268 lines)
  - entity and product routes preserved at /api/umh/entities/* and /api/umh/products/*
affects: [02-03, cockpit-quality-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "configure(get_org_id_fn, require_operator_dep) injection pattern for extracted cockpit modules"
    - "_mount_entity_router() appended after _mount_organism_router() at bottom of cockpit.py"

key-files:
  created:
    - transports/api/cockpit_entity_routes.py
  modified:
    - transports/api/cockpit.py

key-decisions:
  - "No operator auth added to upsert_company or refresh_product_connections — preserved exactly from original cockpit.py"
  - "Entity router uses only get_org_id_fn + require_operator_dep (no check_rate_limit_fn needed — no rate-limited routes in entity block)"

patterns-established:
  - "Pattern: entity module configure() takes only the dependencies it needs — no cargo-culting from spine_router"

requirements-completed: [CQG-01, CQG-03, CQG-04, CQG-06]

# Metrics
duration: 3min
completed: 2026-05-30
---

# Phase 02 Plan 02: Cockpit Entity Routes Extraction Summary

**9 entity/product route handlers extracted from cockpit.py into cockpit_entity_routes.py, shrinking cockpit.py from 3142 to 2874 lines via configure()/include_router() injection pattern**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-30T00:20:13Z
- **Completed:** 2026-05-30T00:22:39Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created cockpit_entity_routes.py with 9 route handlers (portfolio, departments, departments/{slug}, roles, companies GET/POST, companies/{company_id}, products, products/refresh)
- Wired cockpit_entity_routes into cockpit.py via _mount_entity_router() following the same pattern as _mount_organism_router()
- cockpit.py reduced from 3142 to 2874 lines — combined with Plan 01 (3542→3142) total reduction is now 668 lines
- Auth preserved exactly: upsert_company and refresh_product_connections have no operator auth in original, none added

## Task Commits

Each task was committed atomically:

1. **Task 1: Create cockpit_entity_routes.py** - `bb54a447` (feat)
2. **Task 2: Wire cockpit_entity_routes into cockpit.py** - `b9ef4425` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `transports/api/cockpit_entity_routes.py` - Entity/product routes module: configure(), entity_router, 9 handlers
- `transports/api/cockpit.py` - Removed 280-line entity/product block, added _mount_entity_router()

## Decisions Made
- No operator auth added to upsert_company or refresh_product_connections — original had none, none added
- configure() takes only get_org_id_fn + require_operator_dep (not check_rate_limit_fn like spine/organism) since no rate-limited routes exist in this module

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- cockpit.py is now 2874 lines (was 3542 before Phase 2 started)
- Plan 03 is the final extraction needed to clear the 3000-line quality gate
- After Plan 03: cockpit.py should be under 3000 lines, closing the quality gate blocker

---
*Phase: 02-cockpit-quality-gate*
*Completed: 2026-05-30*
