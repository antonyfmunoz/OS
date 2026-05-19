"""
Primitives — stage-aware business rules and contextual reasoning engine.

KnowledgePrimitive        — structured principle with validity conditions matrix.
                             Encodes when a principle applies and when it does NOT
                             based on stage, context, and prerequisites.
PRIMITIVE_LIBRARY         — canonical library of populated primitives.
PrimitiveRegistry         — compose stage-appropriate business context for
                             CognitiveLoop PERCEIVE injection (step 1f)
ContextualReasoningEngine — evaluate whether advice is appropriate for the
                             current BIS stage; used by GENERATE filter

Stage 1 (Validation) primitives reject premature advice about hiring, scaling,
paid ads, and outsourcing — the system corrects itself before returning output.

Usage:
    from state.context.context import load_context_from_env
    from understanding.ontology.primitives import (
        PrimitiveRegistry, ContextualReasoningEngine,
        PRIMITIVE_LIBRARY, KnowledgePrimitive,
    )

    ctx = load_context_from_env()

    pr = PrimitiveRegistry(ctx)
    context_str = pr.compose_business_context('lyfe_institute')
    # inject into prompt

    cre = ContextualReasoningEngine(ctx)
    stage_ctx = cre.get_current_context('lyfe_institute')
    evaluation = cre.evaluate_principle('Should I hire a salesperson?', stage_ctx)
    # {'applies': False, 'warning': '...', 'what_applies_instead': '...'}
"""

from dataclasses import dataclass, field
from state.context.context import EntrepreneurOSContext


# ─── KnowledgePrimitive ───────────────────────────────────────────────────────

@dataclass
class KnowledgePrimitive:
    """
    A single business principle with full validity conditions.

    stage_applicability maps stage int to bool:
        {1: False, 2: True, 3: True}
    A stage 1 founder should NOT receive advice marked False at stage 1.

    validity_conditions is a list of condition dicts:
        {
            'context': 'bootstrapped_pre_revenue',
            'stage_min': int,              # optional
            'stage_max': int,              # optional
            'applies': bool,
            'modification': str,           # optional — adjusted form
            'warning': str,                # shown when it does not apply
            'what_applies_instead': str,   # redirect to right primitive
        }

    prerequisite_ids lists primitives that must apply first.
    common_misapplication documents the most frequent wrong application.
    when_it_applies is plain-language guidance.
    """
    id: str
    principle: str
    domain: str
    evidence: list[str]
    application: str
    exception: str
    source: str
    confidence: float = 1.0
    stage_applicability: dict = field(default_factory=dict)
    validity_conditions: list[dict] = field(default_factory=list)
    prerequisite_ids: list[str] = field(default_factory=list)
    common_misapplication: str = ''
    when_it_applies: str = ''


# ─── PRIMITIVE_LIBRARY ────────────────────────────────────────────────────────

