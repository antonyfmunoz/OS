# Remotion -- Creator-Level Best Practices
Source: https://remotion.dev/docs
API Version: 4.0
SDK Version: remotion 4.0.436
Last Researched: 2026-04-06

---

# Tier 1 -- Technical Mastery

## Section 1: Authentication

Remotion itself requires no API key or token. It is a local framework that runs in Node.js.

**License model:**
- Free for individuals and companies with fewer than 3 developers working on Remotion code
- Company License required for 3+ developers (purchased at remotion.dev/license)
- License validation happens at build/render time, not runtime
- No license key is embedded in code -- the license is tied to the GitHub org or npm account

**AWS credentials (Lambda rendering):**
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as environment variables
- IAM policy needs: `lambda:InvokeFunction`, `s3:PutObject`, `s3:GetObject`, `logs:CreateLogGroup`, `sts:GetCallerIdentity`
- Region must match the deployed function region
- Store in `eos_ai/.env` or `services/.env` depending on which service triggers renders

**ElevenLabs (voiceover generation):**
- `ELEVENLABS_API_KEY` in environment
- Used by the voiceover generation script, not by Remotion itself

**Env vars for EOS:**
```
# Lambda rendering (future)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1

# Voiceover
ELEVENLABS_API_KEY=
```

## Section 2: Core Operations with Exact Signatures

### registerRoot (entry point)
```tsx
import { registerRoot } from "remotion";
import { RemotionRoot } from "./Root";
registerRoot(RemotionRoot);
// No return value. Called once in src/index.ts. Registers the root component.
```

### Composition (video blueprint)
```tsx
import { Composition } from "remotion";
<Composition
  id={string}                          // required -- unique identifier
  component={React.ComponentType}      // required -- the React component to render
  durationInFrames={number}            // required -- total frames (positive integer)
  fps={number}                         // required -- frames per second
  width={number}                       // required -- pixels
  height={number}                      // required -- pixels
  defaultProps={object}                // optional -- initial prop values (JSON-serializable)
  schema={ZodSchema}                   // optional -- Zod schema for parametric input
  calculateMetadata={Function}         // optional -- async function for dynamic config
/>
```

### useCurrentFrame
```tsx
import { useCurrentFrame } from "remotion";
const frame: number = useCurrentFrame();
// Returns current frame number (0-based integer).
// Inside a <Sequence from={N}>, returns local frame starting at 0.
```

### useVideoConfig
```tsx
import { useVideoConfig } from "remotion";
const config = useVideoConfig();
// Returns: { fps: number, durationInFrames: number, width: number, height: number, id: string, defaultProps: object }
```

### interpolate
```tsx
import { interpolate } from "remotion";
const value: number = interpolate(
  input: number,                       // required -- typically useCurrentFrame()
  inputRange: [number, number, ...],   // required -- input breakpoints
  outputRange: [number, number, ...],  // required -- mapped output values
  options?: {
    easing?: (t: number) => number,    // default: Easing.linear
    extrapolateLeft?: "extend" | "clamp" | "identity",   // default: "extend"
    extrapolateRight?: "extend" | "clamp" | "identity",  // default: "extend"
  }
);
// Returns: interpolated number
```

### spring
```tsx
import { spring } from "remotion";
const value: number = spring({
  frame: number,                       // required -- current frame
  fps: number,                         // required -- from useVideoConfig()
  config?: {
    damping?: number,                  // default: 10
    mass?: number,                     // default: 1
    stiffness?: number,                // default: 100
    overshootClamping?: boolean,       // default: false
  },
  from?: number,                       // default: 0
  to?: number,                         // default: 1
  delay?: number,                      // default: 0 (frames)
  durationInFrames?: number,           // optional -- stretch to specific duration
  durationRestThreshold?: number,      // default: 0.001
});
// Returns: number (typically 0 to 1, may overshoot without clamping)
```

### Sequence
```tsx
import { Sequence } from "remotion";
<Sequence
  from={number}                        // optional -- frame offset (can be negative to trim)
  durationInFrames={number}            // optional -- unmounts after N frames
  name={string}                        // optional -- label in Studio timeline
  layout={"absolute-fill" | "none"}    // default: "absolute-fill"
  premountFor={number}                 // optional -- mount N frames early for warm-up
  width={number}                       // optional -- for nesting compositions
  height={number}                      // optional -- for nesting compositions
>
  {children}
</Sequence>
```

