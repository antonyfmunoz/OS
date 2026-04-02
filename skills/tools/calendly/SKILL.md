---
name: calendly-tool
description: "Calendly webhook integration for EOS. Use when a sales call is booked and the booking needs to trigger the sales pipeline."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developer.calendly.com/api-docs"
last_researched: "2026-04-01"
effort: low
trigger: both
context: fork
---

# Tool: Calendly

## What This Tool Does
Calendly webhooks notify EOS when calls are booked or cancelled.
EOS uses it as the trigger for the sales pipeline — booking = lead enters pipeline.

## EOS Integration
- services/calendly_webhook.py — Flask server on port 8080 (os-webhook Docker service)
- Receives: invitee.created (booking) and invitee.canceled events
- Triggers: lead creation in Neon, Notion CRM update, DEX notification
- CALENDLY_WEBHOOK_SIGNING_KEY in services/.env for signature verification

## Quick Reference
```python
# Webhook verification
import hmac, hashlib

def verify_signature(payload: bytes, signature: str, key: str) -> bool:
    expected = hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

# Event types
# invitee.created — new booking
# invitee.canceled — cancellation
```

See references/best_practices.md for event schema and retry behavior.


## Gotchas
- Add failures here as they occur.
- This section compounds over time.
