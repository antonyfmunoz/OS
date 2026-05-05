"""
Notion Cleanup — archives old scaffold databases
and creates individual role dashboard pages.

Problems to fix:
1. Archive old emoji-prefixed scaffold DBs:
   ⚙️ Workflows, ✅ Tasks, 🎯 Pipeline
   (these predate the new schema and are empty)
2. Archive root-level Meetings DB
   (per-venture Meetings DBs now exist)
3. Create individual role pages inside
   the Role Dashboards page for each venture
4. Create Projects and Budget as locked/greyed
   stub pages (stage-gated — visible but locked)
"""

import os
import sys
import requests
from dotenv import load_dotenv

sys.path.insert(0, '/opt/OS')
load_dotenv('/opt/OS/eos_ai/.env')

TOKEN = os.getenv('NOTION_API_KEY', '')
HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
}

# Known old scaffold DB IDs from .env audit.
# These predate the new per-venture schema.
OLD_SCAFFOLD_IDS: dict[str, str] = {
    # Old ⚙️ Workflows (emoji-prefixed, pre-schema)
    '7e5b58e2-0a5c-46a8-af73-a52539ef6d69': '⚙️ Workflows (Lyfe)',
    '357d09b2-deb9-446a-acc7-a7975353fcca': '⚙️ Workflows (Empyrean)',
    '94f5f7ee-083b-42b2-baa4-f61201356d07': '⚙️ Workflows (Brand)',
    # Old ✅ Tasks — keep c6f06702 (Empyrean, has data)
    '8990bb84-273f-4590-ac64-b7cf9321ce8c': '✅ Tasks / Your List (Lyfe)',
    '4ef5362b-6062-4412-bb91-68457ffba5bf': '✅ Tasks / Your List (Brand)',
    # Old standalone Tasks DBs
    '9759dba9-544a-4653-9656-5de637cba081': 'Tasks DB (Lyfe old)',
    'd5afbe6b-768f-4094-99ae-7a14f6f7dbdc': 'Tasks DB (Empyrean old)',
    # Old 🎯 Pipeline — keep 7f090170 (Lyfe, has data)
    '3381905e-50e0-4792-8bc2-1ce48bded8db': '🎯 Pipeline (Empyrean old)',
    # Root-level Meetings DB (per-venture ones now exist)
    '333da8b9-6e4f-81bc-ac06-ee87e7d13fa7': 'Meetings DB (root)',
}

# Venture page IDs
VENTURES = [
    {
        'id': 'personal_brand',
        'name': 'Personal Brand',
        'page_id': '32eda8b9-6e4f-812b-888c-df30298aa856',
    },
    {
        'id': 'lyfe_institute',
        'name': 'Lyfe Institute',
        'page_id': '32eda8b9-6e4f-817f-a314-fc66aa831cc3',
    },
    {
        'id': 'empyrean_creative',
        'name': 'Empyrean Creative',
        'page_id': '32eda8b9-6e4f-81c7-8872-e5a768ea9faf',
    },
]

