"""
CEOAgent — one per company, strategy layer.

Reads primitives from context automatically (never asks the founder).
Reasons about org chart composition based on stage and reality.
Monitors for stage transitions and evolves the org chart.
Reports to Portfolio Agent.

Usage:
    from control_plane.agents.ceo_agent import CEOAgent
    from state.context.context import load_context_from_env

    ctx = load_context_from_env()
    ceo = CEOAgent(ctx)

    primitives = ceo.detect_primitives()
    roles      = ceo.reason_org_chart(primitives)
    changes    = ceo.check_and_evolve()
"""

import json
import os
from typing import Optional
from state.context.context import EntrepreneurOSContext
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



# ─── Stage → minimum viable role map (fallback when AI call fails) ────────────

STAGE_ROLE_MAP: dict[int, list[str]] = {
    1: ['executive_assistant', 'outreach_agent'],
    2: ['executive_assistant', 'outreach_agent', 'content_agent', 'operations_agent'],
    3: ['executive_assistant', 'outreach_agent', 'content_agent',
        'operations_agent', 'sales_agent', 'research_agent'],
}


class CEOAgent:
    """
    Strategy layer. One instance per company.
    Reports to Portfolio Agent. Directs EA Agent and all role agents.

    Never executes — reasons and directs.
    Never asks the founder for info it can find itself.
    """

    def __init__(self, ctx: EntrepreneurOSContext) -> None:
        self.ctx = ctx

    # ─── detect_primitives ────────────────────────────────────────────────────

    def detect_primitives(self) -> dict:
        """
        Read all available context from Neon automatically.
        Sources: BIS data, pipeline, weekly activity, feedback outcomes.
        Never asks the founder — all of it is already accessible.
        """
        primitives: dict = {}

        try:
            from state.storage.db import get_conn

            with get_conn(self.ctx.org_id) as cur:

                # BIS data — most recent bis_update event
                cur.execute(
                    """
                    SELECT payload_json FROM events
                    WHERE org_id = %s
                      AND event_type = 'bis_update'
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (self.ctx.org_id,),
                )
                row = cur.fetchone()
                if row:
                    bis = row['payload_json']
                    if isinstance(bis, str):
                        bis = json.loads(bis)
                    if isinstance(bis, dict):
                        primitives.update(bis)

                # Pipeline — total lead count
                cur.execute(
                    """
                    SELECT COUNT(*) AS leads FROM events
                    WHERE org_id = %s
                      AND event_type = 'pipeline_entry'
                    """,
                    (self.ctx.org_id,),
                )
                row = cur.fetchone()
                primitives['lead_count'] = (row['leads'] if row else 0) or 0

                # Weekly activity — user messages in the last 7 days
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt FROM messages
                    WHERE org_id = %s
                      AND role = 'user'
                      AND created_at > NOW() - INTERVAL '7 days'
                    """,
                    (self.ctx.org_id,),
                )
                row = cur.fetchone()
                primitives['weekly_interactions'] = (row['cnt'] if row else 0) or 0

                # Feedback loop outcomes — recommendation results
                cur.execute(
                    """
                    SELECT
                        payload_json->>'outcome' AS outcome,
                        COUNT(*) AS count
                    FROM events
                    WHERE org_id = %s
                      AND event_type = 'recommendation'
                    GROUP BY outcome
                    """,
                    (self.ctx.org_id,),
                )
                outcomes = {r['outcome']: r['count']
                            for r in cur.fetchall() if r['outcome']}
                primitives['outcomes'] = outcomes

        except Exception as e:
            print(f'[CEOAgent] detect_primitives: {e}')

        # Fill stage from BIS manager if not in events
        if 'stage' not in primitives or 'current_revenue' not in primitives:
            try:
                from state.business.business_instance import BusinessInstanceManager
                from state.storage.db import get_conn, resolve_venture
                with get_conn(self.ctx.org_id) as cur:
                    venture_id = self.ctx.active_venture_id or 'lyfe_institute'
                    resolve_venture(venture_id)
                bim = BusinessInstanceManager(self.ctx)
                bis = bim.get_bis(venture_id)
                if bis:
                    if 'stage' not in primitives:
                        primitives['stage'] = bis.current_stage
                    if 'current_revenue' not in primitives:
                        primitives['current_revenue'] = bis.monthly_revenue
                    if 'client_count' not in primitives:
                        primitives['client_count'] = 0  # derived from interactions
                    if 'primary_channel' not in primitives:
                        primitives['primary_channel'] = bis.primary_channel
                    if 'offer_name' not in primitives:
                        primitives['offer_name'] = bis.offer_name
            except Exception as e:
                print(f'[CEOAgent] BIS fallback: {e}')

        # Safe defaults for any missing keys
        primitives.setdefault('stage', 1)
        primitives.setdefault('current_revenue', 0)
        primitives.setdefault('client_count', 0)
        primitives.setdefault('primary_channel', 'unknown')
        primitives.setdefault('offer_name', 'unknown')
        primitives.setdefault('lead_count', 0)
        primitives.setdefault('weekly_interactions', 0)
        primitives.setdefault('outcomes', {})

        return primitives

    # ─── reason_org_chart ─────────────────────────────────────────────────────

    def reason_org_chart(
        self,
        primitives: Optional[dict] = None,
    ) -> list[str]:
        """
        AI-powered org chart reasoning.
        Not a static map — reasons from actual primitives to determine
        which roles the company needs RIGHT NOW at this exact stage.

        Falls back to STAGE_ROLE_MAP if AI call fails.
        """
        if primitives is None:
            primitives = self.detect_primitives()

        try:
            from execution.runtime.model_router import get_router, TaskType

            # Discover available agent templates from soul docs on disk
            template_dir = f'{_ROOT}/agents'
            excluded = {'ceo_agent.md', 'portfolio_advisor.md', 'CLAUDE.md'}
            available = [
                f.replace('.md', '')
                for f in os.listdir(template_dir)
                if f.endswith('.md') and f not in excluded
            ]

            router = get_router(self.ctx)

            result = router.call_with_fallback(
                TaskType.ANALYSIS,
                prompt=(
                    'You are a CEO Agent for a company.\n'
                    'Based on these primitives, determine which agent roles are needed NOW.\n\n'
                    'BUSINESS STATE:\n'
                    f'Stage: {primitives.get("stage", 1)}\n'
                    f'Revenue: ${primitives.get("current_revenue", 0)}/mo\n'
                    f'Clients: {primitives.get("client_count", 0)}\n'
                    f'Channel: {primitives.get("primary_channel", "unknown")}\n'
                    f'Offer: {primitives.get("offer_name", "unknown")}\n'
                    f'Leads: {primitives.get("lead_count", 0)}\n'
                    f'Weekly interactions: {primitives.get("weekly_interactions", 0)}\n\n'
                    f'AVAILABLE TEMPLATES:\n'
                    f'{chr(10).join(available)}\n\n'
                    'RULES:\n'
                    '- executive_assistant ALWAYS first\n'
                    '- Stage 1: minimum viable team only\n'
                    '- Stage 2: add scale roles\n'
                    '- Stage 3: full team\n'
                    '- Only include roles that add value at this exact stage\n\n'
                    'Return comma-separated role names.\n'
                    'Example: executive_assistant,outreach_agent'
                ),
                max_tokens=60,
            )

            roles = [
                r.strip()
                for r in result.split(',')
                if r.strip() in available
            ]

            if 'executive_assistant' not in roles:
                roles.insert(0, 'executive_assistant')

            print(f'[CEOAgent] Org chart: {roles}')
            return roles

        except Exception as e:
            print(f'[CEOAgent] Org reasoning fallback: {e}')
            stage = primitives.get('stage', 1)
            return STAGE_ROLE_MAP.get(stage, STAGE_ROLE_MAP[1])

    # ─── evaluate_stage_transition ────────────────────────────────────────────

    def evaluate_stage_transition(self, primitives: dict) -> bool:
        """
        Check whether the company has crossed a stage upgrade threshold.
        Stage gates mirror STAGE_PROOF_GATES from business_instance.py.
        """
        stage   = primitives.get('stage', 1)
        revenue = primitives.get('current_revenue', 0)
        clients = primitives.get('client_count', 0)

        if stage == 1:
            return revenue > 5000 or clients > 5
        if stage == 2:
            return revenue > 50000 or clients > 20
        return False

    # ─── spin_up_org ──────────────────────────────────────────────────────────

    def spin_up_org(self, primitives: dict) -> dict:
        """
        Configure org chart for the current stage.
        Determines roles, logs the org chart state.
        Returns the active role list.
        """
        roles = self.reason_org_chart(primitives)
        print(f'[CEOAgent] Org spun up — roles: {roles}')
        return {'roles': roles, 'stage': primitives.get('stage', 1)}

    # ─── check_and_evolve ────────────────────────────────────────────────────

    def check_and_evolve(self) -> dict:
        """
        Full evolution cycle.
        Detects primitives → checks stage gate → evolves org if threshold crossed.
        Returns changes dict with transition details and Discord message.
        Idempotent — safe to call daily.
        """
        primitives = self.detect_primitives()
        changes: dict = {}

        if self.evaluate_stage_transition(primitives):
            old_stage = primitives.get('stage', 1)
            new_stage = old_stage + 1

            # Write new stage to BIS
            try:
                from state.business.business_instance import BusinessInstanceManager
                from state.storage.db import get_conn, resolve_venture
                venture_id = self.ctx.active_venture_id or 'lyfe_institute'
                with get_conn(self.ctx.org_id) as cur:
                    resolve_venture(venture_id)
                bim = BusinessInstanceManager(self.ctx)
                bim.advance_stage(venture_id, {'auto_detected': True})
            except Exception as e:
                print(f'[CEOAgent] advance_stage failed: {e}')

            # Update primitives with new stage for org chart reasoning
            primitives['stage'] = new_stage
            new_roles = self.reason_org_chart(primitives)
            self.spin_up_org(primitives)

            changes = {
                'stage_transition': {
                    'from':      old_stage,
                    'to':        new_stage,
                    'new_roles': new_roles,
                },
                'message': (
                    f'**Stage transition detected**\n'
                    f'Stage {old_stage} → Stage {new_stage}\n\n'
                    f'New roles activated:\n'
                    f'{chr(10).join(new_roles)}\n\n'
                    f'Your company has grown. New capabilities are live.'
                ),
            }

            print(f'[CEOAgent] Stage transition: {old_stage} → {new_stage}')

        return changes

    # ─── get_active_constraint ───────────────────────────────────────────────

    def get_active_constraint(
        self,
        venture_id: str = None,
    ) -> dict:
        """Active constraint from live data."""
        try:
            from control_plane.agents.ceo_intelligence import (
                diagnose_constraint,
            )
            vid = (
                venture_id
                or self.ctx.active_venture_id
                or 'lyfe_institute'
            )
            return diagnose_constraint(
                vid, self.ctx
            )
        except Exception as e:
            print(f'[CEOAgent] constraint: {e}')
            return {
                'constraint': 'leads',
                'recommendation':
                    'Increase outreach volume.',
                'active_agents': [
                    'research_agent',
                    'outreach_agent',
                ],
                'idle_agents': [],
            }

    # ─── generate_brief ──────────────────────────────────────────────────────

    def generate_brief(
        self,
        venture_id: str = None,
        venture_name: str = '',
    ) -> str:
        """Generate CEO intelligence brief."""
        try:
            from control_plane.agents.ceo_intelligence import (
                generate_ceo_brief,
            )
            vid = (
                venture_id
                or self.ctx.active_venture_id
                or 'lyfe_institute'
            )
            return generate_ceo_brief(
                vid,
                venture_name or vid,
                self.ctx,
            )
        except Exception as e:
            print(f'[CEOAgent] brief: {e}')
            return f'Brief unavailable: {e}'
