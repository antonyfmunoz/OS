# Lightroom — Creator-Level Best Practices
Source: helpx.adobe.com/lightroom-classic, helpx.adobe.com/lightroom, developer.adobe.com/firefly-services/docs/lightroom, lightroomqueen.com, mastering-lightroom.com, Adobe Camera Raw release notes
API Version: Lightroom Classic 14.4 (June 2025) / Lightroom (cloud) 8.4 / Adobe Camera Raw 17.x / Firefly Services Lightroom API v1
SDK Version: firefly-services-sdk-js lightroom 1.x (official JS), Python via raw HTTP
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

There are two completely separate auth surfaces, and confusing them is the
first failure mode.

**Desktop apps (Lightroom Classic, Lightroom CC).** Authentication is the
Adobe ID session held by the Creative Cloud desktop app. There is no per-call
token, no API key, no OAuth flow you ever see. The Lightroom binary launches,
checks Creative Cloud's local session, validates the seat against Adobe's
licensing servers, and you're in. License is per-seat, tied to an Adobe ID,
two activations max per seat. The catalog file (`.lrcat`) is just a SQLite
database on disk — no auth on the file itself. Anyone who can read the file
can open it. Treat catalogs as sensitive data because they contain develop
history, keywords, GPS, and previews of every photo you've ever imported.

**Lightroom API (Firefly Services).** Server-to-server OAuth 2.0 against
Adobe IMS. The flow:

1. Provision a project in Adobe Developer Console
   (`developer.adobe.com/console`)
2. Add the Firefly Services API to the project
3. Generate a server-to-server credential — you get `client_id` (a.k.a.
   `x-api-key`), `client_secret`, and a list of granted scopes
4. Exchange those for a bearer token at
   `https://ims-na1.adobelogin.com/ims/token/v3`
5. Cache the token (~24h lifetime); refresh on 401
6. Send `Authorization: Bearer <token>` AND `x-api-key: <client_id>` on
   every Lightroom API call

```bash
curl -X POST https://ims-na1.adobelogin.com/ims/token/v3 \
  -d "grant_type=client_credentials" \
  -d "client_id=$ADOBE_CLIENT_ID" \
  -d "client_secret=$ADOBE_CLIENT_SECRET" \
  -d "scope=openid,AdobeID,read_organizations,firefly_api,ff_apis"
# Response: { "access_token": "...", "token_type": "bearer", "expires_in": 86399 }
```

The required scope set for Lightroom endpoints is currently
`openid,AdobeID,read_organizations,firefly_api,ff_apis`. Adobe has changed
the exact scope strings several times — re-check the Firefly Services docs
quarterly.

Beyond the bearer + key, Lightroom API also requires that input and output
images live on cloud storage you control. Currently supported: Amazon S3,
Azure Blob Storage, Dropbox. You pass presigned URLs in the request body;
the API never sees your storage credentials. Practical implication: every
EOS Lightroom API call needs a presigned-URL minter on the input side and
a presigned-URL minter on the output side, both before the call.

EOS rules: never commit `client_secret`. Live in `eos_ai/.env` as
`ADOBE_CLIENT_ID` / `ADOBE_CLIENT_SECRET`. Token cache in
`eos_ai/.adobe_token_cache.json` (gitignored), regenerate on 401.

## Core Operations with Exact Signatures

Lightroom has three command surfaces. Treat them as three different APIs that
happen to share an editing engine.

### Surface 1 — Lightroom Classic (desktop, GUI + plugin SDK)

There is no shell command for "open this catalog and apply this preset to
this image." The Classic command surface is:

- **The GUI itself** — keyboard shortcuts and menu items
- **The Lightroom SDK** for plugins (Lua, lives in `LightroomSDK/` inside
  the install). Plugins can implement Export, Publish, Metadata, Develop
  preset import, and certain dialogs. They cannot drive the Develop module
  pixel-by-pixel.
