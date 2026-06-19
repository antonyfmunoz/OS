"""Tests for Campaign 22.2 — Production Workforce Runtime.

Self-contained fakes, no conftest. Verifies role-based assignment,
authority constraints, org chart, delegation feasibility, and progress.
"""

from __future__ import annotations

import sys
import time
import unittest
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, "/opt/OS")

from substrate.organism.production_workforce_runtime import (
    ProductionAssignment,
    ProductionAuthority,
    ProductionProgress,
    ProductionRole,
    ProductionWorkforceRuntime,
    _DISCIPLINE_ROLE,
    _ROLE_AUTHORITY,
    _ROLE_RANK,
)


# ── Fakes ────────────────────────────────────────────────────────


@dataclass
class FakeFleetAssignment:
    agent_type: str = "developer"
    agent_label: str = "dev-agent"
    compute_node_id: str = "node-1"
    rationale: dict[str, Any] = field(default_factory=lambda: {
        "capability_score": 0.9,
        "reliability_score": 0.8,
        "summary": "best match",
    })

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "agent_label": self.agent_label,
            "compute_node_id": self.compute_node_id,
            "rationale": self.rationale,
        }


class FakeAgentFleetRuntime:
    def __init__(self, assignments: list[FakeFleetAssignment] | None = None) -> None:
        self._assignments = list(assignments or [FakeFleetAssignment()])
        self._idx = 0

    def assign(
        self,
        capabilities_required: list[str] | None = None,
        risk_class: str = "low",
        domain: str = "",
        description: str = "",
    ) -> FakeFleetAssignment:
        if self._assignments:
            result = self._assignments[self._idx % len(self._assignments)]
            self._idx += 1
            return result
        return FakeFleetAssignment()


class FakeAgentWorkforceRuntime:
    def __init__(self, idle: list[dict[str, Any]] | None = None,
                 overloaded: list[dict[str, Any]] | None = None) -> None:
        self._idle = idle or []
        self._overloaded = overloaded or []

    def idle(self) -> list[dict[str, Any]]:
        return self._idle

    def overloaded(self) -> list[dict[str, Any]]:
        return self._overloaded

    def health(self) -> str:
        return "active"


@dataclass
class FakePlan:
    status: str = "assigned"


class FakeExecutionCoordinator:
    def __init__(self, statuses: dict[str, str] | None = None) -> None:
        self._statuses = statuses or {}

    def plans_by_workpacket(self, wp_id: str) -> list[FakePlan]:
        status = self._statuses.get(wp_id, "assigned")
        return [FakePlan(status=status)]

    def queue_depth(self) -> int:
        return 0


@dataclass
class FakeDelegationResult:
    delegatable: bool = True
    success_probability: float = 0.85
    risk_factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "delegatable": self.delegatable,
            "success_probability": self.success_probability,
            "risk_factors": self.risk_factors,
        }


class FakeDelegationReadinessRuntime:
    def __init__(self, result: FakeDelegationResult | None = None) -> None:
        self._result = result or FakeDelegationResult()

    def assess(self, work_id: str) -> FakeDelegationResult:
        return self._result


def _make_packets(disciplines: list[str], project: str = "test-proj") -> list[dict[str, Any]]:
    return [
        {
            "packet_id": f"wp-{i}",
            "discipline": d,
            "goal": f"Implement {d}",
            "risk_class": "low",
        }
        for i, d in enumerate(disciplines)
    ]


def _make_runtime(**kwargs: Any) -> ProductionWorkforceRuntime:
    defaults: dict[str, Any] = {
        "agent_workforce": FakeAgentWorkforceRuntime(),
        "execution_coordinator": FakeExecutionCoordinator(),
        "agent_fleet": FakeAgentFleetRuntime(),
        "delegation_readiness": FakeDelegationReadinessRuntime(),
    }
    defaults.update(kwargs)
    return ProductionWorkforceRuntime(**defaults)


# ── Tests ────────────────────────────────────────────────────────


