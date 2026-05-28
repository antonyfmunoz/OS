"""Tests for Mission — user conversation to organism execution bridge."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/anti-divergence-gate")

import tempfile
from typing import Any

from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    CostProfile,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
    RuntimeResult,
)
from substrate.organism.coordinator import OrganismCoordinator, ObjectiveStatus
from substrate.organism.mission import (
    Mission,
    MissionResult,
    MissionStatus,
    execute_mission,
    mission_from_user_intent,
    synthesize_mission_result,
)


class FakeAdapter:
    def __init__(self, rid: str = "fake", output: str = "done") -> None:
        self._rid = rid
        self._output = output

    @property
    def runtime_id(self) -> str:
        return self._rid

    @property
    def runtime_class(self) -> RuntimeClass:
        return RuntimeClass.AI_CLI

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        return frozenset(
            {
                RuntimeCapability.REASON,
                RuntimeCapability.CODE_WRITE,
                RuntimeCapability.CODE_REVIEW,
                RuntimeCapability.RESEARCH,
                RuntimeCapability.SHELL,
            }
        )

    def check_available(self) -> bool:
        return True

    def execute(self, prompt: str, **kwargs: Any) -> RuntimeResult | None:
        return RuntimeResult(output=self._output, runtime_id=self._rid, latency_ms=10)


def _make_coordinator(output: str = "done") -> OrganismCoordinator:
    graph = RuntimeGraph()
    adapter = FakeAdapter(output=output)
    graph.register(
        "fake",
        RuntimeClass.AI_CLI,
        adapter.capabilities,
        cost=CostProfile(is_subscription=True),
        adapter=adapter,
    )
    graph.update_status("fake", AvailabilityStatus.AVAILABLE)
    return OrganismCoordinator(graph, state_dir=tempfile.mkdtemp())


class TestMissionFromUserIntent:
    def test_basic_intent(self):
        mission = mission_from_user_intent("research the competitors")
        assert mission.id.startswith("mission-")
        assert mission.user_intent == "research the competitors"
        assert mission.status == MissionStatus.PENDING
        assert len(mission.work_units) == 1
        assert mission.work_units[0]["type"] == "research"

    def test_build_intent(self):
        mission = mission_from_user_intent("build a new dashboard")
        assert mission.work_units[0]["type"] == "build"

    def test_deploy_intent(self):
        mission = mission_from_user_intent("deploy to production")
        assert mission.work_units[0]["type"] == "execute"

    def test_custom_title(self):
        mission = mission_from_user_intent("do something", title="Custom Title")
        assert mission.title == "Custom Title"

    def test_explicit_work_units(self):
        units = [
            {"title": "Research", "type": "research"},
            {"title": "Build", "type": "build", "blocked_by": ["Research"]},
        ]
        mission = mission_from_user_intent("complex task", work_units=units)
        assert len(mission.work_units) == 2
        assert mission.work_units[0]["type"] == "research"
        assert mission.work_units[1]["type"] == "build"

    def test_metadata_passthrough(self):
        mission = mission_from_user_intent("test", metadata={"source": "discord"})
        assert mission.metadata["source"] == "discord"

    def test_title_extracted_from_first_line(self):
        mission = mission_from_user_intent("first line\nsecond line\nthird")
        assert mission.title == "first line"


class TestMission:
    def test_auto_id(self):
        m = Mission(user_intent="test")
        assert m.id.startswith("mission-")
        assert m.created_at > 0

    def test_to_dict(self):
        m = Mission(user_intent="test", title="Test Mission")
        d = m.to_dict()
        assert d["title"] == "Test Mission"
        assert d["status"] == "pending"
        assert d["result"] is None


class TestMissionResult:
    def test_to_dict(self):
        r = MissionResult(
            mission_id="m1",
            status=MissionStatus.COMPLETED,
            summary="done",
            completion_rate=1.0,
            runtimes_used=["cc_sdk"],
        )
        d = r.to_dict()
        assert d["status"] == "completed"
        assert d["completion_rate"] == 1.0
        assert "cc_sdk" in d["runtimes_used"]


class TestExecuteMission:
    def test_successful_execution(self):
        coord = _make_coordinator(output="result text")
        mission = mission_from_user_intent("build a widget")
        result = execute_mission(mission, coord)

        assert result.status == MissionStatus.COMPLETED
        assert result.completion_rate == 1.0
        assert result.duration_ms >= 0
        assert mission.objective_id != ""
        assert mission.status == MissionStatus.COMPLETED

    def test_multi_step_execution(self):
        coord = _make_coordinator()
        units = [
            {"title": "Research phase", "type": "research"},
            {"title": "Build phase", "type": "build"},
        ]
        mission = mission_from_user_intent("full project", work_units=units)
        result = execute_mission(mission, coord)

        assert result.status == MissionStatus.COMPLETED
        assert result.completion_rate == 1.0

    def test_with_dependencies(self):
        coord = _make_coordinator()
        units = [
            {"title": "Step 1", "type": "research"},
            {"title": "Step 2", "type": "build", "blocked_by": ["Step 1"]},
            {"title": "Step 3", "type": "review", "blocked_by": ["Step 2"]},
        ]
        mission = mission_from_user_intent("phased project", work_units=units)
        result = execute_mission(mission, coord)

        assert result.status == MissionStatus.COMPLETED
        assert result.completion_rate == 1.0


class TestSynthesizeMissionResult:
    def test_completed(self):
        mission = Mission(user_intent="test", title="Test")
        mission.objective_id = "obj-123"
        coord_result = {
            "objective_id": "obj-123",
            "status": "completed",
            "completion_rate": 1.0,
            "work_units": 2,
            "results": [
                {"status": "completed", "runtime": "cc_sdk"},
                {"status": "completed", "runtime": "cc_sdk"},
            ],
        }
        result = synthesize_mission_result(mission, coord_result, duration_ms=500)
        assert result.status == MissionStatus.COMPLETED
        assert "2/2" in result.summary
        assert result.duration_ms == 500

    def test_partial(self):
        mission = Mission(user_intent="test", title="Test")
        coord_result = {
            "status": "partial",
            "completion_rate": 0.5,
            "work_units": 2,
            "results": [
                {"status": "completed", "runtime": "cc_sdk"},
                {"status": "failed", "error": "timeout"},
            ],
        }
        result = synthesize_mission_result(mission, coord_result)
        assert result.status == MissionStatus.PARTIAL
        assert "1/2" in result.summary

    def test_failed(self):
        mission = Mission(user_intent="test", title="Test")
        coord_result = {
            "status": "failed",
            "completion_rate": 0.0,
            "work_units": 1,
            "results": [{"status": "failed"}],
        }
        result = synthesize_mission_result(mission, coord_result)
        assert result.status == MissionStatus.FAILED

    def test_runtime_deduplication(self):
        mission = Mission(user_intent="test", title="Test")
        coord_result = {
            "status": "completed",
            "completion_rate": 1.0,
            "work_units": 3,
            "results": [
                {"status": "completed", "runtime": "cc_sdk"},
                {"status": "completed", "runtime": "gemini"},
                {"status": "completed", "runtime": "cc_sdk"},
            ],
        }
        result = synthesize_mission_result(mission, coord_result)
        assert len(result.runtimes_used) == 2
        assert "cc_sdk" in result.runtimes_used
        assert "gemini" in result.runtimes_used
