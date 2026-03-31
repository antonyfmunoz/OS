"""
DRIP Matrix — Dan Martell's task audit framework.
Delegate, Replace, Invest, Produce.
Audits tasks by energy impact and financial value.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv('/opt/OS/eos_ai/.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')

# High Energy + High Value = PRODUCE (do it yourself)
# High Energy + Low Value = INVEST (train someone)
# Low Energy + High Value = REPLACE (hire specialist)
# Low Energy + Low Value = DELEGATE (give to EA/agent)

DRIP_QUADRANTS = {
    'delegate': {
        'label': 'DELEGATE',
        'description': 'Low energy drain, low financial value. Give to DEX immediately.',
        'action': 'DEX handles this. Remove from your plate today.',
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


def classify_task_drip(task: str, ctx=None) -> dict:
    """Classify a single task into a DRIP quadrant using LLM."""
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        result = router.call(model, f"""Apply Dan Martell's DRIP Matrix to classify this task.

Task: {task}

Context: Antony Munoz is a founder running 3 ventures.
His genius zone: strategy, sales, product vision, content creation.
His drain zone: admin, repetitive operations, low-level coordination.

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
  "buyback_priority": "immediate|soon|later|never"}}""").strip()

        if '```' in result:
            result = result.split('```')[1].replace('json', '').strip()
        import json as _json
        data = _json.loads(result)
        quadrant_key = data.get('quadrant', 'delegate')
        data['quadrant_info'] = DRIP_QUADRANTS.get(quadrant_key, DRIP_QUADRANTS['delegate'])
        return data
    except Exception as e:
        logger.warning(f'[DRIP] classify failed: {e}')
        return {
            'quadrant': 'delegate',
            'quadrant_info': DRIP_QUADRANTS['delegate'],
            'energy_score': 0,
            'value_score': 0,
            'reasoning': 'Classification unavailable',
            'buyback_priority': 'later',
        }


def run_drip_audit(tasks: list[str], ctx=None) -> dict:
    """Run a full DRIP audit on a list of tasks."""
    results = {
        'delegate': [],
        'replace': [],
        'invest': [],
        'produce': [],
        'summary': '',
    }

    for task in tasks:
        classification = classify_task_drip(task, ctx)
        quadrant = classification.get('quadrant', 'delegate')
        results[quadrant].append({'task': task, **classification})

    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''INSERT INTO events (org_id, event_type, payload_json, handled_by)
                   VALUES (%s, %s, %s, %s)''',
                (
                    str(ctx.org_id),
                    'drip_audit',
                    json.dumps({
                        'results': results,
                        'task_count': len(tasks),
                        'audited_at': datetime.now(PDT).isoformat(),
                    }),
                    'dex_drip',
                ),
            )
    except Exception:
        pass

    return results


def format_drip_report(results: dict) -> str:
    """Format DRIP audit results for Discord."""
    lines = ['**🔍 DRIP Matrix Audit:**', '']

    for quadrant, emoji, label in [
        ('produce', '⚡', 'PRODUCE — Your genius zone'),
        ('invest', '📈', 'INVEST — Energizing but low value'),
        ('replace', '👥', 'REPLACE — Hire a specialist'),
        ('delegate', '🤖', 'DELEGATE — DEX handles this'),
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
        lines.append(
            f'💡 **{delegate_count} tasks can be given to DEX immediately.**\n'
            f'Reply `!delegate_all` to move them all.'
        )

    return '\n'.join(lines)
