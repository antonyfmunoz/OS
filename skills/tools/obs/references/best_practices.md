# obs (OBS Studio + obs-websocket) — Creator-Level Best Practices
Source: github.com/obsproject/obs-studio, github.com/obsproject/obs-websocket, obsproject.com/kb, NVIDIA NVENC OBS guide, OBS forums
API Version: obs-websocket v5.x (rpcVersion 1) over WebSocket port 4455
SDK Version: obsws-python 1.7+, obs-websocket-js 5.x, OBS Studio 31.x
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

obs-websocket v5 uses an HMAC-SHA256 challenge-response handshake bound to
the WebSocket connection lifetime. There is no bearer token, no API key,
no OAuth — auth is **per-socket** and the result is implicit on every
subsequent request frame.

Protocol sequence:

1. Client opens a WebSocket to `ws://host:4455` (or `wss://` if reverse-proxied).
2. Server immediately sends **Hello** (op 0):
   ```json
   {"op":0,"d":{"obsWebSocketVersion":"5.5.0","rpcVersion":1,
                 "authentication":{"challenge":"<b64>","salt":"<b64>"}}}
   ```
   If auth is disabled, the `authentication` field is absent.
3. Client computes:
   ```
   secret      = base64(sha256(password + salt))
   auth_string = base64(sha256(secret + challenge))
   ```
4. Client sends **Identify** (op 1):
   ```json
   {"op":1,"d":{"rpcVersion":1,"authentication":"<auth_string>",
                 "eventSubscriptions":33}}
   ```
   `eventSubscriptions` is a bitmask — `0` mutes events, `(1<<0 | 1<<5)`
   subscribes to General + Inputs, `1023` subscribes to all base categories.
5. Server replies **Identified** (op 2). Connection is now hot.
6. Subsequent **Request** frames (op 6) carry `requestType`, `requestId`
   (client-chosen, used to correlate the response), and `requestData`.

EOS consequences:
- Store `OBS_WS_PASSWORD` in `eos_ai/.env`. Never commit.
- Bind OBS WebSocket to `127.0.0.1` only. Tunnel via Tailscale for
  remote agents — never expose 4455 to the public internet.
- The connection is stateful; reconnect logic must redo Hello/Identify.
- A wrong password produces close code 4009 ("Authentication Failed"),
  not a request error. Detect on the WebSocket close handler.

## Core Operations with Exact Signatures

All operations are JSON-RPC frames. Below are the request types EOS will
use, grouped by surface, with their request data fields and response
fields. Names match the v5 protocol document exactly.

### General

```
GetVersion                       → obsVersion, obsWebSocketVersion, rpcVersion,
                                    availableRequests[], supportedImageFormats[],
                                    platform, platformDescription
GetStats                         → cpuUsage, memoryUsage, availableDiskSpace,
                                    activeFps, averageFrameRenderTime,
                                    renderSkippedFrames, renderTotalFrames,
                                    outputSkippedFrames, outputTotalFrames,
                                    webSocketSessionIncomingMessages,
                                    webSocketSessionOutgoingMessages
BroadcastCustomEvent             ← eventData {object}
CallVendorRequest                ← vendorName, requestType, requestData
GetHotkeyList                    → hotkeys[]
TriggerHotkeyByName              ← hotkeyName, contextName?
Sleep                            ← sleepMillis | sleepFrames  (batch only)
```

### Config / Profile / Scene Collection

```
GetPersistentData                ← realm, slotName        → slotValue
SetPersistentData                ← realm, slotName, slotValue
GetSceneCollectionList           → currentSceneCollectionName, sceneCollections[]
SetCurrentSceneCollection        ← sceneCollectionName
CreateSceneCollection            ← sceneCollectionName
GetProfileList                   → currentProfileName, profiles[]
SetCurrentProfile                ← profileName
CreateProfile                    ← profileName
RemoveProfile                    ← profileName
GetProfileParameter              ← parameterCategory, parameterName
SetProfileParameter              ← parameterCategory, parameterName, parameterValue
GetVideoSettings                 → fpsNumerator, fpsDenominator, baseWidth,
                                    baseHeight, outputWidth, outputHeight
SetVideoSettings                 ← fpsNumerator?, fpsDenominator?, baseWidth?,
                                    baseHeight?, outputWidth?, outputHeight?
GetStreamServiceSettings         → streamServiceType, streamServiceSettings
SetStreamServiceSettings         ← streamServiceType, streamServiceSettings
GetRecordDirectory               → recordDirectory
SetRecordDirectory               ← recordDirectory
```

### Sources (generic)

```
GetSourceActive                  ← sourceName              → videoActive, videoShowing
GetSourceScreenshot              ← sourceName, imageFormat, imageWidth?,
                                    imageHeight?, imageCompressionQuality?
                                                          → imageData (data URL)
SaveSourceScreenshot             ← sourceName, imageFormat, imageFilePath,
                                    imageWidth?, imageHeight?, imageCompressionQuality?
```

### Inputs

