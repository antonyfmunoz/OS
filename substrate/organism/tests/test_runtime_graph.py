"""Tests for RuntimeGraph — runtime registry, scoring, routing."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

import pytest
from typing import Any

from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    CostProfile,
    ReliabilityScore,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
    RuntimeNode,
    RuntimeResult,
)


class FakeAdapter:
    """Minimal adapter for testing."""

    def __init__(
        self,
        rid: str = "fake",
        rclass: RuntimeClass = RuntimeClass.AI_CLI,
        caps: frozenset[RuntimeCapability] | None = None,
        available: bool = True,
        output: str = "test output",
    ) -> None:
        self._rid = rid
        self._rclass = rclass
        self._caps = caps or frozenset({RuntimeCapability.REASON})
        self._available = available
        self._output = output

    @property
    def runtime_id(self) -> str:
        return self._rid

    @property
    def runtime_class(self) -> RuntimeClass:
        return self._rclass

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return self._caps

    def check_available(self) -> bool:
        return self._available

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        if not self._available:
            return None
        return RuntimeResult(
            output=self._output,
            runtime_id=self._rid,
            latency_ms=50,
        )


class TestRuntimeNode:
    def test_score_default(self):
        node = RuntimeNode(
            runtime_id="test",
            runtime_class=RuntimeClass.AI_CLI,
            capabilities=frozenset({RuntimeCapability.REASON}),
            status=AvailabilityStatus.AVAILABLE,
        )
        score = node.score()
        assert 0.0 < score <= 1.0

    def test_score_degraded_penalty(self):
        node_ok = RuntimeNode(
            runtime_id="ok",
            runtime_class=RuntimeClass.AI_CLI,
            capabilities=frozenset({RuntimeCapability.REASON}),
            status=AvailabilityStatus.AVAILABLE,
        )
        node_deg = RuntimeNode(
            runtime_id="deg",
            runtime_class=RuntimeClass.AI_CLI,
            capabilities=frozenset({RuntimeCapability.REASON}),
            status=AvailabilityStatus.DEGRADED,
        )
        assert node_ok.score() > node_deg.score()

    def test_score_subscription_beats_api(self):
        node_sub = RuntimeNode(
            runtime_id="sub",
            runtime_class=RuntimeClass.AI_CLI,
            capabilities=frozenset({RuntimeCapability.REASON}),
            status=AvailabilityStatus.AVAILABLE,
            cost=CostProfile(is_subscription=True),
        )
        node_api = RuntimeNode(
            runtime_id="api",
            runtime_class=RuntimeClass.AI_API,
            capabilities=frozenset({RuntimeCapability.REASON}),
            status=AvailabilityStatus.AVAILABLE,
            cost=CostProfile(cost_per_1k_input=0.01, cost_per_1k_output=0.03),
        )
        assert node_sub.score() > node_api.score()

    def test_is_available(self):
        node = RuntimeNode(
            runtime_id="t",
            runtime_class=RuntimeClass.AI_CLI,
            capabilities=frozenset(),
        )
        node.status = AvailabilityStatus.AVAILABLE
        assert node.is_available
        node.status = AvailabilityStatus.DEGRADED
        assert node.is_available
        node.status = AvailabilityStatus.UNAVAILABLE
        assert not node.is_available

    def test_to_dict(self):
        node = RuntimeNode(
            runtime_id="t",
            runtime_class=RuntimeClass.AI_CLI,
            capabilities=frozenset({RuntimeCapability.REASON}),
            status=AvailabilityStatus.AVAILABLE,
        )
        d = node.to_dict()
        assert d["runtime_id"] == "t"
        assert "score" in d
        assert "reliability" in d


class TestReliabilityScore:
    def test_default(self):
        r = ReliabilityScore()
        assert r.success_rate == 0.5
        assert r.avg_latency_ms == 10000.0

    def test_recording(self):
        r = ReliabilityScore()
        r.record_success(100)
        r.record_success(200)
        assert r.success_rate == 1.0
        assert r.avg_latency_ms == 150.0

    def test_failures(self):
        r = ReliabilityScore()
        r.record_success(100)
        r.record_failure()
        assert r.success_rate == 0.5


class TestRuntimeGraph:
    def test_register(self):
        graph = RuntimeGraph()
        node = graph.register("test", RuntimeClass.AI_CLI, frozenset({RuntimeCapability.REASON}))
        assert node.runtime_id == "test"
        assert graph.node_count == 1

    def test_unregister(self):
        graph = RuntimeGraph()
        graph.register("test", RuntimeClass.AI_CLI, frozenset())
        assert graph.unregister("test")
        assert graph.node_count == 0
        assert not graph.unregister("nonexistent")

    def test_select_by_capability(self):
        graph = RuntimeGraph()
        graph.register("code", RuntimeClass.AI_CLI, frozenset({RuntimeCapability.CODE_WRITE}))
        graph.register("reason", RuntimeClass.AI_API, frozenset({RuntimeCapability.REASON}))

        graph.update_status("code", AvailabilityStatus.AVAILABLE)
        graph.update_status("reason", AvailabilityStatus.AVAILABLE)

        code_matches = graph.select(RuntimeCapability.CODE_WRITE)
        assert len(code_matches) == 1
        assert code_matches[0].runtime_id == "code"

        reason_matches = graph.select(RuntimeCapability.REASON)
        assert len(reason_matches) == 1

    def test_select_excludes_unavailable(self):
        graph = RuntimeGraph()
        graph.register("a", RuntimeClass.AI_CLI, frozenset({RuntimeCapability.REASON}))
        graph.register("b", RuntimeClass.AI_CLI, frozenset({RuntimeCapability.REASON}))

        graph.update_status("a", AvailabilityStatus.AVAILABLE)
        graph.update_status("b", AvailabilityStatus.UNAVAILABLE)

        matches = graph.select(RuntimeCapability.REASON)
        assert len(matches) == 1
        assert matches[0].runtime_id == "a"

    def test_select_with_exclude_set(self):
        graph = RuntimeGraph()
        graph.register("a", RuntimeClass.AI_CLI, frozenset({RuntimeCapability.REASON}))
        graph.register("b", RuntimeClass.AI_CLI, frozenset({RuntimeCapability.REASON}))

        graph.update_status("a", AvailabilityStatus.AVAILABLE)
        graph.update_status("b", AvailabilityStatus.AVAILABLE)

        matches = graph.select(RuntimeCapability.REASON, exclude={"a"})
        assert len(matches) == 1
        assert matches[0].runtime_id == "b"

    def test_select_prefer_class(self):
        graph = RuntimeGraph()
        graph.register("cli", RuntimeClass.AI_CLI, frozenset({RuntimeCapability.REASON}))
        graph.register("api", RuntimeClass.AI_API, frozenset({RuntimeCapability.REASON}))

        graph.update_status("cli", AvailabilityStatus.AVAILABLE)
        graph.update_status("api", AvailabilityStatus.AVAILABLE)

        matches = graph.select(RuntimeCapability.REASON, prefer_class=RuntimeClass.AI_API)
        assert matches[0].runtime_id == "api"

    def test_record_success_updates_reliability(self):
        graph = RuntimeGraph()
        graph.register("t", RuntimeClass.AI_CLI, frozenset())
        graph.record_success("t", 100)
        node = graph.get("t")
        assert node is not None
        assert node.reliability.successes == 1

    def test_record_failure_marks_unavailable(self):
        graph = RuntimeGraph()
        graph.register("t", RuntimeClass.AI_CLI, frozenset())
        graph.update_status("t", AvailabilityStatus.AVAILABLE)
        for _ in range(10):
            graph.record_failure("t")
        node = graph.get("t")
        assert node is not None
        assert node.status == AvailabilityStatus.UNAVAILABLE

    def test_route_and_execute(self):
        graph = RuntimeGraph()
        adapter = FakeAdapter(rid="fast", output="hello world")
        graph.register(
            "fast",
            RuntimeClass.AI_CLI,
            frozenset({RuntimeCapability.REASON}),
            adapter=adapter,
        )
        graph.update_status("fast", AvailabilityStatus.AVAILABLE)

        result = graph.route_and_execute("test prompt", RuntimeCapability.REASON)
        assert result is not None
        assert result.output == "hello world"
        assert result.runtime_id == "fast"

    def test_route_and_execute_fallback(self):
        graph = RuntimeGraph()

        broken = FakeAdapter(rid="broken", available=False)
        graph.register(
            "broken",
            RuntimeClass.AI_CLI,
            frozenset({RuntimeCapability.REASON}),
            adapter=broken,
        )
        graph.update_status("broken", AvailabilityStatus.AVAILABLE)

        good = FakeAdapter(rid="good", output="fallback result")
        graph.register(
            "good",
            RuntimeClass.AI_CLI,
            frozenset({RuntimeCapability.REASON}),
            adapter=good,
        )
        graph.update_status("good", AvailabilityStatus.AVAILABLE)

        result = graph.route_and_execute("test", RuntimeCapability.REASON)
        assert result is not None
        assert result.runtime_id == "good"

    def test_route_and_execute_no_runtimes(self):
        graph = RuntimeGraph()
        result = graph.route_and_execute("test", RuntimeCapability.GPU_COMPUTE)
        assert result is None

    def test_refresh_availability(self):
        graph = RuntimeGraph()
        adapter = FakeAdapter(rid="t", available=True)
        graph.register("t", RuntimeClass.AI_CLI, frozenset(), adapter=adapter)
        results = graph.refresh_availability()
        assert results["t"] == AvailabilityStatus.AVAILABLE

    def test_to_dict(self):
        graph = RuntimeGraph()
        graph.register("t", RuntimeClass.AI_CLI, frozenset({RuntimeCapability.REASON}))
        d = graph.to_dict()
        assert d["total_runtimes"] == 1
        assert "t" in d["runtimes"]