PRIMITIVE_LIBRARY: dict[str, KnowledgePrimitive] = {

    'offer_optimization': KnowledgePrimitive(
        id='offer_optimization',
        principle=(
            'An irresistible offer eliminates price '
            'objections by making the value so clear '
            'the decision feels obvious.'
        ),
        domain='sales',
        evidence=['Hormozi $100M Offers framework'],
        application=(
            'Stack value, reduce risk, increase '
            'certainty of outcome for buyer.'
        ),
        exception=(
            'Optimizing an offer for unvalidated '
            'demand is polishing noise.'
        ),
        source='Hormozi',
        stage_applicability={
            1: False,  # no demand proof yet
            2: True,   # first sales proven
            3: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': False,
            'warning': (
                'You have not proven demand yet. '
                'Optimizing the offer is premature.'
            ),
            'what_applies_instead': (
                'conversation_first — talk to '
                '20 people first. The offer emerges '
                'from what you learn.'
            ),
            'when_it_applies': (
                'After 3-5 sales from the same channel.'
            ),
        }],
        common_misapplication=(
            'Building the perfect offer before '
            'having a single conversation with '
            'a potential customer.'
        ),
    ),

    'hire_salesperson': KnowledgePrimitive(
        id='hire_salesperson',
        principle=(
            'A dedicated salesperson multiplies '
            'revenue by freeing the founder for '
            'higher leverage activities.'
        ),
        domain='hiring',
        evidence=['Standard scaling playbook'],
        application=(
            'Hire when the sales process is proven '
            'and repeatable.'
        ),
        exception=(
            'Hiring a salesperson for an unproven '
            'process trains someone to fail.'
        ),
        source='general',
        stage_applicability={
            1: False,
            2: False,
            3: True,
            4: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': False,
            'warning': (
                'Stage 1 rule: founder closes first. '
                'You have not proven the sale works.'
            ),
            'what_applies_instead': (
                'Founder does all sales until '
                '10 consistent closes from same channel.'
            ),
            'when_it_applies': (
                'Stage 3: after repeatable channel '
                'is proven and revenue supports hire.'
            ),
        }],
        common_misapplication=(
            'Hiring a salesperson to solve a '
            'lead generation problem.'
        ),
    ),

    'hire_top_down': KnowledgePrimitive(
        id='hire_top_down',
        principle=(
            'Hire VP first, they build the team. '
            'A-players attract A-players.'
        ),
        domain='hiring',
        evidence=['Standard funded startup playbook'],
        application=(
            'VP sets culture, recruits team, '
            'moves faster than bottom-up hiring.'
        ),
        exception=(
            'Only works when you have capital '
            'and systems for them to operate in.'
        ),
        source='general',
        stage_applicability={
            1: False,
            2: False,
            3: False,
            4: True,  # funded or strong revenue
        },
        validity_conditions=[
            {
                'context': 'bootstrapped_pre_revenue',
                'applies': False,
                'warning': (
                    'You have no capital and no systems. '
                    'A VP has nothing to operate in.'
                ),
                'what_applies_instead': (
                    'hire_bottom_up — replace yourself '
                    'first, hire for the task you do '
                    'most that generates least leverage.'
                ),
                'when_it_applies': (
                    'When you have funding or $50K+/month '
                    'in revenue and need to scale a team.'
                ),
            },
            {
                'context': 'bootstrapped_early_revenue',
                'applies': False,
                'modification': (
                    'Hire the constraint, not a VP. '
                    'Find the bottleneck and hire '
                    'exactly that.'
                ),
                'when_it_applies': (
                    'Stage 4+ with proven revenue base.'
                ),
            },
        ],
        common_misapplication=(
            'Applying funded startup hiring advice '
            'to a bootstrapped business with no '
            'revenue or systems.'
        ),
    ),

    'hire_bottom_up': KnowledgePrimitive(
        id='hire_bottom_up',
        principle=(
            'Hire to replace yourself. Find the '
            'task you do most that generates '
            'least leverage. Hire exactly that.'
        ),
        domain='hiring',
        evidence=['Bootstrap hiring playbook'],
        application=(
            'Free yourself for highest leverage work. '
            'Cost must be covered by revenue. '
            'Never hire on hope.'
        ),
        exception=(
            'Do not hire before revenue supports it.'
        ),
        source='general',
        stage_applicability={
            1: False,  # not yet, no revenue
            2: True,   # first hire justified
            3: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': False,
            'warning': 'No revenue to support a hire.',
            'what_applies_instead': (
                'Founder does everything at Stage 1. '
                'First hire comes after first revenue.'
            ),
            'when_it_applies': (
                'When revenue consistently covers '
                'the cost of the hire.'
            ),
        }],
        common_misapplication=(
            'Hiring before revenue is consistent.'
        ),
    ),

    'paid_advertising': KnowledgePrimitive(
        id='paid_advertising',
        principle=(
            'Paid ads scale a proven offer '
            'to a proven audience.'
        ),
        domain='marketing',
        evidence=['Direct response marketing'],
        application=(
            'Pour fuel on a fire that already exists.'
        ),
        exception=(
            'Paid ads on an unproven offer '
            'just accelerates learning that '
            'the offer does not convert.'
        ),
        source='general',
        stage_applicability={
            1: False,
            2: False,
            3: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': False,
            'warning': (
                'You have not proven the offer '
                'converts organically. Paid ads '
                'on an unproven offer burns money.'
            ),
            'what_applies_instead': (
                'Organic outreach first. Prove the '
                'offer converts. Then scale with paid.'
            ),
            'when_it_applies': (
                'After consistent organic conversions '
                'from the same message and audience.'
            ),
        }],
        common_misapplication=(
            'Using paid ads to discover '
            'messaging instead of to scale '
            'proven messaging.'
        ),
    ),

    'conversation_first': KnowledgePrimitive(
        id='conversation_first',
        principle=(
            'Before building anything, have 20 '
            'conversations with your ICP. '
            'The product emerges from what you learn.'
        ),
        domain='validation',
        evidence=[
            'Mom Test — Rob Fitzpatrick',
            'Customer development methodology',
        ],
        application=(
            'Ask about their reality not your idea. '
            'Listen for problems not validation.'
        ),
        exception=(
            'Skip this if you are already '
            'generating revenue from this audience.'
        ),
        source='Fitzpatrick',
        stage_applicability={
            1: True,   # this is THE Stage 1 primitive
            2: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': True,
            'modification': (
                'This is your primary activity. '
                'Not building. Not optimizing. Talking.'
            ),
        }],
        common_misapplication=(
            'Asking "would you buy this?" instead '
            'of "tell me about the last time you '
            'had this problem."'
        ),
        when_it_applies='Always at Stage 1.',
    ),

    'outreach_before_content': KnowledgePrimitive(
        id='outreach_before_content',
        principle=(
            'Direct outreach closes faster '
            'than content at Stage 1. '
            'Content is a long game.'
        ),
        domain='sales',
        evidence=['Stage 1 validation pattern'],
        application=(
            'DM the people who match your ICP. '
            'Do not wait for them to find you.'
        ),
        exception=(
            'Once you have revenue and proof, '
            'content compounds and outreach '
            'becomes less necessary.'
        ),
        source='general',
        stage_applicability={
            1: True,
            2: True,
            3: False,  # content takes over
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': True,
            'modification': (
                'Outreach is primary. '
                'Content is secondary. '
                'Ratio: 80% outreach, 20% content.'
            ),
        }],
        common_misapplication=(
            'Building an audience before '
            'proving the offer converts.'
        ),
    ),

    'retention_over_acquisition': KnowledgePrimitive(
        id='retention_over_acquisition',
        principle=(
            'Keeping a customer costs 5x less than '
            'acquiring a new one. Retention is the '
            'foundation of sustainable growth.'
        ),
        domain='growth',
        evidence=[
            'Bain & Company retention research',
            'SaaS metrics benchmarks',
        ],
        application=(
            'Fix churn before scaling acquisition. '
            'A leaky bucket never fills.'
        ),
        exception=(
            'At Stage 1 with zero customers, '
            'acquisition comes first by necessity.'
        ),
        source='general',
        stage_applicability={
            1: False,
            2: True,
            3: True,
            4: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': False,
            'what_applies_instead': (
                'acquisition_first — you need '
                'customers before you can retain them'
            ),
            'when_it_applies': (
                'After first 5-10 customers acquired'
            ),
        }],
        common_misapplication=(
            'Optimizing retention before '
            'proving anyone wants the product.'
        ),
    ),

    'unit_economics': KnowledgePrimitive(
        id='unit_economics',
        principle=(
            'Every transaction must be profitable '
            'on its own before scaling. '
            'CAC < LTV is non-negotiable.'
        ),
        domain='finance',
        evidence=[
            'First principles business math',
            'VC investment criteria',
        ],
        application=(
            'Know your CAC, LTV, and payback period '
            'before spending on growth.'
        ),
        exception=(
            'VC-funded businesses can run negative '
            'unit economics temporarily to capture '
            'market share. Bootstrapped cannot.'
        ),
        source='general',
        stage_applicability={
            1: True,
            2: True,
            3: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': True,
            'modification': (
                'At Stage 1 calculate manually: '
                'cost to acquire one customer vs '
                'what they pay. Must be positive.'
            ),
        }],
        common_misapplication=(
            'Scaling before unit economics are proven. '
            'Losing money on every customer '
            'and hoping to make it up in volume.'
        ),
        when_it_applies='Always.',
    ),

    'pricing_psychology': KnowledgePrimitive(
        id='pricing_psychology',
        principle=(
            'Price signals value. Low price '
            'attracts bad clients and signals '
            'low quality. Charge what it is worth.'
        ),
        domain='sales',
        evidence=[
            'Hormozi pricing frameworks',
            'Cialdini social proof research',
        ],
        application=(
            'Price based on value delivered '
            'not cost to deliver. '
            'Anchor high, justify with ROI.'
        ),
        exception=(
            'Penetration pricing works when '
            'you need social proof fast and '
            'can afford to subsidize early clients.'
        ),
        source='Hormozi',
        stage_applicability={
            1: True,
            2: True,
            3: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': True,
            'modification': (
                'For Initiate Arena at $750: '
                'frame as investment not cost. '
                'ROI anchor: what does staying '
                'stuck cost you per month?'
            ),
        }],
        common_misapplication=(
            'Lowering price to close hesitant buyers. '
            'Price objections are usually value '
            'objections in disguise.'
        ),
    ),

    'content_strategy': KnowledgePrimitive(
        id='content_strategy',
        principle=(
            'Content is a filter not a broadcast. '
            'It attracts the right people '
            'and repels the wrong ones.'
        ),
        domain='marketing',
        evidence=[
            'Hormozi content philosophy',
            'Long-term brand building research',
        ],
        application=(
            'Create content that speaks directly '
            'to your ICP pain. Volume + consistency '
            'compounds over time.'
        ),
        exception=(
            'Content is a long game. '
            'At Stage 1 outreach closes faster.'
        ),
        source='Hormozi',
        stage_applicability={
            1: False,  # outreach first
            2: True,
            3: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': False,
            'warning': (
                'Content takes 3-6 months to compound. '
                'You need revenue now not in 6 months.'
            ),
            'what_applies_instead': (
                'outreach_before_content — DM people '
                'directly instead of waiting for '
                'them to find your content.'
            ),
            'when_it_applies': (
                'Stage 2: after first 5-10 sales '
                'proven through outreach.'
            ),
        }],
        common_misapplication=(
            'Building an audience instead of '
            'a business. Followers ≠ revenue.'
        ),
    ),

    'referral_flywheel': KnowledgePrimitive(
        id='referral_flywheel',
        principle=(
            'A happy customer is your best '
            'salesperson. Build referral into '
            'the product and process.'
        ),
        domain='growth',
        evidence=[
            'NPS research',
            'Dropbox referral program case study',
        ],
        application=(
            'Ask for referrals at peak happiness: '
            'immediately after first win, '
            'not at the end of the program.'
        ),
        exception=(
            'Cannot build a referral flywheel '
            'without happy customers first.'
        ),
        source='general',
        stage_applicability={
            1: False,
            2: True,
            3: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': False,
            'what_applies_instead': (
                'conversation_first — need customers '
                'before referrals are possible'
            ),
            'when_it_applies': (
                'After first client achieves result.'
            ),
        }],
        common_misapplication=(
            'Asking for referrals before the '
            'client has achieved any result.'
        ),
    ),

    'cash_flow_management': KnowledgePrimitive(
        id='cash_flow_management',
        principle=(
            'Cash flow kills more businesses than '
            'lack of profit. Know your runway. '
            'Revenue is vanity, cash is reality.'
        ),
        domain='finance',
        evidence=[
            'Small business failure statistics',
            'First principles finance',
        ],
        application=(
            'Track money in vs money out weekly. '
            'Know exactly how many months you '
            'can operate at current burn rate.'
        ),
        exception=(
            'VC-funded companies operate differently. '
            'Bootstrapped businesses must be '
            'cash-flow positive or die.'
        ),
        source='general',
        stage_applicability={
            1: True,
            2: True,
            3: True,
        },
        validity_conditions=[{
            'context': 'bootstrapped_pre_revenue',
            'applies': True,
            'modification': (
                'At Stage 1 with no revenue: '
                'your runway is your personal savings. '
                'Know exactly how long it lasts. '
                'Urgency is your friend.'
            ),
        }],
        common_misapplication=(
            'Confusing revenue with profit. '
            'Spending on tools and infrastructure '
            'before generating revenue.'
        ),
        when_it_applies='Always.',
    ),
}


