# Sonner — Creator-Level Best Practices

Library: `sonner` by Emil Kowalski
Version researched: 2.0.7 (released August 2025)
Last researched: 2026-04-06
Sources: sonner.emilkowal.ski, github.com/emilkowalski/sonner,
emilkowal.ski/ui/building-a-toast-component, ui.shadcn.com.

---

## Authentication

**N/A — pure client-side React library.** Sonner has zero network
surface, no API keys, no tokens, no scopes, no service accounts,
no rate limits, no signing, no OAuth. The package ships ESM/CJS
to `node_modules`, runs entirely in the browser, and never makes
a network request of its own. Anything sensitive in toast content
(error messages, user data) is your app's responsibility — Sonner
just renders what you pass it.

The closest things to "credentials" are:
- The single shared `<Toaster />` mount at the app root.
- The `id` you pass to `toast(...)` calls for dedupe and update.
Neither is a secret; both are stable identifiers.

---

## Core Operations

The full callable API surface, with exact signatures and option
shapes derived from `sonner.emilkowal.ski/toast`:

```ts
// Base call — accepts a string or ReactNode
toast(message: ReactNode, options?: ToastOptions): string | number;

// Typed variants — same signature, auto-pick icon and color
toast.success(message: ReactNode, options?: ToastOptions): string | number;
toast.error(message: ReactNode, options?: ToastOptions): string | number;
toast.info(message: ReactNode, options?: ToastOptions): string | number;
toast.warning(message: ReactNode, options?: ToastOptions): string | number;
toast.message(message: ReactNode, options?: ToastOptions): string | number;

// Loading — manual lifecycle control. Usually called with an id
// you'll later resolve via toast.success({ id }) or toast.dismiss(id).
toast.loading(message: ReactNode, options?: ToastOptions): string | number;

// Promise — the canonical async pattern. Renders loading immediately,
// switches to success/error when the promise settles.
toast.promise<T>(
  promise: Promise<T> | (() => Promise<T>),
  data: {
    loading: string | ReactNode;
    success: string | ((data: T) => string | ReactNode);
    error: string | ((err: unknown) => string | ReactNode);
    description?: string | ((data: T) => string);
    finally?: () => void | Promise<void>;
  },
): { unwrap: () => Promise<T> };

// Custom — fully headless, you render the entire toast.
toast.custom(
  jsx: (id: string | number) => ReactElement,
  options?: ToastOptions,
): string | number;

// Dismiss — pass an id to dismiss one, no args to dismiss all.
toast.dismiss(id?: string | number): void;
```

The `ToastOptions` shape (every field is optional):

```ts
interface ToastOptions {
  id?: string | number;          // dedupe + manual update key
  description?: ReactNode;       // secondary text under title
  duration?: number;             // ms; default 4000; Infinity = sticky
  position?:                     // overrides Toaster position for one toast
    | "top-left" | "top-center" | "top-right"
    | "bottom-left" | "bottom-center" | "bottom-right";
  icon?: ReactNode;              // overrides default icon
  action?: {                     // primary button
    label: ReactNode;
    onClick: (e: MouseEvent) => void;
  } | ReactNode;
  cancel?: {                     // secondary button
    label: ReactNode;
    onClick?: (e: MouseEvent) => void;
  } | ReactNode;
  onDismiss?: (toast: ToastT) => void;       // user dismissed
  onAutoClose?: (toast: ToastT) => void;     // duration expired
  closeButton?: boolean;         // override Toaster setting per toast
  dismissible?: boolean;         // default true
  important?: boolean;           // bypass pauseWhenPageIsHidden
  unstyled?: boolean;            // strip Sonner's default classes
  invert?: boolean;              // inverse color scheme
  className?: string;
  descriptionClassName?: string;
  classNames?: {                 // per-part class override
    toast?: string;
    title?: string;
    description?: string;
    actionButton?: string;
    cancelButton?: string;
    closeButton?: string;
    icon?: string;
  };
  style?: CSSProperties;
}
```

The `<Toaster />` props (defaults from `sonner.emilkowal.ski/toaster`):

