---
name: higgsfield
description: "Use when drafting Higgsfield AI video or image prompts for Antony to execute via the web GUI — short-form cinematic content for personal brand, Lyfe Spectrum drops, or Empyrean Studio creative work. Trigger on requests for camera-move shot lists, image-to-video prompts, Soul photo prompts, talking-avatar (Speak) scripts, or any time the brief mentions Bullet Time / Crash Zoom / FPV / Dolly Zoom / cinematic AI video."
allowed-tools: "Read, Write, Edit"
version: 1.0
source_url: "https://higgsfield.ai/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Higgsfield Cloud API — base https://platform.higgsfield.ai (REST, async job queue, webhooks)"
sdk_version: "higgsfield-client (Python, sync + async); JS/TS coming soon"
speed_category: stable
---

# Tool: Higgsfield AI

## What This Tool Does

Higgsfield is a browser-based AI video and image generation platform whose
brand-defining feature is **fine-grained camera-move control**. Where most
AI video tools give you a generic "pan/zoom" toggle, Higgsfield ships 50+
named cinematic motion presets (Bullet Time, Crash Zoom, FPV Drone, Dolly
Zoom, Snorricam, Robo Arm, Lazy Susan, etc.) that lock the subject and
execute the move with film-grade physics.

The platform is a wrapper / orchestration layer over multiple underlying
models (its own DoP/Soul models plus Kling, Veo 3, Sora 2 routed through the
same UI and credit pool). You pick a model, optionally pick a camera-move
preset, optionally pick a Soul aesthetic preset, supply a text prompt and/or
reference image, and Higgsfield generates a 3–15s clip at 720p/1080p.

Core product surface (2026-04):

- **DoP** — cinematic video model. Image-to-video and text-to-video. The
  home of the camera-move catalog.
- **Soul / Soul 2.0** — hyper-realistic photo model with 50+ aesthetic
  presets (iPhone, Tokyo Street Style, Y2K, Editorial, Fisheye). Outputs
  stills that are typically the input frame for DoP.
- **Soul ID** — character consistency: train an identity once, reuse across
  Soul photos and DoP videos.
- **Speak / Speak 2.0** — talking avatar. Image + audio → lip-synced video.
- **Mix** — multi-shot composer for stitching beats into longer cuts.
- **Avatar** — full character pipeline (often paired with Speak).
- **Popcorn / Recast** — newer cinematic / restyling endpoints.
- **Routed models** — Kling 2.5 / 3.0, Veo 3 / 3.1, Sora 2, WAN — all
  consumable through the Higgsfield UI under one credit pool.

## EOS Integration

**Operating mode: hybrid — real API for agent-callable generation + GUI
for creative exploration.** Higgsfield ships a public REST API at
`https://platform.higgsfield.ai` with a Python SDK (`higgsfield-client`),
async job queue, and webhook callbacks. Agents CAN call Higgsfield
directly for headless generation. The GUI remains the exploration
surface — Antony tunes prompts there, then agents productionize the
winning formulas against the API for batch work (drop campaigns, social
cadence, ad creative variation).

Primary EOS use cases:

- **Personal brand short-form** — opening hook shots for Vigilante Architect
  content. Bullet Time on a desk slam, Crash Zoom into the laptop, FPV out
  the window of the Portland HQ.
- **Lyfe Spectrum drops** — apparel hero clips. Glam preset + Lazy Susan
  on a folded hoodie, Snorricam on a model walking, Tokyo Street Style
  Soul stills as the source frame.
- **Empyrean Studio creative work** — client-facing cinematic mood pieces,
  pitch reels, Game of Lyfe early concept tests.
- **Initiate Arena marketing** — conversion-grade B-roll for landing pages
  and ad creative when stock footage is too generic.

Canonical EOS handoff patterns:

**Pattern A — Agent-callable production (API):**
1. Agent picks model (`higgsfield-ai/soul/standard`, `higgsfield-ai/dop/standard`,
   `bytedance/seedream/v4/text-to-image`, `kling-video/v2.1/pro/image-to-video`,
   `bytedance/seedance/v1/pro/image-to-video`, etc.).
