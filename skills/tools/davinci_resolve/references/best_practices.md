# DaVinci Resolve Studio — Creator-Level Best Practices
Source: blackmagicdesign.com/products/davinciresolve, Resolve 19 Reference Manual,
        Developer/Scripting/README.txt (ships with Studio install),
        DaVinci Resolve Scripting Documentation (Blackmagic forum sticky),
        WeSuckLess Fusion scripting wiki, Resolve 19 New Features pdf
API Version: DaVinci Resolve 19.1 Studio (project graph + Resolve Scripting API)
SDK Version: DaVinciResolveScript (Python 3.6+ / Lua 5.1) bundled with Studio
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

There is no token, no API key, no OAuth flow for the Resolve Scripting API.
The script binding is a process-local IPC channel into the running Resolve
application: a Python script imports `DaVinciResolveScript`, which loads the
Blackmagic-shipped `fusionscript` shared library, which in turn talks to the
Fusion script server embedded in Resolve over a local socket / Mach port.
Auth is therefore filesystem permission to the running Resolve user — anyone
who can write that user's tmp dir can drive the API.

There ARE three real auth surfaces in the broader product:

1. **Studio activation** — the application itself is licensed, either via a
   USB dongle (Blackmagic license dongle) or an activation key tied to a
   Blackmagic ID. Without an active license the application starts in free
   mode and the script API silently degrades: many setters return `None`,
   Fusion scripting is unavailable, Neural Engine features are blocked, and
   delivery codecs (H.265, ProRes on Windows, DCP, IMF) are gated.

2. **Project Server (collaboration)** — multi-user projects live in a Postgres
   database. Each user configures host, port, dbname, user, password in
   Project Manager → Database. The DB user must have `CREATE`, `INSERT`,
   `UPDATE`, `DELETE`, and `LISTEN`/`NOTIFY` privileges on the project
   schemas. The default install creates a Postgres role `postgres` with
   password `DaVinci` — change this immediately on any non-laptop install.

3. **Blackmagic Cloud / Presentations** — uses a Blackmagic ID account with
   email + password (and optional 2FA). Cloud projects are thin sync proxies;
   the underlying graph still lives locally.

For EOS scripting, treat the script binding as "trust-the-process": run Resolve
under a dedicated `resolve` system user, never as root, never with the script
dir writable by other users.

## Core Operations with Exact Signatures

All signatures are from `Developer/Scripting/README.txt` shipped with Resolve
19 Studio and the Blackmagic forum sticky. Where types are missing in the
official doc, the empirically observed type is given.

### Top-level entry

```python
import DaVinciResolveScript as dvr_script
resolve = dvr_script.scriptapp("Resolve")          # -> Resolve | None
fusion  = dvr_script.scriptapp("Fusion")           # standalone Fusion Studio
```

### Resolve

```
resolve.GetProductName()                           -> str   "DaVinci Resolve"
resolve.GetVersionString()                         -> str   "19.1.2"
resolve.GetVersion()                               -> [major, minor, patch, build, suffix]
resolve.GetCurrentPage()                           -> "media"|"cut"|"edit"|"fusion"|"color"|"fairlight"|"deliver"|None
resolve.OpenPage(page_name: str)                   -> bool
resolve.GetMediaStorage()                          -> MediaStorage
resolve.GetProjectManager()                        -> ProjectManager
resolve.Quit()                                     -> None
resolve.LoadLayoutPreset(preset_name: str)         -> bool
resolve.SaveLayoutPreset(preset_name: str)         -> bool
resolve.UpdateLayoutPreset(preset_name: str)       -> bool
resolve.ExportLayoutPreset(preset_name, path)      -> bool
resolve.ImportLayoutPreset(path, preset_name="")   -> bool
resolve.GetKeyframeMode()                          -> int
resolve.SetKeyframeMode(mode: int)                 -> bool
```

### ProjectManager

```
pm.ArchiveProject(name, file_path,
                  isArchiveSrcMedia=True,
                  isArchiveRenderCache=True,
                  isArchiveProxyMedia=False)       -> bool
pm.CreateProject(name)                             -> Project | None
pm.LoadProject(name)                               -> Project | None
pm.GetCurrentProject()                             -> Project | None
pm.SaveProject()                                   -> bool
pm.CloseProject(project)                           -> bool
pm.CreateFolder(folder_name)                       -> bool
pm.DeleteFolder(folder_name)                       -> bool
pm.GetProjectListInCurrentFolder()                 -> [str]
pm.GetFolderListInCurrentFolder()                  -> [str]
pm.GotoRootFolder()                                -> bool
pm.GotoParentFolder()                              -> bool
pm.GetCurrentFolder()                              -> str
pm.OpenFolder(folder_name)                         -> bool
pm.ImportProject(file_path, name=None)             -> bool
pm.ExportProject(name, file_path,
                 withStillsAndLUTs=True)           -> bool
pm.RestoreProject(file_path, name=None)            -> bool
pm.GetCurrentDatabase()                            -> {DbType, DbName, IpAddress}
pm.GetDatabaseList()                               -> [{...}]
pm.SetCurrentDatabase(db_info: dict)               -> bool
pm.CreateCloudProject(cloud_settings: dict)        -> Project | None
pm.ImportCloudProject(file_path, cloud_settings)   -> bool
pm.RestoreCloudProject(folder_path, cloud_settings)-> bool
```

### Project

```
project.GetMediaPool()                             -> MediaPool
project.GetTimelineCount()                         -> int
project.GetTimelineByIndex(idx: int)               -> Timeline    # 1-based
project.GetCurrentTimeline()                       -> Timeline | None
project.SetCurrentTimeline(timeline)               -> bool
project.GetGallery()                               -> Gallery
project.GetName()                                  -> str
project.SetName(name)                              -> bool
project.GetPresetList()                            -> [{Name, ...}]
project.SetPreset(preset_name)                     -> bool
project.AddRenderJob()                             -> str  job_id
project.DeleteRenderJob(job_id)                    -> bool
project.DeleteAllRenderJobs()                      -> bool
project.GetRenderJobList()                         -> [{JobId, ...}]
project.GetRenderPresetList()                      -> [str]
project.StartRendering(job_ids=[],
                       isInteractiveMode=False)    -> bool
project.StopRendering()                            -> None
project.IsRenderingInProgress()                    -> bool
project.LoadRenderPreset(preset_name)              -> bool
project.SaveAsNewRenderPreset(preset_name)         -> bool
project.SetRenderSettings(settings: dict)          -> bool
project.GetRenderJobStatus(job_id)                 -> {JobStatus, CompletionPercentage, EstimatedTimeRemainingInMs}
project.GetSetting(setting_name="")                -> str | dict
project.SetSetting(setting_name, value: str)       -> bool
project.GetRenderFormats()                         -> {str: str}
project.GetRenderCodecs(format_name)               -> {str: str}
project.GetCurrentRenderFormatAndCodec()           -> {format, codec}
project.SetCurrentRenderFormatAndCodec(fmt, codec) -> bool
project.GetCurrentRenderMode()                     -> int   # 0 individual, 1 single
project.SetCurrentRenderMode(mode)                 -> bool
project.GetRenderResolutions(format, codec)        -> [{Width, Height}]
project.RefreshLUTList()                           -> bool
project.GetUniqueId()                              -> str
project.InsertAudioToCurrentTrackAtPlayhead(path, startOffsetInSamples, durationInSamples) -> bool
project.LoadBurnInPreset(preset_name)              -> bool
project.ExportCurrentFrameAsStill(file_path)       -> bool
project.GetColorGroupsList()                       -> [ColorGroup]
project.AddColorGroup(group_name)                  -> ColorGroup
project.DeleteColorGroup(color_group)              -> bool
project.Save()                                     -> bool
```

### MediaStorage

```
ms.GetMountedVolumeList()                          -> [str]
ms.GetSubFolderList(folder_path)                   -> [str]
ms.GetFileList(folder_path)                        -> [str]
ms.RevealInStorage(path)                           -> bool
ms.AddItemListToMediaPool(item1, item2, ...)       -> [MediaPoolItem]
ms.AddItemListToMediaPool(items: [str])            -> [MediaPoolItem]
ms.AddClipMattesToMediaPool(mp_item, paths, stereoEye="") -> bool
ms.AddTimelineMattesToMediaPool(paths)             -> [MediaPoolItem]
```

