"""PlanningStore — JSONL persistence for objective-planning records.

Same persistence mechanism as the canonical IntentLoopStore (append-only JSONL
+ tempfile/os.replace atomic rewrite) hardened with:

- an INTERPROCESS ``fcntl`` lock per file (multiple uvicorn workers / the
  degraded CLI path may write concurrently), and
- compare-and-swap plan versioning: status flips and revisions carry
  ``expected_current_version``; a mismatch raises ``PlanningStoreConflict``
  instead of overwriting.

All paths resolve through the runtime-state boundary
(``<runtime-state>/operator/objective_planning/``). Module-level ``_DEFAULT_*``
constants are the established monkeypatch seam for test isolation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from substrate.execution.planning.records import (
    CurrentStateRecord,
    DesiredStateRecord,
    GapAssessmentSnapshot,
    GroundingSnapshot,
    ObjectivePlanRecord,
    ObjectivePlanStatus,
    PlanningSession,
)

try:  # fcntl is POSIX-only; the store degrades to thread-locking elsewhere.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_SUBSYSTEM = "operator/objective_planning"


def _resolve(filename: str) -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path(_SUBSYSTEM, filename, create_parent=False))


# Test-isolation seam: suites monkeypatch these module attributes to tmp paths.
_DEFAULT_SESSIONS_PATH = _resolve("planning_sessions.jsonl")
_DEFAULT_PLANS_PATH = _resolve("objective_plans.jsonl")
_DEFAULT_GROUNDING_PATH = _resolve("grounding_snapshots.jsonl")
_DEFAULT_CURRENT_PATH = _resolve("current_states.jsonl")
_DEFAULT_DESIRED_PATH = _resolve("desired_states.jsonl")
_DEFAULT_GAPS_PATH = _resolve("gap_models.jsonl")


class PlanningStoreConflict(RuntimeError):
    """Raised when a compare-and-swap write loses to a concurrent writer."""


def message_fingerprint(text: str) -> str:
    normalized = " ".join((text or "").lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


class PlanningStore:
    """File-backed store for every objective-planning record type."""

    _thread_lock = threading.Lock()

    def __init__(
        self,
        sessions_path: str | None = None,
        plans_path: str | None = None,
        grounding_path: str | None = None,
        current_path: str | None = None,
        desired_path: str | None = None,
        gaps_path: str | None = None,
    ) -> None:
        self._sessions_path = sessions_path or _DEFAULT_SESSIONS_PATH
        self._plans_path = plans_path or _DEFAULT_PLANS_PATH
        self._grounding_path = grounding_path or _DEFAULT_GROUNDING_PATH
        self._current_path = current_path or _DEFAULT_CURRENT_PATH
        self._desired_path = desired_path or _DEFAULT_DESIRED_PATH
        self._gaps_path = gaps_path or _DEFAULT_GAPS_PATH
        for p in (
            self._sessions_path,
            self._plans_path,
            self._grounding_path,
            self._current_path,
            self._desired_path,
            self._gaps_path,
        ):
            os.makedirs(os.path.dirname(p), exist_ok=True)

    # ── Locking ──────────────────────────────────────────────────────────────

    @contextmanager
    def _file_lock(self, path: str) -> Iterator[None]:
        """Interprocess exclusive lock scoped to one store file."""
        with self._thread_lock:
            lock_path = path + ".lock"
            fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                try:
                    if fcntl is not None:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                finally:
                    os.close(fd)

    # ── Generic JSONL helpers ────────────────────────────────────────────────

    @staticmethod
    def _append_line(path: str, payload: dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str, separators=(",", ":")) + "\n")

    @staticmethod
    def _read_lines(path: str) -> list[dict[str, Any]]:
        if not os.path.exists(path):
            return []
        rows: list[dict[str, Any]] = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    logger.debug("skipping malformed planning line in %s: %s", path, exc)
        return rows

    @staticmethod
    def _rewrite_atomic(path: str, rows: list[dict[str, Any]]) -> None:
        dir_name = os.path.dirname(path)
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, default=str, separators=(",", ":")) + "\n")
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    # ── Append-only evidence records ─────────────────────────────────────────

    def append_grounding(self, snapshot: GroundingSnapshot) -> None:
        with self._file_lock(self._grounding_path):
            self._append_line(self._grounding_path, snapshot.to_dict())

    def append_current_state(self, record: CurrentStateRecord) -> None:
        with self._file_lock(self._current_path):
            self._append_line(self._current_path, record.to_dict())

    def append_desired_state(self, record: DesiredStateRecord) -> None:
        with self._file_lock(self._desired_path):
            self._append_line(self._desired_path, record.to_dict())

    def append_gap_model(self, record: GapAssessmentSnapshot) -> None:
        with self._file_lock(self._gaps_path):
            self._append_line(self._gaps_path, record.to_dict())

    def get_grounding(self, grounding_snapshot_id: str) -> GroundingSnapshot | None:
        for row in self._read_lines(self._grounding_path):
            if row.get("grounding_snapshot_id") == grounding_snapshot_id:
                return GroundingSnapshot.from_dict(row)
        return None

    def get_current_state(self, current_state_id: str) -> CurrentStateRecord | None:
        for row in self._read_lines(self._current_path):
            if row.get("current_state_id") == current_state_id:
                return CurrentStateRecord.from_dict(row)
        return None

    def get_desired_state(self, desired_state_id: str) -> DesiredStateRecord | None:
        for row in self._read_lines(self._desired_path):
            if row.get("desired_state_id") == desired_state_id:
                return DesiredStateRecord.from_dict(row)
        return None

    def get_gap_model(self, gap_model_id: str) -> GapAssessmentSnapshot | None:
        for row in self._read_lines(self._gaps_path):
            if row.get("gap_model_id") == gap_model_id:
                return GapAssessmentSnapshot.from_dict(row)
        return None

    # ── Sessions ─────────────────────────────────────────────────────────────

    def append_session(self, session: PlanningSession) -> None:
        with self._file_lock(self._sessions_path):
            self._append_line(self._sessions_path, session.to_dict())

    def update_session(self, session: PlanningSession) -> None:
        with self._file_lock(self._sessions_path):
            rows = self._read_lines(self._sessions_path)
            found = False
            for i, row in enumerate(rows):
                if row.get("session_id") == session.session_id:
                    rows[i] = session.to_dict()
                    found = True
                    break
            if not found:
                rows.append(session.to_dict())
            self._rewrite_atomic(self._sessions_path, rows)

    def load_sessions(self) -> list[PlanningSession]:
        return [PlanningSession.from_dict(r) for r in self._read_lines(self._sessions_path)]

    def get_session(self, session_id: str) -> PlanningSession | None:
        for s in self.load_sessions():
            if s.session_id == session_id:
                return s
        return None

    def find_active_session(self, conversation_id: str) -> PlanningSession | None:
        """Latest non-closed session for a conversation."""
        if not conversation_id:
            return None
        candidates = [
            s
            for s in self.load_sessions()
            if s.conversation_id == conversation_id and s.stage != "closed"
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.created_at)

    def find_session_by_idempotency(
        self,
        conversation_id: str,
        client_message_id: str,
        fingerprint: str,
    ) -> PlanningSession | None:
        """Primary key (conversation_id, client_message_id); fingerprint fallback."""
        sessions = [s for s in self.load_sessions() if s.conversation_id == conversation_id]
        if client_message_id:
            for s in sessions:
                if s.client_message_id and s.client_message_id == client_message_id:
                    return s
        if fingerprint:
            for s in sessions:
                if s.message_fingerprint == fingerprint:
                    return s
        return None

    # ── Plan records (versioned, CAS-guarded) ────────────────────────────────

    def append_plan(self, plan: ObjectivePlanRecord) -> None:
        with self._file_lock(self._plans_path):
            self._append_line(self._plans_path, plan.to_dict())

    def load_plans(self) -> list[ObjectivePlanRecord]:
        return [ObjectivePlanRecord.from_dict(r) for r in self._read_lines(self._plans_path)]

    def get_plan(self, plan_record_id: str) -> ObjectivePlanRecord | None:
        for row in self._read_lines(self._plans_path):
            if row.get("plan_record_id") == plan_record_id:
                return ObjectivePlanRecord.from_dict(row)
        return None

    def versions_of(self, objective_id: str) -> list[ObjectivePlanRecord]:
        versions = [p for p in self.load_plans() if p.objective_id == objective_id]
        versions.sort(key=lambda p: p.graph_version)
        return versions

    def latest_version_of(self, objective_id: str) -> ObjectivePlanRecord | None:
        versions = self.versions_of(objective_id)
        return versions[-1] if versions else None

    def query_recent_plans(self, limit: int = 50) -> list[ObjectivePlanRecord]:
        plans = self.load_plans()
        plans.sort(key=lambda p: p.created_at, reverse=True)
        return plans[:limit]

    def update_plan_cas(
        self,
        plan: ObjectivePlanRecord,
        expected_current_version: int,
        expected_statuses: tuple[str, ...] | None = None,
    ) -> None:
        """Compare-and-swap update of one plan record (status/decision_log).

        Fails with :class:`PlanningStoreConflict` when the on-disk record's
        ``graph_version`` differs from ``expected_current_version``, when the
        on-disk status is outside ``expected_statuses``, or when the record
        vanished. Never blind-overwrites.
        """
        with self._file_lock(self._plans_path):
            rows = self._read_lines(self._plans_path)
            for i, row in enumerate(rows):
                if row.get("plan_record_id") != plan.plan_record_id:
                    continue
                on_disk_version = int(row.get("graph_version", -1))
                if on_disk_version != expected_current_version:
                    raise PlanningStoreConflict(
                        f"plan {plan.plan_record_id}: expected version "
                        f"{expected_current_version}, found {on_disk_version}"
                    )
                if expected_statuses is not None and row.get("status") not in expected_statuses:
                    raise PlanningStoreConflict(
                        f"plan {plan.plan_record_id}: status {row.get('status')!r} "
                        f"not in expected {list(expected_statuses)}"
                    )
                rows[i] = plan.to_dict()
                self._rewrite_atomic(self._plans_path, rows)
                return
            raise PlanningStoreConflict(f"plan {plan.plan_record_id} not found for CAS update")

    def append_revision_cas(
        self,
        new_plan: ObjectivePlanRecord,
        superseded: ObjectivePlanRecord,
        expected_current_version: int,
    ) -> None:
        """Atomically append v(n+1) and flip v(n) → SUPERSEDED under one lock.

        CAS: fails if the superseded record's on-disk version has moved or its
        status is terminal already (a concurrent revision/decision won).
        """
        revisable = (
            ObjectivePlanStatus.AWAITING_APPROVAL.value,
            ObjectivePlanStatus.APPROVED.value,
            ObjectivePlanStatus.DRAFT.value,
        )
        with self._file_lock(self._plans_path):
            rows = self._read_lines(self._plans_path)
            target_index: int | None = None
            for i, row in enumerate(rows):
                if row.get("plan_record_id") == superseded.plan_record_id:
                    on_disk_version = int(row.get("graph_version", -1))
                    if on_disk_version != expected_current_version:
                        raise PlanningStoreConflict(
                            f"plan {superseded.plan_record_id}: expected version "
                            f"{expected_current_version}, found {on_disk_version}"
                        )
                    if row.get("status") not in revisable:
                        raise PlanningStoreConflict(
                            f"plan {superseded.plan_record_id}: status "
                            f"{row.get('status')!r} is not revisable"
                        )
                    target_index = i
                    break
            if target_index is None:
                raise PlanningStoreConflict(
                    f"plan {superseded.plan_record_id} not found for revision"
                )
            superseded_row = dict(rows[target_index])
            superseded_row["status"] = ObjectivePlanStatus.SUPERSEDED.value
            superseded_row["updated_at"] = new_plan.created_at
            rows[target_index] = superseded_row
            rows.append(new_plan.to_dict())
            self._rewrite_atomic(self._plans_path, rows)


__all__ = [
    "PlanningStore",
    "PlanningStoreConflict",
    "message_fingerprint",
]
