# Phase 96.8X — W0 World Model Candidate Proof

**Date:** 2026-05-08
**Status:** COMPLETE
**Phase:** 96.8X
**Predecessor:** 96.8W (W0 Interpretation Engine Proof)

## Summary

Built and proved a governed world-model candidate system that accumulates
structured interpretations into candidate reality structures WITHOUT
mutating canonical world models. Candidate entities, relationships,
causal links, and constraints are deterministically assembled from
interpretation output. All candidates require governance review before
any canonical promotion.

## Core principle

Interpretation generates hypotheses.
World-model candidates organize hypotheses.
Only governance may promote reality structure into canonical world models.

## Interpretation vs world-modeling

Interpretation and world-modeling are distinct cognitive operations:

**Interpretation** (Phase 96.8W):
- Operates on a single source document
- Produces observations, patterns, decompositions, hypotheses
- 5-stage pipeline: observe → detect → map → hypothesize → analyze
- Output: InterpretationResult with confidence envelope

**World-modeling** (Phase 96.8X):
- Operates on interpretation output
- Organizes observations into candidate entity graphs
- Connects entities with directional relationships
- Forms candidate causal structures from hypotheses
- Tracks uncertainty across entity/relationship/causal dimensions
- Output: WorldModelCandidate with entity graph + causal links

The distinction is structural. Interpretation derives meaning from content.
World-modeling organizes meaning into candidate reality structures. Neither
creates truth — truth only exists through governed promotion.

## Candidate reality structures

A WorldModelCandidate is a structured hypothesis about reality:

- **Entities**: typed objects with confidence scores, observation lineage,
  trace references, and resolution confidence
- **Relationships**: directional links between entities with causal,
  temporal, and constraint flags
- **Causal links**: hypothesis-derived cause/effect connections with
  evidence chains and temporal ordering markers
- **Constraints**: observed limitations that apply to specific entities
- **Observations**: candidate-level observation copies with interpretation
  and trace references

Every element is a candidate. No element is canonical truth.

## Uncertainty-aware entity modeling

Every entity carries:
- `confidence` — how likely this entity exists
- `resolution_confidence` — how confident the system is about entity identity
  (HIGH, MEDIUM, LOW, SPECULATIVE)
- `source_observation_ids` — which observations produced this entity
- `source_trace_ids` — which traces contributed evidence
- `uncertainty_notes` — explicit unknowns about this entity

The CandidateConfidenceEnvelope tracks uncertainty across 5 dimensions:
entity_confidence, relationship_confidence, causal_confidence,
evidence_coverage, and overall uncertainty_score.

## Causal hypothesis accumulation

Causal links are derived from interpretation hypotheses:
- Each hypothesis with supporting observations generates a causal link
- Causal links connect entities (cause → effect)
- Every link carries evidence_observation_ids and unsupported_assumptions
- Temporal ordering is marked but not validated (explicit unknown)

Causal links are the most speculative element of a world-model candidate.
They represent "this hypothesis suggests X causes Y" — not "X causes Y."

## Why world models must remain candidate-bound

A canonical world model represents the substrate's believed reality.
Mutating it without governance means the substrate has autonomously
decided what is true. This is the most dangerous capability a substrate
can have — autonomous truth creation.

The candidate boundary ensures:
- Candidates accumulate evidence but never become truth
- Governance review is structurally required before promotion
- The transition graph enforces: world_model_candidate → governance_review
  (no shortcuts to canonical_memory or world_model_mutation)
- 10 forbidden actions are blocked at the boundary level

## Deterministic reality reconstruction

Same interpretation chain → same candidate world-model hash.

The _DeterministicIdGenerator is seeded from the interpretation output hash.
Every entity ID, relationship ID, causal link ID, and candidate ID is a
pure function of the interpretation output. Two runs of the assembler on
the same interpretation produce byte-identical candidates.

This means candidate reconstruction replays:
1. extraction (raw → extracted content)
2. normalization (extracted → normalized)
3. interpretation (normalized → observations + hypotheses)
4. primitive decomposition (observations → 10-type ontology)
5. entity extraction (observations → candidate entities)
6. relationship formation (patterns → candidate relationships)
7. causal link derivation (hypotheses → candidate causal links)
8. candidate graph assembly (all above → WorldModelCandidate)

Every step is deterministic. Every step has a hash. The full chain
can be replayed to verify any candidate.

## Governance separation

The boundary between candidate and canonical is structural:

| Layer | What it may do | What it may NOT do |
|-------|---------------|-------------------|
| Interpretation | Generate hypotheses | Create truth |
| World-model candidate | Organize hypotheses | Mutate canonical |
| Governance review | Approve/reject | Auto-approve |
| Canonical world model | Persist truth | Self-modify |

Each layer can only reach the next through the transition graph.
There is no shortcut from interpretation to canonical, and no
shortcut from world-model candidate to canonical.

## Epistemic safety

The substrate's epistemic safety rests on a chain of structural
guarantees:

1. **Interpretation boundary**: 6 forbidden capabilities prevent
   the interpretation engine from mutating anything
2. **Candidate boundary**: 6 forbidden capabilities prevent
   world-model candidates from promoting themselves
3. **Transition graph**: VALID_TRANSITIONS prevents stage-skipping
4. **Governance requirement**: GOVERNANCE_REQUIRED_STAGES enforces
   founder approval for canonical_memory and world_model_mutation
5. **Mutation blocking**: MUTATION_BLOCKED_STAGES prevents all
   pre-governance stages from performing writes

A substrate that can autonomously decide what is true is a substrate
that can hallucinate beliefs. The candidate layer is the structural
guarantee that this cannot happen.

## State ledger transition graph (updated)

```
raw_source → extraction → normalization
  → interpretation
    → primitive_decomposition → ingestion_candidate → memory_candidate → governance_review
    → world_model_candidate → governance_review
  → ingestion_candidate (direct)
governance_review → canonical_memory → world_model_mutation
```

interpretation now forks to two paths:
1. primitive_decomposition → memory pipeline
2. world_model_candidate → candidate reality pipeline

Both converge at governance_review before any canonical mutation.

## Forbidden candidate actions (10)

mutate_canonical_world_model, create_canonical_truth, auto_promote,
bypass_governance, trigger_execution, recursive_self_rewrite,
autonomous_memory_promotion, silent_entity_creation,
expand_ontology_without_governance, self_promote_to_canonical

## Candidate statuses (5)

draft, assembled, awaiting_governance, governance_approved,
governance_rejected

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
| 96.8X | **WORLD_MODEL_CANDIDATE** | **Governed world-modeling** |

## Files created

- `core/world_model/world_model_candidate_v1.py` — assembler + contracts
- `core/world_model/entity_resolution_v1.py` — entity/relationship contracts
- `tests/test_world_model_candidate_v1.py` — 85 tests
- 4 example artifacts in `data/runtime/world_model_candidates/`
- `docs/system/phase968x_world_model_candidate_proof.md` — this report

## Files modified

- `core/state/transformation_state_ledger.py` — added WORLD_MODEL_CANDIDATE
  stage, updated VALID_TRANSITIONS and MUTATION_BLOCKED_STAGES

## Test results

- Focused (world model candidate): 85 passed, 0 failed
- Full substrate suite: 554 passed, 0 failed, 0 regressions

## Next gate

W0_CANONICAL_WORLD_MODEL_PROMOTION_PROOF
