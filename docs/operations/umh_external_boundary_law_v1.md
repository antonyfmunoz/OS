# UMH External Boundary Law v1

**Status:** ACTIVE
**Layer:** Adapter Boundary Layer
**Scope:** Universal — applies to all UMH subsystems and platform consumers

---

## Doctrine

No external system, tool, SaaS, model, runtime, environment, human approval process, data source, filesystem, browser, operating system, or physical-world actor may be accessed directly by UMH.

Every external interaction must pass through an Adapter Package, Adapter Family member, Environment Adapter, Model Adapter, Data Source Adapter, Human Approval Adapter, or Physical-World Adapter.

Adapters are the universal connection and translation boundary between UMH's internal model and external reality.

**Adapters do NOT independently execute actions.**

Execution is performed only by the governed Action System through the Execution Spine, using an approved worker/runtime in an explicit environment.

---

## Requirements for External Interaction

Every external interaction must declare:

1. **Adapter boundary** — which Adapter Package or Family mediates
2. **Capability contract** — what the interaction can do
3. **Environment** — where execution happens (when applicable)
4. **Worker/runtime** — what performs execution (when applicable)
5. **Governance policy** — what is allowed/blocked
6. **Mastery requirements** — what competence UMH must have
7. **Work Packet** — governed executable instruction
8. **Proof requirements** — evidence that execution happened correctly
9. **Trace path** — complete inspectable record

---

## Violation Types

| Status | Meaning |
|--------|---------|
| COMPLIANT | All requirements satisfied |
| MISSING_ADAPTER | No adapter boundary declared |
| MISSING_CONTRACT | No capability contract |
| MISSING_GOVERNANCE | No governance policy |
| MISSING_PROOF | No proof requirements |
| MISSING_MASTERY | No mastery requirements |
| MISSING_MATURITY_GATE | No maturity gate |
| MISSING_ENVIRONMENT | Environment required but not declared |
| MISSING_WORKER | Worker required but not declared |
| UNKNOWN_EXTERNAL_SYSTEM | System type not specified |

---

## Enforcement

The External Boundary Law is enforced by:
- `core/adapter_engine/external_boundary_law.py` — evaluates compliance
- `core/adapter_engine/adapter_boundary_validator.py` — validates boundaries
- `core/environment_bridge/packet_validator.py` — validates work packets

Non-compliant interactions are BLOCKED. No exception without explicit founder override.

---

## Relation to Phase 96.8A

The VPS ↔ Local Worker Bridge is an **Environment Adapter / bridge boundary**. It connects the VPS orchestrator to local execution environments (Windows, WSL, tmux). The bridge does not execute — it mediates the connection and translates work packets across the boundary.