### Series
```tsx
import { Series } from "remotion";
<Series>
  <Series.Sequence
    durationInFrames={number}          // required
    offset={number}                    // optional -- shift start (negative = overlap)
    layout={"absolute-fill" | "none"}  // default: "absolute-fill"
  >
    {children}
  </Series.Sequence>
</Series>
```

### staticFile
```tsx
import { staticFile } from "remotion";
const url: string = staticFile(path: string);
// Maps a path relative to public/ to a URL usable by Remotion components.
// Handles encoding of special characters (#, ?, &).
```

### Img
```tsx
import { Img } from "remotion";
<Img
  src={string}                         // required -- URL or staticFile() result
  style={CSSProperties}               // optional
  // Blocks rendering until image is loaded. Never use native <img>.
/>
```

### Video (from @remotion/media)
```tsx
import { Video } from "@remotion/media";
<Video
  src={string}                         // required
  volume={number | ((frame: number) => number)}  // optional -- 0 to 1
  playbackRate={number}                // optional -- speed multiplier
  muted={boolean}                      // optional
  loop={boolean}                       // optional
  trimBefore={number}                  // optional -- frames to skip at start
  trimAfter={number}                   // optional -- frame to stop at
  toneFrequency={number}              // optional -- 0.01 to 2 (render only)
  loopVolumeCurveBehavior={"repeat" | "extend"}  // optional
  style={CSSProperties}               // optional
/>
```

### Audio (from @remotion/media)
```tsx
import { Audio } from "@remotion/media";
<Audio
  src={string}                         // required
  volume={number | ((frame: number) => number)}  // optional
  playbackRate={number}                // optional
  muted={boolean}                      // optional
  loop={boolean}                       // optional
  trimBefore={number}                  // optional
  trimAfter={number}                   // optional
  toneFrequency={number}              // optional -- render only
/>
```

### renderMedia (Node.js API)
```tsx
import { renderMedia } from "@remotion/renderer";
await renderMedia({
  composition: {                       // required
    id: string,
    durationInFrames: number,
    fps: number,
    width: number,
    height: number,
    defaultProps: object,
  },
  serveUrl: string,                    // required -- from bundle() output
  codec: "h264" | "h265" | "vp8" | "vp9" | "prores" | "gif",
  outputLocation: string,             // required -- file path
  inputProps?: object,                 // optional -- override defaultProps
  onProgress?: (progress: { renderedFrames: number, encodedFrames: number }) => void,
});
```

### TransitionSeries
```tsx
import { TransitionSeries, linearTiming, springTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { flip } from "@remotion/transitions/flip";
import { clockWipe } from "@remotion/transitions/clock-wipe";

<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={number}>{children}</TransitionSeries.Sequence>
  <TransitionSeries.Transition
    presentation={fade() | slide({ direction }) | wipe({ direction }) | flip({ direction }) | clockWipe()}
    timing={linearTiming({ durationInFrames: number }) | springTiming({ config, durationInFrames? })}
  />
  <TransitionSeries.Sequence durationInFrames={number}>{children}</TransitionSeries.Sequence>
</TransitionSeries>
```

## Section 3: Pagination Patterns

N/A -- Remotion is a rendering framework, not a data API. There are no paginated endpoints.

When using `calculateMetadata` to fetch external data that IS paginated (e.g., fetching a list of clips from an API), use standard fetch pagination patterns with the `abortSignal` parameter:

```tsx
const calculateMetadata: CalculateMetadataFunction<Props> = async ({ props, abortSignal }) => {
  let allItems = [];
  let cursor = null;
  do {
    const res = await fetch(`${props.apiUrl}?cursor=${cursor || ""}`, { signal: abortSignal });
    const data = await res.json();
    allItems.push(...data.items);
    cursor = data.nextCursor;
  } while (cursor);
  return { props: { ...props, items: allItems } };
};
```

## Section 4: Rate Limits

Remotion itself has no rate limits -- it runs locally or on your own infrastructure.

**Lambda rendering limits:**
- AWS Lambda concurrency limit applies (default 1000 concurrent executions)
- Each Remotion Lambda render spins up multiple Lambda functions (one per chunk)
- A single render of a 30-second video at 30fps may use 10-50 concurrent Lambda invocations
- S3 request limits: 5,500 GET/s, 3,500 PUT/s per prefix
- Monitor via AWS CloudWatch metrics

**Studio preview:**
- No explicit rate limit, but rendering is CPU-bound
- Heavy compositions (3D, multiple videos) may drop preview FPS
- Studio serves on localhost:3000 by default

