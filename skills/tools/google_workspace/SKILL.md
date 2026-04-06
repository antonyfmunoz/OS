---
name: google_workspace
description: "Use when any agent needs to interact with Gmail, Google Calendar, Google Drive, Google Docs, Google Sheets, or Google Tasks — including reading inbox, scheduling events, searching files, scanning documents, managing labels, or handling OAuth/auth issues across any Google service."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developers.google.com/workspace"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Gmail v1, Calendar v3, Drive v3, Sheets v4, Tasks v1"
sdk_version: "@googleworkspace/cli (npx) — subprocess wrapper"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: Google Workspace (Consolidated)

## What This Tool Does

Google Workspace APIs provide programmatic access to Gmail, Google Calendar,
Google Drive, Google Docs, Google Sheets, and Google Tasks. EOS wraps all
Google services through a single connector class (`GWSConnector`) that shells
out to the `@googleworkspace/cli` npm package via `npx`. This avoids managing
the Python `google-api-python-client` SDK directly and delegates OAuth token
management to the CLI's keyring backend.

Core capabilities used by EOS:
- **Gmail** -- inbox scanning, label management, email classification (Dan Martell GPS system), send emails, batch modify
- **Calendar** -- event listing, creation, updates, deletion, conflict checking, invite handling, travel time blocking
- **Drive** -- file search, document export, folder creation, file moves, audit
- **Docs** -- plain-text export for knowledge ingestion (GWS Document Scanner)
- **Tasks** -- task listing, creation, completion
- **Sheets** -- not yet integrated; planned for pipeline/metrics dashboards

## EOS Integration

### Primary module: `eos_ai/gws_connector.py`

The `GWSConnector` class is the single entry point for all Google Workspace
operations in EOS. Every method calls `self._run()` which executes:

```python
cmd = ["npx", "@googleworkspace/cli"] + list(args)
if params:
    cmd += ["--params", json.dumps(params)]
if body:
    cmd += ["--json", json.dumps(body)]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
```

All methods are safe -- they return `None` or `[]` on error, never crash.

### Consumers (who calls GWSConnector)

| Consumer | Service | What it does |
|---|---|---|
| `services/discord_bot.py` | Gmail, Calendar | Inbox checks, event queries from Discord commands |
| `services/telegram_control.py` | Calendar, Gmail | Meeting scheduling, email search from Telegram |
| `services/handlers/cc_command_handler.py` | Calendar, Gmail, Drive | Claude Code command routing |
| `scripts/calendar_invite_handler.py` | Calendar | Polls pending invites, AI-assesses, accepts/declines |
| `eos_ai/orchestrator.py` | Calendar | Morning brief: today's events |
| `eos_ai/email_gps.py` | Gmail | Dan Martell 7-folder inbox classification |
| `eos_ai/eod_closing_loop.py` | Calendar | End-of-day calendar review |
| `eos_ai/daily_sync.py` | Calendar, Gmail | Daily sync context |
| `scripts/call_prep.py` | Calendar | Pre-meeting prep briefs |
| `scripts/midday_checkin.py` | Calendar | Midday schedule check |

### Document scanner: `eos_ai/gws_scanner.py`

The `GWSDocumentScanner` is a separate class (not part of GWSConnector) that:
1. Lists all Google Docs in Drive via the GWS CLI
2. Exports each doc as plain text
3. AI-assesses relevance and venture mapping using AgentRuntime
4. Chunks large docs (3000 chars) and ingests via KnowledgeIntegrator to Neon
5. Deduplicates against previously ingested docs by checking `events` table
6. Generates a founder profile (4 sections) and posts to Discord

Status: Built 2026-03-25, ingested 22/24 docs. **Auth expired 2026-04-03** -- needs re-auth via `npx @googleworkspace/cli auth login`.

## Authentication

### How EOS authenticates: GWS CLI keyring

EOS does NOT use `google-api-python-client` or `google-auth` Python packages.
All auth is handled by the `@googleworkspace/cli` npm package which stores
OAuth2 tokens in the system keyring.

**Initial setup:**
```bash
npx @googleworkspace/cli auth login
```
This opens a browser OAuth consent flow. The resulting access + refresh tokens
are stored in the system keyring. The CLI handles token refresh automatically
on each invocation.

**Auth verification:**
```bash
npx @googleworkspace/cli calendar events list --params '{"calendarId":"primary","maxResults":1}'
```
If this returns JSON, auth is valid. If it errors, run `auth login` again.

**Known issue:** The GWS CLI prints `Using keyring backend: keyring` as a
prefix line. Both `GWSConnector._run()` and `GWSDocumentScanner._run()` strip
this line before JSON parsing.

### Required OAuth scopes

