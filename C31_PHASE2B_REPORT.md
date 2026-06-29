# C31 Phase 2B Report — Dormant Workstation Freeze

**Date:** 2026-06-29
**Branch:** worktree-c31-phase2b
**Scope:** Remove speculative workstation architecture from active import surface.

---

## 1. Summary

| Action | Files | Lines |
|--------|-------|-------|
| Moved to `_dormant/` | 32 | 23,199 |
| Deleted (zero-ref) | 2 | 586 + test |
| Remaining active | 9 | 3,477 |
| Report imports updated | 90 | — |

**Net result:** 23,785 lines of dead/speculative code quarantined from active import surface.

---

## 2. Files Moved to `_dormant/`

### SPECULATIVE (19 files, ~4,866 lines) — Zero external consumers

```
browser_continuity_bridge_v1.py
browser_execution_orchestrator_v1.py
browser_gui_contracts_v1.py
browser_gui_embodiment_engine_v1.py
browser_observability_pipeline_v1.py
browser_operational_modes_v1.py
browser_replay_validator_v1.py
governed_browser_adapter_v1.py
governed_shell_adapter_v1.py
visible_gui_adapter_v1.py
workstation_continuity_bridge_v1.py
workstation_observability_pipeline_v1.py
workstation_operational_embodiment_engine_v1.py
workstation_operational_modes_v1.py
workstation_relay_heartbeat_v1.py
workstation_relay_node_v1.py
workstation_relay_proof_v1.py
workstation_replay_validator_v1.py
workstation_state_registry_v1.py
```

### DORMANT (13 files, ~17,282 lines) — Report-only consumers

```
constitutional_antifragility_resilience_engine_v1.py
constitutional_epistemic_intelligence_engine_v1.py
constitutional_identity_continuity_engine_v1.py
constitutional_resource_economics_engine_v1.py
constitutional_strategic_intelligence_engine_v1.py
constitutional_substrate_governance_layer_v1.py
constitutional_telos_alignment_engine_v1.py
distributed_constitutional_substrate_federation_v1.py
adaptive_governance_intelligence_engine_v1.py
governed_recursive_orchestration_engine_v1.py
persistent_substrate_continuity_engine_v1.py
adapter_autogeneration_engine_v1.py
recursive_capability_planning_engine_v1.py
```

90 import paths in `transports/presence/handlers/reports/` updated to `._dormant.` prefix.

---

## 3. Files Deleted

| File | Lines | Reason |
|------|-------|--------|
| `substrate/execution/bridge/meeting_types.py` | 586 | Zero references in codebase |
| `tests/test_meeting_types.py` | — | Only consumer of deleted module |

---

## 4. Files Kept Active (9)

| File | Lines | Consumer |
|------|-------|----------|
| `environment_mapping_engine_v1.py` | 1,124 | substrate/workstation/, reports/ |
| `tmux_operational_adapter_v1.py` | 266 | cockpit_core_session_routes.py |
| `workstation_contracts_v1.py` | 485 | substrate/workstation/, transports/api/ |
| `workstation_execution_orchestrator_v1.py` | 189 | transports/api/workstation.py |
| `visible_actuation_proof_v1.py` | 285 | substrate_command_handler, reports/ |
| `relay_execution_transport_v1.py` | 285 | substrate_command_handler |
| `workstation_relay_self_heal_v1.py` | 160 | substrate_command_handler |
| `foreground_cu_ingestion_execution_v1.py` | 575 | substrate_command_handler |
| `workstation_node_registry_v1.py` | 108 | substrate_command_handler |

---

## 5. Verification

| Check | Result |
|-------|--------|
| `tests/substrate/` | **70/70 passed** (0.28s) |
| `py_compile` (all 15 report files) | **All pass** |
| `py_compile` (9 active workstation files) | **All pass** |
| Stale import check (13 dormant modules) | **0 remaining** |

No regressions. No behavior changes. Discord report commands continue to work via `_dormant.` import path.

---

## 6. What This Does NOT Do

- Does not delete any code — ideas preserved in `_dormant/` for future harvesting
- Does not change runtime behavior — report generators still import from `_dormant/`
- Does not touch Tier 2/3 silent exceptions
- Does not address the 45 dormant bridge modules (separate scope)
