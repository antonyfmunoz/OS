# WorldView Design System — Reference for Cockpit Unification

Extracted from commit bc928075 (original cockpit shell, 2026-05-18).
This is the style AFM preferred. The Electron rebuild lost it.
Next build session: restore this as the canonical design system.

## Design Tokens

```css
/* Canvas */
--color-canvas: #0A0A0A
--color-surface: #111111
--color-surface-raised: #1A1A1A
--color-surface-overlay: #222222
--color-border: #2A2A2A
--color-border-active: #3A3A3A

/* Accent */
--color-cyan: #00E5FF
--color-cyan-dim: #00E5FF66
--color-cyan-glow: #00E5FF1A

/* Semantic */
--color-ok: #00FF88
--color-ok-dim: #00FF8866
--color-warn: #FFB800
--color-warn-dim: #FFB80066
--color-danger: #FF3D3D
--color-danger-dim: #FF3D3D66
--color-violet: #A855F7
--color-violet-dim: #A855F766

/* Text */
--color-text-primary: #E0E0E0
--color-text-secondary: #888888
--color-text-tertiary: #555555

/* Typography: JetBrains Mono primary, Inter for body */
/* Sizes: 9-14px range. All uppercase labels with wide tracking. */

/* Layout */
--spacing-rail: 240px
--spacing-rail-collapsed: 56px
```

## Component Classes

```css
.wv-card        — bg surface, 1px border, 4px radius
.wv-card-raised — bg surface-raised, 1px border, 4px radius
.wv-badge       — inline-flex, 11px mono, uppercase, 0.05em tracking
.wv-badge-ok    — 15% ok bg, ok text, ok-dim border
.wv-badge-warn  — 15% warn bg, warn text, warn-dim border
.wv-badge-danger— 15% danger bg, danger text, danger-dim border
.wv-badge-cyan  — 15% cyan bg, cyan text, cyan-dim border
.wv-badge-violet— 15% violet bg, violet text, violet-dim border
.wv-label       — 10px uppercase, 0.1em tracking, text-tertiary, mono
.wv-metric      — 28px, weight 600, mono, -0.02em tracking, line-height 1
.wv-hairline    — 1px bottom border in border color
.wv-glow-cyan   — box-shadow: 0 0 12px cyan-glow, 0 0 4px cyan-glow
.wv-pulse       — 2s ease-in-out infinite opacity pulse
.wv-scanline    — repeating gradient overlay (cyan 3% every 4px)
```

## LeftRail (Navigation)

- 240px expanded, 56px collapsed
- Grouped routes with section labels (wv-label)
- Lucide icons + text labels (12px mono)
- Active: cyan text + cyan-glow bg + 2px right border cyan
- Inactive: text-secondary, hover → text-primary + surface-raised bg
- Header: WS status dot (ok/danger) + "UMH Cockpit" label
- Footer: presence mode indicator (Radio icon + pulse)
- Collapse toggle: chevron button

## CommandCenter Layout

- Title bar: "COMMAND CENTER" 14px mono uppercase tracking-widest + Live dot
- PulsePanel: 7 metrics in grid-cols-7, each = wv-metric (28px) + wv-label
- ModelBadges: wv-card with rows showing badge-status + name + provider + latency + cost
- TraceStream: wv-card, scrollable, rows with status-icon + time + agent + action + duration
- ApprovalQueue: wv-card with wv-card-raised items, risk badges, approve/deny buttons
- Layout: 2-column grid below pulse panel

## StatusBar (Bottom HUD)

- bg-surface, top border, 32px height
- Left: presence mode, route label
- Right: system metrics (cpu/mem/agents), timestamps

## Key Differences from Current Cockpit

Current tokens.css uses different values:
- --bg: #07080a (vs #0A0A0A — close but different)
- --surface-1: #0f1012 (vs #111111)
- --border: #ffffff08 (vs #2A2A2A — MUCH less visible)
- --text-primary: #ffffffee (vs #E0E0E0)
- NavRail: 48px icon-only (vs 240px with labels)
- No wv-* component classes at all
- No scanline effect, no glow utilities
- Badges not semantic-colored

## Voice Integration Plan

Voice should be part of the shell chrome, not a floating overlay:
- LeftRail bottom section: voice status + activation button
- StatusBar: live transcript ticker + mic level
- VoiceCommandBar: keep orb + activation modes, but style with wv-* classes
- Active voice session: LeftRail voice section expands with waveform
- Wake word / clap / always-on toggles: settings panel or rail footer

## Original Source Files (for full extraction)

All at commit bc928075:
- jarvis/jarvis_web/src/index.css — full WorldView CSS
- jarvis/jarvis_web/src/views/CommandCenter.tsx — dashboard
- jarvis/jarvis_web/src/views/Awareness.tsx — 6-tier awareness
- jarvis/jarvis_web/src/views/Infrastructure.tsx — node grid
- jarvis/jarvis_web/src/components/LeftRail.tsx — navigation
- jarvis/jarvis_web/src/components/StatusBar.tsx — bottom HUD
- jarvis/jarvis_web/src/components/PresenceOverlay.tsx — 4 presence modes
- jarvis/jarvis_web/src/stores/cockpitStore.ts — unified Zustand store
- jarvis/jarvis_web/src/types/routes.ts — 18 routes, 4 groups