```
GetInputList                     ← inputKind?              → inputs[]
GetInputKindList                 ← unversioned?            → inputKinds[]
GetSpecialInputs                 → desktop1, desktop2, mic1, mic2, mic3, mic4
CreateInput                      ← sceneName|sceneUuid, inputName, inputKind,
                                    inputSettings?, sceneItemEnabled?
                                                          → sceneItemId
RemoveInput                      ← inputName|inputUuid
SetInputName                     ← inputName|inputUuid, newInputName
GetInputDefaultSettings          ← inputKind              → defaultInputSettings
GetInputSettings                 ← inputName|inputUuid    → inputSettings, inputKind
SetInputSettings                 ← inputName|inputUuid, inputSettings, overlay?
GetInputMute                     ← inputName              → inputMuted
SetInputMute                     ← inputName, inputMuted
ToggleInputMute                  ← inputName              → inputMuted
GetInputVolume                   ← inputName              → inputVolumeMul, inputVolumeDb
SetInputVolume                   ← inputName, inputVolumeMul? | inputVolumeDb?
GetInputAudioBalance             ← inputName              → inputAudioBalance
SetInputAudioBalance             ← inputName, inputAudioBalance
GetInputAudioSyncOffset          ← inputName              → inputAudioSyncOffset
SetInputAudioSyncOffset          ← inputName, inputAudioSyncOffset
GetInputAudioMonitorType         ← inputName              → monitorType
SetInputAudioMonitorType         ← inputName, monitorType
GetInputAudioTracks              ← inputName              → inputAudioTracks
SetInputAudioTracks              ← inputName, inputAudioTracks {1..6: bool}
GetInputPropertiesListPropertyItems ← inputName, propertyName → propertyItems[]
PressInputPropertiesButton       ← inputName, propertyName
```

### Scenes

```
GetSceneList                     → currentProgramSceneName, currentProgramSceneUuid,
                                    currentPreviewSceneName, currentPreviewSceneUuid,
                                    scenes[]
GetGroupList                     → groups[]
GetCurrentProgramScene           → currentProgramSceneName, currentProgramSceneUuid
SetCurrentProgramScene           ← sceneName | sceneUuid
GetCurrentPreviewScene           → currentPreviewSceneName, currentPreviewSceneUuid
SetCurrentPreviewScene           ← sceneName | sceneUuid
CreateScene                      ← sceneName              → sceneUuid
RemoveScene                      ← sceneName | sceneUuid
SetSceneName                     ← sceneName | sceneUuid, newSceneName
GetSceneSceneTransitionOverride  ← sceneName              → transitionName, transitionDuration
SetSceneSceneTransitionOverride  ← sceneName, transitionName?, transitionDuration?
```

### Scene items

```
GetSceneItemList                 ← sceneName              → sceneItems[]
GetGroupSceneItemList            ← sceneName              → sceneItems[]
GetSceneItemId                   ← sceneName, sourceName, searchOffset?
                                                          → sceneItemId
GetSceneItemSource               ← sceneName, sceneItemId → sourceName, sourceUuid
CreateSceneItem                  ← sceneName, sourceName, sceneItemEnabled?
                                                          → sceneItemId
RemoveSceneItem                  ← sceneName, sceneItemId
DuplicateSceneItem               ← sceneName, sceneItemId, destinationSceneName?
GetSceneItemTransform            ← sceneName, sceneItemId → sceneItemTransform
SetSceneItemTransform            ← sceneName, sceneItemId, sceneItemTransform
GetSceneItemEnabled              ← sceneName, sceneItemId → sceneItemEnabled
SetSceneItemEnabled              ← sceneName, sceneItemId, sceneItemEnabled
GetSceneItemLocked               ← sceneName, sceneItemId → sceneItemLocked
SetSceneItemLocked               ← sceneName, sceneItemId, sceneItemLocked
GetSceneItemIndex                ← sceneName, sceneItemId → sceneItemIndex
SetSceneItemIndex                ← sceneName, sceneItemId, sceneItemIndex
GetSceneItemBlendMode            ← sceneName, sceneItemId → sceneItemBlendMode
SetSceneItemBlendMode            ← sceneName, sceneItemId, sceneItemBlendMode
```

### Filters

```
GetSourceFilterKindList          → sourceFilterKinds[]
GetSourceFilterList              ← sourceName              → filters[]
GetSourceFilterDefaultSettings   ← filterKind              → defaultFilterSettings
CreateSourceFilter               ← sourceName, filterName, filterKind, filterSettings?
RemoveSourceFilter               ← sourceName, filterName
SetSourceFilterName              ← sourceName, filterName, newFilterName
GetSourceFilter                  ← sourceName, filterName → filterEnabled, filterIndex,
                                                              filterKind, filterSettings
SetSourceFilterIndex             ← sourceName, filterName, filterIndex
SetSourceFilterSettings          ← sourceName, filterName, filterSettings, overlay?
SetSourceFilterEnabled           ← sourceName, filterName, filterEnabled
```

### Transitions / Studio Mode

```
GetTransitionKindList            → transitionKinds[]
GetSceneTransitionList           → currentSceneTransitionName,
                                    currentSceneTransitionUuid,
                                    currentSceneTransitionKind, transitions[]
GetCurrentSceneTransition        → transitionName, transitionUuid, transitionKind,
                                    transitionFixed, transitionDuration,
                                    transitionConfigurable, transitionSettings
SetCurrentSceneTransition        ← transitionName
SetCurrentSceneTransitionDuration ← transitionDuration
SetCurrentSceneTransitionSettings ← transitionSettings, overlay?
GetCurrentSceneTransitionCursor  → transitionCursor
TriggerStudioModeTransition
SetTBarPosition                  ← position, release?
GetStudioModeEnabled             → studioModeEnabled
SetStudioModeEnabled             ← studioModeEnabled
```

### Outputs (recording, streaming, virtual cam, replay buffer)

