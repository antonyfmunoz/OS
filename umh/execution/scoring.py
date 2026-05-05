"""UMH Capability Scoring — track success rate and latency per capability.

In-memory registry that accumulates execution statistics. Not persisted —
resets on process restart. Designed for operational visibility, not billing.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)


@dataclass
class CapabilityStats:
    """Running statistics for a single capability type."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    timed_out_calls: int = 0
    total_latency_ms: int = 0
    total_cost_usd: float = 0.0
    last_error: str | None = None

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def failure_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls

    @property
    def timeout_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.timed_out_calls / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "timed_out_calls": self.timed_out_calls,
            "success_rate": round(self.success_rate, 4),
            "failure_rate": round(self.failure_rate, 4),
            "timeout_rate": round(self.timeout_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "total_cost_usd": round(self.total_cost_usd, 6),
            "last_error": self.last_error,
        }


class CapabilityScorer:
    """In-memory capability execution scorer.

    Thread-safe. Records execution events and provides per-capability statistics.
    Supports both aggregate (per-capability) and environment-specific stats.
    """

    def __init__(self) -> None:
        self._stats: dict[str, CapabilityStats] = {}
        self._env_stats: dict[tuple[str, str], CapabilityStats] = {}
        self._lock = threading.Lock()

    def _record_into(
        self, stats: CapabilityStats, status: str, latency: int, cost: float, error: str | None
    ) -> None:
        stats.total_calls += 1
        stats.total_latency_ms += latency
        stats.total_cost_usd += cost
        if status == "succeeded":
            stats.successful_calls += 1
        elif status == "rejected":
            stats.rejected_calls += 1
        elif status == "timed_out":
            stats.timed_out_calls += 1
            stats.failed_calls += 1
        else:
            stats.failed_calls += 1
        if error:
            stats.last_error = error

    def record(self, event: Any) -> None:
        """Record an execution event.

        Accepts any object with capability_type, status, latency_ms,
        cost_usd, error, environment_type attributes.
        """
        try:
            cap_type = getattr(event, "capability_type", "unknown")
            status = getattr(event, "status", "unknown")
            latency = getattr(event, "latency_ms", 0)
            cost = getattr(event, "cost_usd", 0.0)
            error = getattr(event, "error", None)
            env_type = getattr(event, "environment_type", "local")

            with self._lock:
                if cap_type not in self._stats:
                    self._stats[cap_type] = CapabilityStats()
                self._record_into(self._stats[cap_type], status, latency, cost, error)

                env_key = (cap_type, env_type)
                if env_key not in self._env_stats:
                    self._env_stats[env_key] = CapabilityStats()
                self._record_into(self._env_stats[env_key], status, latency, cost, error)
        except Exception as e:
            _log.debug("CapabilityScorer.record failed (non-fatal): %s", e)

    def get_stats(self, capability_type: str) -> CapabilityStats:
        """Get aggregate statistics for a capability type (all environments)."""
        with self._lock:
            return self._stats.get(capability_type, CapabilityStats())

    def get_env_stats(self, capability_type: str, environment_type: str) -> CapabilityStats:
        """Get statistics for a capability type in a specific environment."""
        with self._lock:
            return self._env_stats.get((capability_type, environment_type), CapabilityStats())

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get aggregate statistics for all capability types."""
        with self._lock:
            return {k: v.to_dict() for k, v in self._stats.items()}

    def get_all_env_stats(self) -> dict[str, dict[str, Any]]:
        """Get per-environment statistics for all capability+environment pairs."""
        with self._lock:
            return {f"{cap}:{env}": v.to_dict() for (cap, env), v in self._env_stats.items()}

    def reset(self) -> None:
        """Clear all accumulated statistics."""
        with self._lock:
            self._stats.clear()
            self._env_stats.clear()


# Module-level singleton
_scorer = CapabilityScorer()


def get_capability_scorer() -> CapabilityScorer:
    """Return the module-level CapabilityScorer singleton."""
    return _scorer