# ─── Stage primitive definitions ──────────────────────────────────────────────

STAGE_PRIMITIVES: dict[int, dict] = {
    1: {
        'name': 'Validation',
        'focus': 'Prove the offer works. Get one paying customer.',
        'rules': [
            'Talk to prospects directly — no automation until 10 paying clients',
            'Manual outreach only — DMs, referrals, warm network',
            'Close manually — be on every sales call yourself',
            'Charge full price immediately — discounting destroys perceived value',
            'Fix the offer from live objections — not assumptions',
            'One channel only — go deep, not wide',
            'Your time is the asset — spend it on conversations that can close',
        ],
        'not_yet': [
            'hire',
            'build a team',
            'outsource',
            'automate outreach',
            'run paid',
            'launch ads',
            'paid ads',
            'scale',
            'raise',
            'invest',
            'expand',
        ],
        'what_applies_instead': (
            'Stage 1 priority: direct outreach → qualify → book call → close. '
            'Repeat manually until $10K/month. Then systematize what works.'
        ),
    },
    2: {
        'name': 'Repeatability',
        'focus': 'Prove you can close 10+ clients consistently.',
        'rules': [
            'Document what is working — build the playbook from live closes',
            'Hire one person for a specific bottleneck you have proven exists',
            'Light automation of proven manual processes only',
            'Second channel only after first channel is converting predictably',
            'Unit economics must be known before any paid acquisition',
        ],
        'not_yet': [
            'raise capital',
            'multiple hires',
            'paid acquisition at scale',
            'expand internationally',
        ],
        'what_applies_instead': (
            'Stage 2 priority: build the playbook, hire one person for the proven '
            'bottleneck, automate what you have already done 20 times manually.'
        ),
    },
    3: {
        'name': 'Scale',
        'focus': 'Pour fuel on a proven, profitable process.',
        'rules': [
            'Paid acquisition is appropriate — CAC must be known and below LTV/3',
            'Team growth is justified — but every role must have a clear ROI',
            'Infrastructure investment returns value at this stage',
            'Systems and automation compound existing proven processes',
        ],
        'not_yet': [],
        'what_applies_instead': (
            'Scale with intent — every dollar deployed must have a measurable outcome.'
        ),
    },
    4: {
        'name': 'Optimization',
        'focus': 'Maximize efficiency and margin across proven revenue streams.',
        'rules': [
            'Process engineering and waste elimination drive outsized returns',
            'Hiring specialists over generalists — precision over coverage',
            'M&A optionality opens at this stage',
        ],
        'not_yet': [],
        'what_applies_instead': 'Optimize before expanding — margin before revenue.',
    },
    5: {
        'name': 'Expansion',
        'focus': 'Add new revenue streams, markets, or products on top of a profitable core.',
        'rules': [
            'New ventures are funded from core business cash flow',
            'Existing systems must run without the founder before expansion',
        ],
        'not_yet': [],
        'what_applies_instead': 'Expand from strength — only when the core is self-managing.',
    },
    6: {
        'name': 'Exit-Ready',
        'focus': 'Build for transferability and multiple-expansion.',
        'rules': [
            'Founder dependency is the #1 valuation killer — remove yourself from operations',
            'EBITDA multiples drive exit value — every efficiency decision compounds',
        ],
        'not_yet': [],
        'what_applies_instead': 'Build the business to run without you.',
    },
}


