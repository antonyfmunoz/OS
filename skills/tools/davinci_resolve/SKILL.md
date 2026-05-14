---
name: davinci_resolve
description: "Use when editing video in DaVinci Resolve Studio, color grading with nodes, compositing in Fusion, mixing in Fairlight, configuring delivery/render queues, OR scripting Resolve from Python/Lua to automate project setup, timeline assembly, media pool ingest, color preset application, marker extraction, or render dispatch."
allowed-tools: "Read, Bash, Write, Edit"
version: 1.0
source_url: "https://www.blackmagicdesign.com/products/davinciresolve"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "DaVinci Resolve 19.1 Studio"
sdk_version: "Resolve Scripting API (Python 3.6+ / Lua 5.1) — DaVinciResolveScript"
speed_category: stable
trigger: both
effort: low
context: fork
---

# Tool: DaVinci Resolve Studio

## What This Tool Does

DaVinci Resolve Studio is Blackmagic Design's all-in-one post-production
application: nonlinear editor, node-based color grader, node-based compositor
(Fusion), DAW-style audio mixer (Fairlight), and delivery/render front end —
plus a fully scriptable project model exposed through the Resolve Scripting API
in Python and Lua. It is the only mainstream NLE that ships with a real
automation surface agents can drive.

Core capabilities:

- **Cut and Edit pages** — pro NLE with multicam, source overwrite, sync bin
- **Color page** — node-graph color grading with primary wheels, curves,
  qualifiers, tracker, ResolveFX, and DaVinci Neural Engine ML tools
- **Fusion page** — node-based compositor for VFX, motion graphics, paint,
  3D, particles (the artist-facing replacement for After Effects timelines)
- **Fairlight page** — multitrack audio mixer with bussing, ADR, Fairlight FX,
  Dolby Atmos rendering, voice isolation
- **Deliver page** — render queue with H.264/H.265/ProRes/DNxHR/DCP/IMF presets
- **Resolve Scripting API** — Python (3.6+) and Lua bindings exposing
  ProjectManager, Project, MediaStorage, MediaPool, Timeline, TimelineItem,
  Gallery, Fusion, plus a callable render queue. Real agent-callable surface.
- **DaVinci Neural Engine** — on-device ML for magic mask, smart reframe,
  voice isolation, scene cut detection, audio classification, transcription
- **Collaboration** — multi-user project server (Postgres) with bin and clip
  locking, change lists, and remote grading
- **Proxy generation** — automatic ProRes/H.264 proxies, online/offline workflow

## EOS Integration

Resolve is a **hybrid skill**: most work happens in the GUI (creative judgment
matters), but the scripting API turns the boring parts into automatable plumbing
the Developer Agent can run on its own.

### GUI use (Antony in the seat)

- **Personal brand content** — short-form vertical for IG/TikTok/YouTube Shorts
  cut on the Cut page; color graded with a Lyfe Spectrum LUT on Color; captions
  via Fairlight transcribe; delivery via vertical 1080x1920 H.264 preset
- **Initiate Arena VSLs** — long-form sales videos cut on Edit; tactical-luxury
  color treatment on Color; voice isolation + de-ess on Fairlight; broadcast-safe
  delivery for paid ads
- **Empyrean Studio client deliverables** — full pipeline ingest → conform →
  grade → finish → multi-format delivery for client work; Fusion for lower-thirds
  and motion graphics templates

### Scripted use (agent-callable, no GUI seat)

- **Project bootstrapping** — create new project from a brand template, set
  timeline resolution / framerate / color science from a JSON spec
- **Media ingest** — walk a directory, add clips to media pool with bin
  organization derived from filename or sidecar JSON
- **Timeline assembly** — append clips in order, place markers from a transcript
  JSON, drop in a brand intro and outro
- **Color preset application** — apply a saved gallery still or PowerGrade
  (.drx) to every clip in a track (Lyfe Spectrum house look)