### MediaPool

```
mp.GetRootFolder()                                 -> Folder
mp.AddSubFolder(parent_folder, name)               -> Folder
mp.RefreshFolders()                                -> bool
mp.CreateEmptyTimeline(name)                       -> Timeline
mp.AppendToTimeline(clip1, clip2, ...)             -> [TimelineItem]
mp.AppendToTimeline(items: [MediaPoolItem|dict])   -> [TimelineItem]
mp.CreateTimelineFromClips(name, clips)            -> Timeline
mp.ImportTimelineFromFile(file_path, opts={})      -> Timeline
mp.DeleteTimelines(timelines)                      -> bool
mp.GetCurrentFolder()                              -> Folder
mp.SetCurrentFolder(folder)                        -> bool
mp.DeleteClips(clips)                              -> bool
mp.ImportFolderFromFile(file_path, opts={})        -> bool
mp.DeleteFolders(folders)                          -> bool
mp.MoveClips(clips, target_folder)                 -> bool
mp.MoveFolders(folders, target_folder)             -> bool
mp.GetClipMatteList(mp_item)                       -> [str]
mp.GetTimelineMatteList(folder)                    -> [MediaPoolItem]
mp.DeleteClipMattes(mp_item, paths)                -> bool
mp.RelinkClips(clips, folder_path)                 -> bool
mp.UnlinkClips(clips)                              -> bool
mp.ImportMedia(items: [str|dict])                  -> [MediaPoolItem]
mp.ExportMetadata(file_name, clips=[])             -> bool
mp.GetUniqueId()                                   -> str
```

### Folder

```
folder.GetClipList()                               -> [MediaPoolItem]
folder.GetName()                                   -> str
folder.GetSubFolderList()                          -> [Folder]
folder.GetIsFolderStale()                          -> bool
folder.GetUniqueId()                               -> str
folder.Export(file_path)                           -> bool
```

### MediaPoolItem

```
mpi.GetName()                                      -> str
mpi.GetMetadata(name="")                           -> str | dict
mpi.SetMetadata(name, value)                       -> bool
mpi.SetMetadata(metadata: dict)                    -> bool
mpi.GetThirdPartyMetadata(name="")                 -> str | dict
mpi.SetThirdPartyMetadata(name, value)             -> bool
mpi.GetMediaId()                                   -> str
mpi.AddMarker(frameId, color, name, note, duration, customData="") -> bool
mpi.GetMarkers()                                   -> {frameId: {color, duration, note, name, customData}}
mpi.GetMarkerByCustomData(customData)              -> {...}
mpi.UpdateMarkerCustomData(frameId, customData)    -> bool
mpi.GetMarkerCustomData(frameId)                   -> str
mpi.DeleteMarkersByColor(color)                    -> bool
mpi.DeleteMarkerAtFrame(frameNum)                  -> bool
mpi.DeleteMarkerByCustomData(customData)           -> bool
mpi.AddFlag(color)                                 -> bool
mpi.GetFlagList()                                  -> [str]
mpi.ClearFlags(color)                              -> bool
mpi.GetClipColor()                                 -> str
mpi.SetClipColor(color_name)                       -> bool
mpi.ClearClipColor()                               -> bool
mpi.GetClipProperty(prop="")                       -> str | dict
mpi.SetClipProperty(prop, value)                   -> bool
mpi.LinkProxyMedia(proxy_path)                     -> bool
mpi.UnlinkProxyMedia()                             -> bool
mpi.ReplaceClip(file_path)                         -> bool
mpi.GetUniqueId()                                  -> str
mpi.TranscribeAudio()                              -> bool
mpi.ClearTranscription()                           -> bool
```

### Timeline

```
timeline.GetName()                                 -> str
timeline.SetName(name)                             -> bool
timeline.GetStartFrame()                           -> int
timeline.GetEndFrame()                             -> int
timeline.GetStartTimecode()                        -> str
timeline.SetStartTimecode(tc)                      -> bool
timeline.GetTrackCount(track_type: "audio"|"video"|"subtitle") -> int
timeline.AddTrack(track_type, sub_track_type="")   -> bool
timeline.DeleteTrack(track_type, track_index)      -> bool
timeline.SetTrackEnable(track_type, track_index, bool) -> bool
timeline.GetIsTrackEnabled(track_type, idx)        -> bool
timeline.SetTrackLock(track_type, idx, bool)       -> bool
timeline.GetIsTrackLocked(track_type, idx)         -> bool
timeline.GetItemListInTrack(track_type, idx)       -> [TimelineItem]
timeline.AddMarker(frameId, color, name, note, duration, customData="") -> bool
timeline.GetMarkers()                              -> {frameId: {...}}
timeline.GetMarkerByCustomData(customData)         -> {...}
timeline.UpdateMarkerCustomData(frameId, customData)-> bool
timeline.DeleteMarkerAtFrame(frameId)              -> bool
timeline.DeleteMarkersByColor(color)               -> bool
timeline.DeleteMarkerByCustomData(customData)      -> bool
timeline.ApplyGradeFromDRX(path, gradeMode, items) -> bool
timeline.GetCurrentTimecode()                      -> str
timeline.SetCurrentTimecode(tc)                    -> bool
timeline.GetCurrentVideoItem()                     -> TimelineItem
timeline.GetCurrentClipThumbnailImage()            -> {width,height,format,data}
timeline.GetTrackName(track_type, idx)             -> str
timeline.SetTrackName(track_type, idx, name)       -> bool
timeline.DuplicateTimeline(new_name="")            -> Timeline
timeline.CreateCompoundClip(items, clipInfo={})    -> TimelineItem
timeline.CreateFusionClip(items)                   -> TimelineItem
timeline.ImportIntoTimeline(file_path, opts={})    -> bool
timeline.Export(file_path, exportType, exportSubtype) -> bool
timeline.GetSetting(name="")                       -> str | dict
timeline.SetSetting(name, value)                   -> bool
timeline.InsertGeneratorIntoTimeline(name)         -> TimelineItem
timeline.InsertFusionGeneratorIntoTimeline(name)   -> TimelineItem
timeline.InsertOFXGeneratorIntoTimeline(name)      -> TimelineItem
timeline.InsertTitleIntoTimeline(name)             -> TimelineItem
timeline.InsertFusionTitleIntoTimeline(name)       -> TimelineItem
timeline.GrabStill()                               -> GalleryStill
timeline.GrabAllStills(stillFrameSource: int)      -> [GalleryStill]
```

### TimelineItem

