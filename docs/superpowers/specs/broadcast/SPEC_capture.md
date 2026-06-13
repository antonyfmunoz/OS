# Broadcast Capture Subsystem — Behavioral Specification

> LICENSE_FIREWALL Zone B artifact. Expression-free.
> No GPL source, identifiers, or structure reproduced.
> Describes WHAT, never HOW. All terminology is original.

---

## 1. Purpose

The Capture subsystem is the ingestion layer of a broadcast pipeline. It acquires raw video frames and audio samples from physical devices, virtual devices, software windows, files, and network streams, then delivers them in a normalized format to downstream consumers (compositing, encoding, preview).

Every source of visual or auditory content enters the broadcast pipeline through Capture. Nothing reaches the compositor without first being captured.

---

## 2. Observable Behaviors

- User selects a source type and configures it (e.g., picks a webcam, chooses resolution).
- The source begins producing frames/samples at a steady cadence.
- Frames arrive in a consistent pixel format and resolution regardless of the native device format.
- Audio samples arrive at a consistent sample rate and channel layout.
- If a device disconnects, the source enters an error state and can optionally show a placeholder.
- Sources can be started, stopped, paused, and reconfigured independently.
- Multiple sources can capture simultaneously from different devices.
- Hot-plugged devices become available for selection without restarting the application.

---

## 3. Inputs

| Input Category | Examples |
|---|---|
| Video device handle | OS camera device path, DirectShow device, AVFoundation device |
| Audio device handle | OS audio input device, ALSA/PulseAudio/CoreAudio/WASAPI identifier |
| Display region | Monitor index, screen coordinates, capture area rectangle |
| Window handle | OS window identifier for a specific application window |
| URL | HTTP/HTTPS address for browser-rendered content or network stream |
| File path | Local path to video file, audio file, image file |
| Text content | User-supplied string, font, size, color, scroll parameters |
| Color value | Solid color (hex/RGB) for a color-fill source |
| Network endpoint | NDI discovery name, RTSP URL, SRT listener address |

---

## 4. Outputs

| Output | Format |
|---|---|
| Video frames | Normalized pixel format (e.g., NV12, I420, or BGRA), at the source's configured resolution and frame rate |
| Audio samples | Normalized PCM format (e.g., 32-bit float), at the source's configured sample rate and channel count |
| Frame metadata | Timestamp (PTS), frame number, source identifier, capture latency |
| Source status events | State changes (active, paused, error), device events (disconnect, reconnect) |

---

## 5. Source Types

### 5.1 Camera / Webcam

Captures video from a physical or virtual camera device. User selects from enumerated devices. Configurable: resolution, frame rate, pixel format, flip/mirror.

Platform acquisition concepts: Video4Linux2, DirectShow, AVFoundation, Media Foundation.

### 5.2 Microphone / Audio Input

Captures audio from a physical microphone, line-in, or virtual audio device. User selects from enumerated audio input devices. Configurable: sample rate, channels (mono/stereo), bit depth, gain.

Platform acquisition concepts: ALSA, PulseAudio, PipeWire, WASAPI, CoreAudio.

### 5.3 Desktop / Display Capture

Captures the entire visible area of a monitor or a rectangular sub-region. User selects which monitor (by index or name). Configurable: capture area, cursor visibility, frame rate.

Platform acquisition concepts: PipeWire screen capture portal, DXGI Desktop Duplication, CGDisplayStream.

### 5.4 Window Capture

Captures the content of a single application window, excluding other windows. User selects from enumerated visible windows. Configurable: capture cursor, capture window chrome vs. client area only.

Platform acquisition concepts: PipeWire window capture, Windows Graphics Capture, CGWindowListCreateImage.

### 5.5 Browser / URL Source

Renders a web page at a specified URL into a video frame. Uses an embedded headless browser engine. Configurable: URL, viewport width/height, CSS override, refresh interval, custom CSS injection, transparency.

### 5.6 Media File Playback

Plays a local video file, audio file, or image sequence as a source. Supports common container formats: MP4, MKV, MOV, WebM, MP3, WAV, FLAC, OGG, animated GIF/WebP. Configurable: loop, playback speed, start/end trim, audio track selection.

### 5.7 Text / Label Source

Renders user-supplied text into a video frame. Configurable: font family, font size, color, background color, alignment, word wrap, scroll direction and speed, outline, shadow, padding, text content (static or from file).

### 5.8 Color Source

Produces a solid color rectangle. Configurable: color (hex/RGB/HSL), width, height, opacity. Used for backgrounds, overlays, or spacing elements.

### 5.9 Image Source

Displays a static image file (PNG, JPEG, BMP, WebP, SVG). Configurable: file path, opacity, aspect ratio handling (stretch, fit, fill, original). Optionally reloads if file changes on disk.

### 5.10 Network Source

Receives video/audio over a network protocol. Supported concepts: NDI (discovery-based, zero-config LAN), RTSP (IP cameras), SRT (low-latency reliable), RIST (reliable internet stream transport). Configurable: endpoint address, buffer size, latency target.

