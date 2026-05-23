"""Runtime Replay Engine v1 for the canonical runtime spine.

Replays execution sequences from observability logs to verify
determinism. Same input → same routing decisions, same governance
verdicts, same capability selections. No re-execution of side effects.

Replay verifies the DECISION PATH, not the EXECUTION.

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .execution_contracts_v1 import (
    ExecutionSignal,
    InterpretedIntent,
    RiskClass,
    SignalSource,
    _new_id,
    _now_iso,
)
from .capability_router_v1 import CapabilityRouter
from .environment_registry_v1 import EnvironmentRegistry
from .governance_execution_bridge_v1 import GovernanceExecutionBridge


@dataclass
class ReplayCheck:
    """A single replay determinism check."""

    check_name: str
    original_value: str
    replayed_value: str
    passed: bool = False

    def __post_init__(self) -> None:
        self.passed = self.original_value == self.replayed_value

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "original_value": self.original_value,
            "replayed_value": self.replayed_value,
            "passed": self.passed,
        }


@dataclass
class ReplayResult:
    """Result of replaying a single execution record."""

    record_id: str
    command_name: str
    checks: list[ReplayCheck] = field(default_factory=list)
    all_passed: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()
        self.all_passed = all(c.passed for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "command_name": self.command_name,
            "checks": [c.to_dict() for c in self.checks],
            "all_passed": self.all_passed,
            "total_checks": len(self.checks),
            "passed_checks": sum(1 for c in self.checks if c.passed),
            "timestamp": self.timestamp,
        }


@dataclass
class ReplaySessionResult:
    """Result of replaying an entire session's execution records."""

    session_id: str = ""
    results: list[ReplayResult] = field(default_factory=list)
    all_passed: bool = False
    total_records: int = 0
    passed_records: int = 0
    total_checks: int = 0
    passed_checks: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = _now_iso()

    def finalize(self) -> None:
        self.total_records = len(self.results)
        self.passed_records = sum(1 for r in self.results if r.all_passed)
        self.total_checks = sum(len(r.checks) for r in self.results)
        self.passed_checks = sum(sum(1 for c in r.checks if c.passed) for r in self.results)
        self.all_passed = self.total_records == self.passed_records

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "all_passed": self.all_passed,
            "total_records": self.total_records,
            "passed_records": self.passed_records,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "results": [r.to_dict() for r in self.results],
            "timestamp": self.timestamp,
        }


class RuntimeReplayEngine:
    """Replays execution decision paths to verify determinism."""

    def __init__(
        self,
        capability_router: CapabilityRouter,
        governance_bridge: GovernanceExecutionBridge,
        proof_dir: str | Path = "data/runtime/replay_proofs",
    ) -> None:
        self._router = capability_router
        self._governance = governance_bridge
        self._proof_dir = Path(proof_dir)
        self._proof_dir.mkdir(parents=True, exist_ok=True)

    def replay_record(self, record: dict[str, Any]) -> ReplayResult:
        """Replay a single observability record through the decision path."""
        command = record.get("command_name", "")
        record_id = record.get("record_id", "")
        checks: list[ReplayCheck] = []

        # Replay routing decision
        route = self._router.resolve(command)
        original_cap = record.get(
            "capability", route.capability.value if route.capability else "none"
        )
        replayed_cap = route.capability.value if route.capability else "none"
        checks.append(
            ReplayCheck(
                check_name="capability_resolved",
                original_value=original_cap,
                replayed_value=replayed_cap,
            )
        )

        checks.append(
            ReplayCheck(
                check_name="risk_class",
                original_value=record.get("risk_class", "safe"),
                replayed_value=route.risk_class.value,
            )
        )

        # Replay governance decision
        intent = InterpretedIntent(
            signal_id="replay",
            command_name=command,
            risk_class=route.risk_class,
            required_capabilities=[route.capability.value] if route.capability else [],
        )
        gov = self._governance.evaluate(intent)
        checks.append(
            ReplayCheck(
                check_name="governance_verdict",
                original_value=record.get("governance_verdict", "approved"),
                replayed_value=gov.verdict.value,
            )
        )

        return ReplayResult(
            record_id=record_id,
            command_name=command,
            checks=checks,
        )

    def replay_session(
        self, records: list[dict[str, Any]], session_id: str = ""
    ) -> ReplaySessionResult:
        """Replay all records from a session."""
        session_result = ReplaySessionResult(session_id=session_id)

        for record in records:
            result = self.replay_record(record)
            session_result.results.append(result)

        session_result.finalize()

        # Persist proof
        proof_path = self._proof_dir / f"replay_proof_{session_id or 'latest'}.json"
        proof_path.write_text(json.dumps(session_result.to_dict(), indent=2))

        return session_result

    def replay_from_file(
        self,
        records_path: str | Path,
        session_id: str = "",
    ) -> ReplaySessionResult:
        """Replay records from a JSONL observability file."""
        path = Path(records_path)
        if not path.exists():
            return ReplaySessionResult(session_id=session_id)

        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        return self.replay_session(records, session_id=session_id)
