# /core/workstation — Status

## Classification: MIXED (RELAY_TRANSPORT + REPORT_GENERATORS)

This directory contains two distinct types of modules:

### A. Relay/Transport Modules (CANONICAL_SUBSTRATE)
These implement workstation relay communication and actuation:

| Module | Classification | Notes |
|--------|---------------|-------|
| `relay_execution_transport_v1.py` | CANONICAL_SUBSTRATE | SSH-based relay transport |
| `workstation_node_registry_v1.py` | CANONICAL_SUBSTRATE | Node registration |
| `workstation_relay_heartbeat_v1.py` | CANONICAL_SUBSTRATE | Heartbeat monitoring |
| `workstation_relay_node_v1.py` | CANONICAL_SUBSTRATE | Relay node implementation |
| `workstation_relay_proof_v1.py` | CANONICAL_SUBSTRATE | Relay proof generation |
| `workstation_relay_self_heal_v1.py` | CANONICAL_SUBSTRATE | Self-healing logic |
| `visible_actuation_proof_v1.py` | CANONICAL_SUBSTRATE | Actuation proof generation |
| `environment_mapping_engine_v1.py` | CANONICAL_SUBSTRATE | Environment discovery |
| `foreground_cu_ingestion_execution_v1.py` | CANONICAL_SUBSTRATE | CU ingestion execution |

### B. Report Generators (REPORT_GENERATOR / PROOF_ONLY)
These generate analysis reports but do NOT enforce runtime behavior:

| Module | Classification | Notes |
|--------|---------------|-------|
| `constitutional_antifragility_resilience_engine_v1.py` | REPORT_GENERATOR | Antifragility analysis reports |
| `constitutional_epistemic_intelligence_engine_v1.py` | REPORT_GENERATOR | Epistemic intelligence reports |
| `constitutional_identity_continuity_engine_v1.py` | REPORT_GENERATOR | Identity continuity reports |
| `constitutional_resource_economics_engine_v1.py` | REPORT_GENERATOR | Resource economics reports |
| `constitutional_strategic_intelligence_engine_v1.py` | REPORT_GENERATOR | Strategic intelligence reports |
| `constitutional_telos_alignment_engine_v1.py` | REPORT_GENERATOR | Telos alignment reports |
| `constitutional_substrate_governance_layer_v1.py` | REPORT_GENERATOR | Governance layer reports |
| `distributed_constitutional_substrate_federation_v1.py` | REPORT_GENERATOR | Federation reports |
| `adaptive_governance_intelligence_engine_v1.py` | REPORT_GENERATOR | Governance intelligence reports |
| `persistent_substrate_continuity_engine_v1.py` | REPORT_GENERATOR | Continuity reports |
| `governed_recursive_orchestration_engine_v1.py` | REPORT_GENERATOR | Orchestration reports |
| `recursive_capability_planning_engine_v1.py` | REPORT_GENERATOR | Capability planning reports |

### C. Adapter Generation (FOUNDATION)
| Module | Classification | Notes |
|--------|---------------|-------|
| `adapter_autogeneration_engine_v1.py` | FOUNDATION | Adapter generation contracts |

## Rule
**No module in this directory may claim enforcement maturity unless it directly
gates runtime execution.** Generating a report about governance is not governance.
The word "engine" in the filename is a misnomer for the report generators —
they should eventually be renamed to `*_report_generator.py`.

> Classified: Phase 96.8BJ — 2026-05-09
