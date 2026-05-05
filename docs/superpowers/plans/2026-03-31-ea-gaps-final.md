# EA Gaps Final — Invoice, Docs, Personal Admin, Travel Research

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill four EA capability gaps: invoice tracking/generation, AI briefing doc creation, important dates + gift research, and travel research commands.

**Architecture:** All backend logic appended to existing Python modules (expense_tracker.py, travel_manager.py) or new focused files (doc_creator.py, personal_admin.py). Discord commands use the `@bot.command()` decorator pattern with `run_in_executor` for blocking LLM calls. Daily sync and EOD loop get non-blocking additions wired after their existing sections.

**Tech Stack:** Python 3.12, discord.py/py-cord commands extension, Neon (events table), eos_ai.model_router, eos_ai.gws_connector, ZoneInfo PDT

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `eos_ai/expense_tracker.py` | Add `create_invoice`, `get_invoices`, `get_overdue_invoices`, `generate_invoice_text`, `generate_expense_report`, `generate_budget_vs_actual` |
| Create | `eos_ai/doc_creator.py` | `create_briefing_doc`, `create_presentation_outline`, `fact_check` |
| Create | `eos_ai/personal_admin.py` | `add_important_date`, `get_upcoming_dates`, `research_gift` |
| Modify | `eos_ai/travel_manager.py` | Add `research_flights`, `research_hotels`, `research_restaurants` |
| Modify | `eos_ai/eod_closing_loop.py` | Wire overdue invoice check after purchases section |
| Modify | `eos_ai/daily_sync.py` | Add `important_dates` field to `SyncAgenda`; wire in `build_agenda` and `format_sync_message` |
| Modify | `13_Scripts/discord_bot.py` | Add 14 commands: `invoices`, `invoice`, `expensereport`, `budget`, `brief`, `board`, `investor`, `slides`, `factcheck`, `dates`, `adddate`, `gift`, `flights`, `hotels`, `restaurants` |

---

## Task 1: Extend expense_tracker.py with invoice and report functions

**Files:**
- Modify: `eos_ai/expense_tracker.py` (append after line 191)

- [ ] **Step 1: Verify current imports in expense_tracker.py**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.expense_tracker import get_monthly_summary
print('existing imports ok')
"
```
Expected: `existing imports ok`

- [ ] **Step 2: Append invoice and report functions**

Add to the end of `eos_ai/expense_tracker.py`:

```python
def create_invoice(
    client_name: str,
    client_email: str,
    items: list[dict],
    venture: str = '',
    due_days: int = 30,
    ctx=None,
) -> dict:
    """
    Create an invoice record in the events table.
    items: [{'description': str, 'amount': float, 'quantity': int}]
    Returns invoice dict with id, total, due_date.
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        from datetime import datetime, timedelta
        import uuid as _uuid
        ctx = ctx or load_context_from_env()

        invoice_id = f'INV-{datetime.now(PDT).strftime("%Y%m%d")}-{str(_uuid.uuid4())[:4].upper()}'
        total = sum(
            item.get('amount', 0) * item.get('quantity', 1)
            for item in items
        )
        due_date = (datetime.now(PDT) + timedelta(days=due_days)).strftime('%Y-%m-%d')

        invoice = {
            'invoice_id': invoice_id,
            'client_name': client_name,
            'client_email': client_email,
            'items': items,
            'total': total,
            'venture': venture,
            'status': 'unpaid',
            'due_date': due_date,
            'created_at': datetime.now(PDT).isoformat(),
        }

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'invoice',
                json.dumps(invoice),
                'dex_invoices',
            ))

        return invoice
    except Exception as e:
        logger.warning(f'[ExpenseTracker] create_invoice failed: {e}')
        return {}


def get_invoices(status: str = None, ctx=None) -> list[dict]:
    """Get invoices, optionally filtered by status."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'invoice'
                ORDER BY created_at DESC
                LIMIT 50
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        invoices = []
        for r in rows:
            p = r['payload_json']
            if isinstance(p, str):
                p = json.loads(p)
            if status is None or p.get('status') == status:
                invoices.append(p)
        return invoices
    except Exception as e:
        logger.warning(f'[ExpenseTracker] get_invoices failed: {e}')
        return []


def get_overdue_invoices(ctx=None) -> list[dict]:
    """Get unpaid invoices past due date."""
    from datetime import datetime
    invoices = get_invoices(status='unpaid', ctx=ctx)
    today = datetime.now().strftime('%Y-%m-%d')
    return [i for i in invoices if i.get('due_date', '9999') < today]


def generate_invoice_text(invoice: dict) -> str:
    """Generate plain-text invoice for sending."""
    lines = [
        f'INVOICE {invoice["invoice_id"]}',
        f'Date: {invoice["created_at"][:10]}',
        f'Due: {invoice["due_date"]}',
        '',
        f'Bill To: {invoice["client_name"]}',
        f'{invoice["client_email"]}',
        '',
        f'{"Item":<40} {"Qty":>5} {"Amount":>10}',
        '-' * 57,
    ]
    for item in invoice.get('items', []):
        desc = item.get('description', '')[:38]
        qty = item.get('quantity', 1)
        amt = item.get('amount', 0)
        lines.append(f'{desc:<40} {qty:>5} ${amt:>9.2f}')
    lines.extend([
        '-' * 57,
        f'{"TOTAL":>46} ${invoice["total"]:>9.2f}',
        '',
        f'Payment due by {invoice["due_date"]}.',
        'Thank you for your business.',
    ])
    return '\n'.join(lines)


