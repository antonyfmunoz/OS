# Phase 96.8Z — W0 Execution Planning Candidate Proof

**Date:** 2026-05-08
**Status:** COMPLETE
**Phase:** 96.8Z
**Predecessor:** 96.8Y (W0 Canonical World Model Promotion Proof)

## Summary

Built and proved a governed execution planning candidate layer that
models proposed actions WITHOUT allowing autonomous execution. Plans
consume canonical truth (governed memory, world models, governance
receipts) and produce deterministic action graphs with dependency
ordering, risk envelopes, and governance escalation requirements.

The planning layer is purely epistemic. It reasons about action.
It does not perform action.

## Core principle

Plans are hypotheses about action.
Plans are not actions.

## Planning vs execution

This is the most consequential architectural boundary in the substrate.
Everything before this phase is epistemic — observing, interpreting,
modeling, promoting truth. Phase 96.8Z introduces the first layer that
reasons about *action* — but structurally prevents crossing into *doing*.

| Layer | Nature | May reason about | May do |
|-------|--------|-----------------|--------|
| Interpretation | Epistemic | Meaning | Nothing |
| World-model candidate | Epistemic | Reality structure | Nothing |
| Canonical world model | Epistemic | Governed truth | Nothing |
| **Execution planning** | **Epistemic** | **Action** | **Nothing** |
| Execution authority | Executive | — | Action (future) |

The planning candidate sits on the epistemic side of the boundary.
The future execution authority engine will sit on the executive side.
The gap between them is the governance gate.

## Epistemic action modeling

An ExecutionPlanningCandidate models:

- **ProposedAction**: a single proposed action with rationale, supporting
  canonical truth references, resource requirements, constraint evaluations,
  expected outcomes, risk envelope, and rollback reference
- **ActionSequence**: ordered list of proposed actions with total cost and risk
- **ActionGraph**: DAG execution structure with dependency edges, topological
  ordering, cycle detection, and rollback chain
- **ResourceRequirement**: typed resource with quantity, unit, financial flag,
  and estimated cost
- **ConstraintEvaluation**: evaluation of a constraint against a proposed
  action with satisfaction flag and violation risk
- **RiskEnvelope**: 6-dimensional risk assessment with escalation tiers
- **ExpectedOutcome**: probability-weighted outcome with impact type and
  supporting truth references
- **ExecutionDependency**: directed edge between actions with blocking flag

Every element is a hypothesis. No element is an executed action.

## Governance-bound planning

### What plans may consume (5 allowed inputs)

- canonical_memory
- canonical_world_model
- governance_receipt
- deterministic_observation
- constraint_system

### What plans may NOT consume (4 forbidden inputs)

- candidate_hypothesis
- ungoverned_interpretation
- recursive_self_generated_plan
- hidden_runtime_state

Plans can only reason from governed truth. A plan that consumes
ungoverned hypotheses would be reasoning from unverified assumptions.
A plan that consumes its own output would be recursive — the most
dangerous planning failure mode.

## Deterministic action graphs

Same canonical truth inputs + same constraints + same risk settings
→ same planning hash.

The _DeterministicIdGenerator is seeded from the canonical model hash.
Every action ID, dependency ID, graph ID, sequence ID, and plan ID is
a pure function of the canonical input. Two assemblies of the same
canonical model produce byte-identical planning candidates.

`compute_output_hash()` serializes only deterministic fields: plan_id,
plan_type, description, action_sequence, action_graph, risk envelope
dimensions (not computed fields), source references. Timestamps are
excluded.

### DAG structure

ActionGraph implements Kahn's algorithm with sorted tie-breaking for
deterministic topological ordering. The sort on both the initial queue
and neighbor insertion ensures stable ordering across runs.

Cycle detection uses the topological sort completeness check: if the
topological order has fewer nodes than the graph, a cycle exists.
Plans with cyclic dependencies fail validation.

## Replayable planning lineage

Every planning candidate carries a PlanningLineageReference:

- `source_canonical_model_id` — which canonical world model was used
- `source_canonical_memory_ids` — which canonical memories were consumed
- `source_governance_receipt_ids` — which governance approvals authorized input
- `source_world_model_hash` — deterministic hash of the source model
- `planning_trace_id` — trace connecting this plan to the full chain

Planning replay reconstructs:
1. Action ordering (topological sort)
2. Dependency graph (edge set)
3. Risk envelope (6 dimensions + escalation)
4. Governance requirements (escalation tier)
5. Escalation path (threshold violations)

## Execution-risk containment

### RiskEnvelope — 6 dimensions

| Dimension | Threshold | Escalation |
|-----------|-----------|------------|
| financial_risk | 0.30 | FOUNDER_APPROVAL |
| execution_risk | 0.50 | APPROVAL |
| uncertainty_risk | 0.60 | APPROVAL |
| trust_boundary_risk | 0.30 | FOUNDER_APPROVAL |
| external_dependency_risk | 0.50 | APPROVAL |
| recursive_autonomy_risk | 0.10 | BLOCKED |

### Escalation tiers

| Tier | Meaning |
|------|---------|
| NONE | No escalation needed |
| REVIEW | Governance review recommended |
| APPROVAL | Governance approval required |
| FOUNDER_APPROVAL | Founder must approve |
| BLOCKED | Cannot proceed — structural block |

`recursive_autonomy_risk` has the lowest threshold (0.10) and the
highest escalation (BLOCKED). Any plan exhibiting recursive autonomy
characteristics is structurally blocked — governance cannot override
this. This is the substrate's guarantee that planning cannot bootstrap
itself into autonomous execution.

