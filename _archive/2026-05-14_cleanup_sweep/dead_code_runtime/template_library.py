"""
TemplateLibrary — pre-composed primitive assemblies for common business types.

World-class defaults. Founder customizes the 20% specific to them.
Injected into CognitiveLoop PERCEIVE step alongside stage primitives.

Usage:
    from runtime.template_library import TemplateLibrary

    tl = TemplateLibrary()
    guidance = tl.get_stage_guidance('coaching_program', 1)
    # {'focus': '...', 'roles': [...], 'workflows': [...], 'metrics': [...]}

    context_str = tl.format_for_prompt('coaching_program', 1)
    # 'BUSINESS TEMPLATE: coaching_program\\nSTAGE 1 FOCUS: ...'
"""

from dataclasses import dataclass, field


# ─── BusinessTemplate ─────────────────────────────────────────────────────────

@dataclass
class BusinessTemplate:
    id: str
    name: str
    description: str
    transaction: dict
    stage_1_roles: list[str]
    stage_1_workflows: list[str]
    stage_1_metrics: list[str]
    stage_1_focus: str
    stage_2_roles: list[str]
    key_primitives: list[str]   # primitive IDs that apply
    icp_description: str
    channel: str
    proof_of_concept: str       # what Stage 1 proof looks like


# ─── TEMPLATE_LIBRARY ─────────────────────────────────────────────────────────

TEMPLATE_LIBRARY: dict[str, BusinessTemplate] = {

    'coaching_program': BusinessTemplate(
        id='coaching_program',
        name='Coaching / Group Program',
        description=(
            'Sell transformation to a specific ICP. '
            'One core offer, one channel, '
            'one repeating transaction.'
        ),
        transaction={
            'offer_type': 'program',
            'delivery': 'group or 1:1 coaching',
            'pricing_model': 'one-time or monthly',
            'outcome': 'identity transformation',
            'proof_of_success': 'Client reports measurable change',
        },
        stage_1_roles=[
            'Founder does everything',
            'No hires until first 10 clients',
        ],
        stage_1_workflows=[
            'ICP identification',
            'Direct outreach (DMs)',
            'Sales conversation',
            'Onboarding',
            'Delivery',
            'Testimonial collection',
        ],
        stage_1_metrics=[
            'DMs sent per day',
            'Response rate',
            'Sales calls booked',
            'Conversion rate',
            'Revenue',
        ],
        stage_1_focus=(
            'One offer. One channel. One ICP. '
            'First sale as fast as possible.'
        ),
        stage_2_roles=[
            'VA for admin and scheduling',
            'CSM for client success',
        ],
        key_primitives=[
            'conversation_first',
            'outreach_before_content',
            'offer_optimization',
        ],
        icp_description=(
            'Specific person with specific pain '
            'who has money and motivation to change'
        ),
        channel='Direct outreach (Instagram/LinkedIn)',
        proof_of_concept='First paying client',
    ),

    'agency': BusinessTemplate(
        id='agency',
        name='Service Agency',
        description=(
            'Sell done-for-you services to businesses. '
            'Revenue from retainers or projects.'
        ),
        transaction={
            'offer_type': 'service',
            'delivery': 'done-for-you',
            'pricing_model': 'retainer or project',
            'outcome': 'business result for client',
            'proof_of_success': 'Client result achieved',
        },
        stage_1_roles=[
            'Founder is the service provider',
            'First hire: junior to do execution',
        ],
        stage_1_workflows=[
            'Lead generation',
            'Discovery call',
            'Proposal',
            'Onboarding',
            'Delivery',
            'Reporting',
            'Renewal / upsell',
        ],
        stage_1_metrics=[
            'Leads in pipeline',
            'Proposals sent',
            'Close rate',
            'MRR',
            'Client retention rate',
        ],
        stage_1_focus=(
            'Land first retainer client. '
            'Deliver exceptional result. '
            'Get case study.'
        ),
        stage_2_roles=[
            'Account manager',
            'Junior executor',
        ],
        key_primitives=[
            'conversation_first',
            'hire_bottom_up',
            'outreach_before_content',
        ],
        icp_description=(
            'Business owner with specific '
            'problem you can solve'
        ),
        channel='Cold outreach + referrals',
        proof_of_concept='First retainer signed',
    ),

    'digital_product': BusinessTemplate(
        id='digital_product',
        name='Digital Product / Course',
        description=(
            'Create once, sell many times. '
            'Leveraged income model.'
        ),
        transaction={
            'offer_type': 'digital product',
            'delivery': 'self-paced online',
            'pricing_model': 'one-time purchase',
            'outcome': 'skill or knowledge gained',
            'proof_of_success': 'Student gets result',
        },
        stage_1_roles=[
            'Founder creates and sells',
            'No hires at Stage 1',
        ],
        stage_1_workflows=[
            'Audience building',
            'Content creation',
            'Launch',
            'Fulfillment',
            'Testimonials',
        ],
        stage_1_metrics=[
            'Audience size',
            'Email list',
            'Conversion rate',
            'Revenue per launch',
        ],
        stage_1_focus=(
            'Validate with a small cohort first. '
            'Teach it live before recording it.'
        ),
        stage_2_roles=[
            'Community manager',
            'Content creator',
        ],
        key_primitives=[
            'conversation_first',
            'offer_optimization',
            'paid_advertising',
        ],
        icp_description=(
            'Person who wants to learn a '
            'specific skill or achieve specific result'
        ),
        channel='Content + email list',
        proof_of_concept='First cohort completes and gets result',
    ),

    'ecommerce': BusinessTemplate(
        id='ecommerce',
        name='Ecommerce / Physical Products',
        description=(
            'Sell physical or digital products '
            'online. Revenue from transactions.'
        ),
        transaction={
            'offer_type': 'product',
            'delivery': 'shipped or digital download',
            'pricing_model': 'one-time purchase',
            'outcome': 'product received and used',
            'proof_of_success': (
                'Customer buys and returns for more'
            ),
        },
        stage_1_roles=[
            'Founder handles everything',
            'No hires until profitable',
        ],
        stage_1_workflows=[
            'Product sourcing or creation',
            'Store setup',
            'Organic marketing',
            'Order fulfillment',
            'Customer service',
            'Review collection',
        ],
        stage_1_metrics=[
            'Daily visitors',
            'Conversion rate',
            'Average order value',
            'Cost per acquisition',
            'Return rate',
            'Repeat purchase rate',
        ],
        stage_1_focus=(
            'Prove one product sells profitably '
            'through one channel before scaling.'
        ),
        stage_2_roles=[
            'Fulfillment VA',
            'Customer service VA',
        ],
        key_primitives=[
            'conversation_first',
            'outreach_before_content',
            'unit_economics',
            'paid_advertising',
        ],
        icp_description=(
            'Person with specific problem your '
            'product solves better than alternatives'
        ),
        channel='Organic social + marketplace',
        proof_of_concept=(
            'First 10 profitable orders '
            'with positive unit economics'
        ),
    ),

    'saas': BusinessTemplate(
        id='saas',
        name='SaaS / Software Product',
        description=(
            'Build software, sell subscriptions. '
            'Revenue compounds with retention.'
        ),
        transaction={
            'offer_type': 'subscription software',
            'delivery': 'web or mobile app',
            'pricing_model': 'monthly or annual subscription',
            'outcome': 'problem solved repeatedly',
            'proof_of_success': (
                'Customer stays subscribed 3+ months'
            ),
        },
        stage_1_roles=[
            'Founder is builder and seller',
            'No hires until product-market fit',
        ],
        stage_1_workflows=[
            'Customer discovery',
            'MVP build',
            'Beta user acquisition',
            'Feedback loop',
            'Iteration',
            'First paid conversion',
        ],
        stage_1_metrics=[
            'Weekly active users',
            'Activation rate',
            'Day 30 retention',
            'MRR',
            'Churn rate',
            'NPS',
        ],
        stage_1_focus=(
            'Find 10 people with the problem. '
            'Build the minimum that solves it. '
            'Charge before it is perfect.'
        ),
        stage_2_roles=[
            'First engineer if founder is non-technical',
            'Customer success for retention',
        ],
        key_primitives=[
            'conversation_first',
            'retention_over_acquisition',
            'unit_economics',
            'hire_bottom_up',
        ],
        icp_description=(
            'Professional or business with '
            'recurring pain you can automate'
        ),
        channel='Direct outreach + product-led growth',
        proof_of_concept=(
            'First 3 paying customers retained '
            'for 60+ days'
        ),
    ),
}


