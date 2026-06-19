"""Production Workforce Runtime — Campaign 22.2.

Connects workforce to production work with organizational authority.
Who should do this? With what authority? Who reviews? Who approves shipping?

Composes AgentWorkforceRuntime + ExecutionCoordinator + AgentFleetRuntime +
DelegationReadinessRuntime into a role-based production workforce.

Role hierarchy: OPERATOR > DIRECTOR > ARCHITECT > LEAD > REVIEWER > CONTRIBUTOR.
Each role has explicit authority bounds. A contributor can implement but not
approve. A reviewer can review but not ship. The operator overrides everything.

C22 substrate organism subsystem. Instance-agnostic. Deterministic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ProductionRole(str, Enum):
    """Organizational hierarchy for software production.

    Mirrors real org structure: Director -> Lead -> IC.
    """

    OPERATOR = "operator"
    DIRECTOR = "director"
    ARCHITECT = "architect"
    LEAD = "lead"
    REVIEWER = "reviewer"
    CONTRIBUTOR = "contributor"


class ProductionAuthority(str, Enum):
    """What each role can do without escalation."""

    PLAN = "plan"
    IMPLEMENT = "implement"
    REVIEW = "review"
    APPROVE = "approve"
    SHIP = "ship"
    OVERRIDE = "override"


# ── Static authority mapping ─────────────────────────────────────

_ROLE_AUTHORITY: dict[str, list[str]] = {
    ProductionRole.OPERATOR.value: [
        ProductionAuthority.PLAN.value,
        ProductionAuthority.IMPLEMENT.value,
        ProductionAuthority.REVIEW.value,
        ProductionAuthority.APPROVE.value,
        ProductionAuthority.SHIP.value,
        ProductionAuthority.OVERRIDE.value,
    ],
    ProductionRole.DIRECTOR.value: [
        ProductionAuthority.PLAN.value,
        ProductionAuthority.REVIEW.value,
        ProductionAuthority.APPROVE.value,
    ],
    ProductionRole.ARCHITECT.value: [
        ProductionAuthority.PLAN.value,
        ProductionAuthority.REVIEW.value,
    ],
    ProductionRole.LEAD.value: [
        ProductionAuthority.PLAN.value,
        ProductionAuthority.IMPLEMENT.value,
        ProductionAuthority.REVIEW.value,
    ],
    ProductionRole.REVIEWER.value: [
        ProductionAuthority.REVIEW.value,
    ],
    ProductionRole.CONTRIBUTOR.value: [
        ProductionAuthority.IMPLEMENT.value,
    ],
}

_ROLE_RANK: dict[str, int] = {
    ProductionRole.OPERATOR.value: 100,
    ProductionRole.DIRECTOR.value: 80,
    ProductionRole.ARCHITECT.value: 70,
    ProductionRole.LEAD.value: 60,
    ProductionRole.REVIEWER.value: 40,
    ProductionRole.CONTRIBUTOR.value: 20,
}

# ── Discipline -> default role mapping ───────────────────────────

_DISCIPLINE_ROLE: dict[str, str] = {
    "architecture": ProductionRole.ARCHITECT.value,
    "implementation": ProductionRole.CONTRIBUTOR.value,
    "testing": ProductionRole.CONTRIBUTOR.value,
    "security": ProductionRole.ARCHITECT.value,
    "observability": ProductionRole.LEAD.value,
    "deployment": ProductionRole.LEAD.value,
    "review": ProductionRole.REVIEWER.value,
    "documentation": ProductionRole.CONTRIBUTOR.value,
    "recovery": ProductionRole.ARCHITECT.value,
    "analysis": ProductionRole.ARCHITECT.value,
    "verification": ProductionRole.REVIEWER.value,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ProductionAssignment:
    """A work packet assigned to an agent with a production role."""

    assignment_id: str = field(default_factory=lambda: f"pa-{uuid4().hex[:8]}")
    packet_id: str = ""
    project_id: str = ""
    role: str = ProductionRole.CONTRIBUTOR.value
    agent_type: str = ""
    agent_label: str = ""
    assignment_rationale: dict[str, Any] = field(default_factory=dict)
    authority: list[str] = field(default_factory=list)
    compute_node: str = ""
    discipline: str = ""
    assigned_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignment_id": self.assignment_id,
            "packet_id": self.packet_id,
            "project_id": self.project_id,
            "role": self.role,
            "agent_type": self.agent_type,
            "agent_label": self.agent_label,
            "assignment_rationale": dict(self.assignment_rationale),
            "authority": list(self.authority),
            "compute_node": self.compute_node,
            "discipline": self.discipline,
            "assigned_at": self.assigned_at,
        }


@dataclass
class ProductionProgress:
    """Progress across a production project's work packets."""

    project_id: str = ""
    total_packets: int = 0
    by_role: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    agents_involved: list[dict[str, Any]] = field(default_factory=list)
    concurrent_projects: int = 0
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "total_packets": self.total_packets,
            "by_role": dict(self.by_role),
            "by_status": dict(self.by_status),
            "agents_involved": list(self.agents_involved),
            "concurrent_projects": self.concurrent_projects,
            "generated_at": self.generated_at,
        }


