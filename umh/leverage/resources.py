"""Phase 87 resource model — typed resource profiles and defaults.

Maps real-world resources into the leverage taxonomy so the system
can reason about what the user has, what is constrained, and what
is available for deployment.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.leverage.contracts import (
    ResourceProfile,
    ResourceType,
    _lev_id,
    normalize_resource_type,
)


def create_resource_profile(
    name: str,
    resource_type: str | ResourceType,
    description: str = "",
    availability: str = "",
    constraints: list[str] | None = None,
    cost: str = "",
    owner: str = "antony",
    sensitivity: str = "normal",
    metadata: dict[str, Any] | None = None,
) -> ResourceProfile:
    return ResourceProfile(
        resource_id=_lev_id("res"),
        name=name,
        resource_type=normalize_resource_type(resource_type),
        description=description,
        availability=availability,
        constraints=constraints or [],
        cost=cost,
        owner=owner,
        sensitivity=sensitivity,
        metadata=metadata or {},
    )


def classify_resource(
    name: str,
    description: str | None = None,
    context: str | None = None,
) -> ResourceType:
    key = (name + " " + (description or "") + " " + (context or "")).lower()

    _MAP: list[tuple[list[str], ResourceType]] = [
        (["attention", "focus"], ResourceType.ATTENTION),
        (["time", "hours", "schedule"], ResourceType.TIME),
        (["energy", "stamina", "willpower"], ResourceType.ENERGY),
        (["money", "capital", "cash", "revenue", "budget"], ResourceType.MONEY),
        (["audience", "followers", "subscribers"], ResourceType.AUDIENCE),
        (["brand", "reputation", "trust"], ResourceType.BRAND),
        (["network", "relationship", "contacts"], ResourceType.NETWORK),
        (["code", "codebase", "software", "repo"], ResourceType.CODE),
        (["ai", "model", "llm", "claude", "gpt"], ResourceType.AI_MODEL),
        (["template", "sop", "playbook"], ResourceType.TEMPLATE),
        (["library", "collection", "archive"], ResourceType.LIBRARY),
        (["data", "analytics", "metrics"], ResourceType.DATA),
        (["tool", "app", "saas"], ResourceType.TOOL),
        (["platform", "instagram", "tiktok", "youtube"], ResourceType.PLATFORM),
        (["process", "workflow", "system"], ResourceType.PROCESS),
        (["human", "person", "contractor", "team"], ResourceType.HUMAN),
        (["equipment", "hardware", "device"], ResourceType.EQUIPMENT),
        (["real estate", "property", "space"], ResourceType.REAL_ESTATE),
        (["manufacturing", "production", "factory"], ResourceType.MANUFACTURING),
        (["fulfillment", "shipping", "logistics"], ResourceType.FULFILLMENT),
        (["robot", "automation", "robotic"], ResourceType.ROBOTICS),
        (["media", "video", "image", "audio", "content"], ResourceType.MEDIA_ASSET),
        (["knowledge", "expertise", "skill", "know-how"], ResourceType.KNOWLEDGE_ASSET),
    ]

    for keywords, rtype in _MAP:
        if any(kw in key for kw in keywords):
            return rtype
    return ResourceType.UNKNOWN


def build_default_user_resource_profiles() -> list[ResourceProfile]:
    return [
        create_resource_profile(
            "User Attention",
            ResourceType.ATTENTION,
            description="Antony's focused attention — highest-leverage personal resource",
            availability="limited — ~12-16 waking hours/day",
            constraints=["finite", "easily fragmented", "context-switch cost"],
        ),
        create_resource_profile(
            "User Time",
            ResourceType.TIME,
            description="Antony's available working hours",
            availability="limited — must allocate across ventures",
            constraints=["non-renewable", "opportunity cost"],
        ),
        create_resource_profile(
            "User Energy",
            ResourceType.ENERGY,
            description="Physical and mental energy for execution",
            availability="variable — depends on sleep, fitness, nutrition",
            constraints=["depletes daily", "recovery required"],
        ),
        create_resource_profile(
            "Personal Brand Audience",
            ResourceType.AUDIENCE,
            description="Social media followers and engaged audience across platforms",
            availability="growing — pre-scale",
            constraints=["platform-dependent", "algorithm-gated"],
        ),
        create_resource_profile(
            "Content Assets",
            ResourceType.MEDIA_ASSET,
            description="Published and draft content pieces, videos, carousels, posts",
            availability="accumulating",
            constraints=["requires production time", "platform-specific formats"],
        ),
        create_resource_profile(
            "AI Agents and Models",
            ResourceType.AI_MODEL,
            description="Claude Code, ChatGPT, Gemini, Ollama — AI cognition leverage",
            availability="24/7 within API/credit limits",
            constraints=["credit costs", "hallucination risk", "context limits"],
        ),
        create_resource_profile(
            "UMH Codebase",
            ResourceType.CODE,
            description="Universal Meta Harness — 1600+ files, full execution spine",
            availability="always available on VPS",
            constraints=["complexity", "maintenance burden"],
        ),
        create_resource_profile(
            "EOS Tomorrow Operating Loop",
            ResourceType.PROCESS,
            description="Phase 86 daily operating cycle — prepare/brief/execute/review/close/handoff",
            availability="built and tested",
            constraints=["deterministic v1 — no LLM enhancement yet"],
        ),
        create_resource_profile(
            "Initiate Arena Offer",
            ResourceType.KNOWLEDGE_ASSET,
            description="Lyfe Institute's first product — transformation program for initiates",
            availability="defined but pre-revenue",
            constraints=["unproven market fit", "needs first sales"],
        ),
        create_resource_profile(
            "Empyrean Studio Capabilities",
            ResourceType.PROCESS,
            description="Creative, marketing, AI agency capabilities — internal execution arm",
            availability="founder-operated",
            constraints=["no team yet", "depends on founder bandwidth"],
        ),
        create_resource_profile(
            "Lyfe Institute Product Suite",
            ResourceType.KNOWLEDGE_ASSET,
            description="Initiate Arena (active), Game of Lyfe (planned), future programs",
            availability="Initiate Arena ready, others planned",
            constraints=["sequential — Arena first, then Game of Lyfe"],
        ),
        create_resource_profile(
            "OST Software and IP",
            ResourceType.CODE,
            description="UMH, EOS, CreatorOS, LyfeOS codebases and architecture",
            availability="in active development",
            constraints=["pre-revenue", "single developer"],
        ),
        create_resource_profile(
            "Social Media Accounts",
            ResourceType.PLATFORM,
            description="Instagram, TikTok, YouTube, X, LinkedIn, Discord, Telegram",
            availability="active accounts",
            constraints=["algorithm-dependent", "platform risk"],
        ),
        create_resource_profile(
            "Documents and Notes",
            ResourceType.KNOWLEDGE_ASSET,
            description="Obsidian vault, Notion workspace, strategy docs, wiki",
            availability="always available",
            constraints=["needs organization", "retrieval hierarchy"],
        ),
        create_resource_profile(
            "AI Chat Archive",
            ResourceType.DATA,
            description="Historical AI conversations — Claude, ChatGPT, Gemini",
            availability="exists but not ingested",
            constraints=["ingestion pipeline not built", "format variety"],
        ),
        create_resource_profile(
            "Saved Media and Algorithmic References",
            ResourceType.DATA,
            description="Instagram saved/liked, TikTok saved, YouTube watch later",
            availability="exists on platforms",
            constraints=["no ingestion yet", "platform API limits"],
        ),
        create_resource_profile(
            "Future Capital",
            ResourceType.MONEY,
            description="Revenue from Initiate Arena and future ventures",
            availability="not yet — pre-revenue",
            constraints=["depends on first sales", "reinvestment needed"],
        ),
        create_resource_profile(
            "Future Contractors and Team",
            ResourceType.HUMAN,
            description="Potential hires, contractors, freelancers for delegation",
            availability="not yet — post-revenue",
            constraints=["requires revenue", "management overhead", "trust building"],
        ),
    ]


def build_eos_workflow_resource_profiles(
    workflow: Any = None,
) -> list[ResourceProfile]:
    if workflow is None:
        return []
    stages = getattr(workflow, "stages", [])
    resources: list[ResourceProfile] = []
    for stage in stages:
        resources.append(
            create_resource_profile(
                f"Workflow Stage: {getattr(stage, 'name', 'unknown')}",
                ResourceType.PROCESS,
                description=getattr(stage, "objective", ""),
                owner=getattr(stage, "owner", "antony"),
                metadata={"stage_id": getattr(stage, "stage_id", "")},
            )
        )
    return resources


def resource_profile_to_dict(r: ResourceProfile) -> dict[str, Any]:
    return r.to_dict()


def resource_profile_from_dict(d: dict[str, Any]) -> ResourceProfile:
    return ResourceProfile.from_dict(d)
