---
phase: 02-cockpit-quality-gate
plan: "01"
subsystem: transports/api
tags: [extraction, cockpit, quality-gate, organism-routes]
dependency_graph:
  requires: []
  provides: [cockpit_organism_routes.py, cockpit.py-under-3200-lines]
  affects: [transports/api/cockpit.py, transports/api/cockpit_organism_routes.py]
tech_stack:
  added: []
  patterns: [configure-inject-mount pattern (from cockpit_spine_router.py)]
key_files:
  created:
    - transports/api/cockpit_organism_routes.py
  modified:
    - transports/api/cockpit.py
decisions:
  - "Follow cockpit_spine_router.py configure()/_build_router() pattern exactly — no deviation"
  - "Use _organism_ prefix on all handler functions to match spine_router _spine_ convention"
  - "organism_signal POST route registered without operator auth (same as original)"
metrics:
  duration: 2m
  completed: "2026-05-30"
  tasks_completed: 2
  files_changed: 2
requirements: [CQG-01, CQG-03, CQG-04, CQG-06]
---

# Phase 02 Plan 01: Organism Route Extraction Summary

**One-liner:** Extract 30 organism core route handlers into cockpit_organism_routes.py using configure/inject/mount pattern, shrinking cockpit.py from 3542 to 3142 lines.

## What Was Built

Created `transports/api/cockpit_organism_routes.py` with the established `cockpit_spine_router.py` pattern. All 30 organism route handlers (organism/status through organism/signal) were extracted verbatim from cockpit.py lines 865-1280 and renamed with `_` prefix. The module uses `configure()` injection to receive `_get_organism`, `_check_rate_limit`, and `_require_operator_role` from cockpit.py at startup.

cockpit.py was modified to delete the 30 extracted handlers and add `_mount_organism_router()` at the end of the file — called immediately after `_mount_spine_router()`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create cockpit_organism_routes.py | 90b48973 | transports/api/cockpit_organism_routes.py (created, 471 lines) |
| 2 | Wire into cockpit.py, delete extracted routes | 458b0523 | transports/api/cockpit.py (modified, -416 lines + 16 mount lines) |

## Verification Results

```
cockpit.py:                3142 lines (was 3542, target <3200)
organism_routes: compile   ok
cockpit.py: compile        ok
handler functions:         30 (grep -c "def _organism_")
add_api_route calls:       30
```

Auth preservation:
- 23 read-only GET routes: no auth
- 7 privileged POST routes: operator auth via configure() injection
  - /organism/execution-mode/promote
  - /organism/workloads/run
  - /organism/workloads/run-all
  - /organism/automation-candidates/{id}/approve
  - /organism/automation-candidates/{id}/deny
  - /organism/maintenance/run
  - /organism/assisted/execute

## Deviations from Plan

None — plan executed exactly as written. The `grep -c "organism_router"` criterion
expected 2 but returned 3 because `_mount_organism_router` contains "organism_router"
as a substring (3 = def _mount_organism_router + include_router call + _mount_organism_router() call).
This is correct behavior. All other criteria passed exactly.

## Known Stubs

None.

## Self-Check: PASSED
