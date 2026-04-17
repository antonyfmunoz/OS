# LLM Planning Layer — Design Specification

**Date:** 2026-04-17
**Status:** Approved
**Author:** AFM + Developer Agent

## Purpose

Introduce a non-deterministic LLM-based planning layer on top of the
existing deterministic intent/planner system. The LLM proposes candidate
events; the system validates, records, and emits them. Replay produces
identical system behavior without calling the LLM.

This is controlled, auditable, replay-safe non-determinism inside the
planning layer — not a replacement for it.

## Scope

**In scope:**
- `LLMPlanningStrategy` — constrained plan proposer
- `ReplayableStrategy` — determinism boundary and `DecisionStrategy` impl
- `EventTypeRegistry` — authoritative validation layer
- Observability events for every code path
- Replay-safe test suite
- Integration into `IntentAwareStrategy` priority chain

**Out of scope:**
- Modifications to `PlannerStrategy` or `RuleBasedStrategy`
- Changes to `DecisionEngine`
- New event types in the scheduler (only new observability events)
- LLM as decision authority (it proposes, system decides)

## Architecture

### Component Hierarchy

```
IntentAwareStrategy (modified)
  priority: llm_planner -> PlannerStrategy -> RuleBasedStrategy
            (single slot)

llm_planner = ReplayableStrategy(LLMPlanningStrategy(...))
```

### ReplayableStrategy

Implements `DecisionStrategy`. Owns the determinism boundary.

Responsibilities:
- Config enforcement (enabled, intent type eligibility)
- State canonicalization before any downstream use
- Replay store (internal, not injected)
- `llm_fn` timeout enforcement
- Selection policy application
- `SchedulerEvent` emission into the scheduler
- Full pipeline record capture
- Sentinel `DecisionOutput` construction

The sentinel `DecisionOutput` is a **control signal**, not a domain
decision. It tells `IntentAwareStrategy` "I handled this, stop the
chain." It carries:
- `event_type = "llm_proposal_accepted"`
- `is_terminal = True`
- `suppress_downstream = True`

Invariant: if `event_type == "llm_proposal_accepted"`, it must not
emit further events or be processed as a normal decision.

### LLMPlanningStrategy

Subordinate component. Does NOT implement `DecisionStrategy`.

Responsibilities:
- Prompt construction from canonical state + intents + registry
- `llm_fn` invocation (the sole non-deterministic boundary)
- Strict JSON parsing
- Canonical normalization
- Validation against `EventTypeRegistry`
- Returns `LLMProposalResult` (never `DecisionOutput`)

### EventTypeRegistry

Authoritative registry of valid event types. Independent from the
scheduler's subscriber map. Defines what the LLM is allowed to emit,
not what currently has handlers.

## Data Models

### ProposedEvent

```python
@dataclass(frozen=True)
class ProposedEvent:
    event_type: str
    payload: dict[str, Any]
    description: str | None = None
```

### LLMEventProposal

```python
@dataclass(frozen=True)
class LLMEventProposal:
    events: tuple[ProposedEvent, ...]
    proposal_id: str          # sha256(canonical_json)
    reasoning: str | None = None
```

`proposal_id` derivation:
- Parse succeeds: `sha256(canonical_json)`
- Parse fails: `sha256(raw_response)`
- Always exists. Traceability is never broken.

`reasoning` is non-authoritative. Stored as hash only in replay
records. Raw text stored in observability events for debugging.
Never used in validation, selection, or replay logic.

### LLMProposalResult

```python
@dataclass(frozen=True)
class LLMProposalResult:
    prompt_hash: str
    raw_response: str
    response_hash: str
    canonical_json: str | None
    proposal: LLMEventProposal | None
    validation: ValidationResult | None
    latency_ms: int
```

### ValidationResult

```python
@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    accepted_events: tuple[ProposedEvent, ...]
    rejected_events: tuple[ProposedEvent, ...]
    rejection_reasons: dict[int, str]  # index -> reason
```

### EventSchema

```python
@dataclass(frozen=True)
class EventSchema:
    event_type: str
    required_fields: frozenset[str]
    optional_fields: frozenset[str]
    field_types: dict[str, type] | None = None
    event_version: int = 1
    is_mutation: bool = True  # False for observability events
```

