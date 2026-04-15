"""Capability Registry — models available execution resources.

Each Capability represents a resource that can execute primitive-derived
tasks: an LLM, a local Python runtime, an external API, or a human.
The registry is the single source of truth for what the system can use.

Performance data is stored alongside each capability and updated after
every execution via `record_outcome()`.  The matcher reads this data
to adjust scoring over time — capabilities that consistently
underperform get ranked lower automatically.

Usage:
    from core.capabilities import CAPABILITY_REGISTRY, get_capability

    cap = get_capability("claude_opus")
    print(cap.quality_score, cap.performance.success_rate)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Performance tracking
# ---------------------------------------------------------------------------

_PERF_LOG_DIR = Path("/opt/OS/logs/capability_performance")


@dataclass
class PerformanceRecord:
    """Running statistics for a single capability.

    Updated after every execution.  Persisted to disk so learning
    survives restarts.
    """

    total_runs: int = 0
    successes: int = 0
    total_latency_s: float = 0.0
    total_cost: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / self.total_runs if self.total_runs > 0 else 0.5

    @property
    def avg_latency_s(self) -> float:
        return self.total_latency_s / self.total_runs if self.total_runs > 0 else 0.0

    @property
    def cost_efficiency(self) -> float:
        """Cost per successful run.  Lower is better."""
        if self.successes == 0:
            return float("inf")
        return self.total_cost / self.successes

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "successes": self.successes,
            "success_rate": round(self.success_rate, 4),
            "avg_latency_s": round(self.avg_latency_s, 4),
            "total_cost": round(self.total_cost, 6),
            "cost_efficiency": (
                round(self.cost_efficiency, 6)
                if self.cost_efficiency != float("inf")
                else None
            ),
        }


# ---------------------------------------------------------------------------
# Capability definition
# ---------------------------------------------------------------------------


@dataclass
class Capability:
    """A single execution resource available to the system.

    Attributes:
        name:            Unique identifier (e.g. "claude_opus", "local_python").
        type:            Resource category: "llm", "local", "api", "human".
        strengths:       What this capability excels at.
        weaknesses:      Known limitations.
        cost:            Normalised cost per invocation (0.0–1.0 scale).
        latency:         Normalised expected latency (0.0–1.0 scale).
        quality_score:   Baseline quality expectation (0.0–1.0).
        supported_tasks: Task types this capability can handle.
        performance:     Adaptive stats updated after every run.
    """

    name: str
    type: str  # "llm" | "local" | "api" | "human"
    strengths: list[str]
    weaknesses: list[str]
    cost: float
    latency: float
    quality_score: float
    supported_tasks: list[str]
    performance: PerformanceRecord = field(default_factory=PerformanceRecord)

    def effective_quality(self) -> float:
        """Quality adjusted by observed success rate.

        Blends the static baseline with live performance.  Early on
        (< 10 runs) the baseline dominates; as data accumulates the
        observed rate takes over.
        """
        if self.performance.total_runs < 3:
            return self.quality_score
        weight = min(self.performance.total_runs / 20.0, 1.0)
        return (
            1 - weight
        ) * self.quality_score + weight * self.performance.success_rate

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "cost": self.cost,
            "latency": self.latency,
            "quality_score": self.quality_score,
            "effective_quality": round(self.effective_quality(), 4),
            "supported_tasks": self.supported_tasks,
            "performance": self.performance.to_dict(),
        }


# ---------------------------------------------------------------------------
# Built-in capabilities
# ---------------------------------------------------------------------------


def _build_default_capabilities() -> dict[str, Capability]:
    caps = [
        Capability(
            name="claude_opus",
            type="llm",
            strengths=["reasoning", "long_context", "planning", "analysis"],
            weaknesses=["cost", "latency"],
            cost=0.9,
            latency=0.6,
            quality_score=0.95,
            supported_tasks=[
                "analysis",
                "strategy",
                "composition",
                "reasoning",
                "planning",
            ],
        ),
        Capability(
            name="gemini_flash",
            type="llm",
            strengths=["speed", "moderate_quality", "long_context"],
            weaknesses=["less_precise_reasoning"],
            cost=0.3,
            latency=0.3,
            quality_score=0.78,
            supported_tasks=[
                "generation",
                "analysis",
                "composition",
                "simple_tasks",
                "reasoning",
            ],
        ),
        Capability(
            name="fast_llm",
            type="llm",
            strengths=["speed", "cheap"],
            weaknesses=["lower_quality"],
            cost=0.2,
            latency=0.2,
            quality_score=0.60,
            supported_tasks=["generation", "simple_tasks", "formatting"],
        ),
        Capability(
            name="local_python",
            type="local",
            strengths=["execution", "speed", "low_cost", "deterministic"],
            weaknesses=["no_reasoning", "no_generation"],
            cost=0.05,
            latency=0.05,
            quality_score=0.70,
            supported_tasks=[
                "execution",
                "transformation",
                "formatting",
                "computation",
            ],
        ),
        Capability(
            name="local_ollama",
            type="llm",
            strengths=["free", "private", "available"],
            weaknesses=["low_quality", "limited_context"],
            cost=0.02,
            latency=0.4,
            quality_score=0.45,
            supported_tasks=["generation", "simple_tasks"],
        ),
        Capability(
            name="human_review",
            type="human",
            strengths=["judgment", "domain_expertise", "approval"],
            weaknesses=["latency", "availability"],
            cost=0.0,
            latency=1.0,
            quality_score=0.99,
            supported_tasks=["approval", "strategy", "review"],
        ),
    ]
    return {c.name: c for c in caps}


# Module-level registry — mutable so capabilities can be added at runtime.
CAPABILITY_REGISTRY: dict[str, Capability] = _build_default_capabilities()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_capability(name: str) -> Capability | None:
    """Look up a capability by name."""
    return CAPABILITY_REGISTRY.get(name)


def register_capability(cap: Capability) -> None:
    """Add or replace a capability in the registry."""
    CAPABILITY_REGISTRY[cap.name] = cap


def list_capabilities(type_filter: str | None = None) -> list[Capability]:
    """Return all capabilities, optionally filtered by type."""
    caps = list(CAPABILITY_REGISTRY.values())
    if type_filter:
        caps = [c for c in caps if c.type == type_filter]
    return caps


def record_outcome(
    capability_name: str,
    *,
    success: bool,
    latency_s: float,
    cost: float = 0.0,
) -> None:
    """Record the outcome of an execution against a capability.

    Updates the in-memory performance record and persists to disk.
    """
    cap = CAPABILITY_REGISTRY.get(capability_name)
    if not cap:
        return

    perf = cap.performance
    perf.total_runs += 1
    if success:
        perf.successes += 1
    perf.total_latency_s += latency_s
    perf.total_cost += cost

    # Persist
    _persist_performance(capability_name, perf)


def load_performance_data() -> None:
    """Load persisted performance data into the registry on startup."""
    if not _PERF_LOG_DIR.exists():
        return
    for cap_name, cap in CAPABILITY_REGISTRY.items():
        path = _PERF_LOG_DIR / f"{cap_name}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                cap.performance = PerformanceRecord(
                    total_runs=data.get("total_runs", 0),
                    successes=data.get("successes", 0),
                    total_latency_s=data.get("total_latency_s", 0.0),
                    total_cost=data.get("total_cost", 0.0),
                )
            except (json.JSONDecodeError, KeyError):
                pass  # corrupt file — start fresh


def _persist_performance(cap_name: str, perf: PerformanceRecord) -> None:
    """Write performance record to disk."""
    _PERF_LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = _PERF_LOG_DIR / f"{cap_name}.json"
    path.write_text(
        json.dumps(
            {
                "total_runs": perf.total_runs,
                "successes": perf.successes,
                "total_latency_s": perf.total_latency_s,
                "total_cost": perf.total_cost,
                "updated_at": time.time(),
            },
            indent=2,
        )
    )


# Load on import so the registry starts warm.
load_performance_data()


__all__ = [
    "Capability",
    "PerformanceRecord",
    "CAPABILITY_REGISTRY",
    "get_capability",
    "register_capability",
    "list_capabilities",
    "record_outcome",
    "load_performance_data",
]
