"""Reconciliation Engine — structured context reconciliation sessions.

Orchestrates the full reconciliation lifecycle: start session, attach
sources, run diagnostics, generate proposals, record operator decisions,
preview propagation, and generate work packet updates.

Phase 13.3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from substrate.organism.source_registry import SourceRegistry
from substrate.organism.ingestion_job import IngestionJobStore
from substrate.organism.context_diagnostic import DiagnosticReportStore
from substrate.organism.canonical_update import (
    CanonicalUpdateProposal,
    ProposalType,
    ProposalStatus,
    ProposalStore,
)
from substrate.organism.reconciliation_session import (
    ReconciliationSession,
    ReconciliationDecision,
    ReconciliationSessionStore,
    ReconciliationMode,
    SessionStatus,
)
from substrate.organism.diagnostic_engine import DiagnosticEngine
from substrate.organism.context_ingestion_engine import ContextIngestionEngine

logger = logging.getLogger(__name__)


class ReconciliationEngine:
    def __init__(
        self,
        registry: SourceRegistry | None = None,
        job_store: IngestionJobStore | None = None,
        report_store: DiagnosticReportStore | None = None,
        proposal_store: ProposalStore | None = None,
        session_store: ReconciliationSessionStore | None = None,
        ingestion_engine: ContextIngestionEngine | None = None,
        diagnostic_engine: DiagnosticEngine | None = None,
    ) -> None:
        self._registry = registry or SourceRegistry()
        self._job_store = job_store or IngestionJobStore()
        self._report_store = report_store or DiagnosticReportStore()
        self._proposal_store = proposal_store or ProposalStore()
        self._session_store = session_store or ReconciliationSessionStore()
        self._ingestion = ingestion_engine or ContextIngestionEngine(self._registry, self._job_store)
        self._diagnostic = diagnostic_engine or DiagnosticEngine(
            self._registry, self._job_store, self._report_store, self._proposal_store
        )

    def start_session(
        self,
        topic: str,
        scope: str = "full",
        mode: str = ReconciliationMode.EXPLORATION.value,
        operator_session_id: str = "",
    ) -> ReconciliationSession:
        session = ReconciliationSession(
            topic=topic,
            scope=scope,
            mode=mode,
            operator_session_id=operator_session_id,
            status=SessionStatus.ACTIVE.value,
        )
        self._session_store.create_session(session)
        return session

    def attach_sources(self, session_id: str, source_ids: list[str] | None = None) -> bool:
        session = self._session_store.get_session(session_id)
        if not session:
            return False
        if source_ids:
            session.source_ids = source_ids
        else:
            sources = self._registry.list_sources()
            session.source_ids = [s.source_id for s in sources]
        self._session_store.update_session(session)
        return True

    def run_diagnostic(self, session_id: str) -> dict[str, Any] | None:
        session = self._session_store.get_session(session_id)
        if not session:
            return None
        report = self._diagnostic.build_diagnostic_report(scope=session.scope)
        session.diagnostic_report_id = report.report_id
        self._session_store.update_session(session)
        return report.to_dict()

    def generate_operator_questions(self, session_id: str) -> list[str]:
        session = self._session_store.get_session(session_id)
        if not session or not session.diagnostic_report_id:
            return []
        report = self._report_store.get_report(session.diagnostic_report_id)
        if not report:
            return []
        questions = list(report.recommended_operator_questions)
        if report.missing_context:
            for mc in report.missing_context[:3]:
                questions.append(f"Can you provide context for: {mc}")
        session.operator_questions = questions
        session.status = SessionStatus.WAITING_FOR_OPERATOR.value
        self._session_store.update_session(session)
        return questions

    def generate_canonical_update_proposals(self, session_id: str) -> list[dict[str, Any]]:
        session = self._session_store.get_session(session_id)
        if not session or not session.diagnostic_report_id:
            return []
        report = self._report_store.get_report(session.diagnostic_report_id)
        if not report:
            return []
        proposals = self._proposal_store.list_proposals(report_id=report.report_id)
        if not proposals:
            for update_id in report.recommended_canonical_updates:
                prop = self._proposal_store.get_proposal(update_id)
                if prop:
                    prop.status = ProposalStatus.PENDING_OPERATOR_REVIEW.value
                    self._proposal_store.save_proposal(prop)
                    proposals.append(prop)
        session.proposals = [p.proposal_id for p in proposals]
        session.status = SessionStatus.PROPOSALS_READY.value
        self._session_store.update_session(session)
        return [p.to_dict() for p in proposals]

    def accept_operator_decision(
        self,
        session_id: str,
        question: str,
        answer: str,
        decision_type: str = "operator_answer",
    ) -> ReconciliationDecision | None:
        session = self._session_store.get_session(session_id)
        if not session:
            return None
        decision = ReconciliationDecision(
            session_id=session_id,
            question=question,
            operator_answer=answer,
            decision_type=decision_type,
        )
        self._session_store.add_decision(decision)
        return decision

    def approve_proposal(self, session_id: str, proposal_id: str, decision: str = "approved") -> bool:
        session = self._session_store.get_session(session_id)
        if not session:
            return False
        if not self._proposal_store.approve(proposal_id, decision):
            return False
        if proposal_id not in session.approved_updates:
            session.approved_updates.append(proposal_id)
        self._session_store.update_session(session)
        return True

    def reject_proposal(self, session_id: str, proposal_id: str, decision: str = "rejected") -> bool:
        session = self._session_store.get_session(session_id)
        if not session:
            return False
        if not self._proposal_store.reject(proposal_id, decision):
            return False
        if proposal_id not in session.rejected_updates:
            session.rejected_updates.append(proposal_id)
        self._session_store.update_session(session)
        return True

    def preview_propagation(self, session_id: str) -> dict[str, Any]:
        session = self._session_store.get_session(session_id)
        if not session:
            return {"error": "session_not_found"}
        approved = []
        for pid in session.approved_updates:
            prop = self._proposal_store.get_proposal(pid)
            if prop:
                approved.append(prop.to_dict())
        preview = {
            "session_id": session_id,
            "approved_proposals": len(approved),
            "affected_entities": [],
            "affected_work_packets": [],
            "affected_knowledge_models": [],
            "dry_run": True,
        }
        entity_set: set[str] = set()
        wp_set: set[str] = set()
        km_set: set[str] = set()
        for prop_dict in approved:
            entity_set.update(prop_dict.get("affected_entities", []))
            wp_set.update(prop_dict.get("affected_work_packets", []))
            km_set.update(prop_dict.get("affected_knowledge_models", []))
        preview["affected_entities"] = sorted(entity_set)
        preview["affected_work_packets"] = sorted(wp_set)
        preview["affected_knowledge_models"] = sorted(km_set)
        session.propagation_previews.append(f"preview-{uuid4().hex[:8]}")
        self._session_store.update_session(session)
        return preview

    def generate_work_packet_updates(self, session_id: str) -> list[dict[str, Any]]:
        session = self._session_store.get_session(session_id)
        if not session:
            return []
        updates: list[dict[str, Any]] = []
        for pid in session.approved_updates:
            prop = self._proposal_store.get_proposal(pid)
            if not prop:
                continue
            if prop.proposal_type in (
                ProposalType.CREATE_WORK_PACKET.value,
                ProposalType.UPDATE_WORK_PACKET.value,
            ):
                updates.append({
                    "proposal_id": prop.proposal_id,
                    "type": prop.proposal_type,
                    "title": prop.title,
                    "description": prop.description,
                    "risk_class": prop.risk_class,
                    "dry_run": True,
                })
        session.generated_work_packets = [u["proposal_id"] for u in updates]
        self._session_store.update_session(session)
        return updates

    def generate_session_summary(self, session_id: str) -> str:
        session = self._session_store.get_session(session_id)
        if not session:
            return ""
        decisions = self._session_store.get_decisions_for_session(session_id)
        parts = [
            f"Reconciliation Session: {session.topic}",
            f"Scope: {session.scope}",
            f"Mode: {session.mode}",
            f"Sources analyzed: {len(session.source_ids)}",
            f"Proposals generated: {len(session.proposals)}",
            f"Approved: {len(session.approved_updates)}",
            f"Rejected: {len(session.rejected_updates)}",
            f"Decisions recorded: {len(decisions)}",
            f"Work packets generated: {len(session.generated_work_packets)}",
        ]
        return "\n".join(parts)

    def complete_session(self, session_id: str) -> bool:
        summary = self.generate_session_summary(session_id)
        return self._session_store.complete_session(session_id, summary)

    def is_exploration_mode(self, session_id: str) -> bool:
        session = self._session_store.get_session(session_id)
        if not session:
            return False
        return session.mode == ReconciliationMode.EXPLORATION.value

    def set_mode(self, session_id: str, mode: str) -> bool:
        session = self._session_store.get_session(session_id)
        if not session:
            return False
        session.mode = mode
        self._session_store.update_session(session)
        return True