```ts
interface ToasterProps {
  theme?: "light" | "dark" | "system";          // default: "light"
  richColors?: boolean;                          // default: false
  expand?: boolean;                              // default: false
  visibleToasts?: number;                        // default: 3
  position?: Position;                           // default: "bottom-right"
  closeButton?: boolean;                         // default: false
  offset?: string | number | OffsetObject;       // default: "32px"
  mobileOffset?: string | number | OffsetObject; // default: "16px"
  swipeDirections?: SwipeDirection[];            // default: based on position
  dir?: "ltr" | "rtl" | "auto";                  // default: "ltr"
  hotkey?: string[];                             // default: ["altKey", "KeyT"]
  invert?: boolean;                              // default: false
  toastOptions?: ToastOptions;                   // default applied to every toast
  gap?: number;                                  // default: 14 (px between toasts)
  icons?: {                                      // override default icons globally
    success?: ReactNode;
    error?: ReactNode;
    info?: ReactNode;
    warning?: ReactNode;
    loading?: ReactNode;
    close?: ReactNode;
  };
  className?: string;
  style?: CSSProperties;
  cn?: (...classes: any[]) => string;            // for tailwind-merge etc
}
```

---

## Pagination

**N/A — Sonner has no list/query APIs.** It's a one-shot imperative
toast trigger. The closest analog is `visibleToasts` (default 3),
which caps how many toasts are simultaneously rendered. Excess toasts
queue and stack visually behind the visible ones; users see them
as a stack of edges and can hover to expand the stack.

---

## Rate Limits

**N/A — no network, no quotas.** The "rate limit" is purely visual:
`visibleToasts` (default 3) controls the on-screen cap. Anything
over that count stacks behind. If you fire 100 toasts in a loop,
all 100 are queued in memory and animate through — this is the
spam anti-pattern; dedupe with stable `id`.

The practical throughput cap is human-perceptible: more than ~2
toasts per second from one event becomes unreadable. Use
`toast.promise` or stable-id updates instead of multiple separate
toasts for the same workflow.

---

## Error Codes

**N/A — Sonner has no error codes.** The library never throws on
toast calls. Invalid options are silently ignored. The two ways
Sonner can "fail":

1. **No `<Toaster />` mounted.** `toast(...)` calls return an id
   but render nothing. No error, no console warning. Diagnose by
   confirming exactly one `<Toaster />` is mounted at the app root.
2. **Hydration mismatch in SSR (Next.js).** If `<Toaster />` is
   rendered in a server component without `"use client"`, you get
   a hydration warning. Always wrap in a client boundary.

Errors that originate INSIDE the toast (your `action.onClick`
throwing, your `onDismiss` callback throwing) propagate normally
to the React error boundary — Sonner does not swallow them.

---

## SDK Idioms

**Install:**
```bash
npm install sonner
# or via shadcn:
npx shadcn@latest add sonner
```

**The shadcn idiom** (canonical for EOS):
```tsx
// components/ui/sonner.tsx is generated by shadcn add
import { Toaster } from "@/components/ui/sonner";
// mount once at root:
<Toaster />
// fire from anywhere:
import { toast } from "sonner";
toast.success("Done");
```

**The promise idiom** — preferred for any async op:
```tsx
toast.promise(api.save(payload), {
  loading: "Saving...",
  success: "Saved",
  error: (err) => `Failed: ${err.message}`,
});
```

**The id idiom** — preferred for progress/long-running:
```tsx
const id = toast.loading("Uploading...");
try {
  await upload(file);
  toast.success("Uploaded", { id });
} catch (err) {
  toast.error("Upload failed", { id, description: err.message });
}
```

**The dedupe idiom** — for status that can repeat:
```tsx
// network listener fires repeatedly; show only one toast
window.addEventListener("offline", () => {
  toast.error("You're offline", { id: "net-status", duration: Infinity });
});
window.addEventListener("online", () => {
  toast.dismiss("net-status");
  toast.success("Back online", { id: "net-status" });
});
```

**Anti-idiom — never do this:**
```tsx
// WRONG: thunk form, Sonner won't call it
toast.promise(() => api.save(), { ... });
// WRONG: loading without resolution id
toast.loading("Working...");
await work();
toast.success("Done"); // creates a SECOND toast
```

