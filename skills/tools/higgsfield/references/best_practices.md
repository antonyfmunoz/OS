# Higgsfield AI — Creator-Level Best Practices
Source: higgsfield.ai, higgsfield.ai/camera-controls, higgsfield.ai/soul,
        higgsfield.ai/pricing, higgsfield.ai/blog, segmind.com Higgsfield guide,
        chasejarvis.com Higgsfield Soul writeup, hackceleration.com review
API Version: Higgsfield web product (no public REST API as of 2026-04)
SDK Version: N/A — GUI / human-operator tool
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

**Higgsfield Cloud API — real, public, REST + SDK + webhooks.**

- **Public docs:** `https://docs.higgsfield.ai/` (Mintlify). Index at
  `docs.higgsfield.ai/llms.txt`. Refresh this skill by fetching that
  index when the `last_researched` drifts.
- **Base URL:** `https://platform.higgsfield.ai`
- **Dashboard / key management:** `https://cloud.higgsfield.ai/`
  (Clerk-authenticated sign-in → `/dashboard`). API keys are generated
  here as **{key_id, key_secret}** pairs.

**Auth header (exact format):**

```
Authorization: Key {HIGGSFIELD_API_KEY}:{HIGGSFIELD_API_KEY_SECRET}
Content-Type: application/json
Accept: application/json
```

Critical: the scheme name is literally `Key` (not `Bearer`), and the
two halves of the key pair are colon-separated inside the header value.
Missing either half = 401.

**EOS secret storage:**

```bash
# /opt/OS/eos_ai/.env (never committed)
HIGGSFIELD_API_KEY=...
HIGGSFIELD_API_KEY_SECRET=...
```

The Python SDK `higgsfield-client` auto-reads both from the environment.

**Two-surface operating model:**

- **API surface** (`platform.higgsfield.ai`) — agent-callable.
  Production batch, scheduled drops, webhook-driven pipelines.
- **GUI surface** (`higgsfield.ai`) — Antony's exploration layer.
  Tune a prompt + preset recipe by hand, then promote the winning
  arguments dict into an API call for repeat runs.

**Failed + NSFW refunds:** Failed requests and NSFW-flagged generations
are **not charged**; credits refund automatically. EOS handlers should
treat Failed/NSFW as terminal-without-billing, not terminal-with-loss.

**Enterprise billing:** Invoice billing available via
`support@higgsfield.ai` for enterprise customers.

## Core Operations with Exact Signatures

All operations are REST against `https://platform.higgsfield.ai` with
the `Authorization: Key {id}:{secret}` header. Every generation is a
submit → poll/webhook → fetch async job.

### Three platform-level endpoints

```
POST  /{model_id}                         → submit generation (returns request_id + status queued)
GET   /requests/{request_id}/status       → poll status (queued | in_progress | completed | failed | nsfw | cancelled)
POST  /requests/{request_id}/cancel       → cancel queued request
```

### Known model IDs (docs snapshot 2026-04-06)

```
# Images
higgsfield-ai/soul/standard                 Flagship text-to-image (Soul)
reve/text-to-image                          Versatile text-to-image alternative
bytedance/seedream/v4/text-to-image         Seedream v4 text-to-image
bytedance/seedream/v4/edit                  Advanced image editing

# Video (image-to-video)
higgsfield-ai/dop/standard                  DoP — camera-move catalog
higgsfield-ai/dop/preview                   DoP premium tier
kling-video/v2.1/pro/image-to-video         Kling v2.1 Pro
bytedance/seedance/v1/pro/image-to-video    Seedance v1 Pro
```

Additional routed models (Veo 3/3.1, Sora 2, WAN, Speak, Mix, Avatar,
Popcorn, Recast) visible in the cloud.higgsfield.ai dashboard. Always
confirm model_id against the dashboard before productionizing a new
route.

### Operation: Soul — text-to-image

```http
POST https://platform.higgsfield.ai/higgsfield-ai/soul/standard
Authorization: Key {id}:{secret}
Content-Type: application/json

{
  "prompt": "tactical-luxury founder at a black desk, editorial lighting",
  "aspect_ratio": "16:9",    // 1:1 | 4:5 | 16:9 | 9:16
  "resolution": "720p"       // 720p | 1080p | 2K (model-dependent)
}

→ 200
{ "status": "queued", "request_id": "<uuid>", "status_url": "...", "cancel_url": "..." }
```

Final webhook payload on completion:

```json
{
  "status": "Completed",
  "request_id": "<uuid>",
  "images": [{"url": "https://cdn.higgsfield.ai/..."}]
}
```

