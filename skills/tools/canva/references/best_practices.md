# Canva — Creator-Level Best Practices
Source: canva.dev/docs/connect, canva.dev/blog, canva.com/newsroom, github.com/canva-sdks/canva-connect-api-starter-kit, canva.com/magic, canva.com/help
API Version: Connect API 2025-09 (post brand-template ID migration), GA since 2024
SDK Version: canva-connect-api-starter-kit (TypeScript via openapi-ts); no official Python SDK — use openapi-generator on the public OpenAPI spec
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Canva Connect uses **OAuth 2.0 Authorization Code with PKCE (SHA-256
mandatory)**. There is no API key, no service account, no machine-to-machine
client_credentials flow. Every token is bound to a real Canva user, and
that user must consent to the exact list of scopes the integration declares.
This is the single biggest architectural fact of the API: there is no
"server identity" inside Canva. If you want a bot to design things, the
bot is acting as a human user.

### PKCE flow (the mandatory long version)

1. Register your integration at canva.dev. You receive a `client_id` and
   `client_secret` (the secret is only used in the token exchange, not in
   the authorize URL).
2. Per-user, per-session, generate a high-entropy `code_verifier`
   (43-128 chars, `[A-Z][a-z][0-9]-._~`, base64url alphabet). Store it
   server-side keyed by `state`.
3. Compute `code_challenge = base64url(sha256(code_verifier))` (no padding).
4. Redirect the user to:
   ```
   https://www.canva.com/api/oauth/authorize
     ?client_id={client_id}
     &redirect_uri={redirect_uri}
     &scope=design:content:read%20design:content:write%20asset:read%20asset:write
     &response_type=code
     &code_challenge={challenge}
     &code_challenge_method=S256
     &state={random_state}
   ```
5. User consents. Canva redirects to your `redirect_uri` with `code` and
   `state`. Validate `state` against the value you stored.
6. POST to the token endpoint:
   ```
   POST https://api.canva.com/rest/v1/oauth/token
   Content-Type: application/x-www-form-urlencoded
   Authorization: Basic base64(client_id:client_secret)

   grant_type=authorization_code
   &code={code}
   &code_verifier={verifier}
   &redirect_uri={redirect_uri}
   ```
7. Response: `{access_token, refresh_token, expires_in, scope, token_type}`.
   `expires_in` is typically 3600s (1h). `refresh_token` is long-lived
   (per Canva docs, 90 days of inactivity expires it).
8. Use `Authorization: Bearer {access_token}` on every API call.
9. Refresh:
   ```
   grant_type=refresh_token
   &refresh_token={refresh}
   ```
   Refresh tokens may rotate — always overwrite stored refresh token with
   the new one if returned.

### Scope grammar

Scopes are colon-separated, resource-action shaped. They are **explicit and
non-implicative** — `asset:write` does not grant `asset:read`, you must
list both. The scope string in authorize is space-separated. Re-consent is
required when an integration adds a new scope; existing refresh tokens do
NOT automatically gain the new permissions.

Common scopes (request the minimum needed):

| Scope | Grants |
|-------|--------|
| `app:read` | Read integration metadata |
| `app:write` | Modify integration metadata |
| `profile:read` | `GET /v1/users/me` profile and capabilities |
| `asset:read` | List and download asset metadata |
| `asset:write` | Upload and update assets |
| `brandtemplate:meta:read` | List brand templates and their metadata |
| `brandtemplate:content:read` | Read brand template dataset (fillable schema) |
| `design:meta:read` | List designs, metadata only |
| `design:content:read` | Read design content (export, structural reads) |
| `design:content:write` | Create designs, autofill, resize, import |
| `folder:read` | List folder contents |
| `folder:write` | Create, move, delete folders |
| `comment:read` | Read comments and replies |
| `comment:write` | Create comments and replies |

### Security recommendations (from canva.dev/docs/connect/guidelines/security)

- Treat `client_secret` as a server-only value. Never ship it to a browser
  or mobile app. PKCE protects the public client legs, not the secret.
- Verify the `state` parameter on every callback. Reject mismatches.
- Use HTTPS for `redirect_uri` in production. Localhost is allowed in dev.
- Store refresh tokens encrypted at rest. Never log access or refresh tokens.
- Request the smallest set of scopes that satisfies the workflow. Users can
  see exactly what you ask for on the consent screen.

## Core Operations with Exact Signatures

All endpoints are under `https://api.canva.com/rest/v1`. Request bodies
are JSON unless noted; responses are JSON. Async operations return a
`{job: {id, status}}` envelope and require polling — see Conceptual Model.

### Designs

```
POST   /v1/designs                          Create blank design
GET    /v1/designs                          List the user's designs (paginated)
GET    /v1/designs/{designId}               Get design metadata
GET    /v1/designs/{designId}/pages         List pages of a design (paginated)
POST   /v1/designs/{designId}/comments      (also under /comments resource)
```

`POST /v1/designs` body:
```json
{
  "design_type": {
    "type": "preset",
    "name": "instagram_post"
  },
  "title": "Daily IG post — 2026-04-06"
}
```
`design_type.type` may be `preset` (named, e.g. `instagram_post`,
`presentation`, `doc_a4`) or `custom` with `width`/`height` in pixels.

Response includes `design.id` (`DAF...`), `urls.edit_url`, `urls.view_url`,
`thumbnail.url`, `created_at`, `updated_at`, `page_count`.

### Brand templates

```
GET /v1/brand-templates                                List accessible templates
GET /v1/brand-templates/{brandTemplateId}              Get template metadata
GET /v1/brand-templates/{brandTemplateId}/dataset      Get the autofill schema
```

The dataset response describes named fields and their types — e.g.
`{"data_fields": {"headline": {"type": "text"}, "hero": {"type": "image"},
"chart_q1": {"type": "chart"}}}`. **Always read the dataset before
autofilling** — never hardcode field names from a screenshot of the GUI.

### Autofill (the headline endpoint)

```
POST /v1/autofills                          Create autofill job
GET  /v1/autofills/{jobId}                  Get autofill job
```

