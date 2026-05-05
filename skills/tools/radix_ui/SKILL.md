<<<<<<< Updated upstream
---
name: radix_ui
description: "Use when building, debugging, or composing accessible React UI primitives (Dialog, Popover, DropdownMenu, Tooltip, Select, Tabs, Accordion, NavigationMenu, AlertDialog, ContextMenu, HoverCard, ScrollArea, Toggle, RadioGroup, Slider, Switch, Avatar, Collapsible, Separator, AspectRatio, VisuallyHidden) via @radix-ui/react-* packages or any shadcn/ui component (which wraps Radix), or troubleshooting focus traps, FocusScope, Portal layering, scroll-lock not releasing, pointer-events stuck, asChild/Slot ref forwarding, controlled vs uncontrolled state, hydration mismatches, or forceMount with animations."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
trigger: both
effort: high
context: fork
last_researched: "2026-04-06"
last_updated: "2026-04-06"
api_version: "1.x / 2.x (per primitive)"
sdk_version: "@radix-ui/react-* 1.x; @radix-ui/react-dialog@1.1.x"
speed_category: "medium"
source_url: "https://www.radix-ui.com/primitives/docs/overview/introduction"
sources:
  - "https://www.radix-ui.com/primitives/docs/overview/introduction"
  - "https://www.radix-ui.com/primitives/docs/overview/accessibility"
  - "https://www.radix-ui.com/primitives/docs/utilities/slot"
  - "https://www.radix-ui.com/primitives/docs/utilities/portal"
  - "https://www.radix-ui.com/primitives/docs/components/dialog"
  - "https://www.radix-ui.com/primitives/docs/components/popover"
  - "https://www.radix-ui.com/primitives/docs/components/dropdown-menu"
  - "https://www.radix-ui.com/primitives/docs/components/select"
  - "https://www.radix-ui.com/primitives/docs/components/tooltip"
  - "https://www.radix-ui.com/primitives/docs/components/alert-dialog"
  - "https://github.com/radix-ui/primitives"
  - "https://ui.shadcn.com/docs"
---

# Tool: Radix UI Primitives — @radix-ui/react-*

Radix UI Primitives is the **headless, accessible, unstyled component
engine** under every interactive UI element in `/opt/OS/saas`. Every
shadcn/ui component you import — Dialog, Popover, DropdownMenu, Select,
Tooltip, AlertDialog, Tabs, Accordion, NavigationMenu, ContextMenu,
HoverCard, ScrollArea, RadioGroup, Slider, Switch, Toggle, Avatar,
Collapsible, Separator — is a Radix Primitive with Tailwind classes
glued on. Knowing Radix is knowing shadcn from the inside.

This skill exists so EOS stops fighting focus traps, portal z-index
wars, scroll-lock leaks, and `asChild` ref-forwarding mysteries. Radix
solved accessibility once. Use it the way Jenna Smith and Pedro Duarte
designed it.

## What This Tool Does

Radix Primitives is a **suite of low-level React components** that
implement WAI-ARIA design patterns correctly: roles, states,
properties, keyboard interaction, focus management, screen reader
announcements. Each primitive is published as its own package
(`@radix-ui/react-dialog`, `@radix-ui/react-popover`, etc.) so you only
ship the primitives you use.

Three architectural rules define everything:

1. **Unstyled.** Radix ships zero CSS. Every part exposes
   `data-state="open"`, `data-side="top"`, `data-disabled`,
   `data-orientation`, etc. You style with Tailwind, vanilla CSS, or
   any styling solution against those data attributes.

2. **Composable via parts.** Every primitive is a tree of named parts:
   `Dialog.Root`, `Dialog.Trigger`, `Dialog.Portal`, `Dialog.Overlay`,
   `Dialog.Content`, `Dialog.Title`, `Dialog.Description`,
   `Dialog.Close`. You assemble them. Radix wires the ARIA between
   parts via React Context — `Trigger` reads the open state from
   `Root`, `Content` registers itself with `Portal`, `Title` gets an
   id auto-bound to `Content`'s `aria-labelledby`.

