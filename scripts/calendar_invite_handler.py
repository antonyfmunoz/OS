"""
Calendar Invite Handler — polls for pending invites every 15 mins.
DEX reviews each one, decides accept/decline based on rules,
notifies Antony in Discord, logs to Notion Meetings DB.
"""

import os
import sys
import json
import asyncio
import discord
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

PDT = ZoneInfo('America/Los_Angeles')
STATE_FILE = '/tmp/calendar_invite_state.json'
GENERAL_CHANNEL_ID = 1486289444830056540


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)


def get_pending_invites() -> list[dict]:
    """Get calendar events where Antony hasn't responded yet."""
    try:
        from adapters.google_workspace.gws_connector import GWSConnector
        gws = GWSConnector()

        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=30)

        data = gws._run(
            "calendar", "events", "list",
            params={
                "calendarId":   "primary",
                "timeMin":      now.isoformat(),
                "timeMax":      time_max.isoformat(),
                "singleEvents": True,
                "orderBy":      "startTime",
            },
        )

        pending = []
        for event in (data or {}).get("items", []):
            organizer = event.get("organizer", {})
            attendees = event.get("attendees", [])

            antony_status = None
            for a in attendees:
                if a.get("self"):
                    antony_status = a.get("responseStatus")
                    break

            if antony_status == "needsAction" and not organizer.get("self"):
                pending.append({
                    "id":             event.get("id"),
                    "title":          event.get("summary", "Untitled"),
                    "start":          event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "")),
                    "organizer":      organizer.get("email", ""),
                    "organizer_name": organizer.get("displayName", organizer.get("email", "")),
                    "location":       event.get("location", ""),
                    "description":    event.get("description", "")[:200],
                    "attendees":      [a.get("email") for a in attendees if not a.get("self")],
                })
        return pending
    except Exception as e:
        print(f"[InviteHandler] get_pending_invites failed: {e}")
        return []


def assess_invite(invite: dict) -> dict:
    """Use LLM to assess invite and recommend accept/decline."""
    try:
        from execution.runtime.model_router import ModelRouter, TaskType
        from state.context.context import load_context_from_env
        ctx = load_context_from_env()
        router = ModelRouter(ctx)
        model = router.route(TaskType.FAST_RESPONSE)

        prompt = f"""You are DEX, EA to Antony Munoz, founder of Munoz Conglomerate.

Assess this calendar invite and recommend accept or decline.

Rules:
- Accept: known contacts, relevant business meetings, calls with leads/clients
- Decline: spam, irrelevant, conflicts with deep work
- Flag for Antony: anything with significant business or financial implications

Invite:
Title: {invite['title']}
From: {invite['organizer_name']} ({invite['organizer']})
When: {invite['start']}
Description: {invite['description']}

Respond with JSON only:
{{"recommendation": "accept|decline|flag", "reason": "one sentence", "confidence": "high|medium|low"}}"""

        result = router.call(model, prompt).strip()
        if '```' in result:
            result = result.split('```')[1].replace('json', '').strip()
        return json.loads(result)
    except Exception as e:
        return {'recommendation': 'flag', 'reason': f'Assessment failed: {e}', 'confidence': 'low'}


def respond_to_invite(event_id: str, response: str) -> bool:
    """Accept or decline a calendar invite. response: 'accepted' or 'declined'"""
    try:
        from adapters.google_workspace.gws_connector import GWSConnector
        gws = GWSConnector()

        event = gws._run(
            "calendar", "events", "get",
            params={"calendarId": "primary", "eventId": event_id},
        )
        if not event:
            print(f"[InviteHandler] respond_to_invite: event {event_id} not found")
            return False

        for attendee in event.get("attendees", []):
            if attendee.get("self"):
                attendee["responseStatus"] = response
                break

        result = gws._run(
            "calendar", "events", "update",
            params={
                "calendarId":  "primary",
                "eventId":     event_id,
                "sendUpdates": "all",
                "body":        event,
            },
        )
        return result is not None
    except Exception as e:
        print(f"[InviteHandler] respond_to_invite failed: {e}")
        return False