---

## 6. Data Flow

```
Device / File / Network / Rendered Content
        |
        v
  +-------------+
  |  Acquirer    |  Platform-specific frame grab
  +------+------+
         |  raw native frames/samples
         v
  +-------------+
  |  Normalizer  |  Convert to standard pixel/sample format
  +------+------+
         |  normalized frames/samples + metadata
         v
  +-------------+
  |  Frame Queue |  Thread-safe buffer (bounded ring)
  +------+------+
         |  consumer pulls at its own cadence
         v
  +-------------+
  |  Consumer    |  Compositor, preview renderer, encoder
  +-------------+
```

- Each source runs its own acquisition loop on a dedicated thread or async task.
- The normalizer converts device-native formats to the pipeline standard format.
- The frame queue decouples acquisition timing from consumption timing.
- If the consumer is slower than the producer, oldest frames are dropped (latest-frame policy) or the queue blocks (configurable).

---

## 7. State Transitions

```
             create()
  [None] ------------> [Created]
                           |
                           | configure()
                           v
                       [Configured] <---- reconfigure()
                           |
                           | start()
                           v
                  +--->[Active] <--- resume()
                  |      |    |
             reconnect() |    | pause()
                  |      |    v
                  |      | [Paused]
                  |      |
                  |    error event
                  |      |
                  |      v
                  +---[Error]
                        |
                        | destroy()
                        v
                    [Destroyed]
```

- **Created**: source object exists, no device acquired.
- **Configured**: device/path/URL set, parameters validated, not yet producing frames.
- **Active**: producing frames at the configured cadence.
- **Paused**: device held open but frames not delivered to queue.
- **Error**: device lost, permission revoked, or unrecoverable failure. May auto-retry.
- **Destroyed**: all resources released. Terminal state.

---

## 8. Public Interfaces

| Operation | Description |
|---|---|
| `enumerate_devices(type)` | List available devices for a given source type |
| `create_source(type, config)` | Instantiate a new source with initial configuration |
| `configure_source(id, config)` | Update source configuration (may require restart) |
| `start_source(id)` | Begin frame/sample production |
| `pause_source(id)` | Suspend production, keep device handle |
| `resume_source(id)` | Resume production from paused state |
| `stop_source(id)` | Stop production, release device |
| `destroy_source(id)` | Release all resources, remove source |
| `get_source_properties(id)` | Read current configuration and capabilities |
| `get_latest_frame(id)` | Pull the most recent frame from the queue |
| `subscribe_frames(id, callback)` | Push-based frame delivery |
| `get_source_state(id)` | Query current lifecycle state |
| `on_device_change(callback)` | Register for hot-plug / device removal events |

---

## 9. Properties Per Source Type

### Camera / Webcam
- `device_id`, `resolution`, `frame_rate`, `pixel_format`
- `flip_horizontal`, `flip_vertical`
- `auto_focus`, `auto_exposure`, `auto_white_balance`

### Microphone / Audio Input
- `device_id`, `sample_rate`, `channels`, `bit_depth`
- `gain_db`, `noise_gate_threshold`

### Desktop / Display Capture
- `monitor_index`, `capture_region` (x, y, w, h)
- `capture_cursor`, `frame_rate`

### Window Capture
- `window_id`, `capture_cursor`, `client_area_only`

### Browser / URL Source
- `url`, `viewport_width`, `viewport_height`
- `refresh_interval_ms`, `custom_css`, `transparent_background`

### Media File Playback
- `file_path`, `loop`, `playback_speed`
- `start_time_ms`, `end_time_ms`, `audio_track_index`

### Text / Label Source
- `text` (or `text_file_path`), `font_family`, `font_size_px`
- `color`, `background_color`, `alignment`, `word_wrap`
- `scroll_direction`, `scroll_speed_px_per_sec`
- `outline_width`, `outline_color`, `shadow_offset`, `shadow_color`

### Color Source
- `color`, `width`, `height`, `opacity`

### Image Source
- `file_path`, `opacity`, `scaling_mode`, `reload_on_change`

### Network Source
- `protocol`, `endpoint`, `buffer_ms`, `latency_target_ms`

---

## 10. Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Device disconnects mid-capture | Error state, placeholder frame, reconnection attempts |
| Permission denied | Error state with reason, no retry until user re-grants |
| Format mismatch | Normalizer converts; if impossible, Error with reason |
| Device hot-plug | Enumeration updates; auto-reconnect if configured |
| Resolution change mid-stream | Re-negotiate, downstream gets resolution-change event |
| File not found | Error state; retry if reload_on_change set |
| Browser source crash | Embedded browser restarts; error frame during restart |
| Audio sample rate mismatch | Resampler converts to pipeline standard |
| Multiple consumers | Independent read cursors per subscriber |
| Source faster than consumer | Drop oldest frames (configurable) |
| Zero-frame source | Color/image render on demand, not at a cadence |
