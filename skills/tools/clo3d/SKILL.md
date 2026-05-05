<<<<<<< Updated upstream
---
name: clo3d
description: "Use when designing, drafting, simulating, fitting, grading, rendering, or exporting garments in CLO 3D for Lyfe Spectrum apparel — including techpack drafts, fabric briefs, fit notes, colorway proposals, render briefs, and CLO-SET handoff. GUI-only human-operator workflow."
allowed-tools: "Read, Write, Edit"
version: 1.0
source_url: "https://www.clo3d.com/docs"
last_researched: "2026-04-09"
instantiated_from: templates/tools/_template/
api_version: "N/A — GUI tool (Python plug-in API exists but runs in-app, not headless)"
sdk_version: "N/A"
speed_category: human-in-the-loop
trigger: both
effort: medium
context: fork
---

# Tool: CLO 3D

## What This Tool Does

CLO 3D is a desktop garment design and simulation application built around a
**2D pattern window joined to a 3D simulation window**. Patterns drafted on the
left immediately drape onto an avatar on the right under a real-time cloth
physics solver. Unlike polygon-first 3D tools (Blender, Marvelous Designer in
artist mode), CLO mirrors how actual apparel is constructed: pieces, seams,
notches, grainlines, darts, interfacing, topstitching, grading rules. The same
file that produced the render is the file the factory cuts from.

Core capabilities:

- **2D pattern drafting** with AAMA/ASTM DXF import/export, AI curve tools, symmetry, tracing, notches, internal lines
- **3D draping simulation** in real time as patterns are edited or sewn
- **Fabric physics** driven by stretch, bend, buckling, density, friction, thickness — calibrated via the CLO Fabric Kit emulator (~90% accurate to real cloth)
- **Avatars** — standard male/female sizes, custom dimensions, MetaHuman import, fit-suit grading, pose/motion packs
- **Materials** — PBR shaders, fabric texture maps, prints, trims, hardware
- **Rendering** — real-time PBR preview plus integrated V-Ray path tracer for hero imagery
- **Tech pack generator** — BOM editor, POM tab, spec sheets exportable to PDF
- **Export** — OBJ, FBX, glTF/GLB, USD, Alembic, ZPRJ/ZPAC/ZFAB native formats
- **CLO-SET** cloud collaboration — upload ZPRJ/ZPAC/AVT directly, comments, workflow states, asset library
- **Marvelous Designer parity** — same parent company, shared file format, but MD targets VFX/games and lacks DXF production export, tech pack generator, BOM/POM

## EOS Integration

CLO 3D is the execution surface for **Lyfe Spectrum garment design**. EOS agents
do not operate CLO directly — there is no headless API for the full workflow.
Instead, agents prepare structured inputs that Antony executes inside CLO during
focused design blocks.

Agent-to-CLO handoff pattern:

- **Techpack draft agent** — generates style number, category, season, target
  retail, BOM (fabric, trim, label, hardware), POM table, construction notes,
  colorway list. Antony imports as a starting tech pack inside CLO.
