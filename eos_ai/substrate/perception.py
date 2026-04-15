"""
Perception layer — ambient sensing of system and environment state.

Collects structured observations from across the substrate (tasks, pipelines,
operator session, node registry, git, runtime logs) into a unified stream of
PerceptionRecords.  The cognitive loop can consume these records to decide
what deserves attention without polling individual subsystems.

Design rules (mirror substrate conventions):
- Additive only — never imported on the hot path.
- Best-effort persistence — flush failures log, never raise.
- Thread-safe singleton store backed by substrate.storage.
- Bounded — max 1000 records, oldest INFO records pruned first.
- Collectors never raise — catch all exceptions internally and log.
- Fingerprint-based dedup — source + summary hash prevents duplicates.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional

# ─── Constants ────────────────────────────────────────────────────────────────

_STORAGE_KEY = "perception_records"
_MAX_RECORDS = 1000


def _log(msg: str) -> None:
    print(f"[substrate.perception] {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return f"perc_{uuid.uuid4().hex[:12]}"


def _make_fingerprint(source_value: str, summary: str) -> str:
    """Compute a stable dedup hash from source value and summary."""
    return hashlib.sha256(f"{source_value}:{summary}".encode()).hexdigest()[:16]


# ─── Enums ────────────────────────────────────────────────────────────────────


class PerceptionSource(str, Enum):
    """Origin subsystem that produced the perception."""

    TASK_SYSTEM = "task_system"
    PIPELINE_SYSTEM = "pipeline_system"
    OPERATOR_SESSION = "operator_session"
    LOCAL_NODE_STATUS = "local_node_status"
    VPS_NODE_STATUS = "vps_node_status"
    DISCORD_PENDING = "discord_pending"
    RUNTIME_LOGS = "runtime_logs"
    GIT_STATUS = "git_status"
    STATION_PRESENCE = "station_presence"
    LOCAL_CONTROL = "local_control"
    LIVE_SESSION = "live_session"


class PerceptionSeverity(str, Enum):
    """How urgent / important the perception is."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ─── Dataclass ────────────────────────────────────────────────────────────────


