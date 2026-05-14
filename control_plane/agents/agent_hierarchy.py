import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

"""
Agent hierarchy for EntrepreneurOS.

Defines the formal authority structure from Founder → EA → CEOs → Departments.
Used by CognitiveLoop (PERCEIVE injection) and Gateway (routing) to ensure
90% of all communication is handled by the Executive Assistant without
unnecessary escalation.

Usage:
    from control_plane.agents.agent_hierarchy import AgentHierarchy, HIERARCHY

    ah = AgentHierarchy()
    print(ah.get_org_chart())
    print(ah.get_primary_interface())          # 'executive_assistant'
    print(ah.format_for_prompt('lyfe_institute_ceo'))
"""

# ─── CORRECTED HIERARCHY AND COMMUNICATION FLOW ───────────────────────────────
#
# Antony (Founder)
#   ↕ communicates via EA
# EA (DEX) — communication bridge only
#   EA routes to CEOs on founder's behalf
#   EA does NOT manage technical execution
#   ↕ routes to
# CEO Agents (per company)
#   Own everything inside their company
#   Including technical execution
#   ↓ directs
# Developer Agents (per company)
#   Report to their respective CEO
#   Build and maintain company tech layer
#   Operate in hybrid mode with human dev
#   ↓ use
# Department Managers + Staff Agents
#   ↓ use
# Execution Layer (tools)
#
# Portfolio Advisor:
#   Pure intelligence only
#   No developer agent
#   Informs CEOs, does not command them
#
# ─── Hierarchy definition ─────────────────────────────────────────────────────

