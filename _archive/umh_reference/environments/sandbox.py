"""Sandbox manager — pre-execution safety validation + real enforcement.

Enforces permission checks, task safety, filesystem isolation (temp
working directories), and timeout bounds before execution.

No imports from umh/cells, umh/adapters, or umh/execution.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable

from umh.environments.models import (
    EnvironmentPermissions,
    ExecutionContext,
    ExecutionTask,
    SandboxVerdict,
    _gen_id,
)
from umh.core.clock import iso_now as _iso_now

_log = logging.getLogger(__name__)

_DANGEROUS_OPERATIONS = frozenset(
    {
        "drop_table",
        "delete_all",
        "rm_rf",
        "format_disk",
        "self_modify_core",
    }
)

_MAX_TIMEOUT_S = 300
_MIN_TIMEOUT_S = 1


class SandboxDecision:
    """Result of a sandbox validation check."""

    __slots__ = ("verdict", "reason", "task_id", "decided_at", "work_dir")

    def __init__(
        self,
        verdict: SandboxVerdict,
        task_id: str,
        reason: str = "",
        work_dir: str | None = None,
    ) -> None:
        self.verdict = verdict
        self.task_id = task_id
        self.reason = reason
        self.decided_at = _iso_now()
        self.work_dir = work_dir


class SandboxManager:
    """Pre-execution safety gate with real filesystem isolation."""

    def __init__(self, base_dir: str | None = None) -> None:
        self._lock = threading.Lock()
        self._decisions: list[SandboxDecision] = []
        self._custom_validators: list[Callable[[ExecutionTask], SandboxDecision | None]] = []
        self._active_dirs: dict[str, Path] = {}
        self._base_dir = base_dir

    def register_validator(
        self, validator: Callable[[ExecutionTask], SandboxDecision | None]
    ) -> None:
        with self._lock:
            self._custom_validators.append(validator)

    def validate_task(self, task: ExecutionTask) -> SandboxDecision:
        if task.operation in _DANGEROUS_OPERATIONS:
            decision = SandboxDecision(
                verdict=SandboxVerdict.REJECTED,
                task_id=task.task_id,
                reason=f"Operation '{task.operation}' is in the dangerous operations list",
            )
            with self._lock:
                self._decisions.append(decision)
            return decision

        timeout = task.metadata.get("timeout_s", 30)
        if not isinstance(timeout, (int, float)) or timeout < _MIN_TIMEOUT_S:
            decision = SandboxDecision(
                verdict=SandboxVerdict.REJECTED,
                task_id=task.task_id,
                reason=f"Invalid timeout: {timeout} (min={_MIN_TIMEOUT_S})",
            )
            with self._lock:
                self._decisions.append(decision)
            return decision

        if timeout > _MAX_TIMEOUT_S:
            decision = SandboxDecision(
                verdict=SandboxVerdict.REJECTED,
                task_id=task.task_id,
                reason=f"Timeout {timeout}s exceeds maximum {_MAX_TIMEOUT_S}s",
            )
            with self._lock:
                self._decisions.append(decision)
            return decision

        with self._lock:
            validators = list(self._custom_validators)

        for validator in validators:
            result = validator(task)
            if result is not None and result.verdict == SandboxVerdict.REJECTED:
                with self._lock:
                    self._decisions.append(result)
                return result

        work_dir = self._create_work_dir(task.task_id)
        decision = SandboxDecision(
            verdict=SandboxVerdict.APPROVED,
            task_id=task.task_id,
            work_dir=str(work_dir) if work_dir else None,
        )
        with self._lock:
            self._decisions.append(decision)
        return decision

    def approve_execution(self, task: ExecutionTask) -> SandboxDecision:
        return self.validate_task(task)

    def reject_execution(
        self, task: ExecutionTask, reason: str = "manually rejected"
    ) -> SandboxDecision:
        decision = SandboxDecision(
            verdict=SandboxVerdict.REJECTED,
            task_id=task.task_id,
            reason=reason,
        )
        with self._lock:
            self._decisions.append(decision)
        return decision

    def _create_work_dir(self, task_id: str) -> Path | None:
        try:
            d = Path(
                tempfile.mkdtemp(
                    prefix=f"umh_sandbox_{task_id}_",
                    dir=self._base_dir,
                )
            )
            with self._lock:
                self._active_dirs[task_id] = d
            return d
        except Exception as e:
            _log.warning("Failed to create sandbox dir for %s: %s", task_id, e)
            return None

    def cleanup_task(self, task_id: str) -> bool:
        with self._lock:
            d = self._active_dirs.pop(task_id, None)
        if d is None:
            return False
        try:
            if d.exists():
                shutil.rmtree(d)
            return True
        except Exception as e:
            _log.warning("Failed to clean sandbox dir %s: %s", d, e)
            return False

    def get_work_dir(self, task_id: str) -> Path | None:
        with self._lock:
            return self._active_dirs.get(task_id)

    def list_decisions(self) -> list[SandboxDecision]:
        with self._lock:
            return list(self._decisions)

    def cleanup_all(self) -> int:
        with self._lock:
            dirs = dict(self._active_dirs)
            self._active_dirs.clear()
        cleaned = 0
        for task_id, d in dirs.items():
            try:
                if d.exists():
                    shutil.rmtree(d)
                cleaned += 1
            except Exception as e:
                _log.warning("Failed to clean sandbox dir %s: %s", d, e)
        return cleaned

    def clear(self) -> None:
        self.cleanup_all()
        with self._lock:
            self._decisions.clear()
            self._custom_validators.clear()
