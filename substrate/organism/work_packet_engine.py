"""Work Packet Engine — creates work packets from user intent.

Orchestrates intent classification, context assembly, delegation topology
planning, workcell generation, scoring, and persistence. The engine is
the primary entry point for converting high-level intent into structured,
governed work.

Phase 11.1. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from substrate.organism.intent_classifier import IntentClassifier, IntentClassification
from substrate.organism.delegation_topology import DelegationTopologyPlanner, DelegationTopology
from substrate.organism.work_packet import (
    WorkPacket, PacketLifecycleStatus, persist_packets, load_packets,
    _VALID_TRANSITIONS,
)
from substrate.organism.workcell import (
    Workcell, AdvisorBranch, PlanningWorkcellStatus, persist_workcells,
)
from substrate.organism.role_contracts import (
    RoleContract, load_role_contracts, SEED_ROLE_CONTRACTS,
)
from substrate.organism.knowledge_model_registry import (
    KnowledgeModelRegistry, KnowledgeModel,
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
        self._packets_path = packets_path or os.path.join(
            _REPO_ROOT, "data", "umh", "universal_work", "work_packets.jsonl",
        )
        self._workcells_path = workcells_path or os.path.join(
            _REPO_ROOT, "data", "umh", "universal_work", "workcells.jsonl",
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

        packet.status = PacketLifecycleStatus.CLASSIFIED
        packet.updated_at = time.time()

        self._packets.append(packet)
        self._workcells.extend(workcells)
        self.persist_packet()

        return packet

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
            topo, classification.work_type, classification.domain,
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
                objective=f"Verify outputs of primary workcell",
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
                self.persist_packet()
                return True
        return False

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
