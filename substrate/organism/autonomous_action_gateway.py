"""Autonomous Action Gateway — structural enforcement of spine-routed mutation.

The single adapter through which ALL autonomous/daemon/tick/scheduled
systems request mutations. This is NOT a new execution spine — it is
the autonomous-facing funnel into the existing GovernedExecutionSpine.

Autonomous systems:
  - AutonomousTick stages
  - MaintenanceLoop
  - WorkloadRunner
  - AutomationPipeline
  - AllocationLoop
  - LeverageAssimilator
  - EnvironmentReconciler
  - AsyncCoordinator
  - WorkcellDaemon
  - cron-triggered entrypoints

These systems may:
  - observe (read-only probes)
  - measure (metrics collection)
  - detect (bottleneck/drift detection)
  - recommend (create recommendations)
  - propose (create ActionEnvelopes)
  - submit (send envelopes to the spine)

These systems may NOT:
  - write/delete files directly
  - run shell mutations directly
  - restart containers directly
  - mutate git directly
  - mutate docker directly
  - mutate tmux directly
  - mutate runtime state directly
  outside the GovernedExecutionSpine.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    BlastRadius,
    EnvelopeStatus,
    ExecutionConstraints,
    ReversibilityClass,
)
from substrate.organism.event_spine import EventDomain, EventPriority, EventSpine
from substrate.organism.execution_journal import ExecutionJournal, JournalPhase
from substrate.organism.execution_modes import ExecutionMode, ExecutionModeManager

logger = logging.getLogger(__name__)


class AutonomousPolicy(str, Enum):
    OBSERVE = "observe"
    RECOMMEND = "recommend"
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"


_POLICY_EXECUTION_MAP: dict[AutonomousPolicy, tuple[bool, bool, bool]] = {
    # (can_recommend, can_submit_low, can_submit_medium_plus)
    AutonomousPolicy.OBSERVE: (False, False, False),
    AutonomousPolicy.RECOMMEND: (True, False, False),
    AutonomousPolicy.ASSISTED: (True, True, False),
    AutonomousPolicy.AUTONOMOUS: (True, True, True),
}


@dataclass
class GatewayDecision:
    """Record of a gateway decision for audit."""

    source: str
    intent: str
    risk_level: str
    action: str  # "allowed", "pending_approval", "blocked", "recommend_only"
    reason: str = ""
    envelope_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "intent": self.intent,
            "risk_level": self.risk_level,
            "action": self.action,
            "reason": self.reason,
            "envelope_id": self.envelope_id,
            "timestamp": self.timestamp,
        }


_RISK_SEVERITY: dict[str, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

_MAX_DECISIONS = 1000
_MAX_BLOCKED = 500


class AutonomousActionGateway:
    """Structural enforcement gateway for autonomous mutation.

    All daemon/tick/scheduled systems route mutation requests through
    this gateway. The gateway:
      1. Checks the autonomous execution policy
      2. Checks the ExecutionModeManager
      3. Validates against the MutationRegistry (via spine)
      4. Submits ActionEnvelopes to GovernedExecutionSpine
      5. Journals every decision
      6. Emits EventSpine events
      7. Blocks direct mutation attempts
    """

    def __init__(
        self,
        governed_spine: Any,
        execution_mode: ExecutionModeManager,
        event_spine: EventSpine,
        journal: ExecutionJournal,
        policy: AutonomousPolicy = AutonomousPolicy.ASSISTED,
        reliability_threshold: float = 0.90,
    ) -> None:
        self._spine = governed_spine
        self._mode = execution_mode
        self._event_spine = event_spine
        self._journal = journal
        self._policy = policy
        self._reliability_threshold = reliability_threshold

        self._decisions: list[GatewayDecision] = []
        self._blocked_attempts: list[GatewayDecision] = []
        self._total_submitted: int = 0
        self._total_blocked: int = 0
        self._total_recommended: int = 0
        self._total_auto_executed: int = 0

    @property
    def policy(self) -> AutonomousPolicy:
        return self._policy

    @property
    def reliability_threshold(self) -> float:
        return self._reliability_threshold

    def set_policy(self, policy: AutonomousPolicy) -> None:
        old = self._policy
        self._policy = policy
        logger.info("autonomous policy changed: %s → %s", old.value, policy.value)
        self._event_spine.emit(
            EventDomain.GOVERNANCE,
            "autonomous_policy_changed",
            "autonomous_action_gateway",
            {"old_policy": old.value, "new_policy": policy.value},
            priority=EventPriority.HIGH,
        )

    def set_reliability_threshold(self, threshold: float) -> None:
        self._reliability_threshold = max(0.0, min(1.0, threshold))

    def submit_envelope(self, envelope: ActionEnvelope) -> ActionEnvelope:
        """Submit an ActionEnvelope through the gateway.

        The gateway checks policy and mode before forwarding to the
        GovernedExecutionSpine. This is the ONLY way autonomous systems
        should request mutations.
        """
        risk_severity = _RISK_SEVERITY.get(envelope.risk_level, 1)
        can_recommend, can_low, can_medium_plus = _POLICY_EXECUTION_MAP[self._policy]

        if not can_recommend:
            decision = self._record_decision(
                envelope.source, envelope.intent, envelope.risk_level,
                "blocked", "policy is OBSERVE — no mutations or recommendations",
                envelope.envelope_id,
            )
            envelope.status = EnvelopeStatus.REJECTED
            envelope.rejected_reason = decision.reason
            self._total_blocked += 1
            return envelope

        if risk_severity == 0 and not can_low:
            decision = self._record_decision(
                envelope.source, envelope.intent, envelope.risk_level,
                "recommend_only", "policy allows recommendations only, not execution",
                envelope.envelope_id,
            )
            self._total_recommended += 1
            envelope.status = EnvelopeStatus.PROPOSED
            envelope.constraints.require_approval = True
            self._spine.submit(envelope)
            self._total_submitted += 1
            return envelope

        if risk_severity >= 1 and not can_medium_plus:
            if not can_low:
                decision = self._record_decision(
                    envelope.source, envelope.intent, envelope.risk_level,
                    "recommend_only", "policy allows recommendations only",
                    envelope.envelope_id,
                )
                self._total_recommended += 1
            else:
                decision = self._record_decision(
                    envelope.source, envelope.intent, envelope.risk_level,
                    "pending_approval",
                    f"risk={envelope.risk_level} requires approval in ASSISTED policy",
                    envelope.envelope_id,
                )
            envelope.constraints.require_approval = True
            self._spine.submit(envelope)
            self._total_submitted += 1
            return envelope

        if risk_severity >= 1 and can_medium_plus:
            reliability = self._mode.reliability
            if risk_severity >= 2 or reliability < self._reliability_threshold:
                envelope.constraints.require_approval = True
                self._record_decision(
                    envelope.source, envelope.intent, envelope.risk_level,
                    "pending_approval",
                    f"HIGH/CRITICAL always requires approval or reliability "
                    f"{reliability:.2f} < {self._reliability_threshold}",
                    envelope.envelope_id,
                )
            else:
                self._record_decision(
                    envelope.source, envelope.intent, envelope.risk_level,
                    "allowed",
                    f"AUTONOMOUS policy, risk={envelope.risk_level}, "
                    f"reliability={reliability:.2f} >= threshold",
                    envelope.envelope_id,
                )
                self._total_auto_executed += 1

        self._spine.submit(envelope)
        self._total_submitted += 1
        return envelope

    def execute_if_allowed(self, envelope: ActionEnvelope) -> ActionEnvelope:
        """Convenience: submit + return the envelope with its status.

        Same as submit_envelope — named for readability in tick stages
        where the caller wants to know if execution happened.
        """
        return self.submit_envelope(envelope)

    def recommend_only(self, envelope: ActionEnvelope) -> ActionEnvelope:
        """Force the envelope into recommendation-only mode.

        Used when a stage wants to create a recommendation without
        attempting execution, regardless of current policy.
        """
        envelope.constraints.require_approval = True
        self._record_decision(
            envelope.source, envelope.intent, envelope.risk_level,
            "recommend_only", "explicitly submitted as recommendation only",
            envelope.envelope_id,
        )
        self._total_recommended += 1
        self._spine.submit(envelope)
        self._total_submitted += 1
        return envelope

    def block_direct_mutation(
        self,
        source: str,
        description: str,
        risk_level: str = "medium",
    ) -> bool:
        """Called when a direct mutation attempt is detected.

        Always blocks. Records the attempt. Returns True (blocked).
        Autonomous systems must not call mutation functions directly.
        """
        self._record_decision(
            source, description, risk_level,
            "blocked", "direct mutation blocked — must use ActionEnvelope via gateway",
        )
        self._total_blocked += 1

        self._journal.record(
            envelope_id=f"gateway-block-{int(time.time() * 1000)}",
            phase=JournalPhase.GOVERNANCE_CHECK,
            source=f"autonomous_gateway:{source}",
            details={
                "description": description,
                "risk_level": risk_level,
                "blocked": True,
                "reason": "direct autonomous mutation attempt",
            },
        )

        self._event_spine.emit(
            EventDomain.GOVERNANCE,
            "autonomous_direct_mutation_blocked",
            source,
            {
                "description": description[:200],
                "risk_level": risk_level,
            },
            priority=EventPriority.CRITICAL,
        )

        return True

    def propose_action(
        self,
        source: str,
        intent: str,
        action_type: ActionType,
        execute_fn: Any,
        risk_level: str = "low",
        blast_radius: BlastRadius = BlastRadius.LOCAL_RUNTIME,
        reversibility: ReversibilityClass = ReversibilityClass.FULLY_REVERSIBLE,
        estimated_manual_seconds: float = 60.0,
        mutation_name: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ActionEnvelope:
        """Create and submit an ActionEnvelope in one call.

        Convenience for tick stages that want to propose + submit
        without manually constructing an ActionEnvelope.
        """
        meta = metadata or {}
        if mutation_name:
            meta["mutation_name"] = mutation_name

        envelope = ActionEnvelope(
            intent=intent,
            action_type=action_type,
            source=source,
            execute_fn=execute_fn,
            risk_level=risk_level,
            blast_radius=blast_radius,
            reversibility=reversibility,
            estimated_manual_seconds=estimated_manual_seconds,
            metadata=meta,
        )

        return self.submit_envelope(envelope)

    def _record_decision(
        self,
        source: str,
        intent: str,
        risk_level: str,
        action: str,
        reason: str,
        envelope_id: str = "",
    ) -> GatewayDecision:
        decision = GatewayDecision(
            source=source,
            intent=intent,
            risk_level=risk_level,
            action=action,
            reason=reason,
            envelope_id=envelope_id,
        )

        if len(self._decisions) >= _MAX_DECISIONS:
            self._decisions = self._decisions[-(_MAX_DECISIONS // 2):]
        self._decisions.append(decision)

        if action == "blocked":
            if len(self._blocked_attempts) >= _MAX_BLOCKED:
                self._blocked_attempts = self._blocked_attempts[-(_MAX_BLOCKED // 2):]
            self._blocked_attempts.append(decision)

        self._event_spine.emit(
            EventDomain.GOVERNANCE,
            f"autonomous_gateway_{action}",
            source,
            decision.to_dict(),
            priority=EventPriority.HIGH if action == "blocked" else EventPriority.NORMAL,
        )

        return decision

    # ── Query interface ──────────────────────────────────────────────────

    def recent_decisions(self, limit: int = 20) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._decisions[-limit:]]

    def blocked_attempts(self, limit: int = 20) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._blocked_attempts[-limit:]]

    def pending_autonomous_envelopes(self) -> list[dict[str, Any]]:
        all_pending = self._spine.pending_envelopes(500)
        return [
            e for e in all_pending
            if e.get("source", "").startswith(("workload_runner", "maintenance_loop",
                                                "assisted_executor", "automation_pipeline",
                                                "autonomous_tick", "autonomous_gateway"))
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": self._policy.value,
            "reliability_threshold": self._reliability_threshold,
            "current_mode": self._mode.current_mode.value,
            "current_reliability": round(self._mode.reliability, 4),
            "total_submitted": self._total_submitted,
            "total_blocked": self._total_blocked,
            "total_recommended": self._total_recommended,
            "total_auto_executed": self._total_auto_executed,
            "recent_decisions_count": len(self._decisions),
            "blocked_attempts_count": len(self._blocked_attempts),
        }
