"""ExecutionAttemptStore — JSONL persistence for the canonical execution slice.

Faithful mirror of ``substrate.execution.planning.store.PlanningStore``:
append-only JSONL + ``tempfile``/``os.replace`` atomic rewrite, hardened with an
interprocess ``fcntl`` lock per file and compare-and-swap versioning. All paths
resolve through the runtime-state boundary (``<runtime-state>/operator/
execution_attempts/``). Module-level ``_DEFAULT_*`` constants are the established
monkeypatch seam for test isolation.

This store is the SOLE current execution truth (Amendment v1 clause 3). The
dispatch spool is transport only; nothing infers execution state from files on
the spool.

The single write path for an attempt's lifecycle is :meth:`transition_cas`
(record-version + expected-status CAS, transition-table + guard validation,
append-only history, identity-field immutability). Grants use
:meth:`update_grant_cas`.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from substrate.execution.attempts.lifecycle import validate_transition
from substrate.execution.attempts.records import (
    ATTEMPT_IMMUTABLE_FIELDS,
    GRANT_IMMUTABLE_FIELDS,
    AttemptTransition,
    ExecutionAttempt,
    ExecutionAuthorizationGrant,
)

try:  # fcntl is POSIX-only; the store degrades to thread-locking elsewhere.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_SUBSYSTEM = "operator/execution_attempts"


def _resolve(filename: str) -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path(_SUBSYSTEM, filename, create_parent=False))


# Test-isolation seam: suites monkeypatch these module attributes to tmp paths.
_DEFAULT_ATTEMPTS_PATH = _resolve("execution_attempts.jsonl")
_DEFAULT_GRANTS_PATH = _resolve("execution_authorization_grants.jsonl")
_DEFAULT_READINESS_PATH = _resolve("readiness_assessments.jsonl")
_DEFAULT_LEASES_PATH = _resolve("environment_leases.jsonl")


class AttemptStoreConflict(RuntimeError):
    """Raised when a compare-and-swap write loses to a concurrent writer, or a
    lifecycle guard rejects the transition."""


class ExecutionAttemptStore:
    """File-backed store for execution attempts, grants, readiness, and leases."""

    _thread_lock = threading.Lock()

    def __init__(
        self,
        attempts_path: str | None = None,
        grants_path: str | None = None,
        readiness_path: str | None = None,
        leases_path: str | None = None,
    ) -> None:
        self._attempts_path = attempts_path or _DEFAULT_ATTEMPTS_PATH
        self._grants_path = grants_path or _DEFAULT_GRANTS_PATH
        self._readiness_path = readiness_path or _DEFAULT_READINESS_PATH
        self._leases_path = leases_path or _DEFAULT_LEASES_PATH
        for p in (
            self._attempts_path,
            self._grants_path,
            self._readiness_path,
            self._leases_path,
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
                    logger.debug("skipping malformed execution line in %s: %s", path, exc)
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

    # ── Attempts: reads ──────────────────────────────────────────────────────

    def get_attempt(self, attempt_id: str) -> ExecutionAttempt | None:
        for row in self._read_lines(self._attempts_path):
            if row.get("attempt_id") == attempt_id:
                return ExecutionAttempt.from_dict(row)
        return None

    def attempts_for_task(self, task_id: str) -> list[ExecutionAttempt]:
        rows = [r for r in self._read_lines(self._attempts_path) if r.get("task_id") == task_id]
        attempts = [ExecutionAttempt.from_dict(r) for r in rows]
        return sorted(attempts, key=lambda a: a.attempt_number)

    def attempts_for_plan(self, plan_record_id: str) -> list[ExecutionAttempt]:
        rows = [
            r
            for r in self._read_lines(self._attempts_path)
            if r.get("plan_record_id") == plan_record_id
        ]
        return [ExecutionAttempt.from_dict(r) for r in rows]

    def active_attempts(self) -> list[ExecutionAttempt]:
        out: list[ExecutionAttempt] = []
        for row in self._read_lines(self._attempts_path):
            attempt = ExecutionAttempt.from_dict(row)
            if not attempt.is_terminal():
                out.append(attempt)
        return out

    def has_active_attempt_for_task(self, task_id: str) -> bool:
        for row in self._read_lines(self._attempts_path):
            if row.get("task_id") != task_id:
                continue
            attempt = ExecutionAttempt.from_dict(row)
            if not attempt.is_terminal():
                return True
        return False

    # ── Attempts: writes ─────────────────────────────────────────────────────

    def create_attempt_idempotent(
        self, attempt: ExecutionAttempt
    ) -> tuple[ExecutionAttempt, bool]:
        """Create an attempt, or return the existing one for the same logical
        key. The idempotency key is
        ``(task_id, execution_authorization_ref, attempt_number)`` — a duplicate
        request (browser retry, queue reload, duplicate message) returns the
        EXISTING attempt and ``created=False``; it never mints a second one.
        """
        with self._file_lock(self._attempts_path):
            rows = self._read_lines(self._attempts_path)
            for row in rows:
                if (
                    row.get("task_id") == attempt.task_id
                    and row.get("execution_authorization_ref")
                    == attempt.execution_authorization_ref
                    and int(row.get("attempt_number", -1)) == attempt.attempt_number
                ):
                    return ExecutionAttempt.from_dict(row), False
            self._append_line(self._attempts_path, attempt.to_dict())
            return attempt, True

    def transition_cas(
        self,
        attempt_id: str,
        to_status: str,
        expected_record_version: int,
        expected_statuses: tuple[str, ...],
        actor: str,
        reason: str = "",
        updates: dict[str, Any] | None = None,
        event_id: str = "",
    ) -> ExecutionAttempt:
        """THE single lifecycle write path (CAS-protected).

        Under the attempts-file lock: reads the row; raises
        :class:`AttemptStoreConflict` on record-version mismatch, on an on-disk
        status outside ``expected_statuses``, or when the record vanished;
        validates ``(status → to_status)`` against the transition table and its
        guards; applies ``updates`` to binding fields only (identity fields are
        immutable — a write to one raises); appends an
        :class:`AttemptTransition`; bumps ``record_version``; atomically
        rewrites. Never blind-overwrites.
        """
        updates = dict(updates or {})
        illegal = ATTEMPT_IMMUTABLE_FIELDS & set(updates)
        if illegal:
            raise AttemptStoreConflict(
                f"attempt {attempt_id}: cannot mutate immutable identity fields {sorted(illegal)}"
            )

        with self._file_lock(self._attempts_path):
            rows = self._read_lines(self._attempts_path)
            for i, row in enumerate(rows):
                if row.get("attempt_id") != attempt_id:
                    continue
                on_disk_version = int(row.get("record_version", -1))
                if on_disk_version != expected_record_version:
                    raise AttemptStoreConflict(
                        f"attempt {attempt_id}: expected record_version "
                        f"{expected_record_version}, found {on_disk_version}"
                    )
                on_disk_status = row.get("status")
                if on_disk_status not in expected_statuses:
                    raise AttemptStoreConflict(
                        f"attempt {attempt_id}: status {on_disk_status!r} not in expected "
                        f"{list(expected_statuses)}"
                    )
                attempt = ExecutionAttempt.from_dict(row)
                # Validate the transition + guards against the on-disk state,
                # with the pending binding updates in view.
                validate_transition(attempt, to_status, actor, updates)
                # Apply binding updates.
                for key, value in updates.items():
                    setattr(attempt, key, value)
                # Append immutable history entry.
                transition = AttemptTransition(
                    from_status=on_disk_status,
                    to_status=to_status,
                    actor=actor,
                    reason=reason,
                    event_id=event_id,
                )
                attempt.transitions.append(transition.to_dict())
                attempt.status = to_status
                attempt.record_version = on_disk_version + 1
                import time as _time

                attempt.updated_at = _time.time()
                rows[i] = attempt.to_dict()
                self._rewrite_atomic(self._attempts_path, rows)
                return attempt
            raise AttemptStoreConflict(f"attempt {attempt_id} not found for CAS transition")

    # ── Grants ───────────────────────────────────────────────────────────────

    def get_grant(self, decision_ref: str) -> ExecutionAuthorizationGrant | None:
        for row in self._read_lines(self._grants_path):
            if row.get("decision_ref") == decision_ref:
                return ExecutionAuthorizationGrant.from_dict(row)
        return None

    def get_grant_by_id(self, grant_id: str) -> ExecutionAuthorizationGrant | None:
        for row in self._read_lines(self._grants_path):
            if row.get("grant_id") == grant_id:
                return ExecutionAuthorizationGrant.from_dict(row)
        return None

    def grants_for_plan(self, plan_record_id: str) -> list[ExecutionAuthorizationGrant]:
        rows = [
            r for r in self._read_lines(self._grants_path) if r.get("plan_record_id") == plan_record_id
        ]
        return [ExecutionAuthorizationGrant.from_dict(r) for r in rows]

    def active_grants(self) -> list[ExecutionAuthorizationGrant]:
        out: list[ExecutionAuthorizationGrant] = []
        for row in self._read_lines(self._grants_path):
            grant = ExecutionAuthorizationGrant.from_dict(row)
            if grant.is_active():
                out.append(grant)
        return out

    def create_grant_idempotent(
        self, grant: ExecutionAuthorizationGrant
    ) -> tuple[ExecutionAuthorizationGrant, bool]:
        """Create or reuse the one grant for a ``decision_ref`` (Amendment v1
        clause 2: activation reuses one grant). Returns ``(grant, created)``."""
        with self._file_lock(self._grants_path):
            rows = self._read_lines(self._grants_path)
            for row in rows:
                if row.get("decision_ref") == grant.decision_ref:
                    return ExecutionAuthorizationGrant.from_dict(row), False
            self._append_line(self._grants_path, grant.to_dict())
            return grant, True

    def update_grant_cas(
        self,
        grant: ExecutionAuthorizationGrant,
        expected_record_version: int,
        expected_statuses: tuple[str, ...] | None = None,
    ) -> ExecutionAuthorizationGrant:
        """CAS update of one grant record (status/bounds progression/decision
        log). Fails with :class:`AttemptStoreConflict` on version mismatch,
        status outside ``expected_statuses``, immutable-field mutation, or a
        vanished record."""
        with self._file_lock(self._grants_path):
            rows = self._read_lines(self._grants_path)
            for i, row in enumerate(rows):
                if row.get("grant_id") != grant.grant_id:
                    continue
                on_disk_version = int(row.get("record_version", -1))
                if on_disk_version != expected_record_version:
                    raise AttemptStoreConflict(
                        f"grant {grant.grant_id}: expected record_version "
                        f"{expected_record_version}, found {on_disk_version}"
                    )
                if expected_statuses is not None and row.get("status") not in expected_statuses:
                    raise AttemptStoreConflict(
                        f"grant {grant.grant_id}: status {row.get('status')!r} not in expected "
                        f"{list(expected_statuses)}"
                    )
                for fld in GRANT_IMMUTABLE_FIELDS:
                    if getattr(grant, fld) != row.get(fld):
                        raise AttemptStoreConflict(
                            f"grant {grant.grant_id}: immutable field {fld!r} may not change"
                        )
                import time as _time

                grant.record_version = on_disk_version + 1
                grant.updated_at = _time.time()
                rows[i] = grant.to_dict()
                self._rewrite_atomic(self._grants_path, rows)
                return grant
            raise AttemptStoreConflict(f"grant {grant.grant_id} not found for CAS update")

    # ── Readiness (append-only evidence) ─────────────────────────────────────

    def append_readiness(self, assessment: Any) -> None:
        payload = assessment.to_dict() if hasattr(assessment, "to_dict") else dict(assessment)
        with self._file_lock(self._readiness_path):
            self._append_line(self._readiness_path, payload)

    def get_readiness(self, assessment_id: str) -> dict[str, Any] | None:
        for row in self._read_lines(self._readiness_path):
            if row.get("assessment_id") == assessment_id:
                return row
        return None

    # ── Leases ───────────────────────────────────────────────────────────────

    def append_lease(self, lease: Any) -> None:
        payload = lease.to_dict() if hasattr(lease, "to_dict") else dict(lease)
        with self._file_lock(self._leases_path):
            self._append_line(self._leases_path, payload)

    def get_lease(self, lease_id: str) -> dict[str, Any] | None:
        latest: dict[str, Any] | None = None
        for row in self._read_lines(self._leases_path):
            if row.get("lease_id") == lease_id:
                latest = row
        return latest

    def active_lease_for_task(self, task_id: str) -> dict[str, Any] | None:
        """Return the newest non-released/revoked/expired lease for a task."""
        latest_by_id: dict[str, dict[str, Any]] = {}
        for row in self._read_lines(self._leases_path):
            if row.get("task_id") == task_id:
                latest_by_id[row.get("lease_id", "")] = row
        for row in latest_by_id.values():
            if row.get("status") == "active":
                return row
        return None

    def update_lease_cas(
        self,
        lease: Any,
        expected_record_version: int,
        expected_statuses: tuple[str, ...] | None = None,
    ) -> Any:
        """CAS update of one lease record (append-latest-wins semantics: the
        newest row per lease_id is truth)."""
        lease_id = lease.lease_id if hasattr(lease, "lease_id") else lease.get("lease_id")
        payload = lease.to_dict() if hasattr(lease, "to_dict") else dict(lease)
        with self._file_lock(self._leases_path):
            rows = self._read_lines(self._leases_path)
            current: dict[str, Any] | None = None
            for row in rows:
                if row.get("lease_id") == lease_id:
                    current = row
            if current is None:
                raise AttemptStoreConflict(f"lease {lease_id} not found for CAS update")
            on_disk_version = int(current.get("record_version", -1))
            if on_disk_version != expected_record_version:
                raise AttemptStoreConflict(
                    f"lease {lease_id}: expected record_version {expected_record_version}, "
                    f"found {on_disk_version}"
                )
            if expected_statuses is not None and current.get("status") not in expected_statuses:
                raise AttemptStoreConflict(
                    f"lease {lease_id}: status {current.get('status')!r} not in expected "
                    f"{list(expected_statuses)}"
                )
            payload["record_version"] = on_disk_version + 1
            rows.append(payload)
            self._rewrite_atomic(self._leases_path, rows)
            return payload


__all__ = ["ExecutionAttemptStore", "AttemptStoreConflict"]
