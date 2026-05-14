"""
TrinityEngine — cross-OS intelligence layer.

When a user has multiple OS modules active, this detects when one
OS's state should inform another OS's response.

This is the cognitive bridge between EntrepreneurOS, CreatorOS,
and LYFEOS. It does not own context — it routes it.

Layer 2 injection order (after Layer 1 step 1h):
  - Format active OS modules for prompt
  - Detect cross-OS signals in the user's input
  - Inject relevant cross-OS insight when multiple modules active

Usage:
    from runtime.trinity import TrinityEngine
    from runtime.context import load_context_from_env

    ctx = load_context_from_env()
    te  = TrinityEngine(ctx)
    print(te.format_for_prompt())
    print(te.get_cross_os_insight('I am exhausted and have a sales call'))
"""

from runtime.context import EOSContext
from state.registries.os_registry import OSRegistryManager


class TrinityEngine:
    """
    Determines which OS modules are active for the current user
    and injects appropriate Layer 2 context into the cognitive loop.

    Cross-OS insight fires only when 2+ modules are active.
    Single-module users see standard module context only.
    """

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx = ctx
        self.orm = OSRegistryManager()

    def get_user_subscriptions(self) -> list[str]:
        """
        Load OS subscriptions from BIS.
        Defaults to EntrepreneurOS if not set or on any error.
        """
        try:
            from state.business.business_instance import BusinessInstanceManager
            bim = BusinessInstanceManager(self.ctx)
            bis = bim.get_bis('lyfe_institute')
            subs = getattr(bis, 'os_subscriptions', [])
            # Default to EntrepreneurOS if not set
            return subs or ['entrepreneur_os']
        except Exception:
            return ['entrepreneur_os']

    def is_full_trinity(self) -> bool:
        """True when all three OS modules are active."""
        return len(self.get_user_subscriptions()) == 3

    def get_active_os_count(self) -> int:
        return len(self.get_user_subscriptions())

    def get_cross_os_insight(self, prompt: str) -> str:
        """
        Detect when the prompt needs cross-OS context injection.
        Only fires when multiple OS modules are active.
        Returns empty string if no cross-OS signal detected.
        """
        subs = self.get_user_subscriptions()
        if len(subs) < 2:
            return ''

        prompt_lower = prompt.lower()

        # Life state signals → affect business performance
        life_signals = [
            'tired', 'exhausted', 'sick',
            'not sleeping', 'burned out',
            'stressed', 'overwhelmed',
            'no energy', 'cant focus',
        ]
        if any(s in prompt_lower for s in life_signals):
            if 'lyfe_os' in subs:
                return (
                    '[LYFEOS → EntrepreneurOS] '
                    'Life state signal detected. '
                    'Physical and mental state directly '
                    'impacts business performance. '
                    'Address the energy first.'
                )

        # Content creation → should serve the business ICP
        content_signals = ['post', 'content', 'audience', 'followers', 'brand']
        if any(b in prompt_lower for b in content_signals):
            if 'creator_os' in subs and 'entrepreneur_os' in subs:
                return (
                    '[CreatorOS ↔ EntrepreneurOS] '
                    'Content serves the business. '
                    'ICP for content = ICP for offer. '
                    'Every post should attract buyers.'
                )

        return ''

    def format_for_prompt(self) -> str:
        """
        Build the Layer 2 system prompt block for this user.
        Returns empty string if no active modules found.
        """
        subs = self.get_user_subscriptions()
        return self.orm.format_for_prompt(subs)
