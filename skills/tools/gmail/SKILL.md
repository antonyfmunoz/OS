---
name: gmail-tool
description: "Gmail API integration for EOS. Use when DEX needs to read, draft, send, or categorize emails on behalf of the founder."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developers.google.com/gmail/api/guides"
last_researched: "2026-04-01"
---

# Tool: Gmail

## What This Tool Does
Gmail API provides read/write access to email threads, messages, labels, and drafts.
EOS uses it as the founder's email interface — DEX reads inbox, drafts responses, and routes signals.

## EOS Integration
- DEX reads inbox via GWS connector (eos_ai/gws_connector.py)
- email_reviewer.py runs nightly review
- email_gps.py handles email-triggered workflows
- Approvals queue: drafts staged to orchestrator/approvals/ before sending

## Authentication
OAuth2 credentials stored in eos_ai/.env.
Token refresh handled automatically by google-auth library.

## Quick Reference
```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

service = build('gmail', 'v1', credentials=creds)

# List messages
messages = service.users().messages().list(userId='me', q='is:unread').execute()

# Get message
msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

# Send draft
service.users().drafts().send(userId='me', body={'id': draft_id}).execute()
```

See references/best_practices.md for quotas and pagination.
