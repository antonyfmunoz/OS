# Acrobat — Creator-Level Best Practices
Source: developer.adobe.com/document-services, opensource.adobe.com/acrobat-sign, helpx.adobe.com/acrobat
API Version: PDF Services REST v3, Acrobat Sign REST v6
SDK Version: pdfservices-sdk Python 4.x / Node 4.x; Acrobat Pro DC 2024+
Last Researched: 2026-04-06

This is a hybrid surface skill. Three Adobe products share document
DNA but live in three different worlds: the headless PDF Services API
(REST + multi-language SDK), the Acrobat Pro desktop GUI (the founder
tool), and the Acrobat Sign API (e-signature, separate auth, separate
shards). Treat them as three integrations that compose, not one.

---

# Tier 1 — Technical Mastery

## Authentication

PDF Services API authenticates via **Adobe IMS OAuth Server-to-Server**
using the `client_credentials` grant type. As of June 30, 2025 the
legacy JWT/Service Account credential type reached end-of-life and no
longer issues tokens. Any tutorial, sample, or SDK version that
references `private.key`, JWT assertions, or `ServiceAccountCredentials`
is obsolete and will fail.

The flow:

```
POST https://ims-na1.adobelogin.com/ims/token/v3
Content-Type: application/x-www-form-urlencoded

client_id=<CLIENT_ID>
client_secret=<CLIENT_SECRET>
grant_type=client_credentials
scope=openid,AdobeID,DCAPI
```

Successful response:

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 86399
}
```

There is **no refresh token** under client_credentials. When the token
expires (24 hours minus a second), call the token endpoint again. The
correct caching strategy is:

1. Cache `(access_token, expires_at)` in memory or Redis
2. Re-fetch when `now > expires_at - 60s` (60-second safety margin)
3. On any 401 from a downstream API, force re-fetch and retry once

Every PDF Services API request needs **two** authentication headers:

```
Authorization: Bearer <access_token>
x-api-key: <CLIENT_ID>
```

The `x-api-key` requirement is buried in the Acrobat Services docs and
omitted from many third-party tutorials. Without it you get
`401 unauthorized` even with a valid bearer token. The value of
`x-api-key` is literally your `client_id` — yes, the same value used
in the token request. Adobe IMS treats the client_id as both an
identity and an API key.

**Acrobat Sign authenticates separately.** It is a different product
under the same brand, with its own integration keys and its own
OAuth flow. Sign uses **shard-scoped** tokens: when you provision an
integration key in the Sign admin panel, it is bound to a specific
data center (NA1, EU1, JP1, AU1, IN1). The first call you make MUST
be to `api.adobesign.com/api/rest/v6/baseUris`, which returns the
correct shard URL (e.g. `https://api.na1.adobesign.com`). All
subsequent calls go to that shard. Hardcoding `api.adobesign.com`
works exactly once.

Acrobat Pro desktop has no auth — it is a licensed local app signed
into the user's Adobe ID via Creative Cloud. There is no API surface
on the desktop product itself.

## Core Operations with Exact Signatures

PDF Services exposes a uniform 4-step pattern for every operation:
**(1) get presigned upload URI, (2) PUT file to URI, (3) submit job,
(4) poll Location header**. Operation endpoints differ only in the
URL path and request body schema.

### Step 1 — Get presigned upload URI

```
POST https://pdf-services.adobe.io/assets
Authorization: Bearer <token>
x-api-key: <client_id>
Content-Type: application/json

{ "mediaType": "application/pdf" }
```

Response (200):
```json
{
  "uploadUri": "https://dcplatformstorageservice.blob.core.windows.net/...",
  "assetID": "urn:aaid:AS:UE1:abc123..."
}
```

`mediaType` accepts: `application/pdf`, `image/jpeg`, `image/png`,
`text/html`, `text/plain`, `application/vnd.openxmlformats-...` for
Office formats, `application/zip` (for HTML bundles).

### Step 2 — PUT file to presigned URI

```
PUT <uploadUri>
Content-Type: <same mediaType>
<binary body>
```

This call goes directly to Azure Blob Storage. **Do NOT include any
Adobe headers** (no Authorization, no x-api-key) — the SAS token in
the URL is the auth, and adding Adobe headers triggers a 403 from the
storage layer. Returns 200 with empty body.

### Step 3 — Submit operation

```
POST https://pdf-services.adobe.io/operation/<op>
Authorization: Bearer <token>
x-api-key: <client_id>
Content-Type: application/json

{ "assetID": "urn:aaid:AS:UE1:abc123...", ...op-specific params }
```

Returns **201 Created** with empty body and a `Location` header
pointing at the job status URL. This is the most common point of
confusion: 201 + empty body looks like an error to people expecting
JSON, but it is the correct success response.

### Step 4 — Poll Location URL

```
GET <Location>
Authorization: Bearer <token>
x-api-key: <client_id>
```

Returns one of three states:

```json
// in flight
{ "status": "in progress" }

// success
{
  "status": "done",
  "asset": {
    "downloadUri": "https://dcplatformstorageservice.blob...",
    "assetID": "urn:aaid:AS:UE1:..."
  }
}

// failure
{
  "status": "failed",
  "error": { "code": "BAD_PDF", "message": "..." }
}
```

Some operations (extractpdf, splitpdf, exportpdftoimages, combinepdf)
return multiple result assets and use `assetList` instead of `asset`.
Always check both fields.

