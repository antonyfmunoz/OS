"""
Inline command handlers for Discord on_message.
Extracted from discord_bot.py — handles !followup, !travel,
!nomeetings, !confirm_event, !meetingroi, !competitive,
!documents, !audit, !stakeholders, !add_stakeholder,
and calendar write detection.

These are NOT @bot.command handlers — they are matched
via startswith() in on_message before gateway routing.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

PDT = ZoneInfo("America/Los_Angeles")


async def handle_followup(message, text: str) -> bool:
    """!followup <email_id> — draft a follow-up for a WAITING_ON email."""
    if not text.startswith("!followup"):
        return False

    email_id = text[9:].strip()
    try:
        from execution.runtime.model_router import get_router, TaskType

        router = get_router()
        model = router.route(TaskType.FAST_RESPONSE)
        draft = router.call(
            model,
            f"Draft a brief, professional follow-up email "
            f"for email ID {email_id}. "
            f"Use the founder's voice — direct, warm, short. "
            f"Subject: Following up. "
            f"Body: one sentence checking in on the status.",
        )
        await message.channel.send(
            f"📧 Follow-up draft:\n```\n{draft[:500]}\n```\nUse `!approve` to send."
        )
    except Exception as e:
        await message.channel.send(f"❌ Error: {e}")
    return True


async def handle_travel(message, text: str) -> bool:
    """!travel [event_id] | [location] | [minutes] — block travel time."""
    if not text.startswith("!travel"):
        return False

    parts = text[7:].strip().split("|")
    if len(parts) < 2:
        await message.channel.send(
            "Usage: `!travel [event_id] | [location] | [minutes optional]`"
        )
        return True
    try:
        from adapters.google_workspace.gws_connector import GWSConnector

        _event_id = parts[0].strip()
        _location = parts[1].strip()
        _minutes = int(parts[2].strip()) if len(parts) > 2 else 30
        _gws = GWSConnector()
        _result = _gws.block_travel_time(_event_id, _location, _minutes)
        if _result:
            await message.channel.send(
                f"🚗 Travel blocks created ({_minutes} min each side)."
            )
        else:
            await message.channel.send("❌ Failed to create travel blocks.")
    except Exception as e:
        await message.channel.send(f"❌ Error: {e}")
    return True


async def handle_nomeetings(message, text: str) -> bool:
    """!nomeetings [date] — block an entire day as no-meetings / deep work."""
    if not text.startswith("!nomeetings"):
        return False

    _parts = text.split()
    try:
        from adapters.google_workspace.gws_connector import GWSConnector

        _gws = GWSConnector()

        if len(_parts) > 1:
            from execution.runtime.model_router import get_router, TaskType

            _router = get_router()
            _model = _router.route(TaskType.FAST_RESPONSE)
            _date_str = _router.call(
                _model,
                f'Convert "{_parts[1]}" to a date in YYYY-MM-DD format. '
                f"Today is {datetime.now(PDT).strftime('%Y-%m-%d')}. "
                f"Return only the date string.",
            ).strip()
            try:
                _block_date = datetime.fromisoformat(_date_str).replace(tzinfo=PDT)
            except Exception:
                _block_date = datetime.now(PDT) + timedelta(days=1)
        else:
            _block_date = datetime.now(PDT) + timedelta(days=1)

        _block_start = _block_date.replace(hour=9, minute=0, second=0, microsecond=0)
        _gws.create_calendar_event(
            title="🚫 No Meetings Day — Deep Work",
            start_iso=_block_start.isoformat(),
            duration_minutes=9 * 60,
            description="Focus day. No meetings. DEX will decline all invites.",
        )

        from runtime.context import load_context_from_env
        from state.storage.db import get_conn

        _ctx = load_context_from_env()
        with get_conn(_ctx.org_id) as _cur:
            _cur.execute(
                """
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    str(_ctx.org_id),
                    "protected_day",
                    json.dumps(
                        {
                            "date": _block_date.strftime("%Y-%m-%d"),
                            "type": "no_meetings",
                        }
                    ),
                    "dex_calendar",
                ),
            )

        _date_display = _block_date.strftime("%A, %B %d")
        await message.channel.send(
            f"🚫 **{_date_display} blocked as a no-meetings day.**\n"
            f"Calendar blocked 9am–6pm. "
            f"Any invites for that day will be auto-declined."
        )
    except Exception as e:
        await message.channel.send(f"❌ Error: {e}")
    return True