2. Agent calls `higgsfield_client.submit(model_id, arguments={...},
   webhook_url=...)` or `subscribe()` for sync.
3. Webhook fires on Completed / Failed / NSFW to an EOS endpoint.
4. Handler downloads output from returned URL within 7-day retention
   window, writes to `/opt/OS/media/higgsfield/{venture}/{date}/`.

**Pattern B — Creative exploration (GUI):**
1. Antony explores a concept in higgsfield.ai web GUI with camera-move
   presets, Soul aesthetics, Soul ID identity lock.
2. Once a winning recipe is found, agent translates it into an API
   `arguments` dict and productionizes for batch/scheduled runs.

## Authentication

**Base URL:** `https://platform.higgsfield.ai`

**Auth header:** API keys are generated in the `cloud.higgsfield.ai`
dashboard (Clerk-authenticated). Each key is a pair —
**key id + key secret** — passed together in the Authorization header:

```
Authorization: Key {HIGGSFIELD_API_KEY}:{HIGGSFIELD_API_KEY_SECRET}
Content-Type: application/json
Accept: application/json
```

EOS secret storage:
- `HIGGSFIELD_API_KEY` and `HIGGSFIELD_API_KEY_SECRET` in
  `/opt/OS/eos_ai/.env` (never committed).
- Python SDK auto-reads them from the environment.

Failed and NSFW-flagged requests are NOT charged — credits refund
automatically. Invoice billing available for enterprise via
`support@higgsfield.ai`.

## Quick Reference

### REST API — raw curl

```bash
# Submit a Soul image generation
curl -X POST 'https://platform.higgsfield.ai/higgsfield-ai/soul/standard' \
  -H 'Authorization: Key '"$HIGGSFIELD_API_KEY:$HIGGSFIELD_API_KEY_SECRET" \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "tactical-luxury founder at black desk, editorial lighting",
    "aspect_ratio": "16:9",
    "resolution": "720p"
  }'
# → { "status": "queued", "request_id": "<uuid>", ... }

# Poll status
curl "https://platform.higgsfield.ai/requests/{request_id}/status" \
  -H 'Authorization: Key '"$HIGGSFIELD_API_KEY:$HIGGSFIELD_API_KEY_SECRET"

# Cancel a queued request
curl -X POST "https://platform.higgsfield.ai/requests/{request_id}/cancel" \
  -H 'Authorization: Key '"$HIGGSFIELD_API_KEY:$HIGGSFIELD_API_KEY_SECRET"
```

### Python SDK — sync

```python
import higgsfield_client

result = higgsfield_client.subscribe(
    'higgsfield-ai/soul/standard',
    arguments={
        'prompt': 'tactical-luxury founder at black desk, editorial lighting',
        'aspect_ratio': '16:9',
        'resolution': '720p',
    },
)
print(result['images'][0]['url'])
```

### Python SDK — submit + webhook (EOS canonical pattern)

```python
import higgsfield_client

controller = higgsfield_client.submit(
    'higgsfield-ai/dop/standard',
    arguments={
        'image_url': 'https://cdn.eos.local/sources/hoodie.jpg',
        'prompt': 'charcoal hoodie slowly rotates, revealing Lyfe Spectrum mark',
        'duration': 5,
    },
    webhook_url='https://eos.munozconglomerate.com/webhooks/higgsfield',
)
request_id = controller.request_id  # persist in Neon for reconciliation
```

### File upload (reference image for image-to-video)

```python
url = higgsfield_client.upload_file('/opt/OS/media/sources/hoodie.jpg')
# Pass as image_url in DoP / Kling / Seedance arguments
```

### Webhook payload (EOS handler)

```python
# POST /webhooks/higgsfield
# Add ?hf_webhook=... on request OR set webhook_url in SDK
{
  "status": "Completed",        # or Failed / NSFW
  "request_id": "<uuid>",
  "status_url": "...",
  "cancel_url": "...",
  "images": [{"url": "..."}]    # for image models
  # OR "video": {"url": "..."}  # for video models
}
# Retry policy: 2 hours until 2xx. Idempotency key: request_id.
```

