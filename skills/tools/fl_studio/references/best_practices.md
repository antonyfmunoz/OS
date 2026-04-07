# FL Studio — Creator-Level Best Practices

Last researched: 2026-04-06
Tool version: FL Studio 21.x / 24.x
Frame: **Human operator skill + project convention reference.** FL Studio is
a GUI-only desktop DAW. There is no public agent-callable API. EOS agents
prepare briefs, conventions, and structure; Antony executes at the keyboard.

---

## 1. Identity & Purpose

FL Studio (originally FruityLoops, 1997, Image-Line, Belgium) is a digital
audio workstation built around a **pattern-first** workflow. Born as a
4-channel MIDI step sequencer, it grew into a full-feature DAW while keeping
its defining trait: musical ideas are reusable Patterns dropped onto a
linear Playlist timeline, not unique regions baked into a track.

This paradigm is the reason FL dominates modern beat-driven music — hip-hop,
trap, EDM, drum & bass, future bass. The workflow rewards iteration: sketch
a 4-bar idea, drop it everywhere it belongs, edit the source once, every
instance updates. Linear DAWs (Pro Tools, Logic) require either copying
regions or wrestling with aliasing; FL has aliasing as the default.

**Lifetime Free Updates** is Image-Line's signature. Buy any edition once,
get every future major version free, forever, with no subscription. This is
unique among professional DAWs and the single biggest reason long-term
producers stay loyal.

For EOS purposes, FL Studio is the production tool of record for any audio
output: future music venture demos and releases, Initiate Arena content
audio (opening sequences, course module beds, transition stings), personal
brand voiceover backing beds, and eventual Empyrean Studio audio service
deliverables.

---

## 2. Conceptual Model

The mental model is **four surfaces orbiting a transport**:

- **Playlist** — the linear timeline. Multi-track. Holds Audio clips,
  Pattern clips (references to a Pattern in the Channel Rack), and
  Automation clips. The Playlist IS the song.
- **Channel Rack** — the pattern editor. Each row is an instrument generator
  channel. The active Pattern (top-of-window dropdown) is what you're
  editing. Step-sequence by clicking grid cells, or open Piano Roll for
  melodic content.
- **Mixer** — 125 insert tracks plus master. Each insert holds an FX chain
  (10 slots), routes to master or other inserts, accepts sends, and binds
  to a hardware input for recording.
- **Piano Roll** — best-in-class MIDI editor. Per-channel, per-pattern.
  Notes, velocity, automation events, ghost notes, scale highlighting.

**Patterns are reusable.** This is the single most important concept. Drop
the same Pattern on the Playlist 16 times, edit the source once, all 16
instances update. Want a variation? Clone the pattern (Pattern menu -> Clone),
edit the clone, drop it where you want the variation. Producers manage
dozens or hundreds of Patterns per project, color-coded and named.

**Channel != Mixer Track.** A Channel Rack row is an instrument generator
that produces audio. A Mixer insert is a signal-processing slot that processes
audio. You connect them by setting the channel's "FX" target (right-click
the channel name -> Channel settings -> FX) to a mixer insert number. One
channel routes to one insert; many channels can share one insert (e.g., all
drums to insert 5 = drum bus).

**Automation is a clip.** Right-click any knob anywhere in FL -> Create
Automation Clip. A new clip appears on the Playlist controlling that
parameter over time. Edit it like any other clip — move, copy, length-stretch,
draw envelope points. This unifies "modulation" and "arrangement" into one
metaphor.

**Right-click is mandatory.** FL's interaction model assumes you right-click
constantly. Left-click does almost nothing useful on most controls. Half the
software lives in context menus. New users from Ableton/Logic miss this and
think FL is incomplete.

**Server-of-truth analogue:** the .flp project file in memory is the truth.
Everything else (rendered audio, exported MIDI, stem WAVs) is a snapshot.
Save often. The undo history is per-session.

---

## 3. Architecture & Data Model

The .flp project file is a proprietary binary container. Officially
undocumented, but reverse-engineered well enough that open-source parsers
exist (PyFLP being the most maintained). At a high level it stores:

