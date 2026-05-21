# Gmail API — Best Practices (Creator-Level Reference)

Source: Google Gmail API documentation + EOS production experience
Version: Gmail API v1
Last Researched: 2026-04-04

---

## 1. Authentication

### GWS CLI auth (EOS primary path)
```bash
# Interactive login — run once per machine
npx @googleworkspace/cli auth login

# Token stored in system keyring
# Auto-refreshes on subsequent calls
# No env var needed — keyring handles token storage
```

### OAuth2 (Python SDK path)
```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
]

creds = None
if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
    with open("token.json", "w") as token:
        token.write(creds.to_json())
```

### OAuth2 scopes
| Scope | Access |
|-------|--------|
| `gmail.readonly` | Read messages, labels, threads |
| `gmail.modify` | Read + modify labels, mark read/unread |
| `gmail.send` | Send emails |
| `gmail.compose` | Create, update, send drafts |
| `gmail.labels` | Manage labels (create, update, delete) |
| `gmail.metadata` | Read message metadata only (headers) |
| `mail.google.com` | Full access (all operations) |

---

## 2. Core Operations with Exact Signatures

### List messages
```
GET https://gmail.googleapis.com/gmail/v1/users/{userId}/messages

Parameters:
  userId: "me" (authenticated user)
  q: "is:unread"                   # Gmail search syntax
  labelIds: ["INBOX"]              # filter by label
  maxResults: 100                  # max per page (default 100)
  pageToken: "token..."            # pagination cursor
  includeSpamTrash: false          # default false

Response:
{
    "messages": [
        {"id": "msg_id", "threadId": "thread_id"}
    ],
    "nextPageToken": "token...",
    "resultSizeEstimate": 150
}

Quota: 5 units per call
```

### Get message
```
GET https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/{id}

Parameters:
  format: "full" | "metadata" | "minimal" | "raw"
  metadataHeaders: ["From", "Subject", "Date"]  # only with format=metadata

Response (format=full):
{
    "id": "msg_id",
    "threadId": "thread_id",
    "labelIds": ["INBOX", "UNREAD"],
    "snippet": "Preview text...",
    "payload": {
        "mimeType": "multipart/alternative",
        "headers": [
            {"name": "From", "value": "sender@example.com"},
            {"name": "Subject", "value": "Subject line"},
            {"name": "Date", "value": "Fri, 4 Apr 2026 09:00:00 -0700"}
        ],
        "parts": [
            {
                "mimeType": "text/plain",
                "body": {"data": "base64url_encoded_body", "size": 1234}
            }
        ]
    },
    "internalDate": "1712242800000"  // epoch ms
}

Quota: 5 units per call
```

### Send message
```
POST https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/send

Request body:
{
    "raw": "base64url_encoded_RFC2822_message"
}

# Building the raw message:
import base64
from email.mime.text import MIMEText

message = MIMEText("Email body")
message["to"] = "recipient@example.com"
message["from"] = "sender@example.com"
message["subject"] = "Subject"
raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

Quota: 100 units per call
```

### Modify message labels
```
POST https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/{id}/modify

Request body:
{
    "addLabelIds": ["Label_123"],
    "removeLabelIds": ["UNREAD"]
}

Quota: 5 units per call
```

### Create draft
```
POST https://gmail.googleapis.com/gmail/v1/users/{userId}/drafts

Request body:
{
    "message": {
        "raw": "base64url_encoded_message"
    }
}

Quota: 10 units per call
```

### Send draft
```
POST https://gmail.googleapis.com/gmail/v1/users/{userId}/drafts/send

Request body:
{
    "id": "draft_id"
}

Quota: 100 units per call
```

### List labels
```
GET https://gmail.googleapis.com/gmail/v1/users/{userId}/labels

Response:
{
    "labels": [
        {
            "id": "Label_123",
            "name": "Antony",
            "type": "user",
            "messagesTotal": 45,
            "messagesUnread": 3
        }
    ]
}

Quota: 1 unit per call
```

### GWS CLI equivalents (EOS pattern)
```python
# GWSConnector wraps these as subprocess calls:
gws._run("gmail", "users", "messages", "list",
    params={"userId": "me", "q": "is:unread", "maxResults": 20})

gws._run("gmail", "users", "messages", "get",
    params={"userId": "me", "id": msg_id, "format": "full"})

gws._run("gmail", "users", "messages", "send",
    body={"raw": base64_message})
```

---

## 3. Pagination Patterns

