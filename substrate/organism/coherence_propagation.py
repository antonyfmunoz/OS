"""Coherence Propagation Engine — parallel dependent-system updates on verified change.

When a governed execution completes verification, the engine:
1. Emits OutcomeCommitted
2. Determines affected propagation targets
3. Groups targets into parallel waves (independent before derived)
4. Executes independent targets concurrently
5. Records each result independently
6. Emits propagation_completed or propagation_failed

Wave 1 (independent immediate updates):
  - OutcomeLearningLoop.record_outcome
  - TemplateRegistry.generate_candidate_from_outcome
  - MemoryPromotionPipeline.generate_candidate_from_outcome
  - AgentCapabilityModel.update_reliability
  - WorldModel.attach_evidence_or_update_status

Wave 2 (derived recalculation):
  - DependencyGraph.recompute_affected
  - ContradictionEngine.recheck_affected
  - ReadinessModel.recalculate
  - BottleneckEngine.recalculate
  - CompositionEngine.refresh_template_index
  - Cockpit realtime state update

Rules:
  - Every target is idempotent
  - Every target records success/failure
  - One failed target does not block unrelated targets
  - Each result includes evidence
  - Each target declares which primitive relationship it updates

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


# ---------------------------------------------------------------------------
# OutcomeCommitted / OutcomeFailed event contracts
# ---------------------------------------------------------------------------


class OutcomeEventType(str, Enum):
    COMMITTED = "outcome_committed"
    FAILED = "outcome_failed"


class PrimitiveRelationship(str, Enum):
    STATE = "state"
    CHANGE = "change"
    CONSTRAINT = "constraint"
    RESOURCE = "resource"
    TIME = "time"
    SIGNAL = "signal"
    FEEDBACK = "feedback"
    GOAL = "goal"
    ACTION = "action"
    OUTCOME = "outcome"


@dataclass
class OutcomeCommitted:
    event_id: str = field(default_factory=lambda: f"oc-{uuid4().hex[:8]}")
    action_envelope_id: str = ""
    execution_graph_id: str = ""
    trial_id: str = ""
    action_type: str = ""
    mutation_type: str = ""
    risk_class: str = "low"
    agent_type: str = "developer_agent"
    capabilities_used: list[str] = field(default_factory=list)
    validation_result: str = "passed"
    rollback_result: str = "not_needed"
    duration_ms: float = 0.0
    changed_files: list[str] = field(default_factory=list)
    changed_entities: list[str] = field(default_factory=list)
    affected_subsystems: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": OutcomeEventType.COMMITTED.value,
            "action_envelope_id": self.action_envelope_id,
            "execution_graph_id": self.execution_graph_id,
            "trial_id": self.trial_id,
            "action_type": self.action_type,
            "mutation_type": self.mutation_type,
            "risk_class": self.risk_class,
            "agent_type": self.agent_type,
            "capabilities_used": self.capabilities_used,
            "validation_result": self.validation_result,
            "rollback_result": self.rollback_result,
            "duration_ms": self.duration_ms,
            "changed_files": self.changed_files,
            "changed_entities": self.changed_entities,
            "affected_subsystems": self.affected_subsystems,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }

    def to_outcome_dict(self) -> dict[str, Any]:
        """Convert to the dict format expected by downstream consumers."""
        return {
            "outcome_id": self.event_id,
            "action_type": self.action_type,
            "description": f"Governed execution: {self.action_type}",
            "success": self.validation_result == "passed",
            "agent_type": self.agent_type,
            "capabilities_used": self.capabilities_used,
            "risk_class": self.risk_class,
            "evidence": self.evidence,
            "trial_id": self.trial_id,
            "envelope_id": self.action_envelope_id,
            "duration_ms": self.duration_ms,
            "steps": [],
        }


@dataclass
class OutcomeFailed:
    event_id: str = field(default_factory=lambda: f"of-{uuid4().hex[:8]}")
    action_envelope_id: str = ""
    execution_graph_id: str = ""
    trial_id: str = ""
    action_type: str = ""
    risk_class: str = "low"
    agent_type: str = "developer_agent"
    failure_reason: str = ""
    validation_result: str = "failed"
    evidence: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": OutcomeEventType.FAILED.value,
            "action_envelope_id": self.action_envelope_id,
            "execution_graph_id": self.execution_graph_id,
            "trial_id": self.trial_id,
            "action_type": self.action_type,
            "risk_class": self.risk_class,
            "agent_type": self.agent_type,
            "failure_reason": self.failure_reason,
            "validation_result": self.validation_result,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Propagation targets and results
# ---------------------------------------------------------------------------


class PropagationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PropagationTarget:
    name: str
    primitive_relationship: PrimitiveRelationship
    wave: int = 1
    handler: Callable[[OutcomeCommitted], dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "primitive_relationship": self.primitive_relationship.value,
            "wave": self.wave,
            "has_handler": self.handler is not None,
        }


@dataclass
class PropagationResult:
    target_name: str
    primitive_relationship: str
    status: PropagationStatus = PropagationStatus.PENDING
    duration_ms: float = 0.0
    input_evidence: list[str] = field(default_factory=list)
    output_artifact: str = ""
    error: str = ""
    wave: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_name": self.target_name,
            "primitive_relationship": self.primitive_relationship,
            "status": self.status.value,
            "duration_ms": round(self.duration_ms, 1),
            "input_evidence": self.input_evidence,
            "output_artifact": self.output_artifact,
            "error": self.error,
            "wave": self.wave,
        }


@dataclass
class PropagationWave:
    wave_number: int
    targets: list[PropagationTarget] = field(default_factory=list)
    results: list[PropagationResult] = field(default_factory=list)
    status: PropagationStatus = PropagationStatus.PENDING
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave_number": self.wave_number,
            "targets": [t.to_dict() for t in self.targets],
            "results": [r.to_dict() for r in self.results],
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class PropagationEvent:
    event_id: str = field(default_factory=lambda: f"pe-{uuid4().hex[:8]}")
    outcome_event_id: str = ""
    waves: list[PropagationWave] = field(default_factory=list)
    status: PropagationStatus = PropagationStatus.PENDING
    started_at: float = 0.0
    completed_at: float = 0.0
    total_targets: int = 0
    succeeded_targets: int = 0
    failed_targets: int = 0
    skipped_targets: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "outcome_event_id": self.outcome_event_id,
            "status": self.status.value,
            "waves": [w.to_dict() for w in self.waves],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_targets": self.total_targets,
            "succeeded_targets": self.succeeded_targets,
            "failed_targets": self.failed_targets,
            "skipped_targets": self.skipped_targets,
        }


# ---------------------------------------------------------------------------
# Parallel Propagation Engine
# ---------------------------------------------------------------------------


class ParallelPropagationEngine:
    """Executes propagation targets in parallel waves after OutcomeCommitted."""

    def __init__(
        self,
        store_dir: str | None = None,
        max_workers: int = 4,
    ):
        self._store_dir = store_dir or os.path.join(_REPO_ROOT, "data", "umh", "propagation")
        self._events_path = os.path.join(self._store_dir, "events.jsonl")
        self._results_path = os.path.join(self._store_dir, "results.jsonl")
        self._max_workers = max_workers
        self._targets: list[PropagationTarget] = []
        self._events: list[PropagationEvent] = []

    def register_target(self, target: PropagationTarget) -> None:
        """Register a propagation target."""
        self._targets.append(target)

    def _build_waves(self) -> dict[int, list[PropagationTarget]]:
        waves: dict[int, list[PropagationTarget]] = {}
        for t in self._targets:
            waves.setdefault(t.wave, []).append(t)
        return dict(sorted(waves.items()))

    def propagate(self, outcome: OutcomeCommitted) -> PropagationEvent:
        """Execute all propagation targets for a committed outcome.

        Wave 1 targets run in parallel. Wave 2 targets run in parallel
        after all Wave 1 targets complete. Failed targets do not block
        sibling targets within the same wave.
        """
        event = PropagationEvent(
            outcome_event_id=outcome.event_id,
            status=PropagationStatus.RUNNING,
            started_at=time.time(),
        )

        waves = self._build_waves()
        total = sum(len(targets) for targets in waves.values())
        event.total_targets = total

        for wave_num, targets in waves.items():
            wave = PropagationWave(
                wave_number=wave_num,
                targets=targets,
                started_at=time.time(),
            )
            wave.status = PropagationStatus.RUNNING

            results = self._execute_wave(targets, outcome)
            wave.results = results
            wave.completed_at = time.time()

            all_ok = all(r.status == PropagationStatus.COMPLETED for r in results)
            any_fail = any(r.status == PropagationStatus.FAILED for r in results)
            wave.status = PropagationStatus.COMPLETED if all_ok else (
                PropagationStatus.FAILED if any_fail else PropagationStatus.COMPLETED
            )

            event.waves.append(wave)
            for r in results:
                if r.status == PropagationStatus.COMPLETED:
                    event.succeeded_targets += 1
                elif r.status == PropagationStatus.FAILED:
                    event.failed_targets += 1
                elif r.status == PropagationStatus.SKIPPED:
                    event.skipped_targets += 1

        event.completed_at = time.time()
        event.status = (
            PropagationStatus.COMPLETED if event.failed_targets == 0
            else PropagationStatus.FAILED
        )

        self._events.append(event)
        self._persist_event(event)
        self._persist_results(event)

        logger.info(
            "Propagation %s: %d/%d succeeded, %d failed",
            event.event_id, event.succeeded_targets, event.total_targets, event.failed_targets,
        )
        return event

    def _execute_wave(
        self,
        targets: list[PropagationTarget],
        outcome: OutcomeCommitted,
    ) -> list[PropagationResult]:
        results: list[PropagationResult] = []

        with ThreadPoolExecutor(max_workers=min(self._max_workers, len(targets) or 1)) as executor:
            future_to_target = {}
            for target in targets:
                if target.handler is None:
                    results.append(PropagationResult(
                        target_name=target.name,
                        primitive_relationship=target.primitive_relationship.value,
                        status=PropagationStatus.SKIPPED,
                        wave=target.wave,
                        error="No handler registered",
                    ))
                    continue
                future = executor.submit(self._run_target, target, outcome)
                future_to_target[future] = target

            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    result = future.result(timeout=30.0)
                    results.append(result)
                except Exception as exc:
                    results.append(PropagationResult(
                        target_name=target.name,
                        primitive_relationship=target.primitive_relationship.value,
                        status=PropagationStatus.FAILED,
                        wave=target.wave,
                        error=f"Executor error: {exc}",
                    ))

        return results

    def _run_target(
        self,
        target: PropagationTarget,
        outcome: OutcomeCommitted,
    ) -> PropagationResult:
        start = time.time()
        try:
            result_data = target.handler(outcome) if target.handler else {}  # type: ignore[misc]
            duration_ms = (time.time() - start) * 1000
            return PropagationResult(
                target_name=target.name,
                primitive_relationship=target.primitive_relationship.value,
                status=PropagationStatus.COMPLETED,
                duration_ms=duration_ms,
                input_evidence=outcome.evidence[:5],
                output_artifact=json.dumps(result_data, default=str)[:500] if result_data else "",
                wave=target.wave,
            )
        except Exception as exc:
            duration_ms = (time.time() - start) * 1000
            logger.warning("Propagation target '%s' failed: %s", target.name, exc)
            return PropagationResult(
                target_name=target.name,
                primitive_relationship=target.primitive_relationship.value,
                status=PropagationStatus.FAILED,
                duration_ms=duration_ms,
                input_evidence=outcome.evidence[:5],
                error=str(exc),
                wave=target.wave,
            )

    def _persist_event(self, event: PropagationEvent) -> None:
        os.makedirs(os.path.dirname(self._events_path), exist_ok=True)
        with open(self._events_path, "a") as f:
            f.write(json.dumps(event.to_dict(), default=str) + "\n")

    def _persist_results(self, event: PropagationEvent) -> None:
        os.makedirs(os.path.dirname(self._results_path), exist_ok=True)
        with open(self._results_path, "a") as f:
            for wave in event.waves:
                for result in wave.results:
                    data = result.to_dict()
                    data["propagation_event_id"] = event.event_id
                    data["outcome_event_id"] = event.outcome_event_id
                    f.write(json.dumps(data, default=str) + "\n")

    def get_event(self, event_id: str) -> PropagationEvent | None:
        for e in self._events:
            if e.event_id == event_id:
                return e
        return None

    def recent_events(self, limit: int = 20) -> list[PropagationEvent]:
        return self._events[-limit:]

    def summary(self) -> dict[str, Any]:
        total_succeeded = sum(e.succeeded_targets for e in self._events)
        total_failed = sum(e.failed_targets for e in self._events)
        return {
            "total_events": len(self._events),
            "total_targets_processed": sum(e.total_targets for e in self._events),
            "total_succeeded": total_succeeded,
            "total_failed": total_failed,
            "registered_targets": len(self._targets),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "recent_events": [e.to_dict() for e in self.recent_events(10)],
            "registered_targets": [t.to_dict() for t in self._targets],
        }

    def to_safe_dict(self) -> dict[str, Any]:
        """HTTP-safe serialization."""
        events = []
        for e in self.recent_events(10):
            events.append({
                "event_id": e.event_id,
                "outcome_event_id": e.outcome_event_id,
                "status": e.status.value,
                "total_targets": e.total_targets,
                "succeeded_targets": e.succeeded_targets,
                "failed_targets": e.failed_targets,
                "started_at": e.started_at,
                "completed_at": e.completed_at,
            })
        return {
            "summary": self.summary(),
            "recent_events": events,
            "registered_targets": [t.to_dict() for t in self._targets],
        }
