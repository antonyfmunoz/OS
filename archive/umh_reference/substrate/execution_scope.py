"""
Execution Scope — scoped task approval with silent execution.

When a task is approved, an ExecutionScope is created that defines
the trust boundary for that task. Actions within the scope execute
silently (AUTO_APPROVE_AND_SUPPRESS). Actions outside the scope
or matching escalation rules go through normal policy evaluation.

Design rules:
- Scopes are immutable once created (frozen dataclass)
- Scopes have mandatory TTL — no indefinite trust grants
- Destructive actions ALWAYS escalate regardless of scope
- System paths ALWAYS blocked regardless of scope
- Scope evaluation is pure: no I/O, no side effects
- ScopeRegistry is the single source of truth for active scopes

Integration point: resolve_permission() in discord_output_policy.py
calls evaluate_scope() before normal policy evaluation.
"""

from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ─── Scope Evaluation Result ─────────────────────────────────────────────


class ScopeVerdict(str, Enum):
    """Result of checking an action against an execution scope."""

    WITHIN_SCOPE = "within_scope"  # action is trusted — silent execution
    OUTSIDE_SCOPE = "outside_scope"  # action not covered — normal policy
    ESCALATE = "escalate"  # action explicitly requires escalation
    NO_SCOPE = "no_scope"  # no active scope for this task
    SCOPE_EXPIRED = "scope_expired"  # scope exists but TTL exceeded


# Actions that ALWAYS require escalation regardless of scope.
# These are non-negotiable — scoped trust never covers destructive
# or system-affecting operations.
_ALWAYS_ESCALATE_ACTIONS: frozenset[str] = frozenset(
    {
        "rm",
        "rmdir",
        "unlink",
        "shred",
        "dd",
        "mkfs",
        "fdisk",
        "kill",
        "killall",
        "pkill",
        "shutdown",
        "reboot",
        "systemctl",
        "chmod",
        "chown",
        "chgrp",
        "mount",
        "umount",
        "iptables",
        "ufw",
    }
)

# Environment and config patterns that always escalate.
_ENV_CONFIG_PATTERNS: tuple[str, ...] = (
    ".env",
    ".bashrc",
    ".profile",
    ".zshrc",
    "docker-compose",
    "Dockerfile",
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "settings.json",
    "settings.local.json",
)

# System paths — scope never grants trust here.
_SYSTEM_ROOTS: tuple[str, ...] = (
    "/etc",
    "/usr",
    "/var",
    "/boot",
    "/sbin",
    "/bin",
    "/lib",
    "/proc",
    "/sys",
    "/dev",
)


# ─── Execution Scope Model ───────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutionScope:
    """Immutable trust boundary for an approved task.

    Once created, a scope defines exactly what actions are trusted
    for silent execution. The scope cannot be widened after creation —
    only a new scope can grant additional trust.

    Attributes:
        scope_id: Unique identifier for this scope.
        task_id: The task this scope is attached to.
        correlation_id: Workflow-level correlation (shared with event spine).
        allowed_roots: Directory trees where file operations are trusted.
            Actions targeting paths under these roots execute silently.
        allowed_intents: Intent types that are trusted within scope.
            Only these intent types get silent execution.
        restricted_actions: Commands that are explicitly blocked within scope.
            Overrides allowed_intents — these always escalate.
        escalation_required_actions: Commands that must escalate even in scope.
            Superset of _ALWAYS_ESCALATE_ACTIONS for task-specific additions.
        created_at: When the scope was created (UTC).
        expires_at: When the scope expires (UTC). Mandatory — no open-ended trust.
        issued_by: Who approved this scope (session name or operator ID).
        metadata: Bounded additional context about the scope.
    """

    scope_id: str
    task_id: str
    correlation_id: str
    allowed_roots: tuple[str, ...]
    allowed_intents: tuple[str, ...]
    restricted_actions: frozenset[str]
    escalation_required_actions: frozenset[str]
    created_at: str
    expires_at: str
    issued_by: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if this scope has exceeded its TTL."""
        now = datetime.now(timezone.utc)
        try:
            expiry = datetime.fromisoformat(self.expires_at)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return now >= expiry
        except (ValueError, TypeError):
            # Malformed expiry → treat as expired (fail-safe)
            return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging and storage."""
        return {
            "scope_id": self.scope_id,
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "allowed_roots": list(self.allowed_roots),
            "allowed_intents": list(self.allowed_intents),
            "restricted_actions": sorted(self.restricted_actions),
            "escalation_required_actions": sorted(self.escalation_required_actions),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "issued_by": self.issued_by,
            "metadata": self.metadata,
        }


