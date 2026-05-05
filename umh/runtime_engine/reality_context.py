"""
RealityContext — ambient present-state snapshot.

Wraps RealityIntelligenceEngine to produce a structured dict of current
market signals that can be cached as ambient state and injected into the
CognitiveLoop PERCEIVE step without requiring a fresh LLM call on every
message.

Refreshed every 30 minutes via orchestrator background cycle.
Stored in SessionState.set_ambient() for zero-latency PERCEIVE injection.

Usage:
    from umh.environments.system_context import load_context_from_env
    from umh.runtime_engine.reality_context import RealityContext

    ctx     = load_context_from_env()
    rc      = RealityContext(ctx)
    reality = rc.get_current_reality()
    # {'lyfe_institute': [{'content': '...', 'tier': 'HIGH', ...}, ...]}
"""

from umh.environments.system_context import EOSContext


class RealityContext:
    """
    Produces and caches a structured snapshot of current market reality
    for injection into the CognitiveLoop PERCEIVE step.
    """

    def __init__(self, ctx: EOSContext):
        self.ctx = ctx

    def _get_founder_pattern(self) -> dict:
        """
        Read interaction timestamps from Neon to derive the founder's actual
        working-hours pattern. Updates night_owl flag automatically from real data.

        Returns a pattern dict with keys:
            night_owl, typical_start_hour, typical_end_hour, timezone, avg_active_hour

        Falls back to static defaults on any failure.
        """
        _default = {
            'night_owl':           True,
            'typical_start_hour':  10,
            'typical_end_hour':    23,
            'timezone':            'America/Los_Angeles',
            'avg_active_hour':     17.0,
        }
        try:
            from umh.storage.adapters.neon import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT EXTRACT(hour FROM created_at AT TIME ZONE 'America/Los_Angeles')
                           AS hour
                    FROM interactions
                    WHERE org_id = %s
                    ORDER BY created_at DESC
                    LIMIT 50
                    """,
                    (self.ctx.org_id,),
                )
                rows = cur.fetchall()

            if not rows:
                return _default

            hours = [float(r['hour']) for r in rows if r['hour'] is not None]
            if not hours:
                return _default

            avg_hour          = sum(hours) / len(hours)
            late_night_count  = sum(1 for h in hours if h >= 22 or h < 4)
            night_owl         = late_night_count > len(hours) * 0.3
            day_hours         = [h for h in hours if 5 <= h < 24]
            typical_start     = int(min(day_hours)) if day_hours else 10
            typical_end       = int(max(day_hours)) if day_hours else 23

            return {
                'night_owl':           night_owl,
                'typical_start_hour':  typical_start,
                'typical_end_hour':    typical_end,
                'timezone':            'America/Los_Angeles',
                'avg_active_hour':     round(avg_hour, 1),
            }

        except Exception as e:
            print(f'[RealityContext] _get_founder_pattern failed: {e}')
            return _default

    def get_current_reality(self) -> dict:
        """
        Scan all ventures for current market signals and return a structured dict.

        Returns:
            {venture_id: [signal_dict, ...]}  — top 3 signals per venture.
            Empty dict on any failure (never blocks callers).
        """
        try:
            from umh.runtime_engine.reality_engine import RealityIntelligenceEngine
            from umh.runtime_engine.venture_knowledge import VentureKnowledgeBase

            rie   = RealityIntelligenceEngine(self.ctx)
            result: dict = {}

            for vid in VentureKnowledgeBase.list_ventures():
                try:
                    signals = rie.scan_market_signals(vid)
                    # Keep top 3 — prioritise CRITICAL and HIGH
                    priority = {'CRITICAL': 0, 'HIGH': 1, 'NORMAL': 2, 'BACKGROUND': 3}
                    sorted_signals = sorted(
                        signals,
                        key=lambda s: priority.get(s.get('tier', 'BACKGROUND'), 3),
                    )
                    result[vid] = sorted_signals[:3]
                except Exception as e:
                    print(f'[RealityContext] {vid} scan failed: {e}')
                    result[vid] = []

            # Include founder working-pattern data
            result['_founder_pattern'] = self._get_founder_pattern()
            return result

        except Exception as e:
            print(f'[RealityContext] get_current_reality failed: {e}')
            return {}

    def format_for_injection(self, reality: dict) -> str:
        """
        Format a reality dict for injection into a CognitiveLoop prompt.
        Returns empty string if no signals.
        """
        if not reality:
            return ''

        lines: list[str] = []
        for vid, signals in reality.items():
            if not signals:
                continue
            venture_label = vid.replace('_', ' ').title()
            for s in signals[:2]:
                tier    = s.get('tier', '')
                content = s.get('content', '')[:120]
                stype   = s.get('signal_type', '')
                if content:
                    lines.append(f'• [{venture_label} / {stype} / {tier}] {content}')

        if not lines:
            return ''

        return 'CURRENT MARKET SIGNALS:\n' + '\n'.join(lines)
