"""
Agent Task Executor — polls the tasks table for
pending AI agent tasks, executes each through the
cognitive loop with the correct agent soul doc,
marks complete, and surfaces results to Discord.

Runs every 5 minutes via cron. This is the missing
link that closes the CEO agent execution loop.
"""

import os
import sys
import asyncio
import discord
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

PDT = ZoneInfo('America/Los_Angeles')
GENERAL_CHANNEL_ID = int(
    os.getenv('DISCORD_GENERAL_CHANNEL_ID', '0')
)

# Map agent IDs to soul doc paths and task types
AGENT_MAP = {
    'sales_agent': {
        'soul_doc': f'{_ROOT}/agents/sales_agent.md',
        'task_type': 'GENERATE',
        'display': 'Sales Agent',
    },
    'research_agent': {
        'soul_doc': f'{_ROOT}/agents/research_agent.md',
        'task_type': 'ANALYZE',
        'display': 'Research Agent',
    },
    'content_agent': {
        'soul_doc': f'{_ROOT}/agents/content_agent.md',
        'task_type': 'ANALYZE',
        'display': 'Content Agent',
    },
    'marketing_agent': {
        'soul_doc': f'{_ROOT}/agents/marketing_agent.md',
        'task_type': 'GENERATE',
        'display': 'Marketing Agent',
    },
    'operations_agent': {
        'soul_doc': f'{_ROOT}/agents/operations_agent.md',
        'task_type': 'GENERATE',
        'display': 'Operations Agent',
    },
    'outreach_agent': {
        'soul_doc': f'{_ROOT}/agents/outreach_agent.md',
        'task_type': 'GENERATE',
        'display': 'Outreach Agent',
    },
    'intelligence_agent': {
        'soul_doc': f'{_ROOT}/agents/intelligence_agent.md',
        'task_type': 'ANALYZE',
        'display': 'Intelligence Agent',
    },
    'finance_agent': {
        'soul_doc': f'{_ROOT}/agents/finance_agent.md',
        'task_type': 'ANALYZE',
        'display': 'Finance Agent',
    },
    'customer_success_agent': {
        'soul_doc': f'{_ROOT}/agents/customer_success_agent.md',
        'task_type': 'GENERATE',
        'display': 'Customer Success Agent',
    },
}

MAX_TASKS_PER_RUN = 5

# Signals that indicate the output requires DEX approval before action
APPROVAL_SIGNALS = [
    'send', 'post', 'publish', 'dm', 'email', 'message',
    'outreach', 'pay', 'invoice', 'charge', 'transfer',
    'reply', 'respond', 'draft', 'write to', 'reach out',
]


