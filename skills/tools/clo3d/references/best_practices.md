# CLO 3D — Creator-Level Best Practices

Source: https://www.clo3d.com/ , https://support.clo3d.com/ , https://developer.clo3d.com/
API Version: N/A — GUI tool. Python plug-in API exists (developer.clo3d.com), runs in-app only.
SDK Version: N/A for EOS. C++ SDK exists for plug-in compilation only.
Last Researched: 2026-04-06

CLO 3D is a desktop garment design and physical simulation application. It is
GUI-only for any practical EOS use. This document captures creator-level
operator knowledge for the human-in-the-loop garment design workflow that
backs Lyfe Spectrum apparel. Sections that would normally cover programmatic
authentication, REST endpoints, webhooks, rate limits, pagination, and SDK
idioms are marked N/A with a brief explanation, because CLO does not expose
those surfaces — agents prepare specs, Antony executes inside CLO.

---

# Tier 1 — Technical Mastery

## Authentication

**N/A — local desktop license.** CLO 3D authenticates via a subscription
license key (sign-in to your CLO Virtual Fashion account on first launch),
which is validated against a license server periodically. There are no API
tokens, OAuth flows, service accounts, or per-request credentials because
there are no per-request calls — CLO is a single binary running on a
workstation.

CLO-SET (the cloud collaboration platform that complements CLO 3D) has its
own web login. It is a separate product, accessed in a browser, used for
asset sharing and review. There is no documented public API for CLO-SET
authentication that EOS could call programmatically.

Operator implication: license seat management is a billing concern, not an
engineering concern. Treat the CLO subscription like a Photoshop subscription
— a tool Antony pays for and signs into once per machine.

## Core Operations with Exact Signatures

CLO does not expose "operations" in the function-signature sense. The
operator-level core operations are GUI actions performed inside the running
application. The complete daily-driver set:

**Pattern operations (2D window)**
- Import DXF (AAMA or ASTM) — `File > Import > DXF (AAMA/ASTM)`
- Trace pattern from image — `2D > Trace`
- Draw rectangle / polygon / curve — toolbar
- Add internal line / internal shape — toolbar (for darts, pockets, topstitch guides)
- Edit curvature — `Edit Curvature` tool
- Add notch — `Notch` tool (matches sewing alignment)
- Symmetric pattern (linked / unlinked) — pattern is mirrored, edits propagate
- Boolean (cut, merge) on pattern pieces

**Sewing operations (2D or 3D)**
- Segment sewing (one edge to one edge)
- Free sewing (point-to-point along irregular edges)
- M:N sewing (one edge to multiple)
- Tack-on between pieces

**Fabric and material**
- New fabric — adds entry to Object Browser
- Apply fabric to pattern — drag fabric onto piece in 2D or 3D
- Edit physical properties (Stretch-Weft, Stretch-Warp, Shear, Bending-Weft,
  Bending-Warp, Buckling-Ratio, Buckling-Stiffness, Internal-Damping, Density,
  Friction, Pressure, Thickness)
- Texture map (color, normal, metalness, roughness, displacement)
- Import .zfab — packed fabric file with textures + properties

**3D simulation**
- Simulate (toggle) — runs the cloth solver
- Pin pattern — fixes part of the pattern in space (used for arranging before drape)
- Reset 2D arrangement — flattens 3D back to 2D
- Reset 3D arrangement — restores last saved 3D layout
- Auto-Fitting — automatically drapes a garment onto a different avatar
- Strengthen / Pressure — temporary solver assistance for stuck folds

**Avatar**
- Load standard avatar (male / female / child)
- Edit measurements (height, bust, waist, hip, etc.)
- Pair avatar for grading size
- Import MetaHuman / DAZ / FBX avatar
- Apply pose / motion — from CLO pose pack or imported FBX
- Generate Fitting Suit (auto-grading helper)

**Render**
- Real-time PBR preview (left side of 3D window when enabled)
- V-Ray Render — opens V-Ray window, configures lights/camera/HDRI/samples
- Image / Video / Turntable / Thumbnail render modes
- Export PNG / JPG / EXR

**Tech pack**
- Open Tech Pack window (`Tech Pack` tab)
- Edit BOM (Bill of Materials)
- Edit POM (Points of Measure) tab
- Add cover, summary, image pages
- Export PDF

**File operations**
- Save / Open `.zprj`
- Save As `.zpac` (packed — embeds all linked assets for sharing)
- Save fabric `.zfab`
- Export OBJ / FBX / glTF / GLB / USD / Alembic
- Import same

## Pagination Patterns