### Operation catalog

Every endpoint below is `POST https://pdf-services.adobe.io/operation/<x>`:

| Endpoint | Inputs | Outputs | Notes |
|---|---|---|---|
| `createpdf` | DOCX/XLSX/PPTX/TXT/RTF | PDF | Office formats, fonts embedded |
| `htmltopdf` | HTML URL or zipped HTML asset | PDF | Pass `htmlToPDFParams` for layout |
| `exportpdf` | PDF | DOCX/XLSX/PPTX/RTF | Specify `targetFormat` |
| `extractpdf` | PDF | ZIP (JSON + tables/ + figures/) | Sensei OCR + layout |
| `ocr` | scanned PDF | searchable PDF | `ocrLang` required |
| `compresspdf` | PDF | PDF (smaller) | `compressionLevel`: LOW/MEDIUM/HIGH |
| `linearizepdf` | PDF | linearized PDF | For fast web view |
| `protectpdf` | PDF | encrypted PDF | `passwordProtection` block |
| `removeprotection` | encrypted PDF | PDF | needs `password` field |
| `combinepdf` | array of assetIDs | merged PDF | up to 20 inputs, 100 pages each |
| `splitpdf` | PDF | array of PDFs | by `pageCount`, `pageRanges`, or `fileCount` |
| `pagemanipulation` | PDF | modified PDF | insert/delete/replace/rotate/reorder |
| `exportpdftoimages` | PDF | PNG/JPEG per page | `outputFormat`, `pageRanges` |
| `pdfproperties` | PDF | JSON metadata | page count, version, compliance |
| `documentgeneration` | DOCX template + JSON | PDF/DOCX | mailmerge with Word tags |
| `autotag` | PDF | tagged PDF + report | accessibility, expensive |
| `electronicseal` | PDF + cert info | sealed PDF | requires seal credential |

### Acrobat Sign REST v6 — core operations

```
POST   /api/rest/v6/transientDocuments      Upload (24h lifetime)
POST   /api/rest/v6/agreements              Create + send for signature
GET    /api/rest/v6/agreements/{id}         Status
GET    /api/rest/v6/agreements/{id}/combinedDocument   Final signed PDF
POST   /api/rest/v6/agreements/{id}/state   Cancel
POST   /api/rest/v6/widgets                 Embeddable signing widget
POST   /api/rest/v6/megaSigns               Bulk send (one doc, many signers)
POST   /api/rest/v6/libraryDocuments        Reusable templates
GET    /api/rest/v6/users/me                Whoami / shard probe
POST   /api/rest/v6/webhooks                Register webhook
GET    /api/rest/v6/webhooks                List webhooks
DELETE /api/rest/v6/webhooks/{id}           Unregister
```

## Pagination Patterns

PDF Services itself has no pagination — it is operation-oriented, not
list-oriented. There are no list endpoints to paginate over.

Acrobat Sign uses **cursor pagination** with a `cursor` query param
on every list endpoint. The response shape is:

```json
{
  "userInfoList": [...],
  "page": {
    "nextCursor": "eyJpZCI6MTIzfQ=="
  }
}
```

When `nextCursor` is absent, you have reached the end. Pass it as
`?cursor=<value>` on the next request. Never assume `pageSize` is
honored — Sign caps it server-side at 100.

For `splitpdf` and `extractpdf`, the result `assetList` is not
paginated — Adobe streams every result asset URI in one shot. With
extracted figures from a 500-page document this can be a 5MB+ JSON.
Plan accordingly.

## Rate Limits

PDF Services rate limits are not published as requests-per-second;
they are billed in **Document Transactions** (DTs):

| Operation | DT cost |
|---|---|
| createpdf, compresspdf, htmltopdf, ocr, protectpdf, combinepdf, splitpdf, etc. | 1 DT per 50 pages |
| extractpdf, pdfToMarkdown | 1 DT per 5 pages |
| autotag | **10 DT per page** (expensive) |
| electronicseal | 10 DT per PDF |

Free tier: 500 DTs/month for 6 months, then the credentials stop
working. Paid tier (per community 2024 pricing): minimum 500,000 DTs
per year at ~$0.05/call, contract-only via Adobe sales.

There IS a soft request-rate ceiling — bursts above ~25 concurrent
jobs per credential get throttled with `429 Too Many Requests` and a
`Retry-After` header (in seconds). Honor it; do not retry without
backoff.

Acrobat Sign has documented rate limits:
- **30 transactions per minute per API user** for most endpoints
- **2,000 transactions per hour per integration key** as a soft cap
- Webhook delivery uses doubling backoff: 1 min, 2 min, 4 min...
  up to 12h, totaling 15 retries over 72 hours

Both products return `429` with a `Retry-After` header on throttle.

## Error Codes and Recovery

PDF Services error codes (from job status `error.code`):

| Code | Meaning | Recovery |
|---|---|---|
| `BAD_PDF` | Input file is corrupt or has Reader Extended rights | Flatten with PyMuPDF, retry |
| `DISQUALIFIED` | Input doesn't match operation (e.g. OCR on already-OCRed) | Skip operation |
| `TIMEOUT` | Job exceeded 10-min processing window | Split input, retry |
| `INVALID_INPUT` | Schema mismatch in request body | Fix params, do not retry blindly |
| `FILE_TOO_LARGE` | Single asset over 100MB or 1500 pages | Split before upload |
| `UNKNOWN` | Internal Adobe error | Retry once with 5s backoff |
| `RATE_LIMITED` | Throttle | Honor Retry-After |
| `QUOTA_EXCEEDED` | Out of DTs for the month | Stop, alert |

