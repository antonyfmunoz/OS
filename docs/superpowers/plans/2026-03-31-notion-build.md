# Notion Database Architecture Build

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the full per-venture primitive database architecture in Notion for EntrepreneurOS — 11 universal + 2 stage-gated databases per venture, role dashboard pages, a Portfolio Overview DB, plus a runtime sync layer in eos_ai.

**Architecture:** Three new files. `scripts/notion_setup.py` creates all Notion databases idempotently and writes every DB ID to `.env`. `eos_ai/notion_sync.py` is the EOS runtime write layer used by agents. `scripts/notion_seed.py` populates initial rows (portfolio entries, roles, tools, goals) after setup. Existing emoji-prefixed partial DBs from prior builds are left in place — new clean-named DBs are created alongside them. Existing `.env` vars are preserved; new vars are added.

**Tech Stack:** Python 3.12, `requests`, `python-dotenv`

---

## Discovered Page IDs (source of truth — confirmed 2026-03-31)

| Entity | Full ID |
|--------|---------|
| EOS root | `32eda8b9-6e4f-8071-b299-fef02dcb1b8c` |
| Companies page | `32eda8b9-6e4f-81ca-b4e0-cc2c3aeeddb8` |
| Personal Brand | `32eda8b9-6e4f-812b-888c-df30298aa856` |
| Lyfe Institute | `32eda8b9-6e4f-817f-a314-fc66aa831cc3` |
| Empyrean Creative | `32eda8b9-6e4f-81c7-8872-e5a768ea9faf` |
| Portfolio — Munoz Holdings | `32eda8b9-6e4f-81eb-b253-f2e50bbd298a` |
| Morning Brief | `32eda8b9-6e4f-818c-a136-c78a1ce79c17` |
| Meetings DB (EOS root, keep) | `333da8b9-6e4f-81bc-ac06-ee87e7d13fa7` |
| Content Calendar (Personal Brand, keep) | `513a621a-5b99-4eca-9287-f0742edea66a` |

## New .env naming convention

`NOTION_{VENTURE}_{DB}_DB` where VENTURE ∈ {PERSONAL_BRAND, LYFE_INSTITUTE, EMPYREAN_CREATIVE}
and DB ∈ {TASKS, GOALS_OKRS, MEETINGS, DOCUMENTS, METRICS_KPIS, DECISIONS, ROLES, TOOLS, SKILLS, WORKFLOWS, PIPELINE_CRM, PROJECTS, BUDGET}

Example: `NOTION_LYFE_INSTITUTE_TASKS_DB`, `NOTION_PERSONAL_BRAND_PIPELINE_CRM_DB`

Portfolio: `NOTION_PORTFOLIO_OVERVIEW_DB`

## Existing .env vars that must NOT be removed

The following are used by currently-running scripts — do not touch them:
- `NOTION_YOUR_LIST_LYFE`, `NOTION_YOUR_LIST_EMPYREAN`, `NOTION_YOUR_LIST_BRAND` → used by `notion_tasks_sync.py`
- `NOTION_LYFE_PIPELINE_ID`, `NOTION_EMPYREAN_PIPELINE_ID` → used by `notion_outcome_sync.py`
- All `NOTION_*_ID` page vars → used by orchestrator scripts

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `scripts/notion_setup.py` | **Create** | One-time idempotent setup — creates all DBs, writes IDs to `.env` |
| `eos_ai/notion_sync.py` | **Create** | Runtime write layer — used by EOS agents to push data to Notion |
| `scripts/notion_seed.py` | **Create** | Seeds initial rows after setup runs |

---

## Task 1: Create scripts/notion_setup.py

**Files:**
- Create: `scripts/notion_setup.py`

- [ ] **Step 1: Write scripts/notion_setup.py**

