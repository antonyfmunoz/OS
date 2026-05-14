# UMH Protocol Contracts — Index

Generated from `/opt/OS/docs/canonical/umh_synthesis.md` §25 Protocol Pack
and contract definitions from Parts III–V.

## File Layout

| File | Source §§ | Layer |
|------|-----------|-------|
| common.py | §6, §5 | Shared enums, refs, base types |
| control_plane.py | §8 | Layer 2 — Control Plane |
| understanding.py | §9.1, §9.2, §9.5, §6.4 | Layer 3 — Understanding |
| state.py | §10.1, §10.2 | Layer 4 — State |
| composition.py | §11.1, §11.3, §11.4, §11.6, §11.10 | Layer 5 — Composition |
| governance.py | §12 | Layer 6 — Governance |
| execution.py | §13.1, §13.2, §13.4 | Layer 7 — Execution Plane |
| adapters.py | §14.1, §14.3 | Layer 8 — Adapter Boundary |
| observability.py | §15.1, §15.2 | Layer 9 — Observability + Proof |
| learning.py | §16.2 | Layer 10 — Learning + Self-Regulation |

## Contract Manifest

### common.py — Shared Types

**Enums (StrEnum):**
- SignalModality
- PrimitiveType (10 core: state, change, constraint, resource, time, signal, feedback, goal, action, outcome)
- RelationshipType
- AuthorityLevel (autonomous, notify, approve, escalate, deny)
- RiskLevel
- MemoryType (14 types)
- PromotionStatus
- MasteryCategory (11 categories)
- MasteryStatus
- ItemStatus
- EnvironmentType
- AdapterCategory (15 categories)
- MaturityStatus
- EvidenceType
- ConfirmationStatus
- PacketStatus
- ApprovalStatus
- SignalType
- Severity

**Ref models (lightweight pointers):**
- EvidenceRef
- EnvironmentRef
- CapabilityRef
- AdapterRef
- WorkerRef
- TemplateRef
- WorkflowRef
- MemoryRef
- GovernancePolicyRef
- AdapterPackageRef
- MasteryRef
- RelationshipRef
- TestRef

**Sub-models:**
- CostModel
- LatencyModel
- Constraint
- FailureMode
- Slot
- Step
- ProofRequirement
- Benchmark
- AuthorityContext

### control_plane.py — §8

- ControlPlaneEvent

### understanding.py — §9.1, §9.2, §9.5, §6.4

- Signal (§9.1)
- IntentCandidate
- InterpretedSignal (§9.2)
- DomainLaw
- SlotSpec
- DomainMap (§9.5)
- Primitive
- Relationship
- PrimitiveMapping (§6.4)

### state.py — §10.1, §10.2

- Entity (§10.1)
- Fact (§10.1)
- WorldState (§10.1)
- MemoryRecord (§10.2)

### composition.py — §11.1, §11.3, §11.4, §11.6, §11.10

- RegistryItem (§11.1)
- ImmutablePrimitive
- FeedbackLoopSpec
- GovernanceSpec
- MemoryUpdateRule
- QualityCriterion
- Template (§11.3)
- ObservabilitySpec
- Capability (§11.4)
- Dependency
- ExecutableComposition (§11.6)
- MasteryGap
- MasteryRequirement (§11.10)

### governance.py — §12

- Permission
- EscalationRule
- ApprovalRequirement
- EnvironmentLimit
- RiskModel
- GovernancePolicy

### execution.py — §13.1, §13.2, §13.4

- StateTransition
- SuccessCriterion
- ActionContract (§13.1)
- OutputSpec
- WorkPacket (§13.2)
- ResourceModel
- NetworkState
- Environment (§13.4)

### adapters.py — §14.1, §14.3

- Adapter (typing.Protocol — 8 methods) (§14.1)
- Connection
- ValidationResult
- ExternalRequest
- ExternalResponse
- NormalizedResult
- StateSnapshot
- AccessPath
- AdapterPackage (§14.3)

### observability.py — §15.1, §15.2

- TimestampSet
- ExecutionResult
- Outcome
- FeedbackEvent
- GovernanceDecision
- WorldStateSnapshot
- Trace (§15.1)
- ParityResult
- ProofArtifact (§15.2)

### learning.py — §16.2

- InternalSignal

## Total Contracts

- **18 enums**
- **13 ref types**
- **9 shared sub-models**
- **~45 primary models**
- **1 typing.Protocol (Adapter)**
- **= ~86 total type definitions**