HTTP-level errors:

| HTTP | Cause | Action |
|---|---|---|
| 400 | Malformed JSON / missing required field | Fix and resubmit |
| 401 | Token expired or `x-api-key` missing | Re-auth, retry once |
| 403 | Wrong scope / asset not owned by caller | Check IMS scopes |
| 404 | Polling Location too fast (race) OR job expired (24h) | Sleep 1s, retry once; if persistent, job is gone |
| 409 | Asset still uploading | Wait 1s, retry |
| 415 | mediaType mismatch | Fix Content-Type on PUT |
| 429 | Rate limited | Honor Retry-After |
| 5xx | Adobe internal | Exponential backoff: 2s, 4s, 8s, 16s, 32s, give up |

The single most common production failure is the **404-on-fast-poll
race**: submitting a job and immediately GET-ing the Location header
returns 404 because the job record hasn't propagated yet. Mitigation:
sleep 1 second before the first poll. The Adobe SDK already does this;
custom HTTP clients usually do not.

Acrobat Sign error codes are descriptive strings, not numbers:
`INVALID_TRANSIENT_DOCUMENT_ID`, `EMPTY_AGREEMENT_NAME`,
`MISCONFIGURED_WEBHOOK_URL`, `WEBHOOK_VERIFICATION_FAILED`, etc.
They come back in a JSON body with HTTP 400.

## SDK Idioms

The Python SDK (`pdfservices-sdk` v4.x) hides the 4-step pattern
behind a `submit/get_job_result` API:

```python
from adobe.pdfservices.operation.auth.service_principal_credentials \
    import ServicePrincipalCredentials
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type \
    import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.ocr_pdf_job import OCRPDFJob
from adobe.pdfservices.operation.pdfjobs.result.ocr_pdf_result \
    import OCRPDFResult

creds = ServicePrincipalCredentials(
    client_id=os.getenv("ADOBE_CLIENT_ID"),
    client_secret=os.getenv("ADOBE_CLIENT_SECRET"),
)
svc = PDFServices(credentials=creds)

with open("scan.pdf", "rb") as f:
    asset = svc.upload(input_stream=f.read(),
                       mime_type=PDFServicesMediaType.PDF)

job = OCRPDFJob(input_asset=asset)
location = svc.submit(job)                       # returns the Location URL
result = svc.get_job_result(location, OCRPDFResult)  # blocks, polls internally
output_asset = result.get_result().get_asset()
stream = svc.get_content(output_asset)
open("searchable.pdf", "wb").write(stream.get_input_stream())
```

The SDK handles: token caching with auto-refresh, the upload PUT
(no extra headers), the polling loop with the 1s initial delay, and
exponential backoff on 5xx. **Use the SDK by default.** Drop to raw
HTTP only when you need cron-friendly bash, when you need to interleave
operations on different events, or when you need explicit control over
the polling cadence (e.g. webhook-driven).

The Node SDK (`@adobe/pdfservices-node-sdk` v4.x) mirrors the Python
shape one-to-one. The Java SDK is older and uses `Operation.execute()`
synchronously — it works but its threading model is different.

For Acrobat Sign, the official SDK is unmaintained. Use the REST API
directly with `requests` (Python) or `axios` (Node).

## Anti-Patterns

- **Polling Location with no initial delay** — race condition, 404.
- **Including `Authorization` headers on the PUT upload** — 403.
- **Treating 201 + empty body as failure** — it is success, the
  Location header is the truth.
- **Caching the downloadUri in a database** — it expires in 24h.
  Cache the assetID if anything; even that expires in 24h.
- **Using JWT auth in 2026** — dead since June 30, 2025.
- **Calling `api.adobesign.com` for actual work** — that hostname is
  shard discovery only. Use the returned shard hostname.
- **Calling `extractpdf` on a scanned PDF without OCR first** — you
  get garbage characters, not text. OCR first, then extract.
- **Running `autotag` over an entire library at once** — 10 DT per
  page burns through your monthly quota in one job.
- **Synchronous Office-to-PDF conversions in a request handler** —
  jobs take 5-30 seconds. Always run async with a webhook or queue.
- **Filling Acrobat Pro forms server-side then sending to PDF Services**
  if the form has Reader Extended rights — flatten first or you get
  BAD_PDF.
- **Hardcoding `compressionLevel` HIGH** — degrades scanned text and
  embedded images. MEDIUM is the right default for storage.
- **Trusting the HTML-to-PDF renderer with external CDN assets** —
  the renderer has no internet by default. Inline CSS or zip the bundle.

## Data Model

PDF Services has a tiny data model:

- **Asset** — `(assetID, downloadUri | uploadUri, mediaType, lifetime=24h)`.
  Owned by the credential that created it. Not shareable across
  credentials. Identified by an `urn:aaid:AS:UE1:...` URN.
- **Job** — `(location, status, asset | assetList | error, createdAt)`.
  Lives at the Location URL for 24h after creation. State machine:
  `created → in progress → done|failed`.
- **Operation** — stateless verb. No persistence. Each POST creates
  a fresh job.