HIERARCHY: dict[str, dict] = {

    'executive_assistant': {
        'level': 2,
        'title': 'Executive Assistant',
        'identity': 'DEX',
        'reports_to': None,
        'manages': [
            'portfolio_advisor',
            'lyfe_institute_ceo',
            'empyrean_ceo',
        ],
        'is_primary_interface': True,
        'owns': [
            'founder_communication',
            'meeting_facilitation',
            'task_routing',
            'morning_brief',
            'follow_up',
            'action_item_tracking',
        ],
        'handle_directly': [
            'morning_brief',
            'status_updates',
            'routine_questions',
            'meeting_scheduling',
            'task_assignment',
            'content_planning',
            'outreach_session',
            'stage_guidance',
        ],
        'escalate_to': {
            'company_strategy':   'relevant_ceo',
            'portfolio_strategy': 'portfolio_advisor',
            'department_execution': 'relevant_manager',
            'capital_allocation': 'portfolio_advisor',
        },
        'soul_doc': f'{_ROOT}/agents/executive_assistant.md',
        'discord_bot_env': 'DISCORD_BOT_TOKEN',
        'emoji': '👁️',
    },

    'portfolio_advisor': {
        'level': 1,
        'title': 'Portfolio Advisor',
        'reports_to': 'executive_assistant',
        'manages': [
            'lyfe_institute_ceo',
            'empyrean_ceo',
        ],
        'is_primary_interface': False,
        'owns': [
            'cross_company_strategy',
            'capital_allocation',
            'portfolio_performance',
            'strategic_patterns',
        ],
        'handle_directly': [
            'portfolio_performance',
            'resource_allocation',
            'cross_company_decisions',
        ],
        'escalate_to': {
            'founder_decision': 'executive_assistant',
        },
        'soul_doc': f'{_ROOT}/agents/portfolio_advisor.md',
        'discord_bot_env': 'DISCORD_BOT_TOKEN_PORTFOLIO',
        'emoji': '📊',
    },

    'lyfe_institute_ceo': {
        'level': 3,
        'title': 'Lyfe Institute CEO',
        'reports_to': 'executive_assistant',
        'manages': [
            'lyfe_developer_agent',
            'lyfe_sales_manager',
            'lyfe_marketing_manager',
            'lyfe_cs_manager',
            'lyfe_operations_manager',
            'lyfe_finance_manager',
        ],
        'is_primary_interface': False,
        'owns': [
            'lyfe_institute_strategy',
            'lyfe_institute_performance',
            'lyfe_institute_team',
        ],
        'handle_directly': [
            'company_strategy',
            'department_coordination',
            'hiring_decisions',
            'product_decisions',
        ],
        'escalate_to': {
            'portfolio_decision': 'portfolio_advisor',
            'founder_decision':   'executive_assistant',
        },
        'venture_id': 'lyfe_institute',
        'soul_doc': f'{_ROOT}/agents/lyfe_institute_ceo.md',
        'discord_bot_env': 'DISCORD_BOT_TOKEN_LYFE',
        'emoji': '🏢',
        # CEO decides own org structure based on founder direction.
        # May appoint a Chief of Staff if complexity warrants it.
        'ceo_intelligence': True,
    },

    'empyrean_ceo': {
        'level': 3,
        'title': 'Empyrean Creative CEO',
        'reports_to': 'executive_assistant',
        'manages': [
            'empyrean_developer_agent',
            'empyrean_sales_manager',
            'empyrean_operations_manager',
        ],
        'is_primary_interface': False,
        'owns': [
            'empyrean_strategy',
            'empyrean_performance',
        ],
        'handle_directly': [
            'company_strategy',
            'client_relationships',
            'service_delivery',
        ],
        'escalate_to': {
            'portfolio_decision': 'portfolio_advisor',
            'founder_decision':   'executive_assistant',
        },
        'venture_id': 'empyrean_creative',
        'soul_doc': f'{_ROOT}/agents/empyrean_ceo.md',
        'discord_bot_env': 'DISCORD_BOT_TOKEN_EMPYREAN',
        'emoji': '⚡',
        'ceo_intelligence': True,
    },

    'lyfe_developer_agent': {
        'level': 4,
        'title': 'Lyfe Institute Developer Agent',
        'identity': 'Claude Code',
        'reports_to': 'lyfe_institute_ceo',
        'manages': [],
        'owns': [
            'lyfe_codebase_integrity',
            'lyfe_agent_creation',
            'lyfe_skill_creation',
            'lyfe_deployment',
            'lyfe_debugging',
        ],
        'handle_directly': [
            'code_changes',
            'debugging',
            'new_agent',
            'new_skill',
            'deployment',
            'testing',
        ],
        'escalate_to': {
            'architecture_decision': 'lyfe_institute_ceo',
            'founder_direction':     'executive_assistant',
        },
        'human_partner': 'developer',
        'autonomy_level': 4,
        'operating_mode': 'hybrid',
        'domain': 'technical',
        'venture_id': 'lyfe_institute',
        'soul_doc': f'{_ROOT}/.claude/CLAUDE.md',
        'emoji': '⚙️',
        'is_developer_agent': True,
    },

    'research_agent': {
        'level': 3,
        'title': 'Research Agent',
        'reports_to': 'lyfe_institute_ceo',
        'manages': [],
        'owns': [
            'icp_analysis',
            'signal_processing',
            'market_intelligence',
            'pattern_detection',
            'competitive_research',
        ],
        'handle_directly': ['RESEARCH', 'ANALYZE', 'INTEL'],
        'escalate_to': {'strategy': 'lyfe_institute_ceo'},
        'soul_doc': f'{_ROOT}/agents/research_agent.md',
        'emoji': '🔬',
    },

    'empyrean_developer_agent': {
        'level': 4,
        'title': 'Empyrean Developer Agent',
        'identity': 'Claude Code',
        'reports_to': 'empyrean_ceo',
        'manages': [],
        'owns': [
            'empyrean_codebase_integrity',
            'empyrean_agent_creation',
            'empyrean_skill_creation',
            'empyrean_deployment',
        ],
        'handle_directly': [
            'code_changes',
            'debugging',
            'new_agent',
            'new_skill',
            'deployment',
        ],
        'escalate_to': {
            'architecture_decision': 'empyrean_ceo',
            'founder_direction':     'executive_assistant',
        },
        'human_partner': 'developer',
        'autonomy_level': 4,
        'operating_mode': 'hybrid',
        'domain': 'technical',
        'venture_id': 'empyrean_creative',
        'soul_doc': f'{_ROOT}/.claude/CLAUDE.md',
        'emoji': '⚙️',
        'is_developer_agent': True,
    },
}


# ─── AgentHierarchy ───────────────────────────────────────────────────────────

