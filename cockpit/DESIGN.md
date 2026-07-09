<!-- LOCKED 2026-07-08 — Do not modify without explicit AFM request -->

# UMH Cockpit — Design Specification

This document is the authoritative design lock for the cockpit UI.
Every value here reflects the confirmed, deployed state as of 2026-07-08.
Changes to any value require explicit AFM approval.

Re-locked 2026-07-08 to capture the voice-message player, chat overflow-wrap
hardening, audio media type, and removal of the voice routing HUD. All layout
values (LeftDrawer 160, RightDrawer 240, HudBar 30, TitleBar 36) are unchanged
from the 2026-07-03 lock.

Applies to: **Web app** (universalmetaharness.tech), **Desktop app** (Electron), **Mobile** (web at ≤640px).

---

## 1. Design Tokens (`styles/tokens.css`)

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--color-canvas` | `#0A0A0A` | Deepest background (BaseCanvas) |
| `--color-surface` | `#111111` | Primary surface |
| `--color-surface-raised` | `#1A1A1A` | Elevated cards, inputs, bubbles |
| `--color-surface-overlay` | `#222222` | Menus, dropdowns |
| `--color-border` | `#2A2A2A` | Default borders |
| `--color-border-active` | `#3A3A3A` | Active/hover borders, scrollbar thumb |
| `--color-cyan` | `#00E5FF` | Primary accent |
| `--color-cyan-dim` | `#00E5FF66` | Selection highlight |
| `--color-cyan-glow` | `#00E5FF1A` | Glow backgrounds (hover states only) |
| `--color-ok` | `#00FF88` | Success/online |
| `--color-warn` | `#FFB800` | Warning/connecting |
| `--color-danger` | `#FF3D3D` | Error/danger |
| `--color-violet` | `#A855F7` | Accent (NOT used in chat bubbles) |
| `--color-text-primary` | `#E0E0E0` | Primary text |
| `--color-text-secondary` | `#888888` | Secondary text, AI responses |
| `--color-text-tertiary` | `#555555` | Tertiary text, labels |
| `--color-text-inverse` | `#0A0A0A` | Inverse text |

### Runtime Colors

| Runtime | Color | Background |
|---------|-------|------------|
| claude | `#D4A017` | `rgba(212,160,23,0.12)` |
| codex | `#00FF88` | `rgba(0,255,136,0.12)` |
| hermes | `#A855F7` | `rgba(168,85,247,0.12)` |
| shell | `--text-secondary` | `rgba(136,136,136,0.12)` |
| browser | `#60A5FA` | `rgba(96,165,250,0.12)` |
| local-model | `#FF6B6B` | `rgba(255,107,107,0.12)` |

### Typography

| Token | Value |
|-------|-------|
| `--font-mono` | `"JetBrains Mono", "Fira Code", "SF Mono", "Cascadia Code", ui-monospace, monospace` |
| `--font-sans` | `"Inter", ui-sans-serif, system-ui, sans-serif` |
| Base font-size | `13px` |
| Line-height | `1.5` |

### Layout Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--spacing` | `3px` | Base spacing scale |
| `--spacing-rail` | `180px` | LeftRail expanded width |
| `--spacing-rail-collapsed` | `54px` | LeftRail collapsed width |
| `--spacing-hud-height` | `30px` | HudBar height |
| `--spacing-chat-width` | `360px` | Reserved |
| `--spacing-titlebar-height` | `36px` | TitleBar height |
| `--drawer-width` | `420px` | Detail drawer width |
| `--drawer-z` | `50` | Detail drawer z-index |

---

## 2. Component Classes (`styles/globals.css`)