**N/A.** CLO 3D operates on a local file system. There are no result sets to
paginate. The CLO-SET web app paginates the asset library and project lists in
its UI but does not expose a public REST API with pagination tokens that EOS
could consume. If batch listing of CLO-SET assets ever becomes necessary the
path would be browser automation, not an API.

## Rate Limits

**N/A.** Local desktop application. The "rate limits" that matter to operators
are workstation resource ceilings, not API quotas:

- **Simulation budget** — particle count drives solver cost. Heavy garments
  (coats, pleated skirts, structured tailoring) above ~50k particles slow the
  real-time simulation noticeably on a mid-tier workstation. Reduce particle
  density on regions that don't need fine drape (interfacing, linings).
- **V-Ray render** — render time is roughly samples × pixels × light count ×
  bounce count. A 4K hero render at 256 samples with three area lights and
  HDRI dome can take 30+ minutes on a single GPU. Plan render queues.
- **Avatar count** — more than two avatars in one scene degrades the
  real-time view. Use individual files per look for lookbook work.
- **Texture memory** — 8K PBR texture sets per fabric × 6 fabrics in one
  scene saturates 16 GB VRAM. Drop to 4K maps for working files, push to 8K
  only for hero renders.

## Error Codes and Recovery

CLO surfaces errors as modal dialogs and status bar messages, not numeric
codes. The operator-relevant failure modes:

- **"Simulation diverged"** — particles flew to infinity, usually because two
  pattern pieces started co-located or a sewing line had zero length. Recovery:
  Undo, separate pieces in 3D, re-simulate.
- **"Failed to open file"** on a `.zprj` — version mismatch (newer file, older
  CLO) or corrupted save. Recovery: open in matching CLO version, then Save As.
- **"Texture file not found"** when opening — `.zprj` references absolute
  paths. Recovery: relink in Object Browser, or always share as `.zpac`.
- **"DXF import failed"** — wrong DXF flavor (AAMA vs ASTM) or unsupported
  CAD entities. Recovery: re-export from source CAD selecting the correct
  flavor; manually clean unsupported entities.
- **V-Ray license error** — V-Ray ships with CLO but ties to the same license.
  Recovery: re-sign-in.
- **Plug-in load failure** — Python plug-in version mismatch with CLO API.
  Recovery: rebuild plug-in against the API version that matches the running
  CLO build.

There is no error code reference document because there are no programmatic
error codes — CLO is interactive software.

## SDK Idioms

**N/A for EOS.** CLO ships a Python plug-in API and a C++ SDK. Both run
**inside the CLO process** and are not invokable from a standalone Python
script, a VPS, a Docker container, or a CI pipeline. There is no
`pip install clo3d`. Scripts must be registered as plug-ins via CLO's Plugin
tab, after which they appear as menu items in the running app.

For the rare case where automation is genuinely useful (e.g. batch render the
same garment in 12 colorways), the pattern would be:

1. Author a Python plug-in on Antony's local Windows machine
2. Register it in CLO via the Plugin tab
3. Drive it by file drops into a watched folder
4. Plug-in iterates colorways, swaps materials, runs V-Ray, exports PNGs

This is local Antony work, not VPS work, and is not currently part of the EOS
build. The EOS-side idioms are file production and consumption: agents write
JSON / Markdown spec files and Antony imports them into CLO manually.

## Anti-Patterns

- **Sculpting the 3D mesh to fix fit** — there is no mesh-edit mode that
  persists. Fix the pattern.
- **Treating fabric as a texture** — applying a denim texture map to a sheet
  with default cotton physics produces a fake-looking drape no render quality
  can rescue.
- **Skipping pattern arrangement before first simulate** — pieces dropped on
  top of each other will explode the solver.
- **Editing default avatar measurements then expecting auto-grade to work** —
  it won't. Use stock + grading rules, or grade by hand.
- **Rendering before the simulation has settled** — folds will lock into
  intermediate states. Wait for the solver to come to rest first.
- **Sharing `.zprj` instead of `.zpac` externally** — collaborators get a
  grey garment because texture paths are local to your machine.
- **Mixing AAMA and ASTM DXF in the same project** — notch behavior subtly
  diverges and you won't notice until the factory cuts wrong.
- **Letting tech pack generator output be the final tech pack** — most
  factories have their own template; use CLO's BOM/POM as the data source
  and rebuild the PDF in the factory's format.
- **Ignoring particle distance** — coarser particle distance is faster but
  loses fold detail; finer is slower and can become chaotic. Tune per piece.
- **Running V-Ray at production samples for every iteration** — burns hours.
  Use real-time PBR for iteration, V-Ray only for hero shots.
- **Loading multiple Lyfe Spectrum styles into one project to "compare"** —
  CLO is happiest one garment per file. Use CLO-SET for cross-style review.