```
ti.GetName()                                       -> str
ti.GetDuration()                                   -> int frames
ti.GetEnd()                                        -> int
ti.GetStart()                                      -> int
ti.GetSourceEndFrame()                             -> int
ti.GetSourceStartFrame()                           -> int
ti.GetLeftOffset()                                 -> int
ti.GetRightOffset()                                -> int
ti.GetMediaPoolItem()                              -> MediaPoolItem
ti.GetFusionCompCount()                            -> int
ti.GetFusionCompByIndex(idx)                       -> Fusion comp
ti.GetFusionCompNameList()                         -> [str]
ti.GetFusionCompByName(name)                       -> Fusion comp
ti.AddFusionComp()                                 -> Fusion comp
ti.ImportFusionComp(path)                          -> Fusion comp
ti.ExportFusionComp(path, version)                 -> bool
ti.DeleteFusionCompByName(name)                    -> bool
ti.LoadFusionCompByName(name)                      -> Fusion comp
ti.RenameFusionCompByName(old, new)                -> bool
ti.AddMarker(frameId, color, name, note, duration, customData="") -> bool
ti.GetMarkers()                                    -> dict
ti.UpdateMarkerCustomData(frameId, customData)     -> bool
ti.GetMarkerCustomData(frameId)                    -> str
ti.DeleteMarkerAtFrame(frameId)                    -> bool
ti.DeleteMarkersByColor(color)                     -> bool
ti.DeleteMarkerByCustomData(customData)            -> bool
ti.AddFlag(color)                                  -> bool
ti.GetFlagList()                                   -> [str]
ti.ClearFlags(color)                               -> bool
ti.GetClipColor()                                  -> str
ti.SetClipColor(color)                             -> bool
ti.ClearClipColor()                                -> bool
ti.AddTake(media_pool_item, startFrame=None, endFrame=None) -> bool
ti.GetSelectedTakeIndex()                          -> int
ti.GetTakesCount()                                 -> int
ti.GetTakeByIndex(idx)                             -> dict
ti.DeleteTakeByIndex(idx)                          -> bool
ti.SelectTakeByIndex(idx)                          -> bool
ti.FinalizeTake()                                  -> bool
ti.CopyGrades(target_items: [TimelineItem])        -> bool
ti.SetClipEnabled(bool)                            -> bool
ti.GetClipEnabled()                                -> bool
ti.UpdateSidecar()                                 -> bool
ti.GetUniqueId()                                   -> str
ti.LoadBurnInPreset(preset_name)                   -> bool
ti.GetNumNodes()                                   -> int
ti.SetLUT(node_index, lut_path)                    -> bool
ti.GetLUT(node_index)                              -> str
ti.GetNodeLabel(node_index)                        -> str
ti.SetCDL(cdl: dict)                               -> bool   # keys: NodeIndex, Slope, Offset, Power, Saturation
ti.GetVersionCount()                               -> int
ti.GetCurrentVersion()                             -> {versionName, versionType}
```

### Gallery / GalleryStillAlbum / GalleryStill

```
gallery.GetAlbumName(album)                        -> str
gallery.SetAlbumName(album, name)                  -> bool
gallery.GetCurrentStillAlbum()                     -> GalleryStillAlbum
gallery.SetCurrentStillAlbum(album)                -> bool
gallery.GetGalleryStillAlbums()                    -> [GalleryStillAlbum]
album.GetStills()                                  -> [GalleryStill]
album.GetLabel(still)                              -> str
album.SetLabel(still, label)                       -> bool
album.ImportStills(file_paths)                     -> bool
album.ExportStills(stills, folder, file_prefix, format) -> bool
album.DeleteStills(stills)                         -> bool
album.ApplyGradeFromDRX(path, gradeMode, items)    -> bool
album.ApplyGrade(still, items)                     -> bool
```

### Fusion (page-level + tool-level)

```
fusion = resolve.Fusion()                          # global Fusion object
fusion.GetVersion()                                -> str
fusion.GetCurrentComp()                            -> Composition
fusion.LoadPrefs(path)                             -> bool
fusion.SavePrefs(path)                             -> bool
fusion.GetPrefs(name="")                           -> dict
fusion.SetPrefs(name, value)                       -> bool
fusion.GetResolve()                                -> Resolve

# Composition
comp.AddTool(tool_id, x=-32768, y=-32768)          -> Tool
comp.FindTool(name)                                -> Tool
comp.GetToolList(selectedOnly=False, regex="")     -> {idx: Tool}
comp.CurrentFrame()                                -> int
comp.GetData(name)                                 -> any
comp.SetData(name, value)                          -> None
comp.Lock(); comp.Unlock()                         -> None
comp.StartUndo(name); comp.EndUndo(keep)           -> None

# Tool
tool.GetAttrs()                                    -> dict
tool.SetAttrs(attrs: dict)                         -> None
tool.GetInputList()                                -> {idx: Input}
tool.GetOutputList()                               -> {idx: Output}
tool.ConnectInput(input_id, source_output)         -> None
tool.SetInput(input_id, value, frame=-1.0)         -> None
tool.GetInput(input_id, frame=-1.0)                -> any
```

### Render settings dictionary keys (most-used)

```
SelectAllFrames        -> bool
MarkIn / MarkOut       -> int (timecode in frames)
TargetDir              -> str
CustomName             -> str
UniqueFilenameStyle    -> 0 prefix | 1 suffix
ExportVideo            -> bool
ExportAudio            -> bool
FormatWidth/Height     -> int
FrameRate              -> "23.976" | "24" | "25" | ...
PixelAspectRatio       -> float
VideoQuality           -> int (codec-dependent)
AudioCodec / AudioBitDepth / AudioSampleRate
ExportAlpha            -> bool
EncodingProfile        -> "Auto" | "Main" | "High" | ...
MultiPassEncode        -> bool
AlphaMode              -> 0 premultiplied | 1 straight
ColorSpaceTag / GammaTag
NetworkOptimization    -> bool   # MOV/MP4 fast-start
```

## Pagination Patterns

N/A in the strict REST sense — Resolve has no paginated network API. The
closest equivalents are bounded list returns:

- `pm.GetProjectListInCurrentFolder()` returns the entire folder contents
  in one synchronous call. For databases with thousands of projects, walk
  the folder tree with `GotoRootFolder` + recursion rather than relying on
  any built-in pagination (there is none).
- `folder.GetClipList()` returns every clip in the bin. With 10k+ clips this
  blocks the script for several seconds; either organize into sub-bins or
  cache results in a sidecar JSON in EOS storage.
- `timeline.GetItemListInTrack("video", idx)` returns all items on a track.
  Iterate by track index 1..GetTrackCount.
- Render job status is polled via `IsRenderingInProgress()` + `GetRenderJobStatus(job_id)`.
  No callback hook; choose poll interval to match expected job duration.

## Rate Limits

N/A — local IPC. There are no quotas. The practical bounds are:

- **GUI redraw budget** — large script bursts (e.g. AddMarker in a tight
  loop on 10k frames) starve the UI thread. Wrap loops with
  `comp.Lock()` / `comp.Unlock()` for Fusion or batch via
  `mp.AppendToTimeline([...])` rather than per-clip calls.
- **Render thread contention** — polling `IsRenderingInProgress` faster than
  ~5 Hz noticeably slows the actual render. 1–2s is the conventional interval.
- **Disk I/O** — the real ceiling on `AddItemListToMediaPool` for large
  ingests; warm the OS file cache first if you need predictable timing.
- **Postgres collab** — the project DB has standard PG limits; the practical
  ceiling is ~25 concurrent grading users on a single Postgres instance per
  Blackmagic's published collaboration guide.

## Error Codes and Recovery

The script API does NOT raise exceptions for most failures — it returns `None`
or `False`. There are no numeric error codes. The recovery posture is
"check every return value, log the call site."

| Symptom | Cause | Recovery |
|---|---|---|
| `scriptapp("Resolve")` returns `None` | Resolve not running, wrong `RESOLVE_SCRIPT_LIB`, wrong arch dylib | start Resolve, fix env vars, match arch (Intel vs ARM) |
| `pm.LoadProject(name)` returns `None` | typo, project in different folder, locked by another collab user | `pm.GetProjectListInCurrentFolder()`, walk folders, unlock |
| `project.SetSetting(...)` returns `False` | unknown key, wrong type (everything is `str`), or read-only after timeline created (e.g. frame rate) | check key against `GetSetting()` enum, stringify all values, set BEFORE first timeline |
| `mp.CreateEmptyTimeline(...)` returns `None` | name collision in current folder, or no project open | unique name, ensure `GetCurrentProject()` is non-None |
| `mp.AppendToTimeline([...])` returns `[]` | no current timeline, or clipInfo dicts malformed | `project.SetCurrentTimeline(t)` first, validate keys |
| `project.AddRenderJob()` returns `""` | no render preset loaded, or no clips on the timeline | `LoadRenderPreset()`, ensure timeline has content |
| `project.StartRendering(...)` returns `False` | another render in progress, or invalid job_ids list | `IsRenderingInProgress()`, `GetRenderJobList()` |
| Render job status `Failed` | usually disk space or codec license | check `TargetDir`, check Studio license for codec |
| `ti.SetLUT(idx, path)` returns `False` | node index out of range, LUT path not in Resolve's LUT folders | `RefreshLUTList()`, copy LUT into `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/` |
| `import DaVinciResolveScript` ImportError | `RESOLVE_SCRIPT_LIB` missing, wrong Python ABI | export the env vars, match Python 3.6+ x86_64/arm64 to dylib |
| Script hangs forever | UI dialog popped (modal save, missing media) | switch to Resolve GUI, dismiss dialog, never script with unsaved-changes prompts pending |
| Fusion `comp.AddTool(...)` returns `None` | invalid tool ID string, or comp locked | use exact tool registry IDs (`Background`, `Merge`, `Text+`), `Unlock()` first |

