"""Life domain bridge — structural mapping from ontology to life primitives.

V1: keyword-based structural rules only. No LLM dependency.
Maps ontology observations to LyfeOS life domain primitives covering
health, habits, relationships, finance, growth, environment, missions,
rituals, reflections, gamification, player profile, and archetypes.
"""

from __future__ import annotations

from understanding.ontology.primitive_decomposition_v1 import PrimitiveObservation

from .contract import DomainProjection, make_projection_id
from .registry import default_registry


_DOMAIN_KEYWORD_MAP: dict[str, dict[str, list[str]]] = {
    "health": {
        "physical_training": [
            "workout",
            "training",
            "exercise",
            "gym",
            "strength training",
            "cardio",
            "running",
            "lifting",
            "body composition",
            "progressive overload",
        ],
        "nutrition": [
            "nutrition",
            "diet",
            "meal prep",
            "calories",
            "macros",
            "protein",
            "supplements",
            "fasting",
            "whole foods",
        ],
        "sleep": [
            "sleep",
            "sleep schedule",
            "circadian",
            "recovery",
            "rest day",
            "sleep hygiene",
            "melatonin",
        ],
        "biomarkers": [
            "bloodwork",
            "biomarker",
            "testosterone",
            "cortisol",
            "blood pressure",
            "heart rate",
            "hrv",
            "resting heart rate",
            "vo2 max",
        ],
        "_domain_generic": [
            "health",
            "fitness",
            "wellness",
            "longevity",
            "biohacking",
        ],
    },
    "habits": {
        "morning_routine": [
            "morning routine",
            "morning ritual",
            "wake up",
            "first hour",
            "morning habit",
        ],
        "evening_routine": [
            "evening routine",
            "night routine",
            "wind down",
            "bedtime",
            "evening ritual",
        ],
        "habit_stacking": [
            "habit stack",
            "habit stacking",
            "chain habit",
            "anchor habit",
            "cue routine reward",
        ],
        "tracking": [
            "habit tracker",
            "streak",
            "consistency",
            "daily tracking",
            "accountability",
        ],
        "_domain_generic": [
            "habit",
            "routine",
            "discipline",
            "daily practice",
            "ritual",
        ],
    },
    "relationships": {
        "inner_circle": [
            "inner circle",
            "close friend",
            "best friend",
            "trusted advisor",
            "mentor",
            "accountability partner",
        ],
        "romantic": [
            "partner",
            "relationship",
            "dating",
            "marriage",
            "significant other",
        ],
        "family": [
            "family",
            "parent",
            "sibling",
            "children",
            "mother",
            "father",
        ],
        "networking": [
            "network",
            "networking",
            "community",
            "mastermind",
            "peer group",
            "social capital",
        ],
        "_domain_generic": [
            "social",
            "connection",
            "people",
            "circle",
        ],
    },
    "personal_finance": {
        "savings_rate": [
            "savings rate",
            "save rate",
            "emergency fund",
            "savings goal",
            "pay yourself first",
        ],
        "investments": [
            "investment",
            "portfolio",
            "compound interest",
            "index fund",
            "real estate",
            "asset allocation",
            "net worth",
        ],
        "debt_management": [
            "debt",
            "student loan",
            "credit card",
            "debt free",
            "debt snowball",
            "payoff",
        ],
        "_domain_generic": [
            "personal finance",
            "money management",
            "financial freedom",
            "wealth building",
        ],
    },
    "personal_growth": {
        "learning": [
            "learning",
            "reading",
            "books",
            "course",
            "skill acquisition",
            "deliberate practice",
            "study",
        ],
        "mindfulness": [
            "meditation",
            "mindfulness",
            "journaling",
            "reflection",
            "gratitude",
            "present moment",
            "breathwork",
        ],
        "goal_setting": [
            "goal setting",
            "vision board",
            "life plan",
            "quarterly review",
            "annual review",
            "north star",
            "life audit",
        ],
        "_domain_generic": [
            "personal development",
            "self improvement",
            "growth mindset",
            "level up",
        ],
    },
    "environment": {
        "workspace": [
            "workspace",
            "desk setup",
            "home office",
            "work environment",
            "ergonomic",
        ],
        "living_space": [
            "apartment",
            "house",
            "living space",
            "declutter",
            "minimalism",
            "organization",
        ],
        "location": [
            "city",
            "relocate",
            "move to",
            "location independence",
            "travel",
            "digital nomad",
        ],
        "_domain_generic": [
            "environment",
            "surroundings",
            "space",
            "setup",
        ],
    },
    "missions": {
        "daily_mission": [
            "daily mission",
            "daily quest",
            "daily challenge",
            "today's mission",
            "day mission",
        ],
        "skill_mission": [
            "skill mission",
            "skill quest",
            "skill challenge",
            "skill building mission",
            "learn skill",
        ],
        "project_mission": [
            "project mission",
            "project quest",
            "project milestone",
            "project challenge",
            "build project",
        ],
        "belief_mission": [
            "belief mission",
            "belief challenge",
            "mindset mission",
            "limiting belief",
            "belief rewrite",
        ],
        "shadow_mission": [
            "shadow mission",
            "shadow work",
            "shadow challenge",
            "confront shadow",
            "shadow integration",
        ],
        "reflection_mission": [
            "reflection mission",
            "reflection quest",
            "self-reflection challenge",
            "introspection mission",
        ],
        "system_mission": [
            "system mission",
            "system quest",
            "system building",
            "system optimization",
            "automate system",
        ],
        "_domain_generic": [
            "mission",
            "quest",
            "challenge",
            "assignment",
        ],
    },
    "threads": {
        "transformation_thread": [
            "transformation thread",
            "transformation arc",
            "character arc",
            "growth thread",
            "evolution thread",
        ],
        "skill_thread": [
            "skill thread",
            "skill arc",
            "mastery thread",
            "competence thread",
        ],
        "identity_thread": [
            "identity thread",
            "identity arc",
            "who i am becoming",
            "identity shift",
        ],
        "_domain_generic": [
            "thread",
            "arc",
            "progression",
            "journey",
        ],
    },
    "rituals": {
        "morning_ritual": [
            "morning ritual",
            "am ritual",
            "sunrise ritual",
            "morning protocol",
            "dawn practice",
        ],
        "evening_ritual": [
            "evening ritual",
            "pm ritual",
            "sunset ritual",
            "evening protocol",
            "wind-down ritual",
        ],
        "weekly_ritual": [
            "weekly ritual",
            "weekly review",
            "weekly reflection",
            "sunday review",
            "weekly reset",
        ],
        "monthly_ritual": [
            "monthly ritual",
            "monthly review",
            "monthly reflection",
            "month-end review",
            "monthly reset",
        ],
        "yearly_ritual": [
            "yearly ritual",
            "annual review",
            "year-end review",
            "annual reflection",
            "yearly reset",
        ],
        "_domain_generic": [
            "ritual",
            "ceremony",
            "protocol",
            "practice",
        ],
    },
    "reflections": {
        "journal_entry": [
            "journal entry",
            "journaling",
            "daily journal",
            "written reflection",
            "diary entry",
        ],
        "insight": [
            "insight",
            "realization",
            "lesson learned",
            "epiphany",
            "breakthrough",
        ],
        "chronilog": [
            "chronilog",
            "life log",
            "timeline entry",
            "chronicle",
            "life chronicle",
        ],
        "_domain_generic": [
            "reflection",
            "reflect",
            "introspection",
            "self-awareness",
        ],
    },
    "gamification": {
        "xp_system": [
            "xp",
            "experience points",
            "earn xp",
            "xp reward",
            "level up xp",
        ],
        "streaks": [
            "streak",
            "day streak",
            "consecutive days",
            "streak count",
            "maintain streak",
        ],
        "levels": [
            "level",
            "player level",
            "rank up",
            "tier up",
            "level progression",
        ],
        "achievements": [
            "achievement",
            "badge",
            "trophy",
            "unlock",
            "milestone badge",
        ],
        "_domain_generic": [
            "gamification",
            "gamify",
            "game mechanics",
            "points",
            "rewards",
        ],
    },
    "player_profile": {
        "character_stats": [
            "character stats",
            "core stats",
            "stat sheet",
            "character sheet",
            "player stats",
        ],
        "archetype": [
            "archetype",
            "player archetype",
            "personality archetype",
            "archetype calibration",
            "character class",
        ],
        "embodiment": [
            "embodiment",
            "embodied practice",
            "somatic",
            "body-mind",
            "embodiment progression",
        ],
        "_domain_generic": [
            "player profile",
            "character",
            "avatar",
            "player",
        ],
    },
    "systems": {
        "energy_management": [
            "energy management",
            "energy level",
            "energy tracking",
            "energy optimization",
            "circadian energy",
        ],
        "focus_management": [
            "focus management",
            "deep work",
            "flow state",
            "focus session",
            "attention management",
        ],
        "recovery_system": [
            "recovery system",
            "active recovery",
            "deload",
            "recovery protocol",
            "rest protocol",
        ],
        "_domain_generic": [
            "system",
            "operating system",
            "life system",
            "personal system",
        ],
    },
}