## Section 5: Error Codes and Recovery

Remotion errors are JavaScript exceptions, not HTTP status codes.

**Common render errors:**
- `Error: No composition with ID "X" found` -- composition ID mismatch between CLI and Root.tsx. Verify the exact `id` prop on `<Composition>`.
- `Error: A media tag with src "X" could not be played` -- broken asset URL. Verify file exists in public/ and use `staticFile()`.
- `Error: Could not play media with src "X" due to a "NotAllowedError"` -- browser autoplay restriction in Player (not during render).
- `Error: Timeout waiting for media to load` -- asset took too long. Increase `timeoutInMilliseconds` or check network.
- `Error: Cannot use <Img> outside of Remotion` -- component rendered outside a composition context.
- `Webpack compilation error` -- TypeScript/import error. Check `npx remotion lint`.

**Recovery strategies:**
- Render errors: most are non-retryable (code/config issues). Fix and re-render.
- Asset loading failures: retryable. Check URLs, add `delayRender`/`continueRender` for custom loading logic.
- Lambda errors: check CloudWatch logs. Common issue is timeout (increase Lambda timeout) or memory (increase memory allocation).
- Out-of-memory during render: reduce `concurrency` parameter or render fewer frames per chunk.

**delayRender / continueRender pattern:**
```tsx
import { delayRender, continueRender } from "remotion";

const [handle] = useState(() => delayRender("Loading data"));

useEffect(() => {
  fetchData().then((data) => {
    setData(data);
    continueRender(handle);
  });
}, [handle]);
```

## Section 6: SDK Idioms

**Package structure:**
- `remotion` -- core: Composition, Sequence, Series, useCurrentFrame, interpolate, spring, Img, staticFile
- `@remotion/cli` -- CLI commands: studio, render, still, bundle, upgrade
- `@remotion/media` -- Video and Audio components (moved from core in v4)
- `@remotion/renderer` -- Node.js rendering API (renderMedia, renderStill, bundle)
- `@remotion/lambda` -- AWS Lambda serverless rendering
- `@remotion/transitions` -- TransitionSeries, fade, slide, wipe, flip
- `@remotion/google-fonts` -- type-safe Google Font loading
- `@remotion/fonts` -- local font loading
- `@remotion/captions` -- caption/subtitle processing
- `@remotion/gif` -- synchronized GIF playback
- `@remotion/lottie` -- Lottie animation embedding
- `@remotion/three` -- Three.js/R3F integration for 3D
- `@remotion/tailwind-v4` -- Tailwind CSS v4 webpack plugin
- `@remotion/zod-types` -- special Zod types (zColor)
- `@remotion/light-leaks` -- light leak overlay effects

**Adding packages:**
Always use `npx remotion add @remotion/package-name` to ensure version alignment.
Never install Remotion packages individually with `npm install` -- versions must match exactly.

**Config file:**
```ts
// remotion.config.ts -- only affects CLI rendering, NOT Node.js API
import { Config } from "@remotion/cli/config";
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
```

**TypeScript:**
- Use `type` not `interface` for component props (required for Zod schema inference)
- Props typing: `React.FC<z.infer<typeof MySchema>>` or direct parameter typing
- `CalculateMetadataFunction<Props>` for typed calculateMetadata

## Section 7: Anti-Patterns

### Anti-pattern 1: Using CSS animations
```tsx
// WRONG -- CSS animations render incorrectly
<div style={{ animation: "fadeIn 1s ease-in" }}>Hello</div>
<div className="animate-fade-in">Hello</div>

// CORRECT -- frame-driven animation
const frame = useCurrentFrame();
const { fps } = useVideoConfig();
const opacity = interpolate(frame, [0, 1 * fps], [0, 1], { extrapolateRight: "clamp" });
<div style={{ opacity }}>Hello</div>
```

### Anti-pattern 2: Using native img/video/audio elements
```tsx
// WRONG -- does not block rendering, causes blank frames
<img src="/logo.png" />
<video src="/clip.mp4" />

// CORRECT -- Remotion components that block until loaded
<Img src={staticFile("logo.png")} />
<Video src={staticFile("clip.mp4")} />
```

### Anti-pattern 3: Not clamping interpolate
```tsx
// WRONG -- opacity goes above 1 after frame 30
const opacity = interpolate(frame, [0, 30], [0, 1]);

// CORRECT -- clamped to [0, 1]
const opacity = interpolate(frame, [0, 30], [0, 1], {
  extrapolateRight: "clamp",
});
```