## Autonomous planning safety

### Forbidden planning actions (14)

runtime_invocation, wallet_usage, api_execution, shell_execution,
browser_execution, financial_execution, credential_access,
memory_mutation, canonical_mutation, adapter_invocation,
trade_placement, money_allocation, autonomous_execution,
recursive_plan_consumption

### Planning governance boundary (16 fields)

| Capability | Default |
|-----------|---------|
| may_propose_actions | True |
| may_sequence_actions | True |
| may_model_dependencies | True |
| may_estimate_resources | True |
| may_estimate_risk | True |
| may_estimate_outcomes | True |
| may_attach_canonical_truths | True |
| may_invoke_runtime | False |
| may_use_wallet | False |
| may_execute_api | False |
| may_execute_shell | False |
| may_execute_browser | False |
| may_execute_financial | False |
| may_access_credentials | False |
| may_mutate_memory | False |
| may_mutate_canonical | False |

Setting any forbidden capability to True raises a validation error.
The boundary has 9 blocked capabilities (vs 6 in previous layers)
because the planning layer sits at the epistemic/executive edge —
the attack surface for autonomous action is larger here than anywhere
else in the substrate.

## Future financial-agent implications

The planning layer is designed to support future financial agents:

- `ResourceRequirement.is_financial` flags financial resources
- `ResourceRequirement.estimated_cost` tracks projected costs
- `ActionSequence.compute_total_cost()` aggregates financial exposure
- `financial_risk` and `trust_boundary_risk` both escalate to
  FOUNDER_APPROVAL at the 0.30 threshold
- `trade_placement` and `money_allocation` are structurally forbidden

When a financial agent is built, it will consume planning candidates
(not create them). The planning layer will model proposed financial
actions — the financial execution layer will execute them after
governance approval. The separation is structural.

## Transition graph update

The EXECUTION_PLANNING_CANDIDATE stage was added to the transformation
state ledger. The updated DAG:

```
raw_source → extraction → normalization
  → interpretation
    → primitive_decomposition → ingestion_candidate → memory_candidate → governance_review
    → world_model_candidate → governance_review
  → ingestion_candidate (direct)
governance_review → canonical_memory → world_model_mutation
governance_review → canonical_world_model
  → world_model_mutation
  → execution_planning_candidate → governance_review
```

canonical_world_model now forks to two paths:
1. world_model_mutation — direct canonical mutation (governed)
2. execution_planning_candidate — action modeling → governance_review

execution_planning_candidate can only reach governance_review.
It cannot reach any execution stage, any canonical store, or any
mutation stage.

EXECUTION_PLANNING_CANDIDATE is in MUTATION_BLOCKED_STAGES — the
ledger enforces that no writes can occur at this stage.

## Epistemic safety chain (updated)

1. **Interpretation boundary**: 6 forbidden capabilities prevent
   the interpretation engine from mutating anything
2. **Candidate boundary**: 6 forbidden capabilities prevent
   world-model candidates from promoting themselves
3. **Canonical boundary**: 6 forbidden capabilities prevent
   canonical world models from self-modifying
4. **Planning boundary**: 9 forbidden capabilities prevent
   planning candidates from executing anything
5. **Transition graph**: VALID_TRANSITIONS prevents stage-skipping
6. **Governance requirement**: GOVERNANCE_REQUIRED_STAGES enforces
   founder approval for canonical_memory, canonical_world_model,
   and world_model_mutation (3 stages)
7. **Mutation blocking**: MUTATION_BLOCKED_STAGES prevents all
   pre-governance stages from performing writes (9 stages)
8. **Risk escalation**: recursive_autonomy_risk ≥ 0.10 → BLOCKED
   (structural, governance cannot override)

## Capability type progression

| Phase | CapabilityType | Trust boundary |
|-------|----------------|----------------|
| 96.8  | SHELL_EXECUTION | Local shell |
| 96.8  | WINDOWS_GUI_EXECUTION | GUI interaction |
| 96.8S | DOCUMENT_EXTRACTION | Read-back |
| 96.8T | INGESTION_CANDIDACY | Data normalization |
| 96.8U | MEMORY_PROMOTION | Governed mutation |
| 96.8V | CANONICAL_MEMORY_QUERY | Governed retrieval |
| 96.8W | INTERPRETATION_ENGINE | Governed interpretation |
| 96.8X | WORLD_MODEL_CANDIDATE | Governed world-modeling |
| 96.8Y | CANONICAL_WORLD_MODEL_PROMOTION | Governed truth promotion |
| 96.8Z | **EXECUTION_PLANNING_CANDIDATE** | **Governed action modeling** |

## Files created

- `core/planning/execution_planning_candidate_v1.py` — planning contracts + assembler
- `tests/test_execution_planning_candidate_v1.py` — 123 tests
- 4 example artifacts in `data/runtime/execution_planning_candidates/`
- `docs/system/phase968z_execution_planning_candidate_proof.md` — this report

## Files modified

- `core/state/transformation_state_ledger.py` — added EXECUTION_PLANNING_CANDIDATE
  stage, updated VALID_TRANSITIONS and MUTATION_BLOCKED_STAGES

## Test results

- Focused (execution planning): 123 passed, 0 failed
- Full substrate suite: 754 passed, 0 failed, 0 regressions

## Next gate

W0_EXECUTION_AUTHORITY_ENGINE_PROOF