```
GetVirtualCamStatus              → outputActive
ToggleVirtualCam                 → outputActive
StartVirtualCam
StopVirtualCam

GetReplayBufferStatus            → outputActive
ToggleReplayBuffer               → outputActive
StartReplayBuffer
StopReplayBuffer
SaveReplayBuffer
GetLastReplayBufferReplay        → savedReplayPath

GetRecordStatus                  → outputActive, outputPaused, outputTimecode,
                                    outputDuration, outputBytes
ToggleRecord                     → outputActive
StartRecord
StopRecord                       → outputPath
ToggleRecordPause
PauseRecord
ResumeRecord
SplitRecordFile                  (v5.5+, splits without stopping)
CreateRecordChapter              ← chapterName             (fragmented MP4)

GetStreamStatus                  → outputActive, outputReconnecting, outputTimecode,
                                    outputDuration, outputCongestion, outputBytes,
                                    outputSkippedFrames, outputTotalFrames
ToggleStream                     → outputActive
StartStream
StopStream
SendStreamCaption                ← captionText            (608 closed-captions)

GetOutputList                    → outputs[]
GetOutputStatus                  ← outputName             → outputActive, ...
ToggleOutput                     ← outputName             → outputActive
StartOutput                      ← outputName
StopOutput                       ← outputName
GetOutputSettings                ← outputName             → outputSettings
SetOutputSettings                ← outputName, outputSettings
```

### Media inputs (clips/playlists)

```
GetMediaInputStatus              ← inputName              → mediaState, mediaDuration,
                                                              mediaCursor
SetMediaInputCursor              ← inputName, mediaCursor
OffsetMediaInputCursor           ← inputName, mediaCursorOffset
TriggerMediaInputAction          ← inputName, mediaAction
   # OBS_WEBSOCKET_MEDIA_INPUT_ACTION_{NONE,PLAY,PAUSE,STOP,RESTART,NEXT,PREVIOUS}
```

## Pagination Patterns

N/A. The protocol has no paginated lists. `GetSceneList`, `GetInputList`,
`GetSourceFilterList`, `GetSceneItemList`, etc. return the complete set in
a single response. The largest practical list (a busy scene collection
with hundreds of inputs) is still well under any payload limit. There is
no cursor, no `nextPageToken`. Iterate by calling once and walking the
returned array.

## Rate Limits

There are no documented quotas. obs-websocket runs in-process inside OBS
and dispatches each request through the same internal API as the GUI.
Practical bounds:

- **Per-frame budget** — OBS render thread targets 16.6 ms (60 fps).
  Heavy synchronous requests (`SetVideoSettings`, `CreateInput` for a
  Browser source) can stall a frame. Don't fire them inside a tight loop.
- **WebSocket message rate** — the asio-based server handles tens of
  thousands of small frames/sec on localhost. The bottleneck is OBS's
  request dispatch lock, not the socket.
- **`SetInputSettings` storms** — updating a text source 60 times/sec
  triggers a re-render of that source every call. Coalesce updates to
  ≤10/sec for lower thirds.
- **Screenshots** — `GetSourceScreenshot` reads back GPU memory; budget
  ~30–80 ms each. Don't poll faster than ~5/sec.

## Error Codes and Recovery

Request responses include `requestStatus.code` (integer) and
`requestStatus.comment`. Codes are documented in the protocol enum.

| Code | Name | Cause | Recovery |
|---|---|---|---|
| 100 | Success | Request handled | n/a |
| 204 | NoRecordToStop | Stop with no recording active | check `GetRecordStatus` first |
| 205 | NoReplayBufferToSave | Buffer not running | start it first |
| 300 | MissingRequestField | Required field missing | fix request payload |
| 301 | MissingRequestData | `requestData` absent | add it |
| 400 | InvalidRequestField | Bad type/value | check field types |
| 401 | InvalidRequestFieldType | Wrong JSON type | cast properly |
| 402 | RequestFieldOutOfRange | Number out of range | clamp |
| 403 | RequestFieldEmpty | Empty string/array | provide value |
| 406 | TooManyRequestFields | Mutually exclusive fields | pass only one |
| 500 | OutputRunning | Tried to start already-running output | check status |
| 501 | OutputNotRunning | Tried to stop idle output | check status |
| 502 | OutputPaused | Pause-toggle on paused output | resume first |
| 503 | OutputNotPaused | Resume on non-paused | check state |
| 504 | OutputDisabled | Output not configured (e.g. record) | configure in OBS settings |
| 600 | ResourceNotFound | Bad scene/input/filter name | refresh names |
| 601 | ResourceAlreadyExists | Create on duplicate name | use unique name |
| 602 | InvalidResourceType | Wrong kind | check `GetInputKindList` |
| 603 | NotEnoughResources | OBS-internal limit | retry, check log |
| 604 | InvalidResourceState | e.g. set transform on locked item | unlock first |
| 605 | InvalidInputKind | Unknown input kind | match platform |
| 606 | ResourceNotConfigurable | Filter/source can't accept setting | skip |
| 700 | RequestProcessingFailed | OBS internal error | read OBS log |
| 701 | CannotAct | Action refused (e.g. start record with no track) | configure OBS |

WebSocket close codes (connection-level):

| Code | Meaning |
|---|---|
| 4000 | Don't disconnect (sentinel) |
| 4002 | Unknown opcode |
| 4003 | Not Identified yet |
| 4004 | Already Identified |
| 4005 | Wrong rpcVersion |
| 4006 | Unsupported feature |
| 4009 | Authentication failed |
| 4010 | Session invalidated |

Recovery recipe for a hung connection:

```python
import obsws_python as obs, time
def connect():
    while True:
        try:
            cl = obs.ReqClient(host='127.0.0.1', port=4455,
                               password=os.getenv('OBS_WS_PASSWORD'),
                               timeout=3)
            cl.get_version()
            return cl
        except Exception as e:
            print(f'OBS reconnect: {e}'); time.sleep(2)
```