# ─── PrimitiveRegistry ────────────────────────────────────────────────────────

class PrimitiveRegistry:
    """
    Composes stage-appropriate business primitives for CognitiveLoop injection.
    Reads the live BIS to determine the current stage per venture.
    """

    def __init__(self, ctx: EntrepreneurOSContext):
        self.ctx = ctx

    def _get_stage(self, venture_id: str) -> int:
        """Read BIS stage. Returns 1 on any failure (safe default)."""
        try:
            from state.business.business_instance import BusinessInstanceManager
            bim     = BusinessInstanceManager(self.ctx)
            ctx_str = bim.get_context_for_agents(venture_id)
            for line in ctx_str.split('\n'):
                if line.startswith('STAGE:'):
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        stage_token = parts[1].strip().split()[0]
                        return int(stage_token)
        except Exception:
            pass
        return 1

    def compose_business_context(self, venture_id: str) -> str:
        """
        Returns a formatted string of stage-appropriate rules for prompt injection.
        Returns empty string on any failure — never blocks execution.
        """
        try:
            stage      = self._get_stage(venture_id)
            primitives = STAGE_PRIMITIVES.get(stage)
            if not primitives:
                return ''

            lines = [
                f'STAGE {stage} PRIMITIVES ({primitives["name"].upper()}):',
                f'Focus: {primitives["focus"]}',
                'Active rules:',
            ]
            for rule in primitives['rules']:
                lines.append(f'  • {rule}')
            if primitives.get('not_yet'):
                lines.append(
                    'Not applicable yet: '
                    + ', '.join(primitives['not_yet'][:6])
                )
            return '\n'.join(lines)
        except Exception:
            return ''


