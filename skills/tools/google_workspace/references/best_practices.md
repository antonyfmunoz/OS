# Google Workspace — Creator-Level Best Practices
Source: https://developers.google.com/workspace
API Version: Gmail v1, Calendar v3, Drive v3, Sheets v4, Tasks v1
SDK Version: @googleworkspace/cli (npx subprocess wrapper)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

### OAuth2 flow (user consent)
EOS uses **OAuth2 with user consent** via the `@googleworkspace/cli` npm package.
The CLI handles the full OAuth2 authorization code flow:

1. `npx @googleworkspace/cli auth login` opens browser
2. User signs in to Google, grants requested scopes
3. CLI receives authorization code, exchanges for access + refresh tokens
4. Tokens stored in system keyring (platform-specific: libsecret on Linux)
5. On each CLI invocation, access token checked; if expired, refresh token used automatically

**Token types:**
- Access token: 1 hour lifetime, auto-refreshed by CLI
- Refresh token: long-lived, stored in keyring. Expires if:
  - User revokes in Google Account > Security > Third-party apps
  - Token unused for 6 months
  - OAuth consent screen in "testing" mode: **7-day hard expiry**
  - Google Cloud project credentials rotated

**Required scopes per service:**

| Service | Scope | Grants |
|---|---|---|
| Gmail (read/modify) | `gmail.modify` | Read, send, trash, label — everything except permanent delete |
| Gmail (send only) | `gmail.send` | Compose and send only |
| Gmail (read only) | `gmail.readonly` | Read messages and metadata |
| Calendar | `calendar` | Full read/write to all calendars |
| Calendar (read only) | `calendar.readonly` | Read events only |
| Drive | `drive` | Full read/write to all files |
| Drive (read only) | `drive.readonly` | Read and download files |
| Sheets | `spreadsheets` | Full read/write to spreadsheets |
| Tasks | `tasks` | Full read/write to task lists and tasks |
| Docs (read only) | `documents.readonly` | Read document content |

**EOS auth location:** System keyring on VPS (100.77.233.50). No env vars for Google tokens.
No `credentials.json` or `token.json` files on disk -- all managed by CLI keyring backend.

**Service accounts vs user consent:**
EOS uses user consent (not service accounts) because it acts on behalf of the founder's
personal Google account. Service accounts are for server-to-server auth where no user
interaction is needed (e.g., internal company tools accessing a shared Drive). Service
accounts cannot access a user's Gmail without domain-wide delegation (Workspace admin required).

**Re-auth procedure (when tokens expire):**
```bash
# SSH to VPS
npx @googleworkspace/cli auth login
# Opens browser -- complete OAuth flow
# Verify:
npx @googleworkspace/cli calendar events list --params '{"calendarId":"primary","maxResults":1}'
```

### Credential storage security
- Never store OAuth tokens in .env files or code
- Keyring backend on Linux uses libsecret (encrypted)
- Google Cloud Console OAuth client ID/secret are in the GCP project, not in EOS code
- If VPS is compromised, revoke tokens immediately via Google Account > Security

---

## Core Operations with Exact Signatures

### Gmail

```python
# List messages (returns IDs only, not content)
gws._run("gmail", "users", "messages", "list",
    params={
        "userId": "me",           # required — always "me" for authenticated user
        "maxResults": 10,         # optional — 1 to 500, default 100
        "q": "is:unread",         # optional — Gmail search syntax
        "labelIds": ["INBOX"],    # optional — filter by label
        "pageToken": "...",       # optional — pagination
    })
# Returns: {"messages": [{"id": str, "threadId": str}], "nextPageToken": str, "resultSizeEstimate": int}

# Get message detail
gws._run("gmail", "users", "messages", "get",
    params={
        "userId": "me",                                    # required
        "id": "msg_id",                                    # required
        "format": "metadata",                              # "full"|"metadata"|"minimal"|"raw"
        "metadataHeaders": ["Subject", "From", "Date"],    # only with format=metadata
    })
# Returns: {"id", "threadId", "labelIds", "snippet", "payload": {"headers": [{"name", "value"}]}}

# Modify message labels
gws._run("gmail", "users", "messages", "modify",
    params={"userId": "me", "id": "msg_id"},
    body={"addLabelIds": ["Label_123"], "removeLabelIds": ["INBOX"]})

# Batch modify (up to 1000 IDs)
gws._run("gmail", "users", "messages", "batchModify",
    params={"userId": "me"},
    body={"ids": ["msg1", "msg2"], "addLabelIds": ["Label_123"]})

# Send email (requires MIME + base64url encoding)
# See GWSConnector.send_email() for the full pattern

# List labels
gws._run("gmail", "users", "labels", "list", params={"userId": "me"})
# Returns: {"labels": [{"id", "name", "type": "system"|"user", "messagesTotal", "messagesUnread"}]}

# Create label
gws._run("gmail", "users", "labels", "create",
    params={"userId": "me"},
    body={"name": "My Label"})
# Returns: {"id", "name", "type": "user"}
```

