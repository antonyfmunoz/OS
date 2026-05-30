"""Operator Approval Gate — requires explicit approval before sandbox execution.

Cadence proposes. Operator approves. Sandbox executes.

An ApprovalPacket bundles all context an operator needs to make an
informed approve/reject decision: candidate evidence, matched template,
governance score, affected files, expected delta, validation plan,
rollback plan, risk classification, and safety justification.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalPacket:
    packet_id: str = field(default_factory=lambda: f"apk-{uuid4().hex[:8]}")
    candidate_id: str = ""
    candidate_source: str = ""
    candidate_title: str = ""
    candidate_description: str = ""
    candidate_evidence: list[dict[str, Any]] = field(default_factory=list)
    matched_template_id: str = ""
    matched_template_type: str = ""
    template_confidence: float = 0.0
    governance_score: float = 0.0
    governance_decision: str = ""
    governance_dimensions: list[dict[str, Any]] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    expected_delta: str = ""
    validation_plan: str = ""
    rollback_plan: str = ""
    sandbox_branch_name: str = ""
    risk_class: str = "low"
    why_safe: str = ""
    what_will_not_happen: list[str] = field(default_factory=list)
    status: ApprovalStatus = ApprovalStatus.PENDING
    decided_by: str = ""
    decided_at: float = 0.0
    rejection_reason: str = ""
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "candidate_id": self.candidate_id,
            "candidate_source": self.candidate_source,
            "candidate_title": self.candidate_title,
            "candidate_description": self.candidate_description,
            "candidate_evidence": self.candidate_evidence,
            "matched_template_id": self.matched_template_id,
            "matched_template_type": self.matched_template_type,
            "template_confidence": round(self.template_confidence, 3),
            "governance_score": round(self.governance_score, 3),
            "governance_decision": self.governance_decision,
            "governance_dimensions": self.governance_dimensions,
            "affected_files": self.affected_files,
            "expected_delta": self.expected_delta,
            "validation_plan": self.validation_plan,
            "rollback_plan": self.rollback_plan,
            "sandbox_branch_name": self.sandbox_branch_name,
            "risk_class": self.risk_class,
            "why_safe": self.why_safe,
            "what_will_not_happen": self.what_will_not_happen,
            "status": self.status.value,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


class OperatorApprovalGate:
    """Gate that holds candidates until operator explicitly approves."""

    def __init__(self, store_dir: str | None = None, ttl_seconds: float = 86400.0) -> None:
        self._store_dir = store_dir or os.path.join(_REPO_ROOT, "data", "umh", "autonomous_lane")
        self._packets_path = os.path.join(self._store_dir, "approval_packets.jsonl")
        self._ttl_seconds = ttl_seconds
        self._packets: dict[str, ApprovalPacket] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self._packets_path):
            return
        try:
            with open(self._packets_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    pkt = ApprovalPacket(**{
                        k: v for k, v in data.items()
                        if k in ApprovalPacket.__dataclass_fields__
                    })
                    if isinstance(pkt.status, str):
                        pkt.status = ApprovalStatus(pkt.status)
                    self._packets[pkt.packet_id] = pkt
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load approval packets: %s", e)

    def _persist(self, packet: ApprovalPacket) -> None:
        os.makedirs(os.path.dirname(self._packets_path), exist_ok=True)
        with open(self._packets_path, "a") as f:
            f.write(json.dumps(packet.to_dict(), default=str) + "\n")

    def create_packet(
        self,
        candidate_id: str,
        candidate_source: str,
        candidate_title: str,
        candidate_description: str,
        candidate_evidence: list[dict[str, Any]],
        matched_template_id: str,
        matched_template_type: str,
        template_confidence: float,
        governance_score: float,
        governance_decision: str,
        governance_dimensions: list[dict[str, Any]],
        affected_files: list[str],
        expected_delta: str,
        validation_plan: str,
        rollback_plan: str,
        risk_class: str = "low",
    ) -> ApprovalPacket:
        slug = candidate_title.lower().replace(" ", "-")[:30]
        short_id = uuid4().hex[:6]
        branch_name = f"auto/low-risk/{slug}-{short_id}"

        what_will_not_happen = [
            "No production truth mutation until merge + post-merge verification",
            "No auto-merge — operator must merge PR manually",
            "No HIGH/CRITICAL actions — only LOW risk operations",
            "No credential, DNS, or auth changes",
            "No destructive cleanup or broad refactors",
            "No direct mutation on main branch",
        ]

        why_safe = (
            f"LOW risk candidate ({risk_class}) with governance score {governance_score:.2f}. "
            f"Template {matched_template_id} (confidence {template_confidence:.2f}) provides "
            f"validated execution pattern. Sandbox isolation prevents production mutation. "
            f"Validation: {validation_plan}. Rollback: {rollback_plan}."
        )

        packet = ApprovalPacket(
            candidate_id=candidate_id,
            candidate_source=candidate_source,
            candidate_title=candidate_title,
            candidate_description=candidate_description,
            candidate_evidence=candidate_evidence,
            matched_template_id=matched_template_id,
            matched_template_type=matched_template_type,
            template_confidence=template_confidence,
            governance_score=governance_score,
            governance_decision=governance_decision,
            governance_dimensions=governance_dimensions,
            affected_files=affected_files,
            expected_delta=expected_delta,
            validation_plan=validation_plan,
            rollback_plan=rollback_plan,
            sandbox_branch_name=branch_name,
            risk_class=risk_class,
            why_safe=why_safe,
            what_will_not_happen=what_will_not_happen,
            expires_at=time.time() + self._ttl_seconds,
        )

        self._packets[packet.packet_id] = packet
        self._persist(packet)
        logger.info("Created approval packet %s for candidate %s", packet.packet_id, candidate_id)
        return packet

    def approve(self, packet_id: str, decided_by: str = "operator") -> ApprovalPacket | None:
        packet = self._packets.get(packet_id)
        if not packet:
            return None
        if packet.status != ApprovalStatus.PENDING:
            return None
        if self._is_expired(packet):
            packet.status = ApprovalStatus.EXPIRED
            return None

        packet.status = ApprovalStatus.APPROVED
        packet.decided_by = decided_by
        packet.decided_at = time.time()
        self._persist(packet)
        logger.info("Operator approved packet %s", packet_id)
        return packet

    def reject(self, packet_id: str, reason: str = "", decided_by: str = "operator") -> ApprovalPacket | None:
        packet = self._packets.get(packet_id)
        if not packet:
            return None
        if packet.status != ApprovalStatus.PENDING:
            return None

        packet.status = ApprovalStatus.REJECTED
        packet.decided_by = decided_by
        packet.decided_at = time.time()
        packet.rejection_reason = reason
        self._persist(packet)
        logger.info("Operator rejected packet %s: %s", packet_id, reason)
        return packet

    def get_packet(self, packet_id: str) -> ApprovalPacket | None:
        return self._packets.get(packet_id)

    def is_approved(self, packet_id: str) -> bool:
        packet = self._packets.get(packet_id)
        if not packet:
            return False
        if self._is_expired(packet):
            packet.status = ApprovalStatus.EXPIRED
            return False
        return packet.status == ApprovalStatus.APPROVED

    def pending_packets(self) -> list[ApprovalPacket]:
        self._expire_stale()
        return [p for p in self._packets.values() if p.status == ApprovalStatus.PENDING]

    def all_packets(self) -> list[ApprovalPacket]:
        self._expire_stale()
        return list(self._packets.values())

    def _is_expired(self, packet: ApprovalPacket) -> bool:
        if packet.expires_at <= 0:
            return False
        return time.time() > packet.expires_at

    def _expire_stale(self) -> None:
        for packet in self._packets.values():
            if packet.status == ApprovalStatus.PENDING and self._is_expired(packet):
                packet.status = ApprovalStatus.EXPIRED

    def summary(self) -> dict[str, Any]:
        self._expire_stale()
        by_status: dict[str, int] = {}
        for p in self._packets.values():
            by_status[p.status.value] = by_status.get(p.status.value, 0) + 1
        return {
            "total_packets": len(self._packets),
            "by_status": by_status,
            "pending_count": by_status.get("pending", 0),
        }

    def to_dict(self) -> dict[str, Any]:
        self._expire_stale()
        return {
            "summary": self.summary(),
            "packets": [p.to_dict() for p in self._packets.values()],
        }