```python
"""
Notion Setup — creates the full per-venture primitive database
architecture for EntrepreneurOS.

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

sys.path.insert(0, '/opt/OS')
load_dotenv('/opt/OS/eos_ai/.env')

ENV_FILE = '/opt/OS/eos_ai/.env'
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
        db_id = resp.json().get('id', '')
        print(f'  ✅ {title} ({db_id[:8]})')
        return db_id
    print(f'  ❌ {title}: '
          f'{resp.json().get("message", "")}')
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
    existing = {}
    for db in resp.json().get('results', []):
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


def _ensure_dashboards_page(venture_page_id: str) -> str:
    """Get or create 'Role Dashboards' sub-page."""
    resp = requests.post(
        'https://api.notion.com/v1/search',
        headers=HEADERS,
        json={'query': 'Role Dashboards', 'page_size': 20},
        timeout=15,
    )
    for r in resp.json().get('results', []):
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
        return resp.json().get('id', '')
    print(f'  ❌ Role Dashboards: '
          f'{resp.json().get("message", "")}')
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
        return resp.json().get('id', '')
    print(f'  ❌ Dashboard {role_name}: '
          f'{resp.json().get("message", "")}')
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
    'Status': {'status': {'options': STATUS_OPTIONS}},
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
            for role in ROLE_DASHBOARDS:
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
    ventures_raw = os.getenv('VENTURES_JSON', '[]')
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

    set_key(ENV_FILE, 'VENTURES_JSON',
            json.dumps(ventures_list))
    print('  VENTURES_JSON updated')
    print('\n✅ Setup complete')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Verify the file exists and imports are clean**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import scripts.notion_setup as s
print('schemas:', len(s.UNIVERSAL_DBS))
print('roles:', len(s.ROLE_DASHBOARDS))
print('ventures:', len(s.VENTURES))
print('import ok')
"
```

Expected output:
```
schemas: 11
roles: 10
ventures: 3
import ok
```

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add scripts/notion_setup.py
git commit -m "feat: add notion_setup.py — full primitive database architecture"
```

---

## Task 2: Run setup script and verify Notion

**Files:**
- Run: `scripts/notion_setup.py`

- [ ] **Step 1: Run the setup script**

```bash
cd /opt/OS && python3 scripts/notion_setup.py
```

Expected output (abbreviated):
```
EOS Notion Setup
=================

── Personal Brand ──
  ✅ Goals / OKRs (xxxxxxxx)
  ✅ Tasks (xxxxxxxx)
  ✅ Meetings (xxxxxxxx)
  ... (11 universal DBs)
  ✅ Role Dashboards page
  ✅ Dashboard: 👤 Founder
  ... (10 dashboards)

── Lyfe Institute ──
  ... (same pattern)

── Empyrean Creative ──
  ... (same pattern)

── Portfolio ──
  ✅ Portfolio Overview (xxxxxxxx)

── Writing to .env ──
  NOTION_PERSONAL_BRAND_GOALS_OKRS_DB=xxxxxxxx...
  ...

── Updating VENTURES_JSON ──
  VENTURES_JSON updated

