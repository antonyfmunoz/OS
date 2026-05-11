"""
Founder Capture — detects tasks, ideas, and reminders from Discord messages
and writes them to the Neon events table so they appear in the morning brief
Section 1 (Your list). Also pushes to Notion dashboard.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Signals that indicate a task or idea worth capturing
_TASK_SIGNALS = [
    'remind me', 'reminder', 'don\'t forget', 'follow up', 'follow-up',
    'need to', 'i need to', 'we need to', 'todo', 'to do', 'to-do',
    'make sure', 'add to', 'put on', 'schedule', 'book', 'reach out',
    'contact', 'call', 'email', 'send', 'check on', 'look into',
    'research', 'draft', 'write', 'create', 'build', 'fix', 'update',
]

_IDEA_SIGNALS = [
    'idea:', 'idea —', 'what if', 'we should', 'i should', 'could we',
    'think about', 'consider', 'maybe we', 'what about', 'potential',
    'opportunity', 'thought:', 'thought —',
]

# Messages that should never be captured
_SKIP_SIGNALS = [
    'how are you', 'what\'s up', 'hey dex', 'morning', 'good morning',
    'status', 'brief', 'what\'s the', 'how\'s', 'show me',
]


def should_capture(text: str) -> tuple[bool, str]:
    """
    Determine if a Discord message should be captured to Your list.
    Returns (should_capture, capture_type) where type is 'task' or 'idea'.
    """
    normalized = text.lower().strip()

    # Never capture greetings or status checks
    if any(s in normalized for s in _SKIP_SIGNALS):
        return False, ''

    # Must be at least 5 words to be worth capturing
    if len(text.split()) < 5:
        return False, ''

    if any(s in normalized for s in _TASK_SIGNALS):
        return True, 'task'

    if any(s in normalized for s in _IDEA_SIGNALS):
        return True, 'idea'

    return False, ''


def _classify_venture(text: str) -> str:
    """Classify which venture a capture belongs to using the model router."""
    try:
        from runtime.model_router import get_router
        router = get_router()
        prompt = f"""Classify which venture this task belongs to.

Ventures:
- lyfe_institute: coaching/education for men 18-25, discipline, identity, personal development
- empyrean_creative: B2B AI infrastructure, business automation, AI systems for companies
- personal_brand: Antony's personal content, Twitch, audience building

Task: "{text}"

Reply with exactly one of: lyfe_institute | empyrean_creative | personal_brand"""

        from runtime.model_router import TaskType
        model = router.route(TaskType.FAST_RESPONSE)
        result = router.call(model, prompt).strip().lower()
        if result in ('lyfe_institute', 'empyrean_creative', 'personal_brand'):
            return result
        return 'lyfe_institute'
    except Exception as e:
        logger.warning(f"[Capture] Venture classification failed: {e}")
        return 'lyfe_institute'


def capture_to_neon(text: str, capture_type: str, ctx=None) -> bool:
    """Write a captured task/idea to the Neon events table."""
    try:
        from runtime.db import get_conn
        from runtime.context import load_context_from_env

        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute(
                """
                INSERT INTO events (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    str(ctx.org_id),
                    'dex_task',
                    json.dumps({
                        'task': f'{capture_type.upper()}: {text}',
                        'status': None,
                        'completed': 'false',
                        'source': 'discord_capture',
                    }),
                    json.dumps([]),
                ),
            )

        logger.info(f"[Capture] Saved {capture_type}: {text[:60]}")
        return True

    except Exception as e:
        logger.warning(f"[Capture] Neon write failed: {e}")
        return False


def capture_to_notion(text: str, capture_type: str, venture_id: str = None) -> bool:
    """Push a captured task/idea to the Notion dashboard."""
    try:
        import os
        import requests
        from datetime import date
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

        token = os.getenv('NOTION_API_KEY')
        # Route to the right venture database
        if venture_id == 'empyrean_creative':
            your_list_db  = os.getenv('NOTION_YOUR_LIST_EMPYREAN')
            venture_label = 'Empyrean Creative'
        elif venture_id == 'personal_brand':
            your_list_db  = os.getenv('NOTION_YOUR_LIST_BRAND')
            venture_label = 'Personal Brand'
        else:
            your_list_db  = os.getenv('NOTION_YOUR_LIST_LYFE')
            venture_label = 'Lyfe Institute'

        if not token or not your_list_db:
            return False

        payload = {
            'parent': {'database_id': your_list_db},
            'properties': {
                'Name': {
                    'title': [{'text': {'content': text[:200]}}]
                },
                'Type': {
                    'select': {'name': 'Idea' if capture_type == 'idea' else 'Task'}
                },
                'Status': {
                    'select': {'name': 'Not Started'}
                },
                'Source': {
                    'select': {'name': 'Discord'}
                },
                'Assigned To': {
                    'select': {'name': 'Antony'}
                },
                'Venture': {
                    'select': {'name': venture_label}
                },
                'Notes': {
                    'rich_text': [{'text': {'content': f'Captured from Discord — {date.today().isoformat()}'}}]
                },
            }
        }

        resp = requests.post(
            'https://api.notion.com/v1/pages',
            headers={
                'Authorization': f'Bearer {token}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=10,
        )
        return resp.status_code == 200

    except Exception as e:
        logger.warning(f"[Capture] Notion write failed: {e}")
        return False


def capture(text: str, ctx=None, venture_id: str = None) -> dict:
    """
    Main entry point. Assess, capture to Neon and Notion if warranted.
    Returns dict with captured, type, neon_ok, notion_ok.
    """
    should, capture_type = should_capture(text)

    if not should:
        return {'captured': False, 'type': None}

    neon_ok = capture_to_neon(text, capture_type, ctx)
    resolved_venture = venture_id or _classify_venture(text)
    notion_ok = capture_to_notion(text, capture_type, venture_id=resolved_venture)

    result = {
        'captured': True,
        'type': capture_type,
        'neon_ok': neon_ok,
        'notion_ok': notion_ok,
    }

    # BBR check — should DEX handle this without flagging Antony?
    try:
        from runtime.founder_rate import get_current_founder_rate
        from runtime.task_yield_matrix import classify_task_yield
        rate = get_current_founder_rate()
        if rate:
            drip = classify_task_yield(text)
            if drip.get('quadrant') == 'delegate':
                result['below_bbr'] = True
                result['bbr_message'] = (
                    f'🤖 This is a DEX task (below ${rate["founder_rate"]}/hr). '
                    f'Adding to DEX queue — not flagging to you.'
                )
    except Exception:
        pass

    return result