### Message list pagination
```python
messages = []
page_token = None

while True:
    params = {"userId": "me", "q": "is:unread", "maxResults": 100}
    if page_token:
        params["pageToken"] = page_token
    
    result = service.users().messages().list(**params).execute()
    messages.extend(result.get("messages", []))
    
    page_token = result.get("nextPageToken")
    if not page_token:
        break
```

### Incremental sync with History API
```python
# Get history ID from last sync
start_history_id = load_last_history_id()

result = service.users().history().list(
    userId="me",
    startHistoryId=start_history_id,
    historyTypes=["messageAdded", "messageDeleted", "labelAdded", "labelRemoved"],
).execute()

for history in result.get("history", []):
    for added in history.get("messagesAdded", []):
        process_new_message(added["message"]["id"])

# Save new history ID
save_history_id(result.get("historyId"))
```

### EOS pattern: simple list with limit
```python
# EOS doesn't paginate — small maxResults, single page
data = gws._run("gmail", "users", "messages", "list",
    params={"userId": "me", "q": "is:unread", "maxResults": 20})
```

---

## 4. Rate Limits

### Quota units
| Method | Cost (units) |
|--------|-------------|
| messages.list | 5 |
| messages.get | 5 |
| messages.send | 100 |
| messages.modify | 5 |
| messages.trash | 5 |
| messages.delete | 10 |
| messages.import | 25 |
| drafts.create | 10 |
| drafts.send | 100 |
| drafts.list | 5 |
| labels.list | 1 |
| labels.create | 5 |
| history.list | 2 |

### Daily quotas
| Resource | Limit |
|----------|-------|
| Daily usage | 1,000,000,000 quota units |
| Sending (consumer) | 500 messages/day |
| Sending (Workspace) | 2,000 messages/day |
| Recipients per message | 500 (consumer), 2000 (Workspace) |

### Per-user rate limits
```
Per second: ~25 quota units/second/user
Per 100 seconds: ~2500 quota units

Practical limits:
  - ~500 messages.list calls per 100 seconds
  - ~25 messages.send calls per 100 seconds
```

### EOS usage (minimal)
```
Morning brief: ~5-10 API calls (list + get recent)
Email GPS batch: ~20-50 calls (list + classify)
Draft sending: ~1-5 sends/day
Total daily: <200 quota units
```

---

## 5. Error Codes and Recovery

### HTTP error codes
| Code | Meaning | Recovery |
|------|---------|----------|
| 400 | Invalid request | Check query syntax, RFC2822 format |
| 401 | Invalid credentials | Refresh OAuth token |
| 403 | Insufficient permission | Check OAuth scopes |
| 404 | Message/draft not found | ID may be invalid or message deleted |
| 429 | Rate limit exceeded | Exponential backoff |
| 500 | Backend error | Retry with backoff |
| 503 | Service unavailable | Retry with backoff |

### Error response format
```json
{
    "error": {
        "code": 403,
        "message": "Insufficient Permission",
        "errors": [
            {
                "domain": "global",
                "reason": "insufficientPermissions",
                "message": "Insufficient Permission"
            }
        ]
    }
}
```

### Common error reasons
| reason | Meaning |
|--------|---------|
| `authError` | Token expired or revoked |
| `notFound` | Resource doesn't exist |
| `invalidArgument` | Invalid parameter value |
| `failedPrecondition` | Account suspended or domain issue |
| `rateLimitExceeded` | Too many requests |
| `userRateLimitExceeded` | Per-user rate limit hit |
| `dailyLimitExceeded` | Daily quota exhausted |

### EOS error handling
```python
# GWSConnector — catches all exceptions, returns None
def _run(self, *args, **kwargs):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # Parse JSON...
        return json.loads(clean)
    except Exception as e:
        print(f"[GWS] Command failed: {e}")
        return None  # Never crashes — caller handles None
```

---

## 6. SDK Idioms

### GWS CLI pattern (EOS primary)
```python
class GWSConnector:
    def _run(self, *args, params=None, body=None):
        cmd = ["npx", "@googleworkspace/cli"] + list(args)
        if params:
            cmd += ["--params", json.dumps(params)]
        if body:
            cmd += ["--json", json.dumps(body)]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # Strip "Using keyring backend: keyring" debug line
        lines = result.stdout.split("\n")
        clean = "\n".join(l for l in lines if not l.startswith("Using keyring"))
        return json.loads(clean.strip()) if clean.strip() else None
```

