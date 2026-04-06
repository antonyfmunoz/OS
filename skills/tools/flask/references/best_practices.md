# Flask — Creator-Level Best Practices
Source: https://flask.palletsprojects.com/en/stable/
API Version: WSGI 1.0
SDK Version: Flask 3.1.3 (Werkzeug 3.x, Jinja2 3.x, itsdangerous 2.x)
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Flask has no built-in authentication. Authentication is implemented at the application
layer. For webhook receivers (EOS's primary use case), authentication means verifying
the sender's signature.

### Webhook signature verification pattern (HMAC-SHA256)
Most webhook providers (Calendly, Stripe, GitHub, Shopify) sign payloads with
HMAC-SHA256 using a shared secret.

```python
import hmac
import hashlib

def verify_webhook_signature(
    payload: bytes,         # request.data — raw bytes
    signature: str,         # From provider-specific header
    secret: str,            # From env var, never hardcoded
    algorithm: str = "sha256"
) -> bool:
    mac = hmac.new(
        secret.encode("utf-8"),
        payload,
        getattr(hashlib, algorithm)
    )
    return hmac.compare_digest(mac.hexdigest(), signature)
```

### Provider signature header map
| Provider | Header | Algorithm | Format |
|---|---|---|---|
| Calendly | `Calendly-Webhook-Signature` | SHA256 | `t=timestamp,v1=signature` |
| Stripe | `Stripe-Signature` | SHA256 | `t=timestamp,v1=signature` |
| GitHub | `X-Hub-Signature-256` | SHA256 | `sha256=hex` |
| Shopify | `X-Shopify-Hmac-Sha256` | SHA256 | base64 |

### Secrets management
- Store signing keys in `.env` files, load with `python-dotenv`
- In EOS: `CALENDLY_SIGNING_KEY` in `services/.env`
- Never log signing keys, even in debug mode
- Rotate keys by updating both provider dashboard and `.env`, then restart container

### Token/key types relevant to EOS webhook receiver
- **Webhook signing key** — shared secret for HMAC verification (Calendly)
- **API keys for downstream calls** — Notion, Telegram, Discord tokens used
  after webhook processing (stored in `services/.env` and `eos_ai/.env`)

## Core Operations with Exact Signatures

### Flask application factory
```python
from flask import Flask
app = Flask(__name__)
# Flask(__name__) sets:
#   import_name: str          — module name for resource lookup
#   static_url_path: str      — default "/static"
#   static_folder: str        — default "static"
#   template_folder: str      — default "templates"
#   instance_path: str        — instance folder path
#   root_path: str            — application root
```

### Route decorator
```python
@app.route(
    rule: str,                   # URL pattern, e.g. "/webhooks/calendly"
    methods: list[str] = None,   # ["GET", "POST", "PUT", "DELETE"]
    endpoint: str = None,        # Name for url_for(), defaults to function name
    defaults: dict = None,       # Default values for rule variables
    strict_slashes: bool = None, # Whether trailing slash matters
)
def handler():
    ...
```

### Request object (flask.request)
```python
from flask import request

request.method          # str: "GET", "POST", etc.
request.path            # str: "/webhooks/calendly"
request.url             # str: full URL
request.headers         # Headers dict-like: request.headers.get("X-Header")
request.data            # bytes: raw request body
request.json            # dict | None: parsed JSON (requires application/json)
request.get_json(
    force: bool = False,     # Parse even without JSON content type
    silent: bool = False,    # Return None instead of raising on error
    cache: bool = True,      # Cache parsed result
) -> dict | None
request.args            # ImmutableMultiDict: query parameters
request.form            # ImmutableMultiDict: form data
request.files           # ImmutableMultiDict: uploaded files
request.content_type    # str: "application/json"
request.content_length  # int | None: Content-Length header value
request.is_json         # bool: True if content type is application/json
request.remote_addr     # str: client IP address
```

### Response helpers
```python
from flask import jsonify, make_response, abort

# jsonify — serialize dict to JSON response with correct Content-Type
jsonify({"status": "ok"})  # Response with application/json

# Tuple return — (body, status_code) or (body, status_code, headers)
return jsonify({"status": "ok"}), 200
return jsonify({"error": "bad"}), 400, {"X-Custom": "header"}

# abort — raise HTTP exception
abort(401)  # Unauthorized
abort(404)  # Not Found

# make_response — full control
resp = make_response(jsonify({"status": "ok"}), 200)
resp.headers["X-Custom"] = "value"
return resp
```

### Error handlers
```python
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(Exception)
def handle_exception(error):
    # Catch-all — log and return generic error
    print(f"[ERROR] {error}")
    return jsonify({"error": "Internal server error"}), 500
```

### Before/after request hooks
```python
@app.before_request
def before():
    # Runs before every request
    # Return a response to short-circuit (e.g., auth check)
    pass

@app.after_request
def after(response):
    # Runs after every request, must return response
    return response

@app.teardown_request
def teardown(exception):
    # Runs after response is sent, even on error
    # Use for cleanup (close DB connections, etc.)
    pass
```

## Pagination Patterns

N/A for webhook receivers. Flask does not implement pagination — it receives
single webhook payloads. If building a query API with Flask, implement cursor
or offset pagination manually in route handlers.

For webhook event replay/history, pagination lives in the webhook provider's API
(e.g., Calendly's list events endpoint), not in the Flask receiver.

## Rate Limits

Flask has no built-in rate limiting. For webhook receivers, rate limiting
means controlling inbound request volume.

### Flask-Limiter (recommended extension)
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # or redis:// for production
)

@app.route("/webhooks/calendly", methods=["POST"])
@limiter.limit("30 per minute")
def calendly_webhook():
    ...
```

### Werkzeug dev server capacity
- Single process, single thread by default
- `app.run(threaded=True)` enables threading (one thread per request)
- Can handle ~50-100 req/s for simple webhook processing
- For EOS: Calendly sends at most a few webhooks per day — no bottleneck

### Gunicorn production capacity
```bash
gunicorn -w 4 -b 0.0.0.0:8080 --timeout 30 services.calendly_webhook:app
```
- 4 workers = 4 concurrent requests
- Each worker handles ~100-500 req/s depending on handler complexity
- `--timeout 30` kills workers that hang (important for webhook handlers
  that make downstream API calls)

### Webhook provider retry behavior
Webhook senders retry on non-2xx responses. Response time matters:
- Calendly: retries up to 7 times with exponential backoff over 24h
- Stripe: retries up to 3 days with exponential backoff
- GitHub: retries within 30 minutes
- Return 200 quickly, process asynchronously if handler is slow

## Error Codes and Recovery

### HTTP status codes to return from webhook handlers
| Code | When | Provider behavior |
|---|---|---|
| 200 | Success | Marks delivery as successful |
| 400 | Malformed payload | Provider logs error, may retry |
| 401 | Invalid signature | Provider logs auth failure |
| 404 | Unknown endpoint | Provider logs, usually no retry |
| 500 | Internal error | Provider will retry with backoff |
| 502/503 | Server down | Provider will retry with backoff |

### Flask exception types
```python
from werkzeug.exceptions import (
    BadRequest,          # 400
    Unauthorized,        # 401
    Forbidden,           # 403
    NotFound,            # 404
    MethodNotAllowed,    # 405
    RequestEntityTooLarge,  # 413
    UnsupportedMediaType,   # 415
    InternalServerError,    # 500
)
```

### Recovery strategies
- **Signature mismatch (401)** — non-retryable. Check signing key in env.
- **JSON parse error (400)** — non-retryable. Log raw payload for debugging.
- **Downstream API failure (500)** — return 200 to prevent retry storms.
  Log the error internally and handle via EOS event system.
- **Import error in handler** — caught by try/except, returns 200.
  Check `docker logs os-webhook` for the actual error.

### Critical: return 200 even on partial failure
If the webhook payload was valid but a downstream action failed (Notion API
down, Discord webhook 429), still return 200. Otherwise the webhook provider
retries, creating duplicate processing. Handle downstream failures
asynchronously.

## SDK Idioms

### Flask 3.x patterns (current)
```python
# Flask 3.x — app factory is optional for simple apps
from flask import Flask, request, jsonify

app = Flask(__name__)

# Type hints on route handlers (Flask 3.x supports them)
@app.route("/webhook", methods=["POST"])
def webhook() -> tuple[dict, int]:
    data = request.get_json(silent=True)
    if data is None:
        return {"error": "Invalid JSON"}, 400
    return {"status": "ok"}, 200
```

### Correct initialization pattern for EOS
```python
import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load env BEFORE Flask app creation
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# sys.path for EOS imports
import sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

app = Flask(__name__)
```

### Async support (Flask 2.0+)
Flask 2.0+ supports async route handlers, but they run on a thread pool,
not a true event loop. For webhook receivers making async downstream calls,
prefer synchronous handlers with `requests` library (as EOS does) unless
switching to Quart (Flask's async twin).

```python
# Works in Flask 2.0+ but runs on thread pool, not event loop
@app.route("/webhook", methods=["POST"])
async def webhook():
    data = request.get_json()
    # async/await works here but isn't true async
    return jsonify({"status": "ok"}), 200
```

### Configuration
```python
# From environment
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max payload

# Or from object
class Config:
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    JSON_SORT_KEYS = False

app.config.from_object(Config)
```

## Anti-Patterns

### 1. Using request.json for signature verification
```python
# WRONG — re-serialization changes payload bytes
signature_check = hmac.new(key, json.dumps(request.json).encode(), hashlib.sha256)

# CORRECT — use raw bytes
signature_check = hmac.new(key, request.data, hashlib.sha256)
```

### 2. Using == for signature comparison
```python
# WRONG — timing attack vulnerable
if computed_signature == provided_signature:

# CORRECT — constant-time comparison
if hmac.compare_digest(computed_signature, provided_signature):
```

### 3. Running Flask dev server in production without understanding limits
```python
# Dev server — fine for low-volume webhooks (EOS current state)
app.run(host="0.0.0.0", port=8080)

# Production — if volume increases
# gunicorn -w 4 -b 0.0.0.0:8080 services.calendly_webhook:app
```
Flask's dev server warns "Do not use in production" but for a webhook
receiver handling <100 events/day, it works. The warning is about scale
and security hardening, not correctness.

### 4. Not returning 200 on partial downstream failure
```python
# WRONG — causes retry storms
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    process_event(data)         # If this raises, Flask returns 500
    return jsonify({"ok": True}), 200

# CORRECT — catch and log
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        process_event(data)
    except Exception as e:
        print(f"[WEBHOOK] Processing failed: {e}")
        # Still return 200 — webhook was received successfully
    return jsonify({"ok": True}), 200
```

### 5. Importing heavy modules at module level in webhook handler
```python
# WRONG — slows app startup, may fail on import
from eos_ai.meetings import create_meeting_record  # at module level

# CORRECT — lazy import inside handler (EOS pattern)
@app.route("/webhooks/calendly", methods=["POST"])
def calendly_webhook():
    try:
        from eos_ai.meetings import create_meeting_record
        create_meeting_record(...)
    except Exception as e:
        print(f"[ERROR] {e}")
```
EOS uses lazy imports inside route handlers for non-critical modules.
This prevents import failures from crashing the entire webhook receiver.

### 6. Not setting MAX_CONTENT_LENGTH
```python
# WRONG — accepts arbitrarily large payloads (DoS vector)
app = Flask(__name__)

# CORRECT — cap payload size
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1MB for webhooks
```

### 7. Exposing internal errors to webhook sender
```python
# WRONG
except Exception as e:
    return jsonify({"error": str(e)}), 500  # Leaks internals

# CORRECT
except Exception as e:
    print(f"[ERROR] {e}")  # Log internally
    return jsonify({"error": "Internal server error"}), 500
```

## Data Model

Flask's data model is request-response. For webhook receivers, the relevant
data structures are:

### Request lifecycle
```
Client sends HTTP request
  -> WSGI server receives it
    -> Flask creates Request context (flask.request)
      -> before_request hooks run
        -> Route handler executes
          -> after_request hooks run
            -> Response sent to client
              -> teardown_request hooks run
```

### Request context stack
Flask uses context locals (thread-local proxies). Each request gets its own
`request` and `g` objects. Safe for multi-threaded servers (gunicorn, threaded
dev server). Not safe for gevent/eventlet without monkey-patching.

### Key objects
- `flask.request` — current request proxy (read-only)
- `flask.g` — request-scoped storage (store DB connections, auth state)
- `flask.session` — cookie-based session (not used for webhooks)
- `flask.current_app` — application proxy (access config)

### Webhook payload structure (Calendly)
```json
{
    "event": "invitee.created",
    "payload": {
        "invitee": {
            "name": "John Doe",
            "email": "john@example.com",
            "questions_and_answers": [
                {"question": "Company?", "answer": "Acme Inc"}
            ]
        },
        "event": {
            "name": "Discovery Call",
            "start_time": "2026-04-10T14:00:00Z",
            "uuid": "abc-123",
            "location": {"join_url": "https://meet.google.com/xyz"}
        },
        "cancellation": {
            "reason": "Schedule conflict"
        }
    }
}
```

## Webhooks and Events

This IS the webhook receiver. EOS uses Flask to receive webhooks, not send them.

### Webhook verification (Calendly-specific)
Calendly's v2 webhook signature format:
```
Calendly-Webhook-Signature: t=1234567890,v1=abc123hex...
```
- `t` is the Unix timestamp of when the webhook was sent
- `v1` is the HMAC-SHA256 hex digest
- The signed payload is: `{timestamp}.{request_body}`

Full Calendly verification:
```python
def verify_calendly_signature(payload: bytes, header: str, secret: str) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(","))
    timestamp = parts.get("t", "")
    signature = parts.get("v1", "")
    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Note: The current EOS implementation uses a simplified verification that
