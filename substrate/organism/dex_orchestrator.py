"""Orchestrator Kernel — central intelligence routing for operator interaction.

Integrates all Phase 11-12 subsystems (work packets, universal work queue,
propagation graph, impact analysis, roadmap, self-build, templates, agent
capabilities, approvals) into a single orchestrator that converts operator
input into structured previews and governed work.

The orchestrator kernel is not a chatbot persona. It classifies intent,
assembles context from real system state, and produces OperatorResponse
objects. It NEVER executes work without explicit operator approval.

Phase 13.0. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any
from uuid import uuid4

from substrate.organism.operator_session import (
    OperatorSession,
    OperatorTurn,
    OperatorIntent,
    IntentType,
    SessionStatus,
    persist_sessions,
    load_sessions,
    persist_turns,
    persist_intents,
)
from substrate.organism.operator_response import (
    OperatorResponse,
    Option,
    OutputMode,
    persist_responses,
    load_responses,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

# ── Intent classification patterns ─────────────────────────────────────

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    (IntentType.CREATE_WORK.value, [
        r"\bbuild\b", r"\bcreate\b", r"\bimplement\b", r"\bdevelop\b",
        r"\bdesign\b", r"\blaunch\b", r"\bship\b", r"\bdeploy\b",
        r"\bi want to\b", r"\blet'?s\b", r"\bwe need\b", r"\badd\b",
        r"\bset up\b", r"\binstall\b", r"\bconfigure\b",
    ]),
    (IntentType.QUERY_STATUS.value, [
        r"\bwhere are we\b", r"\bstatus\b", r"\bprogress\b", r"\bhow far\b",
        r"\bcurrent state\b", r"\bwhat'?s happening\b", r"\boverview\b",
        r"\bshow me\b.*\bstatus\b", r"\breport\b",
    ]),
    (IntentType.QUERY_APPROVALS.value, [
        r"\bapproval\b", r"\bpending\b", r"\bneeds? my\b", r"\bwaiting for\b",
        r"\bapprove\b", r"\breview\b.*\bpending\b",
    ]),
    (IntentType.PREVIEW_PROPAGATION.value, [
        r"\bpropagate\b", r"\bimpact\b", r"\bwhat else changes\b",
        r"\bripple\b", r"\baffect\b", r"\bdownstream\b", r"\bif .+ updates?\b",
        r"\bwhat happens if\b",
    ]),
    (IntentType.PREVIEW_TOPOLOGY.value, [
        r"\btopology\b", r"\bdelegation\b", r"\bworkcell\b", r"\bwho handles\b",
        r"\bhow would .+ be structured\b",
    ]),
    (IntentType.ROADMAP_QUERY.value, [
        r"\broadmap\b", r"\bphase\b", r"\bmilestone\b", r"\bwhat'?s next\b",
        r"\bpriority\b", r"\bpipeline\b", r"\bbacklog\b",
    ]),
    (IntentType.RECOMMEND_NEXT.value, [
        r"\brecommend\b", r"\bsuggest\b", r"\bwhat should\b",
        r"\bnext action\b", r"\bnext step\b",
    ]),
]

_ENTITY_PATTERNS: list[tuple[str, str]] = [
    (r"\bwork ?packet\b", "work_packet"),
    (r"\btemplate\b", "template"),
    (r"\bagent\b", "agent"),
    (r"\broadmap\b", "roadmap"),
    (r"\bapproval\b", "approval"),
    (r"\bpropagation\b", "propagation"),
    (r"\bcockpit\b", "cockpit"),
    (r"\bdashboard\b", "dashboard"),
    (r"\boffer\b", "offer"),
    (r"\bpacket\b", "work_packet"),
]


class DexOrchestrator:
    """Central orchestrator kernel for operator interaction.

    Integrates all Phase 11-12 subsystems. Never executes work
    without explicit operator approval.
    """

    def __init__(
        self,
        sessions_path: str | None = None,
        responses_path: str | None = None,
        work_packets_path: str | None = None,
        propagation_graph_path: str | None = None,
        roadmap_path: str | None = None,
        self_build_path: str | None = None,
        templates_path: str | None = None,
        agent_cap_path: str | None = None,
        approval_store_dir: str | None = None,
    ) -> None:
        self._sessions_path = sessions_path or os.path.join(
            _REPO_ROOT, "data", "umh", "operator_experience", "sessions.jsonl",
        )
        self._responses_path = responses_path or os.path.join(
            _REPO_ROOT, "data", "umh", "operator_experience", "responses.jsonl",
        )
        self._work_packets_path = work_packets_path
        self._propagation_graph_path = propagation_graph_path
        self._roadmap_path = roadmap_path
        self._self_build_path = self_build_path
        self._templates_path = templates_path
        self._agent_cap_path = agent_cap_path
        self._approval_store_dir = approval_store_dir

        self._sessions: list[OperatorSession] = load_sessions(self._sessions_path)
        self._responses: list[OperatorResponse] = []

    # ── Public interface ──────────────────────────────────────────────

    def receive_operator_input(
        self,
        user_input: str,
        session_id: str | None = None,
    ) -> OperatorResponse:
        """Main entry point: operator input -> structured response.

        Never executes work. Always returns preview/response.
        """
        session = self._get_or_create_session(session_id)
        intent = self.classify_intent(user_input)
        context = self.assemble_context(intent)

        turn = OperatorTurn(
            session_id=session.session_id,
            operator_input=user_input,
            intent=intent,
        )

        response = self._route_intent(intent, context, session, turn)
        response.session_id = session.session_id
        response.turn_id = turn.turn_id
        response.intent_type = intent.intent_type

        turn.response_id = response.response_id
        session.add_turn(turn)

        # Persist session state
        self.persist_session_turn(session, turn, intent)

        # Safety invariant
        self.never_execute_without_approval(response)

        return response

    def classify_intent(self, user_input: str) -> OperatorIntent:
        """Deterministic intent classification from operator input."""
        lower = user_input.lower().strip()
        intent = OperatorIntent(raw_input=user_input)

        # Match intent type
        best_type = IntentType.GENERAL_QUERY.value
        best_score = 0
        for intent_type, patterns in _INTENT_PATTERNS:
            score = sum(1 for p in patterns if re.search(p, lower))
            if score > best_score:
                best_score = score
                best_type = intent_type
        intent.intent_type = best_type
        intent.confidence = min(1.0, best_score * 0.25) if best_score > 0 else 0.1

        # Extract entities
        for pattern, entity in _ENTITY_PATTERNS:
            if re.search(pattern, lower):
                if entity not in intent.extracted_entities:
                    intent.extracted_entities.append(entity)

        # Determine if work packet is required
        intent.requires_work_packet = best_type == IntentType.CREATE_WORK.value

        # Extract subject (first 120 chars, cleaned)
        intent.extracted_subject = user_input[:120].strip()
        intent.extracted_action = best_type

        # Determine approval requirement
        intent.requires_approval = best_type in (
            IntentType.CREATE_WORK.value,
            IntentType.APPROVE.value,
            IntentType.REJECT.value,
        )

        return intent

    def assemble_context(self, intent: OperatorIntent) -> dict[str, Any]:
        """Assemble relevant system context for the intent."""
        context: dict[str, Any] = {
            "intent_type": intent.intent_type,
            "timestamp": time.time(),
        }

        if intent.intent_type in (
            IntentType.CREATE_WORK.value,
            IntentType.QUERY_STATUS.value,
            IntentType.RECOMMEND_NEXT.value,
        ):
            context["work_queue_summary"] = self._get_work_queue_summary()

        if intent.intent_type in (
            IntentType.QUERY_STATUS.value,
            IntentType.ROADMAP_QUERY.value,
            IntentType.RECOMMEND_NEXT.value,
        ):
            context["roadmap_summary"] = self._get_roadmap_summary()

        if intent.intent_type in (
            IntentType.QUERY_APPROVALS.value,
            IntentType.RECOMMEND_NEXT.value,
        ):
            context["pending_approvals"] = self._get_pending_approvals()

        if intent.intent_type in (
            IntentType.PREVIEW_PROPAGATION.value,
            IntentType.CREATE_WORK.value,
        ):
            context["graph_summary"] = self._get_graph_summary()

        return context

    def determine_if_work_packet_required(
        self, intent: OperatorIntent,
    ) -> bool:
        """Determine if the intent requires a work packet."""
        return intent.requires_work_packet

    def generate_work_packet(
        self, intent: OperatorIntent,
    ) -> dict[str, Any]:
        """Generate a work packet from operator intent (preview only)."""
        engine = self._get_work_packet_engine()
        packet = engine.create_packet_from_intent(
            user_intent=intent.raw_input,
            desired_end_state=intent.extracted_subject,
            constraints=intent.extracted_constraints,
            source_type="operator_experience",
            source_id=intent.intent_id,
        )
        return packet.to_dict()

    def preview_delegation_topology(
        self, intent: OperatorIntent,
    ) -> dict[str, Any]:
        """Preview delegation topology for an intent."""
        engine = self._get_work_packet_engine()
        classification = engine.classify_intent(intent.raw_input)
        planner = self._get_delegation_topology_planner()
        # Build a minimal packet for topology planning
        packet = engine.create_packet_from_intent(
            user_intent=intent.raw_input,
            desired_end_state=intent.extracted_subject,
            constraints=intent.extracted_constraints,
        )
        topology = planner.plan_topology(packet)
        return {
            "topology": topology.to_dict(),
            "classification": classification.to_dict(),
            "packet_id": packet.packet_id,
        }

    def preview_human_actions(
        self, intent: OperatorIntent, context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Identify human actions required for an intent."""
        actions: list[dict[str, Any]] = []
        classification = self._get_intent_classifier().classify(intent.raw_input)
        if classification.human_action_required:
            actions.append({
                "type": "human_action",
                "description": "Operator action required for high-risk or external dependency",
                "risk_class": classification.risk_class,
                "domain": classification.domain,
            })
        if classification.approval_required:
            actions.append({
                "type": "approval_gate",
                "description": "Governance approval required before execution",
                "risk_class": classification.risk_class,
            })
        return actions

    def preview_approval_gates(
        self, intent: OperatorIntent,
    ) -> list[dict[str, Any]]:
        """Preview approval gates for an intent."""
        classification = self._get_intent_classifier().classify(intent.raw_input)
        gates: list[dict[str, Any]] = []
        if classification.risk_class in ("medium", "high"):
            gates.append({
                "gate_type": "risk_gate",
                "risk_class": classification.risk_class,
                "reason": "Work packet risk class requires operator approval",
            })
        if classification.human_action_required:
            gates.append({
                "gate_type": "human_gate",
                "reason": "External human action required",
            })
        return gates

    def preview_propagation_impact(
        self,
        source_description: str,
        source_node_id: str = "",
    ) -> dict[str, Any]:
        """Preview propagation impact of a change."""
        from substrate.organism.change_event import ChangeEvent, ChangeType
        graph = self._get_propagation_graph()
        analyzer = self._get_impact_analyzer(graph)

        # Build change event from description
        event = ChangeEvent(
            change_type=ChangeType.WORK_PACKET_UPDATED,
            source_node_id=source_node_id or "preview",
            title=source_description[:200],
            description=source_description,
            initiated_by="operator_preview",
        )

        analysis = analyzer.analyze(event)
        planner = self._get_propagation_planner(graph)
        plan = planner.plan(event, analysis)

        return {
            "impact_analysis": analysis.to_dict(),
            "propagation_plan": plan.to_dict(),
            "affected_count": len(analysis.affected_nodes),
            "waves": plan.total_waves,
            "requires_approval": len(analysis.approval_required) > 0,
            "requires_human": len(analysis.human_required) > 0,
        }

    def query_roadmap_status(self) -> dict[str, Any]:
        """Query current roadmap status from real state."""
        engine = self._get_roadmap_engine()
        return engine.summary()

    def query_pending_approvals(self) -> dict[str, Any]:
        """Query pending approvals from real state."""
        store = self._get_approval_store()
        pending = store.list_approvals(status="pending")
        all_approvals = store.list_approvals()
        return {
            "pending_count": len(pending),
            "total_count": len(all_approvals),
            "pending": pending[:20],
        }

    def recommend_next_action(self) -> dict[str, Any]:
        """Recommend next operator action based on system state."""
        recommendations: list[dict[str, Any]] = []

        # Check pending approvals
        approvals = self.query_pending_approvals()
        if approvals["pending_count"] > 0:
            recommendations.append({
                "priority": 1,
                "action": "review_approvals",
                "description": "Review {} pending approval(s)".format(
                    approvals["pending_count"]
                ),
                "details": approvals,
            })

        # Check roadmap
        roadmap = self.query_roadmap_status()
        phase_list = roadmap.get("phases", [])
        in_progress = [p for p in phase_list if p.get("status") == "in_progress"]
        if in_progress:
            recommendations.append({
                "priority": 2,
                "action": "continue_phase",
                "description": "Continue in-progress phase: {}".format(
                    in_progress[0].get("title", "unknown")
                ),
                "details": {"phases_in_progress": in_progress},
            })

        # Check work queue
        queue_summary = self._get_work_queue_summary()
        active_packets = queue_summary.get("active_count", 0)
        if active_packets > 0:
            recommendations.append({
                "priority": 3,
                "action": "review_work_queue",
                "description": "Review {} active work packet(s)".format(active_packets),
                "details": queue_summary,
            })

        if not recommendations:
            recommendations.append({
                "priority": 1,
                "action": "create_work",
                "description": "No pending items. Ready for new work.",
            })

        return {
            "recommendations": sorted(recommendations, key=lambda r: r["priority"]),
            "system_state": "active",
            "timestamp": time.time(),
        }

    def create_operator_response(
        self,
        intent: OperatorIntent,
        session: OperatorSession,
        turn: OperatorTurn,
        **kwargs: Any,
    ) -> OperatorResponse:
        """Create a structured OperatorResponse."""
        response = OperatorResponse(
            session_id=session.session_id,
            turn_id=turn.turn_id,
            intent_type=intent.intent_type,
            **kwargs,
        )
        response.execution_occurred = False
        return response

    def persist_session_turn(
        self,
        session: OperatorSession,
        turn: OperatorTurn,
        intent: OperatorIntent,
    ) -> None:
        """Persist session, turn, and intent to JSONL."""
        # Update sessions list
        found = False
        for i, s in enumerate(self._sessions):
            if s.session_id == session.session_id:
                self._sessions[i] = session
                found = True
                break
        if not found:
            self._sessions.append(session)

        persist_sessions(self._sessions, self._sessions_path)
        persist_turns([turn])
        persist_intents([intent])

    def never_execute_without_approval(self, response: OperatorResponse) -> None:
        """Safety invariant: verify no execution occurred."""
        if response.execution_occurred:
            logger.error(
                "SAFETY VIOLATION: execution_occurred=True on response %s",
                response.response_id,
            )
            response.execution_occurred = False
            response.errors.append("Safety violation corrected: execution flag was set")

    def get_session(self, session_id: str) -> OperatorSession | None:
        """Retrieve a session by ID."""
        for s in self._sessions:
            if s.session_id == session_id:
                return s
        return None

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent sessions."""
        return [s.to_dict() for s in self._sessions[-limit:]]

    # ── Intent routing ────────────────────────────────────────────────

    def _route_intent(
        self,
        intent: OperatorIntent,
        context: dict[str, Any],
        session: OperatorSession,
        turn: OperatorTurn,
    ) -> OperatorResponse:
        """Route classified intent to the appropriate flow."""
        handlers = {
            IntentType.CREATE_WORK.value: self._handle_create_work,
            IntentType.QUERY_STATUS.value: self._handle_query_status,
            IntentType.QUERY_APPROVALS.value: self._handle_query_approvals,
            IntentType.PREVIEW_PROPAGATION.value: self._handle_preview_propagation,
            IntentType.PREVIEW_TOPOLOGY.value: self._handle_preview_topology,
            IntentType.ROADMAP_QUERY.value: self._handle_roadmap_query,
            IntentType.RECOMMEND_NEXT.value: self._handle_recommend_next,
            IntentType.GENERAL_QUERY.value: self._handle_general_query,
        }
        handler = handlers.get(intent.intent_type, self._handle_general_query)
        return handler(intent, context, session, turn)

    def _handle_create_work(
        self,
        intent: OperatorIntent,
        context: dict[str, Any],
        session: OperatorSession,
        turn: OperatorTurn,
    ) -> OperatorResponse:
        """Handle work creation intent — preview only, never execute."""
        # Check duplicate suppression
        existing = self._find_duplicate_packet(intent)
        if existing:
            return OperatorResponse(
                summary="Duplicate work packet found. Existing packet returned.",
                output_mode=OutputMode.CONFIRMATION.value,
                work_packet_preview=existing,
                system_confidence=0.95,
                linked_packet_ids=[existing.get("packet_id", "")],
            )

        packet_preview = self.generate_work_packet(intent)
        topology_result = self.preview_delegation_topology(intent)
        human_actions = self.preview_human_actions(intent, context)
        approval_gates = self.preview_approval_gates(intent)

        # Attempt propagation preview
        propagation = None
        try:
            propagation = self.preview_propagation_impact(intent.raw_input)
        except Exception as e:
            logger.warning("propagation preview failed: %s", e)

        turn.linked_packet_ids.append(packet_preview.get("packet_id", ""))
        session.transition_status(SessionStatus.PACKET_DRAFTED.value)

        return OperatorResponse(
            summary="Work packet drafted. Review preview and approve to proceed.",
            output_mode=OutputMode.PREVIEW.value,
            work_packet_preview=packet_preview,
            delegation_topology_preview=topology_result.get("topology"),
            workcells_preview=topology_result.get("topology", {}).get("workcells", []),
            propagation_preview=propagation,
            human_required_actions=[a for a in human_actions if a["type"] == "human_action"],
            approval_required_actions=approval_gates,
            risks=self._assess_risks(intent),
            system_confidence=0.75,
            linked_packet_ids=[packet_preview.get("packet_id", "")],
            options=[
                Option(
                    label="Approve and release",
                    description="Release work packet to universal work queue",
                    action_key="approve_packet",
                    recommended=True,
                ),
                Option(
                    label="Modify constraints",
                    description="Add or change constraints before release",
                    action_key="modify_constraints",
                ),
                Option(
                    label="Discard",
                    description="Cancel this work packet",
                    action_key="discard_packet",
                    risk_class="low",
                ),
            ],
        )

    def _handle_query_status(
        self,
        intent: OperatorIntent,
        context: dict[str, Any],
        session: OperatorSession,
        turn: OperatorTurn,
    ) -> OperatorResponse:
        """Handle status query."""
        roadmap = self.query_roadmap_status()
        queue = self._get_work_queue_summary()
        approvals = self.query_pending_approvals()

        return OperatorResponse(
            summary="System status assembled from real state.",
            output_mode=OutputMode.FULL.value,
            data={
                "roadmap": roadmap,
                "work_queue": queue,
                "approvals": approvals,
            },
            system_confidence=0.95,
        )

    def _handle_query_approvals(
        self,
        intent: OperatorIntent,
        context: dict[str, Any],
        session: OperatorSession,
        turn: OperatorTurn,
    ) -> OperatorResponse:
        """Handle approval query."""
        approvals = self.query_pending_approvals()
        return OperatorResponse(
            summary="Pending approvals from real state. {} pending.".format(
                approvals["pending_count"]
            ),
            output_mode=OutputMode.FULL.value,
            data={"approvals": approvals},
            approval_required_actions=[
                {"approval_id": a.get("id", ""), "title": a.get("title", "")}
                for a in approvals.get("pending", [])
            ],
            system_confidence=0.95,
        )

    def _handle_preview_propagation(
        self,
        intent: OperatorIntent,
        context: dict[str, Any],
        session: OperatorSession,
        turn: OperatorTurn,
    ) -> OperatorResponse:
        """Handle propagation preview."""
        try:
            preview = self.preview_propagation_impact(intent.raw_input)
            plan_id = preview.get("propagation_plan", {}).get("plan_id", "")
            if plan_id:
                turn.linked_propagation_plan_ids.append(plan_id)
            return OperatorResponse(
                summary="Propagation impact preview computed. {} node(s) affected.".format(
                    preview.get("affected_count", 0)
                ),
                output_mode=OutputMode.PREVIEW.value,
                propagation_preview=preview,
                system_confidence=0.80,
                linked_propagation_plan_ids=[plan_id] if plan_id else [],
            )
        except Exception as e:
            logger.warning("propagation preview failed: %s", e)
            return OperatorResponse(
                summary="Propagation preview could not be computed.",
                output_mode=OutputMode.ERROR.value,
                errors=[str(e)],
                system_confidence=0.0,
            )

    def _handle_preview_topology(
        self,
        intent: OperatorIntent,
        context: dict[str, Any],
        session: OperatorSession,
        turn: OperatorTurn,
    ) -> OperatorResponse:
        """Handle topology preview."""
        try:
            result = self.preview_delegation_topology(intent)
            return OperatorResponse(
                summary="Delegation topology preview computed.",
                output_mode=OutputMode.PREVIEW.value,
                delegation_topology_preview=result.get("topology"),
                data={"classification": result.get("classification")},
                system_confidence=0.80,
                linked_packet_ids=[result.get("packet_id", "")],
            )
        except Exception as e:
            logger.warning("topology preview failed: %s", e)
            return OperatorResponse(
                summary="Topology preview could not be computed.",
                output_mode=OutputMode.ERROR.value,
                errors=[str(e)],
                system_confidence=0.0,
            )

    def _handle_roadmap_query(
        self,
        intent: OperatorIntent,
        context: dict[str, Any],
        session: OperatorSession,
        turn: OperatorTurn,
    ) -> OperatorResponse:
        """Handle roadmap query."""
        roadmap = self.query_roadmap_status()
        return OperatorResponse(
            summary="Roadmap status from real state. {} phase(s).".format(
                roadmap.get("total_phases", 0)
            ),
            output_mode=OutputMode.FULL.value,
            data={"roadmap": roadmap},
            system_confidence=0.95,
        )

    def _handle_recommend_next(
        self,
        intent: OperatorIntent,
        context: dict[str, Any],
        session: OperatorSession,
        turn: OperatorTurn,
    ) -> OperatorResponse:
        """Handle next action recommendation."""
        recommendations = self.recommend_next_action()
        return OperatorResponse(
            summary="Recommendations assembled from system state.",
            output_mode=OutputMode.FULL.value,
            data={"recommendations": recommendations},
            options=[
                Option(
                    label=r.get("description", ""),
                    action_key=r.get("action", ""),
                    recommended=(r.get("priority", 99) == 1),
                )
                for r in recommendations.get("recommendations", [])
            ],
            system_confidence=0.70,
        )

    def _handle_general_query(
        self,
        intent: OperatorIntent,
        context: dict[str, Any],
        session: OperatorSession,
        turn: OperatorTurn,
    ) -> OperatorResponse:
        """Handle unclassified query."""
        return OperatorResponse(
            summary="Intent not specifically classified. Providing system overview.",
            output_mode=OutputMode.SUMMARY.value,
            data={
                "context": context,
                "intent": intent.to_dict(),
            },
            system_confidence=0.3,
        )

    # ── Subsystem accessors (lazy import) ─────────────────────────────

    def _get_work_packet_engine(self):
        from substrate.organism.work_packet_engine import WorkPacketEngine
        return WorkPacketEngine(packets_path=self._work_packets_path)

    def _get_universal_work_queue(self):
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        return UniversalWorkQueue(store_path=self._work_packets_path)

    def _get_intent_classifier(self):
        from substrate.organism.intent_classifier import IntentClassifier
        return IntentClassifier()

    def _get_delegation_topology_planner(self):
        from substrate.organism.delegation_topology import DelegationTopologyPlanner
        return DelegationTopologyPlanner()

    def _get_propagation_graph(self):
        from substrate.organism.propagation_graph import PropagationGraph
        return PropagationGraph.load(path=self._propagation_graph_path)

    def _get_impact_analyzer(self, graph):
        from substrate.organism.impact_analyzer import ImpactAnalyzer
        return ImpactAnalyzer(graph)

    def _get_propagation_planner(self, graph):
        from substrate.organism.propagation_planner import PropagationPlanner
        return PropagationPlanner(graph)

    def _get_roadmap_engine(self):
        from substrate.organism.roadmap_engine import RoadmapEngine
        return RoadmapEngine(store_path=self._roadmap_path)

    def _get_self_build_queue(self):
        from substrate.organism.self_build_queue import SelfBuildQueue
        return SelfBuildQueue(store_path=self._self_build_path)

    def _get_template_registry(self):
        from substrate.organism.template_registry import TemplateRegistry
        return TemplateRegistry(store_dir=self._templates_path)

    def _get_agent_capability_model(self):
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        return AgentCapabilityModel(store_dir=self._agent_cap_path)

    def _get_approval_store(self):
        from substrate.organism.approval_store import ApprovalStore
        store_dir = self._approval_store_dir or os.path.join(
            _REPO_ROOT, "data", "umh", "organism",
        )
        return ApprovalStore(store_dir=store_dir)

    # ── Internal helpers ──────────────────────────────────────────────

    def _get_or_create_session(
        self, session_id: str | None = None,
    ) -> OperatorSession:
        """Get existing session or create new one."""
        if session_id:
            for s in self._sessions:
                if s.session_id == session_id:
                    return s
        session = OperatorSession()
        return session

    def _get_work_queue_summary(self) -> dict[str, Any]:
        """Get work queue summary from real state."""
        try:
            queue = self._get_universal_work_queue()
            active = [
                p for p in queue._packets.values()
                if p.status not in ("completed", "rejected", "failed", "superseded", "archived")
            ]
            return {
                "total_count": len(queue._packets),
                "active_count": len(active),
                "status_breakdown": self._count_statuses(queue._packets),
            }
        except Exception as e:
            logger.warning("work queue summary failed: %s", e)
            return {"total_count": 0, "active_count": 0, "error": str(e)}

    def _get_roadmap_summary(self) -> dict[str, Any]:
        """Get roadmap summary from real state."""
        try:
            return self.query_roadmap_status()
        except Exception as e:
            logger.warning("roadmap summary failed: %s", e)
            return {"error": str(e)}

    def _get_pending_approvals(self) -> dict[str, Any]:
        """Get pending approvals from real state."""
        try:
            return self.query_pending_approvals()
        except Exception as e:
            logger.warning("pending approvals failed: %s", e)
            return {"pending_count": 0, "error": str(e)}

    def _get_graph_summary(self) -> dict[str, Any]:
        """Get propagation graph summary."""
        try:
            graph = self._get_propagation_graph()
            return graph.graph_stats()
        except Exception as e:
            logger.warning("graph summary failed: %s", e)
            return {"error": str(e)}

    def _find_duplicate_packet(
        self, intent: OperatorIntent,
    ) -> dict[str, Any] | None:
        """Check for duplicate work packets with same intent."""
        try:
            queue = self._get_universal_work_queue()
            for packet in queue._packets.values():
                if (
                    packet.user_intent == intent.raw_input
                    and packet.status not in (
                        "completed", "rejected", "failed", "superseded", "archived",
                    )
                ):
                    return packet.to_dict()
        except Exception as e:
            logger.warning("duplicate check failed: %s", e)
        return None

    def _assess_risks(self, intent: OperatorIntent) -> list[dict[str, Any]]:
        """Assess risks for an intent."""
        classification = self._get_intent_classifier().classify(intent.raw_input)
        risks: list[dict[str, Any]] = []
        if classification.risk_class == "high":
            risks.append({
                "level": "high",
                "description": "High-risk operation detected. Requires manual review.",
            })
        if classification.risk_class == "medium":
            risks.append({
                "level": "medium",
                "description": "Medium-risk operation. Approval gate required.",
            })
        return risks

    @staticmethod
    def _count_statuses(packets: dict[str, Any]) -> dict[str, int]:
        """Count packets by status."""
        counts: dict[str, int] = {}
        for p in packets.values():
            status = getattr(p, "status", "unknown")
            if hasattr(status, "value"):
                status = status.value
            counts[status] = counts.get(status, 0) + 1
        return counts