```
.flp
├── Header
│   ├── Magic bytes ("FLhd")
│   ├── FL Studio version that created the file
│   └── Project metadata (title, author, comments, tempo, time sig)
├── Project settings
│   ├── BPM (float, supports fractional)
│   ├── Time signature (numerator/denominator)
│   ├── PPQ (pulses per quarter note, default 96)
│   └── Sample rate
├── Channels (Channel Rack rows)
│   ├── Sample channel
│   │   ├── Sample file path (absolute)
│   │   ├── Pitch, vol, pan, FX target
│   │   └── Sample-level envelope
│   ├── Native generator (3xOsc, Harmor, Sytrus, FLEX, etc.)
│   │   └── Internal preset state
│   └── VST plugin channel
│       ├── Plugin path
│       ├── Preset chunk (opaque blob written by the plugin)
│       └── Wrapper settings (latency, processing mode)
├── Patterns
│   ├── Pattern N
│   │   ├── Name, color
│   │   ├── Step sequencer state per channel
│   │   └── Piano roll notes per channel
├── Playlist
│   ├── Tracks (audio, pattern, automation lanes)
│   └── Clips
│       ├── Start tick
│       ├── Length
│       ├── Source (pattern ID / sample / automation)
│       └── Mute/lock state
├── Mixer
│   ├── Insert 1..125 + Master
│   │   ├── Name, color, icon
│   │   ├── FX slots (10 per insert)
│   │   ├── Sends (destination insert + level)
│   │   ├── Output routing
│   │   └── Hardware in/out binding
├── Automation clips
│   ├── Target parameter ID
│   ├── Envelope points (tick, value, tension, mode)
│   └── LFO settings
└── Render settings (last-used export config)
```

**Sample files are referenced by absolute path, not embedded.** This is the
single biggest portability gotcha. Move the .flp without its samples folder
and FL prompts for "missing files" on load. Solution: **File -> Export ->
Project Bundle (zip with samples)** before sharing or backup.

VST plugin state is stored as an opaque chunk written by the plugin itself.
This means plugin presets travel with the .flp, but only if the same plugin
(same vendor, compatible version) is installed on the destination machine.

---

## 4. Authentication

**N/A for agents.** FL Studio is a local desktop app. The only "auth" is the
Image-Line account login that unlocks the install on a given machine. There
is no remote API surface, no OAuth, no service account. Agents have nothing
to authenticate against.

For Antony as operator: register the account, unlock the machine, save the
credentials in 1Password. Lifetime updates are tied to the account, not the
machine — log in on each new install.

---

## 5. Quick Reference

### Editions

| Edition | Audio recording | Edison | Slicex | Harmor | Sytrus | Gross Beat |
|---|---|---|---|---|---|---|
| Fruity | NO | NO | NO | NO | basic | NO |
| Producer | YES | YES | YES | NO | basic | NO |
| Signature | YES | YES | YES | YES | full | YES |
| All Plugins Bundle | YES | YES | YES | YES | full | YES |

Recommendation for serious work: **Signature**. Producer is the floor for
any real production; Signature adds Harmor and Gross Beat which are the
two highest-value native plugins.

### File extensions

- `.flp` — FL Studio Project (the working file)
- `.fst` — FL Studio State (channel preset, mixer chain snapshot, single FX)
- `.flm` — FL Studio Mobile project (separate format, NOT interchangeable)
- `.fsc` — FL Studio Score (Piano Roll content only)
- Project Bundle (.zip) — .flp + all referenced samples in one folder

### Export formats

- WAV — 16, 24, 32-bit float; 44.1, 48, 88.2, 96, 192 kHz
- MP3 — CBR/VBR, 64-320 kbps
- FLAC — lossless compressed
- OGG Vorbis
- AIFF
- MIDI — per-pattern via Piano Roll -> File -> Export as MIDI

### Render scopes

- **Full song** — Playlist start to end
- **Playlist selection** — selected time range
- **Pattern** — active pattern only
- **Stems by Mixer track** — one WAV per insert
- **Stems by Playlist track** — one WAV per Playlist lane
- **Stems by Channel** — one WAV per Channel Rack row

### Native instruments worth installing/learning

- **Harmor** (Signature+) — additive resynthesis flagship
- **Sytrus** (full in Signature) — FM/RM/subtractive 6-op hybrid
- **FLEX** — preset rompler, free
- **3xOsc** — built-in starter oscillator
- **Slicex / Fruity Slicer** — beat slicing
- **DirectWave** — sampler
- **Edison** — full audio editor as a plugin