The GWS CLI requests these scopes during `auth login`:
- `https://www.googleapis.com/auth/gmail.modify` -- read, send, label, trash
- `https://www.googleapis.com/auth/gmail.send` -- send emails
- `https://www.googleapis.com/auth/calendar` -- full calendar access
- `https://www.googleapis.com/auth/drive` -- full drive access
- `https://www.googleapis.com/auth/tasks` -- full tasks access
- `https://www.googleapis.com/auth/documents.readonly` -- read Google Docs

### Env vars

No Google-specific env vars in `.env` files. Auth is entirely keyring-based
via the GWS CLI. The CLI uses a Google Cloud project with OAuth credentials
configured in the Google Cloud Console.

### Token expiry pattern

OAuth access tokens expire after 1 hour. The GWS CLI automatically uses the
refresh token to obtain new access tokens. Refresh tokens can be revoked or
expire if:
- User revokes access in Google Account settings
- Token unused for 6 months (Google policy)
- OAuth consent screen is in "testing" mode and token is >7 days old

**This is what happened 2026-04-03.** The testing-mode 7-day expiry is the
most likely cause. Fix: publish the OAuth consent screen or re-auth weekly.

## Quick Reference

### Gmail: list recent emails
```python
from eos_ai.gws_connector import GWSConnector
gws = GWSConnector()
emails = gws.get_recent_emails(max_results=10, query="is:unread")
# Returns: [{"id", "subject", "from", "date", "snippet"}, ...]
```

### Gmail: search emails from a sender
```python
emails = gws.search_emails_from("alex@company.com", max_results=5)
```

### Gmail: send an email
```python
result = gws.send_email(
    to_email="lead@company.com",
    subject="Following up",
    body="Hi, just checking in...",
    cc=["team@company.com"],
)
```

### Gmail: label management
```python
label_id = gws.get_or_create_label("To Respond")
gws.apply_label_to_message(msg_id, add_label_ids=[label_id])
gws.batch_modify_messages(msg_ids, add_label_ids=[label_id], remove_label_ids=["INBOX"])
```

### Gmail: audit inbox
```python
audit = gws.audit_inbox(save_path="/opt/OS/data/gmail_audit.json")
# Returns: {existing_labels, total_inbox, label_counts, sample_senders, sample_subjects}
```

### Calendar: today's events
```python
events = gws.get_today_events()
# Returns: [{"title", "start", "end", "location", "description", "meet_link"}, ...]
```

### Calendar: create event with Google Meet
```python
event = gws.create_calendar_event(
    title="Discovery Call - Alex",
    start_iso="2026-04-10T14:00:00-07:00",
    duration_minutes=30,
    attendee_email="alex@company.com",
    description="Initiate Arena discovery",
)
# Returns: {"event_id", "title", "start", "meet_link"}
```

### Calendar: check for conflicts
```python
conflicts = gws.check_conflicts(
    start_iso="2026-04-10T14:00:00-07:00",
    duration_minutes=30,
    buffer_minutes=15,
)
```

### Calendar: block travel time
```python
created = gws.block_travel_time(event_id, location="123 Main St", travel_minutes=30)
```

### Drive: search files
```python
files = gws.search_drive("name contains 'Initiate Arena'", max_results=10)
# Returns: [{"id", "name", "mimeType", "modifiedTime"}, ...]
```

### Drive: read a Google Doc as plain text
```python
content = gws.read_document(file_id)  # Returns first 5000 chars
```

### Drive: folder operations
```python
folder = gws.create_folder("Meeting Notes", parent_id="root_folder_id")
gws.move_file(file_id, new_parent_id=folder["id"])
gws.rename_file(file_id, "New Name")
```

### Drive: audit for organization issues
```python
issues = gws.audit_drive()
# Returns: {"root_files": [...], "untitled": [...], "orphaned": [...]}
```

### Tasks: list and manage
```python
tasks = gws.get_tasks()  # Returns: [{"id", "title", "notes", "due", "status"}, ...]
gws.create_task("Follow up with Alex", notes="Re: Initiate Arena", due="2026-04-10")
gws.complete_task(task_id)
```

### Document Scanner: full knowledge ingestion
```python
from eos_ai.context import load_context_from_env
from eos_ai.gws_scanner import GWSDocumentScanner
ctx = load_context_from_env()
scanner = GWSDocumentScanner(ctx)
docs = scanner.scan_all(limit=200, incremental=True)
scanner.ingest_to_eos(docs)
scanner.save_context_summary(docs)
profile = scanner.generate_founder_profile(docs)
```

## Conceptual Model

