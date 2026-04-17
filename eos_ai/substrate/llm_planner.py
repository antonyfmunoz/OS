"""
LLM planning strategy — constrained plan proposer.

Proposes candidate events based on state + active intents, validates
them against an authoritative EventTypeRegistry, and returns a
structured result bundle.  This module NEVER emits events, writes
state, or constructs DecisionOutput.  It is a subordinate component
owned by ReplayableStrategy.

Design constraints:
- llm_fn is the sole non-deterministic boundary.
- Prompt construction is a pure function of its inputs.
- Canonicalization uses NFC unicode + float repr() + sorted keys.
- Validation is authoritative: the registry defines what the LLM
  may propose.  Independent from the scheduler subscriber map.

Integration:
    ReplayableStrategy calls LLMPlanningStrategy.propose() and
    handles timeout, replay, event emission, and DecisionOutput.
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from eos_ai.substrate.intent_models import IntentType

_LOG_PREFIX = "[substrate.llm_planner]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Canonicalization utilities ──────────────────────────────────────


def _normalize_for_canonical(obj: Any) -> Any:
    """Recursively normalize an object for canonical JSON serialization.

    - Strings: NFC unicode normalization.
    - Floats: repr() for deterministic representation.
    - Dicts: passed through (json.dumps handles key sorting).
    - Lists/tuples: recurse into elements.
    """
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, float):
        return float(repr(obj))
    if isinstance(obj, dict):
        return {
            _normalize_for_canonical(k): _normalize_for_canonical(v)
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [_normalize_for_canonical(item) for item in obj]
    return obj


def _canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, compact separators, ASCII-safe, NFC-normalized."""
    normalized = _normalize_for_canonical(obj)
    return json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _sha256_hex(data: str) -> str:
    """Full SHA-256 hex digest."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _sha256_prefix(data: str, length: int = 16) -> str:
    """First `length` hex chars of SHA-256."""
    return _sha256_hex(data)[:length]


# ─── Enums ───────────────────────────────────────────────────────────


class SelectionPolicy(str, Enum):
    """Policy for selecting events from a multi-event proposal."""

    ALL = "all"
    FIRST = "first"


# ─── Configuration ───────────────────────────────────────────────────


@dataclass
class LLMPlannerConfig:
    """Runtime configuration for the LLM planning layer.

    Enforced inside ReplayableStrategy, not at the orchestration layer.
    """

    # Master switch
    enabled: bool = False

    # Per-intent-type control.  None = eligible for all types.
    enabled_intent_types: set[IntentType] | None = None

    # Replay
    replay_mode: bool = False
    strict_replay_validation: bool = True

    # Selection
    selection_policy: SelectionPolicy = SelectionPolicy.ALL

    # Safety limits
    max_events_per_proposal: int = 5
    max_prompt_tokens: int = 4000
    max_payload_bytes_per_event: int = 8192
    max_payload_bytes_total: int = 32768
    timeout_ms: int = 30000

    # Versioning
    config_version: int = 1
    model_name: str = ""
    temperature: float = 0.0

    # Truncation
    truncation_priority: tuple[str, ...] = (
        "metadata:",
        "history:",
        "payload:",
        "core:",
    )
    max_array_elements: int = 20

    def is_enabled_for_intent(self, intent_type: IntentType) -> bool:
        """Check if the LLM layer is enabled for this intent type."""
        if not self.enabled:
            return False
        if self.enabled_intent_types is None:
            return True
        return intent_type in self.enabled_intent_types


# ─── Event schema and registry ───────────────────────────────────────


@dataclass(frozen=True)
class EventSchema:
    """Schema for a registered event type.

    Attributes:
        event_type: Canonical event type string.
        required_fields: Payload keys that must exist.
        optional_fields: Payload keys that may exist.
        field_types: Optional type enforcement via isinstance().
            Only top-level fields are type-checked.
            Supported: str, int, float, bool, list, dict.
        event_version: Per-event schema evolution.
        is_mutation: False for observability events.  Runtime enforces
            that handlers for non-mutation events cannot return mutations.
    """

    event_type: str
    required_fields: frozenset[str]
    optional_fields: frozenset[str]
    field_types: dict[str, type] | None = None
    event_version: int = 1
    is_mutation: bool = True


class EventTypeRegistry:
    """Authoritative registry of valid event types for LLM proposals.

    Independent from the scheduler subscriber map.  Defines what
    the LLM is allowed to propose, not what currently has handlers.

    Thread-safe via threading.Lock.
    """

    def __init__(self) -> None:
        self._schemas: dict[str, EventSchema] = {}
        self._version: int = 0
        self._lock = threading.Lock()
        self._cached_hash: str | None = None

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    @property
    def schema_hash(self) -> str:
        """Deterministic hash of all registered schemas.

        Computed from canonical JSON of all schemas sorted by event_type.
        """
        with self._lock:
            if self._cached_hash is not None:
                return self._cached_hash
            schemas_data = []
            for et in sorted(self._schemas.keys()):
                s = self._schemas[et]
                schemas_data.append(
                    {
                        "event_type": s.event_type,
                        "required_fields": sorted(s.required_fields),
                        "optional_fields": sorted(s.optional_fields),
                        "field_types": (
                            {k: v.__name__ for k, v in sorted(s.field_types.items())}
                            if s.field_types
                            else None
                        ),
                        "event_version": s.event_version,
                        "is_mutation": s.is_mutation,
                    }
                )
            canonical = _canonical_json(schemas_data)
            self._cached_hash = _sha256_prefix(canonical)
            return self._cached_hash

    def register(self, schema: EventSchema) -> None:
        """Register an event type schema.  Increments version."""
        with self._lock:
            self._schemas[schema.event_type] = schema
            self._version += 1
            self._cached_hash = None  # invalidate

    def get(self, event_type: str) -> EventSchema | None:
        """Look up a schema by event type."""
        with self._lock:
            return self._schemas.get(event_type)

    def is_valid_event_type(self, event_type: str) -> bool:
        """Check if an event type is registered."""
        with self._lock:
            return event_type in self._schemas

    @property
    def event_types(self) -> list[str]:
        """Sorted list of all registered event types."""
        with self._lock:
            return sorted(self._schemas.keys())

    def validate_event(
        self, event_type: str, payload: dict[str, Any]
    ) -> tuple[bool, str]:
        """Validate an event_type + payload against the registry.

        Returns (valid, reason).  Checks:
        1. Event type exists.
        2. All required fields present.
        3. No unknown fields.
        4. Field types match when declared (isinstance check, top-level only).
        """
        with self._lock:
            schema = self._schemas.get(event_type)

        if schema is None:
            return False, f"unknown event_type: {event_type}"

        # Required fields
        missing = schema.required_fields - payload.keys()
        if missing:
            return False, f"missing required fields: {sorted(missing)}"

        # Unknown fields
        allowed = schema.required_fields | schema.optional_fields
        unknown = payload.keys() - allowed
        if unknown:
            return False, f"unknown fields: {sorted(unknown)}"

        # Type checking (when declared)
        if schema.field_types:
            for field_name, expected_type in schema.field_types.items():
                if field_name in payload:
                    if not isinstance(payload[field_name], expected_type):
                        actual = type(payload[field_name]).__name__
                        return False, (
                            f"field {field_name!r}: expected {expected_type.__name__}, "
                            f"got {actual}"
                        )

        return True, ""

    def validate_proposal(
        self,
        proposal: LLMEventProposal,
        config: LLMPlannerConfig,
    ) -> ValidationResult:
        """Validate every ProposedEvent in a proposal.

        Also enforces config limits: max_events_per_proposal,
        max_payload_bytes_per_event, max_payload_bytes_total.
        """
        # Event count limit
        if len(proposal.events) > config.max_events_per_proposal:
            reasons = {
                0: (
                    f"proposal has {len(proposal.events)} events, "
                    f"max is {config.max_events_per_proposal}"
                ),
            }
            return ValidationResult(
                valid=False,
                accepted_events=(),
                rejected_events=proposal.events,
                rejection_reasons=reasons,
                schema_hash=self.schema_hash,
            )

        accepted: list[ProposedEvent] = []
        rejected: list[ProposedEvent] = []
        reasons: dict[int, str] = {}
        total_bytes = 0

        for i, evt in enumerate(proposal.events):
            # Per-event payload size
            payload_json = _canonical_json(evt.payload)
            payload_bytes = len(payload_json.encode("utf-8"))

            if payload_bytes > config.max_payload_bytes_per_event:
                rejected.append(evt)
                reasons[i] = (
                    f"payload size {payload_bytes}B exceeds limit "
                    f"{config.max_payload_bytes_per_event}B"
                )
                continue

            total_bytes += payload_bytes
            if total_bytes > config.max_payload_bytes_total:
                rejected.append(evt)
                reasons[i] = (
                    f"cumulative payload size {total_bytes}B exceeds limit "
                    f"{config.max_payload_bytes_total}B"
                )
                continue

            valid, reason = self.validate_event(evt.event_type, evt.payload)
            if valid:
                accepted.append(evt)
            else:
                rejected.append(evt)
                reasons[i] = reason

        return ValidationResult(
            valid=len(rejected) == 0,
            accepted_events=tuple(accepted),
            rejected_events=tuple(rejected),
            rejection_reasons=reasons,
            schema_hash=self.schema_hash,
        )


# ─── Data models ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProposedEvent:
    """A single candidate event proposed by the LLM."""

    event_type: str
    payload: dict[str, Any]
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "event_type": self.event_type,
            "payload": dict(self.payload),
        }
        if self.description is not None:
            d["description"] = self.description
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ProposedEvent:
        return ProposedEvent(
            event_type=d["event_type"],
            payload=d.get("payload", {}),
            description=d.get("description"),
        )


@dataclass(frozen=True)
class LLMEventProposal:
    """Validated, canonical LLM proposal.

    Attributes:
        events: Ordered tuple of proposed events.
        proposal_id: sha256(canonical_json).  Canonical proposal identity.
        reasoning: Non-authoritative.  Never used for execution or replay.
    """

    events: tuple[ProposedEvent, ...]
    proposal_id: str
    reasoning: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating a proposal against the registry.

    schema_hash is explicitly tied to the registry state at validation
    time.  Replay strict mode compares this to the current registry
    schema_hash before accepting stored proposals.
    """

    valid: bool
    accepted_events: tuple[ProposedEvent, ...]
    rejected_events: tuple[ProposedEvent, ...]
    rejection_reasons: dict[int, str]
    schema_hash: str