async def handle_confirm_event(message, text: str, pending_events: dict) -> bool:
    """!confirm_event — create a calendar event after conflict warning."""
    if text.lower() != "!confirm_event":
        return False

    _ch_id = str(message.channel.id)
    if _ch_id in pending_events:
        _ev_data = pending_events.pop(_ch_id)
        try:
            from adapters.google_workspace.gws_connector import GWSConnector

            _gws = GWSConnector()
            _event = _gws.create_calendar_event(
                title=_ev_data.get("title", "Meeting"),
                start_iso=_ev_data.get("start_iso"),
                duration_minutes=_ev_data.get("duration_minutes", 60),
                attendee_email=_ev_data.get("attendee_email"),
                description=_ev_data.get("description", ""),
            )
            if _event:
                await message.channel.send(
                    f"✅ Created: **{_event['title']}**\n"
                    f"🕐 {_event.get('start', '')}\n"
                    f"🔗 {_event.get('meet_link', '')}"
                )
            else:
                await message.channel.send("❌ Failed to create event.")
        except Exception as e:
            await message.channel.send(f"❌ Error: {e}")
    else:
        await message.channel.send("No pending event to confirm.")
    return True


async def handle_meetingroi(message, text: str) -> bool:
    """!meetingroi [venture] — show meeting ROI for the last 30 days."""
    if not text.startswith("!meetingroi"):
        return False

    _parts = text.split()
    _venture = _parts[1] if len(_parts) > 1 else None
    try:
        from runtime.meetings import calculate_meeting_roi

        _roi = calculate_meeting_roi(venture=_venture, days=30)
        if not _roi or not _roi.get("total"):
            await message.channel.send("📊 No meeting data for the last 30 days.")
            return True
        _lines = [
            f"📊 **Meeting ROI — last 30 days"
            f"{'  (' + _venture + ')' if _venture else ''}:**",
            f"Total: {_roi['total']} | Completed: {_roi['completed']} | "
            f"No-show: {_roi['no_show']} | Cancelled: {_roi['cancelled']}",
            f"Completion rate: {_roi['conversion_rate']:.0%}",
        ]
        if _roi["top_converting_type"]:
            _lines.append(f"Best converting type: {_roi['top_converting_type']}")
        if _roi.get("by_type"):
            _lines.append("\n**By type:**")
            for _mtype, _mdata in _roi["by_type"].items():
                _mrate = (
                    _mdata["advanced"] / _mdata["total"] if _mdata["total"] > 0 else 0
                )
                _lines.append(
                    f"• {_mtype}: {_mdata['total']} meetings, "
                    f"{_mdata['advanced']} advanced ({_mrate:.0%})"
                )
        await message.channel.send("\n".join(_lines))
    except Exception as e:
        await message.channel.send(f"❌ Error: {e}")
    return True


async def handle_competitive(message, text: str) -> bool:
    """!competitive [venture] — synthesize competitive landscape."""
    if not text.startswith("!competitive"):
        return False

    _parts = text.split()
    _venture = _parts[1] if len(_parts) > 1 else "empyrean_creative"
    try:
        from understanding.intelligence.competitive_intel import synthesize_competitive_landscape

        _analysis = synthesize_competitive_landscape(_venture)
        await message.channel.send(
            f"🎯 **Competitive landscape — {_venture}:**\n{_analysis}"
        )
    except Exception as e:
        await message.channel.send(f"❌ Error: {e}")
    return True


async def handle_documents(message, text: str) -> bool:
    """!documents — show recently filed documents."""
    if text.lower() != "!documents":
        return False

    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn

        _ctx = load_context_from_env()
        with get_conn(_ctx.org_id) as _cur:
            _cur.execute(
                """
                SELECT payload_json, created_at FROM events
                WHERE org_id = %s
                AND event_type = 'document_filed'
                AND created_at >= NOW() - INTERVAL '30 days'
                ORDER BY created_at DESC
                LIMIT 10
            """,
                (str(_ctx.org_id),),
            )
            _rows = _cur.fetchall()

        if not _rows:
            await message.channel.send("📁 No documents filed in the last 30 days.")
            return True

        _lines = ["📁 **Recently filed documents:**"]
        for _r in _rows:
            _payload = _r["payload_json"]
            if isinstance(_payload, str):
                _payload = json.loads(_payload)
            _filename = _payload.get("filename", "Unknown")
            _folder = _payload.get("folder", "Unknown")
            _review = " ⚠️" if _payload.get("requires_review") else ""
            _lines.append(f"• {_filename} → {_folder}{_review}")

        await message.channel.send("\n".join(_lines))
    except Exception as e:
        await message.channel.send(f"❌ Error: {e}")
    return True


