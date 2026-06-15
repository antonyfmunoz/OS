"""Empire Router — routes founder intent to domain-classified, governed WorkPackets.

Deterministic routing with profile/session awareness. Transforms high-level
natural language intent into structured, decomposed, agent-routed WorkPackets
with proof requirements and reality model integration.

Phase 3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


def _repo_root() -> str:
    return os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class RoutingResult:
    """Output of the IntentRouter — everything needed to execute work."""

    routing_id: str = ""
    domain: str = ""
    domain_label: str = ""
    objective: str = ""
    scope: str = "single"
    urgency: str = "normal"
    risk_level: str = "low"
    required_approvals: list[str] = field(default_factory=list)
    suggested_agents: list[str] = field(default_factory=list)
    proof_requirements: list[dict[str, Any]] = field(default_factory=list)
    work_packets: list[dict[str, Any]] = field(default_factory=list)
    suggested_sequence: list[str] = field(default_factory=list)
    missing_context: list[str] = field(default_factory=list)
    profile_constraints: dict[str, Any] = field(default_factory=dict)
    background_eligible: bool = True
    next_action: str = ""
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.routing_id:
            import uuid
            self.routing_id = f"route-{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "routing_id": self.routing_id,
            "domain": self.domain,
            "domain_label": self.domain_label,
            "objective": self.objective,
            "scope": self.scope,
            "urgency": self.urgency,
            "risk_level": self.risk_level,
            "required_approvals": self.required_approvals,
            "suggested_agents": self.suggested_agents,
            "proof_requirements": self.proof_requirements,
            "work_packets": self.work_packets,
            "suggested_sequence": self.suggested_sequence,
            "missing_context": self.missing_context,
            "profile_constraints": self.profile_constraints,
            "background_eligible": self.background_eligible,
            "next_action": self.next_action,
            "created_at": self.created_at,
        }


@dataclass
class RealitySnapshot:
    """Current state from the reality model relevant to a routing decision."""

    active_domains: list[str] = field(default_factory=list)
    active_loops: list[dict[str, Any]] = field(default_factory=list)
    blocked_items: list[dict[str, Any]] = field(default_factory=list)
    open_approvals: int = 0
    recent_outcomes: list[dict[str, Any]] = field(default_factory=list)
    current_phase: str = ""
    next_best_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_domains": self.active_domains,
            "active_loops": self.active_loops,
            "blocked_items": self.blocked_items,
            "open_approvals": self.open_approvals,
            "recent_outcomes": self.recent_outcomes,
            "current_phase": self.current_phase,
            "next_best_actions": self.next_best_actions,
        }


class EmpireRouter:
    """Routes founder intent through domain classification, decomposition,
    agent assignment, and profile-aware governance.

    Deterministic-first: keyword/pattern matching for all classification.
    No LLM calls in the routing path.
    """

    def __init__(self) -> None:
        from substrate.organism.domain_registry import DomainRegistry
        from substrate.organism.agent_registry import AgentRegistry
        from substrate.organism.intent_classifier import IntentClassifier
        from substrate.organism.work_packet_engine import WorkPacketEngine

        self._domains = DomainRegistry()
        self._agents = AgentRegistry()
        self._classifier = IntentClassifier()
        self._engine = WorkPacketEngine()

    def route(
        self,
        intent: str,
        desired_end_state: str = "",
        constraints: list[str] | None = None,
        profile_mode: str = "",
        session_mode: str = "",
        operator_available: bool = True,
    ) -> RoutingResult:
        """Full routing pipeline: classify → decompose → assign → govern."""

        classification = self._classifier.classify(intent)
        domain_id = self._domains.resolve_id(classification.domain)
        domain_def = self._domains.get(domain_id)

        result = RoutingResult(
            domain=domain_id,
            domain_label=domain_def.label if domain_def else domain_id,
            objective=intent,
        )

        result.scope = self._determine_scope(classification)
        result.urgency = self._determine_urgency(intent, classification)
        result.risk_level = classification.risk_class

        if domain_def:
            result.required_approvals = list(domain_def.approval_gates)
            result.suggested_agents = list(domain_def.default_agent_types)
            result.proof_requirements = [
                p.to_dict() if hasattr(p, "to_dict") else {
                    "proof_type": p.proof_type,
                    "description": p.description,
                    "required": p.required,
                }
                for p in domain_def.proof_requirements
            ]
            result.background_eligible = domain_def.background_eligible

        if classification.risk_class in ("high", "critical"):
            if "operator_review" not in result.required_approvals:
                result.required_approvals.append("operator_review")

        self._apply_profile_constraints(result, profile_mode, session_mode,
                                         operator_available)

        batch = self._engine.decompose_intent_to_batch(
            user_intent=intent,
            desired_end_state=desired_end_state,
            constraints=constraints,
        )

        if batch.get("child_packets"):
            result.work_packets = batch["child_packets"]
            result.suggested_sequence = [
                p["packet_id"] for p in batch["child_packets"]
            ]
            result.scope = "batch"
        else:
            result.work_packets = [batch["parent_packet"]]
            result.suggested_sequence = [batch["parent_packet"]["packet_id"]]

        for wp in result.work_packets:
            wp_domain = self._domains.resolve_id(wp.get("domain", ""))
            agents = self._agents.agents_for_domain(wp_domain)
            wp["assigned_agents"] = [a.agent_type_id for a in agents[:3]]
            wp_domain_def = self._domains.get(wp_domain)
            if wp_domain_def:
                wp["proof_requirements"] = [
                    {"proof_type": p.proof_type, "description": p.description,
                     "required": p.required}
                    for p in wp_domain_def.proof_requirements
                ]

        result.missing_context = self._detect_missing_context(
            intent, classification, domain_def,
        )

        result.next_action = self._determine_next_action(result, operator_available)

        self._persist_routing(result)

        return result

    def get_reality_snapshot(self) -> RealitySnapshot:
        """Build a snapshot of current reality model state."""
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        q = UniversalWorkQueue()

        active_domains: set[str] = set()
        active_loops: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        recent: list[dict[str, Any]] = []

        for pkt in q.all_packets():
            d = pkt.to_safe_dict()
            if pkt.status.value in ("executing", "delegated", "validating"):
                active_domains.add(pkt.domain)
                active_loops.append({
                    "packet_id": pkt.packet_id,
                    "title": pkt.title,
                    "domain": pkt.domain,
                    "status": pkt.status.value,
                })
            elif pkt.status.value == "blocked":
                blocked.append({
                    "packet_id": pkt.packet_id,
                    "title": pkt.title,
                    "blockers": pkt.blockers,
                })
            elif pkt.status.value == "completed":
                recent.append({
                    "packet_id": pkt.packet_id,
                    "title": pkt.title,
                    "outcome": pkt.outcome_summary,
                })

        approvals = len(q.get_packets_requiring_approval())

        # Enrich from CanonicalRealityModel — extract pattern domains
        try:
            from substrate.reality_model.canonical import CanonicalRealityModel
            canonical = CanonicalRealityModel()
            for pattern in canonical.all():
                if pattern.domain:
                    active_domains.add(pattern.domain)
        except Exception as e:
            logger.debug("reality snapshot canonical enrichment: %s", e)

        # Enrich from InstanceRealityModel — recent observations
        try:
            from substrate.reality_model.instance import InstanceRealityModel
            org_id = os.environ.get(
                "UMH_ORG_ID", os.environ.get("EOS_ORG_ID", "default"),
            )
            user_id = os.environ.get(
                "UMH_USER_ID", os.environ.get("EOS_USER_ID", "default"),
            )
            instance = InstanceRealityModel(user_id=user_id, org_id=org_id)
            for obs in instance.recent(limit=10):
                recent.append({
                    "observation_id": str(obs.id),
                    "content": obs.content,
                    "domain": obs.domain,
                    "confidence": obs.effective_confidence(),
                    "source": (
                        str(obs.source_signal_id) if obs.source_signal_id else None
                    ),
                    "timestamp": obs.observed_at.isoformat(),
                })
        except Exception as e:
            logger.debug("reality snapshot instance enrichment: %s", e)

        nba = self._compute_next_best_actions(q)

        return RealitySnapshot(
            active_domains=sorted(active_domains),
            active_loops=active_loops[:10],
            blocked_items=blocked[:10],
            open_approvals=approvals,
            recent_outcomes=recent[:10],
            next_best_actions=nba,
        )

    def get_domain_summary(self) -> list[dict[str, Any]]:
        """Return all domains with their definitions."""
        return [d.to_dict() for d in self._domains.all_domains()]

    def get_agent_summary(self) -> list[dict[str, Any]]:
        """Return all agent types with their definitions."""
        return [a.to_dict() for a in self._agents.all_agents()]

    # ── Private helpers ───────────────────────────────────────────────

    def _determine_scope(self, classification: Any) -> str:
        if classification.complexity == "strategic":
            return "strategic"
        if classification.complexity == "complex":
            return "batch"
        return "single"

    def _determine_urgency(self, intent: str, classification: Any) -> str:
        lower = intent.lower()
        urgent_signals = ["asap", "urgent", "immediately", "now", "today",
                          "critical", "emergency", "blocking", "blocked"]
        if any(s in lower for s in urgent_signals):
            return "urgent"
        if classification.risk_class in ("high", "critical"):
            return "high"
        scheduled_signals = ["next week", "eventually", "when possible",
                             "low priority", "backlog"]
        if any(s in lower for s in scheduled_signals):
            return "low"
        return "normal"

    def _apply_profile_constraints(
        self,
        result: RoutingResult,
        profile_mode: str,
        session_mode: str,
        operator_available: bool,
    ) -> None:
        constraints: dict[str, Any] = {}

        if profile_mode:
            constraints["profile_mode"] = profile_mode
            profile_domain_map = {
                "DEVELOPER": ["engineering", "infrastructure"],
                "RESEARCH": ["research"],
                "MUSIC": ["music"],
                "DESIGN": ["clothing", "content"],
                "CONTENT": ["content", "marketing"],
                "COMMAND_CENTER": [],
                "FINANCE": ["finance", "real_estate"],
                "LEARNING": ["research", "personal"],
            }
            foreground_domains = profile_domain_map.get(profile_mode, [])
            if foreground_domains and result.domain not in foreground_domains:
                constraints["routing"] = "background"
                constraints["reason"] = (
                    f"Domain '{result.domain}' not in foreground for "
                    f"profile '{profile_mode}' — routing to background"
                )

        if session_mode:
            constraints["session_mode"] = session_mode
            if session_mode in ("NIGHT", "SLEEP"):
                constraints["escalation_only"] = True
                if result.risk_level in ("high", "critical"):
                    constraints["defer_until_morning"] = True

        if not operator_available:
            constraints["operator_available"] = False
            if result.required_approvals:
                constraints["approval_deferred"] = True
                result.next_action = "queue_for_approval"

        result.profile_constraints = constraints

    def _detect_missing_context(
        self,
        intent: str,
        classification: Any,
        domain_def: Any,
    ) -> list[str]:
        missing: list[str] = []
        lower = intent.lower()

        if len(intent.split()) < 5:
            missing.append("Intent is very brief — consider adding more detail")

        if classification.risk_class in ("high", "critical"):
            if "budget" not in lower and "cost" not in lower:
                if domain_def and domain_def.domain_id in ("finance", "real_estate", "sales"):
                    missing.append("High-risk financial domain — budget/cost context missing")

        if classification.complexity == "strategic":
            if "timeline" not in lower and "deadline" not in lower:
                missing.append("Strategic work — timeline not specified")

        return missing

    def _determine_next_action(
        self,
        result: RoutingResult,
        operator_available: bool,
    ) -> str:
        if result.missing_context:
            return "clarify_intent"
        if result.required_approvals and not operator_available:
            return "queue_for_approval"
        if result.required_approvals:
            return "request_approval"
        if result.risk_level in ("high", "critical"):
            return "request_approval"
        if result.scope == "batch":
            return "execute_sequence"
        return "execute"

    def _compute_next_best_actions(self, queue: Any) -> list[str]:
        actions: list[str] = []
        approvals = queue.get_packets_requiring_approval()
        if approvals:
            actions.append(f"Approve {len(approvals)} pending packet(s)")
        blocked = queue.get_blocked_packets()
        if blocked:
            actions.append(f"Unblock {len(blocked)} blocked packet(s)")
        nxt = queue.get_next_best_packet()
        if nxt:
            actions.append(f"Execute next: {nxt.title}")
        return actions

    def _persist_routing(self, result: RoutingResult) -> None:
        route_dir = os.path.join(
            _repo_root(), "data", "umh", "execution", "routings",
        )
        os.makedirs(route_dir, exist_ok=True)
        path = os.path.join(route_dir, f"{result.routing_id}.json")
        try:
            with open(path, "w") as f:
                json.dump(result.to_dict(), f, indent=2)
        except OSError as exc:
            logger.warning("failed to persist routing %s: %s", result.routing_id, exc)