- **Render dispatch** — queue a project across multiple presets (vertical IG,
  square LinkedIn, horizontal YouTube) and trigger `StartRendering()` headless
- **Reporting** — extract markers, durations, and clip metadata back to Neon
  for content tracking

Canonical EOS pattern:

- Resolve Studio runs as a launched app; render workers can run headless on
  Linux under `xvfb-run` for true unattended dispatch
- Python script connects via the official `DaVinciResolveScript` module exposed
  through `RESOLVE_SCRIPT_API` / `RESOLVE_SCRIPT_LIB` env vars
- Project specs live as JSON in `/opt/OS/eos_ai/templates/resolve_projects/`
- House LUTs and PowerGrades versioned in `/opt/OS/assets/resolve/`
- Render queue results piped back through `model_router` for Neon logging

## Authentication

None for the local app surface. The Scripting API connects in-process (Lua
running inside Resolve's console) or out-of-process (Python script using the
Blackmagic `fusionscript` dynamic library) — auth is filesystem permission to
the running Resolve user. There is no token, no API key for scripting.

For Studio collaboration, the Postgres-backed project server uses standard
Postgres credentials (host, port, db, user, password) configured per project
in the Project Server panel. Blackmagic Cloud sync uses a Blackmagic ID account.

For activation: DaVinci Resolve Studio requires either a USB dongle license or
an activation key tied to a Blackmagic ID. The free version exists but does
not expose all scripting features (Fusion scripting and some render preset and
Neural Engine APIs are Studio-only) and many delivery codecs are gated.

## Quick Reference

### Bootstrap the Python scripting environment

```bash
# Linux paths (Resolve installed at /opt/resolve)
export RESOLVE_SCRIPT_API="/opt/resolve/Developer/Scripting"
export RESOLVE_SCRIPT_LIB="/opt/resolve/libs/Fusion/fusionscript.so"
export PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"
python3 -c "import DaVinciResolveScript as dvr; print(dvr.scriptapp('Resolve'))"
```

macOS paths:
```
RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
```

### Connect and walk the object tree

```python
import DaVinciResolveScript as dvr_script
resolve  = dvr_script.scriptapp("Resolve")
pm       = resolve.GetProjectManager()
project  = pm.GetCurrentProject()           # or pm.LoadProject("MyProject")
mp       = project.GetMediaPool()
root     = mp.GetRootFolder()
timeline = project.GetCurrentTimeline()
print(project.GetName(), timeline.GetName(), timeline.GetTrackCount("video"))
```

### Create project, set format

```python
pm.CreateProject("Initiate_Arena_VSL_2026_04_06")
project = pm.GetCurrentProject()
project.SetSetting("timelineResolutionWidth",  "1920")
project.SetSetting("timelineResolutionHeight", "1080")
project.SetSetting("timelineFrameRate",        "23.976")
project.SetSetting("colorScienceMode",         "davinciYRGBColorManagedv2")
```

### Ingest a folder of clips

```python
ms = resolve.GetMediaStorage()
ms.AddItemListToMediaPool("/mnt/footage/2026-04-06_shoot")
```

### Build a timeline programmatically

```python
folder   = mp.GetCurrentFolder()
items    = folder.GetClipList()
timeline = mp.CreateEmptyTimeline("auto_assembly")
mp.AppendToTimeline(items)
```

### Apply a PowerGrade (.drx) to every clip in V1

```python
gallery = project.GetGallery()
album   = gallery.GetCurrentStillAlbum()
for tlitem in timeline.GetItemListInTrack("video", 1):
    album.ApplyGradeFromDRX(
        "/opt/OS/assets/resolve/lyfe_spectrum.drx", 0, [tlitem]
    )
```

### Add a render preset and dispatch

```python
import time
project.LoadRenderPreset("YouTube 1080p")
project.SetRenderSettings({
    "TargetDir":  "/mnt/renders",
    "CustomName": "vsl_v3",
})
job_id = project.AddRenderJob()
project.StartRendering([job_id], isInteractiveMode=False)
while project.IsRenderingInProgress():
    time.sleep(2)
status = project.GetRenderJobStatus(job_id)
```