✅ Setup complete
```

If any DB shows `❌`, re-run — Notion API occasionally rate-limits on bulk creation. Script is idempotent so re-runs skip existing DBs.

- [ ] **Step 2: Verify .env has new keys**

```bash
grep "^NOTION_PERSONAL_BRAND_TASKS_DB\|^NOTION_LYFE_INSTITUTE_TASKS_DB\|^NOTION_EMPYREAN_CREATIVE_TASKS_DB\|^NOTION_PORTFOLIO_OVERVIEW_DB" /opt/OS/eos_ai/.env
```

Expected: 4 lines with UUIDs.

- [ ] **Step 3: Verify old vars untouched**

```bash
grep "^NOTION_YOUR_LIST_LYFE\|^NOTION_LYFE_PIPELINE_ID\|^NOTION_MEETINGS_ID" /opt/OS/eos_ai/.env
```

Expected: 3 lines — original values unchanged.

- [ ] **Step 4: Count new DB keys**

```bash
grep -c "^NOTION_.*_DB=" /opt/OS/eos_ai/.env
```

Expected: at least 34 (11 DBs × 3 ventures + 1 portfolio).

---

## Task 3: Create eos_ai/notion_sync.py

**Files:**
- Create: `eos_ai/notion_sync.py`

- [ ] **Step 1: Write eos_ai/notion_sync.py**

```python
"""
Notion Sync — EOS runtime write layer.
Pushes EOS primitives to Notion databases.
Called by cognitive_loop, orchestrator, and agent_runtime.

All write functions return Notion page ID (str) or '' on failure.
Failures are logged but never raise — EOS continues without Notion.
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/opt/OS/eos_ai/.env')

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
        'Status': {'status': {'name': status}},
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
    return _update_page(
        page_id, {'Status': {'status': {'name': status}}}
    )


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
    if value:
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
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.notion_sync import (
    get_db_id, write_task, write_pipeline_entry,
    write_metric, write_meeting, write_decision,
    write_document,
)
print('get_db_id check:',
    get_db_id('lyfe_institute', 'tasks')[:8] or 'MISSING — run setup first')
print('import ok')
"
```

Expected:
```
get_db_id check: <8-char DB ID> or MISSING — run setup first
import ok
```

If `MISSING`: Task 2 (setup script) hasn't run yet. Run it first, then re-check.

- [ ] **Step 3: Smoke test a write (run after setup script has populated .env)**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.notion_sync import write_task
page_id = write_task(
    'lyfe_institute',
    'Smoke test — delete me',
    status='Not started',
    priority='Low',
    source='System',
    notes='Created by notion_sync smoke test',
)
print('page_id:', page_id or 'FAILED')
"
```

Expected: a UUID printed. Open Lyfe Institute → Tasks in Notion to confirm row appears.

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add eos_ai/notion_sync.py
git commit -m "feat: add notion_sync.py — EOS runtime write layer for Notion"
```

---

## Task 4: Create scripts/notion_seed.py

**Files:**
- Create: `scripts/notion_seed.py`

- [ ] **Step 1: Write scripts/notion_seed.py**

```python
"""
Notion Seed — populates initial rows in EOS Notion databases.
Run once after notion_setup.py has created all DBs.
Idempotent in effect (creates rows, does not check for duplicates —
safe to re-run on empty DBs, do not re-run on populated ones).
"""

import os
import sys
import requests
from datetime import datetime

sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')

from eos_ai.notion_sync import (
    get_db_id, write_decision,
    HEADERS, _title, _select, _text, _number,
    _date, _checkbox, _create_page,
)

TODAY = datetime.now().strftime('%Y-%m-%d')

VENTURES = [
    ('personal_brand', 'Personal Brand'),
    ('lyfe_institute', 'Lyfe Institute'),
    ('empyrean_creative', 'Empyrean Creative'),
]


# ── Portfolio Overview ────────────────────────────

def seed_portfolio() -> None:
    db_id = os.getenv('NOTION_PORTFOLIO_OVERVIEW_DB', '')
    if not db_id:
        print('  ⚠️  NOTION_PORTFOLIO_OVERVIEW_DB not set')
        return
    rows = [
        {
            'name': 'Lyfe Institute',
            'stage': 'Pre-revenue',
            'model': 'B2C Coaching',
            'north_star': '$10K/month net from Initiate Arena',
            'binding': 'Sales — no paying customers yet',
            'proof': '1 customer → $1K MRR → $5K MRR → $10K MRR',
            'focus': 'Initiate Arena outreach and sales calls',
            'health': 0.3,
        },
        {
            'name': 'Personal Brand',
            'stage': 'Pre-revenue',
            'model': 'Content',
            'north_star': 'Primary marketing vehicle for all offers',
            'binding': 'Content volume and consistency',
            'proof': '10K followers → 50K → 100K',
            'focus': 'Content production and distribution',
            'health': 0.25,
        },
        {
            'name': 'Empyrean Creative',
            'stage': 'Pre-revenue',
            'model': 'Agency',
            'north_star': 'AI infrastructure proven internally → productize',
            'binding': 'EOS must work internally before selling externally',
            'proof': 'All EOS services stable + Notion synced',
            'focus': 'Building EOS and AI infrastructure',
            'health': 0.5,
        },
    ]
    print('\n── Portfolio Overview ──')
    for r in rows:
        props = {
            'Company': _title(r['name']),
            'Stage': _select(r['stage']),
            'Business Model': _select(r['model']),
            'North Star': _text(r['north_star']),
            'Binding Constraint': _text(r['binding']),
            'Proof to Advance': _text(r['proof']),
            'Current Focus': _text(r['focus']),
            'Status': _select('Active'),
            'Health Score': _number(r['health']),
            'Revenue MRR': _number(0),
            'Active Agents': _number(0),
            'Tasks In Progress': _number(0),
            'Last Updated': _date(TODAY),
        }
        pid = _create_page(db_id, props)
        print(f'  {"✅" if pid else "❌"} {r["name"]}')


# ── Roles ─────────────────────────────────────────

ROLES = [
    {
        'name': 'Founder',
        'dept': 'Leadership',
        'mode': 'Human Only',
        'authority': 'Strategic',
        'status': 'Active',
        'agent': 'Founder',
        'agent_status': '🟢 Complete',
        'kpi': 'Revenue MRR',
        'kpi_value': '$0 → $10K',
        'responsibilities': (
            'Vision, strategy, capital allocation, final decisions, brand.'
        ),
        'soul_doc': '',
    },
    {
        'name': 'DEX — Executive Assistant',
        'dept': 'Leadership',
        'mode': 'AI Only',
        'authority': 'Operational',
        'status': 'AI-Staffed',
        'agent': 'DEX',
        'agent_status': '⚪ Idle',
        'kpi': 'Tasks completed',
        'kpi_value': '0',
        'responsibilities': (
            'Calendar, email, task routing, meeting prep, '
            'cross-venture coordination, daily brief.'
        ),
        'soul_doc': '/opt/OS/12_Agents/executive_assistant.md',
    },
    {
        'name': 'CEO Agent',
        'dept': 'Leadership',
        'mode': 'AI Only',
        'authority': 'Strategic',
        'status': 'AI-Staffed',
        'agent': 'CEO Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'Revenue growth',
        'kpi_value': '0',
        'responsibilities': (
            'Strategic oversight, delegation to dept agents, '
            'goal setting, org health monitoring.'
        ),
        'soul_doc': '/opt/OS/12_Agents/ceo_agent.md',
    },
    {
        'name': 'Sales Agent',
        'dept': 'Sales',
        'mode': 'AI Only',
        'authority': 'Operational',
        'status': 'AI-Staffed',
        'agent': 'Sales Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'Calls booked / week',
        'kpi_value': '0',
        'responsibilities': (
            'Lead qualification, follow-up sequences, '
            'call booking, pipeline management.'
        ),
        'soul_doc': '',
    },
    {
        'name': 'Outreach Agent',
        'dept': 'Sales',
        'mode': 'AI Only',
        'authority': 'Execution',
        'status': 'AI-Staffed',
        'agent': 'Outreach Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'DMs sent / response rate',
        'kpi_value': '0',
        'responsibilities': (
            'Instagram DM outreach, opener personalization, '
            'initial lead engagement.'
        ),
        'soul_doc': '',
    },
    {
        'name': 'Research / Intelligence Agent',
        'dept': 'Research',
        'mode': 'AI Only',
        'authority': 'Execution',
        'status': 'AI-Staffed',
        'agent': 'Research Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'ICP signals processed',
        'kpi_value': '0',
        'responsibilities': (
            'ICP analysis, market signals, competitive intelligence, '
            'knowledge base maintenance.'
        ),
        'soul_doc': '',
    },
    {
        'name': 'Content Agent',
        'dept': 'Marketing',
        'mode': 'AI Only',
        'authority': 'Execution',
        'status': 'AI-Staffed',
        'agent': 'Content Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'Content pieces published',
        'kpi_value': '0',
        'responsibilities': (
            'Content calendar management, caption drafting, '
            'campaign execution.'
        ),
        'soul_doc': '',
    },
    {
        'name': 'Operations Agent',
        'dept': 'Operations',
        'mode': 'AI Only',
        'authority': 'Operational',
        'status': 'AI-Staffed',
        'agent': 'Operations Agent',
        'agent_status': '⚪ Idle',
        'kpi': 'SOP coverage',
        'kpi_value': '0%',
        'responsibilities': (
            'Process documentation, SOP execution, tool management, '
            'system health monitoring.'
        ),
        'soul_doc': '',
    },
]


def seed_roles(venture_id: str, venture_name: str) -> None:
    db_id = get_db_id(venture_id, 'roles')
    if not db_id:
        print(f'  ⚠️  No Roles DB for {venture_id}')
        return
    print(f'\n── Roles: {venture_name} ──')
    for r in ROLES:
        props: dict = {
            'Name': _title(r['name']),
            'Department': _select(r['dept']),
            'Mode': _select(r['mode']),
            'Authority Level': _select(r['authority']),
            'Status': _select(r['status']),
            'Agent Assigned': _select(r['agent']),
            'Agent Status': _select(r['agent_status']),
            'Primary KPI': _text(r['kpi']),
            'KPI Value': _text(r['kpi_value']),
            'Responsibilities': _text(r['responsibilities']),
            'Last Active': _date(TODAY),
        }
        if r['soul_doc']:
            props['Soul Doc Path'] = _text(r['soul_doc'])
        pid = _create_page(db_id, props)
        print(f'  {"✅" if pid else "❌"} {r["name"]}')


# ── Tools ─────────────────────────────────────────

TOOLS = [
    {
        'name': 'Telegram Bot',
        'dept': 'Operations',
        'role': 'Founder mobile control interface',
        'agent': 'DEX',
        'category': 'Native EOS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Primary founder → EOS command interface',
        'access': 'BOT_TOKEN in .env. 13_Scripts/telegram_control.py',
        'cost': 0,
    },
    {
        'name': 'Discord Bot',
        'dept': 'Operations',
        'role': 'Community management',
        'agent': 'Operations Agent',
        'category': 'Native EOS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Community engagement and moderation',
        'access': 'DISCORD_BOT_TOKEN in .env. 13_Scripts/discord_bot.py',
        'cost': 0,
    },
    {
        'name': 'Instagram (Playwright)',
        'dept': 'Sales',
        'role': 'DM outreach and inbox monitoring',
        'agent': 'Outreach Agent',
        'category': 'Native EOS',
        'integration': 'Browser Agent',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'DM monitor and outreach automation via Playwright',
        'access': 'IG_USERNAME/IG_PASSWORD in .env. 13_Scripts/dm_monitor.py',
        'cost': 0,
    },
    {
        'name': 'Calendly',
        'dept': 'Sales',
        'role': 'Sales call booking',
        'agent': 'Sales Agent',
        'category': 'External SaaS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Booking page + webhook for call scheduling',
        'access': 'CALENDLY_API_KEY in .env. Flask on os-webhook.',
        'cost': 16,
    },
    {
        'name': 'Apify',
        'dept': 'Research',
        'role': 'Instagram scraping and data collection',
        'agent': 'Research Agent',
        'category': 'External SaaS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Comment and profile scraping for lead generation',
        'access': 'APIFY_API_TOKEN in .env',
        'cost': 49,
    },
    {
        'name': 'Notion',
        'dept': 'Operations',
        'role': 'EOS UI layer — business operating system',
        'agent': 'DEX',
        'category': 'External SaaS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Primary UI for EOS primitives. Synced from Neon.',
        'access': 'NOTION_API_KEY in .env',
        'cost': 16,
    },
    {
        'name': 'Neon (PostgreSQL)',
        'dept': 'Engineering',
        'role': 'Primary EOS database',
        'agent': 'None',
        'category': 'Native EOS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': False,
        'desc': 'All EOS data: orgs, ventures, agents, memory, primitives',
        'access': 'DATABASE_URL in .env',
        'cost': 0,
    },
    {
        'name': 'Claude (Anthropic)',
        'dept': 'Engineering',
        'role': 'Primary LLM for all EOS agents',
        'agent': 'None',
        'category': 'API Integration',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': False,
        'desc': 'Haiku for scoring/classification, Sonnet for generation',
        'access': 'ANTHROPIC_API_KEY in .env',
        'cost': 0,
    },
    {
        'name': 'Google Workspace (GWS)',
        'dept': 'Operations',
        'role': 'Email and calendar integration',
        'agent': 'DEX',
        'category': 'External SaaS',
        'integration': 'Direct API',
        'status': 'Active',
        'ai_operable': True,
        'desc': 'Gmail + Google Calendar. OAuth active.',
        'access': 'GWS service account credentials in .env',
        'cost': 6,
    },
]


def seed_tools(venture_id: str, venture_name: str) -> None:
    db_id = get_db_id(venture_id, 'tools')
    if not db_id:
        print(f'  ⚠️  No Tools DB for {venture_id}')
        return
    print(f'\n── Tools: {venture_name} ──')
    for t in TOOLS:
        props: dict = {
            'Name': _title(t['name']),
            'Department': _select(t['dept']),
            'Primary Role': _text(t['role']),
            'Agent': _select(t['agent']),
            'Category': _select(t['category']),
            'Integration Level': _select(t['integration']),
            'Status': _select(t['status']),
            'AI Operable': _checkbox(t['ai_operable']),
            'Description': _text(t['desc']),
            'Access Method': _text(t['access']),
            'Cost Per Month': _number(t['cost']),
        }
        pid = _create_page(db_id, props)
        print(f'  {"✅" if pid else "❌"} {t["name"]}')


# ── Goals ─────────────────────────────────────────

GOALS_BY_VENTURE: dict[str, list[dict]] = {
    'lyfe_institute': [
        {
            'name': '$10K/month net profit from Initiate Arena',
            'type': 'North Star',
            'status': 'Behind',
            'dept': 'Sales',
            'target': '$10,000 MRR net',
            'current': '$0',
            'due': '2026-06-30',
            'progress': 0.0,
            'notes': 'Primary north star. Every decision traces here.',
        },
        {
            'name': 'First paying customer — Initiate Arena',
            'type': 'Key Result',
            'status': 'Behind',
            'dept': 'Sales',
            'target': '1 customer at $750',
            'current': '0',
            'due': '2026-04-30',
            'progress': 0.0,
            'notes': 'Proof of concept. Must happen before scaling.',
        },
        {
            'name': 'Run 20 qualified sales calls',
            'type': 'Key Result',
            'status': 'Behind',
            'dept': 'Sales',
            'target': '20 calls',
            'current': '0',
            'due': '2026-04-15',
            'progress': 0.0,
            'notes': 'Volume needed to find product-market fit.',
        },
    ],
    'personal_brand': [
        {
            'name': 'Establish consistent content output',
            'type': 'Quarterly Goal',
            'status': 'Behind',
            'dept': 'Marketing',
            'target': '5 posts/week across platforms',
            'current': '0',
            'due': '2026-06-30',
            'progress': 0.0,
            'notes': 'Content IS the advertising.',
        },
    ],
    'empyrean_creative': [
        {
            'name': 'EOS fully operational internally',
            'type': 'Quarterly Goal',
            'status': 'At risk',
            'dept': 'Operations',
            'target': 'All 5 EOS services stable + Notion synced',
            'current': '4/5 services up, Notion pending',
            'due': '2026-04-30',
            'progress': 0.6,
            'notes': 'Must prove internally before productizing.',
        },
    ],
}


def seed_goals(venture_id: str, venture_name: str) -> None:
    db_id = get_db_id(venture_id, 'goals')
    if not db_id:
        print(f'  ⚠️  No Goals DB for {venture_id}')
        return
    goals = GOALS_BY_VENTURE.get(venture_id, [])
    print(f'\n── Goals: {venture_name} ──')
    for g in goals:
        props: dict = {
            'Name': _title(g['name']),
            'Type': _select(g['type']),
            'Status': _select(g['status']),
            'Department': _select(g['dept']),
            'Target': _text(g['target']),
            'Current': _text(g['current']),
            'Due Date': _date(g['due']),
            'Progress': _number(g['progress']),
            'Notes': _text(g['notes']),
        }
        pid = _create_page(db_id, props)
        print(f'  {"✅" if pid else "❌"} {g["name"][:60]}')


# ── main ──────────────────────────────────────────

def main() -> None:
    print('EOS Notion Seed')
    print('================')

    seed_portfolio()

    for venture_id, venture_name in VENTURES:
        seed_roles(venture_id, venture_name)
        seed_tools(venture_id, venture_name)
        seed_goals(venture_id, venture_name)

    print('\n✅ Seed complete')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import scripts.notion_seed as s
print('ventures:', len(s.VENTURES))
print('roles:', len(s.ROLES))
print('tools:', len(s.TOOLS))
print('import ok')
"
```

Expected:
```
ventures: 3
roles: 8
tools: 9
import ok
```

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add scripts/notion_seed.py
git commit -m "feat: add notion_seed.py — seeds initial portfolio, roles, tools, goals"
```

---

## Task 5: Run seed script and verify

**Files:**
- Run: `scripts/notion_seed.py`

> **Prerequisite:** Task 2 must be complete. All `NOTION_*_DB` vars must be in `.env`.

- [ ] **Step 1: Verify prerequisites**

```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
# Check a representative sample of required vars
required = [
    'NOTION_PORTFOLIO_OVERVIEW_DB',
    'NOTION_LYFE_INSTITUTE_ROLES_DB',
    'NOTION_LYFE_INSTITUTE_TOOLS_DB',
    'NOTION_LYFE_INSTITUTE_GOALS_OKRS_DB',
]
missing = [k for k in required if not os.getenv(k)]
if missing:
    print('MISSING:', missing)
    print('Run scripts/notion_setup.py first')
else:
    print('Prerequisites OK')
"
```

Expected: `Prerequisites OK`

- [ ] **Step 2: Run the seed script**

```bash
cd /opt/OS && python3 scripts/notion_seed.py
```

Expected output:
```
EOS Notion Seed
================

── Portfolio Overview ──
  ✅ Lyfe Institute
  ✅ Personal Brand
  ✅ Empyrean Creative

── Roles: Personal Brand ──
  ✅ Founder
  ✅ DEX — Executive Assistant
  ... (8 roles × 3 ventures)

── Tools: Personal Brand ──
  ✅ Telegram Bot
  ✅ Discord Bot
  ... (9 tools × 3 ventures)

── Goals: Personal Brand ──
  ✅ Establish consistent content output

── Goals: Lyfe Institute ──
  ✅ $10K/month net profit from Initiate Arena
  ...

✅ Seed complete
```

- [ ] **Step 3: Spot-check in Notion**

Open Notion → Lyfe Institute → Roles. Confirm 8 rows exist with correct fields.
Open Notion → Portfolio — Munoz Holdings → Portfolio Overview. Confirm 3 rows.

- [ ] **Step 4: Delete smoke test row from Task 3**

Find and delete the "Smoke test — delete me" row created in Task 3 Step 3.
In Notion: Lyfe Institute → Tasks → find "Smoke test" → delete.

- [ ] **Step 5: Final import verification**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
import eos_ai
from eos_ai.notion_sync import write_task, get_db_id
print('eos_ai imports: clean')
print('notion_sync imports: clean')
print('lyfe tasks db:', get_db_id('lyfe_institute', 'tasks')[:8])
"
```

Expected: `eos_ai imports: clean`, `notion_sync imports: clean`, and an 8-char DB ID.

- [ ] **Step 6: Final commit**

```bash
cd /opt/OS
git status
git add -p  # review changes
git commit -m "feat: complete notion primitive architecture — setup, sync, seed"
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|-------------|------|
| 11 universal DBs per venture | Task 1 (`UNIVERSAL_DBS` list) |
| Stage-gated Projects (Stage 2+) | Task 1 (`main()` stage check) |
| Stage-gated Budget (Stage 3+) | Task 1 (`main()` stage check) |
| Portfolio Overview DB | Task 1 (`PORTFOLIO_PAGE_ID`) |
| Role dashboard pages per venture | Task 1 (`ROLE_DASHBOARDS` + `_ensure_dashboards_page`) |
| Write all DB IDs to .env | Task 1 (`set_key` loop) |
| Update VENTURES_JSON | Task 1 (`set_key('VENTURES_JSON', ...)`) |
| Idempotency | Task 1 (`_ensure_db` checks `existing_dbs`) |
| Do not remove existing .env vars | Task 1 (`set_key` only adds, never removes) |
| Runtime write layer | Task 3 (`eos_ai/notion_sync.py`) |
| `write_task`, `write_pipeline_entry`, `write_metric` | Task 3 |
| `write_meeting`, `write_decision`, `write_document` | Task 3 |
| `get_db_id` helper | Task 3 |
| Initial portfolio rows | Task 4 (`seed_portfolio`) |
| Initial roles rows (8 roles × 3 ventures) | Task 4 (`seed_roles`) |
| Initial tools rows (9 tools × 3 ventures) | Task 4 (`seed_tools`) |
| Initial goals/OKRs | Task 4 (`seed_goals`) |

**Placeholder scan:** None found. All code is complete and runnable.

**Type consistency:**
- `get_db_id(venture_id, db_key)` → used consistently in `notion_sync.py` and `notion_seed.py`
- `_create_page(db_id, props)` → imported from `notion_sync` in `notion_seed`
- `HEADERS` → imported from `notion_sync` in `notion_seed` — this requires `HEADERS` to be module-level in `notion_sync.py` ✅ (it is)
- `_title`, `_select`, `_text`, `_number`, `_date`, `_checkbox` → all defined in `notion_sync.py`, imported in `notion_seed.py` ✅
