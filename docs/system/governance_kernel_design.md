# Governance Kernel Design

**Version:** 1.0
**Date:** 2026-05-27
**Status:** Design document — unification plan for governance convergence

---

## Current State

11 governance components exist across 3 layers:

### Layer 1: Signal-Level Classification
| Component | File | What it does | Production? |
|-----------|------|-------------|-------------|
| ConcreteGovernanceEngine | control_plane/governance.py | Regex-based risk classification on signal content | YES (facade) |
| AuthorityEngine | governance/policy/authority_engine.py | Action-type risk classification + approval queue | YES (cognitive loop) |

### Layer 2: Execution-Level Governance
| Component | File | What it does | Production? |
|-----------|------|-------------|-------------|
| PolicyEngine | governance/policy_engine.py | Capability-level side-effect governance | YES (facade + cockpit) |
| ExecutionAuthorityEngine | governance/policy/execution_authority_engine_v1.py | Multi-dimensional authority for WorkPackets | Partial (WorkPacket path) |
| SimulationReality | reality_model/simulation.py | Non-mutating hypothesis testing | YES (spine HIGH/CRITICAL) |
| DeliberationCouncil | understanding/deliberation/council.py | Multi-perspective advisory (7 roles) | YES (spine HIGH/CRITICAL) |

### Layer 3: Output/Quality Governance
| Component | File | What it does | Production? |
|-----------|------|-------------|-------------|
| QualityTransformationGate | governance/quality/quality_gate.py | 4-value output quality scoring | YES (gateway output) |
| OutputValidator | governance/validation/output_validator.py | Discord message constraint validation | Partial |
| CompletenessEngine | governance/validation/completeness_engine.py | 13-slot plan completeness validation | No (pipeline only) |
| PrincipleEngine | governance/principles/principle_engine.py | Quality standard prompt injection | YES (gateway) |
| LawRegistry | ontology/laws.py | 14 substrate law constraints | Partial (understanding bridge) |

---

## Target: Unified GovernanceKernel

The GovernanceKernel processes signals through an ordered pipeline of gates.
Each gate is a pure function: `(signal, context) → verdict`.

### Gate Pipeline (ordered)

```
1. STRUCTURAL_DENY
   → Is this signal structurally invalid? (malformed, missing fields, blocked source)
   → Existing: None (new, trivial)

2. LAW_CHECK
   → Does this violate substrate laws?
   → Existing: LawRegistry.check()

3. RISK_CLASSIFICATION
   → What risk class does this signal carry?
   → Existing: ConcreteGovernanceEngine._classify_risk() (content regex)
   → Existing: AuthorityEngine.classify_action() (action type table)
   → Merge: Use AuthorityEngine's table for action types, regex for content. Single output.

4. PERMISSION_TIER
   → Does the actor have permission for this risk class?
   → Existing: AuthorityEngine.check_can_execute()

5. AUTONOMY_LEVEL
   → What autonomy level does the org have? (from BIS)
   → Existing: AuthorityEngine._get_autonomy_stage()

6. AUTHORITY_PROOF
   → For WorkPacket execution: multi-dimensional authority check
   → Existing: ExecutionAuthorityEngine.evaluate()
   → Only applies to WorkPacket execution path, not chat

7. ENVIRONMENT_POLICY
   → Is this action allowed in the current environment?
   → Existing: PolicyEngine.evaluate() (side-effect categories)

8. SIMULATION
   → For HIGH/CRITICAL: dry-run in ephemeral sandbox
   → Existing: SimulationReality.simulate()
   → Only runs for HIGH/CRITICAL risk

9. DELIBERATION
   → For HIGH/CRITICAL: multi-perspective advisory
   → Existing: DeliberationCouncil.deliberate()
   → Only runs for HIGH/CRITICAL risk

10. APPROVAL_REQUIREMENT
    → Does this need human approval?
    → Existing: AuthorityEngine.execute_or_queue()

11. OUTPUT_VALIDATION
    → Post-execution: is the output safe to deliver?
    → Existing: OutputValidator.validate_discord_message()
    → Existing: QualityTransformationGate.transform()

12. QUALITY_GATE
    → Post-execution: does the output meet quality standards?
    → Existing: QualityTransformationGate (4-value scoring)
    → Existing: PrincipleEngine (prompt injection)

13. COMPLETENESS_CHECK
    → Post-execution: is the plan/workflow complete?
    → Existing: CompletenessEngine.evaluate_pipeline_result()

14. AUDIT_PROOF
    → Record the governance decision chain
    → Existing: ExecutionAuthorityEngine.create_proof()
```

