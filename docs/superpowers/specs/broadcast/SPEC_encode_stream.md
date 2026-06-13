# Broadcast Encode/Stream Subsystem — Behavioral Specification

> LICENSE_FIREWALL Zone B artifact. Expression-free.
> No GPL source, identifiers, or structure reproduced.
> Describes WHAT, never HOW. All terminology is original.

---

## 1. Purpose

The Encode/Stream subsystem is the final stage of the broadcast pipeline. It takes the composite video frame and mixed audio from the Compositing subsystem, encodes them into compressed formats, and delivers them to one or more output destinations: live streaming services, local file recordings, virtual camera devices, or network relay endpoints.

---

## 2. Observable Behaviors

- User clicks "Start Stream" and the broadcast goes live to a configured destination.
- User clicks "Start Recording" and a local file begins accumulating encoded output.
- Stream health metrics are visible: bitrate, dropped frames, network latency, encoder load.
- Recording file size and duration are displayed in real-time.
- Virtual camera mode makes the composite output available as a system camera device.
- Multiple outputs can run simultaneously (stream + record + virtual camera).
- User can switch destinations or stop individual outputs independently.

---

## 3. Video Encoding

| Concept | Description |
|---|---|
| **Codec selection** | H.264 (AVC), H.265 (HEVC), AV1. H.264 is the universal default. |
| **Rate control** | CBR (constant bitrate), VBR (variable), CQ (constant quality) |
| **Bitrate** | Target bitrate in kbps (e.g., 4500 for 1080p30, 6000 for 1080p60) |
| **Resolution** | Output resolution, may differ from canvas resolution (downscale) |
| **Frame rate** | Output FPS, typically matching canvas FPS |
| **Keyframe interval** | Seconds between I-frames (typically 2s for streaming) |
| **Encoder preset** | Speed vs. quality tradeoff (ultrafast through veryslow concept spectrum) |
| **Profile / Level** | Codec profile (e.g., High for H.264) and level (e.g., 4.1) |
| **Hardware acceleration** | Offload encoding to GPU: NVENC (NVIDIA), QSV (Intel), AMF (AMD), VAAPI (Linux generic). Falls back to software (CPU-based) if unavailable. |
| **Pixel format** | Internal format for encoding (NV12 typical) |
| **B-frames** | Number of bidirectional prediction frames (0-4) |
| **Look-ahead** | Encoder pre-analyzes N future frames for better rate control |

---

## 4. Audio Encoding

| Concept | Description |
|---|---|
| **Codec** | AAC (universal default), Opus (for WebRTC/SRT contexts) |
| **Bitrate** | 128–320 kbps typical |
| **Sample rate** | 44100 or 48000 Hz |
| **Channels** | Mono (1), Stereo (2), or multi-channel |
| **Audio track count** | Multiple independent audio tracks per output (e.g., desktop audio + voice as separate tracks in recording) |

---

## 5. Container Formats

| Format | Use Case | Notes |
|---|---|---|
| **FLV** | RTMP streaming | Required by most RTMP ingest servers |
| **MPEG-TS** | SRT, RIST, HLS streaming | Resilient to packet loss, supports mid-stream joining |
| **MP4** | Local recording | Good compatibility; NOT crash-resilient (loses data if not finalized) |
| **MKV** | Local recording (recommended) | Crash-resilient, supports more codecs; slightly less compatibility |
| **Fragmented MP4** | HLS/DASH adaptive streaming | Segmented for adaptive bitrate delivery |
| **WebM** | VP8/VP9/AV1 recording | Open format alternative |

---

## 6. Streaming Outputs

### 6.1 RTMP / RTMPS
- Standard protocol for Twitch, YouTube Live, Kick, Facebook Live, custom RTMP ingest.
- Configuration: server URL + stream key.
- RTMPS adds TLS encryption.
- Authentication via stream key embedded in URL or as separate field.

### 6.2 SRT (Secure Reliable Transport)
- Low-latency, reliable transport for professional use.
- Configuration: listener/caller mode, address, port, latency, passphrase.
- Supports encryption (AES-128, AES-256).

### 6.3 RIST (Reliable Internet Stream Transport)
- Alternative reliable transport.
- Configuration: endpoint URL, buffer size.

