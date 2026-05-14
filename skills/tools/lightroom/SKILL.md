---
name: lightroom
description: "Use when editing raw photographs, building or applying develop presets, batch-processing shoots, configuring catalogs/collections, working with smart previews, running AI denoise or AI masking, exporting deliverables, or driving Lightroom programmatically via the Firefly Services Lightroom API for headless preset application and export."
allowed-tools: "Read, Bash, Write, Edit, WebFetch"
version: 1.0
source_url: "https://helpx.adobe.com/lightroom-classic/user-guide.html"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Lightroom Classic 14.4 (June 2025) / Lightroom (cloud) 8.4"
sdk_version: "Firefly Services Lightroom API v1 (REST) / firefly-services-sdk-js lightroom 1.x"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: lightroom

## What This Tool Does

Adobe Lightroom is a non-destructive raw photo editor and digital asset
manager built around one principle: the original file is sacred. Every edit
is an instruction recorded in a database (Classic) or cloud document (CC),
never a destructive write to pixels. Three distinct surfaces share the name
and the develop engine but are otherwise different products:

- **Lightroom Classic** — desktop, catalog-based, the photographer's workhorse.
  Local storage, full folder control, deepest tooling (tethering, plugins,
  publish services, print module, smart previews, full Library/Develop module).
- **Lightroom (CC / Cloud)** — desktop + mobile + web, cloud-native, no local
  catalog. Originals live in Adobe's cloud and sync everywhere. Simpler UI,
  same develop engine, fewer power features.
- **Lightroom API (Firefly Services)** — REST endpoints under
  `developer.adobe.com/firefly-services/docs/lightroom/`. Apply XMP presets
  to images at scale, run develop adjustments, autotone, autostraighten, and
  export — fully headless, no GUI, no local install.

Core capabilities (across surfaces):

- **Non-destructive raw processing** — every adjustment is metadata; raw bytes never change
- **Develop module** — exposure, color, tone curve, HSL, calibration, masking, detail, lens corrections, transform, effects
- **AI Denoise** — ML-based raw denoise (since LrC 12.3, fully non-destructive in 14.4 / June 2025 — no more forced DNG)
- **AI Masking** — Select Subject, Sky, Background, People (with body-part subselects), Objects (brush-prompted)
- **Develop presets** — reusable XMP bundles of develop settings, the unit of style transfer
- **Smart Previews** — ~2540px lossy DNGs that let you edit when originals are offline
- **Catalog (Classic)** — SQLite database tracking every image, edit, keyword, collection, history step, preview
- **Collections + Smart Collections** — virtual groupings (rule-based or manual) that don't move files
- **Export** — render finals to JPEG/TIFF/DNG/PSD with output sharpening, resize, watermark, color space, metadata stripping
- **Tethered capture** — shoot directly into the catalog from a connected camera (Classic only)

## EOS Integration

Lightroom is a **hybrid skill, GUI-primary**. Antony does the actual editing
in Lightroom Classic on the Windows workstation; agents support that workflow
without trying to replace human eyes on the rendered image. Primary uses:

- **Personal brand photography** — tactical luxury aesthetic: deep shadows,
  controlled highlights, cool neutrals with warm skin, modest clarity,
  restrained saturation. The look is the brand. Every public image gets the
  same preset family for visual consistency across the feed grid.
- **Lyfe Spectrum product shots** — apparel and accessory product photography.
  Color-true exports for ecommerce, separate stylized exports for social.
  Batch-driven, consistent across SKUs.
- **Empyrean Studio client retouching** — client work where deliverables and
  turnaround matter. Versioned exports, watermark-locked previews, full-res
  finals on approval.

How agents help (without touching pixels):