### Anti-pattern 4: Using setTimeout/setInterval
```tsx
// WRONG -- no real time passage between frames
setTimeout(() => setVisible(true), 1000);

// CORRECT -- use frame number
const frame = useCurrentFrame();
const { fps } = useVideoConfig();
const visible = frame >= 1 * fps;
```

### Anti-pattern 5: Hardcoding frame numbers instead of seconds
```tsx
// WRONG -- breaks when fps changes
<Sequence from={30} durationInFrames={60}>

// CORRECT -- fps-relative
const { fps } = useVideoConfig();
<Sequence from={1 * fps} durationInFrames={2 * fps}>
```

### Anti-pattern 6: Forgetting premountFor on Sequences
```tsx
// WRONG -- component mounts cold, first frame may be incomplete
<Sequence from={60}><HeavyComponent /></Sequence>

// CORRECT -- warm up 1 second early
<Sequence from={60} premountFor={30}><HeavyComponent /></Sequence>
```

### Anti-pattern 7: Using interface instead of type for props
```tsx
// WRONG -- interface breaks Zod schema inference
interface MyProps { title: string; }

// CORRECT -- use type
type MyProps = { title: string; };
// or
type MyProps = z.infer<typeof MySchema>;
```

## Section 8: Data Model

**Core hierarchy:**
```
RemotionRoot (registered via registerRoot)
  |
  +-- Folder (optional grouping)
  |     +-- Composition (video blueprint)
  |     +-- Still (single-frame image blueprint)
  |
  +-- Composition
        |-- id: string (unique identifier, used in CLI commands)
        |-- component: React.FC (the visual)
        |-- durationInFrames: number (total frames)
        |-- fps: number (frames per second)
        |-- width: number (pixels)
        |-- height: number (pixels)
        |-- defaultProps: object (JSON-serializable initial values)
        |-- schema: ZodSchema (for parametric editing)
        +-- calculateMetadata: async function (dynamic config)
```

**Frame model:**
- Frame 0 is the first frame
- Frame (durationInFrames - 1) is the last frame
- Each frame is a complete React render snapshot
- Inside Sequence, frames are local (0-based from the Sequence start)

**Asset model:**
- Static assets live in `public/` folder
- Referenced via `staticFile("filename")` which returns encoded URL
- Remote URLs used directly (must have CORS for cross-origin)
- Remotion components (<Img>, <Video>, <Audio>) block rendering until loaded

**Immutable after creation:**
- Composition `id` -- changing it breaks CLI render commands and saved presets
- `fps` at render time -- changing fps after design changes all timing
- Output codec -- cannot change mid-render

## Section 9: Webhooks and Events

N/A -- Remotion is a rendering framework, not a SaaS with webhook subscriptions.

**Relevant event-like patterns:**

`onProgress` callback during Node.js API rendering:
```tsx
await renderMedia({
  ...config,
  onProgress: ({ renderedFrames, encodedFrames, renderedDoneIn, encodedDoneIn }) => {
    console.log(`Rendered ${renderedFrames}/${totalFrames}`);
  },
});
```

Lambda rendering provides progress via `getRenderProgress()`:
```tsx
import { getRenderProgress } from "@remotion/lambda";
const progress = await getRenderProgress({
  renderId: string,
  bucketName: string,
  functionName: string,
  region: string,
});
// Returns: { overallProgress: number, framesRendered: number, ... }
```

## Section 10: Limits

**Composition limits:**
- No hard limit on number of compositions in a project
- Composition ID: alphanumeric + hyphens only
- Folder names: letters, numbers, hyphens only
- Width/height: positive integers (no maximum, but memory-bound)

**Rendering limits:**
- Frame concurrency: controlled by `--concurrency` flag (default: 50% of CPU cores)
- Max output file size: filesystem-limited
- Lambda: 10 minutes max execution time per chunk (configurable)
- Lambda memory: 512MB to 10,240MB per function

**Media limits:**
- Video: H.264, H.265, VP8, VP9, ProRes supported
- Audio: MP3, WAV, AAC, OGG supported
- Images: PNG, JPG, SVG, WebP, AVIF supported
- GIF: requires @remotion/gif package
- Maximum concurrent media loads: browser-limited (~6 per domain)

**Embed field limits (Zod schema):**
- String: no Remotion-imposed limit (practical limit: JSON serialization)
- Number: JavaScript number range
- Nested objects: no depth limit but Studio UI becomes unwieldy past 3-4 levels

