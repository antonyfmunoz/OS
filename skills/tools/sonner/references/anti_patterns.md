# Sonner — Anti-Patterns

## 1. Multiple `<Toaster />` mounts

**Wrong:**
```tsx
// app/layout.tsx
<Toaster />
// app/(dashboard)/layout.tsx
<Toaster />  // every toast now renders TWICE
```

**Right:** exactly one `<Toaster />` at the absolute root.

## 2. `toast.loading` without an id

**Wrong:**
```tsx
toast.loading("Saving...");
await save();
toast.success("Saved"); // creates a SECOND toast; loading hangs 4s
```

**Right:**
```tsx
const id = toast.loading("Saving...");
await save();
toast.success("Saved", { id });
// OR just use toast.promise
```

## 3. Toast spam from un-deduped events

**Wrong:**
```tsx
socket.on("error", (err) => toast.error(err.message));
// 10 errors in a second = 10 stacked toasts
```

**Right:**
```tsx
socket.on("error", (err) =>
  toast.error(err.message, { id: "socket-err" })
);
```

## 4. Toasting in render

**Wrong:**
```tsx
function Page({ data }: { data: Data | null }) {
  if (!data) toast.error("No data"); // fires every render
  return <div>...</div>;
}
```

**Right:**
```tsx
React.useEffect(() => {
  if (!data) toast.error("No data");
}, [data]);
```

## 5. Business logic inside `action.onClick`

**Wrong:**
```tsx
toast("Archived", {
  action: {
    label: "Undo",
    onClick: async () => {
      await unarchive();          // toast may unmount mid-await
      qc.invalidateQueries(...);  // error tracking lost
    },
  },
});
```

**Right:** action calls a stable function defined outside the toast,
which has its own try/catch and error reporting.

## 6. Generic error toast that swallows the cause

**Wrong:**
```tsx
try { await op(); } catch { toast.error("Error"); }
```

**Right:**
```tsx
try {
  await op();
} catch (err) {
  toast.error("Operation failed", {
    description: err instanceof Error ? err.message : String(err),
  });
  reportError(err); // also log to Sentry/PostHog
}
```

## 7. `toast.promise` with a thunk

**Wrong:**
```tsx
toast.promise(() => api.save(), { loading: "...", success: "...", error: "..." });
// loading shows forever; Sonner never invokes the thunk
```

**Right:**
```tsx
toast.promise(api.save(), { loading: "...", success: "...", error: "..." });
// pass the PROMISE, not a thunk
```

## 8. Hard-coded short duration breaking accessibility

**Wrong:**
```tsx
toast.success("Saved", { duration: 800 });
// screen reader users can't read it before it disappears
```

**Right:** keep default 4000ms or longer, or use `closeButton`.

## 9. `<Toaster />` mounted inside a dialog/portal

**Wrong:** Toaster lives inside the modal tree → unmounts on close,
killing in-flight toasts.

**Right:** Toaster at the app root, ALWAYS mounted.

## 10. Calling `toast` from a server component

**Wrong:**
```tsx
// app/page.tsx (server component)
import { toast } from "sonner";
toast("hi"); // hydration crash
```

**Right:** mark file `"use client"` or move call into a client event handler.

## 11. `richColors` + custom Tailwind colors

**Wrong:** enabling `richColors` AND trying to override toast colors
via `toastOptions.classNames` — `richColors` injects inline styles
that win.

**Right:** pick one strategy. Either use `richColors` for the
opinionated palette OR disable it and theme via `classNames`.

## 12. Race condition capturing id in component state

**Wrong:**
```tsx
const [id, setId] = React.useState<string | number | null>(null);
async function go() {
  const newId = toast.loading("...");
  setId(newId);          // re-render
  await work();
  toast.success("ok", { id }); // STALE id from closure
}
```

**Right:** capture in a local variable or `useRef`, not state.

## 13. Multiple toasts per item in a bulk operation

**Wrong:**
```tsx
for (const item of items) {
  await processItem(item);
  toast.success(`Imported ${item.name}`);
}
// 50 items = 50 toasts
```

**Right:**
```tsx
const id = toast.loading(`Importing 0/${items.length}`);
let done = 0;
for (const item of items) {
  await processItem(item);
  done++;
  toast.loading(`Importing ${done}/${items.length}`, { id });
}
toast.success(`Imported ${items.length}`, { id });
```