Recovery recipe for a wedged script session:

```python
# 1) Confirm liveness
print(resolve.GetVersionString())
# 2) Reload project from disk to discard in-memory junk
name = pm.GetCurrentProject().GetName()
pm.CloseProject(pm.GetCurrentProject())
pm.LoadProject(name)
# 3) If render queue is jammed
pm.GetCurrentProject().StopRendering()
pm.GetCurrentProject().DeleteAllRenderJobs()
```

## SDK Idioms

The Resolve Scripting API is unusual: it is a hand-rolled C++ binding exposed
through `fusionscript`, originally designed for Fusion's Lua console. Pythonic
idioms do NOT apply. Internalize these patterns:

1. **Stringly-typed settings** — every project/timeline/render setting is a
   string, even numeric ones. `"23.976"` not `23.976`. `"1920"` not `1920`.
   Wrap with `str()` defensively in your own helpers.

2. **Object identity is fragile** — objects returned from the API are thin
   handles back to in-memory C++ objects. Closing/loading a project
   invalidates every cached handle. Re-fetch after any project switch.

3. **No exceptions, only `None` and `False`** — write every line as
   `result = obj.Method(...); assert result, f"call failed: ..."` or you will
   silently lose work. EOS pattern: a `_check(call, label)` helper.

4. **Batch where possible** — `mp.AppendToTimeline([item1, item2, ...])` is
   one call; looping `AppendToTimeline(item)` 100 times is 100 round-trips
   to the UI thread.

5. **`clipInfo` dicts** — for precise placement use the dict form:
   ```python
   mp.AppendToTimeline([{
       "mediaPoolItem": mpi,
       "startFrame":    0,
       "endFrame":      239,
       "trackIndex":    1,
       "recordFrame":   86400,        # in source/timeline frame, not TC
   }])
   ```

6. **Frames not timecode** — most APIs take integer frames. Convert with
   `timeline.GetSetting("timelineFrameRate")` and your own SMPTE math.

7. **Color is a name string** — markers and clip colors are strings:
   `"Blue"`, `"Cyan"`, `"Green"`, `"Yellow"`, `"Red"`, `"Pink"`, `"Purple"`,
   `"Fuchsia"`, `"Rose"`, `"Lavender"`, `"Sky"`, `"Mint"`, `"Lemon"`,
   `"Sand"`, `"Cocoa"`, `"Cream"`. Other strings silently fail.

8. **Fusion comps are a different API** — once you reach into a `tlitem`'s
   Fusion comp via `GetFusionCompByIndex(1)`, you are in Fusion's tool/input
   API. `comp.AddTool("Text+", x, y)` creates a node; `tool.SetInput("StyledText", "hello")`
   sets a parameter. Read the WeSuckLess wiki, not the Resolve scripting README.

9. **Scripts CAN run inside Resolve** — drop a `.py` file in
   `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/`
   (or the Linux/Win equivalent) and it appears under Workspace → Scripts. In
   that mode `resolve` is a global; `dvr_script.scriptapp("Resolve")` is unnecessary.

10. **Lua and Python are equivalent** — every method exposed in Python has
    the same name in Lua. The Lua console is faster to iterate in for Fusion
    work because it lives inside the running app.

## Anti-Patterns

- **Treating `SetSetting` returns as success** — many keys silently no-op;
  always read back with `GetSetting` to verify.
- **Caching `Project` / `Timeline` objects across `LoadProject`** — handles
  go stale; you get `None` returns from valid-looking calls.
- **Looping `AddMarker` per frame** — kills the UI thread; instead build
  markers with a single timeline lock if doing thousands.
- **Using floats for any setting** — `1920.0` is not `"1920"`; the binding
  rejects it as wrong type.
- **Setting frame rate after a timeline exists** — silently fails. Set on
  empty project first.
- **Polling `IsRenderingInProgress` at 100Hz** — slows the render. 1–2s.
- **Hardcoding render preset names** — varies by user; enumerate with
  `GetRenderPresetList()` or ship the preset XML and `ImportLayoutPreset`.
- **Modifying the project from multiple Python processes** — undefined.
  Single-writer only.
- **Forgetting to `project.Save()`** — script work evaporates on crash.
- **Running scripts during a modal dialog** — the API hangs. Always close
  unsaved-changes prompts first.
- **Trying to mutate clips in a locked collaboration bin** — silent failure.
- **Mixing free and Studio scripts** — Fusion scripting and Neural Engine
  calls return `None` on free; build a `is_studio()` probe.
- **Using OS path separators in `SetRenderSettings["TargetDir"]`** — use
  forward slashes on macOS/Linux, backslashes on Windows; the binding does
  not normalize.
- **Calling `Quit()` in the middle of a render** — corrupts the queue.

## Data Model

The Resolve project graph, in dependency order:

```
ProjectManager  (singleton, owns DB connection)
  └── Database  (disk PostgresQL or local sqlite)
        └── Folder*                          (project organization, not bins)
              └── Project*                   (named, persisted)
                    ├── Settings             (str → str map)
                    ├── MediaPool
                    │     └── Folder (bin)*  (recursive)
                    │           └── MediaPoolItem*
                    │                 ├── Metadata (str → str)
                    │                 ├── ClipProperty (str → str)
                    │                 ├── Markers (frame → marker)
                    │                 ├── Flags (set of color)
                    │                 ├── Proxy link
                    │                 └── Source media path
                    ├── Timeline*
                    │     ├── Tracks (video/audio/subtitle, 1-based)
                    │     │     └── TimelineItem*
                    │     │           ├── MediaPoolItem ref
                    │     │           ├── In/Out/Source frames
                    │     │           ├── Color nodes (graph)
                    │     │           │     ├── Primary
                    │     │           │     ├── Secondary (qualifier, mask)
                    │     │           │     ├── ResolveFX
                    │     │           │     ├── LUT
                    │     │           │     └── CDL
                    │     │           ├── Fusion comps (named, multiple)
                    │     │           │     └── Tool graph (nodes + connections)
                    │     │           ├── Audio essence
                    │     │           ├── Markers
                    │     │           ├── Flags
                    │     │           └── Takes
                    │     ├── Markers (timeline-level)
                    │     ├── Compound clips
                    │     └── Settings (resolution, fps, color science)
                    ├── Gallery
                    │     └── StillAlbum*
                    │           └── GalleryStill* (.drx serialization)
                    ├── ColorGroup* (shared grades across clips)
                    ├── RenderJob*
                    │     ├── PresetName
                    │     ├── Settings (dict)
                    │     └── Status (queued|rendering|completed|failed)
                    └── BurnInPreset* (overlay templates)
```

Identity rules:

- Every `MediaPoolItem`, `TimelineItem`, `Folder`, `Timeline`, `Project` has
  a stable `GetUniqueId()` GUID. Persist these in EOS Neon for cross-session
  references — names are user-mutable.
- `MediaPoolItem.GetMediaId()` is a content-derived ID (changes if the file
  is replaced).
- Project handles invalidate on `LoadProject` / `CloseProject`.

## Webhooks and Events

N/A in the network sense. Resolve has no outbound webhooks. There are TWO
event-ish surfaces:

1. **Fusion event handlers** — inside a Fusion comp you can register
   `comp:AddNotify("Comp_Save", function(ev) ... end)` from Lua; Python is
   more limited and generally polls. Useful for in-app tooling, not for EOS.

2. **Render queue polling** — `IsRenderingInProgress()` + `GetRenderJobStatus(id)`
   is the only way to know a job finished. EOS pattern: spawn a watcher
   coroutine that polls every 2s and writes status transitions to Neon.

