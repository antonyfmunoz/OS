"""
Decision engine — control-plane cognition layer.

Reads RuntimeStateStore (read-only), evaluates a pluggable strategy,
and produces a DecisionOutput that the scheduler can emit as an event.
The engine NEVER executes anything directly.

Design constraints:
- Deterministic: same state → same decision (no unseeded randomness).
- Replayable: safe to re-evaluate against a snapshot.
- Observable: every decision emits a DECISION_MADE event.
- Pluggable: strategies implement the DecisionStrategy protocol.

Integration point:
    After EventScheduler drain → state updated →
    DecisionEngine.evaluate(state_snapshot) → emit chosen event

Usage:
    engine = DecisionEngine(strategy=RuleBasedStrategy())
    output = engine.evaluate(store)
    if output is not None:
        scheduler.emit(output.action_event)
        scheduler.emit(output.observability_event)
"""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from runtime.transport.decision_events import build_decision_made_event
from runtime.transport.event_scheduler import SchedulerEvent
from runtime.transport.runtime_state_store import RuntimeStateStore

_LOG_PREFIX = "[substrate.decision_engine]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Data structures ──────────────────────────────────────────────────


@dataclass(frozen=True)
class DecisionOutput:
    """The result of a decision evaluation.

    Fields:
        decision_id: Unique ID for tracing this decision.
        event_type: The event type to emit.
        payload: The event payload.
        reasoning: Human-readable explanation of why this action was chosen.
        state_hash: Hash of the input state at evaluation time.
        strategy_name: Which strategy produced this decision.
    """

    decision_id: str
    event_type: str
    payload: dict[str, Any]
    reasoning: str
    state_hash: str
    strategy_name: str
    is_terminal: bool = False
    suppress_downstream: bool = False

    @property
    def action_event(self) -> SchedulerEvent:
        """Build the SchedulerEvent for the chosen action."""
        return SchedulerEvent(
            event_type=self.event_type,
            session_name=self.payload.get("session_name", ""),
            source=f"decision_engine:{self.strategy_name}",
            run_id=self.payload.get("run_id"),
            payload=self.payload,
            metadata={"decision_id": self.decision_id},
        )

    @property
    def observability_event(self) -> SchedulerEvent:
        """Build the DECISION_MADE observability event."""
        return build_decision_made_event(
            decision_id=self.decision_id,
            session_name=self.payload.get("session_name", ""),
            strategy_name=self.strategy_name,
            state_hash=self.state_hash,
            chosen_event_type=self.event_type,
            chosen_payload=self.payload,
            reasoning=self.reasoning,
            run_id=self.payload.get("run_id"),
        )


# ─── Strategy protocol ───────────────────────────────────────────────


class DecisionStrategy(Protocol):
    """Interface for pluggable decision strategies.

    Strategies are pure functions from state → optional DecisionOutput.
    Returning None means "no action to take."
    """

    @property
    def name(self) -> str:
        """Strategy identifier for logging and tracing."""
        ...

    def evaluate(self, state: dict[str, Any]) -> DecisionOutput | None:
        """Evaluate the current state and return a decision, or None.

        MUST be deterministic: same state dict → same DecisionOutput.
        MUST NOT have side effects.
        """
        ...


# ─── Rule-based strategy ─────────────────────────────────────────────


@dataclass
class Rule:
    """A single decision rule.

    Fields:
        rule_id: Identifier for tracing.
        description: Human-readable description.
        condition: Pure predicate on state. Returns True if rule applies.
        event_type: The event type to emit if this rule fires.
        build_payload: Builds the event payload from state.
        priority: Lower number = evaluated first. Default 100.
    """

    rule_id: str
    description: str
    condition: Any  # Callable[[dict[str, Any]], bool]
    event_type: str
    build_payload: Any  # Callable[[dict[str, Any]], dict[str, Any]]
    priority: int = 100


