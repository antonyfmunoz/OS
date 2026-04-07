# Higgsfield AI — Creator-Level Best Practices
Source: higgsfield.ai, higgsfield.ai/camera-controls, higgsfield.ai/soul,
        higgsfield.ai/pricing, higgsfield.ai/blog, segmind.com Higgsfield guide,
        chasejarvis.com Higgsfield Soul writeup, hackceleration.com review
API Version: Higgsfield web product (no public REST API as of 2026-04)
SDK Version: N/A — GUI / human-operator tool
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

**N/A — GUI tool.** Higgsfield is consumed exclusively through the browser
at higgsfield.ai. There is no public API key, no OAuth client, no service
account, no webhook signing secret. The only credential surface is Antony's
account login (email + password, optional 2FA) and the resulting browser
session cookie. EOS agents do not authenticate to Higgsfield and must never
claim to. The "auth" the agent cares about is **whose account is paying**:
confirm Antony is logged in on his paid tier before drafting prompts that
assume access to Sora 2 / Veo 3 routing or Soul ID.

Note: `cloud.higgsfield.ai` exists as an undocumented endpoint with anecdotal
reports of REST job submission and webhook callbacks, but it has no public
docs, no SLA, no rate-limit table, and no stable contract. Treating it as a
real API is a foot-gun. If a public API ever ships officially, this entire
section gets rewritten.

## Core Operations with Exact Signatures

Higgsfield "operations" are GUI actions, not function calls. The exact
"signature" of each operation is the set of UI fields the operator fills in.
Document those fields the way you would document function parameters.

### Operation: Soul — Generate Photo

```
Surface:    higgsfield.ai → Soul tab
Inputs:
  preset:        one of 50+ aesthetic presets (or "None")
  prompt:        free text, short and direct
  reference:     optional image (Soul ID identity)
  aspect_ratio:  1:1 | 4:5 | 16:9 | 9:16
  count:         1–4 variations
Output:     PNG/JPG still(s) at 1024–2048px
Cost:       ~1–2 credits per image
```

### Operation: DoP — Image-to-Video

```
Surface:    higgsfield.ai → DoP tab → Image-to-Video
Inputs:
  reference_image: REQUIRED — sets identity, composition, aspect ratio
  prompt:          one beat of action, 1–3 sentences
  camera_preset:   one of 50+ camera-move presets (or "None")
  motion_strength: low | medium | high
  duration:        3 | 5 | 8 | 10 | 15 seconds
  resolution:      720p | 1080p
  model_route:     Higgsfield DoP | Kling 2.5 | Kling 3.0 | Veo 3 | Sora 2 | WAN
  seed:            optional integer for reproducibility
Output:     MP4 clip
Cost:       6 credits (Kling 3.0) → 70 credits (Sora 2 / Veo 3.1)
```

### Operation: DoP — Text-to-Video

```
Surface:    higgsfield.ai → DoP tab → Text-to-Video
Inputs:
  prompt:          full scene description (subject + action + style + camera)
  camera_preset:   optional but strongly recommended
  duration:        3 | 5 | 8 | 10 | 15 seconds
  resolution:      720p | 1080p
  model_route:     same routing list as image-to-video
Output:     MP4 clip
Cost:       same routing-dependent table
```

### Operation: Speak — Talking Avatar

```
Surface:    higgsfield.ai → Speak (or Speak 2.0)
Inputs:
  portrait_image:  REQUIRED — front-facing, eyes open, no occlusion
  audio_file:      REQUIRED — clean VO, mono, dry, no music bed
  lip_sync:        on | off
  head_motion:     none | subtle | natural | expressive
  background:      static | subtle motion
  resolution:      720p | 1080p
Output:     MP4, length = audio length
Cost:       ~10–25 credits depending on length
```

### Operation: Mix — Multi-Shot Stitch

```
Surface:    higgsfield.ai → Mix
Inputs:
  shots:           ordered list of 2–6 generated DoP clips
  transitions:     hard cut | match cut | dissolve
  audio_track:     optional music or VO
Output:     stitched MP4, 10–60s
Cost:       free if reusing already-generated clips
```

### Operation: Soul ID — Identity Training

```
Surface:    higgsfield.ai → Soul → Train Identity
Inputs:
  identity_name:   string
  training_images: 8–20 photos of subject, varied angles and lighting
Output:     reusable identity token, attachable to any future Soul/DoP gen
Cost:       one-time credit fee, then free to reuse
```

## Configuration Patterns

