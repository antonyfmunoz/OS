"""
Confidentiality Protocol — handles sensitive
negotiations, investor terms, M&A discussions,
and any context requiring restricted logging.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')

# Signals that indicate confidential context
CONFIDENTIAL_SIGNALS = [
    'acquisition', 'merger', 'm&a', 'term sheet',
    'investment', 'investor terms', 'equity', 'cap table',
    'valuation', 'due diligence', 'nda', 'non-disclosure',
    'confidential', 'off the record', 'sensitive',
    'negotiation', 'partnership terms', 'legal',
    'lawsuit', 'dispute', 'settlement',
]

CONFIDENTIAL_LEVELS = {
    'standard': 'Log normally',
    'restricted': 'Log metadata only, no content',
    'private': 'Do not log — memory only',
    'sealed': 'Do not log, do not retain',
}


def detect_confidential_context(text: str) -> dict:
    """
    Detect if a message contains confidential signals.
    Returns confidence and recommended handling.
    """
    text_lower = text.lower()
    detected = [s for s in CONFIDENTIAL_SIGNALS if s in text_lower]

    if not detected:
        return {'is_confidential': False, 'level': 'standard'}

    # Score by count and severity
    level = 'standard'
    if len(detected) >= 3:
        level = 'private'
    elif len(detected) >= 2:
        level = 'restricted'
    elif any(s in detected for s in [
        'acquisition', 'merger', 'term sheet',
        'lawsuit', 'settlement', 'sealed'
    ]):
        level = 'private'
    else:
        level = 'restricted'

    return {
        'is_confidential': True,
        'level': level,
        'signals': detected,
        'handling': CONFIDENTIAL_LEVELS[level],
        'recommendation': (
            f'This conversation contains sensitive signals: '
            f'{", ".join(detected[:3])}. '
            f'Handling: {CONFIDENTIAL_LEVELS[level]}.'
        ),
    }


def create_confidential_session(
    topic: str,
    parties: list,
    level: str = 'restricted',
    ctx=None,
) -> dict:
    """
    Create a confidential session context.
    Logs metadata only — no content stored.
    """
    try:
        from runtime.context import load_context_from_env
        from state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()
        now = datetime.now(PDT)

        session = {
            'topic': topic,
            'parties': parties,
            'level': level,
            'started_at': now.isoformat(),
            'status': 'active',
        }

        if level != 'sealed':
            AgentMemory().log_event(
                org_id=str(ctx.org_id),
                event_type='confidential_session',
                payload={
                    'topic': topic,
                    'party_count': len(parties),
                    'level': level,
                    'started_at': now.isoformat(),
                },
                handled_by='confidentiality_protocol',
            )

        return session
    except Exception as e:
        logger.warning(f'[Confidentiality] create_session failed: {e}')
        return {}
