---
name: higgsfield
description: "Use when drafting Higgsfield AI video or image prompts for Antony to execute via the web GUI — short-form cinematic content for personal brand, Lyfe Spectrum drops, or Empyrean Studio creative work. Trigger on requests for camera-move shot lists, image-to-video prompts, Soul photo prompts, talking-avatar (Speak) scripts, or any time the brief mentions Bullet Time / Crash Zoom / FPV / Dolly Zoom / cinematic AI video."
allowed-tools: "Read, Write, Edit"
version: 1.0
source_url: "https://higgsfield.ai/"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "Higgsfield web product (no public REST API as of 2026-04)"
sdk_version: "N/A — GUI / human-operator tool"
speed_category: stable
---

# Tool: Higgsfield AI

## What This Tool Does

Higgsfield is a browser-based AI video and image generation platform whose
brand-defining feature is **fine-grained camera-move control**. Where most
AI video tools give you a generic "pan/zoom" toggle, Higgsfield ships 50+
named cinematic motion presets (Bullet Time, Crash Zoom, FPV Drone, Dolly
Zoom, Snorricam, Robo Arm, Lazy Susan, etc.) that lock the subject and
execute the move with film-grade physics.

The platform is a wrapper / orchestration layer over multiple underlying
models (its own DoP/Soul models plus Kling, Veo 3, Sora 2 routed through the
same UI and credit pool). You pick a model, optionally pick a camera-move
preset, optionally pick a Soul aesthetic preset, supply a text prompt and/or
reference image, and Higgsfield generates a 3–15s clip at 720p/1080p.

Core product surface (2026-04):

- **DoP** — cinematic video model. Image-to-video and text-to-video. The
  home of the camera-move catalog.
- **Soul / Soul 2.0** — hyper-realistic photo model with 50+ aesthetic
  presets (iPhone, Tokyo Street Style, Y2K, Editorial, Fisheye). Outputs
  stills that are typically the input frame for DoP.
- **Soul ID** — character consistency: train an identity once, reuse across
  Soul photos and DoP videos.
- **Speak / Speak 2.0** — talking avatar. Image + audio → lip-synced video.
- **Mix** — multi-shot composer for stitching beats into longer cuts.
- **Avatar** — full character pipeline (often paired with Speak).
- **Popcorn / Recast** — newer cinematic / restyling endpoints.
- **Routed models** — Kling 2.5 / 3.0, Veo 3 / 3.1, Sora 2, WAN — all
  consumable through the Higgsfield UI under one credit pool.

## EOS Integration

**Operating mode: human-in-the-loop GUI tool.** Higgsfield has no public
API that EOS can call directly. Antony executes the actual generation in
the browser. The agent's job is to draft *Higgsfield-shaped prompts* —
camera-move + style preset + tightly-scoped subject action — that he can
paste verbatim.

Primary EOS use cases:

- **Personal brand short-form** — opening hook shots for Vigilante Architect
  content. Bullet Time on a desk slam, Crash Zoom into the laptop, FPV out
  the window of the Portland HQ.
- **Lyfe Spectrum drops** — apparel hero clips. Glam preset + Lazy Susan
  on a folded hoodie, Snorricam on a model walking, Tokyo Street Style
  Soul stills as the source frame.
- **Empyrean Studio creative work** — client-facing cinematic mood pieces,
  pitch reels, Game of Lyfe early concept tests.
- **Initiate Arena marketing** — conversion-grade B-roll for landing pages
  and ad creative when stock footage is too generic.

Canonical EOS handoff pattern:

1. Antony provides reference image (or describes subject) + mood / vibe.
2. Agent picks one camera-move preset and one Soul aesthetic preset from
   the catalog in references/best_practices.md.
3. Agent drafts the prompt using the **{ subject anchor } + { one verb-led
   beat } + { camera-move tag } + { style tokens }** structure.
4. Output is a paste-ready block: model choice, preset names, prompt text,
   duration, resolution, expected credit cost.
5. Antony executes in browser, saves output to the relevant brand folder.

## Authentication

N/A for agents. Higgsfield is browser-only — Antony logs in via the web at
higgsfield.ai with his account credentials. There is no API key for EOS to
manage, no OAuth flow, no token to rotate. The "auth" surface is Antony's
session cookie in his browser. If a future public API ships, this section
gets a real signature; until then, treat Higgsfield as a manual GUI tool
and never pretend EOS can authenticate to it.

## Quick Reference

### The two preset axes (pick one of each)

```
CAMERA MOVE  (DoP, locks subject, defines motion)
  Bullet Time | Crash Zoom In/Out | Dolly Zoom In/Out | FPV Drone
  Super Dolly In/Out | 360 Orbit | Lazy Susan | Snorricam | Robo Arm
  Crane Up/Down | Whip Pan | Hyperlapse | Handheld | Static
  (full 50+ catalog in references/best_practices.md)

SOUL AESTHETIC  (look of the source frame)
  iPhone | Tokyo Street Style | Y2K | Editorial | Fisheye | Medieval
  Coquette | Glam | Film Noir | Polaroid | Fashion Editorial
```