`POST /v1/autofills` body:
```json
{
  "brand_template_id": "DAF...",
  "title": "Lyfe Spectrum drop email — black hoodie",
  "data": {
    "headline":   {"type": "text",  "text": "STRUCTURE OVER DISCIPLINE"},
    "subheadline":{"type": "text",  "text": "New drop. Limited."},
    "hero_image": {"type": "image", "asset_id": "MAFooBar123"}
  }
}
```

Field types accepted: `text`, `image`, `chart`. `text` takes `text`. `image`
takes `asset_id` (NOT a URL — upload via `/v1/asset-uploads` first). `chart`
takes a `chart_data` object with rows/columns.

Job result on success:
```json
{ "job": {
    "id": "...",
    "status": "success",
    "result": {
      "type": "create_design",
      "design": {
        "id": "DAFnewDesignId",
        "urls": { "edit_url": "...", "view_url": "..." },
        "thumbnail": { "url": "..." }
      }
    }
}}
```

### Exports

```
POST /v1/exports                            Create export job
GET  /v1/exports/{exportId}                 Get export job
```

`POST /v1/exports` body:
```json
{
  "design_id": "DAF...",
  "format": {
    "type": "pdf",
    "size": "a4",
    "export_quality": "pro",
    "pages": [1, 2, 3]
  }
}
```

`format.type` accepts `png`, `jpg`, `pdf` (with `export_quality` standard|pro
and optional `size`), `mp4`, `gif`, `pptx`. PNG accepts `transparent_background`
and `as_single_image` for multi-page designs. JPG accepts `quality` 1-100.

Successful job returns `urls: ["https://..."]` — one URL per page for
single-image-per-page formats, one URL total for combined formats. **URLs
expire in 24 hours.** Download immediately and persist to your own storage.

### Assets and uploads

```
POST   /v1/asset-uploads                    Upload asset (binary body)
GET    /v1/asset-uploads/{jobId}            Poll upload job
GET    /v1/assets/{assetId}                 Get asset metadata
PATCH  /v1/assets/{assetId}                 Update asset (name, tags)
DELETE /v1/assets/{assetId}                 Delete asset
```

Upload is unusual: body is `application/octet-stream` raw bytes, metadata
goes in a single header `Asset-Upload-Metadata` whose value is a JSON object
with `name_base64` (base64-encoded UTF-8 filename). Large files use the
async job pattern.

### Folders

```
POST   /v1/folders                          Create
GET    /v1/folders/{folderId}               Get
PATCH  /v1/folders/{folderId}               Rename
DELETE /v1/folders/{folderId}               Delete
GET    /v1/folders/{folderId}/items         List items (designs, assets, subfolders)
POST   /v1/folders/{folderId}/items/move    Move item into folder
```

### Comments

```
POST /v1/comments                                       Create thread
POST /v1/comments/{commentId}/replies                   Reply
GET  /v1/comments/{commentId}                           Get thread
```

Comments attach to a `design_id` and optional element coordinates.

### Resizes and design imports

```
POST /v1/resizes                            Create resize job (design → new format)
GET  /v1/resizes/{jobId}                    Poll resize job

POST /v1/imports                            Create design import job (file → design)
GET  /v1/imports/{jobId}                    Poll import job
```

Resize takes a `design_id` and a `design_type` target — Canva creates a
*new* design at the new dimensions; the original is untouched. Import
accepts PPTX, DOCX, PDF and creates an editable Canva design.

### Users

```
GET /v1/users/me                            Profile, team, capabilities
GET /v1/users/me/profile                    Display name, avatar
GET /v1/users/me/capabilities               Feature flags (e.g. autofill enabled)
```

Use `/capabilities` to detect Enterprise membership before attempting
autofill — see Gotchas.

## Pagination Patterns

List endpoints (designs, brand-templates, folder items, assets) use **opaque
cursor pagination**, not page numbers. Each response includes a
`continuation` field that you pass back as a query parameter on the next
request:

```
GET /v1/designs?continuation={token}
```

When the response omits `continuation` (or returns it as null), you have
reached the end. Page sizes are typically 50-100 items; some endpoints
accept a `limit` query parameter (max 100).

Idiomatic Python loop:

```python
def list_all_designs():
    cursor = None
    while True:
        params = {"continuation": cursor} if cursor else {}
        r = httpx.get(f"{BASE}/designs", headers=H, params=params).json()
        for d in r["items"]:
            yield d
        cursor = r.get("continuation")
        if not cursor:
            return
```

Never assume order is stable across pages — sort client-side if you need
deterministic order. Cursors expire after a short window (minutes); resuming
a partial pagination an hour later may 400.

## Rate Limits

Rate limits are **per-endpoint, per-user, per-minute**, not per-integration.
Each user the integration acts on behalf of has their own counter.
Documented numbers (canva.dev as of 2026-04):

| Endpoint | Limit |
|----------|-------|
| `POST /v1/exports` (create export job) | 20 / minute / user |
| `GET /v1/exports/{id}` (poll export job) | 120 / minute / user |
| `POST /v1/autofills` | 20 / minute / user (matches export pattern) |
| `GET /v1/autofills/{id}` | 120 / minute / user |
| `POST /v1/asset-uploads` | 20 / minute / user |
| Read endpoints (designs, folders, brand-templates) | ~100 / minute / user |

When you exceed a limit you receive **HTTP 429** with a `Retry-After` header
in seconds. Honor it. The Canva docs explicitly recommend
**exponential backoff** for polling: start at 1s, multiply by ~1.5-2 each
poll, cap at 8-10s.

A polling worker that does `while True: get; sleep(0.1)` will trip 429
within 12 seconds and is the most common rate-limit footgun. Use the
backoff helper in the SKILL.md Quick Reference.

For batch jobs (e.g. 1000 social posts/day), shape work as: small bursts
of 15-18 autofill creations, then poll those 15-18 jobs with backoff,
then export. Do not parallelize beyond 20 in-flight per user.

## Error Codes and Recovery

Canva returns standard HTTP status codes plus a JSON error envelope:

```json
{
  "code": "permission_denied",
  "message": "Your account does not have access to brand templates."
}
```

Common codes and the right recovery action:

| HTTP | code | Recovery |
|------|------|----------|
| 400 | `invalid_request` | Field name or type wrong. Re-fetch dataset, fix payload. Do NOT retry. |
| 401 | `unauthorized` | Access token expired. Refresh and retry once. If refresh also 401, re-consent the user. |
| 403 | `permission_denied` | Missing scope OR account tier insufficient (e.g. autofill on non-Enterprise). Do NOT retry — fix scope/account. |
| 404 | `not_found` | Resource gone or wrong ID format. Check brand template ID migration (Sept 2025). Do NOT retry. |
| 409 | `conflict` | Optimistic concurrency violation (rare). Re-fetch and retry. |
| 413 | `payload_too_large` | Asset upload exceeds limit (see Limits). Resize before upload. |
| 415 | `unsupported_media_type` | Wrong `Content-Type`. Asset uploads need `application/octet-stream`. |
| 429 | `rate_limited` | Sleep `Retry-After` seconds, then retry. Apply exponential backoff. |
| 500 | `internal_error` | Transient. Retry with backoff up to 3 times. |
| 502/503/504 | upstream | Transient. Backoff retry. |

For async job results, the job envelope itself can be `failed`:
```json
{ "job": { "id": "...", "status": "failed",
           "error": { "code": "design_creation_failed", "message": "..." } } }
```
HTTP is still 200 in this case. Always check `job.status`, never just the
HTTP status.

## SDK Idioms

There is **no official Python SDK** and no official Node SDK *as a
published package*. Canva publishes:

- **OpenAPI spec** — `https://www.canva.dev/docs/connect/api-reference/`
  is generated from it; raw spec is in `canva-connect-api-starter-kit/openapi/spec.yml`.
- **TypeScript starter kit** at `github.com/canva-sdks/canva-connect-api-starter-kit`,
  which uses **`openapi-ts`** to generate a typed TS client into `client/ts`.
- **Postman collection** at postman.com/canva-developers.

Idiomatic patterns:

**TypeScript (starter kit pattern):**
```ts
import { Client } from "./client/ts";

const client = new Client({
  baseUrl: "https://api.canva.com/rest/v1",
  token: () => getAccessToken(userId),  // refresh-aware accessor
});

const job = await client.autofill.createDesignAutofillJob({
  brand_template_id: TEMPLATE_ID,
  title: "Daily post",
  data: { headline: { type: "text", text: "..." } },
});
const design = await pollUntilDone(() =>
  client.autofill.getDesignAutofillJob({ jobId: job.job.id })
);
```

**Python (no SDK, use httpx + openapi-generator if you want types):**
```bash
# Generate a Python client from the spec
pip install openapi-python-client
openapi-python-client generate \
  --url https://www.canva.dev/_next/static/openapi/spec.yml
```

For EOS, the simpler pattern is a thin httpx wrapper module
(`eos_ai/canva_client.py`) with explicit typed methods for the operations
EOS actually uses (autofill, export, upload, list designs). Avoids a
generated-code dependency and stays under 200 lines.

**Token accessor pattern (critical):** Never pass a static `Bearer` string
into a long-lived client. Wrap it in a callable that refreshes when
expired. EOS pattern: a `CanvaTokenManager` keyed on `tenant_id`, backed
by Neon `tenant_secrets`, with an in-process cache TTL of 55 minutes.

## Anti-Patterns

- **Polling without backoff.** `while True: get; sleep(0.1)` trips 429 in
  seconds. Always exponential backoff, capped.
- **Hardcoding brand template field names from the GUI.** Field names
  shown in the GUI are display labels; the dataset uses internal keys.
  Always `GET /brand-templates/{id}/dataset` first.
- **Treating the Connect API as a graphics rendering engine.** It is not.
  It instantiates pre-designed templates. If you need to draw arbitrary
  pixels at runtime, use Pillow or a real rendering library and upload the
  result as an asset.
- **Storing Canva export URLs in a database.** They expire in 24h. Always
  download the bytes and persist to your own storage.
- **Building "machine accounts" for the bot.** There is no such concept.
  Tie the integration to a real Canva user (the founder, in EOS), refresh
  the token, accept that the human user is the audit trail.
- **Asking an agent to "design something in Canva."** Magic Studio is
  GUI-only, the API has no creative AI surface. Agents autofill; humans
  design.
- **Shipping the client_secret in a frontend bundle.** PKCE protects the
  authorize → callback leg, but the token exchange must happen server-side.
- **Treating PNG export `transparent_background` as free.** It only works
  on designs whose background is itself transparent. A white-background
  design exported with `transparent_background=true` still has white pixels.
- **Calling `POST /v1/designs` to create a "blank canvas" then trying to
  add elements.** There is no element-add endpoint. Use a Brand Template
  + Autofill, or use Imports.
- **Forgetting that `asset_id` references are scoped to the uploading user.**
  An asset uploaded under user A cannot be referenced in an autofill call
  acting on behalf of user B unless the asset is in a shared folder.
- **Parsing `Retry-After` as milliseconds.** It is **seconds**.
- **Letting refresh tokens go stale.** 90 days of inactivity expires them.
  EOS runs a weekly heartbeat that refreshes proactively.

## Data Model

The Canva object graph the API exposes:

```
User
 └── Capabilities (autofill_enabled, brand_templates_enabled, ...)
 └── Brand Hub (Enterprise) / Brand Kit (Pro)
       ├── Colors
       ├── Fonts
       ├── Logos
       ├── Voice (Brand Voice — GUI only)
       └── Brand Templates
             └── Dataset (named, typed fillable fields)
                   ├── text fields
                   ├── image fields  → reference Assets by id
                   └── chart fields  → inline data
 └── Designs
       ├── Pages (1..N)
       │     └── Elements (text, image, shape, video, chart, group)  ← read-only via API
       ├── Comments (threads + replies)
       ├── urls.edit_url (signed, rotates)
       ├── urls.view_url (signed, rotates)
       └── thumbnail.url
 └── Assets (images, videos)
       ├── id (MAF...)
       ├── name
       ├── tags
       └── thumbnail
 └── Folders (designs, assets, subfolders)
```

