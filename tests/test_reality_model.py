import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, _ROOT)

import pytest
from uuid import uuid4
from substrate.reality_model.canonical import CanonicalRealityModel, CanonicalPattern
from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation


class TestCanonicalRealityModel:
    @pytest.fixture
    def canonical(self, tmp_path):
        return CanonicalRealityModel(store_path=tmp_path / "canonical.json")

    def test_store_pattern(self, canonical):
        pattern = CanonicalPattern(
            name="test-pattern",
            domain="business",
            description="A test pattern",
            evidence_count=5,
            confidence=0.9,
        )
        pattern_id = canonical.store(pattern)
        assert pattern_id is not None

    def test_retrieve_pattern(self, canonical):
        pattern = CanonicalPattern(
            name="retrieval-test",
            domain="general",
            description="Test retrieval",
            evidence_count=3,
            confidence=0.85,
        )
        canonical.store(pattern)
        found = canonical.get_by_name("retrieval-test")
        assert found is not None
        assert found.name == "retrieval-test"

    def test_list_by_domain(self, canonical):
        for i in range(3):
            canonical.store(CanonicalPattern(
                name=f"biz-{i}", domain="business",
                description=f"Business pattern {i}",
                evidence_count=i + 1, confidence=0.8,
            ))
        canonical.store(CanonicalPattern(
            name="life-0", domain="life",
            description="Life pattern",
            evidence_count=2, confidence=0.7,
        ))
        biz = canonical.list_by_domain("business")
        assert len(biz) == 3

    def test_canonical_is_immutable_without_governance(self, canonical):
        pattern = CanonicalPattern(
            name="immutable-test", domain="general",
            description="Should not change",
            evidence_count=10, confidence=0.95,
        )
        canonical.store(pattern)
        with pytest.raises(ValueError, match="governance"):
            canonical.update("immutable-test", description="changed", governance_approved=False)


class TestInstanceRealityModel:
    @pytest.fixture
    def instance(self):
        return InstanceRealityModel(user_id="test-user", org_id="test-org")

    def test_record_observation(self, instance):
        obs = InstanceObservation(
            content="User prefers morning meetings",
            domain="scheduling",
            confidence=0.8,
            source_signal_id=uuid4(),
        )
        obs_id = instance.record(obs)
        assert obs_id is not None

    def test_query_observations(self, instance):
        instance.record(InstanceObservation(
            content="User is in Portland timezone",
            domain="general",
            confidence=0.95,
            source_signal_id=uuid4(),
        ))
        results = instance.query("Portland")
        assert len(results) >= 1

    def test_instance_is_user_scoped(self, instance):
        assert instance.user_id == "test-user"
        assert instance.org_id == "test-org"