- **Hand-typing the same fabric properties into every project** — save as
  `.zfab` once, drag into every future project.

## Data Model

A CLO project (`.zprj`) is a tree of linked objects. Operator mental model:

```
Project (.zprj)
├── 2D Pattern Space
│   └── Pattern Pieces
│       ├── Outer boundary (curves + points)
│       ├── Internal lines (darts, topstitching, pocket placement)
│       ├── Internal shapes (pocket bags, applique zones)
│       ├── Notches (sewing alignment marks)
│       ├── Grainline
│       ├── Particle distance (mesh density override)
│       └── Material assignment (link to Fabric)
│
├── 3D Simulation Space
│   ├── Avatar(s)
│   │   ├── Skeleton (joints, scale)
│   │   ├── Skin mesh
│   │   ├── Measurements (linked grading sizes)
│   │   ├── Pose / Motion
│   │   └── Fitting Suit (auto-grade helper)
│   ├── Garment State (current draped position of each piece)
│   ├── Sewing Relationships (edges sewn to other edges)
│   ├── Layers (which pieces sit over which)
│   └── Pinning (fixed points in 3D space)
│
├── Object Browser
│   ├── Fabrics (each with physical properties + PBR texture set)
│   ├── Buttons / Trims / Hardware
│   ├── Graphics (printed artwork applied to surfaces)
│   ├── Topstitching (visual + optional bend reinforcement)
│   ├── Lights (V-Ray scene lighting)
│   └── Cameras (saved viewpoints)
│
├── Render Settings
│   ├── Real-time PBR config
│   └── V-Ray scene (HDRI, samples, output resolution)
│
└── Tech Pack
    ├── Cover
    ├── BOM (fabrics, trims, labels, hardware)
    ├── POM (point-of-measure table per size)
    ├── Construction notes
    └── Colorway list
```

The pattern pieces are the primary keys. Everything else hangs off them via
references — fabric assignment, sewing edges, layer order, grading rules.
Delete a piece and every relationship that referenced it goes with it.

## Webhooks and Events

**N/A.** CLO 3D does not emit webhooks. There is no event bus. The closest
thing is CLO-SET sending email notifications when collaborators leave
comments on a shared style, which is a user-facing notification, not a
programmable event sink. EOS cannot subscribe to "Antony saved a ZPRJ" or
"render finished" events without writing a custom file-watcher on Antony's
local machine.

## Limits

- **Particle count** — no documented hard cap, but performance falls off a
  cliff for most workstations above ~150k particles in one scene.
- **Pattern pieces per project** — no documented limit; practical comfort
  zone is under ~200 pieces for a single complex garment.
- **Avatar count per project** — supported but slow above 2.
- **Texture resolution per map** — accepts up to 16K but VRAM is the real cap.
- **CLO-SET file upload size** — varies by plan tier; published limits change,
  check current plan in the web UI before bulk-uploading.
- **Tech pack page count** — no hard limit, but PDFs above ~60 pages get slow
  to regenerate.
- **Undo history** — finite stack; long sessions can lose early-session undo
  capacity. Save aggressively as new files at decision points.

## Cost Model

CLO 3D pricing is **flat-rate subscription** per seat (monthly or annual),
billed by CLO Virtual Fashion. There is no per-render fee, no per-export fee,
no API call cost. The cost-relevant decisions for an operator:

- **CLO 3D vs CLO Standalone vs CLO Enterprise** — feature tiers with
  different DXF, grading, and tech pack capabilities. Lyfe Spectrum at current
  scale needs the basic CLO 3D tier.
- **Marvelous Designer** is significantly cheaper per year and shares the
  file format, but lacks DXF production export, BOM/POM, and the tech pack
  generator. For Lyfe Spectrum (production-bound apparel), CLO 3D is the
  correct tool. MD is only the right call for VFX/games/portfolio art.
- **CLO-SET** is a separate subscription for collaboration. Optional until
  there are external collaborators or factories who need cloud review.
- **V-Ray** is bundled with CLO 3D — no separate Chaos license needed.
- **Workstation hardware** is the largest non-software cost: GPU (V-Ray and
  real-time PBR), RAM (texture sets), SSD (project files).
- **Time cost** — CLO has a real learning curve. Budget weeks of operator
  practice to reach first production-quality garment, not days.

## Version Pinning

- **CLO version** — pin all collaborators to the same major.minor build.
  Newer CLO can open older files; older CLO opening newer files silently
  loses features (or refuses entirely). Track current version in the project
  README and on every CLO-SET upload.
- **CLO API version** — each CLO release pins to a specific API/SDK version
  (e.g. CLO 7.2.44 → API 4.2.0). If/when EOS produces a Python plug-in, pin
  it to one CLO build and gate the install behind a version check.