**Tailwind:**
- Tailwind v4 supported via `@remotion/tailwind-v4`
- `transition-*` and `animate-*` classes forbidden (render incorrectly)
- All other utility classes work normally

## Section 11: Cost Model

**Remotion framework:**
- Free for individuals and companies with < 3 developers on Remotion code
- Company License: contact remotion.dev for pricing (typically per-seat annual)
- No per-render fees for local rendering
- No usage-based pricing for the framework itself

**Local rendering costs:**
- CPU-bound: 1 minute of 1080p30 video takes ~2-10 minutes to render on a modern machine
- Memory: ~2-4 GB RAM for typical compositions, more for 4K or heavy 3D
- Storage: ~10-50 MB per minute of 1080p H.264 output

**Lambda rendering costs (AWS):**
- Lambda invocation cost: ~$0.0000166667 per GB-second
- A 30-second 1080p30 video render typically costs $0.05-0.50 depending on complexity
- S3 storage: $0.023/GB/month for output files
- Data transfer: $0.09/GB outbound
- Monitor via AWS Cost Explorer with tags

**ElevenLabs (voiceover):**
- Free tier: 10,000 characters/month
- Starter: $5/month for 30,000 characters
- Typical 30-second voiceover: ~500 characters = ~$0.01 at starter tier

**Cost optimization:**
- Use lower fps (24 instead of 30) for social content where smoothness is less critical
- Render at 720p for drafts, 1080p for finals
- Use `--concurrency=2` on VPS to avoid OOM (the EOS VPS has limited RAM)
- Lambda: set `framesPerLambda` higher to reduce invocation overhead

## Section 12: Version Pinning

**Current versions in EOS:**
- `remotion`: 4.0.436
- `@remotion/cli`: 4.0.436
- `@remotion/tailwind-v4`: 4.0.436
- `@remotion/eslint-config-flat`: 4.0.436
- React: 19.2.3
- TypeScript: 5.9.3

**Version alignment rule:**
ALL `@remotion/*` packages MUST be the same version. Mismatched versions cause cryptic runtime errors. Always upgrade with:
```bash
npx remotion upgrade
```

**Upgrade policy:**
- Remotion releases frequently (weekly patches, monthly features)
- Breaking changes happen at major versions (3.x -> 4.x was significant)
- v4 moved Video/Audio to `@remotion/media` (was in `remotion` core in v3)
- Check https://remotion.dev/changelog before upgrading

**Deprecation signals:**
- `@remotion/tailwind` (v3 Tailwind) replaced by `@remotion/tailwind-v4`
- `Config.setVideoImageFormat("jpeg")` still works but may move to render options
- `Internals` exports are not public API and may change without notice

**Pinning strategy:**
Lock exact versions in package.json (no ^ or ~). The project already does this with `"remotion": "4.0.436"`.

---

# Tier 2 -- Creator Intelligence

## Section 13: Design Intent and Tradeoffs

**Why Remotion exists:**
Jonny Burger created Remotion because existing video creation tools (After Effects, Premiere, FFmpeg) are either GUI-only (not programmable) or CLI-only (not composable). Remotion's insight: React already solves the problem of declaratively describing visual layouts. If you treat each frame as a React render, you get the entire React ecosystem (components, TypeScript, npm packages, CSS) for free.

**Core design philosophy:**
- **React is the video editor.** Components are layers. Props are parameters. State is forbidden (useCurrentFrame replaces useState for animation).
- **Deterministic rendering.** Given the same frame number and props, the output is always identical. This is why CSS animations, setTimeout, and randomness-without-seed are forbidden.
- **Composition over configuration.** Small primitives (interpolate, spring, Sequence) compose into complex behaviors. There is no "slide template" built in -- you build it from primitives.
- **Developer experience first.** Hot reloading in Studio, TypeScript types, Zod schemas for visual editing, ESLint rules.

**Conscious tradeoffs:**
- Rendering speed sacrificed for React compatibility. Each frame is a full browser render. A 1-minute video at 30fps = 1,800 React renders.
- No real-time preview during rendering. The Studio preview is approximate -- actual render quality may differ (especially for video/audio sync).
- Webpack dependency. Remotion uses Webpack for bundling (not Vite), which adds build complexity but gives full control over loaders.

**What Remotion is NOT:**
- Not a video editor (no timeline GUI for non-developers)
- Not a real-time renderer (not for live streaming)
- Not a replacement for FFmpeg (FFmpeg is used under the hood and for post-processing)
- Not framework-agnostic (React only -- no Vue, Svelte, etc.)

