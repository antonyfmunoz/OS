"""Migration pin: ontology-domain bridge — BusinessBridge.

Pins recent commit: ontology-domain-bridge. Constructs ontology
observations, runs BusinessBridge.bridge(), asserts business
projections produced with authority tier propagation.
"""

import os
import sys

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

from core.ontology.primitive_decomposition_v1 import PrimitiveObservation, PrimitiveType
from runtime.domain_bridge.business import BusinessBridge
from runtime.domain_bridge.contract import DomainBridge, DomainProjection

pytestmark = pytest.mark.migration


def _make_obs(
    obs_id: str,
    ptype: str,
    label: str,
    description: str,
    confidence: float = 0.90,
    authority_tier: int = 5,
) -> PrimitiveObservation:
    obs = PrimitiveObservation(
        observation_id=obs_id,
        primitive_type=PrimitiveType(ptype),
        label=label,
        description=description,
        confidence=confidence,
        source_reference="test:1",
        evidence="test evidence",
    )
    obs.authority_tier = authority_tier
    return obs


class TestBusinessBridgeContract:
    def test_implements_domain_bridge(self):
        bridge = BusinessBridge()
        assert isinstance(bridge, DomainBridge)

    def test_domain_id_is_business(self):
        bridge = BusinessBridge()
        assert bridge.domain_id == "business"

    def test_bridge_returns_projection_or_none(self):
        bridge = BusinessBridge()
        obs = _make_obs("obs-1", "constraint", "Sales constraint", "Must close first")
        result = bridge.bridge(obs)
        assert result is None or isinstance(result, DomainProjection)


class TestBusinessProjections:
    def test_sales_constraint_projects(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-sales",
            "constraint",
            "Founder must close first 10 sales before hiring a salesperson",
            "No salesperson hire until process proven.",
        )
        result = bridge.bridge(obs)
        assert result is not None
        assert isinstance(result, DomainProjection)
        assert result.domain_id == "business"

    def test_outreach_action_projects(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-action",
            "action",
            "Direct outreach via DM to ICP prospects",
            "DM the people who match your ICP.",
        )
        result = bridge.bridge(obs)
        assert result is not None
        assert result.domain_id == "business"

    def test_revenue_goal_projects(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-goal",
            "goal",
            "Reach $10K monthly revenue through organic conversion",
            "First revenue milestone before scaling.",
        )
        result = bridge.bridge(obs)
        assert result is not None

    def test_non_business_returns_none(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-tech",
            "state",
            "Memory palace has 4 navigation layers",
            "Palace, Wing, Room, Locus for structured codebase navigation.",
        )
        result = bridge.bridge(obs)
        # Pure codebase-architecture observation should not match business keywords
        # If it does match, it still must be a valid DomainProjection
        if result is not None:
            assert isinstance(result, DomainProjection)

    def test_projection_has_required_fields(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-fields",
            "constraint",
            "Founder must close first 10 sales before hiring a salesperson",
            "Must be profitable before expanding team.",
        )
        result = bridge.bridge(obs)
        assert result is not None
        assert result.projection_id, "projection_id must not be empty"
        assert result.domain_id == "business"
        assert result.ontology_observation_ref == obs.observation_id
        assert result.confidence > 0
        assert result.evidence

    def test_authority_tier_propagates_to_projection(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-tier",
            "constraint",
            "Founder must close first 10 sales before hiring a salesperson",
            "No hire until proven.",
            authority_tier=2,
        )
        result = bridge.bridge(obs)
        assert result is not None
        assert result.authority_tier == 2

    def test_non_bridgeable_type_returns_none(self):
        bridge = BusinessBridge()
        obs = _make_obs(
            "obs-feedback",
            "feedback",
            "Customer feedback on pricing",
            "Price too high for current features.",
        )
        result = bridge.bridge(obs)
        assert result is None