For "Resolve told EOS the render finished," wrap the poll loop in a Python
script that POSTs to your EOS webhook endpoint when status flips to
`"Complete"`.

## Limits

| Limit | Value | Notes |
|---|---|---|
| Max timeline tracks | 1000 video / 1000 audio (practical) | Resolve refuses past this |
| Max resolution | 32K × 32K (Studio) / 4K (Free) | most Studio installs cap at 8K usefully |
| Max project size | DB-bound; tested 10GB project files | use Postgres collab past 1GB |
| Max clips in bin | no hard limit; 100k+ is sluggish | shard into sub-bins |
| Max render jobs | unlimited | persisted in project |
| Max markers per clip | one per frame | 24*60*60 = 86400 at 24fps |
| Concurrent collab users | ~25 per Postgres instance | Blackmagic guidance |
| Free vs Studio resolution | Free capped at 3840×2160 | Studio uncapped |
| Free framerate | up to 60p | Studio: up to 120p+ for Ultra HD |
| Free codecs | H.264 8-bit 4:2:0 only on Win | Studio adds ProRes, DNx, H.265, DCP, IMF |
| Neural Engine features | Studio-only | Magic Mask, Voice Isolation, Smart Reframe, Detect Scene Cuts, AutoCaption |
| Fusion scripting | Studio-only | Free has no Fusion script API |

## Cost Model

- **Free version** — $0. Sufficient for most editing, basic color, basic
  Fusion (no scripting), basic Fairlight. Enough to learn on.
- **DaVinci Resolve Studio** — $295 USD one-time purchase, perpetual license.
  Includes all updates within the major version (19.x → 19.y free, 19 → 20
  is also typically free). USB dongle adds ~$30 if you need transferable.
- **Postgres collaboration** — free if you self-host PG; Blackmagic does not
  charge. Network costs only.
- **Blackmagic Cloud** — Presentation hosting and Cloud Sync are subscription
  ($5/mo Presentations as of 2024); not required for scripting or rendering.
- **Hardware** — the real cost. Studio takes advantage of NVIDIA/AMD/Apple
  Silicon GPUs; Neural Engine features want a recent GPU (RTX 3060+ or M1+).
  A grading-grade UI panel (Micro Panel $995 / Mini Panel $2995) is the next
  upgrade if Antony moves into client color work for Empyrean Studio.
- **EOS budget impact** — one-time $295 unlocks scripting, Neural Engine,
  Fusion automation, and all delivery codecs. Trivial relative to the
  hours saved on automated render dispatch and project bootstrapping.

## Version Pinning

Resolve has a major.minor.patch.build version. Stable releases ship every
2–3 months; betas (called "public beta") sometimes break the script API
in subtle ways (rename of setting keys, new required fields).

EOS pinning policy:
- Pin to a specific Resolve Studio version on the render workstation via the
  Blackmagic installer (do not auto-update).
- Record `resolve.GetVersionString()` in every script run's Neon log.
- Before upgrading: snapshot the project DB, run the EOS resolve script
  smoke test against the new version on a scratch project.
- Resolve installer keeps no rollback; download the previous version DMG/EXE
  from Blackmagic's "DaVinci Resolve Older Versions" page and keep a copy in
  `/opt/OS/installers/`.
- Project files written by a newer version cannot be opened by an older
  version. Treat the upgrade as one-way per project.
- The script API has been **mostly** stable since Resolve 16. Breaking
  changes are documented in `Developer/Scripting/README.txt` per release;
  diff this file on every upgrade.

Version detection at runtime:

```python
major, minor, patch, build, suffix = resolve.GetVersion()
if (major, minor) < (19, 0):
    raise RuntimeError("EOS scripts require Resolve 19+")
```

## Design Intent and Tradeoffs

Resolve was originally a color grading workstation (da Vinci Systems, 1984).
Blackmagic acquired it in 2009 for $800k and pursued a deliberate strategy:
absorb every adjacent post-production discipline into one binary, free, with
a paid Studio tier that pays for itself the first time you need a real codec.

Design decisions that follow from this history:

- **One process, one project** — there is no "library" concept across
  projects. Render queues, gallery stills, color presets are all
  project-scoped. The script API reflects this — there is no cross-project
  query.
- **Page UIs share state** — Cut, Edit, Color, Fusion, Fairlight, Deliver
  are six lenses on the same in-memory graph. This is why mutations from
  one page instantly appear in another.
- **Color is the heart** — node-based grading is the most powerful module.
  Edit and Fairlight are competitive with Premiere/Pro Tools but the color
  page has no rival.
- **Fusion is bolted on** — Blackmagic acquired eyeon Software's Fusion
  in 2014 and embedded it as a page. The Fusion comp inside a TimelineItem
  is essentially a sub-application with its own object model, scripting
  syntax (originally Lua), and undo stack.
- **Stringly-typed API** — Resolve's binding predates modern Python type
  hints. Blackmagic chose API stability over ergonomic typing.
- **No network API** — Blackmagic's worldview is local-first, hardware-first.
  They sell cameras, control surfaces, and capture cards. Cloud is an add-on,
  not the substrate.
- **Free version is generous** — strategically chosen to dominate education
  and enthusiast markets, then upsell Studio when codecs/features bite.
- **Annual major release at NAB/IBC** — the public beta runs from April,
  stable lands in summer. Plan EOS upgrades around this cycle.

Tradeoffs vs alternatives:

| Vs | Resolve wins | Resolve loses |
|---|---|---|
| Premiere Pro | Color, Fusion, free tier, no subscription | Adobe ecosystem integration, AE roundtrip |
| Final Cut Pro | Cross-platform, color, scripting | macOS-native speed, magnetic timeline UX |
| Avid Media Composer | Modern UI, Fusion, free | Broadcast turnover workflows, ScriptSync |
| After Effects | All-in-one, no roundtrip | AE plugin ecosystem, expression engine |
| Pro Tools | Single binary, included in Studio | DAW plugin ecosystem, mixing console support |

## Problem-Solution Map and Hidden Capabilities

**"I need to cut 50 short-form clips from a 90-min long-form."**
→ Add markers in the long-form on the Edit page, then script:
`for marker in timeline.GetMarkers(): mp.CreateTimelineFromClips(...)`.
Or use Smart Bins with marker filters.

**"Apply the same look to every shot in a series."**
→ Save a PowerGrade still in the Gallery; script
`album.ApplyGradeFromDRX(path, mode, items)` over `GetItemListInTrack`.

**"Render in 5 aspect ratios for one piece of content."**
→ Save 5 render presets, script `LoadRenderPreset` + `AddRenderJob` per
preset, then `StartRendering(all_jobs)`.

**"Conform an EDL/AAF/XML from another NLE."**
→ `mp.ImportTimelineFromFile(path, opts)` accepts EDL, AAF, XML, FCPXML, OTIO.
Conform happens on import; mismatched media flags as offline.

**"Transcribe dialogue."** (hidden — Studio only, 18.5+)
→ `mpi.TranscribeAudio()` then markers appear; export via Fairlight →
Subtitles → Create Subtitles from Audio.

**"Voice isolation on a noisy interview."** (Studio only)
→ Fairlight → Effects → Voice Isolation. ML-driven, on-device, no cloud.

**"Auto-detect scene cuts in a single long file."**
→ Color page → right-click clip → Scene Cut Detection. Outputs cuts as
markers; can be exported as EDL.

**"Magic-mask a person and grade only them."** (Studio only)
→ Color page → Magic Mask → object/person mode → tracker auto-propagates.

**"Reframe horizontal to vertical for IG."** (Studio only)
→ Smart Reframe in the Edit page Inspector. Tracks subject and produces
keyframes you can override.

**"Render burn-ins (timecode, clip name) for review."**
→ Workspace → Data Burn-In → save preset → `project.LoadBurnInPreset(name)`.

**"Backup an entire project including media."**
→ `pm.ArchiveProject(name, file_path, isArchiveSrcMedia=True, isArchiveRenderCache=False)`.