ROLE_CONFIGS = [
    {
        'name': '👤 Founder',
        'dept': 'Leadership',
        'agent': 'CEO Agent + DEX',
        'kpi': 'First sale closed / Portfolio health',
        'description': (
            'Full portfolio view. '
            'Sees all departments unfiltered. '
            'Entry point to org chart via Roles DB.'
        ),
        'filters': [
            'Goals/OKRs — all, no filter',
            'Tasks — all, no filter',
            'Meetings — all, no filter',
            'Metrics/KPIs — all, no filter',
            'Decisions — all, no filter',
            'Pipeline/CRM — all, no filter',
            'Workflows — all, no filter',
            'Roles — Gallery view = org chart',
            'Documents — all, no filter',
            'Tools — all, no filter',
        ],
    },
    {
        'name': '🤖 DEX — Executive Assistant',
        'dept': 'Leadership',
        'agent': 'DEX',
        'kpi': 'Tasks cleared / Inbox zero',
        'description': (
            'Cross-venture operational surface. '
            'Calendar, email, all tasks, '
            'all agent activity, all meetings.'
        ),
        'filters': [
            'Tasks — all, no filter',
            'Meetings — all, no filter',
            'Goals/OKRs — all, no filter',
            'Workflows — all, no filter',
            'Metrics/KPIs — all, no filter',
            'Decisions — all, no filter',
            'Documents — all, no filter',
            'Pipeline/CRM — awareness only',
        ],
    },
    {
        'name': '🏢 CEO Agent',
        'dept': 'Leadership',
        'agent': 'CEO Agent',
        'kpi': 'Delegation completion rate',
        'description': (
            'Strategic delegation and org health. '
            'Sees all to delegate correctly.'
        ),
        'filters': [
            'Tasks — Assigned To = CEO Agent',
            'Goals/OKRs — all, no filter',
            'Roles — all (delegation targets)',
            'Metrics/KPIs — all, no filter',
            'Decisions — Department = Leadership',
            'Workflows — all, no filter',
            'Documents — Category = Strategy',
        ],
    },
    {
        'name': '💼 Sales',
        'dept': 'Sales',
        'agent': 'Sales Agent + Outreach Agent',
        'kpi': 'Reply rate / Calls booked / Closes',
        'description': (
            'Revenue operations. Pipeline, '
            'DM conversations, call booking, '
            'qualification, closing.'
        ),
        'filters': [
            'Tasks — Department = Sales',
            'Meetings — Type = Sales Call or Client Call',
            'Pipeline/CRM — Type = Lead or Customer',
            'Workflows — Department = Sales',
            'Skills — Department = Sales',
            'Tools — Department = Sales',
            'Metrics/KPIs — Department = Sales',
            'Documents — Department = Sales',
        ],
    },
    {
        'name': '📣 Marketing',
        'dept': 'Marketing',
        'agent': 'Content Agent',
        'kpi': 'Content published / Engagement rate',
        'description': (
            'Content, distribution, brand, '
            'campaigns, audience growth.'
        ),
        'filters': [
            'Tasks — Department = Marketing',
            'Meetings — Department = Marketing',
            'Content Calendar — full view',
            'Workflows — Department = Marketing',
            'Skills — Department = Marketing',
            'Tools — Department = Marketing',
            'Metrics/KPIs — Department = Marketing',
            'Documents — Department = Marketing',
        ],
    },
    {
        'name': '⚙️ Operations',
        'dept': 'Operations',
        'agent': 'Operations Agent',
        'kpi': 'Workflows active / SOPs documented',
        'description': (
            'Workflows, SOPs, processes, '
            'systems, efficiency.'
        ),
        'filters': [
            'Tasks — Department = Operations',
            'Meetings — Department = Operations',
            'Workflows — Department = Operations',
            'Skills — Department = Operations',
            'Tools — Department = Operations',
            'Documents — Type = SOP',
            'Metrics/KPIs — Department = Operations',
        ],
    },
    {
        'name': '💰 Finance',
        'dept': 'Finance',
        'agent': 'Finance Agent',
        'kpi': 'Revenue tracked / Expenses logged',
        'description': (
            'Revenue, expenses, budget, '
            'invoicing, financial health.'
        ),
        'filters': [
            'Tasks — Department = Finance',
            'Meetings — Department = Finance',
            'Metrics/KPIs — Department = Finance or Category = Revenue',
            'Decisions — Impact = Critical or High',
            'Documents — Type = Financial Report',
            'Tools — Department = Finance',
            'Budget — full view (unlocks Stage 3)',
        ],
    },
    {
        'name': '🔬 Research',
        'dept': 'Research',
        'agent': 'Research Agent + Intelligence Agent',
        'kpi': 'Signals processed / ICP profiles scored',
        'description': (
            'Market intelligence, ICP signals, '
            'competitive analysis, insights.'
        ),
        'filters': [
            'Tasks — Department = Research',
            'Documents — Source = Research Agent or Intelligence Agent',
            'Workflows — Department = Research',
            'Skills — Department = Research',
            'Tools — Department = Research',
            'Metrics/KPIs — Department = Research',
        ],
    },
    {
        'name': '🤝 Customer Success',
        'dept': 'Customer Success',
        'agent': 'Customer Success Agent',
        'kpi': 'Retention rate / NPS',
        'description': (
            'Customer retention, satisfaction, '
            'onboarding, renewal. '
            'Activates after first sale.'
        ),
        'filters': [
            'Tasks — Department = Customer Success',
            'Meetings — Type = CS Call or Client Call',
            'Pipeline/CRM — Stage = Active Customer, At Risk, or Churned',
            'Workflows — Department = Customer Success',
            'Skills — Department = Customer Success',
            'Tools — Department = Customer Success',
            'Metrics/KPIs — Category = Customer',
            'Documents — Type = Playbook',
        ],
    },
]


# ── Helpers ────────────────────────────────────────

def _get_page_title(page: dict) -> str:
    props = page.get('properties', {})
    tp = props.get('title', {})
    rt = tp.get('title', []) if isinstance(tp, dict) else []
    return rt[0].get('plain_text', '') if rt else ''


