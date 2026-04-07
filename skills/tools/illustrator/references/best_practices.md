# Illustrator — Creator-Level Best Practices
Source: developer.adobe.com/illustrator/uxp, helpx.adobe.com/illustrator, Adobe Firefly Services docs, ai-scripting.docsforadobe.dev (legacy ExtendScript reference)
API Version: Illustrator 28.x (CC 2025) document object model
SDK Version: UXP Scripting v6 (host UXP 8.x); legacy ExtendScript still supported as `.jsx`
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

Illustrator the **desktop app** authenticates against Adobe Identity once at
sign-in. The credential is a refreshable Adobe ID token persisted by the
Creative Cloud desktop client; license re-validation happens silently every
~30 days. UXP scripts run in-process under the user's permissions — there is
no API key surface to manage and no per-script auth. Anyone who can run
Illustrator can run any script.

Illustrator-specific **cloud APIs** are limited. As of 2026-04 there is no
general "Illustrator API" comparable to Photoshop API. The relevant cloud
surfaces are:

- **Firefly Services — Generate Vector** (text-to-SVG) and **Generate Vector
  Pattern**. OAuth2 server-to-server (client credentials) via IMS. You
  exchange `client_id` + `client_secret` for a bearer token, then call
  `https://firefly-api.adobe.io/v3/images/generate-vector` (and the pattern
  variant). Token TTL ~24h. Scopes: `openid`, `AdobeID`, `firefly_api`,
  `ff_apis`.
- **Adobe Fonts API** — read-only metadata, separate IMS token.
- **CC Libraries API** — IMS token, scope `cc_libraries.read,cc_libraries.write`.

Auth recipe (Firefly):

```bash
curl -X POST https://ims-na1.adobelogin.com/ims/token/v3 \
  -d grant_type=client_credentials \
  -d client_id="$ADOBE_CLIENT_ID" \
  -d client_secret="$ADOBE_CLIENT_SECRET" \
  -d scope="openid,AdobeID,firefly_api,ff_apis"
```

Store both halves in `.env`. Never hardcode. Never commit. Tokens go through
the standard rotate-on-suspicion playbook.

EOS consequence: treat Illustrator as a **local tool with a thin remote
shoulder** for vector generation. The desktop is the source of truth.

## Core Operations with Exact Signatures

The UXP scripting model exposes the document tree as JS objects. Key entry
points:

```javascript
const ill = require("illustrator");
const app = ill.app;                       // host app
const doc = app.activeDocument;            // current document
const docs = app.documents;                // collection
```

### Document operations

```
app.documents.add(documentPreset)              → Document
app.open(file)                                 → Document   (await)
doc.close(saveOptions)                         → Promise
doc.save()                                     → Promise
doc.saveAs(file, saveOptions)                  → Promise
doc.exportFile(file, exportType, options)      → Promise
doc.imageCapture(file, clipBounds, options)    → Promise   (raster snapshot)
doc.print(options)                             → Promise
doc.selectObjectsOnActiveArtboard()
doc.rasterize(items, ...)
```

`exportType` enum: `EPS`, `SVG`, `PDF`, `PNG24`, `PNG8`, `JPEG`, `TIFF`,
`PSD`, `FXG`, `TextFormat`. Each takes a corresponding `Export*Options`
object.

### Artboards

```
doc.artboards                                   → Artboards collection
doc.artboards.add(artboardRect)                 → Artboard
doc.artboards.getActiveArtboardIndex()          → number
doc.artboards.setActiveArtboardIndex(index)
doc.artboards.getByName(name)                   → Artboard
doc.artboards.remove(index)
ab.name, ab.artboardRect, ab.rulerOrigin, ab.showCenter, ab.showCrossHairs
```

`artboardRect` is `[left, top, right, bottom]` in points, with **Y growing
DOWN from the document top** in modern Illustrator (post-CS5 coordinate
system flip — older scripts assumed Y up).

### Layers and PageItems

```
doc.layers.add()                              → Layer
doc.layers.getByName(name)                    → Layer
layer.locked, layer.visible, layer.printable
layer.pageItems                               → PageItems collection
layer.pathItems, layer.textFrames, layer.groupItems, layer.placedItems,
layer.symbolItems, layer.compoundPathItems, layer.rasterItems
pi.position = [x, y]
pi.width, pi.height, pi.rotate(angle), pi.scale(sx, sy)
pi.translate(dx, dy)
pi.duplicate(relativeObject, insertionLocation)
pi.zOrder(ZOrderMethod.BRINGTOFRONT)
pi.remove()
```

### Path items

```
layer.pathItems.add()                         → PathItem
pi.setEntirePath([[x1,y1],[x2,y2],...])
pi.closed = true
pi.filled = true; pi.fillColor = swatchOrColor
pi.stroked = true; pi.strokeColor = ...; pi.strokeWidth = 0.5
pi.pathPoints                                 → PathPoints
```

### Text frames

```
layer.textFrames.add()                        → TextFrame
tf.contents = "Hello"
tf.position = [x, y]
tf.textRange.characterAttributes.size = 24
tf.textRange.characterAttributes.tracking = 50          // 1/1000 em
tf.textRange.characterAttributes.textFont = app.textFonts.getByName("Inter-Bold")
tf.textRange.paragraphAttributes.justification = Justification.CENTER
tf.createOutline()                                       // type → paths
```