- **Avatar version** — CLO ships standard avatars that are versioned (e.g.
  `Female_V2`, `Male_V3`). Grading rules built against one avatar version
  may need re-pairing on the next version. Pin avatar version per style.
- **Fabric library version** — `.zfab` files are forward-compatible but
  re-released `.zfab` from CLO Connect can have different physics. Treat
  the `.zfab` files in the Lyfe Spectrum library as locked once production-validated.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

CLO was built by people who understood that **apparel teams already had a
workflow** — patterns, samples, fittings, grading, tech packs — and that the
3D tool's job was to mirror that workflow, not replace it with a 3D-modeller
paradigm. Every design choice in CLO follows from this. The 2D window is
first-class because patterns are the truth. Sewing is a relationship between
edges because that's how garments are constructed. Fabric has measurable
physical properties because real fabric does. Tech pack is a built-in panel
because no apparel team ships without one.

The tradeoff CLO accepts: it is a steeper learning curve than artist-first
3D tools for someone without apparel literacy. A Blender artist will be
faster in Marvelous Designer for the first six months. But CLO produces
files you can actually send to a factory, and that asymmetry only matters
if you are actually shipping garments.

The other tradeoff: CLO is GUI-only by design. The decision to keep the API
in-process is a deliberate stance that the workflow is human-led, not
automatable. CLO is not trying to be a render farm.

## Problem-Solution Map and Hidden Capabilities

| Problem | Standard answer | Hidden capability |
|---|---|---|
| Garment looks fine in PBR but wrong in V-Ray | Re-render at higher samples | Switch to V-Ray Interactive mode mid-iteration to see path-traced result live |
| Auto-Fitting drops garment through avatar | Re-arrange pieces and re-simulate | Use Strengthen + Pressure to temporarily push the garment outside the avatar mesh, then release |
| Pattern piece won't sew straight | Recheck segment endpoints | Use Free Sewing instead of Segment Sewing for irregular edges |
| Heavy fabric folds look like paper | Increase Bending values | Increase Particle Distance density only on the affected piece |
| Lighting looks flat | Add more lights | Swap HDRI dome before adding lights — environment dominates |
| Avatar pose breaks the drape | Re-pose then re-simulate | Use Pre-Simulation to settle the garment, then animate the avatar through pose |
| Fabric texture stretches weirdly across seams | Re-UV the piece | Switch fabric texture orientation between Object / Pattern / Custom |
| Need to compare two colorways | Export both as PNG | Use Colorway feature inside the same project — switch with one click |
| Slow on complex garment | Reduce particle distance globally | Reduce per-piece particle distance only where drape doesn't matter |
| Need quick presentation render | V-Ray at low samples | Use real-time PBR snapshot at hi-res — often enough for IG |

## Operational Behavior and Edge Cases

- **First simulate of a new garment is the riskiest** — pieces are usually
  not arranged yet. Always pre-arrange in 3D, then simulate.
- **Symmetric pattern editing** propagates instantly when linked, but
  unlinking mid-edit can leave inconsistent halves. Decide early.
- **Pinning** persists between simulate runs but is silently discarded by
  Reset 3D Arrangement. Re-pin after reset.
- **Undo across simulate boundaries** is sometimes lossy — long simulate
  runs can collapse undo states. Save before big simulates.
- **Auto-Fitting** to a very different avatar size frequently fails on
  collared / cuffed pieces because those are construction features, not
  drape features. Manually adjust collars and cuffs after auto-fit.
- **MetaHuman avatars** import but require scale matching. The MetaHuman
  default unit is centimeters; CLO defaults can be different per template.
- **Colorways feature** stores per-pattern-piece material assignments only —
  if you swap pattern pieces between colorways the data is lost.
- **V-Ray Interactive mode** gives near-real-time path tracing but uses
  significant GPU. Can crash on lower-VRAM cards.
- **Tech pack image regeneration** is slow on large styles — render once,
  then edit text only.
- **Save As .zpac** rebuilds all texture references on every save and is
  slow on big projects. Use it for handoff, not iteration.

## Ecosystem Position and Composition

CLO sits at the **center of a digital fashion stack**:

```
Upstream (in)              CLO 3D                 Downstream (out)
─────────────              ──────                 ────────────────
Pattern CAD          →     2D + 3D                →    Factory CAD
(Gerber, Optitex,          design                       (DXF AAMA/ASTM)
 Lectra)                   simulation
                                                  →    Manufacturing
Fabric supplier      →     fabric                      tech pack (PDF)
.zfab                      physics
                                                  →    CLO-SET
Adobe Illustrator    →     prints                      collaboration
.ai (graphics)             & graphics
                                                  →    Photoshop
HDRI libraries       →     V-Ray                       (retouch hero
.exr                       lighting                     renders)

MetaHuman / DAZ /    →     avatars            →        Unreal / Unity
Mixamo / FBX                                            (game / AR)

Marvelous Designer   ↔     ZPRJ              →         Blender / Maya
(shared format)            interop                     (VFX / film)
                                                       via OBJ/FBX/USD
```

