"""Governed Execution Runtime — Campaign 16.0.

Single authority path from recommendation to approved execution.
Composes WorkReadiness, DelegationReadiness, ResourceAllocation,
TradeoffIntelligence, and UnifiedApproval into one governed view.

This runtime NEVER executes. It coordinates.
Execution remains in existing subsystems.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ───────────────────────────────────────────────────────────


class ExecutionState(str, Enum):
    IDLE = "idle"
    ASSESSING = "assessing"
    GOVERNED = "governed"
    EXECUTING = "executing"
    BLOCKED = "blocked"


class ExecutionBlocker(str, Enum):
    UNRESOLVED_DEPS = "unresolved_deps"
    MISSING_CAPABILITY = "missing_capability"
    PENDING_APPROVAL = "pending_approval"
    RESOURCE_CONTENTION = "resource_contention"
    NO_EXECUTOR = "no_executor"


class GovernedExecutionHealth(str, Enum):
    OPTIMAL = "optimal"
    ACTIVE = "active"
    CONSTRAINED = "constrained"
    BLOCKED = "blocked"
    OFFLINE = "offline"


# ── Dataclasses ─────────────────────────────────────────────────────


@dataclass
class ExecutionStateAssessment:
    state: str = ExecutionState.IDLE.value
    ready_count: int = 0
    blocked_count: int = 0
    pending_approval_count: int = 0
    active_tradeoffs: int = 0
    top_blockers: list[dict[str, Any]] = field(default_factory=list)
    resource_health: str = "unknown"
    delegation_coverage: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "ready_count": self.ready_count,
            "blocked_count": self.blocked_count,
            "pending_approval_count": self.pending_approval_count,
            "active_tradeoffs": self.active_tradeoffs,
            "top_blockers": self.top_blockers,
            "resource_health": self.resource_health,
            "delegation_coverage": self.delegation_coverage,
            "timestamp": self.timestamp,
        }


@dataclass
class GovernedExecutionSnapshot:
    state: str = ExecutionState.IDLE.value
    health: str = GovernedExecutionHealth.OFFLINE.value
    assessment: dict[str, Any] = field(default_factory=dict)
    readiness_summary: dict[str, Any] = field(default_factory=dict)
    delegation_summary: dict[str, Any] = field(default_factory=dict)
    allocation_summary: dict[str, Any] = field(default_factory=dict)
    tradeoff_summary: dict[str, Any] = field(default_factory=dict)
    approval_summary: dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "state": self.state,
            "health": self.health,
            "assessment": self.assessment,
            "readiness_summary": self.readiness_summary,
            "delegation_summary": self.delegation_summary,
            "allocation_summary": self.allocation_summary,
            "tradeoff_summary": self.tradeoff_summary,
            "approval_summary": self.approval_summary,
            "generated_at": self.generated_at,
        }
        # Hoist assessment fields to root for flat reads (RightRail, ControlPanel)
        if self.assessment:
            for k in (
                "ready_count",
                "blocked_count",
                "pending_approval_count",
                "top_blockers",
                "resource_health",
                "delegation_coverage",
                "active_tradeoffs",
            ):
                if k not in d:
                    d[k] = self.assessment.get(k)
        return d


# ── Runtime ─────────────────────────────────────────────────────────


class GovernedExecutionRuntime:
    """Governed execution coordination — intent to approved execution.

    Composes 5 subsystems into a single governed view:
    - WorkReadinessRuntime: what is ready?
    - DelegationReadinessRuntime: who can execute?
    - ResourceAllocationRuntime: what resources are allocated?
    - TradeoffIntelligenceEngine: what tradeoffs exist?
    - UnifiedApprovalRuntime: what needs approval?

    No mutation. No execution authority. Read-only coordination.
    """

    def __init__(
        self,
        work_readiness: Any | None = None,
        delegation_readiness: Any | None = None,
        resource_allocation: Any | None = None,
        tradeoff_engine: Any | None = None,
        unified_approvals: Any | None = None,
    ) -> None:
        self._work_readiness_dep = work_readiness
        self._delegation_readiness_dep = delegation_readiness
        self._resource_allocation_dep = resource_allocation
        self._tradeoff_engine_dep = tradeoff_engine
        self._unified_approvals_dep = unified_approvals

    # ── Lazy subsystem access ───────────────────────────────────────

    @property
    def _work_readiness(self) -> Any | None:
        if self._work_readiness_dep is not None:
            return self._work_readiness_dep
        try:
            from substrate.organism.work_readiness_runtime import (
                WorkReadinessRuntime,
            )

            self._work_readiness_dep = WorkReadinessRuntime()
        except Exception as exc:
            logger.debug("governed_execution: work_readiness init failed: %s", exc)
        return self._work_readiness_dep

    @property
    def _delegation_readiness(self) -> Any | None:
        if self._delegation_readiness_dep is not None:
            return self._delegation_readiness_dep
        try:
            from substrate.organism.delegation_readiness_runtime import (
                DelegationReadinessRuntime,
            )

            self._delegation_readiness_dep = DelegationReadinessRuntime()
        except Exception as exc:
            logger.debug("governed_execution: delegation_readiness init failed: %s", exc)
        return self._delegation_readiness_dep

    @property
    def _resource_allocation(self) -> Any | None:
        if self._resource_allocation_dep is not None:
            return self._resource_allocation_dep
        try:
            from substrate.organism.resource_allocation_runtime import (
                ResourceAllocationRuntime,
            )

            self._resource_allocation_dep = ResourceAllocationRuntime()
        except Exception as exc:
            logger.debug("governed_execution: resource_allocation init failed: %s", exc)
        return self._resource_allocation_dep

    @property
    def _tradeoff_engine(self) -> Any | None:
        if self._tradeoff_engine_dep is not None:
            return self._tradeoff_engine_dep
        try:
            from substrate.organism.tradeoff_intelligence_engine import (
                TradeoffIntelligenceEngine,
            )

            self._tradeoff_engine_dep = TradeoffIntelligenceEngine()
        except Exception as exc:
            logger.debug("governed_execution: tradeoff_engine init failed: %s", exc)
        return self._tradeoff_engine_dep

    @property
    def _unified_approvals(self) -> Any | None:
        if self._unified_approvals_dep is not None:
            return self._unified_approvals_dep
        try:
            from substrate.workstation.unified_approval_runtime import (
                UnifiedApprovalRuntime,
            )

            self._unified_approvals_dep = UnifiedApprovalRuntime()
        except Exception as exc:
            logger.debug("governed_execution: unified_approvals init failed: %s", exc)
        return self._unified_approvals_dep

    # ── Readiness data ──────────────────────────────────────────────

    def _get_ready_work(self) -> list[Any]:
        try:
            if self._work_readiness is not None:
                return self._work_readiness.ready_work()
        except Exception as exc:
            logger.debug("governed_execution: ready_work failed: %s", exc)
        return []

    def _get_blocked_work(self) -> list[Any]:
        try:
            if self._work_readiness is not None:
                return self._work_readiness.blocked_work()
        except Exception as exc:
            logger.debug("governed_execution: blocked_work failed: %s", exc)
        return []

    def _get_all_work(self) -> list[Any]:
        try:
            if self._work_readiness is not None:
                return self._work_readiness.assess_all()
        except Exception as exc:
            logger.debug("governed_execution: assess_all failed: %s", exc)
        return []

    def _get_pending_approvals(self) -> list[Any]:
        try:
            if self._unified_approvals is not None:
                return self._unified_approvals.pending()
        except Exception as exc:
            logger.debug("governed_execution: pending approvals failed: %s", exc)
        return []

    def _get_delegation_coverage(self) -> float:
        try:
            if self._delegation_readiness is not None:
                snap = self._delegation_readiness.snapshot()
                if hasattr(snap, "to_dict"):
                    d = snap.to_dict()
                    total = d.get("total_assessed", 0)
                    delegatable = d.get("delegatable_count", 0)
                    if total > 0:
                        return delegatable / total
                elif hasattr(snap, "total_assessed") and snap.total_assessed > 0:
                    return getattr(snap, "delegatable_count", 0) / snap.total_assessed
        except Exception as exc:
            logger.debug("governed_execution: delegation_coverage failed: %s", exc)
        return 0.0

    def _get_resource_health(self) -> str:
        try:
            if self._resource_allocation is not None:
                h = self._resource_allocation.health()
                return h.value if hasattr(h, "value") else str(h)
        except Exception as exc:
            logger.debug("governed_execution: resource_health failed: %s", exc)
        return "unknown"

    def _get_active_tradeoffs(self) -> int:
        try:
            if self._tradeoff_engine is not None:
                cmap = self._tradeoff_engine.contention_map()
                return sum(1 for targets in cmap.values() if len(targets) >= 2)
        except Exception as exc:
            logger.debug("governed_execution: active_tradeoffs failed: %s", exc)
        return 0

    # ── Blocker extraction ──────────────────────────────────────────

    def _extract_blockers(
        self,
        blocked: list[Any],
        pending_approvals: list[Any],
    ) -> list[dict[str, Any]]:
        blockers: list[dict[str, Any]] = []

        for item in blocked[:10]:
            blocker_type = ExecutionBlocker.UNRESOLVED_DEPS.value
            desc = ""
            if hasattr(item, "to_dict"):
                d = item.to_dict()
                desc = d.get("description", d.get("work_id", ""))
                if d.get("missing_capabilities"):
                    blocker_type = ExecutionBlocker.MISSING_CAPABILITY.value
                elif d.get("unresolved_deps"):
                    blocker_type = ExecutionBlocker.UNRESOLVED_DEPS.value
            elif isinstance(item, dict):
                desc = item.get("description", item.get("work_id", ""))
                if item.get("missing_capabilities"):
                    blocker_type = ExecutionBlocker.MISSING_CAPABILITY.value
            else:
                desc = str(item)[:100]

            blockers.append(
                {
                    "type": blocker_type,
                    "description": desc,
                }
            )

        for approval in pending_approvals[:5]:
            desc = ""
            if hasattr(approval, "to_dict"):
                d = approval.to_dict()
                desc = d.get("description", d.get("approval_id", ""))
            elif isinstance(approval, dict):
                desc = approval.get("description", approval.get("approval_id", ""))
            else:
                desc = str(approval)[:100]

            blockers.append(
                {
                    "type": ExecutionBlocker.PENDING_APPROVAL.value,
                    "description": desc,
                }
            )

        if self._get_active_tradeoffs() >= 3:
            blockers.append(
                {
                    "type": ExecutionBlocker.RESOURCE_CONTENTION.value,
                    "description": f"{self._get_active_tradeoffs()} active resource contentions",
                }
            )

        if self._get_delegation_coverage() < 0.2 and len(self._get_all_work()) > 0:
            blockers.append(
                {
                    "type": ExecutionBlocker.NO_EXECUTOR.value,
                    "description": f"Delegation coverage at {self._get_delegation_coverage():.0%}",
                }
            )

        return blockers[:15]

    # ── State classification ────────────────────────────────────────

    def state(self) -> ExecutionState:
        ready = self._get_ready_work()
        blocked = self._get_blocked_work()
        all_work = self._get_all_work()
        pending = self._get_pending_approvals()
        coverage = self._get_delegation_coverage()

        if len(all_work) == 0 and len(pending) == 0:
            return ExecutionState.IDLE

        if len(pending) > 0:
            return ExecutionState.GOVERNED

        if len(ready) > 0 and coverage > 0.5:
            return ExecutionState.EXECUTING

        if len(blocked) > len(ready):
            return ExecutionState.BLOCKED

        return ExecutionState.ASSESSING

    # ── Assessment ──────────────────────────────────────────────────

    def assessment(self) -> ExecutionStateAssessment:
        ready = self._get_ready_work()
        blocked = self._get_blocked_work()
        pending = self._get_pending_approvals()
        coverage = self._get_delegation_coverage()
        resource_h = self._get_resource_health()
        tradeoffs = self._get_active_tradeoffs()
        current_state = self.state()

        blocker_list = self._extract_blockers(blocked, pending)

        return ExecutionStateAssessment(
            state=current_state.value,
            ready_count=len(ready),
            blocked_count=len(blocked),
            pending_approval_count=len(pending),
            active_tradeoffs=tradeoffs,
            top_blockers=blocker_list,
            resource_health=resource_h,
            delegation_coverage=coverage,
        )

    def blockers(self) -> list[dict[str, Any]]:
        return self.assessment().top_blockers

    # ── Subsystem summaries ─────────────────────────────────────────

    def readiness_summary(self) -> dict[str, Any]:
        try:
            if self._work_readiness is not None:
                return self._work_readiness.summary()
        except Exception as exc:
            logger.debug("governed_execution: readiness_summary failed: %s", exc)
        return {"status": "unavailable"}

    def delegation_summary(self) -> dict[str, Any]:
        try:
            if self._delegation_readiness is not None:
                return self._delegation_readiness.summary()
        except Exception as exc:
            logger.debug("governed_execution: delegation_summary failed: %s", exc)
        return {"status": "unavailable"}

    def allocation_summary(self) -> dict[str, Any]:
        try:
            if self._resource_allocation is not None:
                return self._resource_allocation.summary()
        except Exception as exc:
            logger.debug("governed_execution: allocation_summary failed: %s", exc)
        return {"status": "unavailable"}

    def tradeoff_summary(self) -> dict[str, Any]:
        try:
            if self._tradeoff_engine is not None:
                return self._tradeoff_engine.summary()
        except Exception as exc:
            logger.debug("governed_execution: tradeoff_summary failed: %s", exc)
        return {"status": "unavailable"}

    def approval_summary(self) -> dict[str, Any]:
        try:
            if self._unified_approvals is not None:
                snap = self._unified_approvals.snapshot()
                if hasattr(snap, "to_dict"):
                    return snap.to_dict()
                return {"pending_count": len(self._get_pending_approvals())}
        except Exception as exc:
            logger.debug("governed_execution: approval_summary failed: %s", exc)
        return {"status": "unavailable"}

    # ── Health ──────────────────────────────────────────────────────

    def health(self) -> GovernedExecutionHealth:
        assessment = self.assessment()

        if assessment.ready_count == 0 and assessment.blocked_count == 0:
            if assessment.pending_approval_count == 0:
                return GovernedExecutionHealth.OFFLINE

        if assessment.blocked_count == 0 and assessment.active_tradeoffs == 0:
            if assessment.delegation_coverage >= 0.7:
                return GovernedExecutionHealth.OPTIMAL

        if assessment.ready_count > assessment.blocked_count:
            return GovernedExecutionHealth.ACTIVE

        if assessment.blocked_count > 0 and assessment.ready_count > 0:
            return GovernedExecutionHealth.CONSTRAINED

        if assessment.blocked_count > assessment.ready_count:
            return GovernedExecutionHealth.BLOCKED

        return GovernedExecutionHealth.ACTIVE

    # ── Snapshot / Summary ──────────────────────────────────────────

    def snapshot(self) -> GovernedExecutionSnapshot:
        assessment = self.assessment()
        return GovernedExecutionSnapshot(
            state=assessment.state,
            health=self.health().value,
            assessment=assessment.to_dict(),
            readiness_summary=self.readiness_summary(),
            delegation_summary=self.delegation_summary(),
            allocation_summary=self.allocation_summary(),
            tradeoff_summary=self.tradeoff_summary(),
            approval_summary=self.approval_summary(),
        )

    def summary(self) -> dict[str, Any]:
        assessment = self.assessment()
        return {
            "state": assessment.state,
            "health": self.health().value,
            "ready_count": assessment.ready_count,
            "blocked_count": assessment.blocked_count,
            "pending_approval_count": assessment.pending_approval_count,
            "delegation_coverage": assessment.delegation_coverage,
            "active_tradeoffs": assessment.active_tradeoffs,
            "resource_health": assessment.resource_health,
            "blocker_count": len(assessment.top_blockers),
        }

    def execution_summary(self) -> dict[str, Any]:
        """Unified execution summary — serves ControlPanel, RightRail, CommandCenterPanel.

        Combines GovernedExecutionRuntime state with work packet stats,
        agent heartbeats, and journal data. Single canonical read path
        replacing /command-center/summary and /governed-execution.
        """
        assessment = self.assessment()
        health_val = self.health().value

        heartbeats = self._load_workcell_heartbeats()
        active_agents = [h for h in heartbeats if h.get("status") == "active"]
        idle_agents = [h for h in heartbeats if h.get("status") == "idle"]

        packets = self._load_work_packets(limit=100)
        executing = [p for p in packets if p.get("status") in ("executing", "delegated")]
        blocked_packets = [
            p for p in packets if p.get("status") == "blocked" or bool(p.get("blockers"))
        ]

        by_status: dict[str, int] = {}
        for p in packets:
            s = p.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1

        ready = [
            p for p in packets if p.get("status") in ("approved", "ready_for_review", "planned")
        ]
        ready.sort(key=lambda p: p.get("leverage_score", 0), reverse=True)
        next_packet = None
        if ready:
            next_packet = {
                "packet_id": ready[0].get("packet_id", ""),
                "title": ready[0].get("title", ""),
                "status": ready[0].get("status", ""),
                "leverage_score": ready[0].get("leverage_score", 0),
            }

        journal = self._load_journal_recent(50)
        completed = [j for j in journal if j.get("phase") == "EXECUTION_COMPLETED"]
        failed = [
            j for j in journal if j.get("phase") in ("EXECUTION_FAILED", "VERIFICATION_FAILED")
        ]

        checkpoint = self._load_checkpoint()
        continuity_state = checkpoint.get(
            "continuity_state",
            checkpoint.get("new_continuity_state", "active"),
        )

        return {
            "ok": True,
            # Governed execution state (from runtime objects)
            "state": assessment.state,
            "health": health_val,
            "ready_count": assessment.ready_count,
            "blocked_count": assessment.blocked_count,
            "pending_approval_count": assessment.pending_approval_count,
            "top_blockers": assessment.top_blockers,
            "delegation_coverage": assessment.delegation_coverage,
            "active_tradeoffs": assessment.active_tradeoffs,
            "resource_health": assessment.resource_health,
            # Work packet stats (from JSONL — same data old /summary read)
            "what_is_happening": {
                "continuity_state": continuity_state,
                "active_agents": len(active_agents),
                "idle_agents": len(idle_agents),
                "total_agents": len(heartbeats),
                "executing_packets": len(executing),
            },
            "who_is_working": [
                {
                    "agent_id": h.get("workcell_id", ""),
                    "role": h.get("role", ""),
                    "status": h.get("status", ""),
                }
                for h in heartbeats
            ],
            "what_is_blocked": {
                "count": len(blocked_packets),
                "items": [
                    {
                        "id": b.get("packet_id", ""),
                        "title": b.get("title", ""),
                        "blockers": b.get("blockers", []),
                    }
                    for b in blocked_packets[:5]
                ],
            },
            "what_needs_approval": {
                "count": assessment.pending_approval_count,
            },
            "what_finished": {
                "recent_completed": len(completed),
                "latest": completed[-1].get("details", {}).get("intent", "") if completed else "",
            },
            "what_failed": {
                "recent_failed": len(failed),
                "latest": failed[-1].get("details", {}).get("error", failed[-1].get("source", ""))
                if failed
                else "",
            },
            "what_should_resume_next": next_packet,
            "packets_by_status": by_status,
            "total_packets": len(packets),
        }

    # ── File loaders for execution_summary ──────────────────────────

    @staticmethod
    def _load_workcell_heartbeats() -> list[dict[str, Any]]:
        from substrate.state.runtime_paths import runtime_state_dir

        wc_dir = str(runtime_state_dir("organism", create=False) / "workcells")
        heartbeats: list[dict[str, Any]] = []
        if not os.path.isdir(wc_dir):
            return heartbeats
        for entry in sorted(os.listdir(wc_dir)):
            hb_path = os.path.join(wc_dir, entry, "heartbeat.json")
            if os.path.exists(hb_path):
                try:
                    with open(hb_path) as f:
                        data = json.load(f)
                    data["workcell_dir"] = entry
                    heartbeats.append(data)
                except (json.JSONDecodeError, OSError):
                    heartbeats.append({"workcell_id": entry, "status": "unavailable"})
        return heartbeats

    @staticmethod
    def _load_work_packets(limit: int = 50) -> list[dict[str, Any]]:
        from substrate.state.runtime_paths import runtime_state_path

        path = str(runtime_state_path("universal_work", "work_packets.jsonl", create_parent=False))
        packets: list[dict[str, Any]] = []
        if not os.path.exists(path):
            return packets
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        packets.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        packets.sort(key=lambda p: p.get("leverage_score", 0), reverse=True)
        return packets[:limit]

    @staticmethod
    def _load_journal_recent(limit: int = 20) -> list[dict[str, Any]]:
        from substrate.state.runtime_paths import runtime_state_path

        path = str(runtime_state_path("organism", "execution_journal.jsonl", create_parent=False))
        entries: list[dict[str, Any]] = []
        if not os.path.exists(path):
            return entries
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return entries[-limit:]

    @staticmethod
    def _load_checkpoint() -> dict[str, Any]:
        umh_root = os.environ.get("UMH_ROOT", "/opt/OS")
        path = os.path.join(umh_root, "data", "umh", "workstation_state", "latest_checkpoint.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}
