# PHASE 2 — CutStudio UI (one-shot execution plan)

**Status: PLANNED, not started. This plan is exhaustive by design — execution is
pure application. No decisions are left to the executor.**

## What it is
A browser app for team members: upload a recording, get a transcript, **strike
text to cut video**, watch a live preview, refine by chat, render. The EDL
(`edl.py`, schema v1 — already built and proven) is the single state object;
the UI is a view over it. Phase 1's pipeline is the engine unchanged.

## Stack (locked)
- **Backend**: Python FastAPI + uvicorn on the VPS (port 8931), serving both the
  API and the built UI as static files. Reuses Phase 1 modules by import.
  No new Python deps beyond `fastapi` + `uvicorn` + `python-multipart`.
- **Frontend**: Vite + React 19 + TypeScript + Tailwind 4 + zustand (matches the
  cockpit stack — patterns are transplantable). **npm install and build run on
  the BEAST only** (node-role law: no node_modules on the VPS); `dist/` is
  synced back and committed.
- **Auth**: single shared token in env `CUTSTUDIO_TOKEN` checked by middleware
  on every /api route (team tool on Tailscale — not public; Clerk comes only if
  it ever leaves the tailnet).
- **AI edit**: backend calls `adapters/models/model_router.call_with_fallback`
  (never a hardcoded client) with transcript + current EDL + instruction →
  revised EDL JSON. Deterministic fallback: if the model fails, return the
  current EDL unchanged with a "model unavailable" note (UI stays functional —
  manual editing is the spine, AI is the enhancement).

## Directory layout (all new files)
```
knowledge/skills/marketing/content/cut/
├── server/
│   ├── app.py            # FastAPI app factory + static mount + auth middleware
│   ├── projects.py       # project store + endpoints
│   ├── jobs.py           # background job runner (transcribe/render) + status
│   └── ai_edit.py        # instruction + transcript + EDL -> revised EDL
├── ui/                   # Vite project (built on Beast)
│   ├── package.json      # react@19, react-dom@19, zustand@5, tailwindcss@4, vite@6, typescript@5
│   ├── vite.config.ts    # base './', proxy /api -> :8931 in dev
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api.ts        # typed fetch client (token from localStorage)
│       ├── store.ts      # zustand: project, transcript, edl, ui state
│       ├── types.ts      # Transcript, Segment, Word, EDL, Clip, Job — mirrors edl.py/transcribe.py EXACTLY
│       └── components/
│           ├── UploadScreen.tsx
│           ├── EditorScreen.tsx      # layout: TranscriptPanel | right column (Preview, Timeline, ChatBox)
│           ├── TranscriptPanel.tsx
│           ├── PreviewPlayer.tsx
│           ├── Timeline.tsx
│           ├── ChatBox.tsx
│           ├── RenderBar.tsx
│           └── JobToast.tsx
└── data/                 # runtime (gitignored): projects/<id>/{source.mp4, transcript.json, source.srt, edl.json, renders/}
```

## Backend API contract (all under /api, token-gated)
| Method+Path | Body | Returns | Behavior |
|---|---|---|---|
| POST `/api/projects` | multipart file | `{id, name}` | id = 12-hex uuid slice; saves to `data/projects/<id>/source.<ext>`; creates default EDL (one clip 0→duration via ffprobe) |
| GET `/api/projects` | — | `[{id, name, created, has_transcript, renders: [names]}]` | list |
| POST `/api/projects/{id}/transcribe` | `{model?: "base"\|"small"}` | `{job_id}` | background thread → `transcribe.transcribe()`; writes transcript.json + .srt into the project dir |
| GET `/api/projects/{id}/transcript` | — | transcript.json or 404 | |
| GET `/api/projects/{id}/edl` | — | edl.json | |
| PUT `/api/projects/{id}/edl` | EDL json | validated EDL | `edl.validate()`; 422 with message on EDLError; bumps `edl_rev` counter in response header `X-EDL-Rev` |
| POST `/api/projects/{id}/ai-edit` | `{instruction: str}` | `{edl, note}` | `ai_edit.revise()`; NEVER auto-saves — UI shows diff, user applies (PUT) |
| POST `/api/projects/{id}/render` | `{vertical?, captions?, output?}` | `{job_id}` | merges flags into EDL copy → background `cutter.cut()` into `renders/`; regenerates SRT from kept words first (see SRT-regen below) |
| GET `/api/jobs/{job_id}` | — | `{state: queued\|running\|done\|error, detail, artifact?}` | poll every 1500ms |
| GET `/api/projects/{id}/file/{name}` | — | file stream | only from the project dir (path-traversal guarded: resolved path must be inside) |
| GET `/healthz` | — | `{ok: true}` | no auth |