### Calendar

```python
# List events
gws._run("calendar", "events", "list",
    params={
        "calendarId": "primary",   # required — "primary" or calendar ID
        "timeMin": "ISO8601",      # optional — lower bound (inclusive)
        "timeMax": "ISO8601",      # optional — upper bound (exclusive)
        "maxResults": 20,          # optional — 1 to 2500, default 250
        "singleEvents": True,      # optional — expand recurring events
        "orderBy": "startTime",    # optional — requires singleEvents=True
        "q": "search text",        # optional — free text search
    })
# Returns: {"items": [EventResource], "nextPageToken": str}
# EventResource: {id, summary, start: {dateTime|date}, end: {dateTime|date},
#   location, description, hangoutLink, attendees: [{email, responseStatus}],
#   organizer: {email, displayName, self}}

# Insert event (with Google Meet)
gws._run("calendar", "events", "insert",
    params={
        "calendarId": "primary",
        "conferenceDataVersion": 1,  # required for Meet link
        "body": {
            "summary": "Title",
            "start": {"dateTime": "ISO8601", "timeZone": "UTC"},
            "end": {"dateTime": "ISO8601", "timeZone": "UTC"},
            "attendees": [{"email": "person@example.com"}],
            "conferenceData": {
                "createRequest": {
                    "requestId": "uuid4-string",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        }
    })

# Update event
gws._run("calendar", "events", "update",
    params={"calendarId": "primary", "eventId": "event_id", "body": {updated_event_resource}})

# Delete event
gws._run("calendar", "events", "delete",
    params={"calendarId": "primary", "eventId": "event_id"})
# Returns empty body on success
```

### Drive

```python
# List files
gws._run("drive", "files", "list",
    params={
        "q": "mimeType='application/vnd.google-apps.document'",  # Drive search syntax
        "pageSize": 100,        # optional — 1 to 1000, default 100
        "fields": "files(id,name,mimeType,modifiedTime,webViewLink)",  # partial response
        "orderBy": "modifiedTime desc",
    })
# Returns: {"files": [FileResource], "nextPageToken": str}

# Export Google Doc as plain text
gws._run("drive", "files", "export",
    params={"fileId": "doc_id", "mimeType": "text/plain"})
# For Sheets: mimeType="text/csv"
# For Slides: mimeType="application/pdf"

# Create file/folder
gws._run("drive", "files", "create",
    params={
        "name": "New Folder",
        "mimeType": "application/vnd.google-apps.folder",  # folder
        "parents": ["parent_folder_id"],
    })

# Update file metadata
gws._run("drive", "files", "update",
    params={"fileId": "id", "name": "New Name", "addParents": "folder_id", "removeParents": "root"})
```

### Tasks

```python
# List tasks
gws._run("tasks", "tasks", "list",
    params={
        "tasklist": "TASKLIST_ID",  # required
        "showCompleted": False,
        "maxResults": 50,           # max 100
    })
# Returns: {"items": [{"id", "title", "notes", "due", "status", "completed"}]}

# Create task
gws._run("tasks", "tasks", "insert",
    params={"tasklist": "TASKLIST_ID", "title": "Task name", "notes": "Details", "due": "RFC3339"})

# Complete task
gws._run("tasks", "tasks", "patch",
    params={"tasklist": "TASKLIST_ID", "task": "task_id", "status": "completed"})
```

---

## Pagination Patterns

All Google APIs use **page token** pagination (not offset-based).

```python
# Generic fetch-all pattern for any Google API list endpoint
results = []
page_token = None
while True:
    params = {"maxResults": 100}  # or pageSize for Drive
    if page_token:
        params["pageToken"] = page_token
    data = gws._run("service", "resource", "list", params=params)
    if not data:
        break
    results.extend(data.get("items", []) or data.get("files", []) or data.get("messages", []))
    page_token = data.get("nextPageToken")
    if not page_token:
        break
```

**Key differences per service:**
- Gmail: `maxResults` (1-500), response key `messages`, `nextPageToken`
- Calendar: `maxResults` (1-2500), response key `items`, `nextPageToken`
- Drive: `pageSize` (1-1000), response key `files`, `nextPageToken`
- Tasks: `maxResults` (1-100), response key `items`, `nextPageToken`
- Sheets: No pagination for spreadsheets.values.get (returns all data at once)