---

## Anti-Patterns

1. **Multiple `<Toaster />` mounts.** Every toast renders in every
   mount. Looks like a duplicate-fire bug. Fix: exactly one mount
   at the app root.

2. **`toast.loading` without an id.** Loading toast hangs full
   duration while resolution toast appears next to it. Fix: capture
   id, pass to resolution, OR use `toast.promise`.

3. **Toast spam from un-deduped events.** Network listeners,
   websocket reconnects, polling errors fire toast.error in a loop.
   Fix: pass a stable `id` so repeats replace instead of stack.

4. **Toasting in render.** `function MyComponent() { toast(...); ... }`
   fires on every render. Fix: move into `useEffect` or event handler.

5. **Business logic in toast `action.onClick`.** Toast may unmount
   before async work resolves; you lose error handling. Fix: action
   should call a function defined in the component, not inline await.

6. **Generic error toasts swallowing the error.** `catch { toast.error("Error"); }`
   loses the cause. Fix: `toast.error("Failed", { description: err.message })`
   AND log to your error tracker.

7. **Hard-coded `duration: 1000`.** Breaks accessibility for screen
   reader users who need time to read. Fix: stay at default 4000ms
   or longer for important messages; use `closeButton` for sticky.

8. **Mounting `<Toaster />` inside a Dialog/Portal.** Toaster
   unmounts when the dialog closes, killing in-flight toasts.
   Fix: root mount only.

9. **Calling `toast` from a server component.** Hydration crash.
   Fix: `"use client"` boundary for any file that calls `toast`.

10. **Using `richColors` AND `toastOptions.classNames` for color.**
    `richColors` injects its own styles that override your classes
    for backgrounds. Pick one strategy.

---

## Data Model

Sonner has one runtime entity: the **Toast**.

```ts
type ToastT = {
  id: string | number;          // stable identity for dedupe/update
  type?: "success" | "error" | "info" | "warning" | "loading" | "default";
  title?: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  action?: { label: ReactNode; onClick: (e: MouseEvent) => void };
  cancel?: { label: ReactNode; onClick?: (e: MouseEvent) => void };
  duration?: number;            // ms
  promise?: () => Promise<unknown>;
  dismissible?: boolean;
  important?: boolean;
  position?: Position;
  closeButton?: boolean;
  // ...style/class overrides
};
```

State lives in a **global ToastState observer** outside React. The
`<Toaster />` subscribes to this observer and renders the current
queue. This is why `toast(...)` works from anywhere — server actions,
fetch handlers, error boundaries — without a Provider.

There is no parent/child relationship between toasts. There are
no groups. There is no persistence — toasts evaporate on full
page reload. If you need persistence, write to localStorage or
your DB and re-fire on mount.

---

## Webhooks

**N/A — no server, no events to webhook.** The closest analog
is the `onDismiss` and `onAutoClose` per-toast callbacks, which
fire locally when a toast leaves the screen. These run in your
React tree and have full closure access to your component scope.

```tsx
toast.success("Lead created", {
  onDismiss: (t) => analytics.track("toast.dismissed", { id: t.id }),
  onAutoClose: (t) => analytics.track("toast.auto_closed", { id: t.id }),
});
```

---

## Limits

- **Default `visibleToasts`:** 3 (configurable, no hard cap).
- **Default `duration`:** 4000ms.
- **Default `gap`:** 14px between toasts.
- **Default `offset`:** 32px desktop, 16px mobile.
- **Bundle size:** ~2-3KB gzipped (one of the smallest in the
  ecosystem).
- **No max toast count** in the queue — fire too many and you'll
  spike memory and animation cost. Practical cap: ~50 simultaneous
  before frame drops on low-end devices.
- **`description` is ReactNode** — you can pass arbitrarily complex
  content but it inherits the toast's max-width (~356px desktop).
- **Title/description length:** no hard limit; long strings wrap
  but very long content (>500 chars) breaks the visual rhythm.
  Truncate or use a Dialog instead for long content.

---

## Cost Model