### Operation: Seedream v4 text-to-image (SDK form)

```python
import higgsfield_client

result = higgsfield_client.subscribe(
    'bytedance/seedream/v4/text-to-image',
    arguments={
        'prompt': 'A serene lake at sunset with mountains',
        'resolution': '2K',
        'aspect_ratio': '16:9',
        'camera_fixed': False,
    },
)
print(result['images'][0]['url'])
```

### Operation: DoP image-to-video

```http
POST https://platform.higgsfield.ai/higgsfield-ai/dop/standard
Authorization: Key {id}:{secret}
Content-Type: application/json

{
  "image_url": "https://cdn.eos.local/sources/hoodie.jpg",
  "prompt": "charcoal hoodie slowly rotates, revealing embroidered mark",
  "duration": 5
}
```

Final webhook payload:

```json
{
  "status": "Completed",
  "request_id": "<uuid>",
  "video": {"url": "https://cdn.higgsfield.ai/..."}
}
```

### Operation: Kling v2.1 Pro image-to-video

```http
POST https://platform.higgsfield.ai/kling-video/v2.1/pro/image-to-video
Body: { "image_url": "...", "prompt": "...", "duration": 5 }
```

### Operation: Seedance v1 Pro image-to-video

```http
POST https://platform.higgsfield.ai/bytedance/seedance/v1/pro/image-to-video
Body: { "image_url": "...", "prompt": "...", "duration": 5 }
```

### Operation: File upload (reference images for image-to-video)

```python
# Raw bytes
with open('hoodie.jpg', 'rb') as f:
    data = f.read()
url = higgsfield_client.upload(data, content_type='image/jpeg')

# Convenience: file path
url = higgsfield_client.upload_file('/opt/OS/media/sources/hoodie.jpg')

# PIL image
from PIL import Image
img = Image.open('hoodie.jpg')
url = higgsfield_client.upload_image(img, format='jpeg')

# Async variants
url = await higgsfield_client.upload_async(data, content_type='image/jpeg')
url = await higgsfield_client.upload_file_async('hoodie.jpg')
```

The returned URL is a Higgsfield-hosted signed URL safe to pass as
`image_url` in any image-to-video model call.

### Operation: Submit + poll (sync)

```python
import higgsfield_client

controller = higgsfield_client.submit(
    'bytedance/seedream/v4/text-to-image',
    arguments={'prompt': 'Football ball', 'resolution': '2K',
               'aspect_ratio': '16:9', 'camera_fixed': False},
    webhook_url='https://eos.local/webhooks/higgsfield',
)

for status in controller.poll_request_status():
    if isinstance(status, higgsfield_client.Queued): print('Queued')
    elif isinstance(status, higgsfield_client.InProgress): print('In progress')
    elif isinstance(status, higgsfield_client.Completed): print('Completed')
    elif isinstance(status, (higgsfield_client.Failed,
                             higgsfield_client.NSFW,
                             higgsfield_client.Cancelled)): print('Done (terminal)')

result = controller.get()
print(result['images'][0]['url'])
```

### Operation: Submit + poll (async)

```python
import asyncio, higgsfield_client

async def main():
    controller = await higgsfield_client.submit_async(
        'bytedance/seedream/v4/text-to-image',
        arguments={'prompt': 'Football ball', 'resolution': '2K',
                   'aspect_ratio': '16:9', 'camera_fixed': False},
        webhook_url='https://eos.local/webhooks/higgsfield',
    )
    async for status in controller.poll_request_status():
        ...
    result = await controller.get()

asyncio.run(main())
```

### Operation: Cancel

```python
controller.cancel()              # sync
await controller.cancel()        # async
```

### Status lifecycle

```
queued → in_progress → completed
                    ↘  failed
                    ↘  nsfw
                    ↘  cancelled
```

Completed / Failed / NSFW / Cancelled are terminal. Webhook fires on
Completed / Failed / NSFW. In-progress updates are poll-only.

## Configuration Patterns

There is no config file. "Configuration" means the consistent set of
defaults Antony uses across runs. Document them in his project folders:

```
brand-presets/personal-brand/higgsfield.md
  default_camera_preset:  Crash Zoom In
  default_soul_preset:    Editorial
  default_aspect:         9:16   (Reels / TikTok / Shorts)
  default_duration:       5s
  default_model:          Kling 3.0   (cost-efficient default)
  fallback_model:         Higgsfield DoP native

brand-presets/lyfe-spectrum/higgsfield.md
  default_camera_preset:  Lazy Susan
  default_soul_preset:    Glam
  default_aspect:         1:1    (product hero)
  default_duration:       5s
  default_model:          Kling 3.0

brand-presets/empyrean-studio/higgsfield.md
  default_camera_preset:  Bullet Time
  default_soul_preset:    Film Noir
  default_aspect:         16:9   (cinematic pitch)
  default_duration:       8s
  default_model:          Veo 3   (when budget allows)
```

