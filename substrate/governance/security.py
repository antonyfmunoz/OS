"""Security hardening — input validation, rate limiting, audit logging.

System boundary validation. Only validates at system boundaries
(API input, external data, user-facing parameters). Internal
substrate code trusts its own contracts.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DANGEROUS_PATTERNS = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.\\"),
    re.compile(r"[;&|`$]"),
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"union\s+select", re.IGNORECASE),
    re.compile(r";\s*drop\s+", re.IGNORECASE),
    re.compile(r"--\s*$"),
    re.compile(r"'\s*or\s+'", re.IGNORECASE),
]

_SAFE_PATH_ROOT = Path("/opt/OS")


@dataclass
class ValidationResult:
    valid: bool = True
    violations: list[str] = field(default_factory=list)
    sanitized: str = ""


def validate_signal_content(content: str, max_length: int = 5000) -> ValidationResult:
    """Validate signal content at the API boundary."""
    result = ValidationResult(sanitized=content)

    if not content or not content.strip():
        result.valid = False
        result.violations.append("empty content")
        return result

    if len(content) > max_length:
        result.valid = False
        result.violations.append(f"content exceeds {max_length} characters")
        return result

    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(content):
            result.violations.append(f"suspicious pattern: {pattern.pattern}")

    if result.violations:
        logger.warning("signal validation: %d violations in content", len(result.violations))

    return result


def validate_path(path: str) -> ValidationResult:
    """Validate a file path is within safe boundaries."""
    result = ValidationResult(sanitized=path)

    if ".." in path:
        result.valid = False
        result.violations.append("path traversal attempt")
        return result

    try:
        resolved = Path(path).resolve()
        if not str(resolved).startswith(str(_SAFE_PATH_ROOT)):
            result.valid = False
            result.violations.append(f"path outside safe root: {resolved}")
    except (ValueError, OSError) as e:
        result.valid = False
        result.violations.append(f"invalid path: {e}")

    return result


def validate_command(command: str) -> ValidationResult:
    """Validate a shell command at the API boundary.

    This is a first-pass filter. The workstation orchestrator's
    GovernedShellAdapter provides the real governance gate.
    """
    result = ValidationResult(sanitized=command)

    if not command.strip():
        result.valid = False
        result.violations.append("empty command")
        return result

    if len(command) > 2000:
        result.valid = False
        result.violations.append("command exceeds 2000 characters")
        return result

    dangerous_commands = [
        "rm -rf /", "mkfs", "dd if=", ":(){", "chmod -R 777 /",
        "wget.*|.*sh", "curl.*|.*sh",
    ]
    cmd_lower = command.lower().strip()
    for dangerous in dangerous_commands:
        if re.search(dangerous, cmd_lower):
            result.valid = False
            result.violations.append(f"blocked command pattern: {dangerous}")

    return result


class RateLimiter:
    """Token bucket rate limiter for API endpoints."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ) -> None:
        self._rpm = requests_per_minute
        self._burst = burst_size
        self._tokens: dict[str, float] = defaultdict(lambda: float(burst_size))
        self._last_refill: dict[str, float] = defaultdict(time.monotonic)

    def allow(self, client_id: str = "default") -> bool:
        """Check if a request is allowed under the rate limit."""
        now = time.monotonic()
        elapsed = now - self._last_refill[client_id]
        self._last_refill[client_id] = now

        refill = elapsed * (self._rpm / 60.0)
        self._tokens[client_id] = min(
            self._burst, self._tokens[client_id] + refill
        )

        if self._tokens[client_id] >= 1.0:
            self._tokens[client_id] -= 1.0
            return True

        return False


class AuditLog:
    """Append-only audit log for sensitive operations."""

    def __init__(self, log_path: str = "data/umh/audit/audit.jsonl") -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        action: str,
        actor: str = "system",
        target: str = "",
        outcome: str = "success",
        detail: str = "",
        risk_level: str = "low",
    ) -> None:
        """Record an auditable event."""
        import json

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "actor": actor,
            "target": target,
            "outcome": outcome,
            "detail": detail[:500],
            "risk_level": risk_level,
            "entry_hash": "",
        }
        raw = json.dumps(entry, sort_keys=True, separators=(",", ":"))
        entry["entry_hash"] = hashlib.sha256(raw.encode()).hexdigest()[:16]

        try:
            with open(self._path, "a") as f:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        except OSError as e:
            logger.error("audit log write failed: %s", e)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Read recent audit entries."""
        import json

        if not self._path.exists():
            return []

        entries: list[dict[str, Any]] = []
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass

        return entries[-limit:]


_rate_limiter = RateLimiter()
_audit_log = AuditLog()


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter


def get_audit_log() -> AuditLog:
    return _audit_log