3. **Polymorphic via `asChild`.** Every renderable part accepts
   `asChild`. When set, the part does NOT render its own DOM element
   — it clones its single child and merges props (className, refs,
   event handlers, ARIA attributes) onto that child. This is how you
   make a `<Dialog.Trigger asChild><Button>Open</Button></Dialog.Trigger>`
   — the button IS the trigger, no extra wrapper, no ref loss.

## EOS Integration

**Where Radix lives in EOS:**

- `/opt/OS/saas/*/src/components/ui/*.tsx` — shadcn-generated wrappers
  around `@radix-ui/react-*`. `dialog.tsx`, `popover.tsx`,
  `dropdown-menu.tsx`, `select.tsx`, `tooltip.tsx`, `alert-dialog.tsx`,
  `tabs.tsx`, `accordion.tsx`, `navigation-menu.tsx`,
  `context-menu.tsx`, `hover-card.tsx`, `scroll-area.tsx`,
  `radio-group.tsx`, `slider.tsx`, `switch.tsx`, `toggle.tsx`,
  `toggle-group.tsx`, `avatar.tsx`, `collapsible.tsx`, `separator.tsx`,
  `aspect-ratio.tsx`. Each file is ~50 lines: `forwardRef`, attach
  `cn(...)` Tailwind classes, re-export.
- `/opt/OS/saas/*/src/features/**/*-dialog.tsx` — feature dialogs
  (lead detail, campaign edit, confirm-destroy) that compose
  `<Dialog>` + `<Form>` + `<Button>`.
- `/opt/OS/saas/*/src/components/layout/*` — `<DropdownMenu>` for
  user nav, `<Tabs>` for section switchers, `<NavigationMenu>` for
  the top bar.

**Stack partners:**
- **shadcn/ui** — owns the styled wrapper layer. Never edit Radix
  imports inside generated `ui/*.tsx` files unless updating Radix.
- **Tailwind** — styles via `data-[state=open]:`, `data-[side=top]:`,
  `data-[disabled]` selectors. Animation via Tailwind's
  `animate-in`/`animate-out` + `tailwindcss-animate` plugin.
- **React Hook Form + Zod** — every form-bearing Dialog uses
  `useForm({ resolver: zodResolver(schema) })` and closes via
  `onSuccess` of the mutation, not via setting `open` from the form.
- **TanStack Query** — mutations resolve, then `onSuccess` calls
  `setOpen(false)` and `queryClient.invalidateQueries`.
- **sonner** — toasts. We do NOT use `@radix-ui/react-toast`. Sonner
  is the chosen toast layer because it stacks better and integrates
  with shadcn out of the box. Radix Toast is the fallback only if
  WCAG ARIA-live compliance is mandated.

**The rule:** never wrap a Radix `Trigger` in a `<button>`. Use
`asChild` and pass your styled `Button` as the single child. Wrapping
creates `<button><button>` which is invalid HTML, breaks focus
management, and double-fires click handlers.

## Authentication

**N/A — Radix UI Primitives is a pure client-side React library with
zero network surface.** No API keys, no tokens, no service accounts,
no rate limits, no webhooks. The package ships as ESM/CJS to
`node_modules`, runs entirely in the browser, and never phones home.

The "auth-like" concerns that DO matter:

- **Version pinning.** Each primitive ships its own semver. Pin
  Dialog, Popover, DropdownMenu, etc. independently. Mixing major
  versions across primitives is supported because each is isolated,
  but mismatched versions of `@radix-ui/react-presence` (a shared
  internal) across primitives can cause double-mount bugs. Run
  `npm ls @radix-ui/react-presence` after upgrades.
- **Peer React.** Radix 1.x supports React 16.8+, 17, 18. Radix is
  React 19 compatible from late 2024 onward (specific minor varies
  per primitive). Our SaaS is React 18 strict mode — works.
- **No runtime auth.** Anything sensitive in dialog content is your
  app's job, not Radix's. Radix only owns the shell, ARIA wiring,
  focus, and keyboard.

## Quick Reference

### Dialog with controlled state + RHF + Zod

