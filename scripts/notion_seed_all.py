"""
Notion Seed All — seeds each configured venture (goals, roles, metrics,
tools, specs) and content calendars from the tenant's notion_seed.

All business copy (venture names, offers, OKRs, pillars, brand strategy)
lives in data/umh/instance.json under `notion_seed`. This script is a pure
template: it reads that seed at runtime and writes it to Notion. No tenant
literals are embedded here.

Idempotent in effect — safe on empty DBs, do not re-run on populated ones.
Degrades gracefully: if no notion_seed is configured, it seeds nothing.
"""

import os
import sys
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

from adapters.notion.notion_sync import (

    get_db_id,
    HEADERS, _title, _select, _text, _number,
    _date, _checkbox, _create_page,
    write_document, write_metric,
)

from substrate.state.business.business_instance import (
    get_notion_seed, get_ai_name, get_founder_name, get_ventures,
)


TODAY = datetime.now().strftime('%Y-%m-%d')


def _ventures() -> list:
    """(venture_id, name) tuples from the tenant registry (BIS) at runtime."""
    try:
        from substrate.state.context.context import load_context_from_env
        return [(v.get('id', ''), v.get('name', v.get('id', '')))
                for v in get_ventures(load_context_from_env()) if v.get('id')]
    except Exception:
        return []


VENTURES = _ventures()


def _ai_name() -> str:
    try:
        return get_ai_name() or 'Assistant'
    except Exception:
        return 'Assistant'


def _founder_name() -> str:
    try:
        from substrate.state.context.context import load_context_from_env
        return get_founder_name(load_context_from_env(), default='the founder')
    except Exception:
        return 'the founder'


AI_NAME = _ai_name()
FOUNDER_NAME = _founder_name()

# Per-tenant workspace seed content. Empty dict for a fresh tenant.
SEED = get_notion_seed()

# Token map for template placeholders stored in the seed.
_FMT = {'founder_name': FOUNDER_NAME, 'ai_name': AI_NAME, 'root': _ROOT,
        'vps_ip': os.getenv('UMH_VPS_IP', '<vps-host>')}


def _fmt(value):
    """Interpolate {founder_name}/{ai_name}/{root}/{vps_ip} tokens in a string.

    Non-strings pass through unchanged. Unknown tokens are left intact so a
    seed entry with an unrelated brace never crashes the seeder.
    """
    if not isinstance(value, str):
        return value
    try:
        return value.format(**_FMT)
    except (KeyError, IndexError, ValueError):
        return value


def _venture_label(vid: str) -> tuple:
    """(emoji, display_name) for a venture, from the seed's venture_labels."""
    label = (SEED.get('venture_labels') or {}).get(vid, {})
    return label.get('emoji', '•'), label.get('name', vid)


# ── Per-venture seeding (goals, roles, metrics, tools, specs) ─────────────