ID prefixes are stable and identifiable:
- `DAF...` — designs and brand templates
- `MAF...` — assets (media)
- Folder IDs and job IDs are opaque, no prefix convention.

Element-level read/write does not exist via API. The API treats a Design
as an opaque renderable referenced by id. The granular structure visible
in the GUI is accessible only through Magic Switch / autofill / export.

The Brand Template **dataset** is the only schema-shaped surface:
field name → field type. This is what makes autofill work — Canva already
knows where the field is positioned, what font, what color, what
constraints. You only supply values.

## Webhooks and Events

**As of 2026-04, the Connect API has no webhook surface for design
lifecycle events.** There is no `design.created`, `design.updated`,
`comment.added`, or `export.completed` callback. This is the largest
functional gap relative to Figma, Adobe, and Notion.

Workarounds:

- **Poll `GET /v1/designs?continuation=...`** and diff `updated_at` against
  a stored watermark. Cheap; appropriate for low-frequency change
  detection (hourly, nightly).
- **Persist a design index in Neon** with `design_id`, `last_seen_at`,
  `updated_at`, hash of metadata. Each poll updates the index.
- **For exports, you already have the job id** — poll it directly with
  exponential backoff. No webhook needed.
- **For comments**, polling `GET /v1/designs/{id}/comments` is the only
  option. If you need realtime comment notifications, use Slack /
  Discord and have humans comment there instead of in Canva.

If/when Canva ships webhooks (likely 2026-2027 based on roadmap signals),
the migration will be: replace polling watermark with webhook handler,
keep the index for backfill.

## Limits

Hard limits documented or empirically observed:

| Limit | Value |
|-------|-------|
| Asset upload — image | 25 MB per file (PNG, JPG, SVG, HEIC) |
| Asset upload — video | 1 GB per file (MP4, MOV) |
| Asset upload — audio | 50 MB per file (MP3, M4A) |
| PDF import | 100 MB |
| PPTX import | 100 MB |
| Design page count | 300 pages (presentation/doc); 1 page (social formats) |
| Brand templates per Brand Kit | 1000 (soft) |
| Autofill data fields per call | ~100 (practical; spec does not document a hard cap) |
| Text field length | 16,000 chars per field (soft) |
| Export PDF page count | matches design page count |
| Export polling | URLs expire 24h after `success` |
| OAuth refresh token inactivity | 90 days |
| Concurrent in-flight jobs per user | ~20 (matches the rate limit) |

Free plan also caps total designs and storage; Pro raises caps; Enterprise
removes most caps. The API does not expose plan-level quotas — you discover
them by hitting them.

## Cost Model

**Connect API itself is free.** There is no per-call charge, no metered
billing surface, and no developer pricing tier. The cost is the **Canva
subscription tier** of the user the integration acts on:

| Plan | Price (2026-04) | Connect API access |
|------|-----------------|---------------------|
| Free | $0 | Profile read, basic design list/create. No brand templates, no autofill. Heavy limits. |
| Canva Pro | ~$15/mo (US) | Brand Kit, full Designs/Exports/Assets/Folders/Comments API. **Still no Brand Template Autofill.** |
| Canva Teams | ~$10/user/mo (3 user min) | Same as Pro plus team features. Still no autofill. |
| Canva Enterprise | Contact sales (~$30/user/mo, 100+ users typical) | **Brand Template Autofill enabled.** Brand Hub. Required for the headline API. |

Practical EOS implication: the autofill workflow requires Enterprise. For
a pre-revenue solo founder this is the binding cost constraint. Workarounds:

1. Run the autofill workflow inside an existing Enterprise tenant where
   Antony already has access (e.g. as part of a client relationship).
2. Skip autofill, use the Designs + Exports + Assets APIs only (Pro tier),
   and keep template instantiation manual in the GUI.
3. Build a local Pillow-based renderer that produces the same PNGs from
   the same JSON inputs, and treat Canva as the *GUI design tool* only,
   not the rendering engine.

Plan choice for EOS today: Canva Pro for Antony's personal account.
Re-evaluate Enterprise when Initiate Arena hits $10K/month and the social
batch workflow is the bottleneck.

## Version Pinning

The Connect API does **not** use a header-based version selector. The
`v1` in the URL path has been stable since GA in 2024 and will be
versioned via path (`v2`) if/when it changes.

Behavior changes are announced in the **Changelog** at
canva.dev/docs/connect/changelog. The most consequential changes since GA:

- **2025-09 — Brand Template ID format migration.** Old IDs accepted for
  6 months, then 404. EOS action: refetch IDs after migration window.
- **2024 — Connect API GA.** Out of public beta.
- **2025 — Autofill expanded to support `chart` field type.**
- **2025 — Asset upload moved to async job pattern** for files over a
  threshold (was synchronous in beta).

EOS pinning strategy: pin the **OpenAPI spec commit hash** from
`canva-connect-api-starter-kit` in `eos_ai/.canva_spec_pin` and re-pull
quarterly. Diff the spec against the previous pin; investigate any
breaking renames before bumping.

For starter kit / openapi-ts based clients: pin `openapi-ts` version in
`package.json`, regenerate clients in CI, and fail the build on any
generated diff that wasn't reviewed.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Canva's design intent is **"design for everyone"** — taken literally as a
product principle, not a tagline. Every decision in the product traces
back to it: drag-and-drop above structured layout, templates above blank
canvases, AI suggestions above tutorials, real-time collaboration above
file versioning, brand kits above style guides. The tool is built for the
person who has never opened Photoshop and never will.

The tradeoffs are sharp and worth naming honestly:

**What Canva chose:**
- **Templates over primitives.** Most users start from a template, not
  a blank artboard. The template economy is the moat.
- **Smart-magic over precision.** Auto-align, snap-to-grid, suggested sizes,
  Magic Switch — Canva would rather guess right than make you specify.
- **Cloud-first.** Files live in Canva's cloud. Local saves are exports,
  not source files. There is no `.canva` file format on disk.
- **Web above desktop.** Desktop apps are wrappers around the web app.
  Mobile is first-class.
- **Composition above creation.** Most "design work" in Canva is selecting,
  arranging, and tweaking pre-built elements, not drawing from scratch.

