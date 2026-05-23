"""
Domain team registry for the OS agent system.

Five teams: sales, research, content, marketing, operations.
Each team maps named sub-agents to a SubAgentConfig (task type + skill + token budget).
The module-level route() function is the single entry point used by AgentRuntime.run_team_task().

Usage:
    from substrate.control_plane.agents.agent_teams import route, run_team_task
    config = route("sales", "icp_qualifier")
    # config.task_type, config.skill_name, config.max_tokens

    result = run_team_task("marketing", "hook_generator", prompt, "lyfe_institute", ctx)
"""

from dataclasses import dataclass

from substrate.execution.runtime.agent_runtime import TaskType


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
    # Multi-touch follow-up sequence — each touch changes angle, not just repeats ask.
    "follow_up": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="follow_up_sequence",
        max_tokens=800,
    ),
    # Surfaces the real fear behind stated objections and moves toward a decision.
    "objection_handler": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="objection_handling",
        max_tokens=700,
    ),
    # Guides discovery → diagnosed problem → direct close for Initiate Arena at $750.
    "closer": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="call_to_close",
        max_tokens=900,
    ),
    # Value-first touchpoint for leads not yet ready to book — no offer attached.
    "nurturer": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="lead_nurture",
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


# ─── Marketing Team ───────────────────────────────────────────────────────────

_MARKETING_AGENTS: dict[str, SubAgentConfig] = {
    # Generates scroll-stopping hooks grounded in ICP signal data.
    "hook_generator": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="generate_content_from_intel",
        max_tokens=1000,
    ),
    # Develops content strategy from ICP patterns — angles, formats, distribution.
    "content_strategist": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="generate_content_from_intel",
        max_tokens=1200,
    ),
    # Analyzes ICP patterns across all stored signals to inform marketing decisions.
    "icp_analyst": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="analyze_icp_signal",
        max_tokens=1400,
    ),
    # Builds a 7-day content calendar grounded in real ICP signals — not invented topics.
    "content_planner": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="content_calendar",
        max_tokens=1400,
    ),
    # Identifies the single constraint limiting marketing performance and prescribes one fix.
    "campaign_doctor": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="campaign_diagnosis",
        max_tokens=1000,
    ),
}


class MarketingTeam:
    NAME = "marketing"

    def route(self, sub_agent: str) -> SubAgentConfig:
        if sub_agent not in _MARKETING_AGENTS:
            raise ValueError(
                f"[MarketingTeam] Unknown sub-agent '{sub_agent}'. "
                f"Available: {list(_MARKETING_AGENTS)}"
            )
        return _MARKETING_AGENTS[sub_agent]


# ─── Customer Success Team ────────────────────────────────────────────────────

_CUSTOMER_SUCCESS_AGENTS: dict[str, SubAgentConfig] = {
    # Runs the Day 0–7 onboarding sequence for a new Initiate Arena client.
    # One action at a time. Personal contact within 1 hour of payment.
    "onboarder": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="onboarding_sequence",
        max_tokens=1200,
    ),
    # Identifies disengaging clients from behavioral signals and prescribes
    # a tiered, personalized intervention — not a generic check-in.
    "retention_agent": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="churn_prevention",
        max_tokens=1000,
    ),
}


class CustomerSuccessTeam:
    NAME = "customer_success"

    def route(self, sub_agent: str) -> SubAgentConfig:
        if sub_agent not in _CUSTOMER_SUCCESS_AGENTS:
            raise ValueError(
                f"[CustomerSuccessTeam] Unknown sub-agent '{sub_agent}'. "
                f"Available: {list(_CUSTOMER_SUCCESS_AGENTS)}"
            )
        return _CUSTOMER_SUCCESS_AGENTS[sub_agent]


# ─── Operations Team ──────────────────────────────────────────────────────────