### Color, swatches, gradients

```
new ill.RGBColor()       { red, green, blue }            (0-255)
new ill.CMYKColor()      { cyan, magenta, yellow, black } (0-100)
new ill.GrayColor()      { gray }                         (0-100)
new ill.SpotColor()      { spot, tint }
new ill.GradientColor()  { gradient, angle, length, origin, hiliteAngle, hiliteLength, matrix }

doc.swatches.add()                            → Swatch
swatch.color = colorObject                    // RGBColor / CMYKColor / SpotColor
doc.spots.add()                               → Spot (Pantone-style)
spot.colorType = ColorModel.SPOT
spot.color = new ill.CMYKColor()              // tint base
```

Global swatch behavior is implicit on `Spot` and explicit (via toggle in the
Swatch Options dialog) on RGB/CMYK swatches. **Set `.spot` or use the Swatch
Options checkbox** to make a regular swatch global.

### Symbols, brushes, styles

```
doc.symbols.add(art, registrationPoint)       → Symbol
doc.symbolItems.add(symbol)                   → SymbolItem (instance)
doc.brushes                                   → Brushes (read-only collection)
doc.graphicStyles.getByName(name).applyTo(item)
doc.characterStyles, doc.paragraphStyles
```

You **cannot create brushes via script** — they must be authored in the GUI
and ride along in the document or in a brush library `.ai` file.

### Save / export option objects

```
new ill.PDFSaveOptions()
  .compatibility = PDFCompatibility.ACROBAT5
  .preserveEditability = true
  .pDFXStandard = PDFXStandard.PDFX1A2001
  .colorConversionID = ColorConversion.None
new ill.IllustratorSaveOptions()
  .compatibility = Compatibility.ILLUSTRATOR28
  .pdfCompatible = true
new ill.ExportOptionsSVG()
  .embedRasterImages = false
  .fontType = SVGFontType.OUTLINEFONT
  .documentEncoding = SVGDocumentEncoding.UTF8
  .coordinatePrecision = 2
new ill.ExportOptionsPNG24()
  .antiAliasing = true
  .transparency = true
  .artBoardClipping = true
  .horizontalScale = 200       // %
  .verticalScale = 200
new ill.ExportForScreensOptionsPNG24()
new ill.ExportForScreensOptionsWebOptimizedSVG()
```

The "Export For Screens" surface is preferred for batched multi-scale output:

```
doc.exportForScreens(folder, exportForScreensType, exportOptions, itemToExport, fileNamePrefix)
```

### Worked example — full per-artboard SVG export

```javascript
const ill = require("illustrator");
const fs  = require("uxp").storage.localFileSystem;

(async () => {
  const doc = ill.app.activeDocument;
  const out = await fs.getFolder();
  const opts = new ill.ExportForScreensOptionsWebOptimizedSVG();
  opts.coordinatePrecision = 2;
  opts.cssProperties = ill.SVGCSSPropertyLocation.PRESENTATIONATTRIBUTES;
  opts.fontType = ill.SVGFontType.OUTLINEFONT;
  opts.svgMinify = true;

  await doc.exportForScreens(
    out,
    ill.ExportForScreensType.SE_SVG,
    opts,
    ill.ExportForScreensItemToExport.ALL_ARTBOARDS,
    ""
  );
})();
```

## Pagination Patterns

N/A — Illustrator's scripting surface is local and synchronous over a single
in-memory document model. There is no paginated resource. Collections
(`doc.pathItems`, `doc.layers`, `doc.swatches`, etc.) return all items at
once. The cloud Firefly Vector endpoints return one or more variations per
request via a single response payload — no cursors, no continuation tokens.

## Rate Limits

N/A for the desktop scripting layer. **Firefly Services** vector endpoints
are billed per generation and rate-limited per Adobe organization (current
default: 60 requests/minute, configurable on enterprise plans). On 429
responses, back off exponentially and respect `Retry-After` if present.
There is no per-document scripting rate limit — UXP scripts are bounded
only by host CPU and the renderer.

## Error Codes and Recovery

UXP scripts throw standard JS `Error` objects with a `.message`. Common
patterns:

| Symptom | Cause | Recovery |
|---|---|---|
| `No such element` | `getByName` against a missing layer/swatch/style | guard with `try/catch`, fall back to creation |
| `The object is locked` | layer or item locked or hidden | `.locked = false; .visible = true` first |
| `Type mismatch` | passed a JS Number where an enum was expected | use `ill.SomeEnum.VALUE` not raw int |
| `Cannot save the file` | path inside a sandboxed UXP folder you don't own | use `fs.getFolder()` user-pick, not hardcoded path |
| `Could not complete the action because of a font problem` | missing font referenced by document | activate via Adobe Fonts, or `createOutline()` |
| `An Illustrator error occurred: 1346458189 ('PARM')` | malformed parameter, often artboardRect not 4-element array | check arity and types |
| Firefly `401 Unauthorized` | IMS token expired or wrong scope | refresh token, verify scope includes `firefly_api` |
| Firefly `429 Too Many Requests` | rate limit | exponential backoff |
| Firefly `400` with `inputImage` errors | unsupported MIME or size | confirm SVG ≤ 10MB, MIME `image/svg+xml` |

Recovery rule: **never swallow errors silently in a UXP script** — write to
`console` and surface to the user via `app.showAlert()` so the GUI operator
sees the failure.

