---
type: codewiki-dir
dir: cockpit/src/renderer
---

# `cockpit/src/renderer/` — the React cockpit app (the operator's window into the organism)

**335 files · ~76,700 lines of TypeScript/TSX · [Full file inventory](../inventory/cockpit.md)**

(Measured: `find /opt/OS/cockpit/src/renderer -type f | wc -l` = 335. Of these, 326
are source — `.ts`/`.tsx`/`.css`/`.html` outside `dist/` — plus 7 static PWA assets
under `public/`, and 3 committed build artifacts under `dist/`. TS/TSX line count:
`find … -name '*.ts*' -not -path './dist/*' -exec cat {} + | wc -l` = 76,722.)

## Purpose
This is the browser application that renders the UMH cockpit — the single-page React
app the operator (AFM) uses to see and drive the organism. It is not a dashboard; it
is a control surface. Every panel, canvas window, chat surface, voice session, and
vision overlay in the cockpit lives here. The renderer talks to the substrate only
over HTTP (`api/client.ts`) and WebSockets (`api/*-ws.ts`); it holds no business
logic of its own — it projects substrate state into pixels and turns operator intent
into governed requests. Its counterpart is the Electron/Capacitor shell and the nginx
+ Python bridge that serve it (see the parent [`cockpit/`](./cockpit.md)).

## How it fits
This is the top of the stack — the **projection presentation layer** for EOS/UMH,
above `transports/api/http/` which serves it. The dependency-direction law
(`.claude/rules/architecture-layers.md`) runs one way downward: the renderer consumes
UMH HTTP infrastructure (auth-gated routes under `/api/umh/...`, the `/eos/*` read
surfaces, `/workspace/mesh-nodes`) but nothing in `substrate/`, `adapters/`, or
`transports/` ever imports from here. Auth is Clerk (`@clerk/clerk-react`): `main.tsx`
wraps the app in `ClerkProvider`, `App.tsx` gates on `SignedIn`/`SignedOut`, and every
request carries the Clerk bearer token (`api/client.ts` `getClerkToken`/`freshToken`).
Build is Vite + React 18 + Zustand; there is no Redux and no server-side rendering.