There is no config file. "Configuration" means the consistent set of
defaults Antony uses across runs. Document them in his project folders:

```
brand-presets/personal-brand/higgsfield.md
  default_camera_preset:  Crash Zoom In
  default_soul_preset:    Editorial
  default_aspect:         9:16   (Reels / TikTok / Shorts)
  default_duration:       5s
  default_model:          Kling 3.0   (cost-efficient default)
  fallback_model:         Higgsfield DoP native

brand-presets/lyfe-spectrum/higgsfield.md
  default_camera_preset:  Lazy Susan
  default_soul_preset:    Glam
  default_aspect:         1:1    (product hero)
  default_duration:       5s
  default_model:          Kling 3.0

brand-presets/empyrean-studio/higgsfield.md
  default_camera_preset:  Bullet Time
  default_soul_preset:    Film Noir
  default_aspect:         16:9   (cinematic pitch)
  default_duration:       8s
  default_model:          Veo 3   (when budget allows)
```

The agent reads these on every Higgsfield handoff and applies them unless
the brief overrides.

## Error Handling

GUI tool, so errors arrive as UI states, not exceptions. The catalog the
agent should know:

- **Generation queued indefinitely** → server load. Wait 2–5 min, do not
  re-submit (you'll burn credits twice).
- **"Content policy violation"** → silent on DoP, explicit on Veo/Sora
  routes. Strip references to brands, weapons, real public figures, NSFW
  language. Re-route through Kling.
- **"Identity drift"** → subject's face morphs mid-clip. Cause: no Soul ID
  or weak reference frame. Fix: re-generate with stronger reference or
  train Soul ID.
- **Black frame / corrupt MP4 download** → known intermittent CDN issue.
  Re-download from the History tab; do not re-generate.
- **"Insufficient credits"** → block. Agent must NOT silently substitute a
  cheaper model — flag to Antony with the cost delta.
- **Soul preset returns wildly off-brief** → preset and prompt fighting.
  Drop the preset, restate aesthetics in prompt body.
- **Speak lip sync drifts** → audio too long (>30s), or audio has music
  underneath. Cut audio into <15s chunks, run separately, stitch in Mix.

## Webhooks / Events

N/A. Higgsfield does not expose a webhook system to end users. There is
no event bus, no completion callback, no "render finished" signal that
EOS can subscribe to. The only completion signal is Antony seeing the
clip appear in his History tab. Build all EOS pipelines around this
fire-and-forget reality: never write code that "waits for Higgsfield to
finish" — there is nothing to wait on programmatically.

## Rate Limits

N/A in the API sense — there is no rate-limited API. The functional limits
that matter:

- **Concurrent jobs** — free tier 1, paid tiers 2–5 depending on plan.
  Antony's plan should be confirmed; assume 2–3 concurrent unless told.
- **Daily credit floor** — free tier 10 credits/day, paid tiers no daily
  cap (just monthly allotment).
- **Credit expiry** — 90 days from purchase. Top-ups rot.
- **Generation queue depth** — soft, model-dependent. Sora 2 queues are
  the longest (often 5–15 min); Kling 3.0 is usually <60s.

The agent should pace shot lists: do not draft a 30-shot batch and tell
Antony to fire them all at once on a 2-concurrent plan. Sequence in
groups of 2–3.

## Pagination / Streaming

N/A. There is no list endpoint, no cursor, no streaming response. The
History tab in the UI is the only "list" surface and it paginates client-
side. If Antony needs to find an old generation, he scrolls or uses the
Search field in the History tab.

## SDK Idioms

N/A — there is no SDK in any language. There are unofficial third-party
wrappers (one MCP server on GitHub: `geopopos/higgsfield_ai_mcp`, plus
n8n / Make.com community connectors that scrape the web UI) but none are
sanctioned, none are stable, and EOS should not depend on any of them
without explicit Antony approval. The "idiomatic" way to use Higgsfield
from EOS is: agent drafts prompt → Antony pastes into browser → Antony
saves output to brand folder → agent references the saved file in
downstream work.

---

# Tier 2 — The Camera-Move Catalog (Core Skill)

This is the heart of the tool. Higgsfield's signature is the named camera
preset, and creator-level mastery means knowing which preset fits which
narrative beat. The full 50+ catalog with usage guidance:

## Push / Pull (subject-anchored translation)

- **Crash Zoom In** — rapid emphasis, surprise, revelation, urgency. The
  default hook for "moment of realization" beats. Subject locked, lens
  punches in fast. Best for face reactions, product reveals.
- **Crash Zoom Out** — sudden context drop, "oh no" reveal, scale shock.
  Use when the joke or stakes live in the wider frame.
- **Super Dolly In** — slow, weighted push toward subject. Gravitas.
  Use for "founder explains the thesis" cinematic openings.
- **Super Dolly Out** — slow weighted pull. Loneliness, scale, finality.
- **Dolly In / Dolly Out** — gentler versions of Super Dolly. Use for
  conversational pacing.
- **Double Dolly** — push then pull within a single clip. Pendulum feel,
  for hesitation or revelation-then-retreat.
- **Rapid Zoom In / Out** — like Crash Zoom but with optical-zoom feel
  rather than physical dolly. Snappier, more "TV news" energy.
- **Through Object In / Out** — camera passes through a foreground
  object (window, doorway, glass). Reveals, transitions between scenes.

## Dolly Zoom (Vertigo)

- **Dolly Zoom In** — physical push + optical zoom-out. Background
  collapses around static subject. Disorientation, dread, realization.
  The Spielberg signature. Use sparingly — overused becomes parody.
- **Dolly Zoom Out** — physical pull + optical zoom-in. Background
  rushes in. Use for "the world closes in" beats.
- **YoYo Zoom** — oscillating dolly zoom. Trippy, anxiety. Use for
  drug/dream sequences or hyper-stylized fashion.

## Orbits & Arcs

- **360 Orbit** — full lateral revolution around subject. The product-
  reveal default. Locks subject identity, shows all angles.
- **Lazy Susan** — subject rotates on a turntable, camera static. Inverse
  of 360 Orbit. Best for products where the BACKGROUND should stay still.
  THE Lyfe Spectrum apparel preset.
- **Arc Left / Arc Right** — partial orbit. Use for half-reveals, profile
  transitions.
- **Robo Arm** — programmatic motion-control rig style. Geometric, fast,
  precision. Looks like a Bot & Dolly demo. Tech / luxury / automotive.

## Crane / Vertical

- **Crane Up** — rises off subject toward sky. Endings, transitions,
  "and then he walked away" beats.
- **Crane Down** — descends from sky onto subject. Openings, arrivals.
- **Crane Over The Head** — overhead pass. Establishing, omniscient.
- **Jib Up / Jib Down** — gentler crane. Conversational, less cinematic.
- **Tilt Up / Tilt Down** — fixed-position vertical pivot. Reveal of tall
  subject (skyscraper, person standing up).

## Handheld / Energy

- **Handheld** — natural human-operator wobble. Documentary feel.
- **FPV Drone** — first-person-view drone, agile, fast, energetic. Action
  sequences, chase, swoops through architecture. The TikTok signature.
- **Snorricam** — camera rigged to subject's body, subject appears static
  while the world moves around them. Disorienting, character-locked,
  walking shots that feel like the world is the thing in motion.
- **Whip Pan** — violently fast pan, transition device, "what just
  happened" energy.
- **Wiggle** — small jittery shake. Comedic emphasis, glitch aesthetic.

## Specialty / Stylized

- **Bullet Time** — frozen-moment circular pan around subject. The Matrix
  signature. Use for HERO beats only — it screams "look at me" and burns
  novelty fast.
- **Hero Cam** — low-angle hero framing, locked on subject, slight push.
  The "founder reveal" preset. Use for personal-brand intros.
- **Glam** — slow, sensual, high-fashion drift. Beauty / fashion / luxury.
- **Mouth In** — extreme push into subject's mouth. Visceral, weird,
  rarely useful — but unforgettable when it fits.
- **Eating Zoom** — push during eating action, food close-up beat.
- **Object POV** — camera mounted on a moving object's perspective.
- **Fisheye** — extreme wide-angle distortion. Skate / 90s hip-hop.
- **Dutch Angle** — tilted horizon. Unease, instability.
- **Focus Change** — rack focus between foreground and background subject.
  Conversational reveal.

## Vehicle / Action

- **Car Chasing** — vehicle pursuit framing, locked on a moving car.
- **Car Grip** — camera rigged to a car body, exterior vehicle motion.
- **Buckle Up** — interior driver POV, fastening seatbelt → drive.
- **Road Rush** — speed-blur road forward motion.
- **Flying Cam Transition** — drone pass-through used as scene cut.

## Time Manipulation

- **Hyperlapse** — accelerated motion through space, walking/driving
  through environments at high speed.
- **Timelapse Glam** — fashion timelapse, outfit changes, hair, makeup.
- **Timelapse Human** — person aging or repeating action across time.
- **Timelapse Landscape** — environment over hours/days.
- **Low Shutter** — long-exposure motion blur on a still subject.

## Static / Reference

- **Static** — camera does not move. Use when the subject's motion is the
  story and the camera should disappear. Often the BEST choice — the
  most cinematic move is no move at all.
- **BTS** — behind-the-scenes documentary framing.
- **Pan Left / Pan Right** — basic horizontal pan.
- **Head Tracking** — camera follows subject's head movement.
- **Incline** — angled approach toward subject.

## Picking the right preset (decision tree)

```
Is the subject a person?
├── YES → Is this a hero/intro shot?
│         ├── YES → Hero Cam | Crash Zoom In | Bullet Time (sparingly)
│         └── NO  → Is the person walking/moving?
│                   ├── YES → Snorricam | Handheld | FPV Drone
│                   └── NO  → Static | Super Dolly In | Dolly Zoom In
└── NO  → Is the subject a product?
          ├── YES → Lazy Susan | 360 Orbit | Robo Arm
          └── NO  → Is it a place/environment?
                    ├── YES → FPV Drone | Crane Down | Hyperlapse
                    └── NO  → Static | Through Object In
```

---

# Tier 3 — Soul Aesthetic Presets

Soul presets define the *look* of the still, which then becomes the input
frame for DoP. The 50+ catalog organized by family:

- **Editorial / Fashion** — Editorial, Fashion Editorial, Glam, Coquette,
  Vogue, Runway, Lookbook, Cover Story
- **Era / Period** — Y2K, 90s, 70s, Medieval, Victorian, Polaroid, Film Noir
- **Place / Subculture** — Tokyo Street Style, Parisian, NYC, LA, Berlin
- **Device / Format** — iPhone, Polaroid, Disposable, Webcam, CCTV, Fisheye
- **Lighting / Mood** — Low Key, High Key, Golden Hour, Blue Hour, Neon
- **Material / Texture** — Cinematic, Matte, Glossy, Grain Heavy

Stacking rule: **one preset + 2–4 modifier tokens.** Exceeding this drowns
identity. Example correct stack:

```
Preset: Editorial
Modifiers: low-key lighting, 35mm anamorphic, teal-and-amber grade,
shallow depth of field
```

Example BROKEN stack (do not do):

```
Preset: Editorial + Glam + Fashion Editorial
Modifiers: cinematic, dramatic, moody, sexy, high fashion, vogue cover,
runway, golden hour, blue hour, neon, anamorphic, 35mm, 50mm, 85mm,
shallow DOF, deep DOF, teal-and-amber, desaturated, vibrant
```

---

# Tier 4 — Prompt Engineering

## The Higgsfield Prompt Formula

```
[Subject] + [One Beat] + [Camera Move] + [Style Tokens]
```

- **Subject** = one sentence locking who/what is in frame.
- **One Beat** = ONE strong verb describing ONE action that happens during
  the camera move's duration. Not three actions. Not a paragraph.
- **Camera Move** = the named preset, on its own line. Do not also
  describe the camera in the body of the prompt.
- **Style Tokens** = 2–4 modifiers: lighting + lens + palette + era.

## Why short prompts beat long ones

Higgsfield rewards direct commands and punishes descriptive paragraphs.
Long prompts force the model to guess which clauses are aesthetic vs
which are action vs which are camera direction. Short prompts collapse
ambiguity. The official Higgsfield blog confirms: "short prompts produce
stronger control than long ones."

Worked comparison:

BAD (long, ambiguous):
```
A handsome young entrepreneur sitting at his desk in a beautiful modern
office with lots of natural light streaming through the windows, looking
thoughtfully at his laptop screen as he types away on an important project,
with the camera slowly moving in toward his face as he looks up and smiles
warmly at the camera while the soft afternoon light creates a beautiful
cinematic atmosphere with shallow depth of field and a teal and orange
color grade reminiscent of modern Hollywood films.
```

GOOD (short, tight):
```
A founder at a black desk, hands on keyboard.
He looks up sharply.
Camera: Crash Zoom In
Style: low-key, 35mm anamorphic, teal-and-amber, shallow DOF.
```

The bad version contains six actions, two camera directions, and stacks
six aesthetic claims. Higgsfield will average them all and produce mush.
The good version contains one action, one camera move, four aesthetic
tokens. Higgsfield executes it cleanly.

## Multi-shot scene structure

For 2–6 shot sequences (use Mix to stitch), structure as:

```
Shot 1 (5s) — [Camera A] — [Beat 1]
Shot 2 (5s) — [Camera B] — [Beat 2]
Shot 3 (5s) — [Camera C] — [Beat 3]
```

Vary the camera preset across shots. Repetition kills cinematic feel —
three Crash Zoom Ins in a row read as a glitch, not a sequence.

---

# Tier 5 — Pricing & Routing Strategy

## Plan tiers (2026-04, subject to change)

- **Free** — 10 credits/day, 1 concurrent job, basic models. Useless for
  production.
- **Basic** — $9/mo, 150 credits/mo
- **Pro** — $17.40/mo, 600 credits/mo
- **Ultimate** — $29.40/mo, 1200 credits/mo
- **Creator** — $119/mo, 6000 credits/mo

Note: alternate tier names appear in some sources (Starter $15, Plus $34,
Ultra $84, Business $49/seat). Pricing is in flux. Confirm with Antony
which plan is active before promising specific output volumes.

## Per-generation cost (model routing)

```
Kling 3.0           ~6 credits     ← cost-efficient default
Kling 2.5 Turbo     ~8 credits
Higgsfield DoP      ~10 credits
Veo 3 / Veo 3.1     40–70 credits  ← premium, gated
Sora 2              40–70 credits  ← premium, gated
WAN                 ~15 credits
Soul (image)        1–2 credits
Speak (per second)  ~2 credits/sec
```

## Routing decision

```
Budget priority?      → Kling 3.0
Realism priority?     → Veo 3
Physics / motion?     → Sora 2
Cinematic / camera?   → Higgsfield DoP native
Speed priority?       → Kling 2.5 Turbo
```

---

# Tier 6 — EOS Usage Patterns

## Pattern 1: Personal brand hook shot

```
TRIGGER:  Antony asks for a 5s opening hook for a piece of brand content.

INPUTS:   topic line + reference photo of him (or describe him)

DRAFT:
  Reference: [photo path]
  Prompt:    [one sentence subject] + [one verb beat]
  Camera:    Crash Zoom In  (or Hero Cam if intro)
  Style:     low-key, 35mm anamorphic, teal-and-amber, shallow DOF
  Model:     Kling 3.0
  Duration:  5s
  Aspect:    9:16
  Cost:      ~6 credits
```

## Pattern 2: Lyfe Spectrum product drop

```
TRIGGER:  Apparel drop announcement, hero clip needed.

INPUTS:   product photo (or product description)

DRAFT:
  Reference: [product photo]
  Prompt:    [garment description] + [rotation or reveal beat]
  Camera:    Lazy Susan  (rotation) or Robo Arm (geometric reveal)
  Style:     Glam preset, hard rim light, matte texture, no people
  Model:     Kling 3.0
  Duration:  5s
  Aspect:    1:1 or 9:16
  Cost:      ~6 credits
```

## Pattern 3: Empyrean Studio pitch reel beat

```
TRIGGER:  Client pitch deck, cinematic mood beat needed.

INPUTS:   client brief + tone reference

DRAFT:
  Camera:    Bullet Time | Dolly Zoom In | FPV Drone (depending on tone)
  Style:     Film Noir | Cinematic | matched to client palette
  Model:     Veo 3  (if budget allows) or Higgsfield DoP native
  Duration:  8s
  Aspect:    16:9
  Cost:      40–70 credits
```

## Pattern 4: Speak talking-head explainer

```
TRIGGER:  Antony has a script he wants delivered as a talking-head clip
          without filming himself.

INPUTS:   script text + portrait reference

STEP 1 — Generate portrait via Soul:
  Preset:    Editorial
  Prompt:    [Antony description], front-facing, neutral background
  Output:    1080x1920 PNG

STEP 2 — Record VO (Antony, dry, mono, no music)

STEP 3 — Speak 2.0:
  Portrait:    [Soul output]
  Audio:       [VO file]
  Lip sync:    on
  Head motion: subtle
  Background:  static
  Duration:    matches audio
```

## Pattern 5: Multi-shot Mix sequence

```
TRIGGER:  30s brand video needed.

DRAFT:    6 × 5s shots, each with different camera preset, stitched in Mix.

Shot 1 — Hero Cam     — Antony sits down at desk
Shot 2 — Crash Zoom   — He opens the laptop
Shot 3 — Static       — Close-up on hands typing
Shot 4 — Lazy Susan   — Coffee cup rotates on desk
Shot 5 — Dolly Zoom   — He looks up at the camera
Shot 6 — Crane Up     — Pull away from desk, room reveals

Stitch in Mix with hard cuts. Total: 30s.
Cost: 6 × 6 = 36 credits.
```

---

# Tier 7 — Gotchas (Full Catalog)

- **No public API.** Do not write EOS code that calls Higgsfield. The
  cloud.higgsfield.ai endpoint is undocumented and not a product.
- **Credits expire after 90 days.** Top-up packs rot. Never recommend
  bulk purchases for "savings."
- **Model routing changes pricing 10×.** Always state model + cost in
  the handoff. A 5-shot sequence on Kling 3.0 is 30 credits; on Sora 2
  it's 350.
- **Camera-move preset overrides prompt camera language.** Never describe
  the camera in the prompt body when a preset is selected. Doubling up
  produces jitter or fights.
- **Soul preset stacking destroys identity.** Max one preset + 2–4
  modifier tokens.
- **5s is the practical default.** Plan in 5s beats. Use Mix to stitch.
- **Speak audio must be dry.** Music bed under VO destroys lip sync.
- **Free tier is a demo, not a tool.** 10 credits/day, 1 concurrent job.
  Useless for production work.
- **No webhooks.** EOS cannot be notified of completion. Fire-and-forget
  handoffs only.
- **Reference image aspect ratio sets output aspect ratio.** Want 9:16?
  Feed 9:16. The model does not recompose.
- **Veo 3 / Sora 2 have hidden content filters.** Silent failures route
  through these models. Fall back to Kling 3.0.
- **GUI ships weekly.** Re-research this skill if a preset name no longer
  matches the UI.
- **Identity drift without Soul ID.** Subject's face morphs across long
  clips. Fix: train Soul ID once, reuse.
- **Long prompts produce weak motion.** Higgsfield rewards short, verb-led,
  single-beat prompts. Paragraphs produce mush.
- **Bullet Time burns novelty.** Use 1× per project max. Overused = parody.
- **Dolly Zoom is the same.** It is the most-cliché preset in the catalog.
  Reach for it sparingly.
- **Static is underrated.** The most cinematic move is often no move. When
  the subject's action is the story, lock the camera and let it breathe.
- **Mix stitching is forgiving but not magic.** Match cuts require matched
  framing. Plan adjacent shots with shared composition.
- **History tab is the only "list."** No search by tag, no sort by cost.
  Antony's archive discipline matters — he must save outputs to brand
  folders immediately or they get lost in the History scroll.
- **Account-bound, not org-bound.** No team workspace at most tiers.
  All generations live in Antony's personal account. Cannot hand off
  to a collaborator without sharing credentials.
- **Mobile UI is a subset of desktop.** Some presets and models hidden
  on mobile. Antony should generate on desktop / iPad code-server, not
  iPhone.
- **Browser memory matters.** Long Soul / DoP sessions leak memory in
  Chrome. Refresh every 30–45 min if outputs start getting weird.
- **Re-research trigger.** If any of: a preset disappears, pricing
  changes by >25%, a new model is added to routing, Higgsfield ships an
  official API. Update last_researched in SKILL.md frontmatter and bump
  this file.

---

# Tier 8 — When to Escalate to Antony

The agent drafts. Antony decides. Always escalate when:

- The shot list exceeds 10 generations (cost compounds fast)
- A preset choice involves brand identity calls (Vigilante Architect tone)
- A Veo 3 / Sora 2 generation is being recommended (40–70 credits each)
- The reference image doesn't exist yet (Antony has to shoot or source)
- The output is destined for paid ad creative (legal/IP review)
- Speak is being used to make Antony "say" something he didn't actually
  write or approve (this is a hard stop — never put words in his mouth
  via Speak without explicit prompt-level approval)

---

# Tier 9 — Verification

After drafting any Higgsfield handoff, the agent must verify:

- [ ] Camera preset name matches the catalog above
- [ ] Soul preset (if used) is one preset, not stacked
- [ ] Style tokens are 2–4 modifiers, not a paragraph
- [ ] Model + credit cost stated explicitly
- [ ] Aspect ratio matches the destination platform
- [ ] Duration is realistic for the camera move (5s default)
- [ ] No camera language in the prompt body (preset owns it)
- [ ] Reference image path or description is provided
- [ ] Brand-preset defaults from the relevant brand folder applied

If any box is unchecked, the handoff is incomplete. Re-draft before
sending to Antony.
