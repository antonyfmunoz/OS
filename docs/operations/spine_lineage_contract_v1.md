# Spine Lineage Contract v1

**Phase:** 96.8G
**Status:** Active
**Layer:** UMH Substrate — Coherence Layer
**Module:** `core/coherence/spine_lineage_contracts.py`

## Doctrine

A work packet is a downstream artifact — not the source of truth.
The source of truth is the spine lineage that produced it.

Every executable work packet must prove it descended from the
canonical 15-stage UMH spine.

## The 15 Canonical Stages

| # | Stage | What It Proves |
|---|-------|---------------|
| 1 | signal | An external trigger or request exists |
| 2 | interpretation | The system understood what the signal means |
| 3 | decomposition | The request was broken into actionable units |
| 4 | primitive_mapping | Units were mapped to UMH primitives |
| 5 | domain_mapping | Units were mapped to domain context |
| 6 | state_context | World/memory/profile context was loaded |
| 7 | composition | An execution plan was assembled |
| 8 | capability_selection | Required capabilities were selected |
| 9 | adapter_selection | Required execution adapters were selected |
| 10 | execution_binding | All 6 execution layers were explicitly bound |
| 11 | mastery_check | Tool mastery was verified |
| 12 | governance_decision | Authority/risk/approval decision was made |
| 13 | work_packet | A governed work packet was generated |
| 14 | proof_contract | Required proof was defined |
| 15 | trace_path | End-to-end trace identifier exists |

## Stage Artifact Contract

Each stage artifact must have:

| Field | Required | Purpose |
|-------|----------|---------|
| stage_name | YES | Which canonical stage |
| artifact_id | YES | Unique identifier |
| artifact_type | YES | What kind of artifact |
| source | YES | What produced this artifact |
| timestamp | YES | When it was produced |
| status | YES | complete, mvp_stub, failed, etc. |
| trace_id | YES | Links all stages in one trace |
| schema_version | YES | Contract version |
| confidence | NO | How confident the source is |
| reason | CONDITIONAL | Required if status=mvp_stub |
| allowed_for | CONDITIONAL | Required if status=mvp_stub |

## MVP Stub Artifacts

When a full subsystem does not exist yet, represent the stage
as an explicit MVP stub:

```
status: mvp_stub
reason: subsystem_not_implemented
allowed_for: W0 coherence validation only
```

This is acceptable **only** when governance explicitly allows
MVP stub lineage (`mvp_stub_allowed: true`).

## Coherence Statuses

| Status | Meaning | Execution? |
|--------|---------|------------|
| coherent | All stages complete | YES |
| coherent_with_mvp_stubs | Stubs present, allowed | YES |
| incomplete_canonical_spine | Missing stages | NO |
| invalid_stage_order | Wrong order | NO |
| invalid_stage_artifact | Bad artifact fields | NO |
| governance_lineage_missing | No governance stage | NO |
| mastery_lineage_missing | No mastery stage | NO |
| execution_binding_lineage_missing | No binding stage | NO |
| proof_contract_lineage_missing | No proof stage | NO |
| trace_path_lineage_missing | No trace stage | NO |

## Ordering Constraints

- Governance decision must appear before work_packet
- Mastery check must appear before governance_decision
- All stages follow canonical order (signal → trace_path)