**EOS implementation:** `GWSConnector.get_messages_by_label()` is the only method
that currently implements pagination. All other methods fetch a single page.
For inbox operations exceeding 500 messages, pagination must be added.

---

## Rate Limits

### Per-service quotas (per user, per 100 seconds)

| Service | Quota | Notes |
|---|---|---|
| Gmail | 250 quota units / user / second | Each method costs different units: list=5, get=5, send=100, modify=5, batchModify=50 |
| Calendar | 500 queries / 100 seconds / user | Shared across all calendar endpoints |
| Drive | 1000 queries / 100 seconds / user | 12000 queries / 100 seconds / project |
| Sheets | 60 read requests / user / minute, 60 write / user / minute | Per-project: 300 reads/min, 300 writes/min |
| Tasks | 500 queries / 100 seconds / user | Shared with Calendar quota pool |

### Daily quotas

| Service | Daily limit |
|---|---|
| Gmail | 1 billion quota units / day (project-wide) |
| Gmail send | 100 emails/day (consumer), 2000/day (Workspace) |
| Calendar | No published daily limit |
| Drive | 1 billion queries / day (project-wide) |
| Sheets | 300 requests / minute / project |

### Rate limit response
All Google APIs return HTTP 429 with:
```json
{
  "error": {
    "code": 429,
    "message": "Rate Limit Exceeded",
    "errors": [{"domain": "usageLimits", "reason": "rateLimitExceeded"}]
  }
}
```

**Retry strategy:** Exponential backoff starting at 1 second, max 5 retries.
Google recommends adding random jitter. The GWS CLI does NOT implement
automatic retry -- EOS must handle this at the application level.

**EOS concern:** `GWSDocumentScanner.scan_all()` makes 2 API calls per document
(list + export). A 200-doc scan = 400+ Drive API calls. With the 1000/100s limit,
this should complete in ~40 seconds. Adding AI assessment calls between each doc
provides natural rate limiting via `time.sleep(0.3)`.

---

## Error Codes and Recovery

### HTTP status codes

| Code | Meaning | Retryable | Recovery |
|---|---|---|---|
| 400 | Bad request (invalid params) | No | Fix request parameters |
| 401 | Invalid credentials / token expired | No | Re-auth: `npx @googleworkspace/cli auth login` |
| 403 | Insufficient permissions / scope | No | Request additional scopes or check sharing |
| 404 | Resource not found | No | Verify resource ID exists |
| 409 | Conflict (concurrent edit) | Yes | Retry with fresh data |
| 429 | Rate limit exceeded | Yes | Exponential backoff with jitter |
| 500 | Internal server error | Yes | Retry up to 3 times with backoff |
| 503 | Service unavailable | Yes | Retry with backoff, check Google status page |

### Gmail-specific errors
- `insufficientPermissions` (403): Missing `gmail.modify` scope when trying to modify labels
- `invalidArgument` (400): Invalid label ID in modify request
- `notFound` (404): Message ID no longer exists (deleted or expunged)

### Calendar-specific errors
- `notFound` (404): Event deleted between list and get calls
- `duplicate` (409): `requestId` in `conferenceData.createRequest` reused

### Drive-specific errors
- `exportSizeLimitExceeded` (403): Google Doc too large to export (>10MB exported)
- `dailyLimitExceeded` (403): Project-wide daily quota hit
- `fileNotFound` (404): File deleted or not shared with authenticated user

### EOS error handling pattern
All `GWSConnector` methods catch exceptions and return `None` or `[]`.
This is safe for the cognitive loop (never crashes) but means errors are
silently swallowed. Check `[GWS]` prefixed print statements in logs for
failure diagnostics.

---

## SDK Idioms

### The GWS CLI approach (what EOS uses)
EOS wraps the `@googleworkspace/cli` npm package via subprocess. This is
unconventional -- most Python projects use `google-api-python-client`.

**Why this approach:**
- Zero Python dependency management for Google auth libraries
- CLI handles token refresh, keyring, and OAuth flow
- Single auth mechanism for all 5 services
- `npx` ensures latest CLI version on each invocation

**Downsides:**
- subprocess overhead (~1-2 seconds per call for npx cold start)
- No streaming or batch request support
- Error messages are less structured than SDK exceptions
- Can't use Python async patterns

### The Python SDK approach (if migrating)
```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Auth
creds = Credentials.from_authorized_user_file('token.json', SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

# Build service
gmail = build('gmail', 'v1', credentials=creds)
calendar = build('calendar', 'v3', credentials=creds)
drive = build('drive', 'v3', credentials=creds)
sheets = build('sheets', 'v4', credentials=creds)
tasks = build('tasks', 'v1', credentials=creds)

# Use
results = gmail.users().messages().list(userId='me', maxResults=10).execute()
```