CLO is the convergence point. Pattern data flows in from CAD; fabric data
flows in from suppliers; graphics flow in from Illustrator; renders, tech
packs, and production-ready DXF flow out. Marvelous Designer is the
sibling product (same parent company, shared file format) used by VFX/games
artists — for apparel manufacturing CLO is correct, for entertainment work
MD is correct.

In the **EOS stack** specifically: CLO sits on Antony's local Windows
workstation. EOS runs on the VPS and prepares specs that flow to CLO as
markdown / JSON / DXF / image references. CLO outputs flow back as PNG
renders (to social pipeline) and tech pack PDFs (to manufacturer email).

## Trajectory and Evolution

- **AI-assisted features** are the active investment area: AI curve drafting,
  AI fabric generation from text, AI auto-fitting improvements.
- **Real-time / interactive rendering** is closing the gap with V-Ray —
  expect the line between PBR preview and final render to blur.
- **CLO-SET integration** is becoming the default collaboration substrate;
  CLO 3D and CLO-SET are increasingly designed together.
- **MetaHuman / Unreal** integration is improving as fashion converges with
  game and virtual try-on use cases.
- **glTF and USD** are becoming the preferred interchange formats over OBJ
  and FBX as the broader 3D ecosystem standardizes on them.
- **Headless / cloud** is not on the roadmap based on current public
  signals — CLO remains a workstation-first product.

For Lyfe Spectrum: bet on CLO + CLO-SET + V-Ray as the primary stack. Bet
on USD/glTF for any future AR/web integration. Do not bet on a server-side
CLO automation surface materializing in the next 24 months.

## Conceptual Model and Solution Recipes

The two axioms (repeated here because they govern every recipe):

1. **The 2D pattern is the truth. The 3D garment is a consequence.**
2. **Fabric is a physics object, not a texture.**

### Recipe: New Lyfe Spectrum overshirt from blank project

1. Start project, save immediately as `LS_OVR_001_{date}.zprj`
2. Load standard male avatar matching Antony's measurements
3. Edit avatar to Antony's exact dimensions (but accept loss of auto-grade)
4. Import existing overshirt block as DXF (or draft in 2D)
5. Apply trusted "structured cotton twill" `.zfab` from Lyfe Spectrum library
6. Pre-arrange pieces in 3D around the avatar
7. Sew in 3D — front to back at shoulders and side seams first
8. Simulate, settle, then add collar / cuffs / placket
9. Re-simulate, evaluate fit, take fit notes
10. Iterate pattern in 2D, watch 3D update
11. When fit is locked, set up V-Ray scene with brand HDRI + key light
12. Render hero PNG at 4K
13. Save As `LS_OVR_001_{date}.zpac`, upload to CLO-SET
14. Export tech pack PDF for factory
15. Hand off PNG to Photoshop pipeline, tech pack PDF to manufacturer

### Recipe: Colorway expansion of an existing style

1. Open the locked `.zprj` for the base style
2. Use Colorway feature — add new colorway, swap fabric color/texture per piece
3. Repeat for each colorway in the brief
4. Render each colorway from the same camera with the same lights
5. Export PNG set
6. Save updated `.zprj`

### Recipe: Fit revision after physical sample

1. Receive fit notes (from agent or human fitter)
2. Open the style, take screenshots of current 3D for diff comparison
3. Edit pattern in 2D following the notes (numeric, not by eye)
4. Re-simulate
5. Compare against screenshots, iterate
6. Update tech pack POM table to reflect new measurements
7. Save new dated revision (do not overwrite — keep history)

### Recipe: Fabric library calibration

1. Acquire physical fabric swatch from supplier
2. Test with CLO Fabric Kit (cutting, weight, stretch, bend)
3. Enter measured properties into a new fabric in CLO
4. Save as `.zfab` named `LS_FABRIC_{type}_{supplier}_{date}.zfab`
5. Add to Lyfe Spectrum fabric library on workstation + CLO-SET
6. Drape on a test shell garment to sanity-check before using in production

## Industry Expert and Cutting-Edge Usage

Production fashion teams using CLO at expert level converge on a few patterns:

- **Block libraries** — every brand maintains a library of base blocks
  (men's shirt, women's blouse, trousers, jacket) that all new styles start
  from. New designs are modifications of blocks, not from-scratch drafts.
  Lyfe Spectrum should build this library from day one.