### 6.4 HLS (HTTP Live Streaming)
- Adaptive bitrate streaming via HTTP.
- Produces .m3u8 playlist + .ts/.mp4 segments.
- Higher latency (5-30s typical), wide device compatibility.

### 6.5 Custom URL
- Generic output to any FFmpeg-compatible URL scheme.
- For advanced users who need non-standard destinations.

### 6.6 Multi-Destination
- Concept: encode once, send the muxed output to multiple destinations simultaneously.
- Each destination has independent connection state and health metrics.
- One destination failing does not affect others.

---

## 7. Recording Outputs

| Feature | Description |
|---|---|
| **Format selection** | MKV (recommended), MP4, WebM |
| **File path** | User-configured directory + filename template |
| **Filename template** | Supports variables: date, time, scene name, counter |
| **Split by duration** | Auto-split recording every N minutes |
| **Split by file size** | Auto-split when file reaches N GB |
| **Pause/resume** | Pause recording without creating a new file |
| **Replay buffer** | Continuously records the last N seconds in memory; user can "save" to capture a retroactive clip on demand (e.g., save last 30 seconds after a highlight moment) |

---

## 8. Virtual Camera

- Exposes the composite program output as a virtual camera device visible to other applications (Zoom, Teams, Google Meet, Discord, etc.).
- The virtual camera has its own lifecycle: start/stop independently of stream/recording.
- Output resolution and frame rate can differ from the stream output.
- Concept: OS-level virtual device driver (v4l2loopback on Linux, virtual camera driver on Windows/macOS).

---

## 9. Output Profiles

A named, saveable configuration that bundles all output settings:

| Field | Description |
|---|---|
| `profile_id` | Unique identifier |
| `name` | Human-readable label (e.g., "Twitch 1080p60", "Local Recording HQ") |
| `output_type` | stream, recording, virtual_camera |
| `video_codec`, `video_bitrate`, `resolution`, `fps` | Video encoding settings |
| `audio_codec`, `audio_bitrate`, `sample_rate` | Audio encoding settings |
| `container_format` | FLV, MKV, MP4, etc. |
| `destination` | For streams: URL + key. For recordings: directory + template. |
| `hardware_encoder` | Preferred hardware encoder (or "software") |
| `encoder_preset` | Speed/quality tradeoff |
| `keyframe_interval_s` | Seconds between keyframes |
| `is_default` | Whether this profile is used when user clicks "Start Stream/Record" |

Users can create, edit, duplicate, and delete profiles. Multiple profiles can be active simultaneously.

---

## 10. Stream Health Metrics

| Metric | Description |
|---|---|
| `output_bitrate_kbps` | Actual bitrate being sent |
| `target_bitrate_kbps` | Configured target |
| `dropped_frames` | Frames skipped due to encoder overload |
| `total_frames` | Total frames encoded |
| `drop_percentage` | dropped / total as percentage |
| `encoder_latency_ms` | Time to encode one frame |
| `network_rtt_ms` | Round-trip time to streaming server |
| `send_queue_depth` | Frames waiting to be sent |
| `bytes_sent` | Total bytes transmitted |
| `uptime_s` | Seconds since output started |
| `reconnection_count` | Number of reconnection attempts |
| `disk_write_rate_mbps` | For recordings: write throughput |
| `disk_space_remaining_gb` | Available space on recording drive |
| `status_tier` | HEALTHY / WARNING / CRITICAL based on thresholds |

Thresholds for status:
- HEALTHY: <1% dropped frames, RTT < 200ms, queue depth < 10
- WARNING: 1-5% dropped frames, RTT 200-500ms, queue depth 10-30
- CRITICAL: >5% dropped frames, RTT > 500ms, queue depth > 30

---

## 11. Data Flow

```
Compositor Program Output
  (composite video frame + mixed audio)
        |
        v
  +-------------------+
  |  Encoder Manager   |  Selects codec, manages HW/SW encoder instances
  +--------+----------+
           |
           v  (encoded video NALUs + encoded audio packets)
  +-------------------+
  |  Muxer             |  Wraps in container format (FLV, MKV, MPEG-TS)
  +--------+----------+
           |
           v  (muxed stream)
  +-------------------+
  |  Output Router     |  Sends to one or more destinations
  +--------+----------+
           |
           +---> Network Sink (RTMP, SRT, RIST, HLS) --> Streaming service
           +---> File Sink (MKV, MP4) --> Local disk
           +---> Segment Sink (HLS .ts files) --> HTTP server / CDN
           +---> Device Sink (virtual camera) --> OS loopback device
           +---> Replay Buffer (ring buffer in memory)
```

