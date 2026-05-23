"""
BusinessInstance — venture-stage context layer.

Tracks where a venture is in its growth journey (Stage 1–6),
the offer, ICP, and channels. Injected into agent prompts
to give context-aware guidance at every stage.

Usage:
    from substrate.state.business.business_instance import BusinessInstance, BusinessInstanceManager
    ctx = load_context_from_env()
    bim = BusinessInstanceManager(ctx)
    bis = bim.get_bis('lyfe_institute')
    context = bim.get_context_for_agents('lyfe_institute')
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json
from datetime import datetime, timezone

# ─── Stage definitions ────────────────────────────────────────────────────────

STAGE_NAMES: dict[int, str] = {
    1: 'Validation',
    2: 'Offer',
    3: 'Acquisition',
    4: 'Systems',
    5: 'Scale',
    6: 'Portfolio',
}

STAGE_PROOF_GATES: dict[int, str] = {
    1: 'First sale closed',
    2: '3 sales from same channel',
    3: '10 sales, ops documented',
    4: '30 sales, team handling ops',
    5: '$10K/month sustained 3 months',
    6: 'Multiple revenue streams profitable',
}

STAGE_GUIDANCE: dict[int, dict] = {
    1: {
        'focus': 'Get one person to pay you money',
        'next_actions': [
            'Identify 10 people with the exact problem',
            'Have a real conversation with each one',
            'Make a direct offer to the most qualified',
            'Close the first sale manually',
        ],
        'what_not_to_do': [
            'Build a website before your first sale',
            'Create content before validating demand',
            'Hire anyone before proof of concept',
            'Optimize anything before it exists',
        ],
    },
    2: {
        'focus': 'Prove the same channel works 3 times',
        'next_actions': [
            'Document exactly how you closed the first sale',
            'Repeat that process on 2 more similar leads',
            'Track conversion rate and cycle time',
            'Identify the single best acquisition channel',
        ],
        'what_not_to_do': [
            'Add more channels before mastering one',
            'Hire a salesperson before you can close yourself',
            'Build complex funnels before simple ones work',
        ],
    },
    3: {
        'focus': 'Make acquisition repeatable and scalable',
        'next_actions': [
            'Document the full sales process as an SOP',
            'Hit 10 sales total',
            'Identify unit economics (CAC, LTV)',
            'Build first repeatable marketing workflow',
        ],
        'what_not_to_do': [
            'Scale spend before unit economics proven',
            'Hire operations before sales is systemized',
        ],
    },
    4: {
        'focus': 'Remove yourself from operations',
        'next_actions': [
            'Document every core process as an SOP',
            'Hire first team member for ops',
            'Build dashboards that show health without you',
            'Define KPIs for every department',
        ],
        'what_not_to_do': [
            'Scale headcount before systems exist',
            'Add new products before core is running without you',
        ],
    },
    5: {
        'focus': 'Grow without adding chaos',
        'next_actions': [
            'Scale the proven acquisition channel',
            'Hire into every bottleneck systematically',
            'Build financial model and forecasting',
            'Pursue strategic partnerships',
        ],
        'what_not_to_do': [
            'Enter new markets before dominating current one',
            'Raise money before clear unit economics',
        ],
    },
    6: {
        'focus': 'Build portfolio of profitable assets',
        'next_actions': [
            'Systematize first company to run without you',
            'Identify second venture using same skills',
            'Build portfolio-level financial view',
            'Consider strategic exits or acquisitions',
        ],
        'what_not_to_do': [
            'Start second company before first is systematized',
            'Neglect core business while building portfolio',
        ],
    },
}


# ─── Data model ───────────────────────────────────────────────────────────────

@dataclass
class BusinessInstance:
    org_id: str
    venture_id: str           # slug e.g. "lyfe_institute"
    name: str
    industry: str
    business_model: str
    current_stage: int = 1
    stage_name: str = 'Validation'
    stage_proof: dict = field(default_factory=dict)
    stage_unlocked_at: Optional[str] = None

    # The offer
    offer_name: str = ''
    offer_price: float = 0.0
    offer_type: str = 'one-time'
    offer_promise: str = ''
    offer_delivery: str = ''
    offer_transformation: str = ''

    # The customer
    icp_description: str = ''
    icp_demographics: dict = field(default_factory=dict)
    icp_psychographics: dict = field(default_factory=dict)
    icp_pain_points: list = field(default_factory=list)
    icp_language: list = field(default_factory=list)
    icp_alternatives: list = field(default_factory=list)

    # Market
    tam_estimate: str = ''
    market_position: str = ''
    main_competitors: list = field(default_factory=list)
    differentiators: list = field(default_factory=list)

    # Channels
    primary_channel: str = ''
    secondary_channels: list = field(default_factory=list)
    channel_metrics: dict = field(default_factory=dict)

    # Financial
    monthly_revenue: float = 0.0
    monthly_target: float = 0.0
    cac: Optional[float] = None
    ltv: Optional[float] = None
    unit_economics_proven: bool = False

    # Team
    founder_name: str = ''
    team_members: list = field(default_factory=list)
    founder_hours_per_week: int = 40
    capital_available: float = 0.0
    runway_months: Optional[int] = None

    # North star
    north_star: str = ''
    time_horizon: str = '3 months'
    success_definition: str = ''

    # AI persona (user-configurable)
    ai_name: str = 'DEX'
    ai_personality: str = (
        'Direct, intelligent, always on. '
        'Challenges bad thinking. '
        'Never agrees just to agree. '
        'Knows the business inside out.'
    )
    ai_soul_doc_path: str = ''  # path to user-generated soul doc (set by setup wizard)

    # OS subscriptions (Layer 2)
    os_subscriptions: list = field(
        default_factory=lambda: ['entrepreneur_os']
    )
    # Options: 'entrepreneur_os', 'creator_os', 'lyfe_os'
    # Full trinity: all three


# ─── Manager ──────────────────────────────────────────────────────────────────

class BusinessInstanceManager:
    """
    Persist and retrieve BusinessInstance data via the ventures table
    config_json column. Provides stage guidance and agent context injection.
    """

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def save_bis(self, bis: BusinessInstance) -> bool:
        """Persist BIS to ventures.config_json. Creates venture row if needed."""
        from substrate.state.stores.venture_store import VentureStore
        data = asdict(bis)
        VentureStore().save_venture(
            org_id=self.ctx.org_id,
            venture_id_slug=bis.venture_id,
            name=bis.name,
            config=data,
        )
        return True

    def get_default_venture_id(self) -> Optional[str]:
        """
        Return the default venture_id for the current org — substrate-neutral.

        Resolution order:
        1. EOS_DEFAULT_VENTURE env var (operator override)
        2. First venture row for this org_id (alphabetical for determinism)
        3. None (caller must handle — no hardcoded fallback)

        Used by gateway/primitives/tenant when a venture isn't passed explicitly.
        """
        import os as _os
        env_default = _os.getenv('EOS_DEFAULT_VENTURE', '').strip()
        if env_default:
            return env_default
        try:
            from substrate.state.storage.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT name FROM ventures
                    WHERE org_id = %s
                    ORDER BY created_at ASC NULLS LAST, name ASC
                    LIMIT 1
                    """,
                    (self.ctx.org_id,),
                )
                row = cur.fetchone()
                if row:
                    return row.get('name')
        except Exception as e:
            print(f'[BIM] get_default_venture_id failed: {e}')
        return None

    def get_bis(self, venture_id: str) -> Optional[BusinessInstance]:
        """Load BIS from ventures.config_json. Returns None if not found."""
        from substrate.state.storage.db import get_conn, resolve_venture
        with get_conn(self.ctx.org_id) as cur:
            # resolve_venture inside get_conn so cache is populated
            venture_uuid = resolve_venture(venture_id)
            if not venture_uuid:
                return None
            cur.execute(
                "SELECT config_json FROM ventures WHERE org_id = %s AND id = %s",
                (self.ctx.org_id, venture_uuid),
            )
            row = cur.fetchone()
        if not row or not row['config_json']:
            return None
        data = row['config_json']
        if isinstance(data, str):
            data = json.loads(data)
        try:
            return BusinessInstance(**data)
        except Exception:
            return None

    def get_stage_guidance(self, venture_id: str) -> dict:
        """Return stage-appropriate focus, actions, and proof gate."""
        bis = self.get_bis(venture_id)
        stage = bis.current_stage if bis else 1
        guidance = STAGE_GUIDANCE.get(stage, {})
        return {
            'current_stage':  stage,
            'stage_name':     STAGE_NAMES.get(stage, ''),
            'proof_needed':   STAGE_PROOF_GATES.get(stage, ''),
            'focus':          guidance.get('focus', ''),
            'next_actions':   guidance.get('next_actions', []),
            'what_not_to_do': guidance.get('what_not_to_do', []),
        }

    def create_from_wizard(self, answers: dict) -> 'BusinessInstance':
        """
        Create a BusinessInstance from onboarding wizard answers dict.
        Uses CognitiveLoop to fill any missing gaps.
        Saves to Neon and returns the complete BIS.
        """
        # Build BIS directly from answers, with sensible defaults
        bis = BusinessInstance(
            org_id=self.ctx.org_id,
            venture_id=answers.get('venture_id', 'new_venture'),
            name=answers.get('name', 'New Venture'),
            industry=answers.get('industry', 'technology'),
            business_model=answers.get('business_model', 'service'),
            current_stage=answers.get('current_stage', 1),
            stage_name=STAGE_NAMES.get(answers.get('current_stage', 1), 'Validation'),
            offer_name=answers.get('offer_name', ''),
            offer_price=float(answers.get('offer_price', 0.0)),
            offer_type=answers.get('offer_type', 'one-time'),
            offer_promise=answers.get('offer_promise', ''),
            offer_delivery=answers.get('offer_delivery', ''),
            offer_transformation=answers.get('offer_transformation', ''),
            icp_description=answers.get('icp_description', ''),
            icp_demographics=answers.get('icp_demographics', {}),
            icp_psychographics=answers.get('icp_psychographics', {}),
            icp_pain_points=answers.get('icp_pain_points', []),
            icp_language=answers.get('icp_language', []),
            icp_alternatives=answers.get('icp_alternatives', []),
            tam_estimate=answers.get('tam_estimate', ''),
            market_position=answers.get('market_position', ''),
            main_competitors=answers.get('main_competitors', []),
            differentiators=answers.get('differentiators', []),
            primary_channel=answers.get('primary_channel', ''),
            secondary_channels=answers.get('secondary_channels', []),
            channel_metrics=answers.get('channel_metrics', {}),
            monthly_revenue=float(answers.get('monthly_revenue', 0.0)),
            monthly_target=float(answers.get('monthly_target', 0.0)),
            cac=answers.get('cac'),
            ltv=answers.get('ltv'),
            unit_economics_proven=bool(answers.get('unit_economics_proven', False)),
            founder_name=answers.get('founder_name', ''),
            team_members=answers.get('team_members', []),
            founder_hours_per_week=int(answers.get('founder_hours_per_week', 40)),
            capital_available=float(answers.get('capital_available', 0.0)),
            runway_months=answers.get('runway_months'),
            north_star=answers.get('north_star', ''),
            time_horizon=answers.get('time_horizon', '3 months'),
            success_definition=answers.get('success_definition', ''),
        )

        # Use CognitiveLoop to fill gaps if key fields are missing
        gaps = []
        if not bis.offer_promise:
            gaps.append('offer_promise')
        if not bis.icp_description:
            gaps.append('icp_description')
        if not bis.market_position:
            gaps.append('market_position')

        if gaps:
            try:
                from control_plane.runtime.cognitive_loop import CognitiveLoop
                from execution.runtime.agent_runtime import TaskType
                loop = CognitiveLoop(self.ctx)
                gap_prompt = (
                    f"For a {bis.business_model} business called '{bis.name}' "
                    f"in {bis.industry}, fill in these missing fields as JSON:\n"
                    f"Fields needed: {gaps}\n"
                    f"Context: offer={bis.offer_name}, price=${bis.offer_price}"
                )
                result = loop.run(
                    input=gap_prompt,
                    agent='ceo_agent',
                    task_type=TaskType.ANALYZE,
                    venture_id=bis.venture_id,
                )
                import json as _json
                try:
                    filled = _json.loads(result.output or '{}', strict=False)
                    for field in gaps:
                        if field in filled and filled[field]:
                            setattr(bis, field, filled[field])
                except Exception:
                    pass
            except Exception as e:
                print(f'[BIS] create_from_wizard gap-fill failed: {e}')

        self.save_bis(bis)
        return bis

    def advance_stage(self, venture_id: str, proof: dict) -> dict:
        """Advance venture to next stage if proof provided."""
        bis = self.get_bis(venture_id)
        if not bis:
            return {'advanced': False, 'reason': 'BIS not found'}
        if bis.current_stage >= 6:
            return {'advanced': False, 'reason': 'Already at max stage'}
        bis.current_stage += 1
        bis.stage_name = STAGE_NAMES[bis.current_stage]
        bis.stage_proof = proof
        bis.stage_unlocked_at = datetime.now(timezone.utc).isoformat()
        self.save_bis(bis)
        return {
            'advanced':       True,
            'new_stage':      bis.current_stage,
            'new_stage_name': bis.stage_name,
            'guidance':       self.get_stage_guidance(venture_id),
        }

    def get_context_for_agents(self, venture_id: str) -> str:
        """Return BIS context string for injection into agent system prompts."""
        bis = self.get_bis(venture_id)
        if not bis:
            return ''
        guidance = self.get_stage_guidance(venture_id)
        return (
            f"VENTURE: {bis.name}\n"
            f"OFFER: {bis.offer_name} ${bis.offer_price:.0f} ({bis.offer_type})\n"
            f"STAGE: {bis.current_stage} — {bis.stage_name}\n"
            f"FOCUS: {guidance['focus']}\n"
            f"ICP: {bis.icp_description}\n"
            f"NORTH STAR: {bis.north_star}\n"
            f"REVENUE: ${bis.monthly_revenue:,.0f}/mo (target ${bis.monthly_target:,.0f})\n"
            f"PROOF NEEDED TO ADVANCE: {guidance['proof_needed']}\n"
            f"AI NAME: {bis.ai_name}\n"
            f"Respond as {bis.ai_name} always.\n"
        )

    def format_full_summary(self, venture_id: str) -> str:
        """Return full BIS summary for /bis Telegram command."""
        bis = self.get_bis(venture_id)
        if not bis:
            return 'No BIS found for this venture.'
        guidance = self.get_stage_guidance(venture_id)
        actions_str = '\n'.join(f'  • {a}' for a in guidance['next_actions'])
        avoid_str = '\n'.join(f'  ✗ {a}' for a in guidance['what_not_to_do'])
        return (
            f"━━ BUSINESS INSTANCE ━━\n"
            f"{bis.name}\n\n"
            f"OFFER: {bis.offer_name}\n"
            f"  ${bis.offer_price:.0f} — {bis.offer_type}\n"
            f"  {bis.offer_promise}\n\n"
            f"STAGE: {bis.current_stage}/6 — {bis.stage_name}\n"
            f"  Focus: {guidance['focus']}\n"
            f"  Proof to advance: {guidance['proof_needed']}\n\n"
            f"NEXT ACTIONS:\n{actions_str}\n\n"
            f"AVOID:\n{avoid_str}\n\n"
            f"ICP: {bis.icp_description}\n"
            f"CHANNEL: {bis.primary_channel}\n"
            f"REVENUE: ${bis.monthly_revenue:,.0f} / ${bis.monthly_target:,.0f} target\n"
            f"NORTH STAR: {bis.north_star}"
        )


# ─── Standalone resolver ──────────────────────────────────────────────────────

def get_ai_name(ctx, venture_id: str = 'lyfe_institute') -> str:
    """
    Resolve AI name for this user.
    Priority: BIS.ai_name → AI_NAME env var → default 'DEX'.
    """
    try:
        bim = BusinessInstanceManager(ctx)
        bis = bim.get_bis(venture_id)
        if bis and bis.ai_name:
            return bis.ai_name
    except Exception:
        pass
    try:
        import os as _os
        name = _os.getenv('AI_NAME')
        if name:
            return name
    except Exception:
        pass
    return 'DEX'