| Class | Properties |
|-------|------------|
| `.wv-card` | bg: surface, border: 1px solid border, radius: 4px |
| `.wv-card-raised` | bg: surface-raised, border: 1px solid border, radius: 4px |
| `.wv-badge` | inline-flex, gap 3px, padding 3px 6px, radius 3px, 11px mono uppercase |
| `.wv-badge-ok/warn/danger/cyan/violet` | 15% color-mix bg, color border, 1px solid dim border |
| `.wv-label` | 10px, line-height 1, uppercase, letter-spacing 0.1em, text-tertiary, mono |
| `.wv-metric` | 28px, weight 600, mono, letter-spacing -0.02em |
| `.wv-hairline` | border-bottom: 1px solid border |
| `.wv-glow-cyan` | box-shadow: 0 0 12px/4px cyan-glow |
| `.wv-pulse` | 2s ease-in-out opacity pulse |
| `.wv-scanline` | repeating-linear-gradient scanline overlay |
| `.titlebar-drag` | -webkit-app-region: drag |
| `.titlebar-no-drag` | -webkit-app-region: no-drag |

### Detail Drawer

```
.wv-drawer: fixed, top 0, right 0, bottom 0, width: 420px, z: 50
  slide-in: transform translateX(100%) → translateX(0), 200ms ease-out
  @media (max-width: 640px): width: 100vw
```

### Chat Markdown (`.chat-markdown`)

Base rule (`min-width: 0; max-width: 100%; overflow-wrap: anywhere;
word-break: break-word`) — the chat body must NEVER push horizontal scroll.
Every child that could hold a long token is bounded to wrap in place.

- base: `min-width 0`, `max-width 100%`, `overflow-wrap anywhere`, `word-break break-word`
- `p`: margin-bottom 0.5em
- `strong`: weight 700, text-primary
- `code`: 0.9em, 0 3px padding, radius 3px, bg surface-raised
- `pre`: 0.5em margin, 6px padding, radius 3px, bg surface-raised, 0.85em, **`overflow-x: hidden`**
- `pre code`: **`word-break: break-all`, `white-space: pre-wrap`** (long code wraps, never scrolls)
- `table`: full width, collapse, 0.85em, **`table-layout: fixed`, `word-break: break-word`**
- `th`: bg surface-raised, text-secondary, weight 600, uppercase
- `a`: color cyan, underline
- `blockquote`: 2px left border, text-tertiary

### Comms Bubbles

```
.wv-bubble-self:  bg cyan, color canvas, radius 12/12/3/12, padding 6px 12px, max-width 75%, ml auto
.wv-bubble-other: bg surface-raised, radius 12/12/12/3, padding 6px 12px, max-width 75%
```

---

## 3. Shell Layout (`Shell.tsx`)

Root: `flex flex-col bg-surface`, height: `100dvh`

### Window Modes

| Mode | Render |
|------|--------|
| `maximized` | Full layout (TitleBar + main + HudBar) |
| `large-fab` | Centered 280px card with chat input |
| `medium-fab` | Centered pill with mode dot + mic |
| `small-fab` | Centered 48×48 circle with voice waveform |
| `invisible` | null |

### Maximized Structure

```
TitleBar                         (36px, z-50, flow)
main                             (flex-1, overflow-hidden, relative)
  ├─ UnifiedCanvasWorkspace      (fills main, contains LeftDrawer)
  ├─ ControlPanel                (absolute overlay)
  ├─ RightDrawer                 (absolute overlay)
  └─ CallOverlay                 (absolute bottom strip)
HudBar                           (fixed bottom-0, 30px, z-50)
VoiceCommandBar                  (absolute, Electron only, z-50)
CommandPalette                   (fixed overlay, z-50, Ctrl+K)
```

---

## 4. Component Specifications

### TitleBar

- **Height**: `var(--spacing-titlebar-height)` = 36px
- **CSS**: `flex items-center px-3 select-none bg-surface border-b border-border relative z-50`
- **Left**: CanvasMenuBar (Canvas/View/Mode dropdown menus)
- **Right**: Window control buttons (fullscreen, minimize, maximize, close)
  - Each: `w-8 h-6`, text-[10px], text-text-secondary, hover:bg-surface-raised
  - Close: hover:bg-danger hover:text-white