class AgentHierarchy:
    """
    Formal hierarchy of agents in the EntrepreneurOS system.

    Responsibilities:
    - Routing: which agent should handle a given request
    - Context injection: format hierarchy context for an agent's system prompt
    - Org chart rendering: human-readable view of the hierarchy
    """

    def __init__(self) -> None:
        self.agents = HIERARCHY

    # ─── Routing ─────────────────────────────────────────────────────────────

    def get_primary_interface(self) -> str:
        """Return the agent_id of the primary founder-facing interface (EA)."""
        for agent_id, config in self.agents.items():
            if config.get('is_primary_interface'):
                return agent_id
        return 'executive_assistant'

    def should_handle_directly(self, agent_id: str, task: str) -> bool:
        """Return True if agent_id should handle this task without escalation."""
        agent = self.agents.get(agent_id, {})
        return task in agent.get('handle_directly', [])

    def get_escalation_target(self, agent_id: str, task_type: str) -> str | None:
        """Return the agent_id this agent should escalate task_type to, or None."""
        agent = self.agents.get(agent_id, {})
        return agent.get('escalate_to', {}).get(task_type)

    def route_request(self, text: str) -> str:
        """
        Determine which agent should handle a natural language request.

        EA handles 90% of cases directly. Only escalates to CEO agents for
        company-specific deep questions, or to Portfolio Advisor for
        portfolio-level decisions.

        Returns agent_id string.
        """
        text_lower = text.lower()

        # Portfolio-level → Portfolio Advisor
        portfolio_words = (
            'portfolio', 'all companies', 'munoz holdings',
            'capital allocation', 'allocate', 'across companies',
            'both ventures', 'both companies',
        )
        if any(w in text_lower for w in portfolio_words):
            return 'portfolio_advisor'

        # Lyfe Institute specific → Lyfe Institute CEO
        lyfe_words = (
            'lyfe institute', 'initiate arena',
            'the program', 'the course', 'cohort',
            'initiate', 'arena',
        )
        if any(w in text_lower for w in lyfe_words):
            return 'lyfe_institute_ceo'

        # Empyrean specific → Empyrean CEO
        empyrean_words = (
            'empyrean', 'creative agency',
            'client project', 'studio',
        )
        if any(w in text_lower for w in empyrean_words):
            return 'empyrean_ceo'

        # Everything else → EA handles directly
        return 'executive_assistant'

    # ─── Context injection ────────────────────────────────────────────────────

    def format_for_prompt(self, agent_id: str) -> str:
        """
        Format hierarchy context for injection into an agent's system prompt.
        Returns empty string if agent_id is not in HIERARCHY.
        """
        agent = self.agents.get(agent_id, {})
        if not agent:
            return ''

        lines: list[str] = [
            f"YOUR ROLE: {agent.get('title')}",
            f"LEVEL: {agent.get('level')}",
        ]

        manages = agent.get('manages', [])
        if manages:
            lines.append(f"YOU MANAGE: {', '.join(manages)}")

        owns = agent.get('owns', [])
        if owns:
            lines.append(f"YOU OWN: {', '.join(owns)}")

        handle = agent.get('handle_directly', [])
        if handle:
            lines.append(f"HANDLE DIRECTLY: {', '.join(handle)}")

        escalate = agent.get('escalate_to', {})
        for task, target in escalate.items():
            lines.append(f"ESCALATE {task.upper()} TO: {target}")

        if agent.get('is_primary_interface'):
            lines.append(
                "PRIMARY INTERFACE: You handle 90% of all founder communication directly. "
                "Only escalate to CEOs for deep company-specific decisions. "
                "Only escalate to Portfolio Advisor for capital allocation decisions."
            )

        if agent.get('ceo_intelligence'):
            lines.append(
                "CEO AUTHORITY: You determine your own org structure based on founder direction. "
                "You may appoint a Chief of Staff if complexity warrants it. "
                "The founder gives direction. You execute it."
            )

        reports_to = agent.get('reports_to')
        if reports_to:
            lines.append(f"REPORTS TO: {reports_to}")

        return '\n'.join(lines)

    # ─── Org chart ────────────────────────────────────────────────────────────

    def get_org_chart(self) -> str:
        """Return a human-readable org chart sorted by level."""
        lines = ['AGENT ORG CHART', '=' * 40]

        # Sort by level, then by agent_id for deterministic output
        sorted_agents = sorted(
            self.agents.items(),
            key=lambda kv: (kv[1].get('level', 0), kv[0]),
        )

        for agent_id, cfg in sorted_agents:
            level   = cfg.get('level', 0)
            indent  = '  ' * (level - 1) if level > 0 else ''
            emoji   = cfg.get('emoji', '•')
            title   = cfg.get('title', agent_id)
            reports = cfg.get('reports_to') or 'founder'
            primary = ' ← PRIMARY INTERFACE' if cfg.get('is_primary_interface') else ''
            lines.append(
                f"{indent}{emoji} L{level}: {title}"
                f" → {reports}{primary}"
            )

        return '\n'.join(lines)

    def get_agent_config(self, agent_id: str) -> dict | None:
        """Return raw config dict for agent_id, or None if not found."""
        return self.agents.get(agent_id)

    def get_agent(self, agent_id: str) -> dict:
        """Return raw config dict for agent_id, or empty dict if not found."""
        return self.agents.get(agent_id) or {}

    def list_agents(self) -> list[str]:
        """Return all registered agent IDs."""
        return list(self.agents.keys())