compares against the raw payload without the timestamp prefix. This works
if the Calendly signing key is configured to send simple signatures.

### Event types EOS handles
| Event | Action |
|---|---|
| `invitee.created` | Full booking flow (11 downstream actions) |
| `invitee.canceled` | Cancellation + recovery flow (7 downstream actions) |

### Delivery guarantees
- Calendly: at-least-once delivery, retries on non-2xx for up to 24 hours
- This means handlers MUST be idempotent or tolerate duplicates
- EOS handles this by checking for existing lead files before creating new ones

### Registering webhooks with Calendly
Webhook subscriptions are managed via Calendly's API or dashboard, not from Flask.
The Flask app only receives — it never manages subscriptions programmatically.

## Limits

### Flask/Werkzeug limits
- **Max content length**: configurable via `MAX_CONTENT_LENGTH` (default: unlimited)
- **Max form memory size**: 500KB (form data only, not JSON)
- **URL length**: limited by web server (Werkzeug: 16KB default)
- **Header size**: limited by web server (Werkzeug: 16KB default per header)
- **Request timeout**: set by WSGI server (gunicorn: 30s default)

### Dev server limits
- Single process by default
- `threaded=True` adds threading but still single process
- No worker management, no graceful restart
- No TLS termination (use reverse proxy)

