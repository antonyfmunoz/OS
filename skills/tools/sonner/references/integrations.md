# Sonner — Integration Map

## react

Sonner is React-only (web). Supports React 18 and 19. The `<Toaster />`
component is a normal React component but its state lives in a global
observer outside React, which is why `toast()` works from anywhere
including non-React code (fetch interceptors, error boundaries,
event listeners).

## typescript

Types ship with the package — no `@types/sonner` needed. The key
exported types are `ToasterProps`, `ToastT`, `ExternalToast`,
`Action`, `Position`. Import for prop typing your wrapper:

```ts
import type { ToasterProps } from "sonner";
```

## shadcn_ui

Canonical install:
```bash
npx shadcn@latest add sonner
```

This generates `src/components/ui/sonner.tsx` — a thin wrapper that
binds `theme` to `next-themes` (or your theme provider) and applies
the EOS class tokens via `toastOptions.classNames`. Never edit the
import path; always import the wrapper, not `sonner` directly, in
feature code:

```tsx
import { Toaster } from "@/components/ui/sonner"; // mount
import { toast } from "sonner";                    // fire
```

Sonner replaced shadcn's previous Radix-based toast in 2024. The
`use-toast` hook is gone in current shadcn — use `toast()` directly.

## tailwind

Style toasts via:

1. **`toastOptions.classNames`** — per-part class override on the
   `<Toaster />`. Most common.
2. **`unstyled: true`** — strips Sonner's default classes for
   full control.
3. **Data attribute selectors:** Sonner toasts expose
   `data-type="success|error|info|warning"`, `data-styled`,
   `data-mounted`, `data-removed`, `data-front`. Style with
   `[&[data-type=success]]:bg-green-50` etc.
4. **`tailwindcss-animate`** plugin for the entrance/exit animations
   if you swap out Sonner's defaults.

## react_hook_form

Sonner is the feedback layer for RHF submissions. The pattern:

```tsx
const onSubmit = form.handleSubmit((values) => {
  toast.promise(mutation.mutateAsync(values), {
    loading: "Saving...",
    success: "Saved",
    error: (err: Error) => err.message,
  });
});
```

Don't put toasts inside `form.formState.errors` rendering — use
inline field errors for validation, toasts for submission outcome.

## zod

Zod errors should render as inline form errors via RHF's
`zodResolver`, NOT as toasts. Reserve toasts for SUBMISSION
outcomes (after Zod has passed). The exception: catastrophic
parse failures of API responses — toast those because there's
no field to render them under.

```tsx
const parsed = ResponseSchema.safeParse(data);
if (!parsed.success) {
  toast.error("Server returned invalid data", {
    description: parsed.error.issues[0]?.message,
  });
  return;
}
```

## tanstack_react_query

The central integration. Two layers:

1. **Global** — `MutationCache.onError` and `QueryCache.onError`
   on the `QueryClient` give every mutation/query a default
   failure toast without per-call boilerplate.

2. **Per-mutation** — wrap `mutation.mutateAsync()` in
   `toast.promise(...)` for the loading→success/error cycle.
   Per-call always wins; the global is for caught-it-anyway safety.

```tsx
new QueryClient({
  mutationCache: new MutationCache({
    onError: (err) =>
      toast.error("Action failed", { description: String(err) }),
  }),
});
```

This pairing is the single most valuable integration in the stack.
It eliminates 90% of "did it work?" UI questions.

## radix_ui

Sonner **replaces** `@radix-ui/react-toast`. Don't run both. Sonner
beats Radix Toast on:
- API ergonomics (no provider, no hooks)
- Animation defaults
- Swipe-to-dismiss
- Stacking visualization

Radix Toast wins on:
- Strict WAI-ARIA aria-live region compliance
- Headless flexibility for fully custom layouts

For EOS, Sonner is the choice. Radix Toast only if a compliance
audit demands it.

**Layering with Radix Dialog:** Sonner's z-index can sit below
Radix Dialog overlays in some configurations. If toasts get hidden
behind dialogs, bump Toaster z-index via `style={{ zIndex: 100 }}`.

## next.js

- **App Router:** `<Toaster />` MUST be inside a `"use client"`
  boundary. Place it in `app/layout.tsx` inside a client wrapper
  (e.g., `<Providers>`) so it mounts once for the whole app.
- **Server Actions:** call `toast(...)` from the CLIENT after the
  action returns. You cannot call `toast` inside a server action
  itself — it runs on the server, Sonner is browser-only.
- **Server components:** can `import { toast }` (harmless) but
  cannot CALL it. Calls live in client components and event handlers.
- **Hydration:** never render `<Toaster />` conditionally based on
  client-only state without a `mounted` guard, or you'll hydration-mismatch.

```tsx
// app/providers.tsx
"use client";
import { Toaster } from "@/components/ui/sonner";
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Toaster />
    </>
  );
}
```