### Native effects

- **Parametric EQ 2** — surgical EQ
- **Maximus** — multiband mastering
- **Fruity Reverb 2** — algorithmic reverb
- **Fruity Delay 3** — modern delay
- **Fruity Compressor / Fruity Limiter** — bread and butter
- **Gross Beat** (Signature+) — time/volume warping for stutter, glitch, gate
- **Soundgoodizer** — front-end of Maximus, one-knob loudness

### Plugin format support

- VST2 (.dll) — supported, legacy
- VST3 (.vst3) — supported (preferred)
- CLAP — supported in FL Studio 24.x and later
- AU (Audio Units) — **NOT supported**, even on macOS
- AAX — NOT supported (Pro Tools format)

### MIDI controller scripting

- Language: Python (FL embedded interpreter)
- Purpose: hardware controller mappings (Novation Launchkey, AKAI MPK,
  Korg nanoKONTROL, custom rigs)
- Location: `Image-Line/FL Studio/Settings/Hardware/`
- Documentation: Image-Line "MIDI Scripting" online manual
- Scope: read MIDI input, write MIDI output, call FL channels/mixer/transport
  via the `channels`, `mixer`, `transport`, `ui`, `device`, `general`,
  `playlist`, `patterns` modules
- **Cannot** be invoked from outside FL. **Cannot** read/write .flp files.
  **Cannot** be reached by an external agent process.

---

## 6. Idiomatic Patterns

### Pattern-first beat workflow

1. New project, set BPM (right-click tempo -> type value)
2. Drop drum samples into Channel Rack rows: kick, snare, clap, closed hat,
   open hat, perc, ride, crash
3. Step-sequence the core groove (16 steps, 4 bars)
4. Add a melodic channel (3xOsc or FLEX), open Piano Roll, sketch melody
5. Add bass channel, sketch sub
6. Pattern 1 = "main groove." Clone to Pattern 2 = "drop variation."
7. Clone to Pattern 3 = "break" (drums out, melody only)
8. Drag patterns onto Playlist: intro -> verse -> drop -> break -> drop ->
   outro
9. Route every channel to a Mixer insert; group: Insert 1 = kick, 2 = snare,
   3-4 = hats, 5 = drum bus, 6 = bass, 7 = lead, 8 = pads, 9 = fx
10. Bus drum inserts (1-4) route output to insert 5 (drum bus)
11. Add FX: EQ, compression, saturation per insert
12. Reference-match the mix in Edison
13. Master on the master insert: EQ -> compression -> Maximus / Pro-L 2
14. Render WAV (24-bit, 48 kHz) and MP3 (320 kbps CBR)

### Naming conventions (EOS standard)

- **Project file:** `YYYY-MM-DD_PROJECT_VERSION.flp`
  e.g. `2026-04-06_arena-opener_v01.flp`
- **Patterns:** `01 intro` `02 verse` `03 drop` `04 break` `05 outro`
- **Mixer inserts:** named for content (`KICK`, `SNARE`, `DRUM BUS`,
  `BASS`, `LEAD`, `PAD`, `FX`, `VOX`)
- **Stems folder:** `stems/YYYY-MM-DD_PROJECT_VERSION/`
- **Bounces:** `bounces/YYYY-MM-DD_PROJECT_VERSION_master.wav`

### Color coding (EOS standard)

- Drums: red
- Bass: orange
- Lead/melody: yellow
- Pad/atmosphere: blue
- FX/risers: purple
- Vocal: green
- Reference: gray

### Brief template (agent draft -> Antony executes)

```
PROJECT: [name]
DELIVERABLE: [stem set / loop / full master / single]
TARGET VENUE: [Initiate Arena opener / IG reel BG / podcast bumper / release]
LENGTH: [seconds or bars]
BPM: [number, or range]
KEY: [C minor / etc.]
TIME SIG: [4/4 default]
MOOD: [3-5 adjectives]
REFERENCE TRACKS: [3 links/titles + what to borrow from each]
INSTRUMENTATION: [drums type, bass type, lead type, atmosphere]
ARRANGEMENT: [intro Xs -> verse Xs -> drop Xs -> outro Xs]
NOTES: [anything else]
```

