"""
Ideal Week — stores and applies Antony's ideal
week template. Used by week_architect.py as baseline.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path as _Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


load_dotenv(_Path(__file__).parent / '.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')

DEFAULT_IDEAL_WEEK = {
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


def get_ideal_week(ctx=None) -> dict:
    """Get stored ideal week template or return default."""
    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''SELECT payload_json FROM events
                   WHERE org_id = %s AND event_type = 'ideal_week'
                   ORDER BY created_at DESC LIMIT 1''',
                (str(ctx.org_id),),
            )
            row = cur.fetchone()

        if row:
            payload = row['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            return payload.get('template', DEFAULT_IDEAL_WEEK)
        return DEFAULT_IDEAL_WEEK
    except Exception:
        return DEFAULT_IDEAL_WEEK


def save_ideal_week(template: dict, ctx=None) -> bool:
    """Save a custom ideal week template."""
    try:
        from runtime.context import load_context_from_env
        from state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()

        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type='ideal_week',
            payload={
                'template': template,
                'saved_at': datetime.now(PDT).isoformat(),
            },
            handled_by='dex_ideal_week',
        )
        return True
    except Exception as e:
        logger.warning(f'[IdealWeek] save failed: {e}')
        return False


def create_process_capture(task_name: str, description: str, ctx=None) -> str:
    """
    Process Capture — create a playbook from a task description.
    User describes how they do a task, DEX turns it into a reusable SOP.
    """
    try:
        from execution.runtime.model_router import get_router, TaskType
        from runtime.context import load_context_from_env
        ctx = ctx or load_context_from_env()

        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        prompt = f"""Apply Dan Martell's Process Capture.
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
        filepath = f'{_ROOT}/skills/Ops/process_capture_{safe_name}.md'
        with open(filepath, 'w') as f:
            f.write(playbook)

        try:
            from runtime.skill_registry_v2 import SkillRegistryV2, SkillV2, SkillDomain, TrustLevel
            registry = SkillRegistryV2(ctx)
            skill = SkillV2(
                id=f'process_capture_{safe_name}',
                name=f'Playbook: {task_name}',
                domain=SkillDomain.OPERATIONS,
                purpose=f'Process Capture playbook for: {task_name}',
                when_to_use=f'When {task_name} needs to be done',
                inputs=['context'],
                outputs=['completed task'],
                process=playbook,
                trust_level=TrustLevel.ASSIST,
            )
            registry.register(skill)
        except Exception:
            pass

        logger.info(f'[IdealWeek] Process Capture playbook created: {filepath}')
        return playbook
    except Exception as e:
        logger.warning(f'[IdealWeek] Process Capture failed: {e}')
        return ''


def save_annual_architecture(year_plan: dict, ctx=None) -> bool:
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
        from runtime.context import load_context_from_env
        from state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()
        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type='annual_architecture',
            payload={
                'plan': year_plan,
                'saved_at': datetime.now(PDT).isoformat(),
            },
            handled_by='dex_annual_plan',
        )
        return True
    except Exception as e:
        logger.warning(f'[IdealWeek] save_annual_architecture failed: {e}')
        return False


def get_annual_architecture(ctx=None) -> dict:
    """Get the most recently saved annual plan."""
    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'annual_architecture'
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
        logger.warning(f'[IdealWeek] get_annual_architecture failed: {e}')
        return {}


def get_current_quarter_rocks(ctx=None) -> list[str]:
    """Get this quarter's rocks from the annual plan."""
    plan = get_annual_architecture(ctx)
    if not plan:
        return []
    month = datetime.now().month
    quarter = f'q{(month - 1) // 3 + 1}'
    return plan.get(quarter, {}).get('rocks', [])