## SDK Idioms

**obsws-python** (Python — preferred for EOS):

```python
import obsws_python as obs
cl = obs.ReqClient(host='127.0.0.1', port=4455, password=PWD)

# Snake-case methods, pascal-case requestType
cl.set_current_program_scene('Live')          # SetCurrentProgramScene
cl.get_scene_list().scenes                    # list[dict]
cl.set_input_settings('LowerThird',
                     {'text': 'Topic'}, True)

# Events client is separate
ev = obs.EventClient(host='127.0.0.1', port=4455, password=PWD)
def on_current_program_scene_changed(data):
    print('switched to', data.scene_name)
ev.callback.register(on_current_program_scene_changed)
```

**obs-websocket-js** (Node — for browser overlays):

```js
import OBSWebSocket from 'obs-websocket-js';
const obs = new OBSWebSocket();
await obs.connect('ws://127.0.0.1:4455', process.env.OBS_WS_PASSWORD,
                  {rpcVersion: 1});
await obs.call('SetCurrentProgramScene', {sceneName: 'Live'});
obs.on('CurrentProgramSceneChanged', d => console.log(d.sceneName));
```

Rules:

1. One client per process — connect once, reuse. The handshake is the
   expensive part.
2. Wrap every call in a try/except. OBS can be closed at any time and the
   socket goes with it.
3. Cache UUIDs at startup. Names change, UUIDs don't.
4. Use the events client for state-changes, never poll. `GetStats` every
   second to draw a graph is wasteful and creates dispatch contention.
5. Prefer batched requests (`Request Batch`, op 8) when issuing >3 calls
   together — it's atomic and avoids interleaving with user clicks.

## Anti-Patterns

- **Polling `GetCurrentProgramScene` in a loop** — subscribe to the
  `CurrentProgramSceneChanged` event instead. The event surface exists.
- **Setting bitrate via `SetProfileParameter`** mid-stream — encoder
  reads the param at start. Stop and restart the output to apply.
- **Creating a Browser Source per overlay update** — sources are heavy.
  Create one and `SetInputSettings` to point at a new URL.
- **Recording to MP4** — corrupts on crash. Use MKV, remux later.
- **`overlay=False` on text updates** — wipes font/color/alignment.
- **Hardcoding `inputName`** in long-running scripts — humans rename
  things. Resolve to UUID at boot.
- **Driving WebSocket over the public internet** — no TLS by default.
  Use Tailscale or wss reverse proxy.
- **Running OBS as root** for "convenience" — file permissions on
  recordings then lock out the editor. Run as the regular user.
- **Stacking heavy filters on every source** — Background Removal +
  Color Correct + LUT + Scale on a 4K cam will encoder-overload a small
  GPU. Apply on the scene, not the source, when possible.
- **Switching scene collections programmatically during a live** — it
  unloads/reloads every source. Stage everything in one collection.

## Data Model

