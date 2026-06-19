"""C22.5 — Product Factory Runtime.

Given ANY software target definition, generate: goal tree, production plan,
capability requirements. Handles all target types through the same pipeline —
self-build and projection-build are the same capability.

Target hierarchy (explicit and equal):
  SUBSTRATE   — UMH itself (self-build)
  PROJECTION  — EOS / LOS / COS (first-class, not secondary)
  CLIENT_PRODUCT — client SaaS products
  INTERNAL_TOOL  — internal tooling
  WEBSITE     — marketing sites, landing pages
  AUTOMATION  — scripts, pipelines, integrations

Composes:
  - ProjectionIntegrationRuntime — projection-specific gap analysis
  - ProductionPlanningRuntime    — packet generation via plan_production()
  - GovernanceRuntime            — policy evaluation
  - TradeoffIntelligenceEngine   — displacement analysis

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


class ProductGoalType(str, Enum):
    """Classification of goals within a product plan."""

    INFRASTRUCTURE = "infrastructure"
    FEATURE = "feature"
    INTEGRATION = "integration"
    MIGRATION = "migration"
    CAPABILITY = "capability"
    LAUNCH = "launch"


class ProductReadiness(str, Enum):
    """Overall readiness of a product for production."""

    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    NOT_STARTED = "not_started"


# Goal type keywords for deterministic classification
_GOAL_TYPE_KEYWORDS: dict[str, list[str]] = {
    "infrastructure": [
        "infra", "infrastructure", "hosting", "deploy", "ci/cd",
        "database", "server", "docker", "kubernetes", "terraform",
        "pipeline", "monitoring", "logging",
    ],
    "migration": [
        "migrate", "migration", "port", "convert", "upgrade",
        "schema change", "data migration", "move from",
    ],
    "integration": [
        "integrate", "integration", "connect", "api", "webhook",
        "plugin", "extension", "bridge", "adapter", "sync",
    ],
    "capability": [
        "capability", "enable", "support", "allow", "make possible",
        "runtime", "engine", "system", "subsystem", "framework",
    ],
    "launch": [
        "launch", "release", "ship", "deploy to production",
        "go live", "publish", "open to users", "public release",
        "ga", "general availability",
    ],
    "feature": [
        "add", "create", "build", "implement", "new", "feature",
        "introduce", "page", "dashboard", "component", "module",
        "screen", "workflow", "view",
    ],
}

_GOAL_TYPE_PRIORITY = [
    "launch", "migration", "infrastructure", "integration",
    "capability", "feature",
]


@dataclass
class ProductGoal:
    """A single goal within a product plan."""

    goal_id: str = ""
    product_id: str = ""
    target_type: str = ""
    goal_type: str = ProductGoalType.FEATURE.value
    title: str = ""
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    priority: int = 0
    risk_class: str = "low"

    def __post_init__(self) -> None:
        if not self.goal_id:
            self.goal_id = f"goal-{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "product_id": self.product_id,
            "target_type": self.target_type,
            "goal_type": self.goal_type,
            "title": self.title,
            "description": self.description,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "risk_class": self.risk_class,
        }


@dataclass
class ProductPlan:
    """Complete product plan: goal tree + production packets + capabilities."""

    product_id: str = ""
    product_name: str = ""
    target_type: str = ""
    goals: list[dict[str, Any]] = field(default_factory=list)
    production_packets: list[dict[str, Any]] = field(default_factory=list)
    capability_requirements: list[str] = field(default_factory=list)
    gap_analysis: dict[str, Any] = field(default_factory=dict)
    estimated_complexity: str = "medium"
    estimated_roles: list[str] = field(default_factory=list)
    generated_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.generated_at:
            self.generated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProductEntry:
    """A registered product tracked by the factory."""

    product_id: str = ""
    product_name: str = ""
    target_type: str = ""
    definition: dict[str, Any] = field(default_factory=dict)
    plan: ProductPlan | None = None
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.product_id:
            self.product_id = f"prod-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "target_type": self.target_type,
            "definition": self.definition,
            "plan": self.plan.to_dict() if self.plan else None,
            "created_at": self.created_at,
        }


@dataclass
class ProductFactorySnapshot:
    """Factory-wide snapshot across all registered products."""

    total_products: int = 0
    by_target_type: dict[str, int] = field(default_factory=dict)
    by_readiness: dict[str, int] = field(default_factory=dict)
    total_goals: int = 0
    total_packets: int = 0
    products: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Capability Requirements ──────────────────────────────────────────

_TARGET_CAPABILITIES: dict[str, list[str]] = {
    "substrate": [
        "python_runtime", "test_suite", "pre_commit_gates",
        "docker_services", "neon_database", "git_workflow",
    ],
    "projection": [
        "typescript_runtime", "react_build", "vite_dev_server",
        "tailwind_css", "express_backend", "drizzle_orm",
        "git_workflow", "neon_database",
    ],
    "client_product": [
        "typescript_runtime", "react_build", "vite_dev_server",
        "express_backend", "drizzle_orm", "git_workflow",
        "hosting", "domain_config", "ssl_cert",
    ],
    "internal_tool": [
        "python_runtime", "git_workflow", "test_suite",
    ],
    "website": [
        "html_css", "static_hosting", "domain_config",
        "ssl_cert", "analytics",
    ],
    "automation": [
        "python_runtime", "cron_scheduler", "git_workflow",
        "monitoring",
    ],
}


# ── Complexity Estimation ────────────────────────────────────────────

def _estimate_complexity(goals: list[ProductGoal]) -> str:
    """Deterministic complexity estimation from goal count and types."""
    if not goals:
        return "trivial"
    count = len(goals)
    has_infra = any(g.goal_type == "infrastructure" for g in goals)
    has_migration = any(g.goal_type == "migration" for g in goals)
    has_launch = any(g.goal_type == "launch" for g in goals)
    high_risk = sum(1 for g in goals if g.risk_class == "high")

    if count >= 8 or (has_launch and has_infra) or high_risk >= 3:
        return "high"
    if count >= 4 or has_infra or has_migration or high_risk >= 1:
        return "medium"
    return "low"


def _classify_goal_type(title: str, description: str = "") -> str:
    """Deterministic goal type classification from keywords."""
    text = f"{title} {description}".lower()
    for gtype in _GOAL_TYPE_PRIORITY:
        keywords = _GOAL_TYPE_KEYWORDS.get(gtype, [])
        for kw in keywords:
            if kw in text:
                return gtype
    return ProductGoalType.FEATURE.value


def _classify_goal_risk(title: str, description: str = "") -> str:
    """Deterministic risk classification for a goal."""
    text = f"{title} {description}".lower()
    high_kw = [
        "production", "database", "migration", "security", "auth",
        "payment", "delete", "schema", "breaking", "critical",
        "user data", "encryption",
    ]
    medium_kw = [
        "api", "endpoint", "deploy", "integration", "infrastructure",
        "service", "config", "upgrade",
    ]
    for kw in high_kw:
        if kw in text:
            return "high"
    for kw in medium_kw:
        if kw in text:
            return "medium"
    return "low"


def _build_dependency_order(goals: list[ProductGoal]) -> list[str]:
    """Topological sort of goals by dependencies."""
    ordered: list[str] = []
    remaining = {g.goal_id: g for g in goals}
    resolved: set[str] = set()
    max_iterations = len(goals) * 2

    for _ in range(max_iterations):
        if not remaining:
            break
        progress = False
        for gid, goal in list(remaining.items()):
            deps_met = all(d in resolved for d in goal.dependencies)
            if deps_met:
                ordered.append(gid)
                resolved.add(gid)
                del remaining[gid]
                progress = True
        if not progress:
            ordered.extend(remaining.keys())
            break

    return ordered


def _estimate_roles(goals: list[ProductGoal]) -> list[str]:
    """Deterministic role estimation from goal types."""
    roles: set[str] = set()
    role_map = {
        "infrastructure": ["architect", "lead"],
        "feature": ["contributor", "reviewer"],
        "integration": ["architect", "contributor"],
        "migration": ["architect", "lead", "contributor"],
        "capability": ["architect", "contributor"],
        "launch": ["director", "lead"],
    }
    for goal in goals:
        for role in role_map.get(goal.goal_type, ["contributor"]):
            roles.add(role)
    if len(goals) >= 4:
        roles.add("director")
    return sorted(roles)


# ── Runtime ──────────────────────────────────────────────────────────


class ProductFactoryRuntime:
    """Given ANY software target definition, generate goal tree,
    production plan, and capability requirements.

    Self-build and projection-build are the same capability.
    The target is a parameter, not a code path.
    """

    def __init__(
        self,
        projection_integration: Any | None = None,
        production_planning: Any | None = None,
        governance_runtime: Any | None = None,
        tradeoff_engine: Any | None = None,
    ) -> None:
        self._projection_integration = projection_integration
        self._production_planning = production_planning
        self._governance_runtime = governance_runtime
        self._tradeoff_engine = tradeoff_engine
        self._products: dict[str, ProductEntry] = {}

    # ── Lazy subsystem access ────────────────────────────────────

    @property
    def _projections(self) -> Any | None:
        if self._projection_integration is None:
            try:
                from substrate.organism.projection_integration_runtime import (
                    ProjectionIntegrationRuntime,
                )
                self._projection_integration = ProjectionIntegrationRuntime()
            except Exception:
                logger.debug("product_factory: could not lazy-load ProjectionIntegrationRuntime")
        return self._projection_integration

    @property
    def _planning(self) -> Any | None:
        if self._production_planning is None:
            try:
                from substrate.organism.production_planning_runtime import (
                    ProductionPlanningRuntime,
                )
                self._production_planning = ProductionPlanningRuntime()
            except Exception:
                logger.debug("product_factory: could not lazy-load ProductionPlanningRuntime")
        return self._production_planning

    @property
    def _governance(self) -> Any | None:
        if self._governance_runtime is None:
            try:
                from substrate.organism.governance_runtime import GovernanceRuntime
                self._governance_runtime = GovernanceRuntime()
            except Exception:
                logger.debug("product_factory: could not lazy-load GovernanceRuntime")
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
                logger.debug("product_factory: could not lazy-load TradeoffIntelligenceEngine")
        return self._tradeoff_engine

    # ── Goal Tree Generation ─────────────────────────────────────

    def _build_goal_tree(
        self,
        product_id: str,
        target_type: str,
        raw_goals: list[dict[str, Any]],
    ) -> list[ProductGoal]:
        """Build typed, prioritized, risk-classified goal tree from raw definition."""
        goals: list[ProductGoal] = []
        for i, raw in enumerate(raw_goals):
            title = raw.get("title", "")
            desc = raw.get("description", "")
            goal_type = raw.get("type") or _classify_goal_type(title, desc)
            risk = raw.get("risk_class") or _classify_goal_risk(title, desc)
            deps = raw.get("dependencies", [])
            priority = raw.get("priority", i)

            goal = ProductGoal(
                goal_id=raw.get("id", f"goal-{uuid.uuid4().hex[:8]}"),
                product_id=product_id,
                target_type=target_type,
                goal_type=goal_type,
                title=title,
                description=desc,
                dependencies=deps,
                priority=priority,
                risk_class=risk,
            )
            goals.append(goal)
        return goals

    # ── Gap Analysis ─────────────────────────────────────────────

    def _projection_gap_analysis(self, product_id: str) -> dict[str, Any]:
        """Delegate gap analysis to ProjectionIntegrationRuntime for projections."""
        if not self._projections:
            return {"available": False, "reason": "ProjectionIntegrationRuntime unavailable"}

        try:
            gaps = self._projections.integration_gaps(product_id)
            readiness = self._projections.build_readiness(product_id)
            return {
                "available": True,
                "gaps": [g.to_dict() if hasattr(g, "to_dict") else g for g in gaps],
                "readiness": readiness.to_dict() if hasattr(readiness, "to_dict") else readiness,
                "gap_count": len(gaps),
                "critical_gaps": sum(
                    1 for g in gaps
                    if (g.severity if isinstance(g, dict) else getattr(g, "severity", "low")) in ("critical", "high")
                ),
            }
        except Exception as exc:
            logger.debug("product_factory: projection gap analysis failed: %s", exc)
            return {"available": False, "reason": str(exc)}

    def _generic_gap_analysis(
        self,
        target_type: str,
        goals: list[ProductGoal],
    ) -> dict[str, Any]:
        """Generic gap analysis for non-projection targets."""
        required_caps = _TARGET_CAPABILITIES.get(target_type, [])
        goal_types = {g.goal_type for g in goals}
        has_infra = "infrastructure" in goal_types

        missing_if_no_infra: list[str] = []
        if not has_infra and required_caps:
            missing_if_no_infra = [
                cap for cap in required_caps
                if cap in ("hosting", "domain_config", "ssl_cert", "static_hosting")
            ]

        return {
            "available": True,
            "required_capabilities": required_caps,
            "goal_coverage": sorted(goal_types),
            "missing_infrastructure_goals": missing_if_no_infra,
            "gap_count": len(missing_if_no_infra),
            "critical_gaps": 0,
        }

    # ── Tradeoff Analysis ────────────────────────────────────────

    def _tradeoff_analysis(self, product_id: str) -> dict[str, Any]:
        """Displacement analysis via TradeoffIntelligenceEngine."""
        if not self._tradeoff:
            return {"available": False}
        try:
            analysis = self._tradeoff.analyze(product_id)
            return analysis.to_dict() if hasattr(analysis, "to_dict") else {"available": True}
        except Exception as exc:
            logger.debug("product_factory: tradeoff analysis failed: %s", exc)
            return {"available": False, "reason": str(exc)}

    # ── Governance Evaluation ────────────────────────────────────

    def _governance_evaluation(self, goals: list[ProductGoal]) -> dict[str, Any]:
        """Policy evaluation via GovernanceRuntime."""
        if not self._governance:
            return {"available": False}
        try:
            health = self._governance.health()
            return {
                "available": True,
                "governance_health": health.value if hasattr(health, "value") else str(health),
                "high_risk_goals": sum(1 for g in goals if g.risk_class == "high"),
                "total_goals": len(goals),
            }
        except Exception as exc:
            logger.debug("product_factory: governance evaluation failed: %s", exc)
            return {"available": False, "reason": str(exc)}

    # ── Production Plan Generation ───────────────────────────────

    def _generate_production_packets(
        self,
        goals: list[ProductGoal],
        target_type: str,
    ) -> list[dict[str, Any]]:
        """Generate production packets for each goal via ProductionPlanningRuntime."""
        all_packets: list[dict[str, Any]] = []

        for goal in goals:
            if self._planning:
                try:
                    plan = self._planning.plan_production(
                        goal=goal.title,
                        target=target_type,
                        constraints={"goal_type": goal.goal_type, "risk_class": goal.risk_class},
                    )
                    if plan and hasattr(plan, "to_dict"):
                        plan_dict = plan.to_dict()
                        packets = plan_dict.get("packets", [])
                        for pkt in packets:
                            pkt["source_goal_id"] = goal.goal_id
                        all_packets.extend(packets)
                        continue
                except Exception as exc:
                    logger.debug("product_factory: planning failed for goal %s: %s", goal.goal_id, exc)

            all_packets.append({
                "packet_id": f"pkt-{uuid.uuid4().hex[:8]}",
                "title": goal.title,
                "description": goal.description,
                "goal_type": goal.goal_type,
                "risk_class": goal.risk_class,
                "source_goal_id": goal.goal_id,
                "target_type": target_type,
                "status": "planned",
            })

        return all_packets

    # ── Product Readiness ────────────────────────────────────────

    def _assess_readiness(self, entry: ProductEntry) -> str:
        """Determine readiness status for a product."""
        if not entry.plan:
            return ProductReadiness.NOT_STARTED.value

        plan = entry.plan
        if not plan.goals:
            return ProductReadiness.NOT_STARTED.value

        gap_count = plan.gap_analysis.get("critical_gaps", 0)
        if gap_count > 0:
            return ProductReadiness.BLOCKED.value

        if plan.production_packets:
            return ProductReadiness.READY.value

        return ProductReadiness.PARTIAL.value

    # ── Public API ───────────────────────────────────────────────

    def generate_product_plan(
        self,
        product_id: str,
        product_definition: dict[str, Any],
    ) -> ProductPlan:
        """Generate a complete product plan from ANY target definition.

        Args:
            product_id: Unique product identifier.
            product_definition: Dict with keys:
                - name: str (product name)
                - target_type: str (ProductionTarget value)
                - goals: list[dict] with title, description, type (optional)
                - constraints: dict (optional)

        Returns:
            ProductPlan with goal tree, packets, capabilities, gap analysis.
        """
        name = product_definition.get("name", product_id)
        target_type = product_definition.get("target_type", "feature")
        raw_goals = product_definition.get("goals", [])
        constraints = product_definition.get("constraints", {})

        # If no goals provided, create a single goal from the product name
        if not raw_goals:
            raw_goals = [{
                "title": f"Build {name}",
                "description": product_definition.get("description", ""),
            }]

        # Build typed goal tree
        goals = self._build_goal_tree(product_id, target_type, raw_goals)

        # Sort by priority
        goals.sort(key=lambda g: g.priority)

        # Dependency ordering
        dep_order = _build_dependency_order(goals)

        # Gap analysis — projection-specific or generic
        if target_type == "projection":
            gap_analysis = self._projection_gap_analysis(product_id)
        else:
            gap_analysis = self._generic_gap_analysis(target_type, goals)

        # Generate production packets
        packets = self._generate_production_packets(goals, target_type)

        # Capability requirements
        capability_reqs = list(_TARGET_CAPABILITIES.get(target_type, []))

        # Complexity and roles
        complexity = _estimate_complexity(goals)
        roles = _estimate_roles(goals)

        # Governance check — always record result (even failures)
        gov_eval = self._governance_evaluation(goals)
        if self._governance_runtime is not None:
            gap_analysis["governance"] = gov_eval

        # Tradeoff analysis — always record result (even failures)
        tradeoff = self._tradeoff_analysis(product_id)
        if self._tradeoff_engine is not None:
            gap_analysis["tradeoff"] = tradeoff

        plan = ProductPlan(
            product_id=product_id,
            product_name=name,
            target_type=target_type,
            goals=[g.to_dict() for g in goals],
            production_packets=packets,
            capability_requirements=capability_reqs,
            gap_analysis=gap_analysis,
            estimated_complexity=complexity,
            estimated_roles=roles,
            generated_at=time.time(),
        )

        # Register the product
        entry = ProductEntry(
            product_id=product_id,
            product_name=name,
            target_type=target_type,
            definition=product_definition,
            plan=plan,
        )
        self._products[product_id] = entry

        logger.debug(
            "product_factory: generated plan for %s (%s) — %d goals, %d packets",
            name, target_type, len(goals), len(packets),
        )
        return plan

    def list_products(self) -> list[dict[str, Any]]:
        """List all registered products."""
        return [
            {
                "product_id": entry.product_id,
                "product_name": entry.product_name,
                "target_type": entry.target_type,
                "has_plan": entry.plan is not None,
                "readiness": self._assess_readiness(entry),
                "goal_count": len(entry.plan.goals) if entry.plan else 0,
                "packet_count": len(entry.plan.production_packets) if entry.plan else 0,
                "created_at": entry.created_at,
            }
            for entry in self._products.values()
        ]

    def product_readiness(self, product_id: str) -> dict[str, Any]:
        """Detailed readiness assessment for a specific product."""
        entry = self._products.get(product_id)
        if not entry:
            return {
                "product_id": product_id,
                "readiness": ProductReadiness.NOT_STARTED.value,
                "reason": "product not registered",
            }

        readiness = self._assess_readiness(entry)
        result: dict[str, Any] = {
            "product_id": product_id,
            "product_name": entry.product_name,
            "target_type": entry.target_type,
            "readiness": readiness,
        }

        if entry.plan:
            result["goal_count"] = len(entry.plan.goals)
            result["packet_count"] = len(entry.plan.production_packets)
            result["complexity"] = entry.plan.estimated_complexity
            result["capability_requirements"] = entry.plan.capability_requirements
            result["gap_analysis"] = entry.plan.gap_analysis
            result["estimated_roles"] = entry.plan.estimated_roles
        else:
            result["reason"] = "no plan generated yet"

        return result

    def by_target_type(self, target_type: str) -> list[dict[str, Any]]:
        """Filter products by target type."""
        return [
            entry.to_dict()
            for entry in self._products.values()
            if entry.target_type == target_type
        ]

    def product_by_id(self, product_id: str) -> ProductEntry | None:
        """Get a product entry by ID."""
        return self._products.get(product_id)

    def goal_tree(self, product_id: str) -> list[dict[str, Any]]:
        """Get the goal tree for a specific product."""
        entry = self._products.get(product_id)
        if not entry or not entry.plan:
            return []
        return list(entry.plan.goals)

    def capability_requirements(self, product_id: str) -> list[str]:
        """Get capability requirements for a specific product."""
        entry = self._products.get(product_id)
        if not entry or not entry.plan:
            return list(_TARGET_CAPABILITIES.get("feature", []))
        return list(entry.plan.capability_requirements)

    def all_target_types(self) -> list[str]:
        """List all valid target types."""
        return [
            "substrate", "projection", "client_product",
            "internal_tool", "website", "automation",
        ]

    def snapshot(self) -> ProductFactorySnapshot:
        """Factory-wide snapshot across all products."""
        by_target: dict[str, int] = {}
        by_readiness: dict[str, int] = {}
        total_goals = 0
        total_packets = 0
        product_summaries: list[dict[str, Any]] = []

        for entry in self._products.values():
            tt = entry.target_type
            by_target[tt] = by_target.get(tt, 0) + 1

            readiness = self._assess_readiness(entry)
            by_readiness[readiness] = by_readiness.get(readiness, 0) + 1

            if entry.plan:
                total_goals += len(entry.plan.goals)
                total_packets += len(entry.plan.production_packets)

            product_summaries.append({
                "product_id": entry.product_id,
                "product_name": entry.product_name,
                "target_type": entry.target_type,
                "readiness": readiness,
            })

        return ProductFactorySnapshot(
            total_products=len(self._products),
            by_target_type=by_target,
            by_readiness=by_readiness,
            total_goals=total_goals,
            total_packets=total_packets,
            products=product_summaries,
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        """Concise factory summary for API/cockpit consumption."""
        snap = self.snapshot()
        return {
            "total_products": snap.total_products,
            "by_target_type": snap.by_target_type,
            "by_readiness": snap.by_readiness,
            "total_goals": snap.total_goals,
            "total_packets": snap.total_packets,
            "generated_at": snap.generated_at,
        }
