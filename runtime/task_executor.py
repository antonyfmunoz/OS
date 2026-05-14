"""
TaskExecutor — agent task execution layer.

Agents don't just respond — they execute typed tasks.
Each task type has a handler. High-risk tasks require approval.
All task executions are persisted to Neon for audit.

Usage:
    from runtime.task_executor import TaskExecutor, AgentTask
    import uuid

    executor = TaskExecutor(ctx)
    task = AgentTask(
        id=str(uuid.uuid4())[:8],
        agent_id='research_agent',
        venture_id='lyfe_institute',
        task_type='research',
        description='Analyze men coaching market',
        inputs={'query': 'men coaching market 2025'},
    )
    result = executor.execute(task)
    print(result.status.value, result.outputs)
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from runtime.context import EOSContext


class TaskStatus(Enum):
    PENDING   = 'pending'
    RUNNING   = 'running'
    COMPLETED = 'completed'
    FAILED    = 'failed'
    BLOCKED   = 'blocked'   # waiting for human approval


@dataclass
class AgentTask:
    id:               str
    agent_id:         str
    venture_id:       str
    task_type:        str
    description:      str
    inputs:           dict = field(default_factory=dict)
    outputs:          dict = field(default_factory=dict)
    status:           TaskStatus = TaskStatus.PENDING
    created_at:       datetime = field(default_factory=datetime.now)
    completed_at:     Optional[datetime] = None
    error:            str = ''
    requires_approval: bool = False


# Tasks that touch external systems on behalf of the founder
_HIGH_RISK_TASKS = frozenset({'send_dm', 'send_email'})


class TaskExecutor:
    """
    Maps task types to handlers and executes them.
    High-risk tasks are blocked for approval rather than executed.
    """

    TASK_HANDLERS = {
        'research':      '_handle_research',
        'draft_message': '_handle_draft',
        'analyze':       '_handle_analyze',
        'scan_pipeline': '_handle_pipeline',
        'generate_brief': '_handle_brief',
        'web_search':    '_handle_search',
        'log_lead':      '_handle_log_lead',
        'send_dm':       '_handle_send_dm',
    }

    def __init__(self, ctx: EOSContext) -> None:
        self.ctx = ctx

    def execute(self, task: AgentTask) -> AgentTask:
        handler_name = self.TASK_HANDLERS.get(task.task_type)
        if not handler_name:
            task.status = TaskStatus.FAILED
            task.error  = f'Unknown task type: {task.task_type}'
            return task

        # High-risk tasks require approval before execution
        if task.task_type in _HIGH_RISK_TASKS:
            task.requires_approval = True
            task.status            = TaskStatus.BLOCKED
            self._queue_for_approval(task)
            return task

        try:
            task.status = TaskStatus.RUNNING
            self._save_task(task)
            handler = getattr(self, handler_name)
            task    = handler(task)
            task.status       = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error  = str(e)
            print(f'[TaskExecutor] Failed: {task.task_type} — {e}')

        self._save_task(task)
        return task

    # ─── Handlers ─────────────────────────────────────────────────────────────

    def _handle_research(self, task: AgentTask) -> AgentTask:
        query = task.inputs.get('query', task.description)
        from execution.runtime.model_router import get_router, TaskType
        router = get_router(self.ctx)
        model  = router.route(TaskType.ANALYSIS)
        if model:
            result = router.call(
                model,
                prompt=(
                    f'Research request: {query}\n\n'
                    f'Provide a concise, factual answer. '
                    f'3-5 sentences maximum.'
                ),
                max_tokens=300,
            )
            task.outputs['result'] = result or ''
        return task

    def _handle_draft(self, task: AgentTask) -> AgentTask:
        recipient = task.inputs.get('recipient', 'prospect')
        context   = task.inputs.get('context', '')
        from execution.runtime.model_router import get_router, TaskType
        router = get_router(self.ctx)
        model  = router.route(TaskType.CONVERSATION)
        if model:
            draft = router.call(
                model,
                prompt=(
                    f'Draft a message to {recipient}.\n'
                    f'Context: {context}\n'
                    f'Tone: direct, professional.\n'
                    f'Draft only. No explanation.'
                ),
                max_tokens=200,
            )
            task.outputs['draft'] = draft or ''
        return task

    def _handle_analyze(self, task: AgentTask) -> AgentTask:
        subject = task.inputs.get('subject', task.description)
        context = task.inputs.get('context', '')
        from execution.runtime.model_router import get_router, TaskType
        router = get_router(self.ctx)
        model  = router.route(TaskType.ANALYSIS)
        if model:
            result = router.call(
                model,
                prompt=(
                    f'Analyze: {subject}\n'
                    f'Context: {context}\n'
                    f'Return: key finding, risk, recommendation.'
                ),
                max_tokens=250,
            )
            task.outputs['analysis'] = result or ''
        return task

    def _handle_pipeline(self, task: AgentTask) -> AgentTask:
        import json as _json
        venture_id = task.inputs.get('venture_id', task.venture_id)
        from state.storage.db import get_conn
        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                """
                SELECT payload_json
                FROM events
                WHERE org_id     = %s
                  AND event_type = 'pipeline_entry'
                  AND payload_json->>'venture_id' = %s
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (self.ctx.org_id, venture_id),
            )
            leads = []
            for row in cur.fetchall():
                data = row['payload_json'] if isinstance(row, dict) else row[0]
                if isinstance(data, str):
                    try:
                        data = _json.loads(data)
                    except Exception:
                        data = {}
                leads.append(data)
        task.outputs['leads'] = leads
        task.outputs['count'] = len(leads)
        return task

    def _handle_brief(self, task: AgentTask) -> AgentTask:
        from runtime.portfolio_advisor import PortfolioAdvisor as PortfolioAgent
        pa       = PortfolioAgent(self.ctx)
        ventures = pa.scan_all_ventures()
        task.outputs['brief'] = pa.generate_portfolio_brief(ventures)
        return task

    def _handle_search(self, task: AgentTask) -> AgentTask:
        query = task.inputs.get('query', task.description)
        from execution.runtime.model_router import get_router, TaskType
        router = get_router(self.ctx)
        model  = router.route(TaskType.ANALYSIS)
        if model:
            result = router.call(model, prompt=query, max_tokens=300)
            task.outputs['result'] = result or ''
        return task

    def _handle_log_lead(self, task: AgentTask) -> AgentTask:
        import json as _json
        from state.storage.db import get_conn
        lead_data = task.inputs.get('lead', task.inputs)
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
                    'pipeline_entry',
                    _json.dumps(lead_data),
                ),
            )
        task.outputs['logged'] = True
        return task

    def _handle_send_dm(self, task: AgentTask) -> AgentTask:
        # Should never reach here — blocked in execute() before dispatch
        task.status            = TaskStatus.BLOCKED
        task.requires_approval = True
        return task

    # ─── Approval + persistence ───────────────────────────────────────────────

    def _queue_for_approval(self, task: AgentTask) -> None:
        self._save_task(task)
        print(f'[TaskExecutor] Queued for approval: {task.task_type} — {task.id}')

    def _save_task(self, task: AgentTask) -> None:
        try:
            import json as _json
            from state.storage.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                cur.execute(
                    """
                    INSERT INTO events (
                        id, org_id, event_type,
                        payload_json, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        str(uuid.uuid4()),
                        self.ctx.org_id,
                        'agent_task_execution',
                        _json.dumps({
                            'task_id': task.id,
                            'agent':   task.agent_id,
                            'type':    task.task_type,
                            'status':  task.status.value,
                            'venture': task.venture_id,
                            'inputs':  task.inputs,
                            'outputs': task.outputs,
                            'error':   task.error,
                        }),
                    ),
                )
        except Exception as e:
            print(f'[TaskExecutor] Save: {e}')