## SDK Idioms

UXP is JavaScript with `async/await`, ES2020+. The host app exposes
`require("illustrator")` and `require("uxp")`. There is no separate "SDK
package" to install; the SDK is the host runtime.

Idiomatic patterns:

```javascript
// 1. Always grab activeDocument once and reuse
const doc = require("illustrator").app.activeDocument;

// 2. Use try/finally to restore state (selection, active layer)
const prev = doc.activeLayer;
try { /* mutate */ } finally { doc.activeLayer = prev; }

// 3. Use the storage API for any file I/O — never assume node fs
const fs = require("uxp").storage.localFileSystem;
const folder = await fs.getFolder();           // pops a picker
const file   = await folder.createFile("out.svg", { overwrite: true });

// 4. Wrap mutations in executeAsModal when running from a panel
const { executeAsModal } = require("photoshop").core;  // host equivalent in Ill UXP
await executeAsModal(async () => { /* doc edits */ }, { commandName: "Batch export" });

// 5. Defer to Action panel for things scripting can't do
//    (creating brushes, certain pathfinder operations on complex art)
```

For the **legacy ExtendScript** path, the same object graph is exposed
synchronously via `#target illustrator` and `app.activeDocument.*`. The two
surfaces share idioms — porting is mostly removing `#target` headers, adding
`async/await`, and replacing `File`/`Folder` with the UXP `storage` API.

## Anti-Patterns

1. **Treating artboards as containers.** Items aren't "in" an artboard. They
   sit at coordinates that may overlap one or more artboard rects. Don't
   write `artboard.pageItems` — it doesn't exist meaningfully.
2. **Local CMYK fills instead of global swatches.** Editing the swatch
   doesn't update the art, recoloring doesn't work, brand changes become
   manual hunts. Always swatch-first.
3. **Outlining type before sending the .ai master to a collaborator.** You
   destroy editability. Outline only on export to the print vendor's PDF.
4. **Saving without `pdfCompatible: true`.** Breaks Figma import, InDesign
   place, Acrobat preview. Default ON unless you have a reason.
5. **Hardcoding paths in UXP scripts.** Script can't access arbitrary
   filesystem locations — use `fs.getFolder()` user picker.
6. **Using `app.showAlert` inside a tight loop.** Halts the script per
   iteration. Collect errors and show one summary alert at the end.
7. **Recording an Action that depends on font activation that isn't on the
   target machine.** Action fails silently or uses fallback font.
8. **Exporting SVG with default settings for web use.** You'll get embedded
   `<style>` blocks and inline raster images. Set Presentation Attributes,
   no embed, decimal precision 2.
9. **Ignoring artboard naming.** Export filenames come from artboard names.
   "Artboard 1" everywhere is a deliverable disaster.
10. **Mixing CMYK and RGB swatches in one document.** Color management gets
    confused, on-screen preview lies. Decide CMYK (print) or RGB (web) at
    document creation.
11. **Using the legacy `app.activeDocument.activeView.zoom` from JSX in a
    UXP context.** UXP doesn't expose the view API the same way. Don't port
    UI-state code; port data-mutation code only.
12. **Trying to script brush creation.** Not supported. Create brushes in
    GUI, ship them in a brush library `.ai`.
13. **Forgetting to set `coordinatePrecision` on SVG export.** Default
    precision can produce huge files for complex art.
14. **Generating spec briefs without nearest-Pantone matches.** Print vendors
    will reject "use #FF6B35" — they need PMS or a process build.

## Data Model

Hierarchy: **Application → Documents → Document → Layers → PageItems**.

```
app
├── documents (collection)
│   └── document
│       ├── artboards (collection of Artboard rects)
│       ├── layers (tree)
│       │   ├── layers (sublayers)
│       │   ├── pageItems (everything visible)
│       │   ├── pathItems
│       │   ├── compoundPathItems
│       │   ├── textFrames
│       │   ├── groupItems
│       │   ├── placedItems     (linked raster/vector)
│       │   ├── rasterItems     (embedded raster)
│       │   ├── symbolItems     (instances)
│       │   └── meshItems
│       ├── swatches
│       ├── spots               (Pantone / spot colors)
│       ├── gradients
│       ├── patterns
│       ├── symbols             (definitions)
│       ├── brushes             (read-only)
│       ├── graphicStyles
│       ├── characterStyles
│       ├── paragraphStyles
│       ├── variables           (for data-driven graphics)
│       └── views
├── textFonts (system + Adobe Fonts activated)
├── colorSettings
└── preferences
```

**Coordinate system**: points (1pt = 1/72 inch). Origin at top-left of the
document, Y growing **down** in modern Illustrator (post-CS5). `rulerOrigin`
on each artboard can offset the apparent ruler but the document model uses
absolute points.

**Z-order**: per layer, item index 0 is the topmost. `zOrder()` moves items
within a layer; `move()` reparents across layers.

**Selection**: `doc.selection` is an array of currently selected PageItems.
Mutating it mutates the GUI selection.

**Color models**: documents are CMYK or RGB at creation; this dictates which
`Color` subclass swatches store. Mixing within one doc is allowed but
discouraged — Illustrator converts on the fly and small color drift results.

## Webhooks and Events

