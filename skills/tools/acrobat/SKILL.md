---
name: acrobat
description: "Use when generating PDFs programmatically (invoices, reports, onboarding packets), running OCR on scanned documents into memory, extracting structured JSON from PDFs (text/tables/figures), compressing/protecting/redacting/splitting/merging PDFs via Adobe PDF Services REST API, sending contracts for e-signature via Acrobat Sign, or working with Acrobat Pro GUI features (forms, redaction, Bates numbering, commenting)."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://developer.adobe.com/document-services/docs/overview/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "PDF Services REST v3 / Acrobat Sign REST v6"
sdk_version: "pdfservices-sdk Python 4.x, Node 4.x; Acrobat Pro DC 2024+"
speed_category: stable
---

# Tool: acrobat (Adobe Acrobat Pro + PDF Services API + Acrobat Sign)

## What This Tool Does

A hybrid surface covering three Adobe products that share document DNA:

1. **Adobe PDF Services API** — REST + SDK for headless PDF work. Create
   PDFs from HTML/Office/text, OCR scanned PDFs, extract structured JSON
   (text, tables, figures, reading order) via Adobe Sensei, compress,
   linearize, password-protect, split, merge, insert/delete/rotate pages,
   export to DOCX/XLSX/PPTX/images, electronic seal, accessibility
   auto-tag.
2. **Adobe Acrobat Pro (desktop GUI)** — interactive workflows: form
   field design, redaction, Bates numbering, comment review, Preflight,
   prepare-for-signature, certificate signing.
3. **Adobe Acrobat Sign API (REST v6)** — full e-signature lifecycle:
   create agreements from templates/library/transient documents, route
   to signers, embed signing widgets, receive webhook events.

The PDF Services API is the EOS workhorse. Acrobat Pro is the founder's
desktop tool for one-off legal/contract polish. Acrobat Sign is the
adjacent surface when an EOS-generated PDF needs human signature.

## EOS Integration

Primary use cases inside EOS:

- **Initiate Arena onboarding packets** — generate personalized PDF
  welcome kits from HTML templates, brand-stamped with Lyfe Spectrum
  identity, sent to new initiates. PDF Services `createPDF` from HTML.
- **Invoices and receipts** — render invoice HTML to PDF via API, compress,
  attach to email or upload to Notion. No human in the loop.
- **Scanned document ingestion** — when the founder photographs a contract
  or letter, the OCR operation makes it searchable, then `extractPDF`
  produces structured JSON the memory layer can index.
- **Memory-grade document extraction** — `extractPDF` returns elements
  with page coordinates, reading order, tables as CSV, and figures as
  PNGs. Feed this directly into the embedding engine instead of brittle
  PyPDF2/pdfminer pipelines.
- **Contract signing** — when Empyrean Studio or Lyfe Institute sends a
  service agreement, EOS uses Acrobat Sign API to create the agreement,
  set signers, and webhook back into the orchestrator on
  `AGREEMENT_ACTION_COMPLETED`.
- **Compression before storage** — every generated PDF passes through
  `compresspdf` (level=MEDIUM) before hitting Neon or S3.

The founder operates Acrobat Pro on the Windows desktop for: redacting
sensitive contract drafts, applying Bates numbers to legal exhibits,
filling out government forms, designing fillable PDF templates that EOS
later flattens via API.

## Authentication

**PDF Services API** uses Adobe IMS OAuth Server-to-Server (the legacy
JWT/Service Account flow reached end-of-life on June 30, 2025 — JWT no
longer works).

```bash
curl -X POST https://ims-na1.adobelogin.com/ims/token/v3 \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'client_id=$ADOBE_CLIENT_ID' \
  -d 'client_secret=$ADOBE_CLIENT_SECRET' \
  -d 'grant_type=client_credentials' \
  -d 'scope=openid,AdobeID,DCAPI'
```

Returns `{access_token, token_type:"bearer", expires_in:86399}`. There
is **no refresh token** — re-call client_credentials when expired.

Every PDF Services request needs **two** headers:
- `Authorization: Bearer <access_token>`
- `x-api-key: <ADOBE_CLIENT_ID>` (the client_id is also the api key)

**Acrobat Sign** uses its own OAuth (separate from IMS). Tokens are
shard-scoped — you must use the shard URL returned with the token
(e.g. `api.na1.adobesign.com`, `api.eu1.adobesign.com`). Hardcoding
`api.adobesign.com` will 401 silently after the first call.

