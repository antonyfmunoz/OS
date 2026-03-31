"""
Perfect Week — stores and applies Antony's ideal
week template. Used by week_architect.py as baseline.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path as _Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv(_Path(__file__).parent / '.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')

DEFAULT_PERFECT_WEEK = {
    'monday': {
        'theme': 'Strategy & Planning',
        'morning': 'Deep work — strategy, product, content creation (9am-12pm)',
        'afternoon': 'Team/agent reviews, weekly planning (1pm-4pm)',
        'protected': ['Deep work 9-12', 'No external calls before noon'],
    },
    'tuesday': {
        'theme': 'Sales & Revenue',
        'morning': 'Sales calls, discovery calls, follow-ups (9am-1pm)',
        'afternoon': 'Proposals, pipeline review (2pm-5pm)',
        'protected': ['Revenue activities all day'],
    },
    'wednesday': {
        'theme': 'Operations & Execution',
        'morning': 'Internal reviews, agent check-ins, execution (9am-12pm)',
        'afternoon': 'Admin, email, approvals (1pm-4pm)',
        'protected': ['Batch admin in afternoon only'],
    },
    'thursday': {
        'theme': 'Relationships & Partnerships',
        'morning': 'Partner calls, client calls, networking (9am-1pm)',
        'afternoon': 'Content creation, recording (2pm-5pm)',
        'protected': ['Content block 2-5pm'],
    },
    'friday': {
        'theme': 'Review & Improve',
        'morning': "Weekly review, metrics, what worked/didn't (9am-11am)",
        'afternoon': 'Learning, prep for next week, personal development (1pm-4pm)',
        'protected': ['No new meetings after 2pm', 'Reflection time protected'],
    },
    'saturday': {
        'theme': 'Personal & Recovery',
        'morning': 'Exercise, family, personal time',
        'afternoon': 'Rest or passion projects',
        'protected': ['Work-free unless urgent'],
    },
    'sunday': {
        'theme': 'Preparation',
        'morning': 'Weekly planning, portfolio brief review (10am-12pm)',
        'afternoon': 'Light prep, family time',
        'protected': ['Max 2 hours work'],
    },
}


def get_perfect_week(ctx=None) -> dict:
    """Get stored perfect week template or return default."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''SELECT payload_json FROM events
                   WHERE org_id = %s AND event_type = 'perfect_week'
                   ORDER BY created_at DESC LIMIT 1''',
                (str(ctx.org_id),),
            )
            row = cur.fetchone()

        if row:
            payload = row['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            return payload.get('template', DEFAULT_PERFECT_WEEK)
        return DEFAULT_PERFECT_WEEK
    except Exception:
        return DEFAULT_PERFECT_WEEK


def save_perfect_week(template: dict, ctx=None) -> bool:
    """Save a custom perfect week template."""
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
                    'perfect_week',
                    json.dumps({
                        'template': template,
                        'saved_at': datetime.now(PDT).isoformat(),
                    }),
                    'dex_perfect_week',
                ),
            )
        return True
    except Exception as e:
        logger.warning(f'[PerfectWeek] save failed: {e}')
        return False


def create_camcorder_playbook(task_name: str, description: str, ctx=None) -> str:
    """
    Camcorder Method — create a playbook from a task description.
    User describes how they do a task, DEX turns it into a reusable SOP.
    """
    try:
        from eos_ai.model_router import get_router, TaskType
        from eos_ai.context import load_context_from_env
        ctx = ctx or load_context_from_env()

        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        prompt = f"""Apply Dan Martell's Camcorder Method.
Convert this task description into a reusable SOP playbook.

Task: {task_name}
How Antony does it: {description}

Create a structured playbook with:
# Playbook: {task_name}

## Purpose
[Why this task exists]

## When to Use
[Trigger conditions]

## Inputs
[What information is needed]

## Process
[Step by step, numbered, specific]

## Quality Check
[How to verify it was done correctly]

## Time Estimate
[How long it should take]

## Trust Level
[OBSERVE/ASSIST/EXECUTE/AUTONOMOUS]

Make it specific enough that DEX can execute it exactly
as Antony would, without asking questions."""

        playbook = router.call(model, prompt, max_tokens=1500).strip()

        safe_name = re.sub(r'[^a-z0-9_]', '_', task_name.lower().replace(' ', '_'))
        filepath = f'/opt/OS/06_Skills/Ops/camcorder_{safe_name}.md'
        with open(filepath, 'w') as f:
            f.write(playbook)

        try:
            from eos_ai.skill_registry_v2 import SkillRegistryV2, SkillV2, SkillDomain, TrustLevel
            registry = SkillRegistryV2(ctx)
            skill = SkillV2(
                id=f'camcorder_{safe_name}',
                name=f'Playbook: {task_name}',
                domain=SkillDomain.OPERATIONS,
                purpose=f'Camcorder playbook for: {task_name}',
                when_to_use=f'When {task_name} needs to be done',
                inputs=['context'],
                outputs=['completed task'],
                process=playbook,
                trust_level=TrustLevel.ASSIST,
            )
            registry.register(skill)
        except Exception:
            pass

        logger.info(f'[PerfectWeek] Camcorder playbook created: {filepath}')
        return playbook
    except Exception as e:
        logger.warning(f'[PerfectWeek] Camcorder failed: {e}')
        return ''


def save_preloaded_year(year_plan: dict, ctx=None) -> bool:
    """
    Save the annual plan to Neon. Structure:
    {
      'q1': {'rocks': [], 'revenue_target': 0, 'key_dates': []},
      'q2': {...}, 'q3': {...}, 'q4': {...},
      'vacation_blocks': ['2026-07-01 to 2026-07-14'],
      'major_milestones': [],
      'annual_revenue_target': 0,
    }
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'preloaded_year',
                json.dumps({
                    'plan': year_plan,
                    'saved_at': datetime.now(PDT).isoformat(),
                }),
                'dex_annual_plan',
            ))
        return True
    except Exception as e:
        logger.warning(f'[PerfectWeek] save_preloaded_year failed: {e}')
        return False


def get_preloaded_year(ctx=None) -> dict:
    """Get the most recently saved annual plan."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'preloaded_year'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (str(ctx.org_id),))
            row = cur.fetchone()
        if row:
            p = row['payload_json']
            if isinstance(p, str):
                p = json.loads(p)
            return p.get('plan', {})
        return {}
    except Exception as e:
        logger.warning(f'[PerfectWeek] get_preloaded_year failed: {e}')
        return {}


def get_current_quarter_rocks(ctx=None) -> list[str]:
    """Get this quarter's rocks from the annual plan."""
    plan = get_preloaded_year(ctx)
    if not plan:
        return []
    month = datetime.now().month
    quarter = f'q{(month - 1) // 3 + 1}'
    return plan.get(quarter, {}).get('rocks', [])
