"""
Meetings — central module for all meeting lifecycle management.
Neon + Notion + Discord all three on every action.
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def create_meeting_record(
    title: str,
    person: str,
    email: str = '',
    company: str = '',
    date_iso: str = '',
    meeting_type: str = 'Discovery',
    venture: str = '',
    source: str = 'Manual',
    meet_link: str = '',
    calendly_event_id: str = '',
    ctx=None,
) -> dict:
    """
    Create a meeting record in Neon + Notion simultaneously.
    Returns dict with neon_id, notion_id, success.
    """
    try:
        from runtime.context import load_context_from_env
        from runtime.db import get_conn
        import requests
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

        ctx = ctx or load_context_from_env()

        # 1. Write to Neon
        neon_id = None
        try:
            with get_conn(ctx.org_id) as cur:
                cur.execute('''
                    INSERT INTO events (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                ''', (
                    str(ctx.org_id),
                    'meeting_scheduled',
                    json.dumps({
                        'title': title,
                        'person': person,
                        'email': email,
                        'company': company,
                        'date': date_iso,
                        'type': meeting_type,
                        'venture': venture,
                        'source': source,
                        'meet_link': meet_link,
                        'calendly_event_id': calendly_event_id,
                    }),
                    'dex_meetings',
                ))
                row = cur.fetchone()
                neon_id = str(row['id']) if row else None
        except Exception as e:
            logger.warning(f'[Meetings] Neon write failed: {e}')

        # 2. Write to Notion
        notion_id = None
        try:
            token = os.getenv('NOTION_API_KEY')
            db_id = os.getenv('NOTION_MEETINGS_ID')
            if token and db_id:
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Notion-Version': '2022-06-28',
                    'Content-Type': 'application/json',
                }
                props = {
                    'Name': {'title': [{'text': {'content': title}}]},
                    'Person': {'rich_text': [{'text': {'content': person}}]},
                    'Email': {'email': email} if email else {'email': None},
                    'Company': {'rich_text': [{'text': {'content': company}}]},
                    'Status': {'select': {'name': 'Scheduled'}},
                    'Type': {'select': {'name': meeting_type}},
                    'Source': {'select': {'name': source}},
                    'Calendly Event ID': {'rich_text': [{'text': {'content': calendly_event_id}}]},
                }
                if date_iso:
                    props['Date'] = {'date': {'start': date_iso}}
                if venture:
                    props['Venture'] = {'select': {'name': venture}}
                if meet_link:
                    props['Meet Link'] = {'url': meet_link}

                resp = requests.post(
                    'https://api.notion.com/v1/pages',
                    headers=headers,
                    json={'parent': {'database_id': db_id}, 'properties': props},
                    timeout=10,
                )
                notion_id = resp.json().get('id')
        except Exception as e:
            logger.warning(f'[Meetings] Notion write failed: {e}')

        return {'success': True, 'neon_id': neon_id, 'notion_id': notion_id}

    except Exception as e:
        logger.error(f'[Meetings] create_meeting_record failed: {e}')
        return {'success': False, 'error': str(e)}


def update_meeting_outcome(
    calendly_event_id: str = '',
    notion_id: str = '',
    status: str = 'Completed',
    outcomes: str = '',
    open_loops: str = '',
    ctx=None,
) -> bool:
    """Update meeting outcomes in Neon + Notion after call ends."""
    try:
        import requests
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

        token = os.getenv('NOTION_API_KEY')
        db_id = os.getenv('NOTION_MEETINGS_ID')

        if not notion_id and calendly_event_id:
            # Find by Calendly Event ID
            headers = {
                'Authorization': f'Bearer {token}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json',
            }
            resp = requests.post(
                f'https://api.notion.com/v1/databases/{db_id}/query',
                headers=headers,
                json={'filter': {'property': 'Calendly Event ID', 'rich_text': {'equals': calendly_event_id}}},
                timeout=10,
            )
            results = resp.json().get('results', [])
            if results:
                notion_id = results[0]['id']

        if notion_id and token:
            headers = {
                'Authorization': f'Bearer {token}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json',
            }
            props = {'Status': {'select': {'name': status}}}
            if outcomes:
                props['Outcomes'] = {'rich_text': [{'text': {'content': outcomes}}]}
            if open_loops:
                props['Open Loops'] = {'rich_text': [{'text': {'content': open_loops}}]}

            requests.patch(
                f'https://api.notion.com/v1/pages/{notion_id}',
                headers=headers,
                json={'properties': props},
                timeout=10,
            )
            if open_loops and status == 'Completed':
                try:
                    queue_follow_up_tasks(
                        person='',
                        open_loops=open_loops,
                    )
                except Exception:
                    pass

            # Part 1 — Auto-draft follow-up email after meeting
            if status == 'Completed' and (outcomes or open_loops):
                try:
                    from execution.runtime.model_router import get_router, TaskType
                    from runtime.context import load_context_from_env
                    from runtime.db import get_conn
                    import json as _json
                    _ctx = ctx or load_context_from_env()
                    _router = get_router()
                    _model = _router.route(TaskType.FAST_RESPONSE)

                    _prompt = f"""You are DEX, EA to Antony Munoz.
