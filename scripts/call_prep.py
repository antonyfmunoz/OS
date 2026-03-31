"""
Call Prep — runs every 15 minutes via cron.
Checks GWS calendar for events starting in the next 25-45 minutes.
Fires a proactive prep brief to Discord if one is found.
"""

import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, '/opt/OS')
from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')


def get_upcoming_calls(window_start_mins: int = 25, window_end_mins: int = 45) -> list:
    """
    Get calendar events starting in the next 25-45 minutes.
    Returns list of event dicts (GWSConnector format).
    """
    try:
        from eos_ai.gws_connector import GWSConnector
        from eos_ai.context import load_context_from_env

        ctx = load_context_from_env()
        gws = GWSConnector(ctx)

        now = datetime.now(timezone.utc)
        window_start = now + timedelta(minutes=window_start_mins)
        window_end = now + timedelta(minutes=window_end_mins)

        events = gws.get_today_events()
        upcoming = []

        for event in (events or []):
            # get_today_events returns 'start' as an ISO string, not a nested dict
            start_str = event.get('start', '')
            if not start_str or 'T' not in str(start_str):
                continue
            try:
                from dateutil import parser as dateparser
                start_dt = dateparser.parse(str(start_str))
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                if window_start <= start_dt <= window_end:
                    upcoming.append(event)
            except Exception:
                continue

        return upcoming

    except Exception as e:
        print(f"[CallPrep] Calendar fetch failed: {e}")
        return []


def build_prep_brief(event: dict, ctx) -> str:
    """Build a concise pre-call brief for a calendar event."""
    from eos_ai.meetings import build_prep_brief as _meetings_brief
    from eos_ai.meetings import find_notion_meeting_by_person, update_meeting_prep_notes

    title     = event.get('title', 'Untitled event')
    start_str = event.get('start', '')
    meet_link = event.get('meet_link', '')
    location  = event.get('location', '')

    # Format start time header
    try:
        from dateutil import parser as dateparser
        start_dt = dateparser.parse(str(start_str))
        time_str = start_dt.strftime('%I:%M %p').lstrip('0')
    except Exception:
        time_str = str(start_str)[:16] if start_str else 'soon'

    header = f"**📞 Call in ~30 mins: {title}**\n"
    header += f"**Time:** {time_str}\n"
    if meet_link:
        header += f"**Link:** {meet_link}\n"
    elif location:
        header += f"**Location:** {location}\n"
    header += "\n"

    # Use central meetings brief (memory search + structure)
    brief_body = _meetings_brief(
        person=title,
        company='',
        meeting_type='Discovery',
        venture='',
        ctx=ctx,
    )

    full_brief = header + brief_body + "\n\nAntony — you're prepped. I'll handle everything else."

    # Write prep notes to Notion meeting record
    try:
        notion_id = find_notion_meeting_by_person(title)
        if notion_id:
            update_meeting_prep_notes(notion_id, full_brief)
    except Exception:
        pass

    return full_brief


def post_to_discord(message: str) -> bool:
    """Post the prep brief to Discord."""
    try:
        import requests
        webhook = os.getenv('DISCORD_BRIEF_WEBHOOK')
        if not webhook:
            print("[CallPrep] No DISCORD_BRIEF_WEBHOOK set")
            return False

        resp = requests.post(
            webhook,
            json={'content': message, 'username': 'DEX'},
            timeout=10,
        )
        return resp.status_code in (200, 204)

    except Exception as e:
        print(f"[CallPrep] Discord post failed: {e}")
        return False


def already_prepped(event_id: str) -> bool:
    """Check if we already sent a prep for this event today."""
    state_file = '/tmp/call_prep_state.txt'
    try:
        if os.path.exists(state_file):
            with open(state_file) as f:
                return event_id in f.read().splitlines()
    except Exception:
        pass
    return False


def mark_prepped(event_id: str) -> None:
    """Record that we've prepped for this event."""
    state_file = '/tmp/call_prep_state.txt'
    try:
        with open(state_file, 'a') as f:
            f.write(event_id + '\n')
    except Exception:
        pass


