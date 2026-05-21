---
name: calendly
description: "Use when any agent needs to handle sales call bookings, cancellations, webhook verification, pipeline triggers, or meeting record creation."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://developer.calendly.com/"
last_researched: "2026-04-04"
instantiated_from: templates/tools/_template/
api_version: "Calendly API v2"
sdk_version: "REST API direct (Flask webhook receiver)"
speed_category: "medium"
trigger: both
effort: medium
context: fork
---

# Tool: Calendly

## What This Tool Does

Calendly webhooks notify EOS when sales calls are booked or canceled. It is the trigger point for the entire sales pipeline — a booking event creates a lead record, updates the CRM, triggers prep briefs, and notifies the founder.

EOS does not use the Calendly REST API for reading events. It only receives inbound webhooks.

## EOS Integration

### Primary: `services/calendly_webhook.py` (os-webhook container, Flask on port 8080)

**What it does on `invitee.created` (booking):**
1. Verifies webhook signature (HMAC-SHA256)
2. Extracts invitee name, email, event time, questions/answers
3. Finds or creates lead file in `03_CRM/Leads/`
4. Updates lead stage to "Booked" in markdown pipeline + Notion CRM
5. Creates meeting record in Neon + Notion via `meetings.py`
6. Runs person recognition (pre-meeting intel check)
7. Builds prep brief with `build_prep_brief()`
8. Publishes event to EventBus (`lead_booked`)
9. Sends Discord alert with prep brief
10. Sends Telegram notification
11. Logs outcome to memory.db (RLHF feedback loop)

**What it does on `invitee.canceled`:**
1. Verifies webhook signature
2. Updates lead stage to "Lost" in markdown pipeline
3. Generates cancellation recovery email draft via model_router
4. Stores draft in Neon events table (pending_approval)
5. Posts draft to Discord for founder approval
6. Sends Telegram notification
7. Logs negative outcome to memory.db

**Architecture:**
```
Calendly (booking confirmed)
  → POST https://vps:8080/webhooks/calendly
    → verify_signature(payload, Calendly-Webhook-Signature)
      → calendly_webhook.py
            ├── find_lead_by_name_or_email()
            ├── update_lead_file() [markdown]
            ├── move_pipeline_card() [markdown kanban]
            ├── update_notion_lead_stage() [Notion API]
            ├── create_meeting_record() [Neon + Notion]
            ├── recognize_person() [pre-meeting intel check]
            ├── build_prep_brief() [AI-generated]
            ├── EventBus.publish_async("lead_booked")
            ├── Discord webhook alert
            ├── Telegram notification
            └── _log_calendly_outcome() [memory.db RLHF]
```

### Venture detection from event name
```python
def _detect_venture_from_event(event_name):
    name = event_name.lower()
    if any(k in name for k in ['lyfe', 'initiate', 'arena', 'coaching']):
        return 'Lyfe Institute'
    if any(k in name for k in ['brand', 'content', 'antony']):
        return 'Personal Brand'
    return 'Empyrean Creative'  # default for B2B
```

### Other modules that reference Calendly:
- `eos_ai/meetings.py` — creates meeting records from booking data
- `eos_ai/ceo_intelligence.py` — checks for upcoming calls
- `eos_ai/email_gps.py` — detects Calendly confirmation emails
- `eos_ai/memory.py` — logs booking outcomes for RLHF
- `eos_ai/event_bus.py` — `lead_booked` event triggers downstream handlers
- `scripts/call_prep.py` — pre-call research brief generation
- `scripts/noshow_detector.py` — detects no-shows after scheduled time

### Agents that use it
- Pipeline Handler (directly — processes webhook events)
- EA Agent (indirectly — receives booking notifications)
- CEO Agent (indirectly — pre-call briefings)
- DEX (indirectly — Discord alerts)

## Authentication

### Webhook signature verification
```python
CALENDLY_SIGNING_KEY = os.getenv("CALENDLY_SIGNING_KEY")

def verify_signature(payload: bytes, signature: str) -> bool:
    if not CALENDLY_SIGNING_KEY:
        return True  # Skip verification if key not set
    expected = hmac.new(
        CALENDLY_SIGNING_KEY.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Signing key configured in Calendly dashboard > Webhooks > Signing Key.
Stored in `services/.env` as `CALENDLY_SIGNING_KEY`.

### Webhook subscription
Configured in Calendly dashboard (not via API in EOS):
- URL: `https://<vps-ip>:8080/webhooks/calendly`
- Events: `invitee.created`, `invitee.canceled`
- Scope: Organization

## Quick Reference

### Webhook payload structure
```json
{
  "event": "invitee.created",
  "payload": {
    "event": {
      "uuid": "evt_...",
      "name": "Initiate Arena Discovery Call",
      "start_time": "2026-04-05T10:00:00-07:00",
      "end_time": "2026-04-05T10:30:00-07:00",
      "location": {
        "type": "google_conference",
        "join_url": "https://meet.google.com/..."
      }
    },
    "invitee": {
      "name": "John Doe",
      "email": "john@example.com",
      "timezone": "America/Los_Angeles",
      "questions_and_answers": [
        {"question": "What company are you with?", "answer": "Acme Corp"}
      ],
      "cancel_url": "https://calendly.com/cancellations/...",
      "reschedule_url": "https://calendly.com/reschedulings/..."
    },
    "cancellation": {
      "reason": "Schedule conflict"
    }
  },
  "created_at": "2026-04-04T09:00:00.000Z"
}
```

### Health check
```bash
curl http://localhost:8080/health
# {"status": "ok"}
```

## Gotchas

### Signing key not set — all webhooks accepted (ACTIVE)
When `CALENDLY_SIGNING_KEY` is not in env, `verify_signature()` returns True for all requests.
This is a security risk — any POST to `/webhooks/calendly` will be processed.
**Fix:** Set `CALENDLY_SIGNING_KEY` in services/.env from Calendly dashboard.

### Calendly retries failed webhooks up to 7 times (BY DESIGN)
If the webhook endpoint returns non-2xx or times out (>10 seconds), Calendly retries with exponential backoff.
**Risk:** Duplicate processing if the first request succeeded but returned non-200.
**Mitigation:** Use `event.uuid` for idempotency. EOS does NOT currently deduplicate.

### os-webhook must be accessible on port 8080 (ACTIVE)
The Flask server listens on 0.0.0.0:8080. Firewall must allow inbound from Calendly's IP range.
Docker Compose exposes port 8080 on the host.
**Detection:** Webhook not received — check `docker logs os-webhook`.

### Pipeline card move fails silently (ACTIVE)
`move_pipeline_card()` manipulates raw markdown in `03_CRM/Pipeline.md`.
If the username isn't found in the expected stage section, it returns False silently.
**Impact:** Lead card stays in old stage. Notion update still works independently.

### Cancellation recovery email requires working model_router (ACTIVE)
Draft generation uses `model_router.call()` with FAST_RESPONSE task type.
If all providers are down (Anthropic 401, Gemini 429, Ollama OOM), the draft fails silently.
**Fallback:** Telegram notification still fires, just without the email draft.

### Notion CRM update uses raw requests, not NotionPublisher (BY DESIGN)
`update_notion_lead_stage()` in calendly_webhook.py makes direct Notion API calls,
not using `notion_publisher.py`. This is because it updates existing pages (PATCH),
while NotionPublisher only creates pages (POST).

See references/best_practices.md for full webhook schema, retry behavior, and API reference.