_BRIDGEABLE_ONTOLOGY_TYPES = frozenset(
    [
        "constraint",
        "action",
        "goal",
        "state",
        "resource",
    ]
)


class LifeBridge:
    """Structural keyword bridge from ontology observations to life domain primitives."""

    @property
    def domain_id(self) -> str:
        return "life"

    def describes(self) -> str:
        return (
            "Maps ontology observations to life domain primitives "
            "(health, habits, relationships, personal_finance, personal_growth, "
            "environment, missions, threads, rituals, reflections, gamification, "
            "player_profile, systems) using structural keyword matching."
        )

    def bridge(self, observation: PrimitiveObservation) -> DomainProjection | None:
        if observation.primitive_type.value not in _BRIDGEABLE_ONTOLOGY_TYPES:
            return None

        text = f"{observation.label} {observation.description}".lower()

        best_domain: str | None = None
        best_primitive: str | None = None
        best_score = 0

        for domain, primitives in _DOMAIN_KEYWORD_MAP.items():
            for prim_id, keywords in primitives.items():
                score = sum(1 for kw in keywords if kw in text)
                if score > best_score:
                    best_score = score
                    best_domain = domain
                    best_primitive = prim_id

        if best_score == 0 or best_domain is None:
            return None

        if best_primitive and best_primitive.startswith("_domain_"):
            best_primitive = None

        confidence = min(observation.confidence, 0.70 + (best_score * 0.05))

        return DomainProjection(
            projection_id=make_projection_id(),
            domain_id=self.domain_id,
            domain_primitive_type=best_primitive or f"domain:{best_domain}",
            label=f"[life:{best_domain}] {observation.label}"[:80],
            description=observation.description,
            properties={
                "source_ontology_type": observation.primitive_type.value,
                "life_domain": best_domain,
                "life_primitive_id": best_primitive,
                "keyword_match_score": best_score,
            },
            ontology_observation_ref=observation.observation_id,
            confidence=confidence,
            evidence=observation.evidence,
            authority_tier=observation.authority_tier,
        )


_life_bridge = LifeBridge()
default_registry.register(_life_bridge)
