"""
Notion Tasks → Neon Sync
Polls the three venture Tasks databases for new/updated items
and writes them to the Neon events table so they appear in the
morning brief Section 1 (Your list).

Runs every 15 minutes via cron alongside call_prep.py.
"""

import sys
import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
from dotenv import load_dotenv
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'eos_ai', '.env'))

NOTION_TOKEN = os.getenv('NOTION_API_KEY')
STATE_FILE = Path(_ROOT) / "scripts" / "notion_tasks_sync_state.json"

DATABASES = {
    'lyfe_institute':    os.getenv('NOTION_YOUR_LIST_LYFE'),
    'empyrean_creative': os.getenv('NOTION_YOUR_LIST_EMPYREAN'),
    'personal_brand':    os.getenv('NOTION_YOUR_LIST_BRAND'),
}

HEADERS = {
    'Authorization': f'Bearer {NOTION_TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {'synced': {}}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def query_database(db_id: str) -> list:
    try:
        resp = requests.post(
            f'https://api.notion.com/v1/databases/{db_id}/query',
            headers=HEADERS,
            json={'page_size': 50},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        return resp.json().get('results', [])
    except Exception as e:
        print(f'[TasksSync] Query failed for {db_id}: {e}')
        return []


def extract_task(page: dict) -> dict:
    props = page.get('properties', {})

    title_list = props.get('Name', {}).get('title', [])
    name = title_list[0]['text']['content'] if title_list else ''

    status_prop = props.get('Status', {}).get('select')
    status = status_prop.get('name') if status_prop else 'Not Started'

    priority_prop = props.get('Priority', {}).get('select')
    priority = priority_prop.get('name') if priority_prop else 'Medium'

    type_prop = props.get('Type', {}).get('select')
    task_type = type_prop.get('name') if type_prop else 'Task'

    venture_prop = props.get('Venture', {}).get('select')
    venture = venture_prop.get('name') if venture_prop else ''

    assigned_prop = props.get('Assigned To', {}).get('select')
    assigned_to = assigned_prop.get('name') if assigned_prop else 'Antony'

    source_prop = props.get('Source', {}).get('select')
    source = source_prop.get('name') if source_prop else 'Notion'

    due_date_prop = props.get('Due Date', {}).get('date')
    due_date = due_date_prop.get('start') if due_date_prop else None

    notes_list = props.get('Notes', {}).get('rich_text', [])
    notes = notes_list[0]['text']['content'] if notes_list else ''

    completed = status in ('Done', 'Archived')

    return {
        'page_id':     page['id'],
        'last_edited': page.get('last_edited_time', ''),
        'name':        name,
        'status':      status,
        'priority':    priority,
        'task_type':   task_type,
        'venture':     venture,
        'assigned_to': assigned_to,
        'source':      source,
        'due_date':    due_date,
        'notes':       notes,
        'completed':   completed,
    }


def write_to_neon(task: dict, venture_id: str) -> bool:
    try:
        from eos_ai.db import get_conn
        from eos_ai.context import load_context_from_env

        ctx = load_context_from_env()
        payload = json.dumps({
            'task':            task['name'],
            'status':          task['status'],
            'priority':        task['priority'],
            'type':            task['task_type'],
            'venture':         task['venture'] or venture_id,
            'assigned_to':     task['assigned_to'],
            'source':          task['source'],
            'due_date':        task['due_date'],
            'notes':           task['notes'],
            'completed':       str(task['completed']).lower(),
            'notion_page_id':  task['page_id'],
        })

        with get_conn(ctx.org_id) as cur:
            # Check if this Notion page already has a Neon record
            cur.execute(
                """
                SELECT id FROM events
                WHERE org_id = %s
                  AND event_type = 'dex_task'
                  AND payload_json->>'notion_page_id' = %s
                """,
                (str(ctx.org_id), task['page_id']),
            )
            existing = cur.fetchone()

            if existing:
                cur.execute(
                    "UPDATE events SET payload_json = %s WHERE id = %s",
                    (payload, existing['id']),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO events (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (str(ctx.org_id), 'dex_task', payload, json.dumps([])),
                )
        return True
    except Exception as e:
        print(f'[TasksSync] Neon write failed: {e}')
        return False


def push_status_to_notion(notion_page_id: str, status: str, assigned_to: str = None) -> bool:
    """Push a status update from Neon back to the Notion page."""
    try:
        properties = {
            'Status': {'select': {'name': status}},
        }
        if assigned_to:
            properties['Assigned To'] = {'select': {'name': assigned_to}}

        resp = requests.patch(
            f'https://api.notion.com/v1/pages/{notion_page_id}',
            headers=HEADERS,
            json={'properties': properties},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f'[TasksSync] Notion status push failed: {e}')
        return False


def sync_neon_to_notion() -> int:
    """
    Push status changes from Neon back to Notion.
    Finds dex_task events flagged with needs_notion_sync and syncs them back.
    """
    try:
        from eos_ai.db import get_conn
        from eos_ai.context import load_context_from_env

        ctx = load_context_from_env()
        updated = 0

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                """
                SELECT id, payload_json
                FROM events
                WHERE org_id = %s
                  AND event_type = 'dex_task'
                  AND payload_json ? 'notion_page_id'
                  AND payload_json ? 'needs_notion_sync'
                """,
                (str(ctx.org_id),),
            )
            rows = cur.fetchall()

            for row in rows:
                try:
                    payload = row['payload_json']
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    page_id    = payload.get('notion_page_id')
                    status     = payload.get('status', 'Not Started')
                    assigned_to = payload.get('assigned_to')

                    if not page_id:
                        continue

                    success = push_status_to_notion(page_id, status, assigned_to)
                    if success:
                        payload.pop('needs_notion_sync', None)
                        cur.execute(
                            "UPDATE events SET payload_json = %s WHERE id = %s",
                            (json.dumps(payload), row['id']),
                        )
                        updated += 1
                except Exception:
                    continue

        return updated
    except Exception as e:
        print(f'[TasksSync] Neon→Notion sync failed: {e}')
        return 0


def run_sync():
    print(f'[TasksSync] Starting — {datetime.now().strftime("%H:%M")}')
    state = load_state()
    synced = state.get('synced', {})
    new_count = 0

    for venture_id, db_id in DATABASES.items():
        if not db_id:
            continue

        pages = query_database(db_id)
        for page in pages:
            task = extract_task(page)
            if not task['name']:
                continue

            page_id = task['page_id']
            last_edited = task['last_edited']

            # Skip if already synced at this version
            if synced.get(page_id) == last_edited:
                continue

            success = write_to_neon(task, venture_id)
            if success:
                synced[page_id] = last_edited
                new_count += 1
                print(f'  [TasksSync] Synced: {task["name"][:60]} ({venture_id})')

    state['synced'] = synced
    state['last_run'] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    # Also push any Neon status changes back to Notion
    neon_to_notion = sync_neon_to_notion()
    print(f'[TasksSync] Done — {new_count} synced from Notion, {neon_to_notion} pushed to Notion')


if __name__ == '__main__':
    run_sync()