def seed_venture(vid: str) -> None:
    """Seed one venture's goals, roles, metrics, tools, and documents
    entirely from the tenant's notion_seed content."""
    emoji, name = _venture_label(vid)
    print(f'\n{emoji} {name}')
    print('=' * 40)

    # Goals
    goals = [dict(g) for g in (SEED.get('goals_by_venture') or {}).get(vid, [])]
    goals_db = get_db_id(vid, 'goals')
    print(f'\n🎯 Goals (DB: {goals_db[:8] if goals_db else "MISSING"})...')
    if goals_db and goals:
        for g in goals:
            props = {
                'Name': _title(_fmt(g['name'])),
                'Type': _select(g['type']),
                'Status': _select(g['status']),
                'Department': _select(g['dept']),
                'Target': _text(_fmt(g['target'])),
                'Current': _text(_fmt(g['current'])),
                'Due Date': _date(g['due']),
                'Progress': _number(g['progress']),
                'Notes': _text(_fmt(g['notes'])),
            }
            pid = _create_page(goals_db, props)
            print(f'  {"✅" if pid else "❌"} {_fmt(g["name"])[:60]}')
    elif not goals:
        print('  ⚠️  Skipped — no goals in seed')
    else:
        print('  ⚠️  Skipped — no Goals DB')

    # Roles
    roles = [dict(r) for r in (SEED.get('roles_by_venture') or {}).get(vid, [])]
    roles_db = get_db_id(vid, 'roles')
    print(f'\n👥 Roles (DB: {roles_db[:8] if roles_db else "MISSING"})...')
    if roles_db and roles:
        for r in roles:
            props: dict = {
                'Name': _title(_fmt(r['name'])),
                'Department': _select(r['dept']),
                'Mode': _select(r['mode']),
                'Authority Level': _select(r['authority']),
                'Status': _select(r['status']),
                'Agent Assigned': _select(_fmt(r['agent'])),
                'Agent Status': _select(r['agent_status']),
                'Primary KPI': _text(r['kpi']),
                'KPI Value': _text(r['kpi_value']),
                'Responsibilities': _text(r['responsibilities']),
                'Last Active': _date(TODAY),
            }
            if r.get('soul_doc'):
                props['Soul Doc Path'] = _text(_fmt(r['soul_doc']))
            pid = _create_page(roles_db, props)
            print(f'  {"✅" if pid else "❌"} {_fmt(r["name"])}')
    elif not roles:
        print('  ⚠️  Skipped — no roles in seed')
    else:
        print('  ⚠️  Skipped — no Roles DB')

    # Metrics
    metrics = (SEED.get('metrics_by_venture') or {}).get(vid, [])
    print(f'\n📊 Metrics...')
    for m in metrics:
        pid = write_metric(
            venture_id=vid,
            metric_name=m['name'],
            value=m['value'],
            target=m['target'],
            unit=m['unit'],
            department=m['dept'],
            category=m['cat'],
            period=m['period'],
            notes=m['notes'],
        )
        print(f'  {"✅" if pid else "❌"} {m["name"]}')
    if not metrics:
        print('  ⚠️  Skipped — no metrics in seed')

    # Tools
    tools = [dict(t) for t in (SEED.get('tools_by_venture') or {}).get(vid, [])]
    tools_db = get_db_id(vid, 'tools')
    print(f'\n🔧 Tools (DB: {tools_db[:8] if tools_db else "MISSING"})...')
    if tools_db and tools:
        for t in tools:
            props = {
                'Name': _title(_fmt(t['name'])),
                'Department': _select(t['dept']),
                'Primary Role': _text(t['role']),
                'Agent': _select(_fmt(t['agent'])),
                'Category': _select(t['cat']),
                'Integration Level': _select(t['integration']),
                'Status': _select('Active'),
                'AI Operable': _checkbox(t['ai_op']),
                'Description': _text(t['desc']),
                'Access Method': _text(_fmt(t['access'])),
                'Cost Per Month': _number(t['cost']),
            }
            pid = _create_page(tools_db, props)
            print(f'  {"✅" if pid else "❌"} {_fmt(t["name"])}')
    elif not tools:
        print('  ⚠️  Skipped — no tools in seed')
    else:
        print('  ⚠️  Skipped — no Tools DB')

    # Documents (venture specs / strategy docs)
    specs = (SEED.get('venture_specs') or {}).get(vid, [])
    docs_db = get_db_id(vid, 'documents')
    print(f'\n📄 Documents (DB: {docs_db[:8] if docs_db else "MISSING"})...')
    if docs_db and specs:
        for d in specs:
            pid = write_document(
                venture_id=vid,
                title=d['title'],
                doc_type=d['type'],
                department=d['dept'],
                category=d.get('cat', 'General'),
                content=d['content'],
                source=d.get('source', 'Founder'),
                confidence=d.get('confidence', 'High'),
            )
            print(f'  {"✅" if pid else "❌"} {d["title"]}')
    elif not specs:
        print('  ⚠️  Skipped — no venture specs in seed')
    else:
        print('  ⚠️  Skipped — no Documents DB')


# ── Content Calendars — every configured venture ─────────────────────────

# Content calendar entries stored in the documents DB under
# type='Content Calendar'. One template entry per venture covers the
# weekly cadence and pillar structure. Copy lives in the tenant seed.

def seed_content_calendars() -> None:
    print('\n📅 Content Calendars')
    print('=' * 40)
    calendars = SEED.get('content_calendar_by_venture') or {}
    for venture_id, venture_name in VENTURES:
        entries = calendars.get(venture_id, [])
        if not entries:
            print(f'\n  ⚠️  No calendar entries defined for {venture_name}')
            continue
        docs_db = get_db_id(venture_id, 'documents')
        print(f'\n{venture_name} (DB: {docs_db[:8] if docs_db else "MISSING"})')
        for e in entries:
            pid = write_document(
                venture_id=venture_id,
                title=e['title'],
                doc_type='Content Calendar',
                department=e['dept'],
                category='Content',
                content=e['content'],
                source='System',
                confidence='High',
            )
            print(f'  {"✅" if pid else "❌"} {e["title"]}')


# ── main ──────────────────────────────────────────

def main() -> None:
    print('EOS Notion Seed — All Ventures')
    print('================================')
    print(f'Date: {TODAY}')

    if not SEED:
        print('\nNo notion_seed configured — nothing to seed.')
        return

    for vid in SEED.get('venture_order', []):
        seed_venture(vid)

    seed_content_calendars()

    print('\n✅ Seed complete')


if __name__ == '__main__':
    main()