---

## What Stays

| Component | Role in Kernel | Notes |
|-----------|---------------|-------|
| AuthorityEngine | Gates 3-5, 10 | Core authority system, keep as-is |
| PolicyEngine | Gate 7 | Side-effect classification, keep |
| QualityTransformationGate | Gates 11-12 | Output quality, keep |
| SimulationReality | Gate 8 | Simulation sandbox, keep |
| DeliberationCouncil | Gate 9 | Multi-perspective advisory, keep |
| LawRegistry | Gate 2 | Substrate law checks, keep |

## What Merges

| Source | Target | How |
|--------|--------|-----|
| ConcreteGovernanceEngine._classify_risk() | AuthorityEngine | Regex patterns become another input to AuthorityEngine's risk classification |
| ConcreteGovernanceEngine.evaluate_action() | AuthorityEngine (direct) | Remove facade indirection — callers go straight to AuthorityEngine |
| ConcreteGovernanceEngine.evaluate_capability() | PolicyEngine (direct) | Remove facade indirection |
| ConcreteGovernanceEngine.evaluate_quality() | QualityTransformationGate (direct) | Remove facade (has API mismatch bug anyway) |

## What Becomes Adapter

| Component | Role | Notes |
|-----------|------|-------|
| OutputValidator | Transport-specific adapter | Discord-specific validation becomes a transport concern |

## What Is Deprecated

| Component | Reason | Timeline |
|-----------|--------|----------|
| ConcreteGovernanceEngine (facade) | All delegation has API mismatches; callers should go direct | After convergence Phase 2 |
| ExecutionAuthorityEngine | Conceptually sound but duplicates AuthorityEngine with more dimensions. Merge the multi-dimensional model into AuthorityEngine. | After convergence Phase 3 |

## Known Bugs to Fix

1. **ConcreteGovernanceEngine.evaluate_quality()** calls `gate.transform(output, context)` with wrong signature (needs 4 args). Silent failure returns `{"score": 0.5, "passed": True}`.

2. **RiskClass naming collision**: `substrate/governance/risk_classes.py` defines `ActionRiskCategory` aliased as `RiskClass`, which shadows `substrate.types.RiskClass`. Different enums with different values.

## Migration Order

1. **Safe**: Fix the evaluate_quality() API mismatch bug
2. **Safe**: Fix the RiskClass naming collision — rename alias to `ActionRiskCategory` everywhere
3. **Medium**: Have cognitive_loop call AuthorityEngine directly instead of through facade
4. **Medium**: Move OutputValidator to transports/discord/ as a transport concern
5. **High**: Merge ExecutionAuthorityEngine dimensions into AuthorityEngine
6. **High**: Replace ConcreteGovernanceEngine facade with GovernanceKernel pipeline
7. **Post-merge**: Wire LawRegistry checks into the kernel pipeline

## Tests Required

- Risk classification: same input → same risk class across old and new systems
- Authority check: approval requirements don't change for existing action types
- Quality gate: 4-value scoring produces same scores
- Simulation: HIGH/CRITICAL signals still trigger simulation
- Deliberation: council still convenes for HIGH/CRITICAL
- Approval queue: pending approvals still accessible