Draft a follow-up email after a meeting.

Person: the person you just met with
Outcomes: {outcomes}
Open loops / next steps: {open_loops}

Write in Antony's voice — direct, warm, short.
No corporate speak. Clear next step at the end.
Include subject line.

Format:
Subject: [subject]

[body]

DEX
On behalf of Antony Munoz"""

                    _draft = _router.call(_model, _prompt).strip()

                    with get_conn(_ctx.org_id) as _cur:
                        _cur.execute('''
                            INSERT INTO events
                            (org_id, event_type, payload_json, handled_by)
                            VALUES (%s, %s, %s, %s)
                        ''', (
                            str(_ctx.org_id),
                            'email_draft_pending',
                            _json.dumps({
                                'draft': _draft,
                                'type': 'meeting_followup',
                                'status': 'pending_approval',
                                'source': 'post_meeting',
                            }),
                            'dex_meetings',
                        ))

                    try:
                        import requests as _req
                        import os as _os
                        _webhook = _os.getenv('DISCORD_BRIEF_WEBHOOK')
                        if _webhook:
                            _msg = (
                                f'📧 **Follow-up email drafted:**\n'
                                f'```\n{_draft[:800]}\n```\n'
                                f'Reply `!approve_followup` to send '
                                f'or `!edit_followup [changes]` to revise.'
                            )
                            _req.post(_webhook, json={'content': _msg}, timeout=5)
                    except Exception:
                        pass

                except Exception as e:
                    logger.warning(f'[Meetings] Auto follow-up draft failed: {e}')

            # Part 2 — Auto-update pipeline stage based on outcome
            if outcomes and status == 'Completed':
                try:
                    from execution.runtime.model_router import get_router, TaskType
                    import json as _json
                    _router = get_router()
                    _model = _router.route(TaskType.FAST_RESPONSE)

                    _stage_prompt = f"""Based on this meeting outcome, what is the deal stage?

Outcomes: {outcomes}
Open loops: {open_loops}

