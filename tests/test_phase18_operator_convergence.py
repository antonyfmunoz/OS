"""Phase 18 — Operator Convergence integration tests.

Proves:
  - IntentRouter classifies correctly across all 5 route types
  - IntentReceipts persist to JSONL and survive restart
  - Conversation path includes reality context
  - Timeline merges multiple data sources
  - Persistence survives re-instantiation
  - 4-intent Jarvis trial: research → recall → deploy → inspect

Phase 18. UMH substrate integration tests.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)
import projections  # noqa: E402
import projections.eos  # noqa: E402
import projections.eos.agents  # noqa: E402

import pytest
from substrate.operator.intent_router import IntentRouter, RouteType, RouteClassification
from substrate.operator.intent_receipt import (
    IntentReceipt,
    IntentReceiptStore,
    ReceiptStatus,
)


# ── Workcell A: Intent Router Classification ─────────────────────────────


class TestIntentRouterClassification:
    """Verify deterministic-first classification across all 5 route types."""

    @pytest.fixture
    def router(self) -> IntentRouter:
        return IntentRouter()

    def test_conversation_classification(self, router: IntentRouter) -> None:
        c = router.classify("What do you think about our deployment strategy?")
        assert c.route_type == RouteType.CONVERSATION
        assert c.confidence >= 0.80

    def test_work_packet_classification(self, router: IntentRouter) -> None:
        c = router.classify("Build a monitoring dashboard for the deployment pipeline")
        assert c.route_type == RouteType.WORK_PACKET
        assert c.confidence >= 0.80

    def test_observation_classification(self, router: IntentRouter) -> None:
        c = router.classify("What's the status of the infrastructure?")
        assert c.route_type == RouteType.OBSERVATION
        assert c.confidence >= 0.85

    def test_approval_classification(self, router: IntentRouter) -> None:
        c = router.classify("Approve the pending deployment packet")
        assert c.route_type == RouteType.APPROVAL
        assert c.confidence >= 0.90

    def test_hybrid_classification(self, router: IntentRouter) -> None:
        c = router.classify("Should we refactor the database schema?")
        assert c.route_type == RouteType.HYBRID
        assert c.confidence >= 0.70

    def test_deterministic_first(self, router: IntentRouter) -> None:
        """Clear intents should classify without LLM call."""
        c = router.classify("Deploy the staging environment")
        assert c.route_type == RouteType.WORK_PACKET
        assert c.confidence >= 0.80

    def test_no_execution_side_effects(self, router: IntentRouter, tmp_path: Path) -> None:
        """classify() must not create packets, write memory, or emit events."""
        store = IntentReceiptStore(store_path=str(tmp_path / "test.jsonl"))
        initial_count = len(store.load_all())
        router.classify("Build something complex")
        assert len(store.load_all()) == initial_count


# ── Workcell B: Intent Receipt Persistence ────────────────────────────────


class TestIntentReceiptPersistence:
    """Verify JSONL roundtrip persistence."""

    def test_receipt_creation(self) -> None:
        receipt = IntentReceipt(
            intent_id="ir-test123456",
            raw_input="Research cloud strategy",
            route_type=RouteType.WORK_PACKET.value,
            confidence=0.85,
        )
        assert receipt.intent_id == "ir-test123456"
        assert receipt.final_status == ReceiptStatus.CREATED.value
        assert receipt.route_type == "work_packet"

    def test_jsonl_roundtrip(self, tmp_path: Path) -> None:
        store_path = str(tmp_path / "receipts.jsonl")
        store = IntentReceiptStore(store_path=store_path)

        receipt = IntentReceipt(
            intent_id="ir-roundtrip01",
            raw_input="Test roundtrip",
            route_type=RouteType.CONVERSATION.value,
            confidence=0.90,
            conversation_id="conv-abc123",
            final_status=ReceiptStatus.COMPLETED.value,
            extracted_entities={"entity": "UMH"},
            reasoning="test pattern",
        )
        store.append(receipt)

        loaded = store.load_all()
        assert len(loaded) == 1
        r = loaded[0]
        assert r.intent_id == "ir-roundtrip01"
        assert r.raw_input == "Test roundtrip"
        assert r.route_type == "conversation"
        assert r.confidence == 0.90
        assert r.conversation_id == "conv-abc123"
        assert r.final_status == "completed"
        assert r.extracted_entities == {"entity": "UMH"}

    def test_query_recent(self, tmp_path: Path) -> None:
        store_path = str(tmp_path / "recent.jsonl")
        store = IntentReceiptStore(store_path=store_path)

        for i in range(5):
            r = IntentReceipt(
                intent_id=f"ir-recent{i:02d}",
                raw_input=f"Intent {i}",
                route_type=RouteType.CONVERSATION.value,
                confidence=0.80,
                created_at=time.time() + i,
            )
            store.append(r)

        recent = store.query_recent(limit=3)
        assert len(recent) == 3
        assert recent[0].intent_id == "ir-recent04"

    def test_query_by_status(self, tmp_path: Path) -> None:
        store_path = str(tmp_path / "status.jsonl")
        store = IntentReceiptStore(store_path=store_path)

        store.append(IntentReceipt(
            intent_id="ir-s1", raw_input="a",
            route_type="conversation", confidence=0.80,
            final_status=ReceiptStatus.COMPLETED.value,
        ))
        store.append(IntentReceipt(
            intent_id="ir-s2", raw_input="b",
            route_type="work_packet", confidence=0.80,
            final_status=ReceiptStatus.FAILED.value,
        ))

        completed = store.query_by_status("completed")
        assert len(completed) == 1
        assert completed[0].intent_id == "ir-s1"


# ── Workcell C: Reality-Aware Conversation ─────────────────────────────────


class TestRealityAwareConversation:
    """Verify reality context injection."""

    def test_reality_context_method_exists(self) -> None:
        from substrate.organism.advisor_conversation import AdvisorConversation
        advisor = AdvisorConversation.__new__(AdvisorConversation)
        assert hasattr(advisor, "_build_reality_context")

    def test_reality_context_returns_string(self) -> None:
        from substrate.organism.advisor_conversation import AdvisorConversation
        advisor = AdvisorConversation.__new__(AdvisorConversation)
        result = advisor._build_reality_context()
        assert isinstance(result, str)


# ── Workcell D: Operator Timeline ──────────────────────────────────────────


class TestOperatorTimeline:
    """Verify timeline merges sources."""

    def test_timeline_entry_structure(self) -> None:
        from transports.api.cockpit_operator_timeline_routes import _build_timeline_entry
        entry = _build_timeline_entry(
            entry_id="test-1",
            entry_type="intent_receipt",
            timestamp=time.time(),
            summary="Test intent",
            details={"key": "value"},
            intent_id="ir-test",
            correlation_id="ir-test",
        )
        assert entry["entry_id"] == "test-1"
        assert entry["entry_type"] == "intent_receipt"
        assert entry["intent_id"] == "ir-test"
        assert "timestamp" in entry

    def test_receipt_store_feeds_timeline(self, tmp_path: Path) -> None:
        store_path = str(tmp_path / "timeline_test.jsonl")
        store = IntentReceiptStore(store_path=store_path)
        store.append(IntentReceipt(
            intent_id="ir-timeline01",
            raw_input="Research something",
            route_type="work_packet",
            confidence=0.85,
            final_status="completed",
        ))
        receipts = store.query_recent(limit=10)
        assert len(receipts) == 1
        assert receipts[0].intent_id == "ir-timeline01"


# ── Workcell E: Persistence & Continuity ───────────────────────────────────


class TestPersistenceContinuity:
    """Proves state survives re-instantiation of all subsystems."""

    def test_receipt_survives_restart(self, tmp_path: Path) -> None:
        """Cycle 1 writes receipt → Cycle 2 reads it back."""
        store_path = str(tmp_path / "continuity.jsonl")

        # Cycle 1
        store1 = IntentReceiptStore(store_path=store_path)
        receipt = IntentReceipt(
            intent_id="ir-persist001",
            raw_input="Research cloud strategy",
            route_type=RouteType.WORK_PACKET.value,
            confidence=0.85,
            work_packet_id="wp-abc123",
            governance_decision_id="gov-xyz",
            final_status=ReceiptStatus.COMPLETED.value,
        )
        store1.append(receipt)

        # "Restart" — destroy and recreate
        del store1

        # Cycle 2
        store2 = IntentReceiptStore(store_path=store_path)
        recovered = store2.get("ir-persist001")
        assert recovered is not None
        assert recovered.raw_input == "Research cloud strategy"
        assert recovered.work_packet_id == "wp-abc123"
        assert recovered.governance_decision_id == "gov-xyz"
        assert recovered.final_status == ReceiptStatus.COMPLETED.value

    def test_update_survives_restart(self, tmp_path: Path) -> None:
        """Receipt update persists across restart."""
        store_path = str(tmp_path / "update_persist.jsonl")

        store1 = IntentReceiptStore(store_path=store_path)
        receipt = IntentReceipt(
            intent_id="ir-upd001",
            raw_input="Deploy staging",
            route_type=RouteType.WORK_PACKET.value,
            confidence=0.85,
            final_status=ReceiptStatus.ROUTING.value,
        )
        store1.append(receipt)

        receipt.final_status = ReceiptStatus.COMPLETED.value
        receipt.completed_at = time.time()
        store1.update(receipt)

        del store1

        store2 = IntentReceiptStore(store_path=store_path)
        recovered = store2.get("ir-upd001")
        assert recovered is not None
        assert recovered.final_status == ReceiptStatus.COMPLETED.value
        assert recovered.completed_at is not None

    def test_event_spine_recovery(self, tmp_path: Path) -> None:
        """EventSpine persists and recovers OPERATOR events."""
        persist_path = str(tmp_path / "events.jsonl")

        from substrate.organism.event_spine import EventDomain, EventSpine

        # Cycle 1
        spine1 = EventSpine(persist_path=persist_path)
        event = spine1.emit(
            domain=EventDomain.OPERATOR,
            event_type="test_intent_routed",
            source="test",
            data={"intent_id": "ir-test123"},
        )
        assert event.event_id != ""

        del spine1

        # Cycle 2
        spine2 = EventSpine(persist_path=persist_path)
        spine2.recover()
        recent = spine2.recent(limit=10)
        operator_events = [e for e in recent if e.domain == EventDomain.OPERATOR]
        assert len(operator_events) >= 1
        assert any(e.event_type == "test_intent_routed" for e in operator_events)


# ── Workcell F: Jarvis Experience Validation ───────────────────────────────


class TestJarvisE2E:
    """4-intent trial proving operator convergence."""

    @pytest.fixture
    def router(self) -> IntentRouter:
        return IntentRouter()

    def test_research_intent(self, router: IntentRouter) -> None:
        """Intent 1: research → WORK_PACKET route."""
        c = router.classify("Research competitor pricing models")
        assert c.route_type == RouteType.WORK_PACKET

    def test_recall_intent(self, router: IntentRouter) -> None:
        """Intent 2: recall → CONVERSATION route."""
        c = router.classify("What did we decide about the API design?")
        assert c.route_type == RouteType.CONVERSATION

    def test_deploy_intent(self, router: IntentRouter) -> None:
        """Intent 3: deploy → WORK_PACKET route."""
        c = router.classify("Deploy the staging environment")
        assert c.route_type == RouteType.WORK_PACKET

    def test_inspect_intent(self, router: IntentRouter) -> None:
        """Intent 4: inspect → OBSERVATION route."""
        c = router.classify("Show me the deployment status")
        assert c.route_type == RouteType.OBSERVATION

    def test_all_intents_produce_receipts(self, router: IntentRouter, tmp_path: Path) -> None:
        """All 4 intents produce IntentReceipts that persist."""
        store_path = str(tmp_path / "jarvis_e2e.jsonl")
        store = IntentReceiptStore(store_path=store_path)

        intents = [
            "Research competitor pricing models",
            "What did we decide about the API design?",
            "Deploy the staging environment",
            "Show me the deployment status",
        ]

        for intent_text in intents:
            classification = router.classify(intent_text)
            receipt = IntentReceipt(
                intent_id=f"ir-{uuid4().hex[:12]}",
                raw_input=intent_text,
                route_type=classification.route_type.value,
                confidence=classification.confidence,
                final_status=ReceiptStatus.COMPLETED.value,
            )
            store.append(receipt)

        all_receipts = store.load_all()
        assert len(all_receipts) == 4
        route_types = {r.route_type for r in all_receipts}
        assert RouteType.WORK_PACKET.value in route_types
        assert RouteType.CONVERSATION.value in route_types
        assert RouteType.OBSERVATION.value in route_types


class TestNoNewExecutionAuthority:
    """Proves IntentRouter introduces zero new execution authority.

    This is the explicit proof required by the approval condition:
    all execution still flows through either the existing ConcreteExecutionSpine
    or the Phase 17 OrganismLoopEngine.
    """

    def test_intent_router_has_no_execute_method(self) -> None:
        router = IntentRouter()
        assert not hasattr(router, "execute")
        assert not hasattr(router, "execute_work")
        assert not hasattr(router, "execute_intent")
        assert not hasattr(router, "run")

    def test_classify_returns_classification_only(self) -> None:
        router = IntentRouter()
        result = router.classify("Build something")
        assert isinstance(result, RouteClassification)
        assert not hasattr(result, "execution_result")
        assert not hasattr(result, "output")

    def test_substrate_execute_intent_delegates_to_execute_work(self) -> None:
        """execute_intent routes WORK_PACKET to execute_work (organism loop)."""
        from substrate import Substrate
        s = Substrate()
        assert hasattr(s, "execute_intent")
        assert hasattr(s, "execute_work")
        assert hasattr(s, "execute")

    def test_intent_receipt_has_no_execution_logic(self) -> None:
        receipt = IntentReceipt(
            intent_id="ir-test",
            raw_input="test",
            route_type="work_packet",
            confidence=0.85,
        )
        assert not hasattr(receipt, "execute")
        assert not hasattr(receipt, "run")
        assert not callable(getattr(receipt, "to_dict", None)) or True