# ─── Scope Evaluation Result ─────────────────────────────────────────────


@dataclass(frozen=True)
class ScopeEvaluation:
    """Result of evaluating an action against an execution scope.

    This is the return type of evaluate_scope(). It carries the verdict
    plus enough context for traceability in PermissionDecision.
    """

    verdict: ScopeVerdict
    scope_id: str | None
    escalation_reason: str | None

    @property
    def within_scope(self) -> bool:
        """True if the action is trusted within the scope."""
        return self.verdict == ScopeVerdict.WITHIN_SCOPE


# Singleton "no scope" result — avoids allocation on every check.
_NO_SCOPE = ScopeEvaluation(
    verdict=ScopeVerdict.NO_SCOPE, scope_id=None, escalation_reason=None
)


# ─── Scope Evaluation (Pure) ─────────────────────────────────────────────


def evaluate_scope(
    scope: ExecutionScope | None,
    intent_type: str,
    target_path: str = "",
    command: str = "",
) -> ScopeEvaluation:
    """Evaluate whether an action falls within an execution scope.

    Pure function — no I/O, no state mutation, deterministic.

    Args:
        scope: Active scope for the current task, or None.
        intent_type: The IntentType value (e.g. "file_write", "command").
        target_path: Target file/directory path, if applicable.
        command: Raw command string, if applicable.

    Returns:
        ScopeEvaluation with verdict and context.
    """
    if scope is None:
        return _NO_SCOPE

    if scope.is_expired():
        return ScopeEvaluation(
            verdict=ScopeVerdict.SCOPE_EXPIRED,
            scope_id=scope.scope_id,
            escalation_reason="scope TTL exceeded",
        )

    # Extract base command for action checks
    base_cmd = _extract_base_command(command) if command else ""

    # Check always-escalate actions (non-negotiable)
    if base_cmd and base_cmd in _ALWAYS_ESCALATE_ACTIONS:
        return ScopeEvaluation(
            verdict=ScopeVerdict.ESCALATE,
            scope_id=scope.scope_id,
            escalation_reason=f"destructive action: {base_cmd}",
        )

    # Check task-specific escalation actions
    if base_cmd and base_cmd in scope.escalation_required_actions:
        return ScopeEvaluation(
            verdict=ScopeVerdict.ESCALATE,
            scope_id=scope.scope_id,
            escalation_reason=f"task-restricted action: {base_cmd}",
        )

    # Check restricted actions (explicit deny within scope)
    if base_cmd and base_cmd in scope.restricted_actions:
        return ScopeEvaluation(
            verdict=ScopeVerdict.ESCALATE,
            scope_id=scope.scope_id,
            escalation_reason=f"restricted action: {base_cmd}",
        )

    # Check intent type is allowed
    if intent_type not in scope.allowed_intents:
        return ScopeEvaluation(
            verdict=ScopeVerdict.OUTSIDE_SCOPE,
            scope_id=scope.scope_id,
            escalation_reason=f"intent {intent_type} not in scope",
        )

    # Check target path is within allowed roots
    if target_path:
        if not _path_within_roots(target_path, scope.allowed_roots):
            reason = "target outside approved roots"
            # Check if it's a system path (more specific reason)
            normalized = os.path.normpath(os.path.abspath(target_path))
            for sys_root in _SYSTEM_ROOTS:
                if normalized.startswith(sys_root):
                    reason = f"system path: {sys_root}"
                    break
            return ScopeEvaluation(
                verdict=ScopeVerdict.ESCALATE,
                scope_id=scope.scope_id,
                escalation_reason=reason,
            )

    # Check for env/config file modifications
    if target_path and intent_type in ("file_write", "command"):
        basename = os.path.basename(target_path)
        for pattern in _ENV_CONFIG_PATTERNS:
            if basename == pattern or basename.startswith(pattern):
                return ScopeEvaluation(
                    verdict=ScopeVerdict.ESCALATE,
                    scope_id=scope.scope_id,
                    escalation_reason=f"config/env file: {basename}",
                )

    # Check for network side effects in commands
    if intent_type == "network_call":
        return ScopeEvaluation(
            verdict=ScopeVerdict.ESCALATE,
            scope_id=scope.scope_id,
            escalation_reason="network side effect",
        )

    # All checks passed — action is within scope
    return ScopeEvaluation(
        verdict=ScopeVerdict.WITHIN_SCOPE,
        scope_id=scope.scope_id,
        escalation_reason=None,
    )


