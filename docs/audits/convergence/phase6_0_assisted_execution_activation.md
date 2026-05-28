# Phase 6.0 — Assisted Execution Activation + Cockpit-Governed Actions

**Date:** 2026-05-27
**Status:** COMPLETE
**Deployed commit:** `42abc247` (security hardening + fail-closed auth)

## Summary

Phase 6.0 proves the organism can safely act, not just observe.
The system promoted from OBSERVE → RECOMMEND (auto, 80% reliability)
→ ASSISTED (operator promotion), executed its first approved maintenance
action end-to-end, and recorded the full lifecycle through audit trail,
leverage metrics, and EventSpine.

## Production Restart Proof

```
docker compose up -d os-operator
# psutil installed in container (missing from image)
# UMH_ALLOW_INSECURE=true added to services/.env (Tailscale-only VPS)
```

Startup log confirms:
- `organism daemon started: 3 agents, graph=True, supervisor=True, tick_stages=15`
- `cockpit router mounted at /api/umh/`
- `organism EventSpine → cockpit WS bridge wired`

## Mode Promotion Proof

| Transition | From | To | Trigger | Justification |
|-----------|------|-----|---------|---------------|
| Auto | observe | recommend | reliability_threshold | reliability 0.80 >= 0.8 |
| Operator | recommend | assisted | operator_promotion | Phase 6.0 activation: gates clean, 470 tests passing, security hardened |

Current mode: **ASSISTED** with 2 transitions recorded.

## OBSERVE Workload Cycle Results

| Workload | Status | Duration | Key Finding |
|----------|--------|----------|-------------|
| repo_health | OK | 0.14s | 6,683 uncommitted files, branch main |
| stale_branch_scan | OK | 0.01s | 2 non-main branches, 2 worktrees |
| docker_health | FAIL | 0.0s | docker socket not available inside container |
| disk_pressure | OK | 0.15s | 76.9% used, pressure=elevated |
| memory_pressure | OK | 0.0s | 37.0% used, pressure=normal |
| knowledge_staleness | OK | 0.0s | 273 files, 0 stale |
| runtime_reconciliation | BLOCKED | 0.0s | Correctly governance-blocked (MEDIUM risk) |

- **5/7 workloads succeeded**
- **1 correctly governance-blocked** (MEDIUM risk requires ASSISTED)
- **1 infrastructure limitation** (docker CLI not in container)

## Maintenance Recommendations

2 maintenance cycles executed. Findings collected:
- Elevated disk pressure (76.9%)
- 6,683 uncommitted files (data/runtime generated files)
- 2 worktree branches still active

No automated recommendations generated (threshold conditions not triggered).

## Assisted Actions Executed

| Action | Category | Result | Duration | Output |
|--------|----------|--------|----------|--------|
| runtime_refresh | runtime_refresh | FAILED | 0.0s | docker CLI not in container |
| test_suite | test_suite | FAILED | 0.02s | pytest not in container |
| **disk_cleanup** | **disk_cleanup** | **SUCCESS** | **1.1s** | **Cleaned 298 __pycache__ directories** |
| log_rotation | log_rotation | SUCCESS | 0.13s | 0 files needed rotation |

**First successful assisted execution: disk_cleanup cleaned 298 __pycache__ directories in 1.1 seconds.**

## Verification Result

- No production service degraded after execution
- Docker containers running normally: `os-operator`, `os-discord`, `os-cockpit`
- All cockpit endpoints returning 200

## Leverage Metrics

| Metric | Value |
|--------|-------|
| Total tasks tracked | 22 |
| Operator seconds saved | 2,247.9s (~37 minutes) |
| Approvals required | 4 |
| Composite leverage score | 0.5543 |
| Time compression | 0.999 |
| Operational reliability | 77.3% |
| Economic efficiency | 1.0 |

## Audit Trail Evidence

4 actions in AssistedExecutor audit trail, all with:
- `approved_by: operator:172.20.0.1`
- Full timestamps (started_at, completed_at)
- Duration measurements
- Reversibility flag = true

EventSpine events:
- 2 `execution_mode_changed` events
- 8 `assisted_action_started` / `assisted_action_completed` events
- Multiple `workload_started` / `workload_completed` events
- 1 `maintenance_cycle_completed` event

## Cockpit Endpoint Status

All Phase 5.9 endpoints verified via Tailscale (100.77.233.50:8091):

| Endpoint | HTTP | Result |
|----------|------|--------|
| GET /organism/workloads | 200 | 19 runs, 79% success |
| GET /organism/workloads/outcomes | 200 | Full outcome history |
| GET /organism/maintenance | 200 | 2 cycles |
| GET /organism/assisted | 200 | 4 executed, 0 blocked |
| GET /organism/assisted/audit | 200 | Full audit trail |
| GET /organism/automation-candidates | 200 | Pipeline status |
| GET /organism/execution-mode | 200 | ASSISTED mode |
| GET /organism/leverage | 200 | 2,247.9s saved |
| GET /organism/bottlenecks | 200 | 8 active (slow_runtime defaults) |
| GET /organism/events | 200 | EventSpine stream |

Public DNS (universalmetaharness.tech) not reachable — all verification via Tailscale.

## Security Hardening (applied during Phase 6.0)

1. **Fail-closed auth**: `_require_api_key` and `_require_operator_role` return 503
   when tokens are unconfigured, unless `UMH_ALLOW_INSECURE=true`
2. **Uniform rate limiting**: `_check_rate_limit()` applied to promote (60s),
   execute (30s), and approve (30s) endpoints
3. **Operator-token separation**: Privileged endpoints require `X-Operator-Token`
   header beyond the standard `X-API-Key`
4. **Argument injection prevention**: Allowlists on test paths, container names,
   `--` separators in subprocess argv

## Test Results

- **470 organism tests** — all passing
- Type divergence gate — clean (1 pre-existing intentional distinction)
- Instance leak gate — clean (533 files scanned)
- Dependency direction — clean (pre-existing abstract ports only)
- Compile check — clean

## Remaining Blockers

1. **Docker CLI in container**: `docker_health`, `runtime_refresh`, and
   `container_restart` actions require docker socket mount. Not a security
   decision to change without explicit approval.
2. **pytest in container**: `test_suite` action requires pytest installed.
   Low priority — tests run in CI and development, not production container.
3. **Public DNS**: universalmetaharness.tech still not reachable.
4. **Operator token**: `UMH_OPERATOR_TOKEN` not configured — running in
   insecure mode behind Tailscale. Before any public exposure, generate
   and set proper tokens.

## Next Highest-Leverage Frontier

Phase 6.1: Earn AUTONOMOUS promotion through sustained reliability.
- Track success rate across 50+ assisted actions
- Auto-promote to AUTONOMOUS at 95% reliability
- Enable policy-controlled autonomous execution for LOW-risk actions
- Wire docker socket for container health monitoring (requires compose change)