The OBS object graph (paralleling tmux's server-as-truth):

```
OBS process
├── Scene collection         (the "save file" — switching reloads everything)
│   ├── Scene                (named canvas)
│   │   └── Scene item       (instance of a source with transform/visibility)
│   │       └── Source       (input or group)
│   │           └── Filter chain
│   ├── Transition           (named, with duration + settings)
│   └── Group                (special scene used as a folder inside other scenes)
├── Profile                  (encoder settings, output paths, hotkeys)
│   ├── Stream service       (Twitch / YouTube / Custom)
│   ├── Output configs       (Simple vs Advanced; recording + streaming separate)
│   └── Video settings       (base canvas, output canvas, fps)
├── Hotkey table
└── obs-websocket session    (per WebSocket client)
```

Key invariants:

- A **source** is referenced by `inputUuid` (stable) and `inputName`
  (mutable). Two scenes can hold scene items pointing at the same source —
  changes to source settings affect both.
- A **scene item** is local to its scene. The same source can be a scene
  item in N scenes, each with a different transform.
- **Transforms** include positionX/Y, scaleX/Y, rotation, sourceWidth/Height,
  width/height, alignment, boundsType/boundsAlignment/boundsWidth/Height,
  cropTop/Bottom/Left/Right.
- **Groups** are technically scenes with `is_group=true`. They show up
  in `GetGroupList`, not `GetSceneList`.
- **Special inputs** (`desktop1`, `mic1`, etc.) are global audio sources
  that exist outside the scene graph. They're always live.

## Webhooks and Events

Events are pushed from server to client over the same WebSocket as
**Event** frames (op 5). Categories are bit-flagged in `eventSubscriptions`
during Identify:

| Bit | Category | Notable events |
|---|---|---|
| 0 (1) | General | ExitStarted, VendorEvent, CustomEvent |
| 1 (2) | Config | CurrentSceneCollectionChanging/Changed, ProfileChanging/Changed |
| 2 (4) | Scenes | SceneCreated, SceneRemoved, SceneNameChanged, CurrentProgramSceneChanged, CurrentPreviewSceneChanged, SceneListChanged |
| 3 (8) | Inputs | InputCreated, InputRemoved, InputNameChanged, InputActiveStateChanged, InputShowStateChanged, InputMuteStateChanged, InputVolumeChanged, InputAudioBalanceChanged, InputAudioSyncOffsetChanged, InputAudioTracksChanged, InputAudioMonitorTypeChanged, InputVolumeMeters |
| 4 (16) | Transitions | CurrentSceneTransitionChanged, CurrentSceneTransitionDurationChanged, SceneTransitionStarted, SceneTransitionEnded, SceneTransitionVideoEnded |
| 5 (32) | Filters | SourceFilterListReindexed, SourceFilterCreated, SourceFilterRemoved, SourceFilterNameChanged, SourceFilterEnableStateChanged, SourceFilterSettingsChanged |
| 6 (64) | Outputs | StreamStateChanged, RecordStateChanged, RecordFileChanged, ReplayBufferStateChanged, VirtualcamStateChanged, ReplayBufferSaved |
| 7 (128) | SceneItems | SceneItemCreated, SceneItemRemoved, SceneItemListReindexed, SceneItemEnableStateChanged, SceneItemLockStateChanged, SceneItemSelected, SceneItemTransformChanged |
| 8 (256) | MediaInputs | MediaInputPlaybackStarted, MediaInputPlaybackEnded, MediaInputActionTriggered |
| 9 (512) | UI | StudioModeStateChanged, ScreenshotSaved |
| 10 (1024) | High-volume | InputVolumeMeters (~60 Hz; only enable if you actually visualize) |

Default subscription is `33` (General + Inputs basic). Compute as
`Scenes | Outputs | SceneItems = 4 | 64 | 128 = 196` for a typical
broadcast controller.

## Limits

- **Canvas resolution**: any positive integer width/height up to GPU
  texture limits (typically 16384). Practically: 1920x1080 base, 1920x1080
  output for streaming; 3840x2160 base only if you need to crop pristine.
- **FPS**: integer or rational. 60 max for sane streaming. NVENC supports
  120/144 for capture but few platforms accept it.
- **Audio tracks**: 6. Each track has its own bitrate setting in Advanced.
- **Outputs**: one streaming output, one recording output (without plugins),
  one virtual cam, one replay buffer. Plugins (`obs-multi-rtmp`,
  `Source Record`) add more.
- **Sources per scene**: no hard cap. Performance degrades with browser
  sources past ~10 (each is a CEF instance).
- **Filter chain depth**: no hard cap. Each filter is a render pass.
- **WebSocket clients**: dozens are fine; each gets its own session.
- **Recording file size**: limited by filesystem (FAT32 = 4 GB; use NTFS/ext4).
- **Replay buffer length**: bounded by RAM. ~10 MB/sec per 1080p60 NVENC track.

## Cost Model

OBS itself is free. The "cost" is hardware:

- **CPU** — x264 veryfast at 1080p60 ≈ 30–50% of an 8-core modern CPU.
  Slower presets (faster, fast, medium) double cost per step.
- **GPU** — NVENC adds ~2–5% GPU load on RTX cards. AV1 NVENC is ~10%.
  Browser sources each cost 50–200 MB VRAM and 1–3% GPU.
- **RAM** — base OBS ~500 MB. Each source ~10–80 MB. Replay buffer
  proportional to length × bitrate.
- **Disk** — recording at 25 Mbps = ~190 MB/min = ~11 GB/hr. Multi-hour
  Initiate Arena lives need 50 GB+ free.
- **Bandwidth** — streaming at 6000 kbps = ~2.7 GB/hr upload. Multi-RTMP
  multiplies by destination count.

Stream service costs (for north-star context):
- Twitch / YouTube / Kick / Rumble — free ingest.
- Restream.io — paid above 2 destinations.
- Self-hosted RTMP (nginx-rtmp, MediaMTX) — VPS bandwidth only.

## Version Pinning

- **OBS Studio**: 31.x is current as of 2026-04. New features land in
  point releases (28.x added Apple Silicon native, 29.x added AV1, 30.x
  added Intel HEVC, 31.x added WHIP and improved fragmented MP4).
- **obs-websocket**: bundled with OBS since 28.x. Standalone plugin still
  exists for legacy v4 (port 4444) but EOS uses **only v5** (port 4455).
- **rpcVersion**: currently `1`. The Identify handshake negotiates;
  mismatched versions get close code 4005.
- **obsws-python**: pin `obsws-python>=1.7,<2` in requirements.txt. The
  1.x line tracks v5 protocol stably.
- **obs-websocket-js**: pin `^5.0.0`. The 4.x line is incompatible.

Pin OBS at a Long-Term-style version on the production rig — don't
auto-update mid-launch week. Test scene collection compatibility on a
secondary profile before upgrading.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

OBS Studio was built around a single radical decision: **the canvas is
authoritative, the encoder is downstream**. Almost every other broadcast
tool built around the encoder first (XSplit, vMix early days) and made
the visual layer a slave to it. OBS inverted this. The canvas is rendered
to a GPU texture every frame; encoders are independent consumers that
read frames from a shared queue. This is why you can record and stream
simultaneously with different codecs, why you can have multiple outputs,
why the virtual camera "just works" — they're all readers on the same
upstream texture.

The tradeoff: OBS will gladly let you build a scene collection your
hardware can't render. There is no automatic quality negotiation. If
you put a 4K browser source full of WebGL on a GTX 1060 and try to
encode 1080p60 NVENC, it'll drop frames, flash the red square, and keep
going. The operator is expected to read the stats and tune.

The second design choice: **plugins talk to the same internal API as the
GUI**. obs-websocket is not a special remote API — it's a thin RPC veneer
over `obs_frontend_*` and `obs_source_*` calls. This is why the protocol
covers nearly the entire GUI surface: the plugin author just exposed the
verbs that already existed. It's also why some things are awkward
(e.g. encoder bitrate is a profile parameter, not a first-class request)
— the protocol matches OBS's internal model, warts and all.

## Problem-Solution Map and Hidden Capabilities

| Problem | Solution |
|---|---|
| Audio out of sync with video | per-input Audio Sync Offset (positive ms = delay audio) |
| Stream looks soft on Twitch | bitrate too low for resolution; drop to 720p60 or raise to 8000 kbps |
| CPU pegged at 100% | switch x264 → NVENC, or use a faster preset |
| Game audio bleeding into mic | Audio Monitoring "Monitor Off" on game capture, "Monitor and Output" on mic if you must hear yourself |
| Mic picks up keyboard | NVIDIA Broadcast or RNNoise filter on the mic source |
| Need a quick still on stream | Image Slide Show source with one image; toggle visibility |
| Need rotating LinkedIn-style banner | Browser Source pointing at a small HTML page that rotates text — animations live in CSS, not OBS |
| Scene won't transition | Studio Mode is on; hit the Transition button or call `TriggerStudioModeTransition` |
| File too big | drop bitrate or use HEVC NVENC CQP |
| Recording out of sync after long session | enable "Force GPU as Render Device" + "Auto-remux to MP4" |
| Want to capture only one app on Linux | PipeWire screen capture with portal selector (X11 fallback uses XSHM and is laggy) |

Hidden capabilities most users miss:

- **Source Record plugin** — record any source (not just program) to its
  own file. Perfect for isolated camera angles to re-edit later.
- **Browser source interaction** — right-click → Interact lets you click
  inside a Browser source as if it were a real browser tab.
- **Custom Browser Docks** — dock any URL inside the OBS UI. Useful for
  Twitch chat, alerts dashboards, EOS Discord channel.
- **Scripting (Lua/Python)** — `obs-scripting` lets a script live inside
  OBS without WebSocket. Useful for hotkey-bound macros.
- **Scene as a source** — drag a scene into another scene to nest it.
  Render once, reuse everywhere.
- **Decklink output** — send program out an SDI card as an isolated
  feed. Multi-camera studio territory.
- **`obs --startrecording --startreplaybuffer --collection X --profile Y`**
  — full CLI launch flags for unattended startup.
- **Source toolbar** — one-click access to common per-source actions
  (refresh browser source, restart media).
- **Color formats**: NV12 (default), I420, P010 (10-bit HDR), RGB. P010
  + HEVC = HDR recording for color grading.

## Operational Behavior and Edge Cases

- **Crash recovery** — OBS writes a crash log to the log directory and
  the scene collection survives because it was last-saved on a normal
  exit. If it crashed mid-edit, your last 30 seconds of arrangement
  changes are gone. Save scene collections explicitly before risky edits.
- **Auto-save** — none in stock OBS. Build a habit or a script.
- **Fragmented MP4** — survives crashes because the moov atom is
  written incrementally. Only available with hardware encoders + a
  flag in Advanced output. Use this if you can't tolerate MKV.
- **GPU device loss** (driver crash) — OBS shows a black canvas until
  restart. Use NVIDIA studio drivers, not Game Ready, on production rig.
- **Hot-plug of cameras / mics** — works on macOS, partial on Windows,
  flaky on Linux PipeWire. The source goes "Inactive" until refresh.
  `PressInputPropertiesButton` with the right propertyName can refresh
  USB device lists without GUI.
- **Multi-monitor scaling on Windows** — display capture resolution
  follows the OS scaling factor. If a 4K monitor is at 150% scaling,
  OBS captures 2560x1440. Compose for the captured size, not the panel.
- **Audio sample rate mismatch** — if Windows mic is 48 kHz and game
  is 44.1, OBS resamples both to 48 kHz (the project sample rate set in
  Settings → Audio). Match the project rate to your most-trusted source.
- **NVENC simultaneous sessions** — RTX consumer cards now allow 5
  concurrent NVENC sessions (was 3 historically). Multi-RTMP with 4
  destinations + Source Record is the practical limit.
- **Browser source freezes after sleep** — OBS doesn't get a wake event
  consistently. Refresh the browser source or restart OBS after laptop
  sleep before going live.

## Ecosystem Position and Composition

OBS sits at the center of a small but rich ecosystem. Composition partners
that matter for EOS:

- **Stream services**: Twitch (RTMP, AAC mandatory), YouTube Live (RTMP,
  WHIP for low-latency), Kick (RTMP), Rumble (RTMP), Trovo, Custom RTMP,
  WHIP for SRT/LL-HLS distribution networks.
- **Restream.io / Castr / StreamYard for restream** — alternative to
  obs-multi-rtmp; takes one ingest and fan-outs cloud-side. Costs money
  but offloads CPU.
- **Self-hosted ingest**: nginx-rtmp, MediaMTX (formerly rtsp-simple-server),
  SRS. Useful for low-latency ingest from OBS to a self-hosted player.
- **Audio chain**: VoiceMeeter Banana / Potato (Windows virtual mixer),
  Loopback / Audio Hijack (macOS), PipeWire patchbay (Linux). OBS just
  consumes whatever device is at the end of the chain.
- **Camera enhancement**: NVIDIA Broadcast (Windows, RTX), mmhmm,
  XSplit VCam, OBS Background Removal plugin (TensorFlow Lite, cross-platform).
- **Overlays**: Streamlabs / StreamElements / Lumia / OWN3D — provide
  browser-source URLs that OBS just adds. Free tiers cover Initiate Arena.
- **Bot ecosystem**: Streamer.bot (Windows), Botisimo, Sammi — desktop
  apps that drive obs-websocket and chat APIs. EOS replaces these with
  its own controller.
- **Editing**: DaVinci Resolve Free / Premiere / Final Cut. OBS records
  → Resolve cuts. ProRes / DNxHR for color work, NVENC HEVC CQP for
  quick-turn.

In the EOS architecture: **gateway/eos_ai → obs-websocket → OBS Studio**.
OBS is a tool layer, not part of the cognitive layer. The controller
module is a thin wrapper that turns intent ("go to Q&A") into OBS verbs.

## Trajectory and Evolution

Where OBS is going:

- **WHIP / WHEP** ingest and playback (added 31.x). Sub-second latency
  to compatible CDNs. This will replace RTMP for new platforms over the
  next 2–3 years.
- **AV1 encoders** — NVENC AV1 (Ada+), AMF AV1 (RDNA3+), QuickSync AV1
  (Arc/Meteor Lake+). YouTube already accepts AV1 ingest. Twitch is
  testing. Better quality per bit, more GPU cost.
- **HDR pipeline** — 10-bit P010, BT.2100 PQ. Recording works; streaming
  to Twitch/YouTube is gated on platform support.
- **PipeWire on Linux** — replacing XSHM. Better Wayland support, finally.
- **obs-websocket** is in maintenance. The protocol is stable; new
  request types are added as new OBS features land. No v6 planned.
- **AI features** — the Background Removal plugin uses TFLite. Expect
  more AI filters (denoise, upscale, frame interpolation) as plugins.
- **Web-based control** — increasingly common to build a React dashboard
  that talks obs-websocket-js. EOS Discord bot is the equivalent.

Risk: OBS development is led by a small core team funded by donations
and sponsorships. There is no corporate owner. The roadmap moves at
volunteer pace. Plan around it; don't bet on a specific request type
landing on a deadline.

## Conceptual Model and Solution Recipes

### Recipe A — Agent-callable Initiate Arena live (the EOS pattern)

```python
# eos_ai/obs_controller.py
import os, time, base64
import obsws_python as obs

class OBSController:
    def __init__(self):
        self.cl = obs.ReqClient(host='127.0.0.1', port=4455,
                                password=os.getenv('OBS_WS_PASSWORD'),
                                timeout=3)
        # cache UUIDs
        self._scenes = {s['sceneName']: s['sceneUuid']
                        for s in self.cl.get_scene_list().scenes}
        self._inputs = {i['inputName']: i['inputUuid']
                        for i in self.cl.get_input_list().inputs}

    def show(self, scene): self.cl.set_current_program_scene(scene)
    def text(self, source, value):
        self.cl.set_input_settings(source, {'text': value}, True)
    def start_record(self): self.cl.start_record()
    def stop_record(self): return self.cl.stop_record().output_path
    def snapshot(self, source, w=640, h=360):
        s = self.cl.get_source_screenshot(source, 'png', w, h, -1)
        return base64.b64decode(s.image_data.split(',', 1)[1])
```

### Recipe B — Lower-third update from Discord command

```python
# services/discord_bot.py snippet
@bot.command()
async def now(ctx, *, topic: str):
    obs_ctl.text('LowerThird', f'Now: {topic}')
    await ctx.message.add_reaction('✅')
```

### Recipe C — Auto-record morning brand content

```bash
# scripts/scheduled/morning_prep.sh tail
python3 -c "
import sys; sys.path.insert(0,'/opt/OS')
from eos_ai.obs_controller import OBSController
o = OBSController(); o.show('Brand - Talking Head'); o.start_record()
print('recording started')
"
```

### Recipe D — Highlight capture (replay buffer save on hotkey/event)

```python
def on_chat_highlight(_):
    obs_ctl.cl.save_replay_buffer()
    path = obs_ctl.cl.get_last_replay_buffer_replay().saved_replay_path
    notify_discord(f'replay saved → {path}')
```

### Recipe E — Multi-RTMP via obs-multi-rtmp plugin

```
OBS → Docks → Multiple RTMP outputs
  + Twitch: rtmp://live.twitch.tv/app/<key>     (encoder: NVENC, 6000 kbps CBR)
  + YouTube: rtmp://a.rtmp.youtube.com/live2/<key> (encoder: NVENC, 6000 kbps CBR)
  + Kick:    rtmps://fa723fc1b171.global-contribute.live-video.net/app/<key>
```

Each target gets a separate encoder instance — budget GPU accordingly.
Don't run x264 multi-target on a small CPU.

### Recipe F — Encoder choice flowchart

```
Have NVIDIA RTX 20+? → NVENC H.264 (or HEVC for recording)
Have AMD RDNA2+?     → AMF H.264
Have Intel Arc / 11th gen+? → QuickSync H.264
Apple Silicon?       → Apple VT H.264
Otherwise            → x264 veryfast
```

### Recipe G — Diagnose dropped frames

```python
s = cl.get_stream_status()
if s.output_skipped_frames / max(s.output_total_frames, 1) > 0.02:
    print('network: dropping frames, lower bitrate or check upload')
stats = cl.get_stats()
if stats.render_skipped_frames > 0:
    print('GPU: render lag — too many heavy sources/filters')
if stats.output_skipped_frames > 0 and stats.cpu_usage > 80:
    print('encoder: CPU pegged — switch to NVENC or faster preset')
```

## Industry Expert and Cutting-Edge Usage

- **EposVox / Harris Heller** — encoder/bitrate guides. Their consensus
  for 2026: NVENC is parity with x264 medium at zero CPU; use it.
- **Andilippi** — scene design, alert theming, lower-thirds. Stresses
  consistent canvas size and 2-pixel safe margins.
- **Esports broadcast rigs** — multi-PC: gaming PC outputs NDI or capture
  card to a dedicated OBS PC running on a 13th-gen i7 + RTX 4070,
  encoder is x264 slow at 9000 kbps for parity with broadcast TV.
- **Podcasters running video** — OBS records each guest as a separate
  Source Record output to disk, in addition to a program mix. Resolve
  edit room re-syncs by audio.
- **Live coding streamers** — code editor as Window Capture (not Display)
  to avoid leaking desktop notifications; Browser source for terminal
  via ttyd or asciinema overlay.
- **Frontier**: WHIP ingest to a self-hosted MediaMTX → HLS via
  ffmpeg → CDN. Full owner-operator stack, sub-second control. Increasingly
  used by independent creators who want to escape platform lock-in.
- **Vertical content** — base canvas 1080x1920, output 1080x1920, single
  scene per platform (TikTok / Reels / Shorts). Restream cloud crops
  horizontally if you don't want to recompose.

---

## EOS Usage Patterns

EOS uses obs-websocket v5 as the agent surface for all broadcast control.
The human surface (OBS GUI) is for scene authoring and pre-show setup;
the agent surface is for real-time operation during lives and recordings.

**Stable patterns:**

- One process-wide `OBSController` instance in `eos_ai/obs_controller.py`,
  imported by the Discord bot, the orchestrator, and the cognitive loop.
- Connection on `127.0.0.1:4455`, password from `eos_ai/.env`.
- UUIDs cached at instantiation; methods accept human-readable names and
  resolve internally.
- All recordings to `/recordings/YYYY-MM-DD/` (matches the EOS YYYY-MM-DD
  filename rule). Auto-remux MKV → MP4 on stop via `ffmpeg`.
- Lower-third source named `LowerThird`, text-only payload, `overlay=True`.
- Scene names follow `Live - <Mode>` and `Brand - <Mode>` conventions
  (e.g. `Live - Talking Head`, `Brand - Demo`, `Live - Q&A`).

**Discord-driven verbs (planned):**
- `!scene <name>` → `set_current_program_scene`
- `!now <text>` → lower-third update
- `!record start` / `!record stop` → record control
- `!snap` → snapshot to Discord channel
- `!replay` → save replay buffer

**Scheduled jobs:**
- `morning_prep.sh` → auto-start record before solo brand session if
  Antony has a content block on the calendar.
- Initiate Arena live cron → 5 min before scheduled live, switch to
  `Live - Pre-Show`, start replay buffer, post Discord ready ping.

**Things EOS does NOT do with OBS:**
- Run OBS on the VPS (no GPU; not supported).
- Drive multi-RTMP from a script (use the plugin's GUI for the destination
  list; toggle outputs with `StartOutput`/`StopOutput`).
- Edit scene collections programmatically (the GUI is the right tool).

## Gotchas

Real failures encountered or anticipated. This section compounds.

- **Port collision** — 4444 (legacy v4) vs 4455 (v5). Random tutorials
  mix them. Always 4455.
- **Auth handshake timeout** — slow Identify due to network jitter or
  blocking I/O between Hello and Identify causes silent disconnect.
  obsws-python handles this synchronously; raw clients must.
- **Wrong text source kind on platform migration** — moving a scene
  collection from Windows to Linux loses text rendering because
  `text_gdiplus_v3` doesn't exist on Linux. Replace with
  `text_ft2_source_v2` and re-set the font.
- **`overlay=False` regret** — overwrites font/color/style on the text
  source when you only meant to change the string.
- **`SetCurrentPreviewScene` while not in Studio Mode** — silently ignored
  with success status. Always check `GetStudioModeEnabled` first or just
  use `SetCurrentProgramScene`.
- **Source name renamed in GUI mid-session** — script using the cached
  name fails with code 600 (ResourceNotFound). Use UUID.
- **Two clients fighting** — Streamer.bot + EOS controller both updating
  the same lower-third. Last write wins. Pick one owner per source.
- **`StartRecord` on a misconfigured profile** — succeeds, writes nothing,
  `output_bytes=0`. Always verify after 500 ms.
- **MKV recording corrupted after kill -9** — header is fine but the
  index is missing. `ffmpeg -i in.mkv -c copy out.mkv` fixes it. MP4
  is unrecoverable.
- **Replay buffer not running** when you call SaveReplayBuffer → code 205.
  Always start the buffer at session begin.
- **`GetSourceScreenshot` huge payloads** — a 1080p PNG base64 is ~3 MB
  and travels through the WebSocket. Pass `imageWidth/imageHeight` to
  downscale, or use `SaveSourceScreenshot` to write directly to disk.
- **Browser source after laptop sleep** — frozen until refresh. Add a
  `PressInputPropertiesButton(propertyName='refreshnocache')` before
  going live.
- **Encoder overload during a critical demo** — preventable: rehearse
  with `GetStats` polling for 60 seconds before going live.
- **NVENC session limit on consumer cards** — exceeding 5 simultaneous
  encodes (multi-RTMP + Source Record + virtual cam recording) silently
  drops sessions. Count outputs.
- **Tailscale port conflicts** — running OBS on Windows desktop while
  agent runs on VPS, expecting 4455 to be reachable. Bind OBS to
  `0.0.0.0` plus Tailscale ACL, NOT the public interface.
- **ProcessExit on OBS quit** — sockets close with code 1001. Reconnect
  loop must distinguish "OBS quit" (wait and retry) from "auth failed"
  (don't retry).
- **Profile parameter writes don't apply mid-output** — encoder bitrate,
  resolution, fps changes only take effect on the next StartStream/Record.
- **Two scene collections holding a source with the same name** — switching
  collections does NOT migrate the source; they're independent. Don't
  expect cross-collection state.
- **PipeWire screen capture portal prompts on every OBS launch** on some
  Linux distros — annoying for headless cron-driven recording. Use the
  XSHM (X11) source instead, or persist the portal token.
