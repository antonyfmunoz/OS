---
name: illustrator
description: "Use when designing or specifying vector artwork — Lyfe Spectrum logos and garment graphics, Initiate Arena brand assets, Empyrean Studio client deliverables — drafting color palettes, typography specs, layout briefs, exporting SVG/PDF/AI for print or web, or writing UXP scripts to automate repetitive Illustrator tasks (batch export, swatch sync, type replace, artboard generation)."
allowed-tools: "Read, Write, Edit, Bash, WebFetch"
version: 1.0
source_url: "https://developer.adobe.com/illustrator/uxp/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Illustrator 28.x (CC 2025), UXP scripting v6"
sdk_version: "Illustrator UXP Scripting (replacing ExtendScript JSX) — UXP 8.x"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: illustrator

## What This Tool Does

Adobe Illustrator is the industry-standard vector graphics editor: a Bezier
curve modeler with a typesetting engine, color management, swatch/symbol/brush
libraries, multi-artboard layout, and PDF/SVG/EPS/AI I/O. Unlike Photoshop
(raster) it stores resolution-independent paths, which is the only correct
representation for logos, garment graphics, badges, icons, type lockups, and
anything that will be printed at multiple sizes or screened onto a fabric.

Core capabilities relevant to EOS work:

- **Vector path tools** — Pen, Curvature, Pencil, Shape Builder, Pathfinder
- **Type engine** — point/area/path type, OpenType features, variable fonts,
  character/paragraph styles, glyph substitution
- **Color systems** — global swatches, spot colors (Pantone), gradients,
  color groups, recolor artwork, CMYK/RGB/Lab profiles
- **Reusable assets** — symbols, brushes (art/scatter/pattern/bristle),
  graphic styles, character/paragraph styles
- **Multi-artboard layout** — up to 1000 artboards per document, each its own
  export target
- **Export pipeline** — Export For Screens (PNG/SVG/PDF/JPG at multiple
  scales), Save As (AI/PDF/EPS), Asset Export panel
- **Automation** — Actions panel (record/replay), UXP scripting (JS-based,
  replacing ExtendScript), and a still-supported legacy ExtendScript surface

## EOS Integration

Illustrator is **GUI-primary, hybrid-skill**. Antony does the actual design
work in the desktop app. Agents:

1. **Draft specs** before he opens the file — color palettes (hex + Pantone
   nearest match), type lockup instructions (font, tracking, weight, vertical
   metrics), layout grids (artboard sizes, bleed, safe area), export targets
   (file names, formats, scales).
2. **Reference scripts** he can run via File > Scripts > Other Script — UXP
   JS files that batch-export artboards, replace swatches site-wide, bulk
   rename layers, generate per-color colorways from a master file.
3. **Verify deliverables** post-export — agents check file naming, SVG
   minification, PDF/X-1a compliance, color profile, dimensions.

Concrete EOS use cases:

- **Lyfe Spectrum** — garment graphic separations (one Pantone per layer for
  screen print), tech pack mockups, hangtag artwork, woven label PDFs
- **Initiate Arena** — badge/seal generation, certificate templates, social
  card masters, deck illustration assets
- **Empyrean Studio** — client logo systems, brand sheet PDFs, web SVG
  exports, App Store icon source files

Canonical EOS pattern:
- Master file lives in `/opt/OS/brand_assets/<brand>/source/*.ai`
- Artboards named after deliverable (`logo-primary`, `logo-mono-white`, ...)
- Global swatches only — no local CMYK fills, ever
- Export script writes to `brand_assets/<brand>/exports/YYYY-MM-DD/`
- Agents reference this directory tree from generated content briefs

## Authentication

Local desktop application. **Adobe ID** required for activation, license
check, Creative Cloud sync, Adobe Fonts (formerly Typekit), and CC Libraries.
After install + sign-in, Illustrator runs offline; license re-validates every
~30 days. No API key, no OAuth token surface for the desktop scripting layer
itself — UXP scripts run inside the host app process with the user's
permissions.

For Adobe **Firefly Services** and Photoshop API there is a real OAuth2
server-to-server flow (client credentials grant). Illustrator-specific cloud
API is far more limited than Photoshop's — as of 2026-04 there is no general
"Illustrator API" endpoint comparable to the Photoshop API; vector generation
in Firefly Services is restricted to the Generate Vector / Generate Pattern
endpoints. Treat Illustrator as a desktop tool, not a cloud service.

## Quick Reference

### Run a UXP script from the GUI

```
File → Scripts → Other Script... → select foo.js
```

Or place `foo.js` in `~/Library/Application Support/Adobe/Adobe Illustrator 28/en_US/Scripts/`
(macOS) / `%APPDATA%\Adobe\Adobe Illustrator 28\en_US\Scripts\` (Windows) and
restart — it appears under `File → Scripts → foo`.

### Minimal UXP script — log every artboard

```javascript
// File: list_artboards.js  (UXP)
const ill = require("illustrator");
const doc = ill.app.activeDocument;
for (let i = 0; i < doc.artboards.length; i++) {
  const ab = doc.artboards[i];
  console.log(`${i}\t${ab.name}\t${ab.artboardRect.join(",")}`);
}
```

### Batch export every artboard as SVG

```javascript
const ill = require("illustrator");
const fs  = require("uxp").storage.localFileSystem;
const doc = ill.app.activeDocument;

