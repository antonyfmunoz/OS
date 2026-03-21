"""
Domain team registry for the OS agent system.

Three teams: sales, research, content.
Each team maps named sub-agents to a SubAgentConfig (task type + skill + token budget).
The module-level route() function is the single entry point used by AgentRuntime.run_team_task().

Usage:
    from eos_ai.agent_teams import route
    config = route("sales", "icp_qualifier")
    # config.task_type, config.skill_name, config.max_tokens
"""

from dataclasses import dataclass

from eos_ai.agent_runtime import TaskType


# ─── Sub-agent config ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SubAgentConfig:
    task_type: TaskType
    skill_name: str          # passed to SkillRegistry.get_skill() — fuzzy matched
    max_tokens: int = 1024


# ─── Sales Team ───────────────────────────────────────────────────────────────

_SALES_AGENTS: dict[str, SubAgentConfig] = {
    # Scores a signal/comment against Lyfe Institute ICP.
    # Returns match score + archetype + psychological state as JSON.
    "icp_qualifier": SubAgentConfig(
        task_type=TaskType.SCORE,
        skill_name="qualify_lead",
        max_tokens=400,
    ),
    # Generates a personalized DM opener from a human profile + venture context.
    "outreach_writer": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="generate_outreach_from_intel",
        max_tokens=600,
    ),
    # Given a lead's reply, generates the optimal response for their specific objection.
    "objection_handler": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="analyze_conversation",
        max_tokens=900,
    ),
    # Given pipeline stage + history, generates the next follow-up with correct framing.
    "follow_up_sequencer": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="generate_follow_up_message",
        max_tokens=600,
    ),
}


class SalesTeam:
    NAME = "sales"

    def route(self, sub_agent: str) -> SubAgentConfig:
        if sub_agent not in _SALES_AGENTS:
            raise ValueError(
                f"[SalesTeam] Unknown sub-agent '{sub_agent}'. "
                f"Available: {list(_SALES_AGENTS)}"
            )
        return _SALES_AGENTS[sub_agent]


# ─── Research Team ────────────────────────────────────────────────────────────

_RESEARCH_AGENTS: dict[str, SubAgentConfig] = {
    # Processes a raw signal (comment, post, reply) — extracts pain language,
    # ICP indicators, and content angles as structured intelligence.
    "signal_analyzer": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="analyze_icp_signal",
        max_tokens=1200,
    ),
    # Summarizes competitor moves and market shifts relevant to Lyfe Institute.
    "market_monitor": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="generate_market_report",
        max_tokens=1400,
    ),
    # Finds recurring themes across N leads or signals using stored ICP patterns.
    "pattern_detector": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="detect_icp_patterns",
        max_tokens=1200,
    ),
}


class ResearchTeam:
    NAME = "research"

    def route(self, sub_agent: str) -> SubAgentConfig:
        if sub_agent not in _RESEARCH_AGENTS:
            raise ValueError(
                f"[ResearchTeam] Unknown sub-agent '{sub_agent}'. "
                f"Available: {list(_RESEARCH_AGENTS)}"
            )
        return _RESEARCH_AGENTS[sub_agent]


# ─── Content Team ─────────────────────────────────────────────────────────────

_CONTENT_AGENTS: dict[str, SubAgentConfig] = {
    # Produces 10 hooks derived from ICP signals and pain language.
    "hook_generator": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="generate_content_from_intel",
        max_tokens=1000,
    ),
    # Full caption: hook + body + CTA, written for the Initiate Arena audience.
    "caption_writer": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="draft_arena_content_post",
        max_tokens=1200,
    ),
    # Given current ICP data, returns the 3 highest-leverage content angles this week.
    "content_strategist": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="generate_content_from_intel",
        max_tokens=1000,
    ),
}


class ContentTeam:
    NAME = "content"

    def route(self, sub_agent: str) -> SubAgentConfig:
        if sub_agent not in _CONTENT_AGENTS:
            raise ValueError(
                f"[ContentTeam] Unknown sub-agent '{sub_agent}'. "
                f"Available: {list(_CONTENT_AGENTS)}"
            )
        return _CONTENT_AGENTS[sub_agent]


# ─── Registry ─────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, SalesTeam | ResearchTeam | ContentTeam] = {
    SalesTeam.NAME:    SalesTeam(),
    ResearchTeam.NAME: ResearchTeam(),
    ContentTeam.NAME:  ContentTeam(),
}


def route(team: str, sub_agent: str) -> SubAgentConfig:
    """
    Resolve a team + sub_agent name to a SubAgentConfig.

    Raises ValueError for unknown team or sub_agent.
    Called by AgentRuntime.run_team_task().
    """
    if team not in _REGISTRY:
        raise ValueError(
            f"[TeamRegistry] Unknown team '{team}'. "
            f"Available: {list(_REGISTRY)}"
        )
    return _REGISTRY[team].route(sub_agent)


def list_teams() -> dict[str, list[str]]:
    """Return a map of team → [sub_agent names] for inspection."""
    return {
        "sales":    list(_SALES_AGENTS),
        "research": list(_RESEARCH_AGENTS),
        "content":  list(_CONTENT_AGENTS),
    }
