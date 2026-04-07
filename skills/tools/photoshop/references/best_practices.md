# Photoshop — Creator-Level Best Practices
Source: developer.adobe.com/photoshop/uxp, developer.adobe.com/firefly-services, developer.adobe.com/photoshop/photoshop-api-docs, helpx.adobe.com/photoshop
API Version: Photoshop 2025 (26.x) desktop / Photoshop API on Firefly Services v3 / Firefly Image Model 3 / UXP Manifest v5
SDK Version: @adobe/photoshop-apis (npm), UXP runtime bundled with desktop, no first-party Python SDK
Last Researched: 2026-04-06

This document is the creator-level reference for the four Photoshop surfaces:
the desktop GUI, UXP scripting/plugins inside the desktop app, the Photoshop
API on Firefly Services (headless cloud edits), and the Firefly Generative API
(text-to-image, generative fill). Where a section is GUI-only and has no API
analogue, the section explains the GUI mechanism and the closest API
equivalent. Where a section is API-only, the GUI implication is called out.

---

# Tier 1 — Technical Mastery

## Authentication

There are three independent authentication surfaces. Confusing them is the
single most common failure mode.

### 1. Desktop GUI

Adobe ID sign-in via `Help > Sign In` in the desktop app. One seat per
machine for the standard Creative Cloud subscription; two activated machines
allowed (Mac + Windows for the same user) but only one running at a time.
Sign-in state is cached in the OS keychain. Offline grace period is 99 days
before reactivation is required. No token surface — the GUI handles its own
session.

### 2. UXP (in-app scripts and plugins)

None. UXP runs **inside** the already-authenticated Photoshop process. A
script that calls `app.activeDocument.layers[0]` is implicitly authorized as
the signed-in user. There is no token to mint, no header to send, no scope
to declare. The only auth-adjacent step is **plugin signing**, required when
distributing a plugin outside your own dev workstation:

- Generate a self-signed certificate (`xd-pkg sign-cert`) or use Adobe's
  signing service via the UDT (UXP Developer Tool).
- The signed `.ccx` is what you upload to Adobe Exchange.
- Unsigned plugins can be loaded into your local UDT for development but
  cannot be installed on a clean Photoshop on someone else's machine.

### 3. Photoshop API + Firefly API (cloud REST)

OAuth 2.0 client-credentials grant against Adobe Identity Management
Services (IMS). Both the Photoshop API and the Firefly API share the same
token; the difference is in the scopes requested.

```
POST https://ims-na1.adobelogin.com/ims/token/v3
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=<client_id>
&client_secret=<client_secret>
&scope=openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86399
}
```

Token TTL is 24h. Cache it. Refresh proactively at TTL minus 60s. Every
API request after the token mint requires both:

- `Authorization: Bearer <access_token>`
- `x-api-key: <client_id>`

The `x-api-key` is your client_id, NOT a separate API key. This trips up
people who expect a separate "API key" string.

### Scope decoder

| Scope               | What it unlocks                                          |
|---------------------|----------------------------------------------------------|
| `openid`            | Required base scope                                       |
| `AdobeID`           | Identity claims                                          |
| `session`           | Session lifecycle                                        |
| `read_organizations`| Org context for the technical account                    |
| `firefly_api`       | Firefly Generative API (text-to-image, fill, expand)     |
| `ff_apis`           | Photoshop API + other Firefly Services (Lightroom etc.)  |

EOS requests both `firefly_api` and `ff_apis` so a single token covers both
surfaces. Without `ff_apis` you get 403 on every Photoshop API call even
though Firefly works fine — and vice versa.

### EOS conventions

- Credentials in `/opt/OS/eos_ai/.env` (`ADOBE_IMS_CLIENT_ID`,
  `ADOBE_IMS_CLIENT_SECRET`, `ADOBE_IMS_ORG_ID`, `ADOBE_FIREFLY_SCOPES`).
- Single `ims_token()` helper in `eos_ai/adobe.py` (TODO when first written)
  with module-level cache. Never mint a token per request.
- Never check the secret into git. Never log the access token.
- The technical account (the IMS principal) needs the Photoshop API and
  Firefly Services products granted in Adobe Admin Console; a fresh project
  in developer.adobe.com is NOT enough.

## Core Operations with Exact Signatures

### UXP DOM (in-app JavaScript)

The high-level DOM lives in the `photoshop` module:

```javascript
const { app, core, action, constants } = require("photoshop");
const { executeAsModal } = core;
const { batchPlay } = action;
```

Top-level entities:

```
app                                        // singleton
app.documents                              // Document[]
app.activeDocument                         // Document | null
app.foregroundColor / backgroundColor      // SolidColor
app.open(token | path)                     // Promise<Document>
app.createDocument(options)                // Promise<Document>

Document
  .layers                Layer[]
  .activeLayers          Layer[]
  .width / height        number (px)
  .resolution            number (dpi)
  .colorMode             constants.ColorMode
  .save() / saveAs()
  .close(saveOptions)
  .closeWithoutSaving()
  .createLayer(opts)     Promise<Layer>
  .duplicateLayers()     Promise<Layer[]>
  .flatten()             Promise<void>
  .resizeImage(w, h, res, resampleMethod)
  .crop(bounds)
  .selection             Selection
  .layerComps            LayerComp[]
  .channels              Channel[]
  .paths                 PathItem[]
  .guides                Guide[]
  .historyStates         HistoryState[]

Layer
  .id                    number (stable for session)
  .name                  string
  .kind                  LayerKind (PIXEL, TEXT, SMART_OBJECT, GROUP, ...)
  .opacity / fillOpacity number (0-100)
  .visible               boolean
  .locked                boolean
  .blendMode             BlendMode
  .bounds                {top, left, bottom, right}
  .parent                Layer | Document
  .delete()
  .duplicate()
  .move(target, location)
  .applyFilter(...)
  .smartObject?          SmartObject  // only if kind === SMART_OBJECT
```

Document creation:

```javascript
await executeAsModal(async () => {
  const doc = await app.createDocument({
    typename: "DocumentCreateOptions",
    width: 2048, height: 2048, resolution: 300,
    mode: "RGBColorMode",
    fill: "white",
    name: "brand-asset",
  });
}, {commandName: "Create document"});
```

Layer creation via the DOM:

```javascript
await executeAsModal(async () => {
  const layer = await app.activeDocument.createLayer({
    name: "Brand Lockup",
    opacity: 100,
    blendMode: "normal",
  });
}, {commandName: "Create layer"});
```

