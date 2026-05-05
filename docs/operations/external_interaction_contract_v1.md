# External Interaction Contract v1

**Phase:** 96.8A.1
**Status:** Active
**Layer:** UMH Substrate — `core/adapter_engine/external_interaction_contract.py`

## Purpose

Every interaction with an external system must be represented as an
ExternalInteraction record. This contract enforces that all external
interactions have an adapter, governance, proof requirements, and
maturity gate before execution.

## Schema

| Field | Type | Purpose |
|-------|------|---------|
| `interaction_id` | str | Unique identifier |
| `intent_summary` | str | What UMH intends to do |
| `external_system` | str | Human-readable system name |
| `external_system_type` | str | From ExternalSystemType enum |
| `adapter_category` | str | From AdapterCategory enum |
| `required_adapter_package` | str | Specific adapter package ID |
| `required_adapter_family` | str | Family if no specific package |
| `capability_contract` | str | What capability is being used |
| `target_environment` | list[str] | Where execution occurs |
| `work_packet_id` | str | Linked work packet if applicable |
| `governance_policy` | str | Governing policy reference |
| `proof_requirements` | list[str] | What must be proven |
| `maturity_gate` | str | Gate that must pass |
| `risk_level` | ExternalInteractionRisk | LOW/MEDIUM/HIGH/CRITICAL |
| `approval_required` | bool | Whether explicit approval needed |
| `status` | ExternalInteractionStatus | Current lifecycle status |
| `notes` | list[str] | Additional context |

## Validation

An ExternalInteraction is validated (`is_validated`) only when ALL of:
1. Has adapter (package or family)
2. Has governance policy
3. Has proof requirements
4. Has maturity gate
5. Has capability contract

Missing any one means the interaction is not validated and cannot
be used for production execution.

## Relationship to Work Packets

Work packets reference external interactions via `external_interaction_id`.
The interaction record provides the adapter boundary context that the
packet needs for execution. A work packet targeting a local GUI must
have an ExternalInteraction that specifies the environment adapter.

## Lifecycle

```
DRAFT → VALIDATED → EXECUTED → COMPLETED
                  → BLOCKED
                  → FAILED
```