### Docker resource limits (EOS)
- Container `os-webhook` has no explicit memory/CPU limits set
- Flask process typically uses 30-80MB RAM
- For EOS webhook volume (<100 events/day), no resource constraints needed

### Webhook payload limits
- Calendly webhook payloads are typically 1-5KB
- Set `MAX_CONTENT_LENGTH = 1MB` as a safety cap
- Reject payloads over this with 413 Request Entity Too Large

## Cost Model

Flask is free and open source (BSD-3-Clause license). Costs come from infrastructure:

### Server costs
- EOS runs Flask in a Docker container on the same VPS as all other services
- Marginal cost: near zero — the VPS is already running
- Flask adds ~30-80MB RAM to the container footprint

### Downstream API costs per webhook event
Each `invitee.created` webhook triggers:
- 1 Notion API call (pipeline update) — free tier
- 1 Telegram API call (notification) — free
- 1 Discord webhook call — free
- 1 Neon Postgres write (memory) — free tier
- 1 LLM call on cancellation (re-engagement draft) — model-dependent cost

### Scaling costs
- Dev server: $0 additional (already running)
- Gunicorn: $0 additional (same server, different process manager)
- Separate webhook server: $5-20/mo for a dedicated VPS if needed
- Rate limiting (Redis): $0 for in-memory, $5-15/mo for Redis instance

