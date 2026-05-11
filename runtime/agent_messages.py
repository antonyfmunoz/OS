"""
AgentMessageBus — inter-agent communication layer.

Agents send typed messages to each other via Neon events.
Messages are directional (upward/downward/lateral) and typed
(task/report/alert/query/result).

Usage:
    from runtime.agent_messages import AgentMessageBus, AgentMessage, MessageType, MessageDirection
    bus = AgentMessageBus(ctx)
    bus.send(AgentMessage(
        from_agent='portfolio_agent',
        to_agent='ceo_agent',
        direction=MessageDirection.DOWNWARD,
        content='Focus on Lyfe Institute — binding constraint.',
        message_type=MessageType.TASK,
        venture_id='lyfe_institute',
    ))
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from runtime.context import EOSContext


class MessageDirection(Enum):
    UPWARD   = 'upward'    # agent → portfolio / founder
    DOWNWARD = 'downward'  # portfolio → CEO → role agents
    LATERAL  = 'lateral'   # peer agents


class MessageType(Enum):
    TASK   = 'task'    # work to be done
    REPORT = 'report'  # status / completion
    ALERT  = 'alert'   # urgent signal
    QUERY  = 'query'   # information request
    RESULT = 'result'  # query response


@dataclass
class AgentMessage:
    from_agent:        str
    to_agent:          str
    direction:         MessageDirection
    content:           str
    message_type:      MessageType
    venture_id:        str = ''
    requires_response: bool = False
    priority:          int = 3   # 1=critical, 5=low
    created_at:        datetime = field(default_factory=datetime.now)


class AgentMessageBus:
    """
    Persists agent messages to Neon events table.
    Allows agents to query their inbox at runtime.
    """

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx = ctx

    def send(self, message: AgentMessage) -> bool:
        try:
            from runtime.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO events (
                        id, org_id, event_type,
                        payload_json, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (
                        str(uuid.uuid4()),
                        self.ctx.org_id,
                        'agent_message',
                        json.dumps({
                            'from':             message.from_agent,
                            'to':               message.to_agent,
                            'direction':        message.direction.value,
                            'content':          message.content,
                            'type':             message.message_type.value,
                            'venture_id':       message.venture_id,
                            'requires_response': message.requires_response,
                            'priority':         message.priority,
                        }),
                    ),
                )
            return True
        except Exception as e:
            print(f'[MessageBus] Send: {e}')
            return False

    def get_messages_for(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> list[dict]:
        try:
            from runtime.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json, created_at
                    FROM events
                    WHERE org_id      = %s
                      AND event_type  = 'agent_message'
                      AND payload_json->>'to' = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (self.ctx.org_id, agent_id, limit),
                )
                results = []
                for row in cur.fetchall():
                    data = row['payload_json'] if isinstance(row, dict) else row[0]
                    ts   = row['created_at']   if isinstance(row, dict) else row[1]
                    if isinstance(data, str):
                        try:
                            data = json.loads(data)
                        except Exception:
                            data = {'content': data}
                    data['created_at'] = str(ts)
                    results.append(data)
                return results
        except Exception as e:
            print(f'[MessageBus] Get: {e}')
            return []

    def get_pending_tasks(self, agent_id: str) -> list[dict]:
        """Return unresolved task messages for this agent."""
        messages = self.get_messages_for(agent_id)
        return [
            m for m in messages
            if m.get('type') == 'task' and not m.get('completed')
        ]