@dataclass
class PerceptionRecord:
    """A single structured observation from any perception collector."""

    record_id: str
    source: PerceptionSource
    observed_at: str
    summary: str
    severity: PerceptionSeverity
    payload: dict[str, Any]
    suggested_action: Optional[str]
    fingerprint: str

    # — factory ──────────────────────────────────────────────────────────────

    @classmethod
    def new(
        cls,
        source: PerceptionSource,
        summary: str,
        severity: PerceptionSeverity,
        *,
        payload: dict[str, Any] | None = None,
        suggested_action: str | None = None,
    ) -> "PerceptionRecord":
        """Create a new PerceptionRecord with generated ID and fingerprint."""
        return cls(
            record_id=_new_id(),
            source=source,
            observed_at=_utcnow(),
            summary=summary,
            severity=severity,
            payload=payload or {},
            suggested_action=suggested_action,
            fingerprint=_make_fingerprint(source.value, summary),
        )

    # — serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Return a JSON-safe dict. Enums serialized as their .value."""
        return {
            "record_id": self.record_id,
            "source": self.source.value,
            "observed_at": self.observed_at,
            "summary": self.summary,
            "severity": self.severity.value,
            "payload": dict(self.payload),
            "suggested_action": self.suggested_action,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PerceptionRecord":
        """Deserialize from a dict, reconstructing enums with safe defaults."""
        try:
            source = PerceptionSource(d.get("source", "task_system"))
        except ValueError:
            source = PerceptionSource.TASK_SYSTEM

        try:
            severity = PerceptionSeverity(d.get("severity", "info"))
        except ValueError:
            severity = PerceptionSeverity.INFO

        raw_payload = d.get("payload")
        payload: dict[str, Any] = (
            dict(raw_payload) if isinstance(raw_payload, dict) else {}
        )

        return cls(
            record_id=str(d.get("record_id") or _new_id()),
            source=source,
            observed_at=str(d.get("observed_at") or _utcnow()),
            summary=str(d.get("summary", "")),
            severity=severity,
            payload=payload,
            suggested_action=d.get("suggested_action"),
            fingerprint=str(d.get("fingerprint") or ""),
        )


# ─── Store ────────────────────────────────────────────────────────────────────


class PerceptionStore:
    """Durable, thread-safe, singleton store for PerceptionRecord objects.

    Dual-layer: in-memory dict + substrate.storage (Neon-backed, JSON fallback).
    Best-effort persistence — flush failures log and the in-memory state
    remains correct.

    Keyed by record_id. Bounded — prunes oldest INFO records first when count
    exceeds _MAX_RECORDS.
    """

    def __init__(self, *, autoload: bool = True) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, PerceptionRecord] = {}
        self._loaded = False
        if autoload:
            self._load()

    # — persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            try:
                from eos_ai.substrate.storage import get_storage

                raw = get_storage().get(_STORAGE_KEY, default=None)
            except Exception as e:  # noqa: BLE001
                _log(f"load failed ({e}); starting empty")
                raw = None
            if isinstance(raw, dict):
                for key, val in raw.items():
                    if isinstance(val, dict):
                        try:
                            self._records[key] = PerceptionRecord.from_dict(val)
                        except Exception as e:  # noqa: BLE001
                            _log(f"skip bad record {key}: {e}")
            self._loaded = True

    def _flush(self) -> None:
        try:
            from eos_ai.substrate.storage import get_storage

            payload = {rid: r.to_dict() for rid, r in self._records.items()}
            get_storage().put(_STORAGE_KEY, payload)
        except Exception as e:  # noqa: BLE001
            _log(f"flush failed: {e}")

    def _prune_if_needed(self) -> None:
        """Remove oldest INFO records first if store exceeds _MAX_RECORDS."""
        if len(self._records) <= _MAX_RECORDS:
            return
        # Sort INFO records by observed_at ascending (oldest first)
        info_records = [
            r for r in self._records.values() if r.severity == PerceptionSeverity.INFO
        ]
        info_records.sort(key=lambda r: r.observed_at)
        to_remove = len(self._records) - _MAX_RECORDS
        removed = 0
        for record in info_records:
            if removed >= to_remove:
                break
            del self._records[record.record_id]
            removed += 1
        # If still over limit after removing all INFO, prune oldest WARNING
        if len(self._records) > _MAX_RECORDS:
            warning_records = [
                r
                for r in self._records.values()
                if r.severity == PerceptionSeverity.WARNING
            ]
            warning_records.sort(key=lambda r: r.observed_at)
            remaining = len(self._records) - _MAX_RECORDS
            for record in warning_records[:remaining]:
                del self._records[record.record_id]

    # — public api ───────────────────────────────────────────────────────────

    def get(self, record_id: str) -> Optional[PerceptionRecord]:
        """Return a record by ID, or None."""
        with self._lock:
            return self._records.get(record_id)

    def put(self, record: PerceptionRecord) -> None:
        """Insert or update a record. Flushes to storage."""
        with self._lock:
            self._records[record.record_id] = record
            self._prune_if_needed()
            self._flush()

    def all(self) -> list[PerceptionRecord]:
        """Return all records, sorted by observed_at descending (newest first)."""
        with self._lock:
            return sorted(
                self._records.values(), key=lambda r: r.observed_at, reverse=True
            )

    def by_source(self, source: PerceptionSource) -> list[PerceptionRecord]:
        """Return records from the given source, sorted by observed_at descending."""
        with self._lock:
            return sorted(
                [r for r in self._records.values() if r.source == source],
                key=lambda r: r.observed_at,
                reverse=True,
            )

    def by_severity(self, severity: PerceptionSeverity) -> list[PerceptionRecord]:
        """Return records with the given severity, sorted by observed_at descending."""
        with self._lock:
            return sorted(
                [r for r in self._records.values() if r.severity == severity],
                key=lambda r: r.observed_at,
                reverse=True,
            )

    def recent(self, limit: int = 50) -> list[PerceptionRecord]:
        """Return the most recent N records, sorted by observed_at descending."""
        with self._lock:
            all_sorted = sorted(
                self._records.values(), key=lambda r: r.observed_at, reverse=True
            )
            return all_sorted[:limit]

    def has_fingerprint(self, fingerprint: str) -> bool:
        """Check if a record with this fingerprint already exists (for dedup)."""
        with self._lock:
            return any(r.fingerprint == fingerprint for r in self._records.values())

    # — singleton ────────────────────────────────────────────────────────────

    _default: Optional["PerceptionStore"] = None
    _default_lock = threading.Lock()

    @classmethod
    def default(cls) -> "PerceptionStore":
        """Return the process-level singleton, creating it on first call."""
        if cls._default is None:
            with cls._default_lock:
                if cls._default is None:
                    cls._default = cls()
        return cls._default

    @classmethod
    def reset_default_for_tests(cls) -> None:
        """Tear down the singleton so the next call to default() creates a fresh instance."""
        with cls._default_lock:
            cls._default = None