## Version Pinning

### Current versions in EOS
- **Flask**: 3.1.3 (from `services/requirements.txt`, unpinned as `flask`)
- **Werkzeug**: 3.x (Flask dependency, auto-resolved)
- **itsdangerous**: 2.x (Flask dependency, used for signing)
- **Jinja2**: 3.x (Flask dependency, not used in webhook context)

### Pin recommendation
```
# services/requirements.txt — current (unpinned)
flask

# Recommended — pin major.minor
flask>=3.1,<4.0
```

### Flask versioning history (relevant)
- Flask 2.0 (2021): async support, nested blueprints, shorter decorators
- Flask 2.2 (2022): removed deprecated code, improved typing
- Flask 2.3 (2023): import changes, deprecation cleanup
- Flask 3.0 (2023): dropped Python 3.7, required Werkzeug 3.0
- Flask 3.1 (2024-2025): typing improvements, minor fixes

### Breaking changes to watch
- Flask 3.0 dropped `flask.json.jsonify` re-export (use `flask.jsonify`)
- Werkzeug 3.0 removed deprecated middleware, changed internal APIs
- Future: potential move toward async-first (Quart merge speculation)

### Deprecation policy
Flask follows semantic versioning. Major version bumps indicate breaking changes.
Pallets team typically provides 6-12 months of overlap before removing deprecated
features. No formal LTS policy.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Flask was created by Armin Ronacher (Pallets project) as a deliberate reaction to
Django's "batteries included" philosophy. The core design decisions:

1. **Micro means micro** — Flask provides routing, request/response handling, and
   templating. Everything else is an extension. This is why Flask has no ORM, no
   auth, no form validation built in.

2. **Explicit over implicit** — no magic. You create the app, you register the routes,
   you run the server. Compare Django where the project structure implies behavior.

3. **WSGI-native** — Flask wraps WSGI directly (via Werkzeug). This means it works
   with any WSGI server (gunicorn, uWSGI, mod_wsgi) without adapters.

4. **Context locals for ergonomics** — `flask.request` as a module-level import that
   magically points to the current request. This was controversial (global state!)
   but made the API dramatically simpler than passing request objects through every
   function.

### What Flask is NOT
- Not an API framework (no built-in serialization, validation, OpenAPI)
- Not async-native (async support is bolted on via thread pools)
- Not a full-stack framework (no ORM, no admin, no migrations)

### Why Flask for EOS webhooks
Flask is the correct choice for EOS's webhook receiver because:
- Minimal footprint (30MB RAM, 10 lines of boilerplate)
- Zero learning curve for Python developers
- No overhead features that add attack surface
- Easy to containerize (single file, single process)
- Production-proven at massive scale (Pinterest, Netflix, LinkedIn used Flask)

## Problem-Solution Map and Hidden Capabilities

