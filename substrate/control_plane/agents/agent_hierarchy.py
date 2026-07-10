import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


def _venture_name(venture_id: str) -> str:
    """Resolve a venture display name from instance config. Falls back to title-cased slug."""
    try:
        from substrate.self_model import SelfModel
        sm = SelfModel()
        for v in sm.instance.ventures:
            if v.get('id') == venture_id:
                return v.get('name', venture_id.replace('_', ' ').title())
    except Exception:
        pass
    return venture_id.replace('_', ' ').title()


"""
Agent hierarchy for UMH substrate.

Defines the formal authority structure from Founder → EA → CEOs → Departments.
Used by CognitiveLoop (PERCEIVE injection) and Gateway (routing) to ensure
90% of all communication is handled by the Executive Assistant without
unnecessary escalation.

Usage:
    from substrate.control_plane.agents.agent_hierarchy import AgentHierarchy, HIERARCHY

    ah = AgentHierarchy()
    print(ah.get_org_chart())
    print(ah.get_primary_interface())          # 'executive_assistant'
    print(ah.format_for_prompt('<venture_slug>_ceo'))
"""

# ─── CORRECTED HIERARCHY AND COMMUNICATION FLOW ───────────────────────────────
#
# Founder
#   ↕ communicates via EA
# EA — communication bridge only
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