class TestProductionRoleEnum(unittest.TestCase):
    def test_all_roles_present(self) -> None:
        roles = {r.value for r in ProductionRole}
        assert "operator" in roles
        assert "director" in roles
        assert "architect" in roles
        assert "lead" in roles
        assert "reviewer" in roles
        assert "contributor" in roles

    def test_role_count(self) -> None:
        assert len(ProductionRole) == 6


class TestProductionAuthorityEnum(unittest.TestCase):
    def test_all_authorities_present(self) -> None:
        auths = {a.value for a in ProductionAuthority}
        assert "plan" in auths
        assert "implement" in auths
        assert "review" in auths
        assert "approve" in auths
        assert "ship" in auths
        assert "override" in auths

    def test_authority_count(self) -> None:
        assert len(ProductionAuthority) == 6


class TestRoleAuthorityMapping(unittest.TestCase):
    def test_operator_has_all_authorities(self) -> None:
        auths = _ROLE_AUTHORITY["operator"]
        for a in ProductionAuthority:
            assert a.value in auths, f"operator missing {a.value}"

    def test_contributor_can_only_implement(self) -> None:
        auths = _ROLE_AUTHORITY["contributor"]
        assert auths == ["implement"]

    def test_reviewer_can_only_review(self) -> None:
        auths = _ROLE_AUTHORITY["reviewer"]
        assert auths == ["review"]

    def test_director_can_approve_but_not_implement(self) -> None:
        auths = _ROLE_AUTHORITY["director"]
        assert "approve" in auths
        assert "implement" not in auths

    def test_architect_can_plan_and_review(self) -> None:
        auths = _ROLE_AUTHORITY["architect"]
        assert "plan" in auths
        assert "review" in auths
        assert "implement" not in auths
        assert "approve" not in auths

    def test_lead_can_plan_implement_review(self) -> None:
        auths = _ROLE_AUTHORITY["lead"]
        assert "plan" in auths
        assert "implement" in auths
        assert "review" in auths
        assert "approve" not in auths

    def test_override_is_operator_only(self) -> None:
        for role, auths in _ROLE_AUTHORITY.items():
            if role == "operator":
                assert "override" in auths
            else:
                assert "override" not in auths, f"{role} should not have override"


class TestRoleRank(unittest.TestCase):
    def test_operator_highest(self) -> None:
        assert _ROLE_RANK["operator"] > _ROLE_RANK["director"]

    def test_rank_ordering(self) -> None:
        assert _ROLE_RANK["operator"] > _ROLE_RANK["director"]
        assert _ROLE_RANK["director"] > _ROLE_RANK["architect"]
        assert _ROLE_RANK["architect"] > _ROLE_RANK["lead"]
        assert _ROLE_RANK["lead"] > _ROLE_RANK["reviewer"]
        assert _ROLE_RANK["reviewer"] > _ROLE_RANK["contributor"]


class TestStaticHelpers(unittest.TestCase):
    def test_authorities_for_role(self) -> None:
        auths = ProductionWorkforceRuntime.authorities_for_role("reviewer")
        assert auths == ["review"]

    def test_authorities_for_unknown_role(self) -> None:
        auths = ProductionWorkforceRuntime.authorities_for_role("alien")
        assert auths == []

    def test_role_has_authority_true(self) -> None:
        assert ProductionWorkforceRuntime.role_has_authority("operator", "override")

    def test_role_has_authority_false(self) -> None:
        assert not ProductionWorkforceRuntime.role_has_authority("contributor", "approve")

    def test_role_rank(self) -> None:
        assert ProductionWorkforceRuntime.role_rank("operator") == 100
        assert ProductionWorkforceRuntime.role_rank("contributor") == 20


class TestRoleForDiscipline(unittest.TestCase):
    def test_architecture_gets_architect(self) -> None:
        assert ProductionWorkforceRuntime.role_for_discipline("architecture") == "architect"

    def test_implementation_gets_contributor(self) -> None:
        assert ProductionWorkforceRuntime.role_for_discipline("implementation") == "contributor"

    def test_review_gets_reviewer(self) -> None:
        assert ProductionWorkforceRuntime.role_for_discipline("review") == "reviewer"

    def test_security_gets_architect(self) -> None:
        assert ProductionWorkforceRuntime.role_for_discipline("security") == "architect"

    def test_deployment_gets_lead(self) -> None:
        assert ProductionWorkforceRuntime.role_for_discipline("deployment") == "lead"

    def test_unknown_gets_contributor(self) -> None:
        assert ProductionWorkforceRuntime.role_for_discipline("unknown_thing") == "contributor"