- **AppleScript / VBScript** on macOS / Windows for very limited automation
  (open catalog, import, export — basically what's exposed via menu)
- **XMP files on disk** — if you write the right XMP next to a raw, Lightroom
  will pick it up on next read

The practical "API" for Lightroom Classic from an external automator is:
write XMP sidecars and let LrC sync from XMP. That's the extent of headless
control without using the cloud API.

Catalog file shape:

```
MyShoot.lrcat                              SQLite database (the catalog)
MyShoot.lrcat-shm / .lrcat-wal             SQLite WAL files
MyShoot Previews.lrdata/                   regular previews bundle
MyShoot Smart Previews.lrdata/             smart previews bundle (~2540px DNG)
MyShoot Helper.lrdata/                     transient helper data
Backups/2026-04-06 0930/MyShoot.lrcat.zip  backup snapshots
```

Important catalog tables (read-only with `sqlite3`):

```
AgLibraryFile                file path, basename, extension
AgLibraryFolder              folder hierarchy, root volume
Adobe_images                 image rows, captureTime, ratings, color label
Adobe_imageDevelopSettings   the develop XMP, per image (BLOB)
AgLibraryKeyword             keyword tree
AgLibraryKeywordImage        many-to-many tagging
AgLibraryCollection          collections (manual)
AgLibraryCollectionStack     collection contents
```

NEVER write to the catalog while Lightroom has it open. NEVER write to it at
all if you can avoid it. Read with `sqlite3 -readonly`.

### Surface 2 — Lightroom (Cloud / CC)

Cloud Lightroom has two API faces:

1. The same Firefly Services Lightroom API (REST, see below). When you push
   to your Lightroom cloud library you can render through the API.
2. The older, less documented Lightroom Services API (`lr.adobe.io`) used by
   the Lightroom mobile/web apps internally. Officially undocumented for
   third parties. Don't build on it.

For agents, Surface 2 = Surface 3.

### Surface 3 — Firefly Services Lightroom API (REST)

Base host: `https://image.adobe.io/lrService/`

```
POST /presets         apply one or more stored XMP presets to an image
POST /xmp             apply inline XMP to an image
POST /edit            apply explicit develop adjustments (non-XMP JSON form)
POST /autoTone        run auto tone
POST /autoStraighten  run auto straighten
GET  /{jobId}         poll job status
```

All endpoints follow the same async pattern:

1. POST returns `202 Accepted` with a job URL in the `Location` header and
   `{"_links":{"self":{"href":"..."}}}` in the body
2. GET the job URL until `status` is `succeeded` or `failed`
3. On success, the rendered output is at the presigned output URL you supplied

Request body shape (canonical):

```json
{
  "inputs": {
    "source": { "href": "<presigned-in>", "storage": "external" }
  },
  "options": {
    "presets": [
      { "href": "<presigned-preset>", "storage": "external" }
    ]
  },
  "outputs": [
    {
      "href": "<presigned-out>",
      "storage": "external",
      "type": "image/jpeg",
      "overwrite": true
    }
  ]
}
```

Storage values: `external` (presigned URL — most common), `adobe` (cloud
content from a Creative Cloud Assets reference), `aws-s3`, `azure`, `dropbox`
(when using direct credential modes).

Output types: `image/jpeg`, `image/tiff`, `image/png`, `image/x-adobe-dng`.

`/edit` endpoint develop fields (subset; the full surface mirrors the Camera
Raw XMP field names without the `crs:` prefix):

```json
{
  "inputs":  { "source": { "href": "...", "storage": "external" } },
  "options": {
    "Exposure": -0.30,
    "Contrast": 12,
    "Highlights": -45,
    "Shadows": 30,
    "Whites": -10,
    "Blacks": -25,
    "Texture": 0,
    "Clarity": 8,
    "Dehaze": 0,
    "Vibrance": 8,
    "Saturation": -5,
    "Temperature": 5200,
    "Tint": 5,
    "Sharpness": 40,
    "LuminanceSmoothing": 0,
    "ColorNoiseReduction": 25
  },
  "outputs": [ { "href": "...", "storage": "external", "type": "image/jpeg" } ]
}
```

Worked examples (EOS-flavored):

```bash
# Get token, cache it
TOKEN=$(./scripts/get_adobe_token.sh)

# Apply a hero preset and export 2048px JPEG sRGB
curl -sS -X POST https://image.adobe.io/lrService/presets \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-api-key: $ADOBE_CLIENT_ID" \
  -H "Content-Type: application/json" \
  -d @hero_apply_request.json \
  | tee /tmp/lr-job.json

JOB_URL=$(jq -r '._links.self.href' /tmp/lr-job.json)

# Poll
while true; do
  STATUS=$(curl -sS -H "Authorization: Bearer $TOKEN" \
                    -H "x-api-key: $ADOBE_CLIENT_ID" \
                    "$JOB_URL" | jq -r .status)
  echo "status=$STATUS"
  case "$STATUS" in
    succeeded) break ;;
    failed)    exit 1 ;;
  esac
  sleep 3
done
```

## Pagination Patterns

The Lightroom API does not return collections — every endpoint operates on a
single input image and produces one or more output renditions. There is
nothing to paginate. The closest concept is fan-out: to process N images you
issue N independent jobs and poll them in parallel. There is no batch endpoint.

Lightroom Classic catalogs are not paginated either — they are queried by
filtering the library view. SQL queries against the catalog return all rows.
Smart Collections support a rule-based filter language but not pagination per
se; the result is materialized lazily as you scroll.

Practical EOS pattern for "process 200 product shots":

```python
import concurrent.futures, requests, time

def process_one(presigned_in, presigned_out, preset_url, token, key):
    body = {
        "inputs":  {"source": {"href": presigned_in, "storage": "external"}},
        "options": {"presets": [{"href": preset_url, "storage": "external"}]},
        "outputs": [{"href": presigned_out, "storage": "external",
                     "type": "image/jpeg", "overwrite": True}],
    }
    r = requests.post("https://image.adobe.io/lrService/presets",
                      headers={"Authorization": f"Bearer {token}", "x-api-key": key},
                      json=body, timeout=30)
    r.raise_for_status()
    job = r.json()["_links"]["self"]["href"]
    while True:
        s = requests.get(job, headers={"Authorization": f"Bearer {token}",
                                       "x-api-key": key}, timeout=30).json()
        if s["status"] in ("succeeded", "failed"):
            return s
        time.sleep(2)

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(lambda t: process_one(*t), tasks))
```

## Rate Limits

Adobe publishes Firefly Services rate limits as **per-organization** quotas.
As of April 2026 the published defaults for Lightroom API are:

- **Burst rate**: ~25 requests / second per org
- **Sustained rate**: ~10 requests / second per org sustained over a minute
- **Concurrent jobs**: ~25 in-flight jobs per org by default
- **Daily render quota**: tier-dependent, paid tier starts in the low
  thousands per day, scales with contract

Going over yields `429 Too Many Requests` with a `Retry-After` header
(seconds). Implement exponential backoff capped at the `Retry-After` value.

There is no per-call cost on Adobe IMS token endpoint; cache and reuse.

For Lightroom Classic the only "rate limit" is local CPU/GPU and storage IO.
AI Denoise on a current GPU runs ~2–10 seconds per 24MP raw; without GPU
acceleration it can hit 30–90 seconds.

## Error Codes and Recovery

Lightroom API uses standard HTTP. Common failures:

| HTTP | Body code | Cause | Recovery |
|---|---|---|---|
| 400 | `bad_request` | malformed JSON, unknown field, missing presigned URL | log body, fix request, do NOT retry |
| 401 | `unauthorized` | token expired or scope missing | refresh token, retry once |
| 403 | `forbidden` | org lacks Firefly Services entitlement, or input URL not accessible | check entitlement, re-mint presigned URL |
| 404 | `not_found` | bad job ID, deleted preset href | stop polling, fail job |
| 409 | `conflict` | output already exists and `overwrite:false` | flip overwrite or pick new path |
| 413 | `payload_too_large` | input image exceeds size cap (~70 MP / ~200 MB depending on tier) | downsample or split |
| 415 | `unsupported_media_type` | input format not supported (proprietary raw without recent ACR support) | convert to DNG first |
| 429 | `rate_limited` | burst or sustained limit | exponential backoff using `Retry-After` |
| 500 | `internal_error` | transient | retry with backoff up to 3x |
| 503 | `service_unavailable` | Adobe-side outage | check status.adobe.com, retry slowly |

Job-level statuses:

```
status: "running"    | wait
status: "succeeded"  | output is at presigned URL
status: "failed"     | inspect "errors" array, do not retry generic failures
```

Recovery recipe for a stuck pipeline:

```bash
# 1. Refresh token
rm eos_ai/.adobe_token_cache.json && ./scripts/get_adobe_token.sh

# 2. Re-mint presigned URLs (they expire — usually 15min default)
python3 scripts/mint_lightroom_urls.py --shoot 2026-04-06

# 3. Resume failed jobs from the manifest
python3 scripts/lightroom_resume.py --shoot 2026-04-06 --only failed
```

For Lightroom Classic, errors are surfaced in the `Library > Catalog` view
or as warning dialogs. The catalog logs to
`%APPDATA%\Adobe\Lightroom\Logs\` on Windows and
`~/Library/Logs/Adobe/Lightroom/` on macOS. Useful files: `Lightroom.log`,
`LrcCatalogMaintenance.log`, `Lightroom Classic Latest Crash.log`.

## SDK Idioms

Adobe ships an official Firefly Services SDK for Node.js
(`@adobe/firefly-services-sdk-js`) that includes a Lightroom client. There
is no first-party Python SDK as of April 2026 — Python users hit the REST
endpoints directly via `requests` or `httpx`.

### Node SDK idiom

```js
import { LightroomClient, ServerToServerAuth } from "@adobe/firefly-services-sdk-js/lightroom";

const auth = new ServerToServerAuth({
  clientId: process.env.ADOBE_CLIENT_ID,
  clientSecret: process.env.ADOBE_CLIENT_SECRET,
  scopes: ["openid", "AdobeID", "read_organizations", "firefly_api", "ff_apis"],
});
const lr = new LightroomClient({ auth });

const job = await lr.applyPresets({
  inputs:  { source: { href: presignedIn,  storage: "external" } },
  options: { presets: [{ href: presetHref, storage: "external" }] },
  outputs: [{ href: presignedOut, storage: "external", type: "image/jpeg", overwrite: true }],
});
const result = await job.waitForCompletion();   // built-in polling
```

The SDK handles token caching, polling, and exponential backoff. Prefer it
over raw HTTP unless you need to embed in a non-Node service.

### Python idiom (REST + helper class)

```python
import os, time, requests

class LightroomClient:
    def __init__(self):
        self.client_id = os.environ["ADOBE_CLIENT_ID"]
        self.secret    = os.environ["ADOBE_CLIENT_SECRET"]
        self._token    = None
        self._exp      = 0

    def _ensure_token(self):
        if self._token and time.time() < self._exp - 60:
            return
        r = requests.post(
            "https://ims-na1.adobelogin.com/ims/token/v3",
            data={
                "grant_type": "client_credentials",
                "client_id":  self.client_id,
                "client_secret": self.secret,
                "scope": "openid,AdobeID,read_organizations,firefly_api,ff_apis",
            }, timeout=15,
        )
        r.raise_for_status()
        d = r.json()
        self._token = d["access_token"]
        self._exp   = time.time() + d["expires_in"]

    def _headers(self):
        self._ensure_token()
        return {"Authorization": f"Bearer {self._token}",
                "x-api-key": self.client_id}

    def apply_preset(self, src_url, preset_url, out_url, mime="image/jpeg"):
        body = {
            "inputs":  {"source": {"href": src_url, "storage": "external"}},
            "options": {"presets": [{"href": preset_url, "storage": "external"}]},
            "outputs": [{"href": out_url, "storage": "external",
                         "type": mime, "overwrite": True}],
        }
        r = requests.post("https://image.adobe.io/lrService/presets",
                          headers={**self._headers(), "Content-Type": "application/json"},
                          json=body, timeout=30)
        r.raise_for_status()
        job_url = r.json()["_links"]["self"]["href"]
        while True:
            s = requests.get(job_url, headers=self._headers(), timeout=30).json()
            if s["status"] == "succeeded": return s
            if s["status"] == "failed":    raise RuntimeError(s.get("errors"))
            time.sleep(2)
```

Idiomatic rules:

1. Cache the IMS token. Refresh only on expiry or 401.
2. Always use presigned URLs with at least 30-minute lifetimes — Lightroom
   API jobs sometimes take >10 minutes for huge raws or AI ops.
3. Validate XMP locally before sending. Malformed XMP returns 400 with a
   useless "internal_error" sometimes; better to catch it upstream.
4. Treat the API as stateless. Persist your manifest of `(input → preset →
   output → job_id → status)` separately. Lightroom API has no list-jobs
   endpoint that lets you discover what you ran yesterday.
5. For Classic-side automation, write XMP, never poke the catalog. The
   catalog is a SQLite file with internal invariants; corrupting it is
   trivial and irreversible.

## Anti-Patterns

1. **Editing files in Finder/Explorer while LrC is open.** Renaming, moving,
   or deleting a file outside Lightroom orphans it in the catalog. Always
   rename/move from inside Library.
2. **Deleting the catalog "to clean up."** The catalog IS your edits. Deleting
   it deletes every adjustment, keyword, collection, history step, and flag.
   If you need a fresh catalog, export selected images as a new catalog first.
3. **Trusting smart previews to be read-only.** Edits made on smart previews
   when originals are offline DO apply to originals on next reconnect. Plan
   for it.
4. **Using JPEG as the master.** Lightroom can edit JPEG, but you lose 90% of
   the develop range. Always shoot raw, always master from raw, export JPEG
   only for delivery.
5. **Synchronizing develop settings indiscriminately.** `Sync Settings` will
   happily sync white balance from a tungsten interior to a daylight
   exterior. Use it on visually similar groups only.
6. **Importing 100k+ photos into one catalog.** Catalogs scale to ~250k
   without pain and several million with care, but a single mega-catalog is
   slow to back up, slow to optimize, slow to open, and a single point of
   failure. Split by project or year.
7. **Skipping `Optimize Catalog`.** SQLite WAL files balloon. Run File >
   Optimize Catalog weekly on heavy catalogs; expect 20–60% size reduction.
8. **AI Denoise as a default on every image.** Denoise is computationally
   expensive and on clean low-ISO files it removes detail. Apply to high-ISO
   only (typically ISO 3200+).
9. **AI Denoise AFTER masking.** Masks were drawn against grain that no
   longer exists post-denoise; some masks shift. Denoise first, mask second.
10. **Develop preset libraries with thousands of unused presets.** The Develop
    module renders a thumbnail per visible preset on every image change. Past
    ~2000 presets the panel becomes laggy. Hide groups you don't use.
11. **Trusting "Auto" white balance for product shots.** Lyfe Spectrum apparel
    needs known WB (custom Kelvin or click on a known neutral). Auto WB shifts
    between similar shots and breaks ecommerce color accuracy.
12. **Calling Lightroom API with raw bytes uploaded inline.** There is no
    inline-bytes mode. Always presigned URL. Period.
13. **Polling Lightroom API jobs faster than 1Hz.** Adds zero latency
    benefit, burns rate limit. 2–3 seconds is fine.
14. **Treating Classic and Cloud as the same product.** Workflows, file
    layout, sync model, plugin support all differ. Pick one as primary.

## Data Model

Three data models, one per surface.

### Lightroom Classic — catalog (`.lrcat`)

A SQLite database. The hierarchy:

```
Catalog
├── Folders            mirror of disk filesystem (root volumes → folders → subfolders)
│   └── Files          one row per file on disk
│       └── Image      one row per "image" (a file may have multiple virtual copies)
│           ├── Develop history       ordered list of edit steps
│           ├── Develop settings      current XMP-equivalent develop state
│           ├── Metadata              EXIF, IPTC, custom
│           ├── Keywords              many-to-many
│           ├── Ratings, flags, color labels
│           └── History snapshots
├── Collections        virtual groupings (independent of folder structure)
│   ├── Manual collections
│   ├── Smart collections (rule-based)
│   └── Collection sets (folders of collections)
├── Keywords           tree, with synonyms and export rules
├── Publish services   external destinations (Flickr, Smugmug, hard drive)
├── Develop presets    per-user, in app data dir
├── Camera profiles    DCP profiles, per-camera
├── Lens profiles      per-lens correction data
└── Previews / Smart Previews   separate .lrdata bundles
```

ID stability: catalog row IDs are stable as long as the catalog file is. They
do not survive an "Export as Catalog" round-trip — new catalog, new IDs.

Virtual copies: a single physical file can have N "virtual copies" in the
catalog, each with its own develop settings. They share the original raw.

### Lightroom Cloud — Adobe cloud document graph

```
Account
└── Library            single global library per account
    ├── Albums         the cloud equivalent of collections
    │   └── Album sets nested grouping
    ├── People         face-based grouping (ML)
    └── Photos         every photo, with cloud-side develop state
        ├── Edits      per-version develop deltas
        ├── Versions   named snapshots
        └── Metadata
```

No folders. There is no notion of disk path because there is no disk
authority — the cloud is the truth. Local devices cache subsets.

### Firefly Services Lightroom API — request/response model

Stateless. Each call is `(inputs, options, outputs) → job → polled → done`.
There is no library, no catalog, no persistent objects between calls. The
only persisted thing is the rendered output you wrote to your own storage.

### Develop XMP namespace (`crs:`)

The Camera Raw XMP namespace is the lingua franca across all three surfaces.
Selected fields:

```
crs:Version                17.0 (current process version)
crs:ProcessVersion         11.0 (PV2012-modern)
crs:WhiteBalance           As Shot|Auto|Daylight|Cloudy|...|Custom
crs:Temperature            Kelvin
crs:Tint                   -150..+150
crs:Exposure2012           -5.0..+5.0 EV
crs:Contrast2012           -100..+100
crs:Highlights2012         -100..+100
crs:Shadows2012            -100..+100
crs:Whites2012             -100..+100
crs:Blacks2012             -100..+100
crs:Texture                -100..+100
crs:Clarity2012            -100..+100
crs:Dehaze                 -100..+100
crs:Vibrance               -100..+100
crs:Saturation             -100..+100
crs:ParametricShadows      tone curve regions
crs:ParametricDarks
crs:ParametricLights
crs:ParametricHighlights
crs:HueAdjustmentRed       HSL per color (Red/Orange/Yellow/Green/Aqua/Blue/Purple/Magenta)
crs:SaturationAdjustmentRed
crs:LuminanceAdjustmentRed
crs:SharpenRadius
crs:SharpenDetail
crs:SharpenEdgeMasking
crs:LuminanceSmoothing     legacy luminance NR
crs:LuminanceNoiseReductionDetail
crs:ColorNoiseReduction
crs:GrainAmount
crs:CropTop / CropLeft / CropBottom / CropRight / CropAngle
crs:LensProfileEnable
crs:RemoveChromaticAberration
crs:DefringePurpleAmount
crs:MaskGroupBasedCorrections   modern mask groups (Subject, Sky, etc.)
```

A develop preset is a `.xmp` file containing exactly these fields. Agents
generating presets need to emit valid XMP wrapped in `<x:xmpmeta>` and
`<rdf:RDF>`. Use a known-good preset as a template — never hand-construct
the XML envelope from scratch.

## Webhooks and Events

Lightroom Classic has no event/webhook system reachable from outside the
process. Inside the SDK Lua plugin host, there are observers for catalog
changes (`LrCatalog.addObserver`), import events, and metadata changes — but
these only fire inside a running plugin context inside LrC.

Lightroom Cloud likewise has no public webhooks for develop events.

Firefly Services Lightroom API has no webhook delivery — it is purely
poll-based. To get "tell me when the job is done," you poll the job URL.
For high-volume EOS use, the right pattern is a job-tracker process that
polls a batch of in-flight jobs every 2–5 seconds and reports completions
into a queue your downstream consumers tail.

The closest thing to an event surface for Classic is **XMP sidecar
modification time**. If you write XMP next to raw files and an external
process tails the directory with `inotifywait` (Linux) or `fswatch`
(macOS), you get a poor-man's "develop changed" signal — useful for sync
pipelines that propagate Antony's edits from his Windows workstation to
the VPS. Pair with the catalog's "Automatically write changes into XMP"
preference enabled.

## Limits

| Surface | Limit | Value | Notes |
|---|---|---|---|
| Classic catalog | max images | ~6 million tested | painful past 1M, split by project |
| Classic catalog | max keywords | unlimited in practice | UI degrades past ~100k |
| Classic catalog | max smart collections | unlimited | rule eval cost adds up |
| Classic | preview size | 2880px long edge max for 1:1 previews | configurable in Catalog Settings |
| Classic | smart preview size | 2540px long edge fixed | not configurable |
| Classic | history steps per image | unlimited | adds DB size, can clear |
| Classic | virtual copies per master | unlimited | each is a row |
| Classic | undo depth | ~50 actions | session-bound |
| Cloud | originals storage | bound by CC plan | typically 1TB or 20GB |
| Cloud | photo count | bound by storage | no count cap |
| Cloud | albums | unlimited | UI ok up to thousands |
| API | input file size | ~200 MB / ~70 MP typical | tier-dependent, 415/413 above |
| API | job lifetime | jobs purged after ~24h | poll URL stops working |
| API | presigned URL lifetime | you control | mint with 30+ min for safety |
| API | concurrent jobs/org | ~25 default | higher tiers raise this |
| API | sustained rate | ~10 req/s/org | 429 above |
| API | burst rate | ~25 req/s/org | use Retry-After |

Develop module specifics:

- Tone curve: 32 control points max
- HSL: 8 color channels (Red, Orange, Yellow, Green, Aqua, Blue, Purple, Magenta)
- Masks: no documented hard cap; UI starts to slow past ~50 mask groups per image
- Crop: 1px minimum, no max (output resolution capped at master resolution)

## Cost Model

**Lightroom Classic / CC subscription.** Adobe Photography Plan:

- Photography Plan 20GB: $9.99/month (LrC + Lr + Photoshop, 20GB cloud)
- Photography Plan 1TB: $19.99/month (LrC + Lr + Photoshop, 1TB cloud)
- Lightroom Plan: $9.99/month (Lr only, 1TB cloud — no Classic, no Photoshop)

For EOS the Photography Plan 1TB is the right tier — Antony needs Classic
locally and 1TB to be the buffer for client cloud sync. Cost is fixed
monthly, not per-image.

**Firefly Services Lightroom API.** Token-based pricing under the Firefly
Services umbrella, billed per generative credit or per API call depending
on operation:

- `/presets`, `/xmp`, `/edit`, `/autoTone`, `/autoStraighten`: typically
  consume **non-generative API credits** at a low rate (fractional credits
  per call) — these are cheap, sometimes free under entitlement bundles
- AI Denoise via API and any generative-fill style operation consume
  **generative credits** at a higher rate

Adobe pricing changes frequently. As of April 2026, server-to-server
Firefly Services starts around $1,200/year for the lowest enterprise tier
with a few thousand credits/month included; pay-as-you-go credit packs are
also offered. Verify current pricing at
`developer.adobe.com/firefly-services/docs/guides/pricing/` before budgeting.

EOS budget rule: the API is for headless batches that justify their cost.
Single-image experiments belong in Classic. Quote a per-batch cost before
running anything over 50 images.

**Storage cost.** Presigned-URL storage (S3 etc.) is your line item, not
Adobe's. Plan: keep raws in cold storage (Glacier/Deep Archive), promote to
S3 Standard for the duration of a render batch, then back to cold.

## Version Pinning

Check version: `Help > System Info` (in either app), or examine the install
folder. Adobe ships major releases roughly twice a year with monthly bug-fix
releases via Creative Cloud.

Current stable as of April 2026:

- **Lightroom Classic 14.4** (June 2025) — non-destructive Denoise
- **Lightroom Classic 14.5–14.6** monthly point releases since
- **Lightroom (Cloud) 8.4** (June 2025) and subsequent
- **Adobe Camera Raw 17.x** (matches LrC develop engine)
- **Firefly Services Lightroom API v1** — stable since 2024 GA

Important version-gated features:

- **Non-destructive AI Denoise** — Lightroom Classic 14.4+ (June 2025).
  Earlier versions create a DNG copy.
- **AI Masking — Select People with body-part subselects** — LrC 12.0+
- **AI Masking — Select Objects (brush prompted)** — LrC 13.0+
- **Generative Remove (cloud-assisted)** — LrC 13.3+ (May 2024)
- **Adaptive Profile** — LrC 14.0+
- **Process Version 6** (current) — LrC 14.0+; older catalogs auto-upgrade
- **Lightroom API `/presets` endpoint** — Firefly Services GA, March 2024
- **Lightroom API `/xmp` inline endpoint** — added late 2024
- **Catalog backup panel improvements** — LrC 14.4+

Pinning strategy for EOS:

- Pin LrC version expectation at >= 14.4 for non-destructive Denoise. If
  Antony's workstation lags behind, agents must NOT auto-Denoise without
  warning about DNG bloat.
- Pin Firefly Services Lightroom API at v1, base host
  `image.adobe.io/lrService/`. Adobe has not signaled a v2.
- Never assume that a develop preset created in LrC 14.x will look identical
  to one applied via the API at the same point in time — process version,
  profile availability, and engine point releases can drift. Always test a
  spot-check render and visually compare before bulk runs.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Lightroom started in 2007 inside Adobe's Pixel Mafia (Mark Hamburg, Thomas
Knoll's circle) as a deliberate counter to Adobe Bridge + Camera Raw +
Photoshop being the wrong shape for working photographers. Bridge was a file
browser. Camera Raw was a one-image-at-a-time dialog. Photoshop was a
pixel-pushing tool. Photographers wanted something else: a single
application that could ingest a card, show contact sheets, organize
thousands of frames, and let them work the develop adjustments
non-destructively across whole shoots without ever opening a single image
in Photoshop.

The original design goals:

1. **Non-destructive everything.** The original file is sacred. Every edit
   is a recorded instruction in a database. You can revert any image to
   import state, indefinitely, regardless of how many times you've edited.
2. **Catalog-centric.** Photographers work in shoots, not files. The catalog
   tracks every image, every keyword, every flag, every edit, every history
   step, and every output rendition. You ask the catalog questions; the
   filesystem is an implementation detail.
3. **Modules, not panels.** Library, Develop, Map, Book, Slideshow, Print,
   Web — each is a different mode optimized for a phase of the workflow.
   Move forward through the pipeline, don't fight a single canvas trying to
   be everything.
4. **One develop engine.** Camera Raw under the hood, exposed as a UI in
   the Develop module. Same engine powers Photoshop's Camera Raw filter,
   Bridge previews, and (much later) the cloud rendering pipeline.

That was Lightroom 1 through Lightroom 6. Then Adobe split the brand in
2017 and the design intent forked:

- **Lightroom Classic** kept the original goals. Catalog. Local. Modules.
  Plugins. Tethering. Print module. The photographer's tool.
- **Lightroom (CC)** was rebuilt cloud-first under the assumption that
  storage is infinite and bandwidth is free. No catalog. No folders. No
  print module. No tethering. Phone-and-web-first. Aimed at hobbyists,
  social photographers, and people who value sync over depth.

Adobe's bet: Classic for pros, Cloud for everyone else. Eight years in,
the bet is mostly correct — the pros never moved (and never will, because
Cloud doesn't have the workflow surface), and Cloud has captured a real
audience of "edit on phone, finish on iPad" users who would otherwise be
on Lightroom's competitors (Capture One mobile, Darkroom, VSCO, Halide).

The Lightroom API (Firefly Services) is the *third* design intent: a
stateless render service that exposes the develop engine without any
catalog or library notion at all. Designed for headless pipelines —
e-commerce, agencies, AI image factories, wedding studios doing automated
first-pass color. This is the surface EOS uses for batches.

Tradeoffs vs alternatives:

- **vs Capture One.** C1 wins on tethering (color accuracy in studio
  workflows), per-channel sharpening, and arguably default raw rendering
  warmth. Lightroom wins on catalog scale, masking AI, ecosystem (plugins,
  presets, mobile sync), and pricing. C1 is what fashion and product studios
  default to. Lightroom is what wedding/portrait/travel/everyone-else uses.
  EOS would consider C1 only if Lyfe Spectrum needed studio tethering at
  scale.
- **vs DxO PhotoLab.** DxO wins on pure noise reduction (DeepPRIME XD is
  arguably better than Lightroom Denoise), lens corrections, and a more
  scientific approach. Loses on catalog, ecosystem, and integration. Common
  pattern: shoot in Lightroom, denoise extreme files in DxO via plugin
  round-trip.
- **vs Darktable / RawTherapee.** Open source. Powerful develop engines.
  Painful UX. No catalog at Lightroom's scale. Free. EOS would only consider
  these if Adobe pricing changed dramatically or sovereignty mattered.
- **vs ON1 Photo RAW / Luminar Neo.** Cheaper, perpetual license available,
  more "AI sky replacement" theatrics. Both ship pretty develop engines but
  neither matches Lightroom's catalog or workflow depth. Hobbyist tier.
- **vs Apple Photos.** Different category — Photos is a library app with a
  shallow editor. Useful as a backup destination, not a workflow.
- **vs raw-to-JPEG ML services (Imagen AI, Aftershoot).** These are
  Lightroom-adjacent — they read your catalog, batch-apply ML-trained
  presets that mimic your style, and write back. They are competitors to the
  Lightroom API for the same use case (batch first-pass color) but they
  layer ON TOP of Lightroom Classic instead of replacing it. EOS could
  evaluate Imagen for Empyrean wedding clients later.

What Lightroom is explicitly NOT: a layer-based pixel editor (use
Photoshop), a tethered studio capture system at the C1 level, a DAM at the
PhotoMechanic ingest speed, or an AI image generator (use Firefly).

## Problem-Solution Map and Hidden Capabilities

Things 95% of Lightroom users never discover:

- **Solo mode for panels.** Right-click any module's panel header > Solo
  Mode. Only the active panel expands; others auto-collapse. Cuts
  scrolling by 80%. The single best UX tweak in the whole app.

- **Range Mask: Color and Luminance.** Inside any mask, you can further
  restrict by color picked from the image or by luminance range. Subject
  mask AND luminance > 70 = "highlights on the subject only." The killer
  feature for teeth whitening, eye sharpening, and selective skin tone work.

- **Reference View (`Shift+R`).** Pin a reference image on the left of the
  Develop module while editing another on the right. Match color across a
  shoot to a hero frame without flipping back and forth. Underused.

- **Solo color label filter combinations.** Library filter bar supports
  AND across attribute, text, metadata, none, and color/flag/star. Build
  filter presets and save them — "All 5-star unrejected from this trip
  with no keyword" is one click.

- **Smart collections with rule chaining.** Smart Collections are a small
  rule language — combine `Capture Date in last 30 days`, `Rating >= 4`,
  `Keywords contains "lyfe spectrum"`, and you have an always-current
  shortlist. Build a "Pending Selects," "Pending Edits," "Pending Export,"
  "Delivered" smart collection set per project and you have a Kanban inside
  Lightroom.

- **Develop > Settings > Defaults.** You can set a develop default per
  camera body (Hasselblad gets one default, iPhone gets another), per ISO,
  per camera+ISO. Every imported image starts with the right default
  applied. Game-changer for high-ISO defaults.

- **Auto Mask on adjustment brush.** Edge-aware brushing — paints up to
  edges intelligently. Predates AI masks but still useful for cleanup.

- **Snapshots (`S` button in Develop history).** Named history snapshots.
  "Hero v1", "Hero v2 cooler", "Client preview." Snapshots survive history
  truncation and travel with the catalog.

- **Virtual copies (`Cmd/Ctrl + '`).** A second develop edit on the same
  master. Color and B&W variants of the same image without exporting.

- **Stack by capture time.** Library > Photo > Stacking > Auto-Stack by
  Capture Time. Collapses bursts. Cleans up grid view.

- **Tethered shoot overlays.** Drop a PNG with alpha into Tethered Capture's
  overlay slot — guideline grids, branding, layout templates. Actors,
  fashion, stop-motion all benefit.

- **Print module's "Print to JPEG."** The print engine can export
  composited contact sheets and layout sheets directly as JPEGs. Great for
  client proof sheets without a separate tool.

- **Map module reverse geocoding.** GPS-tagged images get auto city/region
  lookup. Bulk-write to keywords with one click.

- **Adobe Camera Raw < > Lightroom interoperability.** Open any image in
  ACR (Photoshop's interface), make adjustments, save — XMP comes back to
  Lightroom catalog. Some experimental ACR features arrive there before
  Lightroom Develop UI does.

- **Adaptive Profile (LrC 14.0+).** Adobe-shipped profile that uses ML to
  auto-tune contrast/color per image. Treat as a smarter starting point,
  not a final look.

- **Catalog SQL inspection.** With Lightroom closed, `sqlite3 -readonly
  MyShoot.lrcat` lets you ask any question about your edits, history, and
  metadata. Underused for analytics — "what's my median exposure
  adjustment?" is one query.

- **Develop preset partial fields.** A preset doesn't have to set every
  field. Create a preset that ONLY sets `Sharpening` and apply it on top
  of existing edits without disturbing exposure/color. The "compositional
  preset" pattern: a stack of single-purpose presets applied in sequence.

- **`Lightroom CC mobile`'s direct camera capture with raw + HDR.** Mobile
  app captures DNG raw and computational HDR DNGs that sync back. Useful
  for personal brand iPhone shots that need to live in the same workflow as
  proper camera files.

## Operational Behavior and Edge Cases

- **Catalog locking.** Only one Lightroom Classic process can have a catalog
  open at a time. Network catalogs (NAS) are explicitly unsupported and will
  corrupt under any contention. Always local SSD.

- **Catalog WAL mode.** SQLite write-ahead log. The `.lrcat-wal` and
  `.lrcat-shm` sidecars are real and necessary. Never delete them
  separately from the catalog.

- **"Use Smart Previews instead of Originals" preference.** Switches the
  Develop module to render against the smart preview even when originals
  are available — faster Develop on slow disks. June 2025 LrC 14.4 added a
  startup warning when this is on, because users would forget and ship
  exports rendered from smart previews instead of originals. ALWAYS turn
  this OFF before exporting deliverables.

- **"Automatically write changes into XMP."** Catalog Settings > Metadata.
  When ON, every edit is also written to XMP sidecar (or embedded for
  JPEG/TIFF) within seconds. When OFF, only the catalog has the truth and
  XMPs are stale until you `Cmd/Ctrl+S`. EOS rule: ON, so the VPS sync
  pipeline can read sidecars instead of the catalog.

- **XMP write delay.** As of LrC 14.4, XMP for the active image is written
  every 10 seconds rather than after each edit (used to be per-edit, which
  caused IO storms). Don't expect instant disk-side updates; tail with a
  short debounce.

- **Develop history truncation.** History is per-image and per-catalog. If
  you `Clear History` for an image, develop steps collapse to "as of now."
  Snapshots survive. Use snapshots for important checkpoints.

- **Process Version upgrade prompts.** Old images flagged with an
  exclamation mark in Develop are on an older PV. Updating recomputes the
  look — sometimes dramatically (PV2010 → PV2012 was the most disruptive).
  Test before bulk-updating an old catalog.

- **"Use GPU" preferences.** Performance > Use Graphics Processor. Auto by
  default. On certain Intel iGPUs and old NVIDIA drivers, GPU acceleration
  causes Develop module artifacts (banding, slow brush response). Toggle
  off to test.

- **Smart Preview vs original size mismatch.** Smart Previews are 2540px
  long edge. If you crop heavily on a smart preview and then come back
  online, the crop applies to the original at full resolution — fine. But
  you cannot exceed the smart preview's resolution at edit-time previews;
  you'll see soft previews until originals reconnect.

- **AI Denoise GPU requirement.** Adobe lists specific GPU tiers as
  supported. Below threshold the option is grayed out. Apple Silicon all
  ages supported; on Windows you generally want a discrete GPU with 4GB+
  VRAM.

- **AI Denoise pre-14.4 vs post-14.4 behavior change.** Pre-14.4: Denoise
  generates a new DNG, original raw stays untouched, develop history splits
  between two files. Post-14.4: Denoise is a develop step on the original,
  toggle on/off, slider variable, no DNG. Catalog migration is automatic
  but old DNGs remain on disk taking space. EOS cleanup task: identify
  orphan denoised DNGs after upgrading and delete.

- **Lightroom API job retention.** Adobe purges job records after ~24 hours.
  If your poller crashes and doesn't come back within a day, you've lost
  the job ID. Always persist `(input → preset → output → job_id → status)`
  externally and re-issue if needed.

- **Lightroom API XMP validation.** The endpoint accepts XMP that older
  Camera Raw versions wrote, but new fields (recent process versions, new
  mask types) must be on a supported PV. Mismatched PV silently drops
  fields. Spot-check renders.

- **Generative Remove and Generative Expand are cloud-only,** even when
  invoked from LrC. They route through Adobe's servers, count against
  Firefly generative credits, and require an internet connection. Plan
  for that during travel.

- **Color profile soft proofing.** Develop > Soft Proofing toggles a
  paper-or-screen profile preview. Clipping warnings show out-of-gamut
  pixels for that profile. Essential before print delivery, almost never
  used by web-only workflows.

- **`AppleScript` and Windows automation.** Limited surface — File >
  Auto Import, File > Plug-in Manager, scripted exports via plug-ins.
  Don't try to use AppleScript to drive Develop adjustments; it can't.

## Ecosystem Position and Composition

Composes well with:

- **Photoshop.** Round-trip via `Cmd/Ctrl+E`. Lightroom passes the develop
  state, Photoshop opens a TIFF/PSD, save closes the loop and the layered
  file shows up as a sibling in Lightroom. Used for compositing,
  frequency-separation skin work, advanced removal beyond Lightroom's
  Generative Remove, and any layer work.
- **Adobe Camera Raw (in Photoshop / Bridge).** Same engine as Lightroom
  Develop. Catalogs and Bridge see the same XMP.
- **Firefly Services.** Lightroom API and Firefly's generative APIs share
  auth and infra. EOS can chain "render hero in Lightroom API → run
  generative variation in Firefly → composite back."
- **DxO PureRAW / DxO PhotoLab (Denoise specialists).** Lightroom plugin
  exports a DNG to DxO, DxO denoises with DeepPRIME XD, sends back. Used
  when Lightroom's Denoise isn't strong enough.
- **Topaz Photo AI / DeNoise / Sharpen / Gigapixel.** Same plugin pattern.
  AI upscale and detail-rescue tools, called per image when needed.
- **Imagen AI / Aftershoot.** Catalog-aware AI culling and color services
  that read the catalog, train on your style, and apply edits across
  hundreds of images. Plugin or standalone.
- **PhotoMechanic.** Many sports/event pros use PhotoMechanic for ingest +
  rapid culling, then import only picks into Lightroom. Faster grid view
  and metadata workflow than Lightroom for multi-thousand-frame days.
- **The Mastin Labs / VSCO / Lutify / Replichrome plugin presets.** Preset
  packs delivered as Develop presets. Treat as starting points, not finishes.
- **`exiftool`.** Read/write any metadata around Lightroom. Use `exiftool`
  to inspect XMP that Lightroom wrote, and to bulk-correct EXIF before
  import.
- **`rclone`.** Sync Lightroom export folders or smart preview exports to
  S3/Backblaze/Wasabi. EOS uses this to push API inputs to S3 without
  Adobe's storage path.
- **`inotifywait` / `fswatch`.** Tail XMP sidecar directories for changed
  develop state. Hook into EOS sync pipelines.
- **Capture One** for studio tether → export → finish in Lightroom is a
  legit hybrid (some fashion studios do exactly this).

Composes badly with:

- **Network / NAS catalogs.** Officially unsupported. Will corrupt.
  Catalogs go on local SSD only.
- **Cloud sync of the catalog file** (Dropbox, iCloud, OneDrive). Same
  story — file locking and partial writes corrupt SQLite. Sync raws and
  exports, never the .lrcat.
- **Multiple Lightroom Classic seats sharing one catalog.** Two
  photographers cannot collaborate on a single catalog. The right answer
  is one catalog per person + an asset-management layer above (or move to
  Cloud + shared albums for collaboration with caveats).
- **iCloud Photos + Lightroom Cloud.** Two competing cloud libraries
  fighting for "the source of truth" for the same iPhone photos. Pick one.
- **Heavy use of folder symlinks.** Lightroom follows symlinks
  inconsistently across OS versions. Use Lightroom's own folder management.

## Trajectory and Evolution

Lightroom (Classic) release rhythm: roughly two major releases per year,
plus monthly bug-fix point releases via Creative Cloud. Adobe has been
explicit that Classic is not deprecated and will continue receiving feature
work — most recent additions (Generative Remove, Adaptive Profile,
non-destructive Denoise) prove it.

Highlights of the trajectory:

- **2007.** Lightroom 1.0. Catalog-based, modules, Library + Develop +
  Slideshow + Print + Web. The model that would last.
- **2012.** Lightroom 4. Process Version 2012 — modern tone curve, new
  highlights/shadows. Still the basis of every modern develop edit.
- **2015.** Lightroom 6 / Lightroom CC (the older naming). Last perpetual
  license of standalone Lightroom.
- **2017.** The split. "Lightroom Classic CC" (formerly "Lightroom CC")
  vs "Lightroom CC" (the new cloud product). Renamed in 2019 to
  "Lightroom Classic" and "Lightroom" — clean break.
- **2020.** Tethering improvements, Local Hue, ISO Adaptive presets.
- **2021–2022.** AI Masking arrives. Select Subject, Select Sky, Select
  Background, then per-person body parts. Genuinely new capability not
  available anywhere else at the time.
- **2023.** AI Denoise (LrC 12.3). DNG-based. Initially controversial
  because of disk bloat.
- **2024.** Generative Remove (cloud-assisted, Firefly-powered). Adaptive
  Profile. Lightroom API (Firefly Services) reaches GA in March 2024.
- **2025.** Non-destructive AI Denoise in LrC 14.4 (June 2025) — major
  reversal of the DNG approach. Catalog backup panel improvements. XMP
  write throttle to 10s. Smart Previews startup warning.
- **2026 expected.** Continued integration of generative capabilities,
  more API endpoints, more PV tweaks. Adobe has signaled "more cloud-AI in
  Classic" rather than feature parity in Cloud.

Maintenance status: Adobe-funded, very actively maintained, no signs of
slowing. The product is mature; new features tend to be ML-driven additions
rather than core engine changes.

5-year bet: Lightroom Classic remains the right tool for catalog-driven
photographer workflows. Cloud Lightroom continues to grow on phones and
tablets but won't displace Classic for pros. The Lightroom API will get
more endpoints (likely full mask control, full generative invocation,
batch primitives) and become the right way for any AI/automation pipeline
to apply Lightroom-grade edits at scale. EOS's bet on Classic for human
editing + API for headless batches is correctly aligned.

## Conceptual Model and Solution Recipes

**Mental model.** Lightroom is three things wearing one name:

1. A **catalog database** (Classic) or cloud document graph (CC) holding
   image metadata, develop instructions, and organizational structure
2. A **non-destructive develop engine** (Camera Raw under the hood) that
   reads (input pixels + develop XMP) and produces (output pixels)
3. A **rendering pipeline** that takes catalog images, runs them through
   develop, and writes outputs to disk or cloud

The desktop app is a UI on top of (1) + (2) + (3). The cloud app is a
mobile/web UI on top of a cloud version of the same. The API is just (2)
+ (3) without (1) — pure stateless rendering with the develop engine.

If you internalize "originals never change, edits are XMP, the develop
engine is one engine wearing three skins," every workflow simplifies.

### Recipe A — Personal brand shoot ingest and edit (Antony's primary loop)

```
1. Card → ingest into Classic via File > Import
   - Copy as DNG to /Photos/2026/2026-04-06-personal-brand/
   - Apply default metadata preset (copyright, contact, byline)
   - Apply default develop preset: "AFM Tactical Luxury v3 Base"
   - Build standard previews + smart previews
   - Add keyword: "personal-brand", "2026-04"
2. Library grid view, flag picks (P) and rejects (X)
   - Filter to picks
3. Develop module on the hero frame
   - Reference View (Shift+R) pinned to a known-good frame from prior shoots
   - Tune to taste, save as snapshot "hero v1"
4. Sync to selected: pick frames in same lighting, Auto Sync ON,
   propagate develop settings
5. Per-frame tweaks where needed
6. AI Denoise on any ISO 3200+ frames (Photo > Enhance > Denoise)
7. Export
   - 2048px sRGB JPEG to /Exports/social/
   - 3000px sRGB JPEG to /Exports/web/
   - Full-res sRGB JPEG to /Exports/master/
   - Trigger rclone to push /Exports/social/ to S3 for the social pipeline
8. Add color label = "delivered" once posted
```

Agent role: write the metadata preset, write the default develop preset
spec, generate the export filename template, and trigger the rclone push.

### Recipe B — Lyfe Spectrum product shoot (catalog + API hybrid)

```
1. Studio capture — tethered into Classic or imported from card after
2. Apply per-product metadata (SKU, color, size, season) via metadata preset
3. Manual develop on the hero shot per product:
   - Custom WB clicked on a known neutral patch
   - Background cleaned up with Generative Remove if needed
   - Lens/perspective correction
   - Save as preset "spectrum/2026-spring/{SKU}"
4. Sync settings to all frames of the same product
5. Export DNGs (or push raws + per-product XMP presets to S3)
6. Headless API job: for each SKU, apply "spectrum/2026-spring/{SKU}.xmp"
   to all raws via /presets endpoint, render:
   - 2048px sRGB JPEG (social)
   - 3000px sRGB JPEG (ecommerce hero)
   - 1500px sRGB JPEG (ecommerce thumbs)
   - master TIFF (archive)
7. Rename outputs by SKU + variant + size
8. Push to S3, generate proof contact sheet, notify ops
```

Agent role: orchestrate steps 5–8 entirely. Antony only does 1–4.

### Recipe C — Empyrean Studio client retouch turnaround

```
1. Client raws into a per-engagement catalog (Classic)
2. Cull with picks/rejects, deliver picks count to client
3. Develop the hero set (typically 20–50 frames); save as snapshots
4. Export watermarked low-res proofs (1200px sRGB, watermark overlay)
5. Send proofs to client, await approval
6. On approval: export full-res unwatermarked finals
7. Archive: export-as-catalog the final selects with develop settings,
   push raws + catalog bundle to cold storage
```

Agent role: catalog template setup, export presets, watermark configuration,
proof sheet generation, delivery email, archival push to cold storage.

### Recipe D — Headless API batch (no human in the loop)

```bash
#!/usr/bin/env bash
set -euo pipefail

SHOOT="${1:?usage: $0 SHOOT_DATE}"
PRESET_HREF="$2"
MANIFEST="/opt/OS/data/lightroom/$SHOOT/manifest.jsonl"

TOKEN=$(/opt/OS/scripts/get_adobe_token.sh)

while IFS= read -r line; do
  SRC=$(echo "$line" | jq -r .src_url)
  OUT=$(echo "$line" | jq -r .out_url)
  RESP=$(curl -sS -X POST https://image.adobe.io/lrService/presets \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-api-key: $ADOBE_CLIENT_ID" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg src "$SRC" --arg out "$OUT" --arg p "$PRESET_HREF" \
        '{inputs:{source:{href:$src,storage:"external"}},
          options:{presets:[{href:$p,storage:"external"}]},
          outputs:[{href:$out,storage:"external",type:"image/jpeg",overwrite:true}]}')")
  JOB=$(echo "$RESP" | jq -r '._links.self.href')
  echo "$line" | jq --arg job "$JOB" '. + {job_url: $job, status: "running"}' \
    >> "$MANIFEST.in-flight"
done < "$MANIFEST"

# Hand off to a poller process that drains $MANIFEST.in-flight
python3 /opt/OS/scripts/lightroom_poll.py "$SHOOT"
```

### Recipe E — Spot-check API render against Classic render

Before bulk-running any preset through the API, render one image both
through Classic Develop (manually) and through the API (with the same
.xmp), open both in Photoshop, set Difference blend mode, look for any
non-zero pixels. Process Version drift, profile availability, and engine
point releases can introduce subtle differences. NEVER ship a 200-image
API batch without spot-checking.

## Industry Expert and Cutting-Edge Usage

- **AI culling + AI color (Imagen, Aftershoot, Narrative).** The dominant
  workflow shift in 2024–2026 is letting an ML service train on your
  catalog history and apply first-pass culling and color across thousands
  of frames. Wedding pros report 5–10x speedups on culling. The pattern:
  shoot → ingest → ML cull → ML color → human refines → export. EOS bet:
  evaluate Imagen for Empyrean wedding work after first revenue.

- **Generative Remove as the new spot-removal.** The pre-Firefly
  spot-removal tool was per-pixel content-aware. Generative Remove is a
  diffusion-based fill that handles complex backgrounds (crowds, fences,
  reflections). Costs generative credits. Use for the 5% of frames that
  needed Photoshop before; keep classical removal for the routine 95%.

- **Adaptive Profile as starting default.** The 2024 Adaptive Profile uses
  ML to auto-tune contrast/color per image as a starting profile. Some
  pros now set Adaptive as the default profile per camera, then layer
  presets on top.

- **Cloud sync as the laptop-to-VPS bridge.** Photographers who travel
  shoot on the road, sync via Lightroom CC subscription, edit on tablet,
  then come home to find smart previews already in their Classic catalog.
  The "Sync with Lightroom" toggle in Classic enables this. EOS could use
  this to bridge Antony's iPhone shots to the Windows workstation
  automatically.

- **Catalog SQL analytics.** Power users `sqlite3 -readonly` their
  catalogs to compute "what camera body do I shoot most," "what's my
  median exposure adjustment in 2025," "which lenses produce my keepers."
  Quantified self for photographers. Agents could surface this to Antony
  monthly.

- **Headless render farms (Lightroom API at scale).** Wedding studios and
  e-commerce shops are quietly building Firefly-Services-based render
  farms. Train an ML model on a stylist's color choices, dump it to XMP
  presets, run thousands of weddings per month through the API. EOS is
  doing the small version of this for Lyfe Spectrum.

- **Plugin ecosystem.** Mature: the LR/Mogrify plugins (mogrify-style
  border/text on export), Excire Foto (AI tagging), Photolemur (auto
  enhance). Plus the export-target plugins (Smugmug, Flickr, S3, Dropbox).
  Mostly Lua, mostly free or one-time-paid.

- **Tethering with overlay layers and live focus stacking.** Studios shoot
  100-image stacks tethered into Lightroom and use third-party tools
  (Helicon, Zerene) for the stack. Lightroom hosts the catalog and the
  finishing.

- **Mobile-first creators using Lightroom Cloud.** A whole generation of
  Instagram/TikTok photographers does their entire workflow on iPhone via
  Lightroom Cloud and never touches Classic. Faster, simpler, syncable,
  enough for social-only output. The cloud product is winning that
  audience even if it can't replace Classic for pros.

- **Multi-pass develop with stacked partial presets.** Power users stop
  building monolithic "the look" presets and instead build small composable
  ones: "WB Daylight Cool," "Skin Warmth +", "Crushed Blacks v2," "Film
  Grain Mild," "Hero Sharpen." Apply in sequence. Vastly easier to debug
  and tune than monoliths.

## EOS Usage Patterns

Lightroom is a hybrid skill. Antony is the editor; agents support the
editor. The split is non-negotiable: pixels are a brand decision, made by
the founder, in front of the screen. Everything else around the pixels is
fair game for automation.

Canonical EOS conventions:

- **Lightroom Classic on the Windows workstation is the catalog of record.**
  Per-project catalogs in `D:\Photos\Catalogs\` or equivalent. Personal
  brand catalog separate from Lyfe Spectrum catalog separate from Empyrean
  client catalogs. One catalog per major project domain.
- **Catalog Settings: "Automatically write changes into XMP" = ON** for
  every active catalog. This makes the VPS sync pipeline work — XMP
  sidecars next to raws are always within ~10 seconds of the catalog
  truth, so agents reading XMP via inotifywait/fswatch always see fresh
  develop state.
- **Preset library structure.**
  ```
  AFM/
    base/                 base profile + lens correction defaults
    tactical-luxury/      personal brand finishes
      hero-v1.xmp
      hero-v2.xmp
      hero-v3.xmp
    spectrum/             Lyfe Spectrum product
      ss26/{sku}.xmp
      hero/
    empyrean/             client work, per-engagement
      {client}-{date}/
  ```
  Presets in this structure can be exported as a tree and pushed to S3 for
  the API to consume. Same files, two consumers.
- **Smart Collections per project as Kanban.** "Pending Selects," "Pending
  Edits," "Pending Export," "Delivered." Status moves by changing color
  label.
- **EOS sync pipeline.** A VPS-side script tails the XMP sidecar
  directories synced from the Windows workstation via Tailscale + rsync.
  When XMP changes, it ingests the new develop state into Neon for
  agents to query — "what's the current preset Antony's using on this
  shoot."
- **API batch jobs from VPS only.** Never call Firefly Services Lightroom
  API from a laptop or workstation. Always from the VPS, where token
  caching, presigned URL minting, and job manifest persistence live in
  one place. EOS conventions:
  - Input raws on S3 under `s3://eos-lightroom-in/{shoot}/`
  - Presets on S3 under `s3://eos-lightroom-presets/`
  - Outputs on S3 under `s3://eos-lightroom-out/{shoot}/{variant}/`
  - Job manifest in `/opt/OS/data/lightroom/{shoot}/manifest.jsonl`
  - Token cache in `/opt/OS/eos_ai/.adobe_token_cache.json` (gitignored)
- **Spot-check before bulk.** Every API batch starts with a single
  representative frame rendered both ways (Classic + API), human-eyeballed
  for parity. No 200-image batch goes out without that check.
- **Versioned preset files.** Presets are named with version suffixes
  (`hero-v3.xmp`), committed to a git-tracked path (separate from main
  EOS repo), and changes are reviewed like code. Antony's "look" is a
  versioned artifact.
- **Backup discipline.** Catalog backup on Lightroom exit, keep 10
  generations. Workstation drives backed up to NAS nightly. NAS backed
  up to Backblaze weekly. Raws are sacred — three copies, two media,
  one offsite.
- **Denoise rule.** Apply Denoise only to ISO 3200+ frames. Apply BEFORE
  any masking. If LrC < 14.4, warn about DNG bloat before invoking.
- **Personal brand consistency check.** Once a month, agents pull the
  last month of personal brand exports, run a histogram + color signature
  comparison against the "tactical luxury" reference, flag any drift.
  Brand is visual; visual drift is brand drift.

Verification rule: after any agent-driven Lightroom operation, run

```bash
# Verify the API render exists and is non-trivial
aws s3 ls s3://eos-lightroom-out/$SHOOT/ --recursive --human-readable | tail -20

# Verify XMP sync is fresh (sidecar mtime within last minute of catalog activity)
find $XMP_DIR -name '*.xmp' -newer /tmp/last-sync-marker | wc -l
```

before declaring the job done.

## Gotchas

1. **Catalog deletion deletes edits, not photos.** And the inverse — image
   deletion in Library can mark "Remove from catalog" or "Delete from disk."
   Read the dialog every time.
2. **Network or cloud-synced catalogs corrupt.** Local SSD only. Never
   Dropbox, never iCloud Drive, never NAS. SQLite on a network filesystem
   is a known footgun — Adobe explicitly does not support it.
3. **`Use Smart Previews instead of Originals` left on during export.** You
   ship 2540px JPEGs by accident. The June 2025 startup warning helps but
   you can dismiss it. Default to OFF except when traveling.
4. **Moving files in Finder/Explorer orphans them.** Always rename/move
   inside Library. Recovery: Find Missing Folder.
5. **Process Version upgrade silently changes the look.** Updating an old
   image (from PV2010 to current) recomputes tone and color. Test before
   bulk-updating.
6. **AI Denoise pre-LrC 14.4 generates a DNG copy.** Disk bloat: a 24MB raw
   becomes a ~24MB raw + ~80MB DNG. Across thousands of frames this is
   tens of GB. Upgrade to 14.4+ or accept the bloat.
7. **AI Denoise after masking shifts masks.** Denoise first, then mask.
8. **AI Masking trained on 8MP previews, applied to full res.** The mask
   edges are sometimes coarser than they look at preview zoom. Always
   100% zoom check skin/hair masks before delivery.
9. **`Sync Settings` propagates everything by default.** Including white
   balance and crop. Click "Check None" then check only the fields you
   want before clicking Sync. The "fewer fields, sync more often" rule.
10. **Develop history truncation loses snapshots? No, snapshots survive.**
    But people forget snapshots exist and rely on history scrolling. Train
    yourself to snapshot every keeper state.
11. **Develop preset library past 2000 entries** causes Develop module lag
    (thumbnail render per preset on every image change). Hide unused
    folders.
12. **Catalog backups in `Backups/` directory** can grow into hundreds of
    GB. Set Catalog Settings > Backup > Tested integrity, "Keep last 10"
    or LrC 14.4+ "Keep last N" with auto-prune.
13. **GPU acceleration causes Develop artifacts on certain Intel iGPUs.**
    Symptoms: banding, slow brush response. Toggle Performance > Use
    Graphics Processor off to test.
14. **Tethered capture vendor SDK mismatch.** Camera firmware update can
    silently break tethering until LrC point release catches up. Never
    update camera firmware the day before a paid shoot.
15. **Lightroom API does not accept inline image bytes.** Only presigned
    URLs from S3, Azure Blob, or Dropbox. Plan storage upfront.
16. **Lightroom API jobs purged after ~24 hours.** If your poller crashes
    longer than that, you've lost the job ID. Persist the manifest
    externally and re-issue.
17. **Lightroom API token expiry mid-job.** Tokens are ~24h, jobs are
    minutes. Don't refresh in the middle of polling — let the job finish
    on the token it started with, refresh on the NEXT call.
18. **Presigned URL expiry mid-job.** Mint with at least 30 minutes
    lifetime. AI ops on huge raws can take 10+ minutes server-side.
19. **API XMP fields silently dropped on PV mismatch.** A field from a
    newer process version sent to a render that resolves to an older PV
    is silently ignored. Always verify the resolved PV in your spot-check
    render.
20. **`/edit` endpoint field name drift.** Adobe occasionally renames JSON
    fields between API versions. Pin against current docs and re-test
    quarterly.
21. **`storage: "external"` requires the URL to be reachable from Adobe's
    network.** Buckets behind VPN-only access don't work. Use a public
    presigned URL even if the bucket itself is private.
22. **Lightroom Classic and Lightroom (Cloud) presets are not 100%
    interchangeable.** Most fields work both ways but mask groups, masks
    that depend on Cloud-only ML, and very recent develop fields can
    differ. Test cross-app.
23. **Generative Remove + offline = Generative Remove disabled.** It's a
    cloud call. No internet, no Generative Remove. Plan around for
    travel.
24. **`Auto WB` shift between similar product shots.** Auto WB is image-by-
    image. For consistent product color, set custom Kelvin from a known
    neutral and sync — never trust Auto on product work.
25. **Soft proofing leaks into your master view.** Turn it off when done
    proofing or you'll edit against a paper-profile preview thinking it's
    your screen profile.
26. **Smart Previews encode at 2540px lossy DNG.** If you export from a
    smart preview (because original is offline), the export is upsampled
    from a 2540px source even if your export preset says 4000px. ALWAYS
    verify originals are online before final exports.
27. **Catalog file lock left from a crashed Lightroom.** Look for
    `.lrcat.lock` next to the catalog and delete only if you're sure no
    LrC instance is running. Otherwise you risk double-open and corruption.