def generate_expense_report(
    month: str = None,
    ctx=None,
) -> str:
    """
    Generate a monthly expense report as formatted text.
    month: 'YYYY-MM' format, defaults to current month.
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        from datetime import datetime
        ctx = ctx or load_context_from_env()

        if not month:
            month = datetime.now(PDT).strftime('%Y-%m')

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'expense'
                AND to_char(created_at AT TIME ZONE 'America/Los_Angeles',
                    'YYYY-MM') = %s
                ORDER BY created_at ASC
            ''', (str(ctx.org_id), month))
            rows = cur.fetchall()

        expenses = []
        total = 0.0
        by_category: dict = {}

        for r in rows:
            p = r['payload_json']
            if isinstance(p, str):
                p = json.loads(p)
            amount = float(p.get('amount', 0))
            cat = p.get('category', 'Other')
            total += amount
            by_category[cat] = by_category.get(cat, 0) + amount
            expenses.append(p)

        lines = [
            f'EXPENSE REPORT — {month}',
            f'Generated: {datetime.now(PDT).strftime("%Y-%m-%d")}',
            '',
            f'{"Date":<12} {"Vendor":<25} {"Category":<20} {"Amount":>10}',
            '-' * 70,
        ]

        for e in expenses:
            date = e.get('filed_at', e.get('date', ''))[:10]
            vendor = e.get('vendor', 'Unknown')[:23]
            cat = e.get('category', 'Other')[:18]
            amt = float(e.get('amount', 0))
            lines.append(f'{date:<12} {vendor:<25} {cat:<20} ${amt:>9.2f}')

        lines.extend([
            '-' * 70,
            '',
            'SUMMARY BY CATEGORY:',
        ])
        for cat, amt in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
            lines.append(f'  {cat:<30} ${amt:>9.2f}')

        lines.extend([
            '-' * 40,
            f'  {"TOTAL":<30} ${total:>9.2f}',
        ])

        return '\n'.join(lines)
    except Exception as e:
        logger.warning(f'[ExpenseTracker] generate_expense_report failed: {e}')
        return f'Expense report unavailable: {e}'


def generate_budget_vs_actual(
    revenue_target: float,
    month: str = None,
    ctx=None,
) -> str:
    """Generate a budget vs actual report."""
    try:
        from datetime import datetime
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        if not month:
            month = datetime.now(PDT).strftime('%Y-%m')

        summary = get_monthly_summary(ctx)
        total_expenses = summary.get('total', 0)

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT COALESCE(SUM(
                    (payload_json->>'amount')::float
                ), 0) as total_revenue
                FROM events
                WHERE org_id = %s
                AND event_type IN ('revenue', 'payment_received')
                AND to_char(created_at AT TIME ZONE 'America/Los_Angeles',
                    'YYYY-MM') = %s
            ''', (str(ctx.org_id), month))
            row = cur.fetchone()
            actual_revenue = float(row['total_revenue']) if row else 0

        net = actual_revenue - total_expenses
        variance = actual_revenue - revenue_target

        lines = [
            f'BUDGET VS ACTUAL — {month}',
            '',
            f'{"Metric":<30} {"Target":>12} {"Actual":>12} {"Variance":>12}',
            '-' * 68,
            f'{"Revenue":<30} ${revenue_target:>11,.2f} ${actual_revenue:>11,.2f} ${variance:>+11,.2f}',
            f'{"Expenses":<30} {"—":>12} ${total_expenses:>11,.2f} {"":>12}',
            f'{"Net":<30} {"—":>12} ${net:>11,.2f} {"":>12}',
            '-' * 68,
        ]

        if variance >= 0:
            lines.append(f'Revenue on target (+${variance:,.2f})')
        else:
            lines.append(f'Revenue below target (${abs(variance):,.2f} short)')

        return '\n'.join(lines)
    except Exception as e:
        return f'Budget report unavailable: {e}'
```

- [ ] **Step 3: Verify imports**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.expense_tracker import (
    create_invoice, get_invoices, get_overdue_invoices,
    generate_invoice_text, generate_expense_report, generate_budget_vs_actual,
)
print('all imports ok')
"
```
Expected: `all imports ok`

- [ ] **Step 4: Smoke test invoice creation**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.expense_tracker import create_invoice, generate_invoice_text
inv = create_invoice(
    client_name='Test Client',
    client_email='test@test.com',
    items=[{'description': 'AI Setup', 'amount': 5000.0, 'quantity': 1}],
    venture='empyrean_creative',
)
print(f'Invoice ID: {inv[\"invoice_id\"]}')
print(f'Total: \${inv[\"total\"]}')
print(f'Due: {inv[\"due_date\"]}')
text = generate_invoice_text(inv)
print(text[:200])
"
```
Expected: Invoice ID starts with `INV-`, total is `5000.0`

- [ ] **Step 5: Commit**

```bash
cd /opt/OS
git add eos_ai/expense_tracker.py
git commit -m "feat: add invoice tracking and expense reporting to expense_tracker"
```

---

## Task 2: Create doc_creator.py

**Files:**
- Create: `eos_ai/doc_creator.py`

- [ ] **Step 1: Create the file**

Create `/opt/OS/eos_ai/doc_creator.py`:

```python
"""
Document Creator — generates briefing docs, board updates,
investor updates, proposals, and presentation outlines using
LLM + Google Drive.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv('/opt/OS/eos_ai/.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def create_briefing_doc(
    title: str,
    topic: str,
    context: str = '',
    audience: str = 'Antony',
    doc_type: str = 'briefing',
    ctx=None,
) -> dict:
    """
    Generate a briefing document using LLM and save to Google Drive.
    doc_type: briefing | board_update | investor_update | proposal
    Returns dict with content, drive_file, title, type.
    """
    try:
        from eos_ai.model_router import get_router, TaskType
        from eos_ai.gws_connector import GWSConnector
        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        templates = {
            'briefing': f"""Create a concise executive briefing document.

Title: {title}
Topic: {topic}
Context: {context}
Audience: {audience}

Format:
# {title}
**Date:** {datetime.now(PDT).strftime('%B %d, %Y')}
**Prepared by:** DEX

## Executive Summary
[2-3 sentence summary]

## Background
[Context and relevance]

## Key Points
[3-5 bullet points]

## Recommendations
[1-3 specific actions]

## Next Steps
[What needs to happen and by when]

Keep it under 400 words. Direct. No fluff.""",

            'board_update': f"""Create a board update document.

Company context: Munoz Conglomerate — Lyfe Institute,
Empyrean Creative, Personal Brand
Topic: {topic}
Context: {context}

Format:
# Board Update — {datetime.now(PDT).strftime('%B %Y')}

## Performance Highlights
[Key metrics and wins]

## Portfolio Status
[Each venture: status, revenue, key metric]

## Challenges & Risks
[Top 3 challenges]

## Strategic Priorities
[Next 90 days focus]

## Asks from the Board
[What support is needed]

Keep it under 500 words. Numbers over narrative.""",

            'investor_update': f"""Create a monthly investor update.

Context: {context}
Topic: {topic}

Format:
# Investor Update — {datetime.now(PDT).strftime('%B %Y')}

## The One-Line Summary
[What happened this month in one sentence]

## Progress
[What moved forward]

## Revenue
[Numbers]

## Key Learnings
[What you learned]

## Ask
[What you need from investors/network]

## Next Month
[What you're focused on]

Keep it conversational and honest. Under 400 words.""",

            'proposal': f"""Create a business proposal.

Title: {title}
Topic: {topic}
Context: {context}
Audience: {audience}

Format:
# {title}

## The Situation
[Problem or opportunity]

## Our Solution
[What we're proposing]

## How It Works
[Process/approach]

## Investment
[Pricing and terms]

## Why Us
[Credibility and fit]

## Next Steps
[Call to action]

Keep it under 500 words. Client-facing quality.""",
        }

        prompt = templates.get(doc_type, templates['briefing'])
        content = router.call(model, prompt).strip()

        # Save to Google Drive
        gws = GWSConnector()
        drive_result = gws.create_document(
            title=f'{title} — {datetime.now(PDT).strftime("%Y-%m-%d")}',
            content=content,
        )

        # Log to Neon
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
                    'document_created',
                    json.dumps({
                        'title': title,
                        'type': doc_type,
                        'drive_id': drive_result.get('id', ''),
                        'created_at': datetime.now(PDT).isoformat(),
                    }),
                    'dex_doc_creator',
                ))
        except Exception:
            pass

        return {
            'content': content,
            'drive_file': drive_result,
            'title': title,
            'type': doc_type,
        }
    except Exception as e:
        logger.warning(f'[DocCreator] create_briefing_doc failed: {e}')
        return {'content': '', 'error': str(e)}