**What Canva sacrificed:**
- **Pixel-perfect typographic control.** Canva's text engine is good but
  not Adobe-good. Kerning, optical sizing, OpenType features, hyphenation
  zones — limited or absent.
- **Vector authoring.** You can place SVGs and trace some shapes, but Canva
  is not Illustrator. There is no Bezier pen tool worth using.
- **Print pre-press.** PDF Print exists, but color-managed CMYK workflows
  with spot colors and ICC profiles are not Canva's strong suit.
- **Plugin ecosystem at the depth of Figma's.** The Apps SDK exists but
  the marketplace is curated, narrow, and focused on integrations rather
  than extending the editor itself.
- **File format interop.** Exports are clean; imports of PSD, AI, INDD are
  effectively absent. PPTX/DOCX/PDF in, Canva format out.

For EOS the right framing is: **Canva is the production layer for content
that doesn't need pre-press fidelity, where speed and template reuse
dominate.** Personal brand social posts, hoodie mockups, lead magnet
covers, IG carousels — yes. Print-shop posters with Pantone spots, complex
illustrated brand systems, photo-retouched portraits — no. Use Photoshop
or Illustrator for those (each gets its own skill in this wave).

## Problem-Solution Map and Hidden Capabilities

The features marketing surfaces are well known. The hidden capabilities
are where creator-level mastery lives.

**Hidden in the GUI:**

- **Magic Switch — format conversion.** Take a presentation, switch to a
  blog post, switch to an email, switch to a video script. Canva re-flows
  the content into a different design system. Underused. Killer for
  repurposing one piece of content into ten formats.
- **Magic Switch — language translation.** Same surface, different mode.
  Translates a design into 100+ languages while preserving layout. Useful
  for any global content workflow.
- **Magic Morph.** Apply a stylistic transformation to a selected element.
  Underrated for product mockup variations on Lyfe Spectrum apparel.
- **Magic Grab.** Lift a subject out of a photo and reposition it. Like
  Photoshop's content-aware tools but one click.
- **Magic Eraser.** Remove objects from photos. Faster than going to
  Photoshop for simple cleanups.
- **Magic Expand.** Extend a photo beyond its original frame using
  generative fill. Useful when stock photos are the wrong aspect ratio.
- **Background Remover.** One click. Was a pro feature, now standard.
- **Brand Voice (Magic Write).** Set a tone profile per brand and Magic
  Write conforms to it. Antony can keep separate Brand Voices for personal,
  Lyfe Spectrum, Lyfe Institute, Empyrean.
- **Content Planner.** Built-in social scheduler. Less powerful than
  Buffer/Later, but native to Canva — designs publish from inside the
  tool with no export step. Free in Pro.
- **Bulk Create (CSV → Designs).** GUI feature that does what Connect
  API's autofill does — instantiate a template per CSV row. Free in Pro.
  This is the EOS workaround for not having Enterprise: do bulk create in
  the GUI manually, schedule via Content Planner, skip the API entirely
  until you need >100 variants/day.
- **Frames.** Drop an image into a frame and it auto-clips. Combined with
  Smart Mockups (the underlying tech for `mockups.canva.com`), this is
  the fastest path to apparel/product visuals.
- **Smart Animate.** Auto-animate transitions between slides in a
  presentation by tweening matching elements. Surprisingly good.
- **Talking Photos.** Animate a still photo with generated lip-sync from
  a script. Use with caution — disclosure norms matter.
- **Brand Templates "lock" feature.** Lock specific elements (logo
  placement, brand color regions) so collaborators can edit text but
  cannot move the logo. The API respects locks. Use this when handing
  templates to non-designers.

**Hidden in the API:**

- **Imports endpoint** can convert a PPTX or DOCX to an editable Canva
  design — useful for migrating legacy decks once.
- **Resize endpoint** is a cheap way to fan out one design into all social
  formats without re-authoring.
- **Capabilities endpoint** lets you detect Enterprise membership before
  attempting an autofill that would 403 — query first, fail loudly on
  startup, not at runtime.
- **Comments API** can be used as a structured audit log for design
  approval workflows even when no humans see the comments.

## Operational Behavior and Edge Cases

- **Auto-save is real, version history is shallow.** Canva auto-saves
  continuously. Version history shows named restore points, but the
  granularity is coarse and rolling — it is not git. If you need diff-able
  history, export periodically and version-control the exports.
- **Edit URLs are signed and rotate.** `urls.edit_url` is not a stable
  URL; do not bookmark it long-term. Store `design.id` and regenerate.
- **Brand Kit propagation is eventually-consistent.** Change a brand color
  in Brand Hub, refresh a design with that color — it usually picks up
  the new value, but caching can delay it by minutes. Re-export to be sure.
- **Magic Studio outputs have generation watermarks in metadata** but not
  visually. Treat all AI-generated images as content that may need
  disclosure depending on platform rules.
- **The mobile app is not a subset.** Some features (Magic Studio surface,
  Brand Hub admin, certain export formats) are web-only. Don't promise
  Antony he can do something on iPhone Canva that requires desktop.
- **Real-time collaboration uses CRDTs.** Two people editing the same text
  field simultaneously merge. Two people moving the same element pick the
  most recent. There is no lock or conflict prompt.
- **Fonts are licensed, including in exports.** Canva-bundled fonts can
  be used in exports for any purpose; uploaded custom fonts inherit
  whatever license you uploaded under. Don't upload paid fonts to a
  shared brand kit you don't have multi-user license for.
- **Smart Mockups (the apparel/product mockup engine)** runs on a fixed
  catalog of mockup templates. New mockups appear regularly; the catalog
  is not user-extensible. For Lyfe Spectrum, audit the mockup catalog
  quarterly to see if better hoodie/tee mockups have shipped.
- **Print orders ship from Canva Print** — a separate paid service inside
  Canva. The API does not place print orders. To order printed Lyfe
  Spectrum apparel from Canva Print, use the GUI.
- **Whiteboards have infinite canvas semantics.** They behave differently
  from Designs in API metadata — `design_type` reports `whiteboard`, page
  count is 1, dimensions are virtual. Treat as a separate entity for
  workflow purposes.
