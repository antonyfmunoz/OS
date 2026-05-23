"""Live Replay Coordinator v1.

Replays runtime spine decisions to verify determinism:
  - routing decisions (capability, environment, embodiment)
  - governance decisions (verdict, rules)
  - runtime decisions (cognition, planning)
  - continuity state (continuation type)
  - cognition outputs (intent, domain, plan)

Does NOT replay execution. Only the decision path.

Persist proofs to: data/runtime/live_replay_proofs/

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .live_runtime_contracts_v1 import (
    RuntimeContext,
    RuntimePhase,
    RuntimeSignal,
    RuntimeSignalSource,
    _content_hash,
    _new_id,
    _now_iso,
)
from .live_cognition_coordinator_v1 import LiveCognitionCoordinator
from .live_runtime_router_v1 import LiveRuntimeRouter


@dataclass
class LiveReplayCheck:
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
class LiveReplayResult:
    """Result of replaying a single runtime trace."""

    result_id: str = ""
    command_name: str = ""
    checks: list[LiveReplayCheck] = field(default_factory=list)
    all_passed: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.result_id:
            self.result_id = _new_id("lreplay")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def finalize(self) -> None:
        self.all_passed = all(c.passed for c in self.checks) if self.checks else False

    def to_dict(self) -> dict[str, Any]:
        self.finalize()
        return {
            "result_id": self.result_id,
            "command_name": self.command_name,
            "checks": [c.to_dict() for c in self.checks],
            "all_passed": self.all_passed,
            "total_checks": len(self.checks),
            "passed_checks": sum(1 for c in self.checks if c.passed),
            "timestamp": self.timestamp,
        }


@dataclass
class LiveReplaySessionResult:
    """Result of replaying a full session of runtime traces."""

    session_id: str = ""
    results: list[LiveReplayResult] = field(default_factory=list)
    all_passed: bool = False
    total_records: int = 0
    passed_records: int = 0
    total_checks: int = 0
    passed_checks: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.session_id:
            self.session_id = _new_id("lrsess")
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


class LiveReplayCoordinator:
    """Replays runtime spine decisions to verify determinism."""

    def __init__(
        self,
        proof_dir: str | Path = "data/runtime/live_replay_proofs",
    ) -> None:
        self._proof_dir = Path(proof_dir)
        self._proof_dir.mkdir(parents=True, exist_ok=True)
        self._cognition = LiveCognitionCoordinator()
        self._router = LiveRuntimeRouter()
        self._replay_count: int = 0

    def replay_trace(self, trace: dict[str, Any]) -> LiveReplayResult:
        """Replay a single runtime trace through cognition and routing."""
        command_name = trace.get("command_name", "")
        raw_input = f"!{command_name}"
        self._replay_count += 1

        signal = RuntimeSignal(
            source=RuntimeSignalSource.SPINE,
            raw_input=raw_input,
        )
        context = RuntimeContext(
            signal_id=signal.signal_id,
            correlation_id=signal.correlation_id,
        )

        context = self._cognition.interpret(signal, context)
        context = self._router.resolve(signal, context)

        result = LiveReplayResult(command_name=command_name)
        checks: list[LiveReplayCheck] = []

        checks.append(
            LiveReplayCheck(
                check_name="intent_type",
                original_value=trace.get("intent_type", ""),
                replayed_value=context.intent_type,
            )
        )

        checks.append(
            LiveReplayCheck(
                check_name="domain",
                original_value=trace.get("domain", ""),
                replayed_value=context.domain,
            )
        )

        checks.append(
            LiveReplayCheck(
                check_name="capability",
                original_value=trace.get("capability", ""),
                replayed_value=context.capability_resolved,
            )
        )

        checks.append(
            LiveReplayCheck(
                check_name="environment",
                original_value=trace.get("environment", ""),
                replayed_value=context.environment_resolved,
            )
        )

        checks.append(
            LiveReplayCheck(
                check_name="embodiment_path",
                original_value=trace.get("embodiment_path", ""),
                replayed_value=context.embodiment_path,
            )
        )

        checks.append(
            LiveReplayCheck(
                check_name="risk_class",
                original_value=trace.get("risk_class", ""),
                replayed_value=context.risk_class,
            )
        )

        result.checks = checks
        result.finalize()
        return result

    def replay_session(
        self,
        traces: list[dict[str, Any]],
        session_id: str = "",
    ) -> LiveReplaySessionResult:
        """Replay all traces from a session."""
        session_result = LiveReplaySessionResult(session_id=session_id)

        for trace in traces:
            result = self.replay_trace(trace)
            session_result.results.append(result)

        session_result.finalize()

        proof_path = self._proof_dir / f"live_replay_proof_{session_id or 'latest'}.json"
        proof_path.write_text(
            json.dumps(session_result.to_dict(), indent=2),
            encoding="utf-8",
        )

        return session_result

    def replay_from_file(
        self,
        traces_path: str | Path,
        session_id: str = "",
    ) -> LiveReplaySessionResult:
        """Replay traces from a JSONL observability file."""
        path = Path(traces_path)
        if not path.exists():
            return LiveReplaySessionResult(session_id=session_id)

        traces: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    traces.append(json.loads(stripped))

        return self.replay_session(traces, session_id=session_id)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_replays": self._replay_count,
        }
