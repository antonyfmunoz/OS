"""Capability registry — models available execution resources.

Each Capability represents something the system can use to execute:
an LLM, a local Python runtime, a shell, a browser, a human reviewer.

The registry is the single source of truth for what's available.
Capabilities register at boot and can be queried by type or tag.
Performance data is tracked per-capability and persisted via an
injectable PersistenceBackend Protocol.

No LLM calls. No domain-specific logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Performance tracking
# ---------------------------------------------------------------------------


@dataclass
class PerformanceStats:
    """Running statistics for a capability."""

    total_runs: int = 0
    successes: int = 0
    total_latency_ms: int = 0
    total_cost: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / self.total_runs if self.total_runs > 0 else 0.5

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_runs if self.total_runs > 0 else 0.0

    @property
    def cost_efficiency(self) -> float:
        """Cost per successful run. Lower is better."""
        if self.successes == 0:
            return float("inf")
        return self.total_cost / self.successes

    def record(self, success: bool, latency_ms: int, cost: float = 0.0) -> None:
        self.total_runs += 1
        if success:
            self.successes += 1
        self.total_latency_ms += latency_ms
        self.total_cost += cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "successes": self.successes,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "total_cost": round(self.total_cost, 6),
            "cost_efficiency": (
                round(self.cost_efficiency, 6)
                if self.cost_efficiency != float("inf")
                else None
            ),
        }


# ---------------------------------------------------------------------------
# Persistence protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PersistenceBackend(Protocol):
    """Protocol for persisting capability performance data."""

    def save(self, capability_name: str, stats: PerformanceStats) -> None: ...
    def load(self, capability_name: str) -> PerformanceStats | None: ...


class NullPersistence:
    """No-op persistence — stats live only in memory."""

    def save(self, capability_name: str, stats: PerformanceStats) -> None:
        pass

    def load(self, capability_name: str) -> PerformanceStats | None:
        return None


# ---------------------------------------------------------------------------
# Capability definition
# ---------------------------------------------------------------------------


@dataclass
class Capability:
    """A registered execution resource.

    Attributes:
        name:             Unique identifier (e.g. "claude_opus", "local_python").
        capability_type:  Resource category: "llm", "runtime", "api", "human".
        description:      Human-readable description.
        tags:             Queryable tags — includes strengths and supported tasks.
        quality_score:    Baseline quality expectation (0.0–1.0).
        cost_per_call:    Normalised cost per invocation.
        latency_score:    Normalised expected latency (0.0–1.0, lower = faster).
        available:        Whether this capability is currently usable.
        weaknesses:       Known limitations (for routing awareness).
        performance:      Adaptive stats updated after every run.
        metadata:         Free-form extras (generation_quality, determinism, etc).
    """

    name: str
    capability_type: str
    description: str = ""
    tags: tuple[str, ...] = ()
    quality_score: float = 0.5
    cost_per_call: float = 0.0
    latency_score: float = 0.5
    available: bool = True
    weaknesses: tuple[str, ...] = ()
    performance: PerformanceStats = field(default_factory=PerformanceStats)
    metadata: dict[str, Any] = field(default_factory=dict)

    def effective_quality(self) -> float:
        """Quality adjusted by observed success rate.

        Blends the static baseline with live performance. Early on
        (< 3 runs) the baseline dominates; as data accumulates the
        observed rate takes over.
        """
        if self.performance.total_runs < 3:
            return self.quality_score
        weight = min(self.performance.total_runs / 20.0, 1.0)
        return (
            1 - weight
        ) * self.quality_score + weight * self.performance.success_rate

    def supports_task(self, task_type: str) -> bool:
        """Check if this capability supports a given task type via tags."""
        return task_type in self.tags

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "capability_type": self.capability_type,
            "description": self.description,
            "tags": list(self.tags),
            "quality_score": round(self.quality_score, 4),
            "effective_quality": round(self.effective_quality(), 4),
            "cost_per_call": round(self.cost_per_call, 6),
            "latency_score": round(self.latency_score, 4),
            "available": self.available,
            "weaknesses": list(self.weaknesses),
            "performance": self.performance.to_dict(),
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class CapabilityRegistry:
    """Registry of available capabilities with optional persistence."""

    def __init__(
        self,
        *,
        persistence: PersistenceBackend | None = None,
    ) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._persistence: PersistenceBackend = persistence or NullPersistence()

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.name] = capability

    def unregister(self, name: str) -> None:
        self._capabilities.pop(name, None)

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def list_all(self) -> list[Capability]:
        return list(self._capabilities.values())

    def list_available(self) -> list[Capability]:
        return [c for c in self._capabilities.values() if c.available]

    def by_type(self, capability_type: str) -> list[Capability]:
        return [
            c
            for c in self._capabilities.values()
            if c.capability_type == capability_type and c.available
        ]

    def by_tag(self, tag: str) -> list[Capability]:
        return [c for c in self._capabilities.values() if tag in c.tags and c.available]

    def record_outcome(
        self,
        capability_name: str,
        *,
        success: bool,
        latency_ms: int,
        cost: float = 0.0,
    ) -> None:
        """Record an execution outcome and persist."""
        cap = self._capabilities.get(capability_name)
        if cap is None:
            return
        cap.performance.record(success, latency_ms, cost)
        self._persistence.save(capability_name, cap.performance)

    def load_persisted(self) -> None:
        """Load persisted performance data for all registered capabilities."""
        for name, cap in self._capabilities.items():
            loaded = self._persistence.load(name)
            if loaded is not None:
                cap.performance = loaded

    @property
    def size(self) -> int:
        return len(self._capabilities)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": {n: c.to_dict() for n, c in self._capabilities.items()},
            "total": self.size,
            "available": len(self.list_available()),
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_REGISTRY: CapabilityRegistry | None = None


def get_registry() -> CapabilityRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _default_registry()
    return _REGISTRY


def set_registry(registry: CapabilityRegistry) -> None:
    global _REGISTRY
    _REGISTRY = registry


def reset_registry() -> None:
    global _REGISTRY
    _REGISTRY = None


def _default_registry() -> CapabilityRegistry:
    """Create a registry with built-in capabilities."""
    reg = CapabilityRegistry()

    reg.register(
        Capability(
            name="local_python",
            capability_type="runtime",
            description="Local Python interpreter — pure computation, no side effects",
            tags=(
                "compute",
                "safe",
                "local",
                "deterministic",
                "execution",
                "transformation",
                "formatting",
                "computation",
            ),
            quality_score=0.8,
            cost_per_call=0.0,
            latency_score=0.05,
            available=True,
            metadata={"determinism": 1.0, "generation_quality": 0.0},
        )
    )

    reg.register(
        Capability(
            name="null_llm",
            capability_type="llm",
            description="Null LLM — returns echo/template responses",
            tags=("llm", "safe", "stub"),
            quality_score=0.1,
            cost_per_call=0.0,
            latency_score=0.1,
            available=True,
            metadata={"determinism": 0.0, "generation_quality": 0.05},
        )
    )

    from umh.adapters.llm import discover_llm_adapter

    real_llm = discover_llm_adapter()
    if real_llm is not None:
        model_name = getattr(real_llm, "model", "unknown")
        adapter_type = type(real_llm).__name__
        reg.register(
            Capability(
                name="llm_generation",
                capability_type="llm",
                description=f"Real LLM via {adapter_type} — natural language generation",
                tags=(
                    "llm",
                    "generation",
                    "reasoning",
                    "analysis",
                    "strategy",
                    "composition",
                    "planning",
                ),
                quality_score=0.7,
                cost_per_call=0.001,
                latency_score=0.5,
                available=True,
                weaknesses=("cost", "nondeterministic"),
                metadata={
                    "determinism": 0.1,
                    "generation_quality": 0.9,
                    "adapter": adapter_type,
                    "model": model_name,
                },
            )
        )

    return reg


__all__ = [
    "Capability",
    "CapabilityRegistry",
    "NullPersistence",
    "PerformanceStats",
    "PersistenceBackend",
    "get_registry",
    "reset_registry",
    "set_registry",
]
