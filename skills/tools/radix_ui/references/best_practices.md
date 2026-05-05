# Radix UI Primitives — Creator-Level Best Practices

Last researched: 2026-04-06
Version: @radix-ui/react-* 1.x (per primitive)
Source: https://www.radix-ui.com/primitives/docs

This is the 19-section research protocol applied to Radix UI Primitives.
Sections marked **N/A** include rationale because Radix is a pure
client-side React library with no network surface.

---

## Authentication

**N/A — Radix UI Primitives is a client-only React library with no
network calls, no API keys, no tokens, no service accounts, no OAuth,
no webhook signing, and no rate-limited backend.** Every primitive
ships as ESM/CJS to `node_modules` and runs entirely in the user's
browser. The package never phones home, never calls Radix's servers
(there are no Radix servers for Primitives — Radix Themes is a
separate styled layer also without a backend), and has no concept
of a "user" or "tenant."

The closest things to "auth concerns" are:

1. **Package integrity** — install only from npm under the
   `@radix-ui/react-*` scope. There are typo-squatting packages
   (`radix-ui-react-*` without the `@` scope). Check the publisher is
   `radix-ui` on npm, and use `npm ci` with a committed `package-lock.json`.
2. **Version pinning across primitives** — see Section 12 (Version
   Pinning). Mismatched internal `@radix-ui/react-presence` versions
   cause double-mount bugs. Pin or dedupe.
3. **CSP for Portals** — if you ship a strict Content Security Policy,
   Radix Portals render to `document.body`, which is fine, but inline
   styles set on positioned elements (Popover, Tooltip) require
   `'unsafe-inline'` in `style-src` or use `nonce`. Most apps already
   allow inline styles for Tailwind.

---

## Core Operations

Radix Primitives is a collection of independent packages. Each
primitive exports a `Root` plus a set of named parts. Imports are
namespace-style: `import * as Dialog from "@radix-ui/react-dialog"`.

### Dialog (`@radix-ui/react-dialog`)

Parts:
- `Dialog.Root` — context provider; props: `open`, `defaultOpen`, `onOpenChange`, `modal` (default `true`)
- `Dialog.Trigger` — button that opens the dialog; supports `asChild`
- `Dialog.Portal` — renders children into `document.body`; props: `container`, `forceMount`
- `Dialog.Overlay` — full-viewport backdrop; data-state, data-side
- `Dialog.Content` — the dialog box; props: `onOpenAutoFocus`, `onCloseAutoFocus`, `onEscapeKeyDown`, `onPointerDownOutside`, `onInteractOutside`, `forceMount`
- `Dialog.Title` — required for accessibility (`aria-labelledby`)
- `Dialog.Description` — optional (`aria-describedby`)
- `Dialog.Close` — button that closes; supports `asChild`

State machine: `closed → open` driven by `open`/`onOpenChange`. Modal
mode (default) traps focus, scroll-locks `<body>`, blocks pointer
events outside Content via the Overlay.

### Popover (`@radix-ui/react-popover`)

Parts: `Root`, `Trigger`, `Anchor`, `Portal`, `Content`, `Arrow`, `Close`.

`Content` props:
- `side`: `"top" | "right" | "bottom" | "left"` (default `"bottom"`)
- `sideOffset`: number (px gap from anchor)
- `align`: `"start" | "center" | "end"` (default `"center"`)
- `alignOffset`: number
- `avoidCollisions`: boolean (default `true`) — flips/shifts to stay in viewport
- `collisionBoundary`: `Element | Element[]` — defines the viewport box
- `collisionPadding`: number | object
- `sticky`: `"partial" | "always"`
- `hideWhenDetached`: boolean — hides when anchor is scrolled offscreen

Positioning is implemented via `@floating-ui/react-dom` under the hood
since Radix 1.x. You get all of Floating UI's middleware behavior
without importing it.

### DropdownMenu (`@radix-ui/react-dropdown-menu`)

Parts: `Root`, `Trigger`, `Portal`, `Content`, `Arrow`, `Item`,
`Group`, `Label`, `CheckboxItem`, `RadioGroup`, `RadioItem`,
`ItemIndicator`, `Separator`, `Sub`, `SubTrigger`, `SubContent`.

`Item` props: `onSelect: (e: Event) => void` (call `e.preventDefault()`
to keep menu open), `disabled`, `textValue` (for typeahead).

Keyboard: ↑/↓ navigate, Enter/Space select, Escape close, → opens
SubContent, ← closes SubContent, Home/End jump, typeahead by letter.

### Select (`@radix-ui/react-select`)

Parts: `Root`, `Trigger`, `Value`, `Icon`, `Portal`, `Content`,
`Viewport`, `Item`, `ItemText`, `ItemIndicator`, `Group`, `Label`,
`Separator`, `ScrollUpButton`, `ScrollDownButton`.

Critical: `Item.value` must be a non-empty string. Empty string is
reserved.

### Tooltip (`@radix-ui/react-tooltip`)

