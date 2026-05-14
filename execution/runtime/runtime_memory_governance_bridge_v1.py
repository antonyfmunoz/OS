"""Runtime-to-Memory Governance Bridge v1.

Determines which runtime events should be promoted to canonical memory.
Not every event becomes memory — only operationally significant outcomes,
repeated patterns, and governance-gated decisions.

Deterministic. Rule-based. All promotions produce governance receipts.

UMH substrate subsystem. Phase 96.8BN.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .runtime_cognition_contracts_v1 import (
    OutcomeResult,
    _deterministic_id,
)


class PromotionRule(str, Enum):
    IMPORTANT_OUTCOME = "important_outcome"
    FAILURE_RECORD = "failure_record"
    GOVERNANCE_OVERRIDE = "governance_override"
    REPEATED_PATTERN = "repeated_pattern"
    CRITICAL_OPEN_LOOP = "critical_open_loop"
    NEVER_PROMOTE = "never_promote"


@dataclass
class PromotionCandidate:
    """A runtime record that may be promoted to canonical memory."""

    candidate_id: str
    source_record_id: str
    source_type: str
    content: str
    label: str
    rule_applied: PromotionRule
    should_promote: bool = False
    reason: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_record_id": self.source_record_id,
            "source_type": self.source_type,
            "content": self.content,
            "label": self.label,
            "rule_applied": self.rule_applied.value,
            "should_promote": self.should_promote,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


OUTCOME_PROMOTE_RESULTS = frozenset(
    {
        OutcomeResult.FAILURE.value,
        OutcomeResult.TIMEOUT.value,
        OutcomeResult.BLOCKED.value,
    }
)

OUTCOME_SUCCESS_COMMANDS = frozenset(
    {
        "ingest-safe-doc-cu",
        "chrome-proof",
        "explore-environment",
    }
)


class RuntimeMemoryGovernanceBridge:
    """Evaluates runtime records for memory promotion."""

    def __init__(
        self,
        receipts_dir: str | Path = "data/runtime/runtime_promotion_receipts",
    ):
        self.receipts_dir = Path(receipts_dir)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_path = self.receipts_dir / "promotion_decisions.jsonl"

    def evaluate_outcome(self, outcome: dict[str, Any]) -> PromotionCandidate:
        """Evaluate whether a runtime outcome should become memory."""
        result = outcome.get("result", "")
        command = outcome.get("command", "unknown")
        record_id = outcome.get("outcome_id", "")
        error = outcome.get("error_message", "")

        cand_id = _deterministic_id("rtprom", f"{record_id}:{result}")

        if result in OUTCOME_PROMOTE_RESULTS:
            candidate = PromotionCandidate(
                candidate_id=cand_id,
                source_record_id=record_id,
                source_type="outcome",
                content=f"Command '{command}' resulted in {result}. {error}".strip(),
                label=f"Runtime {result}: {command}",
                rule_applied=PromotionRule.FAILURE_RECORD,
                should_promote=True,
                reason=f"Operationally critical: {result}",
            )
            self._record_decision(candidate)
            return candidate

        if result == OutcomeResult.SUCCESS.value and command in OUTCOME_SUCCESS_COMMANDS:
            candidate = PromotionCandidate(
                candidate_id=cand_id,
                source_record_id=record_id,
                source_type="outcome",
                content=f"Command '{command}' completed successfully.",
                label=f"Runtime success: {command}",
                rule_applied=PromotionRule.IMPORTANT_OUTCOME,
                should_promote=True,
                reason=f"Important operational outcome: {command}",
            )
            self._record_decision(candidate)
            return candidate

        candidate = PromotionCandidate(
            candidate_id=cand_id,
            source_record_id=record_id,
            source_type="outcome",
            content=f"Command '{command}': {result}",
            label=f"Runtime {result}: {command}",
            rule_applied=PromotionRule.NEVER_PROMOTE,
            should_promote=False,
            reason="Routine outcome — does not warrant memory promotion",
        )
        self._record_decision(candidate)
        return candidate

    def evaluate_open_loop(self, loop: dict[str, Any]) -> PromotionCandidate:
        """Evaluate whether a critical open loop should become memory."""
        loop_id = loop.get("loop_id", "")
        loop_type = loop.get("loop_type", "")
        description = loop.get("description", "")

        cand_id = _deterministic_id("rtprom", f"{loop_id}:openloop")

        critical_types = {"failed_execution", "pending_governance", "unresolved_contradiction"}
        if loop_type in critical_types:
            candidate = PromotionCandidate(
                candidate_id=cand_id,
                source_record_id=loop_id,
                source_type="open_loop",
                content=f"Unresolved {loop_type}: {description}",
                label=f"Open loop: {loop_type}",
                rule_applied=PromotionRule.CRITICAL_OPEN_LOOP,
                should_promote=True,
                reason=f"Critical unresolved loop: {loop_type}",
            )
            self._record_decision(candidate)
            return candidate

        candidate = PromotionCandidate(
            candidate_id=cand_id,
            source_record_id=loop_id,
            source_type="open_loop",
            content=f"{loop_type}: {description}",
            label=f"Open loop: {loop_type}",
            rule_applied=PromotionRule.NEVER_PROMOTE,
            should_promote=False,
            reason="Non-critical open loop — tracked but not promoted",
        )
        self._record_decision(candidate)
        return candidate

    def _record_decision(self, candidate: PromotionCandidate) -> None:
        with open(self.receipts_path, "a") as f:
            f.write(json.dumps(candidate.to_dict(), separators=(",", ":")) + "\n")

    def load_decisions(self) -> list[dict[str, Any]]:
        if not self.receipts_path.exists():
            return []
        records = []
        with open(self.receipts_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
