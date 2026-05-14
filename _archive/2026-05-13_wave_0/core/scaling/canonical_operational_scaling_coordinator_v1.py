"""Canonical Operational Scaling Coordinator v1.

Regulates operational capacity:
  execution pressure, queue pressure, operational load,
  concurrency, resource allocation, degraded-mode transitions.

All execution dispatches ONLY through spine.process().
The coordinator CANNOT execute adapters directly.
The coordinator CANNOT scale infrastructure.
The operator still owns intentionality and objectives.

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.scaling.operational_scaling_contracts_v1 import (
    ResourceBudget,
    ScalingCoordinationReceipt,
    ScalingLifecycleState,
    _now_iso,
)
from core.scaling.scaling_lifecycle_engine_v1 import ScalingLifecycleEngine
from core.scaling.execution_pressure_engine_v1 import ExecutionPressureEngine
from core.scaling.operational_backpressure_engine_v1 import (
    OperationalBackpressureEngine,
)
from core.scaling.concurrency_regulation_engine_v1 import (
    ConcurrencyRegulationEngine,
)
from core.scaling.operational_priority_engine_v1 import OperationalPriorityEngine
from core.scaling.degraded_mode_coordination_engine_v1 import (
    DegradedModeCoordinationEngine,
)
from core.scaling.scaling_observability_pipeline_v1 import (
    ScalingObservabilityPipeline,
)
from core.scaling.operational_scaling_contracts_v1 import ScalingEventType


class CanonicalOperationalScalingCoordinator:
    """Coordinates operational scaling regulation.

    Cannot execute adapters directly. Cannot scale infrastructure.
    Cannot create autonomous optimization goals. All execution
    through canonical spine only.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/scaling",
        budget: ResourceBudget | None = None,
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._budget = budget or ResourceBudget()
        self._lifecycle = ScalingLifecycleEngine(state_dir=self._state_dir)
        self._pressure = ExecutionPressureEngine(
            state_dir=self._state_dir,
            max_concurrent=self._budget.max_concurrent,
            max_queue=self._budget.max_queue_depth,
        )
        self._backpressure = OperationalBackpressureEngine(
            state_dir=self._state_dir,
        )
        self._concurrency = ConcurrencyRegulationEngine(
            state_dir=self._state_dir,
            overrides={"global": self._budget.max_concurrent},
        )
        self._priority = OperationalPriorityEngine(state_dir=self._state_dir)
        self._degraded = DegradedModeCoordinationEngine(
            state_dir=self._state_dir,
            base_concurrency=self._budget.max_concurrent,
        )
        self._observability = ScalingObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )
        self._receipts: list[ScalingCoordinationReceipt] = []

    def evaluate_pressure(self) -> dict[str, Any]:
        state = self._pressure.compute_pressure()
        level = self._pressure.get_pressure_level(state.pressure_score)

        old_lifecycle = self._lifecycle.current_state
        if level == "critical" and old_lifecycle not in ("degraded", "suspended"):
            self._lifecycle.transition(ScalingLifecycleState.PRESSURED)
            self._lifecycle.transition(ScalingLifecycleState.THROTTLED)
            self._observability.emit_pressure_increase(
                score=state.pressure_score, level=level,
            )
        elif level == "high" and old_lifecycle == "stable":
            self._lifecycle.transition(ScalingLifecycleState.ELEVATED)
            self._lifecycle.transition(ScalingLifecycleState.PRESSURED)
            self._observability.emit_pressure_increase(
                score=state.pressure_score, level=level,
            )
        elif level == "elevated" and old_lifecycle == "stable":
            self._lifecycle.transition(ScalingLifecycleState.ELEVATED)
            self._observability.emit_pressure_increase(
                score=state.pressure_score, level=level,
            )
        elif level == "nominal" and old_lifecycle in ("elevated", "throttled", "stabilized"):
            if old_lifecycle == "throttled":
                self._lifecycle.transition(ScalingLifecycleState.PRESSURED)
                self._lifecycle.transition(ScalingLifecycleState.ELEVATED)
            elif old_lifecycle == "elevated":
                pass
            self._lifecycle.transition(ScalingLifecycleState.STABLE)
            self._observability.emit_pressure_relief(
                score=state.pressure_score, level=level,
            )
            self._backpressure.release_throttle()

        throttle = self._backpressure.apply_throttle(level, f"pressure_{level}")

        self._emit_receipt(
            "evaluate_pressure", old_lifecycle,
            self._lifecycle.current_state, state.pressure_score,
        )

        return {
            "pressure": state.to_dict(),
            "level": level,
            "lifecycle_state": self._lifecycle.current_state,
            "throttle": throttle.to_dict(),
        }

    def request_execution_slot(
        self,
        item_id: str = "",
        environment_id: str = "",
        workflow_id: str = "",
        session_id: str = "",
    ) -> dict[str, Any]:
        pressure = self._pressure.compute_pressure()
        decision = self._concurrency.request_slot(
            item_id=item_id,
            environment_id=environment_id,
            workflow_id=workflow_id,
            session_id=session_id,
            pressure_score=pressure.pressure_score,
        )

        if decision.allocated:
            self._pressure.record_traversal_start()
        else:
            self._observability.emit_concurrency_limited(
                item_id=item_id, reason=decision.reason,
            )

        return decision.to_dict()

    def release_execution_slot(
        self,
        environment_id: str = "",
        workflow_id: str = "",
        session_id: str = "",
        latency_ms: float = 0.0,
    ) -> None:
        self._concurrency.release_slot(environment_id, workflow_id, session_id)
        self._pressure.record_traversal_end(latency_ms)

    def set_priority(
        self,
        item_id: str,
        priority_class: str = "standard",
        set_by: str = "operator",
    ) -> dict[str, Any]:
        state = self._priority.set_priority(item_id, priority_class, set_by)
        return state.to_dict()

    def override_priority(
        self,
        item_id: str,
        new_priority: str,
        overridden_by: str = "operator",
    ) -> bool:
        ok = self._priority.override_priority(item_id, new_priority, overridden_by)
        if ok:
            self._observability.emit_priority_arbitrated(
                item_id=item_id, new_priority=new_priority,
            )
        return ok

    def arbitrate_queue(self, item_ids: list[str]) -> list[str]:
        return self._priority.arbitrate(item_ids)

    def enter_degraded_mode(
        self,
        reason: str = "environment_failure",
        affected_environments: list[str] | None = None,
    ) -> dict[str, Any]:
        mode = self._degraded.enter_degraded(reason, affected_environments)
        self._lifecycle.transition(ScalingLifecycleState.DEGRADED)
        self._observability.emit_degraded_mode_entered(
            reason=reason, environments=affected_environments,
        )
        self._emit_receipt("enter_degraded", "", "degraded", 0.0)
        return mode.to_dict()

    def attempt_recovery(self) -> bool:
        ok = self._degraded.attempt_recovery()
        if ok:
            self._lifecycle.transition(ScalingLifecycleState.RECOVERING)
        return ok

    def complete_recovery(self) -> dict[str, Any]:
        mode = self._degraded.complete_recovery()
        self._lifecycle.transition(ScalingLifecycleState.STABILIZED)
        self._lifecycle.transition(ScalingLifecycleState.STABLE)
        self._observability.emit_degraded_mode_recovered()
        self._emit_receipt("complete_recovery", "degraded", "stable", 0.0)
        return mode.to_dict()

    def record_queue_change(self, depth: int) -> None:
        self._pressure.record_queue_change(depth)

    def record_continuation(self) -> None:
        self._pressure.record_continuation()

    def record_deferred(self) -> None:
        self._pressure.record_deferred()

    def get_health(self) -> dict[str, Any]:
        pressure = self._pressure.compute_pressure()
        return {
            "lifecycle_state": self._lifecycle.current_state,
            "pressure_score": pressure.pressure_score,
            "degraded": self._degraded.is_degraded(),
            "throttle_active": self._backpressure.get_throttle_state().active,
            "concurrency": self._concurrency.get_window().to_dict(),
        }

    def get_budget(self) -> dict[str, Any]:
        return self._budget.to_dict()

    def get_recent_receipts(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "pressure": self._pressure.get_stats(),
            "backpressure": self._backpressure.get_stats(),
            "concurrency": self._concurrency.get_stats(),
            "priority": self._priority.get_stats(),
            "degraded": self._degraded.get_stats(),
            "observability": self._observability.get_stats(),
        }

    def _emit_receipt(
        self,
        operation: str,
        from_state: str,
        to_state: str,
        pressure_score: float,
    ) -> ScalingCoordinationReceipt:
        receipt = ScalingCoordinationReceipt(
            operation=operation,
            from_state=from_state,
            to_state=to_state,
            pressure_score=pressure_score,
        )
        self._receipts.append(receipt)

        path = self._state_dir / "scaling_coordination_receipts.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict(), default=str) + "\n")

        return receipt
