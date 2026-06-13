# Broadcast Compositing Subsystem — Behavioral Specification

> LICENSE_FIREWALL Zone B artifact. Expression-free.
> No GPL source, identifiers, or structure reproduced.
> Describes WHAT, never HOW. All terminology is original.

---

## 1. Purpose

The Compositing subsystem combines multiple captured visual and audio sources into a single unified output frame. It manages scenes (named layouts of positioned sources), layer ordering, transitions between scenes, audio mixing, and per-source visual/audio filters. The compositor sits between Capture (upstream) and Encode/Stream (downstream).

---

## 2. Observable Behaviors

- User creates named scenes, each containing positioned and layered sources.
- A preview output shows what the next scene will look like before going live.
- A program output shows the current live composite frame.
- Transitioning between scenes produces smooth visual effects (cut, fade, slide, wipe).
- Audio from all active sources is mixed into a single output stream with per-source volume control.
- Visual filters (color correction, chroma key, blur) can be applied per-source.
- Audio filters (gain, noise suppression, compressor) can be applied per-source or to the master mix.
- Sources can be repositioned, resized, cropped, rotated, and reordered in real-time.

---

## 3. Scene Model

A scene is a named, persistent collection of source references with layout and routing information.

| Field | Description |
|---|---|
| `scene_id` | Unique identifier |
| `name` | Human-readable label |
| `source_entries[]` | Ordered list of source placements (see Source Positioning) |
| `canvas_width`, `canvas_height` | Output resolution for this scene |
| `background_color` | Fill color when no source covers a region |
| `transition_in` | Default transition when switching TO this scene |
| `audio_routing` | Per-source audio routing overrides for this scene |
| `hotkey` | Optional keyboard shortcut to activate this scene |
| `created_at`, `updated_at` | Timestamps |

---

## 4. Source Positioning

Each source entry within a scene has placement properties:

| Property | Description |
|---|---|
| `source_ref` | Reference to a Capture source by ID |
| `x`, `y` | Position of the top-left corner on the canvas (pixels) |
| `width`, `height` | Rendered dimensions on the canvas |
| `rotation_deg` | Rotation angle (0-360) |
| `crop_top`, `crop_right`, `crop_bottom`, `crop_left` | Pixel crop from each edge |
| `opacity` | 0.0 (transparent) to 1.0 (fully opaque) |
| `z_order` | Layer index (higher = closer to viewer) |
| `visible` | Whether the source is rendered |
| `locked` | Whether the source can be moved/resized in the editor |
| `blend_mode` | Compositing blend mode (normal, additive, multiply, screen) |
| `filters[]` | Ordered list of visual filters applied to this source |
| `audio_filters[]` | Ordered list of audio filters for this source's audio |

---

## 5. Layer Ordering

- Sources are composited in z_order from lowest (back) to highest (front).
- When two sources have the same z_order, the one later in the source_entries list renders on top.
- Opacity and blend mode determine how overlapping sources combine.
- A source with `visible: false` is skipped entirely — no rendering cost.
- Locked sources cannot be accidentally moved but still render normally.

---

## 6. Transitions

Transitions control how the compositor switches from the current program scene to a new scene.

| Transition Type | Behavior |
|---|---|
| **Cut** | Instant switch, zero duration |
| **Fade** | Cross-dissolve over a configurable duration (ms) |
| **Slide** | New scene slides in from a direction (left, right, up, down) |
| **Wipe** | A boundary sweeps across the frame revealing the new scene |
| **Stinger** | A pre-rendered video overlay plays during the transition (used for branded transitions) |
| **Luma Wipe** | A grayscale image defines the transition boundary shape |

Each transition has:
- `type`: one of the above
- `duration_ms`: how long the transition takes (0 for cut)
- `direction`: for directional transitions
- `media_path`: for stinger/luma transitions
- `easing`: linear, ease-in, ease-out, ease-in-out

---

## 7. Audio Mixing

The compositor produces a single mixed audio output from all active sources.

| Concept | Description |
|---|---|
| **Per-source volume** | Each source has an independent volume level (0.0–1.0 or dB scale) |
| **Per-source mute** | Silences a source without changing its volume setting |
| **Monitor mode** | Per-source: off (no local playback), monitor-only (local but not in output), monitor-and-output (both) |
| **Master volume** | Applied after individual source mixing |
| **Master mute** | Silences the entire output |
| **Audio ducking** | Automatically reduces music/background volume when voice is detected |
| **Channel routing** | Sources can be assigned to left, right, center, or specific output channels |

Audio is mixed by summing normalized PCM samples with per-source gain applied, then clipping or limiting the result to prevent distortion.

---

## 8. Filters / Effects

### 8.1 Visual Filters (applied per-source, in order)

| Filter | Parameters |
|---|---|
| **Color Correction** | Brightness, contrast, saturation, hue shift, gamma |
| **Chroma Key** | Key color, similarity threshold, smoothness, spill reduction |
| **Color Key** | Target color, similarity range |
| **LUT (Lookup Table)** | File path to .cube or .png LUT for color grading |
| **Blur** | Radius, type (gaussian, box, motion) |
| **Sharpen** | Strength |
| **Crop/Pad** | Additional crop or padding beyond the source placement crop |
| **Scroll** | Horizontal and vertical scroll speed |
| **Image Mask** | Alpha mask from an image file |
| **Render Delay** | Delay this source's video by N milliseconds |

### 8.2 Audio Filters (applied per-source or to master, in order)