async def handle_audit(message, text: str) -> bool:
    """!audit [days] — show DEX action trail."""
    if not text.startswith("!audit"):
        return False

    _parts = text.split()
    _days = int(_parts[1]) if len(_parts) > 1 and _parts[1].isdigit() else 1
    try:
        from runtime.context import load_context_from_env
        from state.storage.db import get_conn

        _ctx = load_context_from_env()
        with get_conn(_ctx.org_id) as cur:
            cur.execute(
                """
                SELECT event_type, payload_json, created_at
                FROM events
                WHERE org_id = %s
                AND created_at >= NOW() - INTERVAL '%s days'
                AND event_type IN (
                    'decision', 'dex_task', 'meeting_scheduled',
                    'pipeline_entry', 'email_classified',
                    'approval_requested', 'approval_granted'
                )
                ORDER BY created_at DESC
                LIMIT 20
                """,
                (str(_ctx.org_id), _days),
            )
            _rows = cur.fetchall()

        if not _rows:
            await message.channel.send(
                f"📋 No audit events in the last {_days} day(s)."
            )
            return True

        _lines = [f"📋 **DEX Audit Log — last {_days} day(s):**"]
        for _r in _rows:
            _payload = _r["payload_json"]
            if isinstance(_payload, str):
                _payload = json.loads(_payload)
            _etype = _r["event_type"]
            _created = str(_r["created_at"])[:16]
            if _etype == "decision":
                _desc = _payload.get("description", "Decision")[:60]
                _lines.append(f"🎯 [{_created}] Decision: {_desc}")
            elif _etype == "dex_task":
                _task = _payload.get("task", "Task")[:60]
                _lines.append(f"✅ [{_created}] Task captured: {_task}")
            elif _etype == "meeting_scheduled":
                _person = _payload.get("person", "Unknown")
                _lines.append(f"📅 [{_created}] Meeting: {_person}")
            elif _etype == "pipeline_entry":
                _name = _payload.get("name", "Lead")[:40]
                _lines.append(f"📊 [{_created}] Pipeline: {_name}")
            else:
                _lines.append(f"📝 [{_created}] {_etype}")

        _full_audit = "\n".join(_lines)
        for i in range(0, len(_full_audit), 1900):
            await message.channel.send(_full_audit[i : i + 1900])
    except Exception as e:
        await message.channel.send(f"❌ Audit failed: {e}")
    return True


async def handle_stakeholders(message, text: str) -> bool:
    """!stakeholders [venture] — show stakeholder map."""
    if not text.lower().startswith("!stakeholders"):
        return False

    _parts = text.split()
    _venture = _parts[1] if len(_parts) > 1 else None
    try:
        from runtime.stakeholder_map import (
            get_stakeholders,
            generate_stakeholder_brief,
        )

        if _venture:
            _brief = generate_stakeholder_brief(_venture)
            _list = get_stakeholders(venture=_venture)
            _lines = [f"**Stakeholder map — {_venture}:**\n{_brief}\n"]
            _lines.append("**Contacts:**")
            for _s in _list[:8]:
                _lines.append(
                    f"• {_s['name']} — {_s['role']} "
                    f"({_s['influence']} influence, {_s['status']})"
                )
        else:
            _all = get_stakeholders()
            if not _all:
                await message.channel.send(
                    "No stakeholders mapped yet.\n"
                    "Add with: `!add_stakeholder [name] | [venture] | [role] | [high/medium/low]`"
                )
                return True
            _lines = [f"**All stakeholders ({len(_all)}):**"]
            for _s in _all[:10]:
                _lines.append(
                    f"• {_s['name']} — {_s['venture']} — "
                    f"{_s['role']} ({_s['influence']})"
                )
        await message.channel.send("\n".join(_lines))
    except Exception as e:
        await message.channel.send(f"❌ Error: {e}")
    return True


async def handle_add_stakeholder(message, text: str) -> bool:
    """!add_stakeholder [name] | [venture] | [role] | [influence] — add stakeholder."""
    if not text.lower().startswith("!add_stakeholder"):
        return False

    _parts = text[16:].strip().split("|")
    if len(_parts) < 3:
        await message.channel.send(
            "Usage: `!add_stakeholder [name] | [venture] | [role] | [high/medium/low]`"
        )
        return True
    try:
        from runtime.stakeholder_map import add_stakeholder

        _name = _parts[0].strip()
        _venture = _parts[1].strip()
        _role = _parts[2].strip()
        _influence = _parts[3].strip() if len(_parts) > 3 else "medium"
        _ok = add_stakeholder(
            name=_name,
            venture=_venture,
            role=_role,
            influence=_influence,
        )
        if _ok:
            await message.channel.send(
                f"✅ Stakeholder added: {_name} — {_venture} — {_role}"
            )
        else:
            await message.channel.send("❌ Failed to add stakeholder.")
    except Exception as e:
        await message.channel.send(f"❌ Error: {e}")
    return True