## Section 14: Problem-Solution Map and Hidden Capabilities

**Problem: Dynamic video content from data**
Solution: Zod schema + calculateMetadata + JSON props. Feed database records, API responses, or spreadsheet data as props. Each render produces a unique video without code changes.

**Problem: Consistent brand identity across all video content**
Solution: Create a shared component library (Brand.tsx with colors, fonts, logo placement, lower thirds). Import into every composition. Change once, update everywhere.

**Problem: Matching video duration to audio/voiceover length**
Solution: calculateMetadata measures audio duration with `getAudioDuration()`, sets composition durationInFrames dynamically. Video adapts to content, not the other way around.

**Problem: Batch rendering hundreds of personalized videos**
Solution: Node.js script loops over data records, calls renderMedia() with different inputProps for each. Lambda rendering parallelizes across AWS for 100x throughput.

**Hidden capability: FFmpeg built in**
`npx remotion ffmpeg` and `npx remotion ffprobe` ship with Remotion. No separate FFmpeg install needed. Use for trimming, format conversion, silence detection.

**Hidden capability: Mediabunny**
`@remotion/media-utils` (Mediabunny) provides `getVideoMetadata()`, `getAudioDuration()`, `getVideoFrames()` for probing media files without FFmpeg.

**Hidden capability: Stills for thumbnails**
`<Still>` compositions render a single frame as PNG/JPEG. Use for YouTube thumbnails, social media cards, email headers -- all from the same React codebase as video.

**Hidden capability: Transparent video**
Render with ProRes codec and alpha channel for overlays. Useful for lower thirds, watermarks, animated logos to composite in other tools.

**Hidden capability: Light leaks**
`@remotion/light-leaks` provides cinematic light leak overlays as TransitionSeries overlays. Instant production value.

## Section 15: Operational Behavior and Edge Cases

**Rendering is single-threaded per frame.**
Each frame renders in a headless Chromium instance. Complex DOM (many elements, large images) slows each frame. Keep component trees lean.

**Video/Audio sync edge cases:**
Pitch shifting (`toneFrequency`) only works during server-side rendering. In Studio preview, audio plays at original pitch. Do not QA pitch in preview.

**Font loading race conditions:**
Google Fonts loaded via `@remotion/google-fonts` block rendering until loaded. But local fonts loaded via CSS `@font-face` do NOT block. Use `@remotion/fonts` or `delayRender`/`continueRender` for local fonts.

**Memory leaks during long renders:**
Rendering hundreds of frames with heavy components (3D, multiple videos) can accumulate memory. Set `--concurrency=1` or `--concurrency=2` on memory-constrained machines.

**Tailwind class purging:**
Remotion's Tailwind plugin uses Webpack. Dynamic class names (`bg-${color}-500`) may be purged. Use complete class names or safelist them.

**staticFile path encoding:**
`staticFile("file with spaces.mp4")` works -- Remotion encodes the URL. But `staticFile("file#2.mp4")` also works because `#` is encoded. Do not double-encode.

**Sequence mount/unmount timing:**
A component inside `<Sequence durationInFrames={30}>` unmounts after frame 29. Any cleanup in useEffect will fire. Data fetched inside will be garbage collected.

**calculateMetadata runs once:**
The calculateMetadata function runs once before rendering begins. It does NOT re-run per frame. All data fetching must happen here or in delayRender.

**Lambda cold starts:**
First Lambda render after deployment takes 5-15 seconds extra for cold start. Subsequent renders within ~15 minutes reuse warm instances.

## Section 16: Ecosystem Position and Composition

**Where Remotion sits:**
Remotion is a **rendering engine** in the content creation pipeline. It sits between:
- **Data sources** (CRM, social APIs, analytics) that provide the WHAT
- **Distribution platforms** (YouTube, Instagram, TikTok) that publish the output
- **AI services** (ElevenLabs, Whisper, GPT) that generate voiceover, captions, scripts

**Natural complements:**
- **ElevenLabs / OpenAI TTS** -- generate voiceover audio, feed into Remotion as Audio component
- **Whisper / Deepgram** -- transcribe audio to captions, render as styled subtitles
- **Cloudinary / S3** -- host input assets and output videos
- **Puppeteer / Playwright** -- NOT needed (Remotion has its own headless Chrome)
- **FFmpeg** -- ships with Remotion, used for post-processing (concatenation, format conversion)
- **Three.js / React Three Fiber** -- 3D content via @remotion/three

