---
name: remotion
description: "Use when creating programmatic videos in React, building branded video templates, rendering short-form content, or generating social media clips with code."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://remotion.dev/docs"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "4.0"
sdk_version: "remotion 4.0.436"
speed_category: slow
trigger: both
effort: high
context: fork
---

# Tool: Remotion

## What This Tool Does

Remotion is a framework for creating videos programmatically using React. Every frame
of video is a React component rendered at a specific point in time. You write JSX,
style with CSS/Tailwind, animate with `useCurrentFrame()` and `interpolate()`, and
Remotion renders each frame into a video file (MP4, WebM, GIF, or image sequences).

Core capabilities used by EOS:
- **Compositions** -- define video dimensions, duration, fps, and the React component to render
- **Frame-based animation** -- `useCurrentFrame()` + `interpolate()` + `spring()` drive all motion
- **Sequencing** -- `<Sequence>`, `<Series>`, `<TransitionSeries>` for timeline orchestration
- **Media embedding** -- `<Video>`, `<Audio>`, `<Img>`, `<Gif>` components with auto-loading guarantees
- **Parametric video** -- Zod schemas make compositions data-driven with visual editors in Studio
- **Captions and subtitles** -- `@remotion/captions` for transcription, SRT import, and styled display
- **Transitions** -- fade, slide, wipe, flip, clock-wipe with linear or spring timing
- **Server-side rendering** -- CLI (`npx remotion render`) or Node.js API for headless rendering
- **Lambda rendering** -- `@remotion/lambda` for serverless cloud rendering on AWS
- **Tailwind CSS** -- `@remotion/tailwind-v4` integration via webpack override
- **Google Fonts** -- `@remotion/google-fonts` with type-safe loading and render-blocking

## EOS Integration

### Current state
EOS has a Remotion project scaffolded at `knowledge/skills/marketing/content/remotion/`.
It uses Remotion 4.0.436, React 19, Tailwind v4, and TypeScript 5.9.

The project contains:
- `src/Root.tsx` -- RemotionRoot with a single placeholder `MyComp` composition (1280x720, 30fps, 60 frames)
- `src/Composition.tsx` -- empty component returning null
- `src/index.ts` -- `registerRoot(RemotionRoot)`
- `remotion.config.ts` -- JPEG output format, overwrite enabled, Tailwind webpack override
- Extensive rules library at `.agents/skills/remotion-best-practices/rules/` (40+ rule files)

### Planned integration
Remotion will be used for:
1. **Short-form social content** -- Reels, TikTok, YouTube Shorts for Initiate Arena and personal brand
2. **Branded video templates** -- parameterized compositions driven by JSON data from EOS agents
3. **AI-generated clips** -- ElevenLabs voiceover + dynamic captions + branded overlays
4. **Thumbnail generation** -- `<Still>` compositions for YouTube/social thumbnails

### Architecture pattern
```
EOS Agent (Python) --> generates JSON props
  --> Node.js script passes props to Remotion CLI
    --> npx remotion render --props='{"title":"..."}' src/index.ts MyComp out.mp4
  --> Output uploaded to social platforms via existing EOS pipelines
```

For Lambda (future): Python calls AWS Lambda via boto3, Remotion Lambda function renders and returns S3 URL.

## Authentication

### Remotion license
Remotion is source-available under a custom license:
- **Free** for individuals and companies with fewer than 3 developers working on Remotion code
- **Company License required** for 3+ developers -- purchased at remotion.dev/license
- No API key or token needed for the framework itself
- License is validated at build time, not runtime

### AWS credentials (Lambda rendering only)
When using `@remotion/lambda`:
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in environment
- IAM role with permissions for Lambda, S3, CloudWatch, and STS
- Region must match the deployed Lambda function

### ElevenLabs (voiceover)
- `ELEVENLABS_API_KEY` in environment for AI voiceover generation
- Used by the voiceover generation script, not by Remotion itself

## Quick Reference

### Define a composition
```tsx
import { Composition } from "remotion";
import { MyVideo } from "./MyVideo";

export const RemotionRoot = () => (
  <Composition
    id="MyVideo"
    component={MyVideo}
    durationInFrames={300}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ title: "Hello" }}
  />
);
```

### Animate with useCurrentFrame
```tsx
import { useCurrentFrame, useVideoConfig, interpolate } from "remotion";

export const FadeIn = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const opacity = interpolate(frame, [0, 1 * fps], [0, 1], {
    extrapolateRight: "clamp",
  });
  return <div style={{ opacity }}>Hello</div>;
};
```

### Spring animation
```tsx
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

const frame = useCurrentFrame();
const { fps } = useVideoConfig();
const scale = spring({ frame, fps, config: { damping: 200 } });
```

### Sequence and Series
```tsx
import { Sequence, Series } from "remotion";

// Delay appearance
<Sequence from={30} durationInFrames={60} premountFor={30}>
  <Title />
</Sequence>

// Sequential playback
<Series>
  <Series.Sequence durationInFrames={60}><Intro /></Series.Sequence>
  <Series.Sequence durationInFrames={90}><Main /></Series.Sequence>
  <Series.Sequence durationInFrames={30}><Outro /></Series.Sequence>
</Series>
```