@dataclass
class OrgChartNode:
    """One node in the production org chart."""

    role: str = ""
    agent_type: str = ""
    agent_label: str = ""
    authority: list[str] = field(default_factory=list)
    packet_count: int = 0
    subordinates: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "agent_type": self.agent_type,
            "agent_label": self.agent_label,
            "authority": list(self.authority),
            "packet_count": self.packet_count,
            "subordinates": list(self.subordinates),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ProductionWorkforceRuntime:
    """Role-based production workforce — composes 4 runtimes.

    Wraps AgentFleetRuntime.assign() with organizational authority
    constraints. Tracks assignments by project and role.
    """

    def __init__(
        self,
        agent_workforce: Any | None = None,
        execution_coordinator: Any | None = None,
        agent_fleet: Any | None = None,
        delegation_readiness: Any | None = None,
    ) -> None:
        self._agent_workforce = agent_workforce
        self._execution_coordinator = execution_coordinator
        self._agent_fleet = agent_fleet
        self._delegation_readiness = delegation_readiness
        self._assignments: dict[str, ProductionAssignment] = {}
        self._project_assignments: dict[str, list[str]] = {}

    # ── Lazy composition ─────────────────────────────────────────

    @property
    def _workforce(self) -> Any:
        if self._agent_workforce is None:
            try:
                from substrate.workstation.agent_workforce_runtime import (
                    AgentWorkforceRuntime,
                )
                self._agent_workforce = AgentWorkforceRuntime()
            except Exception:
                logger.debug("AgentWorkforceRuntime unavailable")
        return self._agent_workforce

    @property
    def _coordinator(self) -> Any:
        if self._execution_coordinator is None:
            try:
                from substrate.organism.execution_coordinator import (
                    get_execution_coordinator,
                )
                self._execution_coordinator = get_execution_coordinator()
            except Exception:
                logger.debug("ExecutionCoordinator unavailable")
        return self._execution_coordinator

    @property
    def _fleet(self) -> Any:
        if self._agent_fleet is None:
            try:
                from substrate.organism.agent_fleet_runtime import AgentFleetRuntime
                self._agent_fleet = AgentFleetRuntime(
                    capability_model=None,
                    compute_fabric=None,
                )
            except Exception:
                logger.debug("AgentFleetRuntime unavailable")
        return self._agent_fleet

    @property
    def _delegation(self) -> Any:
        if self._delegation_readiness is None:
            try:
                from substrate.organism.delegation_readiness_runtime import (
                    DelegationReadinessRuntime,
                )
                self._delegation_readiness = DelegationReadinessRuntime()
            except Exception:
                logger.debug("DelegationReadinessRuntime unavailable")
        return self._delegation_readiness

    # ── Helpers ──────────────────────────────────────────────────

    def _safe_call(self, obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
        if obj is None:
            return None
        fn = getattr(obj, method, None)
        if fn is None:
            return None
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.debug("ProductionWorkforceRuntime._safe_call(%s) failed: %s", method, exc)
            return None

    @staticmethod
    def authorities_for_role(role: str) -> list[str]:
        """Return the authority list for a given production role."""
        return list(_ROLE_AUTHORITY.get(role, []))

    @staticmethod
    def role_rank(role: str) -> int:
        """Return the numeric rank for a role (higher = more authority)."""
        return _ROLE_RANK.get(role, 0)

    @staticmethod
    def role_has_authority(role: str, authority: str) -> bool:
        """Check if a role has a specific authority."""
        return authority in _ROLE_AUTHORITY.get(role, [])

    # ── Core: Assign production work ─────────────────────────────

    def assign_production_work(
        self,
        packets: list[dict[str, Any]],
        project_id: str = "",
    ) -> list[ProductionAssignment]:
        """Assign work packets to agents with production roles.

        Wraps AgentFleetRuntime.assign() with role-based authority.
        Each packet gets a role based on its discipline, and the
        assignment inherits the authority bounds of that role.
        """
        assignments: list[ProductionAssignment] = []
        proj = project_id or f"proj-{uuid4().hex[:8]}"

        for packet in packets:
            packet_id = packet.get("packet_id", packet.get("id", f"wp-{uuid4().hex[:8]}"))
            discipline = packet.get("discipline", packet.get("type", "implementation"))
            goal = packet.get("goal", packet.get("title", ""))
            risk_class = packet.get("risk_class", "low")

            role = self.role_for_discipline(discipline)
            authority = self.authorities_for_role(role)

            fleet_assignment = self._try_fleet_assign(
                goal=goal,
                discipline=discipline,
                risk_class=risk_class,
            )

            agent_type = ""
            agent_label = ""
            compute_node = ""
            rationale: dict[str, Any] = {}

            if fleet_assignment is not None:
                if hasattr(fleet_assignment, "agent_type"):
                    agent_type = fleet_assignment.agent_type
                if hasattr(fleet_assignment, "agent_label"):
                    agent_label = fleet_assignment.agent_label
                if hasattr(fleet_assignment, "compute_node_id"):
                    compute_node = fleet_assignment.compute_node_id
                if hasattr(fleet_assignment, "rationale"):
                    rat = fleet_assignment.rationale
                    rationale = rat.to_dict() if hasattr(rat, "to_dict") else (
                        rat if isinstance(rat, dict) else {}
                    )

            assignment = ProductionAssignment(
                packet_id=packet_id,
                project_id=proj,
                role=role,
                agent_type=agent_type or self._default_agent_for_discipline(discipline),
                agent_label=agent_label or f"{role}-{discipline}",
                assignment_rationale=rationale,
                authority=authority,
                compute_node=compute_node,
                discipline=discipline,
            )

            self._assignments[assignment.assignment_id] = assignment
            self._project_assignments.setdefault(proj, []).append(assignment.assignment_id)
            assignments.append(assignment)

        logger.debug(
            "Assigned %d packets to project %s across %d roles",
            len(assignments),
            proj,
            len({a.role for a in assignments}),
        )
        return assignments

    def _try_fleet_assign(
        self,
        goal: str,
        discipline: str,
        risk_class: str,
    ) -> Any:
        """Attempt fleet assignment, return None on failure."""
        if self._fleet is None:
            return None
        try:
            return self._fleet.assign(
                capabilities_required=[discipline],
                risk_class=risk_class,
                domain="engineering",
                description=goal,
            )
        except Exception as exc:
            logger.debug("Fleet assign failed: %s", exc)
            return None

    @staticmethod
    def _default_agent_for_discipline(discipline: str) -> str:
        """Deterministic default agent type when fleet is unavailable."""
        mapping = {
            "architecture": "developer",
            "implementation": "developer",
            "testing": "developer",
            "security": "security-reviewer",
            "observability": "developer",
            "deployment": "devops",
            "review": "code-reviewer",
            "documentation": "developer",
            "recovery": "devops",
            "analysis": "developer",
            "verification": "verifier",
        }
        return mapping.get(discipline, "developer")

    # ── Role mapping ─────────────────────────────────────────────

    @staticmethod
    def role_for_discipline(discipline: str) -> str:
        """Determine the production role for a given discipline."""
        return _DISCIPLINE_ROLE.get(discipline, ProductionRole.CONTRIBUTOR.value)

    # ── Authority queries ────────────────────────────────────────

    def who_can_approve(self, packet_id: str = "") -> list[dict[str, Any]]:
        """Return roles/agents that have APPROVE authority.

        If packet_id is given, return from that packet's project.
        Otherwise, return all roles with approve authority.
        """
        approvers: list[dict[str, Any]] = []

        if packet_id:
            assignment = self._find_assignment_by_packet(packet_id)
            if assignment:
                proj_ids = self._project_assignments.get(assignment.project_id, [])
                seen_roles: set[str] = set()
                for aid in proj_ids:
                    a = self._assignments.get(aid)
                    if a and self.role_has_authority(a.role, ProductionAuthority.APPROVE.value):
                        if a.role not in seen_roles:
                            seen_roles.add(a.role)
                            approvers.append({
                                "role": a.role,
                                "agent_type": a.agent_type,
                                "agent_label": a.agent_label,
                                "authority": a.authority,
                            })

        if not approvers:
            for role, auths in _ROLE_AUTHORITY.items():
                if ProductionAuthority.APPROVE.value in auths:
                    approvers.append({
                        "role": role,
                        "authority": auths,
                    })

        return sorted(approvers, key=lambda x: -_ROLE_RANK.get(x.get("role", ""), 0))

    def who_can_ship(self) -> list[dict[str, Any]]:
        """Return roles that have SHIP authority."""
        shippers: list[dict[str, Any]] = []
        for role, auths in _ROLE_AUTHORITY.items():
            if ProductionAuthority.SHIP.value in auths:
                shippers.append({"role": role, "authority": auths})
        return sorted(shippers, key=lambda x: -_ROLE_RANK.get(x.get("role", ""), 0))

    def who_is_overloaded(self) -> list[dict[str, Any]]:
        """Return overloaded agents from workforce snapshot."""
        result = self._safe_call(self._workforce, "overloaded")
        if result and isinstance(result, list):
            return result
        return []

    def who_is_idle(self) -> list[dict[str, Any]]:
        """Return idle agents from workforce snapshot."""
        result = self._safe_call(self._workforce, "idle")
        if result and isinstance(result, list):
            return result
        return []

    # ── Progress tracking ────────────────────────────────────────

    def production_progress(self, project_id: str = "") -> ProductionProgress:
        """Progress report for a production project."""
        now = time.time()

        if project_id:
            proj_ids = [project_id]
        else:
            proj_ids = list(self._project_assignments.keys())

        by_role: dict[str, int] = {}
        by_status: dict[str, int] = {}
        agents_involved: list[dict[str, Any]] = []
        total_packets = 0
        seen_agents: set[str] = set()

        for pid in proj_ids:
            assignment_ids = self._project_assignments.get(pid, [])
            for aid in assignment_ids:
                a = self._assignments.get(aid)
                if a is None:
                    continue

                total_packets += 1
                by_role[a.role] = by_role.get(a.role, 0) + 1

                status = self._get_packet_status(a.packet_id)
                by_status[status] = by_status.get(status, 0) + 1

                agent_key = f"{a.agent_type}:{a.role}"
                if agent_key not in seen_agents:
                    seen_agents.add(agent_key)
                    agents_involved.append({
                        "agent_type": a.agent_type,
                        "agent_label": a.agent_label,
                        "role": a.role,
                        "packet_count": sum(
                            1 for x in assignment_ids
                            if self._assignments.get(x) and
                            self._assignments[x].agent_type == a.agent_type
                        ),
                    })

        return ProductionProgress(
            project_id=project_id or "all",
            total_packets=total_packets,
            by_role=by_role,
            by_status=by_status,
            agents_involved=agents_involved,
            concurrent_projects=len(self._project_assignments),
            generated_at=now,
        )

    def _get_packet_status(self, packet_id: str) -> str:
        """Get packet execution status from coordinator."""
        if self._coordinator is None:
            return "assigned"
        plans = self._safe_call(self._coordinator, "plans_by_workpacket", packet_id)
        if plans and isinstance(plans, list) and len(plans) > 0:
            plan = plans[-1]
            if hasattr(plan, "status"):
                return plan.status if isinstance(plan.status, str) else plan.status.value
        return "assigned"

    # ── Org chart ────────────────────────────────────────────────

    def org_chart(self, project_id: str = "") -> dict[str, Any]:
        """Build an org chart for the production project.

        Returns a tree: operator at root, roles nested by authority rank.
        """
        if project_id:
            assignment_ids = self._project_assignments.get(project_id, [])
        else:
            assignment_ids = list(self._assignments.keys())

        role_agents: dict[str, list[ProductionAssignment]] = {}
        for aid in assignment_ids:
            a = self._assignments.get(aid)
            if a is not None:
                role_agents.setdefault(a.role, []).append(a)

        operator_node = OrgChartNode(
            role=ProductionRole.OPERATOR.value,
            agent_type="human",
            agent_label="operator",
            authority=_ROLE_AUTHORITY[ProductionRole.OPERATOR.value],
        )

        director_nodes: list[dict[str, Any]] = []
        for a in role_agents.get(ProductionRole.DIRECTOR.value, []):
            director_nodes.append(OrgChartNode(
                role=a.role,
                agent_type=a.agent_type,
                agent_label=a.agent_label,
                authority=a.authority,
                packet_count=1,
            ).to_dict())

        architect_nodes: list[dict[str, Any]] = []
        for a in role_agents.get(ProductionRole.ARCHITECT.value, []):
            architect_nodes.append(OrgChartNode(
                role=a.role,
                agent_type=a.agent_type,
                agent_label=a.agent_label,
                authority=a.authority,
                packet_count=1,
            ).to_dict())

        lead_nodes: list[dict[str, Any]] = []
        for a in role_agents.get(ProductionRole.LEAD.value, []):
            lead_nodes.append(OrgChartNode(
                role=a.role,
                agent_type=a.agent_type,
                agent_label=a.agent_label,
                authority=a.authority,
                packet_count=1,
            ).to_dict())

        reviewer_nodes: list[dict[str, Any]] = []
        for a in role_agents.get(ProductionRole.REVIEWER.value, []):
            reviewer_nodes.append(OrgChartNode(
                role=a.role,
                agent_type=a.agent_type,
                agent_label=a.agent_label,
                authority=a.authority,
                packet_count=1,
            ).to_dict())

        contributor_nodes: list[dict[str, Any]] = []
        for a in role_agents.get(ProductionRole.CONTRIBUTOR.value, []):
            contributor_nodes.append(OrgChartNode(
                role=a.role,
                agent_type=a.agent_type,
                agent_label=a.agent_label,
                authority=a.authority,
                packet_count=1,
            ).to_dict())

        # Nest: contributors under leads, leads under architects,
        # architects under directors, directors under operator
        for lead in lead_nodes:
            lead["subordinates"] = list(contributor_nodes)
        for architect in architect_nodes:
            architect["subordinates"] = list(lead_nodes) + list(reviewer_nodes)
        for director in director_nodes:
            director["subordinates"] = list(architect_nodes)

        operator_node.subordinates = director_nodes if director_nodes else architect_nodes

        return {
            "project_id": project_id or "all",
            "root": operator_node.to_dict(),
            "total_assignments": len(assignment_ids),
            "roles_active": sorted(role_agents.keys()),
        }

    # ── Delegation feasibility ───────────────────────────────────

    def delegation_feasibility(self, packet_id: str) -> dict[str, Any]:
        """Check if a packet can be delegated to an agent."""
        result = self._safe_call(self._delegation, "assess", packet_id)
        if result is not None:
            return result.to_dict() if hasattr(result, "to_dict") else (
                result if isinstance(result, dict) else {"delegatable": False}
            )
        return {
            "delegatable": True,
            "reason": "delegation readiness unavailable, defaulting to delegatable",
        }

    # ── Lookup helpers ───────────────────────────────────────────

    def _find_assignment_by_packet(self, packet_id: str) -> ProductionAssignment | None:
        for a in self._assignments.values():
            if a.packet_id == packet_id:
                return a
        return None

    def get_assignment(self, assignment_id: str) -> ProductionAssignment | None:
        return self._assignments.get(assignment_id)

    def assignments_for_project(self, project_id: str) -> list[ProductionAssignment]:
        ids = self._project_assignments.get(project_id, [])
        return [self._assignments[aid] for aid in ids if aid in self._assignments]

    def all_projects(self) -> list[str]:
        return list(self._project_assignments.keys())

    # ── Summary ──────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Workforce summary for API consumption."""
        total_assignments = len(self._assignments)
        total_projects = len(self._project_assignments)

        by_role: dict[str, int] = {}
        for a in self._assignments.values():
            by_role[a.role] = by_role.get(a.role, 0) + 1

        workforce_health = "unknown"
        ws = self._safe_call(self._workforce, "health")
        if ws is not None:
            workforce_health = ws.value if hasattr(ws, "value") else str(ws)

        idle_count = len(self.who_is_idle())
        overloaded_count = len(self.who_is_overloaded())

        return {
            "ok": True,
            "total_assignments": total_assignments,
            "total_projects": total_projects,
            "by_role": by_role,
            "workforce_health": workforce_health,
            "idle_agents": idle_count,
            "overloaded_agents": overloaded_count,
            "role_hierarchy": list(_ROLE_RANK.keys()),
            "generated_at": time.time(),
        }
