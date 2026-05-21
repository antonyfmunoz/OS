---
name: flask
description: "Use when building or modifying webhook receivers, adding new webhook endpoints, debugging Flask request handling, or deploying Flask services in Docker."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://flask.palletsprojects.com/en/stable/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "WSGI"
sdk_version: "3.1.3"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: Flask (Webhook Receiver)

## What This Tool Does

Flask is a lightweight WSGI micro-framework for Python. EOS uses it exclusively as a
webhook receiver — a thin HTTP layer that accepts inbound POST requests from external
services (Calendly), validates signatures, processes event payloads, and triggers
downstream EOS actions (pipeline updates, Telegram alerts, Discord notifications,
Notion syncs, meeting records, lead creation).

Core capabilities used by EOS:
- **Webhook endpoints** — receive POST payloads from Calendly (invitee.created, invitee.canceled)
- **Signature verification** — HMAC-SHA256 validation of webhook signing keys
- **JSON request parsing** — `request.json` and `request.data` for payload access
- **Health checks** — GET `/health` for Docker container monitoring
- **Event routing** — parse event type from payload, dispatch to correct handler logic

Flask is NOT used for:
- Web UI serving (SaaS repos use React/Vite)
- API backends (no REST API layer in EOS)
- Template rendering (no Jinja2 usage)
- Session management or auth middleware

## EOS Integration

### Primary service
`services/calendly_webhook.py` — Calendly webhook receiver. Runs as `os-webhook` Docker container
on port 8080. Single Flask app with two routes.

### Routes
| Route | Method | Purpose |
|---|---|---|
| `/webhooks/calendly` | POST | Receives Calendly webhook events |
| `/health` | GET | Container health check |

### Downstream actions triggered by webhooks
**On `invitee.created` (call booked):**
1. Find/create lead file in `03_CRM/Leads/`
2. Update lead file stage to "Booked"
3. Move pipeline card (Qualifying/Replied -> Booked)
4. Log outcome to memory via `AgentMemory`
5. Publish `lead_booked` event on EventBus
6. Update Notion pipeline stage
7. Send Telegram notification
8. Person recognition check (pre-meeting intel check)
9. Create meeting record (Neon + Notion)
10. Auto-create lead file if none exists
11. Send Discord alert with prep brief

**On `invitee.canceled`:**
1. Update lead file stage to "Lost"
2. Move pipeline card (Booked -> Lost)
3. Log cancellation outcome to memory
4. Send Telegram notification
5. Generate AI re-engagement email draft
6. Store draft in Neon events table (pending approval)
7. Post draft to Discord for founder review

### Docker deployment
```yaml
os-webhook:
  container_name: os-webhook
  restart: always
  command: python3 services/calendly_webhook.py
  ports:
    - "8080:8080"
  env_file:
    - services/.env
```
Runs on Flask's built-in Werkzeug development server (`app.run()`).
For production scale: switch to gunicorn (`gunicorn -w 4 -b 0.0.0.0:8080 services.calendly_webhook:app`).

### Env vars
```
CALENDLY_SIGNING_KEY=    # HMAC signing key from Calendly webhook subscription
TELEGRAM_BOT_TOKEN=      # For notification dispatch
TELEGRAM_CHAT_ID=        # Founder's Telegram chat
DISCORD_BRIEF_WEBHOOK=   # Discord webhook for booking alerts
NOTION_API_KEY=          # Notion API for pipeline updates
NOTION_LYFE_PIPELINE_ID= # Notion pipeline database ID
```

## Authentication

Flask itself has no authentication layer. Webhook authentication is implemented
at the application level via HMAC signature verification.

### Calendly webhook signature verification
Calendly sends a `Calendly-Webhook-Signature` header with every webhook POST.
EOS verifies it using HMAC-SHA256:

```python
import hmac
import hashlib

CALENDLY_SIGNING_KEY = os.getenv("CALENDLY_SIGNING_KEY")

def verify_signature(payload: bytes, signature: str) -> bool:
    if not CALENDLY_SIGNING_KEY:
        return True  # Skip verification if key not configured
    expected = hmac.new(
        CALENDLY_SIGNING_KEY.encode(),
        payload,       # request.data — raw bytes, NOT request.json
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Critical: Use `request.data` (raw bytes) for signature computation, never
`request.json` (parsed dict). JSON re-serialization changes whitespace/ordering
and breaks HMAC validation.

### Adding new webhook providers
For any new webhook source (Stripe, GitHub, etc.):
1. Read provider docs for their signing mechanism
2. Extract signature from the correct header
3. Use `request.data` for HMAC computation
4. Use `hmac.compare_digest()` — never `==` (timing attack vulnerable)
5. Return 401 on signature mismatch

## Quick Reference

### Minimal webhook receiver
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhooks/example", methods=["POST"])
def webhook():
    data = request.json  # Parsed JSON body
    event_type = data.get("event")
    # Process event...
    return jsonify({"status": "ok"}), 200

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

### Access raw request body (for signature validation)
```python
raw_body = request.data          # bytes
signature = request.headers.get("X-Signature-Header", "")
```

### Return proper error responses
```python
# Bad signature
return jsonify({"error": "Invalid signature"}), 401