class RuleBasedStrategy:
    """Decision strategy that evaluates rules in priority order.

    First matching rule wins. Deterministic: same state + same rules
    → same output, always.
    """

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self._rules: list[Rule] = sorted(rules or [], key=lambda r: r.priority)

    @property
    def name(self) -> str:
        return "rule_based"

    def add_rule(self, rule: Rule) -> None:
        """Add a rule and maintain priority sort."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    @property
    def rules(self) -> list[Rule]:
        """Read-only access to the sorted rule list."""
        return list(self._rules)

    def evaluate(self, state: dict[str, Any]) -> DecisionOutput | None:
        """Evaluate rules in priority order. First match wins."""
        state_hash = _compute_state_hash(state)
        # Deterministic decision_id: derived from state_hash so same
        # state always produces the same decision_id.
        decision_seed = f"rule_based:{state_hash}"
        decision_id = f"dec_{hashlib.sha256(decision_seed.encode()).hexdigest()[:12]}"

        for rule in self._rules:
            try:
                if rule.condition(state):
                    payload = rule.build_payload(state)
                    return DecisionOutput(
                        decision_id=decision_id,
                        event_type=rule.event_type,
                        payload=payload,
                        reasoning=f"Rule [{rule.rule_id}]: {rule.description}",
                        state_hash=state_hash,
                        strategy_name=self.name,
                    )
            except Exception as exc:
                _log(f"rule {rule.rule_id} evaluation error: {exc}")
                continue

        return None


# ─── Decision engine ──────────────────────────────────────────────────


class DecisionEngine:
    """Control-plane decision engine.

    Reads state (read-only), delegates to a strategy, and returns
    a DecisionOutput. Never modifies state or executes anything.

    Usage:
        engine = DecisionEngine(strategy=RuleBasedStrategy(rules))
        output = engine.evaluate(store)
        if output is not None:
            scheduler.emit(output.action_event)
            scheduler.emit(output.observability_event)
    """

    def __init__(
        self,
        strategy: DecisionStrategy,
        enabled: bool = True,
    ) -> None:
        self._strategy = strategy
        self._enabled = enabled
        self._evaluation_count: int = 0

    @property
    def strategy_name(self) -> str:
        return self._strategy.name

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        _log(f"decision engine {'ENABLED' if value else 'DISABLED'}")

    @property
    def evaluation_count(self) -> int:
        return self._evaluation_count

    def evaluate(self, store: RuntimeStateStore) -> DecisionOutput | None:
        """Evaluate the current state and return a decision.

        Takes a RuntimeStateStore and reads a snapshot (read-only).
        Returns None if the engine is disabled or no decision applies.
        """
        if not self._enabled:
            return None

        snapshot = store.snapshot()
        self._evaluation_count += 1

        try:
            output = self._strategy.evaluate(snapshot)
        except Exception as exc:
            _log(f"strategy evaluation failed: {exc}")
            return None

        if output is not None:
            _log(
                f"decision: [{output.decision_id}] → {output.event_type} "
                f"(strategy={output.strategy_name}, hash={output.state_hash})"
            )

        return output

    def evaluate_snapshot(self, snapshot: dict[str, Any]) -> DecisionOutput | None:
        """Evaluate a raw state dict directly.

        Used for replay/testing without a live store.
        """
        if not self._enabled:
            return None

        self._evaluation_count += 1

        try:
            return self._strategy.evaluate(snapshot)
        except Exception as exc:
            _log(f"strategy evaluation failed: {exc}")
            return None


# ─── Helpers ──────────────────────────────────────────────────────────


def _compute_state_hash(state: dict[str, Any]) -> str:
    """SHA-256 prefix of canonical JSON. Matches RuntimeStateStore.compute_state_hash()."""
    canonical = json.dumps(
        state, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def evaluate_and_emit(
    engine: DecisionEngine,
    store: RuntimeStateStore,
    scheduler: "EventScheduler",
) -> DecisionOutput | None:
    """Convenience: evaluate + emit both events into the scheduler.

    Returns the DecisionOutput if a decision was made, None otherwise.
    This is the standard integration point for the post-drain hook.
    """
    from runtime.transport.event_scheduler import EventScheduler

    output = engine.evaluate(store)
    if output is not None:
        scheduler.emit(output.observability_event)
        scheduler.emit(output.action_event)
    return output
