"""
DecisionLog — permanent record of important decisions made in conversation.

Decisions disappear after the context window closes. This module detects
decision language in founder messages, extracts the key decision via LLM,
and stores it permanently in Neon as a 'decision' event.

The stored decisions are surfaced back into the cognitive loop so DEX always
knows what has been decided, and why.

Usage:
    from substrate.state.context.context import load_context_from_env
    from substrate.state.logs.decision_log import DecisionLog

    ctx = load_context_from_env()
    dl = DecisionLog(ctx)

    if dl.detect_decision(text):
        dl.log_decision(description='Going with Instagram DMs', rationale='Signal confirmed')

    decisions = dl.get_recent_decisions(venture_id='lyfe_institute', limit=5)
"""

import json
import re
import uuid
from dataclasses import dataclass, field

from substrate.state.context.context import EntrepreneurOSContext


@dataclass
class Decision:
    id: str
    description: str    # what was decided
    rationale: str      # why
    venture_id: str
    decided_by: str     # 'founder' or 'dex'
    impact: str         # 'high' | 'medium' | 'low'
    tags: list[str] = field(default_factory=list)


DECISION_SIGNALS = (
    'i decided', 'we decided',
    'going with', 'final decision',
    'decided to', 'choosing',
    'committing to',
    'the plan is',
    'from now on',
    'moving forward',
    'new direction',
    'changed my mind',
    'pivoting to',
)


class DecisionLog:

    def __init__(self, ctx: EntrepreneurOSContext):
        self.ctx = ctx

    def detect_decision(self, text: str, venture_id: str = '') -> bool:
        """Return True if the text contains decision language."""
        t = text.lower()
        return any(s in t for s in DECISION_SIGNALS)

    def log_decision(
        self,
        description: str,
        rationale: str = '',
        venture_id: str = '',
        decided_by: str = 'founder',
        impact: str = 'medium',
        tags: list[str] | None = None,
    ) -> str:
        """
        Persist a decision to Neon. Returns short decision_id.
        """
        decision_id = str(uuid.uuid4())[:8]
        try:
            from substrate.state.memory.memory import AgentMemory
            AgentMemory().log_event(
                org_id=str(self.ctx.org_id),
                event_type='decision',
                payload={
                    'decision_id': decision_id,
                    'description': description,
                    'rationale':   rationale,
                    'venture_id':  venture_id,
                    'decided_by':  decided_by,
                    'impact':      impact,
                    'tags':        tags or [],
                },
                handled_by='decision_log',
            )
            print(f'[DecisionLog] Logged: {description[:60]}')
        except Exception as e:
            print(f'[DecisionLog] log failed: {e}')
        return decision_id

    def log_from_message(
        self,
        text: str,
        venture_id: str = '',
    ) -> str | None:
        """
        Auto-extract and log a decision from a founder message.
        Uses LLM to extract structured decision data. Returns decision_id or None.
        """
        try:
            from execution.runtime.model_router import get_router, TaskType as RouterTaskType
            router  = get_router()
            model   = router.route(RouterTaskType.ANALYSIS)
            if not model:
                # Fallback: log the raw message as description
                return self.log_decision(
                    description=text[:200],
                    venture_id=venture_id,
                )

            extraction = router.call(
                model,
                prompt=(
                    'Extract the key decision from this message. '
                    'Return valid JSON with exactly these keys:\n'
                    '{"description": "what was decided (one sentence)",\n'
                    ' "rationale": "why (if mentioned, else empty string)",\n'
                    ' "impact": "high or medium or low"}\n\n'
                    f'Message: {text}'
                ),
                max_tokens=150,
            )

            match = re.search(r'\{[^{}]+\}', extraction, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return self.log_decision(
                    description=data.get('description', text[:200]),
                    rationale=data.get('rationale', ''),
                    venture_id=venture_id,
                    impact=data.get('impact', 'medium'),
                )
        except Exception as e:
            print(f'[DecisionLog] log_from_message failed: {e}')

        # Fallback
        return self.log_decision(description=text[:200], venture_id=venture_id)

    def get_recent_decisions(
        self,
        venture_id: str = '',
        limit: int = 10,
    ) -> list[dict]:
        """Retrieve recent decisions from Neon, optionally filtered by venture."""
        try:
            from substrate.state.storage.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                if venture_id:
                    cur.execute(
                        '''
                        SELECT payload_json, created_at
                        FROM events
                        WHERE org_id = %s
                          AND event_type = 'decision'
                          AND payload_json->>'venture_id' = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        ''',
                        (self.ctx.org_id, venture_id, limit),
                    )
                else:
                    cur.execute(
                        '''
                        SELECT payload_json, created_at
                        FROM events
                        WHERE org_id = %s
                          AND event_type = 'decision'
                        ORDER BY created_at DESC
                        LIMIT %s
                        ''',
                        (self.ctx.org_id, limit),
                    )
                rows = cur.fetchall()

            results = []
            for row in rows:
                data = row['payload_json']
                if isinstance(data, str):
                    data = json.loads(data)
                data['created_at'] = str(row['created_at'])
                results.append(data)
            return results

        except Exception as e:
            print(f'[DecisionLog] get_recent_decisions failed: {e}')
            return []

    def format_for_context(self, decisions: list[dict]) -> str:
        """Format recent decisions for injection into cognitive loop."""
        if not decisions:
            return ''
        lines = ['KEY DECISIONS:']
        for d in decisions[:5]:
            lines.append(
                f'- {d.get("description", "")[:80]} '
                f'({d.get("decided_by", "founder")}, '
                f'{str(d.get("created_at", ""))[:10]})'
            )
        return '\n'.join(lines)