@dataclass(frozen=True)
class LLMProposalResult:
    """Full pipeline output from LLMPlanningStrategy.propose().

    Attributes:
        prompt_hash: Composite hash of (prompt, model, temp, config_v, registry_v).
        raw_response: Raw LLM output string.
        response_hash: sha256(raw_response).  Response identity.
        canonical_json: Normalized JSON string, or None on parse failure.
        proposal: Parsed proposal, or None on parse/validation failure.
        proposal_id: Always present.  On parse success: sha256(canonical_json).
            On parse failure: derived from response_hash with 'raw_' prefix
            to distinguish from canonical proposal identity.
        validation: Validation result, or None if parse failed.
        latency_ms: Wall-clock time for the LLM call.
        parse_failed: True if JSON parsing failed.  Distinguishes
            raw-response identity from canonical proposal identity.
    """

    prompt_hash: str
    raw_response: str
    response_hash: str
    canonical_json: str | None
    proposal: LLMEventProposal | None
    proposal_id: str
    validation: ValidationResult | None
    latency_ms: int
    parse_failed: bool


# ─── Prompt construction ─────────────────────────────────────────────


def _truncate_state(canonical_state: str, config: LLMPlannerConfig) -> str:
    """Truncate canonical state JSON to fit within prompt token budget.

    Algorithm (strict, reproducible):
    1. If within budget, return as-is.
    2. Parse into dict.
    3. Drop keys by priority tier (config.truncation_priority).
       Within each tier, drop keys in reverse lexicographic order.
    4. Arrays truncated to first max_array_elements elements.
    5. After each drop, re-check budget.
    6. Same state + same config = same output, always.

    Budget approximation: 1 token ~= 4 chars.
    """
    max_chars = config.max_prompt_tokens * 4
    if len(canonical_state) <= max_chars:
        return canonical_state

    try:
        state = json.loads(canonical_state)
    except (json.JSONDecodeError, TypeError):
        return canonical_state[:max_chars]

    # Truncate arrays first
    def _truncate_arrays(obj: Any) -> Any:
        if isinstance(obj, list):
            return [_truncate_arrays(item) for item in obj[: config.max_array_elements]]
        if isinstance(obj, dict):
            return {k: _truncate_arrays(v) for k, v in obj.items()}
        return obj

    state = _truncate_arrays(state)
    result = _canonical_json(state)
    if len(result) <= max_chars:
        return result

    # Drop keys by priority tier
    for prefix in config.truncation_priority:
        keys_in_tier = sorted(
            [k for k in state if k.startswith(prefix)],
            reverse=True,
        )
        for key in keys_in_tier:
            del state[key]
            result = _canonical_json(state)
            if len(result) <= max_chars:
                return result

    # Final fallback: drop remaining keys in reverse lex order
    for key in sorted(state.keys(), reverse=True):
        if len(state) <= 1:
            break
        del state[key]
        result = _canonical_json(state)
        if len(result) <= max_chars:
            return result

    return _canonical_json(state)


