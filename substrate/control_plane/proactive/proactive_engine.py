"""
ProactiveIntelligenceEngine — surfaces what matters without being asked.

From PHILOSOPHY.md:
  "The AI runs the business. The founder directs it."

A superhuman mentor doesn't wait to be asked. They already know what you
need to hear before you walk in the door.

This engine runs continuously in the background via the ambient refresh loop
(every 30 minutes). It detects signals that matter and fires them to the
founder through Telegram or Discord.

Detects:
  - Primitive violations: founder discussing approaches locked at their stage
  - Stage transition signals: evidence a transition is near
  - Inaction: no activity for N hours at a critical stage
  - Reality divergence: building instead of selling at Stage 1
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ProactiveSignalType(Enum):
    PRIMITIVE_VIOLATION   = 'primitive_violation'
    STAGE_TRANSITION_NEAR = 'stage_transition_near'
    CONSTRAINT_DETECTED   = 'constraint_detected'
    PATTERN_RECOGNIZED    = 'pattern_recognized'
    OPPORTUNITY_DETECTED  = 'opportunity_detected'
    REALITY_DIVERGENCE    = 'reality_divergence'   # reality diverging from stated goals
    INACTION_DETECTED     = 'inaction_detected'    # no activity for N hours


@dataclass
class ProactiveSignal:
    signal_type:     ProactiveSignalType
    title:           str
    message:         str
    urgency:         int              # 1 (low) to 5 (critical)
    source:          str              # what detected this
    action_required: str             # what to do
    venture_id:      str   = ''
    created_at:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    delivered:       bool  = False


# ─── Stage 1 transition proof ─────────────────────────────────────────────────

_STAGE_1_TRANSITION_PROOF = (
    'One confirmed sale — someone paid the $750. '
    'When that happens, use /advance to unlock Stage 2 primitives.'
)

# ─── Primitive violation keyword map ─────────────────────────────────────────

_VIOLATION_CHECKS: dict[str, list[str]] = {
    'content_strategy': [
        'posting', 'content strategy', 'instagram',
        'tiktok', 'youtube', 'followers',
        'audience', 'going viral', 'viral',
    ],
    'paid_advertising': [
        'ads', 'facebook ads', 'google ads',
        'paid ads', 'advertising', 'boost post',
        'run ads',
    ],
    'hire_salesperson': [
        'hire', 'salesperson', 'sales rep',
        'commission only', 'recruit someone',
        'find a closer',
    ],
    'offer_optimization': [
        'perfect my offer', 'refine the offer',
        'offer stack', 'tweak the offer',
        'bonus stack',
    ],
}


class ProactiveIntelligenceEngine:

    def __init__(self, ctx):
        self.ctx = ctx

    # ─── Main scan ────────────────────────────────────────────────────────────

    def scan(self) -> list[ProactiveSignal]:
        """
        Full proactive scan. Returns all signals worth surfacing.
        Each scanner is isolated — one failure never blocks others.
        """
        signals: list[ProactiveSignal] = []

        try:
            signals.extend(self._scan_primitive_violations())
        except Exception as e:
            print(f'[Proactive] Primitive scan failed: {e}')

        try:
            signals.extend(self._scan_stage_transition())
        except Exception as e:
            print(f'[Proactive] Stage scan failed: {e}')

        try:
            signals.extend(self._scan_inaction())
        except Exception as e:
            print(f'[Proactive] Inaction scan failed: {e}')

        try:
            signals.extend(self._scan_reality_divergence())
        except Exception as e:
            print(f'[Proactive] Reality scan failed: {e}')

        try:
            from substrate.governance.accountability.accountability import AccountabilityEngine
            ae = AccountabilityEngine(self.ctx)
            pending = ae.get_pending_follow_ups()
            for commitment in pending:
                msg = ae.generate_follow_up_message(commitment)
                signals.append(ProactiveSignal(
                    signal_type=ProactiveSignalType.INACTION_DETECTED,
                    title='📋 Commitment check-in',
                    message=msg,
                    urgency=3,
                    source='accountability_engine',
                    action_required='Report back on this',
                ))
                ae.mark_follow_up_sent(commitment['event_id'])
        except Exception as e:
            print(f'[Proactive] Accountability: {e}')

        # Sort by urgency descending
        signals.sort(key=lambda s: s.urgency, reverse=True)
        return signals

    # ─── Scanner: primitive violations ───────────────────────────────────────

    def _scan_primitive_violations(self) -> list[ProactiveSignal]:
        """
        Detect when recent conversation shows founder discussing approaches
        that are locked at their current stage.
        """
        signals: list[ProactiveSignal] = []

        try:
            from substrate.state.memory.memory import ConversationMemory
            # learning/ removed in convergence — EvolutionEngine no longer exists
            from substrate.understanding.ontology.primitives import PRIMITIVE_LIBRARY
        except ImportError:
            print("[ProactiveEngine] _scan_primitive_violations skipped: learning/ removed")
            return signals

        # EvolutionEngine unavailable — cannot determine stage, skip scan
        print("[ProactiveEngine] _scan_primitive_violations skipped: EvolutionEngine removed")
        return signals

    # ─── Scanner: stage transition ────────────────────────────────────────────

    def _scan_stage_transition(self) -> list[ProactiveSignal]:
        """
        Detect when recent conversation contains signals that a stage
        transition is near or has occurred.
        """
        # learning/ removed in convergence — EvolutionEngine no longer exists
        # Cannot determine stage without it, skip scan
        print("[ProactiveEngine] _scan_stage_transition skipped: EvolutionEngine removed")
        return []

    # ─── Scanner: inaction ────────────────────────────────────────────────────

    def _scan_inaction(self) -> list[ProactiveSignal]:
        """
        Detect when no founder activity for an extended period.
        Stage 1: 48 hours of silence is worth surfacing.
        """
        # learning/ removed in convergence — EvolutionEngine no longer exists
        # Cannot determine stage without it, skip scan
        print("[ProactiveEngine] _scan_inaction skipped: EvolutionEngine removed")
        return []

    # ─── Scanner: reality divergence ─────────────────────────────────────────

    def _scan_reality_divergence(self) -> list[ProactiveSignal]:
        """
        Detect when stated goals diverge from actual activity.
        Stage 1: building instead of selling is the most common divergence.
        """
        signals: list[ProactiveSignal] = []

        from substrate.state.memory.memory import ConversationMemory
        from substrate.state.business.business_instance import BusinessInstanceManager

        cm  = ConversationMemory(self.ctx)
        bim = BusinessInstanceManager(self.ctx)

        try:
            bis = bim.get_bis('lyfe_institute')
        except Exception:
            bis = None

        north_star = getattr(bis, 'north_star', '') if bis else ''
        if not north_star:
            return signals

        recent = cm.get_recent(limit=50)
        if not recent:
            return signals

        recent_text = ' '.join(
            m.content.lower() for m in recent
            if m.role == 'user'
        )

        outreach_signals = [
            'dm', 'message', 'outreach',
            'sent', 'replied', 'response',
            'conversation', 'lead', 'prospect',
        ]
        distraction_signals = [
            'logo', 'website', 'brand',
            'color scheme', 'name ideas',
            'business card', 'office space',
            'perfect', 'when i\'m ready',
            'not ready yet',
        ]

        outreach_count    = sum(1 for s in outreach_signals    if s in recent_text)
        distraction_count = sum(1 for s in distraction_signals if s in recent_text)

        if distraction_count > outreach_count and distraction_count > 2:
            signals.append(ProactiveSignal(
                signal_type=ProactiveSignalType.REALITY_DIVERGENCE,
                title='Reality check',
                message=(
                    'Recent activity shows more focus on **building** than **selling**.\n\n'
                    'At Stage 1 this is the most common way founders delay their first sale.\n\n'
                    'The business does not exist until someone pays for it. '
                    'Everything else is preparation for a test that has not happened.'
                ),
                urgency=3,
                source='reality_scanner',
                action_required='Shift focus: outreach before optimization',
                venture_id='lyfe_institute',
            ))

        return signals

    # ─── Formatting ───────────────────────────────────────────────────────────

    def format_signal_for_telegram(self, signal: ProactiveSignal) -> str:
        """Format a signal as a Telegram message."""
        urgency_emoji = {1: '💡', 2: '📍', 3: '⚠️', 4: '🎯', 5: '🚨'}
        emoji = urgency_emoji.get(signal.urgency, '💡')
        return (
            f'{emoji} {signal.title}\n\n'
            f'{signal.message}\n\n'
            f'Action: {signal.action_required}'
        )

    def format_signal_for_discord(self, signal: ProactiveSignal) -> str:
        """Format a signal as a Discord message."""
        urgency_emoji = {1: '💡', 2: '📍', 3: '⚠️', 4: '🎯', 5: '🚨'}
        emoji = urgency_emoji.get(signal.urgency, '💡')
        return (
            f'{emoji} **{signal.title}**\n\n'
            f'{signal.message}\n\n'
            f'**Action:** {signal.action_required}'
        )

    def scan_and_deliver(
        self,
        send_fn=None,
        min_urgency: int = 3,
        # Backwards compat — callers using keyword arg
        send_telegram_fn=None,
    ) -> int:
        """
        Scan for signals and deliver those above min_urgency.
        send_fn: callable(str) — synchronous send function.
        Returns count of signals delivered.
        """
        _send = send_fn or send_telegram_fn
        signals = self.scan()
        delivered = 0

        for signal in signals:
            if signal.urgency < min_urgency:
                continue

            if _send:
                try:
                    msg = self.format_signal_for_telegram(signal)
                    _send(msg)
                    signal.delivered = True
                    delivered += 1
                except Exception as e:
                    print(f'[Proactive] Signal deliver failed: {e}')

        return delivered