Runtime enforcement: if `is_mutation=False`, any handler returning
mutations for that event type raises a violation.

### LLMDecisionRecord

```python
@dataclass(frozen=True)
class LLMDecisionRecord:
    schema_version: int
    validation_version: int
    schema_hash: str               # hash of registry state at validation time
    state_hash: str
    prompt_hash: str               # composite: prompt + model + temp + versions
    raw_response: str
    response_hash: str
    canonical_json: str
    proposal_id: str
    reasoning_hash: str            # hash of reasoning, not raw text
    validation_result: ValidationResult
    emitted_events: tuple[ProposedEvent, ...]
    selected_event_indices: tuple[int, ...]
    selection_policy: str          # policy name at time of decision
    timestamp: str                 # ISO UTC
```

### SelectionPolicy

```python
class SelectionPolicy(str, Enum):
    ALL = "all"
    FIRST = "first"
```

### LLMPlannerConfig

```python
@dataclass
class LLMPlannerConfig:
    enabled: bool = False
    enabled_intent_types: set[IntentType] | None = None
    replay_mode: bool = False
    strict_replay_validation: bool = True
    selection_policy: SelectionPolicy = SelectionPolicy.ALL
    max_events_per_proposal: int = 5
    max_prompt_tokens: int = 4000
    max_payload_bytes_per_event: int = 8192
    max_payload_bytes_total: int = 32768
    timeout_ms: int = 30000
    config_version: int = 1
    model_name: str = ""
    temperature: float = 0.0
    truncation_priority: tuple[str, ...] = (
        "metadata:", "history:", "payload:", "core:",
    )
    max_array_elements: int = 20
```

Config is enforced inside `ReplayableStrategy`, not at the
orchestration layer.

## Event Type Registry

### Validation Pipeline

```
LLM raw text
-> strict JSON parse (fail = fallback)
-> normalization (canonical form, deterministic)
-> schema validation:
   - event_type exists in registry
   - required fields present
   - no unknown fields
   - field types match (when declared)
   - payload size within limits (per-event and total)
   - event count within max_events_per_proposal
-> transform ProposedEvent -> SchedulerEvent
-> emit via scheduler
```

### Registry Independence

The registry is authoritative and independent from the scheduler's
subscriber map. It defines what the LLM is allowed to propose.
Event types can exist in the registry without active handlers.

### Type Validation Semantics

`field_types` maps field names to Python types. Validation uses
`isinstance(payload[field], expected_type)`. Only top-level fields
are type-checked. Nested dicts and lists are validated by presence
only — deep type validation is out of scope for this layer.
Supported types: `str`, `int`, `float`, `bool`, `list`, `dict`.

### Schema Hash

`EventTypeRegistry` exposes a `schema_hash` property: the hash of
all registered schemas in canonical form. Stored in
`LLMDecisionRecord.schema_hash` for replay compatibility checks.

## Flows

### Cache Miss (Live LLM Call)

```
state
-> canonicalize (sorted keys, deterministic serialization)
-> hash state
-> ReplayableStrategy checks config
   -> disabled? emit SKIPPED, return None
   -> intent type excluded? emit SKIPPED, return None
-> replay store lookup -> miss
-> LLMPlanningStrategy.propose(canonical_state)
   -> build prompt (deterministic function of inputs)
   -> emit LLM_DECISION_REQUESTED
   -> call llm_fn(prompt) with timeout
      -> timeout? emit LLM_DECISION_REJECTED(reason="timeout"), return None
   -> emit LLM_DECISION_RECEIVED
   -> strict JSON parse
      -> fail? emit LLM_DECISION_REJECTED(reason="parse_error"), return None
   -> normalize to canonical form
   -> validate against EventTypeRegistry
      -> all rejected? emit LLM_DECISION_REJECTED, return None
   -> return LLMProposalResult
-> apply SelectionPolicy
-> emit selected SchedulerEvents
   (each carries proposal_id + proposal_step_index in metadata)
-> emit LLM_DECISION_ACCEPTED
-> store LLMDecisionRecord (full pipeline trace)
-> return sentinel DecisionOutput
   (is_terminal=True, suppress_downstream=True)
```

### Cache Hit (Replay)

