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
load_dotenv('/opt/OS/umh/.env')


def get_upcoming_calls(window_start_mins: int = 25, window_end_mins: int = 45) -> list:
    """
    Get calendar events starting in the next 25-45 minutes.
    Returns list of event dicts (GWSConnector format).
    """
    try:
        from umh.runtime_engine.gws_connector import GWSConnector

        gws = GWSConnector()

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
    from umh.runtime_engine.meetings import build_prep_brief as _meetings_brief
    from umh.runtime_engine.meetings import find_notion_meeting_by_person, update_meeting_prep_notes

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

    from umh.environments.system_context import load_context_from_env
    ctx = load_context_from_env()

    for event in upcoming:
        event_id = event.get('title', 'unknown') + '_' + str(event.get('start', ''))[:16]

        if already_prepped(event_id):
            print(f"[CallPrep] Already prepped for: {event.get('title')}")
            continue

        brief = build_prep_brief(event, ctx)

        # Detect if this is a recurring meeting and append standing agenda
        is_recurring = bool(event.get('recurrence') or event.get('recurringEventId'))
        if is_recurring:
            try:
                from umh.runtime_engine.model_router import get_router, TaskType as _CPTaskType
                import json as _cpjson

                _cp_router = get_router()
                _cp_model = _cp_router.route(_CPTaskType.FAST_RESPONSE)

                _cp_title = event.get('title', event.get('summary', ''))
                _cp_open_loops = ''
                try:
                    import requests as _cpreq
                    _cp_token = os.getenv('NOTION_API_KEY')
                    _cp_db_id = os.getenv('NOTION_MEETINGS_ID')
                    if _cp_token and _cp_db_id:
                        _cp_headers = {
                            'Authorization': f'Bearer {_cp_token}',
                            'Notion-Version': '2022-06-28',
                            'Content-Type': 'application/json',
                        }
                        _cp_resp = _cpreq.post(
                            f'https://api.notion.com/v1/databases/{_cp_db_id}/query',
                            headers=_cp_headers,
                            json={
                                'filter': {
                                    'property': 'Name',
                                    'rich_text': {'contains': _cp_title[:30]},
                                },
                                'sorts': [{'property': 'Date', 'direction': 'descending'}],
                                'page_size': 1,
                            },
                            timeout=10,
                        )
                        _cp_results = _cp_resp.json().get('results', [])
                        if _cp_results:
                            _cp_props = _cp_results[0].get('properties', {})
                            _cp_open_loops = _cp_props.get('Open Loops', {}).get(
                                'rich_text', [{}]
                            )[0].get('plain_text', '')
                except Exception:
                    pass

                _cp_agenda = _cp_router.call(_cp_model, f"""This is a recurring meeting.
Title: {_cp_title}
Open loops from last session: {_cp_open_loops or 'None captured'}

Draft a concise standing agenda for this recurring meeting.
Include:
- Quick wins/updates since last session
- Open loops to close
- Main agenda items
- Decisions needed

Under 100 words. Direct format.""").strip()

                brief += f'\n\n**🔄 Recurring meeting agenda:**\n{_cp_agenda}'

                try:
                    import requests as _cpreq2
                    _cp_webhook = os.getenv('DISCORD_BRIEF_WEBHOOK')
                    if _cp_webhook and _cp_agenda:
                        _cpreq2.post(
                            _cp_webhook,
                            json={'content': f'📋 **Standing agenda for {_cp_title}:**\n{_cp_agenda}'},
                            timeout=5,
                        )
                except Exception:
                    pass

            except Exception as e:
                print(f'[CallPrep] Recurring agenda failed: {e}')

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
        from umh.runtime_engine.gws_connector import GWSConnector

        _gws = GWSConnector()
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

                from umh.runtime_engine.meetings import draft_meeting_agenda
                from umh.storage.adapters.neon import get_conn

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

    # 48h travel brief window — fire brief day-before for travel events
    try:
        import json as _tj
        from datetime import timezone as _tz
        from dateutil.parser import parse as _tparse
        from umh.runtime_engine.gws_connector import GWSConnector as _TGWS
        from umh.environments.system_context import load_context_from_env as _tctx
        from umh.runtime_engine.travel_manager import detect_travel_event, build_travel_brief, log_trip

        _t_ctx = _tctx()
        _t_gws = _TGWS()  # GWSConnector takes no args
        _t_all = _t_gws.get_upcoming_events(days=3)

        _travel_state_file = '/tmp/travel_brief_state.json'
        try:
            with open(_travel_state_file) as _tf:
                _travel_state = _tj.load(_tf)
        except Exception:
            _travel_state = {}

        _t_now = datetime.now(timezone.utc)
        _t_win_start = _t_now + timedelta(hours=47)
        _t_win_end = _t_now + timedelta(hours=49)

        for _t_event in (_t_all or []):
            _t_id = _t_event.get('id', '')
            if not _t_id or f'travel_{_t_id}' in _travel_state:
                continue
            if not detect_travel_event(_t_event):
                continue

            _t_start_str = _t_event.get('start', '')
            if not _t_start_str or 'T' not in str(_t_start_str):
                continue

            try:
                _t_start_dt = _tparse(str(_t_start_str))
                if _t_start_dt.tzinfo is None:
                    _t_start_dt = _t_start_dt.replace(tzinfo=_tz.utc)

                if not (_t_win_start <= _t_start_dt <= _t_win_end):
                    continue

                _t_location = _t_event.get('location', 'Unknown destination')
                _t_title = _t_event.get('title', _t_event.get('summary', 'Trip'))
                _t_attendees = [
                    a.get('email', '') for a in _t_event.get('attendees', [])
                    if not a.get('self')
                ]
                _t_brief = build_travel_brief(
                    event_title=_t_title,
                    destination=_t_location,
                    start_date=str(_t_start_dt.date()),
                    end_date=str(_t_start_dt.date()),
                    attendees=_t_attendees,
                )
                log_trip(_t_title, _t_location, str(_t_start_dt.date()), '')

                _t_webhook = os.getenv('DISCORD_BRIEF_WEBHOOK')
                if _t_webhook and _t_brief:
                    import requests as _treq
                    _t_msg = f'✈️ **48h Travel Brief: {_t_title}**\n\n{_t_brief}'
                    for _ti in range(0, len(_t_msg), 1900):
                        _treq.post(_t_webhook, json={'content': _t_msg[_ti:_ti+1900]}, timeout=5)

                _travel_state[f'travel_{_t_id}'] = _t_now.isoformat()
                print(f'[CallPrep] Travel brief fired for: {_t_title}')

            except Exception as _te:
                print(f'[CallPrep] Travel brief for {_t_id} failed: {_te}')

        with open(_travel_state_file, 'w') as _tf:
            _tj.dump(_travel_state, _tf)

    except Exception as _te2:
        print(f'[CallPrep] Travel window check failed: {_te2}')


if __name__ == '__main__':
    main()
