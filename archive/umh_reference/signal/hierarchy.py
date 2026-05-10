"""
SignalHierarchyEngine — ranks signal before the filter applies.

From PHILOSOPHY.md Section VI:
  Tier 1 — Reality:      what is actually true?
  Tier 2 — Context:      what domain, what stage?
  Tier 3 — Leverage:     what moves everything else?
  Tier 4 — Optimization: what pattern applies?
  Tier 5 — Delivery:     what lands for this person?

Higher signal always gates lower signal.
Noise never reaches the output.

Every input is classified before context injection.
Domain relevance filters first.
Tier determines injection priority.
"""

from dataclasses import dataclass, field
from enum import Enum


class SignalTier(Enum):
    REALITY      = 1  # what is actually true
    CONTEXT      = 2  # domain + stage + situation
    LEVERAGE     = 3  # what moves everything
    OPTIMIZATION = 4  # what pattern applies
    DELIVERY     = 5  # what lands for this person


@dataclass
class Signal:
    tier:             SignalTier
    source:           str        # where signal came from
    content:          str        # the signal content
    confidence:       float      # 0.0 to 1.0
    domain:           str        # business/life/content/universal
    is_relevant:      bool = True
    relevance_reason: str  = ''


# ─── Reality signals — what is happening now ──────────────────────────────────
_REALITY_SIGNALS = [
    'just happened', 'right now', 'today',
    'this week', 'revenue', 'closed',
    'lost', 'signed', 'canceled', 'replied',
    'no response', 'ghosted', 'meeting',
    'call', 'numbers', 'data', 'results',
]

# ─── Context signals — stage + situation ──────────────────────────────────────
_CONTEXT_SIGNALS = [
    'stage', 'beginning', 'starting',
    'first', 'no clients', 'no revenue',
    'just started', 'portfolio', 'scaling',
    'team', 'hire', 'system',
]

# ─── Leverage signals — what to do ────────────────────────────────────────────
_LEVERAGE_SIGNALS = [
    'what should i', 'what do i',
    'how do i', 'best way to',
    'focus', 'priority', 'most important',
    'highest leverage', 'next step',
]

# ─── Domain signals ───────────────────────────────────────────────────────────
_BUSINESS_SIGNALS = [
    'revenue', 'sales', 'client', 'offer',
    'price', 'pipeline', 'lead', 'close',
    'hire', 'team', 'company', 'business',
    'market', 'product', 'launch', 'dm',
    'outreach', 'content', 'brand',
]

_LIFE_SIGNALS = [
    'sleep', 'energy', 'health', 'tired',
    'workout', 'eat', 'relationship',
    'family', 'stress', 'anxiety', 'focus',
    'habit', 'routine', 'morning', 'evening',
]

_CREATOR_SIGNALS = [
    'post', 'content', 'audience',
    'followers', 'engagement', 'video',
    'podcast', 'newsletter', 'brand',
    'creator', 'platform',
]


class SignalHierarchyEngine:

    def __init__(self, ctx):
        self.ctx = ctx

    def classify_input(
        self,
        text: str,
        channel: str = 'unknown',
    ) -> dict:
        """
        Classify input signal tier and domain before context injection.
        Returns classification dict used downstream by format_for_prompt
        and rank_context_injections.
        """
        text_lower = text.lower()

        domain = self._detect_domain(text_lower)

        # Classify primary tier — Reality gates Context, Context gates Leverage
        if any(s in text_lower for s in _REALITY_SIGNALS):
            primary_tier = SignalTier.REALITY
        elif any(s in text_lower for s in _LEVERAGE_SIGNALS):
            primary_tier = SignalTier.LEVERAGE
        elif any(s in text_lower for s in _CONTEXT_SIGNALS):
            primary_tier = SignalTier.CONTEXT
        else:
            primary_tier = SignalTier.CONTEXT

        return {
            'primary_tier': primary_tier,
            'domain':       domain,
            'text':         text,
            'channel':      channel,
        }

    def _detect_domain(self, text: str) -> str:
        """Detect the primary domain from input text."""
        business_count = sum(1 for s in _BUSINESS_SIGNALS if s in text)
        life_count     = sum(1 for s in _LIFE_SIGNALS      if s in text)
        creator_count  = sum(1 for s in _CREATOR_SIGNALS   if s in text)

        if life_count > business_count and life_count > creator_count:
            return 'life'
        if creator_count > business_count:
            return 'content'
        if business_count > 0:
            return 'business'
        return 'universal'

    def rank_context_injections(
        self,
        injections: list[dict],
        classified_input: dict,
    ) -> list[dict]:
        """
        Rank context injections by relevance to classified input.
        Higher tier injections come first.
        Irrelevant domain injections are filtered out.
        """
        domain = classified_input.get('domain', 'universal')
        tier   = classified_input.get('primary_tier', SignalTier.CONTEXT)

        ranked = []
        for injection in injections:
            inj_domain = injection.get('domain', 'universal')
            inj_tier   = injection.get('tier', SignalTier.CONTEXT)

            # Domain relevance check — universal applies everywhere.
            # Domain-specific only if matching, unless cross-OS intelligence.
            if inj_domain != 'universal' and inj_domain != domain:
                if not injection.get('cross_os'):
                    continue

            score = 0

            # Higher tier = lower value = higher priority
            if isinstance(inj_tier, SignalTier):
                score += (6 - inj_tier.value) * 10
            else:
                score += 20  # default mid-tier if unknown

            # Domain match bonus
            if inj_domain == domain:
                score += 20

            # Reality tier always gets boost — it is ground truth
            if tier == SignalTier.REALITY:
                score += 30

            ranked.append({**injection, 'relevance_score': score})

        ranked.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return ranked

    def filter_noise(
        self,
        content: str,
        min_signal_length: int = 10,
    ) -> bool:
        """
        Returns True if content has signal, False if it's noise.
        """
        if not content:
            return False
        if len(content.strip()) < min_signal_length:
            return False
        noise_patterns = [
            'n/a', 'none', 'null', 'undefined',
            'no data', 'not available',
        ]
        if content.lower().strip() in noise_patterns:
            return False
        return True

    def format_for_prompt(self, classified_input: dict) -> str:
        """
        Format signal classification as context for the cognitive loop.
        Injected at step 0b — after AI identity, before semantic memory.
        """
        domain = classified_input.get('domain', 'universal')
        tier   = classified_input.get('primary_tier', SignalTier.CONTEXT)

        lines = [
            'SIGNAL CLASSIFICATION:',
            f'Domain: {domain}',
            f'Primary tier: {tier.name}',
        ]

        if domain == 'business':
            lines.append(
                'Filter: Apply business primitives, '
                'stage context, leverage analysis'
            )
        elif domain == 'life':
            lines.append(
                'Filter: Apply life context, '
                'energy state, readiness assessment'
            )
        elif domain == 'content':
            lines.append(
                'Filter: Apply content strategy, '
                'audience intelligence, brand context'
            )

        if tier == SignalTier.REALITY:
            lines.append(
                'Reality signal detected: '
                'Ground response in actual current state. '
                'This overrides assumptions.'
            )
        elif tier == SignalTier.LEVERAGE:
            lines.append(
                'Leverage query: '
                'Identify highest leverage action. '
                'Minimum effective dose.'
            )

        return '\n'.join(lines)
