"""Source Truth Runtime — full organizational lineage (Campaign 22.6 CORE).

The runtime that makes UMH categorically better than Cursor/Replit/GitHub.
Tracks the complete chain:

  Intent → Decision → Requirement → WorkPacket → Execution →
  Review → Approval → Deployment → Outcome → Learning → Capability

GitHub tracks one layer (code). UMH tracks the full chain. This runtime
reads across existing subsystem data on demand — it does NOT maintain a
separate store. Each subsystem already has its own persistence; this
runtime assembles lineage graphs by cross-referencing them.

Deterministic. No LLM calls. Substrate layer. Instance-agnostic.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class LineageNodeType(str, Enum):
    """Every node type in the full organizational lineage chain."""
    INTENT = "intent"
    DECISION = "decision"
    REQUIREMENT = "requirement"
    WORK_PACKET = "work_packet"
    EXECUTION = "execution"
    REVIEW = "review"
    APPROVAL = "approval"
    DEPLOYMENT = "deployment"
    OUTCOME = "outcome"
    LESSON = "lesson"
    CAPABILITY = "capability"


# Canonical ordering — defines the natural upstream→downstream direction
_LINEAGE_ORDER: list[str] = [
    LineageNodeType.INTENT.value,
    LineageNodeType.DECISION.value,
    LineageNodeType.REQUIREMENT.value,
    LineageNodeType.WORK_PACKET.value,
    LineageNodeType.EXECUTION.value,
    LineageNodeType.REVIEW.value,
    LineageNodeType.APPROVAL.value,
    LineageNodeType.DEPLOYMENT.value,
    LineageNodeType.OUTCOME.value,
    LineageNodeType.LESSON.value,
    LineageNodeType.CAPABILITY.value,
]


class LineageTerminalState(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    ORPHANED = "orphaned"


@dataclass
class LineageNode:
    """A single node in the organizational lineage graph."""
    node_id: str = ""
    node_type: str = LineageNodeType.INTENT.value
    title: str = ""
    source_id: str = ""
    parent_id: str = ""
    children: list[str] = field(default_factory=list)
    created_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "title": self.title,
            "source_id": self.source_id,
            "parent_id": self.parent_id,
            "children": list(self.children),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LineageNode:
        return cls(
            node_id=d.get("node_id", ""),
            node_type=d.get("node_type", LineageNodeType.INTENT.value),
            title=d.get("title", ""),
            source_id=d.get("source_id", ""),
            parent_id=d.get("parent_id", ""),
            children=list(d.get("children", [])),
            created_at=d.get("created_at", 0.0),
            metadata=dict(d.get("metadata", {})),
        )


@dataclass
class LineageChain:
    """A complete lineage chain from intent to capability."""
    chain_id: str = ""
    root_intent: str = ""
    nodes: list[dict[str, Any]] = field(default_factory=list)
    depth: int = 0
    terminal_state: str = LineageTerminalState.IN_PROGRESS.value
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "root_intent": self.root_intent,
            "nodes": list(self.nodes),
            "depth": self.depth,
            "terminal_state": self.terminal_state,
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LineageChain:
        return cls(
            chain_id=d.get("chain_id", ""),
            root_intent=d.get("root_intent", ""),
            nodes=list(d.get("nodes", [])),
            depth=d.get("depth", 0),
            terminal_state=d.get("terminal_state", LineageTerminalState.IN_PROGRESS.value),
            generated_at=d.get("generated_at", 0.0),
        )


@dataclass
class LineageSummary:
    """Aggregate lineage statistics across the organism."""
    total_chains: int = 0
    complete_chains: int = 0
    in_progress_chains: int = 0
    failed_chains: int = 0
    orphaned_work_packets: int = 0
    deepest_chain: int = 0
    avg_chain_depth: float = 0.0
    nodes_by_type: dict[str, int] = field(default_factory=dict)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SourceTruthRuntime:
    """Full organizational lineage — cross-references all subsystems.

    Reads across DecisionRegistry, WorkPacketEngine, ExecutionCoordinator,
    LearningExtractionRuntime, CapabilityEvolutionEngine, and
    GovernanceRuntime to assemble lineage graphs on demand.

    No separate store. Each subsystem owns its own persistence.
    This runtime reads across them to build the chain.
    """

    def __init__(
        self,
        decision_registry: Any | None = None,
        work_packet_engine: Any | None = None,
        execution_coordinator: Any | None = None,
        learning_extraction: Any | None = None,
        capability_evolution: Any | None = None,
        governance_runtime: Any | None = None,
    ) -> None:
        self._decision_registry_inst = decision_registry
        self._work_packet_engine_inst = work_packet_engine
        self._execution_coordinator_inst = execution_coordinator
        self._learning_extraction_inst = learning_extraction
        self._capability_evolution_inst = capability_evolution
        self._governance_runtime_inst = governance_runtime

    # ── Lazy subsystem composition ─────────────────────────────────────

    @property
    def _decision_registry(self) -> Any | None:
        if self._decision_registry_inst is not None:
            return self._decision_registry_inst
        try:
            from substrate.organism.decision_registry import DecisionRegistry
            self._decision_registry_inst = DecisionRegistry()
            return self._decision_registry_inst
        except Exception:
            logger.debug("DecisionRegistry unavailable")
            return None

    @property
    def _work_packet_engine(self) -> Any | None:
        if self._work_packet_engine_inst is not None:
            return self._work_packet_engine_inst
        try:
            from substrate.organism.work_packet_engine import WorkPacketEngine
            self._work_packet_engine_inst = WorkPacketEngine()
            return self._work_packet_engine_inst
        except Exception:
            logger.debug("WorkPacketEngine unavailable")
            return None

    @property
    def _execution_coordinator(self) -> Any | None:
        if self._execution_coordinator_inst is not None:
            return self._execution_coordinator_inst
        try:
            from substrate.organism.execution_coordinator import ExecutionCoordinator
            self._execution_coordinator_inst = ExecutionCoordinator()
            return self._execution_coordinator_inst
        except Exception:
            logger.debug("ExecutionCoordinator unavailable")
            return None

    @property
    def _learning_extraction(self) -> Any | None:
        if self._learning_extraction_inst is not None:
            return self._learning_extraction_inst
        try:
            from substrate.organism.learning_extraction_runtime import LearningExtractionRuntime
            self._learning_extraction_inst = LearningExtractionRuntime()
            return self._learning_extraction_inst
        except Exception:
            logger.debug("LearningExtractionRuntime unavailable")
            return None

    @property
    def _capability_evolution(self) -> Any | None:
        if self._capability_evolution_inst is not None:
            return self._capability_evolution_inst
        try:
            from substrate.organism.capability_evolution_engine import CapabilityEvolutionEngine
            self._capability_evolution_inst = CapabilityEvolutionEngine()
            return self._capability_evolution_inst
        except Exception:
            logger.debug("CapabilityEvolutionEngine unavailable")
            return None

    @property
    def _governance_runtime(self) -> Any | None:
        if self._governance_runtime_inst is not None:
            return self._governance_runtime_inst
        try:
            from substrate.organism.governance_runtime import GovernanceRuntime
            self._governance_runtime_inst = GovernanceRuntime()
            return self._governance_runtime_inst
        except Exception:
            logger.debug("GovernanceRuntime unavailable")
            return None

    # ── Node extraction helpers ────────────────────────────────────────

    def _extract_intent_nodes(self) -> list[LineageNode]:
        """Extract intent nodes from work packets (intents are the root source)."""
        nodes: list[LineageNode] = []
        wpe = self._work_packet_engine
        if not wpe:
            return nodes
        try:
            packets = wpe.all_packets()
        except Exception:
            logger.debug("Failed to read packets for intent extraction")
            return nodes

        seen_intents: set[str] = set()
        for pkt in packets:
            intent_text = getattr(pkt, "user_intent", "") or ""
            if not intent_text:
                continue
            intent_key = intent_text[:120]
            if intent_key in seen_intents:
                continue
            seen_intents.add(intent_key)
            source_id = getattr(pkt, "source_id", "") or getattr(pkt, "packet_id", "")
            nodes.append(LineageNode(
                node_id=f"intent-{source_id}",
                node_type=LineageNodeType.INTENT.value,
                title=intent_text[:200],
                source_id=source_id,
                created_at=getattr(pkt, "created_at", 0.0),
                metadata={"packet_id": getattr(pkt, "packet_id", "")},
            ))
        return nodes

    def _extract_decision_nodes(self) -> list[LineageNode]:
        """Extract decision nodes from DecisionRegistry."""
        nodes: list[LineageNode] = []
        dr = self._decision_registry
        if not dr:
            return nodes
        try:
            decisions = dr.list_decisions()
        except Exception:
            logger.debug("Failed to read decisions")
            return nodes

        for dec in decisions:
            dec_id = getattr(dec, "decision_id", "")
            wp_refs = getattr(dec, "work_packet_refs", [])
            nodes.append(LineageNode(
                node_id=f"decision-{dec_id}",
                node_type=LineageNodeType.DECISION.value,
                title=getattr(dec, "title", ""),
                source_id=dec_id,
                children=[f"work_packet-{wp}" for wp in wp_refs],
                created_at=getattr(dec, "created_at", 0.0),
                metadata={
                    "status": getattr(dec, "status", ""),
                    "rationale": getattr(dec, "rationale", "")[:200],
                    "goal_refs": getattr(dec, "goal_refs", []),
                },
            ))
        return nodes

    def _extract_work_packet_nodes(self) -> list[LineageNode]:
        """Extract work packet nodes from WorkPacketEngine."""
        nodes: list[LineageNode] = []
        wpe = self._work_packet_engine
        if not wpe:
            return nodes
        try:
            packets = wpe.all_packets()
        except Exception:
            logger.debug("Failed to read work packets")
            return nodes

        for pkt in packets:
            pkt_id = getattr(pkt, "packet_id", "")
            parent_id = getattr(pkt, "parent_packet_id", "")
            child_ids = getattr(pkt, "child_packet_ids", [])
            source_type = getattr(pkt, "source_type", "")

            parent_lineage = ""
            if parent_id:
                parent_lineage = f"work_packet-{parent_id}"
            elif source_type == "operator_request":
                source_id = getattr(pkt, "source_id", "")
                parent_lineage = f"intent-{source_id}" if source_id else ""

            children: list[str] = [f"work_packet-{c}" for c in child_ids]

            nodes.append(LineageNode(
                node_id=f"work_packet-{pkt_id}",
                node_type=LineageNodeType.WORK_PACKET.value,
                title=getattr(pkt, "title", "") or getattr(pkt, "user_intent", "")[:100],
                source_id=pkt_id,
                parent_id=parent_lineage,
                children=children,
                created_at=getattr(pkt, "created_at", 0.0),
                metadata={
                    "status": getattr(pkt, "status", ""),
                    "risk_class": getattr(pkt, "risk_class", ""),
                    "domain": getattr(pkt, "domain", ""),
                },
            ))
        return nodes

    def _extract_execution_nodes(self) -> list[LineageNode]:
        """Extract execution nodes from ExecutionCoordinator."""
        nodes: list[LineageNode] = []
        ec = self._execution_coordinator
        if not ec:
            return nodes

        plans: list[Any] = []
        try:
            if hasattr(ec, "all_plans"):
                plans = ec.all_plans()
            elif hasattr(ec, "_plans"):
                plans = list(ec._plans.values()) if isinstance(ec._plans, dict) else list(ec._plans)
        except Exception:
            logger.debug("Failed to read execution plans")
            return nodes

        for plan in plans:
            plan_id = getattr(plan, "execution_plan_id", "")
            wp_id = getattr(plan, "source_workpacket_id", "")

            nodes.append(LineageNode(
                node_id=f"execution-{plan_id}",
                node_type=LineageNodeType.EXECUTION.value,
                title=getattr(plan, "description", "") or f"Execution of {wp_id}",
                source_id=plan_id,
                parent_id=f"work_packet-{wp_id}" if wp_id else "",
                created_at=getattr(plan, "created_at", 0.0),
                metadata={
                    "status": getattr(plan, "status", ""),
                    "target_executor": getattr(plan, "target_executor", ""),
                    "approval_state": getattr(plan, "approval_state", ""),
                },
            ))
        return nodes

    def _extract_lesson_nodes(self) -> list[LineageNode]:
        """Extract lesson nodes from LearningExtractionRuntime."""
        nodes: list[LineageNode] = []
        le = self._learning_extraction
        if not le:
            return nodes
        try:
            lessons = le.recent_lessons(limit=500)
        except Exception:
            logger.debug("Failed to read lessons")
            return nodes

        for lesson in lessons:
            lesson_id = getattr(lesson, "lesson_id", "")
            related_decisions = getattr(lesson, "related_decision_ids", [])
            related_outcomes = getattr(lesson, "related_outcome_ids", [])

            parent = ""
            if related_outcomes:
                parent = f"outcome-{related_outcomes[0]}"
            elif related_decisions:
                parent = f"decision-{related_decisions[0]}"

            nodes.append(LineageNode(
                node_id=f"lesson-{lesson_id}",
                node_type=LineageNodeType.LESSON.value,
                title=getattr(lesson, "title", ""),
                source_id=lesson_id,
                parent_id=parent,
                created_at=getattr(lesson, "extracted_at", 0.0),
                metadata={
                    "category": getattr(lesson, "category", ""),
                    "confidence": getattr(lesson, "confidence", 0.0),
                    "actionable": getattr(lesson, "actionable", False),
                    "related_capability_ids": getattr(lesson, "related_capability_ids", []),
                },
            ))
        return nodes

    def _extract_capability_nodes(self) -> list[LineageNode]:
        """Extract capability nodes from CapabilityEvolutionEngine."""
        nodes: list[LineageNode] = []
        ce = self._capability_evolution
        if not ce:
            return nodes
        try:
            trajectories = ce.all_trajectories()
        except Exception:
            logger.debug("Failed to read capability trajectories")
            return nodes

        for traj in trajectories:
            cap_id = getattr(traj, "capability_id", "")
            events = getattr(traj, "events", [])
            trigger_outcomes: list[str] = []
            for ev in events:
                to_id = ""
                if isinstance(ev, dict):
                    to_id = ev.get("trigger_outcome_id", "")
                else:
                    to_id = getattr(ev, "trigger_outcome_id", "")
                if to_id:
                    trigger_outcomes.append(to_id)

            parent = ""
            if trigger_outcomes:
                parent = f"outcome-{trigger_outcomes[0]}"

            nodes.append(LineageNode(
                node_id=f"capability-{cap_id}",
                node_type=LineageNodeType.CAPABILITY.value,
                title=getattr(traj, "capability_id", cap_id),
                source_id=cap_id,
                parent_id=parent,
                created_at=getattr(traj, "first_event_at", 0.0) if hasattr(traj, "first_event_at") else 0.0,
                metadata={
                    "current_level": getattr(traj, "current_level", ""),
                    "trend": getattr(traj, "trend", 0.0),
                    "event_count": len(events),
                },
            ))
        return nodes

    def _extract_governance_nodes(self) -> list[LineageNode]:
        """Extract approval nodes from GovernanceRuntime conflict records."""
        nodes: list[LineageNode] = []
        gr = self._governance_runtime
        if not gr:
            return nodes
        try:
            if hasattr(gr, "recent_resolutions"):
                resolutions = gr.recent_resolutions(limit=200)
            elif hasattr(gr, "_conflicts"):
                resolutions = list(gr._conflicts.values()) if isinstance(gr._conflicts, dict) else list(gr._conflicts)
            else:
                return nodes
        except Exception:
            logger.debug("Failed to read governance resolutions")
            return nodes

        for res in resolutions:
            conflict_id = ""
            if isinstance(res, dict):
                conflict_id = res.get("conflict_id", "")
            else:
                conflict_id = getattr(res, "conflict_id", "")

            if not conflict_id:
                continue

            status = ""
            if isinstance(res, dict):
                status = res.get("status", "")
            else:
                status = getattr(res, "status", "")

            created = 0.0
            if isinstance(res, dict):
                created = res.get("detected_at", 0.0)
            else:
                created = getattr(res, "detected_at", 0.0)

            nodes.append(LineageNode(
                node_id=f"approval-{conflict_id}",
                node_type=LineageNodeType.APPROVAL.value,
                title=f"Governance resolution {conflict_id}",
                source_id=conflict_id,
                created_at=created,
                metadata={"status": status},
            ))
        return nodes

    # ── Graph assembly ─────────────────────────────────────────────────

    def _build_full_graph(self) -> dict[str, LineageNode]:
        """Assemble all lineage nodes from all subsystems into a graph."""
        graph: dict[str, LineageNode] = {}

        extractors = [
            self._extract_intent_nodes,
            self._extract_decision_nodes,
            self._extract_work_packet_nodes,
            self._extract_execution_nodes,
            self._extract_governance_nodes,
            self._extract_lesson_nodes,
            self._extract_capability_nodes,
        ]

        for extractor in extractors:
            try:
                nodes = extractor()
                for node in nodes:
                    if node.node_id:
                        graph[node.node_id] = node
            except Exception:
                logger.debug("Extractor %s failed", extractor.__name__)

        # Wire parent→child bidirectional links
        for node in graph.values():
            if node.parent_id and node.parent_id in graph:
                parent = graph[node.parent_id]
                if node.node_id not in parent.children:
                    parent.children.append(node.node_id)

        # Wire decision→work_packet links from decision.work_packet_refs
        for node in graph.values():
            if node.node_type == LineageNodeType.WORK_PACKET.value:
                wp_source_id = node.source_id
                for dec_node in graph.values():
                    if dec_node.node_type != LineageNodeType.DECISION.value:
                        continue
                    dec_wp_refs = dec_node.metadata.get("work_packet_refs_raw", [])
                    if not dec_wp_refs:
                        child_key = f"work_packet-{wp_source_id}"
                        if child_key in dec_node.children:
                            if not node.parent_id:
                                node.parent_id = dec_node.node_id

        return graph

    def _trace_upstream(self, node_id: str, graph: dict[str, LineageNode], visited: set[str] | None = None) -> list[LineageNode]:
        """Walk upstream from a node to its root."""
        if visited is None:
            visited = set()
        if node_id in visited or node_id not in graph:
            return []
        visited.add(node_id)

        node = graph[node_id]
        chain: list[LineageNode] = [node]

        if node.parent_id and node.parent_id in graph:
            upstream = self._trace_upstream(node.parent_id, graph, visited)
            chain = upstream + chain

        return chain

    def _trace_downstream(self, node_id: str, graph: dict[str, LineageNode], visited: set[str] | None = None) -> list[LineageNode]:
        """Walk downstream from a node through its children."""
        if visited is None:
            visited = set()
        if node_id in visited or node_id not in graph:
            return []
        visited.add(node_id)

        node = graph[node_id]
        chain: list[LineageNode] = [node]

        for child_id in node.children:
            if child_id in graph and child_id not in visited:
                downstream = self._trace_downstream(child_id, graph, visited)
                chain.extend(downstream)

        return chain

    def _determine_terminal_state(self, nodes: list[LineageNode]) -> str:
        """Determine the terminal state of a lineage chain."""
        if not nodes:
            return LineageTerminalState.ORPHANED.value

        type_set = {n.node_type for n in nodes}

        if LineageNodeType.CAPABILITY.value in type_set:
            return LineageTerminalState.COMPLETED.value

        has_failed = any(
            n.metadata.get("status", "") in ("failed", "cancelled", "FAILED", "CANCELLED")
            for n in nodes
        )
        if has_failed:
            return LineageTerminalState.FAILED.value

        return LineageTerminalState.IN_PROGRESS.value

    # ── Public API ─────────────────────────────────────────────────────

    def trace_lineage(self, node_id: str, node_type: str = "") -> LineageChain:
        """Given any node, trace upstream to intent and downstream to capability.

        Args:
            node_id: The source_id from the subsystem (e.g., a packet_id,
                     decision_id, lesson_id).
            node_type: Optional LineageNodeType value to disambiguate.
                       If omitted, tries all type prefixes.

        Returns:
            LineageChain with all linked nodes.
        """
        graph = self._build_full_graph()

        # Resolve the lineage node_id from the source_id
        lineage_key = ""
        if node_type:
            candidate = f"{node_type}-{node_id}"
            if candidate in graph:
                lineage_key = candidate
        if not lineage_key:
            for nt in _LINEAGE_ORDER:
                candidate = f"{nt}-{node_id}"
                if candidate in graph:
                    lineage_key = candidate
                    break
        if not lineage_key:
            for key, node in graph.items():
                if node.source_id == node_id:
                    lineage_key = key
                    break

        if not lineage_key:
            return LineageChain(
                chain_id=f"chain-{uuid4().hex[:8]}",
                root_intent="",
                nodes=[],
                depth=0,
                terminal_state=LineageTerminalState.ORPHANED.value,
                generated_at=time.time(),
            )

        # Trace upstream (toward root intent)
        upstream = self._trace_upstream(lineage_key, graph, set())

        # Trace downstream (toward capabilities) — separate visited set
        downstream = self._trace_downstream(lineage_key, graph, set())

        # Merge: upstream + downstream, dedup by node_id
        seen_ids: set[str] = set()
        all_nodes: list[LineageNode] = []
        for node in upstream:
            if node.node_id not in seen_ids:
                seen_ids.add(node.node_id)
                all_nodes.append(node)
        for node in downstream:
            if node.node_id not in seen_ids:
                seen_ids.add(node.node_id)
                all_nodes.append(node)

        # Sort by canonical order then creation time
        type_order = {t: i for i, t in enumerate(_LINEAGE_ORDER)}
        all_nodes.sort(key=lambda n: (type_order.get(n.node_type, 99), n.created_at))

        root_intent = ""
        for n in all_nodes:
            if n.node_type == LineageNodeType.INTENT.value:
                root_intent = n.title
                break

        terminal = self._determine_terminal_state(all_nodes)

        return LineageChain(
            chain_id=f"chain-{uuid4().hex[:8]}",
            root_intent=root_intent,
            nodes=[n.to_dict() for n in all_nodes],
            depth=len(all_nodes),
            terminal_state=terminal,
            generated_at=time.time(),
        )

    def intent_to_capability(self, intent_id: str) -> LineageChain:
        """Trace a full chain from an intent to any resulting capabilities."""
        return self.trace_lineage(intent_id, LineageNodeType.INTENT.value)

    def why_does_this_exist(self, artifact_id: str) -> dict[str, Any]:
        """Given any artifact ID, trace back to the originating intent.

        Returns a dict with the root intent and the full upstream path.
        """
        chain = self.trace_lineage(artifact_id)
        intent_nodes = [
            n for n in chain.nodes
            if n.get("node_type") == LineageNodeType.INTENT.value
        ]
        decision_nodes = [
            n for n in chain.nodes
            if n.get("node_type") == LineageNodeType.DECISION.value
        ]

        return {
            "artifact_id": artifact_id,
            "root_intent": chain.root_intent,
            "intent_nodes": intent_nodes,
            "decision_nodes": decision_nodes,
            "full_chain": chain.to_dict(),
            "depth": chain.depth,
            "terminal_state": chain.terminal_state,
        }

    def full_chain(self, root_intent_id: str) -> LineageChain:
        """Get the complete lineage chain from a root intent ID."""
        return self.trace_lineage(root_intent_id, LineageNodeType.INTENT.value)

    def orphaned_work(self) -> list[dict[str, Any]]:
        """Find work packets with no upstream intent — a governance smell.

        Orphaned work indicates packets created without a traceable intent,
        meaning no one can answer "why does this exist?"
        """
        graph = self._build_full_graph()
        orphans: list[dict[str, Any]] = []

        for node_id, node in graph.items():
            if node.node_type != LineageNodeType.WORK_PACKET.value:
                continue

            has_upstream = False
            current = node
            visited: set[str] = set()
            while current.parent_id and current.parent_id in graph:
                if current.parent_id in visited:
                    break
                visited.add(current.parent_id)
                parent = graph[current.parent_id]
                if parent.node_type in (
                    LineageNodeType.INTENT.value,
                    LineageNodeType.DECISION.value,
                ):
                    has_upstream = True
                    break
                current = parent

            if not has_upstream:
                orphans.append({
                    "node_id": node_id,
                    "source_id": node.source_id,
                    "title": node.title,
                    "status": node.metadata.get("status", ""),
                    "created_at": node.created_at,
                })

        return orphans

    def nodes_by_type(self, node_type: str) -> list[dict[str, Any]]:
        """Get all lineage nodes of a given type."""
        graph = self._build_full_graph()
        return [
            n.to_dict() for n in graph.values()
            if n.node_type == node_type
        ]

    def chain_health(self) -> dict[str, Any]:
        """Assess overall lineage health across the organism.

        Healthy chains have upstream intents and downstream outcomes.
        Unhealthy patterns: orphaned work, broken chains, failed terminal states.
        """
        graph = self._build_full_graph()
        chains_by_intent: dict[str, list[LineageNode]] = {}

        # Group nodes by their root intent
        for node in graph.values():
            if node.node_type == LineageNodeType.INTENT.value:
                chain_nodes = self._trace_downstream(node.node_id, graph, set())
                chains_by_intent[node.node_id] = chain_nodes

        complete = 0
        in_progress = 0
        failed = 0
        for _intent_id, chain_nodes in chains_by_intent.items():
            state = self._determine_terminal_state(chain_nodes)
            if state == LineageTerminalState.COMPLETED.value:
                complete += 1
            elif state == LineageTerminalState.FAILED.value:
                failed += 1
            else:
                in_progress += 1

        orphans = self.orphaned_work()
        total = len(chains_by_intent)

        return {
            "total_chains": total,
            "complete": complete,
            "in_progress": in_progress,
            "failed": failed,
            "orphaned_work_packets": len(orphans),
            "completion_rate": round(complete / total, 4) if total else 0.0,
            "health": (
                "healthy" if total > 0 and complete / total > 0.5 and len(orphans) == 0
                else "degraded" if len(orphans) > 0
                else "building" if total > 0
                else "empty"
            ),
        }

    def summary(self) -> dict[str, Any]:
        """High-level summary of organizational lineage state."""
        graph = self._build_full_graph()

        nodes_by_type: dict[str, int] = {}
        for node in graph.values():
            nodes_by_type[node.node_type] = nodes_by_type.get(node.node_type, 0) + 1

        chain_depths: list[int] = []
        for node in graph.values():
            if node.node_type == LineageNodeType.INTENT.value:
                chain = self._trace_downstream(node.node_id, graph, set())
                chain_depths.append(len(chain))

        orphans = self.orphaned_work()
        health = self.chain_health()

        return {
            "total_nodes": len(graph),
            "nodes_by_type": nodes_by_type,
            "total_chains": len(chain_depths),
            "deepest_chain": max(chain_depths) if chain_depths else 0,
            "avg_chain_depth": round(sum(chain_depths) / len(chain_depths), 2) if chain_depths else 0.0,
            "orphaned_work_packets": len(orphans),
            "health": health.get("health", "empty"),
            "completion_rate": health.get("completion_rate", 0.0),
            "generated_at": time.time(),
        }
