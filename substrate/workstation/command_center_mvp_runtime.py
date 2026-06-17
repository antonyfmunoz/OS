"""Command Center MVP Runtime — operator landing surface.

Answers: "Where am I, what matters, what changed, what needs me,
what should happen next?"

Composes 10 subsystems into a unified command center snapshot.
All subsystem calls are wrapped with graceful degradation — if a
subsystem is None or raises, a safe default is returned.

Campaign 3, Workstream 2. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CommandCenterSection(str, Enum):
    SITUATION = "situation"
    ATTENTION = "attention"
    EXECUTION = "execution"
    CAPABILITY = "capability"
    MIGRATION = "migration"
    RECOMMENDATIONS = "recommendations"


@dataclass
class ExecutionPulse:
    active_work: int = 0
    active_agents: int = 0
    active_compute_nodes: int = 0
    blocked_work: int = 0
    pending_approvals: int = 0
    compounding_candidates: int = 0
    queue_depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_work": self.active_work,
            "active_agents": self.active_agents,
            "active_compute_nodes": self.active_compute_nodes,
            "blocked_work": self.blocked_work,
            "pending_approvals": self.pending_approvals,
            "compounding_candidates": self.compounding_candidates,
            "queue_depth": self.queue_depth,
        }


@dataclass
class CapabilityPulse:
    total_capabilities: int = 0
    by_maturity: dict[str, int] = field(default_factory=dict)
    recent_promotions: int = 0
    coverage_gaps: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_capabilities": self.total_capabilities,
            "by_maturity": self.by_maturity,
            "recent_promotions": self.recent_promotions,
            "coverage_gaps": self.coverage_gaps,
        }


@dataclass
class MigrationPulse:
    total_exits: int = 0
    top_exit_reasons: list[dict[str, Any]] = field(default_factory=list)
    coverage_percentage: float = 0.0
    priorities: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_exits": self.total_exits,
            "top_exit_reasons": self.top_exit_reasons,
            "coverage_percentage": self.coverage_percentage,
            "priorities": self.priorities,
        }


@dataclass
class CommandCenterRecommendation:
    priority: int = 0
    action: str = ""
    rationale: str = ""
    panel_link: str = ""
    source_system: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority": self.priority,
            "action": self.action,
            "rationale": self.rationale,
            "panel_link": self.panel_link,
            "source_system": self.source_system,
        }


@dataclass
class CommandCenterSnapshot:
    situation: dict[str, Any] = field(default_factory=dict)
    attention: list[dict[str, Any]] = field(default_factory=list)
    execution: ExecutionPulse = field(default_factory=ExecutionPulse)
    capability: CapabilityPulse = field(default_factory=CapabilityPulse)
    migration: MigrationPulse = field(default_factory=MigrationPulse)
    recommendations: list[CommandCenterRecommendation] = field(default_factory=list)
    cockpit_health: dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "situation": self.situation,
            "attention": self.attention,
            "execution": self.execution.to_dict(),
            "capability": self.capability.to_dict(),
            "migration": self.migration.to_dict(),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "cockpit_health": self.cockpit_health,
            "generated_at": self.generated_at,
        }


def _safe_call(obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    """Call method on obj, returning None on any failure."""
    if obj is None:
        return None
    try:
        fn = getattr(obj, method, None)
        if fn is None:
            return None
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("safe_call %s.%s failed: %s", type(obj).__name__, method, exc)
        return None


class CommandCenterMVPRuntime:
    """Unified command center composing 10 subsystems.

    Every dependency is optional — the runtime degrades gracefully when
    any subsystem is absent or fails.
    """

    def __init__(
        self,
        snapshot_runtime: Any | None = None,
        attention_engine: Any | None = None,
        intent_runtime: Any | None = None,
        agent_fleet: Any | None = None,
        compute_fabric: Any | None = None,
        governed_work: Any | None = None,
        compounding_engine: Any | None = None,
        migration_runtime: Any | None = None,
        capability_runtime: Any | None = None,
        capability_map: Any | None = None,
    ) -> None:
        self._snapshot_runtime = snapshot_runtime
        self._attention_engine = attention_engine
        self._intent_runtime = intent_runtime
        self._agent_fleet = agent_fleet
        self._compute_fabric = compute_fabric
        self._governed_work = governed_work
        self._compounding_engine = compounding_engine
        self._migration_runtime = migration_runtime
        self._capability_runtime = capability_runtime
        self._capability_map = capability_map

    # ── Individual sections ─────────────────────────────────────────────

    def situation(self) -> dict[str, Any]:
        result = _safe_call(self._snapshot_runtime, "situation")
        if result is None:
            return {"status": "unavailable", "reason": "snapshot_runtime not connected"}
        if hasattr(result, "to_dict"):
            return result.to_dict()
        if isinstance(result, dict):
            return result
        return {"status": "unavailable", "reason": "unexpected return type"}

    def attention(self, limit: int = 10) -> list[dict[str, Any]]:
        items = _safe_call(self._attention_engine, "top", limit)
        if not items:
            return []
        result = []
        for item in items:
            if hasattr(item, "to_dict"):
                result.append(item.to_dict())
            elif isinstance(item, dict):
                result.append(item)
        return result

    def execution_pulse(self) -> ExecutionPulse:
        pulse = ExecutionPulse()

        active = _safe_call(self._governed_work, "active")
        if active is not None:
            pulse.active_work = len(active) if isinstance(active, list) else 0

        blocked = _safe_call(self._governed_work, "blocked")
        if blocked is not None:
            pulse.blocked_work = len(blocked) if isinstance(blocked, list) else 0

        queue = _safe_call(self._governed_work, "queue")
        if queue is not None:
            pulse.queue_depth = len(queue) if isinstance(queue, list) else 0

        fleet = _safe_call(self._agent_fleet, "fleet_status")
        if fleet is not None:
            if isinstance(fleet, dict):
                pulse.active_agents = fleet.get("active_agents", 0)
            elif hasattr(fleet, "active_agents"):
                pulse.active_agents = getattr(fleet, "active_agents", 0)

        dispatches = _safe_call(self._agent_fleet, "active_dispatches")
        if dispatches is not None and isinstance(dispatches, list):
            pulse.active_agents = max(pulse.active_agents, len(dispatches))

        health = _safe_call(self._compute_fabric, "health")
        if health is not None:
            if isinstance(health, dict):
                pulse.active_compute_nodes = health.get("online_nodes", 0)
            elif hasattr(health, "online_nodes"):
                pulse.active_compute_nodes = getattr(health, "online_nodes", 0)

        candidates = _safe_call(self._compounding_engine, "list_candidates", status="proposed")
        if candidates is not None and isinstance(candidates, list):
            pulse.compounding_candidates = len(candidates)

        # pending_approvals derived from queue items with approval status
        if queue is not None and isinstance(queue, list):
            pulse.pending_approvals = sum(
                1 for item in queue
                if (isinstance(item, dict) and item.get("status") == "approval_pending")
                or (hasattr(item, "status") and getattr(item, "status", "") == "approval_pending")
            )

        return pulse

    def capability_pulse(self) -> CapabilityPulse:
        pulse = CapabilityPulse()

        summary = _safe_call(self._capability_runtime, "summary")
        if summary is not None and isinstance(summary, dict):
            pulse.total_capabilities = summary.get("total", 0)
            pulse.by_maturity = summary.get("by_maturity", {})

        emerging = _safe_call(self._capability_runtime, "capabilities_by_maturity", "emerging")
        if emerging is not None and isinstance(emerging, list):
            pulse.coverage_gaps = len(emerging)

        return pulse

    def migration_pulse(self) -> MigrationPulse:
        pulse = MigrationPulse()

        report = _safe_call(self._migration_runtime, "coverage_report")
        if report is not None and isinstance(report, dict):
            pulse.total_exits = report.get("total_exits", 0)
            pulse.coverage_percentage = report.get("coverage_percentage", 0.0)

        priorities = _safe_call(self._migration_runtime, "migration_priorities")
        if priorities is not None and isinstance(priorities, list):
            pulse.priorities = priorities
            # Derive top exit reasons from priorities
            for p in priorities[:5]:
                if isinstance(p, dict) and "reason" in p:
                    pulse.top_exit_reasons.append({
                        "reason": p["reason"],
                        "count": p.get("count", 0),
                        "percentage": p.get("percentage", 0.0),
                    })

        return pulse

    def recommendations(self, limit: int = 5) -> list[CommandCenterRecommendation]:
        recs: list[CommandCenterRecommendation] = []

        # Priority 1: Blocked work
        ep = self.execution_pulse()
        if ep.blocked_work > 0:
            recs.append(CommandCenterRecommendation(
                priority=1,
                action="Unblock",
                rationale=f"{ep.blocked_work} work item(s) blocked",
                panel_link="work",
                source_system="governed_work",
            ))

        # Priority 2: Pending approvals
        if ep.pending_approvals > 0:
            recs.append(CommandCenterRecommendation(
                priority=2,
                action="Review approvals",
                rationale=f"{ep.pending_approvals} approval(s) pending",
                panel_link="approvals",
                source_system="approval_gate",
            ))

        # Priority 3: High attention items
        attn = self.attention(limit=3)
        for item in attn:
            severity = item.get("severity", "")
            if severity in ("high", "critical"):
                recs.append(CommandCenterRecommendation(
                    priority=3,
                    action=item.get("action_hint", "Review attention item"),
                    rationale=item.get("title", "High priority attention item"),
                    panel_link=item.get("capability_link", "commandcenter"),
                    source_system="attention_engine",
                ))
                break

        # Priority 4: Queued work
        if ep.queue_depth > 0:
            recs.append(CommandCenterRecommendation(
                priority=4,
                action="Execute queued work",
                rationale=f"{ep.queue_depth} item(s) in queue",
                panel_link="execution",
                source_system="governed_work",
            ))

        # Priority 5: Compounding candidates
        if ep.compounding_candidates > 0:
            recs.append(CommandCenterRecommendation(
                priority=5,
                action="Review promotions",
                rationale=f"{ep.compounding_candidates} compounding candidate(s)",
                panel_link="knowledge",
                source_system="compounding_engine",
            ))

        # Priority 6: Migration priorities
        mp = self.migration_pulse()
        if mp.priorities:
            first = mp.priorities[0]
            desc = first.get("reason", "External tool dependency") if isinstance(first, dict) else str(first)
            recs.append(CommandCenterRecommendation(
                priority=6,
                action="Reduce external dependency",
                rationale=desc,
                panel_link="metaide",
                source_system="migration_runtime",
            ))

        recs.sort(key=lambda r: r.priority)
        return recs[:limit]

    def section(self, section_name: str) -> dict[str, Any]:
        try:
            sec = CommandCenterSection(section_name)
        except ValueError:
            return {"error": f"unknown section: {section_name}"}

        if sec == CommandCenterSection.SITUATION:
            return self.situation()
        elif sec == CommandCenterSection.ATTENTION:
            return {"items": self.attention()}
        elif sec == CommandCenterSection.EXECUTION:
            return self.execution_pulse().to_dict()
        elif sec == CommandCenterSection.CAPABILITY:
            return self.capability_pulse().to_dict()
        elif sec == CommandCenterSection.MIGRATION:
            return self.migration_pulse().to_dict()
        elif sec == CommandCenterSection.RECOMMENDATIONS:
            return {"items": [r.to_dict() for r in self.recommendations()]}
        return {"error": f"unhandled section: {section_name}"}

    def snapshot(self) -> CommandCenterSnapshot:
        cockpit_health: dict[str, Any] = {}
        ch = _safe_call(self._capability_map, "summary")
        if ch is not None and isinstance(ch, dict):
            cockpit_health = ch

        return CommandCenterSnapshot(
            situation=self.situation(),
            attention=self.attention(),
            execution=self.execution_pulse(),
            capability=self.capability_pulse(),
            migration=self.migration_pulse(),
            recommendations=self.recommendations(),
            cockpit_health=cockpit_health,
        )