**N/A — Sonner is MIT-licensed and free.** No paid tier, no
hosted service, no API quotas. The only "cost" is bundle weight
(~2-3KB gzipped) and the runtime cost of the always-mounted
`<Toaster />` observer (negligible).

---

## Version Pinning

- **Current version:** `sonner@2.0.7` (released August 2025).
- **Pin in `package.json`:** `"sonner": "2.0.7"` (no caret) for
  EOS — minor releases occasionally adjust default class names
  which break custom Tailwind overrides.
- **No API versioning** in the URL/header sense (it's a client
  library, not an API).
- **v1 → v2 migration:** v2 introduced the new `swipeDirections`
  API and changed default `position` handling. Most v1 code works
  unchanged in v2; the breaking change is for users who relied
  on the old swipe internals.
- **Peer deps:** React 18 or 19 (Sonner 2.x supports both).
- **TypeScript:** types ship with the package — no separate
  `@types/sonner`.
- **Deprecation policy:** Emil maintains semver. Breaking changes
  go in major releases with migration notes in the GitHub release
  notes.

---

## Design Intent

Emil Kowalski built Sonner in 2023 because every existing React
toast library required either a hook (`useToast()`), a context
provider, or both — meaning you couldn't fire a toast from outside
React. His thesis, stated in his "Building a toast component" essay
and in conference talks:

1. **Developer experience first.** "No hooks, no context. You
   insert `<Toaster />` once and you call `toast()` to create a
   toast." This is the explicit anti-thesis of `react-hot-toast`'s
   `useToaster()` API and Radix Toast's provider-based approach.

2. **Beauty as leverage.** "It looks good. It has nice defaults
   and good animations... People simply like beautiful things.
   Beauty is generally underutilized in software so you can use
   it as leverage to stand out." Sonner ships opinionated visual
   defaults — the spring animation, the stack-on-hover behavior,
   the swipe gesture — because Emil believes good defaults are
   more valuable than configurability.

3. **Momentum-based swipe.** Mobile users expect to swipe
   notifications away. Sonner implemented this on day one with
   a momentum-based gesture (no threshold) so it feels native.
   Desktop swipe is supported as a "delight" feature most users
   never discover but power users love.

4. **Global observer over hooks.** The state lives outside React
   so toasts persist across route changes, can be fired from
   non-React code (fetch interceptors, error boundaries, server
   actions), and survive the parent unmounting. This is the
   single most important design decision — it's what makes the
   API "two lines."

The tradeoff: you get one global toast layer per app. You can't
have isolated toast scopes (e.g., toasts for one modal that
disappear when the modal closes). Emil considers this a feature,
not a limit.

---

## Problem-Solution Map

| Problem | Sonner solution |
|---|---|
| Show success/error after a mutation | `toast.success` / `toast.error` (one line) |
| Track an async op end-to-end | `toast.promise(promise, { loading, success, error })` |
| Update a toast as work progresses | Stable `id` + repeated `toast.loading({ id })` |
| Avoid duplicate toasts from repeated events | Stable `id` — same id replaces, never stacks |
| Sticky error the user must acknowledge | `duration: Infinity, closeButton: true` |
| Undo pattern after destructive action | `toast(..., { action: { label: "Undo", onClick }})` |
| Long-running background work feedback | `toast.loading("...", { id })` then resolve |
| Network status indicator | Stable id + `online`/`offline` listeners + dismiss |
| Per-mutation feedback in React Query | Per-call `toast.promise` OR global `MutationCache.onError` |
| Custom UI in a toast | `toast.custom((id) => <YourComponent id={id} />)` |
| Theme-aware toasts | `<Toaster theme={theme} />` bound to next-themes |
| Toast from non-React code | Just import `toast` and call — works from anywhere |

Hidden capability: `toast.custom` returns a fully headless slot
where YOU render the entire toast (still inside Sonner's stack
and animation). This is how power users build progress bars,
inline forms, or rich preview cards inside a "toast." Most users
never discover this.

---

## Operational Behavior

- **Mount lifecycle.** `<Toaster />` should mount exactly once
  per app, at the root. The observer is global, so even if you
  unmount and remount Toaster mid-session, queued toasts persist
  in the observer and re-render on the new mount. But re-mounting
  causes existing visible toasts to flash/restart — avoid.