**Python SDK packages:**
- `google-api-python-client` -- service builders
- `google-auth` -- credential handling
- `google-auth-oauthlib` -- OAuth2 flow
- `google-auth-httplib2` -- HTTP transport

### Key CLI idiom: JSON parsing
```python
# Always strip the keyring backend line
output = result.stdout
lines = output.split("\n")
clean = "\n".join(l for l in lines if not l.startswith("Using keyring"))
data = json.loads(clean.strip())
```

---

## Anti-Patterns

### 1. Fetching full message body when you only need metadata
```python
# WRONG: fetches entire message including body
gws._run("gmail", "users", "messages", "get",
    params={"userId": "me", "id": msg_id, "format": "full"})

# RIGHT: fetch only headers you need
gws._run("gmail", "users", "messages", "get",
    params={"userId": "me", "id": msg_id, "format": "metadata",
            "metadataHeaders": ["Subject", "From", "Date"]})
```

### 2. Not using singleEvents=True with orderBy
```python
# WRONG: orderBy without singleEvents raises 400
gws._run("calendar", "events", "list",
    params={"calendarId": "primary", "orderBy": "startTime"})

# RIGHT: expand recurring events first
gws._run("calendar", "events", "list",
    params={"calendarId": "primary", "singleEvents": True, "orderBy": "startTime"})
```

### 3. Using files.get instead of files.export for Google Docs
```python
# WRONG: files.get with alt=media doesn't work for Google Docs/Sheets/Slides
gws._run("drive", "files", "get", params={"fileId": doc_id, "alt": "media"})

# RIGHT: use export with target mimeType
gws._run("drive", "files", "export",
    params={"fileId": doc_id, "mimeType": "text/plain"})
```

### 4. Hardcoding calendar ID instead of using "primary"
```python
# WRONG: using the full calendar email
params={"calendarId": "antony@gmail.com", ...}

# RIGHT: "primary" always refers to the authenticated user's main calendar
params={"calendarId": "primary", ...}
```

### 5. Assuming all-day events have dateTime
```python
# WRONG: crashes on all-day events
start = event["start"]["dateTime"]

# RIGHT: fallback to date field
start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
```

### 6. Not using fields parameter on Drive list
```python
# WRONG: returns all metadata for every file (slow, wasteful)
gws._run("drive", "files", "list", params={"pageSize": 100})

# RIGHT: request only needed fields
gws._run("drive", "files", "list",
    params={"pageSize": 100, "fields": "files(id,name,mimeType,modifiedTime)"})
```

### 7. Sending more than 1000 IDs to Gmail batchModify
```python
# WRONG: API rejects >1000 IDs silently or with 400
gws._run("gmail", "users", "messages", "batchModify",
    params={"userId": "me"},
    body={"ids": all_2000_ids, "addLabelIds": [label]})

# RIGHT: chunk into batches of 1000
for i in range(0, len(ids), 1000):
    chunk = ids[i:i+1000]
    gws._run("gmail", "users", "messages", "batchModify",
        params={"userId": "me"},
        body={"ids": chunk, "addLabelIds": [label]})
```

---

## Data Model

### Gmail hierarchy
```
Account (userId: "me")
  +-- Labels (system + user-created)
  +-- Threads (conversation grouping)
  |     +-- Messages (individual emails)
  |           +-- Payload (headers, body parts, attachments)
  +-- Drafts (unsent messages)
  +-- Settings (filters, forwarding, IMAP/POP)
```

**Key fields on Message:**
- `id` (string) -- unique, immutable
- `threadId` (string) -- groups related messages
- `labelIds` (list) -- both system (INBOX, SENT, DRAFT) and user labels
- `snippet` (string) -- first ~200 chars of message text
- `internalDate` (string) -- epoch ms when Gmail received it
- `payload.headers` -- list of {name, value} objects

### Calendar hierarchy
```
CalendarList (calendars the user has access to)
  +-- Calendar ("primary" = main calendar)
        +-- Events
              +-- Attendees (email, responseStatus)
              +-- Reminders (method, minutes)
              +-- ConferenceData (Meet link)
```

**Key fields on Event:**
- `id` (string) -- unique per calendar
- `summary` (string) -- event title
- `start` / `end` -- `{dateTime: ISO8601}` or `{date: YYYY-MM-DD}` for all-day
- `attendees` -- `[{email, responseStatus: "needsAction"|"accepted"|"declined"|"tentative"}]`
- `hangoutLink` (string) -- Google Meet URL (read-only, created via conferenceData)
- `organizer` -- `{email, displayName, self: bool}`