**jobs.py**: in-process dict `{job_id: {state, detail, artifact}}` + `threading.Thread`
per job; max 2 concurrent (queue otherwise); `cpu_gate_check` not required
(knowledge/ is outside gated dirs) but call it anyway before render — refuse
politely when host is loaded.

**SRT-regen (render step)**: burned captions must match the CUT, not the source.
Build from transcript words: for each EDL clip, take words with
`clip.start <= word.start < clip.end`, shift each by the clip's offset in the
output timeline (`sum of prior clip durations - clip.start`), group into lines
of ≤ 7 words, write `renders/<output>.srt`, pass that to cutter (cutter accepts
an explicit `srt` param — add optional arg `cut(edl_path, out_dir, srt_path=None)`,
default preserves current behavior).

## Frontend spec

**store.ts (zustand)** — single store:
```ts
{ project: {id,name} | null,
  transcript: Transcript | null,
  edl: EDL | null,            // the working copy
  savedRev: number, dirty: boolean,
  playhead: number,           // OUTPUT-timeline seconds
  selection: {segIdx, wordIdx}[] | null,
  jobs: Record<string, Job>,
  chat: {role, text}[],
  pendingAiEdl: EDL | null }  // ai-edit proposal awaiting apply/discard
actions: loadProject, toggleWordRange, strikeSegment, restoreSegment,
  setClipBounds, applyAiEdl, discardAiEdl, save (PUT, debounced 800ms), render
```

**Derived mapping (the core algorithm, in store.ts)**:
- `keptRanges(): {start,end}[]` — from EDL clips (source-time)
- `sourceToOutput(t)` / `outputToSource(t)` — piecewise-linear maps across kept
  ranges; words outside kept ranges have no output time (rendered struck)
- Toggling words edits the EDL: striking a word range SPLITS the containing
  clip (or trims its edge); restoring MERGES adjacent clips when gap < 0.15s.
  Word boundaries snap to `word.start`/`word.end` from the transcript.

**TranscriptPanel** — the primary editor. Renders segments as paragraphs, each
word a `<span data-seg data-word>`. Kept words: `text-[#F5F5F4]`. Struck:
`line-through text-[#8E8E93]/50`. Current word (playhead within its output
range): violet underline. Interactions: click word = seek preview; click-drag
across words then `X`/strike-button = cut range; click struck region = restore;
segment hover shows ⌫ (strike whole segment). All edits go through store
actions → EDL.

**PreviewPlayer** — HTML5 `<video src=/api/projects/{id}/file/source.ext>`
simulating the cut WITHOUT rendering: on `timeupdate` (rAF-driven, 60fps
check), if `currentTime` exits a kept range, jump to next range's start
(`video.currentTime = next.start`); end of last range = pause. Displays
OUTPUT time (`sourceToOutput`). Controls: play/pause (space), ±5s (arrows),
output-duration readout `mm:ss / mm:ss`.

**Timeline** — one horizontal strip (height 56px). Full source duration as a
muted track (`#1F1F23`); kept clips as violet blocks (`#6D28D9`, 4px radius,
label on hover); playhead as 2px `#F5F5F4` line. Click seeks (outputToSource).
Drag clip edges (8px hit area) adjusts `start`/`end` (min clip 0.2s, clamped to
neighbors) — snaps to nearest word boundary within 0.12s.

**ChatBox** — messages list + input. Send → POST ai-edit → proposal arrives:
render a summary diff ("keeps 3 of 5 clips, −41s: [labels]") + Apply / Discard
buttons. Apply = `applyAiEdl` (marks dirty, saves). The chat NEVER mutates
without explicit Apply.