# Missing required field
return jsonify({"error": "Missing event type"}), 400

# Internal error (never expose details)
return jsonify({"error": "Internal server error"}), 500
```

### Guard against missing JSON body
```python
data = request.get_json(silent=True)
if data is None:
    return jsonify({"error": "Invalid JSON"}), 400
```

### Force JSON content type
```python
@app.route("/webhooks/strict", methods=["POST"])
def strict_webhook():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    data = request.get_json()
    # ...
```

### Log incoming webhooks for debugging
```python
@app.before_request
def log_request():
    print(f"[WEBHOOK] {request.method} {request.path} "
          f"Content-Length: {request.content_length}")
```

See references/best_practices.md for production deployment, rate limiting, error handling, and security patterns.

## Conceptual Model

```
External Service (Calendly)
  |
  | HTTPS POST with signed payload
  v
Flask (os-webhook container, port 8080)
  |
  +-- Signature verification (HMAC-SHA256)
  |     |-- Pass -> continue
  |     +-- Fail -> 401 Unauthorized
  |
  +-- Event type routing
  |     |-- invitee.created -> booking flow
  |     +-- invitee.canceled -> cancellation flow
  |
  +-- Downstream actions
        |-- File system (lead files, pipeline)
        |-- Neon Postgres (memory, events, meetings)
        |-- Notion API (pipeline stage update)
        |-- Telegram API (founder notification)
        |-- Discord webhook (team notification)
        +-- EventBus (async event propagation)
```

Flask's role is minimal by design: receive, validate, dispatch. All business
logic lives in EOS modules (`eos_ai.memory`, `eos_ai.meetings`,
`eos_ai.person_recognition`, `eos_ai.event_bus`). Flask is the door, not the house.

## Gotchas

### request.json vs request.data for signature verification
`request.json` parses the body into a Python dict. If you re-serialize it,
key ordering and whitespace differ from the original payload. HMAC verification
MUST use `request.data` (raw bytes). The EOS `verify_signature()` function
correctly uses `request.data`.

### Flask dev server is single-threaded by default
`app.run()` uses Werkzeug's development server — single process, single thread.
Concurrent webhook deliveries will queue. For EOS webhook volume this is fine.
If volume increases, switch to gunicorn with multiple workers.

### request.json returns None on non-JSON content type
If the sender omits `Content-Type: application/json`, `request.json` returns `None`
silently. Use `request.get_json(force=True)` to parse regardless of content type,
or `request.get_json(silent=True)` to get `None` without a 400 error.

### hmac.new vs hmac.compare_digest
The EOS codebase uses `hmac.new()` — this is correct. But signature comparison
MUST use `hmac.compare_digest()` (constant-time), never `==` (variable-time,
vulnerable to timing attacks). EOS does this correctly.

### Docker container restarts for Python changes
Flask files are bind-mounted (`/opt/OS:/app`), but the Flask process caches
Python modules in memory. After editing `calendly_webhook.py`:
```bash
docker restart os-webhook
```

### Port 8080 must be exposed in Docker AND reachable externally
The Calendly webhook subscription points to your server's public IP/domain
on port 8080. If a firewall, reverse proxy, or Tailscale ACL blocks 8080,
webhooks silently fail with no error on the Calendly side.

### Calendly signature header name
The header is `Calendly-Webhook-Signature`, not `X-Calendly-Signature` or
`X-Webhook-Signature`. Each provider uses a different header name. Always
check provider docs for the exact header.

### Silent failure on import errors inside route handlers
The EOS webhook handler imports EOS modules inside handler functions
(e.g., `from eos_ai.event_bus import EventBus`). If an import fails,
the try/except catches it and continues. The webhook returns 200 but
the downstream action never fires. Check container logs after deployment:
```bash
docker logs os-webhook --tail 50
```