- **Docs are first-class designs**, not a separate object. The Connect
  API treats a Canva Doc the same way as a Canva Presentation.

## Ecosystem Position and Composition

Canva sits in a specific competitive position: **the high-volume, low-skill,
template-driven, AI-assisted, all-in-one creative tool for non-designers.**
Its closest peers and how it composes (or competes) with each:

- **Figma** — adjacent. Figma is the design tool for product designers
  and dev-handoff workflows. Canva is the design tool for marketers and
  founders. Figma has a deeper component model and developer mode; Canva
  has a deeper template economy and AI surface. Compose by exporting from
  Figma → uploading to Canva as an image asset → using in social posts.
  Don't try to round-trip; the formats don't share enough.
- **Adobe Express** — direct competitor at the same template-economy
  layer. Express has tighter integration with Adobe Stock, Fonts, and the
  rest of Creative Cloud. Canva has a much larger template marketplace
  and a more mature AI surface. Most independent creators pick one and
  stay there.
- **Photoshop** — complementary, different layer. Canva does what
  Photoshop won't (templates, social formats, drag-drop). Photoshop does
  what Canva can't (pixel surgery, generative fill at high quality, color
  management). Compose: edit photos in Photoshop → save as PNG → upload
  as asset → drop into Canva template. Each is its own EOS skill in this
  wave.
- **Illustrator** — same story for vectors. Authoring in Illustrator,
  composing in Canva. Each its own skill.
- **Photopea** — free in-browser Photoshop clone. Useful as a fallback
  when Antony doesn't want to open Photoshop. Compose with Canva the same
  way.
- **Buffer / Later / Hootsuite** — Canva's Content Planner overlaps with
  the simplest features of these. For multi-account scheduling with
  analytics, EOS still uses an external scheduler; Content Planner is
  good enough for a single-user single-brand cadence.
- **Notion / Coda** — content briefs and outlines live there; designs
  come to Canva. The bridge is manual: copy text from Notion, autofill
  via API.
- **Shopify / Stan / Beehiiv / Substack** — Canva produces the assets,
  these distribute. Shopify product images, newsletter cover images,
  Substack section graphics — all Canva exports.
- **Leonardo.ai (now owned by Canva, surfaced as Dream Lab)** —
  internal. Dream Lab on the Phoenix model is the high-quality image
  generator inside Canva. Treat it as Canva's answer to Midjourney; no
  separate account needed for Pro+ users.
- **Affinity (Designer / Photo / Publisher) — recently acquired by Canva.**
  Roadmap signals point to Affinity becoming the "pro tier" for users
  who outgrow Canva. Expect deeper Canva ↔ Affinity round-tripping over
  the next 12-24 months.

The EOS composition pattern: **Notion writes the words, Canva makes the
visuals, the API stitches them together, social schedulers distribute.**
Canva sits in the middle as the production layer.

## Trajectory and Evolution

The trajectory matters for skill durability — what to build for, what to
expect to be replaced.

- **2013-2018 — Template economy.** Canva became the dominant template
  marketplace for non-designers. Built the moat.
- **2019-2021 — Brand Kit and team features.** Pivot from individual
  creators to teams and SMBs. Brand Hub introduced.
- **2022-2023 — Magic Studio launch.** AI features layered onto every
  surface — text, image, video, format, language. The "design for
  everyone" thesis accelerated.
- **2024 — Connect API GA.** External systems can now drive Canva
  programmatically. Major shift: Canva goes from product to platform.
- **2024 — Leonardo.ai acquisition.** Brought Phoenix model in-house,
  surfaced as Dream Lab. Closed the gap with Midjourney for native users.
- **2024 — Affinity acquisition.** Tells us where Canva is going at the
  high end: a "pro tier" for designers who need more than Magic Studio
  can deliver.
- **2025 — Brand Template ID migration, autofill chart support, async
  asset uploads.** API maturity work.
- **2025 — Canva Enterprise push.** Aggressive sales motion into large
  orgs; Brand Hub and Connect API become the wedge.
- **2025-2026 — Continued AI expansion.** Magic Studio adds Talking
  Photos, Magic Morph, Magic Grab, Brand Voice. The AI surface grows
  faster than any other surface.
- **2026 (likely) — Webhooks for Connect API.** Strong roadmap signal.
- **2026-2027 (likely) — Affinity ↔ Canva round-tripping.** Probably the
  next major platform move.
- **2027 (speculative) — IPO.** Canva has filed signals; pricing and
  enterprise tier discipline will likely tighten in the run-up.

For EOS skill durability: the Connect API surface is stable enough to
build on, the autofill pattern is the durable core, and Magic Studio is
where the most movement happens — expect to re-research Magic Studio
features quarterly. The OAuth + PKCE auth is locked in; don't expect that
to change.

## Conceptual Model and Solution Recipes

The single mental model that unlocks Canva: **everything is either a
template or an instance of a template.** Brand Kit defines the visual
language. Brand Templates compose the language into reusable schemas.
Designs are instances of those schemas. Magic Studio is an AI accelerant
that lives in the GUI and helps produce templates faster; the API
instantiates templates at scale.

Once you hold this model, every workflow is one of three recipes:

**Recipe 1 — Design once, autofill many (the headline pattern).**
1. Antony designs a Brand Template in the GUI for a specific format
   (e.g. IG square post with `headline`, `subhead`, `cta`, `hero`).
2. Mark the fillable fields with the Brand Template tool in the GUI.
3. Save and note the brand template id (`DAF...`).
4. Agent reads `GET /brand-templates/{id}/dataset` to discover field names.
5. For each content row in Neon, agent uploads the hero image to
   `/v1/asset-uploads`, polls until success, then calls `POST /v1/autofills`
   with `{headline, subhead, cta, hero_image}`.
6. Agent polls the autofill job, gets the new design id.
7. Agent calls `POST /v1/exports` for PNG, polls, downloads, persists.
8. Agent hands off to the publisher.