- **Electron**: titlebar-drag enables OS window dragging
- **Web**: Minimize/maximize/close are no-ops (fullscreen toggle works)

### CanvasMenuBar

- **Position**: Left side of TitleBar
- **Menus**: Canvas, View, Mode
- **Button**: `px-2 py-1 text-[10px] rounded`
- **Dropdown**: absolute, bg surface-raised, border, min-w 180px, z-50
- **Mode order**: General, Organism, Agents, Harnesses, Loops, Workflows

### ControlPanel

- **CSS**: `wv-card absolute`
- **Desktop**: top:6, left:172, right:252, z-20
- **Mobile**: top:6, left:6, right:6, z-30
- **Collapsed strip**: `flex items-center gap-2 px-4 py-2 flex-wrap`
  - Status/Mode/Risk badges: `text-[10px] font-bold px-2 py-1 rounded border`
  - Counters: `text-[10px] font-mono uppercase text-text-tertiary`
- **Expanded**: `grid grid-cols-3 gap-4` (Approvals, Overnight, Resources)

### LeftDrawer

- **CSS**: `wv-card absolute z-20 flex flex-col overflow-hidden overflow-y-auto`
- **Desktop**: width 160px, left:6, top:6, bottom:36
- **Mobile**: width calc(33vw), left:6, top:80, bottom:78
- **Content**: CanvasPalette
- **Default state**: closed (`leftDrawerOpen: false`)

### RightDrawer

- **CSS**: `wv-card absolute z-20 flex flex-col overflow-hidden`
- **Desktop**: width 240px, right:6, top:6, bottom:36
- **Mobile**: width calc(55vw), right:6, top:80, bottom:78
- **Content**: RightRail (chat panel)
- **Default state**: closed (`rightDrawerOpen: false`)

### HudBar

- **Position**: `fixed bottom-0 left-0 right-0`, z-50
- **Height**: `var(--spacing-hud-height)` = 30px
- **CSS**: `flex items-center gap-4 px-3 select-none bg-surface border-t border-border`
- **Content (L→R)**: Radio + Full-Screen label, online dot, workstation posture, continuity state, lifecycle mode, profile modes, node count, STT/TTS dots, camera status, voice ticker (or spacer), attention badge, organism metrics (cpu/gpu/ram/disk/nodes), mesh count, API/WS/Voice dots
- **StatusDot**: `w-[6px] h-[6px] rounded-full` — ok/warn/danger

### BaseCanvas