```
state
-> canonicalize
-> hash state
-> ReplayableStrategy checks config
-> replay store lookup -> hit
-> load LLMDecisionRecord
-> if strict_replay_validation:
   -> re-validate canonical_json against current registry
   -> if validation fails: return None (fall through to planner)
-> re-emit SchedulerEvents from stored emitted_events
   (preserving proposal_step_index ordering)
-> return sentinel DecisionOutput
```

### Fallback Paths

Every failure returns None, falling through to PlannerStrategy:
- Config disabled -> SKIPPED
- Intent type excluded -> SKIPPED
- llm_fn timeout -> REJECTED
- JSON parse failure -> REJECTED
- All events rejected by validation -> REJECTED
- Replay strict mode validation failure -> fall through silently

The LLM layer can never block execution.

## Observability Events

Six event types, all registered with `is_mutation=False`:

| Event Type | When | Key Fields |
|---|---|---|
| `llm_decision_requested` | Before LLM call | state_hash, prompt_hash, active_intent_ids |
| `llm_decision_received` | LLM response parsed | proposal_id, prompt_hash, response_hash, event_count, latency_ms |
| `llm_decision_accepted` | Proposal validated and emitted | proposal_id, emitted_event_count, selection_policy |
| `llm_decision_rejected` | Validation rejects (partial or full) | proposal_id, prompt_hash, rejection_reason, rejected_event_count |
| `llm_decision_skipped` | LLM layer bypassed | reason, state_hash |
| `llm_response_drift` | Same prompt_hash, different response | prompt_hash, response_hash_a, response_hash_b |

All carry `decision_phase` for step-level tracing.
Optional: `state_hash_before` / `state_hash_after` for debugging.

## Emitted SchedulerEvent Guarantees

Every `SchedulerEvent` produced from a `ProposedEvent` carries:
- `metadata.proposal_id` — which proposal produced it
- `metadata.proposal_step_index` — position in proposal sequence
- `source` — `"llm_planner"`

Ordering: events are emitted in `proposal_step_index` order.
Consumers must respect `proposal_step_index` for correct sequencing.

Invariant: emitted SchedulerEvents are a deterministic function of
`canonical_proposal + config (including selection_policy)`.

## Prompt Construction

### Structure

```
System instruction (role, constraints, output format)
Schema version: {registry.version}
Event catalog (from registry, filtered to relevant types)
State snapshot (canonical JSON, truncated)
Active intents (serialized)
Output schema (exact JSON structure)
```

### Determinism

The prompt is a pure function of its inputs. No randomness,
no timestamps, no UUIDs.

### Prompt Hash (Composite)

```python
prompt_hash = sha256(canonical({
    "prompt": prompt_string,
    "model": model_name,
    "temperature": temperature,
    "config_v": config_version,
    "registry_v": registry_version,
}))
```

### State Truncation Algorithm

Strict, reproducible:
1. Serialize state as sorted canonical JSON
2. If within budget, use as-is
3. Drop keys by priority tier (configured in `truncation_priority`)
4. Within each tier, drop keys in reverse lexicographic order
5. Arrays truncated to first N elements (`max_array_elements`)
6. After each drop, re-check budget
7. Same state + same config = same truncated output, always

### JSON Output Enforcement

Enforced via strict parsing + rejection at the validation boundary.
Prompt instructions constrain the LLM but are not relied upon for
correctness. The system rejects invalid output regardless of what
the prompt says.

## Canonicalization

All strategies operate only on canonicalized state.

Canonical form:
- `json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`
- Consistent with existing `_compute_state_hash()` in `decision_engine.py`
- Float normalization: `repr()` for consistent representation
- Unicode: NFC normalization applied before serialization
- Empty vs null: preserved as-is (no coercion)

## Integration

### IntentAwareStrategy Modification

```python
class IntentAwareStrategy:
    def __init__(
        self,
        planner: PlannerStrategy | None = None,
        fallback: Any | None = None,
        llm_planner: ReplayableStrategy | None = None,
    ) -> None:
        ...

    def evaluate(self, state: dict[str, Any]) -> DecisionOutput | None:
        # 1. LLM planner (if present)
        if self._llm_planner is not None:
            result = self._llm_planner.evaluate(state)
            if result is not None:
                return result

        # 2. Deterministic planner
        result = self._planner.evaluate(state)
        if result is not None:
            return result

        # 3. Rule-based fallback
        if self._fallback is not None:
            return self._fallback.evaluate(state)

        return None
```