### Drive hierarchy
```
Drive (user's entire storage)
  +-- Files and Folders (flat with parent references)
        +-- Google Docs (mimeType: application/vnd.google-apps.document)
        +-- Google Sheets (mimeType: application/vnd.google-apps.spreadsheet)
        +-- Google Slides (mimeType: application/vnd.google-apps.presentation)
        +-- Folders (mimeType: application/vnd.google-apps.folder)
        +-- Binary files (PDFs, images, etc.)
```

**Key fields on File:**
- `id` (string) -- globally unique, immutable
- `name` (string) -- display name (not unique)
- `mimeType` (string) -- determines if export vs download
- `parents` (list) -- folder IDs (a file can have multiple parents)
- `modifiedTime` (string) -- RFC 3339 timestamp
- `webViewLink` (string) -- URL to open in browser

### Tasks hierarchy
```
TaskLists
  +-- TaskList (has ID, title)
        +-- Tasks (flat list, can have parent for subtasks)
```

---

## Webhooks and Events

### Gmail: Push notifications via Pub/Sub
Gmail supports push notifications through Google Cloud Pub/Sub:
```python
gmail.users().watch(userId='me', body={
    'topicName': 'projects/my-project/topics/gmail-notifications',
    'labelIds': ['INBOX'],
}).execute()
# Returns: {"historyId": str, "expiration": str}
```
- Watch expires after 7 days, must be renewed
- Notification payload contains `historyId`, not message content
- Must call `history.list` to get actual changes
- EOS does NOT currently use Gmail push notifications (uses polling)

### Calendar: Push notifications via webhook
Calendar supports push notifications to an HTTPS endpoint:
```python
calendar.events().watch(calendarId='primary', body={
    'id': 'unique-channel-id',
    'type': 'web_hook',
    'address': 'https://your-server.com/webhook/calendar',
}).execute()
```
- Requires publicly accessible HTTPS endpoint (EOS VPS is on Tailscale, not public)
- EOS does NOT use Calendar push -- uses polling via `calendar_invite_handler.py`

### Drive: Push notifications
Similar to Calendar -- webhook to HTTPS endpoint. Not used by EOS.

### Sheets: No native webhook support
Sheets has no built-in change notification. Options:
- Poll `spreadsheets.get` and compare `modifiedTime`
- Use Apps Script triggers (onEdit) to call an external webhook
- EOS does not currently use Sheets

---

## Limits

### Gmail limits
- Message size: 25 MB (including attachments)
- Labels per user: 10,000
- Batch modify: 1,000 message IDs per request
- Search query length: 4,096 characters
- Messages per send (consumer): 100/day; (Workspace): 2,000/day
- Attachment count: 500 per message

### Calendar limits
- Events per calendar: no published limit (practically unlimited)
- Attendees per event: 200 (consumer), larger for Workspace
- Calendars per user: no published limit
- Event title: 1,024 characters
- Event description: 8,192 characters
- Recurring event instances: 730 (2 years of daily events)

### Drive limits
- File name: 32,767 characters
- File size: 5 TB
- Export size (Google Docs): 10 MB
- Export size (Sheets as CSV): 10 MB per sheet
- Folder depth: no hard limit but deep nesting causes performance issues
- Files per folder: 500,000
- Shared drive items: 400,000

### Sheets limits
- Cells per spreadsheet: 10 million
- Columns per sheet: 18,278 (ZZZ)
- Rows per sheet: practically limited by cell count
- Characters per cell: 50,000
- Sheets per spreadsheet: 200

### Tasks limits
- Task lists per user: 2,000
- Tasks per task list: no published limit
- Task title: 1,024 characters
- Task notes: 8,192 characters

---

## Cost Model

### Free tier (Google Cloud)
All Google Workspace APIs are **free to use** -- there is no per-request charge.
Costs come from:
- Google Cloud project: $0 for API access alone
- Google Workspace subscription: $7.20/user/month (Business Starter) for custom domain
- Consumer Gmail/Calendar/Drive: completely free API access
- Pub/Sub (if using push notifications): $0.40 per million messages

### What actually costs money
- Running the VPS that hosts EOS ($$ per month)
- `npx` cold start overhead (bandwidth + CPU, not billed by Google)
- If using Google Cloud Functions for webhook receivers: $0.40/million invocations

### EOS cost impact
Zero incremental cost for Google API usage. The bottleneck is the VPS
subprocess overhead (~1-2 seconds per GWS CLI call) not monetary cost.

---

## Version Pinning

### Current versions in EOS
- Gmail API: v1 (only version, no versioning changes since launch)
- Calendar API: v3 (stable since 2012, no v4 announced)
- Drive API: v3 (v2 deprecated 2020)
- Sheets API: v4 (v3 deprecated 2020)
- Tasks API: v1 (only version)
- `@googleworkspace/cli`: latest via `npx` (not pinned)

