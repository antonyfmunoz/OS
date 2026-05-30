"""
Notion Setup — creates the full per-venture primitive database
architecture for UMH.

UNIVERSAL (all roles, all stages):
  Goals/OKRs, Tasks, Meetings, Documents,
  Metrics/KPIs, Decisions, Roles, Tools, Skills,
  Workflows, Pipeline/CRM

STAGE-GATED:
  Projects (Stage 2+), Budget (Stage 3+)

STRUCTURE:
  Portfolio Overview DB (portfolio level)
  Role Dashboards page per venture

Run once. Idempotent — skips existing DBs.
Writes all DB IDs to .env using new naming convention.
Never removes existing .env vars.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv, set_key
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', '.env'))

ENV_FILE = f'{_ROOT}/.env'
NOTION_VERSION = '2022-06-28'
TOKEN = os.getenv('NOTION_API_KEY', '')
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json',
}

# ── Real page IDs (discovered 2026-03-31) ─────────

PORTFOLIO_PAGE_ID = '32eda8b9-6e4f-81eb-b253-f2e50bbd298a'

VENTURES = [
    {
        'id': 'personal_brand',
        'name': 'Personal Brand',
        'page_id': '32eda8b9-6e4f-812b-888c-df30298aa856',
        'stage': 1,
        'env_prefix': 'NOTION_PERSONAL_BRAND',
    },
    {
        'id': 'lyfe_institute',
        'name': 'Lyfe Institute',
        'page_id': '32eda8b9-6e4f-817f-a314-fc66aa831cc3',
        'stage': 1,
        'env_prefix': 'NOTION_LYFE_INSTITUTE',
    },
    {
        'id': 'empyrean_creative',
        'name': 'Empyrean Creative',
        'page_id': '32eda8b9-6e4f-81c7-8872-e5a768ea9faf',
        'stage': 1,
        'env_prefix': 'NOTION_EMPYREAN_CREATIVE',
    },
]

# ── Helpers ───────────────────────────────────────

def _to_env_key(name: str) -> str:
    """'Goals / OKRs' → 'GOALS_OKRS'"""
    return (
        name.upper()
        .replace(' / ', '_')
        .replace('/', '_')
        .replace(' ', '_')
        .replace('-', '_')
    )


def _create_db(parent_page_id: str, title: str,
               properties: dict) -> str:
    resp = requests.post(
        'https://api.notion.com/v1/databases',
        headers=HEADERS,
        json={
            'parent': {'page_id': parent_page_id},
            'title': [{'type': 'text',
                        'text': {'content': title}}],
            'properties': properties,
        },
        timeout=15,
    )
    if resp.status_code == 200:
        try:
            db_id = resp.json().get('id', '')
        except Exception:
            db_id = ''
        print(f'  ✅ {title} ({db_id[:8]})')
        return db_id
    try:
        msg = resp.json().get('message', '')
    except Exception:
        msg = resp.text[:120]
    print(f'  ❌ {title}: {msg}')
    return ''


def _get_all_dbs() -> dict:
    """Returns {parent_page_id|title: db_id}"""
    resp = requests.post(
        'https://api.notion.com/v1/search',
        headers=HEADERS,
        json={
            'filter': {'value': 'database',
                        'property': 'object'},
            'page_size': 100,
        },
        timeout=15,
    )
    if resp.status_code != 200:
        try:
            msg = resp.json().get('message', 'unknown')
        except Exception:
            msg = resp.text[:120] or f'HTTP {resp.status_code}'
        print(f'❌ Notion API error ({resp.status_code}): {msg}')
        raise SystemExit(1)
    existing = {}
    try:
        results = resp.json().get('results', [])
    except Exception:
        results = []
    for db in results:
        tl = db.get('title', [])
        title = tl[0].get('plain_text', '') if tl else ''
        parent_id = db.get('parent', {}).get('page_id', '')
        if title and parent_id:
            key = f'{parent_id}|{title}'
            existing[key] = db['id']
    return existing


def _ensure_db(parent_id: str, title: str,
               schema: dict, existing: dict) -> str:
    key = f'{parent_id}|{title}'
    if key in existing:
        print(f'  ⏭️  {title} (exists)')
        return existing[key]
    return _create_db(parent_id, title, schema)


def _get_existing_page_titles(parent_id: str) -> set:
    """Return a set of title strings for all sub-pages under parent_id."""
    resp = requests.post(
        'https://api.notion.com/v1/search',
        headers=HEADERS,
        json={'page_size': 100},
        timeout=15,
    )
    titles: set = set()
    if resp.status_code != 200:
        return titles
    try:
        results = resp.json().get('results', [])
    except Exception:
        results = []
    for r in results:
        if r.get('object') != 'page':
            continue
        if r.get('parent', {}).get('page_id') != parent_id:
            continue
        props = r.get('properties', {})
        tp = props.get('title', {})
        rt = tp.get('title', []) if isinstance(tp, dict) else []
        title = rt[0].get('plain_text', '') if rt else ''
        if title:
            titles.add(title)
    return titles


def _ensure_dashboards_page(venture_page_id: str) -> str:
    """Get or create 'Role Dashboards' sub-page."""
    resp = requests.post(
        'https://api.notion.com/v1/search',
        headers=HEADERS,
        json={'query': 'Role Dashboards', 'page_size': 20},
        timeout=15,
    )
    if resp.status_code != 200:
        return ''
    try:
        results = resp.json().get('results', [])
    except Exception:
        return ''
    for r in results:
        if r.get('object') != 'page':
            continue
        parent = r.get('parent', {})
        if parent.get('page_id') != venture_page_id:
            continue
        props = r.get('properties', {})
        tp = props.get('title', {})
        rt = tp.get('title', []) if isinstance(tp, dict) else []
        title = rt[0].get('plain_text', '') if rt else ''
        if title == 'Role Dashboards':
            print('  ⏭️  Role Dashboards (exists)')
            return r['id']
    resp = requests.post(
        'https://api.notion.com/v1/pages',
        headers=HEADERS,
        json={
            'parent': {'page_id': venture_page_id},
            'properties': {'title': {'title': [
                {'text': {'content': 'Role Dashboards'}}
            ]}},
        },
        timeout=15,
    )
    if resp.status_code == 200:
        print('  ✅ Role Dashboards page')
        try:
            return resp.json().get('id', '')
        except Exception:
            return ''
    try:
        msg = resp.json().get("message", "")
    except Exception:
        msg = ""
    print(f'  ❌ Role Dashboards: {msg}')
    return ''


def _create_role_dashboard_page(
    parent_id: str, role_name: str, dept: str,
    description: str, db_instructions: list,
) -> str:
    instruction_text = '\n'.join(
        f'• {i}' for i in db_instructions
    )
    content = (
        f'Role: {role_name}\n'
        f'Department: {dept}\n'
        f'Purpose: {description}\n\n'
        f'Linked database views to add '
        f'(filter as shown):\n{instruction_text}'
    )
    resp = requests.post(
        'https://api.notion.com/v1/pages',
        headers=HEADERS,
        json={
            'parent': {'page_id': parent_id},
            'properties': {'title': {'title': [
                {'text': {'content': role_name}}
            ]}},
            'children': [{
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {'rich_text': [{
                    'type': 'text',
                    'text': {'content': content},
                }]},
            }],
        },
        timeout=15,
    )
    if resp.status_code == 200:
        print(f'  ✅ Dashboard: {role_name}')
        try:
            return resp.json().get('id', '')
        except Exception:
            return ''
    try:
        msg = resp.json().get('message', '')
    except Exception:
        msg = resp.text[:120]
    print(f'  ❌ Dashboard {role_name}: {msg}')
    return ''


# ── Shared option sets ────────────────────────────

DEPT_OPTIONS = [
    {'name': 'Leadership', 'color': 'red'},
    {'name': 'Sales', 'color': 'green'},
    {'name': 'Marketing', 'color': 'blue'},
    {'name': 'Operations', 'color': 'orange'},
    {'name': 'Finance', 'color': 'purple'},
    {'name': 'Research', 'color': 'yellow'},
    {'name': 'Product', 'color': 'pink'},
    {'name': 'Engineering', 'color': 'gray'},
    {'name': 'Customer Success', 'color': 'brown'},
    {'name': 'Legal', 'color': 'default'},
    {'name': 'All', 'color': 'default'},
]

PRIORITY_OPTIONS = [
    {'name': 'Critical', 'color': 'red'},
    {'name': 'High', 'color': 'orange'},
    {'name': 'Normal', 'color': 'blue'},
    {'name': 'Low', 'color': 'gray'},
]

STATUS_OPTIONS = [
    {'name': 'Not started', 'color': 'default'},
    {'name': 'In progress', 'color': 'blue'},
    {'name': 'In review', 'color': 'yellow'},
    {'name': 'Blocked', 'color': 'red'},
    {'name': 'Done', 'color': 'green'},
    {'name': 'Cancelled', 'color': 'gray'},
]

AGENT_OPTIONS = [
    {'name': 'DEX', 'color': 'blue'},
    {'name': 'CEO Agent', 'color': 'purple'},
    {'name': 'Sales Agent', 'color': 'green'},
    {'name': 'Outreach Agent', 'color': 'pink'},
    {'name': 'Research Agent', 'color': 'yellow'},
    {'name': 'Intelligence Agent', 'color': 'red'},
    {'name': 'Content Agent', 'color': 'orange'},
    {'name': 'Operations Agent', 'color': 'brown'},
    {'name': 'Finance Agent', 'color': 'gray'},
    {'name': 'Customer Success Agent', 'color': 'default'},
    {'name': 'Founder', 'color': 'red'},
    {'name': 'None', 'color': 'default'},
]

# ── Primitive schemas ─────────────────────────────

GOALS_SCHEMA = {
    'Name': {'title': {}},
    'Type': {'select': {'options': [
        {'name': 'Objective', 'color': 'red'},
        {'name': 'Key Result', 'color': 'blue'},
        {'name': 'North Star', 'color': 'yellow'},
        {'name': 'Quarterly Goal', 'color': 'green'},
        {'name': 'Annual Goal', 'color': 'purple'},
    ]}},
    'Status': {'select': {'options': [
        {'name': 'On track', 'color': 'green'},
        {'name': 'At risk', 'color': 'yellow'},
        {'name': 'Behind', 'color': 'red'},
        {'name': 'Complete', 'color': 'blue'},
        {'name': 'Cancelled', 'color': 'gray'},
    ]}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Target': {'rich_text': {}},
    'Current': {'rich_text': {}},
    'Due Date': {'date': {}},
    'Parent Goal': {'rich_text': {}},
    'Progress': {'number': {'format': 'percent'}},
    'Notes': {'rich_text': {}},
    'Last Modified': {'last_edited_time': {}},
}

TASKS_SCHEMA = {
    'Name': {'title': {}},
    'Status': {'select': {'options': STATUS_OPTIONS}},
    'Priority': {'select': {'options': PRIORITY_OPTIONS}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Assignee Type': {'select': {'options': [
        {'name': 'Human', 'color': 'blue'},
        {'name': 'Agent', 'color': 'purple'},
        {'name': 'Both', 'color': 'green'},
    ]}},
    'Assigned To': {'select': {'options': AGENT_OPTIONS}},
    'Source': {'select': {'options': [
        {'name': 'Founder', 'color': 'red'},
        {'name': 'DEX', 'color': 'blue'},
        {'name': 'CEO Agent', 'color': 'purple'},
        {'name': 'Sales Agent', 'color': 'green'},
        {'name': 'Research Agent', 'color': 'yellow'},
        {'name': 'Content Agent', 'color': 'orange'},
        {'name': 'Operations Agent', 'color': 'brown'},
        {'name': 'Finance Agent', 'color': 'gray'},
        {'name': 'System', 'color': 'default'},
    ]}},
    'Type': {'select': {'options': [
        {'name': 'Task', 'color': 'blue'},
        {'name': 'Agent Task', 'color': 'purple'},
        {'name': 'Follow-up', 'color': 'green'},
        {'name': 'Review', 'color': 'yellow'},
        {'name': 'Decision', 'color': 'red'},
        {'name': 'Delegation', 'color': 'orange'},
    ]}},
    'Due Date': {'date': {}},
    'Linked Goal': {'rich_text': {}},
    'Linked Workflow': {'rich_text': {}},
    'Result': {'rich_text': {}},
    'Requires Approval': {'checkbox': {}},
    'Neon ID': {'rich_text': {}},
    'Notes': {'rich_text': {}},
    'Last Modified': {'last_edited_time': {}},
}

MEETINGS_SCHEMA = {
    'Name': {'title': {}},
    'Type': {'select': {'options': [
        {'name': 'Sales Call', 'color': 'green'},
        {'name': 'Strategy', 'color': 'red'},
        {'name': 'Operations', 'color': 'orange'},
        {'name': 'Finance', 'color': 'purple'},
        {'name': 'Marketing', 'color': 'blue'},
        {'name': '1:1', 'color': 'yellow'},
        {'name': 'Team Standup', 'color': 'gray'},
        {'name': 'Client Call', 'color': 'green'},
        {'name': 'Board Meeting', 'color': 'red'},
        {'name': 'Investor Meeting', 'color': 'purple'},
        {'name': 'CS Call', 'color': 'pink'},
        {'name': 'Research', 'color': 'yellow'},
        {'name': 'External', 'color': 'default'},
        {'name': 'Other', 'color': 'default'},
    ]}},
    'Status': {'select': {'options': [
        {'name': 'Scheduled', 'color': 'blue'},
        {'name': 'In Progress', 'color': 'yellow'},
        {'name': 'Completed', 'color': 'green'},
        {'name': 'No Show', 'color': 'red'},
        {'name': 'Cancelled', 'color': 'gray'},
        {'name': 'Rescheduled', 'color': 'orange'},
    ]}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Person': {'rich_text': {}},
    'Email': {'email': {}},
    'Date': {'date': {}},
    'Duration (min)': {'number': {'format': 'number'}},
    'Outcomes': {'rich_text': {}},
    'Open Loops': {'rich_text': {}},
    'Prep Notes': {'rich_text': {}},
    'Meet Link': {'url': {}},
    'Follow Up Sent': {'checkbox': {}},
    'Minutes Link': {'url': {}},
    'Last Modified': {'last_edited_time': {}},
}

DOCUMENTS_SCHEMA = {
    'Title': {'title': {}},
    'Type': {'select': {'options': [
        {'name': 'SOP', 'color': 'blue'},
        {'name': 'Strategy', 'color': 'red'},
        {'name': 'Playbook', 'color': 'orange'},
        {'name': 'Research Brief', 'color': 'yellow'},
        {'name': 'Proposal', 'color': 'green'},
        {'name': 'Contract', 'color': 'purple'},
        {'name': 'Financial Report', 'color': 'gray'},
        {'name': 'Brand Guidelines', 'color': 'pink'},
        {'name': 'Meeting Minutes', 'color': 'default'},
        {'name': 'Knowledge Entry', 'color': 'blue'},
        {'name': 'General', 'color': 'default'},
    ]}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Status': {'select': {'options': [
        {'name': 'Draft', 'color': 'gray'},
        {'name': 'Active', 'color': 'green'},
        {'name': 'Archived', 'color': 'default'},
    ]}},
    'Category': {'select': {'options': [
        {'name': 'ICP', 'color': 'blue'},
        {'name': 'Brand Voice', 'color': 'pink'},
        {'name': 'Market Signal', 'color': 'yellow'},
        {'name': 'Process', 'color': 'orange'},
        {'name': 'Competitive', 'color': 'red'},
        {'name': 'Learning', 'color': 'green'},
        {'name': 'Financial', 'color': 'purple'},
        {'name': 'Legal', 'color': 'gray'},
        {'name': 'General', 'color': 'default'},
    ]}},
    'Source': {'select': {'options': AGENT_OPTIONS}},
    'Confidence': {'select': {'options': [
        {'name': 'High', 'color': 'green'},
        {'name': 'Medium', 'color': 'yellow'},
        {'name': 'Low', 'color': 'red'},
    ]}},
    'Linked Entity': {'rich_text': {}},
    'Content': {'rich_text': {}},
    'File Path': {'rich_text': {}},
    'Last Modified': {'last_edited_time': {}},
}

METRICS_SCHEMA = {
    'Metric': {'title': {}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Category': {'select': {'options': [
        {'name': 'Revenue', 'color': 'green'},
        {'name': 'Growth', 'color': 'blue'},
        {'name': 'Efficiency', 'color': 'orange'},
        {'name': 'Quality', 'color': 'yellow'},
        {'name': 'Customer', 'color': 'pink'},
        {'name': 'Team', 'color': 'purple'},
        {'name': 'Product', 'color': 'gray'},
        {'name': 'Marketing', 'color': 'blue'},
        {'name': 'Sales', 'color': 'green'},
        {'name': 'Finance', 'color': 'purple'},
    ]}},
    'Value': {'number': {'format': 'number'}},
    'Target': {'number': {'format': 'number'}},
    'Unit': {'rich_text': {}},
    'Period': {'select': {'options': [
        {'name': 'Daily', 'color': 'blue'},
        {'name': 'Weekly', 'color': 'green'},
        {'name': 'Monthly', 'color': 'orange'},
        {'name': 'Quarterly', 'color': 'purple'},
        {'name': 'Annual', 'color': 'red'},
    ]}},
    'Trend': {'select': {'options': [
        {'name': '↑ Up', 'color': 'green'},
        {'name': '→ Flat', 'color': 'yellow'},
        {'name': '↓ Down', 'color': 'red'},
    ]}},
    'Progress': {'number': {'format': 'percent'}},
    'Linked Goal': {'rich_text': {}},
    'Last Updated': {'date': {}},
    'Notes': {'rich_text': {}},
}

DECISIONS_SCHEMA = {
    'Decision': {'title': {}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Impact': {'select': {'options': [
        {'name': 'Critical', 'color': 'red'},
        {'name': 'High', 'color': 'orange'},
        {'name': 'Medium', 'color': 'yellow'},
        {'name': 'Low', 'color': 'gray'},
    ]}},
    'Made By': {'select': {'options': AGENT_OPTIONS}},
    'Status': {'select': {'options': [
        {'name': 'Active', 'color': 'green'},
        {'name': 'Superseded', 'color': 'yellow'},
        {'name': 'Reversed', 'color': 'red'},
        {'name': 'Pending', 'color': 'gray'},
    ]}},
    'Rationale': {'rich_text': {}},
    'Alternatives Considered': {'rich_text': {}},
    'Outcome': {'rich_text': {}},
    'Date': {'date': {}},
    'Linked Goal': {'rich_text': {}},
    'Last Modified': {'last_edited_time': {}},
}

ROLES_SCHEMA = {
    'Name': {'title': {}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Mode': {'select': {'options': [
        {'name': 'Human Only', 'color': 'blue'},
        {'name': 'AI Only', 'color': 'purple'},
        {'name': 'Human + AI', 'color': 'green'},
    ]}},
    'Authority Level': {'select': {'options': [
        {'name': 'Strategic', 'color': 'red'},
        {'name': 'Operational', 'color': 'orange'},
        {'name': 'Execution', 'color': 'blue'},
        {'name': 'Support', 'color': 'gray'},
    ]}},
    'Status': {'select': {'options': [
        {'name': 'Active', 'color': 'green'},
        {'name': 'Vacant', 'color': 'yellow'},
        {'name': 'AI-Staffed', 'color': 'purple'},
        {'name': 'Planned', 'color': 'gray'},
    ]}},
    'Human Assigned': {'rich_text': {}},
    'Agent Assigned': {'select': {'options': AGENT_OPTIONS}},
    'Agent Status': {'select': {'options': [
        {'name': '⚪ Idle', 'color': 'gray'},
        {'name': '🔵 Working', 'color': 'blue'},
        {'name': '🔴 Blocked', 'color': 'red'},
        {'name': '🟢 Complete', 'color': 'green'},
        {'name': '⚫ Offline', 'color': 'default'},
    ]}},
    'Current Task': {'rich_text': {}},
    'Primary KPI': {'rich_text': {}},
    'KPI Value': {'rich_text': {}},
    'Performance Score': {'number': {'format': 'percent'}},
    'Reports To': {'rich_text': {}},
    'Responsibilities': {'rich_text': {}},
    'Soul Doc Path': {'rich_text': {}},
    'Last Active': {'date': {}},
    'Last Modified': {'last_edited_time': {}},
}

TOOLS_SCHEMA = {
    'Name': {'title': {}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Primary Role': {'rich_text': {}},
    'Agent': {'select': {'options': AGENT_OPTIONS}},
    'Category': {'select': {'options': [
        {'name': 'Native EOS', 'color': 'blue'},
        {'name': 'External SaaS', 'color': 'green'},
        {'name': 'API Integration', 'color': 'orange'},
        {'name': 'Desktop App', 'color': 'purple'},
        {'name': 'Mobile App', 'color': 'pink'},
        {'name': 'Browser Agent', 'color': 'yellow'},
        {'name': 'Script', 'color': 'gray'},
    ]}},
    'Integration Level': {'select': {'options': [
        {'name': 'Direct API', 'color': 'green'},
        {'name': 'Browser Agent', 'color': 'blue'},
        {'name': 'Desktop Control', 'color': 'orange'},
        {'name': 'Mobile Control', 'color': 'purple'},
        {'name': 'Manual Only', 'color': 'gray'},
    ]}},
    'Status': {'select': {'options': [
        {'name': 'Active', 'color': 'green'},
        {'name': 'Planned', 'color': 'yellow'},
        {'name': 'Broken', 'color': 'red'},
        {'name': 'Deprecated', 'color': 'gray'},
    ]}},
    'AI Operable': {'checkbox': {}},
    'Description': {'rich_text': {}},
    'Access Method': {'rich_text': {}},
    'Cost Per Month': {'number': {'format': 'dollar'}},
    'Documentation': {'url': {}},
    'Last Modified': {'last_edited_time': {}},
}

SKILLS_SCHEMA = {
    'Name': {'title': {}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Agent': {'select': {'options': AGENT_OPTIONS}},
    'Trust Level': {'select': {'options': [
        {'name': 'Observe', 'color': 'gray'},
        {'name': 'Assist', 'color': 'blue'},
        {'name': 'Execute', 'color': 'green'},
        {'name': 'Autonomous', 'color': 'purple'},
    ]}},
    'Status': {'select': {'options': [
        {'name': 'Active', 'color': 'green'},
        {'name': 'Draft', 'color': 'gray'},
        {'name': 'Deprecated', 'color': 'red'},
    ]}},
    'Purpose': {'rich_text': {}},
    'Inputs': {'rich_text': {}},
    'Outputs': {'rich_text': {}},
    'File Path': {'rich_text': {}},
    'Version': {'number': {'format': 'number'}},
    'Success Rate': {'number': {'format': 'percent'}},
    'Last Modified': {'last_edited_time': {}},
}

WORKFLOWS_SCHEMA = {
    'Name': {'title': {}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Status': {'select': {'options': [
        {'name': 'Draft', 'color': 'gray'},
        {'name': 'Active', 'color': 'green'},
        {'name': 'Paused', 'color': 'yellow'},
        {'name': 'Completed', 'color': 'blue'},
        {'name': 'Deprecated', 'color': 'default'},
    ]}},
    'Owner': {'select': {'options': AGENT_OPTIONS}},
    'Type': {'select': {'options': [
        {'name': 'SOP', 'color': 'blue'},
        {'name': 'Campaign', 'color': 'orange'},
        {'name': 'Onboarding', 'color': 'green'},
        {'name': 'Review', 'color': 'yellow'},
        {'name': 'Research', 'color': 'purple'},
        {'name': 'Outreach', 'color': 'pink'},
        {'name': 'Delivery', 'color': 'brown'},
        {'name': 'Admin', 'color': 'gray'},
    ]}},
    'Trigger': {'rich_text': {}},
    'Description': {'rich_text': {}},
    'Linked Goal': {'rich_text': {}},
    'Step Count': {'number': {'format': 'number'}},
    'Version': {'number': {'format': 'number'}},
    'Last Run': {'date': {}},
    'Success Rate': {'number': {'format': 'percent'}},
    'Last Modified': {'last_edited_time': {}},
}

PIPELINE_SCHEMA = {
    'Name': {'title': {}},
    'Stage': {'select': {'options': [
        {'name': 'Lead', 'color': 'gray'},
        {'name': 'Contacted', 'color': 'blue'},
        {'name': 'Qualified', 'color': 'yellow'},
        {'name': 'Proposal', 'color': 'orange'},
        {'name': 'Negotiation', 'color': 'purple'},
        {'name': 'Closed Won', 'color': 'green'},
        {'name': 'Active Customer', 'color': 'green'},
        {'name': 'At Risk', 'color': 'red'},
        {'name': 'Churned', 'color': 'default'},
        {'name': 'Closed Lost', 'color': 'red'},
        {'name': 'Nurture', 'color': 'pink'},
    ]}},
    'Type': {'select': {'options': [
        {'name': 'Lead', 'color': 'blue'},
        {'name': 'Customer', 'color': 'green'},
        {'name': 'Partner', 'color': 'orange'},
        {'name': 'Investor', 'color': 'purple'},
        {'name': 'Vendor', 'color': 'gray'},
        {'name': 'Advisor', 'color': 'yellow'},
        {'name': 'Referral Source', 'color': 'pink'},
    ]}},
    'Channel': {'select': {'options': [
        {'name': 'Instagram DM', 'color': 'pink'},
        {'name': 'Email', 'color': 'blue'},
        {'name': 'Referral', 'color': 'green'},
        {'name': 'Inbound', 'color': 'yellow'},
        {'name': 'Outbound', 'color': 'orange'},
        {'name': 'LinkedIn', 'color': 'blue'},
        {'name': 'Cold Call', 'color': 'gray'},
        {'name': 'Event', 'color': 'purple'},
        {'name': 'Content', 'color': 'pink'},
    ]}},
    'Score': {'number': {'format': 'number'}},
    'AI Qualified': {'checkbox': {}},
    'Assigned To': {'select': {'options': AGENT_OPTIONS}},
    'Email': {'email': {}},
    'Phone': {'phone_number': {}},
    'Company': {'rich_text': {}},
    'Value': {'number': {'format': 'dollar'}},
    'Last Contact': {'date': {}},
    'Next Action': {'rich_text': {}},
    'Next Action Date': {'date': {}},
    'Notes': {'rich_text': {}},
    'Source': {'rich_text': {}},
    'Last Modified': {'last_edited_time': {}},
}

PROJECTS_SCHEMA = {
    'Name': {'title': {}},
    'Status': {'select': {'options': STATUS_OPTIONS}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Priority': {'select': {'options': PRIORITY_OPTIONS}},
    'Owner': {'select': {'options': AGENT_OPTIONS}},
    'Linked Goal': {'rich_text': {}},
    'Start Date': {'date': {}},
    'Due Date': {'date': {}},
    'Budget Allocated': {'number': {'format': 'dollar'}},
    'Budget Spent': {'number': {'format': 'dollar'}},
    'Progress': {'number': {'format': 'percent'}},
    'Description': {'rich_text': {}},
    'Outcome Metric': {'rich_text': {}},
    'Last Modified': {'last_edited_time': {}},
}

BUDGET_SCHEMA = {
    'Name': {'title': {}},
    'Department': {'select': {'options': DEPT_OPTIONS}},
    'Type': {'select': {'options': [
        {'name': 'Allocated', 'color': 'blue'},
        {'name': 'Spent', 'color': 'red'},
        {'name': 'Committed', 'color': 'orange'},
        {'name': 'Available', 'color': 'green'},
    ]}},
    'Amount': {'number': {'format': 'dollar'}},
    'Period': {'select': {'options': [
        {'name': 'Monthly', 'color': 'blue'},
        {'name': 'Quarterly', 'color': 'purple'},
        {'name': 'Annual', 'color': 'red'},
    ]}},
    'Category': {'rich_text': {}},
    'Notes': {'rich_text': {}},
    'Date': {'date': {}},
    'Last Modified': {'last_edited_time': {}},
}

PORTFOLIO_SCHEMA = {
    'Company': {'title': {}},
    'Stage': {'select': {'options': [
        {'name': 'Pre-revenue', 'color': 'gray'},
        {'name': 'First Revenue', 'color': 'yellow'},
        {'name': 'Growing', 'color': 'blue'},
        {'name': 'Scaling', 'color': 'green'},
        {'name': 'Mature', 'color': 'purple'},
    ]}},
    'Business Model': {'select': {'options': [
        {'name': 'B2C Coaching', 'color': 'green'},
        {'name': 'B2B SaaS', 'color': 'blue'},
        {'name': 'B2C SaaS', 'color': 'blue'},
        {'name': 'Agency', 'color': 'orange'},
        {'name': 'E-commerce', 'color': 'pink'},
        {'name': 'Marketplace', 'color': 'purple'},
        {'name': 'Content', 'color': 'yellow'},
        {'name': 'Real Estate', 'color': 'brown'},
        {'name': 'Holding Company', 'color': 'red'},
    ]}},
    'Health Score': {'number': {'format': 'percent'}},
    'Binding Constraint': {'rich_text': {}},
    'North Star': {'rich_text': {}},
    'Revenue MRR': {'number': {'format': 'dollar'}},
    'Proof to Advance': {'rich_text': {}},
    'Active Agents': {'number': {'format': 'number'}},
    'Current Focus': {'rich_text': {}},
    'Tasks In Progress': {'number': {'format': 'number'}},
    'Status': {'select': {'options': [
        {'name': 'Active', 'color': 'green'},
        {'name': 'Paused', 'color': 'yellow'},
        {'name': 'Archived', 'color': 'gray'},
    ]}},
    'Last Agent Activity': {'date': {}},
    'Last Updated': {'date': {}},
}

# ── Universal DB list ─────────────────────────────

UNIVERSAL_DBS = [
    ('Goals / OKRs', GOALS_SCHEMA),
    ('Tasks', TASKS_SCHEMA),
    ('Meetings', MEETINGS_SCHEMA),
    ('Documents', DOCUMENTS_SCHEMA),
    ('Metrics / KPIs', METRICS_SCHEMA),
    ('Decisions', DECISIONS_SCHEMA),
    ('Roles', ROLES_SCHEMA),
    ('Tools', TOOLS_SCHEMA),
    ('Skills', SKILLS_SCHEMA),
    ('Workflows', WORKFLOWS_SCHEMA),
    ('Pipeline / CRM', PIPELINE_SCHEMA),
]

# ── Role dashboard definitions ────────────────────

ROLE_DASHBOARDS = [
    {
        'name': '👤 Founder',
        'dept': 'Leadership',
        'description': (
            'Full portfolio view. All departments unfiltered. '
            'Org chart entry point.'
        ),
        'filters': [
            'Goals/OKRs — all, no filter',
            'Tasks — all, no filter',
            'Meetings — all, no filter',
            'Metrics/KPIs — all, no filter',
            'Decisions — all, no filter',
            'Pipeline/CRM — all, no filter',
            'Workflows — all, no filter',
            'Roles — Gallery view (= org chart)',
            'Documents — all, no filter',
        ],
    },
    {
        'name': '🤖 DEX (Executive Assistant)',
        'dept': 'Leadership',
        'description': (
            'Cross-venture operational view. '
            'Calendar, email, all tasks, all agent activity, all meetings.'
        ),
        'filters': [
            'Tasks — all ventures, all departments',
            'Meetings — all, no filter',
            'Goals/OKRs — all, no filter',
            'Workflows — all, no filter',
            'Pipeline/CRM — awareness only',
            'Metrics/KPIs — all, no filter',
            'Decisions — all, no filter',
            'Documents — all, no filter',
        ],
    },
    {
        'name': '🏢 CEO Agent',
        'dept': 'Leadership',
        'description': (
            'Strategic delegation and org health view. '
            'Sees all departments to delegate correctly.'
        ),
        'filters': [
            'Tasks — Assigned To = CEO Agent',
            'Goals/OKRs — all, no filter',
            'Decisions — all, no filter',
            'Roles — all, no filter',
            'Metrics/KPIs — all, no filter',
            'Pipeline/CRM — awareness only',
        ],
    },
    {
        'name': '💚 Sales Agent',
        'dept': 'Sales',
        'description': 'Pipeline and lead management view.',
        'filters': [
            'Pipeline/CRM — all',
            'Tasks — Dept = Sales',
            'Meetings — Type = Sales Call',
            'Goals/OKRs — Dept = Sales',
            'Metrics/KPIs — Category = Sales',
            'Workflows — Dept = Sales',
        ],
    },
    {
        'name': '📣 Outreach Agent',
        'dept': 'Sales',
        'description': 'Outbound and DM pipeline view.',
        'filters': [
            'Pipeline/CRM — Stage = Lead, Contacted',
            'Tasks — Assigned To = Outreach Agent',
            'Workflows — Dept = Sales, Type = Outreach',
            'Metrics/KPIs — Category = Sales',
        ],
    },
    {
        'name': '🔬 Research / Intelligence Agent',
        'dept': 'Research',
        'description': 'ICP, market, and competitive intelligence.',
        'filters': [
            'Documents — Category = ICP, Market Signal, Competitive',
            'Tasks — Assigned To = Research Agent',
            'Workflows — Dept = Research',
            'Goals/OKRs — Dept = Research',
        ],
    },
    {
        'name': '📸 Content Agent',
        'dept': 'Marketing',
        'description': 'Content calendar, campaigns, and publishing.',
        'filters': [
            'Tasks — Dept = Marketing',
            'Workflows — Dept = Marketing',
            'Goals/OKRs — Dept = Marketing',
            'Metrics/KPIs — Category = Marketing',
            'Documents — Category = Brand Voice',
        ],
    },
    {
        'name': '⚙️ Operations Agent',
        'dept': 'Operations',
        'description': 'Process execution and SOP management.',
        'filters': [
            'Tasks — Dept = Operations',
            'Workflows — all',
            'Roles — all',
            'Tools — all',
            'Skills — all',
            'Decisions — all',
        ],
    },
    {
        'name': '💰 Finance Agent',
        'dept': 'Finance',
        'description': 'Budget, metrics, and financial health.',
        'filters': [
            'Budget — all (Stage 3+)',
            'Metrics/KPIs — Category = Revenue, Finance',
            'Tasks — Dept = Finance',
            'Goals/OKRs — Dept = Finance',
            'Documents — Type = Financial Report',
        ],
    },
    {
        'name': '🤝 Customer Success Agent',
        'dept': 'Customer Success',
        'description': 'Active customers and retention.',
        'filters': [
            'Pipeline/CRM — Stage = Active Customer, At Risk',
            'Tasks — Dept = Customer Success',
            'Meetings — Type = CS Call',
            'Metrics/KPIs — Category = Customer',
            'Workflows — Dept = Customer Success',
        ],
    },
]

# ── main ──────────────────────────────────────────

def main() -> None:
    print('EOS Notion Setup')
    print('=================')

    existing_dbs = _get_all_dbs()
    collected: dict[str, dict[str, str]] = {}

    for venture in VENTURES:
        print(f'\n── {venture["name"]} ──')
        venture_dbs: dict[str, str] = {}

        # Universal primitives
        for title, schema in UNIVERSAL_DBS:
            db_id = _ensure_db(
                venture['page_id'], title, schema, existing_dbs
            )
            if db_id:
                venture_dbs[title] = db_id

        # Stage-gated: Projects (Stage 2+)
        if venture['stage'] >= 2:
            db_id = _ensure_db(
                venture['page_id'], 'Projects',
                PROJECTS_SCHEMA, existing_dbs,
            )
            if db_id:
                venture_dbs['Projects'] = db_id

        # Stage-gated: Budget (Stage 3+)
        if venture['stage'] >= 3:
            db_id = _ensure_db(
                venture['page_id'], 'Budget',
                BUDGET_SCHEMA, existing_dbs,
            )
            if db_id:
                venture_dbs['Budget'] = db_id

        # Role Dashboards page
        dashboards_page = _ensure_dashboards_page(
            venture['page_id']
        )
        if dashboards_page:
            # Fetch existing dashboard sub-pages to skip duplicates
            existing_dash = _get_existing_page_titles(dashboards_page)
            for role in ROLE_DASHBOARDS:
                if role['name'] in existing_dash:
                    print(f'  ⏭️  Dashboard: {role["name"]} (exists)')
                    continue
                _create_role_dashboard_page(
                    dashboards_page,
                    role['name'],
                    role['dept'],
                    role['description'],
                    role['filters'],
                )

        collected[venture['id']] = venture_dbs

    # Portfolio Overview DB
    print('\n── Portfolio ──')
    portfolio_db_id = _ensure_db(
        PORTFOLIO_PAGE_ID, 'Portfolio Overview',
        PORTFOLIO_SCHEMA, existing_dbs,
    )

    # Write IDs to .env
    print('\n── Writing to .env ──')
    for venture in VENTURES:
        prefix = venture['env_prefix']
        vdbs = collected.get(venture['id'], {})
        for db_name, db_id in vdbs.items():
            if not db_id:
                continue
            suffix = _to_env_key(db_name)
            key = f'{prefix}_{suffix}_DB'
            set_key(ENV_FILE, key, db_id)
            print(f'  {key}={db_id[:8]}...')

    if portfolio_db_id:
        set_key(ENV_FILE, 'NOTION_PORTFOLIO_OVERVIEW_DB',
                portfolio_db_id)
        print(f'  NOTION_PORTFOLIO_OVERVIEW_DB='
              f'{portfolio_db_id[:8]}...')

    # Update VENTURES_JSON
    print('\n── Updating VENTURES_JSON ──')
    ventures_raw = os.getenv('VENTURES_JSON', '[]').strip("'\"")
    try:
        ventures_list = json.loads(ventures_raw)
    except json.JSONDecodeError:
        ventures_list = []

    for venture in VENTURES:
        vdbs = collected.get(venture['id'], {})
        notion_fields: dict[str, str] = {}
        for db_name, db_id in vdbs.items():
            if not db_id:
                continue
            field = (
                'notion_'
                + _to_env_key(db_name).lower()
                + '_db'
            )
            notion_fields[field] = db_id

        matched = False
        for v in ventures_list:
            if v.get('id') == venture['id']:
                v.update(notion_fields)
                matched = True
                break
        if not matched:
            ventures_list.append({
                'id': venture['id'],
                'name': venture['name'],
                **notion_fields,
            })

    ventures_json_str = json.dumps(ventures_list)
    set_key(ENV_FILE, 'VENTURES_JSON',
            f"'{ventures_json_str}'")
    print('  VENTURES_JSON updated')
    print('\n✅ Setup complete')


if __name__ == '__main__':
    main()
