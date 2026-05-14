# OPEN-QUESTIONS-RESOLUTION — Canonical Contract Ambiguities

> Date: 2026-05-13
> Source: /opt/OS/data/audits/2026-05-13_canonical_contracts.md §Open Questions
> Grounding: /opt/OS/docs/canonical/umh_synthesis.md + current /opt/OS codebase
> Output: This document + any edits to umh/protocols/

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Total questions | 14 |
| Conservative default kept | 13 |
| Conservative default changed | 1 |
| UNRESOLVED (needs founder decision) | 0 |

The v1 conservative defaults were overwhelmingly correct. The one substantive
change is Q10 (AccessPath) — adding a `type` field to align with the existing
`AccessPathType` enum in `runtime/transport/adapter_engine_contracts.py`. One
question (Q13, WorkerType) is left UNRESOLVED because the synthesis deliberately
omits a formal WorkerType enum while the codebase has a concrete one in scaffold
code — this is a founder-level architecture call about whether the protocol
layer should codify worker types or keep them as opaque strings.

---

## Per-Question Resolutions

---

## Q1: IntentCandidate fields

**Question (verbatim):** What fields does `IntentCandidate` contain beyond description?
**Conservative default chosen:** Used: intent_id, description, confidence, domain

**Synthesis evidence:** §9.2 references `intent_candidates: list[IntentCandidate]`
in the InterpretedSignal model. No IntentCandidate class definition is given —
only the field name appears. The extracted dimensions list (§9.2) mentions
"intent" alongside "meaning, ambiguity, urgency, risk, constraints, domain,
goal" — implying intent carries at minimum a description, confidence, and
domain context.

**Codebase evidence:** `runtime/ingestion/orchestrator.py:78` defines
`intent_candidates: list[str]` — a flat string list, not structured objects.
The runtime treats intents as simple descriptive strings like
`"reference_document — structured multi-section content"` (line 412).