### batchPlay (everything not yet wrapped in the DOM)

`batchPlay` takes an array of action descriptors and executes them as a
single Photoshop command queue:

```
action.batchPlay(
  descriptors: ActionDescriptor[],
  options: { synchronousExecution?: boolean, modalBehavior?: "execute"|"wait"|"fail" }
): Promise<ActionDescriptor[]>
```

An action descriptor:

```javascript
{
  _obj: "make",                         // command verb
  _target: [{_ref: "layer"}],           // what it operates on
  using: { _obj: "layer", name: "X" },  // command-specific args
  _options: { dialogOptions: "dontDisplay" }
}
```

Reference selectors:

```javascript
{_ref: "layer", _id: 123}               // BEST: stable id
{_ref: "layer", _enum: "ordinal", _value: "targetEnum"}  // active layer
{_ref: "layer", _name: "Brand Lockup"}  // by name (NOT unique across groups)
{_ref: "document", _id: 1}
```

How to discover the right descriptor: turn on developer mode in the Actions
panel, record the action via the GUI, then "Copy as JavaScript" from the
panel flyout — the resulting snippet is paste-ready batchPlay.

### Photoshop API REST endpoints

Base: `https://image.adobe.io/pie/psdService`

| Endpoint              | Verb | Purpose                                          |
|-----------------------|------|--------------------------------------------------|
| `/smartObject`        | POST | Replace one or more smart objects in a PSD       |
| `/documentOperations` | POST | Multi-op pipeline (edit text, layers, render)    |
| `/renditionCreate`    | POST | Render PSD to PNG/JPEG/TIFF at given size        |
| `/text`               | POST | Edit text layers (content, font, color)          |
| `/documentManifest`   | POST | Return JSON tree of layers/smart objects         |
| `/photoshopActions`   | POST | Run a `.atn` action file against a PSD           |

Body shape (canonical):

```json
{
  "inputs":  [{"href": "<presigned-get-url>", "storage": "external"}],
  "options": { ... endpoint-specific ... },
  "outputs": [{"href": "<presigned-put-url>", "storage": "external", "type": "image/png"}]
}
```

`storage` values: `external` (any pre-signed URL), `dropbox`, `azure`,
`adobe` (Firefly upload). Photoshop API does NOT expose its own upload —
it requires `external` or a third-party storage value.

Response (always async):

```json
{
  "_links": {
    "self": { "href": "https://image.adobe.io/pie/psdService/status/<job_id>" }
  }
}
```

Poll the `_links.self.href` until `outputs[i].status` is `succeeded` or
`failed`.

### Firefly API endpoints

Base: `https://firefly-api.adobe.io`

| Endpoint                                | Purpose                              |
|-----------------------------------------|--------------------------------------|
| `/v3/images/generate-async`             | Text-to-image (Image Model 3)        |
| `/v3/images/fill-async`                 | Generative fill (mask in-painting)   |
| `/v3/images/expand-async`               | Generative expand (out-painting)     |
| `/v3/images/similar-async`              | Variations of an existing image      |
| `/v2/storage/image`                     | Upload reference image, get short id |
| `/v3/status/<job_id>`                   | Async job status                     |

`generate-async` body:

```json
{
  "prompt": "tactical luxury training facility, matte black, cinematic light",
  "numVariations": 4,
  "size": {"width": 2048, "height": 2048},
  "contentClass": "photo",
  "seeds": [12345],
  "promptBiasingLocaleCode": "en-US",
  "visualIntensity": 6,
  "style": {"presets": ["cinematic"]}
}
```

## Pagination Patterns

The Photoshop API and Firefly API are **task-oriented, not list-oriented**.
There is no `?page=` or `?cursor=` parameter on any documented endpoint.
What looks like pagination in this ecosystem is the **async job model**:

- POST creates a job, returns an immediate 202 with `_links.self.href`.
- GET on that href returns job state. Repeat until terminal.
- Each output in `outputs[]` has its own status.

For anything resembling list iteration (e.g. enumerating all your past
generations), the answer is "store them yourself" — Adobe does not provide
an account-level history endpoint.

The UXP DOM has no pagination either. `app.documents`, `Document.layers`,
etc. are eagerly materialized arrays in the JS runtime (because the entire
document tree is already in memory in the desktop process). Iterate with
ordinary `for...of`. For very large layer trees use `for (let i = layers.length - 1; i >= 0; i--)` so deletes don't shift indices under you.

GUI: N/A. The UI has its own infinite-scroll mechanisms (Libraries panel,
Search, etc.) but they are not exposed.

## Rate Limits

### Photoshop API

Adobe publishes per-organization rate limits but the exact ceiling is set
per technical account in Admin Console and is not in public docs. The
practical floor for new accounts is on the order of a few requests per
second sustained, with burst headroom. The contract:

- HTTP `429 Too Many Requests` when over the limit.
- `Retry-After` header (seconds) on 429s — honor it.
- `x-request-id` echoed on every response — log it for support tickets.
- Async jobs do NOT count against rate limits during polling, only at
  submission. Long-running jobs are free to monitor.

### Firefly API

Same shape: 429 with `Retry-After`. Generation cost ALSO counts against your
plan's per-month image quota — running into the quota wall returns
`402 Payment Required` (or `403` with `quota_exceeded`), NOT `429`. These
are different conditions with different remediations.

### UXP

No rate limit — it's local. The constraint is Photoshop's main thread; long
synchronous loops freeze the UI. Wrap heavy work in `executeAsModal` and
yield with `await` between iterations.

### GUI

N/A. Single user, single session.

### EOS handling

Centralized in `eos_ai/adobe.py` (when written):

```python
def adobe_request(method, url, **kw):
    for attempt in range(5):
        r = requests.request(method, url, **kw)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 2 ** attempt))
            time.sleep(wait); continue
        if r.status_code in (502, 503, 504):
            time.sleep(2 ** attempt); continue
        return r
    r.raise_for_status()
```

## Error Codes and Recovery

### IMS (token mint)

| Code | Meaning                          | Recovery                                  |
|------|----------------------------------|-------------------------------------------|
| 400  | `invalid_client_id`              | Check `ADOBE_IMS_CLIENT_ID`               |
| 400  | `invalid_scope`                  | Wrong scope string — check the comma list |
| 401  | `invalid_credentials`            | Wrong client_secret — rotate              |
| 403  | `not_entitled`                   | Product not granted in Admin Console       |
| 429  | rate-limited token mint           | Cache the token, stop minting per request |