Store in `eos_ai/.env`:
```
ADOBE_CLIENT_ID=...
ADOBE_CLIENT_SECRET=...
ADOBE_SIGN_INTEGRATION_KEY=...
ADOBE_SIGN_SHARD=api.na1.adobesign.com
```

## Quick Reference

### Get a token

```bash
TOKEN=$(curl -s -X POST https://ims-na1.adobelogin.com/ims/token/v3 \
  -d "client_id=$ADOBE_CLIENT_ID" \
  -d "client_secret=$ADOBE_CLIENT_SECRET" \
  -d "grant_type=client_credentials" \
  -d "scope=openid,AdobeID,DCAPI" | jq -r .access_token)
```

### Three-step async pattern (every PDF Services operation)

```bash
# 1. Get a presigned upload URI
RESP=$(curl -s -X POST https://pdf-services.adobe.io/assets \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-api-key: $ADOBE_CLIENT_ID" \
  -H "Content-Type: application/json" \
  -d '{"mediaType":"application/pdf"}')
ASSET_ID=$(echo $RESP | jq -r .assetID)
UPLOAD_URI=$(echo $RESP | jq -r .uploadUri)

# 2. PUT the file directly to the presigned URI (NO Adobe headers)
curl -s -X PUT "$UPLOAD_URI" \
  -H "Content-Type: application/pdf" \
  --data-binary @input.pdf

# 3. Submit operation. Returns 201 with Location header.
LOCATION=$(curl -s -D - -o /dev/null -X POST \
  https://pdf-services.adobe.io/operation/ocr \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-api-key: $ADOBE_CLIENT_ID" \
  -H "Content-Type: application/json" \
  -d "{\"assetID\":\"$ASSET_ID\",\"ocrLang\":\"en-US\"}" \
  | grep -i ^location: | awk '{print $2}' | tr -d '\r')

# 4. Poll Location until status == done
sleep 1   # avoid the 404 race
while true; do
  STATUS=$(curl -s "$LOCATION" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-api-key: $ADOBE_CLIENT_ID")
  S=$(echo $STATUS | jq -r .status)
  [ "$S" = "done" ] && break
  [ "$S" = "failed" ] && echo "FAILED: $STATUS" && exit 1
  sleep 2
done
DOWNLOAD=$(echo $STATUS | jq -r .asset.downloadUri)
curl -s -o output.pdf "$DOWNLOAD"
```

### Operation endpoints (POST to these)

```
/operation/createpdf           HTML/DOCX/XLSX/PPTX/TXT to PDF
/operation/exportpdf           PDF to DOCX/XLSX/PPTX/RTF
/operation/extractpdf          PDF to structured JSON
/operation/ocr                 scanned PDF to searchable PDF
/operation/compresspdf         reduce file size (LOW/MEDIUM/HIGH)
/operation/linearizepdf        optimize for fast web view
/operation/protectpdf          add passwords + permissions
/operation/removeprotection
/operation/combinepdf          merge multiple assets
/operation/splitpdf            by page count, ranges, or file count
/operation/pagemanipulation    insert/replace/delete/rotate/reorder
/operation/exportpdftoimages   PDF to PNG/JPEG per page
/operation/pdfproperties       metadata + page count + compliance
/operation/htmltopdf           URL or zipped HTML to PDF
/operation/documentgeneration  Word template + JSON to PDF
/operation/autotag             add accessibility tags
/operation/electronicseal      apply digital seal certificate
```

### Python SDK (preferred for EOS code)

```python
from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdfjobs.jobs.ocr_pdf_job import OCRPDFJob
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType

creds = ServicePrincipalCredentials(
    client_id=os.getenv("ADOBE_CLIENT_ID"),
    client_secret=os.getenv("ADOBE_CLIENT_SECRET"),
)
pdf_services = PDFServices(credentials=creds)

with open("scan.pdf", "rb") as f:
    asset = pdf_services.upload(input_stream=f.read(),
                                mime_type=PDFServicesMediaType.PDF)
job = OCRPDFJob(input_asset=asset)
location = pdf_services.submit(job)
result = pdf_services.get_job_result(location, OCRPDFResult)
stream = pdf_services.get_content(result.get_result().get_asset())
open("searchable.pdf", "wb").write(stream.get_input_stream())
```