Parts: `Provider` (REQUIRED ancestor), `Root`, `Trigger`, `Portal`,
`Content`, `Arrow`.

`Provider` props: `delayDuration` (default 700ms), `skipDelayDuration`
(default 300ms), `disableHoverableContent`.

### AlertDialog (`@radix-ui/react-alert-dialog`)

Same parts as Dialog plus `AlertDialog.Action` and `AlertDialog.Cancel`.
Differs from Dialog: NOT dismissable via Escape outside-click — user
must explicitly choose Action or Cancel. Use for destructive
confirmations only.

### Tabs, Accordion, NavigationMenu, ContextMenu, HoverCard, RadioGroup, Slider, Switch, Toggle, ToggleGroup, ScrollArea, Avatar, Collapsible, Separator, AspectRatio, VisuallyHidden, Portal, Slot

Each follows the same pattern: `Root` + named parts, ARIA wired
internally, fully controllable via `value`/`onValueChange` (or
`open`/`onOpenChange` for disclosure primitives).

### Slot (`@radix-ui/react-slot`)

```tsx
import { Slot } from "@radix-ui/react-slot";

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp ref={ref} {...props} />;
  },
);
```

This pattern is the foundation of every shadcn `Button`, `Link`,
`Badge`, etc. and is what makes `<Dialog.Trigger asChild><Button>...</Button></Dialog.Trigger>` work.

### Portal (`@radix-ui/react-portal`)

```tsx
import { Portal } from "@radix-ui/react-portal";
<Portal container={document.getElementById("modal-root")}>...</Portal>
```

Lower-level than the per-primitive `Portal` parts. Use directly only
when building custom overlay primitives.

---

## Pagination

**N/A — Radix Primitives has no concept of paginated data.** It is a
UI primitives library, not a data layer. The closest pagination-
adjacent primitive is `ScrollArea`, which provides custom-styled
scrollbars but does not paginate. If you need paginated data inside a
Radix `Dialog` or `Popover`, the data layer is your responsibility
(usually TanStack Query + TanStack Table — see those skills).

For long lists inside `Select`, `DropdownMenu`, or `Combobox`
(typically built on Radix Popover + a list library like cmdk), use
list virtualization via `@tanstack/react-virtual` rather than
pagination — Radix Popover handles arbitrary content height with
`ScrollArea` or native overflow.

---

## Rate Limits

**N/A — Radix Primitives is a client-side React library with no
network surface.** There is no API to throttle. The closest
"rate-limit-like" concerns are:

- **Animation frame budget** — heavy Popover positioning recomputes on
  scroll/resize. Radix uses `@floating-ui/react-dom` which is highly
  optimized, but if you nest 20 popovers in a virtualized list you
  may see jank. Mitigation: only render `Content` when `open === true`
  (default), don't `forceMount` everything.
- **Focus trap re-entry** — if your app rapidly opens/closes a Dialog
  (e.g., a polling loop that triggers a confirm), focus management
  may stutter. Debounce open state.

---

## Error Codes

**Radix throws or warns rather than returning error codes** because it
runs in-process. Notable errors and warnings:

| Trigger | Type | Meaning | Fix |
|---|---|---|---|
| `Select.Item` with `value=""` | runtime throw | Empty string reserved for clear-selection | Use `value="none"` or any non-empty sentinel |
| `Dialog.Content` without `Dialog.Title` | dev warning | `aria-labelledby` target missing | Add `<Dialog.Title>` (wrap in `<VisuallyHidden>` if visually hidden) |
| `Dialog.Content` without `Dialog.Description` | dev warning | `aria-describedby` target missing | Add `Dialog.Description` or pass `aria-describedby={undefined}` to `Content` |
| `Tooltip.Root` without `Tooltip.Provider` ancestor | dev warning | Tooltip context missing | Wrap app root with `<TooltipProvider>` |
| `asChild` with multiple children | runtime throw | `React.Children.only` violated | Pass exactly one child to any `asChild` part |
| `asChild` with text-only child | runtime throw | Slot can't clone a string | Wrap text in an element |
| `Slot` ref not forwarded | silent failure | Custom child component lacks `forwardRef` | Wrap child in `React.forwardRef` |
| Portal in SSR without client gate | hydration mismatch | `document.body` undefined on server | Mark component `"use client"` (Next App Router) and gate `open` to `false` initially |

**Recovery**: all errors are dev-time. None require try/catch in
production code paths. Fix the call site, not the runtime.

---

## SDK Idioms

### Idiomatic import

```tsx
import * as Dialog from "@radix-ui/react-dialog";
// Use as <Dialog.Root>, <Dialog.Trigger>, etc.
```

OR (the shadcn-generated style):

```tsx
import {
  Root as Dialog,
  Trigger as DialogTrigger,
  Portal as DialogPortal,
  // ...
} from "@radix-ui/react-dialog";
```

shadcn generates the second style with `cn(...)` Tailwind classes
attached via `forwardRef`. Both are valid.