### Pinning strategy
The GWS CLI is invoked via `npx @googleworkspace/cli` which always fetches the
latest version. To pin:
```bash
npm install -g @googleworkspace/cli@1.2.3  # install specific version
# Then use the global install instead of npx
```
EOS currently does NOT pin the CLI version. This means CLI updates could
break the subprocess interface without warning.

### Deprecation policy
Google provides 1 year notice before deprecating API versions. They maintain
old versions for 1 year after deprecation announcement. Current versions
(v1 Gmail, v3 Calendar, v3 Drive, v4 Sheets, v1 Tasks) have no announced
deprecation dates.

### Known deprecations
- Drive API v2: deprecated, use v3
- Sheets API v3: deprecated, use v4
- `google.generativeai` Python SDK: deprecated for `google.genai` (Gemini, not Workspace)
- OAuth out-of-band (OOB) flow: deprecated January 2023 -- must use localhost redirect

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Google Workspace APIs were designed with a core philosophy: **every Google product
is an API-first service.** Gmail, Calendar, Drive, and Sheets are all built on the
same API infrastructure that external developers use. This means:

**Mental model:** Each service is a RESTful resource hierarchy. Gmail has users,
messages, labels. Calendar has calendars and events. Drive has files. The API
is a 1:1 mapping of the product's data model.

**Key tradeoff: Consistency over innovation.** Google rarely breaks APIs. Calendar v3
has been stable since 2012. This stability comes at the cost of modern patterns --
no GraphQL, no real-time subscriptions (only webhooks), no batch endpoints for
cross-service operations. Each service is its own silo.

**What Google Workspace is NOT:**
- Not a unified API (each service is separate, different auth scopes)
- Not a real-time platform (polling or webhook-based, not WebSocket)
- Not a database (Drive is file storage, not queryable data)
- Not optimized for automation (designed for interactive use, automation is secondary)

**Why separate APIs matter for EOS:** You can't do a single call to "get today's
emails and calendar events." Each service requires separate calls, separate pagination,
separate error handling. GWSConnector's value is unifying these behind a single class.

---

## Problem-Solution Map and Hidden Capabilities

### Hidden capabilities most users miss

1. **Gmail search syntax is extremely powerful.** `q` parameter supports full Gmail
   search: `from:alex after:2026/01/01 has:attachment -label:processed`. This is
   faster than fetching all messages and filtering in code.

2. **Calendar freebusy endpoint.** Instead of listing all events and checking
   for conflicts manually, use `freebusy.query()` to check availability for
   multiple calendars at once. EOS uses manual conflict checking -- freebusy
   would be more efficient.

3. **Drive search operators.** `q` supports: `fullText contains 'keyword'`,
   `modifiedTime > '2026-01-01'`, `'folder_id' in parents`, `sharedWithMe`,
   `starred`, `trashed = false`. Combine with `and`/`or`/`not`.

4. **Gmail label colors.** Labels created via API can have custom colors
   (`labelColor.backgroundColor` and `textColor`). EOS could color-code the
   GPS folders for visual distinction.

5. **Calendar event attachments.** Events can have Drive file attachments
   (`attachments` field with `fileUrl`). Useful for attaching meeting agendas
   or call prep docs automatically.

6. **Sheets as a lightweight database.** `spreadsheets.values.append()` adds
   rows, `batchUpdate` does conditional formatting. For simple metrics tracking
   (outreach counts, conversion rates), Sheets is simpler than Neon.

---

## Operational Behavior and Edge Cases

### Eventual consistency
- Gmail: message label changes are eventually consistent. A `modify` call returns
  immediately, but `list` with that label may not include the message for up to
  a few seconds.
- Calendar: event changes propagate to attendees asynchronously. The API returns
  success before attendees receive notifications.
- Drive: file metadata updates are eventually consistent across devices.

### Silent failures
- Calendar `events.delete` returns 204 (empty body) on success. `GWSConnector`
  returns `None` from `_run()` (same as error). The current code returns `True`
  unconditionally.
- Gmail `batchModify` returns 204 on success. Same issue.

### Timezone edge cases
- Calendar events without explicit timezone inherit the calendar's timezone
- All-day events use `date` (YYYY-MM-DD) with no timezone component
- `timeMin`/`timeMax` filters use UTC. If you pass a local time without offset,
  behavior is undefined.
- EOS normalizes to UTC internally and converts for display using `zoneinfo`.