- **Fabric libraries** — every fabric the brand has ever validated lives as
  a `.zfab` in a shared library. New styles pull from the library; new
  fabrics are added only after physical calibration.
- **Avatar fit panel** — a small set of avatars sized to the brand's fit
  model (or fit models). Every style is fit-checked against each.
- **Style number convention** — every project file is named with a stable
  style number from day one. Versions are dated suffixes, never overwrites.
- **Daily fit sessions** — design teams run morning fit reviews on the
  current sample set in CLO before touching real fabric. CLO replaces the
  first 2-3 physical sample rounds entirely.
- **Tech pack as data, PDF as format** — the BOM and POM live as
  spreadsheets and CLO data; the PDF is regenerated per delivery. Never
  hand-edit the PDF.
- **CLO-SET as single source of truth** — no email attachments of ZPRJ
  files. Everything goes through CLO-SET so the version history is preserved.
- **Render brief discipline** — every hero render starts from a written brief
  (HDRI, lights, camera, pose, background). Random good renders don't scale.
- **Fit-then-finish** — block out fit completely before adding topstitching,
  trims, or hardware. Visual finish on a bad fit is wasted effort.
- **Avoid the temptation to art-direct in 3D** — if a fold isn't landing,
  the fabric is wrong or the pattern is wrong. Don't push the mesh.
- **Cross-tool render escape** — for hero campaign imagery, expert teams
  export the final draped garment as USD/Alembic into Maya/Blender/Houdini
  for an unrestricted lighting and camera pass. Keep CLO for design,
  promote to dedicated 3D for hero.

For Lyfe Spectrum specifically: the tactical-luxury aesthetic depends on
**fabric weight and structure reading correctly**. This is the area where
amateur CLO output gives itself away. Calibrate fabrics ruthlessly. Use
heavier `bending` and `density` than feels right at first — most digital
garments default to too-light fabric. The brand's matte / structured /
expensive feel is 60% fabric physics, 30% lighting, 10% retouch.

---

## EOS Usage Patterns

EOS-side automation around CLO is **all upstream** — agents prepare specs,
Antony executes inside CLO. The current usage patterns:

- **Techpack draft agent** writes a markdown tech pack draft into
  `01_Companies/lyfe_spectrum/styles/{style_number}/techpack_draft_{date}.md`
  with BOM, POM, construction notes, and colorway proposals. Antony copies
  values into CLO's Tech Pack panel during a design block.
- **Fabric brief agent** writes a fabric spec sheet that Antony enters into
  CLO's fabric property panel or hands to a supplier sourcing call.
- **Fit notes agent** ingests reference photos (Antony in current sample) and
  produces numeric pattern adjustment notes (e.g. "shorten back length 1.0 cm").
- **Render brief agent** writes a V-Ray scene brief (HDRI choice, light
  positions, camera, pose) before render time so render sessions are
  decisive, not exploratory.
- **CLO-SET archive notes** — agents log every uploaded ZPRJ/ZPAC to the
  Lyfe Spectrum company memory in Neon, with style number, version, date,
  and CLO-SET URL.
- **Render-to-store handoff** — when a final render PNG lands in
  `01_Companies/lyfe_spectrum/renders/`, an EOS watcher (future) routes it
  through Photoshop retouch and into the Lyfe Spectrum store imagery pipeline.

What EOS does not do (and should not attempt):
- Run CLO headlessly
- Edit ZPRJ files directly
- Auto-grade patterns
- Run V-Ray on the VPS
- Generate tech pack PDFs without CLO

## Gotchas

- **No headless mode** — CLO requires an interactive desktop session. Plan
  EOS workflows around Antony's design blocks, not around cron.
- **Python plug-in API runs in-process only** — no `pip install clo3d`, no
  CLI, no subprocess. The API exists but is not a substitute for an SDK.
- **DXF flavor (AAMA vs ASTM)** — using the wrong one silently breaks
  notches and grain. Confirm with the manufacturer before exporting.
- **`.zprj` vs `.zpac`** — `.zprj` references textures by local path;
  `.zpac` embeds them. Always share `.zpac` externally.
- **Auto-grade does not work on edited custom avatars** — only on stock
  avatars. Either accept the constraint or grade by hand.
- **Fabric Kit accuracy is ~90%** — calibrated fabrics are good for fit and
  visual judgment but not load-bearing for performance fabrics. Validate
  with a physical sample before bulk production.
- **Simulation explodes on co-located pieces** — always pre-arrange in 3D
  before pressing simulate, especially after Auto-Fitting.