### Always `forwardRef` custom wrappers

```tsx
const StyledContent = React.forwardRef<
  React.ElementRef<typeof Dialog.Content>,
  React.ComponentPropsWithoutRef<typeof Dialog.Content>
>(({ className, children, ...props }, ref) => (
  <Dialog.Portal>
    <Dialog.Overlay className="fixed inset-0 z-50 bg-black/80" />
    <Dialog.Content
      ref={ref}
      className={cn("fixed left-[50%] top-[50%] z-50 ...", className)}
      {...props}
    >
      {children}
    </Dialog.Content>
  </Dialog.Portal>
));
StyledContent.displayName = Dialog.Content.displayName;
```

### Use `data-state` for animations, not `open` state

```tsx
<Dialog.Content
  className="
    data-[state=open]:animate-in
    data-[state=open]:fade-in-0
    data-[state=open]:zoom-in-95
    data-[state=closed]:animate-out
    data-[state=closed]:fade-out-0
    data-[state=closed]:zoom-out-95
  "
>
```

Pair with `tailwindcss-animate` plugin (shadcn ships this).

### Always control state for forms

```tsx
const [open, setOpen] = React.useState(false);
<Dialog.Root open={open} onOpenChange={setOpen}>
```

Uncontrolled (`defaultOpen`) is fine for static demos but breaks
mutation→close flows.

### TooltipProvider at root, once

```tsx
// app/layout.tsx (Next 13+)
<TooltipProvider delayDuration={200} skipDelayDuration={500}>
  {children}
</TooltipProvider>
```

Not per-component. Provider tracks the "skip delay" window globally so
hovering between multiple tooltips doesn't re-trigger the delay.

---

## Anti-Patterns

1. **Wrapping `Trigger` in `<button>`**

   ```tsx
   // WRONG: button-in-button, double click, broken focus
   <button>
     <Dialog.Trigger>Open</Dialog.Trigger>
   </button>
   ```

   ```tsx
   // RIGHT: asChild merges props onto your button
   <Dialog.Trigger asChild>
     <Button>Open</Button>
   </Dialog.Trigger>
   ```

2. **Setting `open` from inside the form's `onSubmit`**

   ```tsx
   // WRONG: race condition with mutation
   onSubmit={() => { setOpen(false); mutate(values); }}
   ```

   ```tsx
   // RIGHT: close on mutation success
   useMutation({ mutationFn, onSuccess: () => setOpen(false) })
   ```

3. **Using fragment under `asChild`**

   ```tsx
   // WRONG: Slot needs exactly one element
   <DropdownMenu.Trigger asChild>
     <>
       <Icon />
       Menu
     </>
   </DropdownMenu.Trigger>
   ```

   ```tsx
   // RIGHT: single element wraps both
   <DropdownMenu.Trigger asChild>
     <Button><Icon />Menu</Button>
   </DropdownMenu.Trigger>
   ```

4. **Forgetting `forceMount` for exit animations**

   ```tsx
   // WRONG: Radix unmounts before animation runs
   <Dialog.Content className="data-[state=closed]:animate-out">
   ```

   ```tsx
   // RIGHT: forceMount + Presence (or Tailwind animate plugin handles it)
   <Dialog.Portal forceMount>
     <Dialog.Content forceMount={open ? true : undefined}>
   ```

   In practice, shadcn's Tailwind animate plugin handles this without
   manual `forceMount` because the exit animation completes before
   Radix unmounts (configured via `tailwindcss-animate`).

5. **`Select.Item value=""`**

   ```tsx
   // WRONG: throws at runtime
   <Select.Item value="">All</Select.Item>
   ```

   ```tsx
   // RIGHT: sentinel value, map back in handler
   <Select.Item value="all">All</Select.Item>
   ```

6. **`onSelect` in `DropdownMenu.CheckboxItem` not preventing default**

   ```tsx
   // WRONG: menu closes on every toggle
   <DropdownMenu.CheckboxItem onCheckedChange={setShow}>
   ```

   ```tsx
   // RIGHT: keep menu open while toggling multiple
   <DropdownMenu.CheckboxItem
     checked={show}
     onCheckedChange={setShow}
     onSelect={(e) => e.preventDefault()}
   >
   ```

7. **Rendering Dialog conditionally on the trigger side**

   ```tsx
   // WRONG: unmount races scroll-lock cleanup
   {showDialog && <Dialog open={true}>...</Dialog>}
   ```

   ```tsx
   // RIGHT: always mount, control via open
   <Dialog open={showDialog} onOpenChange={setShowDialog}>...</Dialog>
   ```

8. **Calling `onOpenChange` asynchronously**

   ```tsx
   // WRONG: pointer-events stuck on body
   onOpenChange={(o) => { setTimeout(() => setOpen(o), 100); }}
   ```

   ```tsx
   // RIGHT: synchronous
   onOpenChange={setOpen}
   ```

---

## Data Model