**"Drive Resolve from a remote machine."**
→ Run script from any host that can reach Resolve's filesystem; for true
remote, use Postgres collaboration and run scripts on the project DB host.

**Hidden gems:**
- `timeline.CreateFusionClip([items])` — turn a stack into a single Fusion
  comp clip.
- `tlitem.CopyGrades([targets])` — propagate a node tree to every match.
- `comp.SetData("eos_marker", value)` — stash arbitrary metadata in a Fusion
  comp; survives save/load.
- `mpi.SetThirdPartyMetadata(...)` — write camera/audio metadata that ships
  out via XML/AAF for downstream tools.
- `Workspace → Console` opens a Lua REPL into the running Resolve — fastest
  way to introspect API objects.

## Operational Behavior and Edge Cases

- **Auto-save** is on by default (every 5 min, configurable). Scripts should
  still call `project.Save()` after major mutations.
- **Undo stack** is shared across pages but per-project. Scripts that mutate
  a project create undo entries; you can wrap with the Fusion-only
  `comp:StartUndo`/`comp:EndUndo` for Fusion mutations.
- **Crash recovery** — Resolve writes a `.crashrecover` next to the project;
  on restart it offers to recover. Scripts that crash mid-mutation rely on
  this; do not depend on it.
- **GPU contention** — Resolve assumes the GPU. Running another GPU-heavy
  process (Stable Diffusion, ML training) on the same machine causes UI
  freezes and render slowdowns. EOS pattern: dedicate a render box.
- **Audio sample rate mismatch** — clips at the wrong rate are resampled on
  the fly; scripts ingesting massive audio batches should pre-conform.
- **Linux quirks** — Resolve on Linux only supports Rocky Linux 8.6 / 8.8
  officially. Other distros work via the AppImage but Blackmagic does not
  test them. Use `xvfb-run` for headless render workers.
- **Project DB lock** — opening a project in the GUI while a script is
  mutating it via Postgres collab → undefined behavior. Use single-writer
  discipline.
- **Render cache** — cached frames live in `Project Settings → Master Settings →
  Working Folders → Cache files location`. Clear from `Playback → Delete Render Cache`
  or by deleting the folder while Resolve is closed.
- **Optimized media vs proxy** — different concepts. Optimized is generated
  internally; proxy is externally linked. Scripts using `LinkProxyMedia`
  must point to a same-frame-count file.
- **Frame rate vs Drop Frame** — `SetSetting("timelineDropFrameTimecode", "1")`
  is independent of the rate. NTSC (29.97/59.94) without DF is a footgun.
- **Color space management** — `colorScienceMode` set to
  `davinciYRGBColorManagedv2` enables DRT; otherwise input/output transforms
  must be set per clip in the Color page.
- **Fairlight mixdown** — render queue audio export goes through the
  Fairlight bus structure. Solo/Mute states affect the render. Reset the
  mix before scripting a delivery.
- **Background of GUI vs script execution** — script ops queue behind GUI
  events. Long script loops appear to "freeze" the GUI; this is normal.

## Ecosystem Position and Composition

Resolve sits at the center of a Blackmagic ecosystem and at the periphery of
the broader post-production world.

Inside the Blackmagic ecosystem:
- **URSA / Pocket Cinema cameras** — shoot in BRAW; Resolve is the only NLE
  with native 12-bit BRAW debayer.
- **Speed Editor / Editor Keyboard / Mini Panel / Micro Panel / Advanced
  Panel** — hardware control surfaces, all driven by the same project graph.
- **Cloud Store / Cloud Pod** — networked storage tuned for Resolve's I/O
  patterns.
- **DeckLink / UltraStudio** — capture and monitoring cards integrated via
  the Decklink page in Project Settings.

Outside Blackmagic:
- **Adobe Premiere / After Effects** — bidirectional via AAF/XML/OTIO; no
  live integration.
- **Avid Media Composer** — AAF interchange.
- **Pro Tools** — AAF audio handoff from Fairlight.
- **Frame.io / Iconik** — third-party MAM integration via export plugins.
- **OTIO (OpenTimelineIO)** — Resolve 18+ supports import and export of OTIO
  for non-destructive timeline interchange. Use this from EOS for future
  cross-tool flexibility.
- **OFX plugins** — Resolve supports OpenFX plugins (BorisFX Sapphire,
  Continuum, NeatVideo). Scripted enable via the OFX node ID.
- **LUTs** — Resolve consumes .cube, .3dl, .ilut, .drx (PowerGrade), and DCTL
  (DaVinci Color Transform Language, GPU shaders).

EOS composition pattern:
- **Capture** (BRAW from URSA Mini Pro, ProRes from FX3) →
- **Ingest** (script-driven AddItemListToMediaPool) →
- **Edit** (GUI, Antony in seat) →
- **Color** (script applies house PowerGrade, GUI for refinement) →
- **Fairlight** (Voice Isolation script + GUI mix) →
- **Deliver** (script renders 5 aspects via render queue) →
- **Publish** (handoff to EOS publish_pipeline.py for IG/YT/X/LinkedIn).

## Trajectory and Evolution

Major milestones:
- **2009** — Blackmagic acquires Resolve from da Vinci Systems for $800k.
- **2011** — Resolve 8 introduces the Mac version, dropping the requirement
  for proprietary hardware.
- **2014** — Resolve 11 adds editing alongside color (becomes a real NLE).
- **2014** — Blackmagic acquires Fusion from eyeon Software.
- **2017** — Resolve 14 adds Fairlight (audio).
- **2018** — Resolve 15 integrates Fusion as a page; first Resolve with all
  five disciplines under one roof.
- **2019** — Resolve 16 introduces the Cut page (fast-edit workflow).
- **2020** — Resolve 17 redesigns color page with HDR palette + new color
  warper.
- **2022** — Resolve 18 introduces Blackmagic Cloud and Proxy Generator.
- **2023** — Resolve 18.5 adds AI text-based editing and voice isolation
  (Studio).
- **2024** — Resolve 19 adds IntelliScript (auto-multicam from text),
  improved Magic Mask, and AudioAssist Auto-EQ. DCTL gains float4.
- **2024** — Resolve 19 expands the script API: timeline transcription,
  improved Fusion comp introspection, render preset import/export.

Direction of travel:
- **More AI on-device** — every release adds Neural Engine features.
  Voice cloning, generative inpaint, and ML-based color matching are
  signaled for 20.x.
- **Deeper cloud collab** — Blackmagic Cloud projects gain features that
  used to be Postgres-collab-only.
- **Wider script API** — Blackmagic has been steadily exposing more of the
  internal model. EOS bet: by 2027 the API will support headless project
  mutation without an active GUI session.
- **BRAW everywhere** — Blackmagic pushes BRAW as a deliverable, not just
  acquisition format.

Implication for EOS: invest in scripting NOW. Every API addition compounds.
Build templates and JSON specs that survive major-version upgrades.

## Conceptual Model and Solution Recipes

Mental model: **Resolve is a project graph, six lenses, one script API.**
The graph is the only truth. Each page (Cut, Edit, Color, Fusion, Fairlight,
Deliver) is a UI projection of the same underlying state. The script API is
the seventh lens — the one EOS uses.

Three conceptual axes that explain almost every Resolve behavior:

1. **What is open?** — `pm.GetCurrentProject()` and `project.GetCurrentTimeline()`
   anchor every script call. If either is `None`, nothing else works.
2. **What is selected?** — many GUI operations act on selection; the script
   API mostly bypasses selection by taking explicit object lists. Prefer
   explicit lists.
3. **What is persisted?** — settings, markers, render jobs are persisted in
   the project. Gallery stills are persisted as `.drx` plus image. Fusion
   comps are persisted as part of TimelineItems. Render results are files
   on disk and survive project deletion.

### Recipe: bootstrap an Initiate Arena VSL project from a JSON spec