---

## 7. Industry Expert Usage

Producers known for FL Studio (verified): Metro Boomin, Southside, Wheezy,
Murda Beatz, TM88 (modern trap); Porter Robinson, Madeon (electronic);
Avicii (early career); Martin Garrix, Deadmau5 (early); 9th Wonder
(hip-hop); Sub Focus, Camo & Krooked (drum & bass); Boi-1da; KSHMR.

The signature workflow is consistent across genres:

1. **Sound selection over composition.** Pros spend disproportionate time
   choosing kicks, snares, and lead patches. The right sound makes a
   mediocre arrangement great; the wrong sound buries a perfect arrangement.
2. **Reference-driven mixing.** Always have a commercial reference loaded
   as an audio clip on a muted Playlist track. Toggle between your mix
   and the reference at matched loudness. Don't trust ears alone.
3. **Bus everything early.** Drum bus, bass bus, lead bus, FX bus —
   each routed through compression and saturation as a group. Master
   bus EQ + compression + limiting last.
4. **Pattern variation discipline.** Every 8-16 bars, something must
   change. Drop a hat. Add a perc layer. Filter the bass. Energy
   never sits still in modern production.
5. **Reference loudness.** Modern target: -8 to -10 LUFS integrated for
   streaming-aware masters; some genres push -6. Use Maximus + Youlean
   Loudness Meter to check.

---

## 8. Ecosystem & Comparison

| DAW | Paradigm | Strength | FL comparison |
|---|---|---|---|
| Ableton Live | Session/Arrangement dual | Live performance, warping, Max for Live | Live wins live + experimental; FL wins Piano Roll + studio production |
| Logic Pro | Linear, region-based | Mac-native, scoring, Apple ecosystem, $200 one-time | Logic wins songwriter/full production; FL wins price + Windows |
| Pro Tools | Linear, audio tracking | Industry standard for studio recording/mixing | Pro Tools owns commercial recording; FL is irrelevant in that lane |
| Cubase | Linear, deep MIDI | Score editor, expression maps, orchestral | Cubase wins orchestral/film; FL wins beat-driven genres |
| Reaper | Linear, scriptable | Lua/Python scripting, $60 license | Reaper wins automation + price; FL wins Piano Roll + native instruments |
| Bitwig | Modular, hybrid grid | Modulators, sound design | Bitwig wins sound design; FL wins workflow speed |
| Studio One | Linear, drag-everywhere | UX polish, integrated mastering | Studio One wins UX cleanliness; FL wins for genres FL invented |

**FL's defining edges:**

- **Piano Roll** — universally regarded as the best in any DAW. Ghost notes,
  scale highlighting, chord tools, Riff Machine, articulation strums, the
  control envelope panel.
- **Lifetime Free Updates** — no other major DAW offers this. Buy in 2010,
  still get FL Studio 24.x in 2025 for free.
- **Pattern-first workflow** — maps to how modern beat-driven music is
  actually written, end of story.
- **Native instruments depth** — Harmor and Sytrus alone justify Signature.

**FL's weaknesses:**

- **Audio recording UX** is workable but feels bolted on vs Pro Tools/Logic.
- **Notation/scoring** essentially absent.
- **macOS support** is real but Windows is the lead platform.
- **Headless / scripting from outside** — does not exist.

---

## 9. Anti-Patterns

- **Working without naming Patterns.** "Pattern 1, Pattern 2, Pattern 3"
  becomes unnavigable past 10 patterns. Name and color from the start.
- **Routing every channel to insert 1.** Defeats the mixer. Bus by section.
- **Mastering on the channel before reaching the master insert.** Maximus
  on a kick channel = clipped kick into the bus. Master on the master.
- **Skipping Project Bundle export when sharing.** The collaborator opens
  it, sees "missing samples" warnings on every channel.
- **Editing Pattern 1 when you meant Pattern 2.** Always check the active
  pattern dropdown before clicking the Channel Rack grid.
- **Using only stock plugins forever.** Stock is excellent, but Pro-Q 3,
  Pro-L 2, Serum, Vital, etc. exist for reasons.
- **Using only third-party plugins forever.** FL's natives are excellent;
  Harmor and Gross Beat have no exact third-party equivalents.