async def process_invites():
    state = load_state()
    pending = get_pending_invites()

    if not pending:
        print('[InviteHandler] No pending invites.')
        return

    new_invites = [i for i in pending if i['id'] not in state]
    if not new_invites:
        print('[InviteHandler] All invites already processed.')
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if not channel:
            print(f'[InviteHandler] Channel {GENERAL_CHANNEL_ID} not found.')
            await client.close()
            return

        for invite in new_invites:
            # Check if event falls on a protected day
            _is_protected = False
            try:
                from state.context.context import load_context_from_env
                from state.storage.db import get_conn
                import json as _pjson
                _ctx = load_context_from_env()
                _event_date = invite.get('start', '')[:10]
                if _event_date:
                    with get_conn(_ctx.org_id) as cur:
                        cur.execute(
                            '''
                            SELECT id FROM events
                            WHERE org_id = %s
                            AND event_type = 'protected_day'
                            AND payload_json->>'date' = %s
                            LIMIT 1
                            ''',
                            (str(_ctx.org_id), _event_date),
                        )
                        _is_protected = cur.fetchone() is not None
            except Exception:
                pass

            if _is_protected:
                ok = respond_to_invite(invite['id'], 'declined')
                msg = (
                    f'🚫 **Auto-declined (protected day):** {invite["title"]}\n'
                    f'📅 {invite["start"][:16]}\n'
                    f'👤 From: {invite["organizer_name"]}\n'
                    f'💬 This day is blocked as a no-meetings day.'
                )
                await channel.send(msg)
                state[invite['id']] = {
                    'processed_at': datetime.now(PDT).isoformat(),
                    'recommendation': 'declined_protected',
                }
                continue

            assessment = assess_invite(invite)
            recommendation = assessment.get('recommendation', 'flag')
            reason = assessment.get('reason', '')
            confidence = assessment.get('confidence', 'low')

            if recommendation == 'accept' and confidence == 'high':
                ok = respond_to_invite(invite['id'], 'accepted')
                emoji = '✅' if ok else '⚠️'
                msg = (
                    f"{emoji} **Auto-accepted:** {invite['title']}\n"
                    f"📅 {invite['start'][:16]}\n"
                    f"👤 From: {invite['organizer_name']}\n"
                    f"💬 {reason}"
                )
                # Block travel time if event has physical location
                _location = invite.get('location', '')
                if ok and _location and 'zoom' not in _location.lower() \
                   and 'meet' not in _location.lower() \
                   and 'teams' not in _location.lower() \
                   and 'http' not in _location.lower():
                    try:
                        from adapters.google_workspace.gws_connector import GWSConnector
                        _gws = GWSConnector()
                        _travel = _gws.block_travel_time(
                            event_id=invite['id'],
                            location=_location,
                            travel_minutes=30,
                        )
                        if _travel:
                            msg += '\n🚗 Travel blocks added (30 min each side).'
                    except Exception:
                        pass
                await channel.send(msg)

            elif recommendation == 'decline' and confidence == 'high':
                ok = respond_to_invite(invite['id'], 'declined')
                emoji = '❌' if ok else '⚠️'
                msg = (
                    f"{emoji} **Auto-declined:** {invite['title']}\n"
                    f"📅 {invite['start'][:16]}\n"
                    f"👤 From: {invite['organizer_name']}\n"
                    f"💬 {reason}"
                )
                await channel.send(msg)

            else:
                msg = (
                    f"📬 **Invite needs your decision:** {invite['title']}\n"
                    f"📅 {invite['start'][:16]}\n"
                    f"👤 From: {invite['organizer_name']}\n"
                    f"💬 DEX assessment: {reason}\n\n"
                    f"Reply `!accept {invite['id']}` or `!decline {invite['id']}`"
                )
                await channel.send(msg)

                try:
                    from adapters.calendar.meetings import create_meeting_record
                    create_meeting_record(
                        title=invite['title'],
                        person=invite['organizer_name'],
                        email=invite['organizer'],
                        date_iso=invite['start'],
                        source='Google Calendar',
                        meeting_type='Other',
                    )
                except Exception as e:
                    print(f'[InviteHandler] Meeting record failed: {e}')

            state[invite['id']] = {
                'processed_at': datetime.now(PDT).isoformat(),
                'recommendation': recommendation,
            }

        save_state(state)
        await client.close()

    await client.start(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == '__main__':
    asyncio.run(process_invites())