def load_soul_doc(path: str) -> str:
    """Read agent soul doc file. Return empty string on failure."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f'[Executor] Failed to load soul doc {path}: {e}')
        return ''


def execute_agent_task(task: dict, ctx) -> dict:
    """
    Execute a single agent task through the cognitive loop.
    Returns a result dict with status, output, agent_id, display_name, tokens.
    """
    from control_plane.runtime.cognitive_loop import CognitiveLoop
    from execution.runtime.agent_runtime import TaskType

    agent_id = task.get('assignee_id', 'default_agent')
    description = task.get('description', '')
    venture_id = task.get('venture_id') or ''

    agent_config = AGENT_MAP.get(agent_id)
    if not agent_config:
        print(f'[Executor] Agent {agent_id!r} not in AGENT_MAP — skipping.')
        return {
            'status': 'failed',
            'output': f'Agent {agent_id!r} is not registered in the executor agent map.',
            'agent_id': agent_id,
            'display_name': agent_id,
        }

    display_name = agent_config['display']
    soul_doc = load_soul_doc(agent_config['soul_doc'])
    task_type_str = agent_config['task_type']

    prompt = (
        f'You are the {display_name}.\n\n'
        f'{soul_doc[:2000]}\n\n'
        f'---\n\n'
        f'TASK ASSIGNED BY CEO AGENT:\n'
        f'{description}\n\n'
        f'Execute this task completely. Be specific and actionable. '
        f'If this requires sending something externally, draft it and flag for DEX approval. '
        f'If this is research or analysis, provide the complete output.\n\n'
        f'Venture context: {venture_id}'
    )

    task_type = getattr(TaskType, task_type_str, TaskType.GENERATE)

    try:
        loop = CognitiveLoop(ctx)
        result = loop.run(
            input=prompt,
            agent=agent_id,
            task_type=task_type,
            venture_id=venture_id or None,
        )
        return {
            'status': 'completed',
            'output': result.output or '',
            'agent_id': agent_id,
            'display_name': display_name,
            'tokens': result.tokens_used,
        }
    except Exception as e:
        print(f'[Executor] Error executing task for {agent_id}: {e}')
        return {
            'status': 'failed',
            'output': f'Execution error: {e}',
            'agent_id': agent_id,
            'display_name': display_name,
        }


def requires_approval(task: dict, result: dict) -> bool:
    """
    Check whether the task description or result output contains signals
    that indicate an external action requiring DEX approval before execution.
    """
    combined = (
        (task.get('description') or '') + ' ' + (result.get('output') or '')
    ).lower()
    return any(signal in combined for signal in APPROVAL_SIGNALS)


async def run_executor():
    """Main executor loop — poll, execute, mark complete, surface to Discord."""
    from state.context.context import load_context_from_env
    from control_plane.coordination.coordination_engine import CoordinationEngine

    print(f'[Executor] Starting — {datetime.now(PDT).strftime("%Y-%m-%d %H:%M:%S %Z")}')

    ctx = load_context_from_env()
    coordination = CoordinationEngine(ctx)

    # Pull all pending tasks for the org
    all_pending = coordination.get_task_queue(status='pending')

    # Filter to AI agent tasks we know how to handle
    agent_tasks = [
        t for t in all_pending
        if t.get('assignee_type') == 'agent'
        and t.get('assignee_id') in AGENT_MAP
    ][:MAX_TASKS_PER_RUN]

    if not agent_tasks:
        print('[Executor] No pending AI tasks.')
        return

    print(f'[Executor] Found {len(agent_tasks)} task(s) to process.')

    results_for_discord = []

    for task in agent_tasks:
        task_id = task['id']
        description = task.get('description', '')
        print(f'[Executor] Processing task {task_id[:8]} — {description[:60]}')

        # Execute through cognitive loop
        exec_result = execute_agent_task(task, ctx)

        # Mark task complete in Neon
        output_summary = exec_result.get('output', '')[:500]
        coordination.complete_task(task_id, output_summary)

        # Write task result to Notion
        try:
            from adapters.notion.notion_sync import write_task
            venture_id = task.get('venture_id') or 'lyfe_institute'
            needs_approval = requires_approval(task, exec_result)
            notion_status = 'In review' if needs_approval else 'Done'
            agent_cfg = AGENT_MAP.get(
                exec_result.get('agent_id', ''), {}
            )
            notion_page_id = write_task(
                venture_id=venture_id,
                name=(
                    f'[{agent_cfg.get("display","Agent")}] '
                    f'{description[:120]}'
                ),
                status=notion_status,
                priority='Normal',
                department='Operations',
                assignee_type='Agent',
                assigned_to=agent_cfg.get('display', 'None'),
                source=agent_cfg.get('display', 'None'),
                task_type='Agent Task',
                neon_id=task_id,
                notes=exec_result.get('output', '')[:1000],
                requires_approval=needs_approval,
            )
            if notion_page_id:
                from state.stores.task_store import TaskStore
                TaskStore().set_notion_page_id(
                    org_id=str(ctx.org_id),
                    task_id=task_id,
                    notion_page_id=notion_page_id,
                )
                print(f'[Executor] → Notion: {notion_page_id[:8]}')
        except Exception as e:
            print(f'[Executor] Notion write skipped: {e}')

        # Log full result to events table
        needs_approval = requires_approval(task, exec_result)
        payload = {
            'task_id': task_id,
            'agent_id': exec_result.get('agent_id', ''),
            'description': description,
            'result': exec_result.get('output', '')[:1000],
            'status': exec_result.get('status', 'unknown'),
            'requires_approval': needs_approval,
            'completed_at': datetime.now(PDT).isoformat(),
        }

        try:
            from state.memory.memory import AgentMemory
            AgentMemory().log_event(
                org_id=str(ctx.org_id),
                event_type='agent_task_result',
                payload=payload,
                handled_by='agent_task_executor',
            )
        except Exception as e:
            print(f'[Executor] Failed to write event for task {task_id[:8]}: {e}')

        results_for_discord.append({
            'task_id': task_id,
            'description': description,
            'agent_name': exec_result.get('display_name', exec_result.get('agent_id', '')),
            'output': exec_result.get('output', ''),
            'status': exec_result.get('status', 'unknown'),
            'needs_approval': needs_approval,
        })

        print(f'[Executor] Task {task_id[:8]} — {exec_result["status"]}')

    # Surface results to Discord
    if not results_for_discord:
        return

    if not GENERAL_CHANNEL_ID:
        print('[Executor] DISCORD_GENERAL_CHANNEL_ID not set — skipping Discord post.')
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            print(f'[Executor] Discord channel {GENERAL_CHANNEL_ID} not found.')
            await client.close()
            return

        for r in results_for_discord:
            status_emoji = '✅' if r['status'] == 'completed' else '❌'
            task_short = r['description'][:80]
            output_preview = r['output'][:400]

            message = (
                f"{status_emoji} **{r['agent_name']} completed task:**\n"
                f"_{task_short}_\n\n"
                f"{output_preview}"
            )

            if r['needs_approval']:
                message += (
                    f"\n\n⚠️ **Requires DEX approval before action.**\n"
                    f"Reply `!approve_task {r['task_id'][:8]}` to approve."
                )

            # Cap at 1900 chars
            message = message[:1900]

            try:
                await channel.send(message)
            except Exception as e:
                print(f'[Executor] Failed to send Discord message: {e}')

        await client.close()

    try:
        await client.start(os.getenv('DISCORD_BOT_TOKEN'))
    except Exception as e:
        print(f'[Executor] Discord connection failed: {e}')


if __name__ == '__main__':
    asyncio.run(run_executor())