# ─── Collectors ───────────────────────────────────────────────────────────────


def collect_task_perception() -> list[PerceptionRecord]:
    """Inspect task system for actionable state.

    Detects:
    - Tasks stuck in WAITING_ON_OPERATOR for > 4 hours
    - Failed tasks (COMPLETED with execution_error)
    - OVERNIGHT_QUEUED tasks exceeding 10
    """
    records: list[PerceptionRecord] = []
    try:
        from eos_ai.substrate.task_system import TaskStore, TaskStatus

        store = TaskStore.default()
        now = _now()

        # Waiting on operator for too long
        waiting = store.by_status(TaskStatus.WAITING_ON_OPERATOR)
        for task in waiting:
            try:
                updated = datetime.fromisoformat(task.updated_at)
                if (now - updated) > timedelta(hours=4):
                    records.append(
                        PerceptionRecord.new(
                            source=PerceptionSource.TASK_SYSTEM,
                            summary=f"Task blocked >4h: {task.title}",
                            severity=PerceptionSeverity.WARNING,
                            payload={
                                "task_id": task.task_id,
                                "hours_blocked": round(
                                    (now - updated).total_seconds() / 3600, 1
                                ),
                            },
                            suggested_action="Review blocked tasks",
                        )
                    )
            except Exception:  # noqa: BLE001
                pass

        # Completed tasks with execution errors
        completed = store.by_status(TaskStatus.COMPLETED)
        for task in completed:
            if task.execution_error:
                records.append(
                    PerceptionRecord.new(
                        source=PerceptionSource.TASK_SYSTEM,
                        summary=f"Completed task had error: {task.title}",
                        severity=PerceptionSeverity.INFO,
                        payload={
                            "task_id": task.task_id,
                            "error": task.execution_error,
                        },
                    )
                )

        # Overnight queue size
        overnight = store.by_status(TaskStatus.OVERNIGHT_QUEUED)
        if len(overnight) > 10:
            records.append(
                PerceptionRecord.new(
                    source=PerceptionSource.TASK_SYSTEM,
                    summary=f"Overnight queue has {len(overnight)} tasks",
                    severity=PerceptionSeverity.WARNING,
                    payload={"count": len(overnight)},
                    suggested_action="Review overnight queue size",
                )
            )
    except Exception as e:  # noqa: BLE001
        _log(f"collect_task_perception failed: {e}")
    return records


def collect_pipeline_perception() -> list[PerceptionRecord]:
    """Inspect pipeline system for blocked/failed state.

    Detects:
    - Pipelines in FAILED status
    - Pipelines in WAITING_ON_OPERATOR status
    - Stalled pipelines (IN_PROGRESS for > 2 hours with no step progress)
    """
    records: list[PerceptionRecord] = []
    try:
        from eos_ai.substrate.task_pipeline import PipelineStore, PipelineStatus

        store = PipelineStore.default()
        now = _now()

        for pipeline in store.all():
            if pipeline.status == PipelineStatus.FAILED:
                records.append(
                    PerceptionRecord.new(
                        source=PerceptionSource.PIPELINE_SYSTEM,
                        summary=f"Pipeline failed: {pipeline.title}",
                        severity=PerceptionSeverity.CRITICAL,
                        payload={
                            "pipeline_id": pipeline.pipeline_id,
                            "task_id": pipeline.task_id,
                        },
                        suggested_action=f"Review failed pipeline: {pipeline.title}",
                    )
                )
            elif pipeline.status == PipelineStatus.WAITING_ON_OPERATOR:
                records.append(
                    PerceptionRecord.new(
                        source=PerceptionSource.PIPELINE_SYSTEM,
                        summary=f"Pipeline waiting on operator: {pipeline.title}",
                        severity=PerceptionSeverity.WARNING,
                        payload={
                            "pipeline_id": pipeline.pipeline_id,
                            "task_id": pipeline.task_id,
                        },
                    )
                )
            elif pipeline.status == PipelineStatus.IN_PROGRESS:
                try:
                    updated = datetime.fromisoformat(pipeline.updated_at)
                    if (now - updated) > timedelta(hours=2):
                        records.append(
                            PerceptionRecord.new(
                                source=PerceptionSource.PIPELINE_SYSTEM,
                                summary=f"Pipeline stalled >2h: {pipeline.title}",
                                severity=PerceptionSeverity.WARNING,
                                payload={
                                    "pipeline_id": pipeline.pipeline_id,
                                    "hours_stalled": round(
                                        (now - updated).total_seconds() / 3600, 1
                                    ),
                                },
                                suggested_action=f"Check stalled pipeline: {pipeline.title}",
                            )
                        )
                except Exception:  # noqa: BLE001
                    pass
    except Exception as e:  # noqa: BLE001
        _log(f"collect_pipeline_perception failed: {e}")
    return records