- **Clipping the master insert.** Loudness on the master, but stay below
  0 dBFS true peak. Use Pro-L 2 or Maximus with TP enabled.
- **No reference track loaded.** Mix in a vacuum, ship a mud bath.
- **Saving over the same .flp file forever.** Use versioned filenames.
  Recoverable history beats undo every time.
- **Treating MIDI scripting as a general scripting layer.** It is not.
  It binds hardware controllers. That is all it does.

---

## 10. Webhooks

**N/A.** FL Studio has no event-emitting surface to remote services. There
are no webhooks. The closest analog is the MIDI Out from a controller script,
which sends MIDI messages to another local MIDI device — not HTTP.

---

## 11. Rate Limits

**N/A.** Local desktop application. There is no remote API to be rate-limited
against. Performance limits are CPU/RAM/voice count constraints inside the
running app.

Practical performance ceilings (modern desktop, 16-core, 32 GB RAM, SSD):

- ~50-100 simultaneous VST instances before CPU strain
- ~125 mixer inserts is a hard ceiling (architecture limit)
- Sample memory bounded by RAM minus FL overhead
- Use **freezing** (consolidate channel to audio) to free CPU on heavy
  patches you've finalized

---

## 12. Error Handling

FL Studio errors live in three places:

1. **Hint bar** at the top of the main window — transient error/warning text
2. **Plugin wrapper dialogs** — VST load failures, missing DLL, version
   mismatch
3. **Crash dump** — `Image-Line/FL Studio/System/Crash dumps/` after a hard
   crash

Common errors and fixes:

- **"Could not load X"** on project open — sample file moved. Open the
  channel, point at the new path, save.
- **VST instance crash** — usually a 32-bit plugin in a 64-bit FL or vice
  versa, or a plugin corrupted by an OS update. Re-scan plugins:
  Options -> Manage Plugins -> Find more plugins.
- **ASIO underrun / glitches** — buffer too small for the project's CPU
  load. Options -> Audio Settings -> raise buffer length to 512/1024
  samples for mixing, drop to 128/256 for recording.
- **"Sample rate mismatch"** — project sample rate != audio interface rate.
  Match them in Audio Settings.
- **"Plugin verification failed"** — first scan after install. Acknowledge
  and retry; usually transient.

For agents drafting briefs: do not invent error states. Refer issues to
Antony with the exact hint bar text or the crash dump filename.

---

## 13. Testing

There is no agent-runnable test layer for FL Studio projects. "Testing" a
project means listening at matched loudness, checking spectrum and metering,
and rendering to the target deliverable.

Operator test checklist:

- **Loudness check** — Youlean Loudness Meter on master, hit target LUFS
- **True peak check** — Pro-L 2 / Maximus shows < -1 dBTP
- **Mono compatibility** — flip mixer to mono (Master -> Stereo Separation
  -100%), check phase issues
- **Reference comparison** — A/B against commercial reference at matched
  loudness
- **Headphone vs monitor vs car/phone** — listen on three systems before
  shipping
- **Re-render from scratch** — render to WAV and re-import; play back the
  rendered file, not the live project, as the final acceptance test

---

## 14. Production Operations

For Antony as operator:

- **Backup discipline** — every .flp project lives under
  `/music/projects/YYYY/PROJECT/` with versioned filenames. Project Bundle
  exports go in `/music/projects/YYYY/PROJECT/bundles/`. Cloud sync
  (Dropbox / iCloud Drive / Tailscale-mounted VPS) for offsite redundancy.
- **Sample library** — single canonical location, e.g. `/music/samples/`,
  with subfolders by category (drums/, bass/, vox/, fx/, loops/). Add the
  root to FL Browser via Options -> File Settings -> Browser extra search
  folders.
- **Plugin sandbox** — for unstable VSTs, right-click the plugin in the
  Channel Rack -> Wrapper Settings -> Make Bridged. Bridged plugins crash
  in their own process and don't take FL down.
- **CPU monitoring** — F2 / View -> CPU panel during heavy mix sessions.
  Freeze channels above ~70% sustained.
- **Render hygiene** — always render WAV first (lossless archive), then
  encode MP3/FLAC from the WAV with a separate tool (or FL's built-in
  exporter for one-shot work).
