"""Universal Work Queue — canonical queue for all work packets.

Ingests work packets from any source (user intent, self-build items,
cadence candidates, roadmap requirements, audit findings), ranks them
deterministically, and provides query/management operations.

Phase 11.1. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from substrate.organism.work_packet import (
    WorkPacket, PacketLifecycleStatus, _TERMINAL_STATUSES,
    _VALID_TRANSITIONS, persist_packets, load_packets,
)
from substrate.organism.work_packet_engine import WorkPacketEngine

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class UniversalWorkQueue:
    """Canonical work queue — ingests, ranks, queries work packets."""

    RANKING_WEIGHTS = {
        "leverage": 0.20,
        "effectiveness": 0.15,
        "efficiency": 0.10,
        "urgency": 0.15,
        "risk_penalty": 0.10,
        "roadmap_relevance": 0.10,
        "priority": 0.10,
        "human_bottleneck_penalty": 0.05,
        "expected_impact": 0.05,
    }

    def __init__(
        self,
        store_path: str | None = None,
        engine: WorkPacketEngine | None = None,
    ) -> None:
        self._store_path = store_path or os.path.join(
            _REPO_ROOT, "data", "umh", "universal_work", "work_packets.jsonl",
        )
        self._engine = engine or WorkPacketEngine(packets_path=self._store_path)
        self._packets: dict[str, WorkPacket] = {}
        self._load()

    def _load(self) -> None:
        loaded = load_packets(self._store_path)
        self._packets = {p.packet_id: p for p in loaded}

    def _save(self) -> None:
        persist_packets(list(self._packets.values()), self._store_path)

    def ingest_work_packet(self, packet: WorkPacket) -> WorkPacket:
        if self._is_duplicate(packet):
            for existing in self._packets.values():
                if (existing.user_intent == packet.user_intent
                        and existing.status not in _TERMINAL_STATUSES):
                    return existing
        self._packets[packet.packet_id] = packet
        self._save()
        return packet

    def ingest_user_intent(
        self,
        user_intent: str,
        desired_end_state: str = "",
        constraints: list[str] | None = None,
    ) -> WorkPacket:
        packet = self._engine.create_packet_from_intent(
            user_intent=user_intent,
            desired_end_state=desired_end_state,
            constraints=constraints,
        )
        return self.ingest_work_packet(packet)

    def ingest_self_build_items(
        self, items: list[dict[str, Any]],
    ) -> list[WorkPacket]:
        packets = []
        for item in items:
            packet = WorkPacket(
                title=item.get("title", "Self-build item"),
                user_intent=item.get("description", ""),
                desired_end_state=item.get("validation_plan", ""),
                domain="self_build",
                source_type="self_build_item",
                source_id=item.get("work_item_id", ""),
                source_evidence=[{"type": "self_build_item", "data": item}],
                risk_class=item.get("risk_class", "low"),
                leverage_score=float(item.get("expected_leverage", 0.0)),
                linked_self_build_item_id=item.get("work_item_id", ""),
                linked_roadmap_phase=item.get("roadmap_phase", ""),
                status=PacketLifecycleStatus.CLASSIFIED,
            )
            packet = self.ingest_work_packet(packet)
            packets.append(packet)
        return packets

    def ingest_cadence_candidates(
        self, candidates: list[dict[str, Any]],
    ) -> list[WorkPacket]:
        packets = []
        for cand in candidates:
            packet = WorkPacket(
                title=cand.get("title", "Cadence candidate"),
                user_intent=cand.get("description", ""),
                domain="self_build",
                source_type="cadence_candidate",
                source_id=cand.get("candidate_id", ""),
                source_evidence=[{"type": "cadence_candidate", "data": cand}],
                risk_class=cand.get("risk_class", "low"),
                leverage_score=float(cand.get("weighted_score", 0.0)),
                status=PacketLifecycleStatus.CLASSIFIED,
            )
            packet = self.ingest_work_packet(packet)
            packets.append(packet)
        return packets

    def ingest_roadmap_requirements(
        self, requirements: list[dict[str, Any]],
    ) -> list[WorkPacket]:
        packets = []
        for req in requirements:
            packet = WorkPacket(
                title=req.get("title", "Roadmap requirement"),
                user_intent=req.get("description", ""),
                domain=req.get("domain", "self_build"),
                source_type="roadmap_requirement",
                source_id=req.get("requirement_id", ""),
                source_evidence=[{"type": "roadmap_requirement", "data": req}],
                risk_class=req.get("risk_class", "low"),
                leverage_score=float(req.get("expected_leverage", 0.0)),
                linked_roadmap_phase=req.get("roadmap_phase", ""),
                status=PacketLifecycleStatus.CLASSIFIED,
            )
            packet = self.ingest_work_packet(packet)
            packets.append(packet)
        return packets

    def ingest_audit_findings(
        self, findings: list[dict[str, Any]],
    ) -> list[WorkPacket]:
        packets = []
        for finding in findings:
            packet = WorkPacket(
                title=finding.get("title", "Audit finding"),
                user_intent=finding.get("description", ""),
                domain="self_build",
                source_type="audit_finding",
                source_id=finding.get("finding_id", ""),
                source_evidence=[{"type": "audit_finding", "data": finding}],
                risk_class=finding.get("risk_class", "low"),
                status=PacketLifecycleStatus.CLASSIFIED,
            )
            packet = self.ingest_work_packet(packet)
            packets.append(packet)
        return packets

    def rank_packets(self) -> list[WorkPacket]:
        active = [
            p for p in self._packets.values()
            if p.status not in _TERMINAL_STATUSES
        ]
        for p in active:
            p._ranking_score = self._compute_ranking_score(p)
        active.sort(key=lambda x: x._ranking_score, reverse=True)
        return active

    def _compute_ranking_score(self, p: WorkPacket) -> float:
        w = self.RANKING_WEIGHTS
        risk_penalty = {"low": 0.0, "medium": 0.5, "high": 1.0}.get(p.risk_class, 0.3)
        roadmap_relevance = 0.8 if p.linked_roadmap_phase else 0.2
        human_bottleneck = 0.5 if p.human_required_actions else 0.0
        urgency_norm = p.urgency / 100.0
        priority_norm = p.priority / 100.0

        score = (
            p.leverage_score * w["leverage"]
            + p.effectiveness_score * w["effectiveness"]
            + p.efficiency_score * w["efficiency"]
            + urgency_norm * w["urgency"]
            + (1.0 - risk_penalty) * w["risk_penalty"]
            + roadmap_relevance * w["roadmap_relevance"]
            + priority_norm * w["priority"]
            + (1.0 - human_bottleneck) * w["human_bottleneck_penalty"]
            + p.leverage_score * w["expected_impact"]
        )
        return round(score, 4)

    def get_next_best_packet(self) -> WorkPacket | None:
        ranked = self.rank_packets()
        eligible = [
            p for p in ranked
            if p.status not in _TERMINAL_STATUSES
            and p.risk_class != "medium"
            and not p.blockers
        ]
        return eligible[0] if eligible else None

    def get_packets_by_domain(self, domain: str) -> list[WorkPacket]:
        return [p for p in self._packets.values() if p.domain == domain]

    def get_packets_by_project(self, project: str) -> list[WorkPacket]:
        return [p for p in self._packets.values() if p.project == project]

    def get_packets_by_status(self, status: str) -> list[WorkPacket]:
        return [p for p in self._packets.values() if p.status.value == status]

    def get_packets_requiring_human(self) -> list[WorkPacket]:
        return [
            p for p in self._packets.values()
            if p.human_required_actions and p.status not in _TERMINAL_STATUSES
        ]

    def get_packets_requiring_approval(self) -> list[WorkPacket]:
        return [
            p for p in self._packets.values()
            if p.approval_gates and p.status not in _TERMINAL_STATUSES
        ]

    def get_blocked_packets(self) -> list[WorkPacket]:
        return [
            p for p in self._packets.values()
            if p.status == PacketLifecycleStatus.BLOCKED
        ]

    def update_packet_status(
        self, packet_id: str, new_status: PacketLifecycleStatus, reason: str = "",
    ) -> bool:
        pkt = self._packets.get(packet_id)
        if not pkt:
            return False
        allowed = _VALID_TRANSITIONS.get(pkt.status, frozenset())
        if new_status not in allowed:
            return False
        pkt.status = new_status
        pkt.status_reason = reason
        pkt.updated_at = time.time()
        self._save()
        return True

    def link_execution_artifacts(
        self, packet_id: str, artifacts: dict[str, str],
    ) -> bool:
        pkt = self._packets.get(packet_id)
        if not pkt:
            return False
        if "pr_url" in artifacts:
            pkt.linked_pr_url = artifacts["pr_url"]
        if "sandbox_id" in artifacts:
            pkt.linked_sandbox_id = artifacts["sandbox_id"]
        if "approval_packet_id" in artifacts:
            pkt.linked_approval_packet_id = artifacts["approval_packet_id"]
        pkt.updated_at = time.time()
        self._save()
        return True

    def mark_resolved(self, packet_id: str, reason: str = "") -> bool:
        return self.update_packet_status(
            packet_id, PacketLifecycleStatus.COMPLETED, reason,
        )

    def suppress_duplicates(self) -> int:
        seen_intents: dict[str, str] = {}
        suppressed = 0
        for pkt in list(self._packets.values()):
            if pkt.status in _TERMINAL_STATUSES:
                continue
            key = pkt.user_intent.strip().lower()
            if not key:
                continue
            if key in seen_intents:
                pkt.status = PacketLifecycleStatus.SUPERSEDED
                pkt.status_reason = f"Duplicate of {seen_intents[key]}"
                suppressed += 1
            else:
                seen_intents[key] = pkt.packet_id
        if suppressed > 0:
            self._save()
        return suppressed

    def compute_queue_summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        domain_counts: dict[str, int] = {}
        for pkt in self._packets.values():
            status_counts[pkt.status.value] = status_counts.get(pkt.status.value, 0) + 1
            if pkt.status not in _TERMINAL_STATUSES:
                domain_counts[pkt.domain] = domain_counts.get(pkt.domain, 0) + 1

        human_required = len(self.get_packets_requiring_human())
        approval_required = len(self.get_packets_requiring_approval())
        blocked = len(self.get_blocked_packets())
        active = len([
            p for p in self._packets.values()
            if p.status not in _TERMINAL_STATUSES
        ])
        completed = len([
            p for p in self._packets.values()
            if p.status == PacketLifecycleStatus.COMPLETED
        ])

        next_best = self.get_next_best_packet()

        return {
            "total_packets": len(self._packets),
            "by_status": status_counts,
            "by_domain": domain_counts,
            "human_required": human_required,
            "approval_required": approval_required,
            "blocked": blocked,
            "active": active,
            "completed": completed,
            "next_best": next_best.to_safe_dict() if next_best else None,
        }

    def get_packet(self, packet_id: str) -> WorkPacket | None:
        return self._packets.get(packet_id)

    def all_packets(self) -> list[WorkPacket]:
        return list(self._packets.values())

    def _is_duplicate(self, packet: WorkPacket) -> bool:
        for existing in self._packets.values():
            if existing.status in _TERMINAL_STATUSES:
                continue
            if (existing.source_id and existing.source_id == packet.source_id
                    and existing.source_type == packet.source_type):
                return True
            if (existing.user_intent and packet.user_intent
                    and existing.user_intent.strip().lower() == packet.user_intent.strip().lower()):
                return True
        return False
