"""Governance Execution Bridge v1 for the canonical runtime spine.

Pre-execution governance gate. Every command must pass through
governance evaluation before the spine dispatches it.

Rules:
  1. Forbidden commands are structurally blocked (no override)
  2. Safe commands auto-approve
  3. Low/Medium risk commands approve with governance trace
  4. High/Critical risk commands require explicit approval
  5. All decisions are persisted with full lineage

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .execution_contracts_v1 import (
    GovernanceEvaluation,
    GovernanceVerdict,
    InterpretedIntent,
    RiskClass,
    _new_id,
    _now_iso,
)
from .capability_router_v1 import FORBIDDEN_COMMANDS, SAFE_COMMANDS


FORBIDDEN_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "wallet_execution",
        "financial_execution",
        "credential_access",
        "recursive_runtime_spawning",
        "canonical_mutation_without_governance",
        "self_govern",
    }
)

AUTO_APPROVE_RISK: frozenset[RiskClass] = frozenset({RiskClass.SAFE, RiskClass.LOW})


@dataclass
class GovernanceDecisionRecord:
    """Persisted record of a governance decision."""

    decision_id: str = ""
    intent_id: str = ""
    command_name: str = ""
    risk_class: str = ""
    verdict: str = ""
    rules_applied: list[str] = field(default_factory=list)
    denial_reasons: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.decision_id:
            self.decision_id = _new_id("govdec")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "intent_id": self.intent_id,
            "command_name": self.command_name,
            "risk_class": self.risk_class,
            "verdict": self.verdict,
            "rules_applied": self.rules_applied,
            "denial_reasons": self.denial_reasons,
            "timestamp": self.timestamp,
        }


class GovernanceExecutionBridge:
    """Pre-execution governance gate for the canonical runtime spine."""

    def __init__(
        self,
        decisions_dir: str | Path = "data/runtime/governance_decisions",
    ) -> None:
        self._decisions_dir = Path(decisions_dir)
        self._decisions_dir.mkdir(parents=True, exist_ok=True)
        self._ledger_path = self._decisions_dir / "governance_decisions.jsonl"
        self._decisions: list[GovernanceDecisionRecord] = []

    def evaluate(self, intent: InterpretedIntent) -> GovernanceEvaluation:
        """Evaluate whether an intent is governance-approved for execution."""
        command = intent.command_name
        risk = intent.risk_class
        rules: list[str] = []
        denial_reasons: list[str] = []

        # Rule 1: Structural prohibition
        if command in FORBIDDEN_COMMANDS or command in FORBIDDEN_ACTION_TYPES:
            rules.append("STRUCTURAL_PROHIBITION")
            denial_reasons.append(f"Command '{command}' is structurally forbidden")
            evaluation = GovernanceEvaluation(
                intent_id=intent.intent_id,
                command_name=command,
                risk_class=risk,
                verdict=GovernanceVerdict.STRUCTURALLY_FORBIDDEN,
                denial_reasons=denial_reasons,
                governance_rules_applied=rules,
            )
            self._record_decision(evaluation)
            return evaluation

        # Rule 2: Safe auto-approve
        if command in SAFE_COMMANDS and risk in AUTO_APPROVE_RISK:
            rules.append("SAFE_AUTO_APPROVE")
            evaluation = GovernanceEvaluation(
                intent_id=intent.intent_id,
                command_name=command,
                risk_class=risk,
                verdict=GovernanceVerdict.APPROVED,
                governance_rules_applied=rules,
            )
            self._record_decision(evaluation)
            return evaluation

        # Rule 3: Medium risk — approved with trace
        if risk == RiskClass.MEDIUM:
            rules.append("MEDIUM_RISK_GOVERNED_APPROVE")
            evaluation = GovernanceEvaluation(
                intent_id=intent.intent_id,
                command_name=command,
                risk_class=risk,
                verdict=GovernanceVerdict.APPROVED,
                governance_rules_applied=rules,
            )
            self._record_decision(evaluation)
            return evaluation

        # Rule 4: High/Critical — requires approval
        if risk in (RiskClass.HIGH, RiskClass.CRITICAL):
            rules.append("HIGH_RISK_REQUIRES_APPROVAL")
            evaluation = GovernanceEvaluation(
                intent_id=intent.intent_id,
                command_name=command,
                risk_class=risk,
                verdict=GovernanceVerdict.REQUIRES_APPROVAL,
                denial_reasons=["High/critical risk requires explicit approval"],
                governance_rules_applied=rules,
            )
            self._record_decision(evaluation)
            return evaluation

        # Rule 5: Forbidden risk class
        if risk == RiskClass.FORBIDDEN:
            rules.append("FORBIDDEN_RISK_CLASS")
            denial_reasons.append(f"Risk class FORBIDDEN for command '{command}'")
            evaluation = GovernanceEvaluation(
                intent_id=intent.intent_id,
                command_name=command,
                risk_class=risk,
                verdict=GovernanceVerdict.DENIED,
                denial_reasons=denial_reasons,
                governance_rules_applied=rules,
            )
            self._record_decision(evaluation)
            return evaluation

        # Default: approve with trace
        rules.append("DEFAULT_GOVERNED_APPROVE")
        evaluation = GovernanceEvaluation(
            intent_id=intent.intent_id,
            command_name=command,
            risk_class=risk,
            verdict=GovernanceVerdict.APPROVED,
            governance_rules_applied=rules,
        )
        self._record_decision(evaluation)
        return evaluation

    def get_decisions(self) -> list[GovernanceDecisionRecord]:
        return list(self._decisions)

    def load_decisions(self) -> list[dict[str, Any]]:
        """Load all decisions from the ledger."""
        if not self._ledger_path.exists():
            return []
        decisions = []
        with open(self._ledger_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    decisions.append(json.loads(line))
        return decisions

    def get_stats(self) -> dict[str, Any]:
        by_verdict: dict[str, int] = {}
        for d in self._decisions:
            by_verdict[d.verdict] = by_verdict.get(d.verdict, 0) + 1
        return {
            "total_decisions": len(self._decisions),
            "by_verdict": by_verdict,
        }

    def _record_decision(self, evaluation: GovernanceEvaluation) -> None:
        record = GovernanceDecisionRecord(
            intent_id=evaluation.intent_id,
            command_name=evaluation.command_name,
            risk_class=evaluation.risk_class.value,
            verdict=evaluation.verdict.value,
            rules_applied=evaluation.governance_rules_applied,
            denial_reasons=evaluation.denial_reasons,
        )
        self._decisions.append(record)
        with open(self._ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), default=str) + "\n")