- **Session length** — production sessions should be time-boxed deep work
  blocks (90-120 min) with no Discord/Slack/email open.

For EOS: agents schedule the deep work blocks, draft the brief that goes
into the session, and catalog the resulting bounces. Agents do not touch
the .flp files.

---

## 15. Integration Points

FL Studio integrates with:

- **VST2/VST3 plugins** — third-party instruments and effects
- **CLAP plugins** (24.x+) — newer open standard
- **MIDI controllers** — USB, DIN, Bluetooth MIDI; ControlSurface scripts
  for advanced bindings
- **ASIO audio interfaces** — Focusrite, RME, UAD, Universal Audio,
  PreSonus, MOTU, etc.
- **ReWire** — legacy, deprecated by Image-Line; use as audio plugin instead
- **Image-Line FL Studio Mobile** — separate app, separate format (.flm),
  NOT interchangeable with .flp
- **ZGameEditor Visualizer** — render music videos alongside audio
- **OSC** — Open Sound Control input/output for visual rigs and Touch OSC

For EOS: the only integration agents should reference is **the file
system**. Catalog .flp files and their bounces. Schedule production
sessions on the calendar. Surface stem WAVs to downstream content
workflows (e.g., dropping a stinger into a video editor).

---

## 16. Versioning

FL Studio uses major.minor versioning (21.x, 24.x as of 2026). Lifetime
Free Updates means every license gets every future major version free.

Project file (.flp) compatibility:

- **Forward compatible** — newer FL opens older .flp files
- **NOT backward compatible** — older FL cannot open newer .flp files
- **Plugin compatibility** — VST presets travel with the .flp but require
  the same VST installed on the destination machine

Always note the FL version that created an archived project so future
loads don't surprise you.

---

## 17. Telemetry & Logs

FL Studio has minimal telemetry exposed to operators:

- **CPU panel** (F2) — real-time CPU per channel/insert
- **Audio Settings -> Status** — sample rate, buffer, dropouts
- **Crash dumps** — `Image-Line/FL Studio/System/Crash dumps/`
- **Plugin scan log** — last plugin verification output

There is no structured log file agents can tail. There is no metrics
endpoint.

---

## 18. Known Issues & Workarounds

- **Sample paths absolute** -> always Project Bundle for sharing/backup
- **VST 32-bit on 64-bit FL** -> bridge or upgrade
- **ASIO exclusive** -> only one app at a time can hold the interface
- **macOS AU not supported** -> use VST3 or CLAP versions of plugins
- **Old .fl projects (pre-FL 11)** -> convert by opening and re-saving in
  modern FL; some legacy automation may need rebuilding
- **Plugin wrapper crash on scan** -> right-click the plugin -> Verify -> retry
- **Latency compensation glitches with bridged plugins** -> manual PDC
  override in plugin wrapper settings
- **Time-stretched audio clip artifacts** -> change stretch algorithm
  (Resample / Stretch / Pro / etc.) per clip in clip properties
- **Disappearing automation clips after moving plugins** -> automation
  bound to parameter+slot; rebuild after restructuring mixer
- **MIDI controller not detected** -> Options -> MIDI Settings -> enable
  device input + assign port number; restart FL if persistent

---

## 19. EOS Skill Boundaries

This skill is a **reference** layer, not an execution layer. Agents cannot
drive FL Studio. Agents can:

**DO:**

- Draft creative briefs for music production (template in section 6)
- Reference EOS naming conventions and color coding
- Compare DAWs honestly when Antony asks
- Catalog .flp project files in a registry (path, name, last modified,
  stage: sketch/arrangement/mix/master)
- Schedule production deep-work blocks on the calendar
- Surface bounced stems/masters to downstream workflows (video editing,
  content publishing)
- Generate reference-track analysis text (structure, BPM, key, instrumentation,
  notes for Antony to internalize)

**DO NOT:**

- Claim to render, modify, or open .flp files
- Invent FL Studio commands callable from a shell
- Suggest "automating FL with Python" for anything other than hardware
  controller bindings
- Promise stem export, MIDI export, or audio render without Antony at
  the keyboard
- Confuse FL Studio (.flp) with FL Studio Mobile (.flm)
- Suggest macOS AU plugins
- Promise lossless backward compatibility of .flp across versions

