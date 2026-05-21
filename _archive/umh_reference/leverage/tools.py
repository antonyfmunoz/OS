"""Phase 87 tool model — typed tool profiles and defaults.

Maps real-world tools into the leverage taxonomy so the system
can reason about what capabilities are available for any task.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.leverage.contracts import (
    ToolProfile,
    ToolType,
    _lev_id,
    normalize_tool_type,
)


def create_tool_profile(
    name: str,
    tool_type: str | ToolType,
    description: str = "",
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    cost: str = "",
    latency: str = "",
    reliability: str = "",
    authority_required: str = "",
    dependency_risk: str = "low",
    metadata: dict[str, Any] | None = None,
) -> ToolProfile:
    return ToolProfile(
        tool_id=_lev_id("tool"),
        name=name,
        tool_type=normalize_tool_type(tool_type),
        description=description,
        inputs=inputs or [],
        outputs=outputs or [],
        cost=cost,
        latency=latency,
        reliability=reliability,
        authority_required=authority_required,
        dependency_risk=dependency_risk,
        metadata=metadata or {},
    )


def classify_tool(
    name: str,
    description: str | None = None,
    context: str | None = None,
) -> ToolType:
    key = (name + " " + (description or "") + " " + (context or "")).lower()

    _MAP: list[tuple[list[str], ToolType]] = [
        (["claude", "chatgpt", "gemini", "llm", "ollama", "gpt"], ToolType.AI_MODEL),
        (["computer use", "browser", "screen", "gui"], ToolType.COMPUTER_USE),
        (["template", "sop", "playbook", "checklist"], ToolType.TEMPLATE),
        (["workflow", "pipeline", "automation"], ToolType.WORKFLOW),
        (
            ["instagram", "tiktok", "youtube", "twitter", "linkedin", "discord"],
            ToolType.SOCIAL_PLATFORM,
        ),
        (["api", "endpoint", "webhook"], ToolType.API),
        (["course", "curriculum", "training", "lesson"], ToolType.COURSE_CONTENT),
        (["document", "doc", "pdf", "spreadsheet"], ToolType.DOCUMENT),
        (["robot", "robotic", "actuator"], ToolType.ROBOTIC_SYSTEM),
        (["physical", "equipment", "hardware", "camera"], ToolType.PHYSICAL_ASSET),
        (["capital", "fund", "loan", "investment"], ToolType.CAPITAL_INSTRUMENT),
        (["channel", "media", "broadcast", "podcast"], ToolType.MEDIA_CHANNEL),
        (["human", "expert", "advisor", "contractor", "consultant"], ToolType.HUMAN_EXPERT),
        (["manual", "handmade", "hand"], ToolType.MANUAL_PROCESS),
        (["software", "app", "saas", "tool", "notion", "obsidian"], ToolType.SOFTWARE),
    ]

    for keywords, ttype in _MAP:
        if any(kw in key for kw in keywords):
            return ttype
    return ToolType.UNKNOWN


def build_default_tool_profiles() -> list[ToolProfile]:
    return [
        create_tool_profile(
            "UMH",
            ToolType.SOFTWARE,
            description="Universal Meta Harness — intelligence substrate powering EOS",
            inputs=["user context", "workflow templates", "governance policies"],
            outputs=["execution traces", "advisory recommendations", "state transitions"],
            reliability="high",
            dependency_risk="low",
        ),
        create_tool_profile(
            "EntrepreneurOS",
            ToolType.SOFTWARE,
            description="Business execution operating system built on UMH",
            inputs=["business workflows", "KPIs", "objectives"],
            outputs=["dashboards", "recommendations", "operating loops"],
            reliability="high",
            dependency_risk="low",
        ),
        create_tool_profile(
            "Claude Code",
            ToolType.AI_MODEL,
            description="Anthropic CLI agent — primary development and reasoning partner",
            inputs=["prompts", "code context", "task descriptions"],
            outputs=["code", "analysis", "recommendations"],
            cost="credit-based",
            reliability="high",
            dependency_risk="medium",
            metadata={"provider": "anthropic"},
        ),
        create_tool_profile(
            "ChatGPT and LLMs",
            ToolType.AI_MODEL,
            description="OpenAI, Gemini, Ollama — supplementary AI cognition",
            inputs=["prompts", "context"],
            outputs=["text", "analysis", "code"],
            cost="variable",
            reliability="medium",
            dependency_risk="medium",
        ),
        create_tool_profile(
            "Computer Use",
            ToolType.COMPUTER_USE,
            description="AI-driven browser/screen interaction for automation",
            inputs=["task instructions", "target URLs"],
            outputs=["screen actions", "data extraction"],
            reliability="low",
            dependency_risk="high",
            metadata={"status": "experimental"},
        ),
        create_tool_profile(
            "Obsidian",
            ToolType.SOFTWARE,
            description="Knowledge management — wiki, vault, memory palace",
            inputs=["notes", "links", "documents"],
            outputs=["organized knowledge", "backlinks", "search"],
            reliability="high",
            dependency_risk="low",
        ),
        create_tool_profile(
            "Notion",
            ToolType.SOFTWARE,
            description="Project management and documentation workspace",
            inputs=["tasks", "docs", "databases"],
            outputs=["organized projects", "dashboards"],
            reliability="high",
            dependency_risk="medium",
        ),
        create_tool_profile(
            "Google Workspace",
            ToolType.SOFTWARE,
            description="Gmail, Docs, Sheets, Drive, Calendar — business operations",
            inputs=["documents", "emails", "data"],
            outputs=["communications", "organized files", "schedules"],
            reliability="high",
            dependency_risk="medium",
        ),
        create_tool_profile(
            "Instagram",
            ToolType.SOCIAL_PLATFORM,
            description="Primary content distribution — reels, carousels, stories",
            inputs=["content", "captions", "hashtags"],
            outputs=["reach", "engagement", "DM leads"],
            reliability="medium",
            dependency_risk="high",
            metadata={"algorithm_dependent": True},
        ),
        create_tool_profile(
            "TikTok",
            ToolType.SOCIAL_PLATFORM,
            description="Short-form video distribution — discovery engine",
            inputs=["video content", "hooks"],
            outputs=["views", "followers", "engagement"],
            reliability="medium",
            dependency_risk="high",
        ),
        create_tool_profile(
            "YouTube",
            ToolType.SOCIAL_PLATFORM,
            description="Long-form video and search distribution",
            inputs=["video content", "SEO"],
            outputs=["views", "subscribers", "authority"],
            reliability="high",
            dependency_risk="medium",
        ),
        create_tool_profile(
            "Discord",
            ToolType.SOCIAL_PLATFORM,
            description="Community platform — Initiate Arena community hub",
            inputs=["messages", "events", "channels"],
            outputs=["community engagement", "retention", "support"],
            reliability="high",
            dependency_risk="medium",
        ),
        create_tool_profile(
            "Telegram",
            ToolType.SOCIAL_PLATFORM,
            description="Direct messaging and bot interface",
            inputs=["messages", "commands"],
            outputs=["responses", "notifications"],
            reliability="high",
            dependency_risk="low",
        ),
        create_tool_profile(
            "CRM / Spreadsheet",
            ToolType.SOFTWARE,
            description="Lead tracking, pipeline management, student records",
            inputs=["leads", "interactions", "status"],
            outputs=["pipeline views", "follow-up lists", "metrics"],
            reliability="high",
            dependency_risk="low",
        ),
        create_tool_profile(
            "Templates and SOPs",
            ToolType.TEMPLATE,
            description="Reusable templates, standard operating procedures, checklists",
            inputs=["process knowledge", "best practices"],
            outputs=["repeatable workflows", "quality consistency"],
            reliability="high",
            dependency_risk="low",
        ),
        create_tool_profile(
            "Human Contractors",
            ToolType.HUMAN_EXPERT,
            description="Future freelancers, VAs, specialists for delegation",
            inputs=["task briefs", "SOPs", "quality standards"],
            outputs=["completed work", "specialized output"],
            cost="variable",
            reliability="variable",
            dependency_risk="medium",
            metadata={"status": "future"},
        ),
        create_tool_profile(
            "Advisors",
            ToolType.HUMAN_EXPERT,
            description="Mentors, coaches, domain experts for strategic guidance",
            inputs=["context", "questions", "decisions"],
            outputs=["advice", "connections", "perspective"],
            cost="relationship-based",
            reliability="variable",
            dependency_risk="low",
            metadata={"status": "future"},
        ),
        create_tool_profile(
            "Future Robotics and Manufacturing Tools",
            ToolType.ROBOTIC_SYSTEM,
            description="Physical production, 3D printing, CNC, robotics — future capability",
            inputs=["designs", "CAD files", "specifications"],
            outputs=["physical products", "prototypes"],
            reliability="unknown",
            dependency_risk="high",
            metadata={"status": "future"},
        ),
    ]


def build_eos_workflow_tool_profiles(
    workflow: Any = None,
) -> list[ToolProfile]:
    if workflow is None:
        return []
    stages = getattr(workflow, "stages", [])
    tools: list[ToolProfile] = []
    for stage in stages:
        tools.append(
            create_tool_profile(
                f"Workflow Tool: {getattr(stage, 'name', 'unknown')}",
                ToolType.WORKFLOW,
                description=f"Execution tool for stage: {getattr(stage, 'objective', '')}",
                metadata={"stage_id": getattr(stage, "stage_id", "")},
            )
        )
    return tools


def tool_profile_to_dict(t: ToolProfile) -> dict[str, Any]:
    return t.to_dict()


def tool_profile_from_dict(d: dict[str, Any]) -> ToolProfile:
    return ToolProfile.from_dict(d)
