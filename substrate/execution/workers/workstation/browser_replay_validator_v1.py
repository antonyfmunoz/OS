"""Browser Replay Validator v1.

Replays browser/GUI execution decision paths to verify determinism:
  - governance decisions (URL blocks, action blocks, mode constraints)
  - routing decisions (adapter selection, navigation scope)
  - capability resolution (action type approval)
  - visible execution lineage

DOES NOT replay destructive GUI actions. Only the decision path.

Persist proofs to: data/runtime/browser_replay_proofs/

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .browser_gui_contracts_v1 import (
    BrowserActionType,
    BrowserActionVerdict,
    BrowserExecutionRequest,
    BrowserOperationalMode,
    _new_id,
    _now_iso,
)
from .governed_browser_adapter_v1 import GovernedBrowserAdapter
from .browser_operational_modes_v1 import get_browser_mode_definition


@dataclass
class BrowserReplayCheck:
    """A single browser replay determinism check."""

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
class BrowserReplayResult:
    """Result of replaying a single browser execution record."""

    result_id: str = ""
    action_type: str = ""
    target_url: str = ""
    checks: list[BrowserReplayCheck] = field(default_factory=list)
    all_passed: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.result_id:
            self.result_id = _new_id("breplay")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def finalize(self) -> None:
        self.all_passed = all(c.passed for c in self.checks) if self.checks else False

    def to_dict(self) -> dict[str, Any]:
        self.finalize()
        return {
            "result_id": self.result_id,
            "action_type": self.action_type,
            "target_url": self.target_url,
            "checks": [c.to_dict() for c in self.checks],
            "all_passed": self.all_passed,
            "total_checks": len(self.checks),
            "passed_checks": sum(1 for c in self.checks if c.passed),
            "timestamp": self.timestamp,
        }


@dataclass
class BrowserReplaySessionResult:
    """Result of replaying a session of browser execution records."""

    session_id: str = ""
    results: list[BrowserReplayResult] = field(default_factory=list)
    all_passed: bool = False
    total_records: int = 0
    passed_records: int = 0
    total_checks: int = 0
    passed_checks: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _new_id("brsess")
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


class BrowserReplayValidator:
    """Replays browser execution decision paths to verify determinism."""

    def __init__(
        self,
        operational_mode: BrowserOperationalMode = BrowserOperationalMode.INSPECTION,
        proof_dir: str | Path = "data/runtime/browser_replay_proofs",
    ) -> None:
        self._mode = operational_mode
        self._mode_def = get_browser_mode_definition(operational_mode)
        self._browser = GovernedBrowserAdapter(operational_mode)
        self._proof_dir = Path(proof_dir)
        self._proof_dir.mkdir(parents=True, exist_ok=True)
        self._replay_count = 0

    def set_mode(self, mode: BrowserOperationalMode) -> None:
        self._mode = mode
        self._mode_def = get_browser_mode_definition(mode)
        self._browser.set_mode(mode)

    def replay_record(self, record: dict[str, Any]) -> BrowserReplayResult:
        """Replay a single browser execution record through the decision path."""
        action_str = record.get("action_type", "inspect_tabs")
        target_url = record.get("target_url", "")
        self._replay_count += 1

        try:
            action_type = BrowserActionType(action_str)
        except ValueError:
            action_type = BrowserActionType.INSPECT_TABS

        result = BrowserReplayResult(action_type=action_str, target_url=target_url)
        checks: list[BrowserReplayCheck] = []

        request = BrowserExecutionRequest(
            action_type=action_type,
            target_url=target_url,
            operational_mode=self._mode,
        )
        decision = self._browser.evaluate_action(request)

        # 1. Replay governance verdict
        checks.append(
            BrowserReplayCheck(
                check_name="governance_verdict",
                original_value=record.get("governance_verdict", ""),
                replayed_value=decision.verdict.value,
            )
        )

        # 2. Replay risk classification
        checks.append(
            BrowserReplayCheck(
                check_name="risk_class",
                original_value=record.get("risk_class", "safe"),
                replayed_value=decision.risk_class,
            )
        )

        # 3. Replay adapter routing
        original_adapter = record.get("adapter_used", "")
        replayed_adapter = (
            "governed_browser" if decision.verdict == BrowserActionVerdict.APPROVED else "denied"
        )
        checks.append(
            BrowserReplayCheck(
                check_name="adapter_routing",
                original_value=original_adapter,
                replayed_value=replayed_adapter,
            )
        )

        # 4. Replay operational mode
        checks.append(
            BrowserReplayCheck(
                check_name="operational_mode",
                original_value=record.get("operational_mode", self._mode.value),
                replayed_value=self._mode.value,
            )
        )

        result.checks = checks
        result.finalize()
        return result

    def replay_session(
        self,
        records: list[dict[str, Any]],
        session_id: str = "",
    ) -> BrowserReplaySessionResult:
        """Replay all records from a browser session."""
        session_result = BrowserReplaySessionResult(session_id=session_id)

        for record in records:
            result = self.replay_record(record)
            session_result.results.append(result)

        session_result.finalize()

        proof_path = self._proof_dir / f"browser_replay_proof_{session_id or 'latest'}.json"
        proof_path.write_text(json.dumps(session_result.to_dict(), indent=2), encoding="utf-8")

        return session_result

    def replay_from_file(
        self,
        records_path: str | Path,
        session_id: str = "",
    ) -> BrowserReplaySessionResult:
        """Replay records from a JSONL observability file."""
        path = Path(records_path)
        if not path.exists():
            return BrowserReplaySessionResult(session_id=session_id)

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