### Problem: Webhook handler is slow, provider times out
**Solution**: Return 200 immediately, process asynchronously.
```python
import threading

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    # Process in background thread
    threading.Thread(target=process_event, args=(data,)).start()
    return jsonify({"status": "accepted"}), 202
```

### Problem: Need to test webhooks locally
**Solution**: Use Flask's test client.
```python
with app.test_client() as client:
    response = client.post(
        "/webhooks/calendly",
        json={"event": "invitee.created", "payload": {...}},
        headers={"Calendly-Webhook-Signature": "test-sig"},
    )
    assert response.status_code == 200
```

### Problem: Multiple webhook providers, each with different signature schemes
**Solution**: Use before_request + route-specific verification.
```python
VERIFIERS = {
    "/webhooks/calendly": verify_calendly,
    "/webhooks/stripe": verify_stripe,
    "/webhooks/github": verify_github,
}

@app.before_request
def verify_webhook():
    verifier = VERIFIERS.get(request.path)
    if verifier and not verifier(request):
        return jsonify({"error": "Invalid signature"}), 401
```

### Hidden capability: signals (blinker)
Flask includes blinker for signals — event hooks beyond before/after_request:
```python
from flask import request_started, request_finished, got_request_exception

@got_request_exception.connect_via(app)
def log_exception(sender, exception, **kwargs):
    print(f"[EXCEPTION] {exception}")
```

### Hidden capability: test request context
```python
# Execute code that needs flask.request outside a real request
with app.test_request_context("/webhooks/test", method="POST"):
    # flask.request is now available
    print(request.path)  # "/webhooks/test"
```

## Operational Behavior and Edge Cases

### Werkzeug dev server auto-reloader
`app.run(debug=True)` enables the reloader — it restarts the process on file change.
In Docker with bind mounts, this can cause unexpected restarts when EOS files change.
EOS runs with `debug=False` (default) which avoids this.

### request.data reads the stream once
`request.data` reads the WSGI input stream and caches it. But if you read
`request.stream` first, `request.data` may be empty. Always use `request.data`
or `request.get_json()`, never mix with `request.stream`.

### JSON parsing with non-UTF-8 encodings
`request.get_json()` assumes UTF-8. If a webhook sender uses a different encoding,
parsing silently produces garbled strings. Calendly sends UTF-8, so this is not
an issue for EOS, but be aware when adding new providers.

### Thread safety of module-level state
EOS stores `_mem = AgentMemory()` at module level. With threaded=True or gunicorn,
multiple requests could access `_mem` concurrently. `AgentMemory` must be thread-safe
or each handler must create its own instance.

### Large payloads and memory
Flask reads the entire request body into memory (`request.data`). For webhook
payloads (1-5KB), this is irrelevant. If ever accepting file uploads via Flask,
use `request.stream` for streaming reads.

### Graceful shutdown
Flask's dev server handles SIGINT but not SIGTERM gracefully. In Docker,
`docker stop` sends SIGTERM then SIGKILL after 10s. The dev server may not
finish processing in-flight requests. Gunicorn handles SIGTERM gracefully
by finishing current requests.

## Ecosystem Position and Composition

### Flask in the EOS architecture
```
External world (Calendly, future: Stripe, GitHub)
  |
  v
Flask (os-webhook) — thin HTTP receiver
  |
  v
EOS Intelligence Layer (eos_ai/)
  |-- memory.py — log outcomes
  |-- event_bus.py — publish events
  |-- meetings.py — create records
  |-- person_recognition.py — identify known contacts
  |-- model_router.py — AI-generated responses
  |
  v
Notification Layer
  |-- Telegram API
  |-- Discord webhooks
  +-- Notion API
```

