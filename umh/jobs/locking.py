"""Job locking — prevents concurrent execution of the same job.

Atomic lock acquisition with expiry support. File-based, in-memory
tracking. Stale locks are automatically released on check.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from umh.core.clock import iso_now as _iso_now


@dataclass(frozen=True)
class JobLock:
    """Represents ownership of a job by a specific node."""

    job_id: str
    node_id: str
    acquired_at: str
    expires_at: str


_DEFAULT_LOCK_TTL_S = 300.0


class JobLockManager:
    """Thread-safe job lock manager with TTL-based expiry."""

    def __init__(self, lock_ttl_s: float = _DEFAULT_LOCK_TTL_S) -> None:
        self._lock = threading.Lock()
        self._locks: dict[str, JobLock] = {}
        self._lock_ttl_s = lock_ttl_s

    @property
    def lock_ttl_s(self) -> float:
        return self._lock_ttl_s

    def acquire_lock(
        self,
        job_id: str,
        node_id: str,
        *,
        now: str = "",
        ttl_s: float | None = None,
    ) -> JobLock | None:
        """Acquire a lock on a job. Returns the lock if acquired, None if already locked."""
        ts = now or _iso_now()
        ttl = ttl_s if ttl_s is not None else self._lock_ttl_s

        from datetime import datetime, timedelta, timezone

        try:
            acquired_dt = datetime.fromisoformat(ts)
            if acquired_dt.tzinfo is None:
                acquired_dt = acquired_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            acquired_dt = datetime.now(timezone.utc)

        expires_dt = acquired_dt + timedelta(seconds=ttl)
        expires_str = expires_dt.isoformat()

        with self._lock:
            existing = self._locks.get(job_id)
            if existing is not None:
                if not self._is_expired(existing, acquired_dt):
                    return None
                del self._locks[job_id]

            lock = JobLock(
                job_id=job_id,
                node_id=node_id,
                acquired_at=ts,
                expires_at=expires_str,
            )
            self._locks[job_id] = lock
            return lock

    def release_lock(self, job_id: str, *, node_id: str | None = None) -> bool:
        """Release a lock. If node_id is given, only releases if the lock is owned by that node."""
        with self._lock:
            existing = self._locks.get(job_id)
            if existing is None:
                return False
            if node_id is not None and existing.node_id != node_id:
                return False
            del self._locks[job_id]
            return True

    def is_locked(self, job_id: str, *, now: str = "") -> bool:
        """Check if a job is currently locked (non-expired)."""
        with self._lock:
            existing = self._locks.get(job_id)
            if existing is None:
                return False

            from datetime import datetime, timezone

            if now:
                try:
                    ref = datetime.fromisoformat(now)
                    if ref.tzinfo is None:
                        ref = ref.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    ref = datetime.now(timezone.utc)
            else:
                ref = datetime.now(timezone.utc)

            if self._is_expired(existing, ref):
                del self._locks[job_id]
                return False
            return True

    def get_lock(self, job_id: str) -> JobLock | None:
        """Get the current lock for a job, or None if unlocked."""
        with self._lock:
            return self._locks.get(job_id)

    def get_owner(self, job_id: str) -> str | None:
        """Get the node_id that owns a job's lock."""
        with self._lock:
            existing = self._locks.get(job_id)
            if existing is None:
                return None
            return existing.node_id

    def list_locks(self) -> list[JobLock]:
        """List all active locks."""
        with self._lock:
            return list(self._locks.values())

    def clear_expired(self, *, now: str = "") -> int:
        """Remove all expired locks. Returns count of removed locks."""
        from datetime import datetime, timezone

        if now:
            try:
                ref = datetime.fromisoformat(now)
                if ref.tzinfo is None:
                    ref = ref.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                ref = datetime.now(timezone.utc)
        else:
            ref = datetime.now(timezone.utc)

        with self._lock:
            expired = [jid for jid, lock in self._locks.items() if self._is_expired(lock, ref)]
            for jid in expired:
                del self._locks[jid]
            return len(expired)

    def clear(self) -> None:
        """Remove all locks."""
        with self._lock:
            self._locks.clear()

    @staticmethod
    def _is_expired(lock: JobLock, ref_dt: "datetime") -> bool:
        from datetime import datetime, timezone

        try:
            expires = datetime.fromisoformat(lock.expires_at)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            return ref_dt >= expires
        except (ValueError, TypeError):
            return False