Radix Primitives has no persistent data model. The "data" model is the
React state of each primitive's `Root`:

| Primitive | State shape |
|---|---|
| Dialog, AlertDialog, Popover, HoverCard, DropdownMenu, ContextMenu, Collapsible | `{ open: boolean }` controlled via `open` / `onOpenChange` |
| Tabs | `{ value: string }` controlled via `value` / `onValueChange` |
| Accordion (single) | `{ value: string }` |
| Accordion (multiple) | `{ value: string[] }` |
| RadioGroup | `{ value: string }` |
| Switch, Toggle, Checkbox | `{ checked: boolean | "indeterminate" }` |
| ToggleGroup (single) | `{ value: string }` |
| ToggleGroup (multiple) | `{ value: string[] }` |
| Slider | `{ value: number[] }` (always array, even single-thumb) |
| Select | `{ value: string, open: boolean }` |
| NavigationMenu | `{ value: string }` |

All state can be uncontrolled (pass `defaultOpen`/`defaultValue`) or
controlled (pass `open`/`value` + `onOpenChange`/`onValueChange`).

ARIA attributes flow through context internally. You don't set
`aria-expanded`, `aria-controls`, `aria-labelledby`, `role`, or
`tabindex` manually — Radix wires them. Setting them yourself
overrides Radix and breaks accessibility.

`data-state`, `data-side`, `data-align`, `data-orientation`,
`data-disabled`, `data-highlighted`, `data-checked` are set on the
DOM elements for styling. Use them as Tailwind selectors:
`data-[state=open]:bg-accent`.

---

## Webhooks

**N/A — Radix Primitives has no webhook surface.** It is a client-side
React library. There are no events to subscribe to from outside the
browser process. Within the browser, Radix exposes React event
callbacks (`onOpenChange`, `onValueChange`, `onSelect`,
`onEscapeKeyDown`, `onPointerDownOutside`, `onInteractOutside`,
`onCloseAutoFocus`, `onOpenAutoFocus`) — these are the equivalent of
"webhooks" for in-process state changes.

If you need to broadcast Radix state to other tabs or services, that's
your application's job (BroadcastChannel, server-sent events, etc.).
Radix has nothing to do with it.

---

## Limits

Radix Primitives has no documented hard limits because there's no
backend. Practical limits:

- **DOM portal targets**: Radix renders to `document.body` by default.
  You can override with `<Portal container={el}>`. Container must be
  in the DOM at render time.
- **Nested overlays**: Radix supports unlimited nesting via
  `DismissableLayer` stack. Practically, more than 3 nested
  Dialog/Popover/DropdownMenu layers becomes confusing UX before it
  becomes a technical problem.
- **Focus scope depth**: `FocusScope` (used internally) supports
  arbitrary nesting. Each modal `Dialog` opens a new trap; closing
  pops back to the previous.
- **Animation duration**: no hard cap, but `tailwindcss-animate`
  defaults are 150–200ms. Longer durations work but feel sluggish.
- **Bundle size**: each primitive is 5–15KB gzipped. Tree-shaking
  works at the primitive level, not the part level. Importing
  `@radix-ui/react-dialog` ships all of Dialog. Mitigation: only
  install primitives you use.
- **`Select` item count**: no hard cap, but virtualization is not
  built in. Over ~500 items, switch to a Combobox (Popover + cmdk +
  virtual) pattern.
- **`Slider` thumb count**: arbitrary; pass `value={[10, 50, 90]}`
  for a 3-thumb slider.

---

## Cost Model

**N/A — Radix UI Primitives is free, open source, MIT licensed.** Zero
runtime cost (no API calls), zero licensing cost, zero usage limits.

The "cost" considerations are:

1. **Bundle size cost** — each primitive adds 5–15KB gzipped to your
   client bundle. Total cost of using the full shadcn surface area is
   ~120–180KB gzipped across all Radix primitives. This is paid once
   and cached.
2. **Maintenance cost** — Radix is maintained by WorkOS (acquired from
   Modulz in 2024). Sustained investment from a profitable company.
   Low risk of abandonment.
3. **Migration cost** — moving away from Radix means rewriting every
   shadcn component. Realistically you don't migrate; you accept it as
   the foundation.

---

## Version Pinning

**Per-primitive semver.** Each `@radix-ui/react-*` package versions
independently. Current major versions (as of 2026-04):

- `@radix-ui/react-dialog`: 1.1.x
- `@radix-ui/react-popover`: 1.1.x
- `@radix-ui/react-dropdown-menu`: 2.1.x
- `@radix-ui/react-select`: 2.1.x
- `@radix-ui/react-tooltip`: 1.1.x
- `@radix-ui/react-alert-dialog`: 1.1.x
- `@radix-ui/react-tabs`: 1.1.x
- `@radix-ui/react-accordion`: 1.2.x
- `@radix-ui/react-navigation-menu`: 1.2.x
- `@radix-ui/react-slot`: 1.1.x
- `@radix-ui/react-portal`: 1.1.x