### Photoshop API

| Code | Meaning                                   | Recovery                              |
|------|-------------------------------------------|---------------------------------------|
| 400  | `BadRequest` malformed body               | Validate against `/documentManifest`  |
| 401  | invalid bearer                            | Re-mint IMS token                     |
| 403  | `forbidden` missing scope or x-api-key    | Add `ff_apis` scope                   |
| 404  | input href 404                            | Check pre-signed URL hasn't expired   |
| 409  | conflicting layer operations              | Order ops in `documentOperations`     |
| 415  | unsupported media type                    | Set `Content-Type: application/json`  |
| 429  | rate limit                                | Honor `Retry-After`                   |
| 500  | internal — Adobe-side                     | Retry with backoff, then file ticket  |

Per-output errors (inside the polled status response) are MORE granular:

```json
{
  "outputs": [{
    "status": "failed",
    "errors": {
      "type": "InputValidationError",
      "code": "InputValidationError",
      "title": "Input file is corrupt or unsupported"
    }
  }]
}
```

Common per-output failure modes:

- `InputValidationError` — PSD couldn't be parsed, often a PSB > 2 GiB.
- `LayerNotFound` — selector targeted a layer name that doesn't exist
  (case-sensitive, group path matters).
- `OutputUploadError` — pre-signed PUT URL expired before the job completed.
- `RenderingError` — corrupt smart object source, missing fonts, missing
  linked files.
- `MissingFont` — font not in Adobe Fonts and not embedded; substitute
  silently or fail loudly via `manageMissingFonts: "fail"`.

### Firefly API

| Code | Meaning                                | Recovery                              |
|------|----------------------------------------|---------------------------------------|
| 400  | `prompt_too_long` (>1024 chars)         | Trim                                  |
| 400  | `unsafe_prompt`                         | Reword — content moderation rejected  |
| 402  | quota exceeded                          | Top up plan                           |
| 422  | `image_too_large` (reference upload)    | Resize to <2048 on long edge          |
| 504  | generation timeout                       | Retry, lower numVariations            |

### UXP

`batchPlay` errors throw with a `.number` field (legacy Action Manager error
code) and a human message:

```javascript
try {
  await action.batchPlay([...], {});
} catch (e) {
  console.error(e.message, e.number);
}
```

Common:
- `Error: not in a modal scope` → wrap in `core.executeAsModal`
- `Error: The command is not currently available` → no document open, or
  wrong layer kind selected
- `Error: General Photoshop error` → almost always a malformed descriptor;
  re-record from the Actions panel

## SDK Idioms

### `@adobe/photoshop-apis` (Node.js)

The official Node SDK wraps the REST contract. Idiomatic use:

```javascript
const { PhotoshopAPI } = require("@adobe/photoshop-apis");
const ps = new PhotoshopAPI({
  clientId: process.env.ADOBE_IMS_CLIENT_ID,
  clientSecret: process.env.ADOBE_IMS_CLIENT_SECRET,
  orgId: process.env.ADOBE_IMS_ORG_ID,
});

const job = await ps.smartObject.replace({
  inputs: [{href: SRC, storage: "external"}],
  options: {layers: [{name: "Artwork", input: {href: NEW, storage: "external"}}]},
  outputs: [{href: OUT, storage: "external", type: "image/png"}],
});

const result = await job.pollUntilDone({intervalMs: 2000, timeoutMs: 300_000});
```

The SDK handles IMS token caching internally. EOS does NOT use this SDK
because EOS is Python-first; the canonical EOS pattern is the raw REST shape
in `eos_ai/adobe.py`.

### Python (no first-party SDK)

There is no official Python SDK for Photoshop API or Firefly API. EOS uses
`requests` directly. Community SDKs exist (e.g. `pyfirefly`) but are
unmaintained. Don't depend on them.

### UXP idioms

- **Always** wrap document mutations in `core.executeAsModal`.
- Prefer DOM methods over `batchPlay` when available — they're typed and
  handle modal scope for you.
- Use `localFileSystem` from `uxp.storage` for all file I/O — direct
  `fs.readFile` is sandboxed away.
- For long operations, call `core.setSuspensionMessage(suspensionId, "Step 3 of 10")` to update the busy dialog.

## Anti-Patterns

- **Per-request IMS token mint.** Doubles latency and trips IMS rate limits.
  Cache for 24h (or 23h to be safe).
- **Polling jobs at 100 ms.** Wastes calls; the work doesn't finish faster.
  Start at 2s, exponential backoff up to 30s.
- **Treating the Photoshop API like a synchronous tool.** Every endpoint is
  async even when the operation feels instant.
- **Selecting layers by name in `batchPlay`** when an `_id` is available.
  Names collide; ids are stable per session.
- **Mutating PSDs in cloud and saving back over the master.** Cloud edits
  should write to a NEW pre-signed PUT URL, never overwrite the canonical
  source. Treat masters as immutable; the GUI is the only authoring surface.
- **Running `batchPlay` outside `executeAsModal`** for any mutating op.
- **Using ExtendScript (`.jsx`)** for new code. The DOM is frozen and
  ExtendScript is removal-pending in a future major.
- **Embedding fonts not on Adobe Fonts in cloud-rendered PSDs.** They will
  silently substitute. Either subset and embed, or use the `fonts` option
  on `documentOperations` to provide pre-signed font URLs.
- **Generating images inline with the user-facing request loop.** Firefly
  generations take 5-30s. Always queue + webhook (or async-poll on a
  worker) so the request thread returns immediately.
- **Hardcoding `https://image.adobe.io/...` URLs in agent code.** Centralize
  in `eos_ai/adobe.py` so endpoint changes are one edit.
- **Skipping `x-api-key` header.** Returns 403 with a confusing
  `unauthorized` message — looks like a token issue, isn't.

## Data Model

### PSD as a tree

