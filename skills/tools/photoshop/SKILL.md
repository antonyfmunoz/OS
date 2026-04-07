---
name: photoshop
description: "Use when designing, editing, or generating raster art in Adobe Photoshop — interactively in the Photoshop GUI for personal-brand content, Lyfe Spectrum mockups, and Empyrean Studio creative; or programmatically via UXP scripting (in-app panels), the Photoshop API on Firefly Services (headless cloud edits, smart-object replacement, PSD rendering), and the Firefly Generative API (text-to-image, generative fill, generative expand) for AI-assisted drafts. Triggers: PSD authoring, layer comp swaps, batch mockup variants, Camera Raw / ACR profiles, color management for print vs web, action/droplet automation, headless thumbnail generation, AI background fill, brand asset productionization."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developer.adobe.com/photoshop/uxp/2022/ps_reference/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Photoshop 2025 (26.x) / UXP Manifest v5 / Firefly Services v3 / Firefly Image Model 3"
sdk_version: "@adobe/photoshop-apis (npm) — UXP runtime bundled with Photoshop"
speed_category: stable
---

# Tool: photoshop

## What This Tool Does

Photoshop is Adobe's flagship raster editor and the de-facto standard for
pixel-precise image authoring. As of the 2025 release line it exposes **three
distinct programmable surfaces** plus the GUI, and EOS uses all four:

1. **GUI (Photoshop desktop app)** — interactive authoring on macOS/Windows.
   The surface Antony uses daily for personal-brand content, Lyfe Spectrum
   apparel mockups, Empyrean Studio creative, and any pixel-level work that
   requires human judgment.

2. **UXP Scripting & Plugins** — JavaScript (ES2021) running **inside** the
   running Photoshop process. UXP replaces ExtendScript (the legacy `.jsx`
   surface) and CEP panels. Two flavours: **scripts** (single `.psjs` files
   you drop on the canvas or run from File > Scripts) and **plugins** (a
   manifest + entry point loaded from the UDT or the Plugins panel). Both use
   the same DOM (`app`, `app.activeDocument`, `Layer`, `Document`) plus
   `batchPlay` for any operation not yet wrapped in the DOM.

3. **Photoshop API on Firefly Services** — a REST surface at
   `https://image.adobe.io/pie/psdService/*` that performs **headless** PSD
   edits in Adobe's cloud: open a PSD from a pre-signed URL, swap a smart
   object, render a PNG/JPEG, return the result as a pre-signed output URL.
   Asynchronous job model with `_links.self` polling. Endpoints include
   `/smartObject`, `/documentOperations`, `/renditionCreate`, `/text`.

4. **Firefly Generative API** — Adobe's text-to-image, generative fill,
   generative expand, and similarity search endpoints (Image Model 3).
   Authenticates the same way as Photoshop API (IMS client credentials).
   Used standalone for thumbnail/idea generation or composed with the
   Photoshop API for "generate then drop into PSD."

The two API surfaces share IMS auth, the asynchronous job pattern, and the
pre-signed URL storage contract; both are billable per generation. They are
NOT the same as UXP — UXP is local and free (it's just a script running
inside the desktop app).

## EOS Integration

Photoshop is a **hybrid skill**: GUI for human-led creative, APIs for
agent-led production. EOS uses each lane for different jobs.

### GUI lane (Antony, daily)

- **Personal-brand content** — IG posts, carousels, story templates. Source
  PSDs live in `/opt/OS/01_brand/photoshop/` (synced via Dropbox/OneDrive
  on the desktop).
- **Lyfe Spectrum mockups** — apparel mockup PSDs with smart-object slots
  for graphics. Smart-object swap is the canonical workflow: edit the smart
  object once, every mockup updates.
- **Empyrean Studio creative** — client-facing creative direction. Layer
  comps for variant presentation. Color management profiled for both web
  (sRGB) and print (Adobe RGB / CMYK with target profile).

### API lane (agents, headless)

- **Mockup productionization** — once a Lyfe Spectrum PSD is approved in
  the GUI, the agent calls `/smartObject` with a new graphic from the
  Spectrum SKU library, gets back a rendered PNG, posts to the storefront.
  Converts a one-shot human design into an N-variant production line.
- **Thumbnail / OG-image generation** — for blog posts and IG carousels,
  the agent calls Firefly text-to-image to draft a hero, then calls
  `/documentOperations` to drop it into a branded template PSD.