### Natural complements
- **gunicorn** — production WSGI server in front of Flask
- **nginx** — reverse proxy, TLS termination, rate limiting
- **Celery/Redis** — async task queue for slow webhook processing
- **sentry-sdk** — error monitoring (`pip install sentry-sdk[flask]`)

### Anti-complement: FastAPI
FastAPI is async-native with built-in validation (Pydantic) and OpenAPI docs.
For a simple webhook receiver, Flask is lighter and simpler. Switch to FastAPI
only if building a full REST API alongside the webhook receiver.

### Data flow integrity
Flask receives raw bytes -> EOS modules process -> Neon stores -> notifications send.
Flask never stores state. If the container crashes, no data is lost — the webhook
provider retries and EOS processes again. The only risk is duplicate processing,
which EOS handles via lead file existence checks.

## Trajectory and Evolution

### Flask's current direction
- Flask 3.x is stable, maintenance-mode for new features
- Pallets team focuses on Werkzeug and Jinja2 improvements
- Async story improving but Flask will never be async-first
- Quart (async Flask-compatible framework) is now maintained by Pallets

### What this means for EOS
- Flask is stable — no forced migrations coming
- If EOS needs async webhook processing, consider Quart (drop-in compatible)
- If EOS needs a full API layer, consider FastAPI (different paradigm)
- For current webhook-only use: Flask is the right tool indefinitely

### Deprecation signals
- No active deprecations in Flask 3.1.x
- `flask.json.jsonify` was removed in 3.0 (use `flask.jsonify`)
- `before_first_request` removed in 2.3 (use app factory pattern instead)
- No indication of Flask 4.0 on the horizon

## Conceptual Model and Solution Recipes

### Mental model: Flask as a switchboard
Think of Flask as a telephone switchboard operator:
1. Call comes in (HTTP request)
2. Operator checks credentials (signature verification)
3. Operator routes to the right desk (route handler)
4. Desk does the work (business logic in EOS modules)
5. Operator confirms receipt (200 response)

Flask is the operator, not the desk. Keep it thin.

### Recipe 1: Add a new webhook provider to EOS
```python
# 1. Add new route
@app.route("/webhooks/stripe", methods=["POST"])
def stripe_webhook():
    # 2. Verify signature (provider-specific)
    sig = request.headers.get("Stripe-Signature", "")
    if not verify_stripe_signature(request.data, sig):
        return jsonify({"error": "Invalid signature"}), 401

    # 3. Parse event
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid JSON"}), 400

    event_type = data.get("type")

    # 4. Route to handler
    if event_type == "payment_intent.succeeded":
        try:
            handle_payment(data)
        except Exception as e:
            print(f"[Stripe] Handler error: {e}")

    # 5. Always return 200
    return jsonify({"status": "ok"}), 200
```

### Recipe 2: Add structured logging to webhook receiver
```python
import json
import datetime

@app.before_request
def log_webhook():
    if request.method == "POST":
        print(json.dumps({
            "time": datetime.datetime.utcnow().isoformat(),
            "path": request.path,
            "content_length": request.content_length,
            "remote_addr": request.remote_addr,
            "signature_present": bool(
                request.headers.get("Calendly-Webhook-Signature")
                or request.headers.get("Stripe-Signature")
            ),
        }))
```

### Recipe 3: Health check with dependency verification
```python
@app.route("/health", methods=["GET"])
def health():
    checks = {}
    # Check Neon connection
    try:
        from eos_ai.db import get_conn
        from eos_ai.context import load_context_from_env
        ctx = load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute("SELECT 1")
        checks["neon"] = "ok"
    except Exception:
        checks["neon"] = "down"

    # Check signing key configured
    checks["signing_key"] = "configured" if os.getenv("CALENDLY_SIGNING_KEY") else "missing"

    status = "ok" if all(v in ("ok", "configured") for v in checks.values()) else "degraded"
    return jsonify({"status": status, "checks": checks}), 200 if status == "ok" else 503
```