Mostly N/A. Illustrator has **no network webhook surface**. There is a
local event subscription system for UXP plugins (`require("uxp").host.events`)
but it is panel-scoped and limited to host lifecycle events
(`document-created`, `document-activated`, `document-closed`,
`selection-changed`, `before-save`, `after-save`). For automation triggered
by external systems (e.g. "new client onboarding row in Notion → generate
brand sheet"), use a server process to render via Firefly Services or to
queue a script that the operator runs in Illustrator on next open.

Firefly Services has **no webhook delivery** — generation is request/response
synchronous. Long-running renders use job IDs polled via GET.

## Limits

- **Artboards per document**: 1000 (hard cap)
- **Layers per document**: practically unlimited; tens of thousands degrade
  the Layers panel UI
- **Path points per path**: 32k anchor points hard cap (post-CC 2018)
- **Document dimensions**: 16,383 x 16,383 pt (227 x 227 inches at 1:1).
  Larger artwork uses scale (1:10, 1:100) at design time.
- **Symbol instances**: tens of thousands fine; updating master propagates
- **Swatches per document**: thousands fine; recolor performance degrades
- **Linked images**: hundreds fine; relinking on file move is per-item
- **UXP script execution time**: no hard limit, but synchronous loops over
  10k+ items will hang the UI without `await` yields
- **Firefly Vector input image**: ≤ 10 MB, SVG/PNG/JPG
- **Firefly Vector output**: variable, typically 100KB-2MB SVG
- **PDF/X-1a max raster resolution**: dictated by print vendor profile

## Cost Model

**Desktop license**: Adobe Creative Cloud subscription. Single-app
Illustrator ~$22.99/mo, All Apps ~$59.99/mo, Teams pricing higher. Annual
commit discounts. No per-script or per-export billing.

**Firefly Services**: per-generation pricing in "generative credits."
Vector generation is roughly 4-8 credits per call (text-to-vector). Adobe
Firefly plans bundle credits monthly; overage charged separately. Vector
pattern generation: similar credit cost. As of 2026-04 the standalone
Firefly Pro plan includes 7,000 credits/mo; enterprise plans negotiate
custom blocks.

**Adobe Fonts**: included in CC subscription. No per-font fee.

**Pantone Connect**: separate subscription (~$15/mo), required for live
Pantone library access since 2022. Without it, existing Pantone references
in old files still display as named swatches but cannot be picked from a
fresh Pantone book.

EOS budget rule: at pre-revenue stage, single-app Illustrator + free Pantone
fallback (use process CMYK builds with documented Pantone matches in spec
briefs) keeps overhead ≤ $25/mo.

## Version Pinning

Check version: `Illustrator → About Illustrator` (macOS) or `Help → About`
(Windows). Format: `Illustrator 28.x.y` (CC 2025 line as of 2026-04).

Notable version inflections:

- **CS5 (15.x)** — coordinate system flipped; older scripts assuming Y up break
- **CC 2018 (22.x)** — Variable Fonts support; Properties panel introduced
- **CC 2020 (24.x)** — Recolor with Adobe Sensei; auto spell check
- **CC 2022 (26.x)** — Pantone Connect plugin replaces bundled libraries;
  3D & Materials panel replaces legacy 3D Effect
- **CC 2023 (27.x)** — Generative Recolor (Firefly), real-time drawing on
  iPad parity, Intertwine
- **CC 2024 (28.x)** — Mockup (place vector on raster), Retype (image to
  editable type), Text to Vector Graphic (Firefly inside Illustrator)
- **UXP scripting GA (2023, parallel to CC 2024)** — JSX still supported
  but new features land in UXP first

Version-breaking caveats:

- A `.ai` saved with `Compatibility.ILLUSTRATOR28` cannot be opened by CC
  2017 or earlier without "Save As Legacy" downgrading
- Variable fonts in a document opened in CC 2017 lose axis info
- Generative features create raster fallbacks for older opens

EOS pin: **CC 2024 (28.x) minimum**, UXP scripts as the default automation
surface, JSX retained only for features UXP doesn't expose yet.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

Adobe Illustrator was first shipped in 1987 as the GUI front-end to Adobe's
PostScript page description language. PostScript was the lingua franca of
laser printers and high-end typesetting; Illustrator existed to let designers
draw curves and set type that PostScript could rasterize at any resolution.
That origin is still visible everywhere in the product:

1. **Bezier curves are first-class.** Every path is a sequence of cubic
   Bezier segments — same primitive PostScript uses. The Pen tool exists
   because someone has to author those control points, and the muscle memory
   of every print designer in the world is built around it.

2. **Resolution independence.** A logo drawn in Illustrator at 1 inch wide
   prints identically at 100 inches wide. There is no "DPI" on a vector path.
   This is the entire reason Illustrator owns the logo/garment/print market:
   one source file, infinite output sizes, zero quality loss.

3. **Color management is built in, not bolted on.** ICC profiles, soft
   proofing, separations preview, and overprint preview ship in the box.
   Photoshop has these too; Figma and Sketch barely have them. For anything
   that ends up on physical material, this is non-negotiable.

4. **Multi-artboard layout.** A single document can hold up to 1000
   independent artboards — a logo system, a brand sheet, an entire icon set,
   a stationery suite — all sharing one swatch palette, one type style
   library, one symbol set. This is how Illustrator competes with multi-page
   tools (InDesign for long documents, Figma for screens) without becoming
   either of them.

Tradeoffs vs alternatives:

- **vs Figma.** Figma wins on real-time collaboration, browser access, ease
  of onboarding, and native screen-design workflow (auto-layout, components,
  variants). Illustrator wins on print, color management, complex paths,
  type engine sophistication, and SVG fidelity. For Lyfe Spectrum garment
  graphics and Initiate Arena print collateral, Illustrator is correct. For
  Empyrean Studio web/app interface mocks, Figma is correct. Use both.
- **vs Affinity Designer.** Affinity wins on price (one-time purchase) and
  raw drawing performance. Illustrator wins on file format ubiquity,
  Pantone integration, plugin/script ecosystem, and the fact that every
  print vendor and every brand asset library on earth speaks `.ai`.
- **vs Inkscape.** Inkscape is free, open source, and SVG-native. Illustrator
  wins on type engine, color management, PDF output, and CC ecosystem. For
  one-off SVG hacking on a Linux server, Inkscape CLI is fine. For brand work,
  no.
- **vs Sketch.** Sketch is screen-only, macOS-only, and abandoned the pro
  print market years ago. Not in the running.
- **vs CorelDRAW.** Still alive in apparel/sign-shop niches. Loses on
  ecosystem and script automation surface.

What Illustrator is explicitly NOT: a page layout tool (use InDesign), a
photo editor (use Photoshop), a UI design tool (use Figma), a 3D modeler
(the 3D & Materials panel is a toy compared to Blender), or a real-time
collaborative tool. Recognize these boundaries and reach for the right tool.

## Problem-Solution Map and Hidden Capabilities

Things 90% of users never discover:

- **Recolor Artwork (Edit → Edit Colors → Recolor Artwork).** Pull every
  color in your selection into a wheel, drag relationships, generate
  colorways. Combine with Color Groups for stored palettes. Pair with the
  Generative Recolor button (Firefly) to brainstorm.
- **Global Edit (Select → Start Global Edit).** Pick a logo on one artboard,
  Illustrator finds visually similar instances across the document, edit
  them all simultaneously. Replaces 90% of "I need to update this in 12
  places" workflows.
- **Symbols + 9-slice scaling.** Place a symbol, scale it, the corners stay
  fixed while the middle stretches — like CSS border-image. Perfect for
  badge/seal templates.
- **Image Trace + Expand.** Drop a raster sketch, click Image Trace,
  Expand, you have a vector. Then Simplify Path. Then clean up. This is
  the fastest "logo from a napkin sketch" pipeline that exists.
- **Pathfinder + Shape Builder.** Shape Builder (Shift+M) is the modern
  alternative to Pathfinder's modal buttons. Drag across overlapping shapes
  to merge, Alt+drag to subtract. Faster than every other approach for
  complex constructive geometry.
- **Appearance panel.** Multiple fills and strokes per object, each with
  its own effects, in a stack. The hidden "object styles" engine. Use it
  to build a star-burst with 4 strokes from one path.
- **Graphic Styles.** Save an Appearance panel state as a style. Drag onto
  any object to apply. Change the style definition, every applied instance
  updates. The vector equivalent of CSS classes.
- **Width tool (Shift+W).** Variable-width strokes by dragging directly on
  the stroke. Save profiles for reuse. Replaces 90% of "I need a tapered
  line" hacks.
- **Live Corners.** Select corner anchor points, drag the small circle
  inward — round corners that stay editable. Set radius numerically in
  Properties. Per-corner control.
- **Type on a Path + Path Type Options.** Set type along any open or closed
  path. Align ascenders, baselines, or center to path. The right way to
  curve a tagline around a badge.
- **Glyphs panel (Window → Type → Glyphs).** Direct access to every glyph
  in the active font, including OpenType alternates, ligatures, swashes,
  small caps, fractions. Critical for typography-driven brands.
- **Variable fonts.** Single font file with continuous axes (weight, width,
  optical size, slant). Animate weight in motion graphics, fine-tune
  exact tracking, save half a megabyte of font files. Inter, Roboto Flex,
  Recursive are excellent open variable fonts.
- **CC Libraries.** Sync swatches, type styles, symbols, character styles,
  graphics across documents and across machines. The right home for a brand
  system you reuse.
- **Asset Export panel.** Drag artwork onto the panel, configure scales
  and formats per asset, click Export. Faster than Save As for one-off
  assets that don't deserve their own artboard.
- **Repeat (Object → Repeat → Radial / Grid / Mirror).** Live, parametric
  repeats with editable seed art. Edit the seed, all instances update.
  Mind-blowing for pattern work.
- **Mockup (Object → Mockup).** Place vector artwork onto a raster mockup
  with perspective + warp from Sensei. Auto-detects garment surfaces.
  Critical for Lyfe Spectrum tech-pack visualization without leaving
  Illustrator.
- **Retype (Type → Retype).** Convert lettering in a raster image to live
  editable type by matching font. Saves rebuilding old logo files.
- **Generative features (Firefly inside Illustrator)** — Text to Vector
  Graphic, Generative Recolor, Generative Pattern, Generative Shape Fill.
  All credit-billed.
- **Variables panel + XML data merge.** Yes, Illustrator has a data-merge
  feature like InDesign. Bind text frames and image placeholders to
  variables, drive from XML, batch-generate. The "1000 personalized
  certificates" workflow.

## Operational Behavior and Edge Cases

- **Auto-recovery**: enabled by default, configurable in Preferences →
  File Handling. Saves a recovery file every N minutes. After a crash,
  next launch offers to restore. Works well; rely on it but don't trust it
  for mission-critical work — also Save As often.
- **Linked vs embedded images**: linked images stay outside the `.ai` file
  and reload on open. Move the source file → "Missing link" warning.
  Embedded images are baked in (file size grows). Use Links panel to
  switch between, package, or relink. For Lyfe Spectrum tech packs always
  embed before sending to vendor.
- **Cloud documents (.aic)**: stored in Adobe cloud, sync across devices,
  enable real-time co-editing. Local `.ai` files do not. The trade is
  filesystem control vs sync — for EOS choose local `.ai` in
  `/opt/OS/brand_assets/` so version control through git LFS is possible.
- **Color profile mismatches**: opening a CMYK doc with a different working
  CMYK profile triggers a dialog — "Use embedded" vs "Convert to working."
  Almost always **Use embedded** to preserve appearance.
- **Outline mode (Cmd/Ctrl+Y)**: see paths only, no fills. Fast for
  navigation in complex docs.
- **Pixel Preview (Cmd/Ctrl+Alt+Y)**: see how artwork will rasterize at
  current zoom. Critical for icon design where snap-to-pixel matters.
- **Snap to Pixel + Align New Objects to Pixel Grid**: required for clean
  icon export. Set in Document Setup.
- **Smart Guides (Cmd/Ctrl+U)**: dynamic alignment lines as you drag.
  Indispensable, sometimes annoying. Toggle frequently.
- **Isolation Mode**: double-click into a group/symbol to edit in place
  with the rest of the document grayed out. Esc to exit. Faster than
  ungroup/regroup.
- **Pasteboard size**: ~227 x 227 inches max. Exceeds and Illustrator
  refuses to scroll further. Design at scale.
- **Memory ceiling**: 64-bit only since CC 2018. Can use as much RAM as
  the OS gives it, but very large documents (~500MB+) start swapping.
- **Stroke alignment**: inside / center / outside the path. Default is
  center. Outside aligned strokes on closed paths can wreck export bounds.

## Ecosystem Position and Composition

Illustrator sits inside Adobe Creative Cloud and composes naturally with:

- **Photoshop** — copy/paste vectors as Smart Objects (stay editable),
  paste as paths (Photoshop path), pixels (rasterize), or shape layers
- **InDesign** — Place `.ai` natively, layers preserved, recoloring via
  InDesign swatches if global. Standard print pipeline.
- **After Effects** — Import `.ai` as composition, layers become AE layers,
  paths become AE shape layers via Create Shapes from Vector Layer
- **XD** — deprecated, but historically copy/paste preserved vector fidelity
- **Figma** — Copy as SVG → paste into Figma. Round-trip is one-way; no
  good way to round-trip from Figma back to Illustrator without losing
  effects.
- **Substance 3D** — Vector logos onto 3D models for product mockups
- **Firefly** — In-app generative buttons + Firefly Services REST API for
  server-side
- **Stock + Mockup libraries** — Adobe Stock vector assets license-bundled

External composition:

- **Print vendors** — speak `.ai`, `.pdf` (PDF/X-1a or X-4), `.eps`. Default
  output: PDF/X-1a CMYK with bleed.
- **Web pipelines** — `.svg` (Export For Screens, Web Optimized SVG)
- **Garment vendors (DTG, screen print, embroidery)** — `.ai`, `.pdf`,
  sometimes `.eps`. Embroidery houses also want `.dst` which Illustrator
  doesn't produce — round-trip via Wilcom or Hatch.
- **App icon pipelines** — Export For Screens at iOS/Android scale presets

EOS-specific compositions:

- Illustrator → SVG → Lyfe Spectrum saas product images
- Illustrator → PDF/X-1a → garment screen print vendor
- Illustrator → SVG → Initiate Arena cert generation pipeline (Python +
  rsvg-convert)
- Illustrator UXP scripts → drive from Antony's local machine, never the
  VPS

## Trajectory and Evolution

The arc of Illustrator over the last decade:

- **2014-2016** — Touch tools, Live Corners, Image Trace overhaul. The
  product was stable; updates were polish.
- **2017-2019 (CC 2018-2020)** — Properties panel, Variable Fonts, Freeform
  Gradients, Global Edit. The first wave of "make Illustrator easier."
- **2020-2022** — Cloud documents, real-time collaboration, iPad version
  reaches near-parity, recolor with Sensei. The "Figma response" wave.
- **2022-2023** — Pantone moves to subscription Pantone Connect (community
  outrage, still resented), 3D & Materials panel replaces ancient 3D
  Effect, Intertwine for over-under weaving.
- **2024-2025 (CC 2024)** — Generative AI lands inside the host:
  - **Text to Vector Graphic** (Firefly) — type a prompt, get vector art,
    fully editable
  - **Generative Recolor** — describe a mood, get palette variations
  - **Generative Pattern** — text-to-pattern
  - **Generative Shape Fill** — fill a shape with generated vector content
  - **Mockup** — place vector on raster mockup with auto-warp
  - **Retype** — image lettering to editable type
- **2025-2026 (CC 2025, Illustrator 28.x)** — UXP scripting reaches GA
  parity for most surfaces; Firefly Services adds standalone Generate Vector
  REST endpoint; iPad version gets full UXP plugin support; Variable Fonts
  axis animation on the timeline previewed at MAX 2025.

Direction of travel: **AI generation as a first-class authoring surface,
UXP scripting as the canonical automation layer, cloud docs and real-time
co-edit closing the gap with Figma**. ExtendScript is on its way out but
hasn't been killed; treat it as legacy and write new automation in UXP.

## Conceptual Model and Solution Recipes

Mental model: **Illustrator is a typed object graph that renders to
PostScript / PDF / SVG.** Every operation either creates, mutates, or
traverses that graph. The GUI is a viewer over the graph; scripts are
another viewer.

Recipes:

### Recipe — Brand sheet from a list of hex colors

1. New document, RGB color mode, Letter size, 1 artboard
2. For each hex in the palette: create a global swatch (Swatches panel,
   New Swatch, Global checkbox ON)
3. Create a Layer per swatch (locks/visibility per color)
4. Use Symbols for any element that repeats across pages
5. Use Character Styles for type lockups
6. Save As `.ai` with PDF Compatible ON
7. Export For Screens → PDF, all artboards, one PDF per artboard

### Recipe — Lyfe Spectrum garment graphic separation

1. Open the artwork file
2. Layers panel: one layer per spot color, named `PMS 185 C`, `White`, etc.
3. Move every path to its corresponding spot-color layer
4. Convert every fill/stroke to the matching Spot swatch (not local CMYK)
5. Window → Separations Preview → toggle each plate to verify
6. File → Save As → PDF → PDF/X-1a:2001 → Output: No Color Conversion,
   Preserve CMYK Numbers
7. Send to vendor with the layer name as the spot color name

### Recipe — Initiate Arena badge generator

1. Master `.ai` with placeholder text frames named via Variables panel
   (e.g. `participant_name`, `cohort`, `date`)
2. CSV with one row per participant
3. UXP script: for each row, set text frame contents from CSV, export
   artboard as PNG, repeat
4. Output to `brand_assets/initiate-arena/badges/YYYY-MM-DD/`
5. Verify count matches CSV row count

### Recipe — Web SVG icon set

1. New doc, 24x24 px artboards, Pixel Preview ON, Snap to Pixel ON
2. Align New Objects to Pixel Grid ON
3. Draw on integer coordinates only
4. Stroke alignment: inside (so 1px strokes don't fall on half pixels)
5. No effects (drop shadows, blurs) — they don't survive minified SVG
6. Export For Screens → SVG → Web Optimized SVG → Presentation
   Attributes, Outline Fonts, Decimal 2, Minify ON
7. Run output through SVGO for further optimization

### Recipe — Empyrean Studio client logo system

1. One master `.ai`, multi-artboard:
   - `logo-primary` (full color, full lockup)
   - `logo-secondary` (alternate orientation)
   - `logo-mono-black`, `logo-mono-white`
   - `logo-icon-only`
   - `clear-space-rules`
   - `dont-do-this`
2. Global swatches for brand colors
3. Character Styles for any type
4. Export For Screens → all artboards → SVG + PNG@2x + PDF
5. Package fonts (File → Package) before sending source to client
6. Deliver: `source.ai`, `exports/` folder, `brand-guide.pdf`

## Industry Expert and Cutting-Edge Usage

What top-tier designers and studios are doing in Illustrator that the
average user isn't:

- **Design systems in CC Libraries**, synced across team Adobe IDs.
  Swatches, type styles, symbols all live in one library, every project
  pulls from it. Updating the library updates every linked instance.
- **Variable font axis automation** — animate weight, width, optical size
  across artboards for a single document that becomes a complete typographic
  exploration.
- **UXP panels as in-house tools** — branded panels that surface a studio's
  custom workflows (template starters, brand swatch loaders, batch
  exporters) directly inside Illustrator's UI. Built with React + Adobe
  Spectrum + UXP plugin manifest.
- **Hybrid AI workflows** — Text to Vector Graphic for ideation, Generative
  Recolor for palette exploration, then human refinement. Treat the AI as
  a "junior designer who never sleeps and produces 100 mediocre options
  fast" — use as starting points, never as deliverables.
- **Substance materials on Illustrator vector mockups** for product
  visualization without leaving the Adobe stack.
- **Live data merge from Notion/Airtable** via export-to-CSV → Variables
  panel → batch generate. Cert mills, ID badge runs, personalized
  marketing.
- **Git LFS for `.ai` source control** — large binary diffing isn't
  meaningful but version history is. Tag releases of brand assets like
  software releases.
- **Headless render farms via Firefly Services** for vector generation at
  scale (hundreds of variations per request batch), then human curation
  in Illustrator.
- **iPad + Apple Pencil for the rough draw**, sync to desktop via Cloud
  Docs, finalize on desktop with the precision of mouse + keyboard.
- **Retype + Image Trace combo** to recover legacy logos from scanned
  letterheads and business cards — a billable service for any brand
  refresh.

## EOS Usage Patterns

How EOS uses Illustrator concretely:

### 1. Spec brief generation (agent-side, before Antony opens the file)

Agents draft a markdown brief with:
- Document specs: dimensions, color mode (CMYK for print, RGB for web),
  bleed, safe area
- Color palette: primary, secondary, accent — hex + nearest Pantone match
- Type lockup: font name (with Adobe Fonts ID), weight, size, tracking,
  leading, alignment
- Artboard list: one per deliverable, named explicitly
- Export targets: filename pattern, format, color profile, scale
- Verification checklist: file naming, dimensions, color profile,
  font outlines

Brief lives at `/opt/OS/brand_assets/<brand>/briefs/YYYY-MM-DD-<deliverable>.md`.
Antony reads, opens Illustrator, executes.

### 2. Reference UXP scripts (run by Antony, not agents)

Agents maintain a library at `/opt/OS/brand_assets/_scripts/`:
- `batch_export_artboards.js` — every artboard to chosen format
- `swatch_replace.js` — find and replace one swatch with another
  document-wide
- `apply_paragraph_style.js` — bulk apply named paragraph style
- `outline_all_text.js` — for print prep
- `rename_layers_from_csv.js` — bulk rename
- `generate_colorways.js` — duplicate document N times with N different
  global swatch sets

Each script starts with a header comment explaining usage. Antony runs via
`File → Scripts → Other Script...`.

### 3. Post-export verification (agent-side, after Antony exports)

After export, agents check `brand_assets/<brand>/exports/YYYY-MM-DD/`:
- Filename pattern matches brief
- File count matches expected artboard count
- SVG: opens in browser, size sane, no embedded raster
- PDF: PDF/X-1a compliant via `pdfinfo` / `qpdf --check`
- PNG: dimensions and DPI match brief

Verification command examples:

```bash
# SVG sanity
xmllint --noout brand_assets/lyfe-spectrum/exports/2026-04-06/*.svg

# PDF/X check
pdfinfo brand_assets/lyfe-spectrum/exports/2026-04-06/tee-front.pdf | grep -E "PDF|Pages|Page size"

# PNG dimensions
identify brand_assets/initiate-arena/exports/2026-04-06/badge-*.png
```

### 4. Brand asset directory convention

```
/opt/OS/brand_assets/
├── _scripts/                       # shared UXP scripts
├── lyfe-spectrum/
│   ├── source/                     # .ai masters
│   ├── briefs/                     # agent-generated specs
│   ├── exports/YYYY-MM-DD/         # dated outputs
│   └── brand-guide.pdf
├── initiate-arena/
├── empyrean-studio/
└── munoz-conglomerate/
```

### 5. Firefly Services for server-side generation (future)

When EOS needs to generate vector content from a Python service (e.g.
auto-generate Initiate Arena social cards from outreach event data),
the path is:

1. Service POSTs prompt + style reference SVG to Firefly Vector endpoint
2. Receive SVG response
3. Optionally tweak via `lxml` server-side
4. Antony imports into Illustrator for finishing if needed, or ship
   raw SVG straight to product

This is **post-$10K/month** infrastructure. Pre-revenue, all generation is
manual in the desktop app.

## Gotchas

Real failures observed and avoided:

- **Vendor rejected a print PDF** because color profile was sRGB IEC61966
  instead of US Web Coated SWOP v2. Fix: Edit → Color Settings → Prepress
  preset before exporting CMYK PDFs.
- **SVG icon set rendered fuzzy on retina** because artwork wasn't on
  pixel grid. Fix: Snap to Pixel + Align New Objects to Pixel Grid +
  redraw on integer coords.
- **Variable font axis stripped on file open** in CC 2018. Fix: pin to
  CC 2024 minimum.
- **UXP script ran in JSX engine accidentally** because file was named
  `.jsx`. Different runtime, sync vs async, completely different
  storage API. Always name UXP files `.js`.
- **Recolor Artwork edited a global swatch** when intent was to recolor
  one selection. Fix: duplicate swatch first, recolor, then apply.
- **Pantone Connect signed out silently** mid-project; existing swatches
  showed as `?` in the picker but kept their names in the file. Fix:
  fall back to documented CMYK builds in spec briefs, treat Pantone
  picker as a luxury.
- **`File → Package` missed an Adobe Font** because the font was
  activated via Adobe Fonts not installed locally. Package only collects
  installed fonts. Fix: outline before sending out, or send a "fonts
  list" alongside.
- **Action recorded with absolute paths** broke when the source folder
  moved. Fix: re-record with "Override Action 'Save In' Commands" in
  Batch dialog, or use UXP script with `fs.getFolder()`.
- **Cloud document corrupted on conflicting edit** from two devices. Fix:
  use local `.ai` for anything irreplaceable; cloud only for collaborative
  WIP.
- **Export For Screens silently overwrote** an earlier version of an
  asset that had been hand-edited post-export. Fix: dated subfolders,
  always.
- **Stroke alignment "outside" pushed export bounds beyond the artboard**,
  cropping the stroke. Fix: align inside or expand stroke before export.
- **`createOutline()` on a TextFrame deleted the source text** without
  undo across script boundaries. Fix: always duplicate the text frame
  first if you need both versions.
- **Symbol detached on save-as-legacy** to an older AI version. Fix:
  don't save as legacy unless you must, and verify symbols panel after.
- **Generative features failed silently** when offline or out of credits.
  Fix: check generative credit balance before opening file, or fall back
  to manual.
- **Missing-font warning on every open** because Adobe Fonts hadn't
  reactivated after a long offline stretch. Fix: open Creative Cloud
  app, let it sync, then open the file.
- **`coordinatePrecision` default** produced 4MB SVG for a 200-path
  illustration. Fix: set to 2 in export options.
- **Linked image went stale** because source moved on disk. Links panel
  shows yellow warning triangle. Fix: relink before save, or embed.
