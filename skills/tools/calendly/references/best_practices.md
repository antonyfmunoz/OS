# Calendly API — Best Practices (Creator-Level Reference)

Source: Calendly Developer Docs + EOS production experience
Version: Calendly API v2
Last Researched: 2026-04-04

---

## 1. Authentication

### Webhook signature verification (EOS primary)
```python
import hmac
import hashlib

CALENDLY_SIGNING_KEY = os.getenv("CALENDLY_SIGNING_KEY")

def verify_signature(payload: bytes, signature: str) -> bool:
    if not CALENDLY_SIGNING_KEY:
        return True  # SECURITY RISK — skip if key not set
    expected = hmac.new(
        CALENDLY_SIGNING_KEY.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# Signature header: Calendly-Webhook-Signature
signature = request.headers.get("Calendly-Webhook-Signature", "")
```

Signing key configured in: Calendly Dashboard > Webhooks > Signing Key.
Stored in `services/.env` as `CALENDLY_SIGNING_KEY`.

### Personal Access Token (for REST API — not used by EOS)
```
Authorization: Bearer <personal_access_token>

# Generated at: calendly.com/integrations/api_webhooks
# Token starts with: eyJhbGciO... (JWT format)
```

### OAuth2 (for multi-user apps — not used by EOS)
```
Authorization: Bearer <oauth_access_token>

# OAuth flow:
# 1. Redirect to: https://auth.calendly.com/oauth/authorize?client_id=...
# 2. User grants access
# 3. Exchange code for token: POST https://auth.calendly.com/oauth/token
```

---

## 2. Core Operations with Exact Signatures

### Webhook events (EOS's primary Calendly interface)

**invitee.created (booking confirmed)**
```
POST https://your-server.com/webhooks/calendly

Headers:
  Calendly-Webhook-Signature: <hmac-sha256-hex>
  Content-Type: application/json

Body:
{
    "event": "invitee.created",
    "payload": {
        "event": {
            "uuid": "evt_abc123",
            "name": "Initiate Arena Discovery Call",
            "start_time": "2026-04-05T10:00:00.000000Z",
            "end_time": "2026-04-05T10:30:00.000000Z",
            "status": "active",
            "location": {
                "type": "google_conference",
                "join_url": "https://meet.google.com/abc-defg-hij"
            },
            "event_memberships": [
                {"user": "https://api.calendly.com/users/user_uuid"}
            ],
            "event_type": "https://api.calendly.com/event_types/type_uuid"
        },
        "invitee": {
            "uuid": "inv_xyz789",
            "name": "John Doe",
            "email": "john@example.com",
            "timezone": "America/Los_Angeles",
            "created_at": "2026-04-04T09:00:00.000000Z",
            "cancel_url": "https://calendly.com/cancellations/inv_xyz789",
            "reschedule_url": "https://calendly.com/reschedulings/inv_xyz789",
            "questions_and_answers": [
                {
                    "question": "What company are you with?",
                    "answer": "Acme Corp",
                    "position": 0
                },
                {
                    "question": "What's your biggest challenge right now?",
                    "answer": "Can't stay consistent with my goals",
                    "position": 1
                }
            ],
            "tracking": {
                "utm_source": "instagram",
                "utm_medium": "dm",
                "utm_campaign": "arena_launch"
            }
        }
    },
    "created_at": "2026-04-04T09:00:05.000000Z"
}
```

**invitee.canceled**
```json
{
    "event": "invitee.canceled",
    "payload": {
        "event": { ... },
        "invitee": {
            "name": "John Doe",
            "email": "john@example.com",
            ...
        },
        "cancellation": {
            "canceled_by": "John Doe",
            "reason": "Schedule conflict",
            "canceler_type": "invitee"
        }
    }
}
```

### REST API endpoints (reference — EOS uses webhooks only)

**List event types**
```
GET https://api.calendly.com/event_types?user=https://api.calendly.com/users/{uuid}

Headers:
  Authorization: Bearer <token>

Response:
{
    "collection": [
        {
            "uri": "https://api.calendly.com/event_types/type_uuid",
            "name": "Initiate Arena Discovery Call",
            "active": true,
            "duration": 30,
            "kind": "solo",
            "scheduling_url": "https://calendly.com/antony/discovery",
            "color": "#8247f5"
        }
    ],
    "pagination": {
        "count": 5,
        "next_page": null,
        "next_page_token": null
    }
}
```