Return JSON only:
{{"stage": "New Lead|Contacted|Qualified|Proposal|Negotiation|Closed Won|Closed Lost|Nurture",
  "confidence": "high|medium|low",
  "should_update": true/false}}"""

                    _result = _router.call(_model, _stage_prompt).strip()
                    if '```' in _result:
                        _result = _result.split('```')[1].replace('json', '').strip()
                    _stage_data = _json.loads(_result)

                    if (
                        _stage_data.get('should_update')
                        and _stage_data.get('confidence') in ('high', 'medium')
                    ):
                        _new_stage = _stage_data.get('stage', '')
                        if _new_stage and notion_id:
                            try:
                                import requests as _req
                                import os as _os
                                _token = _os.getenv('NOTION_API_KEY')
                                _headers = {
                                    'Authorization': f'Bearer {_token}',
                                    'Notion-Version': '2022-06-28',
                                    'Content-Type': 'application/json',
                                }
                                _req.patch(
                                    f'https://api.notion.com/v1/pages/{notion_id}',
                                    headers=_headers,
                                    json={'properties': {
                                        'Status': {'select': {'name': 'Completed'}},
                                        'Outcomes': {'rich_text': [{'text': {
                                            'content': f'{outcomes}\n\nDeal Stage: {_new_stage}'
                                        }}]},
                                    }},
                                    timeout=10,
                                )
                                logger.info(f'[Meetings] Deal stage updated: {_new_stage}')
                            except Exception as e:
                                logger.warning(f'[Meetings] Stage update failed: {e}')
                except Exception as e:
                    logger.warning(f'[Meetings] Deal stage detection failed: {e}')

            # Part 3 — Auto-draft meeting minutes after completion
            if status in ('Completed', 'completed') and outcomes:
                try:
                    _meeting_title = (
                        f'Meeting ({calendly_event_id})' if calendly_event_id else 'Meeting'
                    )
                    mins_result = draft_meeting_minutes(
                        title=_meeting_title,
                        person='',
                        outcomes=outcomes,
                        open_loops=open_loops,
                        attendee_emails=[],
                        ctx=ctx,
                    )
                    if mins_result.get('minutes'):
                        try:
                            import requests as _req
                            import os as _os
                            _webhook = _os.getenv('DISCORD_BRIEF_WEBHOOK')
                            if _webhook:
                                _req.post(_webhook, json={
                                    'content': '📋 **Meeting minutes drafted** — saved to Drive.'
                                }, timeout=5)
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f'[Meetings] Minutes auto-draft failed: {e}')

            return True
    except Exception as e:
        logger.warning(f'[Meetings] update_meeting_outcome failed: {e}')
    return False


def update_meeting_prep_notes(notion_id: str, prep_notes: str) -> bool:
    """Write prep brief to the Prep Notes field of a Notion meeting record."""
    try:
        import requests
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

        token = os.getenv('NOTION_API_KEY')
        if not notion_id or not token:
            return False

        headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json',
        }
        # Notion rich_text has a 2000 char limit per block
        requests.patch(
            f'https://api.notion.com/v1/pages/{notion_id}',
            headers=headers,
            json={'properties': {
                'Prep Notes': {'rich_text': [{'text': {'content': prep_notes[:2000]}}]},
            }},
            timeout=10,
        )
        return True
    except Exception as e:
        logger.warning(f'[Meetings] update_meeting_prep_notes failed: {e}')
        return False


def find_notion_meeting_by_person(person: str) -> str | None:
    """Find the most recent Notion meeting record for a person. Returns notion_id or None."""
    try:
        import requests
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

        token = os.getenv('NOTION_API_KEY')
        db_id = os.getenv('NOTION_MEETINGS_ID')
        if not token or not db_id:
            return None

        headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json',
        }
        resp = requests.post(
            f'https://api.notion.com/v1/databases/{db_id}/query',
            headers=headers,
            json={
                'filter': {'property': 'Person', 'rich_text': {'contains': person}},
                'sorts': [{'property': 'Date', 'direction': 'descending'}],
                'page_size': 1,
            },
            timeout=10,
        )
        results = resp.json().get('results', [])
        return results[0]['id'] if results else None
    except Exception as e:
        logger.warning(f'[Meetings] find_notion_meeting_by_person failed: {e}')
        return None


def get_open_loop_meetings(days_back: int = 7, ctx=None) -> list[dict]:
    """Get completed meetings with unresolved open loops for Section 4 of daily brief."""
    try:
        import requests
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))

        token = os.getenv('NOTION_API_KEY')
        db_id = os.getenv('NOTION_MEETINGS_ID')
        if not token or not db_id:
            return []

        headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json',
        }
        cutoff = (datetime.now(PDT) - timedelta(days=days_back)).date().isoformat()
        resp = requests.post(
            f'https://api.notion.com/v1/databases/{db_id}/query',
            headers=headers,
            json={'filter': {'and': [
                {'property': 'Status', 'select': {'equals': 'Completed'}},
                {'property': 'Open Loops', 'rich_text': {'is_not_empty': True}},
                {'property': 'Date', 'date': {'on_or_after': cutoff}},
            ]}},
            timeout=10,
        )
        results = resp.json().get('results', [])
        meetings = []
        for r in results:
            props = r.get('properties', {})
            meetings.append({
                'title': props.get('Name', {}).get('title', [{}])[0].get('plain_text', ''),
                'person': props.get('Person', {}).get('rich_text', [{}])[0].get('plain_text', ''),
                'open_loops': props.get('Open Loops', {}).get('rich_text', [{}])[0].get('plain_text', ''),
                'date': props.get('Date', {}).get('date', {}).get('start', ''),
                'notion_id': r['id'],
            })
        return meetings
    except Exception as e:
        logger.warning(f'[Meetings] get_open_loop_meetings failed: {e}')
        return []


def queue_follow_up_tasks(
    person: str,
    open_loops: str,
    venture: str = '',
    ctx=None,
) -> bool:
    """Auto-queue follow-up tasks after a meeting."""
    try:
        from runtime.context import load_context_from_env
        from runtime.db import get_conn
        ctx = ctx or load_context_from_env()

        tasks = []

        # Always queue a follow-up email task
        tasks.append(f'Follow up with {person} — send recap and next steps')

        # Queue tasks from open loops
        if open_loops:
            for loop in open_loops.split('.'):
                loop = loop.strip()
                if loop and len(loop) > 10:
                    tasks.append(loop)

        with get_conn(ctx.org_id) as cur:
            for task in tasks:
                cur.execute('''
                    INSERT INTO events (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                ''', (
                    str(ctx.org_id),
                    'dex_task',
                    json.dumps({
                        'task':    task,
                        'status':  'pending',
                        'source':  'post_meeting',
                        'person':  person,
                        'venture': venture,
                    }),
                    'dex_meetings',
                ))
        return True
    except Exception as e:
        logger.warning(f'[Meetings] queue_follow_up_tasks failed: {e}')
        return False


def build_prep_brief(
    person: str,
    company: str,
    meeting_type: str,
    venture: str,
    email: str = '',
    ctx=None,
) -> str:
    """
    Build a world-class pre-meeting prep brief.
    Pulls intelligence profile + semantic memory + structures talking points.
    """
    try:
        from runtime.context import load_context_from_env
        from runtime.person_recognition import (
            build_intelligence_profile,
            format_intelligence_profile,
        )
        ctx = ctx or load_context_from_env()

        # Build intelligence profile
        profile = build_intelligence_profile(
            name=person,
            email=email,
            company=company,
            ctx=ctx,
        )

        lines = [f'## Pre-Meeting Brief: {person}']
        if company:
            lines.append(f'🏢 {company} | {meeting_type} | {venture}')
        lines.append('')

        # Intelligence profile block
        profile_text = format_intelligence_profile(profile)
        if profile_text:
            lines.append(profile_text)
            lines.append('')

        # Semantic memory hits
        try:
            from state.memory.memory import AgentMemory
            mem = AgentMemory(ctx)
            query = f'{person} {company}'.strip()
            results = mem.semantic_search(query=query, limit=5, min_similarity=0.5)
            if results:
                lines.append('**Recent context from memory:**')
                for r in results[:3]:
                    content = r.get('output_summary', '') if isinstance(r, dict) else str(r)
                    if content and len(content) > 20:
                        lines.append(f'• {content[:200]}')
                lines.append('')
        except Exception as e:
            logger.warning(f'[Meetings] Memory search in prep brief failed: {e}')

        # Strategic talking points
        lines.append('**Going into this call:**')
        if meeting_type in ('Sales Call', 'Discovery'):
            lines.append('• Understand their situation before pitching anything')
            lines.append('• Qualify: timeline, budget, decision authority')
            lines.append('• Close or define a clear next step — no open endings')
            if venture == 'Lyfe Institute':
                lines.append("• Ask: what does structure look like for you right now?")
                lines.append("• Ask: what have you tried that hasn't worked?")
            elif venture == 'Empyrean Creative':
                lines.append("• Ask: what's the one operational bottleneck costing you most?")
                lines.append("• Ask: have you tried building AI systems before?")
        elif meeting_type == 'Follow-up':
            lines.append('• Reference what was agreed last time')
            lines.append('• Address any open loops')
            lines.append('• Advance the relationship or close')
        else:
            lines.append('• Be clear on what you need from this call')
            lines.append('• End with a defined next step')

        lines.append('')

        # Add timezone context if attendee email is known
        if email:
            try:
                from runtime.gws_connector import GWSConnector
                _tz_gws = GWSConnector()
                _tz = _tz_gws.detect_timezone_from_email(email)
                from zoneinfo import ZoneInfo
                if _tz != 'America/Los_Angeles':
                    _tz_obj = ZoneInfo(_tz)
                    from datetime import datetime as _dt
                    _now_there = _dt.now(_tz_obj)
                    lines.append(
                        f'🌍 Their timezone: {_tz} '
                        f'(currently {_now_there.strftime("%-I:%M %p %Z")})'
                    )
                    lines.append('')
            except Exception:
                pass

        lines.append('**After this call, use !outcome to capture results.**')

        return '\n'.join(lines)

    except Exception as e:
        logger.warning(f'[Meetings] build_prep_brief failed: {e}')
        return f'Prep brief unavailable: {e}'


def draft_meeting_agenda(
    title: str,
    person: str,
    email: str,
    meeting_type: str,
    venture: str,
    duration_minutes: int = 60,
    ctx=None,
) -> str:
    """
    Draft a meeting agenda to send to attendee 24h before.
    Returns formatted agenda as string.
    """
    try:
        from runtime.context import load_context_from_env
        from execution.runtime.model_router import get_router, TaskType
        from runtime.person_recognition import build_intelligence_profile
        ctx = ctx or load_context_from_env()
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)

        profile = build_intelligence_profile(
            name=person, email=email, ctx=ctx
        )

        prompt = f"""Draft a pre-meeting agenda email.