| Filter | Parameters |
|---|---|
| **Gain** | Volume adjustment in dB |
| **Noise Suppression** | Suppression level (low, medium, high); concept: spectral gating or neural-network based |
| **Noise Gate** | Open threshold, close threshold, attack, hold, release |
| **Compressor** | Threshold, ratio, attack, release, output gain |
| **Limiter** | Ceiling level, release time |
| **Expander** | Threshold, ratio, attack, release |
| **Equalizer** | Multi-band parametric EQ (frequency, gain, Q per band) |
| **De-esser** | Target frequency range, reduction amount |

Filters are applied in list order. Adding, removing, or reordering filters takes effect on the next frame.

---

## 9. Preview vs. Program (Dual-Output Model)

| Output | Purpose |
|---|---|
| **Preview** | Shows the scene that WILL go live on the next transition. Used for setup and verification. Not sent to stream/recording. |
| **Program** | Shows the scene that IS live. This is what goes to the encoder/stream/recording. |

Workflow:
1. User selects a scene in preview.
2. User verifies it looks correct.
3. User triggers a transition.
4. The preview scene becomes the program scene (with transition effect).
5. The old program scene is now available for re-selection.

Alternative mode: **Studio Mode off** — no preview, clicking a scene immediately transitions it to program.

---

## 10. Group Sources

A group source is a container that holds multiple child sources and treats them as a single unit.

- Moving or scaling the group moves/scales all children relative to the group's origin.
- The group has its own x, y, width, height, rotation, opacity, and filters.
- Children within the group are positioned relative to the group's local coordinate space.
- Groups can be nested (a group within a group), but circular references are rejected.
- Collapsing a group in the scene editor hides children for a cleaner view.
- A group can be locked to prevent accidental modification of its children.

---

## 11. Data Flow

```
Capture Sources (N sources producing frames)
        |
        v  (each source's latest frame)
  +------------------+
  |  Scene Resolver   |  Determines which sources are in the active scene
  +--------+---------+
           |
           v  (visible sources + placement data)
  +------------------+
  |  Transform Stage  |  Apply position, scale, crop, rotation per source
  +--------+---------+
           |
           v  (transformed source regions)
  +------------------+
  |  Filter Pipeline  |  Apply visual filters per source in order
  +--------+---------+
           |
           v  (filtered source regions)
  +------------------+
  |  Compositor Core  |  Alpha-blend all layers by z_order onto canvas
  +--------+---------+
           |
           v  (single composite frame + mixed audio)
  +--------+---------+
  |  Output Splitter  |  Sends to preview renderer AND program output
  +------------------+
           |
           +---> Preview display (local only)
           +---> Program output --> Encoder --> Stream/Record
```

---

## 12. State

| State | Description |
|---|---|
| **Scenes list** | All defined scenes with their source entries |
| **Active program scene** | The scene currently being composited for output |
| **Active preview scene** | The scene being composited for preview (may be same as program) |
| **Transition state** | idle, transitioning (with progress 0.0–1.0), or completed |
| **Studio mode** | Whether preview/program dual-output is active |
| **Global audio state** | Master volume, master mute |

---

## 13. Public Interfaces

| Operation | Description |
|---|---|
| `create_scene(name, canvas_size)` | Create a new empty scene |
| `delete_scene(scene_id)` | Remove a scene and its source entries |
| `duplicate_scene(scene_id)` | Clone a scene with all its source entries |
| `rename_scene(scene_id, name)` | Change scene display name |
| `reorder_scenes(scene_ids[])` | Set the scene list order |
| `add_source_to_scene(scene_id, source_ref, placement)` | Add a source entry to a scene |
| `remove_source_from_scene(scene_id, entry_id)` | Remove a source entry |
| `update_source_placement(scene_id, entry_id, placement)` | Change position/size/crop/etc. |
| `reorder_sources(scene_id, entry_ids[])` | Change z_order of sources |
| `add_filter(scene_id, entry_id, filter_config)` | Add a visual/audio filter |
| `remove_filter(scene_id, entry_id, filter_id)` | Remove a filter |
| `reorder_filters(scene_id, entry_id, filter_ids[])` | Change filter processing order |
| `set_preview_scene(scene_id)` | Set the preview scene |
| `trigger_transition(transition_config?)` | Transition preview to program |
| `set_program_scene(scene_id)` | Directly set program scene (cut) |
| `get_preview_frame()` | Get current preview composite frame |
| `get_program_frame()` | Get current program composite frame |
| `set_source_volume(entry_id, volume)` | Set audio level for a source |
| `set_source_mute(entry_id, muted)` | Mute/unmute a source |
| `set_master_volume(volume)` | Set master output volume |
| `toggle_studio_mode()` | Enable/disable preview + program mode |
| `create_group(scene_id, entry_ids[])` | Group selected sources |
| `ungroup(scene_id, group_id)` | Dissolve a group back to individual sources |

---

## 14. Edge Cases

| Scenario | Expected Behavior |
|---|---|
| Source producing no frames | Compositor uses last known frame or a configurable placeholder; does not stall the entire composite |
| Resolution mismatch between sources | Each source is scaled to its placement dimensions regardless of native resolution |
| Audio sync drift | Compositor uses PTS timestamps to align audio; if drift exceeds threshold, resamples to correct |
| Scene with zero sources | Compositor outputs the background color fill |
| Circular group reference | Rejected at creation time with an error |
| Transition triggered during active transition | Queued or cancels current transition (configurable) |
| Source removed while in active scene | Source entry removed; compositor fills the gap with background |
| Filter produces error | Filter is bypassed; source renders without that filter; error logged |
| Extremely high source count | Performance degrades gracefully; sources beyond GPU/CPU budget are skipped with warning |
| Preview and program are the same scene | Both outputs render identically; transitions have no visible effect |
