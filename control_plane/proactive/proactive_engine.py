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

        from state.memory.memory import ConversationMemory
        from learning.evolution.evolution_engine import EvolutionEngine
        from substrate.understanding.ontology.primitives import PRIMITIVE_LIBRARY

        cm = ConversationMemory(self.ctx)
        ee = EvolutionEngine(self.ctx)

        recent = cm.get_recent(limit=20)
        if not recent:
            return signals

        recent_text = ' '.join(
            m.content.lower() for m in recent
            if m.role == 'user'
        )
        if not recent_text.strip():
            return signals

        stage = ee.get_current_stage('lyfe_institute')

        for primitive_id, keywords in _VIOLATION_CHECKS.items():
            primitive = PRIMITIVE_LIBRARY.get(primitive_id)
            if not primitive:
                continue

            # Only fire if primitive is locked at this stage
            stage_applies = primitive.stage_applicability.get(stage, True)
            if stage_applies:
                continue

            # Only fire if founder recently mentioned it
            if not any(kw in recent_text for kw in keywords):
                continue

            # Pull the most relevant warning
            warning = primitive.common_misapplication
            instead = ''
            for vc in primitive.validity_conditions:
                if not vc.get('applies', True):
                    warning  = vc.get('warning', warning)
                    instead  = vc.get('what_applies_instead', '')
                    break

            message = (
                f'You recently mentioned '
                f'**{primitive_id.replace("_", " ")}**.\n\n'
                f'{warning}'
            )
            if instead:
                message += f'\n\n**Instead:** {instead}'

            signals.append(ProactiveSignal(
                signal_type=ProactiveSignalType.PRIMITIVE_VIOLATION,
                title=f'Primitive check: {primitive_id.replace("_", " ")}',
                urgency=3,
                message=message,
                source='primitive_scanner',
                action_required='Review before acting on this approach',
                venture_id='lyfe_institute',
            ))

        return signals

    # ─── Scanner: stage transition ────────────────────────────────────────────

    def _scan_stage_transition(self) -> list[ProactiveSignal]:
        """
        Detect when recent conversation contains signals that a stage
        transition is near or has occurred.
        """
        signals: list[ProactiveSignal] = []

        from learning.evolution.evolution_engine import EvolutionEngine
        from state.memory.memory import ConversationMemory

        ee = EvolutionEngine(self.ctx)
        cm = ConversationMemory(self.ctx)

        stage = ee.get_current_stage('lyfe_institute')

        recent = cm.get_recent(limit=30)
        if not recent:
            return signals

        recent_text = ' '.join(
            m.content.lower() for m in recent
            if m.role == 'user'
        )

        # Stage 1 → 2: first sale signals
        if stage == 1:
            transition_signals = [
                'first client', 'first sale',
                'first customer', 'they paid',
                'got a yes', 'closed',
                'signed', 'paid me',
                'first payment',
            ]
            if any(s in recent_text for s in transition_signals):
                signals.append(ProactiveSignal(
                    signal_type=ProactiveSignalType.STAGE_TRANSITION_NEAR,
                    title='Stage transition signal detected',
                    message=(
                        'Recent conversation suggests you may have closed '
                        'your first sale or are very close.\n\n'
                        f'**To confirm Stage 2:** {_STAGE_1_TRANSITION_PROOF}'
                    ),
                    urgency=4,
                    source='stage_scanner',
                    action_required='Confirm first sale with /advance to unlock Stage 2',
                    venture_id='lyfe_institute',
                ))

        return signals

    # ─── Scanner: inaction ────────────────────────────────────────────────────

    def _scan_inaction(self) -> list[ProactiveSignal]:
        """
        Detect when no founder activity for an extended period.
        Stage 1: 48 hours of silence is worth surfacing.
        """
        signals: list[ProactiveSignal] = []

        from state.memory.memory import ConversationMemory
        from learning.evolution.evolution_engine import EvolutionEngine

        cm = ConversationMemory(self.ctx)
        ee = EvolutionEngine(self.ctx)

        recent = cm.get_recent(limit=1)
        if not recent:
            return signals

        last_message = recent[0]
        created_at = last_message.created_at

        # Neon returns timezone-aware datetimes — handle both cases
        now = datetime.now(timezone.utc)
        if hasattr(created_at, 'tzinfo') and created_at.tzinfo is not None:
            hours_since = (now - created_at).total_seconds() / 3600
        else:
            # Naive datetime — treat as UTC
            created_utc = created_at.replace(tzinfo=timezone.utc)
            hours_since  = (now - created_utc).total_seconds() / 3600

        stage = ee.get_current_stage('lyfe_institute')

        if stage == 1 and hours_since > 48:
            signals.append(ProactiveSignal(
                signal_type=ProactiveSignalType.INACTION_DETECTED,
                title='Checking in',
                message=(
                    f'It has been {int(hours_since)} hours since your last activity.\n\n'
                    'At Stage 1 momentum is everything. The clock is always running.\n\n'
                    '**Where are you with outreach?** '
                    'How many DMs have gone out this week?'
                ),
                urgency=2,
                source='inaction_scanner',
                action_required='Resume outreach activity',
                venture_id='lyfe_institute',
            ))

        return signals

    # ─── Scanner: reality divergence ─────────────────────────────────────────

    def _scan_reality_divergence(self) -> list[ProactiveSignal]:
        """
        Detect when stated goals diverge from actual activity.
        Stage 1: building instead of selling is the most common divergence.
        """
        signals: list[ProactiveSignal] = []

        from state.memory.memory import ConversationMemory
        from state.business.business_instance import BusinessInstanceManager

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