def get_all_dbs() -> dict[str, dict]:
    resp = requests.post(
        'https://api.notion.com/v1/search',
        headers=HEADERS,
        json={
            'filter': {'value': 'database', 'property': 'object'},
            'page_size': 100,
        },
        timeout=15,
    )
    try:
        results = resp.json().get('results', [])
    except Exception:
        return {}
    dbs = {}
    for db in results:
        tl = db.get('title', [])
        title = tl[0].get('plain_text', '') if tl else ''
        dbs[db['id']] = {
            'title': title,
            'parent': db.get('parent', {}),
            'id': db['id'],
        }
    return dbs


def get_child_page_titles(page_id: str) -> set[str]:
    """Return set of child page titles for duplicate checking."""
    resp = requests.get(
        f'https://api.notion.com/v1/blocks/{page_id}/children',
        headers=HEADERS,
        params={'page_size': 100},
        timeout=15,
    )
    titles: set[str] = set()
    try:
        for block in resp.json().get('results', []):
            if block.get('type') != 'child_page':
                continue
            t = block.get('child_page', {}).get('title', '')
            if t:
                titles.add(t)
    except Exception:
        pass
    return titles


def archive_db(db_id: str, label: str) -> None:
    resp = requests.patch(
        f'https://api.notion.com/v1/databases/{db_id}',
        headers=HEADERS,
        json={'archived': True},
        timeout=10,
    )
    try:
        ok = resp.status_code == 200
        msg = '' if ok else resp.json().get('message', '')
    except Exception:
        ok = False
        msg = 'parse error'
    print(f'  {"✅" if ok else "❌"} {label}{": " + msg if msg else ""}')


def ensure_dashboards_page(venture_page_id: str) -> str:
    """Get or create the 'Role Dashboards' sub-page inside a venture."""
    resp = requests.post(
        'https://api.notion.com/v1/search',
        headers=HEADERS,
        json={'query': 'Role Dashboards', 'page_size': 20},
        timeout=15,
    )
    try:
        results = resp.json().get('results', [])
    except Exception:
        return ''
    for r in results:
        if r.get('object') != 'page':
            continue
        if r.get('parent', {}).get('page_id') != venture_page_id:
            continue
        title = _get_page_title(r)
        if title == 'Role Dashboards':
            print('  ⏭️  Role Dashboards (exists)')
            return r['id']
    # Create it
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
    try:
        if resp.status_code == 200:
            print('  ✅ Role Dashboards (created)')
            return resp.json().get('id', '')
        print(f'  ❌ Role Dashboards: {resp.json().get("message", "")}')
    except Exception as e:
        print(f'  ❌ Role Dashboards: {e}')
    return ''


def create_role_page(
    parent_id: str,
    role: dict,
) -> str:
    filter_text = '\n'.join(f'• {f}' for f in role['filters'])
    content = (
        f'Department: {role["dept"]}\n'
        f'Agent: {role["agent"]}\n'
        f'Primary KPI: {role["kpi"]}\n\n'
        f'Purpose: {role["description"]}\n\n'
        f'──────────────────────\n'
        f'Add linked database views below.\n'
        f'Apply these filters:\n\n'
        f'{filter_text}\n\n'
        f'──────────────────────\n'
        f'Instructions:\n'
        f'1. Click + below\n'
        f'2. Choose "Linked view of database"\n'
        f'3. Select the database\n'
        f'4. Click Filter → add Department filter\n'
        f'5. Repeat for each database above'
    )
    resp = requests.post(
        'https://api.notion.com/v1/pages',
        headers=HEADERS,
        json={
            'parent': {'page_id': parent_id},
            'properties': {'title': {'title': [
                {'text': {'content': role['name']}}
            ]}},
            'children': [{
                'object': 'block',
                'type': 'callout',
                'callout': {
                    'rich_text': [{'type': 'text',
                                   'text': {'content': content[:2000]}}],
                    'icon': {'type': 'emoji', 'emoji': '🎯'},
                    'color': 'gray_background',
                },
            }],
        },
        timeout=15,
    )
    try:
        if resp.status_code == 200:
            print(f'  ✅ {role["name"]}')
            return resp.json().get('id', '')
        print(f'  ❌ {role["name"]}: {resp.json().get("message", "")}')
    except Exception as e:
        print(f'  ❌ {role["name"]}: {e}')
    return ''


