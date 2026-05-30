---
phase: 02-cockpit-quality-gate
plan: "03"
subsystem: api
tags: [fastapi, extraction, cockpit, economy-routes, autonomous-routes, quality-gate]

dependency_graph:
  requires:
    - phase: 02-01
      provides: cockpit_organism_routes.py; cockpit.py at 3142 lines
    - phase: 02-02
      provides: cockpit_entity_routes.py; cockpit.py at 2874 lines
  provides:
    - cockpit_economy_routes.py with 21 economy/recursion/advisor/assimilation/topology/reconciliation route handlers
    - cockpit_autonomous_routes.py with 17 autonomous PR factory + cadence route handlers
    - cockpit.py final: 2247 lines (under 3000-line CQG-02 quality gate)
  affects: [cockpit-quality-gate-closure, CQG-02]

tech_stack:
  added: []
  patterns:
    - "configure(get_organism_fn, require_operator_dep) injection without check_rate_limit_fn — only inject what you need"
    - "_mount_economy_router() + _mount_autonomous_router() appended after _mount_entity_router() in cockpit.py"
    - "_get_pr_factory() helper copied verbatim into cockpit_autonomous_routes.py as module-level function using injected _get_organism"

key_files:
  created:
    - transports/api/cockpit_economy_routes.py
    - transports/api/cockpit_autonomous_routes.py
  modified:
    - transports/api/cockpit.py

decisions:
  - "configure() for economy and autonomous modules takes only get_organism_fn + require_operator_dep (no check_rate_limit_fn) — no economy/autonomous routes use rate limiting"
  - "re module imported at module-level as _re in cockpit_autonomous_routes.py (not inline per-handler) — used in 3 path traversal checks, cleaner to lift to module scope"
  - "glob/time/Path/json/os imported at module-level in cockpit_autonomous_routes.py — all used in handlers, consistent with Python best practice"
  - "Route count delta verified: 38 routes moved (21+17), cockpit.py lost exactly 38 @router. decorators (105 → 67)"

metrics:
  duration: 5min
  completed: "2026-05-30"
  tasks_completed: 3
  files_changed: 3
---

# Phase 02 Plan 03: Cockpit Economy + Autonomous Routes Extraction Summary

**21 economy/recursion/advisor/topology routes and 17 autonomous PR factory + cadence routes extracted from cockpit.py into two new modules, closing the CQG-02 quality gate with cockpit.py at 2247 lines (under 3000)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-30T00:24:46Z
- **Completed:** 2026-05-30T00:29:15Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `transports/api/cockpit_economy_routes.py` — 21 route handlers covering organism economy, recursion governance, advisor hierarchy, assimilation, snapshot, runtimes, governor, workcells, topology (static + live), throughput, and reconciliation. 3 privileged (POST) routes carry operator auth, 18 are read-only GET.
- Created `transports/api/cockpit_autonomous_routes.py` — 17 route handlers covering the autonomous PR factory (status, sandboxes, manifests, create-pr, cleanup, parallel-dry-run, production-truth, verify-merge, merge-verifications, cleanup-eligible) and cadence scheduler (status, dry-run, set-mode). 11 routes carry operator auth, 6 are read-only GET. Includes `_get_pr_factory()` helper and `is_relative_to()` path traversal guards copied verbatim.
- Modified `cockpit.py`: deleted economy block (lines 1898-2272) and autonomous block (lines 2273-2546), appended `_mount_economy_router()` and `_mount_autonomous_router()` with their call sites. cockpit.py went from 2874 → 2247 lines.
- **CQG-02 CLOSED**: cockpit.py at 2247 lines, well under the 3000-line gate.
- All 5 sub-routers now mounted in cockpit.py: spine, organism, entity, economy, autonomous.
- WebSocket endpoint (`cockpit_ws`) untouched at line 1720.
- Zero endpoint count change: 38 routes moved from cockpit.py (105 → 67 @router. decorators), 21+17=38 registered in new modules. Total across all 6 files: 174 routes (unchanged from pre-plan-03 total).

## Route File Summary (final state after Phase 02)

| File | Routes | Scope |
|------|--------|-------|
| cockpit.py | 67 + 1 ws | Core cockpit, dev session, loops, execution, chat, config, mesh, analytics |
| cockpit_spine_router.py | 30 | GovernedExecutionSpine, Journal, MutationRegistry, SpineGuard, autonomous gateway |
| cockpit_organism_routes.py | 30 | Organism core (status, agents, deliverables, events, tick, leverage, metrics, bottlenecks) |
| cockpit_entity_routes.py | 9 | Portfolio, departments, roles, companies, products |
| cockpit_economy_routes.py | 21 | Economy, recursion, advisors, assimilation, snapshot, runtimes, governor, workcells, topology, throughput, reconciliation |
| cockpit_autonomous_routes.py | 17 | Autonomous PR factory, cadence scheduler |
| **Total** | **174** | |

## Deviations from Plan

None — plan executed exactly as written.

The plan's "145 total handlers" figure was a planning estimate. Actual measured count at plan creation time was 174 (105 in cockpit.py + 30 spine + 30 organism + 9 entity). The zero-endpoint-delta constraint was verified correctly: 38 routes moved out of cockpit.py (105 → 67), 38 added to new modules (21+17). Total preserved.

## Known Stubs

None. All extracted route handlers contain real implementation bodies copied verbatim from cockpit.py. No placeholder logic introduced.

## Self-Check: PASSED

- transports/api/cockpit_economy_routes.py: FOUND
- transports/api/cockpit_autonomous_routes.py: FOUND
- .planning/phases/02-cockpit-quality-gate/02-03-SUMMARY.md: FOUND
- commit a0843603: FOUND
- commit 3d313e62: FOUND
- commit 0fdaf0fa: FOUND
- cockpit.py compile: OK
- cockpit_economy_routes.py compile: OK
- cockpit_autonomous_routes.py compile: OK
- cockpit.py line count: 2247 (under 3000 CQG-02 gate)
