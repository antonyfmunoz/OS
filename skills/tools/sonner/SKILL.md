<<<<<<< Updated upstream
---
name: sonner
description: "Use when adding, debugging, or composing toast notifications via the `sonner` library — including success/error/info/warning/loading toasts, `toast.promise` async flows, React Query mutation feedback, optimistic UI rollbacks, stable-id dedupe and updates, swipe-to-dismiss tuning, `<Toaster />` placement and configuration in a shadcn/ui app, theme/richColors/expand/closeButton wiring, or fixing common footguns like duplicate `<Toaster />` mounts, race conditions on unmount, or toast spam."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
trigger: both
effort: high
context: fork
last_researched: "2026-04-06"
last_updated: "2026-04-06"
api_version: "2.x"
sdk_version: "sonner@2.0.7"
source_url: "https://sonner.emilkowal.ski/"
speed_category: "stable"
sources:
  - "https://sonner.emilkowal.ski/"
  - "https://sonner.emilkowal.ski/getting-started"
  - "https://sonner.emilkowal.ski/toast"
  - "https://sonner.emilkowal.ski/toaster"
  - "https://github.com/emilkowalski/sonner"
  - "https://emilkowal.ski/ui/building-a-toast-component"
  - "https://ui.shadcn.com/docs/components/sonner"
---

# Tool: Sonner — Emil Kowalski's React Toast

Sonner is **the toast layer for every shadcn/ui app in `/opt/OS/saas`.**
30M+ weekly downloads. Used by Vercel, Cursor, X. Two-line setup, zero
hooks, zero context providers, beautiful defaults, momentum-based
swipe-to-dismiss, and a `toast.promise` API that turns async flows
into single-line feedback loops. shadcn/ui replaced its own built-in
toast with Sonner in 2024 — that's the canonical signal.

## What This Tool Does

Sonner is a React-only toast library built on a **global observer
pattern**. State lives outside React tree, so:

1. You mount `<Toaster />` once at app root.
2. You call `toast(...)` from anywhere — server actions, mutation
   callbacks, error boundaries, route loaders, anywhere.
3. Toasts persist across route changes because they're not bound to
   any component's lifecycle.

The API surface is tight: `toast`, `toast.success`, `toast.error`,
`toast.info`, `toast.warning`, `toast.loading`, `toast.message`,
`toast.promise`, `toast.custom`, `toast.dismiss`. Each call returns
a stable `id` you can use to update or dismiss the same toast later
— this is how you turn a `loading` into `success` without showing
two toasts.

## EOS Integration

**Where Sonner lives in EOS:**

- `/opt/OS/saas/*/src/components/ui/sonner.tsx` — shadcn-generated
  wrapper. Re-exports `<Toaster />` with theme bound to `next-themes`
  (or our theme provider) and the EOS class tokens applied via
  `toastOptions.classNames`.
- `/opt/OS/saas/*/src/main.tsx` (or `app/layout.tsx` for Next) —
  exactly one `<Toaster />` mount, at the root, outside any provider
  that could remount on navigation.
- `/opt/OS/saas/*/src/lib/query-client.ts` — `QueryClient` is
  configured with a `MutationCache` whose global `onError` calls
  `toast.error` so every mutation in the app gets a default failure
  toast without per-call boilerplate.
- `/opt/OS/saas/*/src/features/**/*.tsx` — feature mutations call
  `toast.promise(mutation.mutateAsync(...), {loading, success, error})`
  for the canonical async pattern.

**Stack partners:**

- **shadcn/ui** — installs Sonner via `npx shadcn@latest add sonner`.
  The generated `ui/sonner.tsx` is the only file you should edit
  for theme wiring.
- **Tailwind** — style via `toastOptions.classNames` (per-part class
  override) or the `unstyled` flag for full control.
- **TanStack Query** — Sonner is the feedback layer for every
  `useMutation`. Per-mutation `onError`/`onSuccess` toasts override
  the global `MutationCache` defaults.
- **React Hook Form + Zod** — submit handler awaits the mutation,
  Sonner handles the loading→success/error transition via
  `toast.promise`.
- **Radix UI** — Sonner replaces `@radix-ui/react-toast` (now in
  maintenance). Sonner's swipe gesture and stacking are why shadcn
  switched.
