"""
Task Yield Matrix — task delegation audit framework.
Delegate, Replace, Invest, Produce.
Audits tasks by energy impact and financial value.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv
from substrate.self_model import get_handler_prefix as _ghp

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')

# High Energy + High Value = PRODUCE (do it yourself)
# High Energy + Low Value = INVEST (train someone)
# Low Energy + High Value = REPLACE (hire specialist)
# Low Energy + Low Value = DELEGATE (give to EA/agent)

YIELD_QUADRANTS = {
    'delegate': {
        'label': 'DELEGATE',
        'description': 'Low energy drain, low financial value. Delegate to the AI immediately.',
        'action': 'The AI handles this. Remove from your plate today.',
        'emoji': '🤖',
    },
    'replace': {
        'label': 'REPLACE',
        'description': 'Low energy drain, high financial value. Hire a specialist.',
        'action': 'This generates money but drains you. Replace yourself with a specialist.',
        'emoji': '👥',
    },
    'invest': {
        'label': 'INVEST',
        'description': 'High energy gain, low financial value. Worth doing for growth.',
        'action': "This energizes you but doesn't pay directly. Do it strategically.",
        'emoji': '📈',
    },
    'produce': {
        'label': 'PRODUCE',
        'description': 'High energy gain, high financial value. This is your genius zone.',
        'action': 'Protect this time aggressively. This is where you should spend most of your time.',
        'emoji': '⚡',
    },
}


def classify_task_yield(task: str, ctx=None) -> dict:
    """Classify a single task into a Task Yield Matrix quadrant using LLM."""
    try:
        from substrate.contracts.agent_types import TaskType
        from adapters.models.model_router import get_router
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        result = router.call(model, f"""Apply the Task Yield Matrix to classify this task.

Task: {task}

Context: The founder runs multiple ventures.
Their genius zone: strategy, sales, product vision, content creation.
Their drain zone: admin, repetitive operations, low-level coordination.

Rate the task:
- energy_score: -2 (major drain) to +2 (major energy gain)
- value_score: 1 (low financial impact) to 10 (direct revenue impact)

Based on scores, assign quadrant:
- delegate: energy <= 0 AND value <= 5
- replace: energy <= 0 AND value > 5
- invest: energy > 0 AND value <= 5
- produce: energy > 0 AND value > 5

Return JSON only:
{{"quadrant": "delegate|replace|invest|produce",
  "energy_score": number,
  "value_score": number,
  "reasoning": "one sentence why",
  "founder_priority": "immediate|soon|later|never"}}""").strip()

        if '```' in result:
            result = result.split('```')[1].replace('json', '').strip()
        data = json.loads(result)
        quadrant_key = data.get('quadrant', 'delegate')
        data['quadrant_info'] = YIELD_QUADRANTS.get(quadrant_key, YIELD_QUADRANTS['delegate'])
        return data
    except Exception as e:
        logger.warning(f'[TaskYield] classify failed: {e}')
        return {
            'quadrant': 'delegate',
            'quadrant_info': YIELD_QUADRANTS['delegate'],
            'energy_score': 0,
            'value_score': 0,
            'reasoning': 'Classification unavailable',
            'founder_priority': 'later',
        }


def run_yield_audit(tasks: list[str], ctx=None) -> dict:
    """Run a full Task Yield audit on a list of tasks."""
    results = {
        'delegate': [],
        'replace': [],
        'invest': [],
        'produce': [],
        'summary': '',
    }

    for task in tasks:
        classification = classify_task_yield(task, ctx)
        quadrant = classification.get('quadrant', 'delegate')
        results[quadrant].append({'task': task, **classification})

    try:
        from substrate.state.context.context import load_context_from_env
        from substrate.state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()
        # Strip derived quadrant_info before persisting to Neon
        clean_results = {}
        for quadrant, items in results.items():
            if quadrant == 'summary':
                clean_results[quadrant] = items
                continue
            clean_results[quadrant] = [
                {k: v for k, v in item.items() if k != 'quadrant_info'}
                for item in items
            ]
        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type='yield_audit',
            payload={
                'results': clean_results,
                'task_count': len(tasks),
                'audited_at': datetime.now(PDT).isoformat(),
            },
            handled_by=f'{_ghp()}yield',
        )
    except Exception as e:
        logger.warning(f'[TaskYield] audit persist failed: {e}')

    return results


def format_yield_report(results: dict) -> str:
    """Format Task Yield audit results for Discord."""
    lines = ['**🔍 Task Yield Audit:**', '']

    for quadrant, emoji, label in [
        ('produce', '⚡', 'PRODUCE — Your genius zone'),
        ('invest', '📈', 'INVEST — Energizing but low value'),
        ('replace', '👥', 'REPLACE — Hire a specialist'),
        ('delegate', '🤖', 'DELEGATE — the AI handles this'),
    ]:
        items = results.get(quadrant, [])
        if items:
            lines.append(f'{emoji} **{label} ({len(items)}):**')
            for item in items[:5]:
                lines.append(f'  • {item["task"][:60]}')
                lines.append(f'    ↳ {item.get("reasoning", "")}')
            lines.append('')

    delegate_count = len(results.get('delegate', []))
    if delegate_count > 0:
        _ai_fmt = os.environ.get("AI_NAME", "the AI")
        lines.append(
            f'💡 **{delegate_count} tasks can be given to {_ai_fmt} immediately.**\n'
            f'Reply `!delegate_all` to move them all.'
        )

    return '\n'.join(lines)