**List scheduled events**
```
GET https://api.calendly.com/scheduled_events?user=...&min_start_time=...&max_start_time=...

Response:
{
    "collection": [
        {
            "uri": "https://api.calendly.com/scheduled_events/evt_uuid",
            "name": "Discovery Call",
            "status": "active",
            "start_time": "2026-04-05T10:00:00.000000Z",
            "end_time": "2026-04-05T10:30:00.000000Z",
            "event_type": "https://api.calendly.com/event_types/type_uuid",
            "invitees_counter": {"total": 1, "active": 1}
        }
    ]
}
```

**Get invitee details**
```
GET https://api.calendly.com/scheduled_events/{event_uuid}/invitees

Response:
{
    "collection": [
        {
            "uri": "https://api.calendly.com/invitees/inv_uuid",
            "email": "john@example.com",
            "name": "John Doe",
            "status": "active",
            "questions_and_answers": [...]
        }
    ]
}
```

### Webhook subscription (API)
```
POST https://api.calendly.com/webhook_subscriptions

Headers:
  Authorization: Bearer <token>

Body:
{
    "url": "https://your-server.com/webhooks/calendly",
    "events": ["invitee.created", "invitee.canceled"],
    "organization": "https://api.calendly.com/organizations/org_uuid",
    "scope": "organization",
    "signing_key": "your-signing-key"
}
```

---

## 3. Pagination Patterns

### REST API pagination
```python
# Calendly uses page_token cursor pagination
events = []
page_token = None

while True:
    params = {
        "user": user_uri,
        "min_start_time": start.isoformat(),
        "count": 100,  # max 100 per page
    }
    if page_token:
        params["page_token"] = page_token
    
    resp = requests.get(
        "https://api.calendly.com/scheduled_events",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
    )
    data = resp.json()
    events.extend(data["collection"])
    
    page_token = data.get("pagination", {}).get("next_page_token")
    if not page_token:
        break
```

### Webhook events: no pagination
Webhook events arrive individually. Each booking/cancellation is one webhook call.
No pagination needed.

---

## 4. Rate Limits

### API rate limits
```
100 requests per 15 seconds per API key

429 Too Many Requests when exceeded.
Retry-After header included in response.
```

### Webhook response requirement
```
Must return 2xx within 10 seconds.
Non-2xx or timeout → Calendly retries (up to 7 times).
```

### EOS webhook timing
```python
# calendly_webhook.py processes synchronously:
# 1. Verify signature (~0ms)
# 2. Find lead file (~50ms)
# 3. Update markdown files (~100ms)
# 4. Update Notion (~500ms)
# 5. Create meeting record (~300ms)
# 6. Person recognition (~200ms)
# 7. Build prep brief (~1-3s with AI)
# 8. Send Discord/Telegram (~200ms)
# Total: ~2-5 seconds — within 10s limit

# RISK: If AI draft generation is slow (model_router timeout),
# could exceed 10s and trigger retry
```

---

## 5. Error Codes and Recovery

### API HTTP status codes
| Code | Meaning | Recovery |
|------|---------|----------|
| 200 | Success | — |
| 201 | Created (webhook subscription) | — |
| 400 | Bad request | Check request body |
| 401 | Unauthorized (invalid token) | Check/regenerate API token |
| 403 | Forbidden (insufficient scope) | Check OAuth permissions |
| 404 | Not found | Check UUID in URL |
| 409 | Conflict (duplicate subscription) | Subscription already exists |
| 429 | Rate limited | Respect Retry-After header |
| 500 | Server error | Retry with backoff |

### Webhook retry behavior
```
Retry schedule (exponential backoff):
  Attempt 1: immediate
  Attempt 2: ~1 minute
  Attempt 3: ~4 minutes
  Attempt 4: ~15 minutes
  Attempt 5: ~1 hour
  Attempt 6: ~4 hours
  Attempt 7: ~12 hours (final)

Total: up to 7 retries over ~17 hours
After 7 failures: webhook marked as failed, no more retries
```

