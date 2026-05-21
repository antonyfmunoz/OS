---
name: gmail
description: "Use when any agent needs to read inbox, classify emails, draft responses, manage labels, or handle email-triggered workflows via Gmail API."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developers.google.com/gmail/api/guides"
last_researched: "2026-04-04"
instantiated_from: templates/tools/_template/
api_version: "Gmail API v1"
sdk_version: "GWS CLI (@googleworkspace/cli via npx) + googleapiclient (Python)"
speed_category: "medium"
trigger: both
effort: medium
context: fork
---

# Tool: Gmail

## What This Tool Does

The Gmail API provides read/write access to email threads, messages, labels, drafts, and settings. EOS uses it as the founder's email interface — DEX reads inbox, classifies emails into the 7-folder GPS system, drafts responses, and routes signals to the intelligence pipeline.

Core capabilities:
- **Message operations** — list, get, send, modify, trash, delete
- **Draft operations** — create, update, send, delete
- **Label management** — create, update, list, apply to messages
- **History** — incremental sync via historyId
- **Push notifications** — watch via Cloud Pub/Sub
- **Search** — Gmail search syntax (q parameter)

## EOS Integration

### Primary: `eos_ai/gws_connector.py` — GWS CLI wrapper

EOS accesses Gmail through the Google Workspace CLI (`@googleworkspace/cli`), not the Python SDK directly. The `GWSConnector` class wraps CLI commands as subprocess calls.

```python
from eos_ai.gws_connector import GWSConnector

gws = GWSConnector()
# All methods are safe — log warnings on error, never crash
```

**How it works:**
```python
def _run(self, *args, params=None, body=None):
    cmd = ["npx", "@googleworkspace/cli"] + list(args)
    if params:
        cmd += ["--params", json.dumps(params)]
    if body:
        cmd += ["--json", json.dumps(body)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    # Strips "Using keyring backend: keyring" line before JSON parsing
    return json.loads(clean_output)
```

### Secondary: `eos_ai/email_gps.py` — EmailGPS (7-folder system)

**Folders:**
| Folder | Purpose |
|--------|---------|
| `ANTONY` | His eyes only — needs direct attention |
| `TO_RESPOND` | DEX drafts response, Antony approves |
| `REVIEW` | Discussed in daily sync |
| `RESPONDED` | DEX handled completely |
| `WAITING_ON` | Replied, waiting on someone |
| `RECEIPTS` | All financial emails (receipt, invoice, payment, etc.) |
| `NEWSLETTERS` | Anything with unsubscribe link |

**Rule:** Antony never touches email that DEX hasn't processed first.

**Classification flow:**
1. Hard rules: financial keywords in subject → RECEIPTS
2. Noise detection: social notifications (Reddit, Quora, etc.) → bulk delete
3. Person recognition: known contacts get priority routing
4. AI classification: model_router for ambiguous emails

### Other modules:
- `eos_ai/orchestrator.py` — morning cycle reads inbox for daily brief
- `eos_ai/daily_sync.py` — email status in daily sync
- `eos_ai/coordination_engine.py` — email-based coordination
- `scripts/inbox_zero_init.py` — initial inbox setup
- `scripts/eod_sync.py` — end-of-day email summary

### Agents that use it
- DEX (primary — inbox management, email GPS)
- EA Agent (drafts, scheduling)
- CEO Agent (signal detection from emails)

## Authentication

### GWS CLI auth (primary)
```bash
# Interactive login — run once
npx @googleworkspace/cli auth login

# Token stored in system keyring
# Auto-refreshes on subsequent CLI calls
```

**Auth state:** Managed by the GWS CLI's keyring integration.
The `_run()` method strips the "Using keyring backend" debug line from output.

### OAuth2 scopes required
```
gmail.readonly          — read messages, labels
gmail.modify            — modify labels, mark read/unread
gmail.send              — send emails
gmail.compose           — create/update/send drafts
gmail.labels            — manage labels
```

### Environment variables
| Variable | Purpose |
|----------|---------|
| `GMAIL_OAUTH_CLIENT_ID` | OAuth client ID (GWS connector) |
| `GMAIL_OAUTH_CLIENT_SECRET` | OAuth client secret |
| No token env var | Tokens managed by GWS CLI keyring |

## Quick Reference

### Read inbox via GWS CLI
```python
gws = GWSConnector()

# Get today's unread emails
data = gws._run(
    "gmail", "users", "messages", "list",
    params={"userId": "me", "q": "is:unread", "maxResults": 20},
)
messages = data.get("messages", [])

# Get full message
msg = gws._run(
    "gmail", "users", "messages", "get",
    params={"userId": "me", "id": msg_id, "format": "full"},
)
```

### Email classification (EmailGPS)
```python
from eos_ai.email_gps import EmailGPS, EmailFolder

gps = EmailGPS(ctx)

# Financial keywords → RECEIPTS (hard rule, no AI needed)
_FINANCIAL_SIGNALS = ['receipt', 'invoice', 'payment', 'order confirmation', ...]

# Noise senders → bulk delete
NOISE_SENDERS = ['reddit.com', 'quora.com', 'medium.com', ...]

# DEX response template
DEX_TEMPLATE = (
    'Hi {name},\n\n'
    'This is DEX, Antony\'s assistant. '
    'I got to this email before him ...\n\n'
    '{response}\n\n'
    'Best,\nDEX\nOn behalf of Antony Munoz'
)
```

### Send email via Python SDK (alternative path)
```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

service = build('gmail', 'v1', credentials=creds)

# List messages
results = service.users().messages().list(userId='me', q='is:unread').execute()

# Get message
msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

# Send
import base64
from email.mime.text import MIMEText

message = MIMEText("Body text")
message['to'] = 'recipient@example.com'
message['subject'] = 'Subject'
raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
service.users().messages().send(userId='me', body={'raw': raw}).execute()
```

## Gotchas

### GWS CLI auth expires (ACTIVE — as of 2026-04-03)
The GWS CLI auth token has expired. All Gmail operations return None.
**Fix:** Re-run `npx @googleworkspace/cli auth login` interactively on VPS.
**Impact:** Morning brief shows no calendar/email data until re-authed.

### "Using keyring backend" line breaks JSON parsing (RESOLVED)
GWS CLI outputs a debug line before JSON. `_run()` strips it.
```python
clean = "\n".join(l for l in lines if not l.startswith("Using keyring"))
```

### Gmail API quota is per-call, not per-message (BY DESIGN)
`messages.list` costs 5 quota units per call regardless of `maxResults`.
`messages.send` costs 100 units. Daily limit: 1 billion units (effectively unlimited for EOS).
Practical sending limit: ~500/day consumer, 2000/day Google Workspace.

### Draft approval flow not fully wired (ACTIVE)
EmailGPS generates drafts and stores them in `orchestrator/approvals/`, but the approval-to-send pipeline is manual. DEX doesn't auto-send — founder must approve.
**Impact:** Drafts accumulate without being sent if founder doesn't check approvals.

### Email responses must use DEX template (ACTIVE)
All email responses go through DEX_TEMPLATE to maintain the EA persona.
Never send email directly as Antony — always through DEX.

### No push notifications configured (ACTIVE)
EOS polls for new emails rather than using Gmail's Cloud Pub/Sub watch().
**Impact:** Email processing happens on cron schedule, not real-time.

See references/best_practices.md for full API reference, quota details, and anti-patterns.