def create_presentation_outline(
    title: str,
    topic: str,
    slides: int = 10,
    audience: str = '',
    ctx=None,
) -> dict:
    """
    Generate a presentation outline with slide content.
    Returns dict with slides (structured data) and drive_file.
    """
    try:
        from eos_ai.model_router import get_router, TaskType
        from eos_ai.gws_connector import GWSConnector
        import json as _json
        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        raw = router.call(model, f"""Create a {slides}-slide presentation outline.

Title: {title}
Topic: {topic}
Audience: {audience or 'Business audience'}

For each slide provide:
- Slide number
- Title
- Key message (one sentence)
- 3 bullet points max
- Speaker note (what to say)

Format as JSON:
{{
  "presentation_title": "{title}",
  "slides": [
    {{
      "number": 1,
      "title": "slide title",
      "key_message": "one sentence",
      "bullets": ["point 1", "point 2", "point 3"],
      "speaker_note": "what to say"
    }}
  ]
}}""").strip()

        if '```' in raw:
            raw = raw.split('```')[1].replace('json', '').strip()

        slides_data = _json.loads(raw)

        # Build doc content for Drive
        doc_content = f'# {title}\n\n'
        for slide in slides_data.get('slides', []):
            doc_content += f'## Slide {slide["number"]}: {slide["title"]}\n'
            doc_content += f'**Key message:** {slide["key_message"]}\n\n'
            for bullet in slide.get('bullets', []):
                doc_content += f'- {bullet}\n'
            doc_content += f'\n*Speaker note: {slide.get("speaker_note", "")}*\n\n'

        gws = GWSConnector()
        drive_result = gws.create_document(
            title=f'{title} — Presentation Outline',
            content=doc_content,
        )

        return {
            'slides': slides_data,
            'drive_file': drive_result,
            'slide_count': len(slides_data.get('slides', [])),
        }
    except Exception as e:
        logger.warning(f'[DocCreator] create_presentation_outline failed: {e}')
        return {'slides': {}, 'error': str(e)}