- **Asset migration** — bulk PSD-to-PNG/WEBP rendering via `/renditionCreate`
  during build steps for the SaaS frontends.

### UXP lane (occasional, in-Photoshop automation)

- **Batch ops the GUI doesn't expose** — when Antony has 80 PSDs that all
  need the same 4-step edit, write a `.psjs` script using `batchPlay` and
  run it from File > Scripts inside the desktop app. Faster iteration than
  the cloud API for one-off batch work on already-local files.

### Canonical EOS pattern

```
GUI authors the master PSD → committed to /opt/OS/01_brand/photoshop/
Agent uploads to pre-signed URL → calls /smartObject with variant inputs
Polls _links.self until status='succeeded' → downloads output URL
Posts result to destination (Shopify, IG, blog, Notion)
```

Credentials in `/opt/OS/eos_ai/.env`:
- `ADOBE_IMS_CLIENT_ID`
- `ADOBE_IMS_CLIENT_SECRET`
- `ADOBE_IMS_ORG_ID`
- `ADOBE_FIREFLY_SCOPES=openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis`

## Authentication

**GUI**: Adobe ID sign-in via the desktop app. Single seat per machine.

**UXP**: None — runs inside the already-authenticated desktop app. Plugin
distribution outside the dev workstation requires signing via UDT and
publication on Adobe Exchange.

**Photoshop API + Firefly API**: OAuth 2.0 client-credentials against Adobe
IMS. Single token used for both surfaces.

```bash
curl -X POST https://ims-na1.adobelogin.com/ims/token/v3 \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=client_credentials' \
  -d "client_id=$ADOBE_IMS_CLIENT_ID" \
  -d "client_secret=$ADOBE_IMS_CLIENT_SECRET" \
  -d "scope=$ADOBE_FIREFLY_SCOPES"
```

Token TTL is 24h. Cache it. Every API call requires both:
- `Authorization: Bearer <token>`
- `x-api-key: <client_id>`

## Quick Reference

### IMS token (cached)

```python
import os, time, requests
_TOK = {"v": None, "exp": 0}
def ims_token():
    if _TOK["v"] and time.time() < _TOK["exp"] - 60:
        return _TOK["v"]
    r = requests.post("https://ims-na1.adobelogin.com/ims/token/v3", data={
        "grant_type": "client_credentials",
        "client_id": os.environ["ADOBE_IMS_CLIENT_ID"],
        "client_secret": os.environ["ADOBE_IMS_CLIENT_SECRET"],
        "scope": os.environ["ADOBE_FIREFLY_SCOPES"],
    }, timeout=30)
    r.raise_for_status()
    j = r.json()
    _TOK["v"] = j["access_token"]
    _TOK["exp"] = time.time() + j["expires_in"]
    return _TOK["v"]
```

### Smart-object swap (headless mockup)

```python
headers = {
    "Authorization": f"Bearer {ims_token()}",
    "x-api-key": os.environ["ADOBE_IMS_CLIENT_ID"],
    "Content-Type": "application/json",
}
body = {
    "inputs":  [{"href": SRC_PSD_PRESIGNED, "storage": "external"}],
    "options": {"layers": [{"name": "Artwork", "input": {
        "href": NEW_GRAPHIC_PRESIGNED, "storage": "external"}}]},
    "outputs": [{"href": OUT_PNG_PRESIGNED, "storage": "external",
                 "type": "image/png"}],
}
r = requests.post("https://image.adobe.io/pie/psdService/smartObject",
                  json=body, headers=headers, timeout=30)
job_url = r.json()["_links"]["self"]["href"]
```

### Polling the async job

```python
while True:
    s = requests.get(job_url, headers=headers, timeout=30).json()
    status = s["outputs"][0]["status"]
    if status == "succeeded": break
    if status == "failed":    raise RuntimeError(s["outputs"][0]["errors"])
    time.sleep(2)
```

### Firefly text-to-image (Image Model 3)

```python
r = requests.post("https://firefly-api.adobe.io/v3/images/generate-async",
    headers=headers,
    json={"prompt": "tactical luxury matte black training facility, cinematic",
          "numVariations": 4, "size": {"width": 2048, "height": 2048},
          "contentClass": "photo"})
poll = r.json()["statusUrl"]
```

### UXP `batchPlay` from inside Photoshop (`.psjs`)

```javascript
const { app, core, action } = require("photoshop");
await core.executeAsModal(async () => {
  await action.batchPlay([{
    _obj: "make",
    _target: [{_ref: "layer"}],
    using: {_obj: "layer", name: "Brand Lockup"}
  }], {});
}, {commandName: "Add brand lockup layer"});
```