- **Animation timing.** Default enter is ~400ms spring, exit is
  ~200ms. Don't fire a toast and immediately programmatically
  dismiss it within 100ms — you'll see flicker.

- **Pause on hover.** Hovering any visible toast pauses ALL
  toast timers (the entire stack). Moving the mouse away resumes
  all timers from where they paused. This is the right default
  but surprises people debugging "why didn't my toast close."

- **Pause on tab hidden.** By default, toasts pause when the tab
  is hidden (`pauseWhenPageIsHidden`). `important: true` opts out
  per-toast.

- **SSR.** Sonner's `<Toaster />` works in Next.js App Router as
  long as it's inside a `"use client"` boundary. Server components
  can import `toast` but cannot CALL it — calls must happen in
  client code or event handlers.

- **Memory.** Each toast is a small object in the observer's
  queue. Dismissed toasts are GC'd promptly. No leaks from normal
  usage.

- **Order.** Toasts render newest-on-top by default at bottom
  positions, newest-on-bottom at top positions. The "stack"
  visualization is automatic when more toasts than `visibleToasts`
  exist.

- **Concurrent calls.** Firing 10 `toast(...)` calls in the same
  microtask queue results in 10 distinct toasts (no auto-dedupe).
  You must opt in to dedupe via stable `id`.

---

## Ecosystem Position

Sonner is **the de facto toast layer for the shadcn/ui ecosystem**
as of 2026. shadcn officially replaced its built-in toast with
Sonner; the install command `npx shadcn@latest add sonner` is
canonical.

Position in a typical React stack:

- **Above** React Query / SWR (toast is the feedback layer for
  mutations)
- **Above** React Hook Form (toast on submit success/failure)
- **Beside** Radix UI Dialog/Popover (toast for outside-the-modal
  feedback)
- **Below** your error tracker (Sentry, PostHog) — toast is UX,
  the tracker is forensics; both fire in the same `catch`.

**Natural complements:**
- shadcn/ui (canonical install)
- TanStack Query (`MutationCache.onError` global toast)
- React Hook Form (submit handler `toast.promise`)
- next-themes (theme-aware Toaster)
- Tailwind CSS (per-part class override via `toastOptions.classNames`)

**Forced integrations / friction:**
- @radix-ui/react-toast — Sonner replaces it. Don't run both.
- react-hot-toast — same. Don't run both.
- React Native — Sonner is web-only; use `react-native-toast-message`.

**The 2026 trend:** Timo Lins (creator of react-hot-toast) publicly
acknowledged Sonner's strengths and is rebuilding react-hot-toast
to match. Sonner's lead is the API ergonomics and the visual
defaults; competitors are catching up on features but not on the
"opinionated good defaults" philosophy.

---

## Trajectory

- **Active development.** v2.0.7 shipped August 2025. Releases
  every few months, focused on polish and edge cases rather than
  big new features.
- **API stability.** The core API (`toast`, `toast.promise`,
  `toast.custom`) has not changed since v1. Confidence to build
  on it long-term is high.
- **React 19 support** is in. Sonner is React 19 compatible.
- **Server actions / RSC integration.** Sonner works with Next.js
  Server Actions via `useFormState` + client-side toast call —
  no special API needed.
- **Frontier direction:** Emil's 2025 talks emphasize using toasts
  as a primitive for AI command-result feedback (chat UIs that
  show "Tool used: search_db" toasts as the LLM works). Expect
  more guidance on this pattern but no API changes.
- **Things being de-emphasized:** none observed. No deprecations
  in 2.x. No deprecated endpoints to migrate off.
- **Risk:** Single maintainer (Emil). High bus factor. Mitigation:
  the library is small enough to fork and maintain in-house if
  needed (~1500 LOC).

---

## Conceptual Model

**Think of Sonner as a global event bus with a UI on the end.**

The mental model:

1. **The observer.** A singleton outside React that holds the
   current toast queue. Lives for the life of the page.
2. **The trigger.** `toast(...)` pushes onto the observer. Returns
   an id you can use to update or dismiss.