Major version bumps happen rarely (every 1–2 years per primitive) and
include codemods. Radix's deprecation policy: 1 major version of
warning before removal.

**Pinning strategy for EOS:**
- Use caret ranges (`^1.1.0`) in `package.json` because patch + minor
  are non-breaking by Radix's policy.
- Commit `package-lock.json` so CI installs the same resolved versions.
- After any Radix upgrade, run `npm dedupe` and `npm ls @radix-ui/react-presence`
  to verify no duplicate internals.

**Breaking changes to know:**
- `@radix-ui/react-select@2.0` (2023): added `Portal`, changed
  positioning to Floating UI. Required wrapping `Content` in `Portal`
  manually.
- `@radix-ui/react-dropdown-menu@2.0` (2023): same Portal change.
- `@radix-ui/react-toast`: deprecated in favor of community libraries
  (Sonner). Still maintained but not recommended for new code.

**Upcoming:**
- React 19 ref-as-prop support: Radix is migrating away from
  `forwardRef` internally over 2025–2026. No API change for
  consumers.

---

## Design Intent

Radix UI was built by Jenna Smith, Pedro Duarte, Colm Tuite, Benoît
Grélard, and Andy Hook at Modulz (acquired by WorkOS in 2024). The
design intent traces directly to a single failed assumption that
plagued every prior React UI library: **"styling and accessibility can
be bundled together."** Material UI, Ant Design, Chakra UI, and
Bootstrap-React all coupled the two. The cost: every team that wanted
custom branding either fought the library's CSS or rewrote
accessibility from scratch.

**Radix's bet:** decouple completely. Ship the hard part
(accessibility, focus, keyboard, ARIA, positioning, portal layering,
focus trap, scroll lock) as headless primitives. Let the styling layer
be whatever the team wants.

**The mental model the founders optimized for: "a Radix primitive is a
WAI-ARIA pattern made executable."** Not a "component" in the visual
sense. The Dialog primitive IS the WAI-ARIA dialog pattern in code.
You can't get the ARIA wrong because you're not writing it.

**Tradeoffs consciously made:**

1. **Composition over configuration.** No `<Dialog title="x" body="y">`
   single-prop API. Every part is a separate component you assemble.
   Cost: more imports, more JSX. Benefit: arbitrary content shapes,
   no escape-hatches needed.
2. **`asChild` over `as` prop.** Both achieve polymorphism. `asChild`
   wins because it composes better with custom components that already
   `forwardRef` (your shadcn `Button` works without modification).
   Cost: requires understanding `Slot`. Benefit: zero-config polymorphism.
3. **Per-primitive packages.** Costs more npm metadata. Benefits:
   tree-shaking at primitive granularity, independent versioning,
   smaller bundles for apps using few primitives.
4. **Unstyled.** Costs every team some upfront styling work. Benefits:
   zero CSS conflicts, no design system lock-in, works with any
   styling solution (Tailwind, vanilla CSS, CSS Modules, Emotion,
   styled-components, Panda, vanilla-extract).
5. **Floating UI under the hood.** Cost: extra dependency. Benefit:
   battle-tested positioning that handles every edge case (collision,
   flip, shift, hide, arrow positioning).

**What Radix is explicitly NOT:**
- Not a design system. (Radix Themes is a separate styled layer.)
- Not a component library in the traditional sense (no Card, no
  Button — those are styling decisions).
- Not opinionated about state management, routing, or data fetching.
- Not a form library (use React Hook Form on top).

**Prior art that influenced Radix:**
- Reach UI (the spiritual predecessor; same headless idea, less
  comprehensive, no longer maintained).
- Headless UI (Tailwind Labs; similar philosophy but more limited
  primitive set).
- WAI-ARIA Authoring Practices Guide (the spec Radix implements).
- React Aria (Adobe; the closest competitor; different tradeoff:
  React Aria is hooks-based, Radix is component-based).

---

## Problem-Solution Map

### Problem: "Our Dialog has bad accessibility."
**Solution:** Replace your custom modal with `@radix-ui/react-dialog`.
You inherit focus trap, ESC to close, click-outside, scroll lock,
inert background, ARIA roles and labels, focus restoration on close.
Zero code from you for any of it.

### Problem: "Our DropdownMenu loses keyboard nav."
**Solution:** `@radix-ui/react-dropdown-menu` ships full WAI-ARIA
menu pattern: roving tabindex, ↑/↓/Home/End nav, typeahead, →/← for
submenus, Escape to close at any depth.

### Problem: "Tooltip positioning breaks near viewport edges."
**Solution:** Radix Tooltip uses Floating UI's `flip` and `shift`
middleware automatically. `avoidCollisions={true}` is the default.
Set `collisionPadding` to add breathing room.

### Problem: "Custom Select has terrible mobile support."
**Solution:** `@radix-ui/react-select` falls back to native semantics
(announces as combobox to screen readers, supports typeahead, full
keyboard). For pure native mobile, swap to `<select>` at small
viewports — Radix Select is for desktop control.