### EOS error handling
```python
@app.route("/webhooks/calendly", methods=["POST"])
def calendly_webhook():
    # 1. Verify signature
    if not verify_signature(request.data, signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    # 2. Process event
    try:
        # ... processing logic
        return jsonify({"status": "booked"}), 200
    except Exception as e:
        # Log but don't crash — return 200 to prevent retries
        print(f"[Calendly] Processing error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 200
        # NOTE: EOS returns 200 even on error to prevent duplicate retries
```

---

## 6. SDK Idioms

### EOS uses Flask for webhook receiving
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhooks/calendly", methods=["POST"])
def calendly_webhook():
    signature = request.headers.get("Calendly-Webhook-Signature", "")
    if not verify_signature(request.data, signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    data = request.json
    event_type = data.get("event")
    payload = data.get("payload", {})
    invitee = payload.get("invitee", {})
    
    if event_type == "invitee.created":
        # Process booking
        return jsonify({"status": "booked"}), 200
    elif event_type == "invitee.canceled":
        # Process cancellation
        return jsonify({"status": "canceled"}), 200
    
    return jsonify({"status": "ignored"}), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

### Venture detection pattern
```python
def _detect_venture_from_event(event_name):
    name = event_name.lower()
    if any(k in name for k in ['lyfe', 'initiate', 'arena', 'coaching']):
        return 'Lyfe Institute'
    if any(k in name for k in ['brand', 'content', 'antony']):
        return 'Personal Brand'
    return 'Empyrean Creative'  # B2B default
```

### Meeting record creation
```python
from eos_ai.meetings import create_meeting_record, build_prep_brief

record = create_meeting_record(
    title=event_name,
    person=name,
    email=email,
    company=company,
    date_iso=event_time,
    meeting_type='Sales Call',
    venture=venture,
    source='Calendly',
    meet_link=meet_link,
    calendly_event_id=cal_event_id,
)
# Returns: {"neon_id": ..., "notion_id": ...}

brief = build_prep_brief(
    person=name,
    email=email,
    company=company,
    meeting_type='Sales Call',
    venture=venture,
)
```

---

## 7. Anti-Patterns

### 1. Not verifying webhook signatures
```python
# WRONG — accepts any POST to the webhook URL
@app.route("/webhooks/calendly", methods=["POST"])
def webhook():
    data = request.json
    process(data)  # No verification!

# RIGHT — always verify
if not verify_signature(request.data, signature):
    return jsonify({"error": "Invalid signature"}), 401
```

### 2. Synchronous AI processing in webhook handler
```python
# WRONG — blocks webhook response, risks 10s timeout
result = model_router.call(model, complex_prompt)  # 5-10 seconds
# Calendly retries if response takes >10s

# RIGHT — return 200 immediately, process async
# Or: keep AI processing fast (FAST_RESPONSE task type)
```

### 3. No idempotency handling
```python
# WRONG — processes duplicate webhook deliveries
if event_type == "invitee.created":
    create_lead(name, email)  # Creates duplicate if retried

# RIGHT — check for existing lead before creating
lead_file = find_lead_by_name_or_email(name, email)
if not lead_file:
    create_lead(name, email)
```

### 4. Returning non-2xx on processing errors
```python
# WRONG — triggers retry cascade
except Exception as e:
    return jsonify({"error": str(e)}), 500
    # Calendly retries 7 times — creates 7 duplicate leads

# RIGHT — return 200 to acknowledge receipt, handle errors internally
except Exception as e:
    logger.error(f"Processing error: {e}")
    return jsonify({"status": "error_logged"}), 200
```

### 5. Hardcoded event type names
```python
# WRONG — breaks if Calendly event name changes
if event_name == "Initiate Arena Discovery Call":
    venture = "Lyfe Institute"

# RIGHT — keyword-based detection
if any(k in event_name.lower() for k in ['lyfe', 'initiate', 'arena']):
    venture = "Lyfe Institute"
```

---

## 8. Data Model

### Calendly entity hierarchy
```
Organization
  └── Users (event hosts)
        └── Event Types (scheduling pages)
              └── Scheduled Events (bookings)
                    └── Invitees (attendees)
                          └── Questions & Answers
                          └── Tracking (UTM params)
                          └── Cancellation (if canceled)
```

### EOS data flow on booking
```
Calendly booking
  → Webhook POST /webhooks/calendly
    → Signature verification
      → Extract invitee data
        → find_lead_by_name_or_email()
          ├── Found → update_lead_file() → move_pipeline_card()
          └── Not found → create_lead_file()
        → update_notion_lead_stage() [Notion CRM]
        → create_meeting_record() [Neon + Notion]
        → recognize_person() [Martell rule]
        → build_prep_brief() [AI-generated]
        → EventBus.publish_async("lead_booked")
        → Discord webhook alert
        → Telegram notification
        → _log_calendly_outcome() [RLHF]
```

### EOS data flow on cancellation
```
Calendly cancellation
  → Webhook POST /webhooks/calendly
    → Signature verification
      → Extract invitee + cancellation reason
        → update_lead_file("Lost")
        → move_pipeline_card("Booked" → "Lost")
        → model_router → draft recovery email
        → Store draft in Neon events (pending_approval)
        → Discord alert with draft
        → Telegram notification
        → _log_calendly_outcome("no_reply", 0.0)
```

### Lead file format (created on booking)
```markdown
---
name: John Doe
email: john@example.com
company: Acme Corp
source: calendly
venture: Lyfe Institute
kanban_stage: Booked
status: booked
created: 2026-04-04
---

# Lead: John Doe

## Call Booked
Date: 2026-04-05T10:00:00-07:00
Logged: 2026-04-04
```

---

## 9. Webhooks and Events

### Available webhook event types
| Event | Trigger |
|-------|---------|
| `invitee.created` | New booking confirmed |
| `invitee.canceled` | Booking canceled by invitee or host |
| `routing_form_submission.created` | Routing form submitted |

### Webhook subscription management
```
POST   /webhook_subscriptions        # Create subscription
GET    /webhook_subscriptions/{uuid}  # Get subscription details
DELETE /webhook_subscriptions/{uuid}  # Remove subscription
GET    /webhook_subscriptions         # List subscriptions

# EOS: subscription configured in Calendly dashboard, not via API
```

### Webhook payload structure
```json
{
    "event": "invitee.created",      // Event type
    "payload": {
        "event": { ... },             // Scheduled event details
        "invitee": { ... },           // Attendee details
        "cancellation": { ... }       // Only for invitee.canceled
    },
    "created_at": "2026-04-04T..."   // When webhook was generated
}
```

### EOS event chain
```
Calendly webhook received
  → calendly_webhook.py processes
    → EventBus.publish_async("lead_booked", {...})
      → Downstream handlers (pipeline_handler.py)
        → CRM updates, notifications, prep brief generation
```

---

## 10. Limits

### API limits
| Resource | Limit |
|----------|-------|
| Rate limit | 100 requests/15 seconds |
| Pagination | 100 items max per page |
| Webhook subscriptions | 200 per organization |
| Webhook response time | 10 seconds |
| Webhook retries | 7 attempts |
| Event types per user | Unlimited |
| Scheduled events | Unlimited |

### EOS usage
```
Webhook calls/day: 0-5 (dependent on bookings)
API calls/day: 0 (EOS doesn't use REST API)
Processing time: 2-5 seconds per webhook
```

---

## 11. Cost Model

### Calendly pricing
| Plan | Price | Webhook support |
|------|-------|----------------|
| Free | $0 | No webhooks |
| Standard | $10/seat/month | Yes |
| Teams | $16/seat/month | Yes |
| Enterprise | Custom | Yes + advanced |

**EOS uses Standard or Teams plan** (webhooks required).

### Webhook processing cost
Calendly webhooks are free (included in plan).
EOS cost per booking webhook:
- Flask processing: free (self-hosted)
- Notion API call: free
- AI prep brief: ~$0.001 (Haiku/fast_response)
- Discord/Telegram: free
- Total: ~$0.001 per booking

---

## 12. Version Pinning

### API version
```
# Calendly API v2 — current and only supported version
# Base URL: https://api.calendly.com
# No version header — v2 is default
# v1 was deprecated in 2023
```

### Webhook payload version
```
# No explicit versioning
# Payload structure has been stable since v2 launch
# Calendly announces changes in developer changelog
```

### EOS dependencies
```bash
# Flask (webhook receiver)
pip install flask  # Any modern version

# No Calendly SDK — raw webhook processing only
```

---

## 13. Design Intent and Tradeoffs

### Why webhook-only (no REST API polling)
Calendly webhooks provide real-time notifications on booking events.
There's no need to poll the REST API because:
1. Bookings are infrequent (0-5/day during outreach phase)
2. Real-time notification is critical (founder needs to prepare for calls)
3. Webhook includes all necessary data (no follow-up API calls needed)

**Tradeoff:** Webhook delivery is not guaranteed (network issues, server downtime).
Calendly retries 7 times, but events could still be lost.

### Why Flask over Django/FastAPI
The webhook receiver is a simple HTTP endpoint. Flask is the minimal framework
for this — one file, one route, no ORM, no middleware needed.

### Why synchronous processing
EOS processes webhooks synchronously (not queued) because:
1. Processing time (2-5s) is within Calendly's 10s limit
2. Volume is low (0-5 webhooks/day)
3. Simplicity — no message queue infrastructure needed

**Risk:** If AI draft generation gets slow, could exceed 10s timeout.

---

## 14. Problem-Solution Map and Hidden Capabilities

### Extract custom questions from booking
**Problem:** Need to know lead's company and pain points before call.
**Solution:** Calendly custom questions are in `invitee.questions_and_answers`:
```python
questions = invitee.get("questions_and_answers", [])
company = next(
    (q["answer"] for q in questions if "company" in q.get("question", "").lower()),
    "",
)
```

### Track booking source (UTM parameters)
**Problem:** Need to know which marketing channel drove the booking.
**Solution:** Calendly tracks UTM parameters:
```python
tracking = invitee.get("tracking", {})
utm_source = tracking.get("utm_source")  # e.g., "instagram"
utm_campaign = tracking.get("utm_campaign")  # e.g., "arena_launch"
```

### Cancellation recovery workflow
**Problem:** Lead cancels — don't want to lose them.
**Solution:** Auto-draft a re-engagement email:
```python
# On invitee.canceled:
# 1. Generate warm re-engagement email via model_router
# 2. Store draft in Neon events table (status: pending_approval)
# 3. Post draft to Discord for founder review
# 4. Founder approves → email sent
```

### Person recognition on booking
**Problem:** Is this person already in our system? Known contact?
**Solution:** `recognize_person()` checks name/email against existing records:
```python
from eos_ai.person_recognition import recognize_person
recognition = recognize_person(name=name, email=email)
if recognition.get("known"):
    # Flag as known person in Discord alert
```

---

## 15. Operational Behavior and Edge Cases

### Webhook delivered before page loads
Calendly sends the webhook immediately when booking is confirmed.
The invitee may still be on the Calendly confirmation page.
EOS processing starts before the invitee has even closed their browser.

### Multiple webhooks for same event
Calendly may deliver the same webhook multiple times (retries, network issues).
EOS does NOT currently deduplicate by event UUID.
**Risk:** Duplicate lead files, duplicate Notion pages, duplicate notifications.

### Cancellation after event time passes
If an invitee cancels after the scheduled event time, the webhook still fires.
`event.status` will be "active" at booking time but may change independently.

### Webhook delivered out of order
Created and canceled events for the same invitee may arrive out of order.
EOS processes each independently — could move pipeline card to "Booked"
after it was already moved to "Lost".

### Flask port binding in Docker
```yaml
# docker-compose.yml
os-webhook:
  ports:
    - "8080:8080"
  command: python3 calendly_webhook.py
```
Port 8080 must be accessible from Calendly's webhook delivery infrastructure.
No IP whitelist needed — signature verification provides security.

---

## 16. Ecosystem Position and Composition

### Where Calendly fits in EOS
```
Lead Journey:
  Content / DM / Outreach
    → Booking link (calendly.com/antony/discovery)
      → Calendly booking confirmation
        → Webhook → calendly_webhook.py
          → Lead creation → CRM update → Prep brief → Notifications
            → Sales call → Close → Revenue

Calendly is the bridge between outreach and pipeline.
```

### Interfaces
- **With Flask:** Webhook receiver (os-webhook container)
- **With Notion:** CRM pipeline updates (update_notion_lead_stage)
- **With Neon:** Meeting records, event logs, RLHF outcomes
- **With meetings.py:** Meeting record creation, prep brief generation
- **With person_recognition:** Known person check (Martell rule)
- **With EventBus:** Publishes "lead_booked" for downstream handlers
- **With Discord:** Alert webhook with prep brief
- **With Telegram:** Booking/cancellation notifications
- **With model_router:** AI-generated cancellation recovery email

---

## 17. Trajectory and Evolution

### Current state (2026-04)
- Webhook receiver: operational, processes bookings and cancellations
- CRM integration: markdown pipeline + Notion CRM updates
- Meeting records: Neon + Notion
- Prep brief: AI-generated on booking
- Cancellation recovery: auto-draft email for approval
- Person recognition: Martell rule check

### Potential improvements
- **Idempotency:** Deduplicate webhooks by event UUID
- **Async processing:** Queue webhook processing to avoid 10s timeout risk
- **REST API integration:** Read upcoming events for calendar-aware scheduling
- **Routing forms:** Process routing_form_submission.created events
- **No-show detection:** Compare booked vs attended (partially in noshow_detector.py)
- **Reschedule handling:** Process reschedule events (not currently tracked)

### Dependencies
- Calendly plan (Standard+ for webhooks)
- Port 8080 accessibility from Calendly infrastructure
- Model router availability for cancellation recovery drafts

---

## 18. Conceptual Model and Solution Recipes

### Mental model: Calendly as pipeline trigger
Calendly is not a calendar tool in EOS — it's a pipeline trigger.
When someone books a call, it's the starting gun for the entire sales pipeline:
lead file, CRM update, prep brief, person recognition, notifications.

### Recipe: Add a new Calendly event type
```
1. Create event type in Calendly dashboard
2. Name it to match venture detection keywords:
   - "Initiate Arena Discovery Call" → triggers Lyfe Institute
   - "Brand Strategy Session" → triggers Personal Brand
3. No code changes needed — _detect_venture_from_event() uses keywords
4. Custom questions flow through automatically via questions_and_answers
```

### Recipe: Debug missing webhook
```bash
# 1. Check os-webhook container is running
docker logs os-webhook --tail 20

# 2. Check health endpoint
curl http://localhost:8080/health

# 3. Check Calendly webhook logs
# Calendly Dashboard > Webhooks > Delivery History

# 4. Check if port 8080 is accessible
# From external: curl http://<vps-ip>:8080/health

# 5. Check firewall
iptables -L -n | grep 8080

# 6. Check Docker port mapping
docker port os-webhook
```

### Recipe: Test webhook locally
```bash
# Send test webhook (without signature verification)
curl -X POST http://localhost:8080/webhooks/calendly \
  -H "Content-Type: application/json" \
  -d '{
    "event": "invitee.created",
    "payload": {
      "event": {"uuid": "test", "name": "Test Call", "start_time": "2026-04-05T10:00:00Z"},
      "invitee": {"name": "Test User", "email": "test@example.com", "questions_and_answers": []}
    }
  }'

# NOTE: Only works if CALENDLY_SIGNING_KEY is not set (skip verification)
```

---

## 19. Industry Expert and Cutting-Edge Usage

### Booking as intelligence gathering
EOS extracts maximum value from the booking event:
```
Calendly booking
  → Person recognition (do we know this person?)
  → Company extraction (from custom questions)
  → Venture detection (from event type name)
  → UTM tracking (which channel drove this booking?)
  → Prep brief generation (AI research on person/company)
  → Meeting record (Neon + Notion for tracking)
  → RLHF logging (outcome tracking for model improvement)
```

A single webhook triggers 10+ downstream actions — each enriching the
founder's preparation for the sales call.

### Cancellation as recovery opportunity
Most systems just log cancellations. EOS treats them as recovery opportunities:
```
Cancellation received
  → AI drafts warm re-engagement email
    → Draft posted to Discord for review
      → Founder approves → email sent
        → Lead potentially re-books
```

The recovery email is drafted in Antony's voice (via model_router),
includes the Calendly link for rebooking, and is under 5 sentences.

### Event-driven architecture
Calendly webhooks feed into EOS's EventBus:
```python
EventBus().publish_async("lead_booked", {
    "username": username,
    "booking_time": event_time,
    "venture_id": "lyfe_institute",
})
```
This decouples the webhook handler from downstream processing.
New handlers can subscribe to "lead_booked" without modifying webhook code.

---

## 20. EOS Usage Patterns

### Webhook handler: invitee.created flow
```python
# Full processing chain on booking:
# 1. Verify signature
# 2. Extract: name, email, event_time, questions
# 3. Find/create lead file (03_CRM/Leads/)
# 4. Move pipeline card (03_CRM/Pipeline.md)
# 5. Log RLHF outcome (memory.db)
# 6. EventBus: "lead_booked"
# 7. Update Notion CRM (PATCH /v1/pages/{id})
# 8. Create meeting record (meetings.py → Neon + Notion)
# 9. Person recognition (Martell rule)
# 10. Build prep brief (AI-generated)
# 11. Discord alert (with prep brief)
# 12. Telegram notification
```

### Webhook handler: invitee.canceled flow
```python
# Processing chain on cancellation:
# 1. Verify signature
# 2. Extract: name, cancel_reason
# 3. Update lead file → "Lost"
# 4. Move pipeline card → "Lost"
# 5. Log RLHF outcome (score: 0.0)
# 6. AI draft recovery email (model_router FAST_RESPONSE)
# 7. Store draft in Neon events (pending_approval)
# 8. Discord alert with draft
# 9. Telegram notification
```

### Docker configuration
```yaml
os-webhook:
  container_name: os-webhook
  build: .
  command: python3 /app/services/calendly_webhook.py
  ports:
    - "8080:8080"
  volumes:
    - /opt/OS:/app
  environment:
    - PYTHONUNBUFFERED=1
  restart: always
  networks:
    - eos_network
```

---

## 21. Gotchas (Real EOS Production Issues)

### CALENDLY_SIGNING_KEY not set — all webhooks accepted (ACTIVE)
When `CALENDLY_SIGNING_KEY` is empty/missing, `verify_signature()` returns True for all requests.
**Risk:** Anyone can POST fake booking events to the webhook endpoint.
**Fix:** Set `CALENDLY_SIGNING_KEY` in services/.env from Calendly dashboard.

### No idempotency — duplicate webhook deliveries create duplicate leads (ACTIVE)
Calendly retries up to 7 times. EOS doesn't check event UUID before processing.
**Risk:** Same booking creates multiple lead files and Notion pages.
**Fix:** Store event UUIDs and check before processing.

### AI draft may exceed 10-second webhook timeout (POTENTIAL)
Cancellation recovery generates an email draft via model_router.
If all fast providers are unavailable and Ollama is slow, processing could exceed 10s.
**Symptom:** Calendly retries the webhook, potentially causing duplicate processing.
**Mitigation:** Use FAST_RESPONSE task type, which has lowest-latency routing.

### Pipeline card move fails silently (ACTIVE)
`move_pipeline_card()` manipulates raw markdown in `03_CRM/Pipeline.md`.
If username isn't found in the expected section, returns False without error.
**Impact:** Lead stays in old pipeline stage. Notion CRM update works independently.

### Notion CRM update uses raw API, not NotionPublisher (BY DESIGN)
`update_notion_lead_stage()` makes direct Notion API calls because it updates
existing pages (PATCH), while NotionPublisher only creates pages (POST).
**Impact:** Different error handling patterns for Notion reads vs writes.

### Port 8080 must be externally accessible (ACTIVE)
Calendly's webhook infrastructure needs to reach the Flask server.
If firewall blocks inbound 8080, no webhooks are delivered.
**Detection:** No webhook events in logs. Check Calendly dashboard delivery history.

### Venture detection relies on event type naming convention (ACTIVE)
`_detect_venture_from_event()` checks for keywords in the Calendly event name.
If event is renamed without matching keywords, defaults to "Empyrean Creative".
**Fix:** Keep venture-identifying keywords in Calendly event type names.