### Known model IDs (docs snapshot 2026-04-06)

```
Images:
  higgsfield-ai/soul/standard           (flagship text-to-image, Soul)
  reve/text-to-image                    (versatile alternative)
  bytedance/seedream/v4/text-to-image   (Seedream v4, text-to-image)
  bytedance/seedream/v4/edit            (advanced editing)

Video (image-to-video):
  higgsfield-ai/dop/standard            (DoP — camera-move catalog lives here)
  higgsfield-ai/dop/preview             (premium tier)
  kling-video/v2.1/pro/image-to-video   (Kling v2.1 Pro)
  bytedance/seedance/v1/pro/image-to-video  (Seedance v1 Pro)
```

Full routed-model list (Veo 3/3.1, Sora 2, WAN, Speak, Mix, Avatar,
Popcorn, Recast) is visible in the cloud.higgsfield.ai dashboard.
Confirm exact model_id before coding against a new model.

### The two preset axes (pick one of each)

```
CAMERA MOVE  (DoP, locks subject, defines motion)
  Bullet Time | Crash Zoom In/Out | Dolly Zoom In/Out | FPV Drone
  Super Dolly In/Out | 360 Orbit | Lazy Susan | Snorricam | Robo Arm
  Crane Up/Down | Whip Pan | Hyperlapse | Handheld | Static
  (full 50+ catalog in references/best_practices.md)

SOUL AESTHETIC  (look of the source frame)
  iPhone | Tokyo Street Style | Y2K | Editorial | Fisheye | Medieval
  Coquette | Glam | Film Noir | Polaroid | Fashion Editorial
```

### Prompt skeleton (paste into Higgsfield DoP)

```
[Subject anchor — who/what, one sentence]
[One beat — strong verb, one camera move, one subject action]
Camera: [camera-move preset name, e.g. "Crash Zoom In"]
Style: [aesthetic tokens — lighting, palette, lens, era]
```

### Worked example — Vigilante Architect hook

```
Reference image: Antony at desk, side-lit, dark room, MacBook open.

Prompt:
A tactical-luxury founder seated at a black desk, hands on keyboard.
He looks up sharply as the camera punches in on his face.
Camera: Crash Zoom In
Style: low-key cinematic, single key light from screen, 35mm anamorphic,
teal-and-amber grade, shallow depth of field.

Model:    Higgsfield DoP (image-to-video)
Duration: 5s
Output:   1080p
Est cost: ~6 credits (Kling 3.0 routing)
```

### Worked example — Lyfe Spectrum hoodie drop

```
Reference image: folded charcoal hoodie on concrete, top-down.

Prompt:
A folded heavyweight charcoal hoodie centered on raw concrete.
The garment slowly rotates revealing the embroidered Lyfe Spectrum mark.
Camera: Lazy Susan
Style: Glam preset, hard rim light, shadow play, fashion editorial,
matte texture, no people.

Model:    Higgsfield DoP
Duration: 5s
Output:   1080p
```

### Worked example — Speak talking avatar

```
Inputs:
  - Soul-generated portrait of Antony (Editorial preset)
  - 12s VO recording: "Structure beats discipline. Every time."

Higgsfield Speak 2.0 settings:
  Lip sync:    on
  Head motion: subtle
  Background:  static
  Output:      1080p, 12s
```

## Conceptual Model

**Higgsfield is a director's chair, not a renderer.** The mental model is
not "describe a video, get a video" — that produces mush. The model is
**lock one variable, vary one variable**: lock the subject (via reference
image or Soul ID), lock the camera (via preset), then write a prompt that
only describes the *one beat* of action that happens during the move.

Three locked dimensions, one free dimension:

- **Identity** locked by the reference image or Soul ID.
- **Aesthetic** locked by the Soul preset (or style tokens in the prompt).
- **Camera** locked by the camera-move preset.
- **Action** is the only thing the prompt describes — and it should be
  one verb, one beat, timed to the duration of the camera move.

