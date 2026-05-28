"""
Founder Capture — detects tasks, ideas, and reminders from Discord messages
and writes them to the Neon events table so they appear in the morning brief
Section 1 (Your list). Also pushes to Notion dashboard.
"""

import json
import logging
import os
from datetime import datetime, timezone
from substrate.self_model import get_handler_prefix as _ghp

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
    'how are you', 'what\'s up', 'morning', 'good morning',
    'status', 'brief', 'what\'s the', 'how\'s', 'show me',
]
# Add AI-name-specific skip signals at import time
_ai_lower = os.environ.get("AI_NAME", "").lower()
if _ai_lower:
    _SKIP_SIGNALS.append(f"hey {_ai_lower}")


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
    _default_venture = os.environ.get("UMH_ACTIVE_VENTURE", "")
    try:
        from adapters.models.model_router import get_router
        router = get_router()

        # Build venture list dynamically from instance config
        venture_lines = []
        try:
            from substrate.self_model import SelfModel
            sm = SelfModel()
            for v in sm.instance.ventures:
                venture_lines.append(f"- {v.get('id', '')}: {v.get('name', '')}")
        except Exception:
            # Fallback: use env var for active venture
            if _default_venture:
                venture_lines.append(f"- {_default_venture}")

        venture_block = "\n".join(venture_lines) if venture_lines else "- (no ventures configured)"
        venture_ids = [v.get('id', '') for v in getattr(getattr(SelfModel(), 'instance', None), 'ventures', [])] if venture_lines else [_default_venture]

        prompt = f"""Classify which venture this task belongs to.

Ventures:
{venture_block}

Task: "{text}"

Reply with exactly one venture id."""

        from substrate.contracts.agent_types import TaskType
        model = router.route(TaskType.FAST_RESPONSE)
        result = router.call(model, prompt).strip().lower()
        if result in venture_ids:
            return result
        return _default_venture
    except Exception as e:
        logger.warning(f"[Capture] Venture classification failed: {e}")
        return _default_venture


def capture_to_neon(text: str, capture_type: str, ctx=None) -> bool:
    """Write a captured task/idea to the Neon events table."""
    try:
        from substrate.state.memory.memory import AgentMemory
        from substrate.state.context.context import load_context_from_env

        ctx = ctx or load_context_from_env()

        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type=f'{_ghp()}task',
            payload={
                'task': f'{capture_type.upper()}: {text}',
                'status': None,
                'completed': 'false',
                'source': 'discord_capture',
            },
            handled_by=json.dumps([]),
        )

        logger.info(f"[Capture] Saved {capture_type}: {text[:60]}")
        return True

    except Exception as e:
        logger.warning(f"[Capture] Neon write failed: {e}")
        return False


def capture_to_notion(text: str, capture_type: str, venture_id: str = None) -> bool:
    """Push a captured task/idea to the Notion dashboard via SDK client."""
    try:
        from datetime import date

        from adapters.notion.integration.auth import get_notion_client

        # Resolve Notion DB and label from env vars — keyed by venture_id
        _vid_upper = (venture_id or "").upper().replace(" ", "_")
        your_list_db = os.getenv(f'NOTION_YOUR_LIST_{_vid_upper}') if _vid_upper else None
        venture_label = (venture_id or "").replace("_", " ").title()

        # Fallback: try generic Notion DB env var
        if not your_list_db:
            your_list_db = os.getenv('NOTION_YOUR_LIST_DEFAULT')
        if not your_list_db:
            return False

        _founder = os.environ.get("UMH_FOUNDER_NAME", "Founder")

        client = get_notion_client()
        client.pages.create(
            parent={'database_id': your_list_db},
            properties={
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
                    'select': {'name': _founder}
                },
                'Venture': {
                    'select': {'name': venture_label}
                },
                'Notes': {
                    'rich_text': [{'text': {'content': f'Captured from Discord — {date.today().isoformat()}'}}]
                },
            },
        )
        return True

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

    # BBR check — should the AI handle this without flagging the founder?
    _ai_name = os.environ.get("AI_NAME", "AI")
    try:
        from substrate.state.metrics.founder_rate import get_current_founder_rate
        from substrate.control_plane.strategy.task_yield_matrix import classify_task_yield
        rate = get_current_founder_rate()
        if rate:
            drip = classify_task_yield(text)
            if drip.get('quadrant') == 'delegate':
                result['below_bbr'] = True
                result['bbr_message'] = (
                    f'This is a {_ai_name} task (below ${rate["founder_rate"]}/hr). '
                    f'Adding to {_ai_name} queue — not flagging to you.'
                )
    except Exception:
        pass

    return result
