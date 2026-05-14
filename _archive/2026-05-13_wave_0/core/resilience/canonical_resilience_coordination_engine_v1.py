"""Canonical Resilience Coordination Engine v1.

Coordinates adaptive resilience:
  instability detection, fault containment, cascading failure
  interruption, checkpoint integrity, degraded survivability,
  recovery recommendation, isolation decisions.

All recovery actions are RECOMMENDATIONS — this coordinator
CANNOT execute repairs, rollbacks, mutations, or healing.
The operator still owns recovery decisions.

UMH substrate subsystem. Phase 96.8BZ.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.resilience.adaptive_resilience_contracts_v1 import (
    RecoveryCoordinationReceipt,
    ResilienceLifecycleState,
    IsolationDecision,
    _now_iso,
)
from core.resilience.resilience_lifecycle_engine_v1 import ResilienceLifecycleEngine
from core.resilience.instability_detection_engine_v1 import (
    InstabilityDetectionEngine,
)
from core.resilience.cascading_failure_interruption_engine_v1 import (
    CascadingFailureInterruptionEngine,
)
from core.resilience.checkpoint_integrity_engine_v1 import (
    CheckpointIntegrityEngine,
)
from core.resilience.degraded_survivability_engine_v1 import (
    DegradedSurvivabilityEngine,
)
from core.resilience.recovery_recommendation_engine_v1 import (
    RecoveryRecommendationEngine,
)
from core.resilience.resilience_observability_pipeline_v1 import (
    ResilienceObservabilityPipeline,
)


class CanonicalResilienceCoordinationEngine:
    """Coordinates resilience detection, containment, and recommendation.

    Cannot execute repairs. Cannot rollback state. Cannot heal autonomously.
    Cannot restart subsystems. All recovery requires operator approval.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/resilience",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = ResilienceLifecycleEngine(state_dir=self._state_dir)
        self._instability = InstabilityDetectionEngine(state_dir=self._state_dir)
        self._cascade = CascadingFailureInterruptionEngine(
            state_dir=self._state_dir,
        )
        self._checkpoint = CheckpointIntegrityEngine(state_dir=self._state_dir)
        self._survivability = DegradedSurvivabilityEngine(
            state_dir=self._state_dir,
        )
        self._recommendation = RecoveryRecommendationEngine(
            state_dir=self._state_dir,
        )
        self._observability = ResilienceObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )
        self._receipts: list[RecoveryCoordinationReceipt] = []
        self._isolations: list[IsolationDecision] = []

    def record_success(self, subsystem_id: str) -> dict[str, Any]:
        health = self._instability.record_success(subsystem_id)
        self._survivability.mark_functional(subsystem_id)

        score = self._instability.compute_instability_score()
        if score == 0.0 and self._lifecycle.current_state in (
            "monitored", "stabilized",
        ):
            self._lifecycle.transition(ResilienceLifecycleState.STABLE)
            self._observability.emit_resilience_restored(
                from_state="monitored", to_state="stable",
            )

        return health.to_dict()

    def record_failure(
        self,
        subsystem_id: str,
        upstream: str = "",
    ) -> dict[str, Any]:
        signal = self._instability.record_failure(subsystem_id)

        if upstream:
            self._cascade.report_failure(subsystem_id, upstream)

        if signal is not None:
            old_state = self._lifecycle.current_state

            if old_state == "stable":
                self._lifecycle.transition(ResilienceLifecycleState.MONITORED)
            if signal.instability_class in ("persistent", "cascading", "systemic"):
                if self._lifecycle.current_state == "monitored":
                    self._lifecycle.transition(ResilienceLifecycleState.UNSTABLE)
                if self._lifecycle.current_state == "unstable":
                    self._lifecycle.transition(ResilienceLifecycleState.DEGRADED)

            self._survivability.mark_degraded(subsystem_id)
            self._observability.emit_instability_detected(
                source=subsystem_id,
                severity=signal.severity,
            )

            rec = self._recommendation.recommend(
                target_subsystem=subsystem_id,
                instability_class=signal.instability_class,
                rationale=f"Consecutive failures: {signal.consecutive_failures}",
            )
            self._observability.emit_recovery_recommended(
                target=subsystem_id, action=rec.action,
            )

            self._emit_receipt(
                "failure_detected", old_state,
                self._lifecycle.current_state, signal.severity,
                recommendation=rec.action,
            )

            return signal.to_dict()

        return {"subsystem_id": subsystem_id, "signal": None}

    def contain_fault(
        self,
        source: str,
        boundary: str,
        affected: list[str] | None = None,
    ) -> dict[str, Any]:
        containment = self._cascade.contain_fault(source, boundary, affected)
        self._observability.emit_fault_contained(
            source=source, boundary=boundary,
        )
        return containment.to_dict()

    def isolate_subsystem(
        self,
        target: str,
        scope: str = "subsystem",
        reason: str = "",
    ) -> dict[str, Any]:
        decision = IsolationDecision(
            target=target,
            scope=scope,
            reason=reason,
            isolated=True,
            isolation_boundary=[target],
        )
        self._isolations.append(decision)

        self._survivability.mark_degraded(target)

        if self._lifecycle.current_state in ("degraded",):
            self._lifecycle.transition(ResilienceLifecycleState.ISOLATED)

        self._observability.emit_isolation_applied(
            target=target, scope=scope,
        )

        self._emit_receipt(
            "isolate_subsystem", "", "isolated", 0.0,
        )

        path = self._state_dir / "isolation_decisions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(decision.to_dict(), default=str) + "\n")

        return decision.to_dict()

    def create_checkpoint(
        self,
        subsystem_id: str,
        state_data: dict[str, Any],
    ) -> dict[str, Any]:
        checkpoint = self._checkpoint.create_checkpoint(
            subsystem_id, state_data,
        )
        self._observability.emit_checkpoint_created(
            subsystem=subsystem_id,
            checkpoint_id=checkpoint.checkpoint_id,
        )
        return checkpoint.to_dict()

    def validate_checkpoint(
        self,
        subsystem_id: str,
        state_data: dict[str, Any],
    ) -> dict[str, Any]:
        result = self._checkpoint.validate_checkpoint(
            subsystem_id, state_data,
        )
        if result is not None:
            self._observability.emit_checkpoint_validated(
                subsystem=subsystem_id, valid=result.valid,
            )
            return result.to_dict()
        return {"subsystem_id": subsystem_id, "valid": None}

    def assess_survivability(self) -> dict[str, Any]:
        state = self._survivability.assess_survivability()
        self._observability.emit_survivability_assessed(
            score=state.survivability_score,
            can_continue=state.can_continue,
        )
        return state.to_dict()

    def compute_survivability_score(self) -> dict[str, Any]:
        return self._survivability.compute_survivability_score().to_dict()

    def begin_recovery(self) -> bool:
        if self._lifecycle.current_state in ("degraded", "isolated"):
            if self._lifecycle.current_state == "isolated":
                self._lifecycle.transition(ResilienceLifecycleState.DEGRADED)
            ok = self._lifecycle.transition(ResilienceLifecycleState.RECOVERING)
            return ok
        return False

    def validate_recovery(self) -> bool:
        if self._lifecycle.current_state == "recovering":
            return self._lifecycle.transition(
                ResilienceLifecycleState.VALIDATED,
            )
        return False

    def complete_recovery(self) -> dict[str, Any]:
        if self._lifecycle.current_state == "validated":
            self._lifecycle.transition(ResilienceLifecycleState.STABILIZED)
            self._lifecycle.transition(ResilienceLifecycleState.STABLE)
            self._observability.emit_resilience_restored(
                from_state="validated", to_state="stable",
            )
            self._emit_receipt(
                "complete_recovery", "validated", "stable", 0.0,
            )
        return {"lifecycle_state": self._lifecycle.current_state}

    def approve_recommendation(
        self,
        recommendation_id: str,
        approved_by: str = "operator",
    ) -> bool:
        return self._recommendation.approve(recommendation_id, approved_by)

    def reject_recommendation(self, recommendation_id: str) -> bool:
        return self._recommendation.reject(recommendation_id)

    def get_pending_recommendations(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._recommendation.get_pending()]

    def get_health(self) -> dict[str, Any]:
        score = self._instability.compute_instability_score()
        classification = self._instability.classify_instability(score)
        surv = self._survivability.assess_survivability()
        return {
            "lifecycle_state": self._lifecycle.current_state,
            "instability_score": score,
            "instability_class": classification,
            "survivability_score": surv.survivability_score,
            "can_continue": surv.can_continue,
            "unhealthy_subsystems": self._instability.get_unhealthy_subsystems(),
            "active_cascades": len(self._cascade.get_active_cascades()),
            "pending_recommendations": len(
                self._recommendation.get_pending()
            ),
        }

    def get_recent_receipts(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "instability": self._instability.get_stats(),
            "cascade": self._cascade.get_stats(),
            "checkpoint": self._checkpoint.get_stats(),
            "survivability": self._survivability.get_stats(),
            "recommendation": self._recommendation.get_stats(),
            "observability": self._observability.get_stats(),
        }

    def _emit_receipt(
        self,
        operation: str,
        from_state: str,
        to_state: str,
        instability_score: float,
        recommendation: str = "",
    ) -> RecoveryCoordinationReceipt:
        receipt = RecoveryCoordinationReceipt(
            operation=operation,
            from_state=from_state,
            to_state=to_state,
            instability_score=instability_score,
            recommendation=recommendation,
        )
        self._receipts.append(receipt)

        path = self._state_dir / "resilience_coordination_receipts.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict(), default=str) + "\n")

        return receipt
