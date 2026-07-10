---
type: codewiki-dir
dir: cockpit
---

# `cockpit/` — the UMH Desktop Cockpit frontend (Electron / web / mobile operator surface)

**431 files · 4,598,832 bytes (after excluding `dist/`, `dist-web/`, `out/` build outputs) · [Full file inventory](../inventory/cockpit.md)**

## Purpose
`cockpit/` is the operator-facing frontend for UMH — the single surface a human
uses to talk to DEX (the assistant), watch the organism, and drive governed work.
It ships as **one codebase, three runtimes**: an Electron 42 desktop app, a web
app at `universalmetaharness.tech`, and iOS/Android shells wrapping that same web
app via Capacitor. The renderer (React 19 + Zustand + TailwindCSS 4) is identical
across all three; only the shell around it changes. It is a pure client — it holds
no business logic and no state authority; every mutation and every read goes to the
UMH backend (`os-operator`, `127.0.0.1:8091`) through `/api/umh/*`.

## How it fits
Architecturally the cockpit is an **EOS/UMH projection surface** that lives above
the transport layer: it speaks to `transports/api/` (the UMH HTTP API) and never
imports substrate code directly. Auth is Clerk (`@clerk/clerk-react`) with the JWT
verified server-side in `transports/api/cockpit_auth.py`; the frontend carries no
API keys or secrets of its own. Voice runs over LiveKit (`livekit-client`) and the
one governed voice WebSocket (`/api/umh/voice/ws`) on the API backend. In deployment
the container is nginx serving the built static assets plus a persistent SSH tunnel
(over Tailscale) back to the VPS, so the browser talks same-origin to `/api/umh/*`
and nginx proxies it privately to `os-operator` — nothing on the UMH backend is
exposed publicly.

## Structure
| Path | Role |
|---|---|
| `src/main/` | Electron main process — window/tray/FAB modes, IPC handlers, spawns Python side-servers (voice/vision/browser relays), `desktop-voice-adapter.ts` |
| `src/preload/` | Context-isolated preload bridge — exposes a narrow `window.cockpit` API (window controls, voice, notify, fs) to the renderer |
| `src/renderer/` | The React 19 app — all UI, panels, stores, API client, voice. Summarized below; full detail in [cockpit-renderer.md](./cockpit-renderer.md) |
| `android/` | Capacitor Android shell (Gradle project) wrapping the web app |
| `ios/` | Capacitor iOS shell (Xcode project) wrapping the web app |
| `assets/` | App icons + splash screens (`icon-*.png`, `splash*.png`) fed to `@capacitor/assets` |
| `tests/` | Python package placeholder only (empty `__init__.py`); the real JS/TS tests live in `src/renderer/__tests__/` |
| `verify-env-empty/` | Empty env dir used by `vite.verify.config.ts` so the verify runtime picks up no `.env` |

Top-level files: `deploy.sh` (the deploy gate), `Dockerfile`, `start.sh`,
`nginx.conf.template`, `fly.toml`, `capacitor.config.ts`, `browse-proxy.mjs`
(in-app browser proxy), the four vite/vitest configs, `DESIGN.md`, and
`package.json`.

## Key components

### Electron main process — `src/main/index.ts` (299 lines)
Creates a frameless 1440×900 `BrowserWindow` (`titleBarStyle: 'hiddenInset'`,
`contextIsolation: true`, `sandbox: false`) and a system tray. It implements a
five-mode window system — `maximized`, `large-fab`, `medium-fab`, `small-fab`,
`invisible` (`src/main/index.ts:14`) — so the cockpit can shrink to a floating
always-on-top FAB or hide entirely, toggled from the tray or the global
`Ctrl/Cmd+Alt+J` hotkey (`src/main/index.ts:263`). It registers IPC handlers for
window control, notifications, and a small filesystem bridge (`fs:readDir`,
`fs:readFile`, `fs:writeFile` — the latter capped at 2 MB reads,
`src/main/index.ts:170`). It also spawns three Python side-processes on demand —
`voice_server.py`, `vision_relay.py`, and `services/browser_relay.py` — rooted at
`UMH_ROOT` (default `/opt/OS`), streaming their stdout/stderr to the renderer over
IPC. All three are killed on `window-all-closed` and `before-quit`.

### Preload bridge — `src/preload/index.ts` (33 lines)
The only channel between renderer and main. Uses `contextBridge.exposeInMainWorld`
to publish `window.cockpit` with exactly four capability groups (`window`, `voice`,
`notify`, plus `readDir`/`readFile`/`writeFile`). Nothing else from Electron is
reachable from the renderer — this narrow surface is the security boundary.