def fact_check(claim: str, ctx=None) -> dict:
    """
    Fact-check a claim using LLM knowledge.
    Returns dict with verdict, explanation, confidence, verify.
    """
    try:
        from eos_ai.model_router import get_router, TaskType
        import json as _json
        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        raw = router.call(model, f"""Fact-check this claim.

Claim: {claim}

Return JSON only:
{{"verdict": "TRUE|FALSE|PARTIALLY TRUE|UNVERIFIABLE",
  "explanation": "why",
  "confidence": "high|medium|low",
  "verify": ["thing to check 1", "thing to check 2"]}}""").strip()

        if '```' in raw:
            raw = raw.split('```')[1].replace('json', '').strip()
        return _json.loads(raw)
    except Exception as e:
        return {'verdict': 'UNVERIFIABLE', 'explanation': str(e), 'confidence': 'low', 'verify': []}
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.doc_creator import create_briefing_doc, create_presentation_outline, fact_check
print('doc_creator imports ok')
"
```
Expected: `doc_creator imports ok`

- [ ] **Step 3: Smoke test fact_check (no LLM call needed to test signature)**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.doc_creator import fact_check
result = fact_check('The Earth is 4.5 billion years old')
print(f'Verdict: {result[\"verdict\"]} ({result[\"confidence\"]})')
print(f'Keys present: {list(result.keys())}')
"
```
Expected: Verdict is TRUE or UNVERIFIABLE; keys include `verdict`, `explanation`, `confidence`, `verify`

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add eos_ai/doc_creator.py
git commit -m "feat: add doc_creator module for briefings, presentations, fact-check"
```

---

## Task 3: Create personal_admin.py

**Files:**
- Create: `eos_ai/personal_admin.py`

- [ ] **Step 1: Create the file**

Create `/opt/OS/eos_ai/personal_admin.py`:

```python
"""
Personal Admin — important dates, gift research,
and personal appointment management.
"""

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv('/opt/OS/eos_ai/.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def add_important_date(
    person: str,
    date: str,
    date_type: str,
    notes: str = '',
    ctx=None,
) -> bool:
    """
    Add an important date to the events table.
    date_type: birthday | anniversary | work_anniversary | other
    date format: MM-DD (recurring yearly) or YYYY-MM-DD (one-time)
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
                'important_date',
                json.dumps({
                    'person': person,
                    'date': date,
                    'type': date_type,
                    'notes': notes,
                    'added_at': datetime.now(PDT).isoformat(),
                }),
                'dex_personal',
            ))
        return True
    except Exception as e:
        logger.warning(f'[PersonalAdmin] add_important_date failed: {e}')
        return False


def get_upcoming_dates(days: int = 30, ctx=None) -> list[dict]:
    """Get important dates coming up in the next N days, sorted by days_until."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'important_date'
                ORDER BY created_at DESC
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        now = datetime.now(PDT)
        upcoming = []
        for r in rows:
            p = r['payload_json']
            if isinstance(p, str):
                p = json.loads(p)
            date_str = p.get('date', '')
            if not date_str:
                continue
            try:
                # MM-DD recurring
                if len(date_str) == 5 and '-' in date_str:
                    month, day = date_str.split('-')
                    candidate = now.replace(month=int(month), day=int(day),
                                            hour=0, minute=0, second=0, microsecond=0)
                    if candidate.date() < now.date():
                        candidate = candidate.replace(year=now.year + 1)
                    days_until = (candidate.date() - now.date()).days
                else:
                    target = datetime.fromisoformat(date_str).replace(tzinfo=PDT)
                    days_until = (target.date() - now.date()).days

                if 0 <= days_until <= days:
                    p['days_until'] = days_until
                    upcoming.append(p)
            except Exception:
                continue

        return sorted(upcoming, key=lambda x: x.get('days_until', 99))
    except Exception as e:
        logger.warning(f'[PersonalAdmin] get_upcoming_dates failed: {e}')
        return []


def research_gift(
    person: str,
    occasion: str,
    budget: float = 100,
    context: str = '',
) -> str:
    """
    Research gift ideas for a person and occasion.
    Returns formatted list of 5 specific gift suggestions.
    """
    try:
        from eos_ai.model_router import get_router, TaskType
        from eos_ai.person_recognition import build_intelligence_profile
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        try:
            profile = build_intelligence_profile(name=person)
            person_context = profile.notes or context or 'No specific context available'
        except Exception:
            person_context = context or 'No specific context available'

        return router.call(model, f"""Research gift ideas.

Person: {person}
Occasion: {occasion}
Budget: ${budget}
What I know about them: {person_context}

Suggest 5 specific, thoughtful gift ideas.
For each: name, why it fits, approximate price, where to get it.
Prioritize personalized over generic.
Match the budget closely.

Format as a numbered list.""").strip()
    except Exception as e:
        return f'Gift research unavailable: {e}'
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.personal_admin import add_important_date, get_upcoming_dates, research_gift
print('personal_admin imports ok')
"
```
Expected: `personal_admin imports ok`

- [ ] **Step 3: Smoke test add and retrieve**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.personal_admin import add_important_date, get_upcoming_dates
# Add a date coming up soon (use a month/day near today)
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
soon = (datetime.now(ZoneInfo('America/Los_Angeles')) + timedelta(days=5))
test_date = soon.strftime('%m-%d')
ok = add_important_date('Test Person', test_date, 'birthday', 'test entry')
print(f'Add: {ok}')
upcoming = get_upcoming_dates(days=30)
print(f'Upcoming count: {len(upcoming)}')
if upcoming:
    print(f'First: {upcoming[0][\"person\"]} in {upcoming[0][\"days_until\"]} days')
"
```
Expected: `Add: True`, upcoming count >= 1

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add eos_ai/personal_admin.py
git commit -m "feat: add personal_admin module for important dates and gift research"
```

---

## Task 4: Extend travel_manager.py with research functions

**Files:**
- Modify: `eos_ai/travel_manager.py` (append after line 136)

- [ ] **Step 1: Append three research functions**

Add to the end of `eos_ai/travel_manager.py`:

```python
def research_flights(
    origin: str,
    destination: str,
    date: str,
    return_date: str = '',
) -> str:
    """Research flight options (informational — no booking)."""
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        return router.call(model, f"""Research flight options.

From: {origin}
To: {destination}
Date: {date}
Return: {return_date or 'One way'}

Provide:
1. Typical airlines serving this route
2. Estimated flight duration
3. Typical price range
4. Best booking sites (Google Flights, Kayak, etc.)
5. Tips for this specific route
6. Recommended booking timeline

Note: This is research to help Antony make the booking.
Be specific and practical.""").strip()
    except Exception as e:
        return f'Flight research unavailable: {e}'


def research_hotels(
    city: str,
    check_in: str,
    check_out: str,
    budget_per_night: float = 200,
    preferences: str = '',
) -> str:
    """Research hotel options (informational — no booking)."""
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        return router.call(model, f"""Research hotel options.

City: {city}
Check-in: {check_in}
Check-out: {check_out}
Budget: ${budget_per_night}/night
Preferences: {preferences or 'Business travel, good location, reliable WiFi'}

Provide:
1. 3-4 specific hotel recommendations with names
2. Neighborhood recommendations
3. What to avoid
4. Booking tips for this city
5. Price range to expect

Note: Research only — Antony makes the final booking.""").strip()
    except Exception as e:
        return f'Hotel research unavailable: {e}'


def research_restaurants(
    city: str,
    occasion: str = 'business dinner',
    budget: str = 'moderate',
    dietary: str = '',
) -> str:
    """Research restaurant options for a city and occasion."""
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        return router.call(model, f"""Research restaurant options.

City: {city}
Occasion: {occasion}
Budget: {budget}
Dietary needs: {dietary or 'None specified'}

Recommend 4-5 specific restaurants with:
- Name and neighborhood
- Why it fits this occasion
- Price range
- Must-order dishes
- Reservation tips

Be specific with real restaurant names.""").strip()
    except Exception as e:
        return f'Restaurant research unavailable: {e}'
