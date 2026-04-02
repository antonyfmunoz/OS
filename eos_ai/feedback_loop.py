"""
FeedbackLoop — closes the loop between DEX recommendations and real outcomes.

Every piece of advice DEX gives is logged. When the founder reports back
what happened, the outcome is captured and tied to the recommendation.
Over time this builds a signal of what actually works vs. what doesn't.

Usage:
    from eos_ai.feedback_loop import FeedbackLoop
    fl = FeedbackLoop(ctx)
    rec_id = fl.log_recommendation('Send 20 DMs today', 'lyfe_institute', 'asked for focus')
    fl.log_outcome('I sent the DMs, got 3 replies', 'lyfe_institute')
    stats = fl.get_recommendation_stats()
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OutcomeType(Enum):
    SUCCESS = 'success'
    FAILURE = 'failure'
    PARTIAL = 'partial'
    PENDING = 'pending'
    SKIPPED = 'skipped'


@dataclass
class Recommendation:
    id: str
    content: str           # what DEX recommended
    venture_id: str
    context: str           # what triggered it
    created_at: datetime = field(default_factory=datetime.now)
    outcome: OutcomeType = OutcomeType.PENDING
    outcome_note: str = ''
    outcome_at: datetime = None
    followed: bool = None  # did founder act?


class FeedbackLoop:

    def __init__(self, ctx):
        self.ctx = ctx

    def log_recommendation(
        self,
        content: str,
        venture_id: str,
        context: str = '',
    ) -> str:
        """
        Log every DEX recommendation to Neon.
        Returns recommendation ID.
        """
        rec_id = str(uuid.uuid4())[:8]
        try:
            from eos_ai.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    '''
                    INSERT INTO events (
                        id, org_id, event_type,
                        payload_json, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ''',
                    (
                        str(uuid.uuid4()),
                        self.ctx.org_id,
                        'recommendation',
                        json.dumps({
                            'rec_id': rec_id,
                            'content': content[:500],
                            'venture_id': venture_id,
                            'context': context[:200],
                            'outcome': 'pending',
                            'followed': None,
                        }),
                    ),
                )
            print(f'[FeedbackLoop] Logged rec: {rec_id}')
        except Exception as e:
            print(f'[FeedbackLoop] Log failed: {e}')
        return rec_id

    def log_outcome(
        self,
        text: str,
        venture_id: str = '',
    ) -> bool:
        """
        Detect outcome signals in founder's text and log them
        against the most recent pending recommendation.
        """
        text_lower = text.lower()

        success_signals = [
            'worked', 'it worked', 'got a reply',
            'booked a call', 'closed', 'they said yes',
            'got a client', 'made a sale', 'it landed',
            'did it', 'sent the dms', 'sent 20',
        ]
        failure_signals = [
            "didn't work", 'no replies', 'ghosted',
            'failed', "didn't do it", "couldn't",
            'no response', 'bombed', 'skipped',
        ]
        partial_signals = [
            'kind of worked', 'some replies',
            'partially', 'a few', 'not all',
        ]

        outcome = None
        if any(s in text_lower for s in success_signals):
            outcome = 'success'
        elif any(s in text_lower for s in failure_signals):
            outcome = 'failure'
        elif any(s in text_lower for s in partial_signals):
            outcome = 'partial'

        if not outcome:
            return False

        try:
            from eos_ai.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    '''
                    SELECT id, payload_json
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'recommendation'
                    AND payload_json->>'outcome' = 'pending'
                    ORDER BY created_at DESC
                    LIMIT 1
                    ''',
                    (self.ctx.org_id,),
                )
                row = cur.fetchone()

                if row:
                    event_id = row['id']
                    payload = row['payload_json']
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    payload['outcome'] = outcome
                    payload['outcome_note'] = text[:200]
                    payload['outcome_at'] = datetime.now().isoformat()

                    cur.execute(
                        '''
                        UPDATE events
                        SET payload_json = %s
                        WHERE id = %s
                        ''',
                        (json.dumps(payload), event_id),
                    )
                    print(f'[FeedbackLoop] Outcome logged: {outcome}')
                    return True
        except Exception as e:
            print(f'[FeedbackLoop] Outcome: {e}')
        return False

    def get_recommendation_stats(self) -> dict:
        """
        Return outcome distribution across all logged recommendations.
        What percentage are succeeding? What percentage failing?
        """
        try:
            from eos_ai.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    '''
                    SELECT
                        payload_json->>'outcome' as outcome,
                        COUNT(*) as count
                    FROM events
                    WHERE org_id = %s
                    AND event_type = 'recommendation'
                    GROUP BY outcome
                    ''',
                    (self.ctx.org_id,),
                )
                rows = cur.fetchall()
                return {r['outcome']: r['count'] for r in rows}
        except Exception as e:
            print(f'[FeedbackLoop] Stats: {e}')
            return {}