def _build_event_catalog(registry: EventTypeRegistry) -> str:
    """Build the event catalog section of the prompt from the registry."""
    lines: list[str] = []
    for et in registry.event_types:
        schema = registry.get(et)
        if schema is None:
            continue
        lines.append(f"- {et} (v{schema.event_version})")
        lines.append(f"  required: {sorted(schema.required_fields)}")
        if schema.optional_fields:
            lines.append(f"  optional: {sorted(schema.optional_fields)}")
        if schema.field_types:
            type_strs = {k: v.__name__ for k, v in sorted(schema.field_types.items())}
            lines.append(f"  types: {type_strs}")
    return "\n".join(lines)


def build_llm_prompt(
    canonical_state: str,
    active_intents: list[dict[str, Any]],
    registry: EventTypeRegistry,
    config: LLMPlannerConfig,
) -> str:
    """Build the LLM prompt from canonical state.

    Deterministic: same inputs produce the same prompt string.
    No randomness, no timestamps, no UUIDs.
    """
    truncated_state = _truncate_state(canonical_state, config)
    catalog = _build_event_catalog(registry)
    intents_json = _canonical_json(active_intents) if active_intents else "[]"

    return (
        "You are a planning component in an event-driven system.\n"
        "You propose events to be emitted into a scheduler.\n"
        "\n"
        "CONSTRAINTS:\n"
        "- You may ONLY propose events from the catalog below.\n"
        "- Every event must include all required payload fields.\n"
        "- You must not invent new event types.\n"
        "- Output valid JSON only. No commentary outside the JSON block.\n"
        "\n"
        f"SCHEMA VERSION: {registry.version}\n"
        "\n"
        "EVENT CATALOG:\n"
        f"{catalog}\n"
        "\n"
        "CURRENT STATE:\n"
        f"{truncated_state}\n"
        "\n"
        "ACTIVE INTENTS:\n"
        f"{intents_json}\n"
        "\n"
        "OUTPUT FORMAT:\n"
        "{\n"
        '  "events": [\n'
        '    {"event_type": "...", "payload": {...}, "description": "..."}\n'
        "  ],\n"
        '  "reasoning": "..."\n'
        "}\n"
    )