### Python SDK pattern (alternative)
```python
from googleapiclient.discovery import build

service = build("gmail", "v1", credentials=creds)

# All methods follow: service.users().{resource}().{method}(**params).execute()
service.users().messages().list(userId="me", q="is:unread").execute()
service.users().messages().get(userId="me", id=msg_id, format="full").execute()
service.users().messages().send(userId="me", body={"raw": raw}).execute()
```

### EmailGPS pattern (email classification)
```python
# 7-folder system
class EmailGPS:
    _FINANCIAL_SIGNALS = ["receipt", "invoice", "payment", ...]
    NOISE_SENDERS = ["reddit.com", "quora.com", ...]
    
    def classify(self, email):
        # 1. Hard rules (financial → RECEIPTS)
        if any(sig in email.subject.lower() for sig in self._FINANCIAL_SIGNALS):
            return EmailFolder.RECEIPTS
        
        # 2. Noise detection (social notifications → delete)
        if any(sender in email.from_address for sender in self.NOISE_SENDERS):
            return None  # bulk delete
        
        # 3. Person recognition
        # 4. AI classification via model_router
```

---

## 7. Anti-Patterns

### 1. Polling messages.list in tight loop
```python
# WRONG — wastes quota, slow
while True:
    messages = service.users().messages().list(userId="me").execute()
    time.sleep(1)

# RIGHT — use History API for incremental sync
# Or: use Cloud Pub/Sub watch() for push notifications
```

### 2. Getting full message when metadata suffices
```python
# WRONG — downloads full body
msg = service.users().messages().get(userId="me", id=id, format="full").execute()

# RIGHT — request only what you need
msg = service.users().messages().get(userId="me", id=id, format="metadata",
    metadataHeaders=["From", "Subject", "Date"]).execute()
```

### 3. Sending as Antony directly
```python
# WRONG — breaking EA persona
message["from"] = "antony@example.com"
# Body: "Hi, this is Antony..."

# RIGHT — always use DEX template
DEX_TEMPLATE = "Hi {name},\n\nThis is DEX, Antony's assistant..."
```

### 4. Sending without approval
```python
# WRONG — auto-sending emails
service.users().messages().send(userId="me", body={"raw": raw}).execute()

# RIGHT — draft → approval queue → manual send
# Store in orchestrator/approvals/ or Neon events table
```

### 5. Storing OAuth tokens in plaintext env var
```python
# WRONG
GMAIL_TOKEN=ya29.a0...  # In .env file

# RIGHT — use keyring (GWS CLI) or encrypted token file
# GWS CLI handles this automatically via system keyring
```

### 6. Ignoring message body encoding
```python
# WRONG — assuming body is plain text
body = msg["payload"]["body"]["data"]

# RIGHT — base64url decode
import base64
body_bytes = base64.urlsafe_b64decode(msg["payload"]["body"]["data"])
body_text = body_bytes.decode("utf-8")
```

---

## 8. Data Model

### Gmail entity hierarchy
```
User (userId: "me")
  └── Labels (INBOX, SENT, DRAFT, TRASH, SPAM, custom)
  └── Threads (threadId)
        └── Messages (id, threadId)
              └── Payload (headers, parts, body)
                    └── Parts (mimeType, body)
                          └── Body (data: base64url, size)
  └── Drafts (id, message)
  └── History (historyId, changes)
```

### Message format
```
format=full     → headers + body parts + attachments metadata
format=metadata → headers only (From, Subject, Date, etc.)
format=minimal  → id, threadId, labelIds, snippet
format=raw      → full RFC2822 message as base64url string
```

### EOS email data flow
```
Gmail inbox
  → GWSConnector._run("gmail", "users", "messages", "list")
    → List of message IDs
      → GWSConnector._run("gmail", "users", "messages", "get")
        → Full message with headers and body
          → EmailGPS.classify()
            ├── RECEIPTS (financial keywords)
            ├── NEWSLETTERS (unsubscribe link)
            ├── ANTONY (personal, needs attention)
            ├── TO_RESPOND (DEX drafts response)
            ├── REVIEW (daily sync item)
            ├── RESPONDED (DEX handled)
            └── WAITING_ON (pending reply)
```

### EmailGPS folder definitions
```python
class EmailFolder(Enum):
    ANTONY      = 'Antony'
    TO_RESPOND  = 'To Respond'
    REVIEW      = 'Review'
    RESPONDED   = 'Responded'
    WAITING_ON  = 'Waiting On'
    RECEIPTS    = 'Receipts-Financials'
    NEWSLETTERS = 'Newsletters'
```