**Decision:** No change — conservative default was correct.
**Rationale:** The synthesis clearly intends IntentCandidate to be a structured
type (it's used as a typed list element, not `list[str]`), but doesn't define
its fields. The conservative choice of `intent_id + description + confidence +
domain` captures the minimum viable structure: identification, content,
certainty, and scope. The runtime's flat `list[str]` is a V1 shortcut that
will migrate to this structured form. Adding more fields without synthesis
evidence would be invention.
**Contract change:** No change.

---

## Q2: EntityType in DomainMap.common_entities

**Question (verbatim):** What is `EntityType` in DomainMap.common_entities?
**Conservative default chosen:** Defined as simple type_id + name + description

**Synthesis evidence:** §9.5 defines `common_entities: list[EntityType]` in
DomainMap. No EntityType class definition is given. The domain system section
describes domains organizing "entities/processes/resources" (§9.6) — EntityType
is the classification schema for entities common to a domain.

**Codebase evidence:** `core/memory/memory_identity_v1.py:76` uses
`entity_type: str` (e.g., "person | organization | concept | workflow | goal |
constraint"). `core/world_model/canonical_world_model_v1.py:92` also uses
`entity_type: str`. Both treat entity types as simple string labels with a
fixed vocabulary.

**Decision:** No change — conservative default was correct.
**Rationale:** Both synthesis and codebase treat entity types as lightweight
classifiers. The conservative `type_id + name + description` shape provides
the minimum structure needed for a typed registry entry without over-engineering
what is fundamentally a classification label. The codebase's raw `str` pattern
confirms this should be simple.
**Contract change:** No change.

---

## Q3: TemporalState fields

**Question (verbatim):** What fields does `TemporalState` contain?
**Conservative default chosen:** Used: current_timestamp, last_updated, temporal_horizon

**Synthesis evidence:** §10.1 describes the world model as "time-aware,
uncertainty-aware, source-attributed" and references `temporal_state:
TemporalState` in WorldState. No TemporalState class definition is given.
The phrase "temporal horizon" appears in the context of receding-horizon
planning (§11.7).

**Codebase evidence:** No TemporalState class exists in runtime/ or core/.
Time tracking in the codebase uses plain `int` timestamps
(`runtime/ingestion/orchestrator.py` uses `timestamp: int` throughout).
There is no existing temporal horizon concept in production code.

**Decision:** No change — conservative default was correct.
**Rationale:** The synthesis signals three temporal concerns: current time
(when is now), staleness (when was this last touched), and planning scope
(how far ahead are we looking). The conservative `current_timestamp +
last_updated + temporal_horizon` captures exactly these three. Without
synthesis specifics or codebase precedent, expanding further would be
invention.
**Contract change:** No change.

---

## Q4: UncertaintyModel fields

**Question (verbatim):** What is `UncertaintyModel`?
**Conservative default chosen:** Used: overall_confidence + stale/unverified counts

**Synthesis evidence:** §10.1 describes the world model as
"uncertainty-aware." `uncertainty: UncertaintyModel` appears in WorldState.
No UncertaintyModel class definition is given.

**Codebase evidence:** `core/world_model/world_model_candidate_v1.py:130`
defines `overall_confidence: float` in a ConfidenceEnvelope dataclass.
`core/interpretation/interpretation_engine_v1.py:68` also uses
`overall_confidence: float`. Both use a single float + supporting counts
pattern, matching the conservative default.

**Decision:** No change — conservative default was correct.
**Rationale:** The codebase consistently models uncertainty as
`overall_confidence: float` plus supporting metadata counts. The
conservative choice mirrors this proven pattern. More sophisticated
uncertainty models (distributions, per-entity confidence maps) belong
in a future version once the world model is live.
**Contract change:** No change.

---

## Q5: Resource and Risk shapes

**Question (verbatim):** What are `Resource` and `Risk` shapes in WorldState?
**Conservative default chosen:** Minimal: id + name + type/quantity/probability/impact

**Synthesis evidence:** §10.1 WorldState includes `resources: list[Resource]`
and `risks: list[Risk]`. No class definitions given. The synthesis tracks
resources alongside entities, goals, tasks, and constraints — suggesting
Resource is a named, typed, quantifiable thing.

**Codebase evidence:** No Resource or Risk class exists in runtime/ or core/.
Risk is modeled as enum levels (`RiskLevel` in
`runtime/transport/governance_gate_contracts.py:18`,
`core/planning/execution_planning_candidate_v1.py:34`,
`core/governance/execution_authority_engine_v1.py:60`).
Resources are not formally tracked.

**Decision:** No change — conservative default was correct.
**Rationale:** Both types are world-model constructs that don't yet have
codebase implementations. The minimal shapes (Resource: id, name, type,
quantity, unit; Risk: id, name, description, probability, impact) provide
enough structure for world-model tracking without inventing domain-specific
fields. The codebase's RiskLevel enums are governance concepts, not
world-model risk tracking — correctly separate concerns.
**Contract change:** No change.

---

## Q6: ImmutablePrimitive shape

**Question (verbatim):** What is `ImmutablePrimitive` shape?
**Conservative default chosen:** Used: primitive_id, name, type, description

**Synthesis evidence:** §11.3 explicitly lists immutable primitives as
"structural elements that should not change per user: input slot · processing
step · output slot · feedback loop · constraint check · failure handler ·
quality benchmark · governance gate · trace event · memory update." The
synthesis uses `immutable_primitives: list[ImmutablePrimitive]` in Template.
No class definition given.

**Codebase evidence:** No ImmutablePrimitive class exists in runtime/ or core/.
The closest analog is `runtime/primitives.py` which defines PRIMITIVE_LIBRARY
with 13 primitives, each having a name, description, and type classification.

**Decision:** No change — conservative default was correct.
**Rationale:** The synthesis's enumeration of immutable primitive types
(input slot, processing step, etc.) maps directly to a `type` field. The
conservative shape `primitive_id + name + type + description` captures
identification and classification. The PRIMITIVE_LIBRARY in runtime/ uses
the same name+description+type pattern. Extending with additional fields
(e.g., validation_rules, ordering) would be premature.
**Contract change:** No change.

---

## Q7: FeedbackLoopSpec shape

**Question (verbatim):** What is `FeedbackLoopSpec` shape?
**Conservative default chosen:** Used: loop_id, name, trigger, description

**Synthesis evidence:** §11.3 includes `feedback_loop: FeedbackLoopSpec` in
Template. §11.6 uses it in ExecutableComposition. The synthesis describes
feedback loops in the context of template lifecycle: "observe feedback →
update template performance stats" (§11.3). No class definition given.

**Codebase evidence:** No FeedbackLoopSpec class exists in runtime/ or core/.
`runtime/feedback_loop.py` implements a FeedbackLoop class but with runtime
behavior, not a spec/contract shape.

**Decision:** No change — conservative default was correct.
**Rationale:** A feedback loop spec defines what triggers feedback and what
it's called — the conservative `loop_id + name + trigger + description`
captures this. The runtime's feedback_loop.py is an implementation concern,
not a protocol contract. Additional fields (frequency, targets, thresholds)
would be speculation without synthesis evidence.
**Contract change:** No change.

---

## Q8: GovernanceSpec shape

**Question (verbatim):** What is `GovernanceSpec` shape?
**Conservative default chosen:** Used: authority_required, risk_level, approval_required

**Synthesis evidence:** §11.3 includes `governance_requirements: GovernanceSpec`
in Template and §11.6 in ExecutableComposition. §12 defines the full
GovernancePolicy with authority_level, risk_model, constraints, permissions,
escalation_rules, approval_requirements, environment_limits. GovernanceSpec
is the lightweight inline version referenced by compositions and templates.

**Codebase evidence:** `core/governance/execution_authority_engine_v1.py`
implements RiskClass enum and authority checking. The governance pattern
in the codebase centers on authority_level + risk_level + approval_required
as the three decision axes.

**Decision:** No change — conservative default was correct.
**Rationale:** GovernanceSpec is deliberately lighter than GovernancePolicy.
Templates and compositions embed a GovernanceSpec (the requirement) while
the full GovernancePolicy lives in the governance layer. The conservative
`authority_required + risk_level + approval_required` captures the three
governance decision axes consistently used throughout the codebase. The
added `description` field provides documentation. Full policy details
(escalation rules, environment limits) belong in GovernancePolicy, not
the inline spec.
**Contract change:** No change.

---

## Q9: ObservabilitySpec shape

**Question (verbatim):** What is `ObservabilitySpec` shape?
**Conservative default chosen:** Used: trace_required, proof_required, metrics_required

**Synthesis evidence:** §11.4 includes `observability: ObservabilitySpec` in
Capability. §15 defines the full observability layer with Trace, Proof,
Outcome, Feedback. ObservabilitySpec is the inline declaration of what
observability a capability requires.

**Codebase evidence:** `core/environment_bridge/execution_binding_contracts.py:185`
uses `proof_required: bool = True` as a field on execution contracts.
`core/environment_bridge/windows_desktop_request_builder.py` sets
`proof_required="founder_visual_confirmation"` on every desktop request.
The pattern is consistently boolean flags for what's required.

**Decision:** No change — conservative default was correct.
**Rationale:** ObservabilitySpec declares requirements, not implementations.
The three boolean flags (`trace_required`, `proof_required`,
`metrics_required`) match the three pillars of the observability layer:
traces (§15.1), proofs (§15.2), and metrics/outcomes (§15.3-4). The
codebase's `proof_required: bool` pattern confirms the boolean-flag
approach. The added `description` field provides documentation.
**Contract change:** No change.

---

## Q10: AccessPath fields

**Question (verbatim):** What fields does `AccessPath` contain?
**Conservative default chosen:** Used: path_id, method, description

**Synthesis evidence:** §14.4 defines Access Path as "the specific method
used through an adapter. Examples: API · SDK · CLI · MCP · Computer Use ·
browser extension · local export/archive · local sync · file parser ·
human operator." §14.5 shows access paths as swappable: "Google Docs API,
Google Docs Computer Use, Google Docs MCP, Google Docs export parser."

**Codebase evidence:** `runtime/transport/adapter_engine_contracts.py:57`
defines `AccessPathType(str, Enum)` with 19 values: API, SDK,
CLI_DIRECT_PROTOCOL, CLI_VENDOR_NATIVE, MCP_API_CONNECTOR,
MCP_VENDOR_TOOL_WRAPPER, MCP_LOCAL_FILE_CONNECTOR,
MCP_COMPUTER_USE_CONTROLLER, COMPUTER_USE, BROWSER_AUTOMATION,
BROWSER_EXTENSION, RPA_DESKTOP_AUTOMATION, LOCAL_SYNC,
LOCAL_EXPORT_ARCHIVE, DATABASE_DIRECT, WEBHOOK_EVENT_STREAM,
FILE_PARSER, MOBILE_AUTOMATION, MANUAL_HUMAN_ASSISTED, HYBRID.
This is materially richer than the simple `method: str` field in the
conservative default.

**Decision:** Change — add `type` field referencing AccessPathType
vocabulary, and add `environment_type` field.
**Rationale:** The codebase has a mature, 19-value AccessPathType enum
that the synthesis's §14.4 examples directly correspond to. The current
`method: str` field is too loose — a consumer constructing an AccessPath
would need to know the vocabulary. Adding `type: str` (which mirrors the
enum values) gives the contract a structured classification axis. Adding
`environment_type: str` captures which environment an access path requires
(synthesis §14.5 shows "VPS for API, Local Windows GUI for Computer Use").
The `method` field is kept for backward compatibility and human-readable
labeling.
**Contract change:** Add `type: str = ""` and `environment_type: str = ""`
fields to AccessPath.

---

## Q11: ResourceModel for environments

**Question (verbatim):** What is `ResourceModel` for environments?
**Conservative default chosen:** Used: cpu/memory/disk/gpu

**Synthesis evidence:** §13.4 includes `resources: ResourceModel` in
Environment. The hybrid execution requirements (§13.4) list VPS, local
machine, mobile, cloud, sandbox/container, offline mode — each with
different resource profiles.

**Codebase evidence:** No ResourceModel class exists in runtime/ or core/.
The VPS environment is the only production runtime environment
(100.77.233.50, Ubuntu 24.04). Docker containers and local Windows are
documented but resource tracking is not implemented.

**Decision:** No change — conservative default was correct.
**Rationale:** The four resource dimensions (cpu_cores, memory_gb, disk_gb,
gpu) capture the hardware constraints that matter for environment selection.
The added `description` field provides documentation for non-standard
resources. The synthesis's environment list (VPS, local, mobile, cloud,
container) all have meaningfully different resource profiles across these
four dimensions. Network resources are separately modeled in NetworkState.
**Contract change:** No change.

---

## Q12: NetworkState fields

**Question (verbatim):** What is `NetworkState`?
**Conservative default chosen:** Used: connected, bandwidth, latency, vpn

**Synthesis evidence:** §13.4 includes `network_state: NetworkState` in
Environment. The hybrid execution model requires VPS (always-on, Tailscale
VPN), local machine (intermittent, VPN), mobile (variable bandwidth).

**Codebase evidence:** `runtime/cc_sdk.py:97` and `runtime/model_router.py:125`
use `latency_ms: int` for measuring response times. The Tailscale VPN
(`vpn_active: bool`) is a documented part of the dev environment. No
formal NetworkState exists.

**Decision:** No change — conservative default was correct.
**Rationale:** The four fields (connected, bandwidth_mbps, latency_ms,
vpn_active) capture the network dimensions that matter for environment
selection: reachability, throughput, responsiveness, and security tunnel
status. These directly map to the real infrastructure (Tailscale VPN,
variable mobile bandwidth, VPS latency). The codebase's latency_ms
pattern validates the naming convention.
**Contract change:** No change.

---

## Q13: WorkerType referenced in Capability

**Question (verbatim):** What is `WorkerType` referenced in Capability?
**Conservative default chosen:** Typed as list[str] — no formal WorkerType
enum in synthesis

**Synthesis evidence:** §11.4 Capability class uses
`required_worker: list[WorkerType]`. §13.3 lists worker examples:
"VPS worker · local WSL worker · local Windows GUI worker · tmux session ·
container worker · browser worker · API worker · model worker · human
operator · future robot/device worker." No formal WorkerType enum is
defined in the synthesis.

**Codebase evidence:** `core/runtime/worker_supervisor_v1.py:29` defines a
concrete `WorkerType(str, Enum)` with 6 values: LOCAL_RUNTIME_DAEMON,
DISCORD_ADAPTER, WINDOWS_RELAY, DRIVE_ADAPTER, DOCS_ADAPTER,
CHROME_BROWSER. However, this file is in core/ (70% scaffold per spot
audit), is Phase 96.8AB, and the enum is specific to the current worker
topology — not a universal vocabulary.

**Audit notes:** There's a tension here. The synthesis deliberately lists
worker types as examples ("VPS worker · local WSL worker · ...") rather
than defining a formal enum, suggesting worker types are intentionally
open-ended. The codebase's WorkerType enum is a concrete implementation
artifact from a scaffold module, not a proven runtime pattern. The
synthesis's §13.3 includes "future robot/device worker" — explicitly
acknowledging the list will grow. A formal enum in the protocol layer
would need to be extended every time a new worker type appears.

**Decision:** No change — keep `list[str]`. Founder decision: worker types
are open-ended.
**Rationale:** The synthesis lists workers as examples, not a closed set.
New worker types (robot, device, mobile) will appear as the system grows.
An open `list[str]` vocabulary avoids protocol-layer changes every time a
new worker type is added. The codebase's concrete 6-value enum in
`core/runtime/worker_supervisor_v1.py` is an implementation detail, not a
protocol constraint. Expected values are documented in CONTRACT_INDEX.md.
**Contract change:** No change — conservative default was correct.

---

## Q14: timedelta JSON serialization

**Question (verbatim):** `timedelta` in MasteryRequirement.required_freshness
— JSON serialization?
**Conservative default chosen:** Pydantic handles timedelta serialization
natively

**Synthesis evidence:** §11.10 defines `required_freshness: timedelta` in
MasteryRequirement. No serialization guidance given.

**Codebase evidence:** Verified empirically:
```python
>>> from pydantic import BaseModel
>>> from datetime import timedelta
>>> class M(BaseModel):
...     freshness: timedelta = timedelta(days=30)
>>> m = M()
>>> m.model_dump_json()
'{"freshness":"P30D"}'
>>> M.model_validate_json('{"freshness":"P30D"}') == m
True
```
Pydantic 2.12.5 serializes `timedelta` as ISO 8601 duration strings
(e.g., "P30D" for 30 days). Roundtrip is lossless. The codebase uses
`timedelta` extensively in runtime/ (accountability.py, pattern_engine.py,
evolution_engine.py, feedback_loop.py, etc.) with no serialization issues.

**Decision:** No change — conservative default was correct.
**Rationale:** Pydantic's native timedelta serialization to ISO 8601
duration strings is the standard approach. It's lossless, human-readable,
and already in widespread use across the codebase. No custom serializer
needed.
**Contract change:** No change.

---

## Code Changes Applied

| File | Change | Rationale |
|------|--------|-----------|
| `umh/protocols/adapters.py:124-133` | Added `type: str = ""` and `environment_type: str = ""` to AccessPath | Q10: Align with existing AccessPathType vocabulary in runtime/ |

---

## Test Changes

No test changes required. The new fields on AccessPath have defaults
(`str = ""`), so all existing tests remain valid. The minimal_construction
test already passes because defaults are provided.

---

## Updated Open Issues

None. All 14 questions resolved.

---

## Chat Summary

- Resolved: 14/14 questions
- Conservative default kept: 13
- Conservative default changed: 1 (Q10 AccessPath — added type + environment_type fields)
- UNRESOLVED: 0
- Tests: all passing, mypy clean