def create_stub_page(
    venture_page_id: str,
    name: str,
    emoji: str,
    unlocks_at: str,
    description: str,
) -> str:
    """Create a locked/greyed stub page for a stage-gated feature."""
    content = (
        f'🔒 Stage-gated — {unlocks_at}\n\n'
        f'{description}\n\n'
        f'This page will be built out when the stage milestone is reached.'
    )
    resp = requests.post(
        'https://api.notion.com/v1/pages',
        headers=HEADERS,
        json={
            'parent': {'page_id': venture_page_id},
            'properties': {'title': {'title': [
                {'text': {'content': f'{emoji} {name} (Locked)'}}
            ]}},
            'children': [{
                'object': 'block',
                'type': 'callout',
                'callout': {
                    'rich_text': [{'type': 'text',
                                   'text': {'content': content}}],
                    'icon': {'type': 'emoji', 'emoji': '🔒'},
                    'color': 'red_background',
                },
            }],
        },
        timeout=15,
    )
    try:
        if resp.status_code == 200:
            print(f'  ✅ {emoji} {name} (stub)')
            return resp.json().get('id', '')
        print(f'  ❌ {name} stub: {resp.json().get("message", "")}')
    except Exception as e:
        print(f'  ❌ {name} stub: {e}')
    return ''


# ── Main ────────────────────────────────────────────

def run_cleanup() -> None:
    print('🧹 Notion Cleanup')
    print('=' * 50)

    # ── Step 1: Archive known old scaffold DBs ─────
    print('\n📦 Step 1 — Archiving old scaffold databases...')
    all_dbs = get_all_dbs()
    archived = 0
    skipped = 0

    for db_id, label in OLD_SCAFFOLD_IDS.items():
        # Normalize ID for comparison (add dashes if missing)
        normalized = db_id.replace('-', '')
        match = None
        for known_id in all_dbs:
            if known_id.replace('-', '') == normalized:
                match = known_id
                break
        if match:
            archive_db(match, label)
            archived += 1
        else:
            print(f'  ⏭️  Not found (already archived?): {label}')
            skipped += 1

    # Also catch any remaining emoji-prefixed DBs not in the known list
    emoji_markers = ['⚙️', '✅', '🎯', '📋']
    for db_id, db in all_dbs.items():
        title = db.get('title', '')
        if any(e in title for e in emoji_markers):
            if db_id.replace('-', '') not in {
                k.replace('-', '') for k in OLD_SCAFFOLD_IDS
            }:
                archive_db(db_id, f'{title} (emoji-prefixed)')
                archived += 1

    print(f'\n  Total archived: {archived} | Skipped: {skipped}')

    # ── Step 2: Role Dashboards per venture ────────
    print('\n🗂️  Step 2 — Building Role Dashboards...')
    for venture in VENTURES:
        print(f'\n  [{venture["name"]}]')
        dashboards_id = ensure_dashboards_page(venture['page_id'])
        if not dashboards_id:
            print('  ❌ Could not get/create Role Dashboards page')
            continue
        existing = get_child_page_titles(dashboards_id)
        for role in ROLE_CONFIGS:
            if role['name'] in existing:
                print(f'  ⏭️  {role["name"]} (exists)')
                continue
            create_role_page(dashboards_id, role)

    # ── Step 3: Projects and Budget stub pages ─────
    print('\n🔒 Step 3 — Creating stage-gated stub pages...')
    stubs = [
        {
            'name': 'Projects',
            'emoji': '📁',
            'unlocks_at': 'Stage 2 — first revenue',
            'description': (
                'Project management layer. '
                'Tracks multi-week initiatives across ventures. '
                'Activates when the venture has active customers '
                'and requires structured delivery management.'
            ),
        },
        {
            'name': 'Budget',
            'emoji': '💰',
            'unlocks_at': 'Stage 3 — $5K MRR',
            'description': (
                'Financial planning layer. '
                'Tracks budget, forecasts, and burn rate. '
                'Activates when monthly revenue justifies '
                'formal financial management.'
            ),
        },
    ]
    for venture in VENTURES:
        print(f'\n  [{venture["name"]}]')
        existing = get_child_page_titles(venture['page_id'])
        for stub in stubs:
            stub_name = f'{stub["emoji"]} {stub["name"]} (Locked)'
            if stub_name in existing:
                print(f'  ⏭️  {stub_name} (exists)')
                continue
            create_stub_page(
                venture['page_id'],
                stub['name'],
                stub['emoji'],
                stub['unlocks_at'],
                stub['description'],
            )

    print('\n✅ Cleanup complete')


if __name__ == '__main__':
    run_cleanup()
