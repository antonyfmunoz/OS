"""Tests for Gate 9 — Capability Compounding Engine.

Verifies:
- Types: PromotionType, PromotionStatus, PromotionCandidate
- Deterministic scoring: all 4 tiers
- Detection: outcome→insight, insight→capability, etc.
- Governance: approve, reject, promote
- Human Supremacy: cannot promote without approval
- Reporting: compounding_report, improvement_from_executions
- Persistence: JSONL roundtrip
- Type coherence: canonical_types registration
- Routes: cockpit route mounting
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


class TestTypes(unittest.TestCase):
    def test_promotion_type_enum(self) -> None:
        from substrate.organism.compounding_engine import PromotionType

        assert PromotionType.OUTCOME_TO_INSIGHT.value == "outcome_to_insight"
        assert PromotionType.OPERATIONALIZATION_TO_INFRASTRUCTURE.value == (
            "operationalization_to_infrastructure"
        )
        assert len(PromotionType) == 4

    def test_promotion_status_enum(self) -> None:
        from substrate.organism.compounding_engine import PromotionStatus

        assert PromotionStatus.PROPOSED.value == "proposed"
        assert PromotionStatus.PROMOTED.value == "promoted"
        assert len(PromotionStatus) == 4

    def test_candidate_creation(self) -> None:
        from substrate.organism.compounding_engine import PromotionCandidate

        c = PromotionCandidate(source_id="test")
        assert c.source_id == "test"
        assert c.candidate_id.startswith("promo-")

    def test_candidate_to_dict(self) -> None:
        from substrate.organism.compounding_engine import PromotionCandidate

        c = PromotionCandidate(source_id="test")
        d = c.to_dict()
        assert d["source_id"] == "test"
        assert d["promotion_type"] == "outcome_to_insight"
        assert d["status"] == "proposed"

    def test_candidate_from_dict(self) -> None:
        from substrate.organism.compounding_engine import (
            PromotionCandidate,
            PromotionType,
        )

        d = {
            "candidate_id": "promo-abc",
            "promotion_type": "insight_to_capability",
            "source_id": "cap-1",
        }
        c = PromotionCandidate.from_dict(d)
        assert c.candidate_id == "promo-abc"
        assert c.promotion_type == PromotionType.INSIGHT_TO_CAPABILITY

    def test_invalid_type_defaults(self) -> None:
        from substrate.organism.compounding_engine import (
            PromotionCandidate,
            PromotionType,
        )

        c = PromotionCandidate.from_dict({"promotion_type": "invalid"})
        assert c.promotion_type == PromotionType.OUTCOME_TO_INSIGHT


class TestScoring(unittest.TestCase):
    def test_outcome_to_insight_below_threshold(self) -> None:
        from substrate.organism.compounding_engine import score_outcome_to_insight

        assert score_outcome_to_insight("deploy", 0.8, 2) == 0.0

    def test_outcome_to_insight_above_threshold(self) -> None:
        from substrate.organism.compounding_engine import score_outcome_to_insight

        score = score_outcome_to_insight("deploy", 0.9, 5)
        assert score > 0.0
        assert score <= 1.0

    def test_outcome_to_insight_low_success(self) -> None:
        from substrate.organism.compounding_engine import score_outcome_to_insight

        assert score_outcome_to_insight("deploy", 0.3, 10) == 0.0

    def test_insight_to_capability_below_evidence(self) -> None:
        from substrate.organism.compounding_engine import score_insight_to_capability

        assert score_insight_to_capability(1, 0.9, 1) == 0.0

    def test_insight_to_capability_above_threshold(self) -> None:
        from substrate.organism.compounding_engine import score_insight_to_capability

        score = score_insight_to_capability(5, 0.8, 3)
        assert score > 0.0

    def test_capability_to_operationalization_low_maturity(self) -> None:
        from substrate.organism.compounding_engine import (
            score_capability_to_operationalization,
        )

        assert score_capability_to_operationalization(0.1, 5, True) == 0.0

    def test_capability_to_operationalization_high_maturity(self) -> None:
        from substrate.organism.compounding_engine import (
            score_capability_to_operationalization,
        )

        score = score_capability_to_operationalization(0.8, 5, True)
        assert score > 0.5

    def test_op_to_infra_below_threshold(self) -> None:
        from substrate.organism.compounding_engine import (
            score_operationalization_to_infrastructure,
        )

        assert score_operationalization_to_infrastructure(1, 0.9, 2) == 0.0

    def test_op_to_infra_above_threshold(self) -> None:
        from substrate.organism.compounding_engine import (
            score_operationalization_to_infrastructure,
        )

        score = score_operationalization_to_infrastructure(5, 0.9, 2)
        assert score > 0.5


class TestDetection(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self._path = os.path.join(self._tmp, "candidates.jsonl")

    def _make_engine(self) -> "CompoundingEngine":
        from substrate.organism.compounding_engine import CompoundingEngine

        return CompoundingEngine(store_path=self._path)

    def test_detect_outcome_to_insight(self) -> None:
        eng = self._make_engine()
        outcomes = [{"action_type": "deploy", "status": "success", "id": f"o{i}"} for i in range(5)]
        candidates = eng.detect_outcome_to_insight(outcomes)
        assert len(candidates) >= 1
        assert candidates[0].confidence > 0.0

    def test_detect_outcome_no_pattern(self) -> None:
        eng = self._make_engine()
        outcomes = [
            {"action_type": f"action_{i}", "status": "success", "id": f"o{i}"} for i in range(5)
        ]
        candidates = eng.detect_outcome_to_insight(outcomes)
        assert len(candidates) == 0

    def test_detect_insight_to_capability(self) -> None:
        eng = self._make_engine()
        caps = [
            {
                "capability_id": "cap-1",
                "name": "deployment",
                "evidence": [
                    {
                        "evidence_id": "e1",
                        "quality_score": 0.8,
                        "evidence_type": "execution_outcome",
                    },
                    {
                        "evidence_id": "e2",
                        "quality_score": 0.9,
                        "evidence_type": "manual_attestation",
                    },
                    {
                        "evidence_id": "e3",
                        "quality_score": 0.7,
                        "evidence_type": "reliability_data",
                    },
                ],
            }
        ]
        candidates = eng.detect_insight_to_capability(caps)
        assert len(candidates) == 1

    def test_detect_capability_to_operationalization(self) -> None:
        eng = self._make_engine()
        caps = [
            {
                "capability_id": "cap-1",
                "name": "deployment",
                "maturity_score": 0.8,
                "reuse_potential": 5,
                "template_ids": ["tpl-1"],
            }
        ]
        candidates = eng.detect_capability_to_operationalization(caps)
        assert len(candidates) == 1

    def test_detect_op_to_infrastructure(self) -> None:
        eng = self._make_engine()
        ops = [
            {
                "operationalization_id": "op-1",
                "name": "deploy template",
                "reuse_count": 5,
                "success_rate": 0.9,
                "status": "production",
            }
        ]
        candidates = eng.detect_operationalization_to_infrastructure(ops)
        assert len(candidates) == 1


class TestGovernance(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self._path = os.path.join(self._tmp, "candidates.jsonl")

    def _make_engine(self) -> "CompoundingEngine":
        from substrate.organism.compounding_engine import CompoundingEngine

        return CompoundingEngine(store_path=self._path)

    def _create_candidate(self, eng: "CompoundingEngine") -> str:
        outcomes = [{"action_type": "deploy", "status": "success", "id": f"o{i}"} for i in range(5)]
        candidates = eng.detect_outcome_to_insight(outcomes)
        return candidates[0].candidate_id

    def test_approve(self) -> None:
        eng = self._make_engine()
        cid = self._create_candidate(eng)
        assert eng.approve(cid) is True
        assert eng.get(cid).status.value == "approved"

    def test_reject(self) -> None:
        eng = self._make_engine()
        cid = self._create_candidate(eng)
        assert eng.reject(cid, "not ready") is True
        c = eng.get(cid)
        assert c.status.value == "rejected"
        assert c.rejection_reason == "not ready"

    def test_promote_requires_approval(self) -> None:
        eng = self._make_engine()
        cid = self._create_candidate(eng)
        result = eng.promote(cid)
        assert "error" in result
        assert "approved" in result["error"]

    def test_promote_after_approval(self) -> None:
        eng = self._make_engine()
        cid = self._create_candidate(eng)
        eng.approve(cid)
        result = eng.promote(cid)
        assert result["promoted"] is True

    def test_cannot_approve_rejected(self) -> None:
        eng = self._make_engine()
        cid = self._create_candidate(eng)
        eng.reject(cid, "no")
        assert eng.approve(cid) is False

    def test_promote_nonexistent(self) -> None:
        eng = self._make_engine()
        result = eng.promote("nope")
        assert "error" in result


class TestReporting(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self._path = os.path.join(self._tmp, "candidates.jsonl")

    def _make_engine(self) -> "CompoundingEngine":
        from substrate.organism.compounding_engine import CompoundingEngine

        return CompoundingEngine(store_path=self._path)

    def test_compounding_report(self) -> None:
        eng = self._make_engine()
        outcomes = [{"action_type": "deploy", "status": "success", "id": f"o{i}"} for i in range(5)]
        eng.detect_outcome_to_insight(outcomes)
        report = eng.compounding_report()
        assert report["total_candidates"] >= 1
        assert report["period_days"] == 90

    def test_improvement_from_executions(self) -> None:
        eng = self._make_engine()
        outcomes = [{"action_type": "deploy", "status": "success", "id": f"o{i}"} for i in range(5)]
        candidates = eng.detect_outcome_to_insight(outcomes)
        eng.approve(candidates[0].candidate_id)
        eng.promote(candidates[0].candidate_id)
        report = eng.improvement_from_executions()
        assert report["recent_promotions"] == 1

    def test_summary(self) -> None:
        eng = self._make_engine()
        outcomes = [{"action_type": "deploy", "status": "success", "id": f"o{i}"} for i in range(5)]
        eng.detect_outcome_to_insight(outcomes)
        s = eng.summary()
        assert s["total_candidates"] >= 1
        assert s["pending_approval"] >= 1

    def test_list_candidates(self) -> None:
        from substrate.organism.compounding_engine import PromotionStatus

        eng = self._make_engine()
        outcomes = [{"action_type": "deploy", "status": "success", "id": f"o{i}"} for i in range(5)]
        eng.detect_outcome_to_insight(outcomes)
        all_c = eng.list_candidates()
        assert len(all_c) >= 1
        proposed = eng.list_candidates(status=PromotionStatus.PROPOSED)
        assert len(proposed) >= 1


class TestPersistence(unittest.TestCase):
    def test_jsonl_roundtrip(self) -> None:
        from substrate.organism.compounding_engine import CompoundingEngine

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "candidates.jsonl")
        e1 = CompoundingEngine(store_path=path)
        outcomes = [{"action_type": "deploy", "status": "success", "id": f"o{i}"} for i in range(5)]
        e1.detect_outcome_to_insight(outcomes)

        e2 = CompoundingEngine(store_path=path)
        assert len(e2.list_candidates()) >= 1

    def test_malformed_jsonl_skipped(self) -> None:
        from substrate.organism.compounding_engine import CompoundingEngine

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "candidates.jsonl")
        with open(path, "w") as f:
            f.write("bad json\n")
            f.write(json.dumps({"candidate_id": "promo-ok", "source_id": "s1"}) + "\n")
        e = CompoundingEngine(store_path=path)
        assert len(e.list_candidates()) == 1


class TestTypeCoherence(unittest.TestCase):
    def test_canonical_types_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        for name in [
            "PromotionType",
            "PromotionStatus",
            "PromotionCandidate",
            "CompoundingEngine",
        ]:
            assert name in CANONICAL_TYPES, f"{name} not in canonical_types"
            assert "substrate.organism.compounding_engine" in CANONICAL_TYPES[name]


class TestRoutes(unittest.TestCase):
    def test_routes_importable(self) -> None:
        from transports.api.cockpit_compounding_routes import compounding_router

        assert compounding_router is not None

    def test_cockpit_mounts_compounding_routes(self) -> None:
        import transports.api.cockpit as c

        route_paths = [r.path for r in c.router.routes]
        assert any("/compounding/candidates" in p for p in route_paths)
        assert any("/compounding/summary" in p for p in route_paths)
        assert any("/compounding/report" in p for p in route_paths)


if __name__ == "__main__":
    unittest.main()