**Forced integrations to avoid:**
- **Framer Motion** -- conflicts with Remotion's frame-based rendering model. Use Remotion's own spring() and interpolate().
- **react-spring** -- same issue. Frame-based, not time-based.
- **Video.js / Plyr** -- video player components. Use Remotion's `<Video>` instead.
- **Next.js Image** -- does not block rendering. Use Remotion's `<Img>`.

**EOS composition:**
```
EOS Gateway --> Agent generates video brief (JSON)
  --> Python script calls Node.js render script
    --> Remotion renders video with brief as props
      --> Output uploaded via Apify/direct API to social platforms
```

## Section 17: Trajectory and Evolution

**Where Remotion is heading (as of 2025-2026):**
- **Remotion Studio** is getting more powerful -- visual editing, drag-and-drop timeline, making it accessible to non-developers
- **@remotion/media** package (moved from core) signals modularization trend
- **Mediabunny** (media utility library) replacing older media introspection approaches
- **Tailwind v4** support added, v3 plugin being deprecated
- **React 19** supported (EOS project already uses it)
- **AI integration** is a key growth area -- Remotion positions itself as the rendering backend for AI video generation

**Features gaining investment:**
- Captions and subtitles (competitive with CapCut/Descript for AI captions)
- Parametric video (Zod schemas, visual editors)
- Cloud rendering (Lambda improvements, future multi-cloud support)

**Deprecation signals:**
- `@remotion/tailwind` (v3) -- use `@remotion/tailwind-v4`
- Video/Audio in core `remotion` package -- moved to `@remotion/media`
- Older spring API without `durationInFrames` option
- `Config.setImageFormat()` may consolidate into render options

