"""UMH Improvement Governor — controlled self-modification with audit trail.

Allows system components to PROPOSE improvements without silent mutation.
Changes are classified by risk and only low-risk changes auto-apply.
Medium/high-risk changes are logged as proposals for human review.

Risk levels:
- low:    config, ranking weights, thresholds
- medium: routing weights, objective weights, strategy scoring
- high:   code logic, primitive mapping, execution behavior

Pure stdlib. No LLM calls. I/O limited to proposal files and audit log.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Proposal data
# ---------------------------------------------------------------------------

RiskLevel = Literal["low", "medium", "high"]


@dataclass
class ImprovementProposal:
    """A proposed system modification with risk classification."""

    id: str
    timestamp: float
    target_component: str
    proposed_change: dict[str, Any]
    reason: str
    expected_impact: str
    risk_level: RiskLevel
    requires_approval: bool
    rollback_plan: str
    status: str = "pending"
    applied_at: float | None = None
    source: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "target_component": self.target_component,
            "proposed_change": self.proposed_change,
            "reason": self.reason,
            "expected_impact": self.expected_impact,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "rollback_plan": self.rollback_plan,
            "status": self.status,
            "applied_at": self.applied_at,
            "source": self.source,
            "evidence": self.evidence,
        }


# ---------------------------------------------------------------------------
# Governor
# ---------------------------------------------------------------------------


class Governor:
    """Manages system self-improvement proposals.

    Low-risk changes are auto-applied and logged.
    Medium/high-risk changes are written as proposals for human review.
    All changes are auditable and reversible.
    """

    def __init__(
        self,
        *,
        proposals_dir: Path | str | None = None,
        log_file: Path | str | None = None,
    ) -> None:
        self._proposals: list[ImprovementProposal] = []
        self._applied: dict[str, dict[str, Any]] = {}

        self._proposals_dir = Path(proposals_dir) if proposals_dir else None
        self._log_file = Path(log_file) if log_file else None

        if self._proposals_dir:
            self._proposals_dir.mkdir(parents=True, exist_ok=True)
        if self._log_file:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def propose(
        self,
        target_component: str,
        proposed_change: dict[str, Any],
        reason: str,
        risk_level: RiskLevel = "medium",
        *,
        expected_impact: str = "",
        rollback_plan: str = "",
        source: str = "",
        evidence: dict[str, Any] | None = None,
    ) -> ImprovementProposal:
        """Create an improvement proposal.

        Low-risk proposals are auto-applied.
        Medium/high-risk proposals require approval.
        """
        proposal_id = f"imp_{int(time.time())}_{len(self._proposals):03d}"
        requires_approval = risk_level in ("medium", "high")

        if not rollback_plan:
            rollback_plan = f"revert {target_component} to pre-change state"

        if not expected_impact:
            expected_impact = f"improve {target_component} behavior"

        proposal = ImprovementProposal(
            id=proposal_id,
            timestamp=time.time(),
            target_component=target_component,
            proposed_change=proposed_change,
            reason=reason,
            expected_impact=expected_impact,
            risk_level=risk_level,
            requires_approval=requires_approval,
            rollback_plan=rollback_plan,
            source=source,
            evidence=evidence or {},
        )

        self._proposals.append(proposal)

        if not requires_approval:
            proposal.status = "applied"
            proposal.applied_at = time.time()
            self._log(proposal, "auto_applied")
        else:
            proposal.status = "pending"
            self._write_proposal(proposal)
            self._log(proposal, "proposed")

        return proposal

    def approve(self, proposal_id: str) -> ImprovementProposal | None:
        """Approve and apply a pending proposal."""
        proposal = self._find(proposal_id)
        if not proposal or proposal.status != "pending":
            return None

        proposal.status = "applied"
        proposal.applied_at = time.time()
        self._log(proposal, "approved_and_applied")
        return proposal

    def reject(self, proposal_id: str, reason: str = "") -> ImprovementProposal | None:
        """Reject a pending proposal."""
        proposal = self._find(proposal_id)
        if not proposal or proposal.status != "pending":
            return None

        proposal.status = "rejected"
        proposal.evidence["rejection_reason"] = reason
        self._log(proposal, "rejected")
        return proposal

    def rollback(self, proposal_id: str) -> ImprovementProposal | None:
        """Roll back an applied proposal."""
        proposal = self._find(proposal_id)
        if not proposal or proposal.status != "applied":
            return None

        proposal.status = "rolled_back"
        self._log(proposal, "rolled_back")
        return proposal

    def get_pending(self) -> list[ImprovementProposal]:
        """Return all pending proposals awaiting approval."""
        return [p for p in self._proposals if p.status == "pending"]

    def get_applied(self) -> list[ImprovementProposal]:
        """Return all applied proposals."""
        return [p for p in self._proposals if p.status == "applied"]

    def get_all(self) -> list[ImprovementProposal]:
        """Return all proposals."""
        return list(self._proposals)

    def propose_from_objective_results(
        self,
        objective_results: list[dict[str, Any]],
        aggregate_score: float,
    ) -> list[ImprovementProposal]:
        """Generate proposals based on multi-objective evaluation results."""
        proposals: list[ImprovementProposal] = []

        for result in objective_results:
            if result.get("achieved"):
                continue

            name = result.get("name", "unknown")
            score = result.get("score", 0)
            gap = result.get("gap", 0)
            weight = result.get("weight", 0)
            is_hard = result.get("hard_constraint", False)

            if is_hard:
                proposals.append(
                    self.propose(
                        target_component="objective_engine",
                        proposed_change={
                            f"{name}.threshold": "review_and_adjust",
                            "current_gap": gap,
                        },
                        reason=f"Hard constraint '{name}' failed with gap {gap:.4f}. Threshold may be unrealistic.",
                        risk_level="medium",
                        expected_impact=f"Align {name} threshold with achievable range",
                        source="objective_analysis",
                        evidence=result,
                    )
                )
            elif weight >= 0.3 and score < 0.5:
                proposals.append(
                    self.propose(
                        target_component="router",
                        proposed_change={
                            "prioritize_objective": name,
                            "current_score": score,
                        },
                        reason=f"High-weight objective '{name}' (w={weight}) scored only {score:.2f}",
                        risk_level="low",
                        expected_impact=f"Improve {name} in next execution",
                        source="objective_analysis",
                        evidence=result,
                    )
                )

        return proposals

    def propose_from_strategy(
        self,
        strategy: dict[str, Any],
        current_context: str = "",
    ) -> ImprovementProposal | None:
        """Propose adopting a successful strategy pattern."""
        success_rate = strategy.get("success_rate", 0)
        confidence = strategy.get("confidence", 0)

        if success_rate < 0.6 or confidence < 0.4:
            return None

        return self.propose(
            target_component="composer",
            proposed_change={
                "adopt_strategy": strategy.get("strategy_id", ""),
                "primitive_signature": strategy.get("primitive_signature", []),
            },
            reason=f"Strategy has {success_rate:.0%} success rate with {confidence:.0%} confidence",
            risk_level="low" if confidence >= 0.7 else "medium",
            expected_impact="Improved composition from proven pattern",
            source="strategy_reuse",
            evidence=strategy,
        )

    # -------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------

    def _find(self, proposal_id: str) -> ImprovementProposal | None:
        for p in self._proposals:
            if p.id == proposal_id:
                return p
        return None

    def _write_proposal(self, proposal: ImprovementProposal) -> None:
        """Write proposal to filesystem for human review."""
        if not self._proposals_dir:
            return
        path = self._proposals_dir / f"{proposal.id}.json"
        path.write_text(json.dumps(proposal.to_dict(), indent=2))

    def _log(self, proposal: ImprovementProposal, event: str) -> None:
        """Append to audit log."""
        if not self._log_file:
            return
        entry = {
            "event": event,
            "proposal_id": proposal.id,
            "timestamp": time.time(),
            "risk_level": proposal.risk_level,
            "target": proposal.target_component,
            "status": proposal.status,
        }
        with open(self._log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")


__all__ = [
    "ImprovementProposal",
    "Governor",
    "RiskLevel",
]
