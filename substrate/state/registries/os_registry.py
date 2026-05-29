"""
OSRegistry — formal registry for all three OS modules.

Defines what each OS is, what it owns, what agents and primitives
it activates, and how it injects into the cognitive loop.

This is Layer 2 of the UMH protocol architecture. Each OS module
injects context only when the user is subscribed. OS modules share
the Layer 0 and Layer 1 substrate but do not interfere with each other.

Usage:
    from substrate.state.registries.os_registry import OSRegistryManager, OSModule

    orm = OSRegistryManager()
    active = orm.get_active_modules()
    prompt_block = orm.format_for_prompt(['entrepreneur_os'])
"""

from dataclasses import dataclass, field
from enum import Enum


# ─── OSModule enum ────────────────────────────────────────────────────────────


class OSModule(Enum):
    ENTREPRENEUR = "entrepreneur_os"
    CREATOR = "creator_os"
    LYFE = "lyfe_os"


# ─── OSModuleConfig ───────────────────────────────────────────────────────────


@dataclass
class OSModuleConfig:
    id: str
    name: str
    description: str
    status: str  # 'active' | 'coming' | 'planned'
    version: str

    # What this OS owns
    domain: str
    primary_question: str  # the question this OS answers

    # Agents this OS activates
    agents: list[str]

    # Primitive domains this OS uses
    primitive_domains: list[str]

    # Skills this OS provides
    skill_categories: list[str]

    # What injects into cognitive loop for users subscribed to this OS
    context_injections: list[str]

    # Cross-OS connections — what this OS shares with others
    shares_with: dict[str, list[str]] = field(default_factory=dict)


# ─── OS_REGISTRY ──────────────────────────────────────────────────────────────

OS_REGISTRY: dict[OSModule, OSModuleConfig] = {
    OSModule.ENTREPRENEUR: OSModuleConfig(
        id="entrepreneur_os",
        name="EntrepreneurOS",
        description=(
            "Run your business. Stage-aware intelligence "
            "that knows what applies at your exact stage "
            "and filters everything else out."
        ),
        status="active",
        version="1.0",
        domain="business",
        primary_question=("What is the highest leverage action to grow my business right now?"),
        agents=[
            "executive_assistant",
            "portfolio_advisor",
            "lyfe_institute_ceo",
            "empyrean_ceo",
            "lyfe_developer_agent",
            "empyrean_developer_agent",
        ],
        primitive_domains=[
            "sales",
            "marketing",
            "hiring",
            "finance",
            "growth",
            "validation",
        ],
        skill_categories=[
            "Sales",
            "Marketing",
            "CustomerSuccess",
            "Research",
            "Ops",
        ],
        context_injections=[
            "bis_venture_context",
            "primitive_context",
            "template_context",
            "evolution_context",
            "hierarchy_context",
            "reality_context",
        ],
        shares_with={
            "creator_os": [
                "audience_intelligence",
                "icp_signals",
            ],
            "lyfe_os": [
                "energy_state",
                "focus_capacity",
                "meeting_schedule",
            ],
        },
    ),
    OSModule.CREATOR: OSModuleConfig(
        id="creator_os",
        name="CreatorOS",
        description=(
            "Run your brand and content. "
            "Audience intelligence, content strategy, "
            "and distribution — all stage-aware."
        ),
        status="coming",
        version="0.1",
        domain="content",
        primary_question=("What content should I create today to grow the right audience?"),
        agents=[
            "creator_ea",
            "content_strategist",
            "audience_analyst",
            "brand_guardian",
            "distribution_agent",
        ],
        primitive_domains=[
            "content",
            "audience",
            "brand",
            "distribution",
            "monetization",
        ],
        skill_categories=[
            "Content",
            "Audience",
            "Brand",
            "Distribution",
        ],
        context_injections=[
            "content_calendar_context",
            "audience_intelligence",
            "brand_context",
            "content_primitive_context",
            "distribution_context",
        ],
        shares_with={
            "entrepreneur_os": [
                "offer_context",
                "icp_definition",
                "stage_guidance",
            ],
            "lyfe_os": [
                "energy_state",
                "creative_capacity",
            ],
        },
    ),
    OSModule.LYFE: OSModuleConfig(
        id="lyfe_os",
        name="LYFEOS",
        description=(
            "Run your life. Health, energy, "
            "relationships, habits — all optimized "
            "for peak performance and fulfillment."
        ),
        status="coming",
        version="0.1",
        domain="life",
        primary_question=("What should I do today to maximize my energy, health, and fulfillment?"),
        agents=[
            "life_ea",
            "health_agent",
            "energy_optimizer",
            "relationship_agent",
            "habit_tracker",
            "growth_coach",
        ],
        primitive_domains=[
            "health",
            "energy",
            "relationships",
            "habits",
            "mindset",
            "purpose",
        ],
        skill_categories=[
            "Health",
            "Energy",
            "Relationships",
            "Habits",
            "Mindset",
        ],
        context_injections=[
            "energy_state",
            "habit_context",
            "relationship_context",
            "life_primitive_context",
            "xp_and_progress",
        ],
        shares_with={
            "entrepreneur_os": [
                "energy_state",
                "focus_capacity",
                "schedule_context",
            ],
            "creator_os": [
                "energy_state",
                "creative_capacity",
                "mood_context",
            ],
        },
    ),
}


# ─── OSRegistryManager ────────────────────────────────────────────────────────


class OSRegistryManager:
    """
    Query and format the OS module registry.

    Used by TrinityEngine to determine what context to inject
    into the cognitive loop based on the user's subscriptions.
    """

    def __init__(self) -> None:
        self.registry = OS_REGISTRY

    def get_os(self, module: OSModule) -> OSModuleConfig | None:
        return self.registry.get(module)

    def get_active_modules(self) -> list[OSModuleConfig]:
        """Return all OS modules with status='active'."""
        return [config for config in self.registry.values() if config.status == "active"]

    def get_user_modules(
        self,
        subscriptions: list[str],
    ) -> list[OSModuleConfig]:
        """Return OS configs for the user's subscriptions."""
        result = []
        for sub in subscriptions:
            for config in self.registry.values():
                if config.id == sub:
                    result.append(config)
        return result

    def get_cross_os_context(
        self,
        active_modules: list[str],
    ) -> dict[str, list[str]]:
        """
        Return shared context keys between active modules.
        Only includes cross-OS data when BOTH sides are active.
        """
        shared: dict[str, list[str]] = {}
        for config in self.registry.values():
            if config.id not in active_modules:
                continue
            for target_os, shared_items in config.shares_with.items():
                # Only share if target OS is also active
                if target_os in active_modules:
                    shared.setdefault(target_os, []).extend(shared_items)
        return shared

    def format_for_prompt(self, subscriptions: list[str]) -> str:
        """
        Build the Layer 2 system prompt block for this user's subscriptions.
        Returns empty string if no subscriptions matched.
        """
        modules = self.get_user_modules(subscriptions)
        if not modules:
            return ""

        lines = ["ACTIVE OS MODULES:"]
        for m in modules:
            lines.append(f"  {m.name}: {m.primary_question}")

        # Cross-OS context if multiple active
        if len(modules) > 1:
            cross = self.get_cross_os_context(subscriptions)
            if cross:
                lines.append("")
                lines.append("CROSS-OS INTELLIGENCE ACTIVE:")
                lines.append("Multiple OS modules sharing context.")
                lines.append("Life state informs business decisions.")
                lines.append("Business context informs content strategy.")

        return "\n".join(lines)

    def get_all_modules(self) -> dict[OSModule, OSModuleConfig]:
        return self.registry
