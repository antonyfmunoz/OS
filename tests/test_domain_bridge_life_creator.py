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

from substrate.ontology.domains.contract import DomainBridge, DomainProjection
from substrate.ontology.domains.life import LifeBridge
from substrate.ontology.domains.creator import CreatorBridge
from substrate.ontology.domains.registry import default_registry
from substrate.ontology.primitives import PrimitiveObservation, PrimitiveType


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


class TestLifeBridgeMissions:
    def test_daily_mission_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-mission1",
            "action",
            "Complete daily mission: 10K steps and journal",
            "Daily quest assigned by NOVA system.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "missions"
        assert proj.domain_primitive_type == "daily_mission"

    def test_shadow_mission_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-shadow1",
            "action",
            "Shadow work mission: confront shadow of procrastination",
            "Shadow integration exercise for personal growth.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "missions"
        assert proj.domain_primitive_type == "shadow_mission"

    def test_project_mission_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-projmission1",
            "goal",
            "Project mission: build portfolio website milestone",
            "Project quest with deliverable checkpoint.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "missions"
        assert proj.domain_primitive_type == "project_mission"


class TestLifeBridgeThreads:
    def test_transformation_thread_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-thread1",
            "state",
            "Transformation thread: introvert to confident speaker",
            "Character arc tracking growth in public speaking.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "threads"
        assert proj.domain_primitive_type == "transformation_thread"

    def test_skill_thread_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-thread2",
            "goal",
            "Skill thread: mastery thread in data engineering",
            "Competence thread tracking skill progression.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "threads"
        assert proj.domain_primitive_type == "skill_thread"


class TestLifeBridgeRituals:
    def test_morning_ritual_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-ritual1",
            "action",
            "Execute morning ritual at sunrise",
            "AM ritual and morning protocol for daily activation.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "rituals"
        assert proj.domain_primitive_type == "morning_ritual"

    def test_weekly_ritual_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-ritual2",
            "action",
            "Weekly review ritual: assess progress and plan next week",
            "Sunday review and weekly reflection protocol.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "rituals"
        assert proj.domain_primitive_type == "weekly_ritual"

    def test_yearly_ritual_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-ritual3",
            "action",
            "Year-end review and annual reflection on 2026",
            "Yearly ritual for assessing life trajectory.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "rituals"
        assert proj.domain_primitive_type == "yearly_ritual"


class TestLifeBridgeReflections:
    def test_journal_entry_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-reflect1",
            "action",
            "Write daily journal entry about today's wins",
            "Journaling practice for written reflection.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "reflections"
        assert proj.domain_primitive_type == "journal_entry"

    def test_chronilog_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-chronilog1",
            "state",
            "Chronilog entry: life chronicle update for Q2 2026",
            "Timeline entry documenting life chronicle progression.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "reflections"
        assert proj.domain_primitive_type == "chronilog"


class TestLifeBridgeGamification:
    def test_xp_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-xp1",
            "resource",
            "Earn XP for completing morning training session",
            "Experience points reward for habit completion.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "gamification"
        assert proj.domain_primitive_type == "xp_system"

    def test_streak_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-streak1",
            "state",
            "30 day streak on meditation practice",
            "Consecutive days maintaining streak count.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "gamification"
        assert proj.domain_primitive_type == "streaks"

    def test_level_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-level1",
            "state",
            "Player level 12 — rank up to next tier",
            "Level progression in the gamification system.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "gamification"
        assert proj.domain_primitive_type == "levels"


class TestLifeBridgePlayerProfile:
    def test_archetype_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-archetype1",
            "state",
            "Archetype calibration: warrior-scholar player archetype",
            "Character class assignment based on behavior patterns.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "player_profile"
        assert proj.domain_primitive_type == "archetype"

    def test_character_stats_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-stats1",
            "state",
            "Character stats: strength 8, wisdom 6, charisma 7",
            "Player stats from character sheet assessment.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "player_profile"
        assert proj.domain_primitive_type == "character_stats"


