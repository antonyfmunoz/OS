# /core — Status

## Classification: CANONICAL_SUBSTRATE_AND_INFRASTRUCTURE

This directory contains the canonical UMH substrate contracts and
infrastructure modules. It is the target package for all new
substrate-layer work.

### What this means
- Contains canonical contracts for execution, governance, planning, memory
- Contains infrastructure: paths.py (root resolution), environment.py, convergence/
- Some modules are imported by `handlers/substrate_command_handler.py`
- Some modules are imported by `eos_ai/substrate/` subsystems
- Constitutional modules in `workstation/` are REPORT_GENERATORS, not enforcement
- Ingestion pipeline modules (Phase 96.8BJ) are working but not yet wired to bot commands

### Relationship to eos_ai/
`core/` is the canonical substrate layer. `eos_ai/` is the runtime layer
(legacy-named). Both are part of UMH. New substrate contracts go in `core/`.
Runtime intelligence modules live in `eos_ai/`. When `eos_ai/` is renamed
to `umh_runtime/`, the distinction becomes:
- `core/` = contracts, infrastructure, governance
- `umh_runtime/` = live intelligence, routing, memory, transport

### Subdirectory status
| Subdirectory | Status | Notes |
|-------------|--------|-------|
| `paths.py` | CANONICAL_INFRASTRUCTURE | UMH_ROOT resolution, env chain |
| `adapters/` | CANONICAL_SUBSTRATE | Ingestion bridge, decomposer, candidate gen (working) |
| `memory/` | CANONICAL_SUBSTRATE | Canonical memory store (working, JSONL) |
| `ontology/` | CANONICAL_SUBSTRATE | Primitive type definitions |
| `registry/` | PARTIALLY_VERIFIED | Adapter/capability registry |
| `control_plane_router/` | PARTIALLY_VERIFIED | Control plane routing |
| `workstation/` | MIXED | Relay transport + report generators |
| `execution/` | PARTIALLY_VERIFIED | Execution contracts |
| `governance/` | PARTIALLY_VERIFIED | Governance contracts |
| `world_model/` | PARTIALLY_VERIFIED | World model candidates |
| `interpretation/` | PARTIALLY_VERIFIED | Interpretation engine |
| `planning/` | PARTIALLY_VERIFIED | Planning modules |
| `adapter_engine/` | FOUNDATION | Adapter generation contracts |
| `environment_bridge/` | PARTIALLY_VERIFIED | Environment bootstrap |
| `convergence/` | INFRASTRUCTURE | Repository convergence tooling |
| `security/` | PARTIALLY_VERIFIED | Security/redaction |
| `state/` | PARTIALLY_VERIFIED | State management |
| `coherence/` | PROOF_ONLY | Coherence validation |
| `action_system/` | PARTIALLY_VERIFIED | Action planning |
| `actuation/` | PARTIALLY_VERIFIED | Physical actuation |

### Rules
- New canonical substrate work goes here
- Report generators must NOT be labeled as "engines"
- Every module must declare its layer classification
- core/paths.py is the canonical root resolution module — all path
  resolution should ultimately flow through get_root()

> Classified: Phase 96.8CO — 2026-05-10
> Previous: Phase 96.8BJ — 2026-05-09