### Desktop voice adapter — `src/main/desktop-voice-adapter.ts` (130 lines)
A **flag-disabled scaffold** (packet P4S-31D-3, not started). It exports the full
`PlatformVoiceAdapter` method surface (`requestConsent` / `openSession` /
`startCapture` / `stopCapture` / `closeSession`) but every method returns a typed
`DESKTOP_VOICE_DISABLED` refusal while `DESKTOP_VOICE_ENABLED` is `false`. That flag
is a hard build-time constant, deliberately **not** readable from env, config, IPC,
or any client input — the only way to enable desktop voice is a code change in the
implementation packet. There is no microphone capture, no wake-word runtime, and no
IPC registration (nothing in `index.ts` imports it). The comments document the
voice contract invariants it will bind to: transcript-only transit, fail-closed
consent, no audio persistence, and the CPU Gate Law (no mic runtime on the
orchestrator/VPS node).

### The renderer (`src/renderer/`) — one paragraph
The React app is where all UI lives: 332 files under `src/renderer/` (excluding its
`dist/` build output) split across `panels/`, `components/`, `operator/`, `stores/`
(Zustand — e.g. the cockpit store and EOS action queue), `api/` (the `/api/umh/*`
client, the platform voice adapter, and the always-on `voice-diag.ts` beacon),
`hooks/`, `lib/`, `constants/` (including the device registry constants), `styles/`
(design tokens), and `__tests__/` (the Vitest suite). It renders the operator
workstation — chat with DEX, the organism view, projection mirrors, voice — and is
documented in full on [cockpit-renderer.md](./cockpit-renderer.md).

### Build & deploy story
- **`package.json`** defines the scripts: `dev`/`build` (electron-vite desktop),
  `dev:web`/`build:web` (Vite web app → `dist-web/`), `build:mobile`
  (`vite build && npx cap sync`), plus `cap:ios`/`cap:android`, `typecheck`,
  `test` (Vitest).
- **Four Vite configs**: `electron.vite.config.ts` (main/preload/renderer, renderer
  dev server on :5173), `vite.web.config.ts` (web build → `dist-web/`, also emits a
  service worker `sw.js`), `vite.verify.config.ts` (a Tailscale-only verification
  runtime on :5199 that same-origin-proxies `/api/umh` to `127.0.0.1:8091`, mirroring
  production nginx — **not** a deploy path), and `vitest.config.ts` (jsdom env,
  tests under `src/**/__tests__/**`).
- **`Dockerfile`** is a two-stage build: `node:20-slim` runs
  `vite build --config vite.web.config.ts` with the Clerk publishable key and
  `VITE_AI_NAME` injected as build args; the runtime image is `nginx:alpine` plus
  `tailscale`, `openssh-client`, and `nodejs`, serving `dist-web` and running
  `start.sh`.
- **`start.sh`** copies `nginx.conf.template` → active config (no secret
  substitution — Clerk JWT auth is handled by the backend), starts the browse proxy
  and nginx, brings up `tailscaled` in userspace-networking mode, joins the tailnet
  as `umh-cockpit`, and runs a self-healing SSH tunnel loop that forwards eight local
  ports (8091 API, 8097 vision, 7880 LiveKit, 5173, 8086, 8095, 8100) from the Fly
  container to the VPS over `tailscale nc`.
- **`fly.toml`** — app `umh-cockpit`, region `sjc`, internal port 8080, `force_https`,
  `min_machines_running = 1`, a `shared-cpu-1x` / 1 GB VM. The public hostname the
  user hits is `universalmetaharness.tech`.
- **`deploy.sh`** is the mandatory entry point (see Gotchas).

### Mobile shells — `android/` + `ios/` + `capacitor.config.ts`
`capacitor.config.ts` declares appId `tech.universalmetaharness.cockpit`, `webDir`
`dist-web`, and a `server.url` of `https://universalmetaharness.tech` — so the native
apps load the live web cockpit rather than bundled assets. It configures the splash
screen, dark status bar, and push notifications. `android/` is a standard Gradle
project and `ios/` a standard Xcode workspace; both have their built `public/` web
assets gitignored (synced by `npx cap sync`).