### Problem: "We need a Combobox (autocomplete + keyboard nav)."
**Solution:** Radix doesn't ship a Combobox primitive directly. The
canonical pattern is `@radix-ui/react-popover` + `cmdk` (the command
menu library by Paco Coursey, designed to compose with Radix).
shadcn's Command component IS this composition.

### Hidden capability: nested DropdownMenu with `Sub`

```tsx
<DropdownMenu.Sub>
  <DropdownMenu.SubTrigger>More</DropdownMenu.SubTrigger>
  <DropdownMenu.Portal>
    <DropdownMenu.SubContent>
      <DropdownMenu.Item>Sub item 1</DropdownMenu.Item>
    </DropdownMenu.SubContent>
  </DropdownMenu.Portal>
</DropdownMenu.Sub>
```

Most users don't realize Radix supports infinite menu nesting with
proper keyboard nav (→ to enter, ← to exit) and pointer hover delays.

### Hidden capability: `collisionBoundary` for in-modal popovers

When opening a Popover inside a Dialog, set `collisionBoundary` to the
Dialog Content element so the Popover flips against the Dialog edges,
not the viewport.

### Hidden capability: `forceMount` for SEO content

Render Tabs content with `forceMount` so all panels are in the DOM
even when not active. Hide inactive panels with CSS. SEO crawlers see
everything, users still get tab UX.

---

## Operational Behavior

**Focus management is the operational core.** Every modal primitive
(Dialog, AlertDialog, Popover, DropdownMenu, Select, ContextMenu)
opens a `FocusScope`. On open:
1. Trap focus inside Content (Tab cycles within, Shift+Tab cycles
   reverse).
2. Auto-focus the first focusable element (or the element configured
   via `onOpenAutoFocus`).
3. On close, restore focus to the trigger (or the element configured
   via `onCloseAutoFocus`).

**Edge cases:**
- If the trigger is unmounted while the dialog is open (route change),
  focus restores to `document.body`. Set `onCloseAutoFocus={(e) => e.preventDefault()}`
  and manually focus a target if you need different behavior.
- `inert` attribute is applied to siblings of the open content for
  modal mode, blocking screen reader access to background. Browsers
  without `inert` (older Safari) fall back to `aria-hidden`.

**Scroll lock** uses `body { overflow: hidden; padding-right: <scrollbar-width>px }`
to prevent layout shift. Multiple stacked dialogs reference-count the
lock so closing the inner dialog doesn't unlock until all close.

