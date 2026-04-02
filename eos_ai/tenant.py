"""
Tenant — formal multi-tenant isolation layer for EOS.

Three-layer model:
  PLATFORM  — shared codebase on GitHub (cognitive_loop, primitives, hierarchy)
  INSTANCE  — per-user context loaded from DB (org_id, ai_name, offer, ICP)
  PERSONAL  — emerges from usage over time (preferences, patterns)

Usage:
    from eos_ai.tenant import TenantManager, TenantLayer
    ctx = load_context_from_env()
    tm = TenantManager(ctx)
    tc = tm.get_tenant_context()
    print(tm.format_for_prompt())
"""

from dataclasses import dataclass, field
from enum import Enum


class TenantLayer(Enum):
    PLATFORM = 'platform'   # shared, on GitHub
    INSTANCE = 'instance'   # per user, in DB
    PERSONAL = 'personal'   # emerges over time


@dataclass
class TenantContext:
    org_id: str
    user_id: str
    ai_name: str
    founder_name: str
    os_subscriptions: list
    current_stage: int
    is_active: bool = True

    # Instance layer fields — loaded from DB, not config files
    company_names: list = field(default_factory=list)
    offer_name: str = ''
    offer_price: float = 0.0
    icp_description: str = ''
    primary_channel: str = ''
    north_star: str = ''

    # Personal layer fields — emerge from usage over time
    communication_patterns: dict = field(default_factory=dict)
    preferred_response_length: str = 'adaptive'
    active_hours: dict = field(default_factory=dict)
    learned_preferences: dict = field(default_factory=dict)


class TenantManager:

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def get_tenant_context(self) -> TenantContext:
        """Load full tenant context from DB via BIS."""
        try:
            from eos_ai.business_instance import BusinessInstanceManager
            bim = BusinessInstanceManager(self.ctx)
            bis = bim.get_bis('lyfe_institute')

            return TenantContext(
                org_id=self.ctx.org_id,
                user_id=getattr(self.ctx, 'user_id', self.ctx.org_id),
                ai_name=getattr(bis, 'ai_name', 'AI') if bis else 'AI',
                founder_name=getattr(bis, 'founder_name', 'Founder') if bis else 'Founder',
                os_subscriptions=getattr(
                    bis, 'os_subscriptions', ['entrepreneur_os']
                ) if bis else ['entrepreneur_os'],
                current_stage=getattr(bis, 'current_stage', 1) if bis else 1,
                offer_name=getattr(bis, 'offer_name', '') if bis else '',
                offer_price=getattr(bis, 'offer_price', 0.0) if bis else 0.0,
                icp_description=getattr(bis, 'icp_description', '') if bis else '',
                primary_channel=getattr(bis, 'primary_channel', '') if bis else '',
                north_star=getattr(bis, 'north_star', '') if bis else '',
            )
        except Exception as e:
            print(f'[TenantManager] Load failed: {e}')
            return TenantContext(
                org_id=self.ctx.org_id,
                user_id=self.ctx.org_id,
                ai_name='AI',
                founder_name='Founder',
                os_subscriptions=['entrepreneur_os'],
                current_stage=1,
            )

    def validate_isolation(self, query_org_id: str) -> bool:
        """Verify org_id matches current context. Prevents cross-tenant data access."""
        if query_org_id != self.ctx.org_id:
            print(
                f'[TenantManager] ISOLATION VIOLATION: '
                f'Query org {query_org_id} != '
                f'Context org {self.ctx.org_id}'
            )
            return False
        return True

    def get_layer(self, field_name: str) -> TenantLayer:
        """Returns which protocol layer a field belongs to."""
        platform_fields = [
            'cognitive_loop', 'primitives',
            'agent_hierarchy', 'os_registry',
            'ai_identity', 'protocols',
        ]
        instance_fields = [
            'ai_name', 'founder_name', 'org_id',
            'company_names', 'offer_name',
            'offer_price', 'icp_description',
            'primary_channel', 'north_star',
            'os_subscriptions', 'current_stage',
        ]
        personal_fields = [
            'communication_patterns',
            'preferred_response_length',
            'active_hours', 'learned_preferences',
            'interaction_history',
        ]

        if field_name in platform_fields:
            return TenantLayer.PLATFORM
        elif field_name in instance_fields:
            return TenantLayer.INSTANCE
        elif field_name in personal_fields:
            return TenantLayer.PERSONAL
        return TenantLayer.INSTANCE

    def format_for_prompt(self) -> str:
        """Format tenant context for injection into agent system prompts."""
        tc = self.get_tenant_context()
        lines = [
            'INSTANCE CONTEXT:',
            f'AI Name: {tc.ai_name}',
            f'Founder: {tc.founder_name}',
            f'Stage: {tc.current_stage}',
            f'North star: {tc.north_star}',
        ]
        if tc.offer_name:
            lines.append(f'Offer: {tc.offer_name}')
        if tc.primary_channel:
            lines.append(f'Channel: {tc.primary_channel}')
        return '\n'.join(lines)