async def handle_calendar_write(message, text: str, pending_events: dict) -> bool:
    """Detect scheduling intent and handle calendar write directly."""
    _cal_keywords = [
        "schedule",
        "book",
        "set up a call",
        "set up a meeting",
        "reschedule",
        "cancel the",
        "move the",
        "block time",
        "add to calendar",
        "create an event",
    ]
    if not any(kw in text.lower() for kw in _cal_keywords):
        return False

    try:
        from adapters.google_workspace.gws_connector import GWSConnector

        _gws = GWSConnector()
        from execution.runtime.model_router import call_with_fallback

        _cal_prompt = (
            "Extract calendar event details from this message. "
            f"Today is {datetime.now(PDT).strftime('%A %B %d %Y')}. "
            'Return JSON only: {"action": "create|update|delete|list", "title": "", '
            '"start_iso": "ISO datetime in UTC", "duration_minutes": 60, '
            '"attendee_email": null, "description": "", "event_id": null}\n'
            f'Message: "{text}"'
        )
        _cal_result = call_with_fallback(prompt=_cal_prompt, task_type="fast_response")
        _parsed = json.loads(_cal_result.output.strip())
        _action = _parsed.get("action", "create")

        if _action == "create":
            if _parsed.get("start_iso"):
                try:
                    _conflicts = _gws.check_conflicts(
                        start_iso=_parsed["start_iso"],
                        duration_minutes=_parsed.get("duration_minutes", 60),
                    )
                    if _conflicts:
                        _conflict_names = ", ".join(c["title"] for c in _conflicts[:2])
                        await message.channel.send(
                            f"⚠️ **Conflict detected:** {_conflict_names}\n"
                            f"Still create the event? Reply `!confirm_event` "
                            f"or adjust the time."
                        )
                        pending_events[str(message.channel.id)] = _parsed
                        return True
                except Exception:
                    pass

            _event = _gws.create_calendar_event(
                title=_parsed.get("title", text[:50]),
                start_iso=_parsed.get("start_iso"),
                duration_minutes=_parsed.get("duration_minutes", 60),
                attendee_email=_parsed.get("attendee_email"),
                description=_parsed.get("description", ""),
            )
            if _event:
                _attendee = _parsed.get("attendee_email", "")
                _time_str = (
                    _gws.format_time_for_attendee(
                        _parsed.get("start_iso", ""),
                        _attendee,
                    )
                    if _attendee
                    else str(_event.get("start", ""))[:16]
                )
                await message.channel.send(
                    f"📅 Scheduled: **{_event['title']}**\n"
                    f"🕐 {_time_str}\n"
                    f"🔗 {_event.get('meet_link', 'No Meet link')}"
                )
                return True
        elif _action == "list":
            _events = _gws.list_calendar_events(days=14, query=_parsed.get("title"))
            if _events:
                _lines = ["📅 **Upcoming events:**"]
                for _e in _events[:5]:
                    _start = _e.get("start", {})
                    _dt = _start.get("dateTime", _start.get("date", ""))
                    _lines.append(f"• {_e.get('summary', 'Untitled')} — {_dt}")
                await message.channel.send("\n".join(_lines))
            else:
                await message.channel.send("📅 No upcoming events found.")
            return True
    except Exception as _cal_err:
        print(f"[Discord] Calendar handler failed: {_cal_err}")
        # Fall through to gateway
    return False


# Dispatch table for on_message — try each handler in order
INLINE_HANDLERS = [
    handle_followup,
    handle_travel,
    handle_nomeetings,
    handle_meetingroi,
    handle_competitive,
    handle_documents,
    handle_audit,
    handle_add_stakeholder,  # must be before stakeholders (prefix match)
    handle_stakeholders,
]


async def try_inline_commands(message, text: str, pending_events: dict) -> bool:
    """
    Try all inline command handlers.
    Returns True if one handled the message.
    """
    # confirm_event needs pending_events state
    if await handle_confirm_event(message, text, pending_events):
        return True

    # calendar write needs pending_events state
    if await handle_calendar_write(message, text, pending_events):
        return True

    for handler in INLINE_HANDLERS:
        if await handler(message, text):
            return True

    return False