def collect_operator_session_perception() -> list[PerceptionRecord]:
    """Inspect operator session state.

    Detects:
    - OVERNIGHT mode active for > 12 hours
    - Day open for > 16 hours
    - Session has unfinished_priorities with no active tasks
    """
    records: list[PerceptionRecord] = []
    try:
        from eos_ai.substrate.operator_session import (
            OperatorSessionStore,
            OperatorDayMode,
        )

        store = OperatorSessionStore.default()
        session = store.get()
        if session is None:
            return records

        now = _now()

        # Overnight mode for too long
        if session.day_mode == OperatorDayMode.OVERNIGHT and session.closed_at:
            try:
                closed = datetime.fromisoformat(session.closed_at)
                if (now - closed) > timedelta(hours=12):
                    records.append(
                        PerceptionRecord.new(
                            source=PerceptionSource.OPERATOR_SESSION,
                            summary=f"Overnight mode active for {round((now - closed).total_seconds() / 3600, 1)}h",
                            severity=PerceptionSeverity.WARNING,
                            payload={
                                "day_session_id": session.day_session_id,
                                "closed_at": session.closed_at,
                            },
                            suggested_action="Consider opening a new day",
                        )
                    )
            except Exception:  # noqa: BLE001
                pass

        # Day open for too long
        if session.is_day_open and session.opened_at:
            try:
                opened = datetime.fromisoformat(session.opened_at)
                if (now - opened) > timedelta(hours=16):
                    records.append(
                        PerceptionRecord.new(
                            source=PerceptionSource.OPERATOR_SESSION,
                            summary=f"Day open for {round((now - opened).total_seconds() / 3600, 1)}h",
                            severity=PerceptionSeverity.WARNING,
                            payload={
                                "day_session_id": session.day_session_id,
                                "opened_at": session.opened_at,
                            },
                            suggested_action="Consider closing the day",
                        )
                    )
            except Exception:  # noqa: BLE001
                pass

        # Unfinished priorities with no active tasks
        if session.unfinished_priorities and session.is_day_open:
            try:
                from eos_ai.substrate.task_system import TaskStore, TaskStatus

                task_store = TaskStore.default()
                in_progress = task_store.by_status(TaskStatus.IN_PROGRESS)
                if not in_progress:
                    records.append(
                        PerceptionRecord.new(
                            source=PerceptionSource.OPERATOR_SESSION,
                            summary=f"{len(session.unfinished_priorities)} unfinished priorities with no active tasks",
                            severity=PerceptionSeverity.INFO,
                            payload={
                                "priorities": list(session.unfinished_priorities),
                                "day_session_id": session.day_session_id,
                            },
                            suggested_action="Start working on unfinished priorities",
                        )
                    )
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        _log(f"collect_operator_session_perception failed: {e}")
    return records


