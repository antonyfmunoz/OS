"""
Expense Tracker — processes receipts from Gmail RECEIPTS-FINANCIALS folder,
categorizes, stores in Neon, surfaces in EOD and monthly reports.
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv('/opt/OS/eos_ai/.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')

EXPENSE_CATEGORIES = [
    'Software/SaaS',
    'Infrastructure/Hosting',
    'Marketing/Ads',
    'Contractor/Freelancer',
    'Tools/Equipment',
    'Education/Training',
    'Legal/Accounting',
    'Travel',
    'Meals/Entertainment',
    'Other',
]


def extract_expense_from_email(
    subject: str,
    sender: str,
    body: str = '',
    ctx=None,
) -> dict:
    """Extract expense details from a receipt email using LLM."""
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()

        prompt = f"""Extract expense details from this receipt email.

Subject: {subject}
From: {sender}
Body excerpt: {body[:500]}

Categories: {', '.join(EXPENSE_CATEGORIES)}

Return JSON only:
{{
  "amount": 0.00,
  "currency": "USD",
  "vendor": "vendor name",
  "description": "what was purchased",
  "category": "one of the categories above",
  "date": "YYYY-MM-DD or empty",
  "is_recurring": false,
  "confidence": "high|medium|low"
}}"""

        result = router.call_with_fallback(TaskType.FAST_RESPONSE, prompt).strip()
        if '```' in result:
            result = result.split('```')[1].replace('json', '').strip()
        expense = json.loads(result)
        expense['subject'] = subject
        expense['sender'] = sender
        return expense
    except Exception as e:
        logger.warning(f'[ExpenseTracker] Extract failed: {e}')
        return {}


def store_expense(expense: dict, ctx=None) -> bool:
    """Store expense in Neon events table."""
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
                'expense',
                json.dumps(expense),
                'dex_expense_tracker',
            ))
        return True
    except Exception as e:
        logger.warning(f'[ExpenseTracker] Store failed: {e}')
        return False


def get_monthly_summary(ctx=None) -> dict:
    """Get expense summary for current month."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type = 'expense'
                AND created_at >= DATE_TRUNC('month', NOW())
                ORDER BY created_at DESC
            ''', (str(ctx.org_id),))
            rows = cur.fetchall()

        total = 0.0
        by_category: dict = {}
        expenses = []

        for r in rows:
            payload = r['payload_json']
            if isinstance(payload, str):
                payload = json.loads(payload)
            amount = float(payload.get('amount', 0))
            category = payload.get('category', 'Other')
            total += amount
            by_category[category] = by_category.get(category, 0) + amount
            expenses.append(payload)

        return {
            'total': total,
            'by_category': by_category,
            'count': len(expenses),
            'expenses': expenses,
        }
    except Exception as e:
        logger.warning(f'[ExpenseTracker] Summary failed: {e}')
        return {}


def process_receipt_emails(ctx=None) -> int:
    """
    Pull unprocessed emails from RECEIPTS folder, extract expenses, store them.
    Returns count of processed expenses.
    """
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.gws_connector import GWSConnector
        ctx = ctx or load_context_from_env()
        gws = GWSConnector()

        label_id = gws.get_or_create_label('Receipts-Financials')
        if not label_id:
            return 0

        msgs = gws.get_messages_by_label(label_id, max_results=20)
        processed = 0

        for msg_ref in msgs:
            try:
                detail = gws._run(
                    'gmail', 'users', 'messages', 'get',
                    params={
                        'userId': 'me',
                        'id': msg_ref['id'],
                        'format': 'metadata',
                        'metadataHeaders': ['From', 'Subject', 'Date'],
                    },
                )
                if not detail:
                    continue
                headers = {
                    h['name']: h['value']
                    for h in detail.get('payload', {}).get('headers', [])
                }
                expense = extract_expense_from_email(
                    subject=headers.get('Subject', ''),
                    sender=headers.get('From', ''),
                    ctx=ctx,
                )
                if expense and expense.get('confidence') in ('high', 'medium'):
                    if float(expense.get('amount', 0)) > 0:
                        store_expense(expense, ctx)
                        processed += 1
            except Exception as e:
                logger.warning(f'[ExpenseTracker] Message {msg_ref.get("id")} failed: {e}')
                continue

        return processed
    except Exception as e:
        logger.warning(f'[ExpenseTracker] process_receipt_emails failed: {e}')
        return 0


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
    try:
        from datetime import datetime
        invoices = get_invoices(status='unpaid', ctx=ctx)
        today = datetime.now(PDT).strftime('%Y-%m-%d')
        return [i for i in invoices if i.get('due_date', '9999') < today]
    except Exception as e:
        logger.warning(f'[ExpenseTracker] get_overdue_invoices failed: {e}')
        return []


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
        logger.warning(f'[ExpenseTracker] generate_budget_vs_actual failed: {e}')
        return f'Budget report unavailable: {e}'
