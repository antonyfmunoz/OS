"""Voice Query Engine — context-grounded query resolution.

Bridges IntentRouter classification to actual subsystem queries.
IntentRouter is the authority on route type. This engine only refines
within a route — it never overrides the classification.

Authority hierarchy:
  CommandRuntime (normalizes input)
      ↓
  IntentRouter (classifies route type)
      ↓
  VoiceQueryEngine (resolves OBSERVATION/CONVERSATION routes)

10 query domains, each backed by an existing subsystem:
  STATUS     → OperatorContextEngine
  SCREEN     → ScreenObservationEngine
  WORKSPACE  → WorkspaceTopologyEngine
  RESUME     → ContinuityEngine
  SERVICE    → ServiceFailureEngine
  NODE       → UMHNodeRegistry
  STATE      → StateCoherenceEngine
  REALITY    → RealityIntelligenceEngine
  ACTION     → ApprovalInterceptStore + ExecutionCoordinator
  HELP       → static capability list

All resolvers are read-only. No execution authority. No LLM calls.

Phase 35. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class QueryDomain(str, Enum):
    STATUS = "status"
    SCREEN = "screen"
    WORKSPACE = "workspace"
    RESUME = "resume"
    SERVICE = "service"
    NODE = "node"
    STATE = "state"
    REALITY = "reality"
    ACTION = "action"
    HELP = "help"


@dataclass
class QueryResolution:
    domain: str
    answer_text: str
    structured_data: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    resolved_at: float = field(default_factory=time.time)
    route_type: str = ""
    route_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "answer_text": self.answer_text,
            "structured_data": self.structured_data,
            "sources": self.sources,
            "confidence": self.confidence,
            "resolved_at": self.resolved_at,
            "route_type": self.route_type,
            "route_confidence": self.route_confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueryResolution:
        return cls(
            domain=data.get("domain", "help"),
            answer_text=data.get("answer_text", ""),
            structured_data=data.get("structured_data", {}),
            sources=data.get("sources", []),
            confidence=data.get("confidence", 0.0),
            resolved_at=data.get("resolved_at", time.time()),
            route_type=data.get("route_type", ""),
            route_confidence=data.get("route_confidence", 0.0),
        )


# ── Domain detection patterns ───────────────────────────────────────

_SCREEN_PATTERNS = re.compile(
    r"\b(looking at|on screen|screen|focused|active window|active app"
    r"|what app|which app|what file|which file|working on|editing"
    r"|current file|open file)\b",
    re.IGNORECASE,
)

_WORKSPACE_PATTERNS = re.compile(
    r"\b(repo|repository|workspace|project|branch|git|codebase"
    r"|what repo|which repo|which project|which workspace)\b",
    re.IGNORECASE,
)

_RESUME_PATTERNS = re.compile(
    r"\b(resume|pick up|continue|left off|where was I|last session"
    r"|what was I doing|get back to|checkpoint|hand.?off)\b",
    re.IGNORECASE,
)

_SERVICE_PATTERNS = re.compile(
    r"\b(service|container|docker|failing|failed|down|restart|health"
    r"|depends on|dependency|blast radius|critical path)\b",
    re.IGNORECASE,
)

_NODE_PATTERNS = re.compile(
    r"\b(node|device|beast|vps|server|workstation|mesh|online|offline"
    r"|connected|which devices|which nodes)\b",
    re.IGNORECASE,
)

_STATE_PATTERNS = re.compile(
    r"\b(state domain|state authority|who owns|ownership|coherence"
    r"|domain status|state registry)\b",
    re.IGNORECASE,
)

_REALITY_PATTERNS = re.compile(
    r"\b(why did|what changed|what happened|evidence|contradictions?"
    r"|lineage|trace|priorities|what led to)\b",
    re.IGNORECASE,
)

_ACTION_PATTERNS = re.compile(
    r"\b(approvals?|pending|blocked|queue|executing|work.?packets?"
    r"|active.?packets?|waiting|what is running|what is blocked"
    r"|what is next)\b",
    re.IGNORECASE,
)

_HELP_PATTERNS = re.compile(
    r"^(help|what can you|what do you know|capabilities|commands)\b",
    re.IGNORECASE,
)

_DOMAIN_PATTERNS: list[tuple[QueryDomain, re.Pattern[str], float]] = [
    (QueryDomain.HELP, _HELP_PATTERNS, 0.90),
    (QueryDomain.ACTION, _ACTION_PATTERNS, 0.88),
    (QueryDomain.RESUME, _RESUME_PATTERNS, 0.88),
    (QueryDomain.REALITY, _REALITY_PATTERNS, 0.85),
    (QueryDomain.SERVICE, _SERVICE_PATTERNS, 0.85),
    (QueryDomain.NODE, _NODE_PATTERNS, 0.82),
    (QueryDomain.STATE, _STATE_PATTERNS, 0.82),
    (QueryDomain.WORKSPACE, _WORKSPACE_PATTERNS, 0.80),
    (QueryDomain.SCREEN, _SCREEN_PATTERNS, 0.80),
]


class VoiceQueryEngine:
    """Resolves classified intents into context-grounded answers.

    Sits below IntentRouter in the authority hierarchy. Uses IntentRouter
    for route classification, then refines within the route to query the
    correct subsystem.
    """

    def __init__(self) -> None:
        self._intent_router: Any = None
        self._context_engine: Any = None
        self._screen_engine: Any = None
        self._continuity_engine: Any = None
        self._service_engine: Any = None
        self._node_registry: Any = None
        self._state_engine: Any = None
        self._reality_engine: Any = None
        self._coordinator: Any = None
        self._approval_store: Any = None
        self._workspace_engine: Any = None

    # ── Lazy subsystem access ───────────────────────────────────

    @property
    def intent_router(self) -> Any:
        if self._intent_router is None:
            try:
                from substrate.operator.intent_router import IntentRouter
                self._intent_router = IntentRouter()
            except Exception:
                logger.debug("IntentRouter unavailable")
        return self._intent_router

    @property
    def context_engine(self) -> Any:
        if self._context_engine is None:
            try:
                from substrate.operator.operator_context_engine import (
                    OperatorContextEngine,
                )
                self._context_engine = OperatorContextEngine()
            except Exception:
                logger.debug("OperatorContextEngine unavailable")
        return self._context_engine

    @property
    def screen_engine(self) -> Any:
        if self._screen_engine is None:
            try:
                from substrate.operator.screen_observation_engine import (
                    ScreenObservationEngine,
                )
                self._screen_engine = ScreenObservationEngine()
            except Exception:
                logger.debug("ScreenObservationEngine unavailable")
        return self._screen_engine

    @property
    def continuity_engine(self) -> Any:
        if self._continuity_engine is None:
            try:
                from substrate.operator.continuity_engine import ContinuityEngine
                self._continuity_engine = ContinuityEngine()
            except Exception:
                logger.debug("ContinuityEngine unavailable")
        return self._continuity_engine

    @property
    def service_engine(self) -> Any:
        if self._service_engine is None:
            try:
                from substrate.organism.service_failure_engine import (
                    ServiceFailureEngine,
                )
                self._service_engine = ServiceFailureEngine()
            except Exception:
                logger.debug("ServiceFailureEngine unavailable")
        return self._service_engine

    @property
    def node_registry(self) -> Any:
        if self._node_registry is None:
            try:
                from substrate.organism.umh_node_registry import UMHNodeRegistry
                self._node_registry = UMHNodeRegistry()
            except Exception:
                logger.debug("UMHNodeRegistry unavailable")
        return self._node_registry

    @property
    def state_engine(self) -> Any:
        if self._state_engine is None:
            try:
                from substrate.organism.state_coherence_engine import (
                    StateCoherenceEngine,
                )
                self._state_engine = StateCoherenceEngine()
            except Exception:
                logger.debug("StateCoherenceEngine unavailable")
        return self._state_engine

    @property
    def reality_engine(self) -> Any:
        if self._reality_engine is None:
            try:
                from substrate.reality_model.reality_intelligence import (
                    RealityIntelligenceEngine,
                )
                self._reality_engine = RealityIntelligenceEngine()
            except Exception:
                logger.debug("RealityIntelligenceEngine unavailable")
        return self._reality_engine

    @property
    def coordinator(self) -> Any:
        if self._coordinator is None:
            try:
                from substrate.organism.execution_coordinator import (
                    get_execution_coordinator,
                )
                self._coordinator = get_execution_coordinator()
            except Exception:
                logger.debug("ExecutionCoordinator unavailable")
        return self._coordinator

    @property
    def approval_store(self) -> Any:
        if self._approval_store is None:
            try:
                from substrate.organism.executors.approval_intercept import (
                    ApprovalInterceptStore,
                )
                self._approval_store = ApprovalInterceptStore()
            except Exception:
                logger.debug("ApprovalInterceptStore unavailable")
        return self._approval_store

    @property
    def workspace_engine(self) -> Any:
        if self._workspace_engine is None:
            try:
                from substrate.meta_ide.workspace_topology_engine import (
                    WorkspaceTopologyEngine,
                )
                self._workspace_engine = WorkspaceTopologyEngine()
            except Exception:
                logger.debug("WorkspaceTopologyEngine unavailable")
        return self._workspace_engine

    # ── Public API ──────────────────────────────────────────────

    def resolve(
        self, text: str, classification: Any = None,
    ) -> QueryResolution:
        """Full pipeline: classify → detect domain → query → compose answer.

        If classification is None, runs IntentRouter.classify(text) first.
        IntentRouter is the authority on route type.
        """
        if not text or not text.strip():
            return QueryResolution(
                domain=QueryDomain.HELP.value,
                answer_text="I can answer questions about status, screen, workspace, services, nodes, state, reality, approvals, and continuity.",
                sources=["help"],
                confidence=0.50,
            )

        text = text.strip()

        if classification is None and self.intent_router is not None:
            classification = self.intent_router.classify(text)

        route_type = None
        route_confidence = 0.0
        if classification is not None:
            route_type = getattr(classification, "route_type", None)
            route_confidence = getattr(classification, "confidence", 0.0)
            if hasattr(route_type, "value"):
                route_type = route_type.value

        domain, domain_confidence = self.detect_domain(text, route_type)
        resolution = self.query_domain(domain, text)
        resolution.route_type = route_type or ""
        resolution.route_confidence = route_confidence
        return resolution

    def detect_domain(
        self, text: str, route_type: str | None = None,
    ) -> tuple[QueryDomain, float]:
        """Deterministic sub-intent detection.

        route_type from IntentRouter constrains detection:
        - approval → ACTION domain
        - work_packet/hybrid → HELP (not resolved here)
        - observation/conversation → full domain detection
        """
        if route_type == "approval":
            return QueryDomain.ACTION, 0.95

        if route_type in ("work_packet", "hybrid"):
            return QueryDomain.HELP, 0.40

        matches: list[tuple[QueryDomain, float]] = []
        for domain, pattern, base_confidence in _DOMAIN_PATTERNS:
            if pattern.search(text):
                matches.append((domain, base_confidence))

        if not matches:
            return QueryDomain.STATUS, 0.50

        best = max(matches, key=lambda m: m[1])
        return best

    def query_domain(self, domain: QueryDomain, text: str) -> QueryResolution:
        """Query the appropriate subsystem and compose a structured answer."""
        resolvers = {
            QueryDomain.STATUS: self._resolve_status,
            QueryDomain.SCREEN: self._resolve_screen,
            QueryDomain.WORKSPACE: self._resolve_workspace,
            QueryDomain.RESUME: self._resolve_resume,
            QueryDomain.SERVICE: self._resolve_service,
            QueryDomain.NODE: self._resolve_node,
            QueryDomain.STATE: self._resolve_state,
            QueryDomain.REALITY: self._resolve_reality,
            QueryDomain.ACTION: self._resolve_action,
            QueryDomain.HELP: self._resolve_help,
        }
        resolver = resolvers.get(domain, self._resolve_help)
        try:
            return resolver(text)
        except Exception as exc:
            logger.debug("Resolver %s failed: %s", domain, exc)
            return QueryResolution(
                domain=domain.value,
                answer_text=f"I couldn't retrieve {domain.value} information right now.",
                sources=[domain.value],
                confidence=0.30,
            )

    # ── Resolvers (all read-only) ───────────────────────────────

    def _resolve_status(self, text: str) -> QueryResolution:
        engine = self.context_engine
        if engine is None:
            return self._unavailable(QueryDomain.STATUS)

        snap = engine.snapshot()
        health = snap.health_summary
        overall = health.overall_status if health else "unknown"
        attention_count = len(snap.attention_items) if snap.attention_items else 0
        pending = snap.pending_approvals

        parts = [f"System is {overall}."]
        if attention_count:
            parts.append(f"{attention_count} items need attention.")
        if pending:
            parts.append(f"{pending} approvals pending.")

        return QueryResolution(
            domain=QueryDomain.STATUS.value,
            answer_text=" ".join(parts),
            structured_data=snap.to_dict() if hasattr(snap, "to_dict") else {},
            sources=["OperatorContextEngine"],
            confidence=0.90,
        )

    def _resolve_screen(self, text: str) -> QueryResolution:
        engine = self.screen_engine
        if engine is None:
            return self._unavailable(QueryDomain.SCREEN)

        snap = engine.current_snapshot()
        source = snap.source_type.value if hasattr(snap.source_type, "value") else str(snap.source_type)
        parts = []

        if snap.active_application:
            parts.append(f"Active app: {snap.active_application.app_name}.")
        if snap.file_context:
            parts.append(f"Editing {snap.file_context.file_name}.")
        if snap.repository_context:
            repo = snap.repository_context
            branch_info = f" on {repo.branch}" if repo.branch else ""
            parts.append(f"Repo: {repo.repo_name}{branch_info}.")
        if snap.browser_context and snap.browser_context.title:
            parts.append(f"Browser: {snap.browser_context.title}.")

        if not parts:
            parts.append(f"Screen context is {source}, no detailed information available.")

        answer = " ".join(parts)
        return QueryResolution(
            domain=QueryDomain.SCREEN.value,
            answer_text=answer,
            structured_data=snap.to_dict(),
            sources=["ScreenObservationEngine"],
            confidence=snap.source_confidence if snap.source_confidence else 0.50,
        )

    def _resolve_workspace(self, text: str) -> QueryResolution:
        engine = self.workspace_engine
        if engine is None:
            return self._unavailable(QueryDomain.WORKSPACE)

        try:
            topo = engine.topology()
            workspaces = topo.workspaces if hasattr(topo, "workspaces") else []
            ws_list = []
            for ws in workspaces:
                name = ws.workspace_id if hasattr(ws, "workspace_id") else str(ws)
                ws_list.append(name)

            if ws_list:
                answer = f"{len(ws_list)} workspaces configured: {', '.join(ws_list[:5])}."
            else:
                answer = "No workspaces configured in the topology."

            return QueryResolution(
                domain=QueryDomain.WORKSPACE.value,
                answer_text=answer,
                structured_data={
                    "workspace_count": len(ws_list),
                    "workspaces": ws_list,
                },
                sources=["WorkspaceTopologyEngine"],
                confidence=0.85,
            )
        except Exception:
            return self._unavailable(QueryDomain.WORKSPACE)

    def _resolve_resume(self, text: str) -> QueryResolution:
        engine = self.continuity_engine
        if engine is None:
            return self._unavailable(QueryDomain.RESUME)

        try:
            suggestion = engine.resume_suggestion()
            if suggestion and suggestion.get("has_checkpoint"):
                checkpoint_type = suggestion.get("checkpoint_type", "unknown")
                detail = suggestion.get("detail", "")
                hint = suggestion.get("recovery_hint", "")
                parts = [f"Last checkpoint: {checkpoint_type}."]
                if detail:
                    parts.append(detail)
                if hint:
                    parts.append(f"To resume: {hint}")
                return QueryResolution(
                    domain=QueryDomain.RESUME.value,
                    answer_text=" ".join(parts),
                    structured_data=suggestion,
                    sources=["ContinuityEngine"],
                    confidence=0.85,
                )
            return QueryResolution(
                domain=QueryDomain.RESUME.value,
                answer_text="No recent checkpoint found. Nothing to resume.",
                structured_data=suggestion or {},
                sources=["ContinuityEngine"],
                confidence=0.70,
            )
        except Exception:
            return self._unavailable(QueryDomain.RESUME)

    def _resolve_service(self, text: str) -> QueryResolution:
        engine = self.service_engine
        if engine is None:
            return self._unavailable(QueryDomain.SERVICE)

        try:
            health_map = engine.service_health_map()
            organism = engine.organism_health()
            overall = organism.get("overall_health", "unknown")

            failing = [
                svc for svc, status in health_map.items() if status != "healthy"
            ]

            if failing:
                answer = f"{len(failing)} services not healthy: {', '.join(failing)}. Overall: {overall}."
            else:
                total = len(health_map)
                answer = f"All {total} services healthy. Overall: {overall}."

            return QueryResolution(
                domain=QueryDomain.SERVICE.value,
                answer_text=answer,
                structured_data={
                    "health_map": health_map,
                    "organism_health": organism,
                    "failing_services": failing,
                },
                sources=["ServiceFailureEngine"],
                confidence=0.90,
            )
        except Exception:
            return self._unavailable(QueryDomain.SERVICE)

    def _resolve_node(self, text: str) -> QueryResolution:
        registry = self.node_registry
        if registry is None:
            return self._unavailable(QueryDomain.NODE)

        try:
            nodes = registry.list_nodes()
            node_info = []
            for n in nodes:
                node_id = n.node_id if hasattr(n, "node_id") else str(n)
                role = n.role if hasattr(n, "role") else "unknown"
                node_info.append({"node_id": node_id, "role": role})

            primary = registry.primary_node()
            primary_id = primary.node_id if primary and hasattr(primary, "node_id") else "none"

            answer = f"{len(nodes)} nodes registered. Primary: {primary_id}."

            return QueryResolution(
                domain=QueryDomain.NODE.value,
                answer_text=answer,
                structured_data={
                    "node_count": len(nodes),
                    "nodes": node_info,
                    "primary_node": primary_id,
                },
                sources=["UMHNodeRegistry"],
                confidence=0.85,
            )
        except Exception:
            return self._unavailable(QueryDomain.NODE)

    def _resolve_state(self, text: str) -> QueryResolution:
        engine = self.state_engine
        if engine is None:
            return self._unavailable(QueryDomain.STATE)

        try:
            report = engine.coherence_report()
            overall = report.get("overall_health", "unknown")
            domains = report.get("domains", [])
            total = len(domains)
            coherent = sum(
                1 for d in domains if d.get("status") == "coherent"
            )

            answer = f"State coherence: {overall}. {coherent} of {total} domains coherent."

            return QueryResolution(
                domain=QueryDomain.STATE.value,
                answer_text=answer,
                structured_data=report,
                sources=["StateCoherenceEngine"],
                confidence=0.85,
            )
        except Exception:
            return self._unavailable(QueryDomain.STATE)

    def _resolve_reality(self, text: str) -> QueryResolution:
        engine = self.reality_engine
        if engine is None:
            return self._unavailable(QueryDomain.REALITY)

        try:
            from substrate.reality_model.reality_intelligence import (
                RealityQuery,
                RealityQueryType,
            )

            query_type = RealityQueryType.WHAT_CHANGED
            if re.search(r"\bwhy\b", text, re.IGNORECASE):
                query_type = RealityQueryType.WHY
            elif re.search(r"\bevidence\b", text, re.IGNORECASE):
                query_type = RealityQueryType.EVIDENCE
            elif re.search(r"\bcontradiction", text, re.IGNORECASE):
                query_type = RealityQueryType.CONTRADICTIONS
            elif re.search(r"\blineage\b|\btrace\b", text, re.IGNORECASE):
                query_type = RealityQueryType.LINEAGE
            elif re.search(r"\bpriori", text, re.IGNORECASE):
                query_type = RealityQueryType.PRIORITIES

            rq = RealityQuery(query_type=query_type, text=text)
            result = engine.query(rq)

            answer = result.summary if hasattr(result, "summary") and result.summary else "No reality data found for that query."
            evidence_count = len(result.evidence) if hasattr(result, "evidence") else 0

            return QueryResolution(
                domain=QueryDomain.REALITY.value,
                answer_text=answer,
                structured_data={
                    "query_type": query_type.value,
                    "summary": answer,
                    "evidence_count": evidence_count,
                    "confidence": result.confidence if hasattr(result, "confidence") else 0.0,
                },
                sources=["RealityIntelligenceEngine"],
                confidence=result.confidence if hasattr(result, "confidence") else 0.50,
            )
        except Exception as exc:
            logger.debug("Reality resolution failed: %s", exc)
            return self._unavailable(QueryDomain.REALITY)

    def _resolve_action(self, text: str) -> QueryResolution:
        parts: list[str] = []
        data: dict[str, Any] = {}
        sources: list[str] = []

        store = self.approval_store
        if store is not None:
            try:
                pending = store.list_pending()
                data["pending_approvals"] = len(pending)
                data["approval_details"] = [
                    {
                        "approval_id": a.approval_id,
                        "description": a.description if hasattr(a, "description") else "",
                        "risk_level": a.risk_level if hasattr(a, "risk_level") else "",
                    }
                    for a in pending[:10]
                ]
                if pending:
                    parts.append(f"{len(pending)} approvals waiting.")
                else:
                    parts.append("No pending approvals.")
                sources.append("ApprovalInterceptStore")
            except Exception:
                logger.debug("ApprovalInterceptStore query failed")

        coord = self.coordinator
        if coord is not None:
            try:
                active = coord.active_plans()
                queue = coord.queue_state()
                data["active_plans"] = len(active)
                data["queue_depth"] = len(queue)
                data["active_plan_details"] = [
                    {
                        "plan_id": p.execution_plan_id if hasattr(p, "execution_plan_id") else "",
                        "status": p.status if hasattr(p, "status") else "",
                    }
                    for p in active[:10]
                ]
                if active:
                    parts.append(f"{len(active)} plans executing.")
                if queue:
                    parts.append(f"{len(queue)} in queue.")
                if not active and not queue:
                    parts.append("No active execution.")
                sources.append("ExecutionCoordinator")
            except Exception:
                logger.debug("ExecutionCoordinator query failed")

        if not parts:
            parts.append("Action subsystems unavailable.")

        return QueryResolution(
            domain=QueryDomain.ACTION.value,
            answer_text=" ".join(parts),
            structured_data=data,
            sources=sources,
            confidence=0.85 if sources else 0.30,
        )

    def _resolve_help(self, text: str) -> QueryResolution:
        domains = [d.value for d in QueryDomain]
        return QueryResolution(
            domain=QueryDomain.HELP.value,
            answer_text=(
                "I can answer questions about: "
                + ", ".join(d for d in domains if d != "help")
                + ". Ask about status, screen, workspace, services, nodes, "
                "state, reality, actions, or what to resume."
            ),
            structured_data={"available_domains": domains},
            sources=["help"],
            confidence=0.95,
        )

    def _unavailable(self, domain: QueryDomain) -> QueryResolution:
        return QueryResolution(
            domain=domain.value,
            answer_text=f"The {domain.value} subsystem is not available right now.",
            sources=[domain.value],
            confidence=0.30,
        )

    # ── Gate 3: Voice Action Resolution ──────────────────────────

    def resolve_action(self, text: str, classification: Any | None = None) -> ActionResolution:
        """Resolve an action intent → GovernedWorkRuntime operation.

        Detects action type from text, builds ActionResolution with
        the operation, target, and confirmation text. The caller
        (OperatorLoopRuntime or cockpit) routes the resolution to
        GovernedWorkRuntime — this method does NOT execute.
        """
        lower = text.lower().strip()

        action_type, target_id, params = _detect_action_intent(lower)

        requires_approval = action_type in ("execute", "retry")
        confirmation = _build_confirmation(action_type, target_id, text)

        return ActionResolution(
            action_type=action_type,
            target_id=target_id,
            parameters=params,
            requires_approval=requires_approval,
            confirmation_text=confirmation,
            source_text=text,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Gate 3: ActionResolution types + detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ActionResolution:
    """Resolved action intent — routes to GovernedWorkRuntime."""

    action_type: str = "submit"
    target_id: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    confirmation_text: str = ""
    source_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "target_id": self.target_id,
            "parameters": self.parameters,
            "requires_approval": self.requires_approval,
            "confirmation_text": self.confirmation_text,
            "source_text": self.source_text,
        }


_SUBMIT_PATTERNS = re.compile(
    r"\b(create\s+work|submit\s+work|new\s+packet|create\s+packet"
    r"|make\s+a?\s*work\s*packet|add\s+work)\b",
    re.IGNORECASE,
)

_APPROVE_PATTERNS = re.compile(
    r"\b(approve|accept|greenlight|sign\s+off)\b",
    re.IGNORECASE,
)

_REJECT_PATTERNS = re.compile(
    r"\b(reject|deny|decline|refuse)\b",
    re.IGNORECASE,
)

_EXECUTE_PATTERNS = re.compile(
    r"\b(execute|run\s+(?:this|it|packet)|dispatch|launch|start\s+execution)\b",
    re.IGNORECASE,
)

_CANCEL_PATTERNS = re.compile(
    r"\b(cancel|abort|stop\s+(?:this|execution|work)|kill)\b",
    re.IGNORECASE,
)

_RETRY_PATTERNS = re.compile(
    r"\b(retry|rerun|try\s+again|redo)\b",
    re.IGNORECASE,
)

_RESUME_PATTERNS = re.compile(
    r"\b(resume|continue|pick\s+up|carry\s+on)\b",
    re.IGNORECASE,
)

_ID_PATTERN = re.compile(
    r"\b(wp-[a-f0-9]{12}|expl-[a-f0-9]{12}|exrq-[a-f0-9]{12})\b",
    re.IGNORECASE,
)


def _detect_action_intent(text: str) -> tuple[str, str, dict[str, Any]]:
    """Detect action type and optional target ID from text."""
    target_match = _ID_PATTERN.search(text)
    target_id = target_match.group(1) if target_match else ""

    params: dict[str, Any] = {}

    if _SUBMIT_PATTERNS.search(text):
        intent_text = _SUBMIT_PATTERNS.sub("", text).strip()
        params["intent"] = intent_text if intent_text else text
        return "submit", target_id, params

    if _APPROVE_PATTERNS.search(text):
        return "approve", target_id, params

    if _REJECT_PATTERNS.search(text):
        reason_text = _REJECT_PATTERNS.sub("", text).strip()
        if reason_text:
            params["reason"] = reason_text
        return "reject", target_id, params

    if _EXECUTE_PATTERNS.search(text):
        return "execute", target_id, params

    if _CANCEL_PATTERNS.search(text):
        reason_text = _CANCEL_PATTERNS.sub("", text).strip()
        if reason_text:
            params["reason"] = reason_text
        return "cancel", target_id, params

    if _RETRY_PATTERNS.search(text):
        return "retry", target_id, params

    if _RESUME_PATTERNS.search(text):
        return "resume", target_id, params

    params["intent"] = text
    return "submit", target_id, params


def _build_confirmation(action_type: str, target_id: str, source: str) -> str:
    """Build human-readable confirmation text."""
    target_str = f" {target_id}" if target_id else ""

    confirmations = {
        "submit": f"Create new work packet from: {source[:80]}",
        "approve": f"Approve work{target_str}",
        "reject": f"Reject work{target_str}",
        "execute": f"Execute work{target_str} — this will start real execution",
        "cancel": f"Cancel work{target_str}",
        "retry": f"Retry work{target_str}",
        "resume": f"Resume work{target_str}",
    }

    return confirmations.get(action_type, f"Unknown action: {action_type}")
