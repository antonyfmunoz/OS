# Audio Mechanics Spike — Findings

Investigation date: 2026-06-14
FFmpeg versions: VPS 6.1.1 (Ubuntu), Beast 8.1-full_build (Windows/Gyan)

## Part A — Filter Mechanics (VPS, node-independent)

### A(a) LIVE VOLUME — LIVE ✅

ZMQ command `Parsed_volume_0 volume <val>` changes volume mid-stream.
PID stable (no restart). Response: `0 Success`.

- volume 0.2 → accepted
- volume 1.5 → accepted (boost)
- eval=frame required on the volume filter for runtime changes

**Verdict: LIVE.** Per-source volume is the primary live mix control.

### A(b) LIVE MUTE — LIVE ✅

ZMQ command `Parsed_volume_0 volume 0` silences the source completely.
Unmute with `volume 1.0`. PID stable.

**Verdict: LIVE.** Mute = volume 0, no special mechanism needed.

### A(c) SYNC OFFSET (adelay) — LAUNCH-TIME ONLY ⚠️

ZMQ command `Parsed_adelay_0 delays 500|500` returns `38 Function not implemented`.
PID stable (no crash), but the parameter is rejected at runtime.

**Verdict: LAUNCH-TIME ONLY.** Delay must be set at graph construction.
If a source needs runtime delay adjustment, the graph must be rebuilt
(stop + start with new adelay value). This is acceptable for sync
correction which is typically a set-once-at-setup operation.

### A(d) MIX WEIGHTS (amix) — NOT LIVE, WORKAROUND EXISTS ⚠️

ZMQ command `Parsed_amix_0 weights 0.2 0.8` returns `38 Function not implemented`.
Both space-separated and quoted syntaxes rejected.

**Verdict: NOT LIVE via amix weights.** However, the WORKAROUND is already
proven: use per-source volume filters (A(a)) as the live mix control instead
of amix weights. Set amix weights to `1 1` (unity) at launch, control
mix balance entirely through per-source volume. This is the correct
architecture for the mixer.

### A(e) LEVEL READBACK (VU meters) — LIVE ✅

Two proven paths for per-frame audio levels:

**Path 1: astats + ametadata (RECOMMENDED)**
```
astats=metadata=1:reset=1,ametadata=print:file=/path/to/meta.txt
```
Produces per-frame: Peak_level (dB), RMS_level (dB), RMS_peak, RMS_trough,
Crest_factor, DC_offset, Zero_crossings, Dynamic_range, Entropy.
At 44100Hz / 1024-sample frames = ~43 updates/second.
4M+ lines in 5 seconds — high resolution.

**Path 2: ebur128 + ametadata**
```
ebur128=metadata=1,ametadata=print:file=/path/to/meta.txt
```
Produces: M (momentary loudness), S (short-term), I (integrated), LRA (range).
LUFS-standard metering. 10 updates/second (100ms window).

**For the mixer:**
- Use astats for per-source VU meters (fast, per-channel)
- Use ebur128 on the master bus for broadcast-standard loudness metering
- Read via file poll or pipe — engine parses and forwards via health callback
- Alternative: read directly from progress pipe (already wired for video health)

**Verdict: LIVE.** Both paths work. astats for source VU, ebur128 for master.

---

## Part B — Beast Audio Reality (Windows, via mesh)

### B(f) Mic Capture via dshow — CONFIRMED ✅

Enumerated audio devices on Beast:
- **"Analogue 1 + 2 (Focusrite USB Audio)"** — professional audio interface
- **"Elgato Screen Link"** — audio + video capture device

dshow capture syntax: `-f dshow -i audio="Analogue 1 + 2 (Focusrite USB Audio)"`

Device enumeration: `ffmpeg -list_devices true -f dshow -i dummy`

**Verdict: CONFIRMED.** Mic capture works via dshow. Focusrite is the primary mic.

### B(g) System/Desktop Audio Loopback — REQUIRES SETUP ⚠️

**Current state on Beast:**
- No WASAPI format in FFmpeg build (dshow only)
- No virtual audio cable installed
- "Stereo Mix (Realtek High Definition Audio)" exists but Status: Unknown (DISABLED)
- Active output: "Speakers (Focusrite USB Audio)"

