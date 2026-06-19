"""C22.1 — Production Planning Runtime.

Converts any "Build X" intent into a complete professional software
lifecycle plan — automatically including architecture, testing, security,
observability, deployment, review, documentation, and recovery.

The user says "Build X." The organism knows everything else that must happen.

Composes:
  - WorkPacketEngine  — decompose_intent_to_batch() for packet creation
  - GovernanceRuntime — risk classification
  - TradeoffIntelligenceEngine — displacement analysis
  - TrajectoryIntelligenceRuntime — forecasting for prioritization

Deterministic. No LLM calls. No mutation of composed runtimes.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────


class ProductionDiscipline(str, Enum):
    """Every professional software lifecycle discipline.
    "Build X" automatically includes ALL of these."""

    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    SECURITY = "security"
    OBSERVABILITY = "observability"
    DEPLOYMENT = "deployment"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    RECOVERY = "recovery"


class ProductionType(str, Enum):
    """Deterministic classification of a production request."""

    FULL_PRODUCT = "full_product"
    FEATURE = "feature"
    FIX = "fix"
    REFACTOR = "refactor"
    INFRASTRUCTURE = "infrastructure"
    MIGRATION = "migration"
    AUTOMATION = "automation"
    DOCUMENTATION = "documentation"


@dataclass
class ProductionPlan:
    """Complete production plan with lifecycle disciplines."""

    plan_id: str = ""
    goal: str = ""
    target: str = ""
    production_type: str = ""
    packets: list[dict[str, Any]] = field(default_factory=list)
    dependency_order: list[str] = field(default_factory=list)
    disciplines_covered: list[str] = field(default_factory=list)
    disciplines_deferred: list[str] = field(default_factory=list)
    tradeoff_analysis: dict[str, Any] = field(default_factory=dict)
    risk_summary: dict[str, Any] = field(default_factory=dict)
    estimated_roles: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DisciplinePacket:
    """A work packet generated for a specific discipline."""

    discipline: str = ""
    label: str = ""
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    risk_class: str = "low"
    estimated_effort: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Templates ────────────────────────────────────────────────────────

_PRODUCTION_TEMPLATES: dict[str, list[tuple[str, str, str]]] = {
    "full_product": [
        ("architecture", "Architecture & Design", "Define system architecture, component boundaries, and data flow"),
        ("implementation", "Core Implementation", "Implement core functionality according to architecture"),
        ("testing", "Test Suite", "Unit tests, integration tests, and acceptance tests"),
        ("security", "Security Review", "Security audit, dependency scan, secrets validation"),
        ("observability", "Observability Setup", "Logging, monitoring, alerting, and tracing"),
        ("deployment", "Deployment Pipeline", "CI/CD, containerization, and deployment config"),
        ("review", "Code Review", "Peer review, architecture review, and proof package"),
        ("documentation", "Documentation", "API docs, architecture docs, and runbooks"),
        ("recovery", "Recovery Plan", "Rollback procedures, data recovery, and incident response"),
    ],
    "feature": [
        ("architecture", "Feature Design", "Design feature within existing architecture"),
        ("implementation", "Implementation", "Implement the feature"),
        ("testing", "Tests", "Unit and integration tests for the feature"),
        ("review", "Review", "Code review and proof package"),
    ],
    "fix": [
        ("architecture", "Root Cause Analysis", "Identify root cause and scope of the fix"),
        ("implementation", "Fix", "Implement the fix"),
        ("testing", "Regression Tests", "Tests ensuring fix works and no regressions"),
        ("review", "Verification", "Verify fix resolves the issue"),
    ],
    "refactor": [
        ("architecture", "Impact Analysis", "Analyze impact scope and refactoring strategy"),
        ("implementation", "Refactor", "Execute the refactoring"),
        ("testing", "Tests", "Ensure all existing tests still pass, add missing coverage"),
        ("review", "Review", "Architectural review of refactored code"),
    ],
    "infrastructure": [
        ("architecture", "Infrastructure Design", "Design infrastructure components and topology"),
        ("implementation", "Implementation", "Build infrastructure components"),
        ("security", "Security Hardening", "Network policies, access control, encryption"),
        ("observability", "Monitoring Setup", "Health checks, dashboards, alerts"),
        ("deployment", "Deployment", "Infrastructure provisioning and deployment"),
        ("recovery", "Recovery Plan", "Disaster recovery and failover procedures"),
    ],
    "migration": [
        ("architecture", "Migration Plan", "Schema changes, data mapping, rollback strategy"),
        ("implementation", "Migration Execution", "Execute migration steps"),
        ("testing", "Migration Tests", "Verify data integrity post-migration"),
        ("security", "Security Validation", "Ensure no data exposure during migration"),
        ("deployment", "Cutover Plan", "Zero-downtime cutover and verification"),
        ("recovery", "Rollback Plan", "Detailed rollback procedure if migration fails"),
    ],
    "automation": [
        ("architecture", "Automation Design", "Define triggers, workflow, and error handling"),
        ("implementation", "Implementation", "Build the automation"),
        ("testing", "Tests", "Test automation under normal and failure conditions"),
        ("observability", "Monitoring", "Alerting on automation failures"),
        ("review", "Review", "Review automation logic and edge cases"),
    ],
    "documentation": [
        ("architecture", "Documentation Plan", "Scope, audience, and structure"),
        ("implementation", "Content Creation", "Write the documentation"),
        ("review", "Review", "Technical accuracy and completeness review"),
    ],
}

# Keyword patterns for deterministic production type classification
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "fix": [
        "fix", "bug", "broken", "crash", "error", "fail", "issue",
        "regression", "patch", "hotfix", "repair", "resolve",
    ],
    "refactor": [
        "refactor", "reorganize", "restructure", "clean up", "cleanup",
        "simplify", "consolidate", "decouple", "extract", "split",
        "decompose", "modularize",
    ],
    "infrastructure": [
        "infrastructure", "infra", "ci/cd", "pipeline", "docker",
        "kubernetes", "deploy", "server", "hosting", "database",
        "migration script", "terraform", "ansible", "nginx",
        "reverse proxy", "load balancer", "cdn",
    ],
    "migration": [
        "migrate", "migration", "upgrade version", "move from",
        "transition to", "convert from", "port from", "schema change",
        "data migration",
    ],
    "automation": [
        "automate", "automation", "cron", "scheduled", "script",
        "workflow", "bot", "scraper", "webhook handler",
    ],
    "documentation": [
        "document", "documentation", "docs", "readme", "wiki",
        "runbook", "api doc", "architecture doc",
    ],
    "feature": [
        "add", "create", "build", "implement", "new feature",
        "introduce", "enable", "support", "integrate",
    ],
    "full_product": [
        "full product", "new product", "new app", "new application",
        "new service", "new system", "from scratch", "greenfield",
        "mvp", "prototype", "proof of concept", "poc",
    ],
}

# Priority order for classification — more specific types first
_TYPE_PRIORITY = [
    "full_product", "migration", "infrastructure", "automation",
    "documentation", "fix", "refactor", "feature",
]

# Role estimation per discipline
_DISCIPLINE_ROLES: dict[str, list[dict[str, str]]] = {
    "architecture": [{"role": "architect", "responsibility": "design decisions"}],
    "implementation": [{"role": "contributor", "responsibility": "code production"}],
    "testing": [{"role": "contributor", "responsibility": "test authoring"}],
    "security": [{"role": "reviewer", "responsibility": "security audit"}],
    "observability": [{"role": "lead", "responsibility": "monitoring setup"}],
    "deployment": [{"role": "lead", "responsibility": "deployment management"}],
    "review": [{"role": "reviewer", "responsibility": "code review"}],
    "documentation": [{"role": "contributor", "responsibility": "documentation"}],
    "recovery": [{"role": "architect", "responsibility": "recovery planning"}],
}

# Risk keywords for deterministic risk classification
_RISK_KEYWORDS: dict[str, list[str]] = {
    "high": [
        "production", "database", "migration", "security", "auth",
        "payment", "delete", "drop", "schema", "breaking change",
        "critical", "user data", "encryption",
    ],
    "medium": [
        "refactor", "api", "endpoint", "deploy", "integration",
        "infrastructure", "service", "config", "upgrade",
    ],
    "low": [
        "test", "doc", "readme", "comment", "style", "format",
        "lint", "typo", "rename", "log",
    ],
}


# ── Runtime ──────────────────────────────────────────────────────────


class ProductionPlanningRuntime:
    """Converts 'Build X' intent into governed production plans.

    Wraps WorkPacketEngine for packet creation, adds production-type
    classification, automatic discipline expansion, tradeoff analysis,
    and role estimation. All deterministic — no LLM calls.
    """

    def __init__(
        self,
        work_packet_engine: Any | None = None,
        governance_runtime: Any | None = None,
        tradeoff_engine: Any | None = None,
        trajectory_runtime: Any | None = None,
    ) -> None:
        self._work_packet_engine = work_packet_engine
        self._governance_runtime = governance_runtime
        self._tradeoff_engine = tradeoff_engine
        self._trajectory_runtime = trajectory_runtime
        self._plans: list[ProductionPlan] = []

    # ── Lazy subsystem access ────────────────────────────────────

    @property
    def _packets(self) -> Any | None:
        if self._work_packet_engine is None:
            try:
                from substrate.organism.work_packet_engine import WorkPacketEngine
                self._work_packet_engine = WorkPacketEngine()
            except Exception:
                logger.debug("production_planning: could not lazy-load WorkPacketEngine")
        return self._work_packet_engine

    @property
    def _governance(self) -> Any | None:
        if self._governance_runtime is None:
            try:
                from substrate.organism.governance_runtime import GovernanceRuntime
                self._governance_runtime = GovernanceRuntime()
            except Exception:
                logger.debug("production_planning: could not lazy-load GovernanceRuntime")
        return self._governance_runtime

    @property
    def _tradeoff(self) -> Any | None:
        if self._tradeoff_engine is None:
            try:
                from substrate.organism.tradeoff_intelligence_engine import (
                    TradeoffIntelligenceEngine,
                )
                self._tradeoff_engine = TradeoffIntelligenceEngine()
            except Exception:
                logger.debug("production_planning: could not lazy-load TradeoffIntelligenceEngine")
        return self._tradeoff_engine

    @property
    def _trajectory(self) -> Any | None:
        if self._trajectory_runtime is None:
            try:
                from substrate.organism.trajectory_intelligence_runtime import (
                    TrajectoryIntelligenceRuntime,
                )
                self._trajectory_runtime = TrajectoryIntelligenceRuntime()
            except Exception:
                logger.debug("production_planning: could not lazy-load TrajectoryIntelligenceRuntime")
        return self._trajectory_runtime

    # ── Classification ───────────────────────────────────────────

    def classify_production_type(self, goal: str) -> str:
        """Deterministic keyword-based production type classification.

        Checks more specific types first (full_product, migration) before
        falling back to general types (feature).
        """
        goal_lower = goal.lower()

        scores: dict[str, int] = {}
        for ptype in _TYPE_PRIORITY:
            keywords = _TYPE_KEYWORDS.get(ptype, [])
            score = sum(1 for kw in keywords if kw in goal_lower)
            if score > 0:
                scores[ptype] = score

        if not scores:
            return ProductionType.FEATURE.value

        # Return highest-scoring type, preferring earlier in priority list
        max_score = max(scores.values())
        for ptype in _TYPE_PRIORITY:
            if scores.get(ptype, 0) == max_score:
                return ptype

        return ProductionType.FEATURE.value

    def classify_risk(self, goal: str) -> str:
        """Deterministic risk classification from goal text."""
        goal_lower = goal.lower()

        for level in ["high", "medium", "low"]:
            keywords = _RISK_KEYWORDS.get(level, [])
            if any(kw in goal_lower for kw in keywords):
                return level

        return "low"

    # ── Discipline expansion ─────────────────────────────────────

    def required_disciplines(self, production_type: str) -> list[str]:
        """Return all disciplines required for this production type."""
        template = _PRODUCTION_TEMPLATES.get(production_type, [])
        if not template:
            template = _PRODUCTION_TEMPLATES["feature"]
        return [entry[0] for entry in template]

    def template_for_type(self, production_type: str) -> list[DisciplinePacket]:
        """Expand a production type into discipline packets."""
        template = _PRODUCTION_TEMPLATES.get(production_type, [])
        if not template:
            template = _PRODUCTION_TEMPLATES["feature"]

        packets: list[DisciplinePacket] = []
        prev_disciplines: list[str] = []

        for discipline, label, description in template:
            pkt = DisciplinePacket(
                discipline=discipline,
                label=label,
                description=description,
                depends_on=list(prev_disciplines),
                risk_class=self._discipline_risk(discipline),
                estimated_effort=self._discipline_effort(discipline),
            )
            packets.append(pkt)
            prev_disciplines.append(discipline)

        return packets

    def _discipline_risk(self, discipline: str) -> str:
        """Map discipline to inherent risk level."""
        high_risk = {"security", "deployment", "recovery"}
        medium_risk = {"architecture", "observability"}
        if discipline in high_risk:
            return "high"
        if discipline in medium_risk:
            return "medium"
        return "low"

    def _discipline_effort(self, discipline: str) -> str:
        """Map discipline to estimated effort."""
        high_effort = {"implementation", "testing", "architecture"}
        low_effort = {"review", "documentation"}
        if discipline in high_effort:
            return "high"
        if discipline in low_effort:
            return "low"
        return "medium"

    # ── Role estimation ──────────────────────────────────────────

    def estimate_roles(self, disciplines: list[str]) -> list[dict[str, Any]]:
        """Estimate which org roles are needed for the given disciplines."""
        seen_roles: set[str] = set()
        roles: list[dict[str, Any]] = []

        for discipline in disciplines:
            for role_entry in _DISCIPLINE_ROLES.get(discipline, []):
                role_name = role_entry["role"]
                if role_name not in seen_roles:
                    seen_roles.add(role_name)
                    roles.append({
                        "role": role_name,
                        "disciplines": [discipline],
                        "responsibility": role_entry["responsibility"],
                    })
                else:
                    for r in roles:
                        if r["role"] == role_name:
                            r["disciplines"].append(discipline)
                            break

        return roles

    # ── Tradeoff integration ─────────────────────────────────────

    def tradeoff_preview(self, goal: str) -> dict[str, Any]:
        """Run tradeoff analysis for this production goal."""
        if self._tradeoff is None:
            return {
                "available": False,
                "reason": "TradeoffIntelligenceEngine not available",
            }

        try:
            snapshot = self._tradeoff.snapshot()
            return {
                "available": True,
                "overall_severity": snapshot.overall_severity,
                "active_tradeoffs": len(snapshot.active_tradeoffs),
                "resource_contention": snapshot.resource_contention,
            }
        except Exception:
            logger.debug("production_planning: tradeoff preview failed")
            return {"available": False, "reason": "tradeoff analysis failed"}

    # ── Risk summary ─────────────────────────────────────────────

    def _build_risk_summary(
        self, goal: str, production_type: str, disciplines: list[str]
    ) -> dict[str, Any]:
        """Build deterministic risk summary."""
        goal_risk = self.classify_risk(goal)

        # Check governance health if available
        governance_health = "unknown"
        if self._governance is not None:
            try:
                governance_health = self._governance.health().value
            except Exception:
                logger.debug("production_planning: governance health check failed")

        high_risk_disciplines = [
            d for d in disciplines
            if self._discipline_risk(d) in ("high", "medium")
        ]

        return {
            "overall_risk": goal_risk,
            "governance_health": governance_health,
            "high_risk_disciplines": high_risk_disciplines,
            "discipline_count": len(disciplines),
            "production_type": production_type,
        }

    # ── Trajectory integration ───────────────────────────────────

    def _get_trajectory_context(self) -> dict[str, Any]:
        """Get forecasting context if available."""
        if self._trajectory is None:
            return {"available": False}

        try:
            work_forecast = self._trajectory.forecast_work()
            return {
                "available": True,
                "work_velocity_status": work_forecast.status,
                "work_confidence": round(work_forecast.confidence, 4),
            }
        except Exception:
            logger.debug("production_planning: trajectory context failed")
            return {"available": False}

    # ── Core planning ────────────────────────────────────────────

    def plan_production(
        self,
        goal: str,
        target: str = "substrate",
        constraints: list[str] | None = None,
        skip_disciplines: list[str] | None = None,
    ) -> ProductionPlan:
        """Convert a production goal into a complete governed plan.

        1. Classify production type (deterministic keyword matching)
        2. Select template and expand disciplines
        3. Generate discipline packets with dependency ordering
        4. Apply constraints (skip disciplines if explicitly deferred)
        5. Wrap WorkPacketEngine for actual packet creation
        6. Run tradeoff and risk analysis
        7. Estimate required org roles
        """
        plan_id = f"pp-{uuid.uuid4().hex[:12]}"
        production_type = self.classify_production_type(goal)
        discipline_packets = self.template_for_type(production_type)

        # Apply skip_disciplines if any were explicitly deferred
        deferred: list[str] = []
        if skip_disciplines:
            kept: list[DisciplinePacket] = []
            for dp in discipline_packets:
                if dp.discipline in skip_disciplines:
                    deferred.append(
                        f"{dp.discipline}: explicitly deferred by constraints"
                    )
                else:
                    kept.append(dp)
            discipline_packets = kept

        # Build dependency order
        disciplines_covered = [dp.discipline for dp in discipline_packets]
        dependency_order = [dp.discipline for dp in discipline_packets]

        # Generate work packets through WorkPacketEngine if available
        raw_packets: list[dict[str, Any]] = []
        if self._packets is not None:
            try:
                for dp in discipline_packets:
                    intent = f"{dp.label}: {dp.description} (for: {goal})"
                    batch = self._packets.decompose_intent_to_batch(
                        user_intent=intent,
                        desired_end_state=f"{dp.label} complete for {goal}",
                        constraints=constraints,
                        idempotency_key=f"{plan_id}-{dp.discipline}",
                    )
                    raw_packets.append({
                        "discipline": dp.discipline,
                        "label": dp.label,
                        "batch_id": batch.get("batch_id", ""),
                        "packet_count": batch.get("created_count", 0),
                        "parent_packet": batch.get("parent_packet", {}),
                        "child_packets": batch.get("child_packets", []),
                        "already_existed": batch.get("already_existed", False),
                    })
            except Exception:
                logger.debug("production_planning: packet generation failed, using templates")
                raw_packets = [dp.to_dict() for dp in discipline_packets]
        else:
            raw_packets = [dp.to_dict() for dp in discipline_packets]

        # Estimate roles
        estimated_roles = self.estimate_roles(disciplines_covered)

        # Risk summary
        risk_summary = self._build_risk_summary(goal, production_type, disciplines_covered)

        # Tradeoff analysis
        tradeoff = self.tradeoff_preview(goal)

        plan = ProductionPlan(
            plan_id=plan_id,
            goal=goal,
            target=target,
            production_type=production_type,
            packets=raw_packets,
            dependency_order=dependency_order,
            disciplines_covered=disciplines_covered,
            disciplines_deferred=deferred,
            tradeoff_analysis=tradeoff,
            risk_summary=risk_summary,
            estimated_roles=estimated_roles,
            generated_at=time.time(),
        )

        self._plans.append(plan)
        return plan

    # ── Query methods ────────────────────────────────────────────

    def recent_plans(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent production plans."""
        plans = sorted(self._plans, key=lambda p: p.generated_at, reverse=True)
        return [p.to_dict() for p in plans[:limit]]

    def plan_by_id(self, plan_id: str) -> ProductionPlan | None:
        """Look up a plan by ID."""
        for plan in self._plans:
            if plan.plan_id == plan_id:
                return plan
        return None

    def plans_by_target(self, target: str) -> list[dict[str, Any]]:
        """Return plans for a specific target type."""
        return [
            p.to_dict() for p in self._plans
            if p.target == target
        ]

    def all_production_types(self) -> list[str]:
        """Return all known production types."""
        return [pt.value for pt in ProductionType]

    def all_disciplines(self) -> list[str]:
        """Return all known disciplines."""
        return [d.value for d in ProductionDiscipline]

    def template_summary(self) -> dict[str, list[str]]:
        """Return template → disciplines mapping."""
        result: dict[str, list[str]] = {}
        for tname, entries in _PRODUCTION_TEMPLATES.items():
            result[tname] = [e[0] for e in entries]
        return result

    # ── Summary ──────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Snapshot of the planning runtime state."""
        plans_by_type: dict[str, int] = {}
        plans_by_target: dict[str, int] = {}
        for plan in self._plans:
            plans_by_type[plan.production_type] = (
                plans_by_type.get(plan.production_type, 0) + 1
            )
            plans_by_target[plan.target] = (
                plans_by_target.get(plan.target, 0) + 1
            )

        trajectory_ctx = self._get_trajectory_context()

        return {
            "total_plans": len(self._plans),
            "plans_by_type": plans_by_type,
            "plans_by_target": plans_by_target,
            "available_types": self.all_production_types(),
            "available_disciplines": self.all_disciplines(),
            "trajectory_context": trajectory_ctx,
            "generated_at": time.time(),
        }