def _extract_base_command(command: str) -> str:
    """Extract the base command name from a command string.

    Handles:
    - Simple commands: "ls -la" → "ls"
    - Path-qualified: "/usr/bin/rm foo" → "rm"
    - Sudo prefix: "sudo rm -rf /" → "rm"
    """
    if not command:
        return ""
    parts = command.strip().split()
    if not parts:
        return ""
    cmd = parts[0]
    # Strip path prefix
    cmd = os.path.basename(cmd)
    # Skip sudo
    if cmd == "sudo" and len(parts) > 1:
        cmd = os.path.basename(parts[1])
    return cmd


def _path_within_roots(target_path: str, allowed_roots: tuple[str, ...]) -> bool:
    """Check if a target path falls under any allowed root.

    Uses os.path normalization to prevent traversal attacks.
    """
    if not target_path or not allowed_roots:
        return False
    normalized = os.path.normpath(os.path.abspath(target_path))
    for root in allowed_roots:
        norm_root = os.path.normpath(os.path.abspath(root))
        if normalized.startswith(norm_root + os.sep) or normalized == norm_root:
            return True
    return False


# ─── Scope Registry (Singleton) ──────────────────────────────────────────


class ScopeRegistry:
    """Thread-safe registry for active execution scopes.

    Singleton. One scope per task_id at a time.
    Expired scopes are lazily evicted on lookup.
    """

    _instance: ScopeRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> ScopeRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._scopes: dict[str, ExecutionScope] = {}
                cls._instance._by_correlation: dict[str, str] = {}
                cls._instance._rlock = threading.RLock()
            return cls._instance

    def register(self, scope: ExecutionScope) -> None:
        """Register an active scope. Replaces any existing scope for the same task."""
        with self._rlock:
            # Evict previous scope for this task
            old = self._scopes.get(scope.task_id)
            if old and old.correlation_id in self._by_correlation:
                del self._by_correlation[old.correlation_id]
            self._scopes[scope.task_id] = scope
            self._by_correlation[scope.correlation_id] = scope.task_id

    def get_by_task(self, task_id: str) -> ExecutionScope | None:
        """Lookup scope by task_id. Returns None if expired or missing."""
        with self._rlock:
            scope = self._scopes.get(task_id)
            if scope is None:
                return None
            if scope.is_expired():
                self._evict(task_id)
                return None
            return scope

    def get_by_correlation(self, correlation_id: str) -> ExecutionScope | None:
        """Lookup scope by correlation_id."""
        with self._rlock:
            task_id = self._by_correlation.get(correlation_id)
            if task_id is None:
                return None
            return self.get_by_task(task_id)

    def revoke(self, task_id: str) -> bool:
        """Explicitly revoke a scope. Returns True if scope existed."""
        with self._rlock:
            return self._evict(task_id)

    def active_count(self) -> int:
        """Number of non-expired active scopes."""
        with self._rlock:
            self._sweep_expired()
            return len(self._scopes)

    def all_active(self) -> list[ExecutionScope]:
        """Return all non-expired scopes. Sweeps expired first."""
        with self._rlock:
            self._sweep_expired()
            return list(self._scopes.values())

    def _evict(self, task_id: str) -> bool:
        """Remove a scope by task_id. Returns True if found."""
        scope = self._scopes.pop(task_id, None)
        if scope is None:
            return False
        self._by_correlation.pop(scope.correlation_id, None)
        return True

    def _sweep_expired(self) -> None:
        """Remove all expired scopes."""
        expired = [tid for tid, s in self._scopes.items() if s.is_expired()]
        for tid in expired:
            self._evict(tid)

    def clear_all(self) -> int:
        """Clear all scopes. Returns count cleared. For testing only."""
        with self._rlock:
            count = len(self._scopes)
            self._scopes.clear()
            self._by_correlation.clear()
            return count


