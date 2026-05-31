"""Operator Reconciliation Integration — detects reconciliation intent in operator input.

Classifies operator messages as exploration, reconciliation, decision, or
execution planning. Routes reconciliation-related input through the
ReconciliationEngine. Preserves the boundary between exploration (no
canon changes) and decision (approval required).

Phase 13.3. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any
from uuid import uuid4

from substrate.organism.reconciliation_engine import ReconciliationEngine
from substrate.organism.reconciliation_session import ReconciliationMode, SessionStatus
from substrate.organism.source_registry import SourceRegistry
from substrate.organism.ingestion_job import IngestionJobStore
from substrate.organism.context_diagnostic import DiagnosticReportStore
from substrate.organism.canonical_update import ProposalStore
from substrate.organism.reconciliation_session import ReconciliationSessionStore

logger = logging.getLogger(__name__)


class ReconciliationIntent:
    EXPLORATION = "exploration"
    RECONCILIATION = "reconciliation"
    DECISION = "decision"
    QUERY = "query"
    NONE = "none"


_EXPLORATION_PATTERNS = [
    re.compile(r"\bjust\s+thinking\b", re.IGNORECASE),
    re.compile(r"\bmaybe\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+if\b", re.IGNORECASE),
    re.compile(r"\bjust\s+exploring\b", re.IGNORECASE),
    re.compile(r"\bdon'?t\s+remember\s+(?:this\s+)?yet\b", re.IGNORECASE),
    re.compile(r"\bi'?m\s+(?:just\s+)?brainstorming\b", re.IGNORECASE),
    re.compile(r"\bhypothetically\b", re.IGNORECASE),
]

_RECONCILIATION_PATTERNS = [
    re.compile(r"\bactually\b.*\b(?:handles?|includes?|also)\b", re.IGNORECASE),
    re.compile(r"\bchanged\s+my\s+mind\b", re.IGNORECASE),
    re.compile(r"\blet'?s\s+reconcile\b", re.IGNORECASE),
    re.compile(r"\bthis\s+(?:doc|document)\s+is\s+outdated\b", re.IGNORECASE),
    re.compile(r"\b(?:is|are)\s+(?:no longer|not)\s+(?:correct|accurate|true)\b", re.IGNORECASE),
    re.compile(r"\bupdate\s+(?:the|your)\s+understanding\b", re.IGNORECASE),
    re.compile(r"\bi\s+(?:want|need)\s+(?:to\s+)?(?:correct|fix|update)\b", re.IGNORECASE),
    re.compile(r"\bis\s+outdated\b", re.IGNORECASE),
    re.compile(r"\bis\s+(?:no\s+longer|not)\s+(?:valid|true|correct|current)\b", re.IGNORECASE),
]

_DECISION_PATTERNS = [
    re.compile(r"\bcanonize\b", re.IGNORECASE),
    re.compile(r"\bmake\s+(?:this|that)\s+canonical\b", re.IGNORECASE),
    re.compile(r"\bremember\s+(?:this|that)\b", re.IGNORECASE),
    re.compile(r"\bthis\s+is\s+(?:the\s+)?truth\b", re.IGNORECASE),
    re.compile(r"\bmark\s+(?:as\s+)?(?:canonical|official|truth)\b", re.IGNORECASE),
    re.compile(r"\bapprove\b", re.IGNORECASE),
    re.compile(r"\bconfirm\b.*\bcanonical\b", re.IGNORECASE),
]

_QUERY_PATTERNS = [
    re.compile(r"\bwhat\s+do\s+you\s+(?:understand|know)\b", re.IGNORECASE),
    re.compile(r"\bwhat'?s\s+(?:your|the)\s+(?:current|latest)\b", re.IGNORECASE),
    re.compile(r"\bshow\s+(?:me\s+)?(?:your|the)\s+understanding\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+(?:is|are)\s+(?:canonical|current)\b", re.IGNORECASE),
    re.compile(r"\bhow\s+do\s+you\s+see\b", re.IGNORECASE),
]


def classify_reconciliation_intent(text: str) -> str:
    for pattern in _EXPLORATION_PATTERNS:
        if pattern.search(text):
            return ReconciliationIntent.EXPLORATION
    for pattern in _DECISION_PATTERNS:
        if pattern.search(text):
            return ReconciliationIntent.DECISION
    for pattern in _RECONCILIATION_PATTERNS:
        if pattern.search(text):
            return ReconciliationIntent.RECONCILIATION
    for pattern in _QUERY_PATTERNS:
        if pattern.search(text):
            return ReconciliationIntent.QUERY
    return ReconciliationIntent.NONE


def extract_topic(text: str) -> str:
    text = text.strip()
    for prefix in ("actually ", "canonize ", "reconcile ", "remember "):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
    text = re.sub(r"^(that|this|the)\s+", "", text, flags=re.IGNORECASE)
    return text[:120].strip()


class DexReconciliation:
    def __init__(
        self,
        reconciliation_engine: ReconciliationEngine | None = None,
        **kwargs: Any,
    ) -> None:
        self._engine = reconciliation_engine or ReconciliationEngine(**kwargs)
        self._active_session_id: str = ""

    def process_operator_input(self, text: str, operator_session_id: str = "") -> dict[str, Any]:
        intent = classify_reconciliation_intent(text)
        if intent == ReconciliationIntent.NONE:
            return {"intent": intent, "action": "none", "message": "No reconciliation intent detected"}

        topic = extract_topic(text)
        result: dict[str, Any] = {
            "intent": intent,
            "topic": topic,
            "operator_session_id": operator_session_id,
        }

        if intent == ReconciliationIntent.EXPLORATION:
            result.update(self._handle_exploration(topic, operator_session_id))
        elif intent == ReconciliationIntent.RECONCILIATION:
            result.update(self._handle_reconciliation(topic, operator_session_id))
        elif intent == ReconciliationIntent.DECISION:
            result.update(self._handle_decision(topic, text, operator_session_id))
        elif intent == ReconciliationIntent.QUERY:
            result.update(self._handle_query(topic))

        return result

    def _handle_exploration(self, topic: str, operator_session_id: str) -> dict[str, Any]:
        session = self._engine.start_session(
            topic=topic,
            mode=ReconciliationMode.EXPLORATION.value,
            operator_session_id=operator_session_id,
        )
        self._active_session_id = session.session_id
        return {
            "action": "exploration_started",
            "session_id": session.session_id,
            "message": f"Exploration mode — no canonical changes. Topic: {topic}",
            "canon_safe": True,
        }

    def _handle_reconciliation(self, topic: str, operator_session_id: str) -> dict[str, Any]:
        session = self._engine.start_session(
            topic=topic,
            mode=ReconciliationMode.RECONCILIATION.value,
            operator_session_id=operator_session_id,
        )
        self._active_session_id = session.session_id
        self._engine.attach_sources(session.session_id)
        diagnostic = self._engine.run_diagnostic(session.session_id)
        proposals = self._engine.generate_canonical_update_proposals(session.session_id)
        questions = self._engine.generate_operator_questions(session.session_id)

        return {
            "action": "reconciliation_started",
            "session_id": session.session_id,
            "diagnostic_report_id": diagnostic.get("report_id", "") if diagnostic else "",
            "proposals_count": len(proposals),
            "operator_questions": questions,
            "message": f"Reconciliation session started. {len(proposals)} proposals generated. Approval required before any canonical changes.",
            "canon_safe": True,
        }

    def _handle_decision(self, topic: str, text: str, operator_session_id: str) -> dict[str, Any]:
        if not self._active_session_id:
            session = self._engine.start_session(
                topic=topic,
                mode=ReconciliationMode.DECISION.value,
                operator_session_id=operator_session_id,
            )
            self._active_session_id = session.session_id

        self._engine.set_mode(self._active_session_id, ReconciliationMode.DECISION.value)
        self._engine.attach_sources(self._active_session_id)
        diagnostic = self._engine.run_diagnostic(self._active_session_id)
        proposals = self._engine.generate_canonical_update_proposals(self._active_session_id)

        return {
            "action": "decision_proposals_ready",
            "session_id": self._active_session_id,
            "proposals_count": len(proposals),
            "message": f"Decision mode: {len(proposals)} canonical update proposals generated. Use approve/reject endpoints to decide.",
            "approval_required": True,
            "canon_safe": True,
        }

    def _handle_query(self, topic: str) -> dict[str, Any]:
        sources = self._engine._registry.list_sources()
        items = self._engine._job_store.list_items()
        entities: set[str] = set()
        for item in items:
            entities.update(item.extracted_entities)

        return {
            "action": "query_response",
            "sources_count": len(sources),
            "ingested_items_count": len(items),
            "known_entities": sorted(entities),
            "message": f"Current understanding: {len(sources)} sources, {len(items)} items, {len(entities)} entities.",
            "canon_safe": True,
        }

    def get_active_session(self) -> dict[str, Any] | None:
        if not self._active_session_id:
            return None
        session = self._engine._session_store.get_session(self._active_session_id)
        if not session:
            return None
        return session.to_dict()

    def get_propagation_preview(self) -> dict[str, Any]:
        if not self._active_session_id:
            return {"error": "no_active_session"}
        return self._engine.preview_propagation(self._active_session_id)

    def get_work_packet_implications(self) -> list[dict[str, Any]]:
        if not self._active_session_id:
            return []
        return self._engine.generate_work_packet_updates(self._active_session_id)
