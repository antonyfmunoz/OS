"""Loop completion engine — end-state verification and progress reporting.

Agent loops re-verify end state before marking complete.  All verification
is deterministic pattern matching on evidence dictionaries — no LLM.

Provides a contract-based loop model: create a contract with an end-state
description, advance through iterations providing evidence, and the engine
verifies whether the end-state is reached.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LoopStatus(str, Enum):
    """Status of a loop contract."""

    pending = "pending"
    running = "running"
    verified = "verified"
    failed = "failed"
    abandoned = "abandoned"


@dataclass
class LoopContract:
    """A contract for an agent loop with end-state verification.

    Attributes:
        contract_id: Auto-generated unique contract ID.
        task_description: What the loop is trying to accomplish.
        end_state_description: What the end state looks like (natural language).
        max_iterations: Maximum allowed iterations before failure.
        current_iteration: Current iteration count.
        status: Current loop status.
        started_at: ISO timestamp when the loop started.
        completed_at: ISO timestamp when the loop completed (if done).
        evidence_log: List of evidence summaries from each iteration.
    """

    task_description: str
    end_state_description: str
    max_iterations: int = 5
    current_iteration: int = 0
    status: LoopStatus = LoopStatus.pending
    contract_id: str = ""
    started_at: str = ""
    completed_at: Optional[str] = None
    evidence_log: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.contract_id:
            self.contract_id = f"loop-{uuid.uuid4().hex[:12]}"
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "task_description": self.task_description,
            "end_state_description": self.end_state_description,
            "max_iterations": self.max_iterations,
            "current_iteration": self.current_iteration,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "evidence_log": self.evidence_log,
        }


@dataclass
class VerifyResult:
    """Result of an end-state verification check.

    Attributes:
        verified: Whether the end state was confirmed.
        reason: Explanation of verification outcome.
        evidence_summary: Summary of evidence evaluated.
        iteration: Which iteration this verification occurred at.
    """

    verified: bool
    reason: str
    evidence_summary: str
    iteration: int = 0


@dataclass
class LoopProgressReport:
    """Snapshot of loop progress for cockpit display.

    Attributes:
        contract_id: Which contract this report belongs to.
        iteration: Current iteration number.
        status: Current loop status.
        evidence_snapshot: Evidence dict from last check.
        timestamp: When this report was generated.
        lane_id: Which work lane this loop runs in.
    """

    contract_id: str
    iteration: int
    status: str
    evidence_snapshot: dict[str, Any]
    timestamp: str
    lane_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "iteration": self.iteration,
            "status": self.status,
            "evidence_snapshot": self.evidence_snapshot,
            "timestamp": self.timestamp,
            "lane_id": self.lane_id,
        }


class EndStateVerifier:
    """Deterministic end-state verifier — pattern matches evidence against contract.

    Verification strategies (checked in order):
    1. screenshot_taken + "visible" in end_state -> check non-empty image
    2. process_running + "open"/"running" in end_state -> check process name
    3. url_loaded + "page"/"loaded" in end_state -> check URL non-empty
    4. file_exists -> check path non-empty
    5. completed == True -> generic completion
    6. No match -> not verified
    """

    def verify(self, contract: LoopContract, evidence: dict[str, Any]) -> VerifyResult:
        """Verify whether the end state has been reached.

        Args:
            contract: The loop contract with end_state_description.
            evidence: Dictionary of evidence keys/values from the current iteration.

        Returns:
            VerifyResult with verification outcome.
        """
        end_state = contract.end_state_description.lower()
        summaries: list[str] = []

        # Strategy 1: Screenshot + visibility
        if evidence.get("screenshot_taken") and "visible" in end_state:
            image = evidence.get("screenshot_path", "") or evidence.get("image", "")
            if image:
                return VerifyResult(
                    verified=True,
                    reason="screenshot confirms visibility",
                    evidence_summary=f"screenshot at {image}",
                    iteration=contract.current_iteration,
                )
            summaries.append("screenshot_taken but no image path")

        # Strategy 2: Process running + open/running
        if evidence.get("process_running"):
            if "open" in end_state or "running" in end_state:
                proc = evidence.get("process_name", "")
                if proc:
                    return VerifyResult(
                        verified=True,
                        reason=f"process '{proc}' is running",
                        evidence_summary=f"process={proc}",
                        iteration=contract.current_iteration,
                    )
                summaries.append("process_running but no process_name")

        # Strategy 3: URL loaded + page/loaded
        if evidence.get("url_loaded"):
            if "page" in end_state or "loaded" in end_state:
                url = evidence.get("url", "")
                if url:
                    return VerifyResult(
                        verified=True,
                        reason=f"URL loaded: {url}",
                        evidence_summary=f"url={url}",
                        iteration=contract.current_iteration,
                    )
                summaries.append("url_loaded but no url value")

        # Strategy 4: File exists
        if evidence.get("file_exists"):
            path = evidence.get("file_path", "")
            if path:
                return VerifyResult(
                    verified=True,
                    reason=f"file exists at {path}",
                    evidence_summary=f"file={path}",
                    iteration=contract.current_iteration,
                )
            summaries.append("file_exists but no file_path")

        # Strategy 5: Generic completion
        if evidence.get("completed") is True:
            return VerifyResult(
                verified=True,
                reason="generic completion flag set",
                evidence_summary="completed=True",
                iteration=contract.current_iteration,
            )

        # No strategy matched
        summary = "; ".join(summaries) if summaries else "no matching evidence"
        return VerifyResult(
            verified=False,
            reason="no matching verification strategy",
            evidence_summary=summary,
            iteration=contract.current_iteration,
        )


def advance_loop(
    contract: LoopContract, evidence: dict[str, Any]
) -> tuple[LoopContract, VerifyResult]:
    """Advance a loop contract by one iteration with evidence.

    Steps:
    1. Increment current_iteration
    2. Set status to running if pending
    3. Run EndStateVerifier.verify()
    4. If verified -> set status to verified, set completed_at
    5. If current_iteration >= max_iterations and not verified -> set status to failed
    6. Append evidence summary to evidence_log

    Args:
        contract: The loop contract to advance.
        evidence: Evidence dictionary from the current iteration.

    Returns:
        Tuple of (updated contract, verify result).
    """
    contract.current_iteration += 1

    if contract.status == LoopStatus.pending:
        contract.status = LoopStatus.running

    verifier = EndStateVerifier()
    result = verifier.verify(contract, evidence)

    if result.verified:
        contract.status = LoopStatus.verified
        contract.completed_at = datetime.now(timezone.utc).isoformat()
    elif contract.current_iteration >= contract.max_iterations:
        contract.status = LoopStatus.failed
        contract.completed_at = datetime.now(timezone.utc).isoformat()

    contract.evidence_log.append(
        f"iteration={contract.current_iteration}: {result.evidence_summary}"
    )

    return contract, result


def create_loop_report(contract: LoopContract, lane_id: str) -> LoopProgressReport:
    """Create a progress report snapshot for cockpit display.

    Args:
        contract: The loop contract.
        lane_id: The work lane ID this loop runs in.

    Returns:
        LoopProgressReport snapshot.
    """
    return LoopProgressReport(
        contract_id=contract.contract_id,
        iteration=contract.current_iteration,
        status=contract.status.value,
        evidence_snapshot={
            "evidence_count": len(contract.evidence_log),
            "max_iterations": contract.max_iterations,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
        lane_id=lane_id,
    )