class TestAssignProductionWork(unittest.TestCase):
    def test_basic_assignment(self) -> None:
        rt = _make_runtime()
        packets = _make_packets(["implementation"])
        assignments = rt.assign_production_work(packets, "proj-1")
        assert len(assignments) == 1
        a = assignments[0]
        assert a.packet_id == "wp-0"
        assert a.project_id == "proj-1"
        assert a.role == "contributor"
        assert "implement" in a.authority

    def test_multi_discipline_assignment(self) -> None:
        rt = _make_runtime()
        packets = _make_packets(["architecture", "implementation", "testing", "review"])
        assignments = rt.assign_production_work(packets, "proj-multi")
        assert len(assignments) == 4
        roles = [a.role for a in assignments]
        assert "architect" in roles
        assert "contributor" in roles
        assert "reviewer" in roles

    def test_authority_matches_role(self) -> None:
        rt = _make_runtime()
        packets = _make_packets(["architecture", "review", "implementation"])
        assignments = rt.assign_production_work(packets)
        for a in assignments:
            expected = _ROLE_AUTHORITY.get(a.role, [])
            assert a.authority == expected

    def test_fleet_assignment_populates_agent(self) -> None:
        fleet = FakeAgentFleetRuntime([
            FakeFleetAssignment(agent_type="senior-dev", agent_label="SeniorDev-1"),
        ])
        rt = _make_runtime(agent_fleet=fleet)
        assignments = rt.assign_production_work(_make_packets(["implementation"]))
        assert assignments[0].agent_type == "senior-dev"
        assert assignments[0].agent_label == "SeniorDev-1"

    def test_no_fleet_uses_default_agent(self) -> None:
        rt = _make_runtime(agent_fleet=None)
        packets = _make_packets(["security"])
        assignments = rt.assign_production_work(packets)
        assert assignments[0].agent_type == "security-reviewer"

    def test_project_id_auto_generated(self) -> None:
        rt = _make_runtime()
        assignments = rt.assign_production_work(_make_packets(["implementation"]))
        assert assignments[0].project_id.startswith("proj-")

    def test_assignments_tracked_internally(self) -> None:
        rt = _make_runtime()
        rt.assign_production_work(_make_packets(["implementation"]), "proj-x")
        assert len(rt._assignments) == 1
        assert "proj-x" in rt._project_assignments


class TestProductionAssignment(unittest.TestCase):
    def test_to_dict(self) -> None:
        a = ProductionAssignment(
            packet_id="wp-1",
            project_id="proj-1",
            role="contributor",
            agent_type="developer",
            authority=["implement"],
        )
        d = a.to_dict()
        assert d["packet_id"] == "wp-1"
        assert d["role"] == "contributor"
        assert d["authority"] == ["implement"]

    def test_assignment_id_generated(self) -> None:
        a = ProductionAssignment()
        assert a.assignment_id.startswith("pa-")


class TestWhoCanApprove(unittest.TestCase):
    def test_default_approvers(self) -> None:
        rt = _make_runtime()
        approvers = rt.who_can_approve()
        roles = [a["role"] for a in approvers]
        assert "operator" in roles
        assert "director" in roles
        assert "contributor" not in roles

    def test_approvers_sorted_by_rank(self) -> None:
        rt = _make_runtime()
        approvers = rt.who_can_approve()
        ranks = [_ROLE_RANK.get(a["role"], 0) for a in approvers]
        assert ranks == sorted(ranks, reverse=True)

    def test_approvers_for_specific_packet(self) -> None:
        rt = _make_runtime()
        packets = _make_packets(["architecture", "review"])
        rt.assign_production_work(packets, "proj-a")
        approvers = rt.who_can_approve("wp-0")
        # architect has no approve authority, so should fall back to defaults
        assert len(approvers) >= 1