### Concurrent modification
- Calendar: last-write-wins. No etag/version checking in EOS.
- Drive: supports etag-based optimistic concurrency, but EOS doesn't use it.
- Gmail labels: concurrent label modifications can produce unexpected results
  (both modifications applied, potentially conflicting).

### The "npx cold start" problem
First `npx @googleworkspace/cli` call in a session takes 3-5 seconds (npm
package resolution + Node.js startup). Subsequent calls take ~1 second.
This means the first GWSConnector method call in any EOS flow is noticeably
slower. Consider a warmup call in service startup.

---

## Ecosystem Position and Composition

### Where Google Workspace sits in EOS architecture
```
Data sources (Google Workspace, Notion, Discord) → EOS intelligence layer → Actions
```

Google Workspace is the **personal productivity layer** -- it's where the founder's
real-world interactions live (email, calendar, documents). EOS reads from it to
understand context and writes to it to take action.

### Natural complements
- **Notion** -- structured knowledge (databases, project tracking) vs Google's
  unstructured content (emails, docs). Both feed into EOS cognitive loop.
- **Discord** -- real-time conversational interface. Google data is surfaced
  through Discord (morning brief posts calendar events).
- **Calendly** -- scheduling link that creates Calendar events. EOS detects new
  Calendly events via Calendar polling.
- **Neon Postgres** -- permanent storage. Google data is ephemeral; EOS ingests
  key signals into Neon for long-term intelligence.

### Integration anti-patterns
- Don't use Google Sheets as a primary database -- use Neon. Sheets is for
  human-readable dashboards only.
- Don't poll Gmail more than once per minute -- use push notifications (Pub/Sub)
  for real-time email processing.
- Don't store auth tokens in Drive "just because it's convenient" -- tokens
  belong in keyring or encrypted secret management.

---

## Trajectory and Evolution

### Google's direction (2024-2026)
- **Gemini integration everywhere** -- Gmail summarization, Calendar scheduling
  suggestions, Docs writing assistance. Google is embedding AI into every
  Workspace product, but the API surface hasn't changed to expose these features.
- **Workspace Add-ons consolidation** -- Google is pushing developers toward
  Workspace Add-ons (formerly G Suite Marketplace) as the primary extension point.
- **OAuth consent screen tightening** -- Google continues to restrict sensitive
  scopes. Apps requesting `gmail.modify` or `drive` now require verification
  review (weeks-long process). Testing mode has the 7-day token expiry.

### What to watch
- **Gmail API v2** -- no announcement, but Gmail is the oldest API (v1 since 2014).
  A v2 could modernize message format handling.
- **Workspace Events API** (launched 2024) -- new unified event system for
  cross-service change notifications. Could replace per-service watch/webhook.
- **Apps Script deprecation signals** -- Google is investing in Workspace Add-ons
  and Cloud Functions, not Apps Script. Long-term, expect Apps Script to be
  de-emphasized.

### EOS implications
The GWS CLI approach is stable but won't benefit from new Google features
(like Workspace Events API) until the CLI adds support. Consider migrating
to `google-api-python-client` when auth stabilization is needed.

---

## Conceptual Model and Solution Recipes

### Mental model: Google Workspace as 5 independent databases

Think of each Google service as a separate database with its own schema:
- **Gmail** = message store with label-based categorization
- **Calendar** = event store with time-range queries
- **Drive** = file store with metadata queries
- **Sheets** = tabular data store with cell-level access
- **Tasks** = simple to-do list store

EOS's job is to **read from all 5, reason about the combined context, and write
back to the appropriate one.**

### Recipe 1: Morning Intelligence Brief
```
1. Calendar: get_today_events() → today's schedule
2. Gmail: get_recent_emails(query="is:unread") → unread count + key senders
3. Tasks: get_tasks() → open action items
4. Combine in cognitive loop → generate morning brief
5. Discord: post to #morning-brief channel
```
This runs daily at 6am via `eos_ai/orchestrator.py`.

### Recipe 2: Meeting Lifecycle
```
1. Calendar poll: detect new invite (calendar_invite_handler.py)
2. AI assess: accept/decline/flag recommendation
3. Calendar: respond_to_invite() → accept or decline
4. Discord: notify founder with assessment
5. Pre-meeting: call_prep.py → pull context from Neon + Gmail
6. Post-meeting: post_meeting_capture.py → log outcomes
7. Tasks: create follow-up task
```

### Recipe 3: Email GPS Classification
```
1. Gmail: get_all_inbox_emails() → full inbox
2. AI classify each email into 7 GPS folders
3. Gmail: get_or_create_label() for each folder
4. Gmail: apply_label_to_message() → move to folder
5. Gmail: batch_modify_messages() → remove INBOX label
6. For TO_RESPOND: AI draft response
7. Discord: summary of what was processed
```

