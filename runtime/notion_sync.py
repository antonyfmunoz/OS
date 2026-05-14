"""
Notion Sync — EOS runtime write layer.
Pushes EOS primitives to Notion databases.
Called by cognitive_loop, orchestrator, and agent_runtime.

All write functions return Notion page ID (str) or '' on failure.
Failures are logged but never raise — EOS continues without Notion.
"""

import os
import json as _json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

NOTION_VERSION = '2022-06-28'
TOKEN = os.getenv('NOTION_API_KEY', '')
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json',
}

# venture_id → env prefix
_PREFIXES = {
    'personal_brand': 'NOTION_PERSONAL_BRAND',
    'lyfe_institute': 'NOTION_LYFE_INSTITUTE',
    'empyrean_creative': 'NOTION_EMPYREAN_CREATIVE',
}

# human-readable DB key → env suffix
_DB_SUFFIXES = {
    'tasks': 'TASKS',
    'goals': 'GOALS_OKRS',
    'meetings': 'MEETINGS',
    'documents': 'DOCUMENTS',
    'metrics': 'METRICS_KPIS',
    'decisions': 'DECISIONS',
    'roles': 'ROLES',
    'tools': 'TOOLS',
    'skills': 'SKILLS',
    'workflows': 'WORKFLOWS',
    'pipeline': 'PIPELINE_CRM',
    'projects': 'PROJECTS',
    'budget': 'BUDGET',
}


def get_db_id(venture_id: str, db_key: str) -> str:
    """Return Notion DB ID for a venture+primitive. '' if not found."""
    prefix = _PREFIXES.get(venture_id, '')
    if not prefix:
        return ''
    suffix = _DB_SUFFIXES.get(db_key, db_key.upper())
    return os.getenv(f'{prefix}_{suffix}_DB', '')


# ── Property builders ─────────────────────────────

def _title(value: str) -> dict:
    return {'title': [{'text': {'content': str(value)[:2000]}}]}


def _text(value: str) -> dict:
    return {'rich_text': [{'text': {'content': str(value)[:2000]}}]}


def _select(value: str) -> dict:
    return {'select': {'name': str(value)}}


def _date(value: str) -> dict:
    return {'date': {'start': str(value)}}


def _number(value: float) -> dict:
    return {'number': float(value)}


def _checkbox(value: bool) -> dict:
    return {'checkbox': bool(value)}


# ── Core helpers ──────────────────────────────────