**Pointer events** on the body get `pointer-events: none` while
`Dialog.Overlay` is open, then released on close. The notorious
"stuck pointer events" bug happens when:
- React unmounts mid-close (cleanup doesn't run).
- A toast/portal mounts during close and re-applies the lock without
  release.
- An `onOpenChange` handler is async/debounced and Radix's cleanup
  races the next render.

**Eventual consistency:** none. Radix is fully synchronous React
state. State changes commit immediately on `onOpenChange`.

**Hydration:** any primitive that uses `Portal` cannot render the
portaled content during SSR (no `document.body`). The trigger renders
fine. The portaled content mounts after hydration. In Next.js App
Router, mark dialog-containing components `"use client"`.

**Strict Mode:** Radix is fully compatible with React 18 StrictMode
double-mount. Internal effects clean up correctly on the throwaway
mount.

**Concurrent rendering:** safe. Radix uses `useSyncExternalStore` for
internal state where needed (focus stack, layer stack).

---

## Ecosystem Position

**Radix sits at the "headless primitives" layer** in a React UI stack:

```
[ Application code: features/leads/lead-dialog.tsx ]
            ↓
[ Styled wrappers: shadcn/ui (components/ui/dialog.tsx) ]
            ↓
[ Headless primitives: @radix-ui/react-dialog ]      ← Radix lives here
            ↓
[ Browser DOM + ARIA + native focus management ]
```

**Natural complements:**
- **shadcn/ui** — the canonical styled wrapper. Generated, copy-pasted
  into your repo, Tailwind-based. Designed by Shadcn (Hassan El Mghari)
  specifically around Radix.
- **Tailwind CSS + tailwindcss-animate** — styling and animation.
- **Floating UI** — under the hood for positioning. Don't import
  directly unless building custom positioning logic.
- **cmdk** — for command palette / combobox patterns. Composes with
  Radix Popover.
- **Sonner** — for toasts. Replaces `@radix-ui/react-toast` in
  practice.
- **React Hook Form + Zod** — forms inside dialogs.
- **TanStack Query** — mutations triggered from dialogs.
- **React Aria** — Adobe's competitor; do NOT mix with Radix on the
  same component (different focus management strategies).

**Forced integrations to avoid:**
- Radix + Material UI: both ship focus management; they fight.
- Radix + Bootstrap modals: same conflict.
- Radix + jQuery-based libraries: jQuery directly mutates DOM,
  bypassing React, breaking Radix's state assumptions.
- Two versions of the same Radix primitive (e.g., Dialog 1.0 and 1.1
  in one bundle): React context collisions.

**Where Radix fits in the EOS architecture:**

```
saas/{app}/src/
  components/ui/         ← shadcn wrappers (edit rarely)
    dialog.tsx           ← imports @radix-ui/react-dialog
    popover.tsx
    dropdown-menu.tsx
    ...
  components/data-table/ ← TanStack Table + shadcn
  features/{feature}/    ← compose ui/* with RHF + Query
    *-dialog.tsx         ← business dialogs
    *-menu.tsx           ← business menus
```

You almost never import `@radix-ui/react-*` directly in feature code.
You import from `@/components/ui/*` and Radix is the engine
underneath. The exceptions: `@radix-ui/react-slot` when defining a new
polymorphic primitive, and `@radix-ui/react-visually-hidden` when
adding a screen-reader-only label to a custom component.

---

## Trajectory

**Where Radix is heading (2026):**

1. **WorkOS stewardship.** Modulz was acquired by WorkOS in late 2024.
   Radix is now under WorkOS's open source umbrella alongside the
   WorkOS Auth components. WorkOS funds full-time maintenance,
   removing the "what if Modulz pivots" risk that hung over Radix in
   2022–2023.

2. **React 19 + ref-as-prop migration.** Radix internals are migrating
   off `forwardRef` toward React 19's ref-as-prop pattern. No consumer
   API changes; this is purely internal cleanup. Watch for v2 majors
   on individual primitives once React 19 is the floor.

3. **Radix Themes 4.x.** A separate styled layer (Radix Themes) is
   evolving on a faster cadence than Primitives. Themes is the
   "batteries included" alternative for teams that don't want to use
   Tailwind/shadcn. Most EOS-style apps prefer Primitives + shadcn.

4. **No deprecations on core primitives.** Dialog, Popover,
   DropdownMenu, Select, Tooltip, AlertDialog, Tabs, Accordion are
   stable foundations and won't move.

5. **`@radix-ui/react-toast` is in maintenance mode.** Community has
   converged on Sonner. Toast still works but Radix isn't investing.

6. **Increased investment in compound primitives.** Radix is exploring
   higher-level compositions like Combobox and DatePicker as official
   primitives (currently community-built). Watch their GitHub
   discussions.

7. **Server Components compatibility.** Most primitives are client
   components (need state, refs, effects). Some pure presentational
   parts (Separator, AspectRatio, VisuallyHidden) work as server
   components. Expect more "use client" boundaries to be tightened.

**Dead-end signals to avoid:**
- Don't build new code on `@radix-ui/react-toast` — use Sonner.
- Don't build new code on the older `as` prop pattern — use `asChild`.
- Don't depend on internal `@radix-ui/react-primitive` directly — it's
  a private package that may break.

---

## Conceptual Model

**Mental model: every Radix primitive is a state machine + ARIA
contract + focus contract, exposed as a tree of React components.**

The four atoms of any Radix primitive:

1. **State.** Open/closed, value, checked, expanded. Owned by `Root`,
   shared via context.
2. **ARIA.** Roles, labels, descriptions, expanded states.
   Auto-applied via context.
3. **Focus.** Trap, restore, roving tabindex. Auto-managed.
4. **Keyboard.** Per-pattern keymap (Escape, arrows, Tab,
   Home/End, typeahead). Auto-bound.

Your job as the consumer: arrange the parts in JSX, control state if
needed, style with `data-*` attribute selectors.

### Recipe 1: A confirm-then-mutate destructive action

```tsx
function DeleteCampaignButton({ id }: { id: string }) {
  const [open, setOpen] = React.useState(false);
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => fetch(`/api/campaigns/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      setOpen(false);
      toast.success("Campaign deleted");
    },
  });

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <Button variant="destructive">Delete</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this campaign?</AlertDialogTitle>
          <AlertDialogDescription>
            All leads attached will be unlinked. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              mutation.mutate();
            }}
          >
            {mutation.isPending ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

Note: `e.preventDefault()` stops `AlertDialogAction` from auto-closing
the dialog before the mutation finishes. The `onSuccess` handler does
the close.

### Recipe 2: A multi-select filter DropdownMenu (menu stays open)

```tsx
function StatusFilter({
  selected,
  onChange,
}: {
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}) {
  const statuses = ["new", "contacted", "qualified", "won", "lost"];
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline">
          Status ({selected.size})
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuLabel>Filter by status</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {statuses.map((s) => (
          <DropdownMenuCheckboxItem
            key={s}
            checked={selected.has(s)}
            onCheckedChange={(checked) => {
              const next = new Set(selected);
              checked ? next.add(s) : next.delete(s);
              onChange(next);
            }}
            onSelect={(e) => e.preventDefault()}
          >
            {s}
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

### Recipe 3: A polymorphic Button using Slot

```tsx
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva("inline-flex items-center ...", {
  variants: {
    variant: { default: "...", destructive: "...", outline: "..." },
    size: { sm: "...", md: "...", lg: "..." },
  },
  defaultVariants: { variant: "default", size: "md" },
});

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={buttonVariants({ variant, size, className })}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";
```

This is the foundation of every styled element in shadcn — Radix's
`Slot` is the polymorphism engine.

### Recipe 4: A Tooltip on an icon button

```tsx
<TooltipProvider delayDuration={300}>
  <Tooltip>
    <TooltipTrigger asChild>
      <Button size="icon" variant="ghost">
        <Trash className="h-4 w-4" />
      </Button>
    </TooltipTrigger>
    <TooltipContent side="top">
      Delete this lead
    </TooltipContent>
  </Tooltip>
</TooltipProvider>
```

### Recipe 5: Tabs synced to URL

```tsx
function VenturesTabs() {
  const [tab, setTab] = useQueryState("tab", { defaultValue: "all" });
  return (
    <Tabs value={tab} onValueChange={setTab}>
      <TabsList>
        <TabsTrigger value="all">All</TabsTrigger>
        <TabsTrigger value="active">Active</TabsTrigger>
        <TabsTrigger value="archived">Archived</TabsTrigger>
      </TabsList>
      <TabsContent value="all"><AllVentures /></TabsContent>
      <TabsContent value="active"><ActiveVentures /></TabsContent>
      <TabsContent value="archived"><ArchivedVentures /></TabsContent>
    </Tabs>
  );
}
```

---

## Industry Expert

**How top practitioners use Radix in 2026:**

1. **shadcn/ui as the universal frontend baseline.** Vercel,
   Supabase, Cal.com, Resend, Linear-clones, and the entire
   "next-gen SaaS" cohort have standardized on shadcn — which means
   they've standardized on Radix as the engine. This is the single
   biggest lock-in trend in React UI in years.

2. **Pedro Duarte's `Slot` pattern as a universal polymorphism
   primitive.** Industry experts (Lee Robinson at Vercel, Matt
   Pocock for TypeScript) recommend `Slot` over the older `as` prop
   for any new component library. The pattern has spread beyond Radix
   into community libraries.

3. **Floating UI + Radix Popover for advanced positioning.** Power
   users access the underlying Floating UI middleware via Radix's
   prop pass-through (`collisionBoundary`, `collisionPadding`,
   `sticky`, `hideWhenDetached`) to build "always visible" toolbars,
   sticky headers in Popover content, and viewport-aware menus.

4. **Combining Radix + cmdk for command palettes.** The "press ⌘K"
   pattern that Linear, Vercel Dashboard, GitHub, and Cursor all use
   is built on Radix Dialog + cmdk + Radix Popover. Paco Coursey
   designed cmdk specifically to compose with Radix.

5. **Radix Toast → Sonner migration is universal.** Every team that
   started on Radix Toast in 2022–2023 has migrated to Sonner.
   shadcn's official toast component is now Sonner-based.

6. **Animation via tailwindcss-animate.** The standard is to drive
   enter/exit animations via Tailwind utility classes
   (`data-[state=open]:animate-in`) instead of Framer Motion or
   React Spring inside Radix. Lower bundle, simpler mental model.

7. **AI-powered form generation into Radix Dialog shells.** Frontier
   pattern: code-gen agents (v0, bolt.new, lovable.dev) emit shadcn-
   wrapped Radix Dialog + RHF + Zod skeletons from natural-language
   prompts. The Radix part is the "frame," the AI fills the form.

8. **Server-Component-friendly slot composition.** Next.js 14+ App
   Router teams pass server-rendered children into client-side Radix
   wrappers via `children` prop, keeping the dialog body as a server
   component. Radix's `Slot` handles ref forwarding so this works
   even with mixed server/client trees.

9. **Headless UI accessibility audits using Radix as the gold
   standard.** Auditors at Deque (axe-core) and accessibility consul-
   tants increasingly recommend "if you're not on Radix, justify it"
   for new React projects. Radix's WAI-ARIA fidelity is the bar.

10. **Custom design systems built ON Radix, not replacing it.**
    Companies like Vercel (Geist Design System), Supabase, and
    Stripe's React component library all use Radix as the
    accessibility engine and add their own visual layer. The pattern
    is: "your design tokens + Radix's behavior = your component
    library."

**Frontier pattern most users miss:**

`asChild` chains. You can chain `asChild` through multiple layers:

```tsx
<DropdownMenu.Trigger asChild>
  <Tooltip.Trigger asChild>
    <Button>Menu</Button>
  </Tooltip.Trigger>
</DropdownMenu.Trigger>
```

This makes the same `<Button>` element BOTH a DropdownMenu trigger AND
a Tooltip trigger, with all ARIA attributes merged correctly. Three
behaviors, one DOM element. Most teams render two wrappers and ship
broken focus.