```

- [ ] **Step 2: Verify imports**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.travel_manager import (
    research_flights, research_hotels, research_restaurants,
    build_travel_brief, log_trip,
)
print('travel_manager imports ok')
"
```
Expected: `travel_manager imports ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add eos_ai/travel_manager.py
git commit -m "feat: add flight, hotel, restaurant research to travel_manager"
```

---

## Task 5: Wire overdue invoices into EOD closing loop

**Files:**
- Modify: `eos_ai/eod_closing_loop.py`

The spec says to add an overdue invoice section after the purchases section. In `eod_closing_loop.py`, the purchases section ends around line 59: `sections.append('\n'.join(section))`. Add the new block immediately after.

- [ ] **Step 1: Add overdue invoice section after purchases in `run()`**

In `eos_ai/eod_closing_loop.py`, find this block (lines 53–59):

```python
        # ── Purchases / expenses ──────────────────────────────────────────
        purchases = self._get_todays_purchases()
        if purchases:
            section = ['**Purchases/expenses:**']
            for p in purchases:
                section.append(f'  • {p}')
            sections.append('\n'.join(section))
```

Add immediately after it:

```python
        # ── Overdue invoice check ─────────────────────────────────────────
        try:
            from eos_ai.expense_tracker import get_overdue_invoices
            overdue = get_overdue_invoices()
            if overdue:
                section = [f'**🔴 Overdue invoices ({len(overdue)}):**']
                for inv in overdue[:3]:
                    section.append(
                        f'  • {inv["invoice_id"]} — '
                        f'{inv["client_name"]} — '
                        f'${inv["total"]:,.2f}'
                    )
                sections.append('\n'.join(section))
        except Exception:
            pass
```

- [ ] **Step 2: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.eod_closing_loop import EODClosingLoop
from eos_ai.context import load_context_from_env
ctx = load_context_from_env()
eod = EODClosingLoop(ctx)
print('eod_closing_loop import ok')
"
```
Expected: `eod_closing_loop import ok`

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add eos_ai/eod_closing_loop.py
git commit -m "feat: wire overdue invoice check into EOD closing loop"
```

---

## Task 6: Wire important dates into daily sync

**Files:**
- Modify: `eos_ai/daily_sync.py`

- [ ] **Step 1: Add `important_dates` field to `SyncAgenda`**

In `daily_sync.py`, find this line in the `SyncAgenda` dataclass (line 38):

```python
    quarterly_rocks: list = field(default_factory=list)  # from preloaded year
```

Add immediately after:

```python
    important_dates: list = field(default_factory=list)  # upcoming personal dates
```

- [ ] **Step 2: Wire important_dates into `build_agenda()` after subscription_alerts**

In `daily_sync.py`, find the end of the subscription renewals block (around line 442–443):

```python
        except Exception:
            pass

        return agenda
```

Add before `return agenda`:

```python
        # ── Upcoming important dates (next 14 days) ──────────────────────
        try:
            from eos_ai.personal_admin import get_upcoming_dates
            upcoming = get_upcoming_dates(days=14, ctx=self.ctx)
            if upcoming:
                agenda.important_dates = [
                    f'{d["person"]} — {d["type"]} in {d["days_until"]} days'
                    for d in upcoming[:3]
                ]
            else:
                agenda.important_dates = []
        except Exception:
            agenda.important_dates = []
```

- [ ] **Step 3: Render important_dates in `format_sync_message()`**

In `daily_sync.py`, find the subscription renewal alerts block in `format_sync_message()` (around line 547):

```python
        # Subscription renewal alerts
        if agenda.subscription_alerts:
            lines.append('**💳 Renewals this week:**')
            for alert in agenda.subscription_alerts:
                lines.append(f'  {alert}')
            lines.append('')
```

Add immediately after that block (before the closing lines):

```python
        # Important dates
        if agenda.important_dates:
            lines.append('**🗓️ Coming up:**')
            for d in agenda.important_dates:
                lines.append(f'  • {d}')
            lines.append('')
```