Meeting: {title}
With: {person}
Type: {meeting_type}
Duration: {duration_minutes} minutes
Venture: {venture}
Their context: {profile.notes or 'New contact'}

Format:
Subject: [subject — specific, not generic]

Hi {person},

[2-3 sentence opener — warm, direct]

For our call:
- [agenda item 1 — specific to their situation]
- [agenda item 2]
- [agenda item 3 if needed]

[one sentence on what they should bring/prepare if relevant]

Looking forward to it.
[Antony/DEX]

Keep it under 150 words. No corporate speak."""

        return router.call(model, prompt).strip()
    except Exception as e:
        logger.warning(f'[Meetings] draft_meeting_agenda failed: {e}')
        return ''


def draft_meeting_minutes(
    title: str,
    person: str,
    outcomes: str,
    open_loops: str,
    duration_minutes: int = 60,
    attendee_emails: list = None,
    ctx=None,
) -> dict:
    """
    Draft formal meeting minutes and save to Drive.
    Returns dict with 'minutes' (str) and 'drive_file' (dict).
    """
    import json as _j
    try:
        from execution.runtime.model_router import get_router, TaskType
        from runtime.gws_connector import GWSConnector
        from runtime.context import load_context_from_env
        from runtime.db import get_conn
        from datetime import datetime
        from zoneinfo import ZoneInfo
        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)
        _PDT = ZoneInfo('America/Los_Angeles')
        now = datetime.now(_PDT)

        minutes = router.call(model, f"""Draft formal meeting minutes.