---

## 9. Webhooks and Events

### Gmail Push Notifications (not used by EOS)
```python
# Gmail supports real-time push via Cloud Pub/Sub
# watch() creates a push subscription

response = service.users().watch(
    userId="me",
    body={
        "topicName": "projects/myproject/topics/gmail-notifications",
        "labelIds": ["INBOX"],
        "labelFilterBehavior": "INCLUDE",
    }
).execute()

# Returns: {"historyId": "12345", "expiration": "1712329200000"}
# Must renew before expiration (max 7 days)

# Pub/Sub message payload:
{
    "emailAddress": "user@gmail.com",
    "historyId": 12346
}
# Then use history.list(startHistoryId=12345) to get changes
```

### EOS pattern: cron-based polling
```python
# EOS polls Gmail on schedule rather than using push notifications:
# - Morning cycle: scan inbox for daily brief
# - Nightly review: classify unprocessed emails
# - On-demand: founder triggers via Telegram/Discord command
```

---

## 10. Limits

### API limits
| Resource | Limit |
|----------|-------|
| Daily quota | 1,000,000,000 units |
| Per-user rate | ~25 units/second |
| Messages per send | 500 recipients (consumer) |
| Messages per day | 500 sends (consumer), 2000 (Workspace) |
| Attachment size | 25 MB per message |
| Message size | 35 MB (base64 encoding overhead) |
| Labels per account | 10,000 |
| Label name length | 225 characters |
| Batch requests | 100 per batch |

### Gmail search operators (q parameter)
```
is:unread                    # Unread messages
from:sender@example.com     # From specific sender
to:recipient@example.com    # To specific recipient
subject:"search term"        # In subject line
after:2026/04/01             # After date
before:2026/04/05            # Before date
has:attachment               # Has attachments
label:inbox                  # In specific label
-label:processed             # NOT in label
newer_than:1d                # Within last day
{from:a@b.com from:c@d.com} # OR operator
```

---

## 11. Cost Model

### Gmail API pricing
**Free.** Gmail API is free for all Google accounts.
No per-call charges. Rate limits are the only constraint.

### Google Workspace pricing (if applicable)
| Plan | Price | Gmail included |
|------|-------|---------------|
| Business Starter | $6/user/month | Yes |
| Business Standard | $12/user/month | Yes |
| Business Plus | $18/user/month | Yes |
| Enterprise | Custom | Yes |

### EOS: no direct cost
Gmail access is free. The GWS CLI is free (open source npm package).
Only cost: OAuth token management overhead.

---

## 12. Version Pinning

### Gmail API version
```
# Gmail API v1 — stable, no breaking changes
# Version in URL path: /gmail/v1/users/...
# No version header needed
```

### Python SDK
```bash
pip install google-api-python-client  # Latest
pip install google-auth                # OAuth2 handling
pip install google-auth-oauthlib       # OAuth2 flow

# EOS does not use the SDK directly — uses GWS CLI
```

### GWS CLI
```bash
# Installed via npx (always latest)
npx @googleworkspace/cli

# EOS Dockerfile does NOT pin GWS CLI version
# It runs via npx which downloads latest
```

---

## 13. Design Intent and Tradeoffs

### Why GWS CLI over Python SDK
EOS uses the GWS CLI (`@googleworkspace/cli`) instead of the Python `googleapiclient` because:
1. GWS CLI handles OAuth token storage and refresh automatically
2. No Python dependency for Google auth libraries
3. Consistent subprocess pattern across all GWS integrations (Calendar, Tasks, Drive, Gmail)
4. Single auth flow for all Google services

**Tradeoffs:**
- Pro: Simpler auth, unified access to Calendar + Tasks + Gmail + Drive
- Con: Subprocess overhead per call (~1-2 seconds)
- Con: "Using keyring backend" debug output requires stripping
- Con: Node.js dependency (npx) in Python project

### Why EmailGPS (delegation-first system)
The 7-folder system ensures the founder never touches unprocessed email.
DEX acts as email assistant — classifying, drafting, and routing.
This is a core delegation-first principle: delegation before attention.

### Why approval queue for email sends
EOS never auto-sends emails without founder approval.
Drafts go to `orchestrator/approvals/` or Neon events table.
This prevents AI mistakes from reaching real recipients.

---

## 14. Problem-Solution Map and Hidden Capabilities