**Verification step (every time this skill is used):**

After drafting any brief, template, or convention reference, confirm:

1. Does the deliverable specify BPM, key, length, mood, and references?
2. Does the file naming follow `YYYY-MM-DD_PROJECT_VERSION.flp`?
3. Does the brief end with a clear human action ("Antony to execute in
   FL Studio, deliver bounced WAV by [date]")?
4. Have you avoided promising any agent-side FL automation?

If any answer is "no" — fix before returning to the caller.

---

## Appendix A: Expanded Brief Templates

### A.1 Initiate Arena opening sequence sting

```
PROJECT: arena-opener-[module-slug]
DELIVERABLE: Single stinger, full master + stems
TARGET VENUE: Initiate Arena module opening sequence
LENGTH: 8-12 seconds (negotiable, must hit visual cut at 6s)
BPM: 90-100 (epic-but-controlled)
KEY: D minor or F minor (cinematic dark)
TIME SIG: 4/4
MOOD: tactical, focused, imminent, premium, cold-weather-luxury
REFERENCE TRACKS:
  1. Hans Zimmer - Time (Inception) - swell + arrival
  2. Hidden Citizens covers - cinematic trailer aesthetic
  3. The Newton Brothers - Haunting of Hill House title
INSTRUMENTATION:
  - Sub-octave brass swell
  - Cinematic riser (white noise + filter sweep)
  - Single hit: Taiko + sub kick + cymbal swell + impact reverb tail
  - Optional: vocal "ohhh" pad (Heavyocity Forzo or similar)
ARRANGEMENT:
  0-4s: low rumble + riser
  4-6s: swell intensifies
  6s: HIT
  6-12s: reverb tail + sub decay
NOTES: Must work without dialogue on top. Leave 200 Hz - 4 kHz space.
```

### A.2 Personal brand voiceover backing bed

```
PROJECT: vox-bed-[content-piece]
DELIVERABLE: Looping audio bed, stems + master, 60s duration
TARGET VENUE: Short-form personal brand content (IG/TikTok/Shorts)
LENGTH: 60s (loops every 16 bars at 100 BPM)
BPM: 95-105
KEY: A minor or C minor (versatile, not too dark)
TIME SIG: 4/4
MOOD: confident, momentum, controlled-aggression, premium, no-cheese
REFERENCE TRACKS:
  1. Daniel Caesar instrumentals - warm + grounded
  2. Tom Misch - Geography backing textures
  3. FKJ - jazzy electronic hybrid
INSTRUMENTATION:
  - Soft 808 / sub bass on root
  - Lo-fi-tinged drums (filtered hat, soft kick, dusty snare)
  - Rhodes or Wurlitzer chords (Mk1 sample or Lounge Lizard)
  - One ear-candy element: vinyl crackle or muted guitar lick
ARRANGEMENT: 16-bar loop. Verse-feel throughout. NO drop. NO build.
  Ducks for voiceover: leave 200 Hz - 5 kHz under -12 dBFS.
NOTES: Must sit politely under voice. Test against Antony's voice
  reference clip before delivery.
```

### A.3 Future music venture release demo

```
PROJECT: [release-name]-demo
DELIVERABLE: Full song demo, stem set, rough master
TARGET VENUE: A&R / collaborator review / DSP submission later
LENGTH: 2:30-3:30 (modern release length)
BPM: [genre-specific]
KEY: [composer choice]
TIME SIG: 4/4 default
MOOD: [3-5 adjectives specific to release vision]
REFERENCE TRACKS: [3 commercial references at the same level you want]
INSTRUMENTATION: [genre-driven]
ARRANGEMENT:
  Intro 8 -> Verse 16 -> Pre 8 -> Chorus 16 -> Verse 16 -> Pre 8 ->
  Chorus 16 -> Bridge 8 -> Final Chorus 16 -> Outro 8
NOTES: Demo loudness target -10 LUFS. Final master comes later
  from a dedicated mastering pass.
```

---

## Appendix B: Mixer routing recipes

### B.1 Standard pop/electronic bus structure

```
Insert  1: KICK         -> bus 5
Insert  2: SNARE/CLAP   -> bus 5
Insert  3: HATS         -> bus 5
Insert  4: PERC         -> bus 5
Insert  5: DRUM BUS     -> Master   [comp + saturation + EQ]
Insert  6: BASS SUB     -> bus 8
Insert  7: BASS MID     -> bus 8
Insert  8: BASS BUS     -> Master   [comp + saturation]
Insert  9: LEAD         -> bus 12
Insert 10: HARMONY      -> bus 12
Insert 11: PAD          -> bus 12
Insert 12: MELODIC BUS  -> Master   [glue comp]
Insert 13: VOX MAIN     -> bus 15
Insert 14: VOX HARMONY  -> bus 15
Insert 15: VOX BUS      -> Master   [comp + de-ess + reverb send]
Insert 16: FX RISERS    -> Master
Insert 17: FX IMPACTS   -> Master
Insert 18: REVERB SEND  -> Master   [reverb only, fed by sends]
Insert 19: DELAY SEND   -> Master   [delay only, fed by sends]
Master: EQ -> Glue Comp -> Multiband -> Limiter
```

### B.2 Cinematic stinger structure

```
Insert 1: SUB IMPACT    -> Master
Insert 2: TAIKO         -> bus 6
Insert 3: BRASS SWELL   -> bus 6
Insert 4: RISER         -> bus 6
Insert 5: REVERB TAIL   -> bus 6  [send-fed, 100% wet]
Insert 6: STING BUS     -> Master
Master: gentle limiter only — preserve dynamics
```

---

## Appendix C: Stem export folder convention

```
/music/projects/2026/2026-04-06_arena-opener_v01/
├── 2026-04-06_arena-opener_v01.flp
├── bundles/
│   └── 2026-04-06_arena-opener_v01_bundle.zip
├── bounces/
│   ├── 2026-04-06_arena-opener_v01_master.wav
│   └── 2026-04-06_arena-opener_v01_master.mp3
├── stems/
│   ├── 01_drums.wav
│   ├── 02_bass.wav
│   ├── 03_lead.wav
│   ├── 04_pad.wav
│   ├── 05_fx.wav
│   └── 06_vox.wav
├── reference/
│   ├── ref_01_zimmer-time.mp3
│   └── ref_02_hidden-citizens.mp3
└── notes.md
```

`notes.md` captures: BPM, key, render date, version notes, what changed
since last version, what's still TODO. Agents can read this file to
catalog project state without ever touching the .flp.

---

## Appendix D: Agent-facing project registry schema

When EOS catalogs FL Studio projects, the registry row is:

```
project_id: slug (e.g. arena-opener-module-3)
flp_path: absolute path to current .flp
created: ISO date
last_modified: ISO date (from filesystem mtime)
stage: sketch | arrangement | mix | master | shipped
bpm: number
key: string (e.g. "Dm")
duration_target_seconds: number
deliverable_type: stinger | loop | full-track | stem-set
target_venue: arena-opener | brand-content | release | client-work
brief_path: path to brief markdown
latest_bounce_path: path to most recent rendered WAV (if any)
notes_path: path to notes.md inside project folder
```

Agents read this registry. Agents do NOT touch the .flp. The registry
is the only handle agents have on FL Studio work.

---

## Appendix E: Loudness targets by venue

| Venue | Integrated LUFS | True Peak | Notes |
|---|---|---|---|
| Spotify / Apple Music | -14 (auto-normalized) | -1 dBTP | Don't over-limit; let normalization do work |
| YouTube | -14 | -1 dBTP | Same |
| Instagram / TikTok | -10 to -12 | -1 dBTP | Mobile speakers; slightly hotter ok |
| Initiate Arena video opener | -10 | -1 dBTP | Punchy, sits over no dialogue |
| Voiceover backing bed | -20 to -24 (under voice) | -3 dBTP | Bed must duck under speech |
| Podcast bumper | -16 | -1 dBTP | Matches podcast loudness norms |
| Demo / WIP | -10 | -1 dBTP | Hot enough to evaluate, not final |
| Final mastered release | per DSP target | -1 dBTP | Mastering engineer call |

Use Youlean Loudness Meter (free) on the master insert. Render -> reload
the WAV -> verify the rendered file matches the target, not the live
project (the live project meter can lie if plugins behave differently
during render).

---

End of best_practices.md