```python
import json, time
import DaVinciResolveScript as dvr_script

resolve = dvr_script.scriptapp("Resolve")
pm      = resolve.GetProjectManager()
spec    = json.load(open("/opt/OS/eos_ai/templates/resolve_projects/vsl.json"))

assert pm.CreateProject(spec["name"]), "create failed"
project = pm.GetCurrentProject()
for k, v in spec["settings"].items():
    assert project.SetSetting(k, str(v)), f"setting {k}={v} failed"

mp = project.GetMediaPool()
ms = resolve.GetMediaStorage()
items = ms.AddItemListToMediaPool(spec["ingest_path"])
assert items, "no clips ingested"

timeline = mp.CreateEmptyTimeline(spec["timeline_name"])
project.SetCurrentTimeline(timeline)
mp.AppendToTimeline(items)

album = project.GetGallery().GetCurrentStillAlbum()
for tlitem in timeline.GetItemListInTrack("video", 1):
    album.ApplyGradeFromDRX(spec["powergrade_drx"], 0, [tlitem])

for marker in spec["markers"]:
    timeline.AddMarker(marker["frame"], marker["color"],
                       marker["name"], marker["note"], 1)

for preset in spec["render_presets"]:
    project.LoadRenderPreset(preset["name"])
    project.SetRenderSettings({
        "TargetDir":  preset["out_dir"],
        "CustomName": preset["filename"],
    })
    project.AddRenderJob()

project.Save()
```

### Recipe: render queue watcher with Neon logging

```python
import time
project = pm.GetCurrentProject()
job_ids = [j["JobId"] for j in project.GetRenderJobList()]
project.StartRendering(job_ids, isInteractiveMode=False)
last = {}
while project.IsRenderingInProgress():
    for jid in job_ids:
        st = project.GetRenderJobStatus(jid)
        if st != last.get(jid):
            last[jid] = st
            log_to_neon(jid, st)         # EOS helper
    time.sleep(2)
for jid in job_ids:
    log_to_neon(jid, project.GetRenderJobStatus(jid), final=True)
```

### Recipe: pull all timeline markers as JSON for content tracking

```python
import json
out = []
for ti in timeline.GetItemListInTrack("video", 1):
    out.append({
        "name":   ti.GetName(),
        "start":  ti.GetStart(),
        "end":    ti.GetEnd(),
        "color":  ti.GetClipColor(),
        "markers":ti.GetMarkers(),
    })
json.dump(out, open("/tmp/vsl_markers.json", "w"), indent=2)
```

### Recipe: ingest a folder and bin by filename prefix

```python
import os
ms = resolve.GetMediaStorage()
mp = project.GetMediaPool()
root = mp.GetRootFolder()
bins = {}
for path in ms.GetFileList("/mnt/footage/2026-04-06_shoot"):
    prefix = os.path.basename(path).split("_")[0]
    if prefix not in bins:
        bins[prefix] = mp.AddSubFolder(root, prefix)
    mp.SetCurrentFolder(bins[prefix])
    ms.AddItemListToMediaPool(path)
```

## Industry Expert and Cutting-Edge Usage

How working colorists, editors, and pipeline TDs actually use Resolve:

- **Colorists** keep their Gallery organized by client/show, with PowerGrades
  named with the convention `{ShowCode}_{LookName}_{Version}`. The script
  API turns this into a real asset library.
- **Conform editors** import EDL/AAF from offline (Avid/Premiere) and use
  `mp.ImportTimelineFromFile` with offline-conform options to relink to
  high-res masters. EOS pattern: a script that takes an Avid AAF, conforms
  to a media pool, and creates a single timeline ready for color.
- **VFX supervisors** use Fusion comps inside TimelineItems for shot-level
  cleanup (rig removal, paint, screen replacement) without bouncing to
  Nuke. `tlitem.AddFusionComp()` is the script entry point.
- **Sound editors** export Fairlight sessions via AAF for Pro Tools
  conform. `timeline.Export(path, "aaf", "audio")` is the call.
- **Pipeline TDs** drive Resolve from a render farm using Lua scripts in
  `Workspace → Console` invoked over SSH; the scripts read job manifests
  from a shared filesystem. EOS analog: Python script driven from cron,
  manifests in Neon.
- **Documentary editors** use IntelliScript (Resolve 19) to auto-multicam
  from interview transcripts — script-callable in 19.1.
- **Trailer cutters** lean on Smart Bins with marker color filters
  ("All shots flagged Red are hero beats") rather than manual sorting.
- **Color supervisors on streaming shows** use ColorGroups to cluster shots
  by setup; one grade change propagates. Script: `project.AddColorGroup(name)`,
  then assign clips via the GUI (ColorGroup assignment is not yet in script).
- **DCP delivery houses** use Resolve's built-in DCP encoder (Studio) and
  script the package naming + reel structure via render presets.
- **YouTube creators at scale** (MrBeast-style operations) script-render
  multiple aspect ratios + thumbnail stills + chapter marker exports in a
  single overnight queue.
- **Educational pipelines** (university post programs) use Resolve free
  with Postgres collab so 20+ students share one project DB.

Cutting-edge patterns:
- **DCTL shaders** — write GPU code in DaVinci's color transform language
  for custom looks; ship `.dctl` files alongside PowerGrades.
- **OpenColorIO (OCIO) integration** — Resolve 18.5+ supports OCIO config
  files for VFX pipeline color management.
- **OpenTimelineIO** — round-trip timelines through OTIO for Hiero/Nuke
  conform.
- **USD layers** for Fusion 3D — Fusion 19 reads USD scenes from Houdini/Maya.
- **Generative AI assist** — Resolve 19.1's AI matching cuts shots from
  reference; signaled to expand in 20.x.

## EOS Usage Patterns

Concrete patterns for EOS Developer Agent:

### Pattern 1 — JSON-spec project bootstrap

**When:** Antony shoots a new VSL or content batch and wants the project
pre-configured before he sits down.

**Spec format** (`/opt/OS/eos_ai/templates/resolve_projects/vsl.json`):
```json
{
  "name": "Initiate_Arena_VSL_2026_04_06",
  "settings": {
    "timelineResolutionWidth":  "1920",
    "timelineResolutionHeight": "1080",
    "timelineFrameRate":        "23.976",
    "colorScienceMode":         "davinciYRGBColorManagedv2"
  },
  "ingest_path": "/mnt/footage/2026-04-06_shoot",
  "timeline_name": "v1_assembly",
  "powergrade_drx": "/opt/OS/assets/resolve/lyfe_spectrum.drx",
  "markers": [],
  "render_presets": [
    {"name": "YouTube 1080p",  "out_dir": "/mnt/renders/yt",  "filename": "vsl_yt"},
    {"name": "Vertical 1080",  "out_dir": "/mnt/renders/ig",  "filename": "vsl_ig"},
    {"name": "Square 1080",    "out_dir": "/mnt/renders/li",  "filename": "vsl_li"}
  ]
}
```

**Script:** `/opt/OS/scripts/resolve/bootstrap_project.py` (the recipe above).

**Verification:** after script run, open Resolve, confirm project exists,
timeline has clips, render queue has 3 jobs.

### Pattern 2 — Headless render dispatch

**When:** Antony finishes editing and wants to walk away while Resolve
renders 5 aspect ratios.

**Script:** `/opt/OS/scripts/resolve/dispatch_renders.py` — loads project,
ensures all render presets are queued, calls `StartRendering` non-interactive,
polls and logs each job to Neon.

**Verification:** Neon `resolve_render_log` table has one row per job
transitioning queued → rendering → complete.

### Pattern 3 — Marker extraction for content tracking

**When:** Antony marks beats in the VSL with colored markers; EOS reads
them to populate the Notion content tracker.

**Script:** `/opt/OS/scripts/resolve/extract_markers.py` — opens project,
walks `timeline.GetMarkers()`, writes JSON, syncs to Notion via existing
publisher.

**Verification:** Notion content tracker shows beat-by-beat structure
with timecodes.

### Pattern 4 — House look application

**When:** A client deliverable for Empyrean Studio needs the agreed
house grade applied to every shot in a track.

**Script:** `/opt/OS/scripts/resolve/apply_house_look.py` — loads project,
iterates `timeline.GetItemListInTrack("video", 1)`, calls
`album.ApplyGradeFromDRX(path, 0, [tlitem])` per clip.