```tsx
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  name: z.string().min(1, "Name required"),
  email: z.string().email(),
});
type FormValues = z.infer<typeof schema>;

export function CreateLeadDialog() {
  const [open, setOpen] = React.useState(false);
  const qc = useQueryClient();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", email: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      fetch("/api/leads", {
        method: "POST",
        body: JSON.stringify(values),
      }).then((r) => r.json()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      setOpen(false);
      form.reset();
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>New lead</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
          <DialogHeader>
            <DialogTitle>Create lead</DialogTitle>
            <DialogDescription>
              Add a new lead to the pipeline.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" {...form.register("name")} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" {...form.register("email")} />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### Destructive AlertDialog

```tsx
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

export function DeleteLead({ onConfirm }: { onConfirm: () => void }) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="destructive">Delete</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this lead?</AlertDialogTitle>
          <AlertDialogDescription>
            This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

## Gotchas

- **`asChild` requires a single React element child that forwards
  refs.** Passing two children, a fragment, or a function component
  that doesn't `forwardRef` will silently break ref attachment, and
  Radix can't measure positioning or trap focus. Use `forwardRef`
  on every custom component you intend to drop under `asChild`.

- **Stuck `pointer-events: none` on `<body>` after closing a Dialog.**
  Caused by a re-render racing with the close animation, or a Toast/
  Sonner that opened during the close. Fix: ensure your `onOpenChange`
  setter runs synchronously and isn't gated behind a state machine.
  If using Sonner inside dialogs, render the `<Toaster>` at the root,
  not inside a portal sibling.

- **Scroll lock not releasing.** If you unmount the Dialog mid-open
  (route change, parent rerender), Radix's scroll-lock cleanup may
  not fire. Always close via `onOpenChange(false)`, then unmount.

- **`forceMount` is required for exit animations.** If you use
  Tailwind `data-[state=closed]:animate-out` you must add `forceMount`
  to `Dialog.Content` (and `Dialog.Overlay`) AND wrap them in
  `<Presence present={open}>` or use the `Dialog.Portal forceMount`
  pattern, otherwise Radix unmounts before the animation runs.

- **Title is mandatory for accessibility.** Every `Dialog.Content`
  must contain a `Dialog.Title`. If you visually don't want one,
  wrap it in `<VisuallyHidden>`. Radix logs a console warning in
  dev when missing — do not suppress it.

- **Hydration mismatch from `Portal`.** `Dialog.Portal` renders to
  `document.body` which doesn't exist on the server. Always render
  Dialogs inside a client component (`"use client"` in Next.js App
  Router) and gate with `open` state that defaults to `false`.

- **Nested overlays + `DismissableLayer`.** Opening a Popover from
  inside a Dialog works, but closing the Popover with Escape will
  also close the Dialog if you don't `e.stopPropagation()` in the
  Popover's `onEscapeKeyDown`. Radix layers stack, but escape
  bubbles through the layer stack by design.

- **`Select` requires non-empty string values.** `<Select.Item value="">`
  throws at runtime — empty string is reserved for "clear selection".
  Use `value="none"` or similar sentinel.

- **`DropdownMenu.Item` with `onSelect` closes the menu by default.**
  If you want the menu to stay open (e.g., a checkbox item that
  toggles), call `e.preventDefault()` inside `onSelect`.

- **Tooltip needs a `TooltipProvider` ancestor.** Forgetting it
  causes silent no-op tooltips. Wrap your app root once with
  `<TooltipProvider delayDuration={200}>`.

- **`asChild` + Next.js `<Link>`.** `<Tooltip.Trigger asChild><Link href="/x">…</Link></Tooltip.Trigger>`
  works only because Next 13+ `Link` forwards refs. Older Next
  versions require an inner `<a>` with `legacyBehavior`.

- **`Slot` collision: two children both define `onClick`.** Radix's
  Slot composes event handlers — both your handler and Radix's
  fire. If you want to STOP Radix from opening (e.g., conditional
  trigger), call `e.preventDefault()` in your handler before Radix's
  default would open the menu.

- **z-index wars.** Radix Portals render to `document.body`. Set a
  z-index on `Dialog.Overlay` (e.g., `z-50`) and `Dialog.Content`
  (`z-50` or higher). Tooltips and Popovers inside dialogs need
  even higher z (`z-[60]`). shadcn ships sane defaults — only
  override when stacking custom overlays.

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — EOS-shaped recipes for every primitive.
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — react, typescript, shadcn_ui, tailwind,
  react_hook_form, zod, sonner, tanstack_react_query.