```
Google Cloud Project (OAuth2 credentials)
  |
  +-- @googleworkspace/cli (npm)
  |     |-- auth login → OAuth2 consent → keyring storage
  |     |-- Handles token refresh automatically
  |     +-- Returns JSON to stdout
  |
  +-- GWSConnector (eos_ai/gws_connector.py)
  |     |-- _run() → subprocess.run(["npx", "@googleworkspace/cli", ...])
  |     |-- Strips "Using keyring" prefix before JSON parse
  |     |-- Returns parsed dict or None (never crashes)
  |     |
  |     +-- Gmail section
  |     |     |-- get_recent_emails(), search_emails_from()
  |     |     |-- get_all_inbox_emails(), audit_inbox()
  |     |     |-- send_email(), get_or_create_label()
  |     |     |-- apply_label_to_message(), batch_modify_messages()
  |     |     |-- delete_label(), get_messages_by_label()
  |     |     +-- get_message_headers(), list_all_labels()
  |     |
  |     +-- Calendar section
  |     |     |-- get_today_events(), get_upcoming_events()
  |     |     |-- create_calendar_event() (with Meet link)
  |     |     |-- update_calendar_event(), delete_calendar_event()
  |     |     |-- list_calendar_events(), check_conflicts()
  |     |     |-- block_travel_time()
  |     |     +-- detect_timezone_from_email(), format_time_for_attendee()
  |     |
  |     +-- Drive section
  |     |     |-- search_drive(), read_document()
  |     |     |-- create_folder(), move_file(), rename_file()
  |     |     |-- list_files(), create_document()
  |     |     |-- get_drive_structure(), audit_drive()
  |     |
  |     +-- Tasks section
  |           |-- get_tasks(), create_task(), complete_task()
  |           +-- TASKLIST_ID hardcoded (founder's default list)
  |
  +-- GWSDocumentScanner (eos_ai/gws_scanner.py)
        |-- list_all_docs() → Drive API (docs only)
        |-- read_doc() → Drive export as text/plain
        |-- understand_doc() → AI assessment via AgentRuntime
        |-- scan_all() → full pipeline with dedup
        |-- ingest_to_eos() → KnowledgeIntegrator → Neon
        +-- generate_founder_profile() → 4-section AI summary
```

See references/best_practices.md for rate limits, error codes, and anti-patterns.

## Gotchas

### Auth expires in testing mode after 7 days
If the Google Cloud OAuth consent screen is in "testing" mode (not published),
refresh tokens expire after 7 days. This is what caused the 2026-04-03 auth
failure. Fix: either publish the consent screen (requires Google review for
sensitive scopes) or re-run `npx @googleworkspace/cli auth login` weekly.

### "Using keyring backend: keyring" prefix in stdout
The GWS CLI prints this line before JSON output. Both `GWSConnector._run()` and
`GWSDocumentScanner._run()` filter it out. If you add a new GWS CLI caller,
you must strip this prefix or JSON parsing will fail with a cryptic error.

### subprocess timeout of 30 seconds
`GWSConnector._run()` has `timeout=30`. `GWSDocumentScanner._run()` uses
`timeout=60`. Large Drive exports or slow network can hit the 30s limit.
If operations start timing out, increase the timeout.

### Calendar events: dateTime vs date
All-day events use `start.date` (YYYY-MM-DD string). Timed events use
`start.dateTime` (ISO 8601). EOS methods handle both with fallback:
`e.get("start", {}).get("dateTime") or e.get("start", {}).get("date")`.
Always use this pattern.

### Gmail messages.list returns IDs only
`gmail users messages list` returns `[{"id": "...", "threadId": "..."}]` --
not message content. You must call `messages.get` for each message to get
headers, snippet, or body. EOS does this in a loop which is slow for large
inboxes. Use the `q` parameter to filter first.

### Gmail batch modify: max 1000 message IDs
`batchModify` accepts up to 1000 message IDs per call. For larger batches,
split into chunks of 1000.

### Drive export vs download
Google Docs/Sheets/Slides use `files.export` (converts to requested mimeType).
Binary files (PDFs, images) use `files.get` with `alt=media`. Using the wrong
method returns an error or empty content.

### Google Meet link requires conferenceDataVersion=1
When creating calendar events with Meet links, you must pass
`conferenceDataVersion: 1` as a parameter AND include a `conferenceData`
object with a `createRequest`. Missing either one silently creates the event
without a Meet link.

### GWSConnector.send_email uses MIME encoding
The `send_email()` method constructs a MIME message and base64url-encodes it
before passing to the GWS CLI. If the CLI expects a different format, this
will silently fail. Verify sends by checking the Gmail Sent folder.

### TASKLIST_ID is hardcoded
`GWSConnector.TASKLIST_ID` is hardcoded to the founder's default task list.
This is instance-specific and will break if the task list is deleted or if
EOS is deployed for a different user. Should be moved to .env or BIS.

### Document scanner rate limiting
`GWSDocumentScanner.scan_all()` adds `time.sleep(0.3)` between AI assessment
calls, but not between Drive API calls. A full scan of 200 docs makes 400+
API calls (list + export for each). This can hit Drive rate limits
(1000 queries per 100 seconds per user).