- [ ] **Step 4: Verify import**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.daily_sync import DailySync, SyncAgenda
a = SyncAgenda(date='test')
print(f'important_dates field exists: {hasattr(a, \"important_dates\")}')
print(f'default: {a.important_dates}')
"
```
Expected: `important_dates field exists: True`, `default: []`

- [ ] **Step 5: Commit**

```bash
cd /opt/OS
git add eos_ai/daily_sync.py
git commit -m "feat: wire important dates into daily sync morning brief"
```

---

## Task 7: Add invoice Discord commands

**Files:**
- Modify: `13_Scripts/discord_bot.py` (append new `@bot.command` blocks before the final `bot.run()` call)

Commands to add: `invoices`, `invoice`, `expensereport`, `budget`

- [ ] **Step 1: Find insertion point**

```bash
grep -n "^bot.run\|@bot.event" /opt/OS/13_Scripts/discord_bot.py | tail -5
```
Note the line number of `bot.run(...)`. New commands go before it.

- [ ] **Step 2: Add four invoice commands before `bot.run()`**

```python
@bot.command(name='invoices')
async def cmd_invoices(ctx: commands.Context):
    """List invoices. Usage: !invoices"""
    def _run():
        try:
            from eos_ai.expense_tracker import get_invoices, get_overdue_invoices
            all_inv = get_invoices()
            overdue = get_overdue_invoices()
            if not all_inv:
                return (
                    '📄 No invoices yet.\n'
                    'Create one: `!invoice [client] | [email] | [description] | [amount]`'
                )
            overdue_ids = {i.get('invoice_id') for i in overdue}
            lines = [f'📄 **Invoices ({len(all_inv)}):**']
            for inv in all_inv[:8]:
                if inv.get('invoice_id') in overdue_ids:
                    status_emoji = '🔴'
                elif inv.get('status') == 'unpaid':
                    status_emoji = '🟡'
                else:
                    status_emoji = '✅'
                lines.append(
                    f'{status_emoji} {inv["invoice_id"]} — '
                    f'{inv["client_name"]} — '
                    f'${inv["total"]:,.2f} — '
                    f'due {inv["due_date"]}'
                )
            if overdue:
                lines.append(f'\n🔴 {len(overdue)} overdue')
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='invoice')
async def cmd_invoice(ctx: commands.Context, *, args: str = ''):
    """Create an invoice. Usage: !invoice [client] | [email] | [description] | [amount]"""
    if '|' not in args:
        await ctx.reply(
            'Usage: `!invoice [client name] | [email] | [description] | [amount]`\n'
            'Example: `!invoice Acme Corp | billing@acme.com | AI Setup | 5000`'
        )
        return

    def _run():
        try:
            from eos_ai.expense_tracker import create_invoice, generate_invoice_text
            parts = [p.strip() for p in args.split('|')]
            inv = create_invoice(
                client_name=parts[0],
                client_email=parts[1],
                items=[{
                    'description': parts[2],
                    'amount': float(parts[3]),
                    'quantity': 1,
                }],
            )
            if inv:
                text = generate_invoice_text(inv)
                return (
                    f'📄 **Invoice created: {inv["invoice_id"]}**\n'
                    f'```\n{text[:800]}\n```\n'
                    f'Total: ${inv["total"]:,.2f} — Due: {inv["due_date"]}'
                )
            return '❌ Failed to create invoice.'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply('📄 Creating invoice...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.channel.send(output)


@bot.command(name='expensereport')
async def cmd_expensereport(ctx: commands.Context, month: str = ''):
    """Generate monthly expense report. Usage: !expensereport [YYYY-MM optional]"""
    def _run():
        try:
            from eos_ai.expense_tracker import generate_expense_report
            return generate_expense_report(month or None)
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, _run)
    await ctx.reply(f'📊 **Expense Report:**\n```\n{report[:1800]}\n```')


@bot.command(name='budget')
async def cmd_budget(ctx: commands.Context, target: str = '10000'):
    """Budget vs actual report. Usage: !budget [revenue target optional, default 10000]"""
    def _run():
        try:
            from eos_ai.expense_tracker import generate_budget_vs_actual
            t = float(target.replace('$', '').replace(',', ''))
            return generate_budget_vs_actual(revenue_target=t)
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(None, _run)
    await ctx.reply(f'📊 **Budget vs Actual:**\n```\n{report}\n```')
```

- [ ] **Step 3: Verify no syntax errors**

```bash
python3 -c "
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f:
    ast.parse(f.read())
print('syntax ok')
"
```
Expected: `syntax ok`

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add 13_Scripts/discord_bot.py
git commit -m "feat: add invoices, invoice, expensereport, budget discord commands"
```

---

## Task 8: Add doc/brief/slides/factcheck Discord commands

**Files:**
- Modify: `13_Scripts/discord_bot.py` (append before `bot.run()`)

Commands: `brief_doc`, `board`, `investor`, `slides`, `factcheck`

Note: `brief` is already taken (`cmd_brief` at line 2085 is the morning brief command). Use `brief_doc` instead.

- [ ] **Step 1: Verify `brief` command name is taken**

```bash
grep -n "name='brief'" /opt/OS/13_Scripts/discord_bot.py
```
If `name='brief'` exists, use `name='briefdoc'` for the new command.

- [ ] **Step 2: Add five doc commands before `bot.run()`**

```python
@bot.command(name='briefdoc')
async def cmd_briefdoc(ctx: commands.Context, *, args: str = ''):
    """Create a briefing doc. Usage: !briefdoc [title] | [topic] | [context optional]"""
    if not args:
        await ctx.reply(
            'Usage: `!briefdoc [title] | [topic] | [context optional]`\n'
            'Example: `!briefdoc Q2 Strategy | Revenue acceleration | Focus on Initiate Arena`'
        )
        return

    def _run():
        try:
            from eos_ai.doc_creator import create_briefing_doc
            parts = [p.strip() for p in args.split('|')]
            title = parts[0]
            topic = parts[1] if len(parts) > 1 else title
            context = parts[2] if len(parts) > 2 else ''
            result = create_briefing_doc(title, topic, context)
            if result.get('content'):
                preview = result['content'][:800]
                drive_id = result.get('drive_file', {}).get('id', '')
                out = f'📝 **Briefing: {title}**\n```\n{preview}\n```'
                if drive_id:
                    out += f'\n📁 Drive: `{drive_id}`'
                return out
            return f'❌ Failed: {result.get("error")}'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply('📝 Creating briefing doc...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    for chunk in [output[i:i+1900] for i in range(0, len(output), 1900)]:
        await ctx.channel.send(chunk)


@bot.command(name='board')
async def cmd_board(ctx: commands.Context, *, args: str = ''):
    """Generate board update doc. Usage: !board [extra context optional]"""
    def _run():
        try:
            from eos_ai.doc_creator import create_briefing_doc
            from eos_ai.portfolio_agent import PortfolioAgent
            from eos_ai.context import load_context_from_env
            ctx_eos = load_context_from_env()
            pa = PortfolioAgent(ctx_eos)
            ventures = pa.scan_all_ventures()
            portfolio_context = pa.generate_portfolio_brief(ventures)
            result = create_briefing_doc(
                title='Board Update',
                topic='Monthly portfolio review',
                context=portfolio_context + ('\n' + args if args else ''),
                doc_type='board_update',
            )
            if result.get('content'):
                return f'📋 **Board Update:**\n```\n{result["content"][:1200]}\n```'
            return '❌ Failed to generate.'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply('📋 Generating board update...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    for chunk in [output[i:i+1900] for i in range(0, len(output), 1900)]:
        await ctx.channel.send(chunk)


@bot.command(name='investor')
async def cmd_investor(ctx: commands.Context, *, args: str = ''):
    """Generate investor update. Usage: !investor [context optional]"""
    def _run():
        try:
            from eos_ai.doc_creator import create_briefing_doc
            result = create_briefing_doc(
                title='Investor Update',
                topic='Monthly progress update',
                context=args,
                doc_type='investor_update',
            )
            if result.get('content'):
                return (
                    f'📊 **Investor Update:**\n'
                    f'```\n{result["content"][:1200]}\n```'
                )
            return '❌ Failed to generate.'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply('📊 Generating investor update...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    for chunk in [output[i:i+1900] for i in range(0, len(output), 1900)]:
        await ctx.channel.send(chunk)


@bot.command(name='slides')
async def cmd_slides(ctx: commands.Context, *, args: str = ''):
    """Generate presentation outline. Usage: !slides [title] | [topic] | [slide count optional]"""
    if not args:
        await ctx.reply(
            'Usage: `!slides [title] | [topic] | [slide count optional]`\n'
            'Example: `!slides Initiate Arena Pitch | Why men need structure | 10`'
        )
        return

    def _run():
        try:
            from eos_ai.doc_creator import create_presentation_outline
            parts = [p.strip() for p in args.split('|')]
            title = parts[0]
            topic = parts[1] if len(parts) > 1 else title
            count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10
            result = create_presentation_outline(title, topic, count)
            slides = result.get('slides', {}).get('slides', [])
            if slides:
                lines = [f'📊 **{title} — {len(slides)} slides:**']
                for s in slides[:5]:
                    lines.append(f'{s["number"]}. **{s["title"]}** — {s["key_message"]}')
                if len(slides) > 5:
                    lines.append(f'... and {len(slides)-5} more slides')
                drive_id = result.get('drive_file', {}).get('id', '')
                if drive_id:
                    lines.append(f'\n📁 Full outline saved to Drive: `{drive_id}`')
                return '\n'.join(lines)
            return f'❌ Failed: {result.get("error")}'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply(f'📊 Creating presentation outline...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.channel.send(output)


@bot.command(name='factcheck')
async def cmd_factcheck(ctx: commands.Context, *, claim: str = ''):
    """Fact-check a claim. Usage: !factcheck [claim]"""
    if not claim:
        await ctx.reply('Usage: `!factcheck [claim to verify]`')
        return

    def _run():
        try:
            from eos_ai.doc_creator import fact_check
            result = fact_check(claim)
            verdict_emoji = {
                'TRUE': '✅',
                'FALSE': '❌',
                'PARTIALLY TRUE': '⚠️',
                'UNVERIFIABLE': '❓',
            }.get(result.get('verdict', ''), '❓')
            return (
                f'{verdict_emoji} **{result["verdict"]}** '
                f'(confidence: {result["confidence"]})\n'
                f'{result["explanation"]}'
            )
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)
```