**Recipe 2 — Resize and repurpose (the Magic Switch alternative).**
1. Antony creates a hero design in one format (e.g. IG square).
2. Agent calls `POST /v1/resizes` with target format `instagram_story`,
   `linkedin_post`, `twitter_post`.
3. Agent gets back N new designs at the new dimensions.
4. Each is exported and published.
5. For format conversions Magic Switch handles better (presentation →
   blog post), do it manually in the GUI; the API can't reproduce the
   AI-driven re-flow.

**Recipe 3 — Asset library + manual GUI compose (the Pre-Enterprise pattern).**
1. Agent batches assets into Canva via `/v1/asset-uploads` from a Neon
   queue (e.g. nightly: every new product photo, every podcast cover).
2. Agent organizes them into folders via the Folders API.
3. Antony, in the GUI, designs new content using the pre-uploaded assets —
   no autofill, no Enterprise required.
4. Antony publishes via Content Planner.
5. The boundary: agents handle ingestion and organization; humans handle
   composition. This recipe works on Pro tier and is the EOS default
   until Initiate Arena revenue justifies Enterprise.

## Industry Expert and Cutting-Edge Usage

The frontier of Canva usage in 2026 — what teams that have mastered the
tool actually do:

- **Template businesses.** Selling Canva templates is a real category.
  Top creators run shops on Etsy, Creative Market, and their own sites
  with $5-50 templates. The Brand Template + Bulk Create workflow is the
  production engine. Worth knowing as a business model even if EOS isn't
  pursuing it directly.
- **Bulk Create in the GUI as the poor-person's autofill.** Teams without
  Enterprise pipe a Google Sheet into Bulk Create and generate hundreds
  of variants in one batch. EOS pre-Enterprise pattern: maintain a
  `content/canva_bulk_create_YYYY-MM-DD.csv` file, upload weekly, batch
  schedule.
- **AI-driven content factories.** GPT or Claude writes the copy, Magic
  Media generates the imagery, Brand Kit enforces consistency, autofill
  ships variants. Cycle time: 1 minute per post. Frontier teams produce
  hundreds of pieces per day this way.
- **Brand Voice as a content compliance layer.** Teams set Brand Voice
  per sub-brand, then use Magic Write's voice-conformance check to
  flag any text that drifts from the voice profile. Used as a soft
  brand-guideline enforcement step.
- **Talking Photos for low-budget personal video.** Founders without a
  studio use Talking Photos to produce clean speaking-head clips from a
  single still + script. Disclosure norms are evolving; use with judgment.
- **Whiteboards for async strategy.** Frontier teams are using Canva
  Whiteboards as the primary visual collaboration surface instead of
  Miro, especially on the Canva-native side of the org. Cheaper, same
  Brand Kit, fewer tools to maintain.
- **Print integration with on-demand fulfillment.** Lyfe Spectrum
  competitors run apparel fulfillment through Printful + Canva mockups
  in a single loop: design hoodie in Canva, mock up in Smart Mockups,
  upload to Printful, sell on Shopify. End-to-end inside two tools.
- **Multi-brand template management at agencies.** Agencies running 20+
  client brands use one Canva Enterprise tenant per client, switch via
  Brand Hub, and isolate Brand Kits per project. EOS, with 4-6 brands,
  uses one tenant with multiple Brand Kits.
- **API-driven personalization at scale.** Cold outreach with personalized
  one-pagers per prospect: name, company, industry inserted into a Brand
  Template via autofill, exported as PDF, attached to an email. EOS
  Initiate Arena pattern when outreach scales past 100/day.

The pattern that ties all of these together: **leverage the template
economy plus the AI surface; let the API handle the variants.** Anyone
designing each post from scratch is using Canva at the wrong level.

---

## EOS Usage Patterns

These are the four canonical patterns EOS uses Canva for. Each is a
named workflow with a clear human ↔ agent boundary.

### Pattern 1 — Personal brand template system (Antony, weekly)

Antony maintains a small Brand Template library in his Canva Pro account
for the personal brand: IG square post, IG carousel page, IG Reel cover,
LinkedIn square, X 1600x900, YouTube thumbnail, profile header. Each
template uses the Lyfe Institute palette from Brand Kit. Each has a
small, named field set: `headline`, `subhead`, `cta`, `hero_image`,
optional `quote_attribution`.

Weekly cadence:
- Sunday: review templates in GUI, refresh any that feel stale, run
  Magic Design on a few prompts to seed new template ideas.
- Daily: content brief in Notion → fields populated → next day's posts
  generated (currently in GUI Bulk Create; flips to Connect API
  autofill when on Enterprise).

EOS file: `eos_ai/canva_templates.json` lists each template's id and
field schema, so agents can target them programmatically.

### Pattern 2 — Lyfe Spectrum product mockup autofill (agent-driven)

Lyfe Spectrum has a master Brand Template per garment type (hoodie, tee,
cap, joggers) with fields: `garment_color`, `print_design`, `model_pose`,
`tagline`. The print_design is an asset id (uploaded once per design),
the others are text or selection.

Pipeline:
1. New product design lands in `/opt/OS/lyfe_spectrum/designs/incoming/`.
2. `eos_ai.lyfe_spectrum.canva_mockup_worker` picks it up, uploads as
   asset, gets `MAF...` id.
3. For each (color, garment) combo in the SKU matrix, calls autofill on
   the right brand template.
4. Polls, exports as PNG at 2000x2000, downloads to
   `/opt/OS/lyfe_spectrum/mockups/YYYY-MM-DD/`.
5. Pushes filenames into Neon `lyfe_spectrum_mockups` table.
6. Shopify sync picks up new mockups and updates product images.

Currently runs in dry-run mode (Pro tier, no autofill). Promotes to
real autofill when Lyfe Spectrum hits its first revenue or when EOS
joins an Enterprise tenant.

### Pattern 3 — Initiate Arena social batch generator (agent-driven)

Initiate Arena content lives in Notion. Each row is one piece of content
with `headline`, `body`, `cta`, `hero_image_url`. The
`canva_social_batch` worker runs nightly:

1. Pulls tomorrow's content from Notion.
2. For each piece, downloads the hero image from the URL, uploads to
   Canva via `/v1/asset-uploads`, polls.