### Recipe 4: Idempotency guard for webhook deduplication
```python
import hashlib

_processed_events = set()  # In production, use Redis

@app.route("/webhooks/calendly", methods=["POST"])
def calendly_webhook():
    # Create idempotency key from payload hash
    event_id = hashlib.sha256(request.data).hexdigest()[:16]
    if event_id in _processed_events:
        return jsonify({"status": "already_processed"}), 200
    _processed_events.add(event_id)
    # ... process event ...
```

## Industry Expert and Cutting-Edge Usage

### Pattern: Webhook fan-out with EventBus
EOS already implements this — the Calendly webhook handler publishes to EventBus,
decoupling receipt from processing. This is the industry best practice for webhook
architectures at scale:
```
Webhook -> Flask -> EventBus.publish_async("lead_booked", data)
                       |
                       +-> Handler 1: Update CRM
                       +-> Handler 2: Send notification
                       +-> Handler 3: Create meeting record
```

### Pattern: Webhook replay for development
Store raw webhook payloads in a file or DB, replay them during development:
```python
# Save incoming webhooks (development only)
@app.before_request
def save_webhook():
    if app.debug and request.method == "POST":
        with open(f"/tmp/webhook_{int(time.time())}.json", "wb") as f:
            f.write(request.data)
```

### Pattern: Multi-tenant webhook routing
For SaaS products receiving webhooks from multiple customer accounts:
```python
@app.route("/webhooks/<provider>/<tenant_id>", methods=["POST"])
def multi_tenant_webhook(provider, tenant_id):
    secret = get_tenant_secret(tenant_id, provider)
    if not verify_signature(request.data, request.headers, secret):
        return jsonify({"error": "Unauthorized"}), 401
    # Route to tenant-specific handler
```

### Pattern: Observability without external services
```python
from collections import defaultdict
import time

_metrics = defaultdict(lambda: {"count": 0, "errors": 0, "last_seen": None})

@app.after_request
def track_metrics(response):
    key = f"{request.path}:{response.status_code}"
    _metrics[key]["count"] += 1
    _metrics[key]["last_seen"] = time.time()
    if response.status_code >= 400:
        _metrics[key]["errors"] += 1
    return response

@app.route("/metrics", methods=["GET"])
def metrics():
    return jsonify(dict(_metrics)), 200
```

### AI-powered webhook processing (EOS frontier)
EOS's cancellation recovery flow is a frontier pattern: webhook triggers AI-generated
content (re-engagement email) which is queued for human approval. This pattern —
webhook -> AI processing -> human-in-the-loop approval -> action — is becoming
standard in AI-native business systems.

---

## EOS Usage Patterns

### Current deployment
- Single Flask file: `services/calendly_webhook.py`
- Docker container: `os-webhook` on port 8080
- Server: Werkzeug dev server (adequate for current volume)
- Events handled: `invitee.created`, `invitee.canceled`

### Adding new webhook providers
When adding a new webhook source:
1. Add route to `calendly_webhook.py` or create a new file
2. Implement provider-specific signature verification
3. Add env vars to `services/.env`
4. Expose additional ports in `docker-compose.yml` if needed
5. Test with provider's webhook testing tools

### Restart after changes
```bash
docker restart os-webhook
docker logs os-webhook --tail 20
```

## Gotchas

### request.data consumed by request.json
If you access `request.json` first, then `request.data`, both work because Flask
caches both. But if you access `request.stream` directly, subsequent reads return
empty. Stick to `request.data` and `request.json` — never use `request.stream`
for webhook receivers.

### Flask dev server warning in Docker logs
Every container start logs: "WARNING: This is a development server. Do not use it
in a production deployment." This is expected for EOS's current volume. The warning
is about scalability, not correctness.

### Calendly webhook signature format changed between API versions
Calendly v1 webhooks used a simple HMAC. v2 webhooks use `t=timestamp,v1=signature`
format. Ensure your verification matches the API version your subscription uses.