### Incremental inbox sync
**Problem:** Polling entire inbox is wasteful.
**Solution:** History API tracks changes since last sync.
Only process new/modified messages. Store `historyId` between syncs.

### Email body decoding
**Problem:** Message bodies are base64url encoded and may be multipart.
**Solution:**
```python
import base64

def get_body(msg):
    payload = msg["payload"]
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    # Multipart: find text/plain part
    for part in payload.get("parts", []):
        if part["mimeType"] == "text/plain" and part["body"].get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    return ""
```

### Gmail search as filter
**Problem:** Need to find specific email types (Calendly confirmations, receipts).
**Solution:** Gmail's `q` parameter supports full search syntax:
```python
# Find Calendly booking confirmations
q = "from:calendly.com subject:confirmed newer_than:1d"

# Find financial receipts
q = "subject:(receipt OR invoice OR payment) newer_than:7d"
```

---

## 15. Operational Behavior and Edge Cases

### GWS CLI outputs debug line before JSON
```
Using keyring backend: keyring.backends.SecretService.Keyring
{"messages": [...]}
```
`GWSConnector._run()` strips lines starting with "Using keyring" before JSON parsing.

### OAuth token expiry
GWS CLI tokens expire after ~1 hour. The CLI auto-refreshes using the refresh token.
If the refresh token is revoked (user changes password, removes app access),
all calls return None until re-authenticated.

### Message body may be in nested parts
Multipart messages can have deeply nested part structures:
```
multipart/mixed
  └── multipart/alternative
        ├── text/plain (body)
        └── text/html (formatted body)
  └── application/pdf (attachment)
```
Always traverse parts recursively to find text/plain.

### Gmail labels are per-account
Labels created by EOS (EmailGPS folders) persist across sessions.
They're visible in the Gmail UI and can be edited by the founder.
Changing a label name in Gmail breaks EOS's label-based routing.

### Batch request format
```python
# Batch up to 100 requests into one HTTP call
batch = service.new_batch_http_request()
for msg_id in message_ids:
    batch.add(service.users().messages().get(userId="me", id=msg_id, format="metadata"))
batch.execute()
```
EOS doesn't use batch requests — volume is too low to justify complexity.

---

## 16. Ecosystem Position and Composition

### Where Gmail fits in EOS
```
Founder's email inbox
  └── GWSConnector (read via GWS CLI)
        └── EmailGPS (classify into 7 folders)
              ├── ANTONY → founder's attention
              ├── TO_RESPOND → DEX drafts response
              ├── REVIEW → daily sync item
              ├── RESPONDED → DEX handled
              ├── WAITING_ON → pending
              ├── RECEIPTS → financial tracking
              └── NEWSLETTERS → low priority
        └── Signal detection
              ├── Calendly confirmations → pipeline update
              ├── Stripe receipts → financial tracking
              └── Lead replies → CRM update
```

### Interfaces
- **With GWS CLI:** Subprocess calls for all Gmail operations
- **With model_router:** AI classification of ambiguous emails
- **With orchestrator:** Morning cycle reads inbox for brief
- **With person_recognition:** Identifies known contacts for priority routing
- **With Neon:** Email GPS folder definitions stored in DB

---

## 17. Trajectory and Evolution

### Current state (2026-04)
- GWS CLI auth: **expired** (needs re-auth)
- EmailGPS: classification logic implemented, 7-folder system
- Draft approval: manual via orchestrator/approvals/
- No push notifications (cron-based polling)

### Potential improvements
- **Push notifications:** Cloud Pub/Sub for real-time email processing
- **Auto-draft sending:** Automated approval workflow for low-risk responses
- **History API:** Incremental sync instead of full inbox scans
- **Batch requests:** For high-volume email classification sessions
- **SendGrid integration:** For marketing/transactional email (separate from Gmail)

### Dependencies
- GWS CLI auth state (requires periodic re-auth)
- Gmail API stability (v1, very stable)
- Google Workspace plan (if sending limits matter)

---

## 18. Conceptual Model and Solution Recipes

### Mental model: DEX as email gatekeeper
Gmail is not an inbox — it's DEX's workspace.
The founder never opens Gmail directly. DEX processes everything first,
classifies it, drafts responses, and presents only what needs attention.

### Recipe: Re-authenticate GWS CLI
```bash
# 1. SSH to VPS
ssh root@100.77.233.50

# 2. Run interactive login
npx @googleworkspace/cli auth login

# 3. Follow OAuth flow in browser
# If no browser: use --no-browser flag and copy URL

# 4. Verify
python3 -c "
import sys; sys.path.insert(0, '/opt/OS')
from eos_ai.gws_connector import GWSConnector
gws = GWSConnector()
events = gws.get_today_events()
print(f'Calendar events: {len(events)}')
"
```