- **Draft preset specs** — agent writes a develop-setting recipe ("hero look
  v3: -0.3 EV, contrast +12, highlights -45, shadows +30, whites -10, blacks
  -25, vibrance +8, saturation -5, tone curve crushed at point 25, ...") in
  XMP-ready form. Antony imports and tunes by eye.
- **Batch instructions** — agent generates a step list ("import card, apply
  Hero v3 to picks, sync to selected, denoise the ISO 6400 group, export
  2048px sRGB for Instagram, 3000px sRGB for web") that Antony executes.
- **Lightroom API for headless work** — for programmatic batches (apply
  preset and export across 200 product shots), agents call Firefly Services
  Lightroom API directly. No GUI, no local Lightroom required, runs from VPS.
- **Naming, metadata, delivery** — agents handle the boring half of the
  pipeline: rename exports by SKU, push to S3, generate proof contact sheets,
  email the client.

The split: Lightroom decides what an image looks like — that is human
judgment serving the brand. Agents handle everything around the edit.

## Authentication

**Lightroom Classic / CC desktop** — signed in with Adobe ID via Creative
Cloud desktop. License is per-seat, no per-call auth. The Lightroom binary
talks to its local catalog file or Adobe's sync servers using the CC session.

**Lightroom API (Firefly Services)** — server-to-server OAuth 2.0 via Adobe
IMS. You need:

1. An Adobe Developer Console project with Firefly Services entitlement
2. A server-to-server OAuth credential (client_id, client_secret, scopes)
3. Token exchange against `https://ims-na1.adobelogin.com/ims/token/v3`
4. Pass `Authorization: Bearer <access_token>` and `x-api-key: <client_id>` on every Lightroom API call
5. Tokens last ~24h; cache and refresh on 401

```bash
curl -X POST https://ims-na1.adobelogin.com/ims/token/v3 \
  -d "grant_type=client_credentials" \
  -d "client_id=$ADOBE_CLIENT_ID" \
  -d "client_secret=$ADOBE_CLIENT_SECRET" \
  -d "scope=openid,AdobeID,read_organizations,firefly_api,ff_apis"
```

Input/output images for the API must live on cloud storage with presigned
URLs (S3, Azure Blob, or Dropbox). Lightroom API never accepts raw bytes —
only URLs in, URLs out.

## Quick Reference

### Lightroom Classic — keyboard essentials

```
G        grid view (Library)
E        loupe view
D        develop module
\        before/after toggle in Develop
Y        before/after side-by-side
R        crop
Q        spot removal
K        adjustment brush
M        linear gradient
Shift+M  radial gradient
W        white balance picker
J        clipping warnings (highlights/shadows)
Cmd/Ctrl+Shift+S  sync settings to selected
Cmd/Ctrl+Shift+C/V  copy / paste develop settings
Cmd/Ctrl+'        virtual copy
Cmd/Ctrl+E        edit in Photoshop (round-trip)
P / U / X         flag pick / unflag / reject
1..5              star rating
6..9              color label
```

### Catalog operations (Classic)

```
File > New Catalog              new .lrcat (one per major project)
File > Open Catalog             switch (LrC restarts)
File > Optimize Catalog         vacuum SQLite, run weekly on heavy catalogs
Edit > Catalog Settings         backup cadence, preview cache, smart prev
File > Export as Catalog        subset of catalog as portable .lrcat bundle
```

### Smart Previews (Classic)

```
Library > Previews > Build Smart Previews   for selected images
Catalog Settings > File Handling >
  Automatically write changes into XMP      (sidecars stay in sync with DB)
```

Smart Previews are ~2540px lossy DNG files in
`{CatalogName} Smart Previews.lrdata` next to the catalog. Edits made on
smart previews sync back automatically when originals come online.

### Develop preset I/O

```
Develop > Presets panel > + > Create Preset...   bundle current settings
Right-click preset > Export                       writes a .xmp file
Right-click preset folder > Import                load a .xmp into the panel
```

XMP presets are plain XML; agents can generate them directly.

### AI Denoise

```
Photo > Enhance > Denoise...    slider 0–100, default 50
                                (LrC 14.4+ non-destructive on raw,
                                 no DNG copy generated)
```

Apply Denoise BEFORE AI masking and BEFORE generative tools — they all work
better on a clean noise floor.

### AI Masking

```
Masking panel (in Develop, top-right of Detail)
  Subject     ML segments the main subject
  Sky         ML segments sky
  Background  inverse of subject
  People      per-person, with face/skin/eye/lip/hair/teeth/clothes subselects
  Objects     brush a prompt area, ML refines
  Brush / Linear / Radial / Range / Color / Luminance — manual masks
```

Masks compose with intersect/subtract: Subject AND NOT Face,
Sky INTERSECT Luminance > 60, etc.

### Lightroom API — apply preset and export

```bash
TOKEN=$(./get_adobe_token.sh)

curl -X POST https://image.adobe.io/lrService/presets \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-api-key: $ADOBE_CLIENT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "source": { "href": "https://s3.../in/IMG_001.dng", "storage": "external" }
    },
    "options": {
      "presets": [
        { "href": "https://s3.../presets/hero_v3.xmp", "storage": "external" }
      ]
    },
    "outputs": [
      {
        "href": "https://s3.../out/IMG_001.jpg",
        "storage": "external",
        "type": "image/jpeg",
        "overwrite": true
      }
    ]
  }'
# Returns a job URL — poll until status == "succeeded"
```

### Lightroom API — apply XMP inline

```bash
curl -X POST https://image.adobe.io/lrService/xmp \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-api-key: $ADOBE_CLIENT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs":  { "source": { "href": "...", "storage": "external" } },
    "options": { "xmp": "<x:xmpmeta ...><crs:Exposure2012>-0.30</crs:Exposure2012>...</x:xmpmeta>" },
    "outputs": [ { "href": "...", "storage": "external", "type": "image/jpeg" } ]
  }'
```

## Conceptual Model

**The original file is sacred. Every edit is a recorded instruction.** That
single principle explains everything else.

In Classic, edits live in the catalog (a SQLite database, `.lrcat`). The
catalog also tracks where each file lives on disk, every preview rendered,
every keyword, every collection membership, and every history step.
Optionally the catalog also writes adjustments out to XMP sidecar files next
to the raw file (or into the file itself for JPEG/TIFF). Sidecars are how
edits travel between catalogs and other XMP-aware tools.

In CC / Cloud, the equivalent of the catalog is a cloud document graph held
by Adobe's servers. Originals live in the cloud. Local devices hold cached
copies for offline work. Edits sync as deltas.

In the API, there is no catalog — only "take this input, apply this XMP, write
this output." Stateless. The XMP IS the unit of work.

The develop engine is the same across all three surfaces. A preset rendered
in Classic, in mobile CC, and through the API will look the same (modulo
process version differences). That contract is what makes the API useful:
agents can render exactly what Antony would have rendered himself.

If you internalize "originals never change, edits are metadata, the develop
engine is one engine wearing three skins," every confusing Lightroom behavior
becomes obvious:

- "I deleted the catalog and lost my edits" → the catalog WAS the edits
- "I moved files in Finder and Lightroom shows ?" → the catalog tracks paths
- "My preset looks different in mobile" → process version mismatch
- "Smart Preview edit shows up when I plug the drive back in" → that's the
  whole point of smart previews

## Gotchas

- **Catalogs are not photo libraries.** Deleting an .lrcat does not delete
  photos, but it deletes every edit, keyword, collection, and history step.
  BACK UP THE CATALOG. Catalog Settings > Backup > Every time Lightroom exits,
  keep last 10. Treat the catalog as production data.
- **Moving files outside Lightroom orphans them.** The catalog stores paths.
  Always rename/move from inside Library, never from Finder/Explorer. Recovery:
  right-click missing folder > Find Missing Folder.
- **Smart Preview edits are real edits.** Edit a smart preview while the
  original is offline, and when the original comes back, those edits apply
  to the original automatically. Feature, not bug, but surprises people.
- **XMP sidecars vs catalog can desync.** If "Automatically write changes
  into XMP" is OFF, the catalog is the only truth and sidecars are stale.
  If ON, both must be considered. Pick one rule per catalog and stick with it.
  EOS rule: ON for active shoots, so agents reading sidecars see current state.
- **Develop presets stop scaling past ~2000.** The Develop module renders a
  thumbnail per visible preset every time you change images. 2000+ = lag.
  Cull aggressively. Group by purpose, not by author.
- **AI Denoise pre-LrC 14.4 created a DNG copy** of every denoised raw — disk
  bloat trap. 14.4+ (June 2025) is non-destructive, no DNG. Always check
  `Help > System Info` for version before scripting.
- **Order matters: Denoise BEFORE masking BEFORE generative.** AI tools work
  on the noise floor under them. Denoise first or your masks chase grain.
- **Lightroom API does not accept raw bytes** — only presigned URLs from S3,
  Azure Blob, or Dropbox. Plan storage accordingly.
- **API jobs are async.** POST returns a job URL. Poll until status is
  `succeeded` or `failed`. There is no synchronous render endpoint.
- **Lightroom Classic and Lightroom (Cloud) are different products** sharing
  a name and a develop engine. Antony's catalog is Classic — never confuse
  the two when documenting workflows or writing automation.
- **Process Version drift.** Old edits use older Adobe Camera Raw process
  versions (PV2003, PV2010, PV2012, current). Updating an old image to the
  current PV may shift the look. Test before bulk-updating.
- **Tethered capture is Classic-only** and depends on a vendor SDK match
  (Sony, Canon, Nikon firmware vs LrC version). Always test the day before
  a paid shoot.

See references/best_practices.md for the full 19-section creator-level
knowledge base, EOS usage patterns, and gotcha catalog.