- **Fabric brief agent** — given a garment intent (e.g. "tactical luxury
  overshirt, structured drape, matte hand"), proposes fabric composition,
  weight (gsm), stretch percentage, bending stiffness target, supplier
  candidates. Antony enters values into CLO's fabric property panel or
  calibrates via Fabric Kit.
- **Fit notes agent** — given measurements + reference photos, drafts pattern
  adjustment instructions (e.g. "scoop FBP 0.6 cm, raise armhole 0.4 cm,
  straighten side seam below waist 1.2 cm").
- **Colorway agent** — proposes colorway sets with hex codes, fabric texture
  pairings, and seasonal logic.
- **Render brief agent** — drafts V-Ray scene specs: HDRI, key light angle,
  camera focal length, pose, background.

Render-to-store pipeline:

```
CLO 3D (design + V-Ray render)
   → PNG export (transparent or HDRI background)
   → Photoshop retouch (color grade, cleanup, brand watermark)
   → Lyfe Spectrum store imagery / IG content
   → CLO-SET archive (ZPRJ + render + tech pack PDF)
```

CLO files (ZPRJ) are the canonical source of truth for every Lyfe Spectrum SKU.
Tech pack PDFs go to manufacturers. ZPACs (packed projects with embedded
textures and avatars) go to CLO-SET for collaborator review.

## Authentication

N/A — desktop application with local license. CLO uses subscription license
keys validated against CLO Virtual Fashion's license server on launch. No
per-request auth, no tokens, no OAuth. CLO-SET (the cloud collaboration product)
has its own web login but is a separate product from CLO 3D the desktop app.

## API / SDK

**Largely N/A for EOS purposes.** CLO ships a Python plug-in API and a C++ SDK,
but both run **inside a live CLO process** — they are not a headless automation
surface. There is no `clo3d` pip package, no CLI, no REST endpoint, no way to
boot a server-side CLO instance to batch-process garments from a Linux VPS.

What does exist:

- Python `.py` files registered as plug-ins from CLO's Plugin tab
- C++ plug-ins compiled to `.dll` (Windows) or `.dylib` (macOS)
- Each CLO version pinned to a specific API/SDK version (e.g. CLO 7.2.44 → API 4.2.0)
- Batch rendering possible **inside a running CLO** via a custom plug-in

For EOS this means: agents prepare specs, Antony runs CLO. There is no
"deploy a CLO worker to the VPS" path. If batch rendering ever becomes worth
the engineering, it would run on Antony's local Windows machine via a Python
plug-in driven by file drops, not on the VPS.

## Webhooks

N/A. No webhook surface. CLO-SET has comment notifications via email and
in-app, but no programmable webhook endpoint exposed to third parties.

## Rate Limits

N/A. Local desktop application — the only "rate limit" is GPU/CPU/RAM headroom
on the workstation. Practical ceilings:

- Simulation slows above ~50k pattern particles
- V-Ray render time scales with resolution × samples × light count
- Avatar count >2 in one scene degrades real-time preview noticeably

## Pagination

N/A. Local file system. CLO-SET web UI paginates the asset library but offers
no documented pagination API.

## SDK Idioms

N/A. No SDK in the EOS stack. The Python plug-in API is documented at
developer.clo3d.com but is not used by EOS.

## Quick Reference

### File formats at a glance

| Format | Direction | Use |
|---|---|---|
| `.zprj` | native | full CLO project (patterns, 3D, avatar, fabrics, references) |
| `.zpac` | native | packed project — embeds textures, avatars, fonts for handoff |
| `.zfab` | native | single fabric (physics + textures + properties) |
| `.dxf` (AAMA/ASTM) | in/out | production patterns to/from manufacturer CAD |
| `.obj` + `.mtl` | in/out | static mesh + material to other 3D apps |
| `.fbx` | in/out | mesh + joints + animation + camera |
| `.gltf` / `.glb` | in/out | open standard, web/AR pipelines |
| `.usd` | in/out | Pixar USD for film/VFX pipelines |
| `.abc` (Alembic) | in/out | baked animation cache |
| `.png` / `.jpg` / `.exr` | out | rendered imagery (V-Ray and real-time) |
| `.pdf` | out | tech pack export |

### The 2D <-> 3D loop

Every CLO action lives in one of two windows:

- **2D window (left)** — pattern drafting, true to flat dimensions, the surface that maps to factory cutting
- **3D window (right)** — simulation, fit, drape, render, avatar interaction

Edit a pattern piece in 2D, simulation re-solves in 3D. Sew two edges in 3D, the relationship is stored on the 2D pieces. The two views are the same data shown two ways.

### Fabric physics inputs (the values agents fill in)

- Stretch-Weft / Stretch-Warp
- Shear
- Bending-Weft / Bending-Warp
- Buckling-Ratio / Buckling-Stiffness
- Internal-Damping
- Density (gsm)
- Friction Coefficient
- Pressure
- Thickness (rendered, collision)

## Conceptual Model

**The 2D pattern is the truth. The 3D garment is a consequence.** This is the
inversion that makes CLO different from every other 3D tool. In Blender or
Marvelous Designer (artist mode), you sculpt or drape until it looks right. In
CLO, you draft the pattern the way a tailor would, sew the seams the way a
factory would, and the simulation tells you what that pattern will actually look
like on a body. If the drape is wrong, the answer is never "push the mesh
around" — the answer is always "fix the pattern."

This means CLO rewards apparel literacy. Knowing what an FBA does, what an
armscye looks like, why a princess seam moves bust ease into the side panel —
all of that pays off directly. Agents drafting tech packs for Antony to execute
in CLO must speak this vocabulary, not 3D-modeller vocabulary.

The second axiom: **fabric is a physics object, not a texture**. A texture map
makes denim look like denim. Density, bend, and stretch make denim *behave*
like denim. CLO renders look uncanny when the texture is right but the physics
are wrong — the cloth folds like a bedsheet on a body that should be wearing
14oz selvedge. Calibrate the fabric (Fabric Kit, supplier datasheet, or trusted
.zfab) before judging a fit.

## Gotchas

- **No headless mode** — no way to run CLO from a VPS, cron, or Docker. Every
  CLO action requires an interactive desktop session. Plan workflows accordingly.
- **Python plug-in API runs inside CLO** — not a substitute for SDK. You cannot
  `import clo3d` from a normal Python script.
- **DXF flavor matters** — AAMA and ASTM are different. Manufacturer asks for
  one or the other. Wrong flavor = silently broken notches and grain.
- **ZPAC vs ZPRJ** — share ZPAC externally (embeds textures), keep ZPRJ
  internally (links to local texture files). Sending a ZPRJ to a collaborator
  who doesn't have your texture library produces a grey garment.
- **Fabric Kit accuracy is ~90%** — close enough for fit and visual, not for
  performance fabrics under load. Validate with a physical sample before
  bulk-ordering.
- **Auto-grade only works on standard avatars** — custom-edited avatar
  dimensions disable auto-grade. Either use stock avatars + grading rules or
  hand-grade.
- **V-Ray render times balloon** with cloth thickness + transparent fabrics +
  area lights. Start low-sample, validate composition, then push samples.
- **MetaHuman import requires matching skeleton scale** — wrong scale collapses
  the garment through the avatar on first simulate.
- **Real-time view != V-Ray output** — what looks correct in PBR preview can
  read totally differently under path tracing. Always do a quick V-Ray test
  before committing to a colorway.
- **CLO version pinning** — opening a newer-version ZPRJ in an older CLO
  silently drops features. Pin all collaborators to the same version.
- **Simulation explodes** when two pattern pieces start co-located — separate
  layers in 3D before pressing simulate, especially after Auto-Fitting.
- **Tech pack generator is opinionated** — its layout is fine for internal use
  but most factories want their own template. Plan to export BOM/POM as data
  and rebuild the PDF in the manufacturer's preferred layout.

See references/best_practices.md for the full 19-section creator-level knowledge base.

Sources:
- [CLO 3D](https://www.clo3d.com/en/)
- [CLO Help Center](https://support.clo3d.com/)
- [CLO Developer / API](https://developer.clo3d.com/)
- [CLO-SET](https://www.clo-set.com/)
- [CLO vs Marvelous Designer](https://support.clo3d.com/hc/en-us/articles/115012666547)
- [CLO Fabric Guide](https://support.clo3d.com/hc/en-us/articles/360001436227-CLO-Fabric-Guide)
=======
---
name: clo3d
description: "Use when designing, drafting, simulating, fitting, grading, rendering, or exporting garments in CLO 3D for Lyfe Spectrum apparel — including techpack drafts, fabric briefs, fit notes, colorway proposals, render briefs, and CLO-SET handoff. GUI-only human-operator workflow."
allowed-tools: "Read, Write, Edit"
version: 1.0
source_url: "https://www.clo3d.com/docs"
last_researched: "2026-04-09"
instantiated_from: templates/tools/_template/
api_version: "N/A — GUI tool (Python plug-in API exists but runs in-app, not headless)"
sdk_version: "N/A"
speed_category: human-in-the-loop
---

# Tool: CLO 3D

## What This Tool Does

CLO 3D is a desktop garment design and simulation application built around a
**2D pattern window joined to a 3D simulation window**. Patterns drafted on the
left immediately drape onto an avatar on the right under a real-time cloth
physics solver. Unlike polygon-first 3D tools (Blender, Marvelous Designer in
artist mode), CLO mirrors how actual apparel is constructed: pieces, seams,
notches, grainlines, darts, interfacing, topstitching, grading rules. The same
file that produced the render is the file the factory cuts from.

Core capabilities:

- **2D pattern drafting** with AAMA/ASTM DXF import/export, AI curve tools, symmetry, tracing, notches, internal lines
- **3D draping simulation** in real time as patterns are edited or sewn
- **Fabric physics** driven by stretch, bend, buckling, density, friction, thickness — calibrated via the CLO Fabric Kit emulator (~90% accurate to real cloth)
- **Avatars** — standard male/female sizes, custom dimensions, MetaHuman import, fit-suit grading, pose/motion packs
- **Materials** — PBR shaders, fabric texture maps, prints, trims, hardware
- **Rendering** — real-time PBR preview plus integrated V-Ray path tracer for hero imagery
- **Tech pack generator** — BOM editor, POM tab, spec sheets exportable to PDF
- **Export** — OBJ, FBX, glTF/GLB, USD, Alembic, ZPRJ/ZPAC/ZFAB native formats
- **CLO-SET** cloud collaboration — upload ZPRJ/ZPAC/AVT directly, comments, workflow states, asset library
- **Marvelous Designer parity** — same parent company, shared file format, but MD targets VFX/games and lacks DXF production export, tech pack generator, BOM/POM

## EOS Integration

CLO 3D is the execution surface for **Lyfe Spectrum garment design**. EOS agents
do not operate CLO directly — there is no headless API for the full workflow.
Instead, agents prepare structured inputs that Antony executes inside CLO during
focused design blocks.

Agent-to-CLO handoff pattern:

- **Techpack draft agent** — generates style number, category, season, target
  retail, BOM (fabric, trim, label, hardware), POM table, construction notes,
  colorway list. Antony imports as a starting tech pack inside CLO.
- **Fabric brief agent** — given a garment intent (e.g. "tactical luxury
  overshirt, structured drape, matte hand"), proposes fabric composition,
  weight (gsm), stretch percentage, bending stiffness target, supplier
  candidates. Antony enters values into CLO's fabric property panel or
  calibrates via Fabric Kit.
- **Fit notes agent** — given measurements + reference photos, drafts pattern
  adjustment instructions (e.g. "scoop FBP 0.6 cm, raise armhole 0.4 cm,
  straighten side seam below waist 1.2 cm").
- **Colorway agent** — proposes colorway sets with hex codes, fabric texture
  pairings, and seasonal logic.
- **Render brief agent** — drafts V-Ray scene specs: HDRI, key light angle,
  camera focal length, pose, background.

Render-to-store pipeline:

```
CLO 3D (design + V-Ray render)
   → PNG export (transparent or HDRI background)
   → Photoshop retouch (color grade, cleanup, brand watermark)
   → Lyfe Spectrum store imagery / IG content
   → CLO-SET archive (ZPRJ + render + tech pack PDF)
```

CLO files (ZPRJ) are the canonical source of truth for every Lyfe Spectrum SKU.
Tech pack PDFs go to manufacturers. ZPACs (packed projects with embedded
textures and avatars) go to CLO-SET for collaborator review.

## Authentication

N/A — desktop application with local license. CLO uses subscription license
keys validated against CLO Virtual Fashion's license server on launch. No
per-request auth, no tokens, no OAuth. CLO-SET (the cloud collaboration product)
has its own web login but is a separate product from CLO 3D the desktop app.

## API / SDK

**Largely N/A for EOS purposes.** CLO ships a Python plug-in API and a C++ SDK,
but both run **inside a live CLO process** — they are not a headless automation
surface. There is no `clo3d` pip package, no CLI, no REST endpoint, no way to
boot a server-side CLO instance to batch-process garments from a Linux VPS.

What does exist:

- Python `.py` files registered as plug-ins from CLO's Plugin tab
- C++ plug-ins compiled to `.dll` (Windows) or `.dylib` (macOS)
- Each CLO version pinned to a specific API/SDK version (e.g. CLO 7.2.44 → API 4.2.0)
- Batch rendering possible **inside a running CLO** via a custom plug-in

For EOS this means: agents prepare specs, Antony runs CLO. There is no
"deploy a CLO worker to the VPS" path. If batch rendering ever becomes worth
the engineering, it would run on Antony's local Windows machine via a Python
plug-in driven by file drops, not on the VPS.

## Webhooks

N/A. No webhook surface. CLO-SET has comment notifications via email and
in-app, but no programmable webhook endpoint exposed to third parties.

## Rate Limits

N/A. Local desktop application — the only "rate limit" is GPU/CPU/RAM headroom
on the workstation. Practical ceilings:

- Simulation slows above ~50k pattern particles
- V-Ray render time scales with resolution × samples × light count
- Avatar count >2 in one scene degrades real-time preview noticeably

## Pagination

N/A. Local file system. CLO-SET web UI paginates the asset library but offers
no documented pagination API.

## SDK Idioms

N/A. No SDK in the EOS stack. The Python plug-in API is documented at
developer.clo3d.com but is not used by EOS.

## Quick Reference

### File formats at a glance

| Format | Direction | Use |
|---|---|---|
| `.zprj` | native | full CLO project (patterns, 3D, avatar, fabrics, references) |
| `.zpac` | native | packed project — embeds textures, avatars, fonts for handoff |
| `.zfab` | native | single fabric (physics + textures + properties) |
| `.dxf` (AAMA/ASTM) | in/out | production patterns to/from manufacturer CAD |
| `.obj` + `.mtl` | in/out | static mesh + material to other 3D apps |
| `.fbx` | in/out | mesh + joints + animation + camera |
| `.gltf` / `.glb` | in/out | open standard, web/AR pipelines |
| `.usd` | in/out | Pixar USD for film/VFX pipelines |
| `.abc` (Alembic) | in/out | baked animation cache |
| `.png` / `.jpg` / `.exr` | out | rendered imagery (V-Ray and real-time) |
| `.pdf` | out | tech pack export |

### The 2D <-> 3D loop

Every CLO action lives in one of two windows:

- **2D window (left)** — pattern drafting, true to flat dimensions, the surface that maps to factory cutting
- **3D window (right)** — simulation, fit, drape, render, avatar interaction

Edit a pattern piece in 2D, simulation re-solves in 3D. Sew two edges in 3D, the relationship is stored on the 2D pieces. The two views are the same data shown two ways.

### Fabric physics inputs (the values agents fill in)

- Stretch-Weft / Stretch-Warp
- Shear
- Bending-Weft / Bending-Warp
- Buckling-Ratio / Buckling-Stiffness
- Internal-Damping
- Density (gsm)
- Friction Coefficient
- Pressure
- Thickness (rendered, collision)

## Conceptual Model

**The 2D pattern is the truth. The 3D garment is a consequence.** This is the
inversion that makes CLO different from every other 3D tool. In Blender or
Marvelous Designer (artist mode), you sculpt or drape until it looks right. In
CLO, you draft the pattern the way a tailor would, sew the seams the way a
factory would, and the simulation tells you what that pattern will actually look
like on a body. If the drape is wrong, the answer is never "push the mesh
around" — the answer is always "fix the pattern."

This means CLO rewards apparel literacy. Knowing what an FBA does, what an
armscye looks like, why a princess seam moves bust ease into the side panel —
all of that pays off directly. Agents drafting tech packs for Antony to execute
in CLO must speak this vocabulary, not 3D-modeller vocabulary.

The second axiom: **fabric is a physics object, not a texture**. A texture map
makes denim look like denim. Density, bend, and stretch make denim *behave*
like denim. CLO renders look uncanny when the texture is right but the physics
are wrong — the cloth folds like a bedsheet on a body that should be wearing
14oz selvedge. Calibrate the fabric (Fabric Kit, supplier datasheet, or trusted
.zfab) before judging a fit.

## Gotchas

- **No headless mode** — no way to run CLO from a VPS, cron, or Docker. Every
  CLO action requires an interactive desktop session. Plan workflows accordingly.
- **Python plug-in API runs inside CLO** — not a substitute for SDK. You cannot
  `import clo3d` from a normal Python script.
- **DXF flavor matters** — AAMA and ASTM are different. Manufacturer asks for
  one or the other. Wrong flavor = silently broken notches and grain.
- **ZPAC vs ZPRJ** — share ZPAC externally (embeds textures), keep ZPRJ
  internally (links to local texture files). Sending a ZPRJ to a collaborator
  who doesn't have your texture library produces a grey garment.
- **Fabric Kit accuracy is ~90%** — close enough for fit and visual, not for
  performance fabrics under load. Validate with a physical sample before
  bulk-ordering.
- **Auto-grade only works on standard avatars** — custom-edited avatar
  dimensions disable auto-grade. Either use stock avatars + grading rules or
  hand-grade.
- **V-Ray render times balloon** with cloth thickness + transparent fabrics +
  area lights. Start low-sample, validate composition, then push samples.
- **MetaHuman import requires matching skeleton scale** — wrong scale collapses
  the garment through the avatar on first simulate.
- **Real-time view != V-Ray output** — what looks correct in PBR preview can
  read totally differently under path tracing. Always do a quick V-Ray test
  before committing to a colorway.
- **CLO version pinning** — opening a newer-version ZPRJ in an older CLO
  silently drops features. Pin all collaborators to the same version.
- **Simulation explodes** when two pattern pieces start co-located — separate
  layers in 3D before pressing simulate, especially after Auto-Fitting.
- **Tech pack generator is opinionated** — its layout is fine for internal use
  but most factories want their own template. Plan to export BOM/POM as data
  and rebuild the PDF in the manufacturer's preferred layout.

See references/best_practices.md for the full 19-section creator-level knowledge base.

Sources:
- [CLO 3D](https://www.clo3d.com/en/)
- [CLO Help Center](https://support.clo3d.com/)
- [CLO Developer / API](https://developer.clo3d.com/)
- [CLO-SET](https://www.clo-set.com/)
- [CLO vs Marvelous Designer](https://support.clo3d.com/hc/en-us/articles/115012666547)
- [CLO Fabric Guide](https://support.clo3d.com/hc/en-us/articles/360001436227-CLO-Fabric-Guide)
>>>>>>> Stashed changes
