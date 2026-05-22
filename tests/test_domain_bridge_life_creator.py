"""Tests for life and creator domain bridges."""

import os
import sys

import pytest

_worktree = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _worktree not in sys.path:
    sys.path.insert(0, _worktree)
for mod_name in list(sys.modules):
    if mod_name.startswith("understanding"):
        del sys.modules[mod_name]

from understanding.domains.contract import DomainBridge, DomainProjection
from understanding.domains.life import LifeBridge
from understanding.domains.creator import CreatorBridge
from understanding.domains.registry import default_registry
from understanding.ontology.primitive_decomposition_v1 import PrimitiveObservation, PrimitiveType


def _make_obs(
    obs_id: str,
    ptype: str,
    label: str,
    description: str,
    confidence: float = 0.90,
) -> PrimitiveObservation:
    return PrimitiveObservation(
        observation_id=obs_id,
        primitive_type=PrimitiveType(ptype),
        label=label,
        description=description,
        confidence=confidence,
        source_reference="test:1",
        evidence="test evidence",
    )


class TestLifeBridgeProtocol:
    def test_implements_protocol(self):
        bridge = LifeBridge()
        assert isinstance(bridge, DomainBridge)
        assert bridge.domain_id == "life"
        assert len(bridge.describes()) > 0

    def test_registered_in_default_registry(self):
        bridge = default_registry.get_by_id("life")
        assert bridge is not None
        assert bridge.domain_id == "life"


class TestLifeBridgeMapping:
    def test_workout_maps_to_physical_training(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-workout1",
            "action",
            "Complete 4x strength training workout per week",
            "Progressive overload training program for muscle growth.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.domain_id == "life"
        assert proj.domain_primitive_type == "physical_training"
        assert proj.properties["life_domain"] == "health"

    def test_sleep_maps_to_sleep(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-sleep1",
            "goal",
            "Maintain consistent sleep schedule of 7 hours",
            "Sleep hygiene and circadian rhythm optimization.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.domain_primitive_type == "sleep"
        assert proj.properties["life_domain"] == "health"

    def test_morning_routine_maps_to_habits(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-morning1",
            "action",
            "Execute morning routine: wake up at 5am, journal, train",
            "Morning ritual for consistent daily productivity.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "habits"

    def test_investment_maps_to_personal_finance(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-invest1",
            "resource",
            "Diversified investment portfolio allocation strategy",
            "Asset allocation across index fund and real estate.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "personal_finance"
        assert proj.domain_primitive_type == "investments"

    def test_meditation_maps_to_personal_growth(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-meditate1",
            "action",
            "Daily meditation and mindfulness practice",
            "Journaling and breathwork for reflection.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "personal_growth"
        assert proj.domain_primitive_type == "mindfulness"


class TestLifeBridgeNoMatch:
    def test_non_life_observation(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-tech1",
            "state",
            "Kubernetes cluster has 5 nodes",
            "The production cluster uses GKE with autoscaling.",
        )
        result = bridge.bridge(obs)
        assert result is None

    def test_time_type_not_bridgeable(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-time1",
            "time",
            "Morning starts at 5am",
            "The daily schedule begins early.",
        )
        result = bridge.bridge(obs)
        assert result is None


class TestLifeBridgeConfidence:
    def test_confidence_does_not_exceed_source(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-conf1",
            "goal",
            "Reach 10% body fat through nutrition and training",
            "Cutting through calorie deficit and protein intake.",
            confidence=0.55,
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.confidence <= obs.confidence


class TestCreatorBridgeProtocol:
    def test_implements_protocol(self):
        bridge = CreatorBridge()
        assert isinstance(bridge, DomainBridge)
        assert bridge.domain_id == "creator"
        assert len(bridge.describes()) > 0

    def test_registered_in_default_registry(self):
        bridge = default_registry.get_by_id("creator")
        assert bridge is not None
        assert bridge.domain_id == "creator"


class TestCreatorBridgeMapping:
    def test_youtube_maps_to_long_form(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-yt1",
            "action",
            "Publish weekly YouTube video deep dive",
            "Long form content on entrepreneurship topics.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.domain_id == "creator"
        assert proj.domain_primitive_type == "long_form"
        assert proj.properties["creator_domain"] == "content"

    def test_tiktok_maps_to_short_form(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-tt1",
            "action",
            "Post daily TikTok reel clips from podcast",
            "Short form vertical video repurposing strategy.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.domain_primitive_type == "short_form"
        assert proj.properties["creator_domain"] == "content"

    def test_community_maps_to_audience(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-comm1",
            "goal",
            "Build Discord server community to 1000 members",
            "Community building through engagement and tribe culture.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "audience"
        assert proj.domain_primitive_type == "community_building"

    def test_sponsorship_maps_to_monetization(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-spon1",
            "resource",
            "Brand deal sponsorship revenue from content",
            "Paid promotion and brand partnership income.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "monetization"
        assert proj.domain_primitive_type == "sponsorship"

    def test_brand_identity_maps_to_brand(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-brand1",
            "state",
            "Personal brand identity and visual positioning",
            "Brand archetype and brand aesthetic consistency.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "brand"
        assert proj.domain_primitive_type == "identity"

    def test_newsletter_maps_to_email_list(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-news1",
            "goal",
            "Grow newsletter email list to 10k subscribers",
            "Email marketing subscriber list building strategy.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "audience"
        assert proj.domain_primitive_type == "email_list"


class TestCreatorBridgeNoMatch:
    def test_non_creator_observation(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-db1",
            "state",
            "Database has 3 replicas in us-east",
            "PostgreSQL cluster with read replicas for HA.",
        )
        result = bridge.bridge(obs)
        assert result is None

    def test_signal_type_not_bridgeable(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-sig1",
            "signal",
            "New follower milestone reached",
            "Instagram followers crossed 10K.",
        )
        result = bridge.bridge(obs)
        assert result is None


class TestCreatorBridgeConfidence:
    def test_confidence_does_not_exceed_source(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-conf2",
            "action",
            "Repurpose podcast into short form clips",
            "Content repurposing workflow from long form.",
            confidence=0.50,
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.confidence <= obs.confidence


class TestRegistryHasAllThreeDomains:
    def test_all_three_registered(self):
        ids = {b.domain_id for b in default_registry.get_all()}
        assert "business" in ids
        assert "life" in ids
        assert "creator" in ids