Internalize this and Higgsfield's quirks make sense:
- "Why is my prompt being ignored?" → you over-described the camera; the
  preset already owns the camera. Delete that half of the prompt.
- "Why does the subject morph?" → no reference image, no Soul ID, identity
  unlocked.
- "Why is the motion so weak?" → you wrote a paragraph; Higgsfield rewards
  short, verb-led, single-beat prompts.

## Gotchas

- **Public docs at docs.higgsfield.ai.** The docs index lives at
  `docs.higgsfield.ai/llms.txt` — pull it when refreshing this skill.
  API base is `https://platform.higgsfield.ai`. The management
  dashboard at `cloud.higgsfield.ai` is where API keys are generated
  (Clerk-authenticated).
- **Auth header is `Key {id}:{secret}` — NOT `Bearer`.** The single
  most likely first-integration bug. Both halves of the key pair are
  required, colon-separated.
- **`hf_webhook` query param OR `webhook_url` SDK kwarg.** Two ways to
  register the same callback. Pick one per request, never both.
- **Webhooks have no documented signature verification.** Idempotency
  must be enforced on the handler side using `request_id` as the dedup
  key. Treat the endpoint as publicly callable and verify the
  `request_id` exists in the EOS-issued set before acting.
- **Webhook retries for 2 hours until 2xx.** Return 2xx fast; do the
  work in a background task after ack.
- **7-day file retention.** Generated images/videos disappear from
  Higgsfield storage after ≥7 days. EOS must download outputs into
  `/opt/OS/media/higgsfield/` immediately on webhook ack or the URLs
  will 404.
- **Failed + NSFW requests are NOT charged.** Credits auto-refund.
  Don't build guardrails that pre-pay; let the API reject and refund.
- **Rate limits vary by plan and model.** Not publicly numeric —
  viewable in the cloud.higgsfield.ai dashboard. Enterprise can raise
  via support@higgsfield.ai.
- **Timeouts are per-model.** No global wall-clock. A DoP generation
  timeout is different from a Seedream edit timeout. Exceeded requests
  fail without charge.
- **JS/TS SDK is "coming soon."** Python SDK `higgsfield-client` is
  the only first-party path today. For Node services, use raw REST
  until the JS SDK ships.
- **Credits expire after 90 days.** Top-up packs disappear. Don't tell
  Antony to bulk-buy credits "to save money" — they rot.
- **Model routing changes pricing silently.** Kling 3.0 ≈ 6 credits,
  Sora 2 / Veo 3.1 ≈ 40–70 credits per generation. Always note the model
  in the handoff so he picks the right one.
- **Camera-move preset overrides prompt camera language.** If you also write
  "camera slowly zooms in" in the prompt body, you double-up and get jitter.
  Camera lives ONLY in the preset line.
- **Soul presets stack badly.** More than 2–3 style tokens overpower
  identity. Pare back to: lighting + lens + palette + era. That's it.
- **5s default is real.** Most DoP outputs are 5s clips. Plan shot lists
  as 5s beats, not 30s scenes. Use Mix to stitch.
- **Speak needs clean audio.** Background noise in the VO destroys lip sync.
- **Free tier = 10 credits/day.** Useless for production.
- **Webhooks DO fire on final status only** (Completed / Failed / NSFW),
  not intermediate progress. For progress UI, poll `/requests/{id}/status`.
- **Reference-image aspect ratio sets output aspect ratio.** Want 9:16 for
  Reels? Feed a 9:16 source frame. The model will not recompose.
- **Veo 3 / Sora 2 routing has content filters Higgsfield doesn't surface
  in the UI.** If a generation silently fails, fall back to Kling 3.0.
- **GUI changes ship weekly.** Re-research this skill if a preset name in
  the catalog stops matching what's in the UI.

See references/best_practices.md for the full 19-section creator-level
knowledge base, the complete 50+ camera-move catalog with usage notes,
the Soul preset reference, and the EOS prompt-pattern library.