# ─── ContextualReasoningEngine ────────────────────────────────────────────────

class ContextualReasoningEngine:
    """
    Evaluates whether advice in a generated response is appropriate for the
    current business stage. Used by CognitiveLoop GENERATE filter (step 5b).

    Premature advice is flagged with a stage-appropriate correction prepended
    to the response — the system corrects itself before the founder sees it.
    """

    def __init__(self, ctx: EntrepreneurOSContext):
        self.ctx      = ctx
        self._registry = PrimitiveRegistry(ctx)

    def get_current_context(self, venture_id: str | None = None) -> dict:
        # Resolve default venture from BIM if not passed — no hardcoded venture
        if not venture_id:
            try:
                from state.business.business_instance import BusinessInstanceManager as _BIM
                venture_id = _BIM(self.ctx).get_default_venture_id()
            except Exception:
                venture_id = None
        """
        Return the current stage context dict.
        Used by CognitiveLoop to evaluate stage appropriateness.
        """
        try:
            stage      = self._registry._get_stage(venture_id)
            primitives = STAGE_PRIMITIVES.get(stage, {})
            return {
                'stage':      stage,
                'stage_name': primitives.get('name', 'Unknown'),
                'focus':      primitives.get('focus', ''),
                'not_yet':    primitives.get('not_yet', []),
                'venture_id': venture_id,
            }
        except Exception:
            return {
                'stage':      1,
                'stage_name': 'Validation',
                'focus':      '',
                'not_yet':    [],
                'venture_id': venture_id,
            }

    def evaluate_principle(self, advice: str, context: dict) -> dict:
        """
        Evaluate whether a piece of advice applies at the current stage.

        Pre-checks PRIMITIVE_LIBRARY for a structural match before
        falling through to keyword-based not_yet matching.

        Returns:
            {
                'applies':              bool,
                'warning':              str,
                'what_applies_instead': str,
            }
        """
        try:
            # Pre-check: look up matching primitive by keyword in principle text
            # This gives richer, structured responses before any AI call
            try:
                from learning.evolution.evolution_engine import EvolutionEngine
                _ee = EvolutionEngine(self.ctx)
                _venture = context.get('venture_id')  # may be None — substrate-neutral
                _adv_lower = advice.lower()
                for pid, prim in PRIMITIVE_LIBRARY.items():
                    _prim_words = prim.principle.lower().split()[:5]
                    if any(word in _adv_lower for word in _prim_words):
                        result = _ee.is_primitive_unlocked(pid, _venture)
                        if not result.get('applies', True):
                            return result  # return immediately, no further check needed
            except Exception:
                pass  # pre-check is enhancement — fall through to keyword matching

            stage      = context.get('stage', 1)
            primitives = STAGE_PRIMITIVES.get(stage, {})
            not_yet    = primitives.get('not_yet', [])
            advice_lower = advice.lower()

            violated = [item for item in not_yet if item in advice_lower]
            if not violated:
                return {'applies': True, 'warning': '', 'what_applies_instead': ''}

            return {
                'applies': False,
                'warning': (
                    f'Stage {stage} ({primitives.get("name", "")}) — '
                    f'not the current priority: {", ".join(violated[:3])}'
                ),
                'what_applies_instead': primitives.get('what_applies_instead', ''),
            }
        except Exception:
            return {'applies': True, 'warning': '', 'what_applies_instead': ''}