- **MetaHuman scale mismatch** — collapses garment through avatar on first
  simulate. Match units before importing.
- **CLO version drift between collaborators** — newer ZPRJ in older CLO
  silently drops features. Pin all collaborators to the same major.minor.
- **V-Ray render time scales nonlinearly** with transparent fabrics, area
  lights, and high samples. Iterate in real-time PBR, render hero in V-Ray.
- **Real-time PBR vs V-Ray differ visibly** — always V-Ray test before
  committing to a colorway.
- **Tech pack generator output is opinionated** — most factories want their
  own template. Use CLO BOM/POM as the data source, rebuild PDF in
  factory format.
- **Undo can be lossy across simulate boundaries** — save dated revisions
  at decision points instead of relying on undo.
- **Texture link breakage when moving project folders** — relative paths
  are not always reliable. Keep texture libraries in stable absolute
  locations, or always work in `.zpac`.
- **Multiple avatars in one scene** — supported but slow. Use one avatar
  per file for production work; compose lookbooks downstream.
- **Pattern pieces above ~200** — CLO becomes sluggish. Split complex
  garments (e.g. multi-piece outerwear linings) into sub-files where
  possible.
- **Colorway feature loses data** if you swap pattern pieces between
  colorways. Lock pattern before adding colorways.
- **Symmetric pattern editing** is fast but unlinking mid-edit produces
  inconsistent halves. Decide symmetry early, commit to it.
- **CLO-SET upload limits** vary by plan tier and change over time. Check
  before bulk uploads.
- **License validation requires periodic internet** — CLO will eventually
  refuse to launch if it cannot reach the license server for too long.
  Not an issue on a normal workstation, but worth knowing for travel.

---

## Extended Operator Notes

### The 2D drafting discipline

CLO rewards a tailor's discipline in the 2D window. The operators who get the
most out of CLO treat 2D drafting as a measured, deliberate act:

- **Always work to numbers, not to the eye.** Type measurements into the
  Properties panel rather than dragging points until they "look right." A
  bust width of 47.6 cm is reproducible; a bust width of "looks like 48ish"
  is not.
- **Use internal lines for everything that needs to communicate to the
  factory** — dart legs, pocket placements, topstitching guides, label
  positions. Internal lines export to DXF and become the construction map.
- **Notch every alignment point.** A pattern with no notches is a pattern
  that can be sewn six different ways. Notches are not decoration.
- **Grainline matters even in 3D.** CLO uses grainline to orient fabric
  texture stretch. Wrong grainline = stretch in the wrong direction =
  drape behavior that doesn't match the real garment.
- **Symmetric pattern is the default for symmetric garments.** Edit one
  half, propagate. Unlink only when you genuinely need asymmetry.
- **Particle distance is per-piece, not global.** Use coarser particle
  distance on linings, interfacing, and unseen pieces. Use finer only where
  drape detail matters (collars, drapey skirt panels, gathers).

### The 3D simulation discipline

- **Pre-arrange before pressing simulate.** Drop the front piece in front of
  the avatar, the back behind, sleeves to the sides. Simulating from a pile
  of co-located pieces is the #1 source of "the simulation exploded" bug
  reports.
- **Sew before you simulate.** A garment with no sewing falls off the
  avatar. Sew the major seams first (shoulders, side seams), simulate, then
  add detail seams (collar, cuffs, plackets).
- **Use Pin to hold pieces in space** while you sew the next set. Pinning is
  not cheating — it's the digital equivalent of pinning fabric to a dress
  form before stitching.
- **Settle the simulation** — let it run until the garment stops moving
  before judging fit. A simulation caught mid-drape gives misleading fit
  signals.
- **Layers matter.** If a shirt should sit under a jacket, set the layer
  order explicitly before simulating. CLO does not infer layer order from
  pattern arrangement.
- **Reset 3D Arrangement** is the nuclear option. It restores the last
  saved layout but discards pinning. Save before using.

### Fabric calibration discipline

- **Trust supplier datasheets only as a starting point.** Real fabric
  varies. Calibrate with the Fabric Kit when accuracy matters.
- **Density (gsm) is the most under-tuned property.** Most operators
  default to 200 gsm and ship. A 14oz selvedge denim is closer to 460 gsm.
  Wrong density = wrong drape weight = wrong silhouette.
- **Bending values do most of the visual work.** Two fabrics with identical
  density but different bending look like completely different materials.
  A high-bending wool reads as structured outerwear; a low-bending rayon
  reads as fluid drape.
- **Stretch must match real-world stretch percentage.** A non-stretch
  fabric with 5% stretch in CLO will fit through dimensions a real
  non-stretch fabric won't.