There are NO concepts of users, projects, folders, or tags inside
PDF Services — it is pure compute. Tracking provenance, ownership,
and tags is the caller's responsibility.

Acrobat Sign has a much richer model:

- **Agreement** — the unit of e-signature work. States:
  `DRAFT → AUTHORING → IN_PROCESS → SIGNED|CANCELLED|EXPIRED|REJECTED`.
- **ParticipantSet** — ordered group of signers/approvers/cc.
  Order matters when `signatureFlow` is `SEQUENTIAL`.
- **TransientDocument** — uploaded file, 24h lifetime, single-use.
- **LibraryDocument** — reusable template, persistent.
- **Widget** — embeddable always-on signing form.
- **MegaSign** — bulk send (one doc, many signers, parallel agreements).
- **Webhook** — subscription resource with scope (ACCOUNT/GROUP/USER/RESOURCE).

## Webhooks and Events

PDF Services has **no webhooks**. Async = polling. If you need
push notifications, wrap the SDK in your own queue + worker that
emits events to your bus.

Acrobat Sign has full webhook support. Create with:

```
POST /api/rest/v6/webhooks
{
  "name": "EOS contract pipeline",
  "scope": "ACCOUNT",
  "state": "ACTIVE",
  "webhookSubscriptionEvents": [
    "AGREEMENT_CREATED",
    "AGREEMENT_ACTION_COMPLETED",
    "AGREEMENT_WORKFLOW_COMPLETED",
    "AGREEMENT_EXPIRED",
    "AGREEMENT_REJECTED"
  ],
  "webhookUrlInfo": { "url": "https://eos.example.com/webhooks/sign" },
  "webhookConditionalParams": {
    "webhookResourceEvents": {},
    "webhookNotificationApplicableUsers": "BOTH_SELF_AND_OTHERS"
  }
}
```

**Verification handshake:** before accepting the webhook, Acrobat Sign
sends a `GET` to your URL with header `X-AdobeSign-ClientId`. Your
endpoint must echo that header back in the response (both as a header
AND in the JSON body `{"xAdobeSignClientId": "..."}`) within 10 seconds.
Plain HTTP is rejected — HTTPS with a valid CA cert only.

Retry policy: doubling backoff starting at 1 minute, capping at 12
hours, total 15 attempts over 72 hours. After 72h of failures the
webhook is auto-deactivated.

Event payloads contain `event`, `agreement`, `participantUser`,
`actionType`, `eventDate`, and a signed JWT (`x-adobesign-clientid`
header) for verification. Verify the JWT signature in production.

## Limits

PDF Services hard limits:

- **File size**: 100 MB per asset
- **Page count**: 1500 pages per PDF input (most ops); 200 pages for
  extractpdf with tables
- **Combine**: 20 input PDFs max, 100 pages each
- **Job lifetime**: 24h (status URL + downloadUri both expire)
- **Asset lifetime**: 24h
- **Concurrent jobs per credential**: ~25 before throttling
- **Token lifetime**: 86399 seconds (24h - 1s)
- **HTML to PDF**: zipped bundles up to 100 MB; remote URLs must
  resolve in <30s

Acrobat Sign hard limits:

- **TransientDocument lifetime**: 24h
- **Agreement file size**: 25 MB total per agreement
- **Files per agreement**: up to 100 documents merged into one
- **Recipients per agreement**: up to 25
- **MegaSign recipients**: up to 1000
- **API rate**: 30 req/min/user, 2000 req/hour/integration
- **Webhook URL response timeout**: 10s

Acrobat Pro desktop hard limits: none material — it is a local app.
The largest PDF the GUI can comfortably edit is around 2 GB / 9000
pages before the redaction tool starts thrashing.

## Cost Model

PDF Services billing is **transaction-based**, not time-based or
seat-based. One Document Transaction (DT) is the unit. See Rate Limits
section for the cost table. Free tier is 500 DTs/month for 6 months
total — useful for prototyping, useless for production.

Real-world EOS budget math:
- Generating 100 onboarding packets/month: 100 DTs (createpdf, ~5 pages each)
- OCRing 50 scanned letters/month: 50 DTs
- Extracting structured JSON from 20 contracts: ~20 DTs (most under 5 pages)
- Compressing every output before storage: ~170 DTs
- **Total: ~340 DTs/month** — comfortably inside free tier

If autotag enters the picture, add 10 DT per page across the entire
processed corpus and the budget explodes immediately.

Acrobat Sign is priced per envelope/transaction at the account level
through Adobe sales — no public per-call pricing. Solo plans start
around $15/user/month with limited transactions; team and enterprise
plans add API access and webhooks.

Acrobat Pro is $19.99/month standalone or bundled in Creative Cloud
All Apps. Single-seat. No metering.

## Version Pinning

Pin SDK versions explicitly. Adobe is aggressive about deprecating
SDK majors (the JWT->OAuth migration broke v3.x).

```
# Python
pdfservices-sdk==4.2.0      # current as of 2026-04
google.genai==0.5.0         # for any agent integration

# Node
"@adobe/pdfservices-node-sdk": "4.1.0"
```

REST API version is pinned in the URL path:
- PDF Services: implicit (the host `pdf-services.adobe.io` is v3)
- Acrobat Sign: `/api/rest/v6/...` — v5 is end-of-life