- **next-themes / theme provider** — `<Toaster theme={theme} />`
  reactively switches between `light`, `dark`, and `system`.

## Authentication

**N/A — Sonner is a pure client-side React library.** Zero network
surface, no API keys, no tokens, no scopes, no rate limits, no
webhooks, nothing to authenticate. The package ships ESM/CJS to
`node_modules`, runs entirely in the browser, never phones home.

The "auth-like" concerns that DO matter:

- **Version pinning.** Sonner is on a fast 2.x cadence. Pin exactly
  in `package.json` (`"sonner": "2.0.7"`) and bump intentionally.
  Minor releases occasionally tweak default classnames, breaking
  custom Tailwind overrides.
- **Peer React.** Sonner 2.x supports React 18 and 19. Our SaaS is
  React 18 strict mode — works.
- **Single mount discipline.** Only ONE `<Toaster />` per app.
  Multiple mounts is the #1 footgun (see Gotchas).

## Quick Reference

### Root setup (shadcn/ui pattern)

```tsx
// src/components/ui/sonner.tsx
"use client";

import { useTheme } from "next-themes";
import { Toaster as SonnerToaster, type ToasterProps } from "sonner";

export function Toaster({ ...props }: ToasterProps) {
  const { theme = "system" } = useTheme();
  return (
    <SonnerToaster
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      richColors
      closeButton
      position="bottom-right"
      expand={false}
      visibleToasts={4}
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  );
}
```

```tsx
// src/main.tsx or app/layout.tsx — mount ONCE at the root
import { Toaster } from "@/components/ui/sonner";

<>
  <App />
  <Toaster />
</>
```

### The five canonical patterns

```tsx
import { toast } from "sonner";

// 1. Fire-and-forget feedback
toast.success("Lead created");
toast.error("Failed to save", { description: err.message });

// 2. The promise pattern — the right way for any async op
toast.promise(api.createLead(values), {
  loading: "Creating lead...",
  success: (lead) => `Created ${lead.name}`,
  error: (err) => `Failed: ${err.message}`,
});

// 3. Stable id for manual update (long-running work)
const id = toast.loading("Uploading file...");
await uploadFile(file, {
  onProgress: (pct) => toast.loading(`Uploading ${pct}%`, { id }),
});
toast.success("Upload complete", { id });

// 4. Action button (undo pattern)
toast("Lead archived", {
  action: { label: "Undo", onClick: () => unarchive(lead.id) },
  duration: 8000,
});

// 5. Dedupe — same id never stacks
toast.error("Network offline", { id: "net-status" });
// Calling again with id "net-status" REPLACES instead of stacking.
```

### React Query global error toast

```tsx
// src/lib/query-client.ts
import { QueryClient, MutationCache, QueryCache } from "@tanstack/react-query";
import { toast } from "sonner";

export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000 } },
  queryCache: new QueryCache({
    onError: (err) => toast.error("Request failed", { description: err.message }),
  }),
  mutationCache: new MutationCache({
    onError: (err) => toast.error("Action failed", { description: err.message }),
  }),
});
```

## Gotchas

- **Mount `<Toaster />` exactly once at the root.** Mounting it
  inside a provider that remounts on route change kills queued
  toasts mid-fade. Mounting it twice causes every toast to render
  in both, looking like a duplicate bug. Put it at the absolute
  root, outside `<BrowserRouter>` is fine but inside is preferred
  so it's still under your `ThemeProvider`.

- **`toast.loading` with no id leaks.** If you `toast.loading("...")`
  and then `toast.success("done")` without a shared `id`, the loading
  toast hangs until its 4-second timeout while the success toast
  sits next to it. Always capture `const id = toast.loading(...)`
  and pass `{ id }` to the resolution toast — OR just use
  `toast.promise` which does this for you.

- **`toast.promise` resolves on the original promise.** If you
  pass `mutation.mutateAsync()` directly, that's fine. If you pass
  `() => mutation.mutateAsync()` (function form), Sonner does NOT
  call it — it shows the loading state forever. Pass the promise,
  not a thunk.

- **Race condition on unmount.** Calling `toast.success` inside
  an `await` after the component unmounted is FINE (Sonner is
  global) — but capturing the `id` in component state causes a
  React warning. Capture the id in a ref or a local variable.

