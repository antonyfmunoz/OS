"""Phase 19 — Reality Canonicalization E2E tests.

Verifies the RealityMutation contract, CanonicalRealityWritePath validation,
source-specific wiring (governance, conversation), restart continuity,
and no-new-authority proofs.

Phase 19. UMH test suite.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, "/opt/OS")

from substrate.reality_model.reality_mutation import (
    MutationSource,
    MutationType,
    RealityMutation,
    RealityMutationReceipt,
)
from substrate.reality_model.canonical_reality_write import CanonicalRealityWritePath
from substrate.reality_model.instance import InstanceObservation, InstanceRealityModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_instance_model(tmp_path: Path) -> InstanceRealityModel:
    store = tmp_path / "instance.jsonl"
    return InstanceRealityModel(
        user_id="test-user",
        org_id="test-org",
        store_path=store,
    )


def _make_mutation(
    source: MutationSource = MutationSource.CONVERSATION_MEMORY,
    mutation_type: MutationType = MutationType.INSIGHT_PROMOTED,
    content: str = "test observation content",
    confidence: float = 0.8,
    domain: str = "test",
    **kwargs,
) -> RealityMutation:
    return RealityMutation(
        mutation_id=f"rm-test-{uuid4().hex[:12]}",
        source_system=source,
        source_id=f"trace-{uuid4().hex[:8]}",
        mutation_type=mutation_type,
        content=content,
        confidence=confidence,
        domain=domain,
        **kwargs,
    )


# ===========================================================================
# Test Class 1: Conversation observation → Reality
# ===========================================================================

class TestConversationToReality:

    def test_conversation_mutation_records_observation(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(
            source=MutationSource.CONVERSATION_MEMORY,
            mutation_type=MutationType.INSIGHT_PROMOTED,
            content="User prefers direct communication",
            confidence=0.85,
            domain="conversation",
        )

        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is True
        assert receipt.observation_id is not None
        assert receipt.mutation_id == mutation.mutation_id

        obs_list = model.all()
        assert len(obs_list) == 1
        obs = obs_list[0]
        assert obs.content == "User prefers direct communication"
        assert obs.domain == "conversation"
        assert obs.confidence == 0.85

    def test_source_tag_present(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(source=MutationSource.CONVERSATION_MEMORY)
        writer.apply_mutation(mutation)

        obs = model.all()[0]
        assert "source:conversation_memory" in obs.tags

    def test_mutation_type_tag_present(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(mutation_type=MutationType.INSIGHT_PROMOTED)
        writer.apply_mutation(mutation)

        obs = model.all()[0]
        assert "mutation:insight_promoted" in obs.tags

    def test_confidence_matches_input(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(confidence=0.42)
        writer.apply_mutation(mutation)

        obs = model.all()[0]
        assert obs.confidence == 0.42

    def test_evidence_in_metadata(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(
            evidence={"source_file": "test.md", "memory_type": "feedback"},
        )
        writer.apply_mutation(mutation)

        obs = model.all()[0]
        assert obs.metadata.get("source_file") == "test.md"
        assert obs.metadata.get("memory_type") == "feedback"


# ===========================================================================
# Test Class 2: Governance decision → Reality
# ===========================================================================

class TestGovernanceToReality:

    def test_governance_decision_records(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(
            source=MutationSource.GOVERNANCE,
            mutation_type=MutationType.DECISION_RECORDED,
            content="Governance approved: low risk execution",
            confidence=0.95,
            domain="governance",
            evidence={
                "risk_class": "low",
                "decision": "approve",
                "work_packet_id": "wp-001",
            },
        )

        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is True
        obs = model.all()[0]
        assert obs.domain == "governance"
        assert "source:governance" in obs.tags
        assert obs.metadata.get("risk_class") == "low"
        assert obs.metadata.get("decision") == "approve"
        assert obs.metadata.get("work_packet_id") == "wp-001"

    def test_governance_with_context(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(
            source=MutationSource.GOVERNANCE,
            mutation_type=MutationType.DECISION_RECORDED,
            governance_context={"verdict_id": "v-123"},
        )

        writer.apply_mutation(mutation)

        obs = model.all()[0]
        assert obs.metadata.get("governance_context") == {"verdict_id": "v-123"}

    def test_deny_decision_also_records(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(
            source=MutationSource.GOVERNANCE,
            mutation_type=MutationType.DECISION_RECORDED,
            content="Governance denied: high risk without approval",
            evidence={"risk_class": "high", "decision": "deny"},
        )

        receipt = writer.apply_mutation(mutation)
        assert receipt.accepted is True
        obs = model.all()[0]
        assert "deny" in obs.content.lower() or obs.metadata.get("decision") == "deny"


# ===========================================================================
# Test Class 3: Validation gates
# ===========================================================================

class TestValidationGates:

    def test_empty_content_rejected(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(content="")
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is False
        assert "empty content" in receipt.reason
        assert model.count() == 0

    def test_oversized_content_rejected(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(content="x" * 2001)
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is False
        assert "2000" in receipt.reason
        assert model.count() == 0

    def test_exactly_2000_chars_accepted(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(content="x" * 2000)
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is True

    def test_empty_mutation_id_rejected(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation()
        mutation.mutation_id = ""
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is False
        assert "mutation_id" in receipt.reason

    def test_confidence_too_high_rejected(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(confidence=1.5)
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is False
        assert "confidence" in receipt.reason

    def test_confidence_negative_rejected(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(confidence=-0.1)
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is False
        assert "confidence" in receipt.reason

    def test_confidence_zero_accepted(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(confidence=0.0)
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is True

    def test_confidence_one_accepted(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation(confidence=1.0)
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is True

    def test_valid_mutation_accepted(self, tmp_path):
        model = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model)

        mutation = _make_mutation()
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is True
        assert receipt.reason == "recorded"

    def test_no_model_still_accepts(self):
        writer = CanonicalRealityWritePath(reality_model=None)
        mutation = _make_mutation()
        receipt = writer.apply_mutation(mutation)

        assert receipt.accepted is True
        assert receipt.observation_id is None


# ===========================================================================
# Test Class 4: Restart continuity
# ===========================================================================

class TestRestartContinuity:

    def test_observation_survives_restart(self, tmp_path):
        model1 = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model1)

        mutation = _make_mutation(
            content="critical observation about governance",
            confidence=0.9,
            domain="governance",
            evidence={"key": "value"},
        )
        receipt = writer.apply_mutation(mutation)
        assert receipt.accepted is True

        # Destroy model1, create model2 from same path
        del model1
        model2 = _make_instance_model(tmp_path)

        assert model2.count() == 1
        obs = model2.all()[0]
        assert obs.content == "critical observation about governance"
        assert obs.domain == "governance"
        assert obs.confidence == 0.9
        assert "source:conversation_memory" in obs.tags

    def test_multiple_observations_survive(self, tmp_path):
        model1 = _make_instance_model(tmp_path)
        writer = CanonicalRealityWritePath(reality_model=model1)

        for i in range(5):
            mutation = _make_mutation(content=f"observation {i}", domain=f"domain-{i}")
            writer.apply_mutation(mutation)

        del model1
        model2 = _make_instance_model(tmp_path)

        assert model2.count() == 5
        domains = {o.domain for o in model2.all()}
        assert domains == {f"domain-{i}" for i in range(5)}


# ===========================================================================
# Test Class 5: IntentRouter has no execute (Phase 18 regression)
# ===========================================================================

class TestNoNewAuthority:

    def test_intent_router_has_no_execute(self):
        from substrate.operator.intent_router import IntentRouter
        assert not hasattr(IntentRouter, "execute"), (
            "IntentRouter must not have an execute method — "
            "it classifies and routes, it does not execute"
        )

    def test_intent_router_has_no_run(self):
        from substrate.operator.intent_router import IntentRouter
        assert not hasattr(IntentRouter, "run"), (
            "IntentRouter must not have a run method"
        )


# ===========================================================================
# Test Class 6: CanonicalRealityWritePath has no execution authority
# ===========================================================================

class TestWritePathNoAuthority:

    def test_no_execute_method(self):
        assert not hasattr(CanonicalRealityWritePath, "execute"), (
            "CanonicalRealityWritePath must not have an execute method — "
            "it validates and writes observations, it does not execute work"
        )

    def test_no_run_method(self):
        assert not hasattr(CanonicalRealityWritePath, "run"), (
            "CanonicalRealityWritePath must not have a run method"
        )

    def test_no_dispatch_method(self):
        assert not hasattr(CanonicalRealityWritePath, "dispatch"), (
            "CanonicalRealityWritePath must not have a dispatch method"
        )

    def test_only_apply_mutation_is_public(self):
        public_methods = [
            m for m in dir(CanonicalRealityWritePath)
            if not m.startswith("_") and callable(getattr(CanonicalRealityWritePath, m))
        ]
        assert public_methods == ["apply_mutation"], (
            f"CanonicalRealityWritePath should have exactly one public method: "
            f"apply_mutation. Found: {public_methods}"
        )


# ===========================================================================
# Test Class 7: Mutation contract shape
# ===========================================================================

class TestMutationContract:

    def test_mutation_source_values(self):
        expected = {"execution", "governance", "conversation_memory", "observation_api", "simulation"}
        actual = {m.value for m in MutationSource}
        assert actual == expected

    def test_mutation_type_values(self):
        expected = {"observation_recorded", "pattern_confirmed", "decision_recorded", "insight_promoted"}
        actual = {m.value for m in MutationType}
        assert actual == expected

    def test_receipt_has_required_fields(self):
        receipt = RealityMutationReceipt(
            mutation_id="rm-test",
            observation_id=None,
            accepted=False,
            reason="test rejection",
        )
        assert receipt.mutation_id == "rm-test"
        assert receipt.observation_id is None
        assert receipt.accepted is False
        assert receipt.reason == "test rejection"
        assert isinstance(receipt.timestamp, float)

    def test_mutation_defaults(self):
        mutation = RealityMutation(
            mutation_id="rm-test",
            source_system=MutationSource.EXECUTION,
            source_id="trace-1",
            mutation_type=MutationType.OBSERVATION_RECORDED,
            content="test",
            confidence=0.5,
            domain="test",
        )
        assert isinstance(mutation.timestamp, float)
        assert mutation.evidence == {}
        assert mutation.tags == []
        assert mutation.metadata == {}
        assert mutation.governance_context is None


# ===========================================================================
# Test Class 8: Event emission
# ===========================================================================

class TestEventEmission:

    def test_event_emitted_on_successful_write(self, tmp_path):
        model = _make_instance_model(tmp_path)

        class MockEventSpine:
            def __init__(self):
                self.events = []

            def emit(self, **kwargs):
                self.events.append(kwargs)

        spine = MockEventSpine()
        writer = CanonicalRealityWritePath(reality_model=model, event_spine=spine)

        mutation = _make_mutation()
        writer.apply_mutation(mutation)

        assert len(spine.events) == 1
        event = spine.events[0]
        assert event["event_type"] == "reality_mutation_applied"
        assert event["source"] == "canonical_reality_write"
        assert event["data"]["mutation_id"] == mutation.mutation_id
        assert event["data"]["source_system"] == mutation.source_system.value

    def test_no_event_on_rejection(self, tmp_path):
        model = _make_instance_model(tmp_path)

        class MockEventSpine:
            def __init__(self):
                self.events = []

            def emit(self, **kwargs):
                self.events.append(kwargs)

        spine = MockEventSpine()
        writer = CanonicalRealityWritePath(reality_model=model, event_spine=spine)

        mutation = _make_mutation(content="")
        writer.apply_mutation(mutation)

        assert len(spine.events) == 0