# ─── Scope Factory ────────────────────────────────────────────────────────


# Default scope TTL: 2 hours. Long enough for real tasks,
# short enough that forgotten scopes don't linger.
DEFAULT_SCOPE_TTL_SECONDS: int = 7200


def create_scope_for_task(
    task_id: str,
    correlation_id: str = "",
    allowed_roots: tuple[str, ...] = ("/opt/OS",),
    allowed_intents: tuple[str, ...] = (
        "file_write",
        "file_read",
        "command",
        "process_exec",
    ),
    restricted_actions: frozenset[str] = frozenset(),
    escalation_required_actions: frozenset[str] = frozenset(),
    ttl_seconds: int = DEFAULT_SCOPE_TTL_SECONDS,
    issued_by: str = "operator",
    metadata: dict[str, Any] | None = None,
    *,
    auto_register: bool = True,
) -> ExecutionScope:
    """Create and optionally register an execution scope for a task.

    This is the primary factory. Callers should use this rather than
    constructing ExecutionScope directly.

    Args:
        task_id: The task this scope authorizes.
        correlation_id: Workflow correlation. Generated if empty.
        allowed_roots: Directory trees where operations are trusted.
        allowed_intents: Intent types trusted for silent execution.
        restricted_actions: Commands explicitly blocked in scope.
        escalation_required_actions: Commands that must escalate in scope.
        ttl_seconds: How long the scope lives (default 2h).
        issued_by: Who approved this scope.
        metadata: Additional context.
        auto_register: If True, registers scope in ScopeRegistry.

    Returns:
        The created ExecutionScope.
    """
    now = datetime.now(timezone.utc)
    from datetime import timedelta

    expires = now + timedelta(seconds=ttl_seconds)

    # Merge task-specific escalation with global always-escalate set
    full_escalation = _ALWAYS_ESCALATE_ACTIONS | escalation_required_actions

    scope = ExecutionScope(
        scope_id=f"scope_{uuid.uuid4().hex[:12]}",
        task_id=task_id,
        correlation_id=correlation_id or f"corr_{uuid.uuid4().hex[:12]}",
        allowed_roots=allowed_roots,
        allowed_intents=allowed_intents,
        restricted_actions=restricted_actions,
        escalation_required_actions=full_escalation,
        created_at=now.isoformat(),
        expires_at=expires.isoformat(),
        issued_by=issued_by,
        metadata=metadata or {},
    )

    if auto_register:
        ScopeRegistry().register(scope)

    return scope


# ─── Module API ───────────────────────────────────────────────────────────

__all__ = [
    "DEFAULT_SCOPE_TTL_SECONDS",
    "ExecutionScope",
    "ScopeEvaluation",
    "ScopeRegistry",
    "ScopeVerdict",
    "create_scope_for_task",
    "evaluate_scope",
]