**What to build on:**
- calculateMetadata + Zod schemas (the parametric video pattern is central to Remotion's future)
- @remotion/transitions (actively maintained, growing transition library)
- Lambda rendering (AWS-focused but the serverless model is strategic)

**What to avoid building on:**
- Internal/undocumented APIs (`Internals.*` exports)
- Custom webpack configs that fight Remotion's defaults (breaks on upgrade)

## Section 18: Conceptual Model and Solution Recipes

**Mental model: Video = f(frame, props)**
Every Remotion video is a pure function of frame number and props. Given frame 42 and props `{title: "Hello"}`, the output is always the same visual. This is the key insight that makes Remotion work.

**Primitives:**
- `useCurrentFrame()` -- "where am I in time?"
- `useVideoConfig()` -- "what are my dimensions and speed?"
- `interpolate()` -- "map time to visual property"
- `spring()` -- "physics-based transition from A to B"
- `<Sequence>` -- "this exists from frame X to frame Y"
- `<Series>` -- "these play one after another"
- `staticFile()` -- "load this asset"
- `calculateMetadata()` -- "configure before rendering"

### Recipe 1: Branded Short-Form Social Clip
```
1. Create Zod schema: { headline: string, bgColor: zColor(), logoUrl: string }
2. Create Composition at 1080x1920 (vertical), 30fps, 5 seconds (150 frames)
3. Scene 1 (0-45 frames): Logo entrance with spring animation
4. Scene 2 (45-120 frames): Headline with typewriter text animation
5. Scene 3 (120-150 frames): CTA with fade-in
6. Use TransitionSeries with fade between scenes
7. Add background music via <Audio loop volume={0.3}>
8. Render: npx remotion render src/index.ts BrandedClip output.mp4 --props='...'
```

### Recipe 2: AI Voiceover Explainer Video
```
1. Generate voiceover with ElevenLabs for each scene, save to public/voiceover/
2. Use calculateMetadata to measure audio durations, set total durationInFrames
3. Create scenes as Sequences, each with matching <Audio> and visual content
4. Add @remotion/captions for auto-generated subtitles synced to voiceover
5. Use TransitionSeries for scene transitions
6. Render with: npx remotion render src/index.ts Explainer output.mp4
```

### Recipe 3: Batch Personalized Outreach Videos
```
1. Define Zod schema: { recipientName: string, companyName: string, avatarUrl: string }
2. Create template composition with personalized greeting + value prop
3. Node.js script reads CSV/database of prospects
4. Loop: renderMedia() with each prospect's data as inputProps
5. Output: one video per prospect, named {company}-outreach.mp4
6. Upload to outreach tool or social DMs via EOS pipelines
```

### Recipe 4: YouTube Thumbnail Generation
```
1. Create <Still> composition at 1280x720
2. Design with bold text, face photo, branded colors
3. Accept props: { title: string, subtitle: string, photoUrl: string }
4. Render: npx remotion still src/index.ts Thumbnail thumb.png --props='...'
5. Upload to YouTube via API
```

### Recipe 5: Data-Driven Dashboard Video
```
1. Fetch metrics from Neon/API in calculateMetadata
2. Use @remotion/charts-style bar/line charts animated with spring
3. Each metric gets a Sequence with entrance animation
4. Summary scene at end with key takeaways
5. Render weekly via cron, post to Discord via webhook
```

## Section 19: Industry Expert and Cutting-Edge Usage

**AI-powered video factories:**
Companies like Synthesia, HeyGen, and Creatopy use programmatic video generation (some on Remotion, others on custom engines). The pattern: AI generates script + voiceover + visual layout, rendering engine assembles. Remotion is the open-source option for this pipeline.

**Parametric video at scale:**
E-commerce companies generate thousands of product videos by feeding product data (images, specs, prices) as Remotion props. One template, thousands of outputs. This is the model EOS should follow for Initiate Arena content.

**Captions as a first-class feature:**
Short-form content platforms (TikTok, Reels) prioritize captioned videos. Remotion's @remotion/captions + word-level timestamp display is competitive with paid tools like CapCut and Descript. The display-captions pattern with highlighted current word is the industry standard.

**Lambda for on-demand rendering:**
SaaS products embed Remotion Lambda as a rendering backend. User customizes template in browser (using Remotion Player), clicks "render," Lambda produces video in 30-60 seconds. This is the architecture for a future EOS video SaaS feature.

**GitHub Actions rendering:**
Remotion renders in CI/CD pipelines. Daily/weekly automated content (market updates, metrics summaries) rendered in GitHub Actions, uploaded to social. Zero manual intervention.

**Multi-composition projects:**
Expert Remotion projects organize compositions in Folders by platform:
```
Marketing/
  Instagram/Story (1080x1920)
  Instagram/Reel (1080x1920)
  YouTube/Short (1080x1920)
  YouTube/Video (1920x1080)
  YouTube/Thumbnail (1280x720, Still)
Social/
  Twitter/Card (1200x675, Still)
  LinkedIn/Post (1200x1200)
```
Same content, different aspect ratios. Shared components across all.

**Remotion + Claude Code pattern:**
Claude Code can generate complete Remotion compositions from natural language descriptions. The pattern: describe the video in words, Claude writes the JSX + animation code, render and review. The rules files in the EOS project (`knowledge/skills/marketing/content/remotion/.agents/skills/remotion-best-practices/rules/`) enable this by giving Claude exact syntax patterns.

---

## EOS Usage Patterns

**Current state:** Scaffold project at `knowledge/skills/marketing/content/remotion/` with v4.0.436, React 19, Tailwind v4. Empty composition. Extensive rules library for AI-assisted development.

**Planned workflow:**
1. EOS agent generates video brief (title, scenes, voiceover text, brand colors)
2. Python script calls Node.js render via subprocess
3. Remotion renders using parametric composition with brief as props
4. Output uploaded to social platforms via Apify/direct API integrations

**Standard dimensions for EOS content:**
- Reels/TikTok/Shorts: 1080x1920 @ 30fps
- YouTube landscape: 1920x1080 @ 30fps
- Thumbnails: 1280x720 (Still)
- Instagram square: 1080x1080 @ 30fps

## Gotchas

### CSS animations and Tailwind animate classes do not work
Every animation must use `useCurrentFrame()` with `interpolate()` or `spring()`. CSS transitions, @keyframes, and Tailwind `animate-*` / `transition-*` classes produce incorrect or missing animation during render.

### All @remotion packages must be the same version
Mismatched versions (e.g., remotion 4.0.436 + @remotion/media 4.0.430) cause cryptic runtime errors. Always upgrade with `npx remotion upgrade`.

### Video/Audio moved to @remotion/media in v4
In Remotion v3, `<Video>` and `<Audio>` were exported from `remotion`. In v4, they moved to `@remotion/media`. Old imports compile but may behave differently.

### EOS VPS has limited RAM
The VPS at 100.77.233.50 has limited memory. Use `--concurrency=1` or `--concurrency=2` when rendering locally. For heavy renders, use Lambda.

### Node.js required for rendering
Remotion CLI requires Node.js 18+. The VPS runs Python primarily. Ensure Node.js is installed and accessible when rendering. Use `node --version` to verify.
