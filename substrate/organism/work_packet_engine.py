"""Work Packet Engine — creates work packets from user intent.

Orchestrates intent classification, context assembly, delegation topology
planning, workcell generation, scoring, and persistence. The engine is
the primary entry point for converting high-level intent into structured,
governed work.

Phase 11.1. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from substrate.execution.cpu_gate import gated_subprocess_run
from substrate.organism.delegation_topology import DelegationTopology, DelegationTopologyPlanner
from substrate.organism.intent_classifier import IntentClassification, IntentClassifier
from substrate.organism.knowledge_model_registry import (
    KnowledgeModel,
    KnowledgeModelRegistry,
)
from substrate.organism.role_contracts import (
    SEED_ROLE_CONTRACTS,
    RoleContract,
    load_role_contracts,
)
from substrate.organism.work_packet import (
    _VALID_TRANSITIONS,
    PacketLifecycleStatus,
    WorkPacket,
    load_packets,
    persist_packets,
)
from substrate.organism.workcell import (
    AdvisorBranch,
    PlanningWorkcellStatus,
    Workcell,
    persist_workcells,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class WorkPacketEngine:
    """Creates and manages work packets from user intent."""

    def __init__(
        self,
        packets_path: str | None = None,
        workcells_path: str | None = None,
        roles_path: str | None = None,
        knowledge_path: str | None = None,
    ) -> None:
        from substrate.state.runtime_paths import runtime_state_path

        self._packets_path = packets_path or str(
            runtime_state_path("universal_work", "work_packets.jsonl", create_parent=False)
        )
        self._workcells_path = workcells_path or str(
            runtime_state_path("universal_work", "workcells.jsonl", create_parent=False)
        )
        self._classifier = IntentClassifier()
        self._topo_planner = DelegationTopologyPlanner()
        self._km_registry = KnowledgeModelRegistry(store_path=knowledge_path)
        self._packets: list[WorkPacket] = load_packets(self._packets_path)
        self._workcells: list[Workcell] = []
        self._role_contracts = load_role_contracts(roles_path)
        if not self._role_contracts:
            self._role_contracts = [RoleContract.from_dict(d) for d in SEED_ROLE_CONTRACTS]

    def create_packet_from_intent(
        self,
        user_intent: str,
        desired_end_state: str = "",
        constraints: list[str] | None = None,
        source_type: str = "operator_request",
        source_id: str = "",
        source_evidence: list[dict[str, Any]] | None = None,
    ) -> WorkPacket:
        classification = self.classify_intent(user_intent)
        context = self.assemble_context(classification)
        knowledge_models = self.select_knowledge_models(classification)
        role_contracts = self.select_role_contracts(classification)

        packet = WorkPacket(
            title=self._generate_title(user_intent, classification),
            user_intent=user_intent,
            desired_end_state=desired_end_state or classification.desired_output,
            intent_summary=f"{classification.work_type} in {classification.domain}",
            domain=classification.domain,
            subdomain=classification.subdomain,
            project=classification.project,
            company=classification.company,
            product=classification.product,
            related_entities=[classification.entity] if classification.entity else [],
            source_type=source_type,
            source_id=source_id,
            source_evidence=source_evidence or [{"type": "user_intent", "text": user_intent}],
            context_summary=context,
            constraints=constraints or [],
            success_criteria=self._generate_success_criteria(classification, desired_end_state),
            failure_criteria=self._generate_failure_criteria(classification),
            risk_class=classification.risk_class,
            risk_factors=self._assess_risk_factors(classification),
            expected_impact=classification.desired_output,
            required_knowledge_models=[km.knowledge_model_id for km in knowledge_models],
            required_role_contracts=[rc.role_id for rc in role_contracts],
            human_required_actions=self.map_human_required_actions(classification),
            approval_gates=self.map_approval_gates(classification),
            validation_plan=self.map_validation_plan(classification),
            rollback_plan=self.map_rollback_plan(classification),
            propagation_plan=self.map_propagation_plan(classification),
            status=PacketLifecycleStatus.DRAFTED,
        )

        topo = self.plan_delegation_topology(packet, classification)
        packet.delegation_topology_id = topo.topology_id

        workcells = self.generate_workcells(packet, topo, classification)
        packet.workcells = [wc.workcell_id for wc in workcells]

        if topo.advisor_council:
            packet.advisor_council = topo.advisor_council
            packet.reconvergence_protocol = topo.reconvergence_protocol

        self.score_leverage(packet, classification)
        self.score_effectiveness(packet, classification)
        self.score_efficiency(packet, classification)

        target_proj = self.detect_target_projection(user_intent)
        if target_proj:
            packet.target_projection = target_proj

        packet.status = PacketLifecycleStatus.CLASSIFIED
        packet.updated_at = time.time()

        self._packets.append(packet)
        self._workcells.extend(workcells)
        self.persist_packet()

        return packet

    def decompose_intent_to_batch(
        self,
        user_intent: str,
        desired_end_state: str = "",
        constraints: list[str] | None = None,
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        """Decompose high-level intent into a batch of linked work packets.

        Returns persistent, dependency-ordered, overnight-classified batch.
        Idempotent: same idempotency_key returns existing batch.
        """
        import hashlib

        from substrate.organism.dependency_graph import (
            DependencyEdge,
            DependencyGraph,
            DependencyNode,
            DependencyStrength,
            DependencyType,
        )

        if not idempotency_key:
            idempotency_key = hashlib.sha256(
                f"{user_intent}|{desired_end_state}".encode()
            ).hexdigest()[:16]

        # Check idempotency — return existing batch if found
        for pkt in self._packets:
            if pkt.source_id == idempotency_key and pkt.child_packet_ids:
                children = [p for p in self._packets if p.packet_id in pkt.child_packet_ids]
                return {
                    "batch_id": pkt.packet_id,
                    "idempotency_key": idempotency_key,
                    "parent_packet": pkt.to_safe_dict(),
                    "child_packets": [c.to_safe_dict() for c in children],
                    "dependency_edges": [],
                    "overnight_classification": {
                        c.packet_id: self._classify_overnight_safety(c) for c in children
                    },
                    "created_count": len(children),
                    "already_existed": True,
                    "ok": True,
                }

        classification = self.classify_intent(user_intent)

        # Detect multi-step intent even when classifier says "simple"
        # Multiple work-type keywords indicate batch-worthy work
        _multi_step_signals = [
            "and deploy",
            "and test",
            "with tests",
            "with documentation",
            "then deploy",
            "then test",
            "then verify",
            "build and",
            "implement and",
            "create and",
            "and monitor",
        ]
        intent_lower = user_intent.lower()
        multi_step_count = sum(1 for s in _multi_step_signals if s in intent_lower)
        needs_decomposition = (
            classification.complexity in ("complex", "strategic")
            or multi_step_count >= 1
            or (classification.risk_class in ("medium", "high") and len(user_intent) > 80)
        )

        # Simple intent → single packet, no decomposition
        if not needs_decomposition:
            packet = self.create_packet_from_intent(
                user_intent=user_intent,
                desired_end_state=desired_end_state,
                constraints=constraints,
                source_id=idempotency_key,
            )
            return {
                "batch_id": packet.packet_id,
                "idempotency_key": idempotency_key,
                "parent_packet": packet.to_safe_dict(),
                "child_packets": [],
                "dependency_edges": [],
                "overnight_classification": {
                    packet.packet_id: self._classify_overnight_safety(packet),
                },
                "created_count": 1,
                "already_existed": False,
                "ok": True,
            }

        # Complex/strategic → batch decomposition
        # 1. Create + persist parent packet first
        parent = WorkPacket(
            title=f"Batch: {self._generate_title(user_intent, classification)}",
            user_intent=user_intent,
            desired_end_state=desired_end_state or classification.desired_output,
            intent_summary=f"batch:{classification.work_type} in {classification.domain}",
            domain=classification.domain,
            source_type="batch_decomposition",
            source_id=idempotency_key,
            constraints=constraints or [],
            risk_class=classification.risk_class,
            status=PacketLifecycleStatus.PLANNED,
        )
        self._packets.append(parent)
        self.persist_packet()

        # 2. Determine child steps by work type
        steps = self._decomposition_steps(classification.work_type)

        # 3. Create child packets — persist each immediately
        children: list[WorkPacket] = []
        created_ids: list[str] = []
        try:
            for i, (step_type, step_label) in enumerate(steps):
                child = WorkPacket(
                    title=f"{step_label}: {parent.title.replace('Batch: ', '')}",
                    user_intent=f"{step_label} for: {user_intent}",
                    desired_end_state=f"{step_label} complete",
                    intent_summary=f"{step_type} in {classification.domain}",
                    domain=classification.domain,
                    source_type="batch_child",
                    source_id=idempotency_key,
                    constraints=constraints or [],
                    risk_class=self._child_risk_class(step_type, classification),
                    parent_packet_id=parent.packet_id,
                    status=PacketLifecycleStatus.PLANNED,
                    priority=50 + (len(steps) - i),
                )
                self._packets.append(child)
                children.append(child)
                created_ids.append(child.packet_id)
                self.persist_packet()
        except Exception as exc:
            logger.warning(
                "batch decomposition partial failure at child %d: %s", len(created_ids), exc
            )
            parent.child_packet_ids = created_ids
            self.persist_packet()
            return {
                "batch_id": parent.packet_id,
                "idempotency_key": idempotency_key,
                "parent_packet": parent.to_safe_dict(),
                "child_packets": [c.to_safe_dict() for c in children],
                "dependency_edges": [],
                "overnight_classification": {
                    c.packet_id: self._classify_overnight_safety(c) for c in children
                },
                "created_count": len(created_ids),
                "ok": False,
                "partial": True,
                "error": str(exc),
            }

        # 4. Update parent with child IDs
        parent.child_packet_ids = created_ids
        self.persist_packet()

        # 5. Build dependency graph (sequential edges)
        dep_graph = DependencyGraph()
        for child in children:
            dep_graph.add_node(
                DependencyNode(
                    id=child.packet_id,
                    name=child.title,
                    category=child.domain,
                )
            )
        edges_serialized: list[dict[str, Any]] = []
        for i in range(len(children) - 1):
            edge = DependencyEdge(
                source=children[i + 1].packet_id,
                target=children[i].packet_id,
                dep_type=DependencyType.EXECUTION,
                strength=DependencyStrength.HARD,
                evidence=f"{children[i].title} must complete before {children[i + 1].title}",
            )
            dep_graph.add_edge(edge)
            edges_serialized.append(edge.to_dict())
            # Also set dependencies field on child packets
            children[i + 1].dependencies = [children[i].packet_id]

        self.persist_packet()

        # 6. Overnight classification
        overnight = {c.packet_id: self._classify_overnight_safety(c) for c in children}

        return {
            "batch_id": parent.packet_id,
            "idempotency_key": idempotency_key,
            "parent_packet": parent.to_safe_dict(),
            "child_packets": [c.to_safe_dict() for c in children],
            "dependency_edges": edges_serialized,
            "overnight_classification": overnight,
            "created_count": len(children),
            "already_existed": False,
            "ok": True,
        }

    @staticmethod
    def _decomposition_steps(work_type: str) -> list[tuple[str, str]]:
        """Return (step_work_type, step_label) tuples for decomposition."""
        templates: dict[str, list[tuple[str, str]]] = {
            "implementation": [
                ("research", "Research"),
                ("planning", "Plan"),
                ("implementation", "Implement"),
                ("testing", "Test"),
                ("verification", "Verify"),
            ],
            "analysis": [
                ("research", "Research"),
                ("analysis", "Analyze"),
                ("planning", "Synthesize"),
                ("verification", "Recommend"),
            ],
            "deployment": [
                ("planning", "Prepare"),
                ("verification", "Validate"),
                ("deployment", "Deploy"),
                ("verification", "Verify"),
            ],
            "content_creation": [
                ("research", "Research"),
                ("content_creation", "Draft"),
                ("audit", "Review"),
                ("deployment", "Publish"),
            ],
        }
        return templates.get(
            work_type,
            [
                ("planning", "Plan"),
                ("implementation", "Execute"),
                ("verification", "Verify"),
            ],
        )

    @staticmethod
    def _child_risk_class(step_type: str, classification: IntentClassification) -> str:
        """Derive child risk class from step type and parent classification."""
        low_risk_steps = {"research", "analysis", "audit", "verification", "monitoring"}
        if step_type in low_risk_steps:
            return "low"
        if step_type in ("testing", "configuration", "cleanup", "planning"):
            return min(classification.risk_class, "medium", key=["low", "medium", "high"].index)
        return classification.risk_class

    @staticmethod
    def _classify_overnight_safety(packet: WorkPacket) -> str:
        """Classify overnight safety: 'safe', 'approval_needed', or 'blocked'.

        Amendment 8.3: action-type-aware, not just risk_class.
        Only read-only and proof/test/report work is automatically safe.
        All mutating work requires approval or is blocked.
        """
        work_type = ""
        if packet.intent_summary and " in " in packet.intent_summary:
            work_type = packet.intent_summary.split(" in ")[0].strip()
            if work_type.startswith("batch:"):
                work_type = work_type[6:]

        safe_types = {"research", "analysis", "audit", "verification", "monitoring"}
        approval_types = {"testing", "configuration", "cleanup"}
        blocked_types = {"implementation", "deployment", "content_creation", "coordination"}

        if packet.risk_class in ("high", "critical"):
            return "blocked"

        if work_type in safe_types and packet.risk_class == "low":
            return "safe"

        if work_type in approval_types and packet.risk_class in ("low", "medium"):
            return "approval_needed"

        if work_type in blocked_types:
            return "blocked"

        # Conservative fallback
        return "approval_needed"

    def classify_intent(self, user_intent: str) -> IntentClassification:
        return self._classifier.classify(user_intent)

    def assemble_context(self, classification: IntentClassification) -> str:
        parts = [f"Domain: {classification.domain}"]
        if classification.subdomain:
            parts.append(f"Subdomain: {classification.subdomain}")
        if classification.entity:
            parts.append(f"Entity: {classification.entity}")
        if classification.company:
            parts.append(f"Company: {classification.company}")
        if classification.product:
            parts.append(f"Product: {classification.product}")
        parts.append(f"Work type: {classification.work_type}")
        parts.append(f"Risk: {classification.risk_class}")
        parts.append(f"Complexity: {classification.complexity}")
        return " | ".join(parts)

    def lookup_world_model_entities(self, classification: IntentClassification) -> list[str]:
        entities = []
        if classification.entity:
            entities.append(classification.entity)
        if classification.company:
            entities.append(classification.company)
        if classification.product:
            entities.append(classification.product)
        if classification.project:
            entities.append(classification.project)
        return entities

    def select_knowledge_models(self, classification: IntentClassification) -> list[KnowledgeModel]:
        models = self._km_registry.find_by_domain(classification.domain)
        if classification.entity:
            models.extend(self._km_registry.find_by_entity(classification.entity))
        seen = set()
        unique = []
        for m in models:
            if m.knowledge_model_id not in seen:
                seen.add(m.knowledge_model_id)
                unique.append(m)
        return unique

    def select_templates(self, classification: IntentClassification) -> list[str]:
        return []

    def select_role_contracts(self, classification: IntentClassification) -> list[RoleContract]:
        matched = []
        for rc in self._role_contracts:
            if classification.work_type in rc.owned_work_types:
                matched.append(rc)
            elif classification.domain in rc.owned_domains:
                matched.append(rc)
        return matched or self._role_contracts[:1]

    def plan_delegation_topology(
        self,
        packet: WorkPacket,
        classification: IntentClassification,
    ) -> DelegationTopology:
        topo = self._topo_planner.plan(
            risk_class=classification.risk_class,
            complexity=classification.complexity,
            work_type=classification.work_type,
            human_action_required=classification.human_action_required,
            approval_required=classification.approval_required,
            execution_possible=classification.execution_possible,
            parallel_needed=classification.parallel_workcells_needed,
            packet_id=packet.packet_id,
        )
        topo = self._topo_planner.assign_roles(
            topo,
            classification.work_type,
            classification.domain,
        )
        return topo

    def generate_workcells(
        self,
        packet: WorkPacket,
        topo: DelegationTopology,
        classification: IntentClassification,
    ) -> list[Workcell]:
        workcells = []

        primary = Workcell(
            parent_packet_id=packet.packet_id,
            title=f"Primary: {packet.title}",
            objective=packet.desired_end_state,
            scope=classification.domain,
            assigned_role_contracts=[topo.lead_role_contract],
            validation_plan=packet.validation_plan,
            risk_limit=classification.risk_class,
        )

        if topo.topology_type == "advisor_council" and topo.advisor_council:
            primary.advisor_branches = [
                AdvisorBranch(
                    perspective=f"Perspective from {role}",
                    brief=f"Analyze from {role} viewpoint: {packet.user_intent}",
                    output_contract="Analysis and recommendation",
                )
                for role in topo.advisor_council
            ]
            primary.reconvergence_target = "synthesis_of_advisor_perspectives"
            primary.status = PlanningWorkcellStatus.BRANCHED

        workcells.append(primary)

        if topo.topology_type == "parallel_workcell" and topo.supporting_role_contracts:
            verification = Workcell(
                parent_packet_id=packet.packet_id,
                parent_workcell_id=primary.workcell_id,
                title=f"Verification: {packet.title}",
                objective="Verify outputs of primary workcell",
                scope="verification",
                assigned_role_contracts=topo.supporting_role_contracts,
                validation_plan=packet.validation_plan,
                depth=1,
            )
            workcells.append(verification)
            primary.child_workcells.append(verification.workcell_id)

        return workcells

    def map_human_required_actions(self, classification: IntentClassification) -> list[str]:
        actions = []
        if classification.human_action_required:
            if classification.risk_class in ("medium", "high"):
                actions.append("Operator review and approval required")
            if classification.domain == "finance":
                actions.append("Financial review required")
            if classification.domain == "legal_risk":
                actions.append("Legal review required")
            if not actions:
                actions.append("Human action required for completion")
        return actions

    def map_approval_gates(self, classification: IntentClassification) -> list[str]:
        gates = []
        if classification.approval_required:
            gates.append("operator_approval")
        if classification.risk_class == "high":
            gates.append("risk_review")
        if classification.domain == "finance":
            gates.append("financial_approval")
        return gates

    def map_validation_plan(self, classification: IntentClassification) -> str:
        if classification.work_type == "implementation":
            return "py_compile + test_suite + type_check + code_review"
        if classification.work_type == "deployment":
            return "deployment_verification + health_check + smoke_test"
        if classification.work_type in ("research", "analysis"):
            return "source_verification + consistency_check"
        return "output_review + completeness_check"

    def map_rollback_plan(self, classification: IntentClassification) -> str:
        if classification.work_type == "implementation":
            return "git_revert + test_verification"
        if classification.work_type == "deployment":
            return "rollback_deployment + verify_previous_version"
        return "revert_changes"

    def map_propagation_plan(self, classification: IntentClassification) -> str:
        parts = []
        if classification.work_type == "implementation":
            parts.append("update_tests")
            parts.append("update_documentation")
        if classification.domain == "self_build":
            parts.append("update_world_model")
            parts.append("update_readiness_signals")
        if classification.entity:
            parts.append(f"propagate_to_{classification.entity.lower().replace(' ', '_')}")
        return " + ".join(parts) if parts else "none"

    def score_leverage(self, packet: WorkPacket, classification: IntentClassification) -> None:
        base = 0.5
        if classification.domain in ("self_build", "business", "product"):
            base += 0.2
        if classification.complexity == "strategic":
            base += 0.1
        if classification.risk_class == "low":
            base += 0.1
        packet.leverage_score = min(1.0, base)

    def score_effectiveness(self, packet: WorkPacket, classification: IntentClassification) -> None:
        base = 0.7
        if classification.execution_possible:
            base += 0.1
        if not classification.human_action_required:
            base += 0.1
        packet.effectiveness_score = min(1.0, base)

    def score_efficiency(self, packet: WorkPacket, classification: IntentClassification) -> None:
        base = 0.6
        if classification.complexity == "simple":
            base += 0.2
        elif classification.complexity == "complex":
            base += 0.1
        if classification.risk_class == "low":
            base += 0.1
        packet.efficiency_score = min(1.0, base)

    def persist_packet(self) -> None:
        persist_packets(self._packets, self._packets_path)
        if self._workcells:
            persist_workcells(self._workcells, self._workcells_path)

    def update_packet_status(
        self,
        packet_id: str,
        new_status: PacketLifecycleStatus,
        reason: str = "",
    ) -> bool:
        for pkt in self._packets:
            if pkt.packet_id == packet_id:
                allowed = _VALID_TRANSITIONS.get(pkt.status, frozenset())
                if new_status not in allowed:
                    return False
                pkt.status = new_status
                pkt.status_reason = reason
                pkt.updated_at = time.time()
                if new_status in (
                    PacketLifecycleStatus.COMPLETED,
                    PacketLifecycleStatus.FAILED,
                ):
                    self._record_outcome(pkt, new_status, reason)
                self.persist_packet()
                return True
        return False

    def _record_outcome(
        self,
        pkt: WorkPacket,
        terminal_status: PacketLifecycleStatus,
        reason: str,
    ) -> None:
        """Record an outcome observation to InstanceRealityModel on terminal transition."""
        try:
            from substrate.reality_model.instance import (
                InstanceObservation,
                InstanceRealityModel,
            )

            outcome_type = (
                "success" if terminal_status == PacketLifecycleStatus.COMPLETED else "failure"
            )
            content = (
                f"Work packet {pkt.packet_id} ({pkt.title}) "
                f"reached {terminal_status.value}: {reason or 'no reason given'}"
            )
            observation = InstanceObservation(
                content=content[:2000],
                domain=pkt.domain or "general",
                confidence=0.8 if outcome_type == "success" else 0.6,
                tags=[
                    f"outcome:{outcome_type}",
                    f"packet:{pkt.packet_id}",
                    f"work_type:{pkt.intent_summary.split(' in ')[0] if ' in ' in pkt.intent_summary else 'unknown'}",
                ],
                metadata={
                    "packet_id": pkt.packet_id,
                    "outcome_type": outcome_type,
                    "terminal_status": terminal_status.value,
                    "risk_class": pkt.risk_class,
                    "leverage_score": pkt.leverage_score,
                },
            )
            model = InstanceRealityModel(user_id="system", org_id="system")
            obs_id = model.record(observation)
            pkt.outcome_observation_id = str(obs_id)
            pkt.outcome_summary = content[:500]
            logger.debug("outcome recorded: %s -> %s", pkt.packet_id, obs_id)
        except Exception as exc:
            logger.debug("outcome recording failed: %s", exc)

    def link_packet_to_self_build_item(self, packet_id: str, work_item_id: str) -> bool:
        for pkt in self._packets:
            if pkt.packet_id == packet_id:
                pkt.linked_self_build_item_id = work_item_id
                pkt.updated_at = time.time()
                self.persist_packet()
                return True
        return False

    def link_packet_to_roadmap(self, packet_id: str, phase: str) -> bool:
        for pkt in self._packets:
            if pkt.packet_id == packet_id:
                pkt.linked_roadmap_phase = phase
                pkt.updated_at = time.time()
                self.persist_packet()
                return True
        return False

    def summarize_packet(self, packet_id: str) -> str | None:
        for pkt in self._packets:
            if pkt.packet_id == packet_id:
                return pkt.summarize()
        return None

    def get_packet(self, packet_id: str) -> WorkPacket | None:
        for pkt in self._packets:
            if pkt.packet_id == packet_id:
                return pkt
        return None

    def all_packets(self) -> list[WorkPacket]:
        return list(self._packets)

    # ── WP-3.3: Verification Pipeline ────────────────────────────────────────

    _GATE_SCRIPTS: list[str] = [
        "scripts/check_dependency_direction.py",
        "scripts/check_type_divergence.py",
        "scripts/check_instance_leak.py",
        "scripts/check_projection_leak.py",
    ]

    def run_verification(self, packet_id: str) -> list[dict[str, Any]]:
        """Run gate scripts against a completed packet and attach results."""
        pkt = self.get_packet(packet_id)
        if pkt is None:
            return [{"error": f"packet {packet_id} not found"}]
        if pkt.status != PacketLifecycleStatus.VALIDATING:
            return [{"error": f"packet must be in validating status, got {pkt.status.value}"}]

        results: list[dict[str, Any]] = []
        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        all_passed = True

        for script_rel in self._GATE_SCRIPTS:
            script_path = os.path.join(repo_root, script_rel)
            gate_name = os.path.basename(script_rel).replace(".py", "").replace("check_", "")
            result: dict[str, Any] = {
                "gate": gate_name,
                "script": script_rel,
                "passed": False,
                "exit_code": -1,
                "output": "",
            }
            if not os.path.isfile(script_path):
                result["output"] = f"gate script not found: {script_path}"
                results.append(result)
                all_passed = False
                continue
            try:
                import subprocess

                proc = gated_subprocess_run(
                    ["python3", script_path, "--all"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=repo_root,
                )
                result["exit_code"] = proc.returncode
                result["passed"] = proc.returncode == 0
                result["output"] = (proc.stdout + proc.stderr)[:1000]
                if proc.returncode != 0:
                    all_passed = False
            except subprocess.TimeoutExpired:
                result["output"] = "gate script timed out (60s)"
                all_passed = False
            except Exception as exc:
                result["output"] = str(exc)[:500]
                all_passed = False
            results.append(result)

        pkt.verification_results = results
        pkt.verification_passed = all_passed
        pkt.updated_at = time.time()
        self.persist_packet()
        return results

    # ── WP-3.4: Projection Routing ───────────────────────────────────────────

    _KNOWN_PROJECTIONS: list[str] = ["eos", "creatoros", "lyfeos"]

    def detect_target_projection(self, user_intent: str) -> str:
        """Detect if user intent targets a specific projection directory.

        Returns the projection name (e.g., 'eos') or empty string if
        the intent is projection-agnostic (substrate/general work).
        Checks longer/more-specific projections first to avoid false matches.
        """
        intent_lower = user_intent.lower()
        # Order matters: check specific projections before generic ones
        # ("lyfeos" contains "eos", "creatoros" contains "creator")
        projection_signals: list[tuple[str, list[str]]] = [
            (
                "lyfeos",
                [
                    "lyfeos",
                    "lyfe os",
                    "life operating",
                    "personal system",
                ],
            ),
            (
                "creatoros",
                [
                    "creatoros",
                    "creator ",
                    "content creation",
                    "media production",
                ],
            ),
            (
                "eos",
                [
                    "entrepreneur",
                    "entrepreneuros",
                    "eos ",
                    "venture",
                    "client pipeline",
                ],
            ),
        ]
        for proj_name, signals in projection_signals:
            for signal in signals:
                if signal in intent_lower:
                    return proj_name
        return ""

    def get_projection_root(self, projection_name: str) -> str | None:
        """Return the filesystem root for a projection, or None if unknown."""
        if projection_name not in self._KNOWN_PROJECTIONS:
            return None
        repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
        proj_root = os.path.join(repo_root, "projections", projection_name)
        if os.path.isdir(proj_root):
            return proj_root
        return None

    def _generate_title(self, intent: str, classification: IntentClassification) -> str:
        prefix = classification.work_type.replace("_", " ").title()
        entity = classification.entity or classification.company or classification.product
        if entity:
            return f"{prefix}: {entity}"
        words = intent.split()
        short = " ".join(words[:8])
        if len(words) > 8:
            short += "..."
        return f"{prefix}: {short}"

    def _generate_success_criteria(
        self,
        classification: IntentClassification,
        desired_end_state: str,
    ) -> list[str]:
        criteria = []
        if desired_end_state:
            criteria.append(f"Desired end state achieved: {desired_end_state}")
        criteria.append(f"Work type '{classification.work_type}' completed")
        if classification.work_type == "implementation":
            criteria.append("All tests pass")
            criteria.append("No regressions")
        return criteria

    def _generate_failure_criteria(self, classification: IntentClassification) -> list[str]:
        criteria = ["Desired end state not achieved"]
        if classification.work_type == "implementation":
            criteria.append("Tests fail")
            criteria.append("Regressions detected")
        if classification.risk_class in ("medium", "high"):
            criteria.append("Risk materialized without mitigation")
        return criteria

    def _assess_risk_factors(self, classification: IntentClassification) -> list[str]:
        factors = []
        if classification.risk_class == "medium":
            factors.append("Medium-risk work requires careful review")
        if classification.risk_class == "high":
            factors.append("High-risk work — execution blocked")
        if classification.human_action_required:
            factors.append("Human bottleneck in execution path")
        if classification.complexity == "strategic":
            factors.append("Strategic complexity increases coordination risk")
        return factors
