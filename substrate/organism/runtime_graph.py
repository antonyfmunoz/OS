"""RuntimeGraph — canonical runtime registry with dynamic availability.

The RuntimeGraph is the organism's knowledge of what execution runtimes
exist, what each can do, how reliable each is, and which is best for a
given task. It is the single source of truth for runtime selection.

Every runtime (Claude Code, Codex, Hermes, OpenCode, Ollama, Docker,
tmux, Beast GPU) registers here with its capabilities, cost profile,
and availability status. The graph answers: "given this task, which
runtime should execute it?"

Routing algorithm:
  1. Filter by required capability
  2. Filter by availability (AVAILABLE only)
  3. Score by: reliability * (1 / cost_weight) * (1 / latency_weight)
  4. Return best match with fallback chain

UMH substrate subsystem.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class AvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    STARTING = "starting"
    UNKNOWN = "unknown"


class RuntimeClass(str, Enum):
    AI_CLI = "ai_cli"
    AI_API = "ai_api"
    LOCAL_MODEL = "local_model"
    PROCESS = "process"
    CONTAINER = "container"
    REMOTE_NODE = "remote_node"


class RuntimeCapability(str, Enum):
    CODE_WRITE = "code_write"
    CODE_REVIEW = "code_review"
    CODE_EXECUTE = "code_execute"
    REASON = "reason"
    RESEARCH = "research"
    SHELL = "shell"
    BROWSER = "browser"
    GPU_COMPUTE = "gpu_compute"
    FILE_OPS = "file_ops"
    AUTONOMOUS = "autonomous"
    FAST_RESPONSE = "fast_response"


@dataclass
class CostProfile:
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    is_subscription: bool = False
    monthly_cap_usd: float = 0.0

    @property
    def effective_cost(self) -> float:
        if self.is_subscription:
            return 0.01
        return (self.cost_per_1k_input + self.cost_per_1k_output) / 2


@dataclass
class ReliabilityScore:
    successes: int = 0
    failures: int = 0
    total_latency_ms: int = 0

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        if total == 0:
            return 0.5
        return self.successes / total

    @property
    def avg_latency_ms(self) -> float:
        if self.successes == 0:
            return 10000.0
        return self.total_latency_ms / self.successes

    def record_success(self, latency_ms: int) -> None:
        self.successes += 1
        self.total_latency_ms += latency_ms

    def record_failure(self) -> None:
        self.failures += 1


@runtime_checkable
class RuntimeAdapter(Protocol):
    """Protocol that every runtime adapter must satisfy."""

    @property
    def runtime_id(self) -> str: ...

    @property
    def runtime_class(self) -> RuntimeClass: ...

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]: ...

    def check_available(self) -> bool: ...

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None: ...


@dataclass
class RuntimeResult:
    output: str
    runtime_id: str
    latency_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeNode:
    """A registered runtime in the graph."""

    runtime_id: str
    runtime_class: RuntimeClass
    capabilities: frozenset[RuntimeCapability]
    cost: CostProfile = field(default_factory=CostProfile)
    reliability: ReliabilityScore = field(default_factory=ReliabilityScore)
    status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    last_heartbeat: float = 0.0
    adapter: RuntimeAdapter | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        return self.status in {AvailabilityStatus.AVAILABLE, AvailabilityStatus.DEGRADED}

    def score(self) -> float:
        reliability = self.reliability.success_rate
        cost_factor = 1.0 / (1.0 + self.cost.effective_cost)
        latency_factor = 1.0 / (1.0 + self.reliability.avg_latency_ms / 1000.0)
        degraded_penalty = 0.8 if self.status == AvailabilityStatus.DEGRADED else 1.0
        return reliability * cost_factor * latency_factor * degraded_penalty

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "runtime_class": self.runtime_class.value,
            "capabilities": sorted(c.value for c in self.capabilities),
            "status": self.status.value,
            "score": round(self.score(), 4),
            "reliability": {
                "success_rate": round(self.reliability.success_rate, 3),
                "avg_latency_ms": round(self.reliability.avg_latency_ms, 1),
                "total_calls": self.reliability.successes + self.reliability.failures,
            },
            "cost": {
                "effective": round(self.cost.effective_cost, 4),
                "subscription": self.cost.is_subscription,
            },
            "last_heartbeat": self.last_heartbeat,
        }


_HEARTBEAT_STALE_S = 120.0


class RuntimeGraph:
    """Canonical registry of all execution runtimes.

    Handles registration, availability tracking, capability-based
    routing, and reliability scoring. The organism queries this
    graph to determine where to execute any given task.
    """

    def __init__(self, event_spine: Any | None = None) -> None:
        self._nodes: dict[str, RuntimeNode] = {}
        self._event_spine = event_spine

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self._event_spine is None:
            return
        from substrate.organism.event_spine import EventDomain
        self._event_spine.emit(EventDomain.RUNTIME, event_type, "runtime_graph", data)

    def register(
        self,
        runtime_id: str,
        runtime_class: RuntimeClass,
        capabilities: frozenset[RuntimeCapability],
        cost: CostProfile | None = None,
        adapter: RuntimeAdapter | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeNode:
        node = RuntimeNode(
            runtime_id=runtime_id,
            runtime_class=runtime_class,
            capabilities=capabilities,
            cost=cost or CostProfile(),
            adapter=adapter,
            metadata=metadata or {},
        )
        self._nodes[runtime_id] = node
        logger.info(
            "runtime registered: %s (%s) caps=%s",
            runtime_id,
            runtime_class.value,
            sorted(c.value for c in capabilities),
        )
        self._emit("runtime_registered", {"runtime_id": runtime_id, "class": runtime_class.value})
        return node

    def unregister(self, runtime_id: str) -> bool:
        return self._nodes.pop(runtime_id, None) is not None

    def get(self, runtime_id: str) -> RuntimeNode | None:
        return self._nodes.get(runtime_id)

    def update_status(self, runtime_id: str, status: AvailabilityStatus) -> None:
        node = self._nodes.get(runtime_id)
        if node:
            node.status = status
            node.last_heartbeat = time.time()
            self._emit("runtime_status_changed", {"runtime_id": runtime_id, "new_status": status.value})

    def record_success(self, runtime_id: str, latency_ms: int) -> None:
        node = self._nodes.get(runtime_id)
        if node:
            node.reliability.record_success(latency_ms)
            node.status = AvailabilityStatus.AVAILABLE
            node.last_heartbeat = time.time()
            self._emit("runtime_success_recorded", {"runtime_id": runtime_id, "latency_ms": latency_ms})

    def record_failure(self, runtime_id: str) -> None:
        node = self._nodes.get(runtime_id)
        if node:
            node.reliability.record_failure()
            if node.reliability.success_rate < 0.3:
                node.status = AvailabilityStatus.UNAVAILABLE
            self._emit("runtime_failure_recorded", {"runtime_id": runtime_id})

    def refresh_availability(self) -> dict[str, AvailabilityStatus]:
        """Probe all runtimes and update availability."""
        results: dict[str, AvailabilityStatus] = {}
        now = time.time()

        for rid, node in self._nodes.items():
            if node.adapter is not None:
                try:
                    available = node.adapter.check_available()
                    node.status = (
                        AvailabilityStatus.AVAILABLE
                        if available
                        else AvailabilityStatus.UNAVAILABLE
                    )
                    node.last_heartbeat = now
                except Exception:
                    node.status = AvailabilityStatus.UNAVAILABLE
            elif node.last_heartbeat > 0 and (now - node.last_heartbeat) > _HEARTBEAT_STALE_S:
                node.status = AvailabilityStatus.UNAVAILABLE

            results[rid] = node.status

        return results

    def select(
        self,
        required: RuntimeCapability,
        prefer_class: RuntimeClass | None = None,
        exclude: set[str] | None = None,
    ) -> list[RuntimeNode]:
        """Select runtimes capable of the required capability, ranked by score.

        Returns a ranked list (best first). Caller walks the list as a
        fallback chain: try the first, if it fails try the next.
        """
        exclude = exclude or set()
        candidates = [
            node
            for node in self._nodes.values()
            if required in node.capabilities
            and node.is_available
            and node.runtime_id not in exclude
        ]

        if prefer_class is not None:
            preferred = [n for n in candidates if n.runtime_class == prefer_class]
            others = [n for n in candidates if n.runtime_class != prefer_class]
            preferred.sort(key=lambda n: n.score(), reverse=True)
            others.sort(key=lambda n: n.score(), reverse=True)
            return preferred + others

        candidates.sort(key=lambda n: n.score(), reverse=True)
        return candidates

    def route_and_execute(
        self,
        prompt: str,
        required: RuntimeCapability,
        prefer_class: RuntimeClass | None = None,
        **kwargs: Any,
    ) -> RuntimeResult | None:
        """Select best runtime and execute. Falls through chain on failure."""
        chain = self.select(required, prefer_class=prefer_class)

        if not chain:
            logger.warning(
                "no available runtime for capability=%s",
                required.value,
            )
            return None

        for node in chain:
            if node.adapter is None:
                continue

            start_ms = time.monotonic_ns() // 1_000_000
            try:
                result = node.adapter.execute(prompt, **kwargs)
                elapsed = (time.monotonic_ns() // 1_000_000) - start_ms

                if result is not None:
                    self.record_success(node.runtime_id, elapsed)
                    logger.info(
                        "runtime %s executed in %dms",
                        node.runtime_id,
                        elapsed,
                    )
                    return result

                logger.info("runtime %s returned empty", node.runtime_id)
                self.record_failure(node.runtime_id)

            except Exception as e:
                elapsed = (time.monotonic_ns() // 1_000_000) - start_ms
                logger.warning(
                    "runtime %s failed (%dms): %s",
                    node.runtime_id,
                    elapsed,
                    e,
                )
                self.record_failure(node.runtime_id)

        logger.warning(
            "all runtimes exhausted for capability=%s",
            required.value,
        )
        return None

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def available_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.is_available)

    def all_nodes(self) -> list[RuntimeNode]:
        return list(self._nodes.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runtimes": self.node_count,
            "available": self.available_count,
            "runtimes": {rid: n.to_dict() for rid, n in self._nodes.items()},
        }