**RenderBar** — toggles: Vertical (9:16), Captions; Render button → job toast
with progress states; done → link `/api/projects/{id}/file/renders/<name>` +
"copy link". Render disabled while `dirty` (must save first — button says
"Save & Render", does both).

**UploadScreen** — drag-drop or picker (mp4/mov/webm/mkv, ≤2GB) → POST →
auto-trigger transcribe (model: small) → progress ("Transcribing — ~1min per
10min of video") → EditorScreen on done. Also lists existing projects.

**Brand**: import tokens from a `src/brand.ts` mirroring
`projections/empyrean/brand.py` values verbatim (bg #0A0A0B, surface #121214,
border #1F1F23, text #F5F5F4, muted #8E8E93, accent #6D28D9, soft #8B5CF6;
Archivo headline stack, Inter body). Wordmark "EMPYREAN STUDIOS" top-left,
app name "CutStudio". Dark only. No gold ever.

**Keyboard**: space play/pause · S strike selection · R restore selection ·
←/→ seek 5s · ⌘S save · ⌘Z undo (store keeps a 50-deep EDL undo stack —
`past: EDL[]`, push on every mutating action).

## ai_edit.py contract
```
revise(transcript: dict, edl: dict, instruction: str) -> {"edl": dict, "note": str}
```
Prompt (verbatim skeleton): system = "You edit video by returning EDL JSON only.
Schema: {version:1, source, clips:[{start,end,label}], captions, vertical,
output}. Cut at word boundaries from the transcript. Never invent times.";
user = transcript segments w/ word times (compact) + current EDL + instruction.
Parse the reply's first JSON object; `edl.validate()` it; clamp times to
[0, duration]; on ANY failure return current EDL + note="model unavailable or
invalid — edit manually". Route via `call_with_fallback(prompt=..., agent_type='default')`
— result is `RoutingResult.output` (memory: model-router return type).

## Build & deploy sequence (executor follows in order)
1. Backend: write server/*.py; `pip install fastapi uvicorn python-multipart`
   (venv or system per VPS convention); `python3 -m uvicorn knowledge.skills.marketing.content.cut.server.app:app --port 8931`
2. UI: write ui/* on the VPS (source only), then ON THE BEAST:
   `cd C:\dev\dev\OS\knowledge\skills\marketing\content\cut\ui && npm install && npm run build`
   (pull latest first). Sync `dist/` back via the base64-over-ssh pattern
   (scripts/beast_remotion_render.sh documents it; scp breaks on the username).
3. Static mount: app.py serves `ui/dist` at `/` (SPA fallback to index.html).
4. systemd unit `os-cutstudio.service` (copy pattern from existing service
   units; Restart=on-failure, RestartSec=5 — iptables lesson: never a
   crash-loop with side effects) + Tailscale-only bind (listen 127.0.0.1 +
   tailscale serve, or bind 100.77.233.50 directly).
5. Token: generate, store in 1Password UMH-Production item `CutStudio` field
   `token` THAT session (store-creds-immediately rule), export in unit env.

## Verification (executor must run all)
1. `pytest`-free smoke: upload tests/test_vod.mp4 via curl → transcribe →
   GET transcript has segments+words → PUT a 2-clip EDL → render with
   vertical+captions → poll job to done → GET the render; ffprobe duration
   matches EDL duration ±0.2s, 1080×1920.
2. SRT-regen: burned captions in the render show ONLY kept-words text, timed
   to the output (visually check frame at t=1s and t=5s via ffmpeg thumbnail).
3. AI edit: instruction "keep only the first sentence" returns valid EDL with
   1 clip; kill the model route (unset keys) → returns unchanged EDL + note.
4. UI: strike middle paragraph → preview skips it seamlessly; undo restores;
   drag a clip edge snaps to word boundary; refresh restores saved EDL.
5. Auth: request without token → 401; path traversal `file/../../etc/passwd`
   → 400.
6. Banned-word/gold sweep on UI strings; py_compile + `npm run lint` clean.

## Effort
Backend ~400 lines, ai_edit ~80, UI ~1100 across 10 files. One focused
session on the plan = the app. No open decisions.