- **Container**: `relative w-full h-full overflow-hidden outline-none`
- **Background**: `var(--color-canvas)` (#0A0A0A)
- **Cursor**: `grab` default, `grabbing` while panning
- **Touch-action**: `none`
- **Dot grid**: `radial-gradient(circle, var(--color-border) 1px, transparent 1px)`, 20px spacing × zoom, opacity 0.5
- **Transform layer**: `translate(panX, panY) scale(zoom)`, origin 0 0
- **Pan**: middle-click, left-click on `data-canvas-pan`, or space+click
- **Touch**: single-finger pan on canvas bg, two-finger pinch-zoom
- **Zoom**: Ctrl/Cmd+wheel at cursor point, ZOOM_FACTOR 0.08, range 0.05–5.0
- **Palette slot**: absolute top-0 left-0 h-full z-10
- **Toolbar slot**: absolute bottom:36, centered, z-10

### CanvasToolbar

- **Position**: absolute bottom center, bottom:36px, z-10
- **Height**: 36px
- **CSS**: bg rgba(17,17,17,0.85), backdropFilter blur(8px), border 1px solid border, radius 4
- **Mobile**: maxWidth calc(100vw - 12px)
- **Content (L→R)**: palette toggle | canvas dropdown | zoom out / zoom % / zoom in / reset | extra buttons | panel switcher | chat toggle
- **Separator**: `mx-1`, 1px wide, 16px tall, bg border

### CanvasWindow

- **Position**: absolute in transform layer
- **Styling**: bg surface, border 1px solid border, radius 6
- **Header**: 32px, bg surface-raised, grab cursor
- **Default sizes**: browser 800×600, desktop 960×540, vision 640×480, terminal 600×400, preview 800×600, agent 400×500, panel 600×500
- **Resize min**: 200×150
- **Maximized**: `fixed inset-0 z-9999`
- **Collapsed**: height 32px (header only)
- **Cluster border**: 3px solid cyan on left
- **Selection outline**: 2px solid cyan, offset -2px
- **Status dot**: 8px circle (connected=#22c55e, connecting=#f59e0b, disconnected=#6b7280, error=#ef4444)

### AgentCanvasNode

- **Default size**: 400×500
- **Grid layout**: 3 columns, 20px gap
- **Styling**: same as CanvasWindow (surface/border/radius 6)
- **Maximized**: fixed inset-0 z-9999, shows AgentConfigView

---

## 5. Chat (RightRail) Styling

### Input Layout

```
[hidden file input: accept="*/*"]
┌─────────────────────────────────────────┐  ┌──────┐
│ 📎  Message {aiName}...            🎤  │  │  ➤   │
└─────────────────────────────────────────┘  └──────┘
  paperclip   text input            mic       send
  inside      flex-1                inside    outside
```

- **Container**: `flex items-center gap-1`
- **Input box**: `flex-1 flex items-center rounded bg-surface-raised border border-border`
- **Paperclip**: `p-1 ml-0.5 rounded`, Paperclip icon 12px, accepts all file types
- **Text input**: `flex-1 text-[11px] px-1.5 py-1.5 bg-transparent min-w-0`
- **Mic button**: `p-1 mr-0.5 rounded shrink-0`, Mic/MicOff 12px
- **Send button**: `p-1.5 rounded text-cyan shrink-0`, Send 12px

### Bubble Colors (grey/white only — NO blue, NO purple)

| Element | Class |
|---------|-------|
| Operator bubble | `bg-surface-raised text-text-primary ml-4` |
| AI bubble | `bg-surface-raised text-text-secondary mr-4` |
| AI response text | `color: var(--color-text-secondary)` |
| Voice badge | `bg-surface text-text-tertiary` |
| Media badge | `bg-surface text-text-tertiary` |
| Model tier badge | `bg-surface text-text-tertiary` |
| Draft voice bubble | `bg-surface-raised`, opacity 0.70 |
| Speaking badge | `bg-surface text-text-tertiary` |

### Multimodal File Support

- `PendingMedia.media_type`: `'image' | 'video' | 'audio' | 'file'`
- `MediaAttachment.media_type`: `'image' | 'video' | 'audio' | 'file'`
- `addPendingMedia`: accepts ALL file types (no whitelist filter)
- Image preview: 48×48 thumbnail
- Video preview: 48×48 "VID" label
- File preview: 48×minWidth48 with truncated filename
- MediaGrid: image → linked `<img>` (maxHeight 200); video → native `<video controls>`
  (maxHeight 200); **audio → `VoiceMessagePlayer`** (spec below); file → download link

### Voice Message Player (`VoiceMessagePlayer`)

The playable audio bubble for operator voice messages. Compact, matches the UI —
a bare cyan glyph, NOT a filled circle or glow button. Used in BOTH places audio
appears: the sent message (MediaGrid, `media_type === 'audio'`) AND the pre-send
voice draft review card (`VoiceDraftCard`). No native `<audio controls>` chrome
appears anywhere in the chat — the draft card uses this same component so the play
button looks identical before and after send.

- **Card**: `flex items-center gap-1.5 mt-1 px-1.5 py-1 rounded w-full max-w-[180px]`,
  inline `background: var(--color-surface)`, `border: 1px solid var(--color-border)`
- **Play/Pause**: BARE lucide icon, no bg/circle/glow — `Play`/`Pause` size **11**,
  `color: var(--color-cyan)`, `shrink-0 cursor-pointer transition-colors`
- **Progress track**: `flex-1 min-w-0` wrapper; track `h-1 rounded-full cursor-pointer`
  on `var(--color-border)`; fill `h-full rounded-full` at `var(--color-cyan)`,
  width = `${pct}%`; **click-to-seek** enabled
- **Timestamp**: `shrink-0 text-[8px] font-mono`, `color: var(--color-text-tertiary)` —
  shows current time while playing/scrubbed, otherwise total duration (`m:ss`)
- `<audio preload="metadata" playsInline>` (no native controls chrome)
- **Persistence**: voice messages survive reload — the audio artifact is stored on the
  operator turn (`media` round-trips through `/advisor/converse` → `save_conversation_turn`
  → `/chat/history` → `loadHistory`) and re-renders identically, exactly like text.

### Overflow Containment (chat never scrolls horizontally)

The chat column is bounded so no message — long URLs, code, tables, tokens — ever
forces a horizontal scrollbar. This is a locked invariant.

- Scroll container: `flex-1 min-w-0 overflow-y-auto overflow-x-hidden space-y-2 mb-2`
- `ConversationBubble` (operator + AI): `w-fit min-w-0` on the bubble;
  operator text `<p>` is `whitespace-pre-wrap break-words [overflow-wrap:anywhere]`
- Markdown body: `.chat-markdown` base wrap rules (see §2 Chat Markdown)

### Voice Routing HUD — REMOVED

The `VoiceRouteHud` banner ("VOICE ROUTE / Resolving route…") is deleted. No
component, import, or render exists. Voice failures surface only as the terminal
error banner below — never a routing overlay.

### Voice Error Banner

- Shown only when `voiceError && VOICE_TERMINAL_OUTCOMES.has(voiceLastOutcome)` —
  transient states (requesting/granting/connecting) stay silent
- Style: `text-[9px] font-mono text-danger mb-1 px-1.5 py-1 bg-danger/10 rounded
  border border-danger/40 flex items-center gap-1`, `Mic` icon size 9
- Terminal codes include the typed voice-WS taxonomy: `VOICE_WS_AUTH_TOKEN_MISSING`,
  `VOICE_WS_AUTH_TIMEOUT`, `VOICE_WS_AUTH_FAILED`, `VOICE_WS_UPGRADE_FAILED`,
  `VOICE_WS_PROXY_FAILED`, `VOICE_RUNTIME_TIMEOUT`, `VOICE_RUNTIME_UNAVAILABLE`,
  `VOICE_RUNTIME_NOT_MOUNTED` — each renders a precise reason, never a generic
  "unreachable"

### Message Structure

- Operator: `text-[11px]`, header `text-[9px] font-mono text-text-tertiary`
- AI: `text-[11px]`, header with aiName + intent badges + model tier + timestamp
- Suggested actions: `text-[9px] font-mono px-1.5 py-0.5 rounded border border-cyan/30 text-cyan`
- Attachments: download button with `Download` icon
- Thinking indicator: `animate-pulse` "{aiName} is thinking..."

---

## 6. Canvas Modes

Six modes, each with own zustand store for pan/zoom state:

| Mode | Workspace | Store Key | Unique UI |
|------|-----------|-----------|-----------|
| `general` | CanvasWorkspace | `cockpit:canvas` | CanvasWindow grid, context menu, clustering, presets |
| `agents` | AgentCanvasWorkspace | `cockpit:agent-canvas` | AgentCanvasNode grid, show all/tile/fit, dismiss |
| `workflows` | WorkflowCanvasWorkspace | `cockpit:workflow-canvas` | List + editor views, SVG connections, node types |
| `loops` | LoopCanvasWorkspace | `cockpit:loop-canvas` | List + detail views, persistent + lifecycle sections |
| `harnesses` | HarnessCanvasWorkspace | `cockpit:harness-canvas` | List + detail views, runtime class groups |
| `organism` | OrganismCanvasWorkspace | `cockpit:organism-canvas` | Map + detail views, topology nodes, edge summary |

---

## 7. Mobile vs Desktop

Breakpoint: **640px** (`useIsMobile()` via `window.matchMedia`)

| Component | Desktop | Mobile |
|-----------|---------|--------|
| LeftDrawer | 160px, top:6, bottom:36 | calc(33vw), top:80, bottom:78 |
| RightDrawer | 240px, top:6, bottom:36 | calc(55vw), top:80, bottom:78 |
| ControlPanel | left:172, right:252, z-20 | left:6, right:6, z-30 |
| CanvasToolbar max-width | unconstrained | calc(100vw - 12px) |
| Toolbar zoom % text | visible | hidden |
| Toolbar reset button | visible | hidden |
| Detail drawer | 420px | 100vw |

---

## 8. Web vs Electron

| Feature | Electron | Web |
|---------|----------|-----|
| TitleBar drag | Works (app-region: drag) | No effect |
| Window controls | Functional via `window.cockpit.window` | No-ops |
| VoiceCommandBar | Renders | Does not render |
| Window modes | All 5 work (IPC resize) | Only maximized meaningful |
| Voice engine | Native `window.cockpit.voice` | Requires HTTPS + mediaDevices |
| File operations | `window.cockpit.readDir/readFile/writeFile` | Not available |
| Build | `electron-vite build` → dist/ | `vite build --config vite.web.config.ts` → dist-web/ |

---

## 9. Z-Index Stack

```
z-0      BaseCanvas (bg #0A0A0A, dot grid)
z-10     Canvas palette slot, canvas toolbar slot
z-var    CanvasWindows (dynamic via bringToFront)
z-20     LeftDrawer, RightDrawer, ControlPanel (desktop)
z-30     ControlPanel (mobile only)
z-50     TitleBar, HudBar, VoiceCommandBar, CommandPalette, Detail drawer
z-100    CanvasContextMenu
z-9999   Maximized CanvasWindow
```

---

## 10. Cockpit Store Defaults

```
activePanel: 'commandcenter'
chatOpen: false
splitPanel: null
mode: 'EXECUTE'
windowMode: 'maximized'
railCollapsed: true
rightRailCollapsed: true
controlPanelExpanded: false
leftDrawerOpen: false
rightDrawerOpen: false
rightPanelView: 'chat'
apiStatus: 'disconnected'
wsStatus: 'disconnected'
voiceStatus: 'disconnected'
```

Persisted to `localStorage` key `cockpit:shell`: activePanel, railCollapsed, rightRailCollapsed, leftDrawerOpen, rightDrawerOpen, rightPanelView.

---

## 11. FAB Modes (Electron)

### FabSmall (48×48)
- Rounded-full, bg canvas, border 1px solid border, shadow 0 4px 16px rgba(0,0,0,0.4)
- Content: VoiceWaveform (auto-starts voice)

### FabMedium (pill)
- Rounded-full, px-3 py-2, same bg/border/shadow
- Content: mode color dot, mic button, up/down cycle buttons

### FabLarge (280px)
- Rounded-lg, p-3, bg canvas, border, shadow 0 8px 32px rgba(0,0,0,0.4)
- Content: mode dot + label, agents count, mic, chat input + submit, cycle buttons

---

## 12. Overlay Components

### CommandPalette (Ctrl+K)
- Overlay: fixed inset-0, z-50, bg rgba(0,0,0,0.6), backdropFilter blur(4px)
- Dialog: 500px wide, max-h 384px, radius 8px, bg surface, border border-active
- Input: px-4 py-3, text-sm (14px)
- Results: max-h 288px, items px-4 py-2.5

### CallOverlay
- Position: absolute bottom-0 left-0 right-0, z-10, inside main
- Height: h-9 (36px), bg surface-raised, border-t border
- Content: status dot + text, mute/deafen/return/leave buttons

### VoiceCommandBar (Electron only)
- Position: absolute, bottom calc(hud-height + 16px), centered, z-50
- Shape: pill (radius 28px), backdropFilter blur(12px)
- Content: VoiceOrb (48×48 animated), transcript, activation toggles

---

*End of design specification.*