### Recipe: Add new EmailGPS classification rule
```python
# In eos_ai/email_gps.py:

# 1. Add to hard rules (pattern matching, no AI needed)
_FINANCIAL_SIGNALS = [..., "new_keyword"]

# 2. Or add to AI classification prompt
# The model_router call includes folder definitions
# Update the prompt to include new classification criteria

# 3. Test
python3 -c "
from eos_ai.email_gps import EmailGPS, ProcessedEmail
gps = EmailGPS(ctx)
# ... classify test email
"
```

---

## 19. Industry Expert and Cutting-Edge Usage

### EmailGPS as executive assistant pattern
EOS implements a delegation-first email system:
the founder's inbox is managed by an AI assistant (DEX) that:
1. Classifies every email before the founder sees it
2. Drafts responses for approval
3. Handles routine emails completely
4. Surfaces only what requires the founder's direct attention

This is the same pattern a human EA would follow — but automated.

### Signal extraction from email
Gmail isn't just email — it's a signal source:
```python
# Calendly confirmations → booking pipeline
# Stripe receipts → revenue tracking
# Lead replies → CRM updates
# Newsletter content → market intelligence

# EmailGPS routes each signal type to the appropriate pipeline
```

### Multi-account architecture (future)
GWS CLI supports multiple Google accounts.
As EOS manages more ventures, each could have its own Gmail account
with venture-specific EmailGPS rules and classification.

---

## 20. EOS Usage Patterns

### Morning brief email section
```python
# orchestrator.py morning cycle:
gws = GWSConnector()
# Read unread count
data = gws._run("gmail", "users", "messages", "list",
    params={"userId": "me", "q": "is:unread", "maxResults": 5})
unread_count = data.get("resultSizeEstimate", 0)
# Include in morning brief: "Unread emails: {unread_count}"
```

### Email GPS daily process
```python
# Nightly or on-demand:
# 1. List all unprocessed emails
# 2. For each: classify → apply label → draft if needed
# 3. Store classification results in Neon
# 4. Include summary in next morning brief
```

### DEX response template
```python
DEX_TEMPLATE = (
    'Hi {name},\n\n'
    'This is DEX, Antony\'s assistant. '
    'I got to this email before him '
    'and thought you\'d appreciate '
    'a speedy reply.\n\n'
    '{response}\n\n'
    'Best,\n'
    'DEX\n'
    'On behalf of Antony Munoz'
)
```

---

## 21. Gotchas (Real EOS Production Issues)

### GWS CLI auth expired (ACTIVE — as of 2026-04-03)
The GWS CLI token has expired. All Gmail and Calendar operations return None.
**Symptom:** Morning brief shows no calendar or email data.
**Fix:** Re-run `npx @googleworkspace/cli auth login` interactively on VPS.

### "Using keyring backend" line breaks JSON parsing (RESOLVED)
GWS CLI outputs a debug line before JSON response.
**Fix:** `_run()` strips lines starting with "Using keyring".

### Draft approval pipeline not fully automated (ACTIVE)
EmailGPS generates drafts but the approval-to-send flow is manual.
Drafts accumulate in `orchestrator/approvals/` without being sent.
**Impact:** DEX's email responses require founder to manually approve and send.

### Gmail API quota units are per-call, not per-message (BY DESIGN)
`messages.list` costs 5 units regardless of `maxResults` value.
Getting 1 message or 100 messages costs the same 5 units.
**Impact:** None for EOS — usage is well under daily limits.

### Multipart message body extraction (ACTIVE)
Some emails have deeply nested MIME structures. Body text may be in
`payload.parts[0].parts[0].body.data` instead of `payload.body.data`.
**Fix:** Recursive part traversal, looking for `text/plain` MIME type.

### OAuth scope changes require re-consent (BY DESIGN)
Adding a new scope (e.g., `gmail.send`) requires the user to re-authorize.
The old token with fewer scopes won't work for the new operations.
**Fix:** Request all needed scopes upfront during initial auth.

### Sending limits vary by account type (ACTIVE)
Consumer Gmail: 500 sends/day. Google Workspace: 2000 sends/day.
EOS currently sends <10 emails/day — not a concern now.
**Risk:** Could become relevant when scaling outreach automation.
