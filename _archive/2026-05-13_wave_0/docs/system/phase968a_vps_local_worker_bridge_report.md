# Phase 96.8A Report: VPS ↔ Local Worker Bridge + Agent OS Control Plane v1

**Date:** 2026-05-05
**Status:** COMPLETE
**Updated:** 96.8A.1 — External Boundary Law classification added

## Adapter Boundary Classification (added 96.8A.1)

Phase 96.8A is an **Environment Adapter / Bridge Adapter** implementation
inside the Adapter Engine. It exists because the UMH External Boundary
Law requires that all environment transitions pass through governed
adapter boundaries. The local worker bridge is part of the Adapter
Engine, not separate infrastructure. Work packets are governed external
interaction contracts. Local worker execution crosses the UMH external
boundary. All local GUI, Chrome, tmux, and shell interactions require
environment adapters.

## Mission

Build a durable, always-on bridge between VPS orchestrator and local
Windows worker. Primary mode: pull-based (local worker polls VPS
outbox). Infrastructure only — no live execution of W0-001 CU.

## Deliverables

### Code Modules (9/9 complete)

| Module | Lines | Purpose |
|--------|-------|---------|
| `work_packet.py` | 179 | Packet contract — status, risk, approval, blocked actions |
| `queue_paths.py` | 102 | Canonical filesystem paths for VPS and local queues |
| `packet_validator.py` | 165 | Pre-execution validation + CU governance (17 blocked actions) |
| `local_pull_protocol.py` | 257 | Pull-based lifecycle — discover, copy, claim, validate, execute, result |
| `result_ingestion.py` | 165 | Result validation — proof, governance, confirmation gates |
| `heartbeat.py` | 138 | File-based worker liveness with staleness detection (60s threshold) |
| `tmux_surface.py` | 137 | Tmux command safety — dangerous command blocking |
| `vps_local_bridge.py` | 145 | Bridge orchestrator — mode selection and status evaluation |
| `bootstrap_plan.py` | 231 | One-time local worker setup plan generation |

Package: `core/environment_bridge/` with `__init__.py`.

### Test Files (8/8 complete, 86 tests)

| Test File | Tests |
|-----------|-------|
| `test_environment_work_packet.py` | 14 |
| `test_environment_packet_validator.py` | 10 |
| `test_local_pull_protocol.py` | 12 |
| `test_result_ingestion.py` | 10 |
| `test_environment_heartbeat.py` | 8 |
| `test_tmux_surface.py` | 11 |
| `test_vps_local_bridge.py` | 8 |
| `test_local_worker_bootstrap_plan.py` | 11 |

**All 86 tests pass. 176 regression tests pass (adapter/CU/TME suites).**

### Work Packet (1/1 complete)

`data/work_queue/outbox/w0_001_cu_rerun_while_present_packet.json`
- Packet ID: WP-W0-001-CU-RERUN-001
- Risk: HIGH, Approval: APPROVED
- 7 allowed actions, 17 blocked actions, 9 proof requirements
- Founder confirmation required

### Documentation (9/9 complete)

| Document | Location |
|----------|----------|
| Environment Bridge Doctrine | `docs/operations/environment_bridge_doctrine_v1.md` |
| VPS-Local Bridge Doctrine | `docs/operations/vps_local_worker_bridge_doctrine_v1.md` |
| Local Pull Protocol | `docs/operations/local_pull_worker_protocol_v1.md` |
| Tmux Execution Surface | `docs/operations/local_tmux_execution_surface_v1.md` |
| Work Packet Contract | `docs/operations/work_packet_contract_v1.md` |
| Governance Policy | `docs/operations/local_worker_governance_policy_v1.md` |
| Bootstrap Instructions | `docs/system/local_worker_bootstrap_instructions_v1.md` |
| W0-001 Next Steps | `docs/system/w0_001_cu_rerun_after_bridge_next_steps.md` |
| Phase Report | `docs/system/phase968a_vps_local_worker_bridge_report.md` |

### Queue Directories Created

```
/opt/OS/data/work_queue/
  ├── outbox/    (w0_001 packet lives here)
  ├── inbox/
  ├── archive/
  ├── heartbeats/
  └── results/
```

## Architecture Decisions

1. **Pull over push** — SSH push blocked by VPS sandbox classifier. Local worker initiates all transport.
2. **File-based transport** — JSON files on filesystem. Auditable, git-friendly, no DB required.
3. **Packet-level governance** — Every packet carries its own blocked_actions and proof_requirements.
4. **17-item CU blocked list** — Enforced for any packet targeting local_windows_gui or local_browser.
5. **Heartbeat liveness** — 60-second staleness threshold. Worker writes, VPS reads.
6. **Tmux dangerous command block** — 12 exact commands + 8 prefix patterns blocked at model layer.
7. **Bootstrap once, run forever** — 4 required steps, 3 optional. After bootstrap, worker is autonomous.

## Test Results

```
Phase 96.8A tests:  86 passed, 0 failed
Regression tests:  176 passed, 0 failed
Total:             262 passed, 0 failed
```

## What Was NOT Done (by design)

- W0-001 CU rerun was NOT executed (infrastructure only)
- No live SSH connections attempted
- No credentials, tokens, or cookies captured
- No mutations to Google Workspace
- No commits or pushes

## Phase 96.8A.1 Corrections Applied

Phase 96.8A.1 (External Boundary + Action Separation + Universal Mastery)
applied the following corrections to Phase 96.8A deliverables:

- Bridge reclassified as **Environment Adapter / bridge boundary**
- Adapters clarified as **connection/translation** (not execution)
- Local worker classified as **worker runtime**
- tmux classified as **execution surface**
- Work Packet expanded: `required_mastery_categories`, `required_worker_runtime`, `proof_artifact_requirements`
- Packet Validator expanded: mastery/worker/proof-artifact checks for GUI packets
- All 96.8A tests updated to provide new required fields — zero regressions

## Next Steps

1. Founder bootstraps local worker (one-time, at Windows desktop)
2. W0-001 CU rerun executes via pull protocol with founder present
3. Results ingested and validated
4. Bridge becomes permanent infrastructure for all future local work