(async () => {
  const folder = await fs.getFolder();
  for (let i = 0; i < doc.artboards.length; i++) {
    doc.artboards.setActiveArtboardIndex(i);
    const file = await folder.createFile(`${doc.artboards[i].name}.svg`,
                                         { overwrite: true });
    await doc.saveAs(file, new ill.ExportOptionsSVG());
  }
})();
```

### Action panel — recordable equivalent

For one-off batches use **Window → Actions** to record a sequence then
**File → Automate → Batch...** to apply across a folder. Faster than
scripting when the operation is recordable.

### Headless / command-line

Illustrator does NOT have a true headless mode. The closest:
- macOS: `osascript -e 'tell application "Adobe Illustrator" to do javascript file "/path/script.js"'`
- Windows: `"C:\Program Files\Adobe\Adobe Illustrator 28\Support Files\Contents\Windows\Illustrator.exe" -run "C:\path\script.jsx"`

Both still spawn the full GUI app. Server rendering should use Firefly
Services (vector) or `rsvg-convert`/Inkscape CLI for SVG → PNG.

### Color, type, swatch quick recipes

```javascript
// Create a global Pantone swatch
const sp = doc.spots.add();
sp.name = "PMS 185 C";
sp.color = new ill.CMYKColor();  // populated from Pantone book
sp.colorType = ill.ColorModel.SPOT;

// Set type tracking
const tf = doc.textFrames[0];
tf.textRange.characterAttributes.tracking = 50;  // 1/1000 em

// Apply a paragraph style
const ps = doc.paragraphStyles.getByName("Headline");
tf.paragraphs[0].applyParagraphStyle(ps, true);
```

## Conceptual Model

**Illustrator is a vector document model + a renderer + a UI shell.** A
document is a tree: `Document → Layers → PageItems (paths, groups, text
frames, placed images, symbol instances)`. Every PageItem has appearance
attributes (fill, stroke, effects), transform, and parent-layer membership.
Artboards are independent rectangles in document coordinate space — they are
not containers, just export crops.

The **scripting model** mirrors the document model 1:1. UXP `require("illustrator")`
gives you `app.activeDocument`, then `.layers`, `.pathItems`, `.textFrames`,
`.symbols`, `.swatches`, `.artboards`. Asynchronous calls return Promises.
The legacy ExtendScript surface (`#target illustrator`) used the same object
graph synchronously — UXP scripts can almost always be ported by adding
`async`/`await` and swapping `File`/`Folder` for the UXP `storage` API.

If you internalize **document = tree, artboards = export crops, swatches =
single source of truth for color**, the rest follows. The #1 conceptual
mistake is treating artboards as containers (they aren't — items don't belong
to artboards, they sit at coordinates that may overlap them).

## Gotchas

- **UXP is replacing ExtendScript but not at parity yet.** Some legacy JSX
  scripts (Variables panel, Data-Driven Graphics, older Action playback) must
  still run as `.jsx` via the old engine. Check Adobe's UXP Illustrator API
  status page before porting.
- **`File → Scripts` runs UXP and JSX side-by-side** — `.js` is treated as
  UXP, `.jsx` as ExtendScript. Easy to confuse. Name files explicitly.
- **No real headless mode.** "Server-side Illustrator" is a Firefly Services
  conversation, not a desktop scripting one.
- **Global swatches vs local color.** A path filled with a local CMYK
  rectangle does NOT update when you edit a swatch. Always create swatches
  as **Global** (or Spot) before applying.
- **Artboards aren't containers.** Items overlapping an artboard aren't
  "in" it. Export-by-artboard clips at the artboard rect; bleed beyond it is
  preserved in PDF export but cropped in PNG/SVG.
- **SVG export defaults.** "Presentation Attributes" vs "Inline Style" vs
  "Internal CSS" produces wildly different files. For web SVG sprites, use
  Presentation Attributes + Minify + Responsive off + Decimal 2.
- **Pantone Connect sign-in required** for Pantone libraries since 2022.
  Existing files keep their Pantone names but the swatch picker is gated
  behind a separate subscription.
- **Adobe Fonts activation is per-machine.** A `.ai` file referencing an
  Adobe Font opens with missing-font warnings on a machine where that font
  isn't activated. Outline type or package fonts before sending out.
- **Variable fonts need OpenType-Variable enabled** in Type preferences;
  axis controls live in the Character panel flyout.
- **Save As .ai with PDF Compatible File ON** doubles file size but is
  required for downstream tools that open AI as PDF (InDesign place, Acrobat
  preview, Figma import). Default: leave ON.
- **`Export For Screens` overwrites silently** — no "skip existing" option.
  Script around it if you need incremental exports.
- **PDF/X-1a vs PDF/X-4** — print houses asking for PDF/X-1a want CMYK
  flattened, no transparency, no live type. PDF/X-4 keeps transparency live.
  Confirm with the printer before exporting.
- **Recolor Artwork on Global/Spot swatches** edits the swatch definition
  globally, not just the selection. Surprising the first time.
- **`.ai` is a PDF wrapper** — technically openable in any PDF reader, but
  you lose layer/swatch/symbol fidelity. Always round-trip through Illustrator.
- **UXP scripts cannot block the UI** — every long operation must `await`.
  Synchronous JSX patterns deadlock the host when ported naively.
- **Firefly Services vector generation has separate quota and pricing**
  from Photoshop API. Don't assume "I have Firefly credits" means vector.

See references/best_practices.md for the full 19-section creator-level knowledge base.