=======
---
name: radix_ui
description: "Use when building, debugging, or composing accessible React UI primitives (Dialog, Popover, DropdownMenu, Tooltip, Select, Tabs, Accordion, NavigationMenu, AlertDialog, ContextMenu, HoverCard, ScrollArea, Toggle, RadioGroup, Slider, Switch, Avatar, Collapsible, Separator, AspectRatio, VisuallyHidden) via @radix-ui/react-* packages or any shadcn/ui component (which wraps Radix), or troubleshooting focus traps, FocusScope, Portal layering, scroll-lock not releasing, pointer-events stuck, asChild/Slot ref forwarding, controlled vs uncontrolled state, hydration mismatches, or forceMount with animations."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
trigger: both
effort: high
context: fork
last_researched: "2026-04-06"
last_updated: "2026-04-06"
api_version: "1.x / 2.x (per primitive)"
sdk_version: "@radix-ui/react-* 1.x; @radix-ui/react-dialog@1.1.x"
speed_category: "fast"
source_url: "https://www.radix-ui.com/primitives/docs/overview/introduction"
sources:
  - "https://www.radix-ui.com/primitives/docs/overview/introduction"
  - "https://www.radix-ui.com/primitives/docs/overview/accessibility"
  - "https://www.radix-ui.com/primitives/docs/utilities/slot"
  - "https://www.radix-ui.com/primitives/docs/utilities/portal"
  - "https://www.radix-ui.com/primitives/docs/components/dialog"
  - "https://www.radix-ui.com/primitives/docs/components/popover"
  - "https://www.radix-ui.com/primitives/docs/components/dropdown-menu"
  - "https://www.radix-ui.com/primitives/docs/components/select"
  - "https://www.radix-ui.com/primitives/docs/components/tooltip"
  - "https://www.radix-ui.com/primitives/docs/components/alert-dialog"
  - "https://github.com/radix-ui/primitives"
  - "https://ui.shadcn.com/docs"
---

# Tool: Radix UI Primitives — @radix-ui/react-*

Radix UI Primitives is the **headless, accessible, unstyled component
engine** under every interactive UI element in `/opt/OS/saas`. Every
shadcn/ui component you import — Dialog, Popover, DropdownMenu, Select,
Tooltip, AlertDialog, Tabs, Accordion, NavigationMenu, ContextMenu,
HoverCard, ScrollArea, RadioGroup, Slider, Switch, Toggle, Avatar,
Collapsible, Separator — is a Radix Primitive with Tailwind classes
glued on. Knowing Radix is knowing shadcn from the inside.

This skill exists so EOS stops fighting focus traps, portal z-index
wars, scroll-lock leaks, and `asChild` ref-forwarding mysteries. Radix
solved accessibility once. Use it the way Jenna Smith and Pedro Duarte
designed it.

## What This Tool Does

Radix Primitives is a **suite of low-level React components** that
implement WAI-ARIA design patterns correctly: roles, states,
properties, keyboard interaction, focus management, screen reader
announcements. Each primitive is published as its own package
(`@radix-ui/react-dialog`, `@radix-ui/react-popover`, etc.) so you only
ship the primitives you use.

Three architectural rules define everything:

1. **Unstyled.** Radix ships zero CSS. Every part exposes
   `data-state="open"`, `data-side="top"`, `data-disabled`,
   `data-orientation`, etc. You style with Tailwind, vanilla CSS, or
   any styling solution against those data attributes.

2. **Composable via parts.** Every primitive is a tree of named parts:
   `Dialog.Root`, `Dialog.Trigger`, `Dialog.Portal`, `Dialog.Overlay`,
   `Dialog.Content`, `Dialog.Title`, `Dialog.Description`,
   `Dialog.Close`. You assemble them. Radix wires the ARIA between
   parts via React Context — `Trigger` reads the open state from
   `Root`, `Content` registers itself with `Portal`, `Title` gets an
   id auto-bound to `Content`'s `aria-labelledby`.

3. **Polymorphic via `asChild`.** Every renderable part accepts
   `asChild`. When set, the part does NOT render its own DOM element
   — it clones its single child and merges props (className, refs,
   event handlers, ARIA attributes) onto that child. This is how you
   make a `<Dialog.Trigger asChild><Button>Open</Button></Dialog.Trigger>`
   — the button IS the trigger, no extra wrapper, no ref loss.

