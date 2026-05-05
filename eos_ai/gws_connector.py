"""
GWSConnector — Google Workspace integration via gws CLI.

Provides calendar, tasks, drive, and gmail access for EOS agents.
All methods are safe — they log warnings on error and never crash.

Usage:
    from eos_ai.gws_connector import GWSConnector
    gws = GWSConnector()
    events = gws.get_today_events()
    tasks  = gws.get_tasks()
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path as _Path
from dotenv import load_dotenv as _load_dotenv
_ROOT = _Path(__file__).parent.parent
_load_dotenv(_ROOT / 'services' / '.env')
_load_dotenv(_ROOT / 'eos_ai' / '.env', override=True)

# Circuit breaker: if the CLI times out, skip further calls for this long.
# File-based so cron-spawned processes see each other's failures.
_GWS_COOLDOWN_FILE = "/tmp/gws_cooldown"
_GWS_COOLDOWN_SECONDS = 300  # 5 minutes
_GWS_TIMEOUT = int(os.getenv("GWS_CLI_TIMEOUT", "90"))


def _in_cooldown() -> float:
    """Return seconds remaining in cooldown, or 0 if clear."""
    try:
        ts = float(_Path(_GWS_COOLDOWN_FILE).read_text().strip())
    except Exception:
        return 0.0
    remaining = (ts + _GWS_COOLDOWN_SECONDS) - time.time()
    return max(0.0, remaining)


def _trip_cooldown() -> None:
    try:
        _Path(_GWS_COOLDOWN_FILE).write_text(str(time.time()))
    except Exception:
        pass


class GWSConnector:

    # ── Core runner ───────────────────────────────────────────────────────────

    def _run(
        self,
        *args,
        params: dict | None = None,
        body: dict | None = None,
    ) -> dict | None:
        """
        Run a gws CLI command and return parsed JSON, or None on error.
        Strips the "Using keyring backend: keyring" line before parsing.
        body is passed as --json for POST/PATCH request bodies.

        Circuit breaker: after a CLI timeout, subsequent calls short-circuit
        for _GWS_COOLDOWN_SECONDS to prevent cron timeout-spam.
        """
        remaining = _in_cooldown()
        if remaining > 0:
            print(
                f"[GWS] Skipping {' '.join(args)}: recent timeout, "
                f"cooldown {int(remaining)}s remaining"
            )
            return None

        cmd = ["npx", "@googleworkspace/cli"] + list(args)
        if params:
            cmd += ["--params", json.dumps(params)]
        if body:
            cmd += ["--json", json.dumps(body)]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=_GWS_TIMEOUT
            )
        except subprocess.TimeoutExpired:
            _trip_cooldown()
            print(
                f"[GWS] CLI timeout after {_GWS_TIMEOUT}s: {' '.join(args)} "
                f"— tripping {_GWS_COOLDOWN_SECONDS}s cooldown"
            )
            return None
        except Exception as e:
            print(f"[GWS] Command failed ({type(e).__name__}): {e}")
            return None

        if result.returncode != 0:
            stderr = (result.stderr or "").strip().splitlines()[-1:] or [""]
            print(
                f"[GWS] CLI exit={result.returncode}: {' '.join(args)} "
                f"— {stderr[0]}"
            )
            return None

        output = result.stdout
        lines = output.split("\n")
        clean = "\n".join(
            l for l in lines if not l.startswith("Using keyring")
        )
        clean = clean.strip()
        if not clean:
            return None
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            print(f"[GWS] JSON parse failed: {e} — output head: {clean[:120]!r}")
            return None

    # ── Calendar ──────────────────────────────────────────────────────────────

    def get_today_events(self) -> list[dict]:
        now   = datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end   = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
        data  = self._run(
            "calendar", "events", "list",
            params={
                "calendarId":   "primary",
                "timeMin":      start,
                "timeMax":      end,
                "maxResults":   20,
                "singleEvents": True,
                "orderBy":      "startTime",
            },
        )
        if not data:
            return []
        return [
            {
                "title":       e.get("summary", "Untitled"),
                "start":       e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                "end":         e.get("end",   {}).get("dateTime") or e.get("end",   {}).get("date"),
                "location":    e.get("location", ""),
                "description": e.get("description", "")[:200],
                "meet_link":   e.get("hangoutLink", ""),
            }
            for e in data.get("items", [])
        ]

    def get_upcoming_events(self, days: int = 7) -> list[dict]:
        now  = datetime.now(timezone.utc)
        end  = now + timedelta(days=days)
        data = self._run(
            "calendar", "events", "list",
            params={
                "calendarId":   "primary",
                "timeMin":      now.isoformat(),
                "timeMax":      end.isoformat(),
                "maxResults":   20,
                "singleEvents": True,
                "orderBy":      "startTime",
            },
        )
        if not data:
            return []
        return [
            {
                "title":     e.get("summary", "Untitled"),
                "start":     e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                "end":       e.get("end",   {}).get("dateTime") or e.get("end",   {}).get("date"),
                "location":  e.get("location", ""),
                "meet_link": e.get("hangoutLink", ""),
            }
            for e in data.get("items", [])
        ]

    def create_calendar_event(
        self,
        title: str,
        start_iso: str | None = None,
        duration_minutes: int = 60,
        attendee_email: str | None = None,
        description: str = "",
    ) -> dict | None:
        """
        Create a Google Calendar event with a Google Meet link.
        start_iso: ISO datetime string (UTC). Defaults to now + 5 minutes.
        Returns dict with title, start, meet_link, event_id or None on failure.
        """
        import uuid as _uuid
        now = datetime.now(timezone.utc)
        if start_iso:
            try:
                from dateutil.parser import parse as _parse
                start_dt = _parse(start_iso)
            except Exception:
                start_dt = now + timedelta(minutes=5)
        else:
            start_dt = now + timedelta(minutes=5)

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        params: dict = {
            "calendarId":           "primary",
            "conferenceDataVersion": 1,
            "body": {
                "summary":     title,
                "description": description,
                "start":  {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
                "end":    {"dateTime": end_dt.isoformat(),   "timeZone": "UTC"},
                "reminders": {
                    "useDefault": False,
                    "overrides": [{"method": "popup", "minutes": 10}],
                },
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(_uuid.uuid4()),
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
            },
        }
        if attendee_email:
            params["body"]["attendees"] = [{"email": attendee_email}]

        data = self._run("calendar", "events", "insert", params=params)
        if not data:
            return None
        return {
            "event_id":  data.get("id", ""),
            "title":     data.get("summary", title),
            "start":     data.get("start", {}).get("dateTime", ""),
            "meet_link": data.get("hangoutLink", ""),
        }

    def update_calendar_event(
        self,
        event_id: str,
        title: str | None = None,
        start_iso: str | None = None,
        duration_minutes: int | None = None,
        description: str | None = None,
    ) -> dict | None:
        """Update an existing calendar event."""
        event = self._run(
            "calendar", "events", "get",
            params={"calendarId": "primary", "eventId": event_id},
        )
        if not event:
            print(f"[GWS] update_calendar_event: event {event_id} not found")
            return None
        if title:
            event["summary"] = title
        if description:
            event["description"] = description
        if start_iso:
            from dateutil.parser import parse as _parse
            start_dt = _parse(start_iso)
            end_dt = start_dt + timedelta(minutes=duration_minutes or 60)
            event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "UTC"}
            event["end"]   = {"dateTime": end_dt.isoformat(),   "timeZone": "UTC"}
        updated = self._run(
            "calendar", "events", "update",
            params={"calendarId": "primary", "eventId": event_id, "body": event},
        )
        if not updated:
            return None
        return {"event_id": updated.get("id"), "title": updated.get("summary")}

    def delete_calendar_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        self._run(
            "calendar", "events", "delete",
            params={"calendarId": "primary", "eventId": event_id},
        )
        return True  # delete returns empty body; absence of exception = success

    def list_calendar_events(
        self,
        days: int = 14,
        query: str | None = None,
    ) -> list[dict]:
        """List events with optional search query."""
        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days)
        params: dict = {
            "calendarId":   "primary",
            "timeMin":      now.isoformat(),
            "timeMax":      time_max.isoformat(),
            "singleEvents": True,
            "orderBy":      "startTime",
        }
        if query:
            params["q"] = query
        data = self._run("calendar", "events", "list", params=params)
        if not data:
            return []
        return data.get("items", [])

    def check_conflicts(
        self,
        start_iso: str,
        duration_minutes: int = 60,
        buffer_minutes: int = 15,
    ) -> list[dict]:
        """
        Check for calendar conflicts including buffer time.
        Returns list of conflicting events.
        """
        try:
            from dateutil.parser import parse as _parse
            from datetime import timedelta

            start_dt = _parse(start_iso)
            check_start = start_dt - timedelta(minutes=buffer_minutes)
            check_end = start_dt + timedelta(minutes=duration_minutes + buffer_minutes)

            events = self.list_calendar_events(days=1)
            conflicts = []
            for event in events:
                ev_start = event.get('start', {})
                ev_start_str = ev_start.get('dateTime', ev_start.get('date', ''))
                if not ev_start_str:
                    continue
                try:
                    ev_dt = _parse(ev_start_str)
                    ev_end_str = event.get('end', {}).get(
                        'dateTime', event.get('end', {}).get('date', '')
                    )
                    ev_end_dt = _parse(ev_end_str) if ev_end_str else ev_dt + timedelta(hours=1)
                    if check_start < ev_end_dt and check_end > ev_dt:
                        conflicts.append({
                            'title': event.get('summary', 'Untitled'),
                            'start': ev_start_str,
                            'end': ev_end_str,
                        })
                except Exception:
                    continue
            return conflicts
        except Exception as e:
            print(f'[GWS] check_conflicts failed: {e}')
            return []

    def block_travel_time(
        self,
        event_id: str,
        location: str,
        travel_minutes: int = 30,
    ) -> dict:
        """
        Block travel time before and after an event
        that has a physical location.
        Returns dict with before_event and after_event created.
        """
        try:
            result = self._run('calendar', 'events', 'get',
                params={'calendarId': 'primary', 'eventId': event_id})
            if not result:
                return {}

            start_str = result.get('start', {}).get('dateTime', '')
            end_str = result.get('end', {}).get('dateTime', '')
            title = result.get('summary', 'Event')

            if not start_str or not end_str:
                return {}

            from dateutil.parser import parse as _parse
            from datetime import timedelta

            start_dt = _parse(start_str)
            end_dt = _parse(end_str)

            travel_before_start = start_dt - timedelta(minutes=travel_minutes)
            travel_after_start = end_dt

            created = {}

            before = self.create_calendar_event(
                title=f'🚗 Travel → {title}',
                start_iso=travel_before_start.isoformat(),
                duration_minutes=travel_minutes,
                description=f'Travel to: {location}',
            )
            if before:
                created['before'] = before

            after = self.create_calendar_event(
                title=f'🚗 Travel ← {title}',
                start_iso=travel_after_start.isoformat(),
                duration_minutes=travel_minutes,
                description=f'Travel from: {location}',
            )
            if after:
                created['after'] = after

            return created
        except Exception as e:
            print(f'[GWS] block_travel_time failed: {e}')
            return {}

    def detect_timezone_from_email(self, email: str) -> str:
        """
        Detect likely timezone from email domain.
        Returns timezone string e.g. 'America/New_York'.
        Falls back to 'America/Los_Angeles' (Antony's TZ).
        """
        if not email or '@' not in email:
            return 'America/Los_Angeles'

        domain = email.split('@')[-1].lower()

        TZ_MAP = {
            '.co.uk': 'Europe/London',
            '.uk': 'Europe/London',
            '.au': 'Australia/Sydney',
            '.ca': 'America/Toronto',
            '.de': 'Europe/Berlin',
            '.fr': 'Europe/Paris',
            '.jp': 'Asia/Tokyo',
            '.in': 'Asia/Kolkata',
            '.sg': 'Asia/Singapore',
            '.nz': 'Pacific/Auckland',
            '.br': 'America/Sao_Paulo',
            '.mx': 'America/Mexico_City',
        }

        for suffix, tz in TZ_MAP.items():
            if domain.endswith(suffix):
                return tz

        return 'America/Los_Angeles'

    def format_time_for_attendee(
        self,
        dt_iso: str,
        attendee_email: str,
    ) -> str:
        """
        Format a datetime in both Antony's timezone and
        the attendee's detected timezone.
        """
        try:
            from zoneinfo import ZoneInfo
            from dateutil.parser import parse as _parse

            dt = _parse(dt_iso)
            pdt = ZoneInfo('America/Los_Angeles')
            attendee_tz_str = self.detect_timezone_from_email(attendee_email)
            attendee_tz = ZoneInfo(attendee_tz_str)

            dt_pdt = dt.astimezone(pdt)
            dt_attendee = dt.astimezone(attendee_tz)

            pdt_str = dt_pdt.strftime('%A %B %d at %-I:%M %p PDT')

            if attendee_tz_str == 'America/Los_Angeles':
                return pdt_str

            attendee_str = dt_attendee.strftime('%-I:%M %p')
            tz_abbr = dt_attendee.strftime('%Z')
            return f'{pdt_str} ({attendee_str} {tz_abbr} your time)'
        except Exception as e:
            return dt_iso[:16]

    # ── Tasks ─────────────────────────────────────────────────────────────────

    TASKLIST_ID = "MTI0OTc0NTUyNTc5NjUzNjQwOTI6MDow"

    def get_tasks(self) -> list[dict]:
        data = self._run(
            "tasks", "tasks", "list",
            params={
                "tasklist":      self.TASKLIST_ID,
                "showCompleted": False,
                "maxResults":    50,
            },
        )
        if not data:
            return []
        return [
            {
                "id":     t.get("id"),
                "title":  t.get("title", ""),
                "notes":  t.get("notes", ""),
                "due":    t.get("due", ""),
                "status": t.get("status", ""),
            }
            for t in data.get("items", [])
            if t.get("status") != "completed"
        ]

    def create_task(
        self,
        title: str,
        notes: str = "",
        due: str | None = None,
    ) -> dict | None:
        params: dict = {
            "tasklist": self.TASKLIST_ID,
            "title":    title,
        }
        if notes:
            params["notes"] = notes
        if due:
            params["due"] = due
        return self._run("tasks", "tasks", "insert", params=params)

    def complete_task(self, task_id: str) -> bool:
        result = self._run(
            "tasks", "tasks", "patch",
            params={
                "tasklist": self.TASKLIST_ID,
                "task":     task_id,
                "status":   "completed",
            },
        )
        return result is not None

    # ── Drive ─────────────────────────────────────────────────────────────────

    def search_drive(self, query: str, max_results: int = 10) -> list[dict]:
        data = self._run(
            "drive", "files", "list",
            params={
                "q":        query,
                "pageSize": max_results,
                "fields":   "files(id,name,mimeType,modifiedTime)",
            },
        )
        if not data:
            return []
        return data.get("files", [])

    def read_document(self, file_id: str) -> str:
        """Export a Google Doc as plain text (first 5000 chars)."""
        try:
            result = subprocess.run(
                [
                    "npx", "@googleworkspace/cli", "drive", "files", "export",
                    "--params",
                    json.dumps({"fileId": file_id, "mimeType": "text/plain"}),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout[:5000]
        except Exception:
            return ""

    def create_folder(self, name: str, parent_id: str = None) -> dict:
        """Create a folder in Google Drive."""
        try:
            params: dict = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder',
            }
            if parent_id:
                params['parents'] = [parent_id]
            result = self._run('drive', 'files', 'create', params=params)
            return result or {}
        except Exception as e:
            print(f'[GWS] create_folder failed: {e}')
            return {}

    def move_file(self, file_id: str, new_parent_id: str) -> bool:
        """Move a file to a different folder."""
        try:
            result = self._run('drive', 'files', 'update', params={
                'fileId': file_id,
                'addParents': new_parent_id,
                'removeParents': 'root',
            })
            return bool(result)
        except Exception as e:
            print(f'[GWS] move_file failed: {e}')
            return False

    def list_files(
        self,
        folder_id: str = None,
        query: str = None,
        max_results: int = 20,
    ) -> list[dict]:
        """List files in Drive, optionally filtered by folder or query."""
        try:
            params: dict = {'maxResults': max_results}
            if folder_id:
                params['q'] = f"'{folder_id}' in parents"
            elif query:
                params['q'] = query
            result = self._run('drive', 'files', 'list', params=params)
            return result.get('files', []) if result else []
        except Exception as e:
            print(f'[GWS] list_files failed: {e}')
            return []

    def rename_file(self, file_id: str, new_name: str) -> bool:
        """Rename a file or folder."""
        try:
            result = self._run('drive', 'files', 'update', params={
                'fileId': file_id,
                'name': new_name,
            })
            return bool(result)
        except Exception as e:
            print(f'[GWS] rename_file failed: {e}')
            return False

    def create_document(
        self,
        title: str,
        content: str = '',
        folder_id: str = None,
    ) -> dict:
        """Create a new Google Doc."""
        try:
            params: dict = {
                'name': title,
                'mimeType': 'application/vnd.google-apps.document',
            }
            if folder_id:
                params['parents'] = [folder_id]
            result = self._run('drive', 'files', 'create', params=params)
            return result or {}
        except Exception as e:
            print(f'[GWS] create_document failed: {e}')
            return {}

    def get_drive_structure(self, max_folders: int = 20) -> list[dict]:
        """Get the top-level folder structure of Drive."""
        try:
            result = self._run('drive', 'files', 'list', params={
                'q': "mimeType='application/vnd.google-apps.folder' and 'root' in parents",
                'maxResults': max_folders,
            })
            return result.get('files', []) if result else []
        except Exception as e:
            print(f'[GWS] get_drive_structure failed: {e}')
            return []

    def audit_drive(self) -> dict:
        """
        Audit Drive for organization issues:
        - Files in root (should be in folders)
        - Untitled documents
        """
        issues: dict = {'root_files': [], 'untitled': [], 'orphaned': []}
        try:
            root_files = self._run('drive', 'files', 'list', params={
                'q': "'root' in parents and mimeType!='application/vnd.google-apps.folder'",
                'maxResults': 20,
            })
            if root_files:
                issues['root_files'] = root_files.get('files', [])

            untitled = self._run('drive', 'files', 'list', params={
                'q': "name contains 'Untitled'",
                'maxResults': 10,
            })
            if untitled:
                issues['untitled'] = untitled.get('files', [])

            return issues
        except Exception as e:
            print(f'[GWS] audit_drive failed: {e}')
            return issues

    # ── Gmail ─────────────────────────────────────────────────────────────────

    def get_recent_emails(
        self,
        max_results: int = 10,
        query: str = "",
    ) -> list[dict]:
        params: dict = {"userId": "me", "maxResults": max_results}
        if query:
            params["q"] = query
        data = self._run("gmail", "users", "messages", "list", params=params)
        if not data:
            return []

        messages = []
        for msg in data.get("messages", [])[:max_results]:
            detail = self._run(
                "gmail", "users", "messages", "get",
                params={
                    "userId":          "me",
                    "id":              msg["id"],
                    "format":          "metadata",
                    "metadataHeaders": ["Subject", "From", "Date"],
                },
            )
            if detail:
                headers = {
                    h["name"]: h["value"]
                    for h in detail.get("payload", {}).get("headers", [])
                }
                messages.append(
                    {
                        "id":      msg["id"],
                        "subject": headers.get("Subject", ""),
                        "from":    headers.get("From", ""),
                        "date":    headers.get("Date", ""),
                        "snippet": detail.get("snippet", "")[:200],
                    }
                )
        return messages

    def search_emails_from(
        self,
        sender: str,
        max_results: int = 5,
    ) -> list[dict]:
        return self.get_recent_emails(
            max_results=max_results,
            query=f"from:{sender}",
        )

    def audit_inbox(
        self,
        save_path: str = '/opt/OS/data/gmail_audit.json',
    ) -> dict:
        """
        Read-only audit of current Gmail state.
        Lists all labels, counts inbox emails, samples senders.
        Saves result to save_path. No changes made.
        """
        import json as _json
        from pathlib import Path as _P

        # List all labels
        labels_data = self._run(
            'gmail', 'users', 'labels', 'list',
            params={'userId': 'me'},
        )
        labels: list[dict] = (
            labels_data.get('labels', []) if labels_data else []
        )

        # Count total inbox messages (IDs only — no detail fetch)
        messages_data = self._run(
            'gmail', 'users', 'messages', 'list',
            params={'userId': 'me', 'maxResults': 500, 'q': 'in:inbox'},
        )
        message_list: list[dict] = (
            messages_data.get('messages', []) if messages_data else []
        )
        total_inbox = len(message_list)

        # Fetch metadata for up to 20 sample emails
        samples: list[dict] = []
        for msg in message_list[:20]:
            detail = self._run(
                'gmail', 'users', 'messages', 'get',
                params={
                    'userId':          'me',
                    'id':              msg['id'],
                    'format':          'metadata',
                    'metadataHeaders': ['Subject', 'From', 'Date'],
                },
            )
            if detail:
                hdrs = {
                    h['name']: h['value']
                    for h in detail.get('payload', {}).get('headers', [])
                }
                samples.append({
                    'id':      msg['id'],
                    'from':    hdrs.get('From', ''),
                    'subject': hdrs.get('Subject', ''),
                    'date':    hdrs.get('Date', ''),
                })

        # Count messages per user-created label (estimate)
        label_counts: dict[str, int] = {}
        for label in labels:
            if label.get('type') == 'user':
                count_data = self._run(
                    'gmail', 'users', 'messages', 'list',
                    params={
                        'userId':     'me',
                        'maxResults': 1,
                        'q':          f'label:{label["name"]}',
                    },
                )
                if count_data is not None:
                    label_counts[label['name']] = (
                        count_data.get('resultSizeEstimate', 0)
                    )

        audit = {
            'existing_labels': [
                {
                    'id':   l['id'],
                    'name': l['name'],
                    'type': l.get('type', ''),
                }
                for l in labels
            ],
            'total_inbox':     total_inbox,
            'label_counts':    label_counts,
            'sample_senders':  list({s['from'] for s in samples}),
            'sample_subjects': [s['subject'] for s in samples[:10]],
        }

        _P(save_path).parent.mkdir(parents=True, exist_ok=True)
        _P(save_path).write_text(_json.dumps(audit, indent=2))

        print(f'[Audit] Labels: {len(labels)}')
        print(f'[Audit] Inbox emails: {total_inbox}')
        print(f'[Audit] Saved → {save_path}')

        return audit

    def get_all_inbox_emails(
        self,
        max_results: int = 500,
    ) -> list[dict]:
        """Get ALL inbox emails (read + unread) for Inbox Zero processing."""
        params: dict = {
            "userId":     "me",
            "maxResults": max_results,
            "q":          "in:inbox",
        }
        data = self._run(
            "gmail", "users", "messages", "list",
            params=params,
        )
        if not data:
            return []

        messages = []
        for msg in data.get("messages", [])[:max_results]:
            detail = self._run(
                "gmail", "users", "messages", "get",
                params={
                    "userId":          "me",
                    "id":              msg["id"],
                    "format":          "metadata",
                    "metadataHeaders": ["Subject", "From", "Date"],
                },
            )
            if detail:
                headers = {
                    h["name"]: h["value"]
                    for h in detail.get("payload", {}).get("headers", [])
                }
                messages.append({
                    "id":      msg["id"],
                    "subject": headers.get("Subject", ""),
                    "from":    headers.get("From", ""),
                    "date":    headers.get("Date", ""),
                    "snippet": detail.get("snippet", "")[:200],
                })
        return messages

    def get_or_create_label(self, label_name: str) -> str | None:
        """Return Gmail label ID for label_name, creating it if needed."""
        data = self._run(
            "gmail", "users", "labels", "list",
            params={"userId": "me"},
        )
        if data:
            for label in data.get("labels", []):
                if label.get("name") == label_name:
                    return label["id"]
        # Not found — create it
        result = self._run(
            "gmail", "users", "labels", "create",
            params={"userId": "me"},
            body={"name": label_name},
        )
        if result:
            print(f"[GWS] Created label: {label_name} ({result.get('id')})")
            return result.get("id")
        print(f"[GWS] Failed to create label: {label_name}")
        return None

    def apply_label_to_message(
        self,
        message_id: str,
        add_label_ids: list[str],
        remove_label_ids: list[str] | None = None,
    ) -> bool:
        """Add/remove labels on a message. Returns True on success."""
        body: dict = {"addLabelIds": add_label_ids}
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        result = self._run(
            "gmail", "users", "messages", "modify",
            params={"userId": "me", "id": message_id},
            body=body,
        )
        return result is not None

    def delete_label(self, label_id: str) -> bool:
        """Permanently delete a Gmail label by ID."""
        result = self._run(
            "gmail", "users", "labels", "delete",
            params={"userId": "me", "id": label_id},
        )
        # delete returns empty body on success (None from _run), check stderr
        return True  # _run only returns None on exception; absence of output = success

    def get_messages_by_label(
        self,
        label_id: str,
        max_results: int = 500,
    ) -> list[dict]:
        """List message IDs for a given label."""
        results: list[dict] = []
        page_token: str | None = None

        while len(results) < max_results:
            params: dict = {
                "userId":     "me",
                "labelIds":   [label_id],
                "maxResults": min(500, max_results - len(results)),
            }
            if page_token:
                params["pageToken"] = page_token

            data = self._run(
                "gmail", "users", "messages", "list",
                params=params,
            )
            if not data:
                break

            results.extend(data.get("messages", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return results

    def batch_modify_messages(
        self,
        message_ids: list[str],
        add_label_ids: list[str] | None = None,
        remove_label_ids: list[str] | None = None,
    ) -> bool:
        """Apply label changes to multiple messages in one call."""
        if not message_ids:
            return True
        body: dict = {"ids": message_ids}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        result = self._run(
            "gmail", "users", "messages", "batchModify",
            params={"userId": "me"},
            body=body,
        )
        return result is not None

    def get_message_headers(
        self,
        message_id: str,
        headers: list[str],
    ) -> dict:
        """Fetch specific headers from a message. Returns {header_name: value}."""
        data = self._run(
            "gmail", "users", "messages", "get",
            params={
                "userId":          "me",
                "id":              message_id,
                "format":          "metadata",
                "metadataHeaders": headers,
            },
        )
        if not data:
            return {}
        return {
            h["name"]: h["value"]
            for h in data.get("payload", {}).get("headers", [])
        }

    def list_all_labels(self) -> list[dict]:
        """Return all Gmail labels with id, name, type."""
        data = self._run(
            "gmail", "users", "labels", "list",
            params={"userId": "me"},
        )
        if not data:
            return []
        return [
            {"id": l["id"], "name": l["name"], "type": l.get("type", "")}
            for l in data.get("labels", [])
        ]

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: list = None,
        reply_to: str = None,
    ) -> dict:
        """
        Send an email via Gmail API.
        Returns sent message dict or empty dict on failure.
        """
        try:
            import base64
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart('alternative')
            msg['To'] = to_email
            msg['Subject'] = subject
            if cc:
                msg['Cc'] = ', '.join(cc)
            if reply_to:
                msg['Reply-To'] = reply_to

            # Plain text part
            msg.attach(MIMEText(body, 'plain'))

            raw = base64.urlsafe_b64encode(
                msg.as_bytes()
            ).decode('utf-8')

            result = self._run('gmail', 'users.messages', 'send',
                params={
                    'userId': 'me',
                    'raw': raw,
                })
            return result or {}
        except Exception as e:
            print(f'[GWS] send_email failed: {e}')
            return {}
