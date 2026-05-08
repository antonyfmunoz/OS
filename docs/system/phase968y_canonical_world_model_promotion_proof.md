# Phase 96.8Y — W0 Canonical World Model Promotion Proof

**Date:** 2026-05-08
**Status:** COMPLETE
**Phase:** 96.8Y
**Predecessor:** 96.8X (W0 World Model Candidate Proof)

## Summary

Built and proved a governance-bound promotion pipeline that converts
world-model candidates into canonical world-model truth. Every promotion
requires governance approval, deterministic candidate hash verification,
lineage completeness, and rollback reference. Canonical truth records are
immutable once written. The full chain from extraction through canonical
promotion is deterministically replayable.

## Core principle

Canonical truth is not generated.
Canonical truth is promoted through governed transition.

## What canonical world models store

A CanonicalWorldModel is governed truth — reality structures that have
been promoted through governance review from world-model candidates.

- **Canonical entities**: typed objects with confidence scores, source
  candidate entity references, observation lineage, governance receipt
- **Canonical relationships**: directional links with remapped canonical
  entity IDs, source candidate relationship references, governance receipt
- **Canonical constraints**: observed limitations applied to canonical
  entity IDs, governance receipt
- **Canonical causal graph**: promoted causal links with remapped entity
  IDs, aggregated confidence, governance receipt
- **Truth records**: immutable records binding source candidate to
  canonical hash, with lineage, governance receipt, uncertainty score,
  rollback reference, and allowed/blocked next actions

Every element is governed truth. No element is candidate hypothesis.

## Governance promotion pipeline

The promotion pipeline enforces structural separation between candidate
hypothesis and canonical truth:

1. **PromotionRequest** — requestor declares candidate_id + candidate_hash
2. **PromotionReview** — governance reviewer examines candidate, decides
   approved/rejected/deferred
3. **GovernanceApproval** — if approved, captures approval_id, review_id,
   candidate_id, candidate_hash, approved_by
4. **WorldModelPromoter.promote()** — validates preconditions, builds
   canonical model, returns (CanonicalWorldModel, PromotionReceipt)
5. **PromotionReceipt** — proves candidate was promoted with canonical
   hash, governance approval reference, rollback reference

### Precondition validation

Before any promotion, the promoter validates:
- `approval_id` is present
- `approved_by` is present
- `approval.candidate_id == candidate.candidate_id`
- `approval.candidate_hash == candidate.output_hash`
- Candidate has at least one entity or observation

A stale or mismatched approval cannot promote the wrong candidate.

## Entity ID remapping

During promotion, candidate entity IDs (ENT-xxx) are remapped to
canonical entity IDs (CENT-xxx). All relationships, constraints, and
causal links are updated to reference the new canonical entity IDs
through an `ent_id_map` dictionary. This ensures canonical models form
a self-consistent graph with no dangling references to candidate IDs.

## Deterministic truth hashes

Same candidate + same approval → same canonical hash.

`CanonicalTruthRecord.compute_canonical_hash()` serializes only
content-deterministic fields: truth_id, source_candidate_id,
source_candidate_hash, originating_observation_ids,
originating_interpretation_id, originating_trace_id, confidence.

`CanonicalWorldModel.compute_output_hash()` serializes model_id,
entities, relationships, constraints, causal_graph, and truth records
(deterministic fields only). Timestamps are excluded from both hashes.

The _DeterministicIdGenerator is seeded from the candidate output hash.
Two promotions of the same candidate with the same approval produce
byte-identical canonical models.

## Lineage completeness

Every canonical truth record carries a CanonicalLineageReference with
the full chain:

- `extraction_state_id` — which extraction produced the raw content
- `normalization_state_id` — which normalization processed it
- `interpretation_state_id` — which interpretation derived meaning
- `candidate_state_id` — which candidate organized the hypotheses
- `governance_state_id` — which governance approval promoted it
- `trace_id` — which trace ties the full chain together

This means any canonical truth can be traced back through every
transformation stage to the original source document.

## Rollback system

Every truth record carries a `rollback_reference`. The canonical model
maintains a `rollback_chain` of all rollback references.