class TestWhoCanShip(unittest.TestCase):
    def test_only_operator_can_ship(self) -> None:
        rt = _make_runtime()
        shippers = rt.who_can_ship()
        roles = [s["role"] for s in shippers]
        assert "operator" in roles
        assert "contributor" not in roles
        assert "reviewer" not in roles


class TestWhoIsIdleOverloaded(unittest.TestCase):
    def test_idle_agents(self) -> None:
        workforce = FakeAgentWorkforceRuntime(
            idle=[{"agent_type_id": "dev-1", "label": "Dev 1"}]
        )
        rt = _make_runtime(agent_workforce=workforce)
        idle = rt.who_is_idle()
        assert len(idle) == 1

    def test_overloaded_agents(self) -> None:
        workforce = FakeAgentWorkforceRuntime(
            overloaded=[{"agent_type_id": "dev-2", "label": "Dev 2", "active_count": 3}]
        )
        rt = _make_runtime(agent_workforce=workforce)
        overloaded = rt.who_is_overloaded()
        assert len(overloaded) == 1

    def test_no_workforce_returns_empty(self) -> None:
        class NoopWorkforce:
            def idle(self) -> list[dict[str, Any]]:
                return []
            def overloaded(self) -> list[dict[str, Any]]:
                return []
            def health(self) -> str:
                return "idle"

        rt = _make_runtime(agent_workforce=NoopWorkforce())
        assert rt.who_is_idle() == []
        assert rt.who_is_overloaded() == []


class TestProductionProgress(unittest.TestCase):
    def test_basic_progress(self) -> None:
        rt = _make_runtime()
        rt.assign_production_work(
            _make_packets(["architecture", "implementation", "testing"]),
            "proj-prog",
        )
        progress = rt.production_progress("proj-prog")
        assert progress.total_packets == 3
        assert progress.project_id == "proj-prog"
        assert "architect" in progress.by_role
        assert "contributor" in progress.by_role
        assert progress.concurrent_projects >= 1

    def test_progress_to_dict(self) -> None:
        p = ProductionProgress(
            project_id="p1",
            total_packets=5,
            by_role={"contributor": 3, "architect": 2},
        )
        d = p.to_dict()
        assert d["total_packets"] == 5
        assert d["by_role"]["contributor"] == 3

    def test_all_projects_progress(self) -> None:
        rt = _make_runtime()
        rt.assign_production_work(_make_packets(["implementation"]), "proj-a")
        rt.assign_production_work(_make_packets(["testing"]), "proj-b")
        progress = rt.production_progress()
        assert progress.total_packets == 2
        assert progress.concurrent_projects == 2

    def test_packet_status_from_coordinator(self) -> None:
        coord = FakeExecutionCoordinator(statuses={"wp-0": "executing"})
        rt = _make_runtime(execution_coordinator=coord)
        rt.assign_production_work(_make_packets(["implementation"]), "proj-s")
        progress = rt.production_progress("proj-s")
        assert "executing" in progress.by_status


class TestOrgChart(unittest.TestCase):
    def test_basic_org_chart(self) -> None:
        rt = _make_runtime()
        rt.assign_production_work(
            _make_packets(["architecture", "implementation", "review"]),
            "proj-org",
        )
        chart = rt.org_chart("proj-org")
        assert chart["project_id"] == "proj-org"
        assert chart["total_assignments"] == 3
        assert "root" in chart
        root = chart["root"]
        assert root["role"] == "operator"

    def test_org_chart_has_roles_active(self) -> None:
        rt = _make_runtime()
        rt.assign_production_work(
            _make_packets(["architecture", "security", "implementation"]),
            "proj-roles",
        )
        chart = rt.org_chart("proj-roles")
        assert "architect" in chart["roles_active"]
        assert "contributor" in chart["roles_active"]

    def test_empty_chart(self) -> None:
        rt = _make_runtime()
        chart = rt.org_chart("nonexistent")
        assert chart["total_assignments"] == 0
        assert chart["root"]["role"] == "operator"