3. **The renderer.** `<Toaster />` subscribes to the observer
   and renders the queue with animations, stack management, and
   gestures.

The primitives:

- **toast** = "publish a feedback event"
- **id** = "the address of one event"
- **duration** = "auto-unsubscribe timer"
- **promise** = "subscribe a feedback event to a Promise's lifecycle"
- **dismiss** = "unsubscribe an event"

The verbs:

- `success/error/info/warning/loading/message` — typed publishes
- `promise` — bind to async lifecycle
- `custom` — publish raw JSX
- `dismiss` — unsubscribe one or all

**Recipe: full async mutation feedback loop**

```tsx
const mutation = useMutation({
  mutationFn: (values) => api.createLead(values),
  onSuccess: (lead) => {
    qc.invalidateQueries({ queryKey: ["leads"] });
  },
});

function onSubmit(values: FormValues) {
  toast.promise(mutation.mutateAsync(values), {
    loading: "Creating lead...",
    success: (lead) => `Created ${lead.name}`,
    error: (err) => `Failed: ${err.message}`,
  });
}
```

**Recipe: optimistic update with rollback toast**

```tsx
const mutation = useMutation({
  mutationFn: archiveLead,
  onMutate: async (id) => {
    await qc.cancelQueries({ queryKey: ["leads"] });
    const prev = qc.getQueryData<Lead[]>(["leads"]);
    qc.setQueryData<Lead[]>(["leads"], (old = []) =>
      old.filter((l) => l.id !== id),
    );
    return { prev };
  },
  onError: (err, _id, ctx) => {
    if (ctx?.prev) qc.setQueryData(["leads"], ctx.prev);
    toast.error("Failed to archive — restored", {
      description: err.message,
    });
  },
  onSuccess: () => {
    toast("Lead archived", {
      action: { label: "Undo", onClick: () => unarchive() },
    });
  },
});
```

---

## Industry Expert

**How Vercel, Cursor, and X use Sonner in 2026:**

- **Vercel dashboard.** Sonner is the feedback layer for every
  deployment action. Promise-based for "Deploying..." → "Deployed
  to production" with action button "View deployment." This is
  the canonical use of `toast.promise` + `action`.
- **Cursor IDE.** Uses Sonner for AI command-result feedback —
  "Searching codebase," "Edit applied," "Test failed: 3 errors."
  This is the frontier pattern: toasts as transient log for
  agentic operations. Each toast has a stable id derived from
  the tool call id, so updates flow naturally.
- **X (Twitter).** Sonner for inline feedback on post/like/repost
  actions. Notable: short duration (2000ms) and no `richColors`
  to match the brand.

**Frontier patterns most users miss:**

1. **Toast as transient log for agent operations.** Each tool
   call gets a toast with a stable id; updates flow as the tool
   reports progress; the toast resolves to success/error when
   the tool returns. EOS uses this pattern in `services/discord_bot.py`'s
   web counterpart for surfacing AI operations to the user.

2. **Batched toast collapsing.** Instead of firing N toasts for
   N items, fire ONE toast with a stable id and update its
   description as the batch progresses: "Imported 12/50 leads..."
   This is the right way to handle bulk operations.

3. **Undo as a UX primitive.** Use `toast(..., { action })` for
   any destructive operation instead of confirm dialogs. The
   action is faster, less interruptive, and reversible. Vercel
   pioneered this pattern and Sonner makes it one line.

4. **Toast.custom for inline forms.** A toast that contains a
   small form (e.g., "Add a note before archiving?") gives you
   modal-like interaction without a Dialog. Power-user move.

5. **`onDismiss` for analytics.** Track which toasts users
   dismiss vs auto-close to learn which messages are useful.

6. **Stable id for status indicators.** Network status, sync
   status, build status — all use stable ids so updates replace
   instead of stack. The toast becomes a "live region" without
   any React state in your app.

The creator-level move is realizing Sonner is not "a toast
library" — it's a global UI event bus with built-in animation,
gesture, and accessibility. Once you see it that way, you stop
reaching for Dialogs and Banners for transient state and use
toasts for everything ephemeral.