def _create_page(db_id: str, properties: dict) -> str:
    """Create a page in a Notion database. Returns page ID or ''."""
    try:
        resp = requests.post(
            'https://api.notion.com/v1/pages',
            headers=HEADERS,
            json={
                'parent': {'database_id': db_id},
                'properties': properties,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get('id', '')
        print(f'[NotionSync] create failed: '
              f'{resp.json().get("message", "")}')
        return ''
    except Exception as e:
        print(f'[NotionSync] create error: {e}')
        return ''


def _update_page(page_id: str, properties: dict) -> bool:
    """Update a Notion page. Returns True on success."""
    try:
        resp = requests.patch(
            f'https://api.notion.com/v1/pages/{page_id}',
            headers=HEADERS,
            json={'properties': properties},
            timeout=15,
        )
        if resp.status_code == 200:
            return True
        print(f'[NotionSync] update failed: '
              f'{resp.json().get("message", "")}')
        return False
    except Exception as e:
        print(f'[NotionSync] update error: {e}')
        return False


# ── Write primitives ──────────────────────────────

def write_task(
    venture_id: str,
    name: str,
    status: str = 'Not started',
    priority: str = 'Normal',
    department: str = 'Operations',
    assigned_to: str = 'None',
    assignee_type: str = 'Agent',
    source: str = 'System',
    task_type: str = 'Agent Task',
    due_date: str = '',
    neon_id: str = '',
    notes: str = '',
    requires_approval: bool = False,
) -> str:
    """Create a task row. Returns Notion page ID or ''."""
    db_id = get_db_id(venture_id, 'tasks')
    if not db_id:
        print(f'[NotionSync] No Tasks DB for {venture_id}')
        return ''
    props: dict = {
        'Name': _title(name),
        'Status': _select(status),
        'Priority': _select(priority),
        'Department': _select(department),
        'Assigned To': _select(assigned_to),
        'Assignee Type': _select(assignee_type),
        'Source': _select(source),
        'Type': _select(task_type),
        'Requires Approval': _checkbox(requires_approval),
    }
    if due_date:
        props['Due Date'] = _date(due_date)
    if neon_id:
        props['Neon ID'] = _text(neon_id)
    if notes:
        props['Notes'] = _text(notes)
    return _create_page(db_id, props)


def update_task_status(page_id: str, status: str) -> bool:
    """Update task status by Notion page ID."""
    return _update_page(page_id, {'Status': _select(status)})


def write_pipeline_entry(
    venture_id: str,
    name: str,
    stage: str = 'Lead',
    entry_type: str = 'Lead',
    channel: str = 'Instagram DM',
    score: int = 0,
    email: str = '',
    notes: str = '',
    next_action: str = '',
    source: str = '',
    ai_qualified: bool = False,
    value: float = 0,
) -> str:
    """Create a pipeline/CRM row. Returns page ID or ''."""
    db_id = get_db_id(venture_id, 'pipeline')
    if not db_id:
        print(f'[NotionSync] No Pipeline DB for {venture_id}')
        return ''
    props: dict = {
        'Name': _title(name),
        'Stage': _select(stage),
        'Type': _select(entry_type),
        'Channel': _select(channel),
        'Score': _number(score),
        'AI Qualified': _checkbox(ai_qualified),
    }
    if email:
        props['Email'] = {'email': email}
    if notes:
        props['Notes'] = _text(notes)
    if next_action:
        props['Next Action'] = _text(next_action)
    if source:
        props['Source'] = _text(source)
    if value is not None:
        props['Value'] = _number(value)
    return _create_page(db_id, props)


def update_pipeline_stage(page_id: str, stage: str) -> bool:
    """Update pipeline entry stage by Notion page ID."""
    return _update_page(page_id, {'Stage': _select(stage)})


def write_metric(
    venture_id: str,
    metric_name: str,
    value: float,
    target: float = 0,
    unit: str = '',
    period: str = 'Daily',
    category: str = 'Sales',
    department: str = 'Sales',
    linked_goal: str = '',
    notes: str = '',
) -> str:
    """Create a metric/KPI row. Returns page ID or ''."""
    db_id = get_db_id(venture_id, 'metrics')
    if not db_id:
        print(f'[NotionSync] No Metrics DB for {venture_id}')
        return ''
    today = datetime.now().strftime('%Y-%m-%d')
    props: dict = {
        'Metric': _title(metric_name),
        'Value': _number(value),
        'Target': _number(target),
        'Period': _select(period),
        'Category': _select(category),
        'Department': _select(department),
        'Last Updated': _date(today),
    }
    if unit:
        props['Unit'] = _text(unit)
    if linked_goal:
        props['Linked Goal'] = _text(linked_goal)
    if notes:
        props['Notes'] = _text(notes)
    return _create_page(db_id, props)


def write_meeting(
    venture_id: str,
    name: str,
    meeting_type: str = 'Sales Call',
    status: str = 'Scheduled',
    person: str = '',
    email: str = '',
    date: str = '',
    duration_min: int = 30,
    outcomes: str = '',
    open_loops: str = '',
    meet_link: str = '',
    prep_notes: str = '',
) -> str:
    """Create a meeting row. Returns page ID or ''."""
    db_id = get_db_id(venture_id, 'meetings')
    if not db_id:
        # Fall back to EOS-root Meetings DB
        db_id = os.getenv('NOTION_MEETINGS_ID', '')
    if not db_id:
        print(f'[NotionSync] No Meetings DB for {venture_id}')
        return ''
    props: dict = {
        'Name': _title(name),
        'Type': _select(meeting_type),
        'Status': _select(status),
        'Duration (min)': _number(duration_min),
    }
    if person:
        props['Person'] = _text(person)
    if email:
        props['Email'] = {'email': email}
    if date:
        props['Date'] = _date(date)
    if outcomes:
        props['Outcomes'] = _text(outcomes)
    if open_loops:
        props['Open Loops'] = _text(open_loops)
    if meet_link:
        props['Meet Link'] = {'url': meet_link}
    if prep_notes:
        props['Prep Notes'] = _text(prep_notes)
    return _create_page(db_id, props)


def write_decision(
    venture_id: str,
    decision: str,
    department: str = 'Operations',
    impact: str = 'Medium',
    made_by: str = 'Founder',
    rationale: str = '',
    outcome: str = '',
) -> str:
    """Create a decision row. Returns page ID or ''."""
    db_id = get_db_id(venture_id, 'decisions')
    if not db_id:
        print(f'[NotionSync] No Decisions DB for {venture_id}')
        return ''
    today = datetime.now().strftime('%Y-%m-%d')
    props: dict = {
        'Decision': _title(decision),
        'Department': _select(department),
        'Impact': _select(impact),
        'Made By': _select(made_by),
        'Status': _select('Active'),
        'Date': _date(today),
    }
    if rationale:
        props['Rationale'] = _text(rationale)
    if outcome:
        props['Outcome'] = _text(outcome)
    return _create_page(db_id, props)


def write_document(
    venture_id: str,
    title: str,
    doc_type: str = 'Knowledge Entry',
    department: str = 'Operations',
    category: str = 'General',
    content: str = '',
    source: str = 'System',
    confidence: str = 'Medium',
    file_path: str = '',
    linked_entity: str = '',
) -> str:
    """Create a document/knowledge row. Returns page ID or ''."""
    db_id = get_db_id(venture_id, 'documents')
    if not db_id:
        print(f'[NotionSync] No Documents DB for {venture_id}')
        return ''
    props: dict = {
        'Title': _title(title),
        'Type': _select(doc_type),
        'Department': _select(department),
        'Category': _select(category),
        'Source': _select(source),
        'Confidence': _select(confidence),
        'Status': _select('Active'),
    }
    if content:
        props['Content'] = _text(content[:2000])
    if file_path:
        props['File Path'] = _text(file_path)
    if linked_entity:
        props['Linked Entity'] = _text(linked_entity)
    return _create_page(db_id, props)


logger = logging.getLogger(__name__)


def push_pending_tasks_to_notion(venture_id: str, ctx=None) -> int:
    """
    Push tasks from Neon to Notion that don't have a notion_page_id yet.
    Returns count of tasks pushed.
    """
    db_id = get_db_id(venture_id, 'tasks')
    if not db_id:
        return 0

    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn

        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                '''
                SELECT id, description,
                       assignee_id, assignee_type,
                       priority, status,
                       venture_id, created_at
                FROM tasks
                WHERE org_id = %s
                  AND (notion_page_id IS NULL
                       OR notion_page_id = '')
                  AND status != 'cancelled'
                  AND created_at >= NOW() - INTERVAL '7 days'
                ORDER BY created_at DESC
                LIMIT 20
                ''',
                (str(ctx.org_id),),
            )
            rows = cur.fetchall()

        status_map = {
            'pending': 'Not started',
            'in_progress': 'In progress',
            'completed': 'Done',
            'blocked': 'Blocked',
        }
        priority_map = {
            'critical': 'Critical',
            'high': 'High',
            'normal': 'Normal',
            'low': 'Low',
        }

        pushed = 0
        for row in rows:
            task_id = str(row['id'])
            description = row.get('description', '') or ''
            assignee = row.get('assignee_id', '') or ''
            priority = row.get('priority', 'normal') or 'normal'
            status = row.get('status', 'pending') or 'pending'
            assignee_type_raw = row.get('assignee_type', '') or ''

            notion_status = status_map.get(status, 'Not started')
            notion_priority = priority_map.get(priority.lower(), 'Normal')
            assignee_type = 'Agent' if assignee_type_raw == 'agent' else 'Human'

            notion_page_id = write_task(
                venture_id=venture_id,
                name=description[:200],
                status=notion_status,
                priority=notion_priority,
                assignee_type=assignee_type,
                assigned_to=assignee[:100] if assignee else 'Founder',
                source='Neon Sync',
                task_type='Task',
                neon_id=task_id,
            )

            if notion_page_id:
                from state.stores.task_store import TaskStore
                TaskStore().set_notion_page_id(
                    org_id=str(ctx.org_id),
                    task_id=task_id,
                    notion_page_id=notion_page_id,
                )
                pushed += 1

        return pushed
    except Exception as e:
        print(f'[NotionSync] push_tasks failed for {venture_id}: {e}')
        return 0


def push_all_ventures(ctx=None) -> dict:
    """Push pending tasks to Notion for all ventures in VENTURES_JSON."""
    ventures = _json.loads(os.getenv('VENTURES_JSON', '[]').strip("'\""))
    results = {}
    for v in ventures:
        vid = v.get('id', '')
        if not vid:
            continue
        pushed = push_pending_tasks_to_notion(vid, ctx)
        results[vid] = {'pushed': pushed}
    return results