### Render PSD to PNG (`/renditionCreate`)

```bash
curl -X POST https://image.adobe.io/pie/psdService/renditionCreate \
  -H "Authorization: Bearer $TOK" -H "x-api-key: $CID" \
  -H "Content-Type: application/json" \
  -d '{"inputs":[{"href":"'$SRC'","storage":"external"}],
       "outputs":[{"href":"'$DST'","storage":"external","type":"image/png","width":1024}]}'
```

## Conceptual Model

**The PSD is the source of truth. Every surface is a different way of
mutating it.** A PSD is a tree: `document → layers → smart objects → pixels`,
plus side-channels (layer comps, paths, channels, ACR settings, color
profile). The GUI mutates that tree visually. UXP mutates it via the JS DOM
or `batchPlay` (which is just a JSON command queue piped into Photoshop's
internal action manager). The Photoshop API mutates it from the cloud — Adobe
spins up a Photoshop process server-side, applies your operations, and hands
back the result. The Firefly API doesn't touch a PSD at all; it generates
fresh pixels you can then drop into one.

If you internalize "PSD as tree," every surface stops being magic:
- "Why does my smart-object swap need the layer name?" → it's a tree-node selector
- "Why is `batchPlay` so verbose?" → it's the literal action descriptor format the GUI records
- "Why is the API async?" → because rendering a real PSD takes seconds, not millis
- "Why do I need pre-signed URLs?" → Adobe never stores your assets; you bring storage

The four surfaces compose: GUI authors the master, UXP automates batches the
GUI doesn't expose, Photoshop API productionizes mockups headlessly, Firefly
generates source pixels. Pick the surface that matches the cardinality and
the latency budget.

## Gotchas

- **ExtendScript is dead.** `.jsx` files still run on legacy Photoshop but
  the DOM is frozen. UXP (`.psjs` / plugins) is the only surface getting new
  features. Don't write new ExtendScript.
- **`batchPlay` MUST be inside `executeAsModal`** for any document-mutating
  call, or you get `Error: not in a modal scope`. The DOM equivalents
  (`createLayer`, etc.) handle this for you.
- **`batchPlay` action references prefer `_id` over `_name`** — names are
  not unique across layer groups. Copy from "Copy as JavaScript" in the
  Actions panel (developer mode on) to get correct descriptors.
- **Photoshop API needs pre-signed URLs, not file uploads.** No multipart.
  Generate signed PUT URLs on S3/GCS/Azure first, upload the PSD, then pass
  the GET URL as `inputs[].href`. Firefly has its own `/upload` endpoint —
  Photoshop API does not.
- **Async jobs return immediately with a `_links.self` href.** Always poll;
  never assume completion. Status values: `pending`, `running`, `succeeded`,
  `failed`. `partial` is possible when one of N outputs failed.
- **IMS token scopes matter.** `firefly_api` covers Firefly, `ff_apis`
  covers Photoshop API and other Firefly Services. Request both or you'll
  get 403 on one of them.
- **Color profiles travel with the PSD.** If your master is Adobe RGB and
  the cloud renders without converting to sRGB, your IG post will look
  desaturated. Convert with `/documentOperations` `convertToProfile` before
  rendering for web.
- **Smart-object replacement preserves transforms** (scale, skew, perspective)
  from the original placement. This is the magic that makes mockup PSDs work.
  If your replacement art is the wrong aspect ratio, it will distort silently.
- **Camera Raw (ACR) settings persist on the layer**, not the document.
  Re-applying ACR via UXP requires `_obj: "Adobe Camera Raw Filter"` and
  embedded XMP — not exposed in the high-level DOM.
- **Action droplets** (`.app` on macOS, `.exe` on Windows) are the legacy
  GUI-only batch surface. Functional but unmaintained — prefer UXP scripts.
- **Photoshop API per-call cost is non-trivial.** Budget before turning on
  a batch loop.
- **Firefly generations are NOT free** even in dev. Each variation counts.
- **PSD is a 4 GiB max format**; PSB is 32 EiB. The API rejects > 2 GiB
  PSDs in practice — split into linked smart objects if you need more.

See references/best_practices.md for the full creator-level knowledge base
covering UXP DOM, batchPlay descriptors, Photoshop API endpoints, Firefly
Services, IMS authentication, async job model, error catalog, color
management, EOS usage patterns, and the complete gotcha list.