- **Friction matters for layered garments.** A satin lining slips against
  an outer wool the way a high-friction cotton doesn't. Wrong friction =
  the lining behaves like the outer.
- **Save calibrated fabrics as `.zfab` immediately** and add to the brand
  library. Never re-calibrate the same fabric twice.

### Render discipline

- **Lighting is brand language.** Lyfe Spectrum's tactical-luxury aesthetic
  has a specific lighting recipe — directional key, low-fill, controlled
  shadow, neutral or cool HDRI. Document the recipe and reuse it across
  every style render so the lookbook reads as a coherent collection.
- **Camera focal length matters.** A 35mm shot reads editorial; an 85mm
  reads catalog; a 24mm reads distorted. Pick a focal length per use case
  and stick to it.
- **HDRI dominates everything.** Picking the right HDRI does more for image
  quality than adding lights. Build a small HDRI library of brand-approved
  environments.
- **Render at 2x intended display resolution.** Down-sampling cleans up
  noise and aliasing. A 4K render down-sampled to 2K reads cleaner than a
  native 2K render at the same sample count.
- **Sample count vs noise** — start at 64, evaluate, push to 128 or 256
  only if noise is visible at the intended display size.
- **Real-time PBR for IG content** — Instagram is forgiving. Real-time PBR
  snapshots are often enough for social. Save V-Ray for hero/lookbook/
  e-commerce.
- **Always render a turntable** for hero garments. A 360 turntable for
  e-commerce shows the garment more honestly than a static front-view.

### Tech pack discipline

- **BOM and POM are the data; the PDF is just the format.** Treat BOM and
  POM as structured records (CLO panel, spreadsheet, or Notion table). The
  PDF is regenerated per delivery, never hand-edited.
- **Style number first, file name second.** Every file in a style folder
  starts with the style number. Search and version control depend on it.
- **Construction notes belong in the tech pack, not in your head.** Stitch
  type, seam allowance, label placement, hangtag attachment — all of it
  goes in writing, every time.
- **Colorway list is part of the tech pack** and changes over time. Date
  the colorway revisions.
- **Approved sample sign-off** lives at the end of the tech pack. The
  factory should never have to ask which version is the approved one.

### CLO-SET discipline

- **Upload `.zpac`, not `.zprj`.** External collaborators do not have your
  texture libraries.
- **Workflow state per style** — set the CLO-SET workflow state on every
  upload (concept, fit-1, fit-2, approved, in-production, shipped). The
  state is the project status, not a label.
- **Comments are the source of truth** for collaborator feedback. Do not
  accept feedback through email or DM. If it isn't in CLO-SET, it didn't
  happen.
- **Asset library** — fabrics, trims, hardware, prints all live in the
  brand's CLO-SET asset library. Pull from the library on every new style.

### Working session shape

A productive Lyfe Spectrum CLO design session looks like:

1. **Open** — pull style number, load EOS-prepared spec brief, open the
   appropriate `.zprj`.
2. **Recap** — read the previous session's notes, look at the current 3D
   state, identify what changed since last open.
3. **Plan** — write down the 3-5 specific changes this session will make.
   No exploration without a plan.
4. **Execute** — make the changes in 2D and 3D. Follow the discipline
   sections above.
5. **Render** — quick real-time PBR render of the current state.
6. **Save** — dated revision, never overwrite.
7. **Log** — write a session note (what changed, why, what's next) into
   the style folder so the next agent run has context.
8. **Upload** — push the new `.zpac` to CLO-SET if collaborators need to see it.

This shape — open / recap / plan / execute / render / save / log / upload —
is the operator equivalent of the EOS cognitive loop. It is what makes
CLO sessions compound instead of restart.

---

## Sources

- https://www.clo3d.com/en/
- https://www.clo3d.com/en/clo/features
- https://support.clo3d.com/
- https://support.clo3d.com/hc/en-us/articles/115000470688-CLO-File-Formats
- https://support.clo3d.com/hc/en-us/articles/115012536047
- https://support.clo3d.com/hc/en-us/articles/115012666547
- https://support.clo3d.com/hc/en-us/articles/360001436227-CLO-Fabric-Guide
- https://support.clo3d.com/hc/en-us/articles/360041074334-Fabric-Kit-Manual
- https://support.clo3d.com/hc/en-us/articles/115014784747-Run-V-Ray-Render
- https://support.clo3d.com/hc/en-us/articles/360055935233-Pair-Avatar-for-Grading-Size
- https://support.clo3d.com/hc/en-us/articles/360034333053-Auto-Fitting
- https://developer.clo3d.com/
- https://developer.clo3d.com/python.html
- https://www.clo-set.com/
- https://style.clo-set.com/aboutus
- https://style.clo-set.com/service/features