The SDK handles polling, retries, and exponential backoff — use it
unless you need cron-friendly bash.

### Acrobat Sign — send for signature

```bash
# 1. Upload transient document (24h lifetime)
TD=$(curl -s -X POST https://$SHARD/api/rest/v6/transientDocuments \
  -H "Authorization: Bearer $SIGN_TOKEN" \
  -F "File=@contract.pdf" | jq -r .transientDocumentId)

# 2. Create agreement
curl -s -X POST https://$SHARD/api/rest/v6/agreements \
  -H "Authorization: Bearer $SIGN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"fileInfos\":[{\"transientDocumentId\":\"$TD\"}],
    \"name\":\"Lyfe Institute Service Agreement\",
    \"participantSetsInfo\":[{
      \"memberInfos\":[{\"email\":\"client@x.com\"}],
      \"order\":1, \"role\":\"SIGNER\"}],
    \"signatureType\":\"ESIGN\",
    \"state\":\"IN_PROCESS\"}"
```

## Conceptual Model

**PDF Services is async-first.** Every operation is a job, not an RPC.
The mental model: upload asset to submit job to poll location to download
result. Synchronous-looking SDKs hide this loop but it is happening.
A 201 with empty body and a Location header is success — not an error.

**Assets are ephemeral.** Both upload and download URIs expire in 24h.
Treat them as transient. Never store them in a database.

**Acrobat Pro is the authoring tool, the API is the runtime.** Founder
designs a fillable form template once in Acrobat Pro, stores the PDF
in the repo, and EOS uses `documentgeneration` (or pdf-lib for filling
form fields) to populate it per-user. The desktop app and the API are
two ends of the same pipeline, not competitors.

**Acrobat Sign is a separate product on a separate auth, sharing
nothing but the brand.** It has its own dashboard, its own webhooks,
its own rate limits, its own SDK. Treat it as a third tool that
happens to consume PDFs.

## Gotchas

- **JWT auth is dead** (June 30, 2025). Any tutorial showing
  `private.key` + JWT assertion is obsolete. Use OAuth Server-to-Server
  client_credentials.
- **`x-api-key` is mandatory and undocumented in many examples.**
  Missing it gives `401 unauthorized` even with a valid bearer token.
  The value is your `client_id`.
- **Race condition on polling** (community thread #311579). If you GET
  the Location URL within ~500ms of the 201 response, you can get a
  spurious 404. Sleep 1 second before the first poll.
- **Presigned PUT must NOT include Adobe auth headers** — they belong
  to the storage backend (Azure/S3), not Adobe. Including
  `Authorization` here causes a 403 from the storage layer.
- **Free tier is 500 transactions/month for 6 months**, then dies.
  Extract counts as 1 per 5 pages. AutoTag is 10 per page (expensive).
  All other ops are 1 per 50 pages. Budget accordingly.
- **Token lifetime is 24h (86399s) and there is no refresh token** —
  cache it, but always have a re-fetch path on 401.
- **Acrobat Sign shards** — `api.adobesign.com` is just bootstrap.
  You MUST switch to the shard URL returned by `baseUris`
  (`api.na1`, `api.eu1`, `api.jp1`) or every call 401s.
- **OCR locale matters** — `ocrLang` defaults to `en-US`. Spanish
  scans with the default produce garbage. Pass the right locale.
- **Extract API output is a ZIP**, not a JSON. The downloadUri returns
  a `.zip` containing `structuredData.json` plus `tables/` and
  `figures/` subdirs. Unzip first.
- **HTML to PDF requires a ZIP** if your HTML references CSS/images —
  zip the whole folder with `index.html` at root.
- **Acrobat Pro fillable forms saved with "Reader Extended" rights**
  cannot be edited by the API afterward — flatten before sending
  to PDF Services or you get a `BAD_PDF` error.
- **Bates numbering is Acrobat Pro GUI only** — there is no API
  endpoint. If EOS needs Bates, generate plain PDF then post-process
  with PyMuPDF.
- **Redaction in the API is paid-tier only** — for one-off founder
  redaction work, use Acrobat Pro desktop, not the API.
- **Webhook URL must be HTTPS and respond to a `client-id` validation
  GET** before Acrobat Sign accepts it. Plain HTTP or self-signed
  certs are rejected.

See references/best_practices.md for the full 19-section creator-level knowledge base.