## EOS Integration

**Where Radix lives in EOS:**

- `/opt/OS/saas/*/src/components/ui/*.tsx` — shadcn-generated wrappers
  around `@radix-ui/react-*`. `dialog.tsx`, `popover.tsx`,
  `dropdown-menu.tsx`, `select.tsx`, `tooltip.tsx`, `alert-dialog.tsx`,
  `tabs.tsx`, `accordion.tsx`, `navigation-menu.tsx`,
  `context-menu.tsx`, `hover-card.tsx`, `scroll-area.tsx`,
  `radio-group.tsx`, `slider.tsx`, `switch.tsx`, `toggle.tsx`,
  `toggle-group.tsx`, `avatar.tsx`, `collapsible.tsx`, `separator.tsx`,
  `aspect-ratio.tsx`. Each file is ~50 lines: `forwardRef`, attach
  `cn(...)` Tailwind classes, re-export.
- `/opt/OS/saas/*/src/features/**/*-dialog.tsx` — feature dialogs
  (lead detail, campaign edit, confirm-destroy) that compose
  `<Dialog>` + `<Form>` + `<Button>`.
- `/opt/OS/saas/*/src/components/layout/*` — `<DropdownMenu>` for
  user nav, `<Tabs>` for section switchers, `<NavigationMenu>` for
  the top bar.

**Stack partners:**
- **shadcn/ui** — owns the styled wrapper layer. Never edit Radix
  imports inside generated `ui/*.tsx` files unless updating Radix.
- **Tailwind** — styles via `data-[state=open]:`, `data-[side=top]:`,
  `data-[disabled]` selectors. Animation via Tailwind's
  `animate-in`/`animate-out` + `tailwindcss-animate` plugin.
- **React Hook Form + Zod** — every form-bearing Dialog uses
  `useForm({ resolver: zodResolver(schema) })` and closes via
  `onSuccess` of the mutation, not via setting `open` from the form.
- **TanStack Query** — mutations resolve, then `onSuccess` calls
  `setOpen(false)` and `queryClient.invalidateQueries`.
- **sonner** — toasts. We do NOT use `@radix-ui/react-toast`. Sonner
  is the chosen toast layer because it stacks better and integrates
  with shadcn out of the box. Radix Toast is the fallback only if
  WCAG ARIA-live compliance is mandated.

**The rule:** never wrap a Radix `Trigger` in a `<button>`. Use
`asChild` and pass your styled `Button` as the single child. Wrapping
creates `<button><button>` which is invalid HTML, breaks focus
management, and double-fires click handlers.

## Authentication

**N/A — Radix UI Primitives is a pure client-side React library with
zero network surface.** No API keys, no tokens, no service accounts,
no rate limits, no webhooks. The package ships as ESM/CJS to
`node_modules`, runs entirely in the browser, and never phones home.

The "auth-like" concerns that DO matter:

- **Version pinning.** Each primitive ships its own semver. Pin
  Dialog, Popover, DropdownMenu, etc. independently. Mixing major
  versions across primitives is supported because each is isolated,
  but mismatched versions of `@radix-ui/react-presence` (a shared
  internal) across primitives can cause double-mount bugs. Run
  `npm ls @radix-ui/react-presence` after upgrades.
- **Peer React.** Radix 1.x supports React 16.8+, 17, 18. Radix is
  React 19 compatible from late 2024 onward (specific minor varies
  per primitive). Our SaaS is React 18 strict mode — works.
- **No runtime auth.** Anything sensitive in dialog content is your
  app's job, not Radix's. Radix only owns the shell, ARIA wiring,
  focus, and keyboard.

## Quick Reference

### Dialog with controlled state + RHF + Zod

```tsx
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  name: z.string().min(1, "Name required"),
  email: z.string().email(),
});
type FormValues = z.infer<typeof schema>;

export function CreateLeadDialog() {
  const [open, setOpen] = React.useState(false);
  const qc = useQueryClient();
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", email: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      fetch("/api/leads", {
        method: "POST",
        body: JSON.stringify(values),
      }).then((r) => r.json()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["leads"] });
      setOpen(false);
      form.reset();
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>New lead</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
          <DialogHeader>
            <DialogTitle>Create lead</DialogTitle>
            <DialogDescription>
              Add a new lead to the pipeline.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" {...form.register("name")} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" {...form.register("email")} />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

### Destructive AlertDialog

```tsx
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