def collect_node_status_perception() -> list[PerceptionRecord]:
    """Inspect node registry for availability issues.

    Detects:
    - Nodes with status OFFLINE or DEGRADED
    - Local station node not seen in > 1 hour
    """
    records: list[PerceptionRecord] = []
    try:
        from eos_ai.substrate.nodes import NodeRegistry, NodeStatus, NodeType

        registry = NodeRegistry.default()
        now = _now()

        for node in registry.all():
            if node.status == NodeStatus.OFFLINE:
                records.append(
                    PerceptionRecord.new(
                        source=PerceptionSource.VPS_NODE_STATUS
                        if node.node_type == NodeType.VPS
                        else PerceptionSource.LOCAL_NODE_STATUS,
                        summary=f"Node offline: {node.node_id}",
                        severity=PerceptionSeverity.CRITICAL,
                        payload={
                            "node_id": node.node_id,
                            "node_type": node.node_type.value,
                        },
                        suggested_action=f"Investigate offline node: {node.node_id}",
                    )
                )
            elif node.status == NodeStatus.DEGRADED:
                records.append(
                    PerceptionRecord.new(
                        source=PerceptionSource.VPS_NODE_STATUS
                        if node.node_type == NodeType.VPS
                        else PerceptionSource.LOCAL_NODE_STATUS,
                        summary=f"Node degraded: {node.node_id}",
                        severity=PerceptionSeverity.WARNING,
                        payload={
                            "node_id": node.node_id,
                            "node_type": node.node_type.value,
                        },
                    )
                )

            # Local station not seen recently
            if node.node_type == NodeType.LOCAL_STATION and node.last_seen:
                try:
                    last_seen = datetime.fromisoformat(node.last_seen)
                    if (now - last_seen) > timedelta(hours=1):
                        records.append(
                            PerceptionRecord.new(
                                source=PerceptionSource.LOCAL_NODE_STATUS,
                                summary=f"Local station not seen in {round((now - last_seen).total_seconds() / 3600, 1)}h",
                                severity=PerceptionSeverity.WARNING,
                                payload={
                                    "node_id": node.node_id,
                                    "last_seen": node.last_seen,
                                },
                            )
                        )
                except Exception:  # noqa: BLE001
                    pass
    except Exception as e:  # noqa: BLE001
        _log(f"collect_node_status_perception failed: {e}")
    return records