- [ ] **Step 3: Verify syntax**

```bash
python3 -c "
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f:
    ast.parse(f.read())
print('syntax ok')
"
```

- [ ] **Step 4: Commit**

```bash
cd /opt/OS
git add 13_Scripts/discord_bot.py
git commit -m "feat: add briefdoc, board, investor, slides, factcheck discord commands"
```

---

## Task 9: Add personal admin Discord commands

**Files:**
- Modify: `13_Scripts/discord_bot.py` (append before `bot.run()`)

Commands: `dates`, `adddate`, `gift`

- [ ] **Step 1: Add three personal admin commands before `bot.run()`**

```python
@bot.command(name='dates')
async def cmd_dates(ctx: commands.Context):
    """List upcoming important dates (60 days). Usage: !dates"""
    def _run():
        try:
            from eos_ai.personal_admin import get_upcoming_dates
            dates = get_upcoming_dates(days=60)
            if not dates:
                return (
                    '📅 No important dates tracked yet.\n'
                    'Add with: `!adddate [person] | [MM-DD or YYYY-MM-DD] | [type]`\n'
                    'Types: birthday, anniversary, work_anniversary, other'
                )
            lines = ['📅 **Upcoming important dates (60 days):**']
            for d in dates:
                days_until = d.get('days_until', '?')
                if isinstance(days_until, int):
                    urgency = '🔴' if days_until <= 7 else '🟡' if days_until <= 14 else '🔵'
                else:
                    urgency = '🔵'
                lines.append(
                    f'{urgency} {d["person"]} — {d["type"]} — '
                    f'in {days_until} days ({d["date"]})'
                )
                if d.get('notes'):
                    lines.append(f'   _{d["notes"]}_')
            return '\n'.join(lines)
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='adddate')
async def cmd_adddate(ctx: commands.Context, *, args: str = ''):
    """Add an important date. Usage: !adddate [person] | [MM-DD] | [type] | [notes optional]"""
    if '|' not in args:
        await ctx.reply(
            'Usage: `!adddate [person] | [MM-DD or YYYY-MM-DD] | [type] | [notes optional]`\n'
            'Types: birthday, anniversary, work_anniversary, other\n'
            'Example: `!adddate Mom | 06-15 | birthday | Get flowers`'
        )
        return

    def _run():
        try:
            from eos_ai.personal_admin import add_important_date
            parts = [p.strip() for p in args.split('|')]
            ok = add_important_date(
                person=parts[0],
                date=parts[1],
                date_type=parts[2],
                notes=parts[3] if len(parts) > 3 else '',
            )
            if ok:
                return f'📅 Date added: **{parts[0]}** — {parts[2]} on {parts[1]}'
            return '❌ Failed to add date.'
        except Exception as e:
            return f'❌ Error: {e}'

    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    await ctx.reply(output)


@bot.command(name='gift')
async def cmd_gift(ctx: commands.Context, *, args: str = ''):
    """Research gift ideas. Usage: !gift [person] | [occasion] | [budget optional]"""
    if '|' not in args:
        await ctx.reply(
            'Usage: `!gift [person] | [occasion] | [budget optional]`\n'
            'Example: `!gift Mom | birthday | 150`'
        )
        return

    def _run():
        try:
            from eos_ai.personal_admin import research_gift
            parts = [p.strip() for p in args.split('|')]
            person = parts[0]
            occasion = parts[1] if len(parts) > 1 else 'birthday'
            budget = float(parts[2].replace('$', '')) if len(parts) > 2 else 100
            ideas = research_gift(person, occasion, budget)
            return f'🎁 **Gift ideas for {person} — {occasion}:**\n{ideas[:1500]}'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply(f'🎁 Researching gifts...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    for chunk in [output[i:i+1900] for i in range(0, len(output), 1900)]:
        await ctx.channel.send(chunk)
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f:
    ast.parse(f.read())
print('syntax ok')
"
```

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add 13_Scripts/discord_bot.py
git commit -m "feat: add dates, adddate, gift discord commands"
```

---

## Task 10: Add travel research Discord commands

**Files:**
- Modify: `13_Scripts/discord_bot.py` (append before `bot.run()`)

Commands: `flights`, `hotels`, `restaurants`

- [ ] **Step 1: Add three travel research commands before `bot.run()`**

```python
@bot.command(name='flights')
async def cmd_flights(ctx: commands.Context, *, args: str = ''):
    """Research flights. Usage: !flights [from] | [to] | [date] | [return date optional]"""
    if '|' not in args:
        await ctx.reply(
            'Usage: `!flights [from] | [to] | [date] | [return date optional]`\n'
            'Example: `!flights Portland | San Francisco | 2026-04-15 | 2026-04-17`'
        )
        return

    def _run():
        try:
            from eos_ai.travel_manager import research_flights
            parts = [p.strip() for p in args.split('|')]
            result = research_flights(
                origin=parts[0],
                destination=parts[1],
                date=parts[2] if len(parts) > 2 else '',
                return_date=parts[3] if len(parts) > 3 else '',
            )
            return f'✈️ **Flight research — {parts[0]} → {parts[1]}:**\n{result}'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply('✈️ Researching flights...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    for chunk in [output[i:i+1900] for i in range(0, len(output), 1900)]:
        await ctx.channel.send(chunk)


@bot.command(name='hotels')
async def cmd_hotels(ctx: commands.Context, *, args: str = ''):
    """Research hotels. Usage: !hotels [city] | [check-in] | [check-out] | [budget/night optional]"""
    if '|' not in args:
        await ctx.reply(
            'Usage: `!hotels [city] | [check-in] | [check-out] | [budget/night optional]`\n'
            'Example: `!hotels San Francisco | 2026-04-15 | 2026-04-17 | 250`'
        )
        return

    def _run():
        try:
            from eos_ai.travel_manager import research_hotels
            parts = [p.strip() for p in args.split('|')]
            city = parts[0]
            check_in = parts[1] if len(parts) > 1 else ''
            check_out = parts[2] if len(parts) > 2 else ''
            budget = float(parts[3].replace('$', '')) if len(parts) > 3 else 200
            result = research_hotels(city, check_in, check_out, budget)
            return f'🏨 **Hotels — {city}:**\n{result}'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply(f'🏨 Researching hotels...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    for chunk in [output[i:i+1900] for i in range(0, len(output), 1900)]:
        await ctx.channel.send(chunk)


@bot.command(name='restaurants')
async def cmd_restaurants(ctx: commands.Context, *, args: str = ''):
    """Research restaurants. Usage: !restaurants [city] | [occasion] | [budget]"""
    if not args:
        await ctx.reply(
            'Usage: `!restaurants [city] | [occasion] | [budget]`\n'
            'Example: `!restaurants San Francisco | business dinner | moderate`'
        )
        return

    def _run():
        try:
            from eos_ai.travel_manager import research_restaurants
            parts = [p.strip() for p in args.split('|')]
            city = parts[0]
            occasion = parts[1] if len(parts) > 1 else 'business dinner'
            budget = parts[2] if len(parts) > 2 else 'moderate'
            result = research_restaurants(city, occasion, budget)
            return f'🍽️ **Restaurants — {city}:**\n{result}'
        except Exception as e:
            return f'❌ Error: {e}'

    await ctx.reply(f'🍽️ Researching restaurants...')
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, _run)
    for chunk in [output[i:i+1900] for i in range(0, len(output), 1900)]:
        await ctx.channel.send(chunk)
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f:
    ast.parse(f.read())
print('syntax ok')
"
```

- [ ] **Step 3: Commit**

```bash
cd /opt/OS
git add 13_Scripts/discord_bot.py
git commit -m "feat: add flights, hotels, restaurants discord commands"
```

---

## Task 11: Full integration verification and deploy

**Files:** No changes — verification and deploy only.

- [ ] **Step 1: Full import check**

```bash
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.expense_tracker import (
    create_invoice, get_invoices, get_overdue_invoices,
    generate_invoice_text, generate_expense_report, generate_budget_vs_actual,
)
from eos_ai.doc_creator import create_briefing_doc, create_presentation_outline, fact_check
from eos_ai.personal_admin import add_important_date, get_upcoming_dates, research_gift
from eos_ai.travel_manager import (
    research_flights, research_hotels, research_restaurants,
    build_travel_brief, log_trip,
)
from eos_ai.eod_closing_loop import EODClosingLoop
from eos_ai.daily_sync import DailySync, SyncAgenda
print('all imports clean')
"
```
Expected: `all imports clean`

- [ ] **Step 2: Verify discord_bot.py syntax**

```bash
python3 -c "
import ast
with open('/opt/OS/13_Scripts/discord_bot.py') as f:
    ast.parse(f.read())
print('discord_bot syntax ok')
"
```

- [ ] **Step 3: Verify new commands are registered**

```bash
grep -n "name='invoices'\|name='invoice'\|name='expensereport'\|name='budget'\|name='briefdoc'\|name='board'\|name='investor'\|name='slides'\|name='factcheck'\|name='dates'\|name='adddate'\|name='gift'\|name='flights'\|name='hotels'\|name='restaurants'" /opt/OS/13_Scripts/discord_bot.py
```
Expected: 15 lines (each command name appears once)

- [ ] **Step 4: Deploy**

```bash
cd /opt/OS
docker compose restart os-discord
sleep 15
docker logs os-discord --tail 15
```
Expected: No `ImportError` or `Traceback`. Bot shows as online.
