"""Workstation Replay Validator v1.

Replays workstation execution decision paths to verify determinism:
  - governance decisions (structural block, mode allowlist, chain detection)
  - routing decisions (adapter selection, operational mode constraints)
  - command approval (shell verdict, tmux verdict)
  - environment selection (adapter used, target session)

DOES NOT replay destructive execution. Only the decision path.
Same input → same governance verdict, same adapter routing,
same risk classification.

Persist proofs to: data/runtime/workstation_replay_proofs/

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .workstation_contracts_v1 import (
    OperationalMode,
    ShellCommandVerdict,
    _new_id,
    _now_iso,
)
from .governed_shell_adapter_v1 import GovernedShellAdapter
from .workstation_operational_modes_v1 import get_mode_definition


@dataclass
class ReplayCheck:
    """A single replay determinism check."""

    check_name: str = ""
    original_value: str = ""
    replayed_value: str = ""
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
    """Result of replaying a single workstation execution record."""

    result_id: str = ""
    command: str = ""
    checks: list[ReplayCheck] = field(default_factory=list)
    all_passed: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.result_id:
            self.result_id = _new_id("wreplay")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def finalize(self) -> None:
        self.all_passed = all(c.passed for c in self.checks) if self.checks else False

    def to_dict(self) -> dict[str, Any]:
        self.finalize()
        return {
            "result_id": self.result_id,
            "command": self.command,
            "checks": [c.to_dict() for c in self.checks],
            "all_passed": self.all_passed,
            "total_checks": len(self.checks),
            "passed_checks": sum(1 for c in self.checks if c.passed),
            "timestamp": self.timestamp,
        }


@dataclass
class ReplaySessionResult:
    """Result of replaying an entire session of workstation execution records."""

    session_id: str = ""
    results: list[ReplayResult] = field(default_factory=list)
    all_passed: bool = False
    total_records: int = 0
    passed_records: int = 0
    total_checks: int = 0
    passed_checks: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _new_id("wrsess")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def finalize(self) -> None:
        for r in self.results:
            r.finalize()
        self.total_records = len(self.results)
        self.passed_records = sum(1 for r in self.results if r.all_passed)
        self.total_checks = sum(len(r.checks) for r in self.results)
        self.passed_checks = sum(sum(1 for c in r.checks if c.passed) for r in self.results)
        self.all_passed = self.total_records > 0 and self.total_records == self.passed_records

    def to_dict(self) -> dict[str, Any]:
        self.finalize()
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


class WorkstationReplayValidator:
    """Replays workstation execution decision paths to verify determinism."""

    def __init__(
        self,
        operational_mode: OperationalMode = OperationalMode.DEVELOPER,
        proof_dir: str | Path = "data/runtime/workstation_replay_proofs",
    ) -> None:
        self._mode = operational_mode
        self._mode_def = get_mode_definition(operational_mode)
        self._shell = GovernedShellAdapter(operational_mode)
        self._proof_dir = Path(proof_dir)
        self._proof_dir.mkdir(parents=True, exist_ok=True)
        self._replay_count = 0

    def set_mode(self, mode: OperationalMode) -> None:
        self._mode = mode
        self._mode_def = get_mode_definition(mode)
        self._shell.set_mode(mode)

    def replay_record(self, record: dict[str, Any]) -> ReplayResult:
        """Replay a single execution record through the decision path.

        Replays: governance verdict, risk class, adapter routing,
        operational mode constraint. Does NOT re-execute commands.
        """
        command = record.get("command", "")
        self._replay_count += 1

        result = ReplayResult(command=command)
        checks: list[ReplayCheck] = []

        # 1. Replay shell governance verdict
        decision = self._shell.evaluate_command(command)
        checks.append(
            ReplayCheck(
                check_name="governance_verdict",
                original_value=record.get("governance_verdict", ""),
                replayed_value=decision.verdict.value,
            )
        )

        # 2. Replay risk classification
        checks.append(
            ReplayCheck(
                check_name="risk_class",
                original_value=record.get("risk_class", "safe"),
                replayed_value=decision.risk_class,
            )
        )

        # 3. Replay adapter routing
        original_adapter = record.get("adapter_used", "")
        replayed_adapter = self._resolve_adapter(command, record)
        checks.append(
            ReplayCheck(
                check_name="adapter_routing",
                original_value=original_adapter,
                replayed_value=replayed_adapter,
            )
        )

        # 4. Replay operational mode constraint
        original_mode = record.get("operational_mode", self._mode.value)
        checks.append(
            ReplayCheck(
                check_name="operational_mode",
                original_value=original_mode,
                replayed_value=self._mode.value,
            )
        )

        # 5. Replay mode allowlist check
        prefix = self._shell._extract_prefix(command.strip())
        mode_allowed = self._mode_def.allows_command(prefix)
        original_mode_allowed = (
            record.get("governance_verdict", "") != "denied"
            or record.get("denial_reason", "") == ""
        )
        # If the original was denied due to mode, the replayed should also deny
        replayed_mode_verdict = "allowed" if mode_allowed else "denied"
        original_mode_verdict = "allowed" if original_mode_allowed else "denied"
        # Only check mode allowlist when verdict matches (structural blocks supersede)
        if decision.verdict == ShellCommandVerdict.DENIED and "STRUCTURAL" in str(
            decision.rules_applied
        ):
            replayed_mode_verdict = "structural_block"
            original_mode_verdict = "structural_block"
        checks.append(
            ReplayCheck(
                check_name="mode_allowlist",
                original_value=original_mode_verdict,
                replayed_value=replayed_mode_verdict,
            )
        )

        result.checks = checks
        result.finalize()
        return result

    def replay_session(
        self,
        records: list[dict[str, Any]],
        session_id: str = "",
    ) -> ReplaySessionResult:
        """Replay all records from a workstation session."""
        session_result = ReplaySessionResult(session_id=session_id)

        for record in records:
            result = self.replay_record(record)
            session_result.results.append(result)

        session_result.finalize()

        proof_path = self._proof_dir / f"replay_proof_{session_id or 'latest'}.json"
        proof_path.write_text(json.dumps(session_result.to_dict(), indent=2), encoding="utf-8")

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

        records: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))

        return self.replay_session(records, session_id=session_id)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_replays": self._replay_count,
            "operational_mode": self._mode.value,
        }

    def _resolve_adapter(self, command: str, record: dict[str, Any]) -> str:
        """Determine which adapter would be selected for this command."""
        target_session = record.get("target_session", "")
        adapter_type = record.get("adapter_type", "")

        if adapter_type == "tmux" or target_session:
            if self._mode_def.allows_adapter("tmux"):
                return "tmux"
            return "denied"

        if self._mode_def.allows_adapter("shell"):
            return "governed_shell"
        return "denied"