def collect_git_perception() -> list[PerceptionRecord]:
    """Inspect git state (bounded, safe read-only).

    Detects:
    - Uncommitted changes count > 20 files
    - Unpushed commits
    """
    records: list[PerceptionRecord] = []
    try:
        # Uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/opt/OS",
        )
        if result.returncode == 0:
            lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
            if len(lines) > 20:
                records.append(
                    PerceptionRecord.new(
                        source=PerceptionSource.GIT_STATUS,
                        summary=f"Uncommitted changes: {len(lines)} files",
                        severity=PerceptionSeverity.WARNING,
                        payload={"file_count": len(lines)},
                        suggested_action="Review and commit pending changes",
                    )
                )

        # Unpushed commits
        result = subprocess.run(
            ["git", "log", "@{u}..HEAD", "--oneline"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/opt/OS",
        )
        if result.returncode == 0:
            commit_lines = [
                ln for ln in result.stdout.strip().splitlines() if ln.strip()
            ]
            if commit_lines:
                records.append(
                    PerceptionRecord.new(
                        source=PerceptionSource.GIT_STATUS,
                        summary=f"Unpushed commits: {len(commit_lines)}",
                        severity=PerceptionSeverity.INFO,
                        payload={
                            "commit_count": len(commit_lines),
                            "commits": commit_lines[:10],
                        },
                        suggested_action="Push commits to remote",
                    )
                )
    except Exception as e:  # noqa: BLE001
        _log(f"collect_git_perception failed: {e}")
    return records


def collect_runtime_log_perception() -> list[PerceptionRecord]:
    """Inspect recent runtime logs for errors (bounded).

    Reads last 100 lines of the most recent .log file in /opt/OS/logs/.
    Looks for ERROR/CRITICAL patterns.
    """
    records: list[PerceptionRecord] = []
    try:
        import os
        from pathlib import Path

        logs_dir = Path("/opt/OS/logs")
        if not logs_dir.is_dir():
            return records

        # Find most recent .log file
        log_files = sorted(
            logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not log_files:
            return records

        latest = log_files[0]
        try:
            with open(latest) as f:
                all_lines = f.readlines()
        except Exception:  # noqa: BLE001
            return records

        tail = all_lines[-100:] if len(all_lines) > 100 else all_lines

        error_lines: list[str] = []
        critical_lines: list[str] = []
        for line in tail:
            stripped = line.strip()
            if not stripped:
                continue
            upper = stripped.upper()
            if "CRITICAL" in upper:
                critical_lines.append(stripped)
            elif "ERROR" in upper:
                error_lines.append(stripped)

        if critical_lines:
            records.append(
                PerceptionRecord.new(
                    source=PerceptionSource.RUNTIME_LOGS,
                    summary=f"CRITICAL in logs ({latest.name}): {len(critical_lines)} lines",
                    severity=PerceptionSeverity.CRITICAL,
                    payload={"file": str(latest), "sample": critical_lines[:5]},
                    suggested_action="Review critical log entries",
                )
            )

        if error_lines:
            records.append(
                PerceptionRecord.new(
                    source=PerceptionSource.RUNTIME_LOGS,
                    summary=f"Errors in logs ({latest.name}): {len(error_lines)} lines",
                    severity=PerceptionSeverity.WARNING,
                    payload={"file": str(latest), "sample": error_lines[:5]},
                    suggested_action="Review error log entries",
                )
            )
    except Exception as e:  # noqa: BLE001
        _log(f"collect_runtime_log_perception failed: {e}")
    return records


# ─── Station / Local Control / Live Session Collectors ────────────────────────


def collect_station_presence_perception() -> list[PerceptionRecord]:
    """Inspect station presence for workstation-level issues.

    Detects:
    - Station mode AWAY while blocked operator tasks exist
    - Local node restored (available changed to True with recent trigger)
    - Overnight mode persisting with unresolved items
    """
    records: list[PerceptionRecord] = []
    try:
        from eos_ai.substrate.station_presence import get_station_presence, StationPresenceMode

        state = get_station_presence()

        # Station AWAY while blocked work exists
        if state.mode == StationPresenceMode.AWAY:
            try:
                from eos_ai.substrate.task_system import TaskStore, TaskStatus

                blocked = TaskStore.default().by_status(TaskStatus.WAITING_ON_OPERATOR)
                if blocked:
                    records.append(
                        PerceptionRecord.new(
                            source=PerceptionSource.STATION_PRESENCE,
                            summary=f"Station AWAY with {len(blocked)} tasks waiting on operator",
                            severity=PerceptionSeverity.WARNING,
                            payload={
                                "presence_mode": state.mode.value,
                                "blocked_count": len(blocked),
                            },
                            suggested_action="Review blocked tasks or update station presence",
                        )
                    )
            except Exception:  # noqa: BLE001
                pass

        # Overnight mode with unfinished priorities
        if state.mode == StationPresenceMode.OVERNIGHT:
            try:
                from eos_ai.substrate.operator_session import OperatorSessionStore

                session = OperatorSessionStore.default().get()
                if session and session.unfinished_priorities:
                    records.append(
                        PerceptionRecord.new(
                            source=PerceptionSource.STATION_PRESENCE,
                            summary=f"Overnight mode with {len(session.unfinished_priorities)} unfinished priorities",
                            severity=PerceptionSeverity.INFO,
                            payload={
                                "priorities": list(session.unfinished_priorities)[:5],
                            },
                            suggested_action="Consider opening a new day to address priorities",
                        )
                    )
            except Exception:  # noqa: BLE001
                pass

    except Exception as e:  # noqa: BLE001
        _log(f"collect_station_presence_perception failed: {e}")
    return records


def collect_local_control_perception() -> list[PerceptionRecord]:
    """Inspect local control for blocked/failed requests.

    Detects:
    - Requests blocked by current control mode
    - Failed requests in the last 24 hours
    """
    records: list[PerceptionRecord] = []
    try:
        from eos_ai.substrate.local_control import (
            LocalControlStore,
            RequestStatus,
        )
        from datetime import timedelta

        store = LocalControlStore.default()
        all_reqs = store.all()
        now = _now()
        cutoff = (now - timedelta(hours=24)).isoformat()

        blocked_recent = [
            r for r in all_reqs
            if r.status == RequestStatus.BLOCKED and r.created_at >= cutoff
        ]
        failed_recent = [
            r for r in all_reqs
            if r.status == RequestStatus.FAILED and r.created_at >= cutoff
        ]

        if blocked_recent:
            records.append(
                PerceptionRecord.new(
                    source=PerceptionSource.LOCAL_CONTROL,
                    summary=f"{len(blocked_recent)} control requests blocked by mode in last 24h",
                    severity=PerceptionSeverity.WARNING,
                    payload={
                        "blocked_count": len(blocked_recent),
                        "control_mode": store.get_mode().value,
                    },
                    suggested_action="Review blocked control requests or adjust control mode",
                )
            )

        if failed_recent:
            records.append(
                PerceptionRecord.new(
                    source=PerceptionSource.LOCAL_CONTROL,
                    summary=f"{len(failed_recent)} control requests failed in last 24h",
                    severity=PerceptionSeverity.INFO,
                    payload={"failed_count": len(failed_recent)},
                )
            )

    except Exception as e:  # noqa: BLE001
        _log(f"collect_local_control_perception failed: {e}")
    return records


def collect_live_session_perception() -> list[PerceptionRecord]:
    """Inspect live sessions for issues.

    Detects:
    - Live sessions paused for > 1 hour
    - Live sessions in WAITING_ON_OPERATOR state
    - Failed live sessions in last 24h
    """
    records: list[PerceptionRecord] = []
    try:
        from eos_ai.substrate.live_sessions import (
            LiveSessionStore,
            LiveSessionState,
        )
        from datetime import timedelta

        store = LiveSessionStore.default()
        all_sessions = store.all()
        now = _now()

        for s in all_sessions:
            if s.state == LiveSessionState.PAUSED:
                try:
                    updated = datetime.fromisoformat(s.updated_at)
                    if (now - updated) > timedelta(hours=1):
                        records.append(
                            PerceptionRecord.new(
                                source=PerceptionSource.LIVE_SESSION,
                                summary=f"Live session paused >1h: {s.title}",
                                severity=PerceptionSeverity.WARNING,
                                payload={
                                    "live_session_id": s.live_session_id,
                                    "hours_paused": round(
                                        (now - updated).total_seconds() / 3600, 1
                                    ),
                                },
                                suggested_action=f"Resume or end paused session: {s.title}",
                            )
                        )
                except Exception:  # noqa: BLE001
                    pass

            elif s.state == LiveSessionState.WAITING_ON_OPERATOR:
                records.append(
                    PerceptionRecord.new(
                        source=PerceptionSource.LIVE_SESSION,
                        summary=f"Live session waiting on operator: {s.title}",
                        severity=PerceptionSeverity.WARNING,
                        payload={
                            "live_session_id": s.live_session_id,
                            "attached_pipelines": list(s.attached_pipeline_ids),
                        },
                        suggested_action=f"Attend to live session: {s.title}",
                    )
                )

            elif s.state == LiveSessionState.FAILED:
                cutoff = (now - timedelta(hours=24)).isoformat()
                if s.updated_at >= cutoff:
                    records.append(
                        PerceptionRecord.new(
                            source=PerceptionSource.LIVE_SESSION,
                            summary=f"Live session failed: {s.title}",
                            severity=PerceptionSeverity.INFO,
                            payload={
                                "live_session_id": s.live_session_id,
                                "last_event": s.last_event,
                            },
                        )
                    )

    except Exception as e:  # noqa: BLE001
        _log(f"collect_live_session_perception failed: {e}")
    return records


# ─── Master Collector ─────────────────────────────────────────────────────────


def collect_all_perceptions() -> list[PerceptionRecord]:
    """Run all collectors and return combined results.

    Never raises — each collector is called independently and failures
    are logged but do not prevent other collectors from running.
    """
    all_records: list[PerceptionRecord] = []
    collectors = [
        collect_task_perception,
        collect_pipeline_perception,
        collect_operator_session_perception,
        collect_node_status_perception,
        collect_git_perception,
        collect_runtime_log_perception,
        collect_station_presence_perception,
        collect_local_control_perception,
        collect_live_session_perception,
    ]
    for collector in collectors:
        try:
            all_records.extend(collector())
        except Exception as e:  # noqa: BLE001
            _log(f"collector {collector.__name__} raised unexpectedly: {e}")
    return all_records


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "PerceptionSource",
    "PerceptionSeverity",
    "PerceptionRecord",
    "PerceptionStore",
    "collect_task_perception",
    "collect_pipeline_perception",
    "collect_operator_session_perception",
    "collect_node_status_perception",
    "collect_git_perception",
    "collect_runtime_log_perception",
    "collect_station_presence_perception",
    "collect_local_control_perception",
    "collect_live_session_perception",
    "collect_all_perceptions",
]