Meeting: {title}
Attendees: Antony Munoz, {person}
Date: {now.strftime('%B %d, %Y')}
Duration: {duration_minutes} minutes

Outcomes/decisions: {outcomes}
Open loops/action items: {open_loops}

Format:
# Meeting Minutes — {title}
**Date:** {now.strftime('%B %d, %Y')}
**Attendees:** Antony Munoz, {person}
**Duration:** {duration_minutes} min

## Summary
[2 sentence summary]

## Decisions Made
[bullet list of decisions]

## Action Items
[bullet list with owner and timeline]

## Next Steps
[what happens next and when]

Keep it professional and concise.""").strip()

        gws = GWSConnector()
        drive_file = {}
        try:
            drive_file = gws.create_document(
                title=f'Minutes — {title} — {now.strftime("%Y-%m-%d")}',
                content=minutes,
            )
        except Exception:
            pass

        ctx = ctx or load_context_from_env()
        try:
            with get_conn(ctx.org_id) as cur:
                cur.execute('''
                    INSERT INTO events
                    (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                ''', (
                    str(ctx.org_id),
                    'meeting_minutes',
                    _j.dumps({
                        'title': title,
                        'person': person,
                        'minutes': minutes,
                        'drive_id': drive_file.get('id', ''),
                        'attendee_emails': attendee_emails or [],
                        'created_at': now.isoformat(),
                    }),
                    'dex_meetings',
                ))
        except Exception:
            pass

        return {
            'minutes': minutes,
            'drive_file': drive_file,
            'attendee_emails': attendee_emails or [],
        }
    except Exception as e:
        logger.warning(f'[Meetings] draft_meeting_minutes failed: {e}')
        return {}


def calculate_meeting_roi(
    venture: str = None,
    days: int = 30,
    ctx=None,
) -> dict:
    """
    Calculate meeting ROI — which meeting types are
    converting, which are time sinks.
    """
    try:
        import requests as _req
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
        token = os.getenv('NOTION_API_KEY')
        db_id = os.getenv('NOTION_MEETINGS_ID')
        if not token or not db_id:
            return {}

        headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json',
        }

        cutoff = (datetime.now(PDT) - timedelta(days=days)).date().isoformat()
        filter_clause: dict = {
            'and': [
                {'property': 'Date', 'date': {'on_or_after': cutoff}},
            ]
        }
        if venture:
            filter_clause['and'].append(
                {'property': 'Venture', 'select': {'equals': venture}}
            )

        resp = _req.post(
            f'https://api.notion.com/v1/databases/{db_id}/query',
            headers=headers,
            json={'filter': filter_clause, 'page_size': 50},
            timeout=10,
        )
        meetings = resp.json().get('results', [])

        stats: dict = {
            'total': len(meetings),
            'completed': 0,
            'no_show': 0,
            'cancelled': 0,
            'by_type': {},
            'conversion_rate': 0.0,
            'top_converting_type': '',
        }

        for m in meetings:
            props = m.get('properties', {})
            status = props.get('Status', {}).get('select', {}).get('name', '')
            meeting_type = props.get('Type', {}).get('select', {}).get('name', 'Other')
            outcomes = (
                props.get('Outcomes', {})
                     .get('rich_text', [{}])[0]
                     .get('plain_text', '')
            )

            if status == 'Completed':
                stats['completed'] += 1
            elif status == 'No-show':
                stats['no_show'] += 1
            elif status == 'Cancelled':
                stats['cancelled'] += 1

            if meeting_type not in stats['by_type']:
                stats['by_type'][meeting_type] = {
                    'total': 0, 'completed': 0, 'advanced': 0
                }
            stats['by_type'][meeting_type]['total'] += 1
            if status == 'Completed':
                stats['by_type'][meeting_type]['completed'] += 1
                if any(kw in outcomes.lower() for kw in [
                    'closed', 'proposal', 'next step', 'moving forward',
                    'agreed', 'yes', 'signed'
                ]):
                    stats['by_type'][meeting_type]['advanced'] += 1

        if stats['total'] > 0:
            stats['conversion_rate'] = round(
                stats['completed'] / stats['total'], 2
            )

        best_rate = 0.0
        for mtype, data in stats['by_type'].items():
            if data['total'] > 0:
                rate = data['advanced'] / data['total']
                if rate > best_rate:
                    best_rate = rate
                    stats['top_converting_type'] = mtype

        return stats
    except Exception as e:
        logger.warning(f'[Meetings] calculate_meeting_roi failed: {e}')
        return {}