export function DeleteLead({ onConfirm }: { onConfirm: () => void }) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="destructive">Delete</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this lead?</AlertDialogTitle>
          <AlertDialogDescription>
            This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

## Gotchas

- **`asChild` requires a single React element child that forwards
  refs.** Passing two children, a fragment, or a function component
  that doesn't `forwardRef` will silently break ref attachment, and
  Radix can't measure positioning or trap focus. Use `forwardRef`
  on every custom component you intend to drop under `asChild`.

- **Stuck `pointer-events: none` on `<body>` after closing a Dialog.**
  Caused by a re-render racing with the close animation, or a Toast/
  Sonner that opened during the close. Fix: ensure your `onOpenChange`
  setter runs synchronously and isn't gated behind a state machine.
  If using Sonner inside dialogs, render the `<Toaster>` at the root,
  not inside a portal sibling.

- **Scroll lock not releasing.** If you unmount the Dialog mid-open
  (route change, parent rerender), Radix's scroll-lock cleanup may
  not fire. Always close via `onOpenChange(false)`, then unmount.

- **`forceMount` is required for exit animations.** If you use
  Tailwind `data-[state=closed]:animate-out` you must add `forceMount`
  to `Dialog.Content` (and `Dialog.Overlay`) AND wrap them in
  `<Presence present={open}>` or use the `Dialog.Portal forceMount`
  pattern, otherwise Radix unmounts before the animation runs.

- **Title is mandatory for accessibility.** Every `Dialog.Content`
  must contain a `Dialog.Title`. If you visually don't want one,
  wrap it in `<VisuallyHidden>`. Radix logs a console warning in
  dev when missing — do not suppress it.

- **Hydration mismatch from `Portal`.** `Dialog.Portal` renders to
  `document.body` which doesn't exist on the server. Always render
  Dialogs inside a client component (`"use client"` in Next.js App
  Router) and gate with `open` state that defaults to `false`.

- **Nested overlays + `DismissableLayer`.** Opening a Popover from
  inside a Dialog works, but closing the Popover with Escape will
  also close the Dialog if you don't `e.stopPropagation()` in the
  Popover's `onEscapeKeyDown`. Radix layers stack, but escape
  bubbles through the layer stack by design.

- **`Select` requires non-empty string values.** `<Select.Item value="">`
  throws at runtime — empty string is reserved for "clear selection".
  Use `value="none"` or similar sentinel.

- **`DropdownMenu.Item` with `onSelect` closes the menu by default.**
  If you want the menu to stay open (e.g., a checkbox item that
  toggles), call `e.preventDefault()` inside `onSelect`.

- **Tooltip needs a `TooltipProvider` ancestor.** Forgetting it
  causes silent no-op tooltips. Wrap your app root once with
  `<TooltipProvider delayDuration={200}>`.

- **`asChild` + Next.js `<Link>`.** `<Tooltip.Trigger asChild><Link href="/x">…</Link></Tooltip.Trigger>`
  works only because Next 13+ `Link` forwards refs. Older Next
  versions require an inner `<a>` with `legacyBehavior`.

- **`Slot` collision: two children both define `onClick`.** Radix's
  Slot composes event handlers — both your handler and Radix's
  fire. If you want to STOP Radix from opening (e.g., conditional
  trigger), call `e.preventDefault()` in your handler before Radix's
  default would open the menu.

- **z-index wars.** Radix Portals render to `document.body`. Set a
  z-index on `Dialog.Overlay` (e.g., `z-50`) and `Dialog.Content`
  (`z-50` or higher). Tooltips and Popovers inside dialogs need
  even higher z (`z-[60]`). shadcn ships sane defaults — only
  override when stacking custom overlays.

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — EOS-shaped recipes for every primitive.
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — react, typescript, shadcn_ui, tailwind,
  react_hook_form, zod, sonner, tanstack_react_query.
>>>>>>> Stashed changes