### Markers from a transcript JSON

```python
import json
for cue in json.load(open("/tmp/transcript.json")):
    timeline.AddMarker(
        cue["frame"], "Blue", cue["label"], cue["text"], 1
    )
```

## Conceptual Model

**Resolve is a single in-memory project graph wrapped by five page UIs and one
script API.** The graph is `ProjectManager → Project → (MediaPool, Timelines,
Gallery, Fusion comps, Fairlight mix) → TimelineItems → Clips → Takes`.
Every page (Cut, Edit, Color, Fusion, Fairlight, Deliver) is a different lens
on the same graph. The script API is a sixth lens — one that an agent can hold.

If you internalize graph-as-truth, the page model becomes obvious: Color "sees"
TimelineItems as nodes with grades; Fusion "sees" them as composition inputs;
Fairlight "sees" their audio essence. Edits in any page mutate the shared graph.

Three rules every Resolve scripter learns the hard way:
- The script API only sees the **currently open project** — there is no offline
  project mutation; you must `LoadProject` first.
- Render jobs are **persisted in the project file**, so adding a job from a
  script and saving the project means the job is there next launch.
- Many setters return `True`/`False` instead of raising — ALWAYS check.

## Gotchas

- **Free vs Studio API surface** — Fusion scripting, some ResolveFX, Neural
  Engine features, and stereoscopic settings are Studio-only. Calls silently
  return `None` on free.
- **`scriptapp("Resolve")` returns `None`** if Resolve is not running OR if
  `RESOLVE_SCRIPT_LIB` points to the wrong arch (Intel vs ARM dylib on macOS,
  missing `.so` on Linux). Verify env vars before debugging script logic.
- **Project must be open** — `pm.GetCurrentProject()` returns the *currently
  loaded* project. There is no headless "open project file, mutate, close" mode.
  Always `pm.LoadProject(name)` first; if it returns `None` the name is wrong
  or another user has it locked in collaboration mode.
- **Setters return booleans** — `project.SetSetting(...)` returns `False` on
  unknown key OR wrong type (everything is a STRING in the API, even numbers).
  `"23.976"` not `23.976`.
- **Frame rate is sticky** — once a timeline has clips you cannot change its
  frame rate. Set it on the project BEFORE creating the first timeline.
- **`AppendToTimeline` ignores the playhead** — it always appends to V1/A1.
  For sophisticated placement use `mp.AppendToTimeline([{...clipInfo}])` with
  explicit `mediaPoolItem`, `startFrame`, `endFrame`, `trackIndex`.
- **`IsRenderingInProgress()` polls** — there is no callback. Use a 1–2s sleep
  loop; tighter polling burns CPU and can stall the render thread on small jobs.
- **Render preset names are exact strings** — case, spacing, parentheses all
  must match the saved name. `project.GetRenderPresetList()` to enumerate.
- **macOS Gatekeeper / Linux dylib path** — `fusionscript.so` must be on the
  loader path or `import DaVinciResolveScript` raises `ImportError` with a
  cryptic libc message. Always set `RESOLVE_SCRIPT_LIB` explicitly.
- **Saving** — most mutations are in-memory until `project.Save()` or until
  Resolve auto-saves. A crash before save loses script work.
- **Collaboration locks** — in collab mode, bins and clips are locked per user.
  Scripts that mutate locked items fail silently. Unlock first via the GUI.
- **Fusion comps inside TimelineItems** are a separate graph — the Edit/Color
  API does not reach into them. Use `tlitem.GetFusionCompByIndex(1)` then the
  Fusion Tool/Input/Output API which is a different shape entirely.
- **Headless rendering on Linux** still requires a display server unless you
  run Resolve under `xvfb-run`. There is no true CLI render mode.

See references/best_practices.md for the full 19-section creator-level knowledge base
including exact API signatures, the data model, hidden Fusion script idioms,
and EOS-specific automation recipes.