def _venture_ceo_entry(venture_id: str, display_name: str) -> dict:
    """Build a per-venture CEO hierarchy entry for a single tenant venture.

    Multi-tenant: venture_id / display_name come from the tenant's BIS venture
    roster at runtime — never a hardcoded slug. A managing developer agent is
    added by build_hierarchy() alongside this entry.
    """
    return {
        'level': 3,
        'title': f'{display_name} CEO',
        'reports_to': 'executive_assistant',
        'manages': [f'{venture_id}_developer_agent'],
        'is_primary_interface': False,
        'owns': [
            f'{venture_id}_strategy',
            f'{venture_id}_performance',
            f'{venture_id}_team',
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
        'venture_id': venture_id,
        'soul_doc': f'{_ROOT}/agents/{venture_id}_ceo.md',
        'discord_bot_env': f'DISCORD_BOT_TOKEN_{venture_id.upper()}',
        'emoji': '🏢',
        # CEO decides own org structure based on founder direction.
        # May appoint a Chief of Staff if complexity warrants it.
        'ceo_intelligence': True,
    }


def _venture_developer_entry(venture_id: str, display_name: str) -> dict:
    """Build a per-venture developer-agent hierarchy entry for a single tenant venture."""
    return {
        'level': 4,
        'title': f'{display_name} Developer Agent',
        'identity': 'Claude Code',
        'reports_to': f'{venture_id}_ceo',
        'manages': [],
        'owns': [
            f'{venture_id}_codebase_integrity',
            f'{venture_id}_agent_creation',
            f'{venture_id}_skill_creation',
            f'{venture_id}_deployment',
            f'{venture_id}_debugging',
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
            'architecture_decision': f'{venture_id}_ceo',
            'founder_direction':     'executive_assistant',
        },
        'human_partner': 'developer',
        'autonomy_level': 4,
        'operating_mode': 'hybrid',
        'domain': 'technical',
        'venture_id': venture_id,
        'soul_doc': f'{_ROOT}/.claude/CLAUDE.md',
        'emoji': '⚙️',
        'is_developer_agent': True,
    }


def build_hierarchy(ctx=None) -> dict[str, dict]:
    """Compose the agent hierarchy for the active tenant.

    Static roles (EA, portfolio advisor, research agent) are tenant-agnostic.
    Per-venture CEO + developer-agent entries are generated from this tenant's
    BIS venture roster (``get_ventures(ctx)``) — never from literal slugs, so
    each seat sees only its own org's ventures. When no roster is resolvable
    (context/DB unset), only the static roles exist.
    """
    try:
        from substrate.state.business.business_instance import get_ventures
        ventures = get_ventures(ctx)
    except Exception:
        ventures = []

    venture_ceo_ids = [f"{v['id']}_ceo" for v in ventures if v.get('id')]

    hierarchy: dict[str, dict] = {

        'executive_assistant': {
            'level': 2,
            'title': 'Executive Assistant',
            'identity': '',
            'reports_to': None,
            'manages': ['portfolio_advisor', *venture_ceo_ids],
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
            'manages': list(venture_ceo_ids),
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

        'research_agent': {
            'level': 3,
            'title': 'Research Agent',
            'reports_to': venture_ceo_ids[0] if venture_ceo_ids else 'executive_assistant',
            'manages': [],
            'owns': [
                'icp_analysis',
                'signal_processing',
                'market_intelligence',
                'pattern_detection',
                'competitive_research',
            ],
            'handle_directly': ['RESEARCH', 'ANALYZE', 'INTEL'],
            'escalate_to': {'strategy': venture_ceo_ids[0] if venture_ceo_ids else 'executive_assistant'},
            'soul_doc': f'{_ROOT}/agents/research_agent.md',
            'emoji': '🔬',
        },
    }

    # Per-venture CEO + developer-agent entries, generated from the tenant roster.
    for v in ventures:
        vid = v.get('id')
        if not vid:
            continue
        vname = v.get('name') or _venture_name(vid)
        hierarchy[f'{vid}_ceo'] = _venture_ceo_entry(vid, vname)
        hierarchy[f'{vid}_developer_agent'] = _venture_developer_entry(vid, vname)

    return hierarchy


# Module-level default hierarchy — env-based tenant resolution (empty roster when
# UMH_ORG_ID is unset, so no named tenant leaks into the default build).
HIERARCHY: dict[str, dict] = build_hierarchy()


# ─── AgentHierarchy ───────────────────────────────────────────────────────────

class AgentHierarchy:
    """
    Formal hierarchy of agents in the UMH substrate.

    Responsibilities:
    - Routing: which agent should handle a given request
    - Context injection: format hierarchy context for an agent's system prompt
    - Org chart rendering: human-readable view of the hierarchy
    """

    def __init__(self, ctx=None) -> None:
        # Build the hierarchy for the active tenant. When no ctx is passed the
        # env-based build applies (UMH_ORG_ID); an empty roster yields only the
        # static roles rather than any named tenant's ventures.
        self.agents = build_hierarchy(ctx) if ctx is not None else HIERARCHY

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

        # Build portfolio keywords dynamically from org name
        _org = os.environ.get("UMH_ORG_NAME", "").lower()
        portfolio_words = [
            'portfolio', 'all companies',
            'capital allocation', 'allocate', 'across companies',
            'both ventures', 'both companies',
        ]
        if _org:
            portfolio_words.append(_org)
        if any(w in text_lower for w in portfolio_words):
            return 'portfolio_advisor'

        # Route to venture CEOs by matching venture/product names from config
        try:
            from substrate.self_model import SelfModel
            sm = SelfModel()
            for v in sm.instance.ventures:
                v_name = v.get('name', '').lower()
                v_id = v.get('id', '')
                if v_name and v_name in text_lower:
                    # Find the CEO agent for this venture
                    for agent_id, cfg in self.agents.items():
                        if cfg.get('venture_id') == v_id and cfg.get('ceo_intelligence'):
                            return agent_id
            for p in sm.instance.products:
                p_name = p.get('name', '').lower()
                p_venture = p.get('venture', '')
                if p_name and p_name in text_lower:
                    for agent_id, cfg in self.agents.items():
                        if cfg.get('venture_id') == p_venture and cfg.get('ceo_intelligence'):
                            return agent_id
        except Exception:
            pass

        # Generic program/course keywords → default to first venture CEO
        generic_words = ('the program', 'the course', 'cohort')
        if any(w in text_lower for w in generic_words):
            for agent_id, cfg in self.agents.items():
                if cfg.get('ceo_intelligence'):
                    return agent_id

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