No other files in the existing system are modified.

### Wiring (At Construction Time)

```python
registry = EventTypeRegistry()
# ... register schemas ...

config = LLMPlannerConfig(enabled=True, model_name="gemini-2.5-flash")

llm_strategy = LLMPlanningStrategy(
    llm_fn=lambda prompt: call_with_fallback(prompt=prompt, ...),
    registry=registry,
    config=config,
)

replayable = ReplayableStrategy(
    inner=llm_strategy,
    scheduler=scheduler,
    config=config,
)

strategy = IntentAwareStrategy(
    planner=PlannerStrategy(),
    fallback=RuleBasedStrategy(rules),
    llm_planner=replayable,
)

engine = DecisionEngine(strategy=strategy)
```

## Invariants

1. LLM cannot invent event types or bypass validation.
2. Every failure path falls through to the deterministic planner.
3. Replay reproduces full decision trace, not just output.
4. Sentinel DecisionOutput is a control signal, not a domain decision.
5. Observability covers every code path.
6. `llm_fn` is the sole non-deterministic boundary.
7. All hashes are composite (prompt + model + temp + versions).
8. Emitted SchedulerEvents are a deterministic function of
   canonical_proposal + config.
9. All strategies operate only on canonicalized state.
10. selection_policy is part of the replay identity.
11. Observability events are non-mutating at the schema level.
12. proposal_id always exists (derived from response if parse fails).

## Deliverables

| File | Type |
|---|---|
| `eos_ai/substrate/llm_planner.py` | New |
| `eos_ai/substrate/llm_replay.py` | New |
| `eos_ai/substrate/llm_decision_events.py` | New |
| `eos_ai/substrate/planner.py` | Modified |
| `tests/test_llm_planner.py` | New |
| `tests/test_llm_replay.py` | New |
| `tests/test_llm_integration.py` | New |

## Testing Strategy

### Unit Tests — LLMPlanningStrategy

- propose() with valid JSON -> correct LLMProposalResult
- propose() with malformed JSON -> proposal=None
- propose() with unknown event_type -> validation rejects
- propose() with missing required fields -> rejects
- propose() with wrong field types -> rejects
- propose() with too many events -> rejects
- propose() with oversized payload -> rejects
- prompt determinism (same state -> same prompt)
- canonical normalization determinism

### Unit Tests — ReplayableStrategy

- config disabled -> None, emits SKIPPED
- intent type excluded -> None, emits SKIPPED
- cache miss -> calls inner, stores record, emits events + sentinel
- cache hit -> skips inner, re-emits from stored record
- cache hit + strict mode + registry change -> re-validates
- cache hit + strict mode + validation failure -> returns None
- llm_fn timeout -> emits REJECTED, returns None
- invalid proposal -> returns None, falls through
- sentinel has is_terminal=True, suppress_downstream=True
- all SchedulerEvents carry proposal_id + proposal_step_index
- full LLMDecisionRecord captured

### Integration Tests

- LLM valid -> chain stops, planner not called
- LLM None -> planner called
- LLM disabled -> planner called directly
- LLM fails -> planner called (silent fallback)
- all three None -> None

### Replay Tests

- record then replay -> identical SchedulerEvents
- same state_hash -> same events, no llm_fn call
- different state_hash -> cache miss, llm_fn called
- registry change + strict -> re-validation
- registry change + non-strict -> stored result used
- schema_version migration
- full round-trip comparison

### Concurrency Tests

- parallel evaluate() same state -> single llm_fn call
- parallel evaluate() different states -> independent records
- replay store under contention -> no corruption

### Idempotency Tests

- replayed events with same event_id -> scheduler dedup
- replayed events produce identical handler results

### Fuzz Tests

- partial JSON, wrong structure, wrong types, extra fields
- empty events array, unicode edge cases, oversized payloads

### Canonicalization Edge Cases

- dict key ordering stability
- float normalization (0.0 vs -0.0)
- unicode NFC normalization
- empty vs null vs missing fields

### Drift Detection

- same prompt_hash + different response -> LLM_RESPONSE_DRIFT emitted
- drift does not block execution