Acrobat Pro version pinning matters for the founder workflow: PDF
features added in DC 2024 (e.g. AI Assistant) are not present in
DC 2020 perpetual licenses. EOS-generated PDFs with PDF 2.0 features
(unicode passwords, SHA-256 hashes) require Reader DC 2020+ to open
properly. Default to PDF 1.7 unless you know the recipient.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

PDF Services API was designed by the Adobe Document Cloud team
(formerly the Adobe Acrobat team) to expose Acrobat's PDF engine as a
network service. The constraints they optimized for, in priority order:

1. **Fidelity to Acrobat behavior** — if the desktop product can do
   it, the API should produce identical output. This is why
   PDF Services produces PDFs that pass Acrobat Preflight where
   open-source alternatives (LibreOffice headless, Ghostscript,
   wkhtmltopdf) often produce subtly broken PDFs.
2. **Correctness over speed** — every operation runs Adobe's full
   PDF rendering and validation stack. A 3-page invoice takes 2-5
   seconds; this is a feature, not a bug.
3. **Async by default** — the rendering stack is heavy enough that
   sync HTTP can't reliably hold the connection. Async + polling
   matches the underlying reality.
4. **Transaction-based billing** — Adobe makes money on Acrobat Pro
   seats; the API is a complementary product, not a cost center.
   Per-DT pricing reflects this — there is no infra-cost-recovery
   pricing tier, just enterprise-grade contracts.

The **biggest tradeoff** is opacity. You cannot see inside the
rendering pipeline, you cannot tune it, you cannot bring your own
fonts in many operations, you cannot control the JS engine used by
the HTML renderer. You get Adobe's defaults or nothing. For high-
fidelity invoice/report generation this is exactly right; for
"render this React app to PDF" it is the wrong tool — use Puppeteer.

The **second tradeoff** is async. Every workflow needs a polling
loop or a queue worker. There is no synchronous mode. For request-
handler use cases (user clicks button, gets PDF immediately) you
either accept a 5-30s latency with a spinner, or you pre-render
asynchronously and serve from cache.

Acrobat Sign was designed for **legal-grade audit trails first,
developer experience second**. Every signature event is timestamped,
geo-tagged, IP-logged, and certified. The API surface reflects this
— it has more endpoints than necessary because each one maps to a
distinct legal artifact (the agreement, the audit report, the
certificate of completion, the form data export).

## Problem-Solution Map and Hidden Capabilities

| Problem | Right tool | Wrong tool |
|---|---|---|
| Generate branded onboarding PDF | createpdf from HTML | wkhtmltopdf (font issues) |
| Make scanned contract searchable | ocr (with correct lang) | tesseract (lower accuracy) |
| Extract tables from PDF for analysis | extractpdf (returns CSV) | tabula (structure-blind) |
| Fill a form template per-user | documentgeneration | manual pdf-lib field setting |
| Reduce PDF size for email | compresspdf MEDIUM | Ghostscript (quality loss) |
| Password-protect a contract | protectpdf | qpdf (no audit trail) |
| Send for legal signature | Acrobat Sign agreements | DocuSign (different ecosystem) |
| Bates number legal exhibits | Acrobat Pro GUI | API (does not exist) |
| Redact sensitive draft | Acrobat Pro GUI | API (paid tier only, awkward) |
| Bulk-generate 1000 personalized PDFs | documentgeneration loop | createpdf (wasteful, slower) |
| Convert PDF to DOCX for editing | exportpdf | pandoc (loses layout) |
| Get page count + metadata | pdfproperties | PyPDF2 (works but counts as 0 DTs) |

**Hidden capabilities** most users miss:

- **`extractpdf` returns reading order** — the JSON output orders
  elements as a human would read them, even on multi-column
  layouts. This is gold for embedding pipelines: you get cleaner
  chunks than any open-source PDF parser produces.
- **`extractpdf` returns table data as CSV files inside the ZIP** —
  no need to re-parse tables from text. Look in `tables/` subdir.
- **`extractpdf` includes character bounding boxes** when you set
  `getCharBounds: true` — useful for PDF→HTML reconstruction.
- **`documentgeneration` supports conditionals and loops** in the
  Word template via `{% if %}` / `{% for %}` Jinja-like tags. You
  can build entire dynamic reports from a single template + JSON.
- **`htmltopdf` can take a remote URL directly** — no upload needed.
  But the renderer has no internet egress to third-party CDNs by
  default; Adobe-hosted assets work, others usually don't.
- **`protectpdf` supports permissions** beyond just passwords:
  `printing` (NONE/LOW_RES/HIGH_RES), `editing` (NONE/INSERT_DELETE_ROTATE/...),
  `enableCopying`, `enableAccessibility`. Use these for client deliverables.
- **`splitpdf` can split by page ranges** with discontinuous specs:
  `{"pageRanges": [{"start": 1, "end": 5}, {"start": 10, "end": 15}]}`.
- **Acrobat Sign widgets** — embeddable signing forms that never
  expire. One URL, infinite signers. Perfect for waivers.
- **Acrobat Pro Action Wizard** — record a sequence of GUI operations
  (e.g. flatten + redact + Bates) and re-run on a folder. The closest
  thing to scripting on the desktop.

## Operational Behavior and Edge Cases

**Cold start latency.** First job after a quiet period takes ~5s
longer than subsequent jobs. Adobe's autoscaler spins down idle
worker pools. For latency-sensitive flows, run a no-op `pdfproperties`
call every 5 minutes as a keep-warm.

