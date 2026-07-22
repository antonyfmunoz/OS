"""Strategic Gap Engine — compares current reality to target goals, produces gaps,
priorities, recommendations, and candidate WorkPackets.

Phase 4. UMH substrate subsystem. Instance-agnostic.

Composes existing primitives:
  - RealitySnapshot (empire_router)
  - WorkPacket / UniversalWorkQueue (work_packet, universal_work_queue)
  - DomainRegistry (domain_registry)
  - AgentRegistry (agent_registry)
  - EmpireRouter (empire_router)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator
from uuid import uuid4

try:  # fcntl is POSIX-only; the registry degrades to thread-locking elsewhere.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


def _data_dir() -> str:
    return os.path.join(_repo_root(), "data", "umh", "strategic_gaps")


def _legacy_goals_paths() -> tuple[str, ...]:
    """Pre-Wave-1 goal store locations, in probe order. READ-ONLY migration
    sources — the registry never writes to either again (§22.1 boundary)."""
    return (
        os.path.join(_data_dir(), "goals.jsonl"),
        os.path.join(_data_dir(), "goals", "goals.jsonl"),
    )


def _durable_goals_path() -> str:
    """Canonical durable goal store beneath the runtime-state boundary."""
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path("strategic_gaps", "goals.jsonl"))


def _ensure_dirs() -> None:
    base = _data_dir()
    for sub in ("goals", "gaps", "recommendations", "decisions"):
        os.makedirs(os.path.join(base, sub), exist_ok=True)


# ── Enums ──────────────────────────────────────────────────────────────


class GoalStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ABANDONED = "abandoned"


class GoalType(str, Enum):
    VISION = "vision"
    OBJECTIVE = "objective"
    OUTCOME = "outcome"
    INITIATIVE = "initiative"
    PROJECT = "project"
    GOAL = "goal"
    ROADMAP = "roadmap"
    MILESTONE = "milestone"


class GapSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"
    EXPIRED = "expired"


# ── Goal Model ─────────────────────────────────────────────────────────


@dataclass
class SuccessCriterion:
    description: str = ""
    measurable: bool = True
    current_value: str = ""
    target_value: str = ""
    met: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "measurable": self.measurable,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "met": self.met,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SuccessCriterion:
        return cls(
            description=d.get("description", ""),
            measurable=d.get("measurable", True),
            current_value=d.get("current_value", ""),
            target_value=d.get("target_value", ""),
            met=d.get("met", False),
        )


@dataclass
class Goal:
    goal_id: str = field(default_factory=lambda: f"goal-{uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    goal_type: GoalType = GoalType.GOAL
    status: GoalStatus = GoalStatus.ACTIVE
    domain: str = ""
    parent_goal_id: str = ""
    child_goal_ids: list[str] = field(default_factory=list)
    success_criteria: list[SuccessCriterion] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    required_milestones: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    target_date: str = ""
    priority: int = 50
    # Wave 1 (§22.1) backward-compatible additions. version is the CAS counter
    # (pre-Wave-1 records deserialize as version 1). tenant_id/objective_key/
    # scope_hash form the idempotent create-or-reuse identity for Objectives.
    version: int = 1
    tenant_id: str = ""
    objective_key: str = ""
    scope_hash: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "goal_type": self.goal_type.value,
            "status": self.status.value,
            "domain": self.domain,
            "parent_goal_id": self.parent_goal_id,
            "child_goal_ids": self.child_goal_ids,
            "success_criteria": [c.to_dict() for c in self.success_criteria],
            "required_capabilities": self.required_capabilities,
            "required_milestones": self.required_milestones,
            "dependencies": self.dependencies,
            "target_date": self.target_date,
            "priority": self.priority,
            "version": self.version,
            "tenant_id": self.tenant_id,
            "objective_key": self.objective_key,
            "scope_hash": self.scope_hash,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Goal:
        return cls(
            goal_id=d.get("goal_id", f"goal-{uuid4().hex[:8]}"),
            title=d.get("title", ""),
            description=d.get("description", ""),
            goal_type=GoalType(d["goal_type"]) if "goal_type" in d else GoalType.GOAL,
            status=GoalStatus(d["status"]) if "status" in d else GoalStatus.ACTIVE,
            domain=d.get("domain", ""),
            parent_goal_id=d.get("parent_goal_id", ""),
            child_goal_ids=d.get("child_goal_ids", []),
            success_criteria=[SuccessCriterion.from_dict(c) for c in d.get("success_criteria", [])],
            required_capabilities=d.get("required_capabilities", []),
            required_milestones=d.get("required_milestones", []),
            dependencies=d.get("dependencies", []),
            target_date=d.get("target_date", ""),
            priority=d.get("priority", 50),
            version=d.get("version", 1),
            tenant_id=d.get("tenant_id", ""),
            objective_key=d.get("objective_key", ""),
            scope_hash=d.get("scope_hash", ""),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
        )

    def completion_ratio(self) -> float:
        if not self.success_criteria:
            return 0.0
        met = sum(1 for c in self.success_criteria if c.met)
        return met / len(self.success_criteria)


# ── Gap Model ──────────────────────────────────────────────────────────


@dataclass
class Gap:
    gap_id: str = field(default_factory=lambda: f"gap-{uuid4().hex[:8]}")
    goal_id: str = ""
    title: str = ""
    description: str = ""
    gap_type: str = ""
    severity: GapSeverity = GapSeverity.MEDIUM
    domain: str = ""
    current_state: str = ""
    required_state: str = ""
    blocking_goals: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    estimated_effort: str = ""
    priority_score: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "gap_type": self.gap_type,
            "severity": self.severity.value,
            "domain": self.domain,
            "current_state": self.current_state,
            "required_state": self.required_state,
            "blocking_goals": self.blocking_goals,
            "dependencies": self.dependencies,
            "estimated_effort": self.estimated_effort,
            "priority_score": self.priority_score,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Gap:
        return cls(
            gap_id=d.get("gap_id", f"gap-{uuid4().hex[:8]}"),
            goal_id=d.get("goal_id", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            gap_type=d.get("gap_type", ""),
            severity=GapSeverity(d["severity"]) if "severity" in d else GapSeverity.MEDIUM,
            domain=d.get("domain", ""),
            current_state=d.get("current_state", ""),
            required_state=d.get("required_state", ""),
            blocking_goals=d.get("blocking_goals", []),
            dependencies=d.get("dependencies", []),
            estimated_effort=d.get("estimated_effort", ""),
            priority_score=d.get("priority_score", 0.0),
            created_at=d.get("created_at", time.time()),
        )


# ── Recommendation Model ──────────────────────────────────────────────


@dataclass
class Recommendation:
    recommendation_id: str = field(default_factory=lambda: f"rec-{uuid4().hex[:8]}")
    gap_id: str = ""
    title: str = ""
    rationale: str = ""
    impact_estimate: str = ""
    risk_estimate: str = ""
    suggested_domain: str = ""
    suggested_agents: list[str] = field(default_factory=list)
    dependency_chain: list[str] = field(default_factory=list)
    priority_score: float = 0.0
    status: RecommendationStatus = RecommendationStatus.PENDING
    converted_packet_id: str = ""
    decision_reason: str = ""
    created_at: float = field(default_factory=time.time)
    decided_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "gap_id": self.gap_id,
            "title": self.title,
            "rationale": self.rationale,
            "impact_estimate": self.impact_estimate,
            "risk_estimate": self.risk_estimate,
            "suggested_domain": self.suggested_domain,
            "suggested_agents": self.suggested_agents,
            "dependency_chain": self.dependency_chain,
            "priority_score": self.priority_score,
            "status": self.status.value,
            "converted_packet_id": self.converted_packet_id,
            "decision_reason": self.decision_reason,
            "created_at": self.created_at,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Recommendation:
        return cls(
            recommendation_id=d.get("recommendation_id", f"rec-{uuid4().hex[:8]}"),
            gap_id=d.get("gap_id", ""),
            title=d.get("title", ""),
            rationale=d.get("rationale", ""),
            impact_estimate=d.get("impact_estimate", ""),
            risk_estimate=d.get("risk_estimate", ""),
            suggested_domain=d.get("suggested_domain", ""),
            suggested_agents=d.get("suggested_agents", []),
            dependency_chain=d.get("dependency_chain", []),
            priority_score=d.get("priority_score", 0.0),
            status=RecommendationStatus(d["status"])
            if "status" in d
            else RecommendationStatus.PENDING,
            converted_packet_id=d.get("converted_packet_id", ""),
            decision_reason=d.get("decision_reason", ""),
            created_at=d.get("created_at", time.time()),
            decided_at=d.get("decided_at", 0.0),
        )


# ── Decision Record (Learning Loop) ───────────────────────────────────


@dataclass
class DecisionRecord:
    decision_id: str = field(default_factory=lambda: f"dec-{uuid4().hex[:8]}")
    recommendation_id: str = ""
    gap_id: str = ""
    goal_id: str = ""
    action: str = ""
    reason: str = ""
    outcome_packet_id: str = ""
    outcome_summary: str = ""
    was_effective: bool | None = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "recommendation_id": self.recommendation_id,
            "gap_id": self.gap_id,
            "goal_id": self.goal_id,
            "action": self.action,
            "reason": self.reason,
            "outcome_packet_id": self.outcome_packet_id,
            "outcome_summary": self.outcome_summary,
            "was_effective": self.was_effective,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DecisionRecord:
        return cls(
            decision_id=d.get("decision_id", f"dec-{uuid4().hex[:8]}"),
            recommendation_id=d.get("recommendation_id", ""),
            gap_id=d.get("gap_id", ""),
            goal_id=d.get("goal_id", ""),
            action=d.get("action", ""),
            reason=d.get("reason", ""),
            outcome_packet_id=d.get("outcome_packet_id", ""),
            outcome_summary=d.get("outcome_summary", ""),
            was_effective=d.get("was_effective"),
            created_at=d.get("created_at", time.time()),
        )


# ── Goal Registry ─────────────────────────────────────────────────────


class GoalConflictError(RuntimeError):
    """A CAS goal write found a different current version than expected."""

    def __init__(self, goal_id: str, expected: int, actual: int) -> None:
        super().__init__(f"goal {goal_id}: expected version {expected}, found {actual}")
        self.goal_id = goal_id
        self.expected = expected
        self.actual = actual


class GoalRegistry:
    """Persists and queries goals. JSONL-backed like all UMH stores.

    Wave 1 durability (§22.1):
      - default store resolves through the runtime-state boundary
        (``<runtime-state>/strategic_gaps/goals.jsonl``) — never a new write
        to the tracked ``data/umh/strategic_gaps/`` tree;
      - bounded one-time migration of pre-existing legacy goal records
        (IDs and serialized fields preserved; legacy file left untouched);
      - interprocess ``fcntl`` locking + in-process thread lock, with
        reload-before-write so concurrent writers see current truth;
      - atomic replacement writes (temp file + ``os.replace``);
      - per-goal ``version`` counter with optional compare-and-set
        (``expected_version`` mismatch raises ``GoalConflictError``);
      - idempotent Objective create-or-reuse keyed on
        ``tenant_id + objective_key + scope_hash``.
    """

    def __init__(self, store_path: str | None = None) -> None:
        if store_path:
            self._store_path = store_path
        else:
            self._store_path = _durable_goals_path()
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        self._thread_lock = threading.RLock()
        self._goals: dict[str, Goal] = {}
        if not store_path:
            self._migrate_legacy_once()
        self._load()

    # ── Locking / durability primitives ───────────────────────────────

    @contextmanager
    def _file_lock(self) -> Iterator[None]:
        """Interprocess exclusive lock scoped to the goal store file."""
        with self._thread_lock:
            lock_path = self._store_path + ".lock"
            fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                try:
                    if fcntl is not None:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                finally:
                    os.close(fd)

    def _migrate_legacy_once(self) -> None:
        """Bounded one-time copy of legacy goal records into the boundary
        store. Read-only on the legacy side; skipped once the durable store
        exists (even empty)."""
        if os.path.exists(self._store_path):
            return
        for legacy in _legacy_goals_paths():
            if not os.path.exists(legacy):
                continue
            try:
                with open(legacy) as f:
                    lines = [ln.strip() for ln in f if ln.strip()]
                migrated = 0
                tmp = self._store_path + ".tmp"
                with open(tmp, "w") as out:
                    for line in lines:
                        try:
                            goal = Goal.from_dict(json.loads(line))
                        except (json.JSONDecodeError, KeyError, ValueError) as exc:
                            logger.debug("skipping unreadable legacy goal line: %s", exc)
                            continue
                        out.write(json.dumps(goal.to_dict()) + "\n")
                        migrated += 1
                os.replace(tmp, self._store_path)
                logger.info(
                    "migrated %d goal record(s) from legacy store %s → %s (legacy file untouched)",
                    migrated,
                    legacy,
                    self._store_path,
                )
                return
            except OSError as e:
                logger.error("legacy goal migration failed for %s: %s", legacy, e)

    def _load(self) -> None:
        self._goals = {}
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    goal = Goal.from_dict(d)
                    self._goals[goal.goal_id] = goal
        except (json.JSONDecodeError, OSError) as e:
            logger.error("failed to load goals: %s", e)

    def _save(self) -> None:
        """Atomic full-store replacement. Callers hold the file lock."""
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        tmp = self._store_path + ".tmp"
        with open(tmp, "w") as f:
            for goal in self._goals.values():
                f.write(json.dumps(goal.to_dict()) + "\n")
        os.replace(tmp, self._store_path)

    def _check_version(self, goal_id: str, expected_version: int | None) -> int:
        """Return the current stored version, enforcing CAS when requested."""
        current = self._goals.get(goal_id)
        actual = current.version if current else 0
        if expected_version is not None and actual != expected_version:
            raise GoalConflictError(goal_id, expected_version, actual)
        return actual

    # ── Writes (locked, versioned) ─────────────────────────────────────

    def add(self, goal: Goal, expected_version: int | None = None) -> Goal:
        with self._file_lock():
            self._load()
            actual = self._check_version(goal.goal_id, expected_version)
            goal.version = actual + 1
            self._goals[goal.goal_id] = goal
            self._save()
        return goal

    def get(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def update(self, goal: Goal, expected_version: int | None = None) -> Goal:
        with self._file_lock():
            self._load()
            actual = self._check_version(goal.goal_id, expected_version)
            goal.updated_at = time.time()
            goal.version = actual + 1
            self._goals[goal.goal_id] = goal
            self._save()
        return goal

    def remove(self, goal_id: str) -> bool:
        with self._file_lock():
            self._load()
            if goal_id in self._goals:
                del self._goals[goal_id]
                self._save()
                return True
            return False

    def create_or_reuse_objective(
        self,
        tenant_id: str,
        objective_key: str,
        scope_hash: str,
        title: str = "",
        description: str = "",
        domain: str = "",
        parent_goal_id: str = "",
    ) -> tuple[Goal, bool]:
        """Idempotently resolve the canonical Objective Goal for one identity.

        Identity key: ``tenant_id + objective_key + scope_hash`` (§22.1).
        Returns ``(goal, created)`` — retries and duplicate submissions reuse
        the exact same goal_id. New Objectives start in the canonical initial
        state ``GoalStatus.DRAFT`` (no new lifecycle states, §23.3).
        """
        if not tenant_id.strip():
            raise ValueError("create_or_reuse_objective requires a non-empty tenant_id")
        if not objective_key.strip():
            raise ValueError("create_or_reuse_objective requires a non-empty objective_key")
        with self._file_lock():
            self._load()
            for g in self._goals.values():
                if (
                    g.goal_type == GoalType.OBJECTIVE
                    and g.tenant_id == tenant_id
                    and g.objective_key == objective_key
                    and g.scope_hash == scope_hash
                ):
                    return g, False
            goal = Goal(
                title=title or objective_key,
                description=description,
                goal_type=GoalType.OBJECTIVE,
                status=GoalStatus.DRAFT,
                domain=domain,
                parent_goal_id=parent_goal_id,
                tenant_id=tenant_id,
                objective_key=objective_key,
                scope_hash=scope_hash,
            )
            goal.version = 1
            self._goals[goal.goal_id] = goal
            self._save()
            return goal, True

    def active_goals(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == GoalStatus.ACTIVE]

    def all_goals(self) -> list[Goal]:
        return list(self._goals.values())

    def goals_by_domain(self, domain: str) -> list[Goal]:
        return [g for g in self._goals.values() if g.domain == domain]

    def goals_by_type(self, goal_type: GoalType) -> list[Goal]:
        return [g for g in self._goals.values() if g.goal_type == goal_type]

    def children_of(self, goal_id: str) -> list[Goal]:
        return [g for g in self._goals.values() if g.parent_goal_id == goal_id]

    def goals_by_status(self, status: GoalStatus) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == status]

    def ancestors(self, goal_id: str) -> list[Goal]:
        """Walk parent_goal_id chain upward. Returns leaf-to-root order."""
        chain: list[Goal] = []
        seen: set[str] = set()
        current = self._goals.get(goal_id)
        while current and current.parent_goal_id:
            if current.parent_goal_id in seen:
                break
            seen.add(current.parent_goal_id)
            parent = self._goals.get(current.parent_goal_id)
            if parent:
                chain.append(parent)
            current = parent
        return chain

    def tree(self, root_id: str | None = None) -> dict[str, Any]:
        """Nested dict of goal hierarchy. If root_id is None, returns forest."""

        def _build(gid: str) -> dict[str, Any]:
            goal = self._goals.get(gid)
            if not goal:
                return {}
            children = self.children_of(gid)
            return {
                **goal.to_dict(),
                "children": [_build(c.goal_id) for c in children],
            }

        if root_id:
            return _build(root_id)

        roots = [g for g in self._goals.values() if not g.parent_goal_id]
        return {"roots": [_build(r.goal_id) for r in roots]}


# ── Priority Engine ───────────────────────────────────────────────────


_PRIORITY_WEIGHTS = {
    "impact": 0.30,
    "dependency_weight": 0.20,
    "strategic_importance": 0.20,
    "risk_penalty": 0.15,
    "time_compression": 0.15,
}

_SEVERITY_SCORES = {
    GapSeverity.CRITICAL: 1.0,
    GapSeverity.HIGH: 0.75,
    GapSeverity.MEDIUM: 0.50,
    GapSeverity.LOW: 0.25,
}


def score_gap(gap: Gap, goal: Goal | None, all_gaps: list[Gap]) -> float:
    """Score a gap for priority ranking. Returns 0-100."""

    impact = _SEVERITY_SCORES.get(gap.severity, 0.5)

    blocked_count = len(gap.blocking_goals)
    dependency_weight = min(1.0, blocked_count * 0.25)

    strategic = (goal.priority / 100.0) if goal else 0.5

    risk_keywords = {"critical", "breaking", "security", "data loss", "outage"}
    risk_score = 0.0
    desc_lower = gap.description.lower()
    for kw in risk_keywords:
        if kw in desc_lower:
            risk_score += 0.2
    risk_score = min(1.0, risk_score)

    deps_in_set = sum(1 for d in gap.dependencies if any(g.gap_id == d for g in all_gaps))
    time_compression = 1.0 - (min(deps_in_set, 4) * 0.25)

    raw = (
        _PRIORITY_WEIGHTS["impact"] * impact
        + _PRIORITY_WEIGHTS["dependency_weight"] * dependency_weight
        + _PRIORITY_WEIGHTS["strategic_importance"] * strategic
        + _PRIORITY_WEIGHTS["risk_penalty"] * risk_score
        + _PRIORITY_WEIGHTS["time_compression"] * time_compression
    )
    return round(raw * 100, 2)


# ── Gap Detector ──────────────────────────────────────────────────────


class GapDetector:
    """Compares current reality against goal targets and produces Gap objects."""

    def detect_gaps(
        self,
        goal: Goal,
        reality: dict[str, Any],
        active_packets: list[dict[str, Any]] | None = None,
    ) -> list[Gap]:
        gaps: list[Gap] = []

        for criterion in goal.success_criteria:
            if criterion.met:
                continue
            gap = Gap(
                goal_id=goal.goal_id,
                title=f"Unmet: {criterion.description}",
                description=(
                    f"Goal '{goal.title}' requires: {criterion.description}. "
                    f"Current: {criterion.current_value or 'not started'}. "
                    f"Target: {criterion.target_value or 'complete'}."
                ),
                gap_type="unmet_criterion",
                domain=goal.domain,
                current_state=criterion.current_value,
                required_state=criterion.target_value,
            )
            gaps.append(gap)

        for cap in goal.required_capabilities:
            cap_lower = cap.lower()
            active_domains = [d.lower() for d in reality.get("active_domains", [])]
            recent_text = " ".join(
                str(o.get("summary", "")) for o in reality.get("recent_outcomes", [])
            ).lower()

            if cap_lower not in " ".join(active_domains) and cap_lower not in recent_text:
                gap = Gap(
                    goal_id=goal.goal_id,
                    title=f"Missing capability: {cap}",
                    description=f"Goal '{goal.title}' requires capability '{cap}' which is not currently active or recently completed.",
                    gap_type="missing_capability",
                    severity=GapSeverity.HIGH,
                    domain=goal.domain,
                    current_state="absent",
                    required_state=cap,
                )
                gaps.append(gap)

        for ms in goal.required_milestones:
            ms_lower = ms.lower()
            completed_packets = active_packets or []
            completed_titles = [
                p.get("title", "").lower()
                for p in completed_packets
                if p.get("status") in ("completed", "archived")
            ]
            if not any(ms_lower in t for t in completed_titles):
                gap = Gap(
                    goal_id=goal.goal_id,
                    title=f"Missing milestone: {ms}",
                    description=f"Goal '{goal.title}' requires milestone '{ms}' which has not been completed.",
                    gap_type="missing_milestone",
                    severity=GapSeverity.MEDIUM,
                    domain=goal.domain,
                    current_state="not completed",
                    required_state=ms,
                )
                gaps.append(gap)

        blocked = reality.get("blocked_items", [])
        for item in blocked:
            item_domain = item.get("domain", "")
            if item_domain == goal.domain or not item_domain:
                gap = Gap(
                    goal_id=goal.goal_id,
                    title=f"Blocker: {item.get('title', item.get('packet_id', 'unknown'))}",
                    description=f"Blocked work in domain '{goal.domain}': {item.get('status_reason', 'no reason')}",
                    gap_type="blocker",
                    severity=GapSeverity.HIGH,
                    domain=goal.domain,
                    current_state="blocked",
                    required_state="resolved",
                    blocking_goals=[goal.goal_id],
                )
                gaps.append(gap)

        for dep_id in goal.dependencies:
            gap = Gap(
                goal_id=goal.goal_id,
                title=f"Dependency: {dep_id}",
                description=f"Goal '{goal.title}' depends on '{dep_id}' which must be addressed first.",
                gap_type="dependency",
                severity=GapSeverity.LOW,
                domain=goal.domain,
                dependencies=[dep_id],
            )
            gaps.append(gap)

        return gaps


# ── Recommendation Engine ─────────────────────────────────────────────


class RecommendationEngine:
    """Generates recommendations from ranked gaps."""

    def __init__(self) -> None:
        from substrate.organism.domain_registry import DomainRegistry
        from substrate.organism.agent_registry import AgentRegistry

        self._domains = DomainRegistry()
        self._agents = AgentRegistry()

    def generate(
        self,
        gaps: list[Gap],
        goals: dict[str, Goal],
        historical_decisions: list[DecisionRecord] | None = None,
    ) -> list[Recommendation]:
        recs: list[Recommendation] = []
        history = historical_decisions or []

        effective_domains = self._effective_domain_set(history)

        for gap in gaps:
            goal = goals.get(gap.goal_id)
            domain_id = gap.domain or (goal.domain if goal else "engineering")
            domain_def = self._domains.get(domain_id)

            agents = []
            if domain_def:
                agents = list(domain_def.default_agent_types)
            if not agents:
                best = self._agents.best_agent_for(domain_id, "medium")
                if best:
                    agents = [best.agent_type_id]

            boost = 1.0
            if domain_id in effective_domains:
                boost = 1.1

            impact = self._estimate_impact(gap, goal)
            risk = self._estimate_risk(gap)

            rec = Recommendation(
                gap_id=gap.gap_id,
                title=f"Address: {gap.title}",
                rationale=gap.description,
                impact_estimate=impact,
                risk_estimate=risk,
                suggested_domain=domain_id,
                suggested_agents=agents,
                dependency_chain=list(gap.dependencies),
                priority_score=round(gap.priority_score * boost, 2),
            )
            recs.append(rec)

        recs.sort(key=lambda r: r.priority_score, reverse=True)
        return recs

    def _effective_domain_set(self, history: list[DecisionRecord]) -> set[str]:
        """Domains where past recommendations led to effective outcomes."""
        effective: dict[str, int] = {}
        total: dict[str, int] = {}
        for dec in history:
            domain = dec.goal_id.split("-")[0] if dec.goal_id else ""
            if not domain:
                continue
            total[domain] = total.get(domain, 0) + 1
            if dec.was_effective:
                effective[domain] = effective.get(domain, 0) + 1
        return {d for d, count in effective.items() if count / max(total.get(d, 1), 1) > 0.5}

    def _estimate_impact(self, gap: Gap, goal: Goal | None) -> str:
        if gap.severity == GapSeverity.CRITICAL:
            return "critical — blocks core goal progress"
        if gap.severity == GapSeverity.HIGH:
            return "high — significant advancement toward goal"
        if goal and goal.priority >= 80:
            return "high — supports high-priority goal"
        if gap.severity == GapSeverity.MEDIUM:
            return "medium — meaningful progress"
        return "low — incremental improvement"

    def _estimate_risk(self, gap: Gap) -> str:
        if gap.severity == GapSeverity.CRITICAL:
            return "medium — critical gaps often have complex root causes"
        if gap.gap_type == "blocker":
            return "medium — blockers may require investigation"
        if gap.gap_type == "dependency":
            return "low — dependency resolution is well-understood"
        return "low — straightforward gap closure"


# ── Strategic Gap Engine (Orchestrator) ────────────────────────────────


class StrategicGapEngine:
    """Top-level orchestrator composing all gap analysis components.

    Consumes existing UMH primitives. Produces gaps, priorities,
    recommendations, and candidate WorkPackets for operator approval.
    """

    def __init__(
        self,
        goal_registry: GoalRegistry | None = None,
        store_path: str | None = None,
    ) -> None:
        _ensure_dirs()
        self._goals = goal_registry or GoalRegistry()
        self._detector = GapDetector()
        self._recommender = RecommendationEngine()
        self._store = store_path or _data_dir()
        self._decisions: list[DecisionRecord] = []
        self._load_decisions()

    def _load_decisions(self) -> None:
        path = os.path.join(self._store, "decisions.jsonl")
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    self._decisions.append(DecisionRecord.from_dict(json.loads(line)))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("failed to load decisions: %s", e)

    def _save_decisions(self) -> None:
        path = os.path.join(self._store, "decisions.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            for d in self._decisions:
                f.write(json.dumps(d.to_dict()) + "\n")

    @property
    def goal_registry(self) -> GoalRegistry:
        return self._goals

    def analyze(self) -> dict[str, Any]:
        """Full analysis cycle: reality → gaps → priorities → recommendations."""

        reality = self._get_reality()
        active_packets = self._get_active_packets()
        active_goals = self._goals.active_goals()

        all_gaps: list[Gap] = []
        goal_map: dict[str, Goal] = {}

        for goal in active_goals:
            goal_map[goal.goal_id] = goal
            goal_gaps = self._detector.detect_gaps(
                goal,
                reality,
                active_packets,
            )
            all_gaps.extend(goal_gaps)

        for gap in all_gaps:
            goal = goal_map.get(gap.goal_id)
            gap.priority_score = score_gap(gap, goal, all_gaps)

        all_gaps.sort(key=lambda g: g.priority_score, reverse=True)

        recommendations = self._recommender.generate(
            all_gaps,
            goal_map,
            self._decisions,
        )

        self._persist_gaps(all_gaps)
        self._persist_recommendations(recommendations)

        return {
            "reality": reality,
            "goals": [g.to_dict() for g in active_goals],
            "gaps": [g.to_dict() for g in all_gaps],
            "gap_count": len(all_gaps),
            "recommendations": [r.to_dict() for r in recommendations],
            "recommendation_count": len(recommendations),
            "top_recommendation": recommendations[0].to_dict() if recommendations else None,
            "analyzed_at": time.time(),
        }

    def get_top_recommendations(self, limit: int = 5) -> list[Recommendation]:
        """Return the top N recommendations from last analysis."""
        path = os.path.join(self._store, "recommendations")
        recs: list[Recommendation] = []
        if not os.path.isdir(path):
            return recs
        for fname in sorted(os.listdir(path), reverse=True):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(path, fname)) as f:
                    d = json.loads(f.read())
                rec = Recommendation.from_dict(d)
                if rec.status == RecommendationStatus.PENDING:
                    recs.append(rec)
            except (json.JSONDecodeError, OSError):
                continue
            if len(recs) >= limit:
                break
        recs.sort(key=lambda r: r.priority_score, reverse=True)
        return recs[:limit]

    def approve_recommendation(
        self,
        recommendation_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Approve a recommendation and convert it into a governed WorkPacket."""
        rec = self._load_recommendation(recommendation_id)
        if not rec:
            return {"success": False, "error": f"recommendation {recommendation_id} not found"}

        from substrate.organism.empire_router import EmpireRouter

        router = EmpireRouter()
        routing = router.route(
            intent=rec.title.removeprefix("Address: "),
            desired_end_state=rec.rationale,
        )

        rec.status = RecommendationStatus.CONVERTED
        rec.decided_at = time.time()
        if routing.work_packets:
            rec.converted_packet_id = routing.work_packets[0].get("packet_id", "")
        self._save_recommendation(rec)

        decision = DecisionRecord(
            recommendation_id=rec.recommendation_id,
            gap_id=rec.gap_id,
            goal_id=self._gap_to_goal_id(rec.gap_id),
            action="approved",
            reason=reason,
            outcome_packet_id=rec.converted_packet_id,
        )
        self._decisions.append(decision)
        self._save_decisions()

        return {
            "success": True,
            "recommendation_id": rec.recommendation_id,
            "routing": routing.to_dict(),
            "decision_id": decision.decision_id,
            "packet_id": rec.converted_packet_id,
        }

    def reject_recommendation(
        self,
        recommendation_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Reject a recommendation with reasoning for future learning."""
        rec = self._load_recommendation(recommendation_id)
        if not rec:
            return {"success": False, "error": f"recommendation {recommendation_id} not found"}

        rec.status = RecommendationStatus.REJECTED
        rec.decision_reason = reason
        rec.decided_at = time.time()
        self._save_recommendation(rec)

        decision = DecisionRecord(
            recommendation_id=rec.recommendation_id,
            gap_id=rec.gap_id,
            goal_id=self._gap_to_goal_id(rec.gap_id),
            action="rejected",
            reason=reason,
            was_effective=False,
        )
        self._decisions.append(decision)
        self._save_decisions()

        return {
            "success": True,
            "recommendation_id": rec.recommendation_id,
            "decision_id": decision.decision_id,
        }

    def record_outcome(
        self,
        decision_id: str,
        was_effective: bool,
        summary: str = "",
    ) -> dict[str, Any]:
        """Record whether a decision led to effective outcome (learning loop)."""
        for dec in self._decisions:
            if dec.decision_id == decision_id:
                dec.was_effective = was_effective
                dec.outcome_summary = summary
                self._save_decisions()
                return {
                    "success": True,
                    "decision_id": decision_id,
                    "was_effective": was_effective,
                }
        return {"success": False, "error": f"decision {decision_id} not found"}

    def get_decision_history(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._decisions]

    # ── Private helpers ────────────────────────────────────────────

    def _get_reality(self) -> dict[str, Any]:
        try:
            from substrate.organism.empire_router import EmpireRouter

            router = EmpireRouter()
            return router.get_reality_snapshot().to_dict()
        except Exception as e:
            logger.error("failed to get reality snapshot: %s", e)
            return {
                "active_domains": [],
                "active_loops": [],
                "blocked_items": [],
                "open_approvals": 0,
                "recent_outcomes": [],
                "current_phase": "",
                "next_best_actions": [],
            }

    def _get_active_packets(self) -> list[dict[str, Any]]:
        try:
            from substrate.organism.universal_work_queue import UniversalWorkQueue

            q = UniversalWorkQueue()
            return [p.to_dict() for p in q.all_packets()]
        except Exception as e:
            logger.error("failed to get active packets: %s", e)
            return []

    def _persist_gaps(self, gaps: list[Gap]) -> None:
        gap_dir = os.path.join(self._store, "gaps")
        os.makedirs(gap_dir, exist_ok=True)
        for gap in gaps:
            path = os.path.join(gap_dir, f"{gap.gap_id}.json")
            with open(path, "w") as f:
                json.dump(gap.to_dict(), f, indent=2)

    def _persist_recommendations(self, recs: list[Recommendation]) -> None:
        rec_dir = os.path.join(self._store, "recommendations")
        os.makedirs(rec_dir, exist_ok=True)
        for rec in recs:
            path = os.path.join(rec_dir, f"{rec.recommendation_id}.json")
            with open(path, "w") as f:
                json.dump(rec.to_dict(), f, indent=2)

    def _load_recommendation(self, rec_id: str) -> Recommendation | None:
        path = os.path.join(self._store, "recommendations", f"{rec_id}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                return Recommendation.from_dict(json.loads(f.read()))
        except (json.JSONDecodeError, OSError):
            return None

    def _save_recommendation(self, rec: Recommendation) -> None:
        path = os.path.join(self._store, "recommendations", f"{rec.recommendation_id}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(rec.to_dict(), f, indent=2)

    def _gap_to_goal_id(self, gap_id: str) -> str:
        gap_path = os.path.join(self._store, "gaps", f"{gap_id}.json")
        if os.path.exists(gap_path):
            try:
                with open(gap_path) as f:
                    return json.loads(f.read()).get("goal_id", "")
            except (json.JSONDecodeError, OSError):
                pass
        return ""