### Embed media
```tsx
import { Img, staticFile } from "remotion";
import { Video, Audio } from "@remotion/media";

<Img src={staticFile("logo.png")} />
<Video src={staticFile("clip.mp4")} volume={0.5} />
<Audio src={staticFile("music.mp3")} loop />
```

### Render from CLI
```bash
# Preview in browser
npx remotion studio

# Render to file
npx remotion render src/index.ts MyComp output.mp4

# Render with custom props
npx remotion render src/index.ts MyComp output.mp4 --props='{"title":"Custom"}'

# Render a still image
npx remotion still src/index.ts Thumbnail thumbnail.png
```

### Parametric video with Zod
```tsx
import { z } from "zod";
export const Schema = z.object({ title: z.string(), color: zColor() });

// In Root.tsx
<Composition
  id="MyComp"
  component={MyComp}
  schema={Schema}
  defaultProps={{ title: "Default", color: "#ff0000" }}
  ...
/>
```

### Transitions
```tsx
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";

<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={60}><SceneA /></TransitionSeries.Sequence>
  <TransitionSeries.Transition
    presentation={fade()}
    timing={linearTiming({ durationInFrames: 15 })}
  />
  <TransitionSeries.Sequence durationInFrames={60}><SceneB /></TransitionSeries.Sequence>
</TransitionSeries>
```

## Conceptual Model

```
Remotion Framework
  |
  +-- Composition (blueprint)
  |     |-- id, width, height, fps, durationInFrames
  |     |-- component: React.FC that receives props
  |     |-- schema: Zod schema for parametric input
  |     +-- calculateMetadata: async function for dynamic config
  |
  +-- Frame Rendering (core loop)
  |     |-- useCurrentFrame() --> current frame number (0-based)
  |     |-- useVideoConfig() --> { fps, width, height, durationInFrames }
  |     |-- interpolate(frame, inputRange, outputRange, options)
  |     +-- spring({ frame, fps, config }) --> 0-to-1 physics animation
  |
  +-- Timeline (sequencing)
  |     |-- <Sequence from={n} durationInFrames={n}> -- position in time
  |     |-- <Series> -- sequential playback
  |     +-- <TransitionSeries> -- scenes with transitions
  |
  +-- Media (assets)
  |     |-- staticFile("path") -- reference public/ folder assets
  |     |-- <Img>, <Video>, <Audio> -- render-safe media components
  |     +-- <Gif> from @remotion/gif -- synchronized GIF playback
  |
  +-- Output (rendering)
        |-- remotion studio -- browser preview with hot reload
        |-- remotion render -- local headless rendering
        |-- remotion still -- single frame export
        |-- @remotion/renderer -- Node.js API (renderMedia, renderStill)
        +-- @remotion/lambda -- serverless rendering on AWS
```

Key mental model: Remotion is NOT a video editor. It is a **video compiler**.
You write React components that describe what each frame looks like, and Remotion
visits every frame, screenshots it, and stitches the screenshots into a video.
CSS transitions, requestAnimationFrame, and setTimeout do not work because there
is no real passage of time -- only discrete frame numbers.

See references/best_practices.md for complete API signatures, rate limits, and anti-patterns.

## Gotchas

### CSS animations and transitions do not work
Remotion renders each frame independently. CSS `transition`, `animation`, `@keyframes`,
and Tailwind `animate-*` / `transition-*` classes produce incorrect output or no animation
at all. All animation MUST go through `useCurrentFrame()` + `interpolate()` or `spring()`.

### useCurrentFrame() is local inside Sequence
Inside a `<Sequence from={60}>`, `useCurrentFrame()` returns 0 on the first visible frame,
not 60. This is intentional -- components are reusable regardless of where they sit in the
timeline. If you need the global frame, do not wrap in a Sequence.

### Always premount Sequences
Without `premountFor`, a `<Sequence>` component mounts cold on its first frame. If the
component fetches data or loads fonts, the first frame renders incomplete. Always use
`<Sequence premountFor={1 * fps}>` to warm up components before they appear.

### Img vs img -- always use Remotion's Img
Native `<img>` elements do not block rendering. During export, the frame may render before
the image loads, producing blank frames. Always use `<Img>` from `remotion`, `<Video>` from
`@remotion/media`, etc. These components block the render until the asset is ready.

### interpolate does not clamp by default
`interpolate(frame, [0, 100], [0, 1])` returns values outside [0, 1] when frame > 100.
This causes opacity > 1, scale overshoot, etc. Always pass
`{ extrapolateRight: "clamp", extrapolateLeft: "clamp" }` unless you intentionally want
unbounded extrapolation.

### TransitionSeries shortens total duration
A 15-frame transition between two 60-frame scenes produces 105 frames total, not 120.
The transition overlaps both scenes. Calculate total duration as
`sum(sceneDurations) - sum(transitionDurations)`.

### Pitch shifting only works in rendering
`toneFrequency` on `<Video>` and `<Audio>` only works during server-side rendering.
It has no effect in the Studio preview or in the `<Player>` component.

### staticFile paths are case-sensitive
`staticFile("Logo.png")` and `staticFile("logo.png")` resolve to different files.
On macOS (case-insensitive filesystem) this works locally but breaks in Docker/Linux CI.

### React 19 compatibility
The EOS Remotion project uses React 19.2.3. Some older Remotion examples use
`React.FC<Props>` patterns that work but newer patterns prefer direct prop typing.
Ensure `@types/react` matches the React version.