## Structure
| Subdir | Files | Role |
|---|---|---|
| `panels/` | 80 | Feature panels — one per organism concern (see grouping below). Rendered as canvas windows, not tabs. |
| `stores/` | 81 | Zustand state stores — one per domain, the client-side mirror of substrate state. |
| `components/` | 112 | Shared UI: shell/rail/drawer chrome (51 top-level) + `canvas/` (24), `rooms/` (17), `vision/` (14), `cards/` (6). |
| `api/` | 13 | HTTP client + WebSocket clients (broadcast, browser, vision, voice) + the voice-diag beacon. |
| `hooks/` | 13 | React hooks: realtime subscriptions, polling, media auth, mobile/keyboard/canvas interaction. |
| `stores/` (see above) | — | — |
| `types/` | 3 | Shared TS types: `rooms.ts`, `rrip.ts` (renderer's RRIP contract), `routes.ts`. |
| `lib/` | 3 | Cross-cutting helpers: `pushNotifications.ts`, `rrip-normalize.ts`, `time.ts`. |
| `operator/` | 2 | Operator voice input plumbing: `speechInputAdapter.ts`, `voiceTypes.ts`. |
| `utils/` | 2 | `ids.ts`, `canvasCoords.ts`. |
| `constants/` | 1 | `devices.ts` — device-naming single source of truth (see Gotchas). |
| `styles/` | 2 | `globals.css`, `tokens.css` (design tokens). |
| `__tests__/` | 6 | Vitest suites: `cockpitStore`, `apiClient`, `projectionMirrors`, `eosActionQueue`, `ids`, plus `setup.ts`. |
| `public/` | 7 | PWA static assets: manifest, icons (192/512 + maskable), `offline.html`, `favicon.ico`. |
| `dist/` | 3 | Committed web build output (`index.html` + hashed JS/CSS bundle). |

Top-level files: `main.tsx` (bootstrap), `App.tsx` (auth gate + shell mount),
`sw.ts` (service worker), `capacitor-init.ts` (native shell init), `constants.ts`,
`global.d.ts`, `index.html`.

## Key components

**Entry & shell.** `main.tsx:1` creates the React root, registers the service worker
(non-native) or initializes Capacitor (native), and mounts `App` inside `ClerkProvider`.
`App.tsx:128` is the router: it renders `GuestJoinPage` for `/join/<code>`, the Clerk
`LoginScreen` when signed out, and `AuthenticatedApp` otherwise — which wires the
realtime hooks (`useOrganismRealtime`, `useVisionConnection`, `useKeyboard`), the
bootstrap sequence (`bootstrapStore.boot()` → chat history + polling), and mounts
`components/Shell.tsx`. Panels render only as canvas windows via
`canvasStore.addWindow` — `cockpitStore.activePanel` does **not** render (see
`App.tsx:29` comment); `?panel=<id>` deep-links open a panel as a window on load, the
same hook automated browser verification drives.

**Panels (80), grouped by organism concern:**
- **Chat / DEX & operator home:** `OperatorHomePanel`, `OperatorPanel`,
  `OperatorTimelinePanel`, `OperatorContinuityPanel`, `ContinuityPanel`, `ProfilePanel`.
- **Execution & runtime:** `ExecutionPanel`, `UnifiedExecutionPanel`, `ExecCoordPanel`,
  `ExecutorPanel` (1,016 lines), `OrchestratorPanel`, `DistributedRuntimePanel`,
  `RuntimePanel`, `DelegationPanel`, `RecoveryDashboardPanel`.
- **Build / meta-IDE loop:** `BuildLoopPanel`, `SelfBuildPanel`, `MetaIDEPanel`
  (1,285 lines), `EngineeringPanel`, `IntentLoopPanel`, `IntentPanel`,
  `OperatingLoopPanel`, `OrganismLoopPanel`, `TickLoopPanel`.
- **Browser & workspace:** `BrowserPanel`, `WorkstationPanel`, `WorkspaceTopologyPanel`,
  `TmuxPanel`, `InfrastructurePanel`, `ServiceGraphPanel`, `UMHNodePanel`, `PresencePanel`.
- **Analytics & intelligence:** `AnalyticsPanel`, `DashboardPanel`, `IntelligencePanel`,
  `PredictionPanel`, `WorkIntelligencePanel`, `RealityIntelligencePanel`,
  `CapabilityIntelligence`-backed `CapabilitiesPanel`/`CapabilityMapPanel`, `LearningPanel`,
  `MemoryPanel`, `KnowledgePanel`.
- **Voice & vision:** `VisionPanel`, `ScreenAwarenessPanel`, `ConferenceRoomsPanel`.
- **Governance / reality / organism:** `GovernancePanel`, `ApprovalsPanel`,
  `StateAuthorityPanel`, `ProofInspectorPanel`, `RealityGraphPanel`, `RealityTimelinePanel`,
  `WorldModelPanel`, `OrganismPanel`, `OrganismMapPanel`, `PropagationGraphPanel`,
  `CoherenceStore`-backed panels, `ProjectionPanel`/`ProjectionMirrorsPanel`/
  `ProjectionIntegrationPanel`, `UniversalWorkPanel`, `WorkPanel`, `PortfolioPanel`,
  `GoalPanel`, `CompanyPanel`, `StrategyPanel`/`StrategicPanel`/`ExecutivePanel`,
  `MVPReadinessPanel`, `SessionPanel`/`SessionResumePanel`, `SettingsPanel`,
  `CommandCenterPanel`/`CommandsPanel`, `CommsPanel`, `BroadcastPanel`, `TasksPanel`,
  `ActionsPanel`, `ActivityPanel`, `OperationsPanel`.

**Stores (81), grouped by domain:** each panel is backed by a Zustand store of the same
stem. Notable groupings: **canvas/window** (`canvasStore`, `unifiedCanvasStore`,
`agentCanvasStore`, `organismCanvasStore`, `harnessCanvasStore`, `loopCanvasStore`,
`workflowCanvasStore`, `collapseStore`, `viewContextStore`); **chat/DEX**
(`chatStore` — 408 lines, `cockpitStore`, `operatorExperienceStore`); **voice**
(`voiceStore`, `voiceSessionStore` — 1,220 lines, `voiceMessageStore` — 704 lines,
`realtimeStore`); **vision** (`visionStore` — 1,288 lines, `screenAwarenessStore`);
**loops** (`operatorLoopStore` — 1,553 lines, the largest file here,
`operatingLoopStore`, `intentLoopStore`, `organismLoopStore`); **execution/governance**
(`executionSummaryStore`, `unifiedExecutionStore`, `governanceStore`, `unifiedApprovalStore`,
`stateAuthorityStore`, `delegationStore`, `recoveryDashboardStore`); **reality/organism**
(`realityGraphStore`, `realityTimelineStore`, `realityIntelligenceStore`, `organismStore`,
`worldModelStore`, `coherenceStore`); **rooms** (`roomsStore` — 1,042 lines,
`presenceStore`, `deviceSessionStore`, `deviceStore`); plus `bootstrapStore`
(hydration gate consumed by `App.tsx`) and `settingsStore`/`configStore`.

**api/ (WebSocket + HTTP clients).** `client.ts` is the HTTP core — `fetchApi<T>` with
Clerk-token injection, in-flight GET de-dup, per-path timeouts (120s for
`/converse`/`/approve`/`/dispatch`, 60s otherwise), and `authHeader()` for raw
multipart `fetch`. WS clients: `websocket.ts` (base), `broadcast-ws.ts`,
`browser-ws.ts`, `vision-ws.ts`, and the voice cluster (`voice-ws.ts`,
`voice-controller.ts`, `voice-turn-assembler.ts`, `tts-playback-controller.ts`,
`platform-voice-adapter.ts`, `voiceErrorCodes.ts`). `voice-diag.ts` is the
**permanent** client-stage diagnostic beacon (`diagStartTap`/`diagStage`/`diagFlush`)
required by `.claude/rules/client-failure-observability.md` — never delete it as
scaffolding (see Gotchas).

**components/ subgroups.** `canvas/` (24) is the windowing engine —
`BaseCanvas`, `CanvasWorkspace` + its `*Workspace` variants, `CanvasWindow`,
`WindowContent` dispatcher and per-type contents (`PanelWindowContent`,
`BrowserWindowContent`, `TerminalWindowContent`, `VisionWindowContent`, etc.),
`WorkflowNode`/`WorkflowConnection`, palette/toolbar/context-menu. `rooms/` (17) is
the Discord-like server/channel/voice-room UI including `GuestJoinPage`. `vision/` (14)
holds the camera overlays (face/hand/pose/object tracking, scene inventory, HUD).
`cards/` (6) render structured message payloads (`RRIPRenderer`, `ApprovalCard`,
`ReportCard`, `CommandResultCard`, `ConversationBubble`, `ErrorCard`). The 51
top-level components are the app chrome: `Shell`, `LeftRail`/`RightRail`,
`LeftDrawer`/`RightDrawer`, `NavRail`, `HudBar`, `TitleBar`, `CommandPalette`,
`ConnectionBanner`, the `Fab*` action buttons, `Voice*` bars, and the `ViewportSelector`.

## Data & state
Reads/writes are all over the wire — no local DB. **HTTP:** all requests go to
`${API_BASE}` (`/api/umh/...`) with a Clerk bearer; the EOS read surfaces
(`/eos/activation`, `/eos/pipeline`, `/eos/kpis`, `/eos/activity`, …) and
`/workspace/mesh-nodes` feed panels. **WebSockets:** broadcast (organism realtime),
browser stream, vision stream, and the voice session/TTS channels. **Client state:**
81 Zustand stores held in memory; `bootstrapStore` hydrates from `/bootstrap` before
first render (`waitForHydration()` in `App.tsx:54`). **Service worker** (`sw.ts`)
caches the shell (`umh-shell-v2`), handles Web Push notifications, and serves
`offline.html`; `main.tsx` force-updates the SW on every load and reloads once on
`controllerchange` so a fresh deploy is picked up without a manual cache clear.
**Env:** `VITE_CLERK_PUBLISHABLE_KEY` (build-time) selects Clerk vs. no-auth mode.
**Device labels** come from `constants/devices.ts` (mirroring `infra/device_registry.json`).

## Gotchas
- **Layout is LOCKED (2026-07-03).** The full cockpit layout, chat styling, and input
  design — desktop *and* mobile — are frozen. Do not change Shell/rail/drawer geometry,
  chat bubble styling, or the input field without an explicit request. This is a
  standing user directive, not a suggestion.
- **`/chat/upload` requires the Clerk bearer on raw `fetch`.** That route is
  operator-role gated (`require_operator`). The voice-draft send path
  (`stores/voiceMessageStore.ts:608`) and chat-attachment path
  (`stores/chatStore.ts:150`) POST multipart `FormData` with a bare `fetch`, which
  can't use `fetchApi` (it would clobber the multipart boundary). They MUST spread
  `authHeader()` (`api/client.ts:124`) or the server returns 403 and the message
  silently "fails to send."
- **iOS-Safari mobile voice traps (8 known).** The voice path has bitten repeatedly on
  iOS Safari. The biggest: `unlockAudioForIOS()`'s `audio.play()` hangs on iOS 18.7 —
  never `await` a TTS-nicety on the mic-start critical path. Others include self-decode
  mp4, volatile-id consent, a request-scoped WS reconnect storm, `bearer.<jwt>`
  subprotocol auth, unbounded token fetch, a non-JWT token, and a frameless idle socket.
  When a voice failure is invisible in server logs, instrument the client with the
  `voice-diag.ts` beacon FIRST — do not ship a second speculative fix
  (`.claude/rules/client-failure-observability.md`).
- **`voice-diag.ts` is permanent.** It is a required diagnostic per the
  client-failure-observability law and partially enforced by Gate 14
  (`scripts/check_voice_runtime_divergence.py`). Do not remove it as "scaffolding."
- **Device names are never hardcoded.** Import from `constants/devices.ts` or read
  `/workspace/mesh-nodes`. Never write literal "VPS"/"Beast"/"Windows" in renderer code
  (`.claude/rules/device-naming.md`).
- **Panels don't render from `activePanel`.** Only `canvasStore.addWindow` renders a
  panel (as a canvas window). Setting `cockpitStore.activePanel` alone shows nothing —
  a real footgun when wiring new navigation (`App.tsx:29`).
- **`dist/` is committed build output**, not source. The 335 file count includes it and
  the 7 `public/` PWA assets; treat only the 326 non-`dist` source files as editable.

## See also
- [`cockpit/`](./cockpit.md) — parent: the Electron/Capacitor shell, nginx, deploy gate.
- [`transports/`](./transports.md) — the HTTP/WS API layer this renderer consumes.
- [`substrate-organism/`](./substrate-organism.md) — organism state the panels project.
- [`../architecture.md`](../architecture.md) — the four-layer dependency-direction law.
- [Full file inventory](../inventory/cockpit.md)