The agent reads these on every Higgsfield handoff and applies them unless
the brief overrides.

## Error Handling

GUI tool, so errors arrive as UI states, not exceptions. The catalog the
agent should know:

- **Generation queued indefinitely** → server load. Wait 2–5 min, do not
  re-submit (you'll burn credits twice).
- **"Content policy violation"** → silent on DoP, explicit on Veo/Sora
  routes. Strip references to brands, weapons, real public figures, NSFW
  language. Re-route through Kling.
- **"Identity drift"** → subject's face morphs mid-clip. Cause: no Soul ID
  or weak reference frame. Fix: re-generate with stronger reference or
  train Soul ID.
- **Black frame / corrupt MP4 download** → known intermittent CDN issue.
  Re-download from the History tab; do not re-generate.
- **"Insufficient credits"** → block. Agent must NOT silently substitute a
  cheaper model — flag to Antony with the cost delta.
- **Soul preset returns wildly off-brief** → preset and prompt fighting.
  Drop the preset, restate aesthetics in prompt body.
- **Speak lip sync drifts** → audio too long (>30s), or audio has music
  underneath. Cut audio into <15s chunks, run separately, stitch in Mix.

## Webhooks / Events

**Real, first-class.** Register a webhook per request by either:

1. SDK kwarg: `webhook_url='https://eos.local/webhooks/higgsfield'`
2. Query param: `?hf_webhook=https%3A%2F%2Feos.local%2Fwebhooks%2Fhiggsfield`

Higgsfield fires a POST to the registered URL on **final status only**:
Completed, Failed, or NSFW. In-progress / queued updates must be
polled via `GET /requests/{id}/status`.

### Payload schema

```json
// image model
{
  "status": "Completed",
  "request_id": "<uuid>",
  "status_url": "https://platform.higgsfield.ai/requests/<uuid>/status",
  "cancel_url": "https://platform.higgsfield.ai/requests/<uuid>/cancel",
  "images": [{"url": "https://cdn.higgsfield.ai/..."}]
}

// video model
{
  "status": "Completed",
  "request_id": "<uuid>",
  "status_url": "...",
  "cancel_url": "...",
  "video": {"url": "https://cdn.higgsfield.ai/..."}
}

// failure
{ "status": "Failed", "request_id": "<uuid>", "error": "..." }

// nsfw (unbilled)
{ "status": "NSFW", "request_id": "<uuid>" }
```

### Delivery guarantees

- **Retries:** automatic for up to **2 hours** until handler returns 2xx.
- **Receiver requirements:** publicly accessible, POST, 2xx response.
- **Signature verification:** NOT documented. Treat the endpoint as
  unsigned — enforce idempotency on `request_id` and validate it
  against an EOS-issued set before acting.
- **Idempotency:** required on your side. Higgsfield may redeliver;
  dedup on `request_id`.

### EOS handler skeleton

```python
from flask import Flask, request
from eos_ai.db import get_conn
app = Flask(__name__)

@app.post('/webhooks/higgsfield')
def higgsfield_webhook():
    payload = request.get_json()
    rid = payload['request_id']
    status = payload['status']

    with get_conn() as conn:
        cur = conn.cursor()
        # Idempotency + issued-by-EOS validation
        cur.execute(
            "SELECT id, venture, model_id FROM higgsfield_jobs "
            "WHERE request_id=%s AND status IS NULL FOR UPDATE",
            (rid,),
        )
        row = cur.fetchone()
        if not row:
            return '', 200   # unknown or already processed — ack and drop

        # Download output within 7-day retention window
        url = (payload.get('images') or [{}])[0].get('url') \
              or (payload.get('video') or {}).get('url')
        if status == 'Completed' and url:
            download_to_eos_media(url, venture=row.venture, request_id=rid)

        cur.execute(
            "UPDATE higgsfield_jobs SET status=%s, finished_at=now() "
            "WHERE request_id=%s",
            (status, rid),
        )
    return '', 200
```

## Rate Limits

**Plan-dependent, not publicly numeric.** Rate limits vary by
subscription tier and by specific model. Exact numbers are viewable
in the `cloud.higgsfield.ai` dashboard under the account billing /
usage page. Enterprise customers can request increased limits via
`support@higgsfield.ai`.

Model-specific **timeouts** also exist — generation requests that
exceed the per-model wall-clock ceiling fail without charge.

### EOS pacing strategy

Because limits are opaque, treat rate limiting as a backpressure
problem rather than a precomputed budget:

1. Serialize submissions through a single async worker per model
   family (one worker per `dop/*`, one per `soul/*`, one per
   `kling-video/*`, etc.).
2. On 429 / rate-limit error, apply exponential backoff starting at
   5s, capped at 5 minutes. Respect any `Retry-After` header if
   present.
3. For large batches (drop-day 30-shot runs), interleave submissions
   across model families to spread load.
4. Track in Neon: `{request_id, model_id, submitted_at, finished_at}`
   and compute empirical per-model throughput for future batches.

## Pagination / Streaming

**N/A at the API surface** — Higgsfield's public API is per-request
async job submission, not a list endpoint. There is no `GET /requests`
that lists your history and no cursor pagination.

EOS pagination lives on the Neon side: the `higgsfield_jobs` table is
the canonical history, agents query it for past generations by
`venture`, `model_id`, `submitted_at`, or `request_id`.

## SDK Idioms

**`higgsfield-client`** is the first-party Python SDK. Install:

```bash
pip install higgsfield-client
```

Supported languages:
- **Python** — sync + async, first-party, shipped.
- **JavaScript / TypeScript** — "coming soon" as of 2026-04-06. Until
  it ships, Node services must use raw REST against
  `https://platform.higgsfield.ai`.

### Three idiomatic call shapes

**1. Fire-and-wait (`subscribe`)** — blocks until terminal.

```python
result = higgsfield_client.subscribe(model_id, arguments={...})
```

**2. Submit + poll (`submit`)** — returns a controller for manual
progress tracking.

```python
ctl = higgsfield_client.submit(model_id, arguments={...},
                                webhook_url='https://eos.local/...')
for status in ctl.poll_request_status():
    ...
result = ctl.get()
```

**3. Submit + callback kwargs** — `on_enqueue=`, `on_queue_update=`
event hooks.

```python
def on_enqueue(request_id): ...
def on_status_update(status): ...

higgsfield_client.subscribe(model_id, arguments={...},
                             on_enqueue=on_enqueue,
                             on_queue_update=on_status_update)
```

### Async twins

Every sync function has an `_async` counterpart: `subscribe_async`,
`submit_async`, `upload_async`, `upload_file_async`, `upload_image_async`.

### Controller object

The object returned by `submit()` / `submit_async()` exposes:

```python
ctl.request_id               # uuid string — persist in Neon
ctl.poll_request_status()    # generator / async generator of status objects
ctl.status()                 # one-shot status read
ctl.get()                    # block/await for terminal result
ctl.cancel()                 # cancel queued request
```

Status class hierarchy (use `isinstance` for dispatch):

```
higgsfield_client.Queued
higgsfield_client.InProgress
higgsfield_client.Completed
higgsfield_client.Failed
higgsfield_client.NSFW
higgsfield_client.Cancelled
```

### EOS wrapper pattern

Wrap the SDK in a thin EOS-specific module
(`eos_ai/higgsfield_client.py`) that:

1. Reads `HIGGSFIELD_API_KEY` + `HIGGSFIELD_API_KEY_SECRET` from
   `/opt/OS/eos_ai/.env`.
2. Inserts a `higgsfield_jobs` row in Neon on submit (request_id +
   venture + model_id + args + submitted_at).
3. Registers a single webhook URL (`https://eos.local/webhooks/
   higgsfield`) for every call.
4. Provides `higgsfield.generate(venture, model_id, **kwargs)` as the
   only entry point — no direct SDK calls elsewhere in the codebase.
5. Handles the 7-day retention download on webhook ack, writing to
   `/opt/OS/media/higgsfield/{venture}/{YYYY-MM-DD}/{request_id}.{ext}`.

---

# Tier 2 — The Camera-Move Catalog (Core Skill)

This is the heart of the tool. Higgsfield's signature is the named camera
preset, and creator-level mastery means knowing which preset fits which
narrative beat. The full 50+ catalog with usage guidance:

## Push / Pull (subject-anchored translation)

- **Crash Zoom In** — rapid emphasis, surprise, revelation, urgency. The
  default hook for "moment of realization" beats. Subject locked, lens
  punches in fast. Best for face reactions, product reveals.
- **Crash Zoom Out** — sudden context drop, "oh no" reveal, scale shock.
  Use when the joke or stakes live in the wider frame.
- **Super Dolly In** — slow, weighted push toward subject. Gravitas.
  Use for "founder explains the thesis" cinematic openings.
- **Super Dolly Out** — slow weighted pull. Loneliness, scale, finality.
- **Dolly In / Dolly Out** — gentler versions of Super Dolly. Use for
  conversational pacing.
- **Double Dolly** — push then pull within a single clip. Pendulum feel,
  for hesitation or revelation-then-retreat.
- **Rapid Zoom In / Out** — like Crash Zoom but with optical-zoom feel
  rather than physical dolly. Snappier, more "TV news" energy.
- **Through Object In / Out** — camera passes through a foreground
  object (window, doorway, glass). Reveals, transitions between scenes.

## Dolly Zoom (Vertigo)

- **Dolly Zoom In** — physical push + optical zoom-out. Background
  collapses around static subject. Disorientation, dread, realization.
  The Spielberg signature. Use sparingly — overused becomes parody.
- **Dolly Zoom Out** — physical pull + optical zoom-in. Background
  rushes in. Use for "the world closes in" beats.
- **YoYo Zoom** — oscillating dolly zoom. Trippy, anxiety. Use for
  drug/dream sequences or hyper-stylized fashion.

## Orbits & Arcs

- **360 Orbit** — full lateral revolution around subject. The product-
  reveal default. Locks subject identity, shows all angles.
- **Lazy Susan** — subject rotates on a turntable, camera static. Inverse
  of 360 Orbit. Best for products where the BACKGROUND should stay still.
  THE Lyfe Spectrum apparel preset.
- **Arc Left / Arc Right** — partial orbit. Use for half-reveals, profile
  transitions.
- **Robo Arm** — programmatic motion-control rig style. Geometric, fast,
  precision. Looks like a Bot & Dolly demo. Tech / luxury / automotive.

## Crane / Vertical

- **Crane Up** — rises off subject toward sky. Endings, transitions,
  "and then he walked away" beats.
- **Crane Down** — descends from sky onto subject. Openings, arrivals.
- **Crane Over The Head** — overhead pass. Establishing, omniscient.
- **Jib Up / Jib Down** — gentler crane. Conversational, less cinematic.
- **Tilt Up / Tilt Down** — fixed-position vertical pivot. Reveal of tall
  subject (skyscraper, person standing up).

## Handheld / Energy

- **Handheld** — natural human-operator wobble. Documentary feel.
- **FPV Drone** — first-person-view drone, agile, fast, energetic. Action
  sequences, chase, swoops through architecture. The TikTok signature.
- **Snorricam** — camera rigged to subject's body, subject appears static
  while the world moves around them. Disorienting, character-locked,
  walking shots that feel like the world is the thing in motion.
- **Whip Pan** — violently fast pan, transition device, "what just
  happened" energy.
- **Wiggle** — small jittery shake. Comedic emphasis, glitch aesthetic.

## Specialty / Stylized

- **Bullet Time** — frozen-moment circular pan around subject. The Matrix
  signature. Use for HERO beats only — it screams "look at me" and burns
  novelty fast.
- **Hero Cam** — low-angle hero framing, locked on subject, slight push.
  The "founder reveal" preset. Use for personal-brand intros.
- **Glam** — slow, sensual, high-fashion drift. Beauty / fashion / luxury.
- **Mouth In** — extreme push into subject's mouth. Visceral, weird,
  rarely useful — but unforgettable when it fits.
- **Eating Zoom** — push during eating action, food close-up beat.
- **Object POV** — camera mounted on a moving object's perspective.
- **Fisheye** — extreme wide-angle distortion. Skate / 90s hip-hop.
- **Dutch Angle** — tilted horizon. Unease, instability.
- **Focus Change** — rack focus between foreground and background subject.
  Conversational reveal.

## Vehicle / Action

- **Car Chasing** — vehicle pursuit framing, locked on a moving car.
- **Car Grip** — camera rigged to a car body, exterior vehicle motion.
- **Buckle Up** — interior driver POV, fastening seatbelt → drive.
- **Road Rush** — speed-blur road forward motion.
- **Flying Cam Transition** — drone pass-through used as scene cut.

## Time Manipulation

- **Hyperlapse** — accelerated motion through space, walking/driving
  through environments at high speed.
- **Timelapse Glam** — fashion timelapse, outfit changes, hair, makeup.
- **Timelapse Human** — person aging or repeating action across time.
- **Timelapse Landscape** — environment over hours/days.
- **Low Shutter** — long-exposure motion blur on a still subject.

## Static / Reference

- **Static** — camera does not move. Use when the subject's motion is the
  story and the camera should disappear. Often the BEST choice — the
  most cinematic move is no move at all.
- **BTS** — behind-the-scenes documentary framing.
- **Pan Left / Pan Right** — basic horizontal pan.
- **Head Tracking** — camera follows subject's head movement.
- **Incline** — angled approach toward subject.

## Picking the right preset (decision tree)

```
Is the subject a person?
├── YES → Is this a hero/intro shot?
│         ├── YES → Hero Cam | Crash Zoom In | Bullet Time (sparingly)
│         └── NO  → Is the person walking/moving?
│                   ├── YES → Snorricam | Handheld | FPV Drone
│                   └── NO  → Static | Super Dolly In | Dolly Zoom In
└── NO  → Is the subject a product?
          ├── YES → Lazy Susan | 360 Orbit | Robo Arm
          └── NO  → Is it a place/environment?
                    ├── YES → FPV Drone | Crane Down | Hyperlapse
                    └── NO  → Static | Through Object In
```

---

# Tier 3 — Soul Aesthetic Presets

Soul presets define the *look* of the still, which then becomes the input
frame for DoP. The 50+ catalog organized by family:

- **Editorial / Fashion** — Editorial, Fashion Editorial, Glam, Coquette,
  Vogue, Runway, Lookbook, Cover Story
- **Era / Period** — Y2K, 90s, 70s, Medieval, Victorian, Polaroid, Film Noir
- **Place / Subculture** — Tokyo Street Style, Parisian, NYC, LA, Berlin
- **Device / Format** — iPhone, Polaroid, Disposable, Webcam, CCTV, Fisheye
- **Lighting / Mood** — Low Key, High Key, Golden Hour, Blue Hour, Neon
- **Material / Texture** — Cinematic, Matte, Glossy, Grain Heavy

Stacking rule: **one preset + 2–4 modifier tokens.** Exceeding this drowns
identity. Example correct stack:

```
Preset: Editorial
Modifiers: low-key lighting, 35mm anamorphic, teal-and-amber grade,
shallow depth of field
```

Example BROKEN stack (do not do):

```
Preset: Editorial + Glam + Fashion Editorial
Modifiers: cinematic, dramatic, moody, sexy, high fashion, vogue cover,
runway, golden hour, blue hour, neon, anamorphic, 35mm, 50mm, 85mm,
shallow DOF, deep DOF, teal-and-amber, desaturated, vibrant
```

---

# Tier 4 — Prompt Engineering

## The Higgsfield Prompt Formula

```
[Subject] + [One Beat] + [Camera Move] + [Style Tokens]
```

- **Subject** = one sentence locking who/what is in frame.
- **One Beat** = ONE strong verb describing ONE action that happens during
  the camera move's duration. Not three actions. Not a paragraph.
- **Camera Move** = the named preset, on its own line. Do not also
  describe the camera in the body of the prompt.
- **Style Tokens** = 2–4 modifiers: lighting + lens + palette + era.

## Why short prompts beat long ones

Higgsfield rewards direct commands and punishes descriptive paragraphs.
Long prompts force the model to guess which clauses are aesthetic vs
which are action vs which are camera direction. Short prompts collapse
ambiguity. The official Higgsfield blog confirms: "short prompts produce
stronger control than long ones."

Worked comparison:

BAD (long, ambiguous):
```
A handsome young entrepreneur sitting at his desk in a beautiful modern
office with lots of natural light streaming through the windows, looking
thoughtfully at his laptop screen as he types away on an important project,
with the camera slowly moving in toward his face as he looks up and smiles
warmly at the camera while the soft afternoon light creates a beautiful
cinematic atmosphere with shallow depth of field and a teal and orange
color grade reminiscent of modern Hollywood films.
```

GOOD (short, tight):
```
A founder at a black desk, hands on keyboard.
He looks up sharply.
Camera: Crash Zoom In
Style: low-key, 35mm anamorphic, teal-and-amber, shallow DOF.
```

The bad version contains six actions, two camera directions, and stacks
six aesthetic claims. Higgsfield will average them all and produce mush.
The good version contains one action, one camera move, four aesthetic
tokens. Higgsfield executes it cleanly.

## Multi-shot scene structure

For 2–6 shot sequences (use Mix to stitch), structure as:

```
Shot 1 (5s) — [Camera A] — [Beat 1]
Shot 2 (5s) — [Camera B] — [Beat 2]
Shot 3 (5s) — [Camera C] — [Beat 3]
```

Vary the camera preset across shots. Repetition kills cinematic feel —
three Crash Zoom Ins in a row read as a glitch, not a sequence.

---

# Tier 5 — Pricing & Routing Strategy

## Plan tiers (2026-04, subject to change)

- **Free** — 10 credits/day, 1 concurrent job, basic models. Useless for
  production.
- **Basic** — $9/mo, 150 credits/mo
- **Pro** — $17.40/mo, 600 credits/mo
- **Ultimate** — $29.40/mo, 1200 credits/mo
- **Creator** — $119/mo, 6000 credits/mo

Note: alternate tier names appear in some sources (Starter $15, Plus $34,
Ultra $84, Business $49/seat). Pricing is in flux. Confirm with Antony
which plan is active before promising specific output volumes.

## Per-generation cost (model routing)

```
Kling 3.0           ~6 credits     ← cost-efficient default
Kling 2.5 Turbo     ~8 credits
Higgsfield DoP      ~10 credits
Veo 3 / Veo 3.1     40–70 credits  ← premium, gated
Sora 2              40–70 credits  ← premium, gated
WAN                 ~15 credits
Soul (image)        1–2 credits
Speak (per second)  ~2 credits/sec
```

## Routing decision

```
Budget priority?      → Kling 3.0
Realism priority?     → Veo 3
Physics / motion?     → Sora 2
Cinematic / camera?   → Higgsfield DoP native
Speed priority?       → Kling 2.5 Turbo
```

---

# Tier 6 — EOS Usage Patterns

## Pattern 1: Personal brand hook shot

```
TRIGGER:  Antony asks for a 5s opening hook for a piece of brand content.

INPUTS:   topic line + reference photo of him (or describe him)

DRAFT:
  Reference: [photo path]
  Prompt:    [one sentence subject] + [one verb beat]
  Camera:    Crash Zoom In  (or Hero Cam if intro)
  Style:     low-key, 35mm anamorphic, teal-and-amber, shallow DOF
  Model:     Kling 3.0
  Duration:  5s
  Aspect:    9:16
  Cost:      ~6 credits
```

## Pattern 2: Lyfe Spectrum product drop

```
TRIGGER:  Apparel drop announcement, hero clip needed.

INPUTS:   product photo (or product description)

DRAFT:
  Reference: [product photo]
  Prompt:    [garment description] + [rotation or reveal beat]
  Camera:    Lazy Susan  (rotation) or Robo Arm (geometric reveal)
  Style:     Glam preset, hard rim light, matte texture, no people
  Model:     Kling 3.0
  Duration:  5s
  Aspect:    1:1 or 9:16
  Cost:      ~6 credits
```

## Pattern 3: Empyrean Studio pitch reel beat

```
TRIGGER:  Client pitch deck, cinematic mood beat needed.

INPUTS:   client brief + tone reference

DRAFT:
  Camera:    Bullet Time | Dolly Zoom In | FPV Drone (depending on tone)
  Style:     Film Noir | Cinematic | matched to client palette
  Model:     Veo 3  (if budget allows) or Higgsfield DoP native
  Duration:  8s
  Aspect:    16:9
  Cost:      40–70 credits
```

## Pattern 4: Speak talking-head explainer

```
TRIGGER:  Antony has a script he wants delivered as a talking-head clip
          without filming himself.

INPUTS:   script text + portrait reference

STEP 1 — Generate portrait via Soul:
  Preset:    Editorial
  Prompt:    [Antony description], front-facing, neutral background
  Output:    1080x1920 PNG

STEP 2 — Record VO (Antony, dry, mono, no music)

STEP 3 — Speak 2.0:
  Portrait:    [Soul output]
  Audio:       [VO file]
  Lip sync:    on
  Head motion: subtle
  Background:  static
  Duration:    matches audio
```

## Pattern 5: Multi-shot Mix sequence

```
TRIGGER:  30s brand video needed.

DRAFT:    6 × 5s shots, each with different camera preset, stitched in Mix.

Shot 1 — Hero Cam     — Antony sits down at desk
Shot 2 — Crash Zoom   — He opens the laptop
Shot 3 — Static       — Close-up on hands typing
Shot 4 — Lazy Susan   — Coffee cup rotates on desk
Shot 5 — Dolly Zoom   — He looks up at the camera
Shot 6 — Crane Up     — Pull away from desk, room reveals

Stitch in Mix with hard cuts. Total: 30s.
Cost: 6 × 6 = 36 credits.
```

---

# Tier 7 — Gotchas (Full Catalog)

- **Public API confirmed at `platform.higgsfield.ai`.** Docs at
  `docs.higgsfield.ai`. Auth is `Key {id}:{secret}` (not Bearer).
  Python SDK is `higgsfield-client`. Webhooks fire on Completed/
  Failed/NSFW. 7-day file retention — download outputs into
  `/opt/OS/media/higgsfield/` immediately on webhook ack.
- **Auth scheme foot-gun.** `Authorization: Key {id}:{secret}` — the
  word "Key" is literal, both halves required, colon-separated. Most
  common first-integration bug is using "Bearer".
- **7-day retention.** Generated media URLs expire after ≥7 days.
  Always persist to EOS media storage on webhook receipt.
- **No documented webhook signature.** Enforce idempotency with
  `request_id` dedup; validate it exists in the EOS-issued set before
  acting on the payload.
- **JS/TS SDK not yet shipped.** Python only for first-party SDK
  support. Node services must use raw REST.
- **Credits expire after 90 days.** Top-up packs rot. Never recommend
  bulk purchases for "savings."
- **Model routing changes pricing 10×.** Always state model + cost in
  the handoff. A 5-shot sequence on Kling 3.0 is 30 credits; on Sora 2
  it's 350.
- **Camera-move preset overrides prompt camera language.** Never describe
  the camera in the prompt body when a preset is selected. Doubling up
  produces jitter or fights.
- **Soul preset stacking destroys identity.** Max one preset + 2–4
  modifier tokens.
- **5s is the practical default.** Plan in 5s beats. Use Mix to stitch.
- **Speak audio must be dry.** Music bed under VO destroys lip sync.
- **Free tier is a demo, not a tool.** 10 credits/day, 1 concurrent job.
  Useless for production work.
- **No webhooks.** EOS cannot be notified of completion. Fire-and-forget
  handoffs only.
- **Reference image aspect ratio sets output aspect ratio.** Want 9:16?
  Feed 9:16. The model does not recompose.
- **Veo 3 / Sora 2 have hidden content filters.** Silent failures route
  through these models. Fall back to Kling 3.0.
- **GUI ships weekly.** Re-research this skill if a preset name no longer
  matches the UI.
- **Identity drift without Soul ID.** Subject's face morphs across long
  clips. Fix: train Soul ID once, reuse.
- **Long prompts produce weak motion.** Higgsfield rewards short, verb-led,
  single-beat prompts. Paragraphs produce mush.
- **Bullet Time burns novelty.** Use 1× per project max. Overused = parody.
- **Dolly Zoom is the same.** It is the most-cliché preset in the catalog.
  Reach for it sparingly.
- **Static is underrated.** The most cinematic move is often no move. When
  the subject's action is the story, lock the camera and let it breathe.
- **Mix stitching is forgiving but not magic.** Match cuts require matched
  framing. Plan adjacent shots with shared composition.
- **History tab is the only "list."** No search by tag, no sort by cost.
  Antony's archive discipline matters — he must save outputs to brand
  folders immediately or they get lost in the History scroll.
- **Account-bound, not org-bound.** No team workspace at most tiers.
  All generations live in Antony's personal account. Cannot hand off
  to a collaborator without sharing credentials.
- **Mobile UI is a subset of desktop.** Some presets and models hidden
  on mobile. Antony should generate on desktop / iPad code-server, not
  iPhone.
- **Browser memory matters.** Long Soul / DoP sessions leak memory in
  Chrome. Refresh every 30–45 min if outputs start getting weird.
- **Re-research trigger.** If any of: a preset disappears, pricing
  changes by >25%, a new model is added to routing, Higgsfield ships an
  official API. Update last_researched in SKILL.md frontmatter and bump
  this file.

---

# Tier 8 — When to Escalate to Antony

The agent drafts. Antony decides. Always escalate when:

- The shot list exceeds 10 generations (cost compounds fast)
- A preset choice involves brand identity calls (Vigilante Architect tone)
- A Veo 3 / Sora 2 generation is being recommended (40–70 credits each)
- The reference image doesn't exist yet (Antony has to shoot or source)
- The output is destined for paid ad creative (legal/IP review)
- Speak is being used to make Antony "say" something he didn't actually
  write or approve (this is a hard stop — never put words in his mouth
  via Speak without explicit prompt-level approval)

---

# Tier 9 — Verification

After drafting any Higgsfield handoff, the agent must verify:

- [ ] Camera preset name matches the catalog above
- [ ] Soul preset (if used) is one preset, not stacked
- [ ] Style tokens are 2–4 modifiers, not a paragraph
- [ ] Model + credit cost stated explicitly
- [ ] Aspect ratio matches the destination platform
- [ ] Duration is realistic for the camera move (5s default)
- [ ] No camera language in the prompt body (preset owns it)
- [ ] Reference image path or description is provided
- [ ] Brand-preset defaults from the relevant brand folder applied

If any box is unchecked, the handoff is incomplete. Re-draft before
sending to Antony.