### Prompt skeleton (paste into Higgsfield DoP)

```
[Subject anchor — who/what, one sentence]
[One beat — strong verb, one camera move, one subject action]
Camera: [camera-move preset name, e.g. "Crash Zoom In"]
Style: [aesthetic tokens — lighting, palette, lens, era]
```

### Worked example — Vigilante Architect hook

```
Reference image: Antony at desk, side-lit, dark room, MacBook open.

Prompt:
A tactical-luxury founder seated at a black desk, hands on keyboard.
He looks up sharply as the camera punches in on his face.
Camera: Crash Zoom In
Style: low-key cinematic, single key light from screen, 35mm anamorphic,
teal-and-amber grade, shallow depth of field.

Model:    Higgsfield DoP (image-to-video)
Duration: 5s
Output:   1080p
Est cost: ~6 credits (Kling 3.0 routing)
```

### Worked example — Lyfe Spectrum hoodie drop

```
Reference image: folded charcoal hoodie on concrete, top-down.

Prompt:
A folded heavyweight charcoal hoodie centered on raw concrete.
The garment slowly rotates revealing the embroidered Lyfe Spectrum mark.
Camera: Lazy Susan
Style: Glam preset, hard rim light, shadow play, fashion editorial,
matte texture, no people.

Model:    Higgsfield DoP
Duration: 5s
Output:   1080p
```

### Worked example — Speak talking avatar

```
Inputs:
  - Soul-generated portrait of Antony (Editorial preset)
  - 12s VO recording: "Structure beats discipline. Every time."

Higgsfield Speak 2.0 settings:
  Lip sync:    on
  Head motion: subtle
  Background:  static
  Output:      1080p, 12s
```

## Conceptual Model

**Higgsfield is a director's chair, not a renderer.** The mental model is
not "describe a video, get a video" — that produces mush. The model is
**lock one variable, vary one variable**: lock the subject (via reference
image or Soul ID), lock the camera (via preset), then write a prompt that
only describes the *one beat* of action that happens during the move.

Three locked dimensions, one free dimension:

- **Identity** locked by the reference image or Soul ID.
- **Aesthetic** locked by the Soul preset (or style tokens in the prompt).
- **Camera** locked by the camera-move preset.
- **Action** is the only thing the prompt describes — and it should be
  one verb, one beat, timed to the duration of the camera move.

Internalize this and Higgsfield's quirks make sense:
- "Why is my prompt being ignored?" → you over-described the camera; the
  preset already owns the camera. Delete that half of the prompt.
- "Why does the subject morph?" → no reference image, no Soul ID, identity
  unlocked.
- "Why is the motion so weak?" → you wrote a paragraph; Higgsfield rewards
  short, verb-led, single-beat prompts.

## Gotchas

- **No public API.** Anything that says "call the Higgsfield API from EOS"
  is wrong. cloud.higgsfield.ai exists but is undocumented and not a
  product surface. Drafting prompts for Antony is the only valid agent path.
- **Credits expire after 90 days.** Top-up packs disappear. Don't tell
  Antony to bulk-buy credits "to save money" — they rot.
- **Model routing changes pricing silently.** Kling 3.0 ≈ 6 credits,
  Sora 2 / Veo 3.1 ≈ 40–70 credits per generation. Always note the model
  in the handoff so he picks the right one.
- **Camera-move preset overrides prompt camera language.** If you also write
  "camera slowly zooms in" in the prompt body, you double-up and get jitter.
  Camera lives ONLY in the preset line.
- **Soul presets stack badly.** More than 2–3 style tokens overpower
  identity. Pare back to: lighting + lens + palette + era. That's it.
- **5s default is real.** Most DoP outputs are 5s clips. Plan shot lists
  as 5s beats, not 30s scenes. Use Mix to stitch.
- **Speak needs clean audio.** Background noise in the VO destroys lip sync.
- **Free tier = 10 credits/day.** Useless for production.
- **No webhooks, no callbacks.** EOS cannot be notified when a render
  finishes. Fire-and-forget; Antony reports back manually.
- **Reference-image aspect ratio sets output aspect ratio.** Want 9:16 for
  Reels? Feed a 9:16 source frame. The model will not recompose.
- **Veo 3 / Sora 2 routing has content filters Higgsfield doesn't surface
  in the UI.** If a generation silently fails, fall back to Kling 3.0.
- **GUI changes ship weekly.** Re-research this skill if a preset name in
  the catalog stops matching what's in the UI.

See references/best_practices.md for the full 19-section creator-level
knowledge base, the complete 50+ camera-move catalog with usage notes,
the Soul preset reference, and the EOS prompt-pattern library.