- **Sonner toasts appear above Radix Dialogs and lose swipe.**
  Known issue (#667). When a Dialog is open, Sonner's pointer
  events get blocked by the Dialog's `DismissableLayer`. Mitigation:
  bump Toaster z-index higher than `z-50` via `style={{ zIndex: 100 }}`,
  or dismiss the dialog before showing the toast.

- **`richColors` overrides your Tailwind theme.** With `richColors`
  on, Sonner injects its own success/error background colors that
  ignore `toastOptions.classNames`. If you want themed colors, leave
  `richColors` off and style via `classNames` with `data-[type=success]`
  selectors.

- **Default duration is 4000ms.** Errors auto-dismiss too — set
  `duration: Infinity` and `closeButton: true` for errors users
  must acknowledge. Or set `important: true` (still auto-closes
  but bypasses pause-on-hide).

- **`toast.promise` swallows the rejection.** If your `error`
  callback runs, the original promise rejection is consumed by
  Sonner. If you need to re-throw or chain, attach `.catch()`
  on the promise BEFORE passing to `toast.promise`.

- **`<Select.Item value="">` from Radix interacts badly with toasts
  inside the same render pass.** Unrelated, but worth noting: don't
  fire a toast from a Radix `onValueChange` synchronously — defer
  with `setTimeout(() => toast(...), 0)` to avoid Radix re-render
  cascades.

- **Server components can import `toast`** but cannot CALL it. Toast
  calls must be inside `"use client"` files or event handlers.
  Importing in a server file is harmless; calling crashes hydration.

- **Hotkey collision.** Default hotkey is `⌥ + T` (Alt+T). If your
  app already binds Alt+T, override via `<Toaster hotkey={["altKey", "KeyN"]} />`
  or set to an unused combo.

- **shadcn install command:** `npx shadcn@latest add sonner` (not
  `shadcn-ui` — the package was renamed in 2024).

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — toast.promise + React Query, optimistic
  rollback, long-running progress, undo pattern, AlertDialog confirm.
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — react, typescript, shadcn_ui, tailwind,
  react_hook_form, zod, tanstack_react_query, radix_ui, next.js.
=======
---
name: sonner
description: "Use when adding, debugging, or composing toast notifications via the `sonner` library — including success/error/info/warning/loading toasts, `toast.promise` async flows, React Query mutation feedback, optimistic UI rollbacks, stable-id dedupe and updates, swipe-to-dismiss tuning, `<Toaster />` placement and configuration in a shadcn/ui app, theme/richColors/expand/closeButton wiring, or fixing common footguns like duplicate `<Toaster />` mounts, race conditions on unmount, or toast spam."
allowed-tools: "Read, Write, Edit, Bash, WebFetch, WebSearch"
version: 1.0
trigger: both
effort: high
context: fork
last_researched: "2026-04-06"
last_updated: "2026-04-06"
api_version: "2.x"
sdk_version: "sonner@2.0.7"
source_url: "https://sonner.emilkowal.ski/"
speed_category: "fast"
sources:
  - "https://sonner.emilkowal.ski/"
  - "https://sonner.emilkowal.ski/getting-started"
  - "https://sonner.emilkowal.ski/toast"
  - "https://sonner.emilkowal.ski/toaster"
  - "https://github.com/emilkowalski/sonner"
  - "https://emilkowal.ski/ui/building-a-toast-component"
  - "https://ui.shadcn.com/docs/components/sonner"
---

# Tool: Sonner — Emil Kowalski's React Toast

Sonner is **the toast layer for every shadcn/ui app in `/opt/OS/saas`.**
30M+ weekly downloads. Used by Vercel, Cursor, X. Two-line setup, zero
hooks, zero context providers, beautiful defaults, momentum-based
swipe-to-dismiss, and a `toast.promise` API that turns async flows
into single-line feedback loops. shadcn/ui replaced its own built-in
toast with Sonner in 2024 — that's the canonical signal.

## What This Tool Does

Sonner is a React-only toast library built on a **global observer
pattern**. State lives outside React tree, so:

1. You mount `<Toaster />` once at app root.
2. You call `toast(...)` from anywhere — server actions, mutation
   callbacks, error boundaries, route loaders, anywhere.
3. Toasts persist across route changes because they're not bound to
   any component's lifecycle.

The API surface is tight: `toast`, `toast.success`, `toast.error`,
`toast.info`, `toast.warning`, `toast.loading`, `toast.message`,
`toast.promise`, `toast.custom`, `toast.dismiss`. Each call returns
a stable `id` you can use to update or dismiss the same toast later
— this is how you turn a `loading` into `success` without showing
two toasts.

## EOS Integration

**Where Sonner lives in EOS:**

- `/opt/OS/saas/*/src/components/ui/sonner.tsx` — shadcn-generated
  wrapper. Re-exports `<Toaster />` with theme bound to `next-themes`
  (or our theme provider) and the EOS class tokens applied via
  `toastOptions.classNames`.
- `/opt/OS/saas/*/src/main.tsx` (or `app/layout.tsx` for Next) —
  exactly one `<Toaster />` mount, at the root, outside any provider
  that could remount on navigation.
- `/opt/OS/saas/*/src/lib/query-client.ts` — `QueryClient` is
  configured with a `MutationCache` whose global `onError` calls
  `toast.error` so every mutation in the app gets a default failure
  toast without per-call boilerplate.
- `/opt/OS/saas/*/src/features/**/*.tsx` — feature mutations call
  `toast.promise(mutation.mutateAsync(...), {loading, success, error})`
  for the canonical async pattern.

**Stack partners:**

- **shadcn/ui** — installs Sonner via `npx shadcn@latest add sonner`.
  The generated `ui/sonner.tsx` is the only file you should edit
  for theme wiring.
- **Tailwind** — style via `toastOptions.classNames` (per-part class
  override) or the `unstyled` flag for full control.
- **TanStack Query** — Sonner is the feedback layer for every
  `useMutation`. Per-mutation `onError`/`onSuccess` toasts override
  the global `MutationCache` defaults.
- **React Hook Form + Zod** — submit handler awaits the mutation,
  Sonner handles the loading→success/error transition via
  `toast.promise`.
- **Radix UI** — Sonner replaces `@radix-ui/react-toast` (now in
  maintenance). Sonner's swipe gesture and stacking are why shadcn
  switched.
- **next-themes / theme provider** — `<Toaster theme={theme} />`
  reactively switches between `light`, `dark`, and `system`.

## Authentication

**N/A — Sonner is a pure client-side React library.** Zero network
surface, no API keys, no tokens, no scopes, no rate limits, no
webhooks, nothing to authenticate. The package ships ESM/CJS to
`node_modules`, runs entirely in the browser, never phones home.

The "auth-like" concerns that DO matter:

- **Version pinning.** Sonner is on a fast 2.x cadence. Pin exactly
  in `package.json` (`"sonner": "2.0.7"`) and bump intentionally.
  Minor releases occasionally tweak default classnames, breaking
  custom Tailwind overrides.
- **Peer React.** Sonner 2.x supports React 18 and 19. Our SaaS is
  React 18 strict mode — works.
- **Single mount discipline.** Only ONE `<Toaster />` per app.
  Multiple mounts is the #1 footgun (see Gotchas).

## Quick Reference

### Root setup (shadcn/ui pattern)

```tsx
// src/components/ui/sonner.tsx
"use client";

import { useTheme } from "next-themes";
import { Toaster as SonnerToaster, type ToasterProps } from "sonner";

export function Toaster({ ...props }: ToasterProps) {
  const { theme = "system" } = useTheme();
  return (
    <SonnerToaster
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      richColors
      closeButton
      position="bottom-right"
      expand={false}
      visibleToasts={4}
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  );
}
```

```tsx
// src/main.tsx or app/layout.tsx — mount ONCE at the root
import { Toaster } from "@/components/ui/sonner";

<>
  <App />
  <Toaster />
</>
```

### The five canonical patterns

```tsx
import { toast } from "sonner";

// 1. Fire-and-forget feedback
toast.success("Lead created");
toast.error("Failed to save", { description: err.message });

// 2. The promise pattern — the right way for any async op
toast.promise(api.createLead(values), {
  loading: "Creating lead...",
  success: (lead) => `Created ${lead.name}`,
  error: (err) => `Failed: ${err.message}`,
});

// 3. Stable id for manual update (long-running work)
const id = toast.loading("Uploading file...");
await uploadFile(file, {
  onProgress: (pct) => toast.loading(`Uploading ${pct}%`, { id }),
});
toast.success("Upload complete", { id });

// 4. Action button (undo pattern)
toast("Lead archived", {
  action: { label: "Undo", onClick: () => unarchive(lead.id) },
  duration: 8000,
});

// 5. Dedupe — same id never stacks
toast.error("Network offline", { id: "net-status" });
// Calling again with id "net-status" REPLACES instead of stacking.
```

### React Query global error toast

```tsx
// src/lib/query-client.ts
import { QueryClient, MutationCache, QueryCache } from "@tanstack/react-query";
import { toast } from "sonner";

export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000 } },
  queryCache: new QueryCache({
    onError: (err) => toast.error("Request failed", { description: err.message }),
  }),
  mutationCache: new MutationCache({
    onError: (err) => toast.error("Action failed", { description: err.message }),
  }),
});
```

## Gotchas

- **Mount `<Toaster />` exactly once at the root.** Mounting it
  inside a provider that remounts on route change kills queued
  toasts mid-fade. Mounting it twice causes every toast to render
  in both, looking like a duplicate bug. Put it at the absolute
  root, outside `<BrowserRouter>` is fine but inside is preferred
  so it's still under your `ThemeProvider`.

- **`toast.loading` with no id leaks.** If you `toast.loading("...")`
  and then `toast.success("done")` without a shared `id`, the loading
  toast hangs until its 4-second timeout while the success toast
  sits next to it. Always capture `const id = toast.loading(...)`
  and pass `{ id }` to the resolution toast — OR just use
  `toast.promise` which does this for you.

- **`toast.promise` resolves on the original promise.** If you
  pass `mutation.mutateAsync()` directly, that's fine. If you pass
  `() => mutation.mutateAsync()` (function form), Sonner does NOT
  call it — it shows the loading state forever. Pass the promise,
  not a thunk.

- **Race condition on unmount.** Calling `toast.success` inside
  an `await` after the component unmounted is FINE (Sonner is
  global) — but capturing the `id` in component state causes a
  React warning. Capture the id in a ref or a local variable.

- **Sonner toasts appear above Radix Dialogs and lose swipe.**
  Known issue (#667). When a Dialog is open, Sonner's pointer
  events get blocked by the Dialog's `DismissableLayer`. Mitigation:
  bump Toaster z-index higher than `z-50` via `style={{ zIndex: 100 }}`,
  or dismiss the dialog before showing the toast.

- **`richColors` overrides your Tailwind theme.** With `richColors`
  on, Sonner injects its own success/error background colors that
  ignore `toastOptions.classNames`. If you want themed colors, leave
  `richColors` off and style via `classNames` with `data-[type=success]`
  selectors.

- **Default duration is 4000ms.** Errors auto-dismiss too — set
  `duration: Infinity` and `closeButton: true` for errors users
  must acknowledge. Or set `important: true` (still auto-closes
  but bypasses pause-on-hide).

- **`toast.promise` swallows the rejection.** If your `error`
  callback runs, the original promise rejection is consumed by
  Sonner. If you need to re-throw or chain, attach `.catch()`
  on the promise BEFORE passing to `toast.promise`.

- **`<Select.Item value="">` from Radix interacts badly with toasts
  inside the same render pass.** Unrelated, but worth noting: don't
  fire a toast from a Radix `onValueChange` synchronously — defer
  with `setTimeout(() => toast(...), 0)` to avoid Radix re-render
  cascades.

- **Server components can import `toast`** but cannot CALL it. Toast
  calls must be inside `"use client"` files or event handlers.
  Importing in a server file is harmless; calling crashes hydration.

- **Hotkey collision.** Default hotkey is `⌥ + T` (Alt+T). If your
  app already binds Alt+T, override via `<Toaster hotkey={["altKey", "KeyN"]} />`
  or set to an unused combo.

- **shadcn install command:** `npx shadcn@latest add sonner` (not
  `shadcn-ui` — the package was renamed in 2024).

## References

- `references/best_practices.md` — full 19-section creator-level protocol.
- `references/examples.md` — toast.promise + React Query, optimistic
  rollback, long-running progress, undo pattern, AlertDialog confirm.
- `references/anti_patterns.md` — real failure modes and fixes.
- `references/integrations.md` — react, typescript, shadcn_ui, tailwind,
  react_hook_form, zod, tanstack_react_query, radix_ui, next.js.
>>>>>>> Stashed changes