class TestDelegationFeasibility(unittest.TestCase):
    def test_delegatable(self) -> None:
        rt = _make_runtime()
        result = rt.delegation_feasibility("wp-0")
        assert result["delegatable"] is True

    def test_not_delegatable(self) -> None:
        dr = FakeDelegationReadinessRuntime(
            FakeDelegationResult(delegatable=False, risk_factors=["too risky"])
        )
        rt = _make_runtime(delegation_readiness=dr)
        result = rt.delegation_feasibility("wp-0")
        assert result["delegatable"] is False

    def test_no_delegation_runtime(self) -> None:
        class FailingDelegation:
            def assess(self, work_id: str) -> None:
                raise RuntimeError("unavailable")

        rt = _make_runtime(delegation_readiness=FailingDelegation())
        result = rt.delegation_feasibility("wp-0")
        assert result["delegatable"] is True


class TestLookupHelpers(unittest.TestCase):
    def test_get_assignment(self) -> None:
        rt = _make_runtime()
        assignments = rt.assign_production_work(_make_packets(["implementation"]), "proj-l")
        found = rt.get_assignment(assignments[0].assignment_id)
        assert found is not None
        assert found.packet_id == "wp-0"

    def test_get_missing_assignment(self) -> None:
        rt = _make_runtime()
        assert rt.get_assignment("nonexistent") is None

    def test_assignments_for_project(self) -> None:
        rt = _make_runtime()
        rt.assign_production_work(_make_packets(["implementation", "testing"]), "proj-f")
        found = rt.assignments_for_project("proj-f")
        assert len(found) == 2

    def test_all_projects(self) -> None:
        rt = _make_runtime()
        rt.assign_production_work(_make_packets(["implementation"]), "proj-a")
        rt.assign_production_work(_make_packets(["testing"]), "proj-b")
        projects = rt.all_projects()
        assert "proj-a" in projects
        assert "proj-b" in projects


class TestSummary(unittest.TestCase):
    def test_summary_structure(self) -> None:
        rt = _make_runtime()
        rt.assign_production_work(
            _make_packets(["architecture", "implementation"]),
            "proj-sum",
        )
        s = rt.summary()
        assert s["ok"] is True
        assert s["total_assignments"] == 2
        assert s["total_projects"] == 1
        assert "by_role" in s
        assert "workforce_health" in s
        assert "generated_at" in s

    def test_summary_empty(self) -> None:
        rt = _make_runtime()
        s = rt.summary()
        assert s["total_assignments"] == 0
        assert s["total_projects"] == 0

    def test_summary_role_hierarchy(self) -> None:
        rt = _make_runtime()
        s = rt.summary()
        assert "role_hierarchy" in s
        assert "operator" in s["role_hierarchy"]


class TestEdgeCases(unittest.TestCase):
    def test_fleet_assign_failure(self) -> None:
        class FailingFleet:
            def assign(self, **kwargs: Any) -> None:
                raise RuntimeError("fleet down")

        rt = _make_runtime(agent_fleet=FailingFleet())
        packets = _make_packets(["implementation"])
        assignments = rt.assign_production_work(packets)
        assert len(assignments) == 1
        assert assignments[0].agent_type == "developer"

    def test_concurrent_projects(self) -> None:
        rt = _make_runtime()
        rt.assign_production_work(_make_packets(["implementation"]), "p1")
        rt.assign_production_work(_make_packets(["architecture"]), "p2")
        rt.assign_production_work(_make_packets(["testing"]), "p3")
        progress = rt.production_progress()
        assert progress.concurrent_projects == 3

    def test_full_lifecycle_disciplines(self) -> None:
        rt = _make_runtime()
        all_disciplines = [
            "architecture", "implementation", "testing", "security",
            "observability", "deployment", "review", "documentation", "recovery",
        ]
        assignments = rt.assign_production_work(
            _make_packets(all_disciplines), "proj-full"
        )
        assert len(assignments) == 9
        roles = {a.role for a in assignments}
        assert "architect" in roles
        assert "contributor" in roles
        assert "lead" in roles
        assert "reviewer" in roles


if __name__ == "__main__":
    unittest.main()