3. For each (piece, platform) pair — IG square, IG story, LinkedIn,
   X — calls autofill on the matching brand template.
4. Polls the 5-20 autofill jobs in parallel (under the 20-in-flight cap),
   exponential backoff.
5. For each resulting design, calls export PNG, polls, downloads.
6. Persists exported PNGs to `/opt/OS/initiate_arena/social/YYYY-MM-DD/`.
7. Hands off to `social_publisher` skill which schedules via Content
   Planner or external scheduler.

Verification step (mandatory in EOS): after a run, check that
`mockup_count == content_count * platform_count` and that every PNG is
non-zero bytes. Failures alert via Discord.

### Pattern 4 — Magic Studio GUI workflows for hero designs (Antony, ad-hoc)

For any "hero" piece — landing page hero image, lead magnet cover, sales
page section graphics, podcast cover art, video thumbnails for hero
videos — Antony designs in the GUI, using Magic Studio:

- Magic Design for first-draft layouts from a prompt.
- Dream Lab (Magic Media) for original photography-style imagery.
- Magic Edit for tweaking generated imagery.
- Background Remover for compositing product shots.
- Magic Grab + Magic Eraser for cleanup.
- Brand Voice (Magic Write) for headline copy aligned to brand voice.

These are never run via the API. They are explicitly the human creative
loop. Outputs are saved as Brand Templates if they will be reused, or
as one-off designs if they are unique.

The boundary rule: **if it requires creative judgment, it happens in
the GUI. If it requires variation at scale, it happens via the API.**

---

## Gotchas

- **Brand Template + Autofill require Canva Enterprise membership.**
  Pro and Free 403 on `/v1/brand-templates` and `/v1/autofills`. The
  binding constraint for solo founder pre-revenue. Workarounds: GUI
  Bulk Create, manual templates, or wait for revenue to justify
  Enterprise.
- **September 2025 Brand Template ID migration.** Old IDs accepted for
  6 months; after that, 404. If any EOS config was generated before
  Sept 2025, refetch via `GET /v1/brand-templates`.
- **Scopes do not imply each other.** `asset:write` without `asset:read`
  means upload-only. `design:content:write` does not grant
  `design:content:read`. Always request both halves.
- **Re-consent required when scopes change.** Adding a scope does not
  upgrade existing refresh tokens; users must re-authorize.
- **Autofill field types must match dataset exactly.** Read the dataset
  before calling autofill. `text` only takes `text`, `image` only takes
  `asset_id`, `chart` only takes `chart_data`.
- **Image autofill takes `asset_id`, not URL.** Upload first via
  `/v1/asset-uploads`, poll until success, use the resulting `asset.id`.
- **Export jobs are async, download URLs expire in 24h.** Persist the
  binary to your own storage immediately.
- **Rate limits are per-endpoint, per-user, per-minute.** Notable:
  exports 20/min create, 120/min poll. Use exponential backoff. Naive
  100ms polling trips 429 in 12 seconds.
- **`Retry-After` is in seconds**, not milliseconds.
- **PDF Print vs PDF Standard.** Specify `export_quality=pro` for print.
  Standard PDFs sent to a printer will look wrong.
- **Magic Studio is GUI-only.** No Magic Design, Magic Media, Magic Switch,
  Magic Edit, Brand Voice via API. Plan workflows around: human designs
  in GUI, agent autofills.
- **OAuth callback host must match exactly** in production. HTTPS public
  domain. Localhost only in dev.
- **No webhooks for design lifecycle events.** As of 2026-04. Poll
  `GET /v1/designs` and diff `updated_at` against a watermark.
- **Comments API has no realtime push.** Useful as audit trail, not
  for live notifications.
- **Free plan cannot use Connect API for production work.** Pro is the
  practical floor for non-autofill use; Enterprise for autofill.
- **`design.id` is stable, but `urls.edit_url` rotates.** Store the id,
  regenerate URLs on demand.
- **Asset IDs are scoped to the uploading user.** An asset uploaded
  under user A cannot be referenced in autofill acting as user B unless
  in a shared folder.
- **Refresh tokens expire after 90 days of inactivity.** Run a weekly
  heartbeat refresh in EOS to keep them warm.
- **`POST /v1/designs` with `design_type.preset` does not support every
  preset name** — check the docs for the supported list. Unknown presets
  return 400.
- **PPTX/DOCX import retains layout but not animations** for PPTX, and
  not heavy formatting for DOCX. Treat imports as starting points,
  not faithful conversions.
- **Bulk Create in the GUI has a 300-row cap per batch.** Larger sets
  must be split.
- **Canva's font catalog occasionally rotates** — a font you used in a
  brand template six months ago may have been removed. Designs still
  render but the GUI shows a substitution warning.
- **Whiteboard exports are limited.** PNG works, PDF is single-page,
  there is no "tiled" export of a large whiteboard.
- **`thumbnail.url` on designs and brand templates is signed and short-lived.**
  Like `urls.edit_url`, do not store long-term.
- **Magic Studio outputs may include subtle generation artifacts** —
  always do a human visual check before publishing AI-generated imagery
  to brand-critical surfaces.
- **The "free trial" of Enterprise** offered through sales is bounded,
  and downgrading after trial expiration deletes Brand Hub data that
  doesn't fit in Pro Brand Kit. Don't store the only copy of brand
  assets in an Enterprise trial.
- **Connect API Postman collection lags the docs by weeks.** Treat
  canva.dev as the source of truth, not Postman.
- **`canva-connect-api-starter-kit` requires Node 20.14.0 exactly** —
  use nvm and the included `.nvmrc`. Mismatched Node versions cause
  silent generation failures in `openapi-ts`.
- **Resize endpoint creates a new design, not an in-place transform.**
  The original is untouched; you now have two designs to manage.
- **`POST /v1/designs` does not let you place elements.** It creates a
  blank design. To populate it, you either autofill from a brand template
  or import from a file. There is no programmatic element insertion.
- **Brand Voice profiles do not sync to the API.** They live inside Magic
  Write, invisible to Connect. Brand consistency for API-generated content
  has to come from the Brand Template design, not Brand Voice.