---

## 12. State Transitions

### Streaming Lifecycle
```
[Idle] --start()--> [Connecting] --connected--> [Live]
                         |                        |
                    connection_failed        network_error
                         |                        |
                         v                        v
                     [Failed]              [Reconnecting]
                                                |
                                           reconnected --> [Live]
                                           max_retries --> [Failed]
                                           
[Live] --stop()--> [Disconnecting] --done--> [Idle]
```

### Recording Lifecycle
```
[Idle] --start()--> [Recording] --pause()--> [Paused]
                        |                       |
                   stop()                  resume()--> [Recording]
                        |                       |
                        v                  stop()
                   [Finalizing]                 |
                        |                       v
                   done()               [Finalizing]
                        |                       |
                        v                  done()
                     [Idle]                     |
                                                v
                                             [Idle]
```

### Virtual Camera Lifecycle
```
[Inactive] --start()--> [Active] --stop()--> [Inactive]
```

---

## 13. Public Interfaces

| Operation | Description |
|---|---|
| `create_output_profile(config)` | Create a new output profile |
| `update_output_profile(id, config)` | Modify an existing profile |
| `delete_output_profile(id)` | Remove a profile |
| `list_output_profiles()` | Get all configured profiles |
| `start_streaming(profile_id?)` | Begin streaming with specified or default profile |
| `stop_streaming(profile_id?)` | Stop a specific stream or all streams |
| `start_recording(profile_id?)` | Begin recording |
| `stop_recording(profile_id?)` | Stop recording and finalize file |
| `pause_recording(profile_id?)` | Pause recording (keep file open) |
| `resume_recording(profile_id?)` | Resume paused recording |
| `start_virtual_camera()` | Activate virtual camera output |
| `stop_virtual_camera()` | Deactivate virtual camera |
| `save_replay_buffer()` | Save the current replay buffer contents to a file |
| `get_stream_health(profile_id?)` | Get current health metrics for an output |
| `get_recording_status()` | Get recording duration, file size, path |
| `list_available_encoders()` | Enumerate available HW and SW encoders |
| `test_connection(destination)` | Test connectivity to a streaming destination without going live |

---

## 14. Multi-Output

- Multiple outputs can run simultaneously with independent profiles.
- Common combination: stream to Twitch + record locally + virtual camera for Discord.
- The compositor produces one program frame; the encoder can be shared (encode once) or per-output (encode separately with different settings).
- Encode-once is preferred when multiple outputs use the same codec/bitrate.
- Separate encoding is needed when outputs require different resolutions or codecs.
- GPU encoder sessions are limited (typically 2-3 concurrent on consumer GPUs).
- Each output has independent start/stop, health metrics, and error handling.

---

## 15. Edge Cases

| Scenario | Expected Behavior |
|---|---|
| **Network disconnect mid-stream** | Enter Reconnecting state; retry with exponential backoff; if max retries exceeded, enter Failed state and notify user |
| **Encoder overload (CPU/GPU)** | Drop frames to maintain real-time; increment dropped_frames counter; if sustained, downgrade encoder preset dynamically (if configured) or warn user |
| **Disk full during recording** | Stop recording gracefully, finalize file, notify user with error |
| **Destination server rejects connection** | Enter Failed state with server's rejection reason; do not retry automatically |
| **Codec incompatibility with destination** | Reject at profile validation time (before going live) with clear error |
| **Hardware encoder unavailable** | Fall back to software encoder; warn user about performance impact |
| **Abnormal termination (crash/power loss)** | MKV files remain playable up to the last written cluster; MP4 files may be unrecoverable without remux |
| **Audio/video sync drift** | Monitor PTS alignment; resample audio to correct drift exceeding threshold |
| **Stream key exposed in logs** | Stream keys are treated as secrets: masked in UI, never written to log files |
| **Multiple streams to same destination** | Allowed but warned — some services reject duplicate connections |
| **Replay buffer memory exhaustion** | Bounded by configured duration; oldest frames evicted when buffer is full |
| **Mid-stream resolution change** | Requires encoder restart; brief interruption to stream (some services disconnect on resolution change) |