**Verification:** open Color page, every node tree shows the imported
PowerGrade structure.

### Pattern 5 — Project template library

**When:** Antony or a future Empyrean Studio editor wants to start a new
project from a vetted starting point.

**Implementation:** keep `.drp` (Resolve project export) files in
`/opt/OS/assets/resolve/templates/`; script `pm.ImportProject(path, name)`
to instantiate.

**Verification:** new project appears in Project Manager, contains the
template's settings/timelines/render presets.

### Pattern 6 — Studio probe

**When:** A script runs on a machine that may have free or Studio Resolve.

**Script:**
```python
def is_studio(resolve):
    return "Studio" in resolve.GetProductName()
if not is_studio(resolve):
    log("downgrading: free Resolve, skipping Fusion + Neural Engine steps")
```

### Pattern 7 — Tmux + Resolve render worker

Run Resolve under `xvfb-run` inside a pinned tmux session so the EOS
render worker survives SSH disconnects:

```bash
tmux -L eos new-session -d -s resolve -x 220 -y 50 \
  'xvfb-run -a /opt/resolve/bin/resolve'
```

Then run dispatch scripts from another pane against the same Resolve.

### Pattern 8 — Pre-flight smoke test before any deploy

```python
import DaVinciResolveScript as dvr
resolve = dvr.scriptapp("Resolve")
assert resolve, "Resolve not running"
assert "Studio" in resolve.GetProductName(), "Free Resolve, scripting limited"
pm = resolve.GetProjectManager()
assert pm, "ProjectManager unavailable"
print("RESOLVE OK", resolve.GetVersionString())
```

## Gotchas

The full failure catalog. Add to this list every time a new failure mode
bites EOS in production.

- **`scriptapp("Resolve")` returns `None`** — Resolve not running, or
  `RESOLVE_SCRIPT_LIB` env var missing/wrong arch. Verify env first.
- **`import DaVinciResolveScript` ImportError** — `RESOLVE_SCRIPT_API`
  not on `PYTHONPATH`. Export it before launching the interpreter.
- **Free vs Studio silent degradation** — Fusion scripting and Neural
  Engine APIs return `None` on free with no warning. Always probe
  `resolve.GetProductName()` and branch.
- **Stringly-typed settings** — `SetSetting("timelineFrameRate", 23.976)`
  fails; `SetSetting("timelineFrameRate", "23.976")` works. Wrap with
  `str()` defensively.
- **Frame rate sticky after first timeline** — set framerate on the empty
  project, BEFORE creating the timeline. After: silently rejected.
- **`SetSetting` returns `False`** — many keys are read-only or unknown;
  always check the return.
- **`AppendToTimeline` ignores playhead** — appends to V1/A1 only. Use
  the dict form with `trackIndex` and `recordFrame` for explicit placement.
- **`mp.AppendToTimeline(item)` (single arg)** — works but inefficient;
  pass a list to batch.
- **Object handles invalidate on `LoadProject`** — re-fetch every handle
  after switching projects.
- **`pm.LoadProject(name)` returns `None`** — wrong folder. `GotoRootFolder`
  + walk first, OR remember the folder.
- **No exceptions** — every call can return `None` / `False`. Wrap with a
  `_check(call, label)` helper or you will lose work.
- **Render queue persists** — old jobs from yesterday's session are still
  there. Call `DeleteAllRenderJobs` before adding new ones if you want
  a clean queue.
- **Render preset name typo** — fails with `False` from `LoadRenderPreset`;
  enumerate via `GetRenderPresetList` first.
- **`StartRendering` returns `False`** — another render in progress, or
  empty job list, or invalid IDs. Check `IsRenderingInProgress` first.
- **Polling `IsRenderingInProgress` too fast** — degrades render speed.
  1–2s sleep is the sweet spot.
- **Modal dialog freezes script** — unsaved-changes prompt, missing media
  warning, or license expired. The script hangs forever. Always launch
  Resolve fresh and dismiss prompts before scripting.
- **macOS dylib arch mismatch** — Intel Python with ARM Resolve dylib
  raises a cryptic libc error. Match the arch.
- **Linux: not Rocky 8** — official support is Rocky 8.6/8.8. Other
  distros (Ubuntu, Debian) work via AppImage but Blackmagic does not
  test them; expect graphics driver pain.
- **Headless Linux render needs `xvfb-run`** — Resolve refuses to start
  without an X server. There is no true CLI mode.
- **`ApplyGradeFromDRX` with mode 0/1/2** — 0 = node graph, 1 = display
  LUT, 2 = entire grade. Use 0 for PowerGrades; mode confusion silently
  applies the wrong thing.
- **Marker color string typo** — `"blue"` (lowercase) silently fails;
  `"Blue"` works. The 16 valid colors are documented above.
- **`AddMarker` duration units** — frames, not seconds. `1` means
  one-frame marker; `0` is invalid.
- **Frame numbers vs timecodes** — most APIs are frames; only a few
  (`SetCurrentTimecode`) take TC strings. Convert with explicit math.
- **Save before quit, always** — `Quit()` does NOT auto-save. `pm.SaveProject()`
  first.
- **Collaboration locks** — bin/clip locked by another user → mutations
  silently no-op. Use single-writer scripts.
- **Postgres default password `DaVinci`** — change it. Default install is
  insecure on any networked machine.
- **Project DB version mismatch** — opening a 19.1 project on 18 fails
  with a confusing error. Pin Resolve versions across collab seats.
- **Auto-backup window** — can mask script-mutated state. Disable
  auto-save during long script runs if precise timing matters.
- **Fusion comp script API is different** — `GetFusionCompByIndex(1)`
  returns a comp object whose methods (`AddTool`, `FindTool`) are NOT in
  the Resolve scripting README. Reference the WeSuckLess wiki and the
  Fusion lua docs.
- **`comp.AddTool(name, x, y)` x/y are tile coordinates** — not pixels.
  Use multiples of 32 for clean layouts.
- **Setting Fusion tool inputs** — `tool.SetInput("InputName", value, frame)`;
  the input name is case-sensitive and tool-specific (`StyledText` for
  Text+, `Filename` for Loader).
- **`ti.SetLUT(node, path)` requires LUT in Resolve's LUT folders** — copy
  to `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/`
  first, then `project.RefreshLUTList()`.
- **CDL keys** — `SetCDL({"NodeIndex": 1, "Slope": "1.0 1.0 1.0", ...})` —
  values are space-separated strings, not arrays.
- **`TranscribeAudio` is async** — call returns immediately; the result
  appears later as markers. Poll `GetMarkers()` until they appear, with a
  timeout, or use Workspace → Audio Transcription progress UI.
- **`SetRenderSettings` keys are case-sensitive** — `targetDir` fails;
  `TargetDir` works.
- **Forward slashes vs backslashes** — Linux/macOS use `/`, Windows use `\`.
  No normalization.
- **`UniqueFilenameStyle` 0 vs 1** — 0 prefix, 1 suffix; default 0. Get
  this wrong and renders all share the same name with no version suffix.
- **`MarkIn`/`MarkOut`** in render settings — frame offsets from timeline
  start, not source frames.
- **Render cache eats disk** — clear it periodically; scripts can run
  `Playback → Delete Render Cache → All` only via UI, not API. Manage at
  the filesystem layer if needed.
- **Network drive ingestion** — Resolve indexes media on add; large NAS
  ingests can take minutes per thousand clips. Stage to local SSD first
  if possible.
- **BRAW debayer settings** — set per-clip in Camera Raw panel; not yet
  fully exposed in script. Workaround: save a Camera Raw decode preset
  in the GUI and apply via the project's "Decode using" setting.
- **Smart Bins are dynamic** — script-querying via folder API does not see
  Smart Bin contents directly; they are filters, not folders.
- **Project DB backups** — Postgres collab requires `pg_dump`-based backup;
  DiskDB (sqlite) projects need filesystem snapshot. Build EOS backup
  script accordingly.
- **`Quit()` mid-render corrupts the queue** — always `StopRendering()`
  first, then `Quit()`.

End of best_practices.md.