def main():
    print(f"[CallPrep] Running at {datetime.now().strftime('%H:%M')}")

    upcoming = get_upcoming_calls()

    if not upcoming:
        print("[CallPrep] No calls in the next 25-45 minutes")
        return

    from eos_ai.context import load_context_from_env
    ctx = load_context_from_env()

    for event in upcoming:
        event_id = event.get('title', 'unknown') + '_' + str(event.get('start', ''))[:16]

        if already_prepped(event_id):
            print(f"[CallPrep] Already prepped for: {event.get('title')}")
            continue

        brief = build_prep_brief(event, ctx)
        success = post_to_discord(brief)

        if success:
            mark_prepped(event_id)
            print(f"[CallPrep] Prepped for: {event.get('title')}")
        else:
            print(f"[CallPrep] Failed to post prep for: {event.get('title')}")

    # 24h agenda window — draft agenda for tomorrow's meetings
    try:
        import json as _json
        from datetime import timezone
        from dateutil.parser import parse as _parse
        from eos_ai.gws_connector import GWSConnector
        from eos_ai.context import load_context_from_env

        _ctx = load_context_from_env()
        _gws = GWSConnector(_ctx)
        _all_events = _gws.get_upcoming_events(days=2)

        _agenda_state_file = '/tmp/agenda_sent_state.json'
        try:
            with open(_agenda_state_file) as _f:
                _agenda_state = _json.load(_f)
        except Exception:
            _agenda_state = {}

        _now_utc = datetime.now(timezone.utc)
        _agenda_window_start = _now_utc + timedelta(hours=23)
        _agenda_window_end = _now_utc + timedelta(hours=25)

        for _event in (_all_events or []):
            _event_id = _event.get('id', '') or (
                _event.get('title', '') + '_' + str(_event.get('start', ''))[:16]
            )
            if not _event_id or _event_id in _agenda_state:
                continue

            _start_str = _event.get('start', '')
            if not _start_str or 'T' not in str(_start_str):
                continue

            try:
                _event_start = _parse(str(_start_str))
                if _event_start.tzinfo is None:
                    _event_start = _event_start.replace(tzinfo=timezone.utc)

                if not (_agenda_window_start <= _event_start <= _agenda_window_end):
                    continue

                _attendees = _event.get('attendees', [])
                _attendee_email = next(
                    (a.get('email') for a in _attendees if not a.get('self')),
                    '',
                )
                if not _attendee_email:
                    continue

                from eos_ai.meetings import draft_meeting_agenda
                from eos_ai.db import get_conn

                _agenda = draft_meeting_agenda(
                    title=_event.get('title', _event.get('summary', 'Our call')),
                    person=_attendee_email.split('@')[0],
                    email=_attendee_email,
                    meeting_type='Meeting',
                    venture='',
                    ctx=_ctx,
                )

                if _agenda:
                    with get_conn(_ctx.org_id) as _cur:
                        _cur.execute('''
                            INSERT INTO events
                            (org_id, event_type, payload_json, handled_by)
                            VALUES (%s, %s, %s, %s)
                        ''', (
                            str(_ctx.org_id),
                            'email_draft_pending',
                            _json.dumps({
                                'draft': _agenda,
                                'to_email': _attendee_email,
                                'type': 'meeting_agenda',
                                'event_id': _event_id,
                                'status': 'pending_approval',
                            }),
                            'call_prep',
                        ))

                    _webhook = os.getenv('DISCORD_BRIEF_WEBHOOK')
                    if _webhook:
                        import requests as _req
                        _msg = (
                            f'📋 **Agenda drafted for tomorrow:**\n'
                            f'{_event.get("title", "Meeting")} with {_attendee_email}\n'
                            f'```\n{_agenda[:600]}\n```\n'
                            f'`!approve_followup` to send.'
                        )
                        _req.post(_webhook, json={'content': _msg}, timeout=5)

                    _agenda_state[_event_id] = _now_utc.isoformat()
                    print(f'[CallPrep] Agenda drafted for: {_event.get("title")}')

            except Exception as _e:
                print(f'[CallPrep] Agenda for {_event_id} failed: {_e}')

        with open(_agenda_state_file, 'w') as _f:
            _json.dump(_agenda_state, _f)

    except Exception as _e:
        print(f'[CallPrep] Agenda window check failed: {_e}')


if __name__ == '__main__':
    main()
