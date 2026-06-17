"""Gate 5 — Capability Runtime tests.

Tests emergent capability tracking: registration, evidence, maturity
scoring, lineage, pattern detection, and API routes.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTypes:
    def test_capability_maturity_enum(self):
        from substrate.organism.capability_runtime import CapabilityMaturity

        assert CapabilityMaturity.EMERGING.value == "emerging"
        assert CapabilityMaturity.VALIDATED.value == "validated"
        assert CapabilityMaturity.OPERATIONAL.value == "operational"
        assert CapabilityMaturity.INSTITUTIONAL.value == "institutional"

    def test_evidence_type_enum(self):
        from substrate.organism.capability_runtime import CapabilityEvidenceType

        assert CapabilityEvidenceType.EXECUTION_OUTCOME.value == "execution_outcome"
        assert CapabilityEvidenceType.TEMPLATE_MATCH.value == "template_match"
        assert CapabilityEvidenceType.MANUAL_ATTESTATION.value == "manual_attestation"
        assert CapabilityEvidenceType.RELIABILITY_DATA.value == "reliability_data"
        assert CapabilityEvidenceType.GOAL_ALIGNMENT.value == "goal_alignment"

    def test_emergent_capability_creation(self):
        from substrate.organism.capability_runtime import EmergentCapability, CapabilityMaturity

        cap = EmergentCapability(
            name="Test Capability",
            description="A test capability",
            origin_intent_id="intent-abc123",
        )
        assert cap.name == "Test Capability"
        assert cap.maturity == CapabilityMaturity.EMERGING
        assert cap.capability_id.startswith("ecap-")
        assert cap.origin_intent_id == "intent-abc123"

    def test_emergent_capability_to_dict(self):
        from substrate.organism.capability_runtime import EmergentCapability, CapabilityMaturity

        cap = EmergentCapability(name="Test", maturity=CapabilityMaturity.VALIDATED)
        d = cap.to_dict()
        assert d["maturity"] == "validated"
        assert d["name"] == "Test"
        assert isinstance(d["evidence_ids"], list)

    def test_emergent_capability_from_dict(self):
        from substrate.organism.capability_runtime import EmergentCapability, CapabilityMaturity

        d = {"capability_id": "ecap-test123", "name": "Test", "maturity": "operational"}
        cap = EmergentCapability.from_dict(d)
        assert cap.capability_id == "ecap-test123"
        assert cap.maturity == CapabilityMaturity.OPERATIONAL

    def test_capability_evidence_roundtrip(self):
        from substrate.organism.capability_runtime import CapabilityEvidence, CapabilityEvidenceType

        ev = CapabilityEvidence(
            capability_id="ecap-test",
            evidence_type=CapabilityEvidenceType.EXECUTION_OUTCOME,
            source_id="outcome-123",
            description="Build succeeded",
            quality_score=0.9,
        )
        d = ev.to_dict()
        ev2 = CapabilityEvidence.from_dict(d)
        assert ev2.evidence_type == CapabilityEvidenceType.EXECUTION_OUTCOME
        assert ev2.quality_score == 0.9

    def test_invalid_maturity_defaults_to_emerging(self):
        from substrate.organism.capability_runtime import EmergentCapability, CapabilityMaturity

        cap = EmergentCapability.from_dict({"maturity": "nonexistent"})
        assert cap.maturity == CapabilityMaturity.EMERGING

    def test_invalid_evidence_type_defaults_to_manual(self):
        from substrate.organism.capability_runtime import CapabilityEvidence, CapabilityEvidenceType

        ev = CapabilityEvidence.from_dict({"evidence_type": "nonexistent"})
        assert ev.evidence_type == CapabilityEvidenceType.MANUAL_ATTESTATION


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Maturity scoring
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestMaturityScoring:
    def test_no_evidence_score_zero(self):
        from substrate.organism.capability_runtime import compute_maturity_score

        assert compute_maturity_score([]) == 0.0

    def test_single_low_quality_evidence(self):
        from substrate.organism.capability_runtime import (
            CapabilityEvidence,
            CapabilityEvidenceType,
            compute_maturity_score,
            maturity_from_score,
            CapabilityMaturity,
        )

        evidence = [
            CapabilityEvidence(
                quality_score=0.3, evidence_type=CapabilityEvidenceType.MANUAL_ATTESTATION
            )
        ]
        score = compute_maturity_score(evidence)
        assert score > 0.0
        assert score < 0.3
        assert maturity_from_score(score) == CapabilityMaturity.EMERGING

    def test_five_high_quality_evidence_scores_high(self):
        from substrate.organism.capability_runtime import (
            CapabilityEvidence,
            CapabilityEvidenceType,
            compute_maturity_score,
            maturity_from_score,
            CapabilityMaturity,
        )

        evidence = [
            CapabilityEvidence(
                quality_score=0.95, evidence_type=CapabilityEvidenceType.EXECUTION_OUTCOME
            )
            for _ in range(5)
        ]
        score = compute_maturity_score(evidence)
        assert score >= 0.85
        assert maturity_from_score(score) == CapabilityMaturity.INSTITUTIONAL

    def test_coverage_factor_scales_with_count(self):
        from substrate.organism.capability_runtime import (
            CapabilityEvidence,
            CapabilityEvidenceType,
            compute_maturity_score,
        )

        one = [
            CapabilityEvidence(
                quality_score=0.9, evidence_type=CapabilityEvidenceType.EXECUTION_OUTCOME
            )
        ]
        five = [
            CapabilityEvidence(
                quality_score=0.9, evidence_type=CapabilityEvidenceType.EXECUTION_OUTCOME
            )
            for _ in range(5)
        ]
        assert compute_maturity_score(five) > compute_maturity_score(one)

    def test_execution_outcome_weighted_higher_than_manual(self):
        from substrate.organism.capability_runtime import (
            CapabilityEvidence,
            CapabilityEvidenceType,
            compute_maturity_score,
        )

        exec_ev = [
            CapabilityEvidence(
                quality_score=0.8, evidence_type=CapabilityEvidenceType.EXECUTION_OUTCOME
            )
            for _ in range(5)
        ]
        manual_ev = [
            CapabilityEvidence(
                quality_score=0.8, evidence_type=CapabilityEvidenceType.MANUAL_ATTESTATION
            )
            for _ in range(5)
        ]
        assert compute_maturity_score(exec_ev) > compute_maturity_score(manual_ev)

    def test_maturity_thresholds(self):
        from substrate.organism.capability_runtime import maturity_from_score, CapabilityMaturity

        assert maturity_from_score(0.0) == CapabilityMaturity.EMERGING
        assert maturity_from_score(0.29) == CapabilityMaturity.EMERGING
        assert maturity_from_score(0.30) == CapabilityMaturity.VALIDATED
        assert maturity_from_score(0.59) == CapabilityMaturity.VALIDATED
        assert maturity_from_score(0.60) == CapabilityMaturity.OPERATIONAL
        assert maturity_from_score(0.84) == CapabilityMaturity.OPERATIONAL
        assert maturity_from_score(0.85) == CapabilityMaturity.INSTITUTIONAL
        assert maturity_from_score(1.0) == CapabilityMaturity.INSTITUTIONAL


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pattern detection
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPatternDetection:
    def test_no_outcomes_no_proposals(self):
        from substrate.organism.capability_runtime import detect_capability_patterns

        assert detect_capability_patterns([]) == []

    def test_below_min_occurrences_filtered(self):
        from substrate.organism.capability_runtime import detect_capability_patterns

        outcomes = [
            {"action_type": "code_review", "status": "success", "description": "Review PR #1"},
            {"action_type": "code_review", "status": "success", "description": "Review PR #2"},
        ]
        assert detect_capability_patterns(outcomes, min_occurrences=3) == []

    def test_sufficient_occurrences_and_success_rate(self):
        from substrate.organism.capability_runtime import detect_capability_patterns

        outcomes = [
            {"action_type": "code_review", "status": "success", "description": f"Review PR #{i}"}
            for i in range(5)
        ]
        proposals = detect_capability_patterns(outcomes, min_occurrences=3)
        assert len(proposals) == 1
        assert proposals[0]["proposed_name"] == "Code Review"
        assert proposals[0]["success_rate"] == 1.0
        assert proposals[0]["occurrences"] == 5

    def test_low_success_rate_filtered(self):
        from substrate.organism.capability_runtime import detect_capability_patterns

        outcomes = [
            {"action_type": "deploy", "status": "success"},
            {"action_type": "deploy", "status": "failure"},
            {"action_type": "deploy", "status": "failure"},
            {"action_type": "deploy", "status": "failure"},
        ]
        assert detect_capability_patterns(outcomes, min_occurrences=3, min_success_rate=0.6) == []

    def test_multiple_action_types(self):
        from substrate.organism.capability_runtime import detect_capability_patterns

        outcomes = []
        for i in range(4):
            outcomes.append({"action_type": "code_review", "status": "success"})
        for i in range(3):
            outcomes.append({"action_type": "deploy", "status": "success"})
        proposals = detect_capability_patterns(outcomes, min_occurrences=3)
        assert len(proposals) == 2
        assert proposals[0]["proposed_name"] == "Code Review"

    def test_empty_action_type_ignored(self):
        from substrate.organism.capability_runtime import detect_capability_patterns

        outcomes = [{"action_type": "", "status": "success"} for _ in range(5)]
        assert detect_capability_patterns(outcomes, min_occurrences=3) == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CapabilityRuntime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def runtime(tmp_path):
    from substrate.organism.capability_runtime import CapabilityRuntime

    return CapabilityRuntime(
        capabilities_path=str(tmp_path / "caps.jsonl"),
        evidence_path=str(tmp_path / "evidence.jsonl"),
    )


class TestCapabilityRuntime:
    def test_register_and_get(self, runtime):
        cap = runtime.register(name="Test Cap", description="A test")
        assert cap.name == "Test Cap"
        retrieved = runtime.get(cap.capability_id)
        assert retrieved is not None
        assert retrieved.name == "Test Cap"

    def test_register_with_intent(self, runtime):
        cap = runtime.register(
            name="Intent-linked Cap",
            description="Linked to intent",
            origin_intent_id="intent-abc123",
        )
        assert cap.origin_intent_id == "intent-abc123"

    def test_list_all(self, runtime):
        runtime.register(name="Cap1", description="First")
        runtime.register(name="Cap2", description="Second")
        caps = runtime.list_capabilities()
        assert len(caps) == 2

    def test_list_by_maturity(self, runtime):
        from substrate.organism.capability_runtime import CapabilityMaturity

        runtime.register(name="Cap1", description="First")
        caps = runtime.list_capabilities(maturity=CapabilityMaturity.EMERGING)
        assert len(caps) == 1
        caps = runtime.list_capabilities(maturity=CapabilityMaturity.OPERATIONAL)
        assert len(caps) == 0

    def test_list_by_tag(self, runtime):
        runtime.register(name="Cap1", description="First", tags=["infra"])
        runtime.register(name="Cap2", description="Second", tags=["product"])
        caps = runtime.list_capabilities(tag="infra")
        assert len(caps) == 1
        assert caps[0].name == "Cap1"

    def test_get_nonexistent_returns_none(self, runtime):
        assert runtime.get("nonexistent") is None

    def test_add_evidence(self, runtime):
        from substrate.organism.capability_runtime import CapabilityEvidenceType

        cap = runtime.register(name="Cap", description="Test")
        ev = runtime.add_evidence(
            cap.capability_id,
            evidence_type=CapabilityEvidenceType.EXECUTION_OUTCOME,
            source_id="outcome-1",
            description="Build passed",
            quality_score=0.85,
        )
        assert ev is not None
        assert ev.capability_id == cap.capability_id
        assert ev.quality_score == 0.85

    def test_add_evidence_nonexistent_capability(self, runtime):
        from substrate.organism.capability_runtime import CapabilityEvidenceType

        ev = runtime.add_evidence("nonexistent", CapabilityEvidenceType.MANUAL_ATTESTATION)
        assert ev is None

    def test_evidence_quality_clamped(self, runtime):
        from substrate.organism.capability_runtime import CapabilityEvidenceType

        cap = runtime.register(name="Cap", description="Test")
        ev = runtime.add_evidence(
            cap.capability_id, CapabilityEvidenceType.MANUAL_ATTESTATION, quality_score=1.5
        )
        assert ev.quality_score == 1.0
        ev2 = runtime.add_evidence(
            cap.capability_id, CapabilityEvidenceType.MANUAL_ATTESTATION, quality_score=-0.5
        )
        assert ev2.quality_score == 0.0

    def test_evidence_for(self, runtime):
        from substrate.organism.capability_runtime import CapabilityEvidenceType

        cap = runtime.register(name="Cap", description="Test")
        runtime.add_evidence(
            cap.capability_id, CapabilityEvidenceType.MANUAL_ATTESTATION, quality_score=0.5
        )
        runtime.add_evidence(
            cap.capability_id, CapabilityEvidenceType.EXECUTION_OUTCOME, quality_score=0.8
        )
        evidence = runtime.evidence_for(cap.capability_id)
        assert len(evidence) == 2

    def test_maturity_auto_promotes(self, runtime):
        from substrate.organism.capability_runtime import CapabilityEvidenceType, CapabilityMaturity

        cap = runtime.register(name="Cap", description="Test")
        assert cap.maturity == CapabilityMaturity.EMERGING
        for _ in range(5):
            runtime.add_evidence(
                cap.capability_id,
                CapabilityEvidenceType.EXECUTION_OUTCOME,
                quality_score=0.95,
            )
        updated = runtime.get(cap.capability_id)
        assert updated.maturity == CapabilityMaturity.INSTITUTIONAL

    def test_maturity_never_demotes(self, runtime):
        from substrate.organism.capability_runtime import CapabilityEvidenceType, CapabilityMaturity

        cap = runtime.register(name="Cap", description="Test")
        for _ in range(5):
            runtime.add_evidence(
                cap.capability_id, CapabilityEvidenceType.EXECUTION_OUTCOME, quality_score=0.9
            )
        assert runtime.get(cap.capability_id).maturity in (
            CapabilityMaturity.OPERATIONAL,
            CapabilityMaturity.INSTITUTIONAL,
        )
        runtime.add_evidence(
            cap.capability_id, CapabilityEvidenceType.MANUAL_ATTESTATION, quality_score=0.1
        )
        assert runtime.get(cap.capability_id).maturity != CapabilityMaturity.EMERGING

    def test_maturity_score(self, runtime):
        from substrate.organism.capability_runtime import CapabilityEvidenceType

        cap = runtime.register(name="Cap", description="Test")
        assert runtime.maturity_score(cap.capability_id) == 0.0
        runtime.add_evidence(
            cap.capability_id, CapabilityEvidenceType.EXECUTION_OUTCOME, quality_score=0.9
        )
        assert runtime.maturity_score(cap.capability_id) > 0.0

    def test_lineage(self, runtime):
        cap = runtime.register(
            name="Test Cap",
            description="Test",
            origin_intent_id="intent-abc123",
            understanding_sources=["doc-1", "doc-2"],
        )
        lineage = runtime.lineage(cap.capability_id)
        assert lineage["origin_intent_id"] == "intent-abc123"
        assert lineage["understanding_sources"] == ["doc-1", "doc-2"]
        assert lineage["evidence_count"] == 0

    def test_lineage_nonexistent(self, runtime):
        lineage = runtime.lineage("nonexistent")
        assert "error" in lineage

    def test_capabilities_from_intent(self, runtime):
        runtime.register(name="Cap1", description="First", origin_intent_id="intent-x")
        runtime.register(name="Cap2", description="Second", origin_intent_id="intent-x")
        runtime.register(name="Cap3", description="Third", origin_intent_id="intent-y")
        caps = runtime.capabilities_from_intent("intent-x")
        assert len(caps) == 2
        assert all(c.origin_intent_id == "intent-x" for c in caps)

    def test_propose_from_patterns(self, runtime):
        outcomes = [
            {"action_type": "code_review", "status": "success", "description": f"PR #{i}"}
            for i in range(5)
        ]
        proposals = runtime.propose_from_patterns(outcomes)
        assert len(proposals) == 1
        assert proposals[0]["proposed_name"] == "Code Review"

    def test_propose_excludes_existing(self, runtime):
        runtime.register(name="Code Review", description="Already exists")
        outcomes = [{"action_type": "code_review", "status": "success"} for _ in range(5)]
        proposals = runtime.propose_from_patterns(outcomes)
        assert len(proposals) == 0

    def test_summary(self, runtime):
        from substrate.organism.capability_runtime import CapabilityEvidenceType

        cap = runtime.register(name="Cap", description="Test", tags=["infra"])
        runtime.add_evidence(
            cap.capability_id, CapabilityEvidenceType.MANUAL_ATTESTATION, quality_score=0.5
        )
        summary = runtime.summary()
        assert summary["total_capabilities"] == 1
        assert summary["total_evidence"] == 1
        assert summary["by_maturity"]["emerging"] == 1
        assert summary["tags"]["infra"] == 1

    def test_capabilities_by_maturity(self, runtime):
        runtime.register(name="Cap1", description="First")
        runtime.register(name="Cap2", description="Second")
        by_mat = runtime.capabilities_by_maturity()
        assert len(by_mat["emerging"]) == 2
        assert len(by_mat["validated"]) == 0

    def test_link_operationalization(self, runtime):
        cap = runtime.register(name="Cap", description="Test")
        assert runtime.link_operationalization(cap.capability_id, "op-123")
        updated = runtime.get(cap.capability_id)
        assert "op-123" in updated.operationalization_ids

    def test_link_operationalization_nonexistent(self, runtime):
        assert not runtime.link_operationalization("nonexistent", "op-123")

    def test_link_operationalization_idempotent(self, runtime):
        cap = runtime.register(name="Cap", description="Test")
        runtime.link_operationalization(cap.capability_id, "op-123")
        runtime.link_operationalization(cap.capability_id, "op-123")
        updated = runtime.get(cap.capability_id)
        assert updated.operationalization_ids.count("op-123") == 1

    def test_link_projection(self, runtime):
        cap = runtime.register(name="Cap", description="Test")
        assert runtime.link_projection(cap.capability_id, "EntrepreneurOS")
        updated = runtime.get(cap.capability_id)
        assert "EntrepreneurOS" in updated.projections_using

    def test_link_projection_nonexistent(self, runtime):
        assert not runtime.link_projection("nonexistent", "EntrepreneurOS")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Persistence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestPersistence:
    def test_jsonl_roundtrip(self, tmp_path):
        from substrate.organism.capability_runtime import CapabilityRuntime, CapabilityEvidenceType

        caps_path = str(tmp_path / "caps.jsonl")
        ev_path = str(tmp_path / "evidence.jsonl")
        rt1 = CapabilityRuntime(capabilities_path=caps_path, evidence_path=ev_path)
        cap = rt1.register(name="Persistent Cap", description="Survives reload")
        rt1.add_evidence(
            cap.capability_id, CapabilityEvidenceType.EXECUTION_OUTCOME, quality_score=0.9
        )

        rt2 = CapabilityRuntime(capabilities_path=caps_path, evidence_path=ev_path)
        loaded = rt2.get(cap.capability_id)
        assert loaded is not None
        assert loaded.name == "Persistent Cap"
        assert len(rt2.evidence_for(cap.capability_id)) == 1

    def test_empty_file_loads_clean(self, tmp_path):
        from substrate.organism.capability_runtime import CapabilityRuntime

        caps_path = str(tmp_path / "caps.jsonl")
        rt = CapabilityRuntime(capabilities_path=caps_path)
        assert rt.list_capabilities() == []

    def test_malformed_jsonl_skipped(self, tmp_path):
        from substrate.organism.capability_runtime import CapabilityRuntime

        caps_path = str(tmp_path / "caps.jsonl")
        with open(caps_path, "w") as f:
            f.write("not valid json\n")
            f.write('{"capability_id": "ecap-valid", "name": "Valid"}\n')
        rt = CapabilityRuntime(capabilities_path=caps_path)
        caps = rt.list_capabilities()
        assert len(caps) == 1
        assert caps[0].capability_id == "ecap-valid"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Type coherence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTypeCoherence:
    def test_no_collision_with_job_capability(self):
        from substrate.organism.capability_runtime import EmergentCapability
        from substrate.execution.runtime.capability_router import Capability

        assert EmergentCapability.__name__ != Capability.__name__

    def test_no_collision_with_types_capability(self):
        from substrate.organism.capability_runtime import EmergentCapability
        from substrate.types import Capability as TypesCapability

        assert EmergentCapability.__name__ != TypesCapability.__name__

    def test_canonical_types_registered(self):
        from substrate.canonical_types import lookup

        assert lookup("EmergentCapability") is not None
        assert lookup("CapabilityMaturity") is not None
        assert lookup("CapabilityEvidence") is not None
        assert lookup("CapabilityEvidenceType") is not None
        assert lookup("CapabilityRuntime") is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Routes (FastAPI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestRoutes:
    def test_capability_routes_importable(self):
        from transports.api.cockpit_capability_routes import capability_router

        assert capability_router is not None

    def test_cockpit_mounts_capability_routes(self):
        import transports.api.cockpit as c

        route_paths = [r.path for r in c.router.routes if hasattr(r, "path")]
        assert any("/capabilities" in p for p in route_paths)