```
Document
├─ Color Profile (ICC: sRGB, Adobe RGB, ProPhoto, CMYK profiles)
├─ Bit depth (8/16/32)
├─ Color mode (RGB, CMYK, Lab, Indexed, Grayscale, Multichannel)
├─ Resolution (dpi)
├─ Layers[]
│  ├─ Pixel Layer        (raster, has channels)
│  ├─ Text Layer         (vector, font + glyph runs + warp)
│  ├─ Shape Layer        (vector path + fill + stroke)
│  ├─ Smart Object       (embedded or linked, transforms preserved)
│  │  ├─ Embedded: PSD/PSB/JPG/RAW data inside the parent PSD
│  │  └─ Linked: external file path, resolved at render
│  ├─ Adjustment Layer   (curves, levels, HSL, LUT, ...)
│  ├─ Fill Layer         (solid, gradient, pattern)
│  ├─ Group              (recursive container, can clip/mask)
│  └─ Background         (special locked pixel layer at bottom)
├─ Layer Comps[]         (named snapshots: visibility, position, appearance)
├─ Paths[]               (vector paths, used for selections, masks, shapes)
├─ Channels[]            (R, G, B, A + alpha channels + spot colors)
├─ Guides / Grid
├─ Slices                (legacy web export, mostly dead)
├─ History States[]      (undo stack, not persisted in PSD)
└─ Metadata (XMP, IPTC, EXIF)
```

### Smart objects

The single most important feature for productionization. A smart object is
a **container layer** holding either:

- **Embedded** content (the source PSD/JPG/AI/RAW data is copied into the
  parent PSD's binary), or
- **Linked** content (a path to an external file, resolved on open/render).

Crucially: **transforms applied to the smart object container are preserved
across content swaps.** If you scale a 4000×4000 logo down to 800×800,
rotate 15°, and apply a perspective skew, then "Replace Contents" with a
new 4000×4000 logo, the new logo gets exactly the same scale, rotation, and
skew. This is the entire mechanism behind apparel mockups.

The Photoshop API `/smartObject` endpoint does this swap headlessly, given
the parent PSD and the new content URL.

### Layer comps

A layer comp captures three things per layer:

1. Visibility
2. Position
3. Appearance (layer styles + opacity + blend mode)

You can flip between comps in the Layer Comps panel. The Photoshop API can
render any comp via `documentOperations` with a `layerComp` selector. EOS
uses comps for "same template, multiple variant slates" — e.g. one PSD with
five comps, each rendering a different IG carousel slide.

### Camera Raw / ACR

Camera Raw is a non-destructive raw processing engine bundled with
Photoshop. As a layer-level smart filter (`Filter > Camera Raw Filter`) it
holds an XMP sidecar of edits (exposure, contrast, HSL, curves, masks,
profile). ACR settings travel with the layer, not the document. The Adobe
RAW SDK underlying ACR is the same engine Lightroom uses.

The Photoshop API does NOT expose ACR directly — to apply an ACR preset
headlessly you bake it into a `.atn` action and run via `/photoshopActions`,
or use the Lightroom API on Firefly Services for raw-first workflows.

### Color management

Photoshop is one of the few apps that actually does color management
correctly. Three places color profiles live:

1. **Working space** (Edit > Color Settings) — what new docs default to.
2. **Document profile** — what's embedded in the PSD itself.
3. **Output profile** — what `Convert to Profile` or `Save As...` writes.

The chain matters: an Adobe RGB master rendered to PNG **without** profile
conversion will look correct in color-managed viewers (browsers with ICC
support) and DESATURATED in non-managed contexts (most IG previews,
Discord, Slack thumbnails). Always `convertToProfile: sRGB` for web output,
preserve Adobe RGB or CMYK for print delivery.

### Actions and droplets

An **action** is a recorded sequence of GUI commands stored in `.atn`. The
Actions panel records, plays back, and allows step-by-step editing. Actions
are the legacy automation surface (pre-UXP, pre-API) and are still useful
because they record EVERYTHING the GUI does.

A **droplet** is an action exported as an OS executable (`.app` on macOS,
`.exe` on Windows). Drop files on the droplet → Photoshop opens, runs the
action, saves. This is the legacy desktop batch surface; functional but
unmaintained. Prefer UXP scripts for new work, prefer Photoshop API for
remote/headless batches.

The Photoshop API DOES support actions: `/photoshopActions` accepts a `.atn`
file URL plus an input PSD URL and runs the action against it. This is the
fastest way to migrate an existing GUI workflow into the cloud.

## Webhooks and Events

### Photoshop API + Firefly API

Neither surface provides callback webhooks. The async job model is
**polling-only**: POST returns a job URL, you GET it until terminal.

The closest analogue: Firefly Services jobs return signed output URLs in
the polled status response, so once you see `succeeded` you have the result
URL ready to fetch. Pre-signed URLs typically have a 1-hour TTL — fetch
immediately or store the result yourself.

EOS pattern for "webhook-like" behavior: a worker that polls jobs from a
local queue, then publishes a Discord/Telegram message when the result
is ready. The worker is the durable side, not Adobe.

### UXP events

UXP exposes Photoshop's event system for in-app reactions:

```javascript
const { addNotificationListener } = require("photoshop").action;
addNotificationListener(["select", "make", "set"], (event, descriptor) => {
  console.log("Photoshop event:", event, descriptor);
});
```

Use cases: panels that update when the user selects a layer, plugins that
react to document open. Local-only — no network surface.

### GUI

Scripts > Event Manager (legacy) maps Photoshop events to action playback.
Functional but unmaintained — UXP `addNotificationListener` is the
forward path.

## Limits

| Limit                                           | Value                            |
|-------------------------------------------------|----------------------------------|
| PSD max file size                               | 4 GiB                            |
| PSB max file size                               | 32 EiB (effectively unlimited)   |
| PSD max canvas dimension                        | 30,000 × 30,000 px               |
| PSB max canvas dimension                        | 300,000 × 300,000 px             |
| Photoshop API max input file size (practical)   | ~2 GiB                           |
| Photoshop API max output PNG dim                | 30,000 px on long edge           |
| Firefly text-to-image max output                | 2048 × 2048 (Image Model 3)      |
| Firefly prompt max length                       | 1024 characters                  |
| Firefly numVariations max                       | 4 per call                       |
| Pre-signed URL TTL (Adobe-side defaults)        | 60 min for outputs               |
| IMS token TTL                                   | 24 hours                         |
| UXP `batchPlay` array length                    | No hard limit; perf degrades >1k |
| Layers per PSD                                  | 8000 (hard limit, 26.x)          |
| Layer name length                               | 255 chars                        |
| Channels per document                           | 56 max                           |
| History states (configurable)                   | 1000 max                         |

## Cost Model

### GUI

Creative Cloud subscription. Photoshop single-app ~$23/mo, All Apps ~$60/mo.
EOS uses the All Apps plan because Lightroom + Illustrator + InDesign all
get used. No per-document or per-export cost.

### UXP

Free. Bundled with Photoshop. No marginal cost for scripts, plugins, or
batchPlay calls.

### Photoshop API

Pay-per-call against the Firefly Services plan. Pricing as of late 2025:

- Smart object replace: 1 transaction
- Document operations: 1 transaction
- Rendition create: 1 transaction (per output)
- Photoshop actions: 1 transaction
- Document manifest: free / very low

Transactions bundle into the Firefly Services plan. New developer accounts
get a free monthly allowance; production use requires a paid plan via Adobe
sales. Budget seriously before turning on a batch loop — 10,000 mockup
renders/month is real money.

### Firefly API

Per-image-generated quota. Each variation in a `numVariations: 4` call
counts as 4 generations. Same plan envelope as Photoshop API.

### EOS budgeting

- Lyfe Spectrum mockup pipeline: budget per SKU × variants × storefront
  refresh frequency.
- Firefly text-to-image is for DRAFT generation only; never put it in a
  user-facing real-time path.
- Cache aggressively: every generated asset goes to S3 with content-hash
  keys so we never regenerate the same thing twice.

## Version Pinning

| Component             | Pinning strategy                                          |
|-----------------------|-----------------------------------------------------------|
| Photoshop desktop     | Auto-update via Creative Cloud; pin to current release    |
| UXP runtime           | Bundled with Photoshop; pin via `manifestVersion: 5`      |
| Plugin manifest       | Declare `host.minVersion` and `host.maxVersion` in manifest|
| Photoshop API         | Implicit; Adobe versions endpoints by URL path            |
| Firefly API           | Explicit; URL path `/v3/...` is the version              |
| `@adobe/photoshop-apis`| `package.json` semver pin                                |

UXP plugin manifest example:

```json
{
  "manifestVersion": 5,
  "id": "com.eos.brand-tools",
  "name": "EOS Brand Tools",
  "version": "1.0.0",
  "host": {
    "app": "PS",
    "minVersion": "24.0.0"
  },
  "main": "index.html",
  "entrypoints": [
    {"type": "panel", "id": "panel.brand", "label": {"default": "Brand"}}
  ],
  "requiredPermissions": {
    "localFileSystem": "fullAccess",
    "network": {"domains": ["https://image.adobe.io", "https://firefly-api.adobe.io"]}
  }
}
```

Network permissions MUST be declared per-domain. UXP rejects fetches to
undeclared hosts at runtime — silent in console, broken in panel.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Photoshop is 35+ years old. Every decision in the API surface reflects an
evolution from a single-machine pixel editor → multi-document workspace →
non-destructive workflow → cloud-native creative platform. Understanding
the trajectory makes the surfaces stop feeling arbitrary.

**Why three programmable surfaces?** Each was added at a different era:

- **Action Manager / ScriptListener (1996+)** — the original automation,
  recorded GUI commands. Persists today as the underlying engine that
  `batchPlay` talks to.
- **ExtendScript (2003+)** — JS-based scripting bundled with Adobe apps.
  Stable, ubiquitous, frozen, dying. Adobe stopped adding new APIs in 2021.
- **CEP (2013+)** — HTML panels in Adobe apps. Replaced by UXP. Removal
  scheduled but repeatedly delayed.
- **UXP (2020+)** — modern JS runtime, sandboxed, ES2021+, the only
  forward-compatible surface. Replaces both ExtendScript and CEP.
- **Photoshop API on Firefly Services (2022+)** — headless cloud, originally
  positioned as "Creative Cloud Automation Services." Folded into Firefly
  Services in 2024 alongside Lightroom API and Firefly Generative API.
- **Firefly Generative API (2023+)** — Adobe's bet on commercially-safe
  generative AI. Trained on Adobe Stock + public domain + licensed content
  to give enterprises IP indemnification.

**Why async-only on cloud APIs?** Real Photoshop work is slow. Opening a
2 GiB PSD takes seconds, rendering a 30,000 × 30,000 canvas takes longer.
The async contract is honest about that — no fake synchronous wrapper that
times out at 30s and leaves jobs orphaned.

**Why pre-signed URLs and not multipart?** Adobe deliberately doesn't store
your assets. Bring your own storage = no data residency confusion, no
"where did my PSD go," no GDPR ambiguity. The tradeoff is more setup work
on the caller side.

**Why `executeAsModal` in UXP?** Photoshop's internal command system was
designed assuming a single user driving a single document with a modal lock
(the "you can't edit while a filter is running" lock). UXP exposes that
lock explicitly so plugins can't race the user. The annoyance is real but
the alternative would be subtle corruption.

## Problem-Solution Map and Hidden Capabilities

| Problem                                                   | Solution                                                         |
|-----------------------------------------------------------|------------------------------------------------------------------|
| Generate 50 apparel mockups from 1 design                 | `/smartObject` per variant; cache by content hash                |
| Brand-safe AI hero images                                 | Firefly text-to-image with `contentClass: photo`                 |
| Batch resize 200 PSDs to web sizes                        | `/renditionCreate` in a loop; or UXP script for local files      |
| Replace text in PSD without opening it                    | `/text` endpoint or `documentOperations` with `editText`         |
| Apply same Curves adjustment to many photos               | Record action, run via `/photoshopActions`                       |
| Out-painting beyond original frame                        | `firefly-api /v3/images/expand-async`                            |
| Remove background non-destructively                       | `Select Subject` (sensei), then layer mask; UXP-driven via batchPlay |
| Generate variations of a hero image                       | `firefly-api /v3/images/similar-async`                           |
| Inspect what's inside a PSD without downloading           | `/documentManifest` returns layer JSON                           |
| Re-render a comp without editing it                       | `/renditionCreate` with `layerComp` selector                     |
| Build a panel that lives in Photoshop                     | UXP plugin with manifest v5                                      |
| Generate alt-text for image                               | Firefly Custom Models / Adobe Sensei (separate API)              |
| Convert RAW to PSD non-destructively                      | Open via Camera Raw (Smart Object option ON); ACR settings persist|
| Batch ACR preset application                              | `/photoshopActions` running an action that applies the preset    |

### Hidden capabilities people miss

- **`/documentManifest` is free intel.** Pull the layer tree of a PSD
  before mutating it; you don't have to know layer names ahead of time.
- **Smart object linked vs embedded** — embed for portability, link for
  shared sources updated across many parents (e.g. one logo file linked
  into 200 mockup PSDs).
- **Adjustment layers stack non-destructively** — never bake a curves
  adjustment into a pixel layer. The cloud API preserves them.
- **`Select Subject` + `Select Sky` use Adobe Sensei** locally, no API
  call, no cost — they're bundled ML models.
- **Generative Fill in the GUI** uses the Firefly model under the hood;
  the cloud `/v3/images/fill-async` is the same engine.
- **`fontProperties` in batchPlay** can introspect every glyph run — text
  layers are surprisingly rich.
- **Layer comps + the API together** is the cleanest variant pattern: one
  PSD, N comps, render N PNGs from a single `/renditionCreate` per comp.

## Operational Behavior and Edge Cases

### GUI

- **Auto-save** writes a `.psd~` recovery file every N minutes (configurable
  in Preferences). Crash recovery uses these.
- **Scratch disk** — Photoshop spills to disk when RAM fills. If your
  scratch volume runs out, Photoshop locks up. Configure a fast SSD scratch
  in Preferences > Scratch Disks.
- **GPU acceleration** — required for many filters. Disable via Preferences
  > Performance if your GPU is unstable.
- **Font activation** — Adobe Fonts auto-activate when you open a PSD that
  uses them, IF you're signed in with internet. Offline → missing font
  warnings.

### UXP

- **Modal scope** is a hard contract; nothing in the JS sandbox can mutate
  the document outside it.
- **`localFileSystem` permissions** must be declared in manifest and
  consented to by the user at install time.
- **Console output** appears in the UDT (UXP Developer Tool) attached
  debugger. There is no Photoshop-side log file for plugin `console.log`.
- **Hot reload** in UDT lets you iterate without restarting Photoshop.

### Photoshop API

- **Job retention** — completed jobs are queryable for ~24h, then garbage
  collected. Pre-signed output URLs may expire sooner.
- **Concurrent jobs** — soft cap on concurrent jobs per technical account
  (~10-20 in practice). Excess queues server-side; doesn't 429.
- **Idempotency** — no idempotency key support. Re-POSTing the same body
  creates a new job. Caller must dedupe by content hash on its side.
- **Region** — `image.adobe.io` is global; underlying compute is
  multi-region. No region pinning available.

### Firefly API

- **Content credentials** — every Firefly-generated image gets C2PA content
  credentials baked into the file metadata. Stripping them is a TOS
  violation.
- **Determinism** — same prompt + same seed → same image, mostly. Small
  drift on model updates.
- **Style ref images** — uploaded reference images expire after a few
  hours. Re-upload if you reuse them.

## Ecosystem Position and Composition

Photoshop sits at the top of Adobe's raster stack. It composes with:

- **Lightroom (CC + Classic)** — raw-first cataloging. Same ACR engine.
  Lightroom API on Firefly Services is for raw workflows; Photoshop API is
  for layered editing.
- **Illustrator** — vector. AI files import into Photoshop as smart objects
  (preserving vector paths). Illustrator API also exists on Firefly Services.
- **InDesign** — page layout. Links to Photoshop files.
- **Bridge** — file browser, metadata, batch rename. The forgotten useful tool.
- **Adobe Camera Raw** — bundled raw processor, used by both PS and LR.
- **Adobe Stock** — licensed asset library, surfaces in Libraries panel.
- **Adobe Fonts** — typeface activation, surfaces via Creative Cloud desktop.
- **Adobe Express** — consumer-tier templated design. Different surface,
  some shared assets.
- **Firefly (web app)** — consumer Firefly UI. Same models as the API.

Outside Adobe:
- **Figma / Sketch** — vector design tools. PSD import via plugins, lossy.
- **Affinity Photo** — direct Photoshop competitor, opens PSDs natively.
- **GIMP / Krita** — open-source. Limited PSD compatibility.
- **ImageMagick / Pillow** — code-first raster, no layer awareness.
- **DALL-E / Midjourney / SD** — competing generative models. None offer
  the IP indemnification Firefly does.
- **Stability AI ControlNet** — finer control over generation; Firefly
  catching up via `style.imageReference` and `structure.imageReference`.

EOS uses Photoshop as the **canonical raster authoring + production
surface** because:
1. Antony already owns the desktop and uses it daily.
2. Firefly's IP indemnification matters for commercial work.
3. The Photoshop API is the only headless engine that understands PSDs.
4. Smart-object workflows are non-substitutable for apparel mockups.

## Trajectory and Evolution

Photoshop's roadmap (publicly stated by Adobe in 2024-2025):

- **UXP everywhere** — final removal of CEP and ExtendScript on a multi-year
  schedule. Build all new automation in UXP.
- **Generative models expanding** — Image Model 4 in development, video
  models (Firefly Video) shipping, structure/style references getting better.
- **Photoshop on the web (browser)** — already in beta, full UXP runtime
  in-browser, eventually equivalent to desktop.
- **iPad** — Photoshop iPad gets feature-parity steadily; UXP runs there.
- **Cloud documents** — `.psdc` format, real-time collab, version history.
  Currently supported in UXP and via the Cloud Documents endpoints.
- **Substance integration** — 3D material editing via Substance, surfacing
  in Photoshop's 3D tools (long-deprecated 3D layer system being rebuilt).
- **Content credentials enforcement** — C2PA metadata becoming default for
  all generative output.

What's NOT on the roadmap:
- ExtendScript revival.
- CEP feature work.
- A first-party Python SDK.
- Synchronous Photoshop API endpoints.
- Free-tier Firefly API usage at scale.

## Conceptual Model and Solution Recipes

### Recipe: brand mockup production line

```
1. GUI: Author the master mockup PSD. Smart object slot named "Artwork".
2. Commit master to /opt/OS/01_brand/photoshop/mockups/
3. Agent: For each SKU graphic in the catalog:
     a. Upload graphic to S3, get pre-signed GET URL.
     b. Generate pre-signed PUT URL for output PNG (content-hashed key).
     c. Check S3 for cached output; skip if hit.
     d. POST /smartObject with master + graphic + output URL.
     e. Poll job_url every 2s with exp backoff.
     f. On success: result is already at the PUT URL.
     g. On failure: log + write to dead-letter queue.
4. Publish all output URLs to the storefront.
```

Verification: agent compares the count of cataloged SKUs to the count of
output objects in S3. Mismatch = dead letters need attention.

### Recipe: AI-drafted hero images for blog posts

```
1. Agent reads blog post draft, extracts a visual concept prompt.
2. POST firefly-api /v3/images/generate-async with numVariations=4.
3. Poll until succeeded.
4. Store all 4 variations to S3.
5. Post to Discord with the 4 variations and a vote prompt.
6. After human pick: store the chosen variation as the canonical hero image.
7. Optional: drop into a branded template PSD via /documentOperations.
```

Verification: each post has a hero image; the hero image is the human-picked
variation, not the first.

### Recipe: in-app UXP panel for "apply EOS brand defaults"

```
1. UXP panel registers a button "Apply EOS Brand".
2. On click: executeAsModal wraps a sequence:
     a. createLayer for each brand element (background, gradient, lockup).
     b. batchPlay to set foreground color to the brand hex.
     c. Apply layer styles via batchPlay descriptors.
3. Panel shows a confirmation toast.
```

Verification: panel reload + click + visual confirmation that the layers
appear and match the brand palette.

### Recipe: bulk PSD-to-web conversion

```
1. Agent walks /opt/OS/01_brand/photoshop/ for all .psd files.
2. For each: upload to S3, POST /renditionCreate at width=1920 PNG, poll, download.
3. Convert to sRGB via /documentOperations convertToProfile before render.
4. Drop into the SaaS asset bucket.
```

## Industry Expert and Cutting-Edge Usage

What top Photoshop creators and Adobe engineering staff actually do that
casual users don't:

- **Action Manager scripting** — pre-UXP, pros wrote ScriptListener
  recordings as the source of truth for automation. Modern equivalent:
  recording in the GUI and copy-as-JS for batchPlay.
- **Smart object preview rendering** — for ultra-large linked smart
  objects, store a low-res preview alongside the link to keep the parent
  PSD responsive.
- **Bridge for metadata** — Adobe Bridge handles XMP/IPTC editing across
  thousands of files in ways the GUI can't.
- **Substance materials in 3D layers** — for mockups that need actual
  physical-based rendering, not just smart-object swap.
- **Custom Sensei training via Firefly Custom Models** — fine-tune a
  Firefly model on brand assets. Enterprise-only currently; would let EOS
  generate "in the Lyfe Spectrum house style" reliably.
- **C2PA content credentials inspection** — verify provenance of incoming
  assets via `verify.contentauthenticity.org` or the Content Credentials
  Chrome extension.
- **CEP-to-UXP migration plugins** — community tools like `CEP-to-UXP-Adapter`
  ease porting old plugins. The future is full UXP, but the migration is
  real work.
- **Photoshop scripts via the command line** — `photoshop -r script.jsx`
  on macOS is still supported for ExtendScript. UXP equivalent: launch
  Photoshop with a `.psjs` URI handler.
- **Headless Photoshop in CI** — run real Photoshop inside a macOS GitHub
  runner for parity tests. Slow but bit-for-bit accurate vs the cloud API.

---

# EOS Usage Patterns

## Pattern: Lyfe Spectrum mockup pipeline

The canonical "GUI authors, agents productionize" pattern.

```python
# eos_ai/lyfe_spectrum/mockup_pipeline.py (when written)
import os, time, hashlib, requests
from eos_ai.adobe import ims_token, adobe_request, sign_get, sign_put

def render_mockup(master_psd_s3_key: str, artwork_s3_key: str) -> str:
    """Render a mockup PSD with the artwork swapped into the smart object.
    Returns the S3 key of the rendered PNG. Cached by content hash."""
    h = hashlib.sha256(f"{master_psd_s3_key}|{artwork_s3_key}".encode()).hexdigest()[:16]
    output_key = f"renders/mockups/{h}.png"
    if s3_exists(output_key):
        return output_key
    headers = {
        "Authorization": f"Bearer {ims_token()}",
        "x-api-key": os.environ["ADOBE_IMS_CLIENT_ID"],
        "Content-Type": "application/json",
    }
    body = {
        "inputs":  [{"href": sign_get(master_psd_s3_key), "storage": "external"}],
        "options": {"layers": [{"name": "Artwork", "input": {
            "href": sign_get(artwork_s3_key), "storage": "external"}}]},
        "outputs": [{"href": sign_put(output_key), "storage": "external",
                     "type": "image/png"}],
    }
    r = adobe_request("POST",
        "https://image.adobe.io/pie/psdService/smartObject",
        json=body, headers=headers, timeout=30)
    job_url = r.json()["_links"]["self"]["href"]
    return _poll_until_done(job_url, headers, output_key)

def _poll_until_done(job_url, headers, output_key):
    delay = 2
    while True:
        s = adobe_request("GET", job_url, headers=headers, timeout=30).json()
        status = s["outputs"][0]["status"]
        if status == "succeeded": return output_key
        if status == "failed":    raise RuntimeError(s["outputs"][0]["errors"])
        time.sleep(delay)
        delay = min(delay * 1.5, 30)
```

## Pattern: Firefly draft hero image

```python
# eos_ai/content/hero_image.py (when written)
def draft_hero(prompt: str, n: int = 4) -> list[str]:
    headers = _adobe_headers()
    r = adobe_request("POST",
        "https://firefly-api.adobe.io/v3/images/generate-async",
        headers=headers, timeout=30,
        json={"prompt": prompt, "numVariations": n,
              "size": {"width": 2048, "height": 2048},
              "contentClass": "photo"})
    poll = r.json()["statusUrl"]
    while True:
        s = adobe_request("GET", poll, headers=headers).json()
        if s["status"] == "succeeded":
            return [o["image"]["url"] for o in s["result"]["outputs"]]
        if s["status"] == "failed":
            raise RuntimeError(s.get("error"))
        time.sleep(2)
```

## Pattern: UXP `.psjs` for batch local processing

```javascript
// brand_batch.psjs — drop on Photoshop or run from File > Scripts
const { app, core, action } = require("photoshop");
const fs = require("uxp").storage.localFileSystem;

(async () => {
  const folder = await fs.getFolder();  // user picks
  const entries = await folder.getEntries();
  for (const entry of entries) {
    if (!entry.name.endsWith(".psd")) continue;
    const doc = await app.open(entry);
    await core.executeAsModal(async () => {
      // Apply EOS brand defaults via batchPlay descriptors
      await action.batchPlay([
        {_obj: "convertMode", to: {_class: "RGBColorMode"}},
      ], {});
      await doc.flatten();
      await doc.saveAs.png(await folder.createFile(entry.name + ".png"));
    }, {commandName: "EOS brand batch"});
    await doc.closeWithoutSaving();
  }
})();
```

## Pattern: cached IMS token helper

```python
# eos_ai/adobe.py (when written)
import os, time, requests, threading

_lock = threading.Lock()
_token_cache = {"value": None, "expires_at": 0}

def ims_token() -> str:
    with _lock:
        if _token_cache["value"] and time.time() < _token_cache["expires_at"] - 60:
            return _token_cache["value"]
        r = requests.post(
            "https://ims-na1.adobelogin.com/ims/token/v3",
            data={
                "grant_type": "client_credentials",
                "client_id": os.environ["ADOBE_IMS_CLIENT_ID"],
                "client_secret": os.environ["ADOBE_IMS_CLIENT_SECRET"],
                "scope": os.environ["ADOBE_FIREFLY_SCOPES"],
            },
            timeout=30,
        )
        r.raise_for_status()
        j = r.json()
        _token_cache["value"] = j["access_token"]
        _token_cache["expires_at"] = time.time() + int(j["expires_in"])
        return _token_cache["value"]
```

## Pattern: cost guard before batch loops

Before any batch that could spend significant API quota, agents emit:

```
PHOTOSHOP API BATCH PROPOSAL
  endpoint: /smartObject
  count:    1240 calls
  est cost: ~ X transactions
  source:   /opt/OS/01_brand/photoshop/lyfe_spectrum/spring26.psd
  cache:    980 already cached, 260 fresh
  proceed?: y/n
```

Antony confirms or cancels. No agent writes to a paid endpoint in a tight
loop without this guard.

---

## Gotchas

This is the canonical failure catalog. Add to it as new failures occur.

- **ExtendScript is dead but not removed.** `.jsx` files still execute,
  which means new code can quietly land in the wrong surface. Lint for
  `.jsx` in repos and reject in PRs.
- **`batchPlay` outside `executeAsModal`** → `Error: not in a modal scope`.
  ALWAYS wrap mutations.
- **`batchPlay` selector by name** when an `_id` is available → silent
  selection of the wrong layer when names collide across groups. Prefer
  `_id`. Get ids from `app.activeDocument.layers[i].id`.
- **Photoshop API multipart upload** → 415. There is no multipart endpoint.
  Use pre-signed URLs.
- **Pre-signed URL expired mid-job** → `OutputUploadError` after the work
  completed. Generate URLs with TTL >> expected job duration.
- **Polling at 100 ms** → wastes API calls and trips secondary rate limits.
  Start at 2s, exp backoff to 30s.
- **`firefly_api` scope but not `ff_apis`** → 403 on Photoshop API even
  though Firefly works. Always request both.
- **Skipping `x-api-key` header** → 403 with a confusing error. Both
  headers are mandatory.
- **Per-request IMS token mint** → trips IMS rate limits and doubles
  every API call's latency. Cache the token for 24h.
- **Color profile not converted to sRGB** before web render → desaturated
  IG/Discord previews. `convertToProfile` first.
- **Smart object replacement with wrong aspect ratio** → silent distortion
  that looks "almost right." Pre-validate aspect ratios in the agent.
- **Missing fonts in cloud render** → silent substitution unless
  `manageMissingFonts: "fail"`. Either subset/embed or supply via the
  `fonts` option.
- **Linked smart objects with paths the cloud can't reach** → render
  fails. Convert to embedded before uploading the master to cloud.
- **PSB > 2 GiB** → `InputValidationError`. Split into linked smart objects
  or downsize.
- **`flatten()` before saving as PSD** → destroys layer structure. Only
  flatten before exporting raster, never on the master.
- **`closeWithoutSaving` forgotten in UXP batch loops** → memory grows
  unbounded as documents accumulate.
- **`localFileSystem` permission not declared in manifest** → file picker
  works but read/write throws `permission denied`.
- **Network domain not declared in manifest `requiredPermissions`** →
  fetch silently fails with no console error. Add the host explicitly.
- **`historyStates` set too high** → memory blowout. Cap at 100 for normal
  work, 1000 only on machines with 64+ GiB.
- **GPU disabled but expected** → many filters slow to a crawl. Verify GPU
  in Preferences > Performance.
- **Adobe Fonts not activated** → opening a PSD silently substitutes.
  Sign in to Creative Cloud first.
- **Per-output `status: partial`** in API responses → some outputs
  succeeded, some failed. Don't treat the job as done; iterate per output.
- **Treating `_links.self.href` as opaque** → it's a normal HTTPS URL,
  GET it with the same headers as the original POST.
- **Action droplets on Apple Silicon** → some old droplets crash because
  they're 32-bit. Re-record under Photoshop 2025.
- **Cloud documents (`.psdc`) and Photoshop API** → not all endpoints
  support cloud documents. Stick to `.psd`/`.psb` from external storage
  for cloud edits.
- **Camera Raw smart filter via batchPlay** → descriptor is undocumented;
  copy from a recorded action and treat as opaque blob.
- **Firefly content credentials stripping** → TOS violation. Don't.
- **`numVariations: 4` × parallel calls** → quota burns very fast in dev.
  Start with `numVariations: 1` while iterating.
- **Reusing pre-signed PUT URLs across jobs** → second job overwrites the
  first. Generate fresh URLs per job.
- **UXP `console.log` invisible** → only the UDT debugger sees it. Open
  UDT and "Debug" the plugin to see logs.
- **GUI scratch disk full** → Photoshop locks up with "Could not complete
  your request because the scratch disks are full." Clear or add a disk.
- **`new Error()` thrown inside `executeAsModal` callback** → Photoshop
  rolls back the entire modal block. Use this for transactional safety,
  but expect the doc state to revert.
- **Saving over the master PSD from cloud output** → destroys human
  authoring work. Treat masters as immutable; cloud writes go to a
  derived path.
- **`batchPlay` array of 1000+ descriptors** → Photoshop main thread
  freezes. Chunk into smaller batches and yield with `await` between.
- **`app.documents` mutated during iteration** → indices shift. Iterate
  by id snapshot first, then operate.
- **Photoshop 2025 manifest v5 plugin loaded in older Photoshop** → silent
  refusal to load. Set `host.minVersion` correctly.
- **Anti-pattern: API in user-facing real-time path** — generations are
  5-30s. Always queue and notify, never block a request thread.

End of best_practices.md.