**Concurrent jobs share quota, not throughput.** You can submit 25
jobs concurrently and they will all process in parallel — but they
all bill against the same DT pool and the same per-credential rate
limit. There is no per-job priority.

**Office format edge cases** in `createpdf`:
- DOCX with embedded fonts: fonts preserved
- DOCX with linked external fonts: substituted silently with
  Adobe's font matching (sometimes wrong)
- XLSX with formulas: formulas evaluated server-side using Excel-
  compatible engine (mostly correct, edge cases in INDIRECT/OFFSET)
- PPTX with animations: animations dropped (PDF can't animate)
- PPTX with embedded videos: video frames captured at t=0

**HTML to PDF edge cases**:
- `@media print` CSS is honored
- Custom fonts via `@font-face` work IF the font file is in the ZIP
- JavaScript runs (Chromium-based renderer) but with no network
- `<iframe>` elements are blanked
- Page breaks via `page-break-before: always` work; `break-inside`
  is honored only for direct table rows

**OCR edge cases**:
- Languages: 30+ supported via `ocrLang` (en-US, es-ES, fr-FR, de-DE,
  ja-JP, zh-CN, etc.)
- `ocrType`: `searchable_image` (default, preserves original visuals)
  vs `searchable_image_exact` (replaces with rendered text — smaller
  but loses fidelity)
- Skewed scans: OCR auto-deskews up to ±15°. Beyond that, results
  degrade fast.
- Handwriting: not supported. OCR is print-only.

**Acrobat Sign edge cases**:
- `signatureType: ESIGN` is the standard click-to-sign. `WRITTEN`
  means the signer prints, signs in ink, scans, uploads. EU eIDAS
  flows use `signatureType: ESIGN` plus a separate `signerSecurityOptions`
  block to upgrade to advanced/qualified signature.
- An agreement in `AUTHORING` state has not been sent yet — you can
  still edit it. Once it transitions to `IN_PROCESS`, edits create
  audit trail entries.
- Webhook events fire in **eventual order**, not strict order.
  Don't assume `AGREEMENT_CREATED` arrives before `AGREEMENT_ACTION_COMPLETED`
  for the first signer. Use `eventDate` for ordering.

## Ecosystem Position and Composition

PDF Services API competes with:
- **DocRaptor** (HTML→PDF, simpler, less faithful)
- **PDFKit / pdf-lib** (open-source, low-level, no OCR/extract)
- **Aspose.PDF** (Java-heavy, on-prem licensing)
- **Foxit PDF SDK** (closer to Adobe in fidelity, weaker REST)
- **PSPDFKit / Nutrient** (mobile/web SDK focus)
- **Mistral OCR / Llama Parse** (LLM-native PDF extraction, newer)

The differentiator is **fidelity to the Acrobat reference renderer**.
For anything legal, contract, or invoice the founder will sign their
name to, this matters. For "extract text from research papers for
embeddings," LLM-native parsers (Llama Parse, Mistral OCR) increasingly
match or beat Adobe.

Inside EOS, PDF Services composes naturally with:
- **Notion** — generated PDFs uploaded as page attachments
- **Gmail / Postmark** — PDFs as email attachments
- **Neon Postgres** — PDF metadata + assetID stored, file in S3
- **Embedding engine** — extractpdf JSON → chunks → embeddings → memory
- **Discord bot** — drop a PDF, get OCR'd searchable version back
- **The orchestrator** — webhook-triggered generation on Stripe events

Acrobat Sign composes with:
- **The orchestrator** — webhook receiver in services/ for agreement events
- **Lyfe Institute CRM** — agreement status syncs to lead pipeline
- **The cognitive loop** — completed agreements trigger memory writes

## Trajectory and Evolution

Adobe is moving aggressively toward **AI-native PDF**. The 2024-2026
direction:

- **Acrobat AI Assistant** (in Pro and the API) — RAG over uploaded
  PDFs. Currently a Pro feature; an `aiAssistant` API endpoint is in
  beta.
- **PDF Accessibility Auto-Tag** — already shipping, will expand
  beyond tagging into semantic structure.
- **Document Generation** — gaining LLM-driven template authoring
  (write a prompt, get a Word template back).
- **Extract API getting layout-aware** — current `extractpdf` already
  does reading order; the next iteration adds semantic role tagging
  (heading hierarchy, footnote linkage, citation parsing).

The OAuth Server-to-Server migration (June 2025) was the cleanup
before this push — Adobe wanted a uniform credential model across
Document Services, Firefly, Express, and Substance for cross-product
AI flows.

Acrobat Sign trajectory: tighter integration with eIDAS qualified
signatures in EU, expansion of webhook event types, deprecation of
the legacy SOAP API (already removed), continued investment in
embedded widgets for SaaS partners.

Acrobat Pro desktop: Adobe is folding more AI into the GUI (AI
Assistant pane, Generate Summary, Q&A over the open document).
The API surface lags the GUI by ~12 months — features land in Pro
first, then graduate to PDF Services if there is demand.

## Conceptual Model and Solution Recipes

**Model: PDF Services is a remote pure function on assets.** Every
operation has the shape `(input_asset[, params]) -> output_asset`.
The state lives in the assets, which are ephemeral. The compute is
the API. There is no project, no folder, no permission system —
you bring your own.

**Model: Acrobat Sign is a state machine over agreements.** Every
agreement walks a defined path from DRAFT through terminal states
(SIGNED/CANCELLED/EXPIRED/REJECTED). Webhooks emit transitions. Your
job is to mirror that state into your own database.

**Model: Acrobat Pro is the founder's PDF IDE.** Author once,
operate forever via the API. The GUI is for designing forms,
templates, and one-off legal artifacts the API can't produce.

### Recipe: HTML invoice → branded PDF → Notion attachment

1. Render Jinja invoice template to HTML (in EOS)
2. Zip with brand CSS + logo PNG (`index.html` at root)
3. Upload zip → PDF Services asset
4. POST `/operation/createpdf` with `documentLanguage: "en-US"`
5. Poll Location, download result
6. POST `/operation/compresspdf` with `compressionLevel: MEDIUM`
7. Upload final to Notion via Notion API as page property attachment

### Recipe: Scanned letter → memory ingestion

1. Founder photographs letter in iPhone Notes
2. iCloud sync → Mac → upload to EOS via Discord drop
3. EOS uploads PDF → PDF Services asset
4. POST `/operation/ocr` with correct `ocrLang`
5. Poll, download searchable PDF
6. Re-upload searchable PDF as new asset
7. POST `/operation/extractpdf`, download ZIP
8. Unzip, parse `structuredData.json`, walk elements in reading order
9. Chunk into 500-token pieces, embed with text-embedding-3-large
10. Write embeddings + raw text to memory.documents

### Recipe: Service agreement → e-signature → webhook → CRM update

1. EOS renders agreement DOCX from template + client JSON
2. Convert DOCX → PDF via `/operation/createpdf`
3. POST `/api/rest/v6/transientDocuments` to Acrobat Sign with the PDF
4. POST `/api/rest/v6/agreements` with the transientDocumentId,
   client email as participant, `state: IN_PROCESS`
5. Sign emails the client; client signs in browser
6. Acrobat Sign POSTs `AGREEMENT_WORKFLOW_COMPLETED` to EOS webhook
7. Webhook handler GETs `/agreements/{id}/combinedDocument` for the
   final signed PDF
8. Stores PDF in S3, updates CRM lead state to `SIGNED`, triggers
   onboarding playbook

### Recipe: Bulk personalize 100 onboarding packets

1. Author a single Word template with `{{firstName}}`, `{{startDate}}`,
   `{% for module in modules %}` loop, etc.
2. Upload template once → asset
3. For each initiate:
   a. POST `/operation/documentgeneration` with `assetID` + JSON data
   b. Poll Location, get PDF
   c. POST `/operation/compresspdf` MEDIUM
   d. Email or upload to delivery target
4. Track DTs: 1 generation + 1 compress = 2 DTs per packet * 100 = 200 DTs

## Industry Expert and Cutting-Edge Usage

**Patterns from teams running PDF Services at scale**:

- **Pre-warm with `pdfproperties`** every 5 minutes via cron to
  defeat cold starts. Costs 0 DTs.
- **Submit to a queue, not directly.** Wrap PDF Services calls in a
  Celery/RQ/Sidekiq queue. Workers handle the polling loop, retries,
  and exponential backoff. The HTTP request handler returns immediately
  with a job ID.
- **Mirror job status into your own DB** with states matching Adobe's
  (`pending`, `submitted`, `polling`, `done`, `failed`). Polling
  workers update the DB; consumers query the DB, never PDF Services
  directly.
- **Asset garbage collection is automatic** at 24h, but the safety
  pattern is to delete output assets explicitly after download via
  `DELETE /assets/{assetID}` so quota usage is predictable.
- **Use `documentgeneration` for any templated PDF, even single-shot**
  — it is cheaper than HTML→PDF (1 DT vs potentially many for complex
  HTML) and produces more reliable layout for table-heavy reports.
- **Run `extractpdf` BEFORE chunking for embeddings.** The reading
  order is too valuable to skip. Even paying 1 DT/5 pages is cheaper
  than the engineering time to fix bad chunk boundaries.
- **For Acrobat Sign at scale**: never poll for status. Use webhooks.
  Polling burns rate limit and is delayed anyway.

**Cutting-edge in 2026**:

- **LLM-PDF hybrid pipelines** — extractpdf for layout/tables, then
  Claude/Gemini for semantic enrichment of the extracted JSON.
- **Vector indexing the extractpdf output directly** — element-level
  embeddings (paragraph, table cell, figure caption) instead of
  whole-document embeddings, enabling pinpoint citations.
- **Headless contract assembly** — documentgeneration + Acrobat Sign
  + webhook → fully automated B2B contract pipelines with zero human
  touch on the seller side.
- **AI Assistant API (beta)** — RAG over uploaded PDFs without
  building your own embedding pipeline. Useful for one-off Q&A;
  too opaque for production memory systems.

## EOS Usage Patterns

EOS-specific applications, ranked by current priority:

1. **Initiate Arena onboarding packet generation** — when a new
   initiate is added to the CRM, the orchestrator triggers
   `documentgeneration` with their personalized data (name, cohort,
   start date, module list, calendar integration link). Compressed
   and emailed via Postmark. End-to-end zero human touch.

2. **Service agreement pipeline** — Empyrean Studio and Lyfe
   Institute proposals turn into signed agreements via
   createpdf → Acrobat Sign → webhook → CRM state machine.
   Webhook handler lives in `services/sign_webhook.py` (TODO).

3. **Document memory ingestion** — anything PDF the founder sends
   into EOS via Discord, Telegram, or email gets the
   ocr → extractpdf → embed → memory pipeline. This replaces
   the brittle pdfminer/PyPDF2 path currently in
   `eos_ai/embedding_engine.py`.

4. **Invoice generation** — when revenue starts flowing,
   per-customer invoices via documentgeneration from a Word
   template. Compressed before storage. Sent via email.

5. **Report exports** — strategic reports, board packets, and
   investor updates rendered from Markdown via Pandoc → DOCX →
   PDF Services createpdf, with brand styling from a Word
   template's stylesheet.

EOS-specific guardrails:

- Always `compresspdf MEDIUM` before storage. Never store raw output.
- Always `protectpdf` outputs sent to external parties with a
  permissions block (no editing, no copying), even if no password.
- Never call `autotag` from automated flows — its 10 DT/page cost
  is prohibitive at the free tier. Reserve for explicit founder
  request.
- Cache the IMS access token in `eos_ai/provider_health.py` along
  with the other provider tokens. Re-fetch on 401 with backoff.
- Wrap all PDF Services calls in `model_router.py`-style fallback:
  on quota exhaustion, fall back to local PyMuPDF for the basic
  ops (split, merge, compress) and fail loudly only for
  ocr/extract/createpdf where there is no equivalent.
- Acrobat Sign webhook handler must verify the JWT signature.
  Never trust the payload without verification.
- Store IMS credentials in `eos_ai/.env`, never in code. Rotate
  via the Adobe Developer Console quarterly.

## Gotchas

- **JWT/Service Account auth is dead** as of June 30, 2025.
  Tutorials, blog posts, and old SDK versions referencing JWT will
  silently fail with `INVALID_CLIENT`. Use OAuth Server-to-Server.
- **`x-api-key` header is mandatory** on every PDF Services call,
  not just optional. Its value is your `client_id`. Missing it
  produces a misleading 401.
- **Polling 404 race** — the Location URL returns 404 if you GET it
  within ~500ms of the 201 response. Sleep 1 second before the
  first poll. The SDK does this for you.
- **Presigned PUT must NOT include Adobe headers** — the URL is
  pre-signed for Azure/S3, and adding Authorization triggers a
  403 from the storage backend.
- **Free tier dies after 6 months**, not just at 500 DTs. Even if
  you used 0 DTs, the credentials stop working at month 6.
- **No refresh token** under client_credentials. Just re-call
  the token endpoint when expired. Cache with a 60s safety margin.
- **Acrobat Sign shard discovery is one-shot** — `api.adobesign.com`
  works for `baseUris` only. All other calls must go to the
  returned shard hostname (`api.na1`, `api.eu1`, etc.).
- **OCR locale defaults to en-US** — Spanish, French, German, and
  Asian language scans need explicit `ocrLang` or you get garbled
  text that looks plausible.
- **Extract API output is a ZIP**, not JSON. The downloadUri returns
  a `.zip` containing `structuredData.json` plus `tables/` and
  `figures/` subdirectories. Many integrations break here.
- **HTML to PDF needs ALL assets in the ZIP** — no external CDN,
  no Google Fonts URLs. Inline or bundle.
- **createPDF strips JavaScript by default** in HTML inputs. The
  renderer is Chromium-based but sandboxed; no network egress.
- **Reader Extended forms can't be edited via the API** — flatten
  with PyMuPDF before sending or you get `BAD_PDF`.
- **Bates numbering is GUI-only** — there is no `/operation/bates`
  endpoint. Use Acrobat Pro Action Wizard or post-process with
  PyMuPDF.
- **Redaction in the API is paid-tier only** and operates by content
  patterns, not visual selection — for sensitive one-off work, use
  Acrobat Pro desktop.
- **Webhook URL verification is GET-then-echo** — Acrobat Sign sends
  a GET with `X-AdobeSign-ClientId`, your endpoint must echo that
  header AND include `{"xAdobeSignClientId": "..."}` in the JSON
  body within 10s. HTTPS only.
- **Webhook retries last 72 hours then auto-deactivate** — monitor
  webhook health or you'll silently miss agreement completions.
- **Compress HIGH degrades scanned text** noticeably. MEDIUM is the
  storage default; use HIGH only for "throwaway preview" use cases.
- **Combine endpoint maxes at 20 inputs / 100 pages each** — for
  larger merges, do two-pass merging or use PyMuPDF locally.
- **Async polling burns connections** if you submit hundreds of
  jobs in a tight loop without a queue. Always queue.
- **Document Transactions don't roll over** month to month. Use
  them or lose them.
- **Acrobat Pro versions differ** — features added in DC 2024
  (AI Assistant, new redaction UI) won't exist in DC 2020 perpetual.
  EOS-generated PDFs targeting external recipients should default
  to PDF 1.7 features, not PDF 2.0.
- **Token endpoint URL** is `/ims/token/v3`, not `/ims/token`.
  The v1 endpoint still answers but with the old JWT-style flow.
  Always use v3.
- **OCR on an already-OCRed PDF** returns `DISQUALIFIED`. Check with
  `pdfproperties` first or just catch the error and proceed.
- **`mediaType` on the upload step must match the actual file type**
  exactly (`application/pdf`, not `application/octet-stream`).
  Mismatch triggers a 415 on the operation step, not the upload step,
  making it look like a job failure.