class TestLifeBridgeSystems:
    def test_energy_management_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-energy1",
            "state",
            "Energy management: track circadian energy levels",
            "Energy tracking and optimization throughout the day.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "systems"
        assert proj.domain_primitive_type == "energy_management"

    def test_focus_management_maps(self):
        bridge = LifeBridge()
        obs = _make_obs(
            "obs-focus1",
            "action",
            "Deep work focus session: 90 min flow state block",
            "Focus management for attention and productivity.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["life_domain"] == "systems"
        assert proj.domain_primitive_type == "focus_management"


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


class TestCreatorBridgeProducts:
    def test_course_maps_to_products(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-course1",
            "resource",
            "Launch cohort-based course on Kajabi",
            "Online course curriculum with 8 modules.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "products"
        assert proj.domain_primitive_type == "course"

    def test_digital_download_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-download1",
            "resource",
            "Sell template pack as digital download on Gumroad",
            "Preset pack and printable bundle for creators.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "products"
        assert proj.domain_primitive_type == "digital_download"

    def test_event_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-event1",
            "action",
            "Host live event workshop on content strategy",
            "Virtual summit masterclass for audience.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "products"
        assert proj.domain_primitive_type == "event"

    def test_service_offer_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-service1",
            "resource",
            "Coaching package: service offer with retainer",
            "Service productize for consulting clients.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "products"
        assert proj.domain_primitive_type == "service_offer"


class TestCreatorBridgeCommunities:
    def test_tiers_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-tier1",
            "resource",
            "Set up premium tier and VIP tier membership",
            "Community tier with access tier differentiation.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "communities"
        assert proj.domain_primitive_type == "tiers"

    def test_ugc_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-ugc1",
            "goal",
            "Launch user generated content campaign from members",
            "UGC and member spotlight to boost community content.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "communities"
        assert proj.domain_primitive_type == "ugc"

    def test_roles_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-roles1",
            "action",
            "Assign community role: moderator and admin role",
            "Community manager setup for member role permissions.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "communities"
        assert proj.domain_primitive_type == "roles"


class TestCreatorBridgeCampaigns:
    def test_launch_campaign_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-launch1",
            "action",
            "Execute launch campaign for product launch sequence",
            "Launch funnel with email nurture and landing page.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "campaigns"
        assert proj.domain_primitive_type == "launch_campaign"

    def test_email_campaign_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-emailcamp1",
            "action",
            "Build drip campaign and welcome sequence for email list",
            "Email campaign with nurture sequence automation.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "campaigns"
        assert proj.domain_primitive_type == "email_campaign"

    def test_promotion_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-promo1",
            "action",
            "Run flash sale promotion with discount code",
            "Limited offer coupon for black friday.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "campaigns"
        assert proj.domain_primitive_type == "promotion"


class TestCreatorBridgeStorefronts:
    def test_storefront_design_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-store1",
            "action",
            "Design storefront with product page and sales page",
            "Landing page and checkout page for digital products.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "storefronts"
        assert proj.domain_primitive_type == "storefront_design"

    def test_entitlements_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-entitle1",
            "state",
            "Configure entitlement rules: gated content paywall",
            "Access control and drip access for content lock.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "storefronts"
        assert proj.domain_primitive_type == "entitlements"

    def test_automations_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-auto1",
            "action",
            "Set up workflow automation via Zapier and Make.com",
            "Trigger automation for auto-deliver on purchase.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "storefronts"
        assert proj.domain_primitive_type == "automations"

    def test_series_collections_maps(self):
        bridge = CreatorBridge()
        obs = _make_obs(
            "obs-series1",
            "resource",
            "Create video series and content series collection",
            "Playlist and course series for organized content.",
        )
        proj = bridge.bridge(obs)
        assert proj is not None
        assert proj.properties["creator_domain"] == "storefronts"
        assert proj.domain_primitive_type == "series_collections"


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
