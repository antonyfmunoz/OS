"""Cross-Source Reconciler — detect relationships across fragmented sources.

Compares signals from emails, files, apps, docs, repos, and artifacts to
infer possible relationships: app subscriptions, duplicate documents,
stale tools, workflow connections. Every cross-source inference requires
operator confirmation before canonization.

Phase 13.3. UMH substrate subsystem. Instance-agnostic.
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

from substrate.organism.permission_dialogue import (
    SocraticPermissionEngine,
    Sensitivity,
    ApprovalOption,
    RequestStatus,
)
from substrate.organism.canonical_update import (
    CanonicalUpdateProposal,
    ProposalType,
    ProposalStatus,
    ProposalStore,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_SIGNALS_PATH = os.path.join(
    _REPO_ROOT, "data", "umh", "context_assimilation", "cross_source_signals.jsonl"
)


class SignalType(str, Enum):
    APP_SUBSCRIPTION_DETECTED = "app_subscription_detected"
    APP_USAGE_DETECTED = "app_usage_detected"
    DUPLICATE_DOCUMENT_DETECTED = "duplicate_document_detected"
    STALE_DOCUMENT_DETECTED = "stale_document_detected"
    ACCOUNT_OVERLAP_DETECTED = "account_overlap_detected"
    PROJECT_TOOL_RELATIONSHIP = "project_tool_relationship"
    COMPANY_TOOL_RELATIONSHIP = "company_tool_relationship"
    WORKFLOW_TOOL_RELATIONSHIP = "workflow_tool_relationship"
    PAID_BUT_UNUSED_TOOL = "paid_but_unused_tool"
    USED_BUT_NOT_CANONICAL_TOOL = "used_but_not_canonical_tool"
    EXTERNAL_SOURCE_CONFLICT = "external_source_conflict"
    MISSING_TOOL_CONTEXT = "missing_tool_context"


class SignalStatus(str, Enum):
    DETECTED = "detected"
    PERMISSION_REQUIRED = "permission_required"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANONIZED = "canonized"
    DEFERRED = "deferred"


@dataclass
class CrossSourceSignal:
    signal_id: str = ""
    signal_type: str = SignalType.APP_USAGE_DETECTED.value
    source_ids: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    inferred_relationship: str = ""
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    sensitivity: str = Sensitivity.INTERNAL.value
    requires_permission: bool = True
    requires_operator_confirmation: bool = True
    permission_request_id: str = ""
    status: str = SignalStatus.DETECTED.value
    created_at: float = 0.0

    def __post_init__(self) -> None:
        if not self.signal_id:
            self.signal_id = f"xsig-{uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "source_ids": self.source_ids,
            "entities": self.entities,
            "inferred_relationship": self.inferred_relationship,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "sensitivity": self.sensitivity,
            "requires_permission": self.requires_permission,
            "requires_operator_confirmation": self.requires_operator_confirmation,
            "permission_request_id": self.permission_request_id,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CrossSourceSignal:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CrossSourceReconciler:
    def __init__(
        self,
        permission_engine: SocraticPermissionEngine | None = None,
        proposal_store: ProposalStore | None = None,
        signals_path: str | None = None,
    ) -> None:
        self._permissions = permission_engine or SocraticPermissionEngine()
        self._proposals = proposal_store or ProposalStore()
        self._signals_path = signals_path or _SIGNALS_PATH
        self._signals: dict[str, CrossSourceSignal] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._signals_path):
            return
        with open(self._signals_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    sig = CrossSourceSignal.from_dict(d)
                    self._signals[sig.signal_id] = sig
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Skipping malformed cross-source signal line")

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._signals_path), exist_ok=True)
        with open(self._signals_path, "w") as f:
            for sig in self._signals.values():
                f.write(json.dumps(sig.to_dict(), default=str) + "\n")

    def detect_signal(
        self,
        signal_type: str,
        source_ids: list[str],
        entities: list[str],
        inferred_relationship: str,
        evidence: list[str],
        sensitivity: str = Sensitivity.INTERNAL.value,
        confidence: float = 0.5,
    ) -> CrossSourceSignal:
        requires_permission = sensitivity in (
            Sensitivity.FINANCIAL.value,
            Sensitivity.PERSONAL.value,
            Sensitivity.SENSITIVE.value,
        )
        signal = CrossSourceSignal(
            signal_type=signal_type,
            source_ids=source_ids,
            entities=entities,
            inferred_relationship=inferred_relationship,
            evidence=evidence,
            sensitivity=sensitivity,
            confidence=confidence,
            requires_permission=requires_permission,
            requires_operator_confirmation=True,
            status=SignalStatus.PERMISSION_REQUIRED.value if requires_permission else SignalStatus.DETECTED.value,
        )
        self._signals[signal.signal_id] = signal
        self._save()
        return signal

    def request_permission_for_signal(self, signal_id: str) -> dict[str, Any] | None:
        signal = self._signals.get(signal_id)
        if not signal:
            return None
        req = self._permissions.create_request(
            requested_action=f"cross_source_link:{signal.signal_type}",
            reason=f"Detected possible relationship: {signal.inferred_relationship}",
            source_type="cross_source",
            source_id=signal_id,
            data_requested=f"Cross-referencing {len(signal.source_ids)} sources for entities: {', '.join(signal.entities[:5])}",
            sensitivity=signal.sensitivity,
            what_umh_will_do=f"Compare signals across sources to verify: {signal.inferred_relationship}",
            what_umh_will_not_do="Will not auto-canonize. Will not share externally. Will not modify any source.",
            possible_inferences=[signal.inferred_relationship],
        )
        signal.permission_request_id = req.request_id
        self._save()
        return req.to_dialogue()

    def confirm_signal(self, signal_id: str) -> bool:
        signal = self._signals.get(signal_id)
        if not signal:
            return False
        if signal.requires_permission and signal.permission_request_id:
            if not self._permissions.is_permitted(signal.permission_request_id):
                return False
        signal.status = SignalStatus.CONFIRMED.value
        self._save()
        return True

    def reject_signal(self, signal_id: str) -> bool:
        signal = self._signals.get(signal_id)
        if not signal:
            return False
        signal.status = SignalStatus.REJECTED.value
        self._save()
        return True

    def canonize_signal(self, signal_id: str) -> CanonicalUpdateProposal | None:
        signal = self._signals.get(signal_id)
        if not signal:
            return None
        if signal.status != SignalStatus.CONFIRMED.value:
            return None
        prop = CanonicalUpdateProposal(
            proposal_type=ProposalType.PROMOTE_CLAIM.value,
            title=f"Canonize cross-source finding: {signal.inferred_relationship[:60]}",
            description=signal.inferred_relationship,
            current_state="unverified cross-source signal",
            proposed_state="canonical relationship",
            source_ids=signal.source_ids,
            evidence=signal.evidence,
            confidence=signal.confidence,
            risk_class="low",
            affected_entities=signal.entities,
            status=ProposalStatus.PENDING_OPERATOR_REVIEW.value,
        )
        self._proposals.save_proposal(prop)
        signal.status = SignalStatus.CANONIZED.value
        self._save()
        return prop

    def detect_subscription_signal(
        self,
        app_name: str,
        source_ids: list[str],
        evidence: list[str],
    ) -> CrossSourceSignal:
        return self.detect_signal(
            signal_type=SignalType.APP_SUBSCRIPTION_DETECTED.value,
            source_ids=source_ids,
            entities=[app_name],
            inferred_relationship=f"{app_name} may be an active paid subscription",
            evidence=evidence,
            sensitivity=Sensitivity.FINANCIAL.value,
            confidence=0.6,
        )

    def detect_tool_project_relationship(
        self,
        tool_name: str,
        project_name: str,
        source_ids: list[str],
        evidence: list[str],
    ) -> CrossSourceSignal:
        return self.detect_signal(
            signal_type=SignalType.PROJECT_TOOL_RELATIONSHIP.value,
            source_ids=source_ids,
            entities=[tool_name, project_name],
            inferred_relationship=f"{tool_name} may be used for {project_name}",
            evidence=evidence,
            sensitivity=Sensitivity.INTERNAL.value,
            confidence=0.5,
        )

    def detect_unused_subscription(
        self,
        app_name: str,
        source_ids: list[str],
        evidence: list[str],
    ) -> CrossSourceSignal:
        return self.detect_signal(
            signal_type=SignalType.PAID_BUT_UNUSED_TOOL.value,
            source_ids=source_ids,
            entities=[app_name],
            inferred_relationship=f"{app_name} appears to be paid but not actively used",
            evidence=evidence,
            sensitivity=Sensitivity.FINANCIAL.value,
            confidence=0.4,
        )

    def get_signal(self, signal_id: str) -> CrossSourceSignal | None:
        return self._signals.get(signal_id)

    def list_signals(
        self, signal_type: str | None = None, status: str | None = None
    ) -> list[CrossSourceSignal]:
        result = list(self._signals.values())
        if signal_type:
            result = [s for s in result if s.signal_type == signal_type]
        if status:
            result = [s for s in result if s.status == status]
        return result

    def list_actionable(self) -> list[CrossSourceSignal]:
        return [
            s for s in self._signals.values()
            if s.status in (SignalStatus.DETECTED.value, SignalStatus.PERMISSION_GRANTED.value)
        ]

    def generate_cleanup_candidates(self) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for sig in self._signals.values():
            if sig.signal_type == SignalType.PAID_BUT_UNUSED_TOOL.value:
                candidates.append({
                    "signal_id": sig.signal_id,
                    "app": sig.entities[0] if sig.entities else "unknown",
                    "type": "subscription_cleanup",
                    "confidence": sig.confidence,
                    "evidence": sig.evidence,
                    "status": sig.status,
                })
            elif sig.signal_type == SignalType.STALE_DOCUMENT_DETECTED.value:
                candidates.append({
                    "signal_id": sig.signal_id,
                    "entity": sig.entities[0] if sig.entities else "unknown",
                    "type": "stale_document_cleanup",
                    "confidence": sig.confidence,
                    "evidence": sig.evidence,
                    "status": sig.status,
                })
        return candidates

    def count(self) -> int:
        return len(self._signals)

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for s in self._signals.values():
            by_type[s.signal_type] = by_type.get(s.signal_type, 0) + 1
            by_status[s.status] = by_status.get(s.status, 0) + 1
        return {
            "total": len(self._signals),
            "by_type": by_type,
            "by_status": by_status,
            "actionable": len(self.list_actionable()),
        }