# ─── TemplateLibrary ──────────────────────────────────────────────────────────

class TemplateLibrary:

    def __init__(self) -> None:
        self.templates = TEMPLATE_LIBRARY

    def get_template(self, business_type: str) -> BusinessTemplate | None:
        return self.templates.get(business_type)

    def detect_business_type(self, description: str) -> str:
        """Detect which template best fits the description."""
        desc_lower = description.lower()
        if any(w in desc_lower for w in [
            'coach', 'program', 'course', 'teach',
            'transformation', 'mentor', 'group',
        ]):
            return 'coaching_program'
        if any(w in desc_lower for w in [
            'agency', 'service', 'done for you',
            'client', 'retainer',
        ]):
            return 'agency'
        if any(w in desc_lower for w in [
            'saas', 'software', 'subscription', 'app',
            'mrr', 'churn', 'retention', 'product-led',
        ]):
            return 'saas'
        if any(w in desc_lower for w in [
            'ecommerce', 'shopify', 'physical', 'ship',
            'store', 'marketplace', 'product',
        ]):
            return 'ecommerce'
        if any(w in desc_lower for w in [
            'digital', 'download', 'self-paced', 'passive',
        ]):
            return 'digital_product'
        return 'coaching_program'  # default

    def get_stage_guidance(
        self,
        business_type: str,
        current_stage: int,
    ) -> dict:
        template = self.get_template(business_type)
        if not template:
            return {}

        if current_stage == 1:
            return {
                'focus':          template.stage_1_focus,
                'roles':          template.stage_1_roles,
                'workflows':      template.stage_1_workflows,
                'metrics':        template.stage_1_metrics,
                'proof_needed':   template.proof_of_concept,
                'key_primitives': template.key_primitives,
            }
        elif current_stage == 2:
            return {
                'focus':          'Scale what works at Stage 1',
                'roles':          template.stage_2_roles,
                'key_primitives': template.key_primitives,
            }
        return {}

    def format_for_prompt(
        self,
        business_type: str,
        current_stage: int,
    ) -> str:
        """Return a compact string for injection into the system prompt."""
        guidance = self.get_stage_guidance(business_type, current_stage)
        if not guidance:
            return ''

        lines = [
            f'BUSINESS TEMPLATE: {business_type}',
            f'STAGE {current_stage} FOCUS: {guidance.get("focus", "")}',
        ]
        metrics = guidance.get('metrics', [])
        if metrics:
            lines.append(f'TRACK: {", ".join(metrics)}')
        proof = guidance.get('proof_needed', '')
        if proof:
            lines.append(f'STAGE PROOF NEEDED: {proof}')
        return '\n'.join(lines)
