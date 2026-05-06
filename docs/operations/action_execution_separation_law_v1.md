# Action / Execution Separation Law v1

**Status:** ACTIVE
**Layer:** Execution Plane + Governance Layer
**Scope:** Universal — governs all UMH execution

---

## Doctrine

Action is NOT execution. These are distinct concepts that must never be conflated.

---

## Definitions

| Concept | Definition |
|---------|-----------|
| **Action** | Intended state transformation |
| **Capability** | Abstract ability required to perform or support that transformation |
| **Adapter** | Connection and translation boundary to an external system |
| **Environment** | Where execution occurs (VPS, WSL, Windows GUI, Chrome, tmux) |
| **Worker Runtime** | Process/session/node that performs execution |
| **Actuation** | Low-level effect-producing operation |
| **Work Packet** | Governed executable instruction |
| **Proof Artifact** | Evidence that the action happened correctly |
| **Trace** | Complete inspectable record |
| **Learning** | Governed update process |

---

## Hard Rules

1. **Action is not execution** — declaring intent is separate from performing it
2. **Adapter is not worker** — translating is separate from performing
3. **Environment is not worker** — where execution happens is not what performs it
4. **Actuation is not adapter** — producing effects is separate from translating
5. **Work Packet must bind action to execution** — the packet is the bridge
6. **Proof requirements must exist BEFORE execution** — not added after

---

## Contract Structure

### ActionContract

Declares the intended state transformation:
- action_id, action_type
- intended_state_change
- required_capabilities
- required_adapters, required_environments, required_workers
- governance_policy, risk_level, authority_required
- success_criteria, failure_modes
- proof_requirements
- idempotency_key

### ExecutionBinding

Binds an action to a specific execution context:
- action_id, work_packet_id
- environment_id, worker_runtime_id
- adapter_boundaries
- actuator_type, trace_id

---

## Validation Status

| Status | Meaning |
|--------|---------|
| VALID | Full separation with all requirements |
| ACTION_MISSING | No action declared |
| CAPABILITY_MISSING | No capabilities specified |
| ENVIRONMENT_MISSING | No environment bound |
| WORKER_MISSING | No worker bound |
| ADAPTER_BOUNDARY_MISSING | No adapter boundary |
| GOVERNANCE_MISSING | No governance policy |
| PROOF_MISSING | No proof requirements |

---

## Implementation

`core/execution/action_execution_contracts.py` enforces this law through:
- `validate_action_execution_separation(action, binding)` — returns status
- `action_contract_is_complete(action)` — checks action completeness
- `execution_binding_is_complete(binding)` — checks binding completeness