## Data & state
The cockpit stores no durable state itself. It reads/writes UMH state exclusively
through `/api/umh/*` (proxied by nginx to `os-operator` on `127.0.0.1:8091`) and the
governed voice/vision WebSockets. Client state is ephemeral: Zustand stores in the
renderer, plus a service worker (`sw.js`) for the web/PWA build. Build-time inputs:
`VITE_CLERK_PUBLISHABLE_KEY`, `VITE_API_URL` (`/api/umh`), and `VITE_AI_NAME` (`DEX`)
baked in during the Docker build. Runtime container secrets are Fly secrets consumed
by `start.sh`: `MESH_KEY` (SSH key), `TAILSCALE_AUTHKEY`, `VPS_HOST_KEY`, and
`UMH_VPS_IP` (default `100.77.233.50`). The Electron `fs:*` IPC handlers can read and
write the local filesystem on the desktop app only.

## Gotchas

- **Deploy gate is NON-NEGOTIABLE — never run `flyctl deploy` directly for the
  cockpit.** Always use `bash cockpit/deploy.sh`. The gate (`deploy.sh:11`) verifies
  that `nginx.conf.template`, `Dockerfile`, and `start.sh` byte-match the `main`
  branch before deploying, blocks if the retired `nginx.conf` file exists (replaced
  by `nginx.conf.template` + envsubst in commit `1680083f`), asserts the template
  injects **no** secrets and no `X-API-Key` header (auth is Clerk JWT, verified
  server-side), and confirms `transports/api/cockpit_auth.py` exists. This rule
  exists because on **2026-06-06** a worktree deploy shipped stale auth config
  (no API-key injection), causing 401 Unauthorized on every cockpit API call. The
  gate also auto-refreshes the Fly deploy token from 1Password and runs a post-deploy
  health check against `universalmetaharness.tech/healthz`.

- **Single domain — always `universalmetaharness.tech`, never `umh-cockpit.fly.dev`.**
  The Fly app is named `umh-cockpit` but the operator-facing URL is only ever the
  custom domain. `capacitor.config.ts` and `deploy.sh`'s post-deploy check both use
  `universalmetaharness.tech`; the native mobile shells load it directly.

- **Client-failure observability law applies here** (`.claude/rules/client-failure-observability.md`).
  The cockpit is exactly the kind of client-heavy surface where a failure can happen
  entirely in the browser and never reach `docker logs`. When a user-facing failure
  can't be seen server-side, STOP writing fixes and instrument the client first: the
  permanent voice-diag beacon lives at `src/renderer/api/voice-diag.ts`
  (`diagStartTap` / `diagStage` / `diagFlush`) and flushes to
  `POST /api/umh/voice/diag`, logged as `[VoiceClientDiag]`. Do not delete it as
  "scaffolding." The rule was written after a mobile-voice bug cost a full day and six
  wrong fixes (2026-07-09) because the failure — `unlockAudioForIOS()`'s `audio.play()`
  hanging on iOS 18.7 Safari — never hit the server. Never `await` a non-essential
  call (like a TTS autoplay nicety) on a user-blocking path such as mic start.
  Partially enforced by Gate 14 (`scripts/check_voice_runtime_divergence.py`), which
  requires the diag beacon to exist and be wired and blocks the known-hang audio-unlock
  call from being awaited on the voice-start critical path.

- **`cockpit/tests/` is a decoy.** It holds only an empty `__init__.py`. The actual
  test suite is Vitest under `src/renderer/__tests__/` (`cockpitStore.test.ts`,
  `apiClient.test.ts`, `projectionMirrors.test.tsx`, `ids.test.ts`,
  `eosActionQueue.test.tsx`) run via `npm test`.

- **`DESIGN.md` is a design lock** (locked 2026-07-08). It is the authoritative record
  of every design token, layout dimension (LeftDrawer 160, RightDrawer 240, HudBar 30,
  TitleBar 36), color, and runtime accent. Changing any value requires explicit AFM
  approval — treat it as frozen, not as documentation to freely edit.

- **API 502s until the tunnel is up.** `start.sh` starts nginx before the SSH tunnel
  so Fly health checks pass immediately; the `/api/umh/*` proxy returns 502 until the
  tunnel to the VPS connects. This is expected cold-start behavior, not a deploy
  failure.

## See also
- [cockpit-renderer.md](./cockpit-renderer.md) — the React 19 renderer in full
- [../architecture.md](../architecture.md) — layer law and dependency direction
- [../services-runtime.md](../services-runtime.md) — `os-operator` and the API backend the cockpit talks to
- [../tech-stack.md](../tech-stack.md) — full technology inventory
- [transports/](./transports.md) — the `/api/umh/*` HTTP surface + `cockpit_auth.py`