def compute_prompt_hash(
    prompt: str,
    model_name: str,
    temperature: float,
    config_version: int,
    registry_version: int,
) -> str:
    """Composite prompt hash over all inputs that affect LLM output.

    Includes prompt string, model, temperature, config version,
    and registry version.  Not just the prompt string alone.
    """
    composite = _canonical_json(
        {
            "prompt": prompt,
            "model": model_name,
            "temperature": temperature,
            "config_v": config_version,
            "registry_v": registry_version,
        }
    )
    return _sha256_prefix(composite)


# ─── LLM Planning Strategy ──────────────────────────────────────────


class LLMPlanningStrategy:
    """Constrained plan proposer.  Subordinate component.

    Does NOT implement DecisionStrategy.  Owned by ReplayableStrategy.

    Responsibilities:
    - Build deterministic prompt from canonical state + intents + registry.
    - Call llm_fn (the sole non-deterministic boundary).
    - Strict JSON parse.
    - Normalize to canonical form.
    - Validate against EventTypeRegistry.
    - Return structured LLMProposalResult.

    Does NOT:
    - Enforce timeout (ReplayableStrategy's job).
    - Emit events.
    - Write state.
    - Construct DecisionOutput.
    """

    def __init__(
        self,
        llm_fn: Callable[[str], str],
        registry: EventTypeRegistry,
        config: LLMPlannerConfig,
    ) -> None:
        self._llm_fn = llm_fn
        self._registry = registry
        self._config = config

    @property
    def name(self) -> str:
        return "llm_planner"

    def propose(
        self,
        canonical_state: str,
        state_hash: str,
        active_intents: list[dict[str, Any]],
    ) -> LLMProposalResult:
        """Propose candidate events from current state.

        Args:
            canonical_state: Pre-canonicalized state JSON string.
            state_hash: Pre-computed hash of canonical_state.
            active_intents: Serialized active intents (list of dicts).

        Returns:
            LLMProposalResult with full pipeline trace.
        """
        # 1. Build prompt (deterministic)
        prompt = build_llm_prompt(
            canonical_state=canonical_state,
            active_intents=active_intents,
            registry=self._registry,
            config=self._config,
        )
        prompt_hash = compute_prompt_hash(
            prompt=prompt,
            model_name=self._config.model_name,
            temperature=self._config.temperature,
            config_version=self._config.config_version,
            registry_version=self._registry.version,
        )

        # 2. Call LLM (sole non-deterministic boundary)
        start_ms = int(time.monotonic() * 1000)
        raw_response = self._llm_fn(prompt)
        latency_ms = int(time.monotonic() * 1000) - start_ms

        response_hash = _sha256_prefix(raw_response)

        # 3. Strict JSON parse
        try:
            parsed = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError) as exc:
            _log(f"JSON parse failed: {exc}")
            # proposal_id derived from response with 'raw_' prefix to
            # distinguish from canonical proposal identity
            return LLMProposalResult(
                prompt_hash=prompt_hash,
                raw_response=raw_response,
                response_hash=response_hash,
                canonical_json=None,
                proposal=None,
                proposal_id=f"raw_{response_hash}",
                validation=None,
                latency_ms=latency_ms,
                parse_failed=True,
            )

        # 4. Normalize to canonical form
        canonical_json = _canonical_json(parsed)
        proposal_id = _sha256_prefix(canonical_json)

        # 5. Parse into ProposedEvent objects
        raw_events = parsed.get("events", [])
        if not isinstance(raw_events, list):
            _log("'events' field is not a list")
            return LLMProposalResult(
                prompt_hash=prompt_hash,
                raw_response=raw_response,
                response_hash=response_hash,
                canonical_json=canonical_json,
                proposal=None,
                proposal_id=proposal_id,
                validation=None,
                latency_ms=latency_ms,
                parse_failed=True,
            )

        proposed_events: list[ProposedEvent] = []
        for raw_evt in raw_events:
            if not isinstance(raw_evt, dict) or "event_type" not in raw_evt:
                continue
            proposed_events.append(
                ProposedEvent(
                    event_type=raw_evt["event_type"],
                    payload=raw_evt.get("payload", {}),
                    description=raw_evt.get("description"),
                )
            )

        reasoning = parsed.get("reasoning")
        if reasoning is not None and not isinstance(reasoning, str):
            reasoning = str(reasoning)

        proposal = LLMEventProposal(
            events=tuple(proposed_events),
            proposal_id=proposal_id,
            reasoning=reasoning,
        )

        # 6. Validate against registry
        validation = self._registry.validate_proposal(proposal, self._config)

        return LLMProposalResult(
            prompt_hash=prompt_hash,
            raw_response=raw_response,
            response_hash=response_hash,
            canonical_json=canonical_json,
            proposal=proposal,
            proposal_id=proposal_id,
            validation=validation,
            latency_ms=latency_ms,
            parse_failed=False,
        )