### Recipe 4: Document Knowledge Ingestion
```
1. Drive: list_all_docs() → all Google Docs
2. Drive: read_doc() → export each as plain text
3. AI: understand_doc() → relevance score + venture mapping
4. Filter: keep score >= 3
5. Chunk: split into 3000-char segments
6. Neon: KnowledgeIntegrator.integrate() → permanent storage
7. Generate: founder_profile → 4-section analysis
8. Discord: post learning report
```

### Recipe 5: Scheduling with Conflict Detection
```
1. Parse: extract date/time from natural language
2. Calendar: check_conflicts() with 15-min buffer
3. If conflict: suggest alternative times
4. Calendar: create_calendar_event() with Meet link
5. Calendar: block_travel_time() if location exists
6. Gmail: send confirmation email to attendee
7. Notion: create meeting record
8. Discord: notify founder
```

---

## Industry Expert and Cutting-Edge Usage

### AI-powered email triage (what EOS does)
EOS implements Dan Martell's "Buy Back Your Time" email GPS system -- AI reads
every email and classifies it before the founder sees it. This is cutting-edge
because most email automation tools (SaneBox, Clean Email) use rules, not LLMs.
EOS uses LLM reasoning to understand context, relationships, and urgency.

### Document-to-knowledge pipeline
The GWS Document Scanner pattern (scan all Docs, AI-assess, chunk, ingest to
vector store) is used by companies like Notion AI and Glean. EOS does this
entirely on the founder's own infrastructure -- no third-party AI has access
to the documents.

### Calendar-as-signal-source
Advanced users treat calendar data as business intelligence: meeting frequency
with a prospect = engagement signal, meeting no-shows = relationship risk,
time allocation across ventures = strategic alignment check. EOS's
`calendar_invite_handler.py` already does basic invite assessment; the next
level is tracking patterns over time.

### Emerging patterns
- **Workspace Events API** -- subscribe to changes across Gmail, Calendar, and
  Drive in a single subscription. Eliminates polling entirely.
- **Gmail delegated access** -- have the AI operate as a delegate (separate
  identity) rather than impersonating the founder. Provides audit trail.
- **Sheets as metrics dashboard** -- write KPIs to Sheets automatically,
  use Sheets' built-in charts for visualization. Cheaper and faster than
  building a custom dashboard.
- **Drive as content management** -- use Drive folder structure as a content
  calendar (folders = weeks, docs = content pieces). AI monitors and prompts
  for missing content.

---

## EOS Usage Patterns

### GWSConnector instantiation
Always import and instantiate fresh per operation:
```python
from eos_ai.gws_connector import GWSConnector
gws = GWSConnector()
```
GWSConnector has no state except `TASKLIST_ID`. It's safe to create multiple
instances. Each method call is an independent subprocess.

### GWSDocumentScanner instantiation
Requires EOSContext:
```python
from eos_ai.context import load_context_from_env
from eos_ai.gws_scanner import GWSDocumentScanner
ctx = load_context_from_env()
scanner = GWSDocumentScanner(ctx)
```

### Auth check pattern
Before any GWS-dependent flow, verify auth is valid:
```python
gws = GWSConnector()
test = gws.get_today_events()
if test is None:
    print("[WARNING] GWS auth may be expired. Run: npx @googleworkspace/cli auth login")
```

---

## Gotchas

### Auth expired 2026-04-03 (testing mode 7-day limit)
The Google Cloud OAuth consent screen was in "testing" mode. Refresh tokens
issued in testing mode expire after 7 days. The GWS document scanner stopped
working. Fix: either publish the consent screen or re-auth weekly.

### "Using keyring backend: keyring" stdout pollution
Both `_run()` methods strip this line. Any new GWS CLI wrapper must do the same
or JSON parsing breaks silently.

### npx cold start adds 3-5 second latency on first call
First invocation downloads/resolves the npm package. Cache warms after that.
Consider installing globally to avoid npx overhead:
`npm install -g @googleworkspace/cli`

### Gmail messages.list does NOT return message content
Only returns `{id, threadId}`. Must call `messages.get` per message for headers,
snippet, or body. This is by design for performance but means N+1 queries for
inbox processing.

### Drive files.export vs files.get
Google Docs/Sheets/Slides MUST use `export` (converts format). Binary files
(PDFs, images) use `get` with `alt=media`. Using the wrong one fails silently
or returns an error.

### Calendar singleEvents=True required for orderBy=startTime
Without `singleEvents=True`, recurring events appear as a single master event.
`orderBy=startTime` requires expanded instances, so `singleEvents=True` is mandatory.
Omitting it returns HTTP 400.