_OPERATIONS_AGENTS: dict[str, SubAgentConfig] = {
    # Analyzes a workflow or process and identifies the highest-leverage optimization.
    "process_optimizer": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="analyze_conversation",
        max_tokens=900,
    ),
    # Coordinates task assignments across agents and humans for a given objective.
    "task_coordinator": SubAgentConfig(
        task_type=TaskType.GENERATE,
        skill_name="qualify_lead",
        max_tokens=600,
    ),
    # Identifies the single bottleneck blocking throughput in a defined workflow.
    "bottleneck_finder": SubAgentConfig(
        task_type=TaskType.ANALYZE,
        skill_name="analyze_conversation",
        max_tokens=800,
    ),
}


class OperationsTeam:
    NAME = "operations"

    def route(self, sub_agent: str) -> SubAgentConfig:
        if sub_agent not in _OPERATIONS_AGENTS:
            raise ValueError(
                f"[OperationsTeam] Unknown sub-agent '{sub_agent}'. "
                f"Available: {list(_OPERATIONS_AGENTS)}"
            )
        return _OPERATIONS_AGENTS[sub_agent]


# ─── Registry ─────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, SalesTeam | ResearchTeam | ContentTeam | MarketingTeam | OperationsTeam | CustomerSuccessTeam] = {
    SalesTeam.NAME:           SalesTeam(),
    ResearchTeam.NAME:        ResearchTeam(),
    ContentTeam.NAME:         ContentTeam(),
    MarketingTeam.NAME:       MarketingTeam(),
    OperationsTeam.NAME:      OperationsTeam(),
    CustomerSuccessTeam.NAME: CustomerSuccessTeam(),
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


def run_team_task(
    team: str,
    sub_agent: str,
    prompt: str,
    venture_id: str,
    ctx=None,
    username: str | None = None,
) -> dict:
    """
    Convenience wrapper — resolves team/sub_agent, runs via AgentRuntime,
    returns result as a plain dict for easy inspection.

    Args:
        team:       Domain team name — 'sales', 'research', 'content',
                    'marketing', or 'operations'.
        sub_agent:  Named sub-agent within that team.
        prompt:     Task input.
        venture_id: Venture context to inject.
        ctx:        EntrepreneurOSContext — loaded from env if not provided.
        username:   Optional Instagram handle for human profile injection.

    Returns:
        dict with keys: output, model_used, tokens_used, skill_used,
        interaction_id, cost_usd, duration_ms.
    """
    from substrate.execution.runtime.agent_runtime import AgentRuntime
    from substrate.state.context.context import load_context_from_env

    runtime = AgentRuntime(ctx or load_context_from_env())
    result = runtime.run_team_task(
        team=team,
        sub_agent=sub_agent,
        prompt=prompt,
        venture_id=venture_id,
        username=username,
    )
    return {
        "output":         result.output,
        "model_used":     result.model_used,
        "tokens_used":    result.tokens_used,
        "skill_used":     result.skill_used,
        "interaction_id": result.interaction_id,
        "cost_usd":       result.cost_usd,
        "duration_ms":    result.duration_ms,
    }


async def run_browser_action(
    team: str,
    url: str,
    task: str,
    ctx=None,
) -> dict:
    """
    Execute a browser task on behalf of any department team.

    Wires the Level 4 execution layer (browser_agent.py) into the
    department agent hierarchy. Any team can now operate real websites.

    Args:
        team: Department team name — for logging/attribution only.
        url:  URL to navigate to before running the task.
        task: Natural-language task description for the browser agent.
        ctx:  EntrepreneurOSContext — loaded from env if not provided.

    Returns:
        {success, steps_taken, page_states, findings, final_url}
    """
    from substrate.execution.agents.browser_agent import run_browser_task
    print(f"[AgentTeams] {team} → browser_action: {task[:60]} @ {url}")
    return await run_browser_task(url, task, ctx)


def list_teams() -> dict[str, list[str]]:
    """Return a map of team → [sub_agent names] for inspection."""
    return {
        "sales":            list(_SALES_AGENTS),
        "research":         list(_RESEARCH_AGENTS),
        "content":          list(_CONTENT_AGENTS),
        "marketing":        list(_MARKETING_AGENTS),
        "operations":       list(_OPERATIONS_AGENTS),
        "customer_success": list(_CUSTOMER_SUCCESS_AGENTS),
    }