`WorldModelPromoter.create_rollback_receipt()` generates a RollbackReceipt
that preserves:
- `prior_canonical_hash` — the hash before rollback
- `new_canonical_hash` — the hash after rollback (empty until applied)
- `rolled_back_truth_ids` — which truths were rolled back
- `rollback_reason` — why the rollback occurred
- `governance_reference` — which governance decision authorized it

Rollback requires governance. There is no autonomous rollback.

## Transition graph update

The CANONICAL_WORLD_MODEL stage was added to the transformation state
ledger. The updated DAG:

```
raw_source → extraction → normalization
  → interpretation
    → primitive_decomposition → ingestion_candidate → memory_candidate → governance_review
    → world_model_candidate → governance_review
  → ingestion_candidate (direct)
governance_review → canonical_memory → world_model_mutation
governance_review → canonical_world_model → world_model_mutation
```

governance_review now forks to two canonical stores:
1. canonical_memory — from the memory pipeline
2. canonical_world_model — from the world-model pipeline

Both converge at world_model_mutation.

CANONICAL_WORLD_MODEL is in GOVERNANCE_REQUIRED_STAGES — governance
reference is mandatory for any ledger record at this stage.

## Epistemic safety

The substrate's epistemic safety chain now extends through canonical
world models:

1. **Interpretation boundary**: 6 forbidden capabilities prevent
   the interpretation engine from mutating anything
2. **Candidate boundary**: 6 forbidden capabilities prevent
   world-model candidates from promoting themselves
3. **Canonical boundary**: 6 forbidden capabilities prevent
   canonical world models from self-modifying
4. **Transition graph**: VALID_TRANSITIONS prevents stage-skipping
5. **Governance requirement**: GOVERNANCE_REQUIRED_STAGES enforces
   founder approval for canonical_memory, canonical_world_model,
   and world_model_mutation (3 stages)
6. **Mutation blocking**: MUTATION_BLOCKED_STAGES prevents all
   pre-governance stages from performing writes (8 stages)

### Forbidden canonical actions (10)

self_mutate, recursive_rewrite, auto_promote_new_truths,
trigger_execution, reinterpret_observations, bypass_governance,
circular_truth_reference, ungrounded_entity_generation,
silent_ontology_mutation, self_reinforcing_promotion

### Canonical boundary enforcement (12 fields)

| Capability | Default |
|-----------|---------|
| may_store_governed_truth | True |
| may_expose_retrieval | True |
| may_support_replay | True |
| may_support_rollback | True |
| may_support_lineage_traversal | True |
| may_support_governance_audit | True |
| may_self_mutate | False |
| may_recursive_rewrite | False |
| may_auto_promote | False |
| may_trigger_execution | False |
| may_reinterpret_observations | False |
| may_bypass_governance | False |

Setting any forbidden capability to True raises a validation error.

## Governance separation table

| Layer | What it may do | What it may NOT do |
|-------|---------------|-------------------|
| Interpretation | Generate hypotheses | Create truth |
| World-model candidate | Organize hypotheses | Mutate canonical |
| Governance review | Approve/reject/defer | Auto-approve |
| Canonical world model | Persist governed truth | Self-modify |

Each layer can only reach the next through the transition graph.

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
| 96.8Y | **CANONICAL_WORLD_MODEL_PROMOTION** | **Governed truth promotion** |

## Files created

- `core/world_model/canonical_world_model_v1.py` — canonical model contracts
- `core/world_model/world_model_promotion_v1.py` — promotion pipeline
- `tests/test_canonical_world_model_v1.py` — 77 tests
- 6 example artifacts in `data/runtime/canonical_world_models/`
- `docs/system/phase968y_canonical_world_model_promotion_proof.md` — this report

## Files modified

- `core/state/transformation_state_ledger.py` — added CANONICAL_WORLD_MODEL
  stage, updated GOVERNANCE_REQUIRED_STAGES and VALID_TRANSITIONS

## Test results

- Focused (canonical world model): 77 passed, 0 failed
- Full substrate suite: 631 passed, 0 failed, 0 regressions

## Next gate

Phase 96.8Z or higher — world model mutation / canonical truth evolution.
