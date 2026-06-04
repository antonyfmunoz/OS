# UMH Source Truth / Production Truth Lifecycle

**Phase:** 14.6B-UMH | **Status:** DRAFT | **Provenance:** CODE_RESOLVED_CURRENT_TRUTH + OPERATOR_CORRECTION

---

## Lifecycle Stages

### 1. Raw Source
External documents, code, conversations, observations
**Current:** Google Drive docs, /opt/OS codebase, Phase 14 artifacts, operator corrections

### 2. Source Inventory
Cataloging all source inputs with metadata
**Current:** umh_source_inventory.json (this phase), previous phases' source_truth_packets

### 3. Extracted Claims
Individual claims extracted from sources with provenance
**Current:** Phase 14.3A full_content_convergence artifacts

### 4. Provenance Classification
Each claim labeled with its origin and reliability
**Labels:** SOURCE_PRESERVED_TRUTH, CODE_RESOLVED_CURRENT_TRUTH, SYNTHESIZED_CANON, INFERRED_PROFESSIONAL_GAP, OPEN_QUESTION_OPERATOR_DECISION_REQUIRED, IMPLEMENTATION_DEBT

### 5. Version/Contradiction Matrix
Detecting contradictions across sources
**Current:** Phase 14.3A contradiction_matrix artifacts

### 6. Code Truth Inspection
Verifying claims against actual codebase
**Current:** This phase (14.6B-UMH) deep codebase analysis

### 7. Synthesized Canon Draft
Combining sources into a coherent canon document
**Current:** umh_lossless_product_canon.md, umh_code_resolved_substrate_canon.md (this phase)

### 8. Professional Gap Register
Identifying gaps not visible in any source
**Current:** umh_professional_gap_register.md (this phase)

### 9. Operator Decision Queue
Questions requiring operator judgment
**Current:** umh_open_questions_operator_decision_queue.md (this phase)

### 10. Ratification Packet
Package for operator review
**Current:** umh_ratification_packet.md (this phase)

### 11. Operator Approval
Operator reviews and approves/modifies
**Status:** NEXT STEP after this phase

### 12. Approved Canon
Operator-approved truth
**Status:** Not yet — this phase produces drafts

### 13. Work Packet
Implementation work derived from approved canon
**Status:** Future — requires approved canon first

### 14. Dry Run
Simulated execution of work packets
**Current code:** substrate/reality_model/simulation.py (SimulationReality)
**Cockpit code:** cockpit_propagation_graph_routes.py has dry-run endpoint

### 15. Implementation
Actual code changes
**Status:** BLOCKED — this phase does not implement

### 16. Tests
Verification of implementation
**Current:** 2,832 test functions across 86 files

### 17. Production Truth Promotion
Promoting tested implementation to production truth
**Current code:** substrate/organism/production_truth_delta.py, substrate/organism/operational_truth.py
**Cockpit code:** /api/umh/promote endpoint (rate-limited 60s)

### 18. Monitoring
Ongoing observation of production behavior
**Current code:** organism daemon tick loop, reliability signals, operational truth snapshots

### 19. Drift Review
Detecting drift from approved canon
**Current code:** substrate/organism/dex_reconciliation.py, substrate/organism/coherence_propagation.py

### 20. Correction Loop
Correcting drift and feeding back into source truth
**Current:** This phase (14.6B-UMH) IS a correction loop — correcting Phase 14.6A drafts

## Required Objects (for future formalization)

| Object | Description | Current Implementation |
|--------|-------------|----------------------|
| SourceArtifact | A raw source document | Phase 14 JSON artifacts |
| SourceInventory | Catalog of all sources | umh_source_inventory.json |
| ExtractedClaim | Individual claim with provenance | Phase 14.3A extractions |
| CodeTruthFinding | Code inspection result | umh_current_implementation_truth.json |
| ProvenanceLabel | Origin classification | 6 labels defined |
| Contradiction | Conflict between sources | Phase 14.3A contradiction matrices |
| CanonDraft | Synthesized canon document | This phase's artifacts |
| ProfessionalGap | Gap not in any source | umh_professional_gap_register.md |
| OperatorDecision | Question for operator | umh_open_questions_operator_decision_queue.md |
| RatificationPacket | Review package | umh_ratification_packet.md |
| ApprovedCanon | Operator-approved truth | NOT YET |
| WorkPacket | Implementation work item | substrate/organism/work_packet.py |
| DryRunResult | Simulation output | substrate/reality_model/simulation.py |
| ImplementationGate | Pre-implementation checks | substrate/organism/spine_guard.py |
| TestGate | Test verification | pytest suite |
| ProductionTruthPromotion | Promotion record | substrate/organism/production_truth_delta.py |
| DriftSignal | Drift detection | substrate/organism/dex_reconciliation.py |
| CorrectionPacket | Correction input | Phase 14.6B artifacts |

## What This Phase Produces

This phase (14.6B-UMH) operates at stages 1-10 of the lifecycle:
1. Source Inventory (umh_source_inventory.json)
2. Code Truth Inspection (umh_github_codebase_deep_analysis.md, umh_current_implementation_truth.json)
3. Synthesized Canon Draft (umh_lossless_product_canon.md, umh_code_resolved_substrate_canon.md)
4. Professional Gap Register (umh_professional_gap_register.md)
5. Operator Decision Queue (umh_open_questions_operator_decision_queue.md)
6. Ratification Packet (umh_ratification_packet.md)

It does NOT:
- Approve canon (stage 11)
- Create work packets (stage 13)
- Implement anything (stage 15)
- Promote to production truth (stage 17)
