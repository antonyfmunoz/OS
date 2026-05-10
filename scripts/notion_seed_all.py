"""
Notion Seed All — seeds Empyrean Creative, Personal Brand ventures
and content calendars for all three ventures.

Lyfe Institute was already seeded in notion_seed.py.
This script completes the remaining two ventures.

Idempotent in effect — safe on empty DBs, do not re-run on populated ones.
"""

import os
import sys
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'eos_ai', '.env'))

from eos_ai.notion_sync import (
    get_db_id,
    HEADERS, _title, _select, _text, _number,
    _date, _checkbox, _create_page,
    write_document, write_metric,
)

TODAY = datetime.now().strftime('%Y-%m-%d')

VENTURES = [
    ('personal_brand',     'Personal Brand'),
    ('lyfe_institute',     'Lyfe Institute'),
    ('empyrean_creative',  'Empyrean Creative'),
]


# ── Empyrean Creative ─────────────────────────────

def seed_empyrean() -> None:
    vid = 'empyrean_creative'
    print('\n⚡ Empyrean Creative')
    print('=' * 40)

    # Goals
    goals_db = get_db_id(vid, 'goals')
    print(f'\n🎯 Goals (DB: {goals_db[:8] if goals_db else "MISSING"})...')
    goals = [
        {
            'name': 'Close first B2B client',
            'type': 'North Star',
            'status': 'Behind',
            'dept': 'Sales',
            'target': '1 client',
            'current': '0 clients',
            'due': '2026-09-30',
            'progress': 0.0,
            'notes': 'Prove AI service externally after internal validation.',
        },
        {
            'name': 'Hit $10K MRR',
            'type': 'Annual Goal',
            'status': 'Behind',
            'dept': 'Finance',
            'target': '$10,000 MRR',
            'current': '$0 MRR',
            'due': '2026-12-31',
            'progress': 0.0,
            'notes': 'Secondary north star. Triggered after Lyfe Institute hits $10K.',
        },
        {
            'name': 'Prove EntrepreneurOS internally first',
            'type': 'Quarterly Goal',
            'status': 'At risk',
            'dept': 'Operations',
            'target': 'Full internal deployment — all 5 services stable + Notion synced',
            'current': 'Phase 1 complete — 4/5 services up',
            'due': '2026-04-30',
            'progress': 0.6,
            'notes': 'Must prove on own ops before selling externally.',
        },
        {
            'name': 'Build 3 AI service productized offerings',
            'type': 'Quarterly Goal',
            'status': 'Not started',
            'dept': 'Product',
            'target': '3 offerings defined, priced, and packaged',
            'current': '0 defined',
            'due': '2026-06-30',
            'progress': 0.0,
            'notes': 'Phase 2 trigger. After internal EOS is fully proven.',
        },
    ]
    if goals_db:
        for g in goals:
            props = {
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
            pid = _create_page(goals_db, props)
            print(f'  {"✅" if pid else "❌"} {g["name"][:60]}')
    else:
        print('  ⚠️  Skipped — no Goals DB')

    # Roles
    roles_db = get_db_id(vid, 'roles')
    print(f'\n👥 Roles (DB: {roles_db[:8] if roles_db else "MISSING"})...')
    roles = [
        {
            'name': 'CEO / Founder',
            'dept': 'Leadership',
            'mode': 'Human Only',
            'authority': 'Strategic',
            'status': 'Active',
            'agent': 'Founder',
            'agent_status': '🟢 Active',
            'kpi': 'First client closed',
            'kpi_value': '0 / 1',
            'responsibilities': (
                'Vision, strategy, product direction, client relationships.'
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
            'kpi': 'Tasks cleared / Ops running',
            'kpi_value': '0 tasks',
            'responsibilities': (
                'Calendar, email, meetings, task coordination, daily ops.'
            ),
            'soul_doc': '/opt/OS/agents/executive_assistant.md',
        },
        {
            'name': 'CEO Agent',
            'dept': 'Leadership',
            'mode': 'AI Only',
            'authority': 'Strategic',
            'status': 'AI-Staffed',
            'agent': 'CEO Agent',
            'agent_status': '⚪ Idle',
            'kpi': 'Product development progress',
            'kpi_value': '0%',
            'responsibilities': (
                'Product strategy, org evolution, departmental delegation.'
            ),
            'soul_doc': '/opt/OS/agents/ceo_agent.md',
        },
        {
            'name': 'Operations Agent',
            'dept': 'Operations',
            'mode': 'AI Only',
            'authority': 'Execution',
            'status': 'AI-Staffed',
            'agent': 'Operations Agent',
            'agent_status': '⚪ Idle',
            'kpi': 'Systems operational',
            'kpi_value': '0 / 5 systems',
            'responsibilities': (
                'Internal systems, workflows, automation infrastructure.'
            ),
            'soul_doc': '',
        },
        {
            'name': 'Research Agent',
            'dept': 'Research',
            'mode': 'AI Only',
            'authority': 'Execution',
            'status': 'AI-Staffed',
            'agent': 'Research Agent',
            'agent_status': '⚪ Idle',
            'kpi': 'Market intelligence reports',
            'kpi_value': '0 reports',
            'responsibilities': (
                'Market research, competitor analysis, client intelligence.'
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
            'kpi': 'Content pieces produced',
            'kpi_value': '0 pieces',
            'responsibilities': (
                'Brand content, case studies, thought leadership, '
                'portfolio documentation.'
            ),
            'soul_doc': '',
        },
        {
            'name': 'Finance Agent',
            'dept': 'Finance',
            'mode': 'AI Only',
            'authority': 'Execution',
            'status': 'AI-Staffed',
            'agent': 'Finance Agent',
            'agent_status': '⚪ Idle',
            'kpi': 'Expenses tracked / Runway',
            'kpi_value': '$0 tracked',
            'responsibilities': (
                'Expense tracking, invoice management, financial reporting.'
            ),
            'soul_doc': '',
        },
    ]
    if roles_db:
        for r in roles:
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
            pid = _create_page(roles_db, props)
            print(f'  {"✅" if pid else "❌"} {r["name"]}')
    else:
        print('  ⚠️  Skipped — no Roles DB')

    # Metrics
    print(f'\n📊 Metrics...')
    metrics = [
        {
            'name': 'Monthly Revenue (MRR)',
            'value': 0, 'target': 10000,
            'unit': '$', 'dept': 'Finance',
            'cat': 'Revenue', 'period': 'Monthly',
            'notes': 'Primary financial north star.',
        },
        {
            'name': 'Active Clients',
            'value': 0, 'target': 3,
            'unit': 'clients', 'dept': 'Sales',
            'cat': 'Customer', 'period': 'Monthly',
            'notes': 'Phase 2 target.',
        },
        {
            'name': 'AI Service Products Defined',
            'value': 0, 'target': 3,
            'unit': 'products', 'dept': 'Product',
            'cat': 'Product', 'period': 'Quarterly',
            'notes': 'Productized AI service offerings.',
        },
        {
            'name': 'Internal Systems Live',
            'value': 4, 'target': 5,
            'unit': 'systems', 'dept': 'Operations',
            'cat': 'Efficiency', 'period': 'Quarterly',
            'notes': '4 containers + Notion sync = 5 systems.',
        },
        {
            'name': 'AI Workflows Active',
            'value': 0, 'target': 10,
            'unit': 'workflows', 'dept': 'Operations',
            'cat': 'Efficiency', 'period': 'Monthly',
            'notes': 'Automated recurring workflows running without intervention.',
        },
    ]
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

    # Tools
    tools_db = get_db_id(vid, 'tools')
    print(f'\n🔧 Tools (DB: {tools_db[:8] if tools_db else "MISSING"})...')
    tools = [
        {
            'name': 'EntrepreneurOS (Internal)',
            'dept': 'All',
            'role': 'Primary product — proven internally before selling',
            'agent': 'None',
            'cat': 'Native EOS',
            'integration': 'Direct API',
            'ai_op': True,
            'desc': 'AI business OS. Build → Test → Validate → Productize.',
            'access': 'VPS + Discord + Notion',
            'cost': 0,
        },
        {
            'name': 'Claude Code',
            'dept': 'Engineering',
            'role': 'Primary build tool for EOS development',
            'agent': 'Operations Agent',
            'cat': 'External SaaS',
            'integration': 'Direct API',
            'ai_op': True,
            'desc': 'AI-native coding assistant running 24/7 on VPS.',
            'access': 'Claude Code CLI on VPS tmux',
            'cost': 100,
        },
        {
            'name': 'Neon PostgreSQL',
            'dept': 'All',
            'role': 'Operational backend database',
            'agent': 'None',
            'cat': 'Native EOS',
            'integration': 'Direct API',
            'ai_op': False,
            'desc': 'All EOS data: orgs, ventures, agents, memory, primitives.',
            'access': 'Internal via db.py. DATABASE_URL in .env',
            'cost': 0,
        },
        {
            'name': 'GitHub',
            'dept': 'Engineering',
            'role': 'Version control and code repository',
            'agent': 'Operations Agent',
            'cat': 'External SaaS',
            'integration': 'Direct API',
            'ai_op': True,
            'desc': 'OS repo. Feature branch workflow. PR to dev → main.',
            'access': 'GitHub API + SSH deploy key',
            'cost': 0,
        },
        {
            'name': 'Hostinger VPS',
            'dept': 'Operations',
            'role': 'Server hosting all EOS containers',
            'agent': 'Operations Agent',
            'cat': 'External SaaS',
            'integration': 'Direct API',
            'ai_op': False,
            'desc': 'Ubuntu 24. 4 Docker containers. 24/7 uptime.',
            'access': 'SSH via Tailscale. 100.77.233.50',
            'cost': 30,
        },
        {
            'name': 'Notion',
            'dept': 'Operations',
            'role': 'EOS UI layer — business operating system frontend',
            'agent': 'DEX',
            'cat': 'External SaaS',
            'integration': 'Direct API',
            'ai_op': True,
            'desc': 'Primary UI for all EOS data. Synced from Neon via notion_sync.',
            'access': 'NOTION_API_KEY in .env',
            'cost': 16,
        },
        {
            'name': 'Telegram Bot',
            'dept': 'Operations',
            'role': 'Founder mobile control interface',
            'agent': 'DEX',
            'cat': 'Native EOS',
            'integration': 'Direct API',
            'ai_op': True,
            'desc': 'Natural language commands → EOS from iPhone via Termius.',
            'access': 'BOT_TOKEN in .env. 13_Scripts/telegram_control.py',
            'cost': 0,
        },
    ]
    if tools_db:
        for t in tools:
            props = {
                'Name': _title(t['name']),
                'Department': _select(t['dept']),
                'Primary Role': _text(t['role']),
                'Agent': _select(t['agent']),
                'Category': _select(t['cat']),
                'Integration Level': _select(t['integration']),
                'Status': _select('Active'),
                'AI Operable': _checkbox(t['ai_op']),
                'Description': _text(t['desc']),
                'Access Method': _text(t['access']),
                'Cost Per Month': _number(t['cost']),
            }
            pid = _create_page(tools_db, props)
            print(f'  {"✅" if pid else "❌"} {t["name"]}')
    else:
        print('  ⚠️  Skipped — no Tools DB')

    # Documents
    docs_db = get_db_id(vid, 'documents')
    print(f'\n📄 Documents (DB: {docs_db[:8] if docs_db else "MISSING"})...')
    if docs_db:
        docs = [
            {
                'title': 'Empyrean Creative Business Spec',
                'type': 'Strategy',
                'dept': 'Leadership',
                'cat': 'General',
                'content': (
                    'Creative studio. Design, brand systems, media production, '
                    'AI infrastructure. Build AI infrastructure for own operations '
                    'first, then productize as AI service business. '
                    'Stage 1: Internal Validation. Stage 2: First external client.'
                ),
                'source': 'Founder',
                'confidence': 'High',
            },
            {
                'title': 'EntrepreneurOS Product Vision',
                'type': 'Strategy',
                'dept': 'Product',
                'cat': 'General',
                'content': (
                    'AI-native business OS. Proves model on own companies first. '
                    'Phase 1: Internal proof — all EOS services stable, Notion synced. '
                    'Phase 2: Productize as AI service. Phase 3: SaaS. '
                    'Three protocol layers: AI Identity (universal), EOS platform, '
                    'OS module (subscription-based).'
                ),
                'source': 'Founder',
                'confidence': 'High',
            },
            {
                'title': 'AI Service Offer Framework',
                'type': 'Playbook',
                'dept': 'Product',
                'cat': 'General',
                'content': (
                    'Three productized AI service offerings planned. '
                    'Target: B2B founders and operators. '
                    'Delivery: Done-for-you EOS deployment. '
                    'Pricing model: TBD post internal validation. '
                    'Go-to-market: Personal brand content → inbound.'
                ),
                'source': 'Founder',
                'confidence': 'Medium',
            },
        ]
        for d in docs:
            pid = write_document(
                venture_id=vid,
                title=d['title'],
                doc_type=d['type'],
                department=d['dept'],
                category=d['cat'],
                content=d['content'],
                source=d['source'],
                confidence=d['confidence'],
            )
            print(f'  {"✅" if pid else "❌"} {d["title"]}')
    else:
        print('  ⚠️  Skipped — no Documents DB')


# ── Personal Brand ────────────────────────────────

def seed_personal_brand() -> None:
    vid = 'personal_brand'
    print('\n🎭 Personal Brand')
    print('=' * 40)

    # Goals
    goals_db = get_db_id(vid, 'goals')
    print(f'\n🎯 Goals (DB: {goals_db[:8] if goals_db else "MISSING"})...')
    goals = [
        {
            'name': 'Primary marketing vehicle for all offers',
            'type': 'North Star',
            'status': 'Behind',
            'dept': 'Marketing',
            'target': 'Content IS the advertising — no paid ads needed',
            'current': '0 posts published',
            'due': '2026-12-31',
            'progress': 0.0,
            'notes': 'Content drives all leads for Lyfe Institute and Empyrean. Product placement, not pitching.',
        },
        {
            'name': 'Consistent content output — 5 posts/week',
            'type': 'Quarterly Goal',
            'status': 'Behind',
            'dept': 'Marketing',
            'target': '5 posts per week across all platforms',
            'current': '0 posts/week',
            'due': '2026-06-30',
            'progress': 0.0,
            'notes': 'Instagram primary. Shock value with depth. Visceral. Polarizing.',
        },
        {
            'name': 'Reach 10K followers on Instagram',
            'type': 'Key Result',
            'status': 'Not started',
            'dept': 'Marketing',
            'target': '10,000 followers',
            'current': '0',
            'due': '2026-12-31',
            'progress': 0.0,
            'notes': 'First milestone. Then 50K → 100K.',
        },
        {
            'name': 'Establish brand aesthetic — Lyfe Spectrum wardrobe',
            'type': 'Quarterly Goal',
            'status': 'In progress',
            'dept': 'Brand',
            'target': 'Full uniform/wardrobe set designed and sewn',
            'current': 'Designing — 3D modeling in progress',
            'due': '2026-06-30',
            'progress': 0.2,
            'notes': 'Wear Lyfe Spectrum in all content. Product placement like a movie.',
        },
    ]
    if goals_db:
        for g in goals:
            props = {
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
            pid = _create_page(goals_db, props)
            print(f'  {"✅" if pid else "❌"} {g["name"][:60]}')
    else:
        print('  ⚠️  Skipped — no Goals DB')

    # Roles
    roles_db = get_db_id(vid, 'roles')
    print(f'\n👥 Roles (DB: {roles_db[:8] if roles_db else "MISSING"})...')
    roles = [
        {
            'name': 'Founder — Antony F. Munoz',
            'dept': 'Leadership',
            'mode': 'Human Only',
            'authority': 'Strategic',
            'status': 'Active',
            'agent': 'Founder',
            'agent_status': '🟢 Active',
            'kpi': 'Content published / Followers',
            'kpi_value': '0 / 0',
            'responsibilities': (
                'On-camera talent, brand identity, creative direction, '
                'aesthetic decisions, lifestyle embodiment.'
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
            'kpi': 'Content calendar filled / Captions drafted',
            'kpi_value': '0 pieces',
            'responsibilities': (
                'Content calendar management, caption and hook drafting, '
                'campaign concept generation, posting schedule.'
            ),
            'soul_doc': '',
        },
        {
            'name': 'Research Agent',
            'dept': 'Research',
            'mode': 'AI Only',
            'authority': 'Execution',
            'status': 'AI-Staffed',
            'agent': 'Research Agent',
            'agent_status': '⚪ Idle',
            'kpi': 'Trend signals processed',
            'kpi_value': '0',
            'responsibilities': (
                'Trend analysis, ICP audience research, '
                'competitor content monitoring, hook library maintenance.'
            ),
            'soul_doc': '',
        },
        {
            'name': 'DEX — Executive Assistant',
            'dept': 'Operations',
            'mode': 'AI Only',
            'authority': 'Operational',
            'status': 'AI-Staffed',
            'agent': 'DEX',
            'agent_status': '⚪ Idle',
            'kpi': 'Publishing schedule adherence',
            'kpi_value': '0%',
            'responsibilities': (
                'Cross-venture coordination, '
                'publishing reminders, collaboration scheduling.'
            ),
            'soul_doc': '/opt/OS/agents/executive_assistant.md',
        },
    ]
    if roles_db:
        for r in roles:
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
            pid = _create_page(roles_db, props)
            print(f'  {"✅" if pid else "❌"} {r["name"]}')
    else:
        print('  ⚠️  Skipped — no Roles DB')

    # Metrics
    print(f'\n📊 Metrics...')
    metrics = [
        {
            'name': 'Instagram Followers',
            'value': 0, 'target': 10000,
            'unit': 'followers', 'dept': 'Marketing',
            'cat': 'Growth', 'period': 'Monthly',
            'notes': 'First milestone → 50K → 100K.',
        },
        {
            'name': 'Posts Published / Week',
            'value': 0, 'target': 5,
            'unit': 'posts', 'dept': 'Marketing',
            'cat': 'Output', 'period': 'Weekly',
            'notes': 'Consistency is the multiplier.',
        },
        {
            'name': 'Avg Reel Views',
            'value': 0, 'target': 10000,
            'unit': 'views', 'dept': 'Marketing',
            'cat': 'Reach', 'period': 'Monthly',
            'notes': 'Top-of-funnel reach indicator.',
        },
        {
            'name': 'Profile Link Clicks',
            'value': 0, 'target': 500,
            'unit': 'clicks', 'dept': 'Marketing',
            'cat': 'Conversion', 'period': 'Monthly',
            'notes': 'Content → offer intent.',
        },
        {
            'name': 'Content Calendar Fill Rate',
            'value': 0, 'target': 100,
            'unit': '%', 'dept': 'Marketing',
            'cat': 'Efficiency', 'period': 'Weekly',
            'notes': '% of planned slots with content ready.',
        },
    ]
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

    # Tools
    tools_db = get_db_id(vid, 'tools')
    print(f'\n🔧 Tools (DB: {tools_db[:8] if tools_db else "MISSING"})...')
    tools = [
        {
            'name': 'Instagram',
            'dept': 'Marketing',
            'role': 'Primary content distribution platform',
            'agent': 'Content Agent',
            'cat': 'External SaaS',
            'integration': 'Browser Agent',
            'ai_op': True,
            'desc': 'Reels, feed posts, stories. Primary platform.',
            'access': 'IG_USERNAME/IG_PASSWORD in .env. Playwright monitor.',
            'cost': 0,
        },
        {
            'name': 'Lyfe Spectrum (Shopify)',
            'dept': 'Brand',
            'role': 'Fashion / wardrobe for content',
            'agent': 'None',
            'cat': 'External SaaS',
            'integration': 'Manual',
            'ai_op': False,
            'desc': 'Tactical luxury fashion house. Worn in all content — product placement.',
            'access': 'Shopify admin. lyfe-spectrum.myshopify.com',
            'cost': 30,
        },
        {
            'name': 'CapCut / Premiere',
            'dept': 'Marketing',
            'role': 'Video editing for Reels',
            'agent': 'None',
            'cat': 'External SaaS',
            'integration': 'Manual',
            'ai_op': False,
            'desc': 'Primary video editing tools. Cinematic aesthetic.',
            'access': 'Local desktop apps',
            'cost': 0,
        },
        {
            'name': 'Apify',
            'dept': 'Research',
            'role': 'Competitor and trend analysis scraping',
            'agent': 'Research Agent',
            'cat': 'External SaaS',
            'integration': 'Direct API',
            'ai_op': True,
            'desc': 'Instagram data scraping for ICP and trend research.',
            'access': 'APIFY_API_TOKEN in .env',
            'cost': 49,
        },
        {
            'name': 'Claude (Anthropic)',
            'dept': 'Marketing',
            'role': 'Caption drafting and content ideation',
            'agent': 'Content Agent',
            'cat': 'API Integration',
            'integration': 'Direct API',
            'ai_op': True,
            'desc': 'Haiku for classification, Sonnet for generation.',
            'access': 'ANTHROPIC_API_KEY in .env',
            'cost': 0,
        },
    ]
    if tools_db:
        for t in tools:
            props = {
                'Name': _title(t['name']),
                'Department': _select(t['dept']),
                'Primary Role': _text(t['role']),
                'Agent': _select(t['agent']),
                'Category': _select(t['cat']),
                'Integration Level': _select(t['integration']),
                'Status': _select('Active'),
                'AI Operable': _checkbox(t['ai_op']),
                'Description': _text(t['desc']),
                'Access Method': _text(t['access']),
                'Cost Per Month': _number(t['cost']),
            }
            pid = _create_page(tools_db, props)
            print(f'  {"✅" if pid else "❌"} {t["name"]}')
    else:
        print('  ⚠️  Skipped — no Tools DB')

    # Documents
    print('\n📄 Documents...')
    docs = [
        {
            'title': 'Personal Brand Identity Spec',
            'type': 'Strategy',
            'dept': 'Brand',
            'content': (
                'Archetypes: Bodhi (Point Break), Bruce Wayne/Batman, Tyler Durden, '
                'Deckard (Blade Runner). Persona: Cinematic, rebellious, luxury-driven. '
                'The Architect, not the hero. Invites reclaiming authorship of own life. '
                'Aesthetic: Tactical luxury. Dark, structured, intentional. '
                'Voice: Bold, direct, authoritative mentorship. Never breaks fourth wall.'
            ),
        },
        {
            'title': 'Content Strategy — Life Maxing Framework',
            'type': 'Playbook',
            'dept': 'Marketing',
            'content': (
                'Content IS the advertising. Product placement like a movie, not a pitch. '
                'Wear Lyfe Spectrum. Use EOS products naturally. Live the brand. '
                'Style: Shock value with depth. Visceral. Polarizing and emotionally resonant. '
                'Challenges societal norms. 5 posts/week target. Instagram primary.'
            ),
        },
    ]
    for d in docs:
        pid = write_document(
            venture_id=vid,
            title=d['title'],
            doc_type=d['type'],
            department=d['dept'],
            content=d['content'],
            source='Founder',
            confidence='High',
        )
        print(f'  {"✅" if pid else "❌"} {d["title"]}')


# ── Content Calendars — all three ventures ────────

# Content calendar entries stored in the documents DB
# under type='Content Calendar'. One template entry
# per venture covers the weekly cadence and pillar structure.

_CONTENT_CALENDARS: dict[str, list[dict]] = {
    'personal_brand': [
        {
            'title': 'Content Calendar — April 2026',
            'dept': 'Marketing',
            'content': (
                'Platform: Instagram Reels + Feed.\n'
                'Cadence: 5 posts/week.\n'
                'Pillars: (1) Mindset / Life Maxing — philosophical, visceral. '
                '(2) Behind-the-build — EOS, systems, process. '
                '(3) Brand / aesthetic — Lyfe Spectrum wardrobe. '
                '(4) Proof / results — client wins, milestones. '
                '(5) Polarizing takes — challenge societal norms.\n'
                'Hook formula: Shock value + depth. Lead with the wound.\n'
                'CTA: Soft. Link in bio. Never pitch directly.'
            ),
        },
        {
            'title': 'Content Calendar — May 2026',
            'dept': 'Marketing',
            'content': (
                'Platform: Instagram Reels + Feed.\n'
                'Cadence: 5 posts/week.\n'
                'Pillars: Same as April. Introduce: first client proof content.\n'
                'New angle: Game of Lyfe teaser (if Lyfe Institute $10K hit).\n'
                'Lyfe Spectrum: Wear completed wardrobe set in all content.'
            ),
        },
    ],
    'lyfe_institute': [
        {
            'title': 'Content Calendar — April 2026',
            'dept': 'Marketing',
            'content': (
                'Platform: Instagram (organic via Personal Brand).\n'
                'Cadence: Tied to Personal Brand content — no separate channel yet.\n'
                'Pillars: (1) Initiate Arena proof — transformation stories. '
                '(2) Discipline and execution hooks. '
                '(3) Men 18-25 identity — calling out mediocrity.\n'
                'CTA: DM "Initiate" or link to Calendly booking.\n'
                'Priority: Sales calls over content volume this month.'
            ),
        },
        {
            'title': 'Content Calendar — May 2026',
            'dept': 'Marketing',
            'content': (
                'Platform: Instagram. Scale if first client closed in April.\n'
                'Cadence: Increase to dedicated Lyfe Institute content if $1K+ MRR.\n'
                'Pillars: Add student testimonials and case studies.\n'
                'New: Begin Game of Lyfe waitlist content if north star hit.'
            ),
        },
    ],
    'empyrean_creative': [
        {
            'title': 'Content Calendar — April 2026',
            'dept': 'Marketing',
            'content': (
                'Platform: None yet. Empyrean content is dormant until Phase 2.\n'
                'Phase 2 trigger: Lyfe Institute $10K MRR stable.\n'
                'Planned platforms: LinkedIn (B2B), Instagram (brand).\n'
                'Pillars (future): (1) AI infrastructure build logs. '
                '(2) EOS case studies — own companies. '
                '(3) Thought leadership — AI for founders.\n'
                'Content angle: Show the system working, not pitch it.'
            ),
        },
    ],
}


def seed_content_calendars() -> None:
    print('\n📅 Content Calendars')
    print('=' * 40)
    for venture_id, venture_name in VENTURES:
        entries = _CONTENT_CALENDARS.get(venture_id, [])
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

    seed_empyrean()
    seed_personal_brand()
    seed_content_calendars()

    print('\n✅ Seed complete')


if __name__ == '__main__':
    main()