**The gotcha:** Stereo Mix captures Realtek output only, NOT Focusrite output.
If audio is playing through the Focusrite (which it is — that's the active
speakers), Stereo Mix won't capture it.

**Options (ranked by quality):**

1. **Virtual Audio Cable (RECOMMENDED)** — Install VB-Audio CABLE or similar.
   Creates a virtual device that can route any output through it as a loopback.
   Works with all audio outputs including Focusrite.
   Free: VB-Audio CABLE. Pro: VB-Audio Voicemeeter for routing matrix.

2. **NVIDIA RTX Audio Virtual Device** — Already listed in devices
   ("NVIDIA Virtual Audio Device (Wave Extensible) (WDM)"). May provide
   loopback but needs testing — it's primarily for noise suppression.

3. **Elgato Screen Link** — Shows as audio+video source. May capture
   system audio but this is Elgato-specific behavior, not general loopback.

4. **Enable Stereo Mix** — Quick fix but only for Realtek output. Sound →
   Recording → Show Disabled → Enable "Stereo Mix". Limitation: Focusrite
   audio not captured.

5. **OBS Virtual Audio** — OBS is installed (OBS Virtual Camera detected).
   OBS can monitor/capture desktop audio and output to a virtual cable.
   But adds OBS as a dependency.

**Verdict: REQUIRES VIRTUAL AUDIO CABLE INSTALL.** This is a one-time setup
on the Beast. VB-Audio CABLE (free) is the recommended solution. Without it,
desktop/system audio capture is not possible through the Focusrite output path.

### B(h) Filter Compatibility — ALL PASS ✅

Tested on Beast FFmpeg 8.1 (Windows):

| Filter | Status | Notes |
|--------|--------|-------|
| volume | ✅ PASS | Works identically to Linux |
| amix | ✅ PASS | Works identically to Linux |
| acompressor | ✅ PASS | Works identically to Linux |
| agate | ✅ PASS | Works identically to Linux |
| astats | ✅ PASS | metadata=1 works |
| ebur128 | ✅ PASS | Use -af syntax, not filter_complex with dual output |
| arnndn | ✅ PASS* | Filter present, requires model file (m= param) |
| azmq | ✅ PRESENT | Filter listed, ZMQ bind quoting differs on Windows shell |
| adelay | ✅ PASS | Works but not runtime-commandable (same as Linux) |

*arnndn requires downloading a noise suppression model (e.g., rnnoise models
from xiph.org). Not a filter availability issue — configuration only.

**ZMQ on Windows:** The `azmq` filter is built-in (`--enable-libzmq` confirmed).
The challenge is shell escaping of the bind address — Windows cmd.exe handles
backslash-colon escaping differently than bash. The broadcast adapter handles
this by building args programmatically (not via shell string), which avoids
the escaping issue entirely.

**Verdict: ALL FILTERS IDENTICAL.** No corrections needed for Windows.

---

## Corrections to BROADCAST_BUILD_PLAN.md

### Phase 1 (Audio Mixer) corrections forced by findings:

1. **Mix control architecture:** Use per-source volume filters (live via ZMQ)
   as the primary mix control. Set amix weights to unity. Do NOT rely on
   amix weights for live mixing — they are launch-time only.

2. **Sync offset:** adelay is launch-time only. Expose as a "resync" operation
   that rebuilds the audio subgraph (brief audio glitch acceptable for a
   correction that happens once per session).

3. **System audio source:** Add a prerequisite check for virtual audio cable
   on Beast. The mixer should detect available loopback devices and warn if
   desktop audio capture is requested without one installed.

4. **VU meter path:** Use astats for per-source meters, ebur128 for master bus.
   Read from file/pipe, forward via health callback (same path as video health).

5. **arnndn noise suppression:** Requires model file deployment to Beast.
   Add model download/copy as a setup step in Phase 1.

---

## Teardown Verification

- VPS: 0 ffmpeg processes (verified via `pgrep`)
- Beast: 0 ffmpeg processes (verified via `tasklist`)
- ZMQ ports 5555-5557: released (processes terminated)
- Spike output files: in job tmp dir, not committed
